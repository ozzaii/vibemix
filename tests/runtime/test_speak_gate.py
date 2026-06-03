# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.runtime.speak_gate import decide_speak_gate, event_speak_fingerprint
from vibemix.state import Event, MusicState


def _event(
    event_type: str,
    extra: dict | None = None,
    *,
    bands: dict[str, float] | None = None,
) -> Event:
    state = MusicState()
    if bands is not None:
        state.bands = bands
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


def test_grounded_heartbeat_payload_reaches_sven() -> None:
    decision = decide_speak_gate(
        _event("HEARTBEAT", {"set_progress_voice_line": "[mix:set_progress=next]"}),
    )

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"


def test_grounded_phase_payload_reaches_sven() -> None:
    decision = decide_speak_gate(
        _event("PHASE", {"judge_evidence_line": "[judge:transition=clean]"}),
    )

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"


def test_structural_events_keep_existing_speech_path() -> None:
    decision = decide_speak_gate(_event("MIX_MOVE", {"moves": ["eq_low:A"]}))

    assert decision.verdict == "speak"
    assert decision.reason == "event_priority"


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
        {"new_phase": "build", "judge_evidence_line": "[judge:transition=clean]"},
        bands={"sub": 0.26, "low": 0.31, "mid": 0.22, "high": 0.11},
    )
    fingerprint = event_speak_fingerprint(ev)

    decision = decide_speak_gate(ev, recent_fingerprints=(fingerprint,))

    assert decision.verdict == "silent"
    assert decision.reason == "repeat_of_recent"


def test_novel_phase_with_fresh_band_still_speaks() -> None:
    old = _event(
        "PHASE",
        {"new_phase": "build", "judge_evidence_line": "[judge:transition=clean]"},
        bands={"sub": 0.2, "low": 0.2, "mid": 0.2, "high": 0.2},
    )
    new = _event(
        "PHASE",
        {"new_phase": "build", "judge_evidence_line": "[judge:transition=clean]"},
        bands={"sub": 0.6, "low": 0.2, "mid": 0.2, "high": 0.2},
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
