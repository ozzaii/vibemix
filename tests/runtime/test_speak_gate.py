# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.runtime.speak_gate import decide_speak_gate
from vibemix.state import Event, MusicState


def _event(event_type: str, extra: dict | None = None) -> Event:
    return Event(event_type, MusicState(), extra=extra or {})


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
