# SPDX-License-Identifier: Apache-2.0
"""ingest — the DJ-library ingest orchestrator (Phase 89, the walking skeleton).

One vertical: ``detect → iter_tracks → CLAP embed → store``, resumable + honest.
A :class:`~vibemix.library.sources.base.LibrarySource` yields parsed tracks; each
track's local audio file is embedded ON-DEVICE via the product ``ClapEmbedder`` /
``ClapEngine(backend="onnx")`` seam (512-dim, keyless — no genai client, no API
cost), and the vector is persisted to the active :class:`LibraryStore`. After
the run a ``library.pkl`` is written so ``library search`` / ``similar`` resolve
ingested titles.

Posture (mirrors :mod:`vibemix.library.folder_ingest`, the proven loop shape):

    * CUE-ANCHORED (Plan 03) — instead of embedding the whole file, each track
      is embedded over its cue-anchored ≤80s mixable windows (DJ cues first,
      caller-injected Rekordbox ANLZ structure second, the offline
      ``detect_cues_auto`` engine as fallback), mean-pooled to one vector. A
      track with no structure at all degrades to a whole-track embed — never
      anchor-less, never a faked vector.
    * RESUMABLE — a content-hash cache hit re-stores the cached vector cheaply
      (counted ``skipped_cached``); a re-run does ~0 embeds. The cache key is
      ``sha256(file-bytes) || clap-backend-tag || INGEST_CUE_STRATEGY_VERSION``
      in a DISTINCT ``~/.cache/vibemix/clap_embeddings.db`` (namespaced away from
      legacy Gemini cache rows AND from the whole-track strategy).
    * HONEST partial failure — a missing/unreadable file or an embed raise is
      LOGGED + counted ``failed`` and the loop CONTINUES. A failed file NEVER
      produces a faked vector (Invariant #3 — trust the audio).
    * DIM posture — store whatever ClapEmbedder returns (512), matching the
      global ``EMBEDDING_DIM``. On an empty store pinned at a different dim →
      ``recreate_table`` (clean wipe). On a NON-empty store at a mismatched dim
      → fail-loud RuntimeError; we never silently mix dims.

CLAP's ONNX deps stay lazy through ``ClapEngine``; the optional torch/laion_clap
reference backend also remains lazy. This module imports only numpy + stdlib +
the source/store seams at top level.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import subprocess
import tempfile
import urllib.parse
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Protocol

import numpy as np

from vibemix.library.cache_paths import CLAP_EMBED_CACHE_DB_PATH
from vibemix.library.excerpt import anchors_for_track, cut_windows
from vibemix.library.folder_ingest import IngestReport, _write_library_cache
from vibemix.library.rekordbox import TrackEntry
from vibemix.library.section_builder import sections_for_entry
from vibemix.library.section_vectors import (
    SECTION_VECTOR_CACHE_VERSION,
    init_section_vector_schema,
    open_default_section_vector_db,
    put_section_vector,
    section_vector_cached,
)

logger = logging.getLogger(__name__)

# The whole-track strategy tag (Plan 01). Retained as the FALLBACK strategy and
# kept distinct from the cue-anchored tag below so the two never cache-collide.
INGEST_STRATEGY_VERSION = "v1-clap-wholetrack"

# Plan 03 — the cue-anchored strategy tag. A cue-anchored mean-pooled vector for
# a file must NEVER collide with that file's whole-track vector in the
# content-hash cache, so this distinct version is folded into the cache key
# (T-89-10). v2 is ANLZ-aware: when a caller supplies a matching ANLZ meta we
# also fold a private-path-safe ANLZ fingerprint into that track's cache key.
# "cueanchored" in the tag is asserted by the test.
INGEST_CUE_STRATEGY_VERSION = "v2-clap-cueanchored-anlz"

# ffmpeg window-slice budget (mirrors embed.py's FFMPEG_TIMEOUT_SECONDS posture).
_FFMPEG_TIMEOUT_SECONDS = 60.0

# Read the file in chunks so a multi-hundred-MB lossless file never loads whole.
_HASH_CHUNK_BYTES = 64 * 1024


class _Embedder(Protocol):  # pragma: no cover - structural typing only
    # Window path (cue-anchored): embed an ffmpeg-sliced ≤80s clip.
    def embed_audio_bytes(self, data: bytes, mime: str) -> np.ndarray: ...

    # Whole-track fallback: embed the file when there are no usable windows.
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


def _content_hash_key(
    path: Path,
    backend_tag: str,
    *,
    strategy_tag: str = INGEST_CUE_STRATEGY_VERSION,
) -> str:
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
    # Cue-anchored strategy tag — namespaces the key so a cue-anchored vector
    # never collides with Plan 01's whole-track vector for the same file (T-89-10).
    h.update(strategy_tag.encode("utf-8"))
    return h.hexdigest()


def _match_anlz_for_cache(track: TrackEntry, anlz_index: object | None) -> object | None:
    """Best-effort ANLZ match used only to namespace the embed cache.

    `excerpt.py` performs the authoritative cue-source priority again during
    embedding. This preflight is deliberately light: no ANLZ index means the old
    non-ANLZ key; a unique match means a separate ANLZ-keyed vector so a previous
    whole-track/auto fallback can never mask newly available Rekordbox structure.
    """
    if anlz_index is None:
        return None
    try:
        from vibemix.library.anlz_ingest import match_track_to_anlz

        return match_track_to_anlz(track, anlz_index)
    except Exception as e:
        logger.warning(
            "[ingest] ANLZ cache match failed for %s (%s); using non-ANLZ cache key.",
            track.track_id,
            e,
        )
        return None


def _cue_strategy_tag_for_anlz(meta: object | None) -> str:
    if meta is None:
        return INGEST_CUE_STRATEGY_VERSION
    return f"{INGEST_CUE_STRATEGY_VERSION}:meta:{_anlz_meta_fingerprint(meta)}"


def _anlz_meta_fingerprint(meta: object) -> str:
    """Hash ANLZ structure into the cache key without storing local paths."""
    h = hashlib.sha256()
    for attr in ("ext_path", "dat_path", "ppth_path", "basename_key"):
        value = str(getattr(meta, attr, ""))
        h.update(value.encode("utf-8", "surrogatepass"))
        h.update(b"\0")
        if attr.endswith("_path"):
            h.update(_path_stat_token(value).encode("utf-8"))
            h.update(b"\0")

    for phrase in tuple(getattr(meta, "phrases", ())):
        fields = (
            getattr(phrase, "mood", ""),
            getattr(phrase, "kind", ""),
            getattr(phrase, "cue_label", ""),
            getattr(phrase, "start_beat", ""),
            getattr(phrase, "end_beat", ""),
            getattr(phrase, "start_s", ""),
            getattr(phrase, "end_s", ""),
            getattr(phrase, "confidence", ""),
        )
        h.update("|".join(str(field) for field in fields).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:16]


def _path_stat_token(path: str) -> str:
    try:
        stat = Path(path).stat()
    except OSError:
        return ""
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def _cache_get(conn: sqlite3.Connection, key: str) -> np.ndarray | None:
    row = conn.execute("SELECT vector, dim FROM clap_embed_cache WHERE key = ?", (key,)).fetchone()
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
        "INSERT OR REPLACE INTO clap_embed_cache (key, vector, dim, ts) VALUES (?, ?, ?, ?)",
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
        f"Migrate or wipe the stale store before CLAP ingest runs."
    )


# --------------------------------------------------------------------------- #
# Cue-anchored window embedding                                                #
# --------------------------------------------------------------------------- #


def _default_slicer(path: str, start_s: float, length_s: float) -> bytes:
    """ffmpeg-slice a single mp3 window ``[start_s, start_s+length_s)``.

    Mirrors :meth:`embed.LibraryEmbedder._slice_window` (libmp3lame, 128k,
    tempfile, cleaned up). Injectable so tests stub it — NO real ffmpeg runs in
    the offline suite. ffmpeg is resolved lazily here so importing this module
    never shells out.
    """
    import shutil

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg not found on PATH")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        cmd = [
            ffmpeg,
            "-y",
            "-loglevel",
            "error",
            "-ss",
            f"{start_s:.3f}",
            "-i",
            str(path),
            "-t",
            f"{length_s:.3f}",
            "-acodec",
            "libmp3lame",
            "-b:a",
            "128k",
            str(tmp_path),
        ]
        subprocess.run(cmd, check=True, timeout=_FFMPEG_TIMEOUT_SECONDS, capture_output=True)
        return tmp_path.read_bytes()
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass


def _embed_track_cue_anchored(
    track: TrackEntry,
    local: Path,
    embedder: _Embedder,
    *,
    anlz_index: object | None = None,
    slicer: Callable[[str, float, float], bytes] | None = None,
) -> np.ndarray:
    """Embed a track over its cue-anchored ≤80s windows, mean-pooled.

    Pipeline (mirrors :meth:`embed.LibraryEmbedder._embed_audio_cue_anchored`):
        1. ``anchors_for_track`` — DJ-first, caller-injected ANLZ second, auto
           fallback (``[]`` honestly when no structure).
        2. ``cut_windows`` — clamp each anchor to a 1..80s window.
        3. Per window: ``slicer`` → ``embedder.embed_audio_bytes`` (per-window
           try/except → skip; one bad window must not abort — T-89-11).
        4. ``np.mean`` the per-window vectors → ``l2_normalize`` → one vector.

    Falls back to ``embedder.embed_audio_file`` (whole-track) when there are no
    usable windows OR every window embed fails — NEVER a faked vector (the
    fallback re-embeds the real file). Any exception in the whole-track fallback
    propagates to the caller's honest-failure handler.
    """
    from vibemix.library._cosine import l2_normalize

    # Resolve the slicer at call time (not as a default arg) so a test that
    # monkeypatches the module-level ``_default_slicer`` is honored.
    if slicer is None:
        slicer = _default_slicer

    # anchors_for_track may run detect_cues_auto (CUE-DETR ONNX if installed,
    # heuristic fallback otherwise). A detection failure must degrade to whole-track
    # embed, NOT abort the track (T-89-09: never anchor-less). Mirror embed.py's
    # _embed_audio_cue_anchored fallback posture.
    try:
        anchors = anchors_for_track(track, anlz_index=anlz_index)
    except Exception as e:
        logger.warning(
            "[ingest] cue anchoring failed for %s (%s); falling back to whole-track embed.",
            local,
            e,
        )
        anchors = []
    windows = cut_windows(anchors, float(track.duration_s or 0.0))

    vecs: list[np.ndarray] = []
    for start_s, end_s in windows:
        length_s = end_s - start_s
        try:
            clip = slicer(str(local), start_s, length_s)
            vec = embedder.embed_audio_bytes(clip, "audio/mpeg")
        except Exception as e:
            logger.warning(
                "[ingest] cue-window embed failed at %.1fs for %s (%s); skipping this window.",
                start_s,
                local,
                e,
            )
            continue
        vecs.append(np.asarray(vec, dtype=np.float32))

    if not vecs:
        # No usable windows OR every window failed → whole-track fallback. A
        # real re-embed of the file, never a faked/zero vector (Invariant #3).
        return np.asarray(embedder.embed_audio_file(str(local)), dtype=np.float32)

    mean = np.mean(np.stack(vecs), axis=0).astype(np.float32)
    return l2_normalize(mean)


def _ensure_section_vectors_for_track(
    track: TrackEntry,
    local: Path,
    embedder: _Embedder,
    cache: sqlite3.Connection,
    *,
    track_cache_key: str,
    backend_tag: str,
    slicer: Callable[[str, float, float], bytes] | None = None,
) -> int:
    """Populate per-section CLAP vectors for transition scoring.

    This is additive to the track vector: failures are logged and skipped so a
    bad section window never invalidates a successfully ingested track.
    """
    from vibemix.library._cosine import l2_normalize

    if slicer is None:
        slicer = _default_slicer

    written = 0
    for section in sections_for_entry(track):
        start_s = max(0.0, float(section.start_s))
        end_s = float(section.end_s)
        if track.duration_s and track.duration_s > 0:
            end_s = min(end_s, float(track.duration_s))
        end_s = min(max(end_s, start_s), start_s + 80.0)
        length_s = end_s - start_s
        if length_s < 1.0:
            continue

        source_hash = _section_source_hash(track_cache_key, section.section_id, start_s, end_s)
        if section_vector_cached(cache, section.section_id, source_hash=source_hash):
            continue

        try:
            clip = slicer(str(local), start_s, length_s)
            vector = l2_normalize(np.asarray(embedder.embed_audio_bytes(clip, "audio/mpeg")))
            put_section_vector(
                cache,
                section_id=section.section_id,
                source_hash=source_hash,
                vector=vector.astype(np.float32),
                model_tag=backend_tag,
                strategy_tag=SECTION_VECTOR_CACHE_VERSION,
                start_s=start_s,
                end_s=end_s,
            )
            written += 1
        except Exception as e:
            logger.warning(
                "[ingest] section-vector embed failed for %s (%s); skipping section.",
                section.section_id,
                e,
            )
    return written


def _section_source_hash(
    track_cache_key: str, section_id: str, start_s: float, end_s: float
) -> str:
    h = hashlib.sha256()
    h.update(track_cache_key.encode("utf-8"))
    h.update(b"||")
    h.update(section_id.encode("utf-8"))
    h.update(b"||")
    h.update(f"{start_s:.3f}:{end_s:.3f}".encode())
    return h.hexdigest()


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
    section_cache: sqlite3.Connection | None = None,
    anlz_index: object | None = None,
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
        anlz_index: optional caller-built ``AnlzIndex``. When supplied, ingest
            uses Rekordbox ANLZ phrases after DJ cues and before auto-cues, and
            matched ANLZ metadata is folded into the per-track cache key.

    Returns:
        :class:`~vibemix.library.folder_ingest.IngestReport` (same shape).
    """
    owns_cache = cache is None
    if cache is None:
        cache = _open_clap_cache()
    else:
        _init_clap_cache_schema(cache)
    owns_section_cache = section_cache is None
    if section_cache is None:
        section_cache = open_default_section_vector_db(create=True)
        assert section_cache is not None
    else:
        init_section_vector_schema(section_cache)

    backend_tag = str(getattr(embedder, "backend", "clap"))

    report = IngestReport(embed_strategy=INGEST_CUE_STRATEGY_VERSION)
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
                anlz_meta = _match_anlz_for_cache(track, anlz_index)
                strategy_tag = _cue_strategy_tag_for_anlz(anlz_meta)
                key = _content_hash_key(local, backend_tag, strategy_tag=strategy_tag)
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
                _ensure_section_vectors_for_track(
                    track,
                    local,
                    embedder,
                    section_cache,
                    track_cache_key=key,
                    backend_tag=backend_tag,
                )
                handled[track.track_id] = track
                report.skipped_cached += 1
                _emit(progress, idx, "skip", label)
                continue

            # Cache miss → embed the cue-anchored windows (mean-pooled), with a
            # whole-track fallback baked into the helper. Broad-except so one bad
            # file never aborts the run.
            try:
                vec = _embed_track_cue_anchored(
                    track,
                    local,
                    embedder,
                    anlz_index=anlz_index,
                )
            except Exception as e:
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
            _ensure_section_vectors_for_track(
                track,
                local,
                embedder,
                section_cache,
                track_cache_key=key,
                backend_tag=backend_tag,
            )
            handled[track.track_id] = track
            report.embedded += 1
            _emit(progress, idx, "ok", label)
    finally:
        if owns_cache:
            try:
                cache.close()
            except Exception:  # pragma: no cover - defensive
                pass
        if owns_section_cache and section_cache is not None:
            try:
                section_cache.close()
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
    "CLAP_EMBED_CACHE_DB_PATH",
    "INGEST_CUE_STRATEGY_VERSION",
    "INGEST_STRATEGY_VERSION",
    "_ensure_section_vectors_for_track",
    "ingest_source",
]
