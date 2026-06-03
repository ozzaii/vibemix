# SPDX-License-Identifier: Apache-2.0

from vibemix.coach.citation_linter import CitationLinter
from vibemix.runtime.suggestion_voice import build_next_suggestion_voice_line
from vibemix.state import EvidenceRegistry


def test_next_suggestion_voice_line_registers_track_and_mix_citations() -> None:
    registry = EvidenceRegistry()
    suggestion = {
        "track_id": "track-42",
        "title": "Ananta [live] | cut",
        "artist": "Crew",
        "why": "similar vibe",
        "transition": {"risk_flags": ["source_loop_recent"]},
    }

    line = build_next_suggestion_voice_line(
        suggestion,
        event_type="TRACK_CHANGE",
        evidence_registry=registry,
    )

    assert line is not None
    assert "Ananta (live) / cut by Crew" in line
    assert "[track:track-42]" in line
    assert "[mix:next_suggestion=track-42]" in line
    assert "[mix:next_suggestion_risk=source_loop_recent]" in line
    assert "not a proven transition" in line

    result = CitationLinter().check(line, registry.snapshot(), mode="live")
    assert result.valid is True
    assert result.reason == "valid"


def test_next_suggestion_voice_line_registers_section_pairing() -> None:
    registry = EvidenceRegistry()
    suggestion = {
        "track_id": "track-42",
        "title": "Ananta",
        "why": "similar vibe",
        "transition": {"from_role": "breakdown", "to_role": "intro"},
    }

    line = build_next_suggestion_voice_line(
        suggestion,
        event_type="TRANSITION_OPPORTUNITY",
        evidence_registry=registry,
    )

    assert line is not None
    assert "Section pairing: mix out of this breakdown into that intro." in line
    assert "[mix:next_suggestion_section=breakdown_to_intro]" in line
    assert "not a proven transition" in line

    result = CitationLinter().check(line, registry.snapshot(), mode="live")
    assert result.valid is True
    assert result.reason == "valid"


def test_next_suggestion_voice_line_abstains_on_unknown_section_pairing() -> None:
    for transition in (
        {"from_role": "unknown", "to_role": "intro"},
        {"to_role": "intro"},
    ):
        registry = EvidenceRegistry()

        line = build_next_suggestion_voice_line(
            {"track_id": "track-42", "title": "Ananta", "transition": transition},
            event_type="TRACK_CHANGE",
            evidence_registry=registry,
        )

        assert line is not None
        assert "Section pairing" not in line
        assert "next_suggestion_section=" not in line
        assert "next_suggestion_section=unknown_to_intro" not in registry.snapshot().get(
            "mix",
            {},
        )


def test_next_suggestion_voice_line_abstains_on_uncitable_track_id() -> None:
    registry = EvidenceRegistry()

    line = build_next_suggestion_voice_line(
        {"track_id": "bad id with spaces", "title": "Bad"},
        event_type="TRACK_CHANGE",
        evidence_registry=registry,
    )

    assert line is None
    assert registry.snapshot() == {}


def test_next_suggestion_voice_line_only_runs_on_voice_events() -> None:
    registry = EvidenceRegistry()

    line = build_next_suggestion_voice_line(
        {"track_id": "track-42", "title": "Ananta"},
        event_type="HEARTBEAT",
        evidence_registry=registry,
    )

    assert line is None
    assert registry.snapshot() == {}
