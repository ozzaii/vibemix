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
from vibemix.state import Event, EvidenceRegistry

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
    event_payload = fake_recorder.log_event.call_args.kwargs
    assert fake_recorder.log_event.call_args.args == ("event",)
    assert event_payload["type"] == "TRACK_CHANGE"
    assert event_payload["audible"] is True
    assert event_payload["deck"] == "A"
    assert event_payload["track"] == "Some Track"
    assert event_payload["track_conf"] == 0.85
    assert event_payload["phase"] == "peak"
    assert "context_feed_contract[" in event_payload["context_feed_contract"]
    assert "speed=no_extra_model_pass" in event_payload["context_feed_contract"]


def test_coach_event_log_carries_deck_move_audio_context(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    music_state.audible = True
    music_state.audible_deck = "A"
    music_state.phase = "groove"
    music_state.controller_connected = True
    music_state.xfader = 0
    music_state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    music_state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    music_state.recent_moves = [(0.5, "A_low: flat→killed (big twist)")]
    music_state.audio_delta = ["sub energy fell 50% (strong)"]
    ev = Event(
        type="MIX_MOVE",
        state=music_state,
        extra={"moves": ["A_low: flat→killed (big twist)"]},
    )
    audio_capture_context = {
        "deck_channels": {"A": "0,1", "B": "2,3"},
        "deck_audio_capture_enabled": True,
        "deck_audio_rms": {"A": 0.02, "B": 0.0},
        "deck_audio_features": {
            "A": {"activity": "active", "rms": 0.02, "peak": 0.1, "zcr": 0.03},
            "B": {"activity": "silent", "rms": 0.0, "peak": 0.0, "zcr": 0.0},
        },
        "deck_audio_deltas": {
            "A": ["rms_rose_100pct_strong"],
            "B": ["rms_fell_50pct_strong"],
        },
        "deck_audio_windows": {
            "pre_s": [-6.0, -1.0],
            "current_s": [-1.0, 0.0],
            "A": {
                "pre": {"activity": "active", "rms": 0.02, "peak": 0.1, "flux": 0.004},
                "current": {
                    "activity": "active",
                    "rms": 0.04,
                    "peak": 0.12,
                    "flux": 0.009,
                },
                "delta": ["rms_rose_100pct_strong"],
            },
            "B": {
                "pre": {"activity": "active", "rms": 0.03, "peak": 0.11, "flux": 0.006},
                "current": {
                    "activity": "silent",
                    "rms": 0.0,
                    "peak": 0.0,
                    "flux": 0.001,
                },
                "delta": ["rms_fell_50pct_strong"],
            },
        },
    }
    fake_event_detector.detect.return_value = ev

    def _capture_event_at_agent_handoff(sent_ev):
        assert sent_ev.extra["audio_capture_context"] is audio_capture_context

    fake_agent.set_next_event.side_effect = _capture_event_at_agent_handoff

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            asyncio.Event(),
            {"in_flight": False},
            stop_event,
            audio_capture_context=audio_capture_context,
        )
    )

    event_calls = [
        call for call in fake_recorder.log_event.call_args_list if call.args[:1] == ("event",)
    ]
    assert event_calls
    payload = event_calls[-1].kwargs
    assert payload["context_feed_contract"].startswith("context_feed_contract[")
    assert "surface=session_event" in payload["context_feed_contract"]
    assert "history=past_comparison_not_live_proof" in payload["context_feed_contract"]
    assert "cache=static_persona_rules_only" in payload["context_feed_contract"]
    assert "speed=no_extra_model_pass" in payload["context_feed_contract"]
    assert payload["deck_lane_context"].startswith("deck_lanes_context[")
    assert "B(identity=unknown" in payload["deck_lane_context"]
    assert payload["deck_reference_context"].startswith("deck_reference_context[")
    assert "deck1=A" in payload["deck_reference_context"]
    assert "deck2=B" in payload["deck_reference_context"]
    assert "audio=P1_global_mix" in payload["deck_reference_context"]
    assert payload["deck_source_context"].startswith("deck_source_context[")
    assert "second_deck=independent_source_required" in payload["deck_source_context"]
    assert "rule=unresolved_deck_is_not_transition_evidence" in payload["deck_source_context"]
    assert payload["deck_audio_context"].startswith("deck_audio_context[")
    assert payload["deck_audio_separation_context"].startswith(
        "deck_audio_separation_context["
    )
    assert "mode=deck_pair_capture_configured" in payload["deck_audio_separation_context"]
    assert payload["deck_audio_features_context"].startswith("deck_audio_features_context[")
    assert "A_activity=active" in payload["deck_audio_features_context"]
    assert payload["deck_audio_delta_context"].startswith("deck_audio_delta_context[")
    assert "A_delta=rms_rose_100pct_strong" in payload["deck_audio_delta_context"]
    assert payload["deck_audio_window_context"].startswith("deck_audio_window_context[")
    assert "timeline=pre_action_current" in payload["deck_audio_window_context"]
    assert "A_current=active_rms_0.040" in payload["deck_audio_window_context"]
    assert payload["audio_window_context"].startswith("audio_window_context[")
    assert (
        "move_anchor=A_low:_flat_to_killed_big_twist@-0.5s:inside_P1"
        in payload["audio_window_context"]
    )
    assert payload["audio_delta"] == ["sub energy fell 50% (strong)"]
    assert "live_evidence[" in payload["live_evidence_context"]
    assert "mix:deck_audio_support=single_deck_A" in payload["live_evidence_context"]
    assert "mix:deck_audio_capture=A_active+B_silent" in payload["live_evidence_context"]
    assert (
        "mix:deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000"
        in payload["live_evidence_context"]
    )
    assert (
        "mix:deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong"
        in payload["live_evidence_context"]
    )
    assert (
        "mix:deck_audio_window=A_active_pre_0.020_current_0.040+"
        "B_silent_pre_0.030_current_0.000"
        in payload["live_evidence_context"]
    )
    assert ev.extra["audio_capture_context"] is audio_capture_context
    assert "move_context[" in payload["move_context"]
    assert "deck_change_context[" in payload["deck_change_context"]
    assert "move_effect_context[" in payload["move_effect_context"]


