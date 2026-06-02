# SPDX-License-Identifier: Apache-2.0

from vibemix.coach.citation_linter import CitationLinter
from vibemix.runtime.transition_verdict_voice import build_transition_verdict_voice_line
from vibemix.state import EvidenceRegistry


def _suggestion(**transition_overrides):
    transition = {
        "candidate_id": "tr_001",
        "source_deck": "A",
        "target_deck": "B",
        "from_track_id": "source-1",
        "to_track_id": "target-2",
        "from_role": "outro",
        "to_role": "intro",
        "from_camelot": "7B",
        "to_camelot": "8B",
        "score": 0.84,
        "confidence": 0.74,
        "risk_flags": ["timing_low_confidence"],
        "reasons": [
            "outro into intro is a strong role pair",
            "harmonic move is compatible",
        ],
    }
    transition.update(transition_overrides)
    return {
        "track_id": "target-2",
        "title": "Target",
        "transition": transition,
    }


def test_transition_verdict_voice_line_registers_track_mix_and_risk_citations() -> None:
    registry = EvidenceRegistry()

    line = build_transition_verdict_voice_line(
        _suggestion(),
        event_type="TRANSITION_OPPORTUNITY",
        evidence_registry=registry,
    )

    assert line is not None
    assert "10-signal transition scorer" in line
    assert "deck A to deck B" in line
    assert "outro to intro" in line
    assert "score 0.84" in line
    assert "confidence 0.74" in line
    assert "outro into intro is a strong role pair" in line
    assert "[track:target-2]" in line
    assert "[mix:transition_verdict=tr_001]" in line
    assert "[mix:transition_risk=timing_low_confidence]" in line
    assert "not proof of a fader, EQ, or timing move" in line
    assert "do not invent deck-control causes" in line

    result = CitationLinter().check(line, registry.snapshot(), mode="live")
    assert result.valid is True
    assert result.reason == "valid"


def test_transition_verdict_voice_line_abstains_below_live_confidence_floor() -> None:
    registry = EvidenceRegistry()

    line = build_transition_verdict_voice_line(
        _suggestion(confidence=0.61),
        event_type="TRANSITION_OPPORTUNITY",
        evidence_registry=registry,
    )

    assert line is None
    assert registry.snapshot() == {}


def test_transition_verdict_voice_line_abstains_without_two_deck_context() -> None:
    registry = EvidenceRegistry()

    line = build_transition_verdict_voice_line(
        _suggestion(source_deck=None),
        event_type="TRANSITION_OPPORTUNITY",
        evidence_registry=registry,
    )

    assert line is None
    assert registry.snapshot() == {}


def test_transition_verdict_voice_line_abstains_on_uncitable_candidate_id() -> None:
    registry = EvidenceRegistry()

    line = build_transition_verdict_voice_line(
        _suggestion(candidate_id="bad id"),
        event_type="TRANSITION_OPPORTUNITY",
        evidence_registry=registry,
    )

    assert line is None
    assert registry.snapshot() == {}


def test_transition_verdict_voice_line_only_runs_on_voice_events() -> None:
    registry = EvidenceRegistry()

    line = build_transition_verdict_voice_line(
        _suggestion(),
        event_type="HEARTBEAT",
        evidence_registry=registry,
    )

    assert line is None
    assert registry.snapshot() == {}


def test_transition_verdict_voice_line_abstains_without_transition_payload() -> None:
    registry = EvidenceRegistry()

    line = build_transition_verdict_voice_line(
        {"track_id": "target-2", "title": "Target"},
        event_type="TRACK_CHANGE",
        evidence_registry=registry,
    )

    assert line is None
    assert registry.snapshot() == {}
