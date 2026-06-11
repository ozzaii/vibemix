# SPDX-License-Identifier: Apache-2.0
"""ClapEmbedder — the on-device CLAP product embedder.

Phase 90: wraps :class:`vibemix.library.clap_engine.ClapEngine` (Xenova ONNX,
512-dim) behind the SAME public surface the rest of the library layer already
expects — so ``vibe_search`` / ``folder_ingest`` / ``grounding`` / the Viber
agent all use one backend-neutral embedder contract:

    embed_track(track)            -> (512,) float32, L2-normalized   [+ cache]
    embed_query(query)            -> (512,) float32, L2-normalized
    embed_audio_bytes(data, mime) -> (512,) float32, L2-normalized
    has_cached_embedding(track)   -> bool

Selected by ``embed_factory.build_embedder`` as the product embedding path.
The legacy cloud embedder remains only as migration/test code; normal
library/search/curate embeddings are CLAP.

Cache: reuses the SAME ``embeddings.db`` content-hash store, but the key carries a
CLAP model tag so CLAP vectors never collide with historical Gemini rows (and
the ``_cosine`` wrong-dim guard turns any stale row into a clean miss anyway).

Import-safe: constructing a ClapEmbedder does NOT import onnxruntime/tokenizers
— that is deferred to ``ClapEngine`` on first embed (mirrors the engine's lazy
contract), so ``import vibemix.library.embed_clap`` is safe where CLAP deps are
absent.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from pathlib import Path

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.library.clap_engine import ClapEngine
from vibemix.library.embed_cache import (
    init_cache_schema as _init_cache_schema,
)
from vibemix.library.embed_cache import (
    open_default_cache_db as _open_default_cache_db,
)
from vibemix.library.embed_config import (
    CUE_ANCHORED_STRATEGY_VERSION,
    DEFAULT_EMBED_STRATEGY,
    EMBED_STRATEGIES,
)
from vibemix.library.rekordbox import TrackEntry

logger = logging.getLogger(__name__)

# Cache-key namespace: distinct from any Gemini model id so clap rows never
# collide with Gemini rows in the shared embeddings.db. Bump on a model change.
_CLAP_MODEL_TAG = "clap-xenova-music-and-speech-512"


class ClapEmbedder:
    """On-device CLAP product embedder (512-dim)."""

    def __init__(
        self,
        engine: ClapEngine | None = None,
        cache_db: sqlite3.Connection | None = None,
        embed_strategy: str = DEFAULT_EMBED_STRATEGY,
    ) -> None:
        if embed_strategy not in EMBED_STRATEGIES:
            raise ValueError(
                f"unknown embed_strategy {embed_strategy!r}; "
                f"expected one of {EMBED_STRATEGIES!r}"
            )
        # Lazy engine — no heavy import here (ClapEngine defers onnxruntime).
        self._engine = engine if engine is not None else ClapEngine(backend="onnx")
        self._model = _CLAP_MODEL_TAG
        self._embed_strategy = embed_strategy
        if cache_db is None:
            self._cache = _open_default_cache_db()
            self._owns_cache = True
        else:
            _init_cache_schema(cache_db)
            self._cache = cache_db
            self._owns_cache = False

    def __del__(self) -> None:  # pragma: no cover - GC path
        if getattr(self, "_owns_cache", False) and self._cache is not None:
            try:
                self._cache.close()
            except Exception:
                pass

    # ─── Public product embedder surface ───────────────────────────────────
    def embed_track(self, track: TrackEntry) -> np.ndarray:
        """Embed a track → (512,) float32 L2-normalized. Audio when the file is
        local; otherwise a CLAP TEXT embed of the title/artist signature (CLAP is
        cross-modal — text + audio share one 512-dim space)."""
        key = self._track_hash(track)
        cached = self._cache_get(key)
        if cached is not None:
            from vibemix.library.budget import get_telemetry as _gt
            _gt().increment_cache_hit()
            return cached

        local_path: Path | None = None
        if track.filepath:
            p = Path(track.filepath)
            if p.exists():
                local_path = p

        if local_path is not None:
            if self._embed_strategy == "cue_anchored":
                from vibemix.library.ingest import _embed_track_cue_anchored

                vector = _embed_track_cue_anchored(track, local_path, self)
            else:
                vector = self.embed_audio_file(str(local_path))
        else:
            vector = self._engine.embed_query(_text_signature(track))
        vector = l2_normalize(np.asarray(vector, dtype=np.float32))
        self._cache_put(key, vector)
        return vector

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a text vibe-search query → (512,) float32 L2-normalized."""
        return l2_normalize(np.asarray(self._engine.embed_query(query), dtype=np.float32))

    def embed_audio_bytes(self, data: bytes, mime: str) -> np.ndarray:
        """Embed raw audio bytes → (512,) — the grounding ('what's playing') path."""
        return l2_normalize(
            np.asarray(self._engine.embed_audio_bytes(data, mime), dtype=np.float32)
        )

    def embed_audio_array(self, samples: np.ndarray, *, sr: int) -> np.ndarray:
        """Embed already-decoded mono samples → (512,) — the PyAV window path.

        Skips the tempfile + re-decode round trip ``embed_audio_bytes`` pays;
        the window slicers feed CLAP-rate arrays straight to the engine.
        """
        return l2_normalize(
            np.asarray(self._engine.embed_audio_array(samples, sr=sr), dtype=np.float32)
        )

    def embed_audio_file(self, path: str) -> np.ndarray:
        """Embed a local audio file → (512,), used by cue fallback paths."""
        return l2_normalize(
            np.asarray(self._engine.embed_audio_file(path), dtype=np.float32)
        )

    def has_cached_embedding(self, track: TrackEntry) -> bool:
        try:
            return self._cache_get(self._track_hash(track)) is not None
        except sqlite3.Error:
            return False

    # ─── Internal: content-hash cache (clap-tagged) ────────────────────────
    def _track_hash(self, track: TrackEntry) -> str:
        h = hashlib.sha256()
        if track.filepath and Path(track.filepath).exists():
            with Path(track.filepath).open("rb") as f:
                while True:
                    chunk = f.read(64 * 1024)
                    if not chunk:
                        break
                    h.update(chunk)
        else:
            h.update(f"<streaming>{track.track_id}".encode())
        h.update(b"||")
        h.update(self._model.encode())
        if self._embed_strategy == "cue_anchored":
            h.update(b"||")
            h.update(CUE_ANCHORED_STRATEGY_VERSION.encode())
        return h.hexdigest()

    def _cache_get(self, key: str) -> np.ndarray | None:
        row = self._cache.execute(
            "SELECT vector FROM embed_cache WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        vec = np.frombuffer(row[0], dtype=np.float32).copy()
        if vec.shape[0] != EMBEDDING_DIM:  # stale-dim row → clean miss
            return None
        return vec

    def _cache_put(self, key: str, vector: np.ndarray) -> None:
        assert vector.dtype == np.float32 and vector.shape == (EMBEDDING_DIM,)
        self._cache.execute(
            "INSERT OR REPLACE INTO embed_cache (key, vector, ts) VALUES (?, ?, ?)",
            (key, vector.tobytes(), time.time()),
        )
        self._cache.commit()


def _text_signature(track: TrackEntry) -> str:
    """Compact 'title by artist | BPM | key' signature for the text fallback."""
    parts = [track.title or track.track_id]
    if getattr(track, "artist", None):
        parts.append(f"by {track.artist}")
    extra = []
    if getattr(track, "bpm", None):
        extra.append(f"{track.bpm:.0f} BPM")
    if getattr(track, "key", None):
        extra.append(str(track.key))
    sig = " ".join(parts)
    if extra:
        sig += " | " + " | ".join(extra)
    return sig
