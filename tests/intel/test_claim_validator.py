# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from typing import Any

from vibemix.intel.agent_contract import AgentContextEnvelope, AgentDecision
from vibemix.intel.claim_validator import validate_decision_claims


def _envelope(*, claim_summary: tuple[dict, ...]) -> AgentContextEnvelope:  # type: ignore[type-arg]
    return AgentContextEnvelope(
        schema_version="intel_context_v1",
        packet_id="ctx_001",
        mode="prep",
        intent="chat",
        current={},
        candidates=(),
        constraints={"strict_claim_validation": True},
        allowed_actions=("select", "hold", "suppress", "ask"),
        allowed_claims=(),
        forbidden_claims=(),
        citation_scope={"claim": tuple(str(row["claim_id"]) for row in claim_summary)},
        confidence_policy={},
        claim_ids=tuple(str(row["claim_id"]) for row in claim_summary),
        claim_summary=claim_summary,
    )


def _claim(
    claim_id: str,
    claim_type: str,
    *,
    value: Any = "ok",
    forbidden: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "type": claim_type,
        "subject_id": "tr_001",
        "value": value,
        "unit": None,
        "scope": "transition",
        "confidence": 0.9,
        "status": "allowed",
        "allowed_phrases": (),
        "forbidden_phrases": forbidden,
        "reason_codes": (),
    }


def test_exact_timing_phrase_rejected_without_timing_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "cue_slot"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            spoken_text="Use cue A in 16 bars.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_timing" in result.errors


def test_tempo_phrase_rejected_without_bpm_claim() -> None:
    envelope = _envelope(claim_summary=())

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="The tempo is close.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_tempo" in result.errors


def test_texture_phrase_requires_semantic_claim() -> None:
    envelope = _envelope(claim_summary=())

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="The section texture is close.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_semantic" in result.errors


def test_energy_phrase_requires_energy_claim() -> None:
    envelope = _envelope(claim_summary=())

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="The energy shape fits.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_energy" in result.errors


def test_phrase_boundary_copy_requires_phrase_claim() -> None:
    envelope = _envelope(claim_summary=())

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="The entry lands on a phrase boundary.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_phrase" in result.errors


def test_loop_held_copy_requires_risk_claim() -> None:
    envelope = _envelope(claim_summary=())

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="Loop held.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_risk" in result.errors


def test_loop_held_copy_accepts_matching_risk_claim_id() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "risk"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="Loop held.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_stayed_quiet_phrase_requires_suppression_claim() -> None:
    envelope = _envelope(claim_summary=())

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="I stayed quiet because playhead confidence was low.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_suppression" in result.errors


def test_stayed_quiet_phrase_accepts_decision_suppression_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "decision_suppressed"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="I stayed quiet because playhead confidence was low.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_suppressed_timing_phrase_accepts_blend_suppression_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "blend_suppression"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="I suppressed exact timing during the blend.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_section_texture_copy_accepts_matching_claim_id() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "semantic_match"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="The section texture is close.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_exported_phrase_requires_action_success_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "proposal_issued"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="I exported the cue map.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_export" in result.errors


def test_created_playlist_phrase_requires_playlist_success_claim() -> None:
    envelope = _envelope(claim_summary=())

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="I created the playlist.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_playlist" in result.errors


def test_created_playlist_phrase_accepts_playlist_success_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "playlist_created"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="I created the playlist.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_saved_playlist_phrase_requires_export_and_playlist_success_claims() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "playlist_created"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="I saved the playlist.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_export" in result.errors
    assert "missing_claim_id_for_playlist" not in result.errors


def test_export_ready_phrase_requires_cue_export_status_claim() -> None:
    envelope = _envelope(claim_summary=())

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="This map is export-ready.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_cue_export_status" in result.errors


def test_review_only_cue_cannot_be_called_export_ready() -> None:
    envelope = _envelope(
        claim_summary=(_claim("clm_ctx_001_000", "cue_export_status", value="review"),)
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="This map is export-ready.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "cue_export_status_mismatch:clm_ctx_001_000:export_ready" in result.errors


def test_export_ready_copy_accepts_matching_status_claim() -> None:
    envelope = _envelope(
        claim_summary=(_claim("clm_ctx_001_000", "cue_export_status", value="export_ready"),)
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="This map is export-ready.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_review_only_copy_accepts_matching_status_claim() -> None:
    envelope = _envelope(
        claim_summary=(_claim("clm_ctx_001_000", "cue_export_status", value="review"),)
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="This map is review-only.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_forbidden_phrase_rejected_even_when_claim_is_cited() -> None:
    envelope = _envelope(
        claim_summary=(_claim("clm_ctx_001_000", "transition_fit", forbidden=("guaranteed",)),)
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="This is guaranteed.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "forbidden_phrase:clm_ctx_001_000:guaranteed" in result.errors


def test_unknown_claim_id_rejected() -> None:
    envelope = _envelope(claim_summary=())

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="This works.",
            cited_claim_ids=("clm_ctx_001_999",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "unknown_claim_id:clm_ctx_001_999" in result.errors
