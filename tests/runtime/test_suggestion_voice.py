# SPDX-License-Identifier: Apache-2.0

from types import SimpleNamespace

import pytest

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
    assert line.startswith("Forward read: Ananta (live) / cut by Crew pairs next")
    assert "Ananta (live) / cut by Crew" in line
    assert "similar vibe" in line
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
    assert line.startswith("Forward read: Ananta pairs next")
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


def _cue_state(**overrides):
    values = {
        "next_phrase_cue_id": "phrase_boundary@164.0",
        "phrase_position_confidence": 0.7,
        "next_phrase_at": 164.0,
        "set_seconds": 100.0,
        "bpm": 120.0,
        "bpm_confidence": 0.9,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_cue_lookahead_voice_line_registers_citable_phrase_boundary() -> None:
    registry = EvidenceRegistry()

    line = build_next_suggestion_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=registry,
        state=_cue_state(),
    )

    assert line is not None
    assert line.startswith("Forward cue receipt:")
    assert "next citable phrase boundary is about 32 bars ahead" in line
    assert "one forward timing nudge for what comes next" in line
    assert "[cue:phrase_boundary@164.0]" in line
    assert registry.has("cue", "phrase_boundary@164.0", 164.0) is True

    result = CitationLinter().check(line, registry.snapshot(), mode="live")
    assert result.valid is True
    assert result.reason == "valid"


@pytest.mark.parametrize(
    "overrides",
    [
        {"phrase_position_confidence": 0.69},
        {"next_phrase_at": 100.0},
        {"next_phrase_at": 164.1},
        {"next_phrase_cue_id": None},
    ],
)
def test_cue_lookahead_voice_line_abstains_without_grounded_forward_signal(
    overrides,
) -> None:
    registry = EvidenceRegistry()

    line = build_next_suggestion_voice_line(
        None,
        event_type="TRACK_CHANGE",
        evidence_registry=registry,
        state=_cue_state(**overrides),
    )

    assert line is None
    assert registry.snapshot() == {}


def test_cue_lookahead_voice_line_abstains_without_state() -> None:
    registry = EvidenceRegistry()

    line = build_next_suggestion_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=registry,
        state=None,
    )

    assert line is None
    assert registry.snapshot() == {}
