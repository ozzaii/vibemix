# SPDX-License-Identifier: Apache-2.0
"""Compile scored transition candidates into a bounded agent context."""

from __future__ import annotations

from typing import Any

from vibemix.intel.agent_contract import (
    SCHEMA_VERSION,
    AgentContextEnvelope,
    ContextIntent,
    ContextMode,
)
from vibemix.intel.claims import MusicClaimLedger
from vibemix.intel.transition_scorer import (
    EXACT_TIMING_CONFIDENCE_FLOOR,
    LIVE_SELECT_CONFIDENCE_FLOOR,
    TransitionCandidate,
)

DEFAULT_ALLOWED_CLAIMS: tuple[str, ...] = (
    "transition_role",
    "semantic_fit",
    "harmonic_fit",
    "tempo_fit",
    "energy_shape",
    "phrase_alignment",
    "cue_operability",
    "risk",
    "uncertainty",
)

DEFAULT_FORBIDDEN_CLAIMS: tuple[str, ...] = (
    "invented_track_id",
    "invented_section_id",
    "invented_cue_slot",
    "invented_bpm",
    "invented_key",
    "invented_energy",
    "exact_timing_below_confidence",
    "unsupported_musical_fact",
)


def compile_transition_context(
    *,
    packet_id: str,
    mode: ContextMode,
    intent: ContextIntent,
    current: dict[str, Any],
    candidates: tuple[TransitionCandidate, ...],
    max_candidates: int | None = None,
) -> AgentContextEnvelope:
    """Return a redacted, bounded context envelope for transition decisions."""
    cap = max_candidates if max_candidates is not None else (5 if mode == "live" else 12)
    bounded = tuple(candidates[: max(0, cap)])
    exact_timing_allowed = any(candidate.start_in_bars is not None for candidate in bounded)
    candidate_payloads = tuple(_candidate_payload(candidate) for candidate in bounded)
    claim_ledger = _claim_ledger(packet_id, bounded)
    return AgentContextEnvelope(
        schema_version=SCHEMA_VERSION,
        packet_id=packet_id,
        mode=mode,
        intent=intent,
        current=_redact_current(current),
        candidates=candidate_payloads,
        constraints={
            "max_candidates": cap,
            "exact_timing_allowed": exact_timing_allowed,
            "model_may_create_ids": False,
            "raw_vectors_included": False,
            "raw_audio_included": False,
            "local_paths_included": False,
            "strict_claim_validation": True,
        },
        allowed_actions=_allowed_actions(mode),
        allowed_claims=DEFAULT_ALLOWED_CLAIMS,
        forbidden_claims=DEFAULT_FORBIDDEN_CLAIMS,
        citation_scope=_citation_scope(bounded, claim_ledger),
        confidence_policy={
            "live_select_floor": LIVE_SELECT_CONFIDENCE_FLOOR,
            "exact_timing_floor": EXACT_TIMING_CONFIDENCE_FLOOR,
            "exact_timing_allowed": exact_timing_allowed,
        },
        claim_ids=claim_ledger.claim_ids(),
        claim_summary=claim_ledger.claim_summary(),
    )


def _candidate_payload(candidate: TransitionCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "from_track_id": candidate.from_track_id,
        "from_section_id": candidate.from_section_id,
        "from_role": candidate.from_role,
        "to_track_id": candidate.to_track_id,
        "to_section_id": candidate.to_section_id,
        "to_role": candidate.to_role,
        "recommended_cue_slot": candidate.cue_slot,
        "start_in_bars": candidate.start_in_bars,
        "score": candidate.score,
        "confidence": candidate.confidence,
        "scores": {
            "semantic": candidate.components.semantic,
            "harmonic": candidate.components.harmonic,
            "bpm": candidate.components.bpm,
            "energy_shape": candidate.components.energy_shape,
            "role": candidate.components.role,
            "phrase_alignment": candidate.components.phrase_alignment,
            "cue_operability": candidate.components.cue_operability,
            "taste": candidate.components.taste,
            "novelty": candidate.components.novelty,
            "risk_penalty": candidate.components.risk_penalty,
        },
        "risk_flags": candidate.risk_flags,
        "deterministic_reason": candidate.reasons[0] if candidate.reasons else "",
    }


def _redact_current(current: dict[str, Any]) -> dict[str, Any]:
    forbidden_keys = {"filepath", "file_path", "path", "local_path", "raw_audio", "vector"}
    redacted: dict[str, Any] = {}
    for key, value in current.items():
        if key in forbidden_keys:
            continue
        if isinstance(value, str) and _looks_like_local_path(value):
            continue
        redacted[key] = value
    return redacted


def _looks_like_local_path(value: str) -> bool:
    return value.startswith("/") or value.startswith("file://") or ":\\" in value


def _allowed_actions(mode: ContextMode) -> tuple[str, ...]:
    if mode == "live":
        return ("select", "hold", "suppress")
    return ("select", "hold", "suppress", "ask")


