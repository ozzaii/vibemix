# SPDX-License-Identifier: Apache-2.0
"""Optional section-vector lookup for transition scoring.

This module is deliberately small and duck-typed. The real section embedding
store can land behind any of these methods without changing the live pill or
agent tool contracts:

* ``section_vector_for_id(section_id)``
* ``section_vector(section_id)``
* ``load_section_vectors([section_id, ...])``
* a ``section_vectors`` / ``_section_vectors`` mapping

When no section vector exists, callers can pass a whole-track fallback vector.
The returned ``basis`` makes that fallback explicit, so downstream payloads do
not accidentally claim section-level audio evidence.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

import numpy as np

from vibemix.library.cache_paths import SECTION_VECTOR_CACHE_DB_PATH

SectionVectorBasis = Literal["section_vector", "track_vector_fallback", "semantic_unknown"]

# v2: the window slicer moved from an ffmpeg-binary 128k mp3 re-encode to a
# direct PyAV float decode. The slice BYTES change, so persisted v1 vectors
# must never mix with v2 ones — the bump retires them cleanly.
SECTION_VECTOR_CACHE_VERSION = "v2-clap-section-window-pyav"
SECTION_VECTOR_WINDOW_MAX_SECONDS = 80.0
SECTION_VECTOR_MIN_SECONDS = 1.0

logger = logging.getLogger(__name__)


class SectionVectorEmbedder(Protocol):  # pragma: no cover - protocol
    backend: str

    def embed_audio_bytes(self, data: bytes, mime: str) -> np.ndarray: ...


@dataclass(frozen=True, slots=True)
class SectionVectorResult:
    vector: np.ndarray | None
    basis: SectionVectorBasis


def open_default_section_vector_db(*, create: bool = True) -> sqlite3.Connection | None:
    """Open the default section-vector DB, optionally without creating it."""
    path = SECTION_VECTOR_CACHE_DB_PATH
    if not create and not path.exists():
        return None
    return open_section_vector_db(path, create=create)


def open_section_vector_db(path: str | Path, *, create: bool = True) -> sqlite3.Connection:
    """Open a section-vector SQLite cache and initialize the schema."""
    db_path = Path(path).expanduser()
    if create:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    init_section_vector_schema(conn)
    return conn


def init_section_vector_schema(conn: sqlite3.Connection) -> None:
    """Create the section-vector table if absent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS section_vector_cache (
            section_id TEXT PRIMARY KEY,
            source_hash TEXT NOT NULL,
            vector BLOB NOT NULL,
            dim INTEGER NOT NULL,
            model_tag TEXT NOT NULL,
            strategy_tag TEXT NOT NULL,
            start_s REAL NOT NULL,
            end_s REAL NOT NULL,
            ts REAL NOT NULL
        )
        """
    )
    conn.commit()


def get_cached_section_vector(conn: sqlite3.Connection, section_id: str) -> np.ndarray | None:
    """Read a section vector by id, returning ``None`` on miss/corruption."""
    row = conn.execute(
        "SELECT vector, dim FROM section_vector_cache WHERE section_id = ?",
        (section_id,),
    ).fetchone()
    if row is None:
        return None
    blob, dim = row
    vector = np.frombuffer(blob, dtype=np.float32)
    if vector.ndim != 1 or vector.shape[0] != int(dim):
        return None
    return vector.copy()


def section_vector_cached(
    conn: sqlite3.Connection,
    section_id: str,
    *,
    source_hash: str | None = None,
) -> bool:
    """Return whether a usable row exists, optionally matching source hash."""
    if source_hash is None:
        row = conn.execute(
            "SELECT dim, length(vector) FROM section_vector_cache WHERE section_id = ?",
            (section_id,),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT dim, length(vector)
            FROM section_vector_cache
            WHERE section_id = ? AND source_hash = ?
            """,
            (section_id, source_hash),
        ).fetchone()
    if row is None:
        return False
    dim, byte_len = row
    return int(dim) > 0 and int(byte_len) == int(dim) * 4


