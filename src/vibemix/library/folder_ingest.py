# SPDX-License-Identifier: Apache-2.0
"""folder_ingest — raw-folder audio ingest for the vibemix library.

quick-260525-gz2. Kaan's DJ library is a raw folder tree of audio files
    (mp3 / m4a / wav / flac / aac), NOT a Rekordbox ``collection.xml``. This
    module walks such a folder, derives a minimal :class:`TrackEntry` per file
    (filename stem as title, ffprobe duration), embeds each via the active
    product embedder, persists the 512-d CLAP vectors to the active
:class:`LibraryStore`, and writes a ``library.pkl`` cache compatible with
``RekordboxLibrary.try_load_cache()`` so the existing ``search`` / ``similar``
CLIs can resolve filenames for folder-ingested tracks.

Data flow::

    scan_folder(root)            # walk → sorted [Path, ...] of supported files
      └─ probe_duration_s(path)  # ffprobe → float | None (None == skip honestly)
              └─ folder_to_track_entry(path, dur) → TrackEntry (namespaced id)
                  └─ embedder.embed_track(entry) → 512-d L2-normalized vec
                  └─ store.add_batch([(id, vec)])
    # after loop: write RekordboxLibrary CACHE_PATH pickle (titles)

Design rules (honest + resilient):
    * UNPROBEABLE / EMBED-FAILED files are LOGGED + COUNTED FAILED and the
      loop CONTINUES — one bad file never aborts a 1500-file run, and a
      failed file NEVER produces a faked embedding (T-gz2-02 / T-gz2-05).
    * RESUMABLE — a content-hash cache hit (``has_cached_embedding``) is
      counted ``skipped_cached`` and re-stored cheaply; a re-run does ~0
      API calls (the embed cache absorbs it).
    * DIM-MISMATCH fail-loud — if the on-disk store holds vectors at a
      different dim than ``EMBEDDING_DIM`` (a stale 768 build), ingest
      raises before embedding anything (T-gz2-01).

The ffprobe call is injectable (``probe`` arg) so the unit tests need no
real binary and no real audio files.
"""

from __future__ import annotations

import hashlib
import logging
import os
import pickle
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Protocol

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM
from vibemix.library.key_estimator import estimate_key
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry, _CacheBlob
from vibemix.library.tempo_estimator import estimate_bpm

logger = logging.getLogger(__name__)

# Supported raw-audio suffixes. Lower-case; matched case-insensitively.
SUPPORTED_SUFFIXES: tuple[str, ...] = (".mp3", ".m4a", ".wav", ".flac", ".aac")

# ffprobe subprocess timeout — guard against a hung/malformed file.
FFPROBE_TIMEOUT_SECONDS = 20

ProbeFn = Callable[[Path], "float | None"]


class _Embedder(Protocol):  # pragma: no cover - structural typing only
    def embed_track(self, track: TrackEntry) -> np.ndarray: ...
    def has_cached_embedding(self, track: TrackEntry) -> bool: ...


class _Store(Protocol):  # pragma: no cover - structural typing only
    def add_batch(self, items: list[tuple[str, np.ndarray]]) -> None: ...
    def search(
        self, query_vector: np.ndarray, k: int = ...
    ) -> list[tuple[str, float]]: ...


@dataclass(slots=True)
class IngestReport:
    """Outcome of an :func:`ingest_folder` run.

    ``embedded`` + ``skipped_cached`` + ``failed`` == ``total`` for every
    file scan_folder yielded. ``failures`` carries ``(filepath, error)`` so
    the CLI can surface exactly which files were skipped and why.
    """

    total: int = 0
    embedded: int = 0
    skipped_cached: int = 0
    failed: int = 0
    cost_estimate_eur: float = 0.0
    failures: list[tuple[str, str]] = field(default_factory=list)
    # Which embed strategy this run used (Path 2). "mean_excerpt" (default) or
    # "cue_anchored". Surfaced so the CLI / caller can confirm the opt-in took.
    embed_strategy: str = "mean_excerpt"
    cue_agreement_tracks: int = 0
    cue_agreement_scored: int = 0
    cue_agreement_weak_labels: int = 0
    cue_agreement_score_sum: float = 0.0
    cue_agreement_offset_sum_s: float = 0.0
    cue_agreement_offset_count: int = 0
    key_estimated_tracks: int = 0
    key_estimation_failed: int = 0
    bpm_estimated_tracks: int = 0
    bpm_estimation_failed: int = 0

    def as_dict(self) -> dict:
        mean_score = (
            self.cue_agreement_score_sum / self.cue_agreement_scored
            if self.cue_agreement_scored
            else None
        )
        mean_offset_s = (
            self.cue_agreement_offset_sum_s / self.cue_agreement_offset_count
            if self.cue_agreement_offset_count
            else None
        )
        return {
            "total": self.total,
            "embedded": self.embedded,
            "skipped_cached": self.skipped_cached,
            "failed": self.failed,
            "embed_strategy": self.embed_strategy,
            "cue_agreement": {
                "tracks": self.cue_agreement_tracks,
                "scored": self.cue_agreement_scored,
                "weak_labels": self.cue_agreement_weak_labels,
                "mean_score": round(mean_score, 6) if mean_score is not None else None,
                "mean_abs_offset_s": (
                    round(mean_offset_s, 6) if mean_offset_s is not None else None
                ),
            },
            "key_estimation": {
                "estimated": self.key_estimated_tracks,
                "failed": self.key_estimation_failed,
            },
            "bpm_estimation": {
                "estimated": self.bpm_estimated_tracks,
                "failed": self.bpm_estimation_failed,
            },
            "cost_estimate_eur": round(self.cost_estimate_eur, 6),
            "failures": [
                {"filepath": fp, "error": err} for fp, err in self.failures
            ],
        }


