# SPDX-License-Identifier: Apache-2.0
"""COACH-01..13 + CONST-WS-01 — coach_loop event pump + WS constants.

Strategy: patch ``asyncio.sleep`` in ``vibemix.runtime.coach`` with a
fast-forward callable that yields immediately and signals stop after N
ticks. Patch ``time.time`` to advance deterministically via a generator.
pytest-asyncio is NOT a project dep — use ``asyncio.run`` inside sync
test functions (same pattern as ``tests/state/test_refresh.py``).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from vibemix.runtime.coach import coach_loop

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _time_iter(times: list[float]):
    """Returns a callable usable as ``time.time`` side_effect that walks the
    provided list. The list MUST be long enough for the test or the iterator
    raises StopIteration (and pytest will surface a clear failure)."""
    it = iter(times)
    return lambda: next(it)


def _auto_time(start: float = 1000.0, step: float = 0.1):
    """Auto-advancing time — returns ``start, start+step, start+2*step, ...``."""
    state = {"t": start}

    def _now() -> float:
        cur = state["t"]
        state["t"] += step
        return cur

    return _now


# Capture the real asyncio.sleep BEFORE any test patches it — used inside
# the fake_sleep replacement to yield without recursing through the patch.
_REAL_SLEEP = asyncio.sleep


def _make_stop_after(n_sleeps: int, stop_event: asyncio.Event):
    """Build a fake_sleep coroutine that stops the loop after ``n_sleeps``
    asyncio.sleep calls. The 1st call is always the 2.0s warmup; subsequent
    calls are 0.1s post-warmup poll-cadence sleeps."""
    sleep_calls: list[float] = []

    async def fake_sleep(s: float) -> None:
        sleep_calls.append(s)
        if len(sleep_calls) >= n_sleeps:
            stop_event.set()
        # Yield to the loop via the REAL sleep so we don't recurse into the patch.
        await _REAL_SLEEP(0)

    return fake_sleep, sleep_calls


# ---------------------------------------------------------------------------
# COACH-01 — warmup
# ---------------------------------------------------------------------------


def test_coach_01_warmup_no_detect_before_first_post_warmup_tick(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """COACH-01: stop_event set during the warmup sleep → coach_loop
    returns without ever calling event_detector.detect."""
    stop_event = asyncio.Event()
    fake_sleep, sleep_calls = _make_stop_after(1, stop_event)

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

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
        )
    )

    assert sleep_calls[0] == 2.0
    assert fake_event_detector.detect.call_count == 0


# ---------------------------------------------------------------------------
# COACH-02 — poll cadence
# ---------------------------------------------------------------------------


def test_coach_02_poll_cadence_is_0_1s(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """COACH-02: each post-warmup loop iteration calls asyncio.sleep(0.1)."""
    stop_event = asyncio.Event()
    fake_sleep, sleep_calls = _make_stop_after(4, stop_event)  # 1 warmup + 3 ticks

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

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
        )
    )

    assert sleep_calls[0] == 2.0
    assert all(s == 0.1 for s in sleep_calls[1:])


# ---------------------------------------------------------------------------
# COACH-03 — event fire path
# ---------------------------------------------------------------------------


def test_coach_03_event_fire_path(
    mocker,
    fake_session,
    fake_handle,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_event,
):
    """COACH-03: with detect returning an event, the body calls
    agent.set_next_event(ev) → session.generate_reply →
    handle.wait_for_playout. Trigger_state.in_flight ends False.
    recorder.log_event('event', ...) is called with expected kwargs."""
    music_state.audible = True
    music_state.audible_deck = "A"
    music_state.audible_track = "Some Track"
    music_state.audible_track_confidence = 0.85
    music_state.phase = "peak"

    fake_event_detector.detect.return_value = fake_event

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)  # 1 warmup + 1 tick

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

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
        )
    )

    fake_agent.set_next_event.assert_called_once_with(fake_event)
    fake_session.generate_reply.assert_called_once_with(allow_interruptions=False)
    assert fake_handle.wait_for_playout.await_count == 1
    assert trigger_state["in_flight"] is False
    fake_recorder.log_event.assert_any_call(
        "event",
        type="TRACK_CHANGE",
        audible=True,
        deck="A",
        track="Some Track",
        track_conf=0.85,
        phase="peak",
    )


# ---------------------------------------------------------------------------
# COACH-04 — in-flight blocks subsequent ticks
# ---------------------------------------------------------------------------


def test_coach_04_in_flight_skips_detect(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """COACH-04: trigger_state.in_flight=True with recent in_flight_at
    (age <12s) → detect is skipped on this tick."""
    # 2 ticks with fresh in_flight_at (close to current time)
    mocker.patch(
        "vibemix.runtime.coach.time.time",
        side_effect=_time_iter([1000.05, 1000.15]),
    )

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(3, stop_event)  # 1 warmup + 2 ticks

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    manual_trigger = asyncio.Event()
    # in_flight_at=1000.0; first tick now=1000.05, age=0.05 <12 → skip
    trigger_state = {"in_flight": True, "in_flight_at": 1000.0}

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
        )
    )

    assert fake_event_detector.detect.call_count == 0
    assert trigger_state["in_flight"] is True


# ---------------------------------------------------------------------------
# COACH-05 — stale-clear at 12s
# ---------------------------------------------------------------------------


def test_coach_05_stale_clear_at_12s(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """COACH-05: trigger_state.in_flight=True with in_flight_at age >12s →
    loop clears in_flight=False AND proceeds with detect on the same tick."""
    # in_flight_at=1000.0; first tick now=1500.0, age=500s > 12 → clear + proceed
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_time_iter([1500.0, 1500.1]))

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)  # 1 warmup + 1 tick

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": True, "in_flight_at": 1000.0}

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
        )
    )

    assert trigger_state["in_flight"] is False
    assert fake_event_detector.detect.call_count == 1


# ---------------------------------------------------------------------------
# COACH-06 — AI talking blocks
# ---------------------------------------------------------------------------


def test_coach_06_ai_talking_blocks(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """COACH-06: levels.voice above AI_TALK_THRESHOLD → detect is skipped."""
    fake_levels.voice = 0.1  # above AI_TALK_THRESHOLD = 0.02

    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)  # 1 warmup + 1 tick

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

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
        )
    )

    assert fake_event_detector.detect.call_count == 0


# ---------------------------------------------------------------------------
# COACH-07 — post-AI cooldown (7s)
# ---------------------------------------------------------------------------


def test_coach_07_post_ai_cooldown(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """COACH-07: after AI stops talking, detect is skipped while delta <7s,
    then resumes after delta >=7s."""
    # 3-tick scenario:
    # tick 1: voice high → sets last_ai_voice_at=1001.0
    # tick 2: voice 0, now=1003.0 → delta=2.0 <7 → skip
    # tick 3: voice 0, now=1010.0 → delta=9.0 >=7 → detect
    voice_iter = iter([0.1, 0.0, 0.0])
    time_iter = iter([1001.0, 1003.0, 1010.0])

    # Make `voice` a property on the mock instance via the type
    type(fake_levels).voice = property(lambda self: next(voice_iter))

    mocker.patch("vibemix.runtime.coach.time.time", side_effect=lambda: next(time_iter))

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(4, stop_event)  # 1 warmup + 3 ticks

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

    try:
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
            )
        )
        assert fake_event_detector.detect.call_count == 1
    finally:
        # Clean up the property override so subsequent tests get the simple attr back
        del type(fake_levels).voice


# ---------------------------------------------------------------------------
# COACH-08 — KAAN_SPOKE full sequence
# ---------------------------------------------------------------------------


def test_coach_08_kaan_spoke_full_sequence(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """COACH-08: drive mic above threshold for 3 frames, then below for >0.6s
    → kaan_just_spoke=True is passed to detect on the firing tick.

    Also assert state.last_kaan_spoke_at was updated during active frames."""
    fake_levels.voice = 0.0

    # 5 ticks: 3 above threshold, 1 below (start silence), 1 below (>0.6s elapsed)
    mic_iter = iter([0.15, 0.15, 0.15, 0.0, 0.0])
    type(fake_levels).mic = property(lambda self: next(mic_iter))

    # Ticks at 1001, 1002, 1003, 1004, 1005 — silence elapsed 1005-1004 = 1.0s > 0.6s
    time_iter = iter([1001.0, 1002.0, 1003.0, 1004.0, 1005.0])
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=lambda: next(time_iter))

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(6, stop_event)  # 1 warmup + 5 ticks

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

    try:
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
            )
        )

        detect_calls = fake_event_detector.detect.call_args_list
        assert len(detect_calls) == 5, f"expected 5 detect calls, got {len(detect_calls)}"

        # First 4 ticks: kaan_just_spoke=False
        for i, call in enumerate(detect_calls[:-1]):
            assert call.kwargs.get("kaan_just_spoke") is False, (
                f"tick {i + 1} expected False, got {call.kwargs}"
            )
        # 5th tick: kaan_just_spoke=True
        assert detect_calls[-1].kwargs.get("kaan_just_spoke") is True

        # last_kaan_spoke_at was updated to the last active-frame time (1003.0)
        assert music_state.last_kaan_spoke_at == 1003.0
    finally:
        del type(fake_levels).mic


# ---------------------------------------------------------------------------
# COACH-09 — mic active < 3 frames does NOT fire KAAN_SPOKE
# ---------------------------------------------------------------------------


def test_coach_09_mic_under_3_frames_no_kaan_spoke(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """COACH-09: only 2 frames above threshold then mic drops → no
    kaan_just_spoke=True ever passed to detect."""
    fake_levels.voice = 0.0

    mic_iter = iter([0.15, 0.15, 0.0, 0.0])
    type(fake_levels).mic = property(lambda self: next(mic_iter))

    time_iter = iter([1001.0, 1002.0, 1003.0, 1005.0])
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=lambda: next(time_iter))

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(5, stop_event)  # 1 warmup + 4 ticks

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

    try:
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
            )
        )

        detect_calls = fake_event_detector.detect.call_args_list
        for i, call in enumerate(detect_calls):
            assert call.kwargs.get("kaan_just_spoke") is False, (
                f"tick {i + 1} expected False, got {call.kwargs}"
            )
    finally:
        del type(fake_levels).mic


# ---------------------------------------------------------------------------
# COACH-10 — manual trigger
# ---------------------------------------------------------------------------


def test_coach_10_manual_trigger(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """COACH-10: manual_trigger.set() then run one tick → manual=True is
    passed to detect AND manual_trigger is cleared after."""
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)  # 1 warmup + 1 tick

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    manual_trigger = asyncio.Event()
    manual_trigger.set()
    trigger_state = {"in_flight": False}

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
        )
    )

    assert fake_event_detector.detect.call_count == 1
    assert fake_event_detector.detect.call_args.kwargs.get("manual") is True
    assert not manual_trigger.is_set()


# ---------------------------------------------------------------------------
# COACH-11 — timeout doesn't crash loop
# ---------------------------------------------------------------------------


def test_coach_11_timeout_doesnt_crash_loop(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_event,
):
    """COACH-11: asyncio.wait_for raises TimeoutError on first event fire →
    loop catches, clears in_flight, continues. Next tick proceeds normally."""
    fake_event_detector.detect.return_value = fake_event

    call_count = {"n": 0}

    async def fake_wait_for(coro, timeout):
        # Always close the coroutine to avoid resource warnings
        try:
            coro.close()
        except Exception:
            pass
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise TimeoutError
        return None

    mocker.patch("vibemix.runtime.coach.asyncio.wait_for", side_effect=fake_wait_for)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(3, stop_event)  # 1 warmup + 2 ticks (both fire)

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

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
        )
    )

    assert fake_session.generate_reply.call_count == 2
    assert trigger_state["in_flight"] is False


# ---------------------------------------------------------------------------
# COACH-12 — exception in fire path doesn't crash loop
# ---------------------------------------------------------------------------


def test_coach_12_exception_doesnt_crash_loop(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_event,
):
    """COACH-12: session.generate_reply raises RuntimeError → loop catches,
    clears in_flight, continues. Next tick proceeds normally."""
    fake_event_detector.detect.return_value = fake_event

    call_count = {"n": 0}

    def gen_reply_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("boom")
        h = MagicMock()
        h.wait_for_playout = AsyncMock(return_value=None)
        return h

    fake_session.generate_reply.side_effect = gen_reply_side_effect

    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(3, stop_event)  # 1 warmup + 2 ticks

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

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
        )
    )

    assert fake_session.generate_reply.call_count == 2
    assert trigger_state["in_flight"] is False


# ---------------------------------------------------------------------------
# COACH-13 — stop_event exits cleanly
# ---------------------------------------------------------------------------


def test_coach_13_stop_event_exits_cleanly(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """COACH-13: stop_event.set() causes the loop to exit cleanly on the
    next iteration boundary with no in_flight leak."""
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(4, stop_event)  # 1 warmup + 3 ticks

    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    manual_trigger = asyncio.Event()
    trigger_state = {"in_flight": False}

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
        )
    )

    assert trigger_state["in_flight"] is False


# ---------------------------------------------------------------------------
# CONST-WS-01 — WS_HOST / WS_PORT centralized
# ---------------------------------------------------------------------------


def test_const_ws_01_ws_host_and_port_in_vibemix_audio() -> None:
    """CONST-WS-01: WS_HOST/WS_PORT are exported from vibemix.audio (and
    via vibemix.audio.constants). v4:123-124 values preserved."""
    from vibemix.audio import WS_HOST, WS_PORT
    from vibemix.audio.constants import WS_HOST as ch_host
    from vibemix.audio.constants import WS_PORT as ch_port

    assert WS_HOST == "127.0.0.1"
    assert WS_PORT == 8765
    assert WS_HOST == ch_host
    assert WS_PORT == ch_port
