# SPDX-License-Identifier: Apache-2.0
"""Phase 28 Plan 07 — source-aware library freshness nudges.

Closes v2.0 LIBRARY-06 deferred surface: detect when the user's library
cache is older than 30 days, when a source catalog/folder has changed after the
cache was written, or when a known Rekordbox ``collection.xml`` is present but
the user has not indexed it yet. Snooze persists 7 days in
``~/.config/vibemix/state.json``.

Pure functions — no module-level state. Caller (``__main__.py``) decides
when to call ``emit_nudge_if_stale`` (once per boot).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pickle
import tempfile
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# 30-day staleness threshold + 7-day snooze duration. Locked.
STALE_AGE_SECONDS = 30 * 86400
SNOOZE_DURATION_SECONDS = 7 * 86400

# Plan 25's library.pkl path — the staleness signal.
DEFAULT_LIBRARY_PKL = Path.home() / ".cache" / "vibemix" / "library.pkl"

# Snooze state lives under the standard user config dir.
DEFAULT_STATE_FILE_PATH = Path.home() / ".config" / "vibemix" / "state.json"
STATE_KEY = "library_staleness_snoozed_until"
FreshnessStatus = Literal["fresh", "stale", "not_indexed", "source_missing", "cache_unreadable"]
FreshnessChangeWaiter = Callable[[set[Path], asyncio.Event, float], Awaitable[None]]
_AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".flac", ".aac"}


@dataclass(frozen=True, slots=True)
class LibraryFreshness:
    """Truthful freshness status for the cache Viber/set prep depends on."""

    status: FreshnessStatus
    stale: bool
    reason: str
    age_days: int
    cache_path: str
    source_path: str | None = None
    source_age_days: int | None = None
    cache_mtime: float | None = None
    source_mtime: float | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _age_days_from_mtime(mtime: float, *, now: float) -> int:
    return max(0, int((now - mtime) // 86400))


def _refreshable_source_path(status: LibraryFreshness) -> str | None:
    """Return a source path the existing XML importer can refresh directly."""
    source_path = status.source_path
    if not source_path:
        return None
    path = Path(source_path)
    if path.suffix.lower() != ".xml" or not path.exists():
        return None
    return source_path


def _detect_library_source_path() -> str | None:
    """Return a local source catalog the app can import without user browsing.

    This is intentionally narrow: today only a Rekordbox ``collection.xml`` at
    the known export locations is auto-detected. Raw music folders still require
    an explicit user action via ``embed-folder`` so we never recursively scan a
    DJ's whole Music tree without consent.
    """
    try:
        from vibemix.library.sources.rekordbox import RekordboxSource

        source = RekordboxSource()
        if source.detect():
            return source.resolved_path
    except Exception as e:
        logger.debug("library source auto-detect failed: %s", e)
    return None


def _catalog_tree_mtime(root: Path) -> float:
    """Latest mtime for a folder-backed library source.

    ``folder_ingest`` stores the source as the folder root. A plain root mtime
    misses changes in nested crate folders, so include directory mtimes plus
    supported audio-file mtimes. This is still read-only and bounded to the
    folder the DJ already imported.
    """
    latest = root.stat().st_mtime
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if not name.startswith(".")]
        try:
            latest = max(latest, Path(dirpath).stat().st_mtime)
        except OSError:
            continue
        for filename in filenames:
            if filename.startswith(".") or Path(filename).suffix.lower() not in _AUDIO_SUFFIXES:
                continue
            try:
                latest = max(latest, (Path(dirpath) / filename).stat().st_mtime)
            except OSError:
                continue
    return latest


def _current_source_mtime(source_path: str) -> float:
    path = Path(source_path).expanduser()
    if path.is_dir():
        return _catalog_tree_mtime(path)
    return os.path.getmtime(path)


def _legacy_cache_path(pkl: Path) -> Path | None:
    if pkl.name.endswith(".v1bak"):
        return None
    return pkl.with_suffix(pkl.suffix + ".v1bak")


def _should_emit_nudge(status: LibraryFreshness) -> bool:
    if status.status == "not_indexed":
        return _refreshable_source_path(status) is not None
    return status.stale


def is_stale(library_pkl: Path | None = None) -> tuple[bool, int]:
    """Return ``(is_stale, age_in_days)`` for the library cache.

    Returns ``(False, 0)`` when no ``library.pkl`` exists — fresh-install
    users must NOT see a nudge they don't yet need.
    """
    pkl = Path(library_pkl) if library_pkl else DEFAULT_LIBRARY_PKL
    if not pkl.exists():
        return False, 0
    age = time.time() - pkl.stat().st_mtime
    return age > STALE_AGE_SECONDS, int(age // 86400)


def library_freshness_status(
    library_pkl: Path | None = None,
    *,
    now: float | None = None,
) -> LibraryFreshness:
    """Return a source-aware freshness status for ``library.pkl``.

    ``is_stale`` is the legacy 30-day nudge. This status is stricter for
    product claims: if the source catalog/folder is newer than the cache, Viber
    should treat the library as stale even when the cache is young.
    """
    if library_pkl is None:
        from vibemix.library.rekordbox import RekordboxLibrary

        pkl = RekordboxLibrary.CACHE_PATH
    else:
        pkl = Path(library_pkl)
    now_ts = time.time() if now is None else now
    cache_path = str(pkl)
    if not pkl.exists():
        legacy_pkl = _legacy_cache_path(pkl)
        if legacy_pkl is not None and legacy_pkl.exists():
            return library_freshness_status(legacy_pkl, now=now_ts)
        detected_source = _detect_library_source_path()
        return LibraryFreshness(
            status="not_indexed",
            stale=False,
            reason=(
                "source_detected_not_indexed"
                if detected_source
                else "library_cache_missing"
            ),
            age_days=0,
            cache_path=cache_path,
            source_path=detected_source,
        )

    try:
        cache_stat = pkl.stat()
    except OSError as e:
        return LibraryFreshness(
            status="cache_unreadable",
            stale=True,
            reason=f"cache_stat_failed:{type(e).__name__}",
            age_days=0,
            cache_path=cache_path,
        )

    cache_age_days = _age_days_from_mtime(cache_stat.st_mtime, now=now_ts)
    try:
        with pkl.open("rb") as fh:
            blob = pickle.load(fh)
    except Exception as e:  # cache is optional; stats must stay fail-soft
        return LibraryFreshness(
            status="cache_unreadable",
            stale=True,
            reason=f"cache_read_failed:{type(e).__name__}",
            age_days=cache_age_days,
            cache_path=cache_path,
            cache_mtime=cache_stat.st_mtime,
        )

    source_path = getattr(blob, "xml_path", None)
    recorded_source_mtime = getattr(blob, "xml_mtime", None)
    if not isinstance(source_path, str) or not source_path:
        return LibraryFreshness(
            status="cache_unreadable",
            stale=True,
            reason="cache_missing_source_path",
            age_days=cache_age_days,
            cache_path=cache_path,
            cache_mtime=cache_stat.st_mtime,
        )
    if not isinstance(recorded_source_mtime, (int, float)):
        return LibraryFreshness(
            status="cache_unreadable",
            stale=True,
            reason="cache_missing_source_mtime",
            age_days=cache_age_days,
            cache_path=cache_path,
            source_path=source_path,
            cache_mtime=cache_stat.st_mtime,
        )

    from vibemix.library.rekordbox import (
        _is_repo_test_fixture_source_path,
        _is_user_library_cache_path,
    )

    if _is_user_library_cache_path(pkl) and _is_repo_test_fixture_source_path(source_path):
        legacy_pkl = _legacy_cache_path(pkl)
        if legacy_pkl is not None and legacy_pkl.exists():
            legacy_status = library_freshness_status(legacy_pkl, now=now_ts)
            if legacy_status.reason != "cache_points_to_test_fixture":
                return legacy_status
        detected_source = _detect_library_source_path()
        return LibraryFreshness(
            status="cache_unreadable",
            stale=True,
            reason="cache_points_to_test_fixture",
            age_days=cache_age_days,
            cache_path=cache_path,
            source_path=detected_source,
            cache_mtime=cache_stat.st_mtime,
            source_mtime=float(recorded_source_mtime),
        )

    try:
        current_source_mtime = _current_source_mtime(source_path)
    except OSError:
        return LibraryFreshness(
            status="source_missing",
            stale=True,
            reason="source_path_missing",
            age_days=cache_age_days,
            cache_path=cache_path,
            source_path=source_path,
            cache_mtime=cache_stat.st_mtime,
            source_mtime=float(recorded_source_mtime),
        )

    source_age_days = _age_days_from_mtime(current_source_mtime, now=now_ts)
    if current_source_mtime > float(recorded_source_mtime) + 1.0:
        return LibraryFreshness(
            status="stale",
            stale=True,
            reason="source_newer_than_cache",
            age_days=cache_age_days,
            cache_path=cache_path,
            source_path=source_path,
            source_age_days=source_age_days,
            cache_mtime=cache_stat.st_mtime,
            source_mtime=current_source_mtime,
        )
    if now_ts - cache_stat.st_mtime > STALE_AGE_SECONDS:
        return LibraryFreshness(
            status="stale",
            stale=True,
            reason="cache_older_than_30d",
            age_days=cache_age_days,
            cache_path=cache_path,
            source_path=source_path,
            source_age_days=source_age_days,
            cache_mtime=cache_stat.st_mtime,
            source_mtime=current_source_mtime,
        )
    return LibraryFreshness(
        status="fresh",
        stale=False,
        reason="cache_current",
        age_days=cache_age_days,
        cache_path=cache_path,
        source_path=source_path,
        source_age_days=source_age_days,
        cache_mtime=cache_stat.st_mtime,
        source_mtime=current_source_mtime,
    )


def freshness_nudge_payload(
    library_pkl: Path | None = None,
    state_path: Path | None = None,
    *,
    now: float | None = None,
) -> dict[str, object] | None:
    """Return an existing-schema nudge payload when freshness needs attention."""
    status = library_freshness_status(library_pkl, now=now)
    if not _should_emit_nudge(status):
        return None
    if is_snoozed(state_path):
        return None
    return {
        "age_days": status.age_days,
        "snoozed_until_ts": load_snooze_state(state_path),
        "source_path": _refreshable_source_path(status),
        "reason": status.reason,
        "schema_version": "1",
    }


def _freshness_watch_targets(
    status: LibraryFreshness,
    library_pkl: Path | None = None,
) -> set[Path]:
    """Backward-compatible wrapper for the watcher module's target planner."""
    from vibemix.library.watcher import _freshness_watch_targets as _impl

    return _impl(status, library_pkl)