def scan_folder(root: Path) -> list[Path]:
    """Recursively list supported audio files under ``root``.

    Deterministic sorted order (by resolved string path). Dotfiles and
    unsupported extensions are excluded; suffix match is case-insensitive.
    Returns ``[]`` if ``root`` is not a directory.
    """
    root = Path(root)
    if not root.is_dir():
        return []
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        if p.suffix.lower() in SUPPORTED_SUFFIXES:
            out.append(p)
    out.sort(key=lambda x: str(x))
    return out


def probe_duration_s(path: Path) -> float | None:
    """Return audio duration in seconds via ffprobe, or ``None`` on any failure.

    ffprobe ships with the already-pinned ffmpeg hard dep. A ``None`` return
    is the honest "we can't trust this file" signal — the caller skips it
    rather than embedding a guessed duration.
    """
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        logger.warning(
            "ffprobe not on PATH — cannot probe %s (install ffmpeg)", path
        )
        return None
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=FFPROBE_TIMEOUT_SECONDS,
        )
    except (subprocess.SubprocessError, OSError) as e:
        logger.warning("ffprobe failed for %s: %s", path, e)
        return None
    raw = (result.stdout or "").strip()
    if not raw:
        return None
    try:
        dur = float(raw)
    except ValueError:
        return None
    if dur <= 0 or dur != dur:  # non-positive or NaN
        return None
    return dur


def folder_to_track_entry(path: Path, duration_s: float) -> TrackEntry:
    """Build a minimal :class:`TrackEntry` from a raw audio file.

    ``track_id`` is a stable, namespaced hash of the absolute path
    (``folder:<sha1[:16]>``) so it never collides with Rekordbox numeric
    TrackIDs. ``title`` is the filename stem; artist/album/key are empty,
    bpm 0.0, cues empty — folder ingest has no metadata beyond the file.
    """
    abspath = str(Path(path).resolve())
    digest = hashlib.sha1(abspath.encode("utf-8")).hexdigest()[:16]
    return TrackEntry(
        track_id=f"folder:{digest}",
        title=Path(path).stem,
        artist="",
        album="",
        bpm=0.0,
        key="",
        duration_s=float(duration_s),
        cues=(),
        filepath=abspath,
    )


