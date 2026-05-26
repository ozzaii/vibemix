# SPDX-License-Identifier: Apache-2.0
"""ingest — the DJ-library ingest orchestrator (Phase 89, the walking skeleton).

One vertical: ``detect → iter_tracks → CLAP embed → store``, resumable + honest.
A :class:`~vibemix.library.sources.base.LibrarySource` yields parsed tracks; each
track's local audio file is embedded ON-DEVICE via the staged ``ClapEngine``
(512-dim, keyless — no genai client, no API cost), and the vector is persisted
to the active :class:`LibraryStore`. After the run a ``library.pkl`` is written
so ``library search`` / ``similar`` resolve ingested titles.

Posture (mirrors :mod:`vibemix.library.folder_ingest`, the proven loop shape):

    * RESUMABLE — a content-hash cache hit re-stores the cached vector cheaply
      (counted ``skipped_cached``); a re-run does ~0 embeds. The cache key is
      ``sha256(file-bytes) || clap-backend-tag || INGEST_STRATEGY_VERSION`` in a
      DISTINCT ``~/.cache/vibemix/clap_embeddings.db`` (namespaced away from
      embed.py's Gemini-keyed embeddings.db).
    * HONEST partial failure — a missing/unreadable file or an embed raise is
      LOGGED + counted ``failed`` and the loop CONTINUES. A failed file NEVER
      produces a faked vector (Invariant #3 — trust the audio).
    * DIM posture (CONTEXT-locked) — store whatever clap_engine returns (512).
      We do NOT flip the global EMBEDDING_DIM. On an empty store pinned at a
      different dim → ``recreate_table`` (clean wipe). On a NON-empty store at a
      mismatched dim → fail-loud RuntimeError naming the CLAP-wiring session as
      the owner of the dim reconciliation; we never silently mix dims.

CLAP's heavy deps (torch/laion_clap) stay lazy — this module imports only
numpy + stdlib + the numpy-free source/store seams at top level.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Callable, Iterable, Protocol

import numpy as np

from vibemix.library.folder_ingest import IngestReport, _write_library_cache
from vibemix.library.rekordbox import TrackEntry

logger = logging.getLogger(__name__)

# Bump this when the embed pipeline changes shape (whole-track → cue-anchored in
# Plan 03) so cached vectors invalidate cleanly. Part of the content-hash key.
INGEST_STRATEGY_VERSION = "v1-clap-wholetrack"

# The CLAP content-hash cache. DISTINCT from embed.py's Gemini-keyed
# ~/.cache/vibemix/embeddings.db — a CLAP 512-d vector must never collide with a
# Gemini 1536-d row keyed by the same file.
CLAP_EMBED_CACHE_DB_PATH = Path.home() / ".cache" / "vibemix" / "clap_embeddings.db"

# Read the file in chunks so a multi-hundred-MB lossless file never loads whole.
_HASH_CHUNK_BYTES = 64 * 1024


class _Embedder(Protocol):  # pragma: no cover - structural typing only
    def embed_audio_file(self, path: str) -> np.ndarray: ...


class _Store(Protocol):  # pragma: no cover - structural typing only
    def add_batch(self, items: list[tuple[str, np.ndarray]]) -> None: ...


class _Source(Protocol):  # pragma: no cover - structural typing only
    name: str

    def detect(self) -> bool: ...

    def iter_tracks(self) -> Iterable[TrackEntry]: ...


# --------------------------------------------------------------------------- #
# Local-path resolution                                                        #
# --------------------------------------------------------------------------- #


def _resolve_local_path(filepath: str) -> Path | None:
    """Resolve a TrackEntry ``filepath`` to an existing local file, or None.

    Rekordbox stores ``Location`` as a ``file://localhost/abs/path`` URL. In
    practice the path reaches us in one of two shapes, both handled here:

      1. The raw URL still carries ``file://[localhost]`` (defensive — some
         exports / our own fixtures). We strip the scheme + optional authority,
         leaving the leading ``/``.
      2. pyrekordbox 0.4.4 has ALREADY stripped ``file://localhost/`` for us —
         INCLUDING the leading slash — so a macOS absolute path arrives as a
         host-relative ``private/var/...`` (no leading ``/``). We restore the
         leading slash when the as-is path does not exist but a root-anchored
         one does. (On Windows a ``C:\\...`` path is already absolute and skips
         this branch.)

    Honest skip: returns None when no candidate resolves to a real file — a
    missing file is counted ``failed``, never embedded as a faked vector.
    """
    raw = (filepath or "").strip()
    if not raw:
        return None
    if raw.startswith("file://"):
        rest = raw[len("file://") :]
        # Drop an optional "localhost" authority, leaving the leading slash.
        if rest.startswith("localhost"):
            rest = rest[len("localhost") :]
        raw = urllib.parse.unquote(rest)

    candidates = [raw]
    # pyrekordbox-stripped host-relative form: a POSIX absolute path that lost
    # its leading slash. Only add the slash-restored candidate when the path is
    # not already root-anchored and not a Windows drive path.
    if not raw.startswith("/") and not (len(raw) >= 2 and raw[1] == ":"):
        candidates.append("/" + raw)

    for cand in candidates:
        p = Path(cand)
        try:
            if p.is_file():
                return p
        except OSError:  # pragma: no cover - odd FS
            continue
    return None


# --------------------------------------------------------------------------- #
# Content-hash cache (CLAP-namespaced)                                          #
# --------------------------------------------------------------------------- #


def _open_clap_cache() -> sqlite3.Connection:
    """Open the default CLAP content-hash cache with schema init."""
    CLAP_EMBED_CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CLAP_EMBED_CACHE_DB_PATH))
    _init_clap_cache_schema(conn)
    return conn


def _init_clap_cache_schema(conn: sqlite3.Connection) -> None:
    """Idempotent: create the clap_embed_cache table if absent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS clap_embed_cache (
            key TEXT PRIMARY KEY,
            vector BLOB NOT NULL,
            dim INTEGER NOT NULL,
            ts REAL NOT NULL
        )
        """
    )
    conn.commit()


def _content_hash_key(path: Path, backend_tag: str) -> str:
    """sha256(file-bytes) || backend || strategy → the cache key.

    Streams the file in 64KB chunks so a huge lossless file never loads whole.
    """
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_HASH_CHUNK_BYTES), b""):
            h.update(chunk)
    h.update(b"||")
    h.update(backend_tag.encode("utf-8"))
    h.update(b"||")
    h.update(INGEST_STRATEGY_VERSION.encode("utf-8"))
    return h.hexdigest()


def _cache_get(conn: sqlite3.Connection, key: str) -> np.ndarray | None:
    row = conn.execute(
        "SELECT vector, dim FROM clap_embed_cache WHERE key = ?", (key,)
    ).fetchone()
    if row is None:
        return None
    blob, dim = row
    vec = np.frombuffer(blob, dtype=np.float32)
    if vec.shape[0] != dim:  # corrupt row — treat as miss
        return None
    return vec.copy()


def _cache_put(conn: sqlite3.Connection, key: str, vec: np.ndarray) -> None:
    import time as _time

    conn.execute(
        "INSERT OR REPLACE INTO clap_embed_cache (key, vector, dim, ts) "
        "VALUES (?, ?, ?, ?)",
        (key, vec.astype(np.float32).tobytes(), int(vec.shape[0]), _time.time()),
    )
    conn.commit()


# --------------------------------------------------------------------------- #
# Dim reconciliation                                                           #
# --------------------------------------------------------------------------- #


def _reconcile_store_dim(store: _Store, embedded_dim: int) -> None:
    """Honor the CONTEXT-locked dim posture before storing the first vector.

    * store.vector_dim() is None (unknown / empty numpy backend) → no-op.
    * vector_dim() == embedded_dim → no-op.
    * vector_dim() != embedded_dim AND row_count() == 0 → recreate_table()
      (clean wipe; the stale-but-empty schema carries no real data).
    * vector_dim() != embedded_dim AND row_count() > 0 → fail-loud RuntimeError;
      the dim flip is the CLAP-wiring session's lane, NOT this ingest slice's.
    """
    dim_fn = getattr(store, "vector_dim", None)
    if not callable(dim_fn):
        return
    stored_dim = dim_fn()
    if stored_dim is None or stored_dim == embedded_dim:
        return

    count_fn = getattr(store, "row_count", None)
    count = count_fn() if callable(count_fn) else None
    recreate_fn = getattr(store, "recreate_table", None)
    if count == 0 and callable(recreate_fn):
        logger.warning(
            "[ingest] store pinned at dim %s != embedded dim %s but is empty — "
            "recreating the table (clean wipe, no data lost).",
            stored_dim,
            embedded_dim,
        )
        recreate_fn()
        return

    raise RuntimeError(
        f"Library store holds {count} vectors at dim {stored_dim}, but CLAP "
        f"ingest produces dim {embedded_dim}. Refusing to mix dims silently. "
        f"Reconciling the embedding dimensionality (e.g. flipping EMBEDDING_DIM "
        f"1536 → {embedded_dim}) is the CLAP-wiring session's responsibility — "
        f"that session must migrate or wipe the store before CLAP ingest runs."
    )


# --------------------------------------------------------------------------- #
# The orchestrator                                                             #
# --------------------------------------------------------------------------- #


def ingest_source(
    source: _Source,
    embedder: _Embedder,
    store: _Store,
    *,
    persist_library: bool = True,
    progress: Callable[[str], None] | None = None,
    cache: sqlite3.Connection | None = None,
) -> IngestReport:
    """Detect → iter → CLAP embed → store one source, resumably + honestly.

    Args:
        source: a :class:`LibrarySource` (Rekordbox today). Its ``iter_tracks``
            drives the loop; ``detect`` is the CLI's gate (already passed here).
        embedder: anything exposing ``embed_audio_file(path) -> np.ndarray``
            (``ClapEngine`` in production; a fake in tests).
        store: a :class:`LibraryStore` (or any ``add_batch`` object).
        persist_library: when True (default) write ``library.pkl`` of handled
            tracks so search/similar resolve titles.
        progress: optional per-track human-line callback.
        cache: an injectable content-hash cache connection. Defaults to a NEW
            ``~/.cache/vibemix/clap_embeddings.db`` (distinct from the Gemini
            cache). Caller owns the lifecycle when they pass one in.

    Returns:
        :class:`~vibemix.library.folder_ingest.IngestReport` (same shape).
    """
    owns_cache = cache is None
    if cache is None:
        cache = _open_clap_cache()
    else:
        _init_clap_cache_schema(cache)

    backend_tag = str(getattr(embedder, "backend", "clap"))

    report = IngestReport(embed_strategy=INGEST_STRATEGY_VERSION)
    handled: dict[str, TrackEntry] = {}
    dim_reconciled = False

    try:
        for idx, track in enumerate(source.iter_tracks(), start=1):
            report.total += 1
            label = track.title or track.track_id

            local = _resolve_local_path(track.filepath)
            if local is None:
                logger.error(
                    "[ingest err] %s: local audio file missing (%s)",
                    track.track_id,
                    track.filepath,
                )
                report.failed += 1
                report.failures.append((track.filepath, "local audio file missing"))
                _emit(progress, idx, "err", label)
                continue

            # Resumable: content-hash cache probe.
            try:
                key = _content_hash_key(local, backend_tag)
            except OSError as e:
                logger.error("[ingest err] %s: cannot read file (%s)", local, e)
                report.failed += 1
                report.failures.append((str(local), f"unreadable: {e}"))
                _emit(progress, idx, "err", label)
                continue

            cached = _cache_get(cache, key)
            if cached is not None:
                if not dim_reconciled:
                    _reconcile_store_dim(store, int(cached.shape[0]))
                    dim_reconciled = True
                store.add_batch([(track.track_id, cached.astype(np.float32))])
                handled[track.track_id] = track
                report.skipped_cached += 1
                _emit(progress, idx, "skip", label)
                continue

            # Cache miss → embed. Broad-except so one bad file never aborts.
            try:
                vec = embedder.embed_audio_file(str(local))
            except Exception as e:  # noqa: BLE001 — one bad file must not abort
                logger.error("[ingest err] %s: %s", local, e)
                report.failed += 1
                report.failures.append((str(local), str(e)))
                _emit(progress, idx, "err", label)
                continue

            vec = np.asarray(vec, dtype=np.float32)
            if not dim_reconciled:
                _reconcile_store_dim(store, int(vec.shape[0]))
                dim_reconciled = True

            # Honest store: only a real vector lands. Cache AFTER a clean embed.
            _cache_put(cache, key, vec)
            store.add_batch([(track.track_id, vec)])
            handled[track.track_id] = track
            report.embedded += 1
            _emit(progress, idx, "ok", label)
    finally:
        if owns_cache:
            try:
                cache.close()
            except Exception:  # pragma: no cover - defensive
                pass

    if persist_library and handled:
        # Mirror folder_ingest: write a library.pkl so search/similar resolve
        # titles. Use the source's resolved collection path as the cache marker
        # when available, else a stable per-source marker.
        marker = getattr(source, "resolved_path", None) or f"source:{source.name}"
        try:
            _write_library_cache(handled, Path(marker))
        except OSError as e:  # cache is a perf affordance, not correctness
            logger.warning("library.pkl cache write failed: %s", e)

    return report


def _emit(
    progress: Callable[[str], None] | None,
    n: int,
    tag: str,
    label: str,
) -> None:
    if progress is None:
        return
    try:
        progress(f"[{n}] {tag} {label}")
    except Exception:  # pragma: no cover - defensive
        pass


__all__ = [
    "INGEST_STRATEGY_VERSION",
    "CLAP_EMBED_CACHE_DB_PATH",
    "ingest_source",
]
