# SPDX-License-Identifier: Apache-2.0

from vibemix.coach.citation_linter import CitationLinter
from vibemix.runtime.set_plan_voice import build_set_progress_voice_line
from vibemix.state import EvidenceRegistry


def _progress() -> dict[str, object]:
    return {
        "pool_name": "Psy Plan [live]",
        "current_track_id": "track-a",
        "current_index": 1,
        "total": 5,
        "next_track_id": "track-b",
        "next_title": "Next Portal | cut",
        "next_artist": "Two",
    }


def test_set_progress_voice_line_registers_track_and_mix_citations() -> None:
    registry = EvidenceRegistry()

    line = build_set_progress_voice_line(
        _progress(),
        event_type="TRACK_CHANGE",
        evidence_registry=registry,
    )

    assert line is not None
    assert "slot 2/5" in line
    assert "Psy Plan (live)" in line
    assert "Next Portal / cut by Two" in line
    assert "[track:track-b]" in line
    assert "[mix:set_progress=track-a->track-b]" in line
    assert "Do not say ahead/behind the energy curve" in line

    result = CitationLinter().check(line, registry.snapshot(), mode="live")
    assert result.valid is True
    assert result.reason == "valid"


def test_set_progress_voice_line_abstains_on_uncitable_or_non_voice_context() -> None:
    registry = EvidenceRegistry()

    assert (
        build_set_progress_voice_line(
            {**_progress(), "next_track_id": "bad id with spaces"},
            event_type="TRACK_CHANGE",
            evidence_registry=registry,
        )
        is None
    )
    assert (
        build_set_progress_voice_line(
            _progress(),
            event_type="HEARTBEAT",
            evidence_registry=registry,
        )
        is None
    )
    assert registry.snapshot() == {}
