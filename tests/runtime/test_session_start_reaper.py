# SPDX-License-Identifier: Apache-2.0
"""Activation-timeout zombie reaper — vibemix.__main__._reap_session_task.

A Start whose activation never signals 'started' (e.g. a wedged CoreAudio
open) used to leave the activation task alive forever: Start became a silent
no-op (task not done) and Stop a silent no-op (live_session_active never
flipped), so only an app relaunch recovered. The reaper cancels + drains the
zombie so the timeout error that reaches the UI is also the backend truth.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from vibemix.__main__ import _reap_session_task


def test_reaper_cancels_a_wedged_activation_task() -> None:
    async def go() -> None:
        stop = asyncio.Event()

        async def wedged_activation() -> None:
            await asyncio.Event().wait()  # never returns — the wedge

        task = asyncio.create_task(wedged_activation())
        await asyncio.sleep(0)
        await _reap_session_task(task, stop)
        assert stop.is_set()
        assert task.done()
        assert task.cancelled()

    asyncio.run(go())


def test_reaper_tolerates_missing_refs() -> None:
    async def go() -> None:
        await _reap_session_task(None, None)  # must not raise

    asyncio.run(go())


def test_reaper_swallows_teardown_errors() -> None:
    async def go() -> None:
        async def raises_on_cancel() -> None:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                raise RuntimeError("teardown failed")

        task = asyncio.create_task(raises_on_cancel())
        await asyncio.sleep(0)
        await _reap_session_task(task, None)  # must not raise
        assert task.done()

    asyncio.run(go())


def test_start_timeout_branch_reaps_and_resets_the_slots() -> None:
    """Source contract (the lifecycle lives in main()'s closure): the
    TimeoutError branch must reap the zombie and reset active_task/
    active_stop_event before raising, and the post-wait path must surface a
    draining activation failure instead of a phantom success."""
    src = Path("src/vibemix/__main__.py").read_text(encoding="utf-8")
    after_wait = src.split("await asyncio.wait_for(started_event.wait()", 1)[1][:2400]
    assert "await _reap_session_task(active_task, active_stop_event)" in after_wait
    assert "session.start timed out" in after_wait
    assert "elif not live_session_active:" in after_wait