def _claim_ledger(packet_id: str, candidates: tuple[TransitionCandidate, ...]) -> MusicClaimLedger:
    ledger = MusicClaimLedger(packet_id)
    for candidate in candidates:
        candidate_ref = f"candidate:{candidate.candidate_id}"
        ledger.add(
            "transition_fit",
            subject_id=candidate.candidate_id,
            value="compatible" if candidate.score >= 0.62 else "tentative",
            evidence_refs=(candidate_ref,),
            confidence=candidate.confidence,
            scope="transition",
            allowed_phrases=("compatible entry", "works as a next entry", "good entry"),
            forbidden_phrases=("perfect", "guaranteed"),
            reason_codes=candidate.risk_flags,
            provenance_ref=candidate_ref,
        )
        ledger.add(
            "section_role",
            subject_id=candidate.to_section_id,
            value=candidate.to_role,
            evidence_refs=(f"section:{candidate.to_section_id}", candidate_ref),
            confidence=candidate.confidence,
            scope="section",
            allowed_phrases=(candidate.to_role,),
            forbidden_phrases=("main drop",) if candidate.to_role != "drop" else (),
            reason_codes=(),
            provenance_ref=f"section:{candidate.to_section_id}",
        )
        if "key_unknown" not in candidate.risk_flags:
            ledger.add(
                "harmonic_fit",
                subject_id=candidate.candidate_id,
                value="compatible" if candidate.components.harmonic >= 0.78 else "risky",
                evidence_refs=(candidate_ref, f"score:{candidate.candidate_id}:harmonic"),
                confidence=candidate.components.harmonic,
                scope="transition",
                allowed_phrases=("neighboring key", "harmonically close")
                if candidate.components.harmonic >= 0.78
                else ("harmonic risk",),
                forbidden_phrases=("guaranteed key fit",),
                reason_codes=tuple(
                    flag for flag in candidate.risk_flags if flag.startswith("harmonic")
                ),
                provenance_ref=f"score:{candidate.candidate_id}:harmonic",
            )
        if "bpm_unknown" not in candidate.risk_flags:
            ledger.add(
                "tempo_fit",
                subject_id=candidate.candidate_id,
                value="close" if candidate.components.bpm >= 0.78 else "risky",
                evidence_refs=(candidate_ref, f"score:{candidate.candidate_id}:bpm"),
                confidence=candidate.components.bpm,
                scope="transition",
                allowed_phrases=("tempo is close", "BPM is close")
                if candidate.components.bpm >= 0.78
                else ("tempo push",),
                forbidden_phrases=("tempo is identical",),
                reason_codes=tuple(
                    flag for flag in candidate.risk_flags if flag.startswith("tempo")
                ),
                provenance_ref=f"score:{candidate.candidate_id}:bpm",
            )
        if candidate.cue_slot:
            ledger.add(
                "cue_slot",
                subject_id=candidate.candidate_id,
                value=candidate.cue_slot,
                evidence_refs=(candidate_ref,),
                confidence=candidate.components.cue_operability,
                scope="cue",
                allowed_phrases=(f"cue {candidate.cue_slot}", f"hot cue {candidate.cue_slot}"),
                forbidden_phrases=("overwrite cue",),
                reason_codes=tuple(flag for flag in candidate.risk_flags if "cue" in flag),
                provenance_ref=candidate_ref,
            )
        if candidate.start_in_bars is not None:
            ledger.add(
                "bars_until_event",
                subject_id=candidate.candidate_id,
                value=candidate.start_in_bars,
                unit="bars",
                evidence_refs=(f"packet:{packet_id}", candidate_ref),
                confidence=candidate.confidence,
                scope="live_timing",
                allowed_phrases=(
                    f"in {candidate.start_in_bars} bars",
                    f"after {candidate.start_in_bars} bars",
                ),
                forbidden_phrases=("exactly now",),
                reason_codes=(),
                provenance_ref=f"packet:{packet_id}",
            )
    return ledger


def _citation_scope(
    candidates: tuple[TransitionCandidate, ...], claim_ledger: MusicClaimLedger
) -> dict[str, tuple[str, ...]]:
    candidate_ids = tuple(candidate.candidate_id for candidate in candidates)
    section_ids = tuple(
        dict.fromkeys(
            section_id
            for candidate in candidates
            for section_id in (candidate.from_section_id, candidate.to_section_id)
        )
    )
    track_ids = tuple(
        dict.fromkeys(
            track_id
            for candidate in candidates
            for track_id in (candidate.from_track_id, candidate.to_track_id)
        )
    )
    return {
        "candidate": candidate_ids,
        "section": section_ids,
        "track": track_ids,
        "claim": claim_ledger.claim_ids(),
    }


__all__ = [
    "DEFAULT_ALLOWED_CLAIMS",
    "DEFAULT_FORBIDDEN_CLAIMS",
    "compile_transition_context",
]
