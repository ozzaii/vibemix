# SPDX-License-Identifier: Apache-2.0
"""LibraryEmbedder — Gemini Embedding 2 client for Phase 28 library work.

# Proxy-only contract
==================

This module NEVER reads any AIza-style env var directly. All Gemini API
traffic flows through the Bravoh proxy via ``build_proxy_genai_client``.
Callers (``__main__.py`` boot path + drag-drop importer) build the proxy
client once and pass it in. The privacy + cost-control invariants from
LIBRARY-04 + LIBRARY-10 hold because this module cannot bypass the proxy.

# Strategy
========

1. Tracks with ``duration_s > 180`` are split into 3 mp3 excerpts
   (intro / mid / outro, 60s each via ffmpeg) and the mean of their
   embeddings is used. Mitigates Pitfall P54 (Gemini Embedding 2's 180s
   audio cap).
2. Tracks <= 180s pass the raw file as a single audio Part.
3. Streaming-only tracks (no local file) fall back to text-only embed of
   ``"title by artist | bpm BPM | key K"``.
4. Every embed is keyed by SHA256 of
   ``(file_bytes || model_id || strategy_version)`` and persisted to
   ``~/.cache/vibemix/embeddings.db`` so re-imports do 0 API calls.
5. Output dimensionality is locked to 768 (CONTEXT D-cost-balanced;
   MRL-truncated from Gemini Embedding 2's native 3072).

# Critical corrections (Phase 28 RESEARCH Open Qs)
===============================================

- Model ID is ``gemini-embedding-2`` (Open Q9 — earlier text-only
  embedding-0xx series is superseded and CONTEXT was stale).
- Cache DB path is ``~/.cache/vibemix/embeddings.db`` — distinct from
  Plan 02's ``library.db`` (vec0 store) and Phase 25's ``library.pkl``
  (Rekordbox parsed cache).
- No legacy task-routing kwarg (Open Q8 — not valid for Embedding 2).
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from google import genai
from google.genai import types

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.library.rekordbox import TrackEntry

logger = logging.getLogger(__name__)


# ─── Locked constants ──────────────────────────────────────────────────────────

# Open Q9 — Gemini Embedding 2 supersedes the legacy text-only embedding series.
GEMINI_EMBEDDING_MODEL = "gemini-embedding-2"

# Bump to invalidate ALL cached embeddings. Format: vN-<strategy-name>.
EXCERPT_STRATEGY_VERSION = "v1-3excerpt-mean"

# Gemini Embedding 2 hard audio cap. P54.
AUDIO_CAP_SECONDS = 180

# Per excerpt length in the 3-excerpt path.
EXCERPT_DURATION = 60

# ffmpeg subprocess timeout per excerpt — guard against malformed audio.
FFMPEG_TIMEOUT_SECONDS = 30

# Cache database. NOT library.db (Plan 02 owns that for vec0). NOT
# library.pkl (Phase 25 Rekordbox parsed cache).
EMBED_CACHE_DB_PATH = Path.home() / ".cache" / "vibemix" / "embeddings.db"

# Re-export so downstream plans don't have to import from _cosine directly.
__all__ = [
    "LibraryEmbedder",
    "GEMINI_EMBEDDING_MODEL",
    "EXCERPT_STRATEGY_VERSION",
    "EMBEDDING_DIM",
    "AUDIO_CAP_SECONDS",
    "EMBED_CACHE_DB_PATH",
]


# ─── ffmpeg availability check ─────────────────────────────────────────────────


def _require_ffmpeg() -> str:
    """Return the ffmpeg binary path or raise RuntimeError (fail-loud).

    Per RESEARCH "ffmpeg not available" pitfall: ffmpeg is a hard requirement
    for the 3-excerpt path. Surface the missing-binary error at module entry
    rather than mid-embed.
    """
    ff = shutil.which("ffmpeg")
    if ff is None:
        raise RuntimeError(
            "ffmpeg is required for the LibraryEmbedder 3-excerpt path. "
            "Install via `brew install ffmpeg` (mac) or "
            "`winget install Gyan.FFmpeg` (windows)."
        )
    return ff


# ─── Cache helpers ─────────────────────────────────────────────────────────────


def _open_default_cache_db() -> sqlite3.Connection:
    """Open the default ~/.cache/vibemix/embeddings.db with schema init."""
    EMBED_CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(EMBED_CACHE_DB_PATH))
    _init_cache_schema(conn)
    return conn


def _init_cache_schema(conn: sqlite3.Connection) -> None:
    """Idempotent: create embed_cache table if absent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embed_cache (
            key TEXT PRIMARY KEY,
            vector BLOB NOT NULL,
            ts REAL NOT NULL
        )
        """
    )
    conn.commit()


# ─── LibraryEmbedder ───────────────────────────────────────────────────────────


class LibraryEmbedder:
    """Single entry point for embedding tracks + queries via Gemini Embedding 2.

    Construction:
        ``LibraryEmbedder(client, cache_db=None)`` where ``client`` is a
        proxy-wired ``genai.Client`` built via
        ``vibemix.agent.proxy_client.build_proxy_genai_client(...)``.
        ``cache_db`` defaults to ``~/.cache/vibemix/embeddings.db``.

    Public API:
        ``embed_track(track)`` → 768-dim float32 L2-normalized vector.
        ``embed_query(query)`` → 768-dim float32 L2-normalized vector (no
            content-hash cache here; Plan 03 owns the 24h query cache).

    Thread safety:
        SQLite connection is not safe across threads by default. Callers in
        async contexts must wrap embed calls in
        ``loop.run_in_executor(None, embedder.embed_track, track)`` (matches
        the existing cohost_v4 pattern).
    """

    def __init__(
        self,
        client: genai.Client,
        cache_db: sqlite3.Connection | None = None,
    ) -> None:
        self._client = client
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

    # ─── Public surface ────────────────────────────────────────────────────

    def embed_track(self, track: TrackEntry) -> np.ndarray:
        """Embed a track, returning a 768-dim float32 L2-normalized vector.

        Decision tree:
            1. content-hash cache hit → return cached
            2. local file exists → audio path (3-excerpt if > 180s else
               single call)
            3. else → text-only embed of "title by artist | BPM | key"
        """
        key = self._track_hash(track)
        cached = self._cache_get(key)
        if cached is not None:
            logger.debug("LibraryEmbedder cache hit: %s", track.track_id)
            # Plan 28-08 — telemetry.
            from vibemix.library.budget import get_telemetry as _gt
            _gt().increment_cache_hit()
            return cached

        local_path: Path | None = None
        if track.filepath:
            p = Path(track.filepath)
            if p.exists():
                local_path = p

        if local_path is not None:
            vector = self._embed_audio(local_path, track.duration_s)
        else:
            text = self._text_signature(track)
            vector = self._call_gemini_text(text)
            vector = l2_normalize(vector)

        self._cache_put(key, vector)
        return vector

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a natural-language vibe-search query (text-only path).

        No content-hash cache here — Plan 28-03's 24h LRU sits on top of
        this, keyed on ``query + library_snapshot_hash``.
        """
        vec = self._call_gemini_text(query)
        return l2_normalize(vec)

    # ─── Internal: audio path ──────────────────────────────────────────────

    def _embed_audio(self, audio_path: Path, duration_s: float) -> np.ndarray:
        """Audio embed path. Returns L2-normalized float32 vector."""
        # Short track — try single call first; on cap-error, force-fallback.
        force_excerpts = False
        if duration_s <= AUDIO_CAP_SECONDS:
            try:
                clip = audio_path.read_bytes()
                mime = self._mime_for_path(audio_path)
                vec = self._call_gemini_audio_single(clip, mime)
                return l2_normalize(vec)
            except Exception as e:
                if not self._is_audio_cap_error(e):
                    raise
                logger.warning(
                    "Single-call audio embed failed with cap error "
                    "(%s); falling back to 3-excerpt path.",
                    e,
                )
                force_excerpts = True

        # 3-excerpt path: intro / mid / outro.
        excerpts = self._extract_excerpts(
            audio_path, duration_s, force=force_excerpts
        )
        vecs: list[np.ndarray] = []
        for clip in excerpts:
            vec = self._call_gemini_audio_single(clip, mime_type="audio/mpeg")
            vecs.append(vec)
        mean = np.mean(np.stack(vecs), axis=0).astype(np.float32)
        return l2_normalize(mean)

    @staticmethod
    def _mime_for_path(path: Path) -> str:
        """Pick MIME type for the single-call path.

        Per Open Q6: ffmpeg transcodes to MP3 for the 3-excerpt path, so the
        mid path is always audio/mpeg. The single-call path passes the file
        bytes through directly — pick MIME by suffix.
        """
        suffix = path.suffix.lower()
        if suffix == ".wav":
            return "audio/wav"
        if suffix == ".flac":
            return "audio/flac"
        if suffix in (".m4a", ".aac"):
            return "audio/mp4"
        return "audio/mpeg"

    @staticmethod
    def _is_audio_cap_error(err: Exception) -> bool:
        """Heuristic match for Gemini 'audio too long' / 400 cap errors."""
        msg = str(err).lower()
        if "too long" in msg:
            return True
        if "audio cap" in msg or "duration" in msg and "180" in msg:
            return True
        # google.genai.errors.APIError carries .code on some versions.
        code = getattr(err, "code", None) or getattr(err, "status_code", None)
        if code == 400 and "audio" in msg:
            return True
        return False

    def _extract_excerpts(
        self,
        audio_path: Path,
        duration_s: float,
        force: bool = False,
    ) -> list[bytes]:
        """Use ffmpeg to slice 3 mp3 excerpts (intro / mid / outro).

        Each excerpt is 60s, encoded as MP3 at 128 kbps. Tempfiles are
        cleaned up before return.

        For tracks <= 180s, normally we should not be here (single-call
        path handles them); defensive guard returns the whole file as 1
        excerpt. Pass ``force=True`` to override (used when the single-call
        path fails with an audio-cap error and we want a 3-excerpt
        fallback even on a short-duration track).
        """
        if duration_s <= AUDIO_CAP_SECONDS and not force:
            return [audio_path.read_bytes()]

        ffmpeg = _require_ffmpeg()
        starts: list[float] = [
            0.0,
            max(0.0, (duration_s / 2.0) - (EXCERPT_DURATION / 2.0)),
            max(0.0, duration_s - EXCERPT_DURATION),
        ]
        out_clips: list[bytes] = []
        for start in starts:
            with tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            ) as tmp:
                tmp_path = Path(tmp.name)
            try:
                cmd = [
                    ffmpeg,
                    "-y",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{start:.3f}",
                    "-i",
                    str(audio_path),
                    "-t",
                    str(EXCERPT_DURATION),
                    "-acodec",
                    "libmp3lame",
                    "-b:a",
                    "128k",
                    str(tmp_path),
                ]
                subprocess.run(
                    cmd,
                    check=True,
                    timeout=FFMPEG_TIMEOUT_SECONDS,
                    capture_output=True,
                )
                out_clips.append(tmp_path.read_bytes())
            finally:
                try:
                    tmp_path.unlink()
                except FileNotFoundError:
                    pass
        return out_clips

    # ─── Internal: Gemini calls ───────────────────────────────────────────

    def _call_gemini_audio_single(
        self, clip: bytes, mime_type: str
    ) -> np.ndarray:
        """Single audio-Part embed_content call."""
        result = self._client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=[types.Part.from_bytes(data=clip, mime_type=mime_type)],
            config=types.EmbedContentConfig(
                output_dimensionality=EMBEDDING_DIM
            ),
        )
        values = list(result.embeddings[0].values)
        # Plan 28-08 — runtime cost telemetry.
        from vibemix.library.budget import get_telemetry as _gt
        _gt().increment_audio_embed()
        return np.asarray(values, dtype=np.float32)

    def _call_gemini_text(self, text: str) -> np.ndarray:
        """Text-mode embed_content call.

        Per Gemini SDK 2.0.1: text mode takes a string directly, NOT a
        list. ``contents="..."`` not ``contents=["..."]``.
        """
        result = self._client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(
                output_dimensionality=EMBEDDING_DIM
            ),
        )
        values = list(result.embeddings[0].values)
        # Plan 28-08 — runtime cost telemetry.
        from vibemix.library.budget import get_telemetry as _gt
        _gt().increment_text_embed()
        return np.asarray(values, dtype=np.float32)

    # ─── Internal: text-only signature & cache key ────────────────────────

    @staticmethod
    def _text_signature(track: TrackEntry) -> str:
        """Build the text-only embed signature for streaming-only tracks.

        Phase 25's TrackEntry coerces missing bpm to 0.0 and missing key
        to empty string, so we just stringify in place.
        """
        bpm = int(track.bpm or 0)
        key = track.key or "unknown"
        return f"{track.title} by {track.artist} | {bpm} BPM | key {key}"

    @staticmethod
    def _track_hash(track: TrackEntry) -> str:
        """SHA256 of (file_bytes_or_marker || model_id || strategy_version).

        For local files: stream in 64KB chunks (avoid loading large mp3s).
        For streaming-only: marker derived from track_id so re-imports of
        the same streaming-only entry still cache-hit.
        """
        h = hashlib.sha256()
        if track.filepath:
            p = Path(track.filepath)
            if p.exists():
                with p.open("rb") as f:
                    while True:
                        chunk = f.read(64 * 1024)
                        if not chunk:
                            break
                        h.update(chunk)
            else:
                h.update(f"<streaming>{track.track_id}".encode())
        else:
            h.update(f"<streaming>{track.track_id}".encode())
        h.update(b"||")
        h.update(GEMINI_EMBEDDING_MODEL.encode())
        h.update(b"||")
        h.update(EXCERPT_STRATEGY_VERSION.encode())
        return h.hexdigest()

    # ─── Internal: cache get/put ──────────────────────────────────────────

    def _cache_get(self, key: str) -> np.ndarray | None:
        row = self._cache.execute(
            "SELECT vector FROM embed_cache WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        blob = row[0]
        return np.frombuffer(blob, dtype=np.float32).copy()

    def _cache_put(self, key: str, vector: np.ndarray) -> None:
        import time as _time

        assert vector.dtype == np.float32 and vector.shape == (EMBEDDING_DIM,)
        self._cache.execute(
            "INSERT OR REPLACE INTO embed_cache (key, vector, ts) "
            "VALUES (?, ?, ?)",
            (key, vector.tobytes(), _time.time()),
        )
        self._cache.commit()