async def watch_library_freshness(
    emit_ipc: Callable[[str, dict], None],
    stop_event: asyncio.Event,
    *,
    poll_seconds: float = 10.0,
    library_pkl: Path | None = None,
    state_path: Path | None = None,
    status_provider: Callable[[], LibraryFreshness] | None = None,
    change_waiter: FreshnessChangeWaiter | None = None,
) -> None:
    """Backward-compatible wrapper for ``vibemix.library.watcher``."""
    from vibemix.library.watcher import watch_library_freshness as _impl

    await _impl(
        emit_ipc,
        stop_event,
        poll_seconds=poll_seconds,
        library_pkl=library_pkl,
        state_path=state_path,
        status_provider=status_provider,
        change_waiter=change_waiter,
    )


def load_snooze_state(state_path: Path | None = None) -> float | None:
    """Read the snooze timestamp from state.json.

    Returns ``None`` when:
        - state.json doesn't exist (fresh install)
        - JSON is malformed (graceful — we log + over-nudge rather than crash)
        - the snooze key is absent
    """
    sp = Path(state_path) if state_path else DEFAULT_STATE_FILE_PATH
    try:
        with sp.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("staleness state.json malformed (%s); treating as empty", e)
        return None
    val = data.get(STATE_KEY)
    if isinstance(val, (int, float)):
        return float(val)
    return None


