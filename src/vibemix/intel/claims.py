# SPDX-License-Identifier: Apache-2.0
"""Typed musical claims for grounded agent decisions.

Deterministic engines create these claims; model-written copy may only select
and paraphrase them. The ledger is packet-scoped and intentionally small enough
to ride inside an ``AgentContextEnvelope`` without leaking paths, vectors, or raw
audio facts.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

MusicClaimType = Literal[
    "track_identity",
    "section_boundary",
    "section_role",
    "cue_slot",
    "cue_role",
    "cue_export_status",
    "cue_overwrite_safety",
    "harmonic_fit",
    "tempo_fit",
    "phrase_fit",
    "cue_operability",
    "energy_shape",
    "density_match",
    "semantic_match",
    "vocal_risk",
    "current_position",
    "bars_until_event",
    "blend_suppression",
    "risk",
    "uncertainty",
    "taste_preference",
    "taste_fit",
    "taste_uncertain",
    "transition_fit",
    "export_result",
    "playlist_created",
    "proposal_issued",
    "decision_suppressed",
]
ClaimScope = Literal[
    "track", "section", "cue", "transition", "live_timing", "taste", "action", "system"
]
ClaimStatus = Literal["allowed", "hedged", "internal_only", "rejected"]
ClaimValue = str | float | int | bool | None


@dataclass(frozen=True, slots=True)
class MusicClaim:
    claim_id: str
    claim_type: MusicClaimType
    subject_id: str
    value: ClaimValue
    unit: str | None
    scope: ClaimScope
    evidence_refs: tuple[str, ...]
    confidence: float
    claim_status: ClaimStatus
    allowed_phrases: tuple[str, ...]
    forbidden_phrases: tuple[str, ...]
    reason_codes: tuple[str, ...]
    provenance_ref: str

    def public_summary(self) -> dict[str, Any]:
        """Return the compact, model-safe representation for a context packet."""
        return {
            "claim_id": self.claim_id,
            "type": self.claim_type,
            "subject_id": self.subject_id,
            "value": self.value,
            "unit": self.unit,
            "scope": self.scope,
            "confidence": self.confidence,
            "status": self.claim_status,
            "allowed_phrases": self.allowed_phrases,
            "forbidden_phrases": self.forbidden_phrases,
            "reason_codes": self.reason_codes,
        }

    def trace_dict(self) -> dict[str, Any]:
        """Return redacted trace data. Evidence refs stay ID-shaped only."""
        data = self.public_summary()
        data["evidence_refs"] = tuple(
            ref for ref in self.evidence_refs if _is_safe_evidence_ref(ref)
        )
        data["provenance_ref"] = self.provenance_ref
        return data


@dataclass(slots=True)
class MusicClaimLedger:
    packet_id: str
    claims: dict[str, MusicClaim] = field(default_factory=dict)
    _next_ordinal: int = 0

    def add(
        self,
        claim_type: MusicClaimType,
        *,
        subject_id: str,
        value: ClaimValue,
        evidence_refs: Sequence[str],
        confidence: float,
        scope: ClaimScope,
        unit: str | None = None,
        claim_status: ClaimStatus | None = None,
        allowed_phrases: Sequence[str] = (),
        forbidden_phrases: Sequence[str] = (),
        reason_codes: Sequence[str] = (),
        provenance_ref: str | None = None,
    ) -> MusicClaim:
        """Append one packet-scoped claim and return it."""
        evidence_tuple = tuple(evidence_refs)
        clean_evidence = tuple(ref for ref in evidence_tuple if _is_safe_evidence_ref(ref))
        clean_confidence, confidence_safe = _clean_confidence(confidence)
        status = claim_status or claim_status_for_confidence(clean_confidence)
        reasons = tuple(reason_codes)
        if len(clean_evidence) != len(evidence_tuple):
            reasons = (*reasons, "redacted_unsafe_evidence_ref")
            status = "rejected"
        if not confidence_safe:
            reasons = (*reasons, "nonfinite_claim_confidence")
            status = "rejected"
        clean_subject, subject_safe = _clean_public_subject(subject_id)
        clean_value, value_safe = _clean_public_value(value)
        clean_allowed, allowed_safe = _clean_phrases(allowed_phrases)
        clean_forbidden, forbidden_safe = _clean_phrases(forbidden_phrases)
        if not (subject_safe and value_safe and allowed_safe and forbidden_safe):
            reasons = (*reasons, "redacted_unsafe_public_payload")
            status = "rejected"
        claim = MusicClaim(
            claim_id=self._next_claim_id(),
            claim_type=claim_type,
            subject_id=clean_subject,
            value=clean_value,
            unit=unit,
            scope=scope,
            evidence_refs=clean_evidence,
            confidence=round(max(0.0, min(1.0, clean_confidence)), 6),
            claim_status=status,
            allowed_phrases=clean_allowed,
            forbidden_phrases=clean_forbidden,
            reason_codes=reasons,
            provenance_ref=provenance_ref or f"packet:{self.packet_id}",
        )
        self.claims[claim.claim_id] = claim
        return claim

    def allowed_for_model(self) -> tuple[MusicClaim, ...]:
        return tuple(
            claim for claim in self.claims.values() if claim.claim_status in {"allowed", "hedged"}
        )

    def claim_ids(self) -> tuple[str, ...]:
        return tuple(claim.claim_id for claim in self.allowed_for_model())

    def claim_summary(self) -> tuple[dict[str, Any], ...]:
        return tuple(claim.public_summary() for claim in self.allowed_for_model())

    def trace(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "claims": tuple(claim.trace_dict() for claim in self.claims.values()),
        }

    def _next_claim_id(self) -> str:
        claim_id = f"clm_{self.packet_id}_{self._next_ordinal:03d}"
        self._next_ordinal += 1
        return claim_id


def claim_status_for_confidence(confidence: float) -> ClaimStatus:
    if confidence >= 0.78:
        return "allowed"
    if confidence >= 0.55:
        return "hedged"
    if confidence >= 0.35:
        return "internal_only"
    return "rejected"


def _clean_confidence(confidence: float) -> tuple[float, bool]:
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return 0.0, False
    if not math.isfinite(value):
        return 0.0, False
    return value, True


def _clean_public_subject(subject_id: str) -> tuple[str, bool]:
    text = str(subject_id).strip()
    if not text or _is_unsafe_public_text(text):
        return "redacted", False
    return text, True


def _clean_public_value(value: ClaimValue) -> tuple[ClaimValue, bool]:
    if value is None or isinstance(value, bool):
        return value, True
    if isinstance(value, str):
        text = value.strip()
        if _is_unsafe_public_text(text):
            return None, False
        return text, True
    if isinstance(value, int | float):
        numeric = float(value)
        if not math.isfinite(numeric):
            return None, False
        return value, True
    return None, False


def _clean_phrases(phrases: Sequence[str]) -> tuple[tuple[str, ...], bool]:
    clean: list[str] = []
    safe = True
    phrase_iter = (phrases,) if isinstance(phrases, str) else phrases
    for phrase in phrase_iter:
        if not isinstance(phrase, str):
            safe = False
            continue
        text = phrase.strip()
        if not text:
            continue
        if _is_unsafe_public_text(text):
            safe = False
            continue
        clean.append(text)
    return tuple(clean), safe


def _is_safe_evidence_ref(ref: str) -> bool:
    if not isinstance(ref, str) or not ref:
        return False
    if _is_unsafe_public_text(ref):
        return False
    return ":" in ref


def _is_unsafe_public_text(text: str) -> bool:
    lowered = text.lower()
    return (
        text.startswith("/")
        or lowered.startswith("file://")
        or ":\\" in text
        or "/users/" in lowered
        or "/volumes/" in lowered
        or "/home/" in lowered
        or "/tmp/" in lowered
        or "/private/" in lowered
        or "/var/folders/" in lowered
        or "\\users\\" in lowered
        or lowered.startswith("vector:")
        or lowered.startswith("audio:raw")
        or "raw_audio" in lowered
        or "raw vector" in lowered
    )


__all__ = [
    "ClaimScope",
    "ClaimStatus",
    "ClaimValue",
    "MusicClaim",
    "MusicClaimLedger",
    "MusicClaimType",
    "claim_status_for_confidence",
]
