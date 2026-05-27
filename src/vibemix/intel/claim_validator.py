# SPDX-License-Identifier: Apache-2.0
"""Validate model-written musical copy against issued claim summaries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from vibemix.intel.agent_contract import AgentContextEnvelope, AgentDecision

ClaimValidationStatus = Literal["accepted", "rejected"]

_TIMING_RE = re.compile(r"\b(?:in|after)\s+\d+\s+(?:bar|bars|beat|beats|second|seconds)\b", re.I)
_CUE_RE = re.compile(r"\b(?:hot\s+cue|cue\s+[A-H])\b", re.I)
_HARMONIC_RE = re.compile(r"\b(?:key|harmonic|camelot|neighboring?\s+key)\b", re.I)
_TEMPO_RE = re.compile(r"\b(?:bpm|tempo|pitch)\b", re.I)
_STRUCTURE_RE = re.compile(r"\b(?:drop|breakdown|build|outro|intro)\b", re.I)
_SEMANTIC_RE = re.compile(r"\b(?:texture|timbre|sonic|sound(?:s|ed)?\s+close)\b", re.I)
_ENERGY_RE = re.compile(r"\b(?:energy|intensity|energy\s+shape)\b", re.I)
_PHRASE_RE = re.compile(r"\b(?:phrase|downbeat|bar\s+line|boundary)\b", re.I)
_EXPORT_RE = re.compile(r"\b(?:exported|wrote|saved)\b", re.I)
_PLAYLIST_ACTION_RE = re.compile(
    r"\b(?:(?:created|made|built|generated|saved|wrote)\s+(?:the\s+)?"
    r"(?:playlist|m3u|json|set)|(?:playlist|m3u|json)\s+"
    r"(?:created|made|built|generated|saved|written))\b",
    re.I,
)
_EXPORT_READY_RE = re.compile(
    r"\b(?:export[- ]ready|ready\s+to\s+export|safe\s+to\s+export)\b", re.I
)
_REVIEW_ONLY_RE = re.compile(r"\b(?:review[- ]only|needs\s+review|for\s+review)\b", re.I)
_TASTE_RE = re.compile(r"\b(?:you usually|your preference|you like)\b", re.I)
_RISK_RE = re.compile(r"\b(?:loop\s+held|source\s+loop|risk)\b", re.I)

_REQUIRED_TYPES: dict[str, frozenset[str]] = {
    "timing": frozenset({"bars_until_event", "current_position"}),
    "cue": frozenset({"cue_slot", "cue_role", "cue_export_status", "cue_operability"}),
    "harmonic": frozenset({"harmonic_fit"}),
    "tempo": frozenset({"tempo_fit"}),
    "structure": frozenset({"section_role", "section_boundary"}),
    "semantic": frozenset({"semantic_match"}),
    "energy": frozenset({"energy_shape"}),
    "phrase": frozenset({"phrase_fit"}),
    "export": frozenset({"export_result"}),
    "playlist": frozenset({"playlist_created"}),
    "taste": frozenset({"taste_preference", "taste_fit", "taste_uncertain"}),
    "risk": frozenset({"risk", "uncertainty"}),
}


@dataclass(frozen=True, slots=True)
class ClaimValidationResult:
    status: ClaimValidationStatus
    errors: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"


def validate_decision_claims(
    envelope: AgentContextEnvelope,
    decision: AgentDecision,
) -> ClaimValidationResult:
    """Reject copy that uses musical phrases without matching issued claim IDs."""
    strict = bool(envelope.constraints.get("strict_claim_validation", False))
    cited_claim_ids = tuple(decision.cited_claim_ids)
    if not strict and not cited_claim_ids:
        return ClaimValidationResult("accepted")

    claim_map = {
        str(row.get("claim_id")): row for row in envelope.claim_summary if isinstance(row, dict)
    }
    issued_ids = set(envelope.claim_ids)
    errors: list[str] = []
    cited_rows: list[dict[str, Any]] = []
    for claim_id in cited_claim_ids:
        if claim_id not in issued_ids or claim_id not in claim_map:
            errors.append(f"unknown_claim_id:{claim_id}")
            continue
        row = claim_map[claim_id]
        if row.get("status") not in {"allowed", "hedged"}:
            errors.append(f"claim_status_not_public:{claim_id}")
            continue
        cited_rows.append(row)

    text = decision.spoken_text or ""
    lower_text = text.lower()
    for row in cited_rows:
        for phrase in row.get("forbidden_phrases", ()):
            if isinstance(phrase, str) and phrase and phrase.lower() in lower_text:
                errors.append(f"forbidden_phrase:{row.get('claim_id')}:{phrase}")

    cited_types = {str(row.get("type")) for row in cited_rows}
    for family in _claim_families_implied_by_text(text):
        if not (_REQUIRED_TYPES[family] & cited_types):
            errors.append(f"missing_claim_id_for_{family}")
    _validate_cue_export_status_phrase(text, cited_rows, errors)

    return (
        ClaimValidationResult("rejected", tuple(errors))
        if errors
        else ClaimValidationResult("accepted")
    )


def _claim_families_implied_by_text(text: str) -> tuple[str, ...]:
    families: list[str] = []
    checks = (
        ("timing", _TIMING_RE),
        ("cue", _CUE_RE),
        ("harmonic", _HARMONIC_RE),
        ("tempo", _TEMPO_RE),
        ("structure", _STRUCTURE_RE),
        ("semantic", _SEMANTIC_RE),
        ("energy", _ENERGY_RE),
        ("phrase", _PHRASE_RE),
        ("export", _EXPORT_RE),
        ("playlist", _PLAYLIST_ACTION_RE),
        ("taste", _TASTE_RE),
        ("risk", _RISK_RE),
    )
    for family, pattern in checks:
        if pattern.search(text):
            families.append(family)
    return tuple(families)


def _validate_cue_export_status_phrase(
    text: str,
    cited_rows: list[dict[str, Any]],
    errors: list[str],
) -> None:
    for expected_status in _cue_export_statuses_implied_by_text(text):
        status_rows = [row for row in cited_rows if row.get("type") == "cue_export_status"]
        if not status_rows:
            errors.append("missing_claim_id_for_cue_export_status")
            continue
        if not any(str(row.get("value")) == expected_status for row in status_rows):
            claim_id = str(status_rows[0].get("claim_id") or "unknown")
            errors.append(f"cue_export_status_mismatch:{claim_id}:{expected_status}")


def _cue_export_statuses_implied_by_text(text: str) -> tuple[str, ...]:
    statuses: list[str] = []
    if _EXPORT_READY_RE.search(text):
        statuses.append("export_ready")
    if _REVIEW_ONLY_RE.search(text):
        statuses.append("review")
    return tuple(dict.fromkeys(statuses))


__all__ = [
    "ClaimValidationResult",
    "ClaimValidationStatus",
    "validate_decision_claims",
]
