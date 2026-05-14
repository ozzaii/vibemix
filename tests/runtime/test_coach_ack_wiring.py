# SPDX-License-Identifier: Apache-2.0
"""coach_loop ack-fire wiring — Plan 19-05 Task 3.

When ``ack_bank``, ``cancel_gate``, ``ttft_meter`` and ``playback`` are ALL
provided, ``coach_loop`` queries ``ack_bank.should_fire(...)`` BEFORE
``set_next_event``/``generate_reply``. On (True, "fire"), the picked PCM is
pushed straight into ``PlaybackQueue`` (bypassing LiveKit TTS per
LATENCY-01) and ``recorder.log_event("ack_fire", ...)`` is emitted.

When any of those four kwargs is None, the legacy path runs verbatim with
``allow_interruptions=False`` so the byte-identical Phase 4 contract holds.
"""

from __future__ import annotations

import asyncio

from vibemix.runtime.coach import coach_loop


# Capture the real asyncio.sleep BEFORE any test patches it.
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


def test_should_fire_true_pushes_pcm_and_logs_ack_fire(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_event,
    fake_ack_bank,
    fake_cancel_gate,
    fake_ttft_meter,
    fake_playback,
):
    """Plan 19-05: should_fire returns (True, 'fire') → ack PCM pushed into
    playback + recorder logs ack_fire event with bucket+sample_index+reason."""
    fake_event_detector.detect.return_value = fake_event
    fake_ack_bank.should_fire.return_value = (True, "fire")

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
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
            ack_bank=fake_ack_bank,
            cancel_gate=fake_cancel_gate,
            ttft_meter=fake_ttft_meter,
            playback=fake_playback,
        )
    )

    fake_ack_bank.should_fire.assert_called_once()
    fake_ack_bank.pick_for_event.assert_called_once_with(fake_event)
    assert fake_playback.push.call_count == 1
    pushed = fake_playback.push.call_args.args[0]
    assert isinstance(pushed, bytes)
    assert len(pushed) > 0  # 2400 int16 samples = 4800 bytes
    fake_recorder.log_event.assert_any_call(
        "ack_fire", bucket="drop_hit", sample_index=0, reason="fire"
    )


def test_should_fire_false_does_not_push(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_event,
    fake_ack_bank,
    fake_cancel_gate,
    fake_ttft_meter,
    fake_playback,
):
    """Plan 19-05: should_fire returns (False, 'ttft_ok') → playback NOT
    called and no ack_fire log event."""
    fake_event_detector.detect.return_value = fake_event
    fake_ack_bank.should_fire.return_value = (False, "ttft_ok")

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
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
            ack_bank=fake_ack_bank,
            cancel_gate=fake_cancel_gate,
            ttft_meter=fake_ttft_meter,
            playback=fake_playback,
        )
    )

    fake_ack_bank.should_fire.assert_called_once()
    fake_ack_bank.pick_for_event.assert_not_called()
    fake_playback.push.assert_not_called()
    # No ack_fire emission.
    ack_fire_calls = [
        c for c in fake_recorder.log_event.call_args_list if c.args and c.args[0] == "ack_fire"
    ]
    assert ack_fire_calls == []


def test_cancel_cooldown_active_passed_to_should_fire(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_event,
    fake_ack_bank,
    fake_cancel_gate,
    fake_ttft_meter,
    fake_playback,
):
    """Plan 19-05: when cancel_gate.last_cancel_at is recent (<8s) the
    cancel_cooldown_active=True flag is passed to should_fire."""
    fake_event_detector.detect.return_value = fake_event
    fake_ack_bank.should_fire.return_value = (False, "cancel_cooldown")

    # last_cancel_at very close to current monotonic — cooldown active.
    import time as _t

    fake_cancel_gate.last_cancel_at = _t.monotonic() - 3.0

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
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
            ack_bank=fake_ack_bank,
            cancel_gate=fake_cancel_gate,
            ttft_meter=fake_ttft_meter,
            playback=fake_playback,
        )
    )

    fake_ack_bank.should_fire.assert_called_once()
    call = fake_ack_bank.should_fire.call_args
    assert call.kwargs.get("cancel_cooldown_active") is True


def test_cancel_cooldown_inactive_passed_to_should_fire(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_event,
    fake_ack_bank,
    fake_cancel_gate,
    fake_ttft_meter,
    fake_playback,
):
    """Plan 19-05: when cancel_gate.last_cancel_at == 0.0, cancel_cooldown_active=False."""
    fake_event_detector.detect.return_value = fake_event
    fake_ack_bank.should_fire.return_value = (False, "ttft_ok")
    fake_cancel_gate.last_cancel_at = 0.0

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
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
            ack_bank=fake_ack_bank,
            cancel_gate=fake_cancel_gate,
            ttft_meter=fake_ttft_meter,
            playback=fake_playback,
        )
    )

    call = fake_ack_bank.should_fire.call_args
    assert call.kwargs.get("cancel_cooldown_active") is False


def test_ack_fire_updates_last_ack_at(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_event,
    fake_ack_bank,
    fake_cancel_gate,
    fake_ttft_meter,
    fake_playback,
):
    """Plan 19-05: on ack fire, trigger_state['last_ack_at'] is updated to
    a monotonic timestamp so the next should_fire call respects the
    min-gap-to-ack gate."""
    fake_event_detector.detect.return_value = fake_event
    fake_ack_bank.should_fire.return_value = (True, "fire")

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    manual_trigger = asyncio.Event()
    trigger_state: dict = {"in_flight": False}

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
            ack_bank=fake_ack_bank,
            cancel_gate=fake_cancel_gate,
            ttft_meter=fake_ttft_meter,
            playback=fake_playback,
        )
    )

    assert "last_ack_at" in trigger_state
    assert isinstance(trigger_state["last_ack_at"], float)
    assert trigger_state["last_ack_at"] > 0.0


def test_allow_interruptions_true_when_wired(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_event,
    fake_ack_bank,
    fake_cancel_gate,
    fake_ttft_meter,
    fake_playback,
):
    """Plan 19-05: when wired, generate_reply is called with
    allow_interruptions=True so the CancelGate seam can preempt the playout."""
    fake_event_detector.detect.return_value = fake_event

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
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
            ack_bank=fake_ack_bank,
            cancel_gate=fake_cancel_gate,
            ttft_meter=fake_ttft_meter,
            playback=fake_playback,
        )
    )

    fake_session.generate_reply.assert_called_once_with(allow_interruptions=True)


def test_allow_interruptions_false_when_unwired(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
    fake_event,
):
    """Plan 19-05: when ack_bank/cancel_gate/playback are None, the legacy
    code path runs and generate_reply uses allow_interruptions=False
    (byte-identical to Phase 4)."""
    fake_event_detector.detect.return_value = fake_event

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
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

    fake_session.generate_reply.assert_called_once_with(allow_interruptions=False)