def test_coach_hands_grounded_next_suggestion_to_agent(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    class _SuggestionService:
        def maybe_schedule_compute_from_state(self, state):
            return False

        def current_for_state(self, state):
            return {
                "track_id": "track-42",
                "title": "Ananta Gathering",
                "artist": "Crew",
                "why": "similar vibe",
                "transition": {
                    "candidate_id": "tr_001",
                    "source_deck": "A",
                    "target_deck": "B",
                    "from_track_id": "track-11",
                    "to_track_id": "track-42",
                    "from_role": "outro",
                    "to_role": "intro",
                    "from_camelot": "7B",
                    "to_camelot": "8B",
                    "score": 0.83,
                    "confidence": 0.74,
                    "risk_flags": ["timing_low_confidence"],
                    "reasons": ["outro into intro is a strong role pair"],
                },
            }

    ev = Event(type="TRACK_CHANGE", state=music_state, extra={})
    fake_event_detector.detect.return_value = ev
    registry = EvidenceRegistry()

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            asyncio.Event(),
            {"in_flight": False},
            stop_event,
            suggestion_service=_SuggestionService(),
            evidence_registry=registry,
        )
    )

    sent_ev = fake_agent.set_next_event.call_args.args[0]
    line = sent_ev.extra["next_suggestion_voice_line"]
    assert "Ananta Gathering by Crew" in line
    assert "[track:track-42]" in line
    assert "[mix:next_suggestion=track-42]" in line
    assert "[mix:next_suggestion_risk=timing_low_confidence]" in line
    transition_line = sent_ev.extra["transition_verdict_voice_line"]
    assert "10-signal transition scorer" in transition_line
    assert "deck A to deck B" in transition_line
    assert "[track:track-42]" in transition_line
    assert "[mix:transition_verdict=tr_001]" in transition_line
    assert "[mix:transition_risk=timing_low_confidence]" in transition_line
    snapshot = registry.snapshot()
    assert "track-42" in snapshot["track"]
    assert "next_suggestion=track-42" in snapshot["mix"]
    assert "transition_verdict=tr_001" in snapshot["mix"]
    assert "transition_risk=timing_low_confidence" in snapshot["mix"]


