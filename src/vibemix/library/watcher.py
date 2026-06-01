# SPDX-License-Identifier: Apache-2.0
"""Event-driven library freshness watcher.

This module owns the live-session watcher loop. The freshness policy and
snooze state stay in ``staleness.py``; the watcher is intentionally fail-soft
and off-loop so catalog refresh checks never wedge live audio.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

from vibemix.library.staleness import (
    DEFAULT_LIBRARY_PKL,
    LibraryFreshness,
    _refreshable_source_path,
    is_snoozed,
    library_freshness_status,
    load_snooze_state,
)

logger = logging.getLogger(__name__)

FreshnessChangeWaiter = Callable[[set[Path], asyncio.Event, float], Awaitable[None]]


def _freshness_watch_targets(
    status: LibraryFreshness,
    library_pkl: Path | None = None,
) -> set[Path]:
    """Files whose change should trigger an immediate freshness re-check."""
    targets: set[Path] = set()
    cache_path = status.cache_path or str(library_pkl or DEFAULT_LIBRARY_PKL)
    if cache_path:
        targets.add(Path(cache_path).expanduser())
    if status.source_path:
        targets.add(Path(status.source_path).expanduser())
    return targets


async def _wait_for_watchfiles_or_timeout(
    targets: set[Path],
    stop_event: asyncio.Event,
    poll_seconds: float,
) -> None:
    """Wait for a watched library file to change, falling back to the poll timer."""
    if stop_event.is_set():
        return
    poll = max(0.01, float(poll_seconds))
    try:
        from watchfiles import awatch
    except Exception:
        awatch = None

    if awatch is not None and targets:
        resolved_targets = {p.resolve(strict=False) for p in targets}
        roots = sorted(
            {
                (p if p.is_dir() else p.parent).resolve(strict=False)
                for p in targets
                if (p if p.is_dir() else p.parent).exists()
            }
        )
        if roots:

            def _watch_filter(_change, path: str) -> bool:
                return Path(path).resolve(strict=False) in resolved_targets

            async def _one_change() -> None:
                async for changes in awatch(
                    *roots,
                    watch_filter=_watch_filter,
                    debounce=500,
                    recursive=False,
                ):
                    if changes or stop_event.is_set():
                        return

            try:
                watch_task = asyncio.create_task(_one_change())
                stop_task = asyncio.create_task(stop_event.wait())
                done, pending = await asyncio.wait(
                    {watch_task, stop_task},
                    timeout=poll,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                for task in done:
                    task.result()
                return
            except TimeoutError:
                return
            except Exception as e:  # pragma: no cover - watcher must degrade to poll
                logger.debug("watchfiles library watcher unavailable: %s", e)

    try:
        await asyncio.wait_for(stop_event.wait(), timeout=poll)
    except TimeoutError:
        pass


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
    """Watch library freshness and emit a staleness nudge when it changes stale.

    This intentionally reuses the existing closed IPC schema
    ``ipc.library.staleness_nudge``. The richer status travels through
    ``library stats``; the watcher is the lightweight "pay attention now" pulse.
    ``watchfiles`` gives fast source/cache invalidation when available; otherwise
    the loop degrades to the existing bounded poll.
    """
    poll = max(0.01, float(poll_seconds))
    last_signature: tuple[object, ...] | None = None
    wait_for_change = change_waiter or _wait_for_watchfiles_or_timeout
    while not stop_event.is_set():
        watch_targets = {Path(library_pkl or DEFAULT_LIBRARY_PKL).expanduser()}
        try:
            status = (
                status_provider()
                if status_provider is not None
                else library_freshness_status(library_pkl)
            )
            signature = (
                status.status,
                status.reason,
                status.cache_mtime,
                status.source_mtime,
            )
            payload = None
            if signature != last_signature and status.status != "not_indexed" and status.stale:
                if not is_snoozed(state_path):
                    payload = {
                        "age_days": status.age_days,
                        "snoozed_until_ts": load_snooze_state(state_path),
                        "source_path": _refreshable_source_path(status),
                        "reason": status.reason,
                        "schema_version": "1",
                    }
            last_signature = signature
            watch_targets = _freshness_watch_targets(status, library_pkl)
            if payload is not None:
                emit_ipc("ipc.library.staleness_nudge", payload)
        except Exception as e:  # pragma: no cover - watcher must never kill live runtime
            logger.warning("library freshness watcher failed: %s", e)
        await wait_for_change(watch_targets, stop_event, poll)


__all__ = [
    "FreshnessChangeWaiter",
    "_freshness_watch_targets",
    "watch_library_freshness",
]
