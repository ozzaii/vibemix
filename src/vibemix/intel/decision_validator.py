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
        errors.extend(_selected_claim_alignment_errors(envelope, selected, decision))
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


def _selected_claim_alignment_errors(
    envelope: AgentContextEnvelope,
    selected: dict,
    decision: AgentDecision,
) -> tuple[str, ...]:
    claim_map = {
        str(row.get("claim_id")): row for row in envelope.claim_summary if isinstance(row, dict)
    }
    support = _selected_support(selected, envelope)
    errors: list[str] = []
    for claim_id in decision.cited_claim_ids:
        row = claim_map.get(claim_id)
        if row is None:
            continue
        expected_subjects = _expected_subjects_for_selected_claim(str(row.get("type")), support)
        if expected_subjects is None:
            continue
        if str(row.get("subject_id")) not in expected_subjects:
            errors.append(f"claim_subject_mismatch:{claim_id}:{row.get('type')}")
    return tuple(errors)


def _expected_subjects_for_selected_claim(
    claim_type: str,
    support: dict[str, frozenset[str]],
) -> frozenset[str] | None:
    if claim_type == "track_identity":
        return support["target_tracks"]
    if claim_type in {
        "transition_fit",
        "semantic_match",
        "energy_shape",
        "density_match",
        "phrase_fit",
        "harmonic_fit",
        "tempo_fit",
        "vocal_risk",
        "cue_slot",
        "cue_role",
        "cue_export_status",
        "cue_overwrite_safety",
        "cue_operability",
        "taste_fit",
        "taste_uncertain",
        "move_grade",
    }:
        return support["candidate"]
    if claim_type in {"section_role", "section_boundary"}:
        return support["sections"]
    if claim_type == "bars_until_event":
        return support["candidate"] | support["sections"] | support["source_subjects"]
    if claim_type == "current_position":
        return support["source_subjects"]
    if claim_type in {"risk", "uncertainty", "blend_suppression"}:
        return (
            support["candidate"]
            | support["sections"]
            | support["source_subjects"]
            | support["target_tracks"]
        )
    return None


def _selected_support(selected: dict, envelope: AgentContextEnvelope) -> dict[str, frozenset[str]]:
    candidate_id = _nonempty_str(selected.get("candidate_id"))
    from_track_id = _nonempty_str(selected.get("from_track_id"))
    to_track_id = _nonempty_str(selected.get("to_track_id"))
    sections = frozenset(
        item
        for item in (
            _nonempty_str(selected.get("from_section_id")),
            _nonempty_str(selected.get("to_section_id")),
        )
        if item is not None
    )
    source_subjects = frozenset(
        item
        for item in (
            "source",
            from_track_id,
            _nonempty_str(envelope.current.get("track_id")),
            _nonempty_str(envelope.current.get("active_track_id")),
            *_source_context_subjects(envelope.current),
        )
        if item is not None
    )
    return {
        "candidate": frozenset({candidate_id}) if candidate_id is not None else frozenset(),
        "target_tracks": frozenset({to_track_id}) if to_track_id is not None else frozenset(),
        "sections": sections,
        "source_subjects": source_subjects,
    }


def _source_context_subjects(current: dict) -> tuple[str, ...]:
    source_context = current.get("source_context")
    if not isinstance(source_context, dict):
        return ()
    subjects: list[str] = []
    track_id = _nonempty_str(source_context.get("track_id"))
    if track_id is not None:
        subjects.append(track_id)
    for key in ("current_section", "next_section"):
        section = source_context.get(key)
        if not isinstance(section, dict):
            continue
        section_id = _nonempty_str(section.get("section_id"))
        section_track_id = _nonempty_str(section.get("track_id"))
        if section_id is not None:
            subjects.append(section_id)
        if section_track_id is not None:
            subjects.append(section_track_id)
    return tuple(dict.fromkeys(subjects))


def _nonempty_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


__all__ = ["ValidationResult", "ValidationStatus", "validate_agent_decision"]