def test_coach_hands_grounded_set_progress_to_agent_without_suggestion_service(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    music_state.set_progress = {
        "pool_name": "Psy Plan",
        "current_track_id": "track-a",
        "current_index": 0,
        "total": 4,
        "next_track_id": "track-b",
        "next_title": "Next Portal",
        "next_artist": "Two",
    }
    ev = Event(type="TRACK_CHANGE", state=music_state, extra={})
    fake_event_detector.detect.return_value = ev
    registry = EvidenceRegistry()

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            asyncio.Event(),
            {"in_flight": False},
            stop_event,
            evidence_registry=registry,
        )
    )

    sent_ev = fake_agent.set_next_event.call_args.args[0]
    line = sent_ev.extra["set_progress_voice_line"]
    assert "Saved-set receipt" in line
    assert "slot 1/4" in line
    assert "Next Portal by Two" in line
    assert "[track:track-b]" in line
    assert "[mix:set_progress=track-a->track-b]" in line
    snapshot = registry.snapshot()
    assert "track-b" in snapshot["track"]
    assert "set_progress=track-a->track-b" in snapshot["mix"]


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
# COACH-14 — HEARTBEAT speak gate
# ---------------------------------------------------------------------------


def test_coach_14_plain_heartbeat_stays_silent(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """Plain HEARTBEATs are true-but-low-value describe-bank candidates.

    The runtime should record the suppression and avoid the LLM call entirely.
    """
    fake_event_detector.detect.return_value = Event("HEARTBEAT", music_state, extra={})
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)  # 1 warmup + 1 tick
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            asyncio.Event(),
            {"in_flight": False},
            stop_event,
        )
    )

    assert fake_agent.set_next_event.call_count == 0
    assert fake_session.generate_reply.call_count == 0
    fake_recorder.log_event.assert_called_once_with(
        "speak_gate",
        type="HEARTBEAT",
        verdict="silent",
        reason="heartbeat_describe_bank_only",
        tier="runtime_value_gate",
        schema_version="1",
    )


def test_coach_15_manual_heartbeat_reaches_model(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """Manual trigger stays high priority even if the detector returns HEARTBEAT."""
    ev = Event("HEARTBEAT", music_state, extra={})
    fake_event_detector.detect.return_value = ev
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)  # 1 warmup + 1 tick
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    manual_trigger = asyncio.Event()
    manual_trigger.set()
    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            manual_trigger,
            {"in_flight": False},
            stop_event,
        )
    )

    fake_agent.set_next_event.assert_called_once_with(ev)
    fake_session.generate_reply.assert_called_once_with(allow_interruptions=False)


def test_coach_16_live_credit_refreshes_coaching_aim(
    mocker,
    fake_session,
    fake_agent,
    fake_levels,
    fake_recorder,
    fake_event_detector,
    music_state,
):
    """A cited Learn credit can change the Competent-not-Mastered frontier.

    The runtime asks the agent to rebuild the fixed coach AIM prefix only after
    a real credit, keeping the refresh out of normal non-credit turns.
    """
    ev = Event("MIX_MOVE", music_state, extra={"moves": ["A_low: open->killed"]})
    fake_event_detector.detect.return_value = ev
    learn_progress = object()
    fake_agent.refresh_coaching_aim = AsyncMock(return_value=True)
    mocker.patch("vibemix.runtime.coach._credit_live_skill_demo", return_value=["eq_mixing"])
    mocker.patch("vibemix.runtime.coach._emit_earned_wall_refresh", new=AsyncMock())
    mocker.patch("vibemix.runtime.coach.time.time", side_effect=_auto_time())

    stop_event = asyncio.Event()
    fake_sleep, _ = _make_stop_after(2, stop_event)
    mocker.patch("vibemix.runtime.coach.asyncio.sleep", side_effect=fake_sleep)

    asyncio.run(
        coach_loop(
            fake_session,
            fake_agent,
            music_state,
            fake_levels,
            fake_event_detector,
            fake_recorder,
            asyncio.Event(),
            {"in_flight": False},
            stop_event,
            learn_progress=learn_progress,
        )
    )

    fake_agent.refresh_coaching_aim.assert_awaited_once_with(learn_progress)


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
