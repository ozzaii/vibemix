# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.runtime.speak_gate import decide_speak_gate
from vibemix.state import Event, MusicState


def _event(event_type: str, extra: dict | None = None) -> Event:
    return Event(event_type, MusicState(), extra=extra or {})


def test_plain_heartbeat_stays_silent_by_default() -> None:
    decision = decide_speak_gate(_event("HEARTBEAT"))

    assert decision.verdict == "silent"
    assert decision.reason == "heartbeat_describe_bank_only"


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
    assert decision.reason == "heartbeat_grounded_voice_payload"


def test_structural_events_keep_existing_speech_path() -> None:
    decision = decide_speak_gate(_event("MIX_MOVE", {"moves": ["eq_low:A"]}))

    assert decision.verdict == "speak"
    assert decision.reason == "event_priority"