def save_snooze_state(
    snoozed_until_ts: float, state_path: Path | None = None
) -> None:
    """Atomic write of snooze state. Preserves existing keys.

    **Single-process assumption (REVIEW WR-03):** the read+merge+write
    sequence is NOT atomic across processes. vibemix is a single-instance
    desktop app — concurrent writers from multiple sidecar instances
    would race and the loser's update (including unrelated state.json
    keys) would be lost. v1 accepts this; if multi-instance support
    lands later, add an advisory ``fcntl.flock`` around the read+write.
    The file write itself IS atomic via ``os.replace``.
    """
    sp = Path(state_path) if state_path else DEFAULT_STATE_FILE_PATH
    sp.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sp.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}
    data[STATE_KEY] = float(snoozed_until_ts)

    # Atomic write: tempfile in same dir + os.replace. NamedTemporaryFile so
    # the tmp file is cleaned up on exception before the replace.
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=str(sp.parent), prefix=".state-", suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp_path, sp)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def is_snoozed(state_path: Path | None = None) -> bool:
    """True iff snooze is set AND not yet expired."""
    snoozed_until = load_snooze_state(state_path)
    if snoozed_until is None:
        return False
    return snoozed_until > time.time()


def emit_nudge_if_stale(
    emit_ipc: Callable[[str, dict], None],
    library_pkl: Path | None = None,
    state_path: Path | None = None,
) -> bool:
    """Boot-time check: emit a freshness/import nudge when action is needed.

    Returns ``True`` if the nudge was emitted, ``False`` otherwise. Pure —
    caller must invoke once per boot.
    """
    payload = freshness_nudge_payload(library_pkl, state_path)
    if payload is None:
        return False
    emit_ipc("ipc.library.staleness_nudge", payload)
    return True


def apply_snooze_action(
    action: str, state_path: Path | None = None
) -> None:
    """Apply a renderer-initiated staleness action.

    Actions:
        ``"dismiss"``  → no-op on disk (UI hides banner this-session only).
        ``"snooze_7d"`` → persist ``time.time() + SNOOZE_DURATION_SECONDS``.

    Unknown actions raise ValueError.
    """
    if action == "dismiss":
        return
    if action == "snooze_7d":
        save_snooze_state(time.time() + SNOOZE_DURATION_SECONDS, state_path)
        return
    raise ValueError(
        f"unknown staleness action {action!r}; "
        f"expected 'dismiss' or 'snooze_7d'"
    )


__all__ = [
    "DEFAULT_LIBRARY_PKL",
    "DEFAULT_STATE_FILE_PATH",
    "SNOOZE_DURATION_SECONDS",
    "STALE_AGE_SECONDS",
    "STATE_KEY",
    "FreshnessStatus",
    "LibraryFreshness",
    "apply_snooze_action",
    "emit_nudge_if_stale",
    "freshness_nudge_payload",
    "is_snoozed",
    "is_stale",
    "library_freshness_status",
    "load_snooze_state",
    "save_snooze_state",
    "watch_library_freshness",
]
