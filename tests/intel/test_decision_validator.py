# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from vibemix.intel.agent_contract import AgentDecision
from vibemix.intel.context_compiler import compile_transition_context
from vibemix.intel.decision_validator import validate_agent_decision
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


def _envelope(*, mode: str = "live", exact_timing: bool = True):
    source = _section("t1#s000", "t1", "outro", "F")
    destination = _section("t2#s000", "t2", "intro", "A")
    live_position = (
        LivePosition(remaining_bars=16, playhead_confidence=0.95) if exact_timing else None
    )
    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=(destination,),
            mode=mode,  # type: ignore[arg-type]
            live_position=live_position,
        )
    )
    return compile_transition_context(
        packet_id="ctx_001",
        mode=mode,  # type: ignore[arg-type]
        intent="live_next_pill" if mode == "live" else "transition_slate",
        current={},
        candidates=slate,
    )


def _claim_id(envelope, claim_type: str) -> str:  # type: ignore[no-untyped-def]
    for claim in envelope.claim_summary:
        if claim["type"] == claim_type:
            return str(claim["claim_id"])
    raise AssertionError(f"missing claim type {claim_type}")


def _claim_ids(envelope, claim_type: str) -> tuple[str, ...]:  # type: ignore[no-untyped-def]
    ids = tuple(
        str(claim["claim_id"]) for claim in envelope.claim_summary if claim["type"] == claim_type
    )
    if not ids:
        raise AssertionError(f"missing claim type {claim_type}")
    return ids


def test_validator_accepts_issued_select_decision() -> None:
    envelope = _envelope()
    result = validate_agent_decision(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            candidate_id="tr_001",
            cue_slot="A",
            timing_text="in 16 bars",
            spoken_text="Next good entry: Track B cue A in 16 bars.",
            cited_claims=("transition_role", "cue_operability"),
            cited_claim_ids=(
                _claim_id(envelope, "transition_fit"),
                _claim_id(envelope, "cue_slot"),
                _claim_id(envelope, "bars_until_event"),
            ),
            confidence=0.9,
        ),
    )

    assert result.accepted


def test_validator_accepts_section_role_copy_when_claim_backed() -> None:
    envelope = _envelope()
    result = validate_agent_decision(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            candidate_id="tr_001",
            cue_slot="A",
            spoken_text="Next good entry: cue A, outro into intro.",
            cited_claim_ids=(
                _claim_id(envelope, "cue_slot"),
                *_claim_ids(envelope, "section_role"),
            ),
            confidence=0.9,
        ),
    )

    assert result.accepted


def test_validator_rejects_unknown_candidate_id() -> None:
    envelope = _envelope()
    result = validate_agent_decision(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            candidate_id="tr_999",
            cue_slot="A",
            spoken_text="Take this one.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "unknown_candidate_id" in result.errors


def test_validator_rejects_cue_slot_mismatch() -> None:
    envelope = _envelope()
    result = validate_agent_decision(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            candidate_id="tr_001",
            cue_slot="D",
            spoken_text="Use cue D.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "cue_slot_mismatch" in result.errors


def test_validator_rejects_timing_when_context_forbids_it() -> None:
    envelope = _envelope(mode="prep", exact_timing=False)
    result = validate_agent_decision(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            candidate_id="tr_001",
            cue_slot="A",
            timing_text="in 16 bars",
            spoken_text="Use cue A in 16 bars.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "timing_not_allowed" in result.errors


def test_validator_rejects_ask_in_live_mode() -> None:
    envelope = _envelope(mode="live")
    result = validate_agent_decision(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="ask",
            spoken_text="Do you want a sharper cut?",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "action_not_allowed" in result.errors


def test_validator_rejects_unsupported_claim() -> None:
    envelope = _envelope()
    result = validate_agent_decision(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            candidate_id="tr_001",
            cue_slot="A",
            spoken_text="The crowd will love this.",
            cited_claims=("crowd_reaction",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "unsupported_claim:crowd_reaction" in result.errors


def test_validator_rejects_textual_overclaim_without_claim_id() -> None:
    envelope = _envelope()
    result = validate_agent_decision(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            candidate_id="tr_001",
            cue_slot="A",
            spoken_text="Use cue A in 16 bars.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_cue" in result.errors
    assert "missing_claim_id_for_timing" in result.errors
