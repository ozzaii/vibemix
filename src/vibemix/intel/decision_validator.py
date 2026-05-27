# SPDX-License-Identifier: Apache-2.0
"""Validate agent decisions against an issued musical context envelope."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from vibemix.intel.agent_contract import SCHEMA_VERSION, AgentContextEnvelope, AgentDecision
from vibemix.intel.claim_validator import validate_decision_claims

ValidationStatus = Literal["accepted", "rejected"]


@dataclass(frozen=True, slots=True)
class ValidationResult:
    status: ValidationStatus
    errors: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"


def validate_agent_decision(
    envelope: AgentContextEnvelope, decision: AgentDecision
) -> ValidationResult:
    """Accept only decisions that stay inside the issued context packet."""
    errors: list[str] = []
    if decision.schema_version != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if decision.action not in envelope.allowed_actions:
        errors.append("action_not_allowed")

    candidates = {str(candidate["candidate_id"]): candidate for candidate in envelope.candidates}
    selected = None
    if decision.action == "select":
        if not decision.candidate_id:
            errors.append("select_requires_candidate_id")
        else:
            selected = candidates.get(decision.candidate_id)
            if selected is None:
                errors.append("unknown_candidate_id")
    elif decision.candidate_id is not None:
        errors.append("candidate_id_only_allowed_for_select")

    if selected is not None:
        expected_slot = selected.get("recommended_cue_slot")
        if decision.cue_slot != expected_slot:
            errors.append("cue_slot_mismatch")
        if decision.timing_text is not None:
            if not envelope.constraints.get("exact_timing_allowed", False):
                errors.append("timing_not_allowed")
            if selected.get("start_in_bars") is None:
                errors.append("selected_candidate_has_no_exact_timing")
    elif decision.cue_slot is not None:
        errors.append("cue_slot_requires_selected_candidate")

    allowed_claims = set(envelope.allowed_claims)
    for claim in decision.cited_claims:
        if claim not in allowed_claims:
            errors.append(f"unsupported_claim:{claim}")

    claim_result = validate_decision_claims(envelope, decision)
    errors.extend(claim_result.errors)

    if decision.action != "suppress" and not decision.spoken_text.strip():
        errors.append("spoken_text_required")
    if not 0.0 <= decision.confidence <= 1.0:
        errors.append("confidence_out_of_range")

    return ValidationResult("rejected", tuple(errors)) if errors else ValidationResult("accepted")


__all__ = ["ValidationResult", "ValidationStatus", "validate_agent_decision"]
