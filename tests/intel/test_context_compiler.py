# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from vibemix.intel.context_compiler import compile_transition_context
from vibemix.intel.transition_scorer import (
    LivePosition,
    SectionRecord,
    TransitionScoringInput,
    score_transition_slate,
)


def _section(section_id: str, track_id: str, role: str, cue_slot: str = "A") -> SectionRecord:
    return SectionRecord(
        section_id=section_id,
        track_id=track_id,
        role=role,
        confidence=0.9,
        start_s=0.0,
        end_s=64.0,
        start_beat=0,
        bar_count=32,
        bpm=128.0,
        camelot="8A",
        energy_mean=50.0,
        cue_slot=cue_slot,
        cue_source="dj",
    )


def test_compile_transition_context_bounds_and_redacts_live_packet() -> None:
    source = _section("t1#s000", "t1", "outro", "F")
    destinations = tuple(_section(f"t{i}#s000", f"t{i}", "intro") for i in range(2, 9))
    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=destinations,
            mode="live",
            live_position=LivePosition(remaining_bars=16, playhead_confidence=0.95),
        ),
        max_candidates=7,
    )

    envelope = compile_transition_context(
        packet_id="ctx_001",
        mode="live",
        intent="live_next_pill",
        current={
            "active_track_id": "t1",
            "filepath": "/Users/ozai/Music/private.wav",
            "vector": [1.0, 0.0],
        },
        candidates=slate,
    )

    assert envelope.schema_version == "intel_context_v1"
    assert len(envelope.candidates) == 5
    assert envelope.allowed_actions == ("select", "hold", "suppress")
    assert "filepath" not in envelope.current
    assert "vector" not in envelope.current
    assert envelope.constraints["raw_vectors_included"] is False
    assert envelope.constraints["strict_claim_validation"] is True
    assert envelope.citation_scope["candidate"] == tuple(
        candidate["candidate_id"] for candidate in envelope.candidates
    )
    assert envelope.citation_scope["claim"] == envelope.claim_ids


def test_compile_transition_context_exposes_score_components_without_vectors() -> None:
    source = _section("t1#s000", "t1", "outro", "F")
    destination = _section("t2#s000", "t2", "intro", "A")
    slate = score_transition_slate(
        TransitionScoringInput(source=source, destinations=(destination,))
    )

    envelope = compile_transition_context(
        packet_id="ctx_001",
        mode="prep",
        intent="transition_slate",
        current={"active_track_id": "t1"},
        candidates=slate,
    )

    candidate = envelope.candidates[0]
    assert candidate["candidate_id"] == "tr_001"
    assert candidate["recommended_cue_slot"] == "A"
    assert "semantic" in candidate["scores"]
    assert "vector" not in candidate
    assert envelope.allowed_actions == ("select", "hold", "suppress", "ask")
    assert {claim["type"] for claim in envelope.claim_summary} >= {
        "transition_fit",
        "section_role",
        "harmonic_fit",
        "tempo_fit",
        "cue_slot",
    }


def test_compile_transition_context_blocks_exact_timing_when_slate_has_none() -> None:
    source = _section("t1#s000", "t1", "outro", "F")
    destination = _section("t2#s000", "t2", "intro", "A")
    slate = score_transition_slate(
        TransitionScoringInput(source=source, destinations=(destination,), mode="prep")
    )

    envelope = compile_transition_context(
        packet_id="ctx_001",
        mode="prep",
        intent="transition_slate",
        current={},
        candidates=slate,
    )

    assert envelope.constraints["exact_timing_allowed"] is False
    assert envelope.confidence_policy["exact_timing_allowed"] is False
    assert "bars_until_event" not in {claim["type"] for claim in envelope.claim_summary}