def _assert_store_dim_compatible(store: _Store) -> None:
    """Fail-loud if the store holds vectors at a different dim than EMBEDDING_DIM.

    Two-layer check:
      1. If the backend can introspect its declared vector dim
         (``vector_dim()`` — sqlite-vec reads the FLOAT[N] schema), compare
         it to EMBEDDING_DIM. This catches a STALE-BUT-EMPTY 768 vec0 table
         that the row-data cosine path below would miss (the table's
         ``CREATE ... IF NOT EXISTS`` keeps the old dim, so a 512-d insert
         fails deep in the extension with a cryptic error).
      2. Probe with a zero query of the current dim. An empty store no-ops
         (cosine_topk returns [] for N==0). A stale-dim store with rows
         raises an Assertion/Value/shape error inside cosine_topk.

    Either failure re-raises as an actionable RuntimeError.
    """
    _stale_dim_error = RuntimeError(
        f"Library store holds vectors at a different dimensionality than "
        f"EMBEDDING_DIM={EMBEDDING_DIM}. The on-disk index is stale "
        f"(likely a 768-dim build). Delete ~/.cache/vibemix/library.db "
        f"(and library_vectors.npy / library_ids.json for the numpy "
        f"backend) and re-run embed-folder."
    )

    dim_fn = getattr(store, "vector_dim", None)
    if callable(dim_fn):
        stored = dim_fn()
        if stored is not None and stored != EMBEDDING_DIM:
            # An EMPTY stale-dim table carries no real data — auto-recreate
            # it at the new dim (clean wipe, per gz2 research: the DB has 0
            # rows). A POPULATED stale-dim table would lose real embeddings,
            # so we NEVER auto-wipe it — fail loud and let the user decide.
            count_fn = getattr(store, "row_count", None)
            count = count_fn() if callable(count_fn) else None
            recreate_fn = getattr(store, "recreate_table", None)
            if count == 0 and callable(recreate_fn):
                logger.warning(
                    "[ingest] store table is empty but pinned at dim %s != "
                    "EMBEDDING_DIM=%s — recreating it (clean wipe, no data).",
                    stored,
                    EMBEDDING_DIM,
                )
                recreate_fn()
            else:
                raise _stale_dim_error

    try:
        store.search(np.zeros(EMBEDDING_DIM, dtype=np.float32), k=1)
    except (AssertionError, ValueError) as e:
        raise RuntimeError(
            f"Library store holds vectors at a different dimensionality than "
            f"EMBEDDING_DIM={EMBEDDING_DIM}. The on-disk index is stale "
            f"(likely a 768-dim build). Delete ~/.cache/vibemix/library.db "
            f"(and library_vectors.npy / library_ids.json for the numpy "
            f"backend) and re-run embed-folder. (probe error: {e})"
        ) from e


def _write_library_cache(entries: dict[str, TrackEntry], root: Path) -> Path:
    """Write a ``RekordboxLibrary.try_load_cache``-compatible pickle.

    Mirrors ``RekordboxLibrary._write_cache`` shape: a ``_CacheBlob`` with
    ``version=SCHEMA_VERSION``, ``xml_path`` = the resolved folder path,
    ``xml_mtime`` = the folder's mtime, and the track dict. Track IDs keep the
    ``folder:<sha1[:16]>`` namespace; the cache source path stays stat-able so
    ``try_load_cache`` can detect when the folder is newer than the cache.
    Returns the cache path written.
    """
    cache_path = RekordboxLibrary.CACHE_PATH
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    # try_load_cache stats this path's mtime and compares to xml_mtime; record
    # the live folder mtime so source-folder freshness remains observable.
    marker = str(Path(root).resolve())
    try:
        folder_mtime = os.path.getmtime(marker)
    except OSError:
        folder_mtime = time.time()
    blob = _CacheBlob(
        version=RekordboxLibrary.SCHEMA_VERSION,
        xml_path=marker,
        xml_mtime=folder_mtime,
        tracks=dict(entries),
    )
    tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    with open(tmp_path, "wb") as fh:
        pickle.dump(blob, fh, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp_path, cache_path)
    return cache_path


