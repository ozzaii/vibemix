# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.runtime.speak_gate import (
    decide_speak_gate,
    event_speak_fingerprint,
    interruption_worthiness,
)
from vibemix.state import Event, MusicState


def _event(
    event_type: str,
    extra: dict | None = None,
    *,
    bands: dict[str, float] | None = None,
    state_values: dict[str, object] | None = None,
) -> Event:
    state = MusicState()
    if bands is not None:
        state.bands = bands
    for key, value in (state_values or {}).items():
        setattr(state, key, value)
    return Event(event_type, state, extra=extra or {})


def test_plain_heartbeat_stays_silent_by_default() -> None:
    decision = decide_speak_gate(_event("HEARTBEAT"))

    assert decision.verdict == "silent"
    assert decision.reason == "describe_bank_only"


def test_plain_phase_stays_silent_by_default() -> None:
    decision = decide_speak_gate(_event("PHASE", {"prev_phase": "build", "new_phase": "low"}))

    assert decision.verdict == "silent"
    assert decision.reason == "describe_bank_only"


def test_plain_layer_arrival_stays_silent_by_default() -> None:
    decision = decide_speak_gate(_event("LAYER_ARRIVAL", {"band": "high"}))

    assert decision.verdict == "silent"
    assert decision.reason == "describe_bank_only"


def test_manual_heartbeat_reaches_sven() -> None:
    decision = decide_speak_gate(_event("HEARTBEAT"), manual=True)

    assert decision.verdict == "speak"
    assert decision.reason == "human_or_manual"


def test_kaan_spoke_heartbeat_reaches_sven() -> None:
    decision = decide_speak_gate(_event("HEARTBEAT"), kaan_just_spoke=True)

    assert decision.verdict == "speak"
    assert decision.reason == "human_or_manual"


def test_grounded_heartbeat_payload_still_needs_interruption_worthiness() -> None:
    decision = decide_speak_gate(
        _event("HEARTBEAT", {"set_progress_voice_line": "[mix:set_progress=next]"}),
    )

    assert decision.verdict == "silent"
    assert decision.reason == "below_worthiness"
    assert decision.worthiness is not None
    assert decision.worthiness < 0.38


def test_grounded_heartbeat_payload_reaches_sven_when_audio_builds() -> None:
    decision = decide_speak_gate(
        _event(
            "HEARTBEAT",
            {"set_progress_voice_line": "[mix:set_progress=next]"},
            state_values={"audible": True, "rms": 0.12, "buildup_score": 0.85},
        ),
    )

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"
    assert decision.worthiness is not None
    assert decision.worthiness >= 0.38


def test_energy_read_heartbeat_payload_reaches_sven() -> None:
    decision = decide_speak_gate(
        _event(
            "HEARTBEAT",
            {"energy_read_voice_line": "[energy:master_read=audio_build_4]"},
            state_values={
                "audible": True,
                "rms": 0.12,
                "buildup_score": 0.50,
                "audio_delta": ["master energy rose 42%"],
            },
        ),
    )

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"


def test_grounded_phase_payload_reaches_sven() -> None:
    decision = decide_speak_gate(
        _event(
            "PHASE",
            {
                "prev_phase": "groove",
                "new_phase": "build",
                "judge_evidence_line": "[judge:transition=clean]",
            },
            state_values={"audible": True, "rms": 0.12},
        ),
    )

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"


def test_structural_events_keep_existing_speech_path() -> None:
    decision = decide_speak_gate(
        _event(
            "MIX_MOVE",
            {"moves": ["eq_low:A"]},
            state_values={"audible": True, "rms": 0.12},
        )
    )

    assert decision.verdict == "speak"
    assert decision.reason == "event_priority"


def test_priority_event_in_dead_air_holds_below_floor() -> None:
    decision = decide_speak_gate(_event("MIX_MOVE", {"moves": ["eq_low:A"]}))

    assert decision.verdict == "hold"
    assert decision.reason == "priority_below_floor"
    assert decision.worthiness is not None
    assert decision.worthiness < 0.24


def test_priority_event_without_detector_payload_holds() -> None:
    for event_type in ("KICK_SWAP", "KICK_DENSITY_SHIFT"):
        decision = decide_speak_gate(_event(event_type))

        assert decision.verdict == "hold"
        assert decision.reason == "priority_missing_payload"


