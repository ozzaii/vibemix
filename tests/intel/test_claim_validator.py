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
    status: str = "allowed",
    forbidden: tuple[str, ...] = (),
    reason_codes: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "type": claim_type,
        "subject_id": "tr_001",
        "value": value,
        "unit": None,
        "scope": "transition",
        "confidence": 0.9,
        "status": status,
        "allowed_phrases": (),
        "forbidden_phrases": forbidden,
        "reason_codes": reason_codes,
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


def test_now_cue_call_requires_current_position_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "cue_slot"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="Hit cue A now.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_now_timing" in result.errors


def test_now_cue_call_accepts_current_position_claim() -> None:
    envelope = _envelope(
        claim_summary=(
            _claim("clm_ctx_001_000", "cue_slot"),
            _claim("clm_ctx_001_001", "current_position", value=48.0),
        )
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="Hit cue A now.",
            cited_claim_ids=("clm_ctx_001_000", "clm_ctx_001_001"),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_timing_refusal_right_now_does_not_require_current_position_claim() -> None:
    envelope = _envelope(claim_summary=())

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="I cannot call exact timing right now.",
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_combo_phrase_requires_grade_progress_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "move_grade"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            spoken_text="Next LIT AFF move, combo x3.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_grade_progress" in result.errors


def test_xp_phrase_requires_grade_progress_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "move_grade"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            spoken_text="Next LIT AFF move, +100 xp.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_grade_progress" in result.errors


def test_level_phrase_requires_grade_progress_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "move_grade"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            spoken_text="Next LIT AFF move, lv 2.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_grade_progress" in result.errors


def test_level_up_phrase_requires_grade_progress_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "move_grade"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            spoken_text="Next LIT AFF move, level up.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_grade_progress" in result.errors


def test_combo_phrase_accepts_grade_progress_claim() -> None:
    envelope = _envelope(
        claim_summary=(
            _claim("clm_ctx_001_000", "move_grade"),
            _claim("clm_ctx_001_001", "grade_progress", value=3),
        )
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            spoken_text="Next LIT AFF move, combo x3.",
            cited_claim_ids=("clm_ctx_001_000", "clm_ctx_001_001"),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_xp_phrase_accepts_grade_progress_claim() -> None:
    envelope = _envelope(
        claim_summary=(
            _claim("clm_ctx_001_000", "move_grade"),
            _claim("clm_ctx_001_001", "grade_progress", value=1),
        )
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            spoken_text="Next LIT AFF move, +100 xp.",
            cited_claim_ids=("clm_ctx_001_000", "clm_ctx_001_001"),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_level_phrase_accepts_grade_progress_claim() -> None:
    envelope = _envelope(
        claim_summary=(
            _claim("clm_ctx_001_000", "move_grade"),
            _claim("clm_ctx_001_001", "grade_progress", value=2),
        )
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            spoken_text="Next LIT AFF move, level 2.",
            cited_claim_ids=("clm_ctx_001_000", "clm_ctx_001_001"),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_level_up_phrase_accepts_grade_progress_claim() -> None:
    envelope = _envelope(
        claim_summary=(
            _claim("clm_ctx_001_000", "move_grade"),
            _claim(
                "clm_ctx_001_001",
                "grade_progress",
                value=2,
                reason_codes=("level_up:true",),
            ),
        )
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            spoken_text="Next LIT AFF move, level up.",
            cited_claim_ids=("clm_ctx_001_000", "clm_ctx_001_001"),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_level_up_phrase_rejects_grade_progress_without_level_up_reason() -> None:
    envelope = _envelope(
        claim_summary=(
            _claim("clm_ctx_001_000", "move_grade"),
            _claim("clm_ctx_001_001", "grade_progress", value=2),
        )
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="select",
            spoken_text="Next LIT AFF move, level up.",
            cited_claim_ids=("clm_ctx_001_000", "clm_ctx_001_001"),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "grade_progress_level_up_value_mismatch:clm_ctx_001_001" in result.errors


def test_drop_it_now_is_timing_action_not_section_role_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "current_position", value=48.0),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="Drop it now.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert result.accepted


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


def test_role_specific_copy_requires_matching_section_role_value() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "section_role", value="intro"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="This is the main drop.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "section_role_value_mismatch:clm_ctx_001_000:drop" in result.errors


def test_unhedged_role_copy_rejects_hedged_section_role_claim() -> None:
    envelope = _envelope(
        claim_summary=(_claim("clm_ctx_001_000", "section_role", value="drop", status="hedged"),)
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="This is the main drop.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "section_role_requires_hedged_language:clm_ctx_001_000:drop" in result.errors


def test_hedged_role_copy_accepts_hedged_section_role_claim() -> None:
    envelope = _envelope(
        claim_summary=(_claim("clm_ctx_001_000", "section_role", value="drop", status="hedged"),)
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="Likely drop.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_role_specific_copy_requires_section_role_not_only_boundary() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "section_boundary", value=64.0),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="The drop starts at 1:04.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_section_role:drop" in result.errors


def test_role_specific_copy_accepts_matching_section_roles() -> None:
    envelope = _envelope(
        claim_summary=(
            _claim("clm_ctx_001_000", "section_role", value="outro"),
            _claim("clm_ctx_001_001", "section_role", value="intro"),
        )
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="Outro into intro.",
            cited_claim_ids=("clm_ctx_001_000", "clm_ctx_001_001"),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_cue_timestamp_copy_requires_boundary_or_position_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "cue_slot"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="Use cue A at 3:10.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_timestamp" in result.errors


def test_cue_timestamp_copy_rejects_mismatched_boundary_claim_value() -> None:
    envelope = _envelope(
        claim_summary=(
            _claim("clm_ctx_001_000", "cue_slot"),
            _claim("clm_ctx_001_001", "section_boundary", value=64.0),
        )
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="Use cue A at 3:10.",
            cited_claim_ids=("clm_ctx_001_000", "clm_ctx_001_001"),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "timestamp_claim_value_mismatch:clm_ctx_001_001:190" in result.errors


def test_cue_timestamp_copy_accepts_matching_boundary_claim_value() -> None:
    envelope = _envelope(
        claim_summary=(
            _claim("clm_ctx_001_000", "cue_slot"),
            _claim("clm_ctx_001_001", "section_boundary", value=190.0),
        )
    )

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="Use cue A at 3:10.",
            cited_claim_ids=("clm_ctx_001_000", "clm_ctx_001_001"),
            confidence=0.8,
        ),
    )

    assert result.accepted


def test_seconds_timestamp_copy_accepts_matching_current_position_claim() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "current_position", value=32.2),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="The source position is at 32 seconds.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert result.accepted


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


def test_crowd_prediction_is_rejected_as_unsupported_musical_fact() -> None:
    envelope = _envelope(claim_summary=())

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="The crowd will love this.",
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_unsupported_musical_fact" in result.errors


def test_perfect_transition_claim_is_rejected_as_unsupported_musical_fact() -> None:
    envelope = _envelope(claim_summary=(_claim("clm_ctx_001_000", "transition_fit"),))

    result = validate_decision_claims(
        envelope,
        AgentDecision(
            schema_version="intel_context_v1",
            action="hold",
            spoken_text="This is a perfect transition.",
            cited_claim_ids=("clm_ctx_001_000",),
            confidence=0.8,
        ),
    )

    assert not result.accepted
    assert "missing_claim_id_for_unsupported_musical_fact" in result.errors


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


def test_exported_phrase_rejects_failed_export_result_claim() -> None:
    envelope = _envelope(
        claim_summary=(_claim("clm_ctx_001_000", "export_result", value="failed"),)
    )

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
    assert "action_claim_not_success:clm_ctx_001_000:export_result" in result.errors


def test_exported_phrase_accepts_successful_export_result_claim() -> None:
    envelope = _envelope(
        claim_summary=(_claim("clm_ctx_001_000", "export_result", value="file_written"),)
    )

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

    assert result.accepted


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


def test_created_playlist_phrase_rejects_planned_playlist_claim() -> None:
    envelope = _envelope(
        claim_summary=(_claim("clm_ctx_001_000", "playlist_created", value="planned"),)
    )

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

    assert not result.accepted
    assert "action_claim_not_success:clm_ctx_001_000:playlist_created" in result.errors


def test_created_playlist_phrase_rejects_false_playlist_claim() -> None:
    envelope = _envelope(
        claim_summary=(_claim("clm_ctx_001_000", "playlist_created", value=False),)
    )

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

    assert not result.accepted
    assert "action_claim_not_success:clm_ctx_001_000:playlist_created" in result.errors


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