def put_section_vector(
    conn: sqlite3.Connection,
    *,
    section_id: str,
    source_hash: str,
    vector: np.ndarray,
    model_tag: str,
    strategy_tag: str = SECTION_VECTOR_CACHE_VERSION,
    start_s: float,
    end_s: float,
) -> None:
    """Persist one grounded section vector."""
    vec = np.asarray(vector, dtype=np.float32)
    if vec.ndim != 1 or vec.size == 0:
        raise ValueError("section vector must be a non-empty 1-D float32 array")
    conn.execute(
        """
        INSERT OR REPLACE INTO section_vector_cache (
            section_id, source_hash, vector, dim, model_tag, strategy_tag, start_s, end_s, ts
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            section_id,
            source_hash,
            vec.tobytes(),
            int(vec.shape[0]),
            model_tag,
            strategy_tag,
            float(start_s),
            float(end_s),
            time.time(),
        ),
    )
    conn.commit()


def section_window_for_record(section: Any, duration_s: float | None = None) -> tuple[float, float] | None:
    """Return the bounded audio window for one grounded section.

    Section vectors intentionally embed the section window itself, not a
    whole-track mean. Windows are clamped to ``<=80s`` so they mirror the
    existing cue-window budget and never ask CLAP to summarize a whole song.
    """
    start_s = max(0.0, float(getattr(section, "start_s", 0.0) or 0.0))
    end_s = float(getattr(section, "end_s", 0.0) or 0.0)
    if duration_s is not None and duration_s > 0:
        end_s = min(end_s, float(duration_s))
    end_s = min(max(end_s, start_s), start_s + SECTION_VECTOR_WINDOW_MAX_SECONDS)
    if end_s - start_s < SECTION_VECTOR_MIN_SECONDS:
        return None
    return start_s, end_s


def section_source_hash(
    track_cache_key: str, section_id: str, start_s: float, end_s: float
) -> str:
    """Stable section cache key from track content key + section bounds."""
    h = hashlib.sha256()
    h.update(track_cache_key.encode("utf-8"))
    h.update(b"||")
    h.update(section_id.encode("utf-8"))
    h.update(b"||")
    h.update(f"{start_s:.3f}:{end_s:.3f}".encode())
    return h.hexdigest()


def default_section_slicer(path: str, start_s: float, length_s: float) -> np.ndarray:
    """PyAV-slice ``[start_s, start_s + length_s)`` to mono float32 @ CLAP rate.

    The packaged app ships NO ffmpeg binary (and ``open -a`` strips PATH), so
    slicing rides the bundled PyAV decoder instead of a subprocess. Decoding
    straight to CLAP's native 48k also drops the old lossy 128k mp3 re-encode
    plus its tempfile round trip — the embedder consumes the array directly.
    """
    from vibemix.library.audio_decode import load_audio_mono
    from vibemix.library.clap_engine import CLAP_SR

    return load_audio_mono(
        path, target_sr=CLAP_SR, offset_s=start_s, duration_s=length_s
    )


def embed_window_clip(embedder: Any, clip: np.ndarray | bytes) -> np.ndarray:
    """Route one sliced window into the embedder without any subprocess.

    Array clips (the default PyAV slicer, mono float32 @ CLAP rate) take the
    in-memory ``embed_audio_array`` seam; byte clips (legacy/injected slicers)
    keep the ``embed_audio_bytes`` contract. An array clip against a
    bytes-only embedder degrades to a stdlib PCM16 WAV round trip so
    duck-typed embedders keep working.
    """
    if isinstance(clip, np.ndarray):
        from vibemix.library.clap_engine import CLAP_SR

        embed_array = getattr(embedder, "embed_audio_array", None)
        if callable(embed_array):
            return np.asarray(embed_array(clip, sr=CLAP_SR), dtype=np.float32)
        from vibemix.library.audio_decode import pcm16_wav_bytes

        return np.asarray(
            embedder.embed_audio_bytes(pcm16_wav_bytes(clip, sr=CLAP_SR), "audio/wav"),
            dtype=np.float32,
        )
    return np.asarray(embedder.embed_audio_bytes(clip, "audio/mpeg"), dtype=np.float32)


def persist_section_vectors_for_track(
    track: Any,
    local: Path,
    embedder: SectionVectorEmbedder,
    conn: sqlite3.Connection,
    *,
    track_cache_key: str,
    backend_tag: str | None = None,
    slicer: Callable[[str, float, float], np.ndarray | bytes] | None = None,
) -> int:
    """Populate per-section CLAP vectors for one local audio track.

    This is additive and honest: a bad section window is logged and skipped,
    while already-cached matching rows are left alone. The caller supplies a
    ``track_cache_key`` derived from the audio/strategy so section rows invalidate
    when the underlying audio embedding strategy changes.
    """
    from vibemix.library._cosine import l2_normalize
    from vibemix.library.section_builder import sections_for_entry

    if slicer is None:
        slicer = default_section_slicer
    model_tag = backend_tag or str(getattr(embedder, "backend", "clap"))

    written = 0
    duration_s = float(getattr(track, "duration_s", 0.0) or 0.0)
    for section in sections_for_entry(track):
        window = section_window_for_record(section, duration_s)
        if window is None:
            continue
        start_s, end_s = window
        source_hash = section_source_hash(
            track_cache_key,
            str(section.section_id),
            start_s,
            end_s,
        )
        if section_vector_cached(conn, section.section_id, source_hash=source_hash):
            continue

        try:
            clip = slicer(str(local), start_s, end_s - start_s)
            vector = l2_normalize(embed_window_clip(embedder, clip))
            put_section_vector(
                conn,
                section_id=section.section_id,
                source_hash=source_hash,
                vector=vector.astype(np.float32),
                model_tag=model_tag,
                strategy_tag=SECTION_VECTOR_CACHE_VERSION,
                start_s=start_s,
                end_s=end_s,
            )
            written += 1
        except Exception as e:
            logger.warning(
                "section-vector embed failed for %s (%s); skipping section.",
                section.section_id,
                e,
            )
    return written


def resolve_section_vector(
    provider: Any,
    section_id: str,
    *,
    fallback_vector: np.ndarray | None = None,
) -> SectionVectorResult:
    """Return a section vector when available, else an explicit fallback."""
    vector = _lookup_provider_vector(provider, section_id)
    if vector is not None:
        return SectionVectorResult(vector=vector, basis="section_vector")
    if fallback_vector is not None:
        return SectionVectorResult(
            vector=np.asarray(fallback_vector, dtype=np.float32).copy(),
            basis="track_vector_fallback",
        )
    return SectionVectorResult(vector=None, basis="semantic_unknown")


def semantic_basis_for_pair(source_basis: str | None, destination_basis: str | None) -> str:
    """Collapse source/destination vector provenance into one public label."""
    bases = {source_basis or "semantic_unknown", destination_basis or "semantic_unknown"}
    if bases == {"section_vector"}:
        return "section_vector"
    if "semantic_unknown" in bases:
        return "semantic_unknown"
    if "section_vector" in bases and "track_vector_fallback" in bases:
        return "mixed_section_track"
    return "track_vector_fallback"


def _lookup_provider_vector(provider: Any, section_id: str) -> np.ndarray | None:
    for obj in _provider_objects(provider):
        vector = _lookup_method_vector(obj, section_id)
        if vector is not None:
            return vector
        vector = _lookup_mapping_vector(getattr(obj, "section_vectors", None), section_id)
        if vector is not None:
            return vector
        vector = _lookup_mapping_vector(getattr(obj, "_section_vectors", None), section_id)
        if vector is not None:
            return vector
    return None


def _provider_objects(provider: Any) -> tuple[Any, ...]:
    backend = getattr(provider, "_backend", None)
    if backend is None or backend is provider:
        return (provider,)
    return (provider, backend)


def _lookup_method_vector(obj: Any, section_id: str) -> np.ndarray | None:
    for name in ("section_vector_for_id", "section_vector", "get_section_vector"):
        method = getattr(obj, name, None)
        if callable(method):
            vector = _coerce_vector(_call_or_none(method, section_id))
            if vector is not None:
                return vector
    loader = getattr(obj, "load_section_vectors", None)
    if callable(loader):
        loaded = _call_or_none(loader, [section_id])
        vector = _lookup_mapping_vector(loaded, section_id)
        if vector is not None:
            return vector
        loaded = _call_or_none(loader)
        vector = _lookup_mapping_vector(loaded, section_id)
        if vector is not None:
            return vector
    return None


def _call_or_none(method: Any, *args: Any) -> Any:
    try:
        return method(*args)
    except TypeError:
        return None
    except Exception:
        return None


def _lookup_mapping_vector(raw: Any, section_id: str) -> np.ndarray | None:
    if not isinstance(raw, dict):
        return None
    for key in (section_id, f"vec8:{section_id}", f"vec512:{section_id}"):
        vector = _coerce_vector(raw.get(key))
        if vector is not None:
            return vector
    return None


def _coerce_vector(raw: Any) -> np.ndarray | None:
    if raw is None:
        return None
    try:
        vector = np.asarray(raw, dtype=np.float32)
    except (TypeError, ValueError):
        return None
    if vector.ndim != 1 or vector.size == 0:
        return None
    return vector.copy()


__all__ = [
    "SECTION_VECTOR_CACHE_VERSION",
    "SECTION_VECTOR_MIN_SECONDS",
    "SECTION_VECTOR_WINDOW_MAX_SECONDS",
    "SectionVectorBasis",
    "SectionVectorEmbedder",
    "SectionVectorResult",
    "default_section_slicer",
    "embed_window_clip",
    "get_cached_section_vector",
    "init_section_vector_schema",
    "open_default_section_vector_db",
    "open_section_vector_db",
    "persist_section_vectors_for_track",
    "put_section_vector",
    "resolve_section_vector",
    "section_source_hash",
    "section_vector_cached",
    "section_window_for_record",
    "semantic_basis_for_pair",
]
