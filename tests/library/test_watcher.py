# SPDX-License-Identifier: Apache-2.0
"""Direct tests for the event-driven library freshness watcher."""
from __future__ import annotations

import asyncio
from pathlib import Path

from vibemix.library.staleness import LibraryFreshness
from vibemix.library.watcher import _freshness_watch_targets, watch_library_freshness


def _fresh_status(cache: Path, source: Path) -> LibraryFreshness:
    return LibraryFreshness(
        status="fresh",
        stale=False,
        reason="cache_current",
        age_days=0,
        cache_path=str(cache),
        source_path=str(source),
        cache_mtime=1.0,
        source_mtime=1.0,
    )


def _stale_status(cache: Path, source: Path) -> LibraryFreshness:
    return LibraryFreshness(
        status="stale",
        stale=True,
        reason="source_newer_than_cache",
        age_days=0,
        cache_path=str(cache),
        source_path=str(source),
        cache_mtime=1.0,
        source_mtime=2.0,
    )


def test_freshness_watch_targets_falls_back_to_library_cache_path(tmp_path: Path) -> None:
    cache = tmp_path / "library.pkl"
    status = LibraryFreshness(
        status="fresh",
        stale=False,
        reason="cache_current",
        age_days=0,
        cache_path="",
    )

    assert _freshness_watch_targets(status, library_pkl=cache) == {cache}


def test_watch_library_freshness_updates_targets_after_each_status(tmp_path: Path) -> None:
    cache = tmp_path / "library.pkl"
    first_source = tmp_path / "first.xml"
    second_source = tmp_path / "second.xml"
    statuses = [
        _fresh_status(cache, first_source),
        _fresh_status(cache, second_source),
    ]
    targets_seen: list[set[Path]] = []

    def provider() -> LibraryFreshness:
        return statuses.pop(0) if statuses else _fresh_status(cache, second_source)

    async def change_waiter(
        targets: set[Path],
        stop_event: asyncio.Event,
        poll_seconds: float,
    ) -> None:
        assert poll_seconds == 0.01
        targets_seen.append(targets)
        if len(targets_seen) >= 2:
            stop_event.set()
        await asyncio.sleep(0)

    async def _run() -> None:
        stop = asyncio.Event()
        await asyncio.wait_for(
            watch_library_freshness(
                lambda _msg_type, _payload: None,
                stop,
                poll_seconds=0.01,
                status_provider=provider,
                change_waiter=change_waiter,
            ),
            timeout=0.5,
        )

    asyncio.run(_run())

    assert targets_seen == [
        {cache, first_source},
        {cache, second_source},
    ]


def test_watch_library_freshness_suppresses_duplicate_stale_signature(tmp_path: Path) -> None:
    cache = tmp_path / "library.pkl"
    source = tmp_path / "collection.xml"
    source.write_text("<DJ_PLAYLISTS />", encoding="utf-8")
    stale = _stale_status(cache, source)
    emissions: list[tuple[str, dict]] = []
    waits = 0

    async def change_waiter(
        _targets: set[Path],
        stop_event: asyncio.Event,
        _poll_seconds: float,
    ) -> None:
        nonlocal waits
        waits += 1
        if waits >= 2:
            stop_event.set()
        await asyncio.sleep(0)

    async def _run() -> None:
        stop = asyncio.Event()
        await asyncio.wait_for(
            watch_library_freshness(
                lambda msg_type, payload: emissions.append((msg_type, payload)),
                stop,
                poll_seconds=0.01,
                state_path=tmp_path / "state.json",
                status_provider=lambda: stale,
                change_waiter=change_waiter,
            ),
            timeout=0.5,
        )

    asyncio.run(_run())

    assert [msg_type for msg_type, _payload in emissions] == ["ipc.library.staleness_nudge"]
    assert emissions[0][1]["reason"] == "source_newer_than_cache"
