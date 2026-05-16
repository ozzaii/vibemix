# SPDX-License-Identifier: Apache-2.0
"""WATCHDOG-01..04 — parent_watchdog.watch_parent.

The watchdog trips ``stop_event`` when ``os.getppid()`` changes from the
value sampled at task start — covering both the ppid=1 orphan adoption by
launchd and any other parent-replacement edge case. These tests pin the
core invariants without spinning real subprocesses.
"""

from __future__ import annotations

import asyncio
import inspect

from vibemix.runtime.parent_watchdog import POLL_INTERVAL_S, watch_parent

_REAL_SLEEP = asyncio.sleep


def test_watchdog_01_is_async_function():
    """WATCHDOG-01: ``watch_parent`` is a coroutine."""
    assert inspect.iscoroutinefunction(watch_parent)


def test_watchdog_02_exits_cleanly_on_external_stop(mocker):
    """WATCHDOG-02: setting ``stop_event`` from elsewhere lets the task
    return without consulting ppid again (covers normal SIGTERM path)."""
    # Pin getppid so a flake doesn't drive the assertion.
    mocker.patch("vibemix.runtime.parent_watchdog.os.getppid", return_value=12345)

    async def runner():
        stop = asyncio.Event()
        task = asyncio.create_task(watch_parent(stop))
        await _REAL_SLEEP(0)  # let watch_parent enter the wait
        stop.set()
        await asyncio.wait_for(task, timeout=1.0)

    asyncio.run(runner())


def test_watchdog_03_trips_stop_when_ppid_becomes_one(mocker):
    """WATCHDOG-03: when ``getppid()`` returns 1 after the initial sample,
    the watchdog sets ``stop_event`` and exits.

    Simulates the launchd-adoption orphan path. Shrinks the poll interval
    via module-constant monkey-patch so the test runs in ~50 ms instead
    of the production 2 s cadence.
    """
    ppid_returns = iter([12345, 1, 1, 1])  # initial, then orphan flip
    mocker.patch(
        "vibemix.runtime.parent_watchdog.os.getppid", side_effect=lambda: next(ppid_returns)
    )
    mocker.patch("vibemix.runtime.parent_watchdog.POLL_INTERVAL_S", 0.01)

    async def runner():
        stop = asyncio.Event()
        await asyncio.wait_for(watch_parent(stop), timeout=1.0)
        assert stop.is_set()

    asyncio.run(runner())


def test_watchdog_04_no_op_when_already_orphaned(mocker):
    """WATCHDOG-04: when the initial ppid is 1 (we were launched detached,
    e.g. ``open vibemix.app`` outside Tauri), the watchdog returns
    immediately without ever tripping stop. Prevents shutting down a
    legitimately-detached run."""
    mocker.patch("vibemix.runtime.parent_watchdog.os.getppid", return_value=1)

    async def runner():
        stop = asyncio.Event()
        await asyncio.wait_for(watch_parent(stop), timeout=0.2)
        assert not stop.is_set()

    asyncio.run(runner())


def test_watchdog_05_poll_interval_within_reason():
    """WATCHDOG-05: pin the poll interval — too short burns CPU on every
    sidecar; too long widens the orphan window past a normal dev relaunch.
    The 2 s constant is the documented sweet spot."""
    assert 0.5 <= POLL_INTERVAL_S <= 5.0