def test_priority_event_with_detector_payload_reaches_sven() -> None:
    kick_swap = decide_speak_gate(
        _event(
            "KICK_SWAP",
            {"prev_centroid_hz": 120.0, "new_centroid_hz": 180.0, "delta_hz": 60.0},
        )
    )
    density = decide_speak_gate(
        _event("KICK_DENSITY_SHIFT", {"prev_density": 6.0, "new_density": 4.5, "delta": -1.5})
    )

    assert kick_swap.verdict == "speak"
    assert kick_swap.reason == "event_priority"
    assert density.verdict == "speak"
    assert density.reason == "event_priority"


def test_plain_track_change_stays_silent_by_default() -> None:
    decision = decide_speak_gate(_event("TRACK_CHANGE", {"new_track": "B"}))

    assert decision.verdict == "silent"
    assert decision.reason == "describe_bank_only"


def test_grounded_track_change_payload_reaches_sven() -> None:
    decision = decide_speak_gate(
        _event(
            "TRACK_CHANGE",
            {"next_suggestion_voice_line": "[track:track-42] [mix:next_suggestion=track-42]"},
        ),
    )

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"


def test_repeat_of_recent_phase_stays_silent() -> None:
    ev = _event(
        "PHASE",
        {
            "prev_phase": "groove",
            "new_phase": "build",
            "judge_evidence_line": "[judge:transition=clean]",
        },
        bands={"sub": 0.26, "low": 0.31, "mid": 0.22, "high": 0.11},
        state_values={"audible": True, "rms": 0.12},
    )
    fingerprint = event_speak_fingerprint(ev)

    decision = decide_speak_gate(ev, recent_fingerprints=(fingerprint,))

    assert decision.verdict == "silent"
    assert decision.reason == "repeat_of_recent"


def test_novel_phase_with_fresh_band_still_speaks() -> None:
    old = _event(
        "PHASE",
        {
            "prev_phase": "groove",
            "new_phase": "build",
            "judge_evidence_line": "[judge:transition=clean]",
        },
        bands={"sub": 0.2, "low": 0.2, "mid": 0.2, "high": 0.2},
        state_values={"audible": True, "rms": 0.12},
    )
    new = _event(
        "PHASE",
        {
            "prev_phase": "groove",
            "new_phase": "build",
            "judge_evidence_line": "[judge:transition=clean]",
        },
        bands={"sub": 0.6, "low": 0.2, "mid": 0.2, "high": 0.2},
        state_values={"audible": True, "rms": 0.12},
    )

    decision = decide_speak_gate(new, recent_fingerprints=(event_speak_fingerprint(old),))

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"


def test_empty_recent_fingerprints_preserves_default_gate() -> None:
    decision = decide_speak_gate(
        _event("PHASE", {"new_phase": "build"}),
        recent_fingerprints=(),
    )

    assert decision.verdict == "silent"
    assert decision.reason == "describe_bank_only"


def test_manual_overrides_repeat() -> None:
    ev = _event(
        "PHASE",
        {"new_phase": "build", "judge_evidence_line": "[judge:transition=clean]"},
    )
    fingerprint = event_speak_fingerprint(ev)

    decision = decide_speak_gate(ev, manual=True, recent_fingerprints=(fingerprint,))

    assert decision.verdict == "speak"
    assert decision.reason == "human_or_manual"


def test_track_change_does_not_dedup_against_phase() -> None:
    phase = _event("PHASE", {"new_phase": "build"})
    track_change = _event("TRACK_CHANGE", {"new_track": "Next"})

    assert event_speak_fingerprint(phase) != event_speak_fingerprint(track_change)


def test_interruption_worthiness_rewards_real_heartbeat_audio_trajectory() -> None:
    steady = _event(
        "HEARTBEAT",
        state_values={"audible": True, "rms": 0.12, "buildup_score": 0.0},
    )
    building = _event(
        "HEARTBEAT",
        state_values={"audible": True, "rms": 0.12, "buildup_score": 0.85},
    )

    assert interruption_worthiness(steady) < 0.38
    assert interruption_worthiness(building) >= 0.38


def test_interruption_worthiness_penalizes_recent_speech() -> None:
    ev = _event(
        "HEARTBEAT",
        state_values={
            "audible": True,
            "rms": 0.12,
            "buildup_score": 0.85,
            "last_kaan_spoke_at": 100.0,
        },
    )

    assert interruption_worthiness(ev, now_s=104.0) < interruption_worthiness(ev, now_s=140.0)