def ingest_folder(
    root: Path,
    embedder: _Embedder,
    store: _Store,
    *,
    persist_library: bool = True,
    progress: Callable[[str], None] | None = None,
    probe: ProbeFn = probe_duration_s,
    embed_strategy: str | None = None,
    compute_band_shares: bool = False,
    compute_key: bool = True,
    compute_bpm: bool = True,
) -> IngestReport:
    """Walk ``root``, embed each supported audio file, persist to ``store``.

    Resumable + partial-failure-tolerant + honest (see module docstring).

    Args:
        root: folder to ingest (recursive).
        embedder: anything with ``embed_track`` + ``has_cached_embedding``.
        store: anything with ``add_batch`` + ``search``.
        persist_library: when True (default), write a
            ``RekordboxLibrary.CACHE_PATH`` pickle of all successfully
            handled tracks so search/similar resolve titles.
        progress: optional callback receiving a per-track human line.
        probe: duration probe (injectable for tests).
        embed_strategy: informational label for the report (Path 2). The
            actual strategy is decided at product embedder construction; if
            ``None`` we read it off the embedder's ``_embed_strategy`` attribute
            when present, else default "mean_excerpt". This NEVER changes
            embedding behavior — it's a report annotation so the caller can
            confirm the opt-in took.
        compute_band_shares: when True, also compute per-track band-share
            scalars + kick-correlation and write to the side-car band_shares
            table inside library-clap.db. Best-effort — failures log and skip.
            Default False keeps legacy callers byte-identical (Plan 93-06).
        compute_key: when True, estimate a missing musical key offline with a
            pure-numpy K-S estimator. Existing key tags are never clobbered.
        compute_bpm: when True, estimate missing BPM offline with the same
            kick-band autocorrelation used by the cue engine. Existing source
            BPM is never clobbered.

    Returns:
        :class:`IngestReport`.
    """
    from vibemix.library.budget import get_telemetry

    root = Path(root)
    _assert_store_dim_compatible(store)

    if embed_strategy is None:
        embed_strategy = getattr(embedder, "_embed_strategy", "mean_excerpt")

    files = scan_folder(root)
    report = IngestReport(total=len(files), embed_strategy=embed_strategy)
    handled: dict[str, TrackEntry] = {}

    for idx, path in enumerate(files, start=1):
        filename = path.name

        duration = probe(path)
        if duration is None:
            logger.error("[ingest err] %s: unprobeable", path)
            report.failed += 1
            report.failures.append((str(path), "unprobeable"))
            _emit_progress(progress, idx, report.total, "err", filename, get_telemetry)
            continue

        entry = folder_to_track_entry(path, duration)
        if compute_key and not entry.key:
            est = estimate_key(path)
            if est is not None:
                entry = replace(
                    entry,
                    key=est.musical,
                    camelot=est.camelot,
                    key_source=est.source,
                )
                report.key_estimated_tracks += 1
            else:
                report.key_estimation_failed += 1
        if compute_bpm and (not entry.bpm or entry.bpm <= 0.0):
            bpm_est = estimate_bpm(path)
            if bpm_est is not None:
                entry = replace(entry, bpm=bpm_est.bpm, bpm_source=bpm_est.source)
                report.bpm_estimated_tracks += 1
            else:
                report.bpm_estimation_failed += 1

        # Resumable accounting — was this content already embedded?
        try:
            was_cached = bool(embedder.has_cached_embedding(entry))
        except Exception:  # pragma: no cover - defensive
            was_cached = False

        try:
            vec = embedder.embed_track(entry)
        except Exception as e:  # broad on purpose — one bad file must not abort
            logger.error("[ingest err] %s: %s", path, e)
            report.failed += 1
            report.failures.append((str(path), str(e)))
            _emit_progress(progress, idx, report.total, "err", filename, get_telemetry)
            continue

        # Honest store: only persist a real vector.
        store.add_batch([(entry.track_id, vec)])
        handled[entry.track_id] = entry

        # === Plan 93-06 / EXEMPLAR-01 — additive: persist band-shares ===
        # Gated by the ``compute_band_shares`` kwarg so existing CLAP-only
        # ingest callers (e.g. ``vibemix library ingest``) stay byte-identical.
        # Best-effort: a band-share failure NEVER aborts an otherwise-good
        # CLAP ingest — log + skip the row.
        #
        # Local imports keep the legacy ingest path's import graph identical
        # when the flag is off (``learn.exemplar`` + ``learn.band_share_store``
        # are NEVER loaded). The 93-RESEARCH.md Pattern 9 verbatim port.
        if compute_band_shares:
            try:
                from vibemix.learn import exemplar as _exemplar_mod
                from vibemix.learn.band_share_store import (
                    open_default_db as _bs_open,
                )
                from vibemix.learn.band_share_store import (
                    upsert as _bs_upsert,
                )

                feats = _exemplar_mod.compute_band_shares(str(path))
                with _bs_open() as bs_conn:
                    _bs_upsert(
                        bs_conn,
                        entry.track_id,
                        feats["sub_share"],
                        feats["low_share"],
                        feats["mid_share"],
                        feats["high_share"],
                        feats["kick_corr"],
                        time.time(),
                    )
            except Exception as bs_exc:
                logger.warning("[band-share err] %s: %s", path, bs_exc)
        # === END Plan 93-06 ===

        if was_cached:
            report.skipped_cached += 1
            tag = "skip"
        else:
            report.embedded += 1
            tag = "ok"
        _emit_progress(progress, idx, report.total, tag, filename, get_telemetry)

    report.cost_estimate_eur = float(
        get_telemetry().current_cost_estimate_eur()
    )

    if persist_library and handled:
        try:
            _write_library_cache(handled, root)
        except OSError as e:  # cache is a perf affordance, not correctness
            logger.warning("library.pkl cache write failed: %s", e)

    return report


def _emit_progress(
    progress: Callable[[str], None] | None,
    n: int,
    total: int,
    tag: str,
    filename: str,
    get_telemetry: Callable[[], object],
) -> None:
    if progress is None:
        return
    try:
        cost = float(get_telemetry().current_cost_estimate_eur())  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - defensive
        cost = 0.0
    progress(f"[{n}/{total}] {tag} {filename}  ~€{cost:.4f}")


__all__ = [
    "SUPPORTED_SUFFIXES",
    "IngestReport",
    "folder_to_track_entry",
    "ingest_folder",
    "probe_duration_s",
    "scan_folder",
]
