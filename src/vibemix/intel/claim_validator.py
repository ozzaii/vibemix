# SPDX-License-Identifier: Apache-2.0
"""Validate model-written musical copy against issued claim summaries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal

from vibemix.intel.agent_contract import AgentContextEnvelope, AgentDecision

ClaimValidationStatus = Literal["accepted", "rejected"]
_TIMESTAMP_TOLERANCE_S = 0.51

_TIMING_RE = re.compile(r"\b(?:in|after)\s+\d+\s+(?:bar|bars|beat|beats|second|seconds)\b", re.I)
_NOW_TIMING_RE = re.compile(
    r"\b(?:press|hit|trigger|fire|drop|start|play|bring|cut|enter|go|launch|take|use|cue)"
    r"\b[^\n.!?]{0,80}\b(?:right\s+now|now)\b"
    r"|\b(?:right\s+now|now)\b[^\n.!?]{0,40}"
    r"\b(?:press|hit|trigger|fire|drop|start|play|bring|cut|enter|go|launch|take|use|cue)\b",
    re.I,
)
_CLOCK_TIMESTAMP_RE = re.compile(
    r"\b(?:at|around|near|from)\s+(?P<minute>\d{1,3}):(?P<second>[0-5]\d)\b", re.I
)
_SECONDS_TIMESTAMP_RE = re.compile(
    r"\b(?:at|around|near|from)\s+"
    r"(?P<seconds>\d+(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds)\b",
    re.I,
)
_TIMESTAMP_RE = re.compile(f"{_CLOCK_TIMESTAMP_RE.pattern}|{_SECONDS_TIMESTAMP_RE.pattern}", re.I)
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
_SUPPRESSION_RE = re.compile(
    r"\b(?:stayed\s+quiet|kept\s+quiet|held\s+back|suppressed|stayed\s+silent)\b",
    re.I,
)
_UNSUPPORTED_MUSICAL_FACT_RE = re.compile(
    r"\b(?:crowd|audience|dancefloor|floor)\s+"
    r"(?:will|is\s+going\s+to|gonna)\s+"
    r"(?:love|go\s+off|explode|respond|react)\b"
    r"|\bguaranteed\b"
    r"|\bperfect\s+(?:mix|transition|fit|key|cue|entry|match)\b"
    r"|\bwill\s+(?:work|hit|land)\s+perfectly\b",
    re.I,
)

_REQUIRED_TYPES: dict[str, frozenset[str]] = {
    "timing": frozenset({"bars_until_event", "current_position"}),
    "now_timing": frozenset({"current_position"}),
    "timestamp": frozenset({"section_boundary", "current_position"}),
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
    "suppression": frozenset({"decision_suppressed", "blend_suppression"}),
    "unsupported_musical_fact": frozenset(),
}
_SUCCESS_CLAIM_VALUES = frozenset(
    {
        "ok",
        "success",
        "succeeded",
        "done",
        "complete",
        "completed",
        "true",
        "written",
        "file_written",
        "created",
        "playlist_created",
        "exported",
        "saved",
    }
)


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
    _validate_action_success_phrases(text, cited_rows, errors)
    _validate_timestamp_phrases(text, cited_rows, errors)

    return (
        ClaimValidationResult("rejected", tuple(errors))
        if errors
        else ClaimValidationResult("accepted")
    )


def _claim_families_implied_by_text(text: str) -> tuple[str, ...]:
    families: list[str] = []
    checks = (
        ("timing", _TIMING_RE),
        ("now_timing", _NOW_TIMING_RE),
        ("timestamp", _TIMESTAMP_RE),
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
        ("suppression", _SUPPRESSION_RE),
        ("unsupported_musical_fact", _UNSUPPORTED_MUSICAL_FACT_RE),
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


def _validate_action_success_phrases(
    text: str,
    cited_rows: list[dict[str, Any]],
    errors: list[str],
) -> None:
    for claim_type, pattern in (
        ("export_result", _EXPORT_RE),
        ("playlist_created", _PLAYLIST_ACTION_RE),
    ):
        if not pattern.search(text):
            continue
        rows = [row for row in cited_rows if row.get("type") == claim_type]
        if not rows or any(_claim_value_is_success(row.get("value")) for row in rows):
            continue
        claim_id = str(rows[0].get("claim_id") or "unknown")
        errors.append(f"action_claim_not_success:{claim_id}:{claim_type}")


def _validate_timestamp_phrases(
    text: str,
    cited_rows: list[dict[str, Any]],
    errors: list[str],
) -> None:
    implied_seconds = _timestamp_seconds_implied_by_text(text)
    if not implied_seconds:
        return
    rows = [
        row for row in cited_rows if row.get("type") in {"section_boundary", "current_position"}
    ]
    if not rows:
        return
    for seconds in implied_seconds:
        if any(_claim_value_matches_seconds(row.get("value"), seconds) for row in rows):
            continue
        claim_id = str(rows[0].get("claim_id") or "unknown")
        errors.append(f"timestamp_claim_value_mismatch:{claim_id}:{_format_seconds(seconds)}")


def _claim_value_is_success(value: Any) -> bool:
    if value is True:
        return True
    if not isinstance(value, str):
        return False
    return value.strip().lower() in _SUCCESS_CLAIM_VALUES


def _timestamp_seconds_implied_by_text(text: str) -> tuple[float, ...]:
    seconds: list[float] = []
    for match in _CLOCK_TIMESTAMP_RE.finditer(text):
        seconds.append(int(match.group("minute")) * 60 + int(match.group("second")))
    for match in _SECONDS_TIMESTAMP_RE.finditer(text):
        seconds.append(float(match.group("seconds")))
    return tuple(dict.fromkeys(seconds))


def _claim_value_matches_seconds(value: Any, seconds: float) -> bool:
    parsed = _claim_value_seconds(value)
    return parsed is not None and abs(parsed - seconds) <= _TIMESTAMP_TOLERANCE_S


def _claim_value_seconds(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        number = float(value)
        return number if isfinite(number) and number >= 0.0 else None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    clock = re.fullmatch(r"(?P<minute>\d{1,3}):(?P<second>[0-5]\d)", stripped)
    if clock is not None:
        return int(clock.group("minute")) * 60 + int(clock.group("second"))
    try:
        number = float(stripped)
    except ValueError:
        return None
    return number if isfinite(number) and number >= 0.0 else None


def _format_seconds(seconds: float) -> str:
    return str(int(seconds)) if seconds.is_integer() else f"{seconds:.3f}".rstrip("0").rstrip(".")


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
