# SPDX-License-Identifier: Apache-2.0
"""coach_loop cancel-and-refire wiring — Plan 19-05 Task 3.

When a stale in-flight handle exists in ``trigger_state`` (e.g. left over
from a TimeoutError on the previous tick) and a new event arrives with
strictly greater ``Event.priority``, ``coach_loop`` invokes
``cancel_gate.try_cancel(handle, incoming, in_flight_ev)``. On True it
awaits ``agent.invalidate_cache()`` (so the refire starts with a fresh
cached prefix) and proceeds to fire the new event.

The current synchronous ``await wait_for_playout()`` invariant means a
stale handle is the ONLY path through which the cancel branch is
reachable from Plan 19-05. v2.x asynchronous fan-in (multiple events
arriving inside one playout) will also flow through the same seam.
"""

from __future__ import annotations

import asyncio

from vibemix.runtime.coach import coach_loop
from vibemix.state import Event


_REAL_SLEEP = asyncio.sleep


def _auto_time(start: float = 1000.0, step: float = 0.1):
    state = {"t": start}

    def _now() -> float:
        cur = state["t"]
        state["t"] += step
        return cur

    return _now


def _make_stop_after(n_sleeps: int, stop_event: asyncio.Event):
    sleep_calls: list[float] = []

    async def fake_sleep(s: float) -> None:
        sleep_calls.append(s)
        if len(sleep_calls) >= n_sleeps:
            stop_event.set()
        await _REAL_SLEEP(0)

    return fake_sleep, sleep_calls


def test_stale_inflight_handle_preempted_by_higher_priority(
    mocker,
    fake_session,
    fake_handle,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_cancel_gate,
    fake_ttft_meter,
    fake_playback,
):
    """Stale handle from prior tick + incoming MANUAL (priority=10) over
    in_flight HEARTBEAT (priority=1) → try_cancel called and on True,
    invalidate_cache awaited."""
    incoming = Event(type="MANUAL", state=music_state, extra={})
    in_flight_ev = Event(type="HEARTBEAT", state=music_state, extra={})
    fake_event_detector.detect.return_value = incoming
    fake_cancel_gate.try_cancel = mocker.MagicMock(return_value=True)

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    manual_trigger = asyncio.Event()
    # Pre-seed a stale in-flight handle + ev — simulates a prior tick where
    # wait_for_playout TimeoutError'd but didn't clear handle/ev.
    trigger_state = {
        "in_flight": False,  # the prior tick's finally cleared this
        "in_flight_handle": fake_handle,
        "in_flight_ev": in_flight_ev,
    }

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            manual_trigger,
            trigger_state,
            stop_event,
            cancel_gate=fake_cancel_gate,
            ttft_meter=fake_ttft_meter,
            playback=fake_playback,
        )
    )

    fake_cancel_gate.try_cancel.assert_called_once()
    cargs = fake_cancel_gate.try_cancel.call_args
    assert cargs.args[0] is fake_handle
    assert cargs.args[1] is incoming
    assert cargs.args[2] is in_flight_ev
    fake_agent.invalidate_cache.assert_awaited_once()


def test_stale_inflight_handle_not_preempted_by_lower_priority(
    mocker,
    fake_session,
    fake_handle,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_cancel_gate,
    fake_ttft_meter,
    fake_playback,
):
    """Stale handle in-flight MANUAL (priority=10) + incoming HEARTBEAT
    (priority=1) → try_cancel returns False → invalidate_cache NOT awaited."""
    incoming = Event(type="HEARTBEAT", state=music_state, extra={})
    in_flight_ev = Event(type="MANUAL", state=music_state, extra={})
    fake_event_detector.detect.return_value = incoming
    fake_cancel_gate.try_cancel = mocker.MagicMock(return_value=False)

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    manual_trigger = asyncio.Event()
    trigger_state = {
        "in_flight": False,
        "in_flight_handle": fake_handle,
        "in_flight_ev": in_flight_ev,
    }

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            manual_trigger,
            trigger_state,
            stop_event,
            cancel_gate=fake_cancel_gate,
            ttft_meter=fake_ttft_meter,
            playback=fake_playback,
        )
    )

    fake_cancel_gate.try_cancel.assert_called_once()
    fake_agent.invalidate_cache.assert_not_awaited()


def test_no_stale_handle_skips_cancel_path(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_event,
    fake_cancel_gate,
    fake_ttft_meter,
    fake_playback,
):
    """No stale in_flight_handle in trigger_state → try_cancel never called."""
    fake_event_detector.detect.return_value = fake_event
    fake_cancel_gate.try_cancel = mocker.MagicMock(return_value=False)

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}  # no in_flight_handle / in_flight_ev

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            manual_trigger,
            trigger_state,
            stop_event,
            cancel_gate=fake_cancel_gate,
            ttft_meter=fake_ttft_meter,
            playback=fake_playback,
        )
    )

    fake_cancel_gate.try_cancel.assert_not_called()
    fake_agent.invalidate_cache.assert_not_awaited()
