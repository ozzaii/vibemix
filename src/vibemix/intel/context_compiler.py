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
    TransitionScoreComponents,
)

DEFAULT_ALLOWED_CLAIMS: tuple[str, ...] = (
    "transition_role",
    "transition_fit",
    "section_role",
    "section_boundary",
    "semantic_fit",
    "semantic_match",
    "harmonic_fit",
    "tempo_fit",
    "energy_shape",
    "phrase_alignment",
    "phrase_fit",
    "cue_operability",
    "cue_slot",
    "bars_until_event",
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


def compile_suggestion_context(
    *,
    packet_id: str,
    current: dict[str, Any],
    suggestion: dict[str, Any],
    mode: ContextMode = "live",
    intent: ContextIntent = "live_next_pill",
    max_candidates: int | None = None,
) -> AgentContextEnvelope:
    """Compile a live pill suggestion payload into the claim-ledger contract."""
    return compile_transition_context(
        packet_id=packet_id,
        mode=mode,
        intent=intent,
        current=current,
        candidates=transition_candidates_from_suggestion(suggestion),
        max_candidates=max_candidates,
    )


def transition_candidates_from_suggestion(
    suggestion: dict[str, Any],
) -> tuple[TransitionCandidate, ...]:
    """Return context candidates from a ``next_suggestion`` wire payload.

    The live pill scores each alternative independently, so raw transition
    payloads can carry duplicate scorer-local ids. The compiled context is a
    fresh ranked packet: candidate ids are reassigned by current order
    (``tr_001``, ``tr_002``...) so citations stay unambiguous.
    """
    candidates: list[TransitionCandidate] = []
    for index, payload in enumerate(_suggestion_transition_payloads(suggestion), start=1):
        candidate = _transition_candidate_from_payload(payload, f"tr_{index:03d}")
        if candidate is not None:
            candidates.append(candidate)
    return tuple(candidates)


def _suggestion_transition_payloads(suggestion: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    raw_alternatives = suggestion.get("transition_alternatives")
    payloads: list[dict[str, Any]] = []
    if isinstance(raw_alternatives, (list, tuple)):
        for raw in raw_alternatives:
            if not isinstance(raw, dict):
                continue
            transition = raw.get("transition")
            if not isinstance(transition, dict):
                continue
            payload = dict(transition)
            if not payload.get("to_track_id") and isinstance(raw.get("track_id"), str):
                payload["to_track_id"] = raw["track_id"]
            payloads.append(payload)
    if not payloads and isinstance(suggestion.get("transition"), dict):
        payloads.append(dict(suggestion["transition"]))
    return tuple(payloads)


def _transition_candidate_from_payload(
    payload: dict[str, Any],
    candidate_id: str,
) -> TransitionCandidate | None:
    from_section_id = _required_str(payload.get("from_section_id"))
    to_section_id = _required_str(payload.get("to_section_id"))
    from_track_id = _required_str(payload.get("from_track_id"))
    to_track_id = _required_str(payload.get("to_track_id"))
    if None in (from_section_id, to_section_id, from_track_id, to_track_id):
        return None

    scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    components = TransitionScoreComponents(
        semantic=_score_component(scores, "semantic", 0.50),
        harmonic=_score_component(scores, "harmonic", 0.50),
        bpm=_score_component(scores, "bpm", 0.50),
        energy_shape=_score_component(scores, "energy_shape", 0.50),
        role=_score_component(scores, "role", 0.50),
        phrase_alignment=_score_component(scores, "phrase_alignment", 0.50),
        cue_operability=_score_component(scores, "cue_operability", 0.50),
        taste=_score_component(scores, "taste", 0.50),
        novelty=_score_component(scores, "novelty", 0.50),
        risk_penalty=_score_component(scores, "risk_penalty", 0.0),
    )
    transition_key = _required_str(payload.get("transition_key")) or "|".join(
        (
            "suggestion",
            candidate_id,
            from_section_id or "",
            to_section_id or "",
            str(payload.get("cue_slot") or ""),
        )
    )
    return TransitionCandidate(
        candidate_id=candidate_id,
        transition_key=transition_key,
        from_section_id=from_section_id or "",
        to_section_id=to_section_id or "",
        from_track_id=from_track_id or "",
        to_track_id=to_track_id or "",
        from_role=_str_or(payload.get("from_role"), "unknown"),
        to_role=_str_or(payload.get("to_role"), "unknown"),
        from_start_s=_float_or(payload.get("from_start_s"), 0.0),
        from_end_s=_float_or(payload.get("from_end_s"), 0.0),
        to_start_s=_float_or(payload.get("to_start_s"), 0.0),
        to_end_s=_float_or(payload.get("to_end_s"), 0.0),
        from_bpm=_optional_float(payload.get("from_bpm")),
        to_bpm=_optional_float(payload.get("to_bpm")),
        from_camelot=_optional_str(payload.get("from_camelot")),
        to_camelot=_optional_str(payload.get("to_camelot")),
        cue_slot=_optional_str(payload.get("cue_slot")),
        start_in_bars=_optional_int(payload.get("start_in_bars")),
        score=_float_or(payload.get("score"), 0.0),
        confidence=_float_or(payload.get("confidence"), 0.0),
        semantic_basis=_str_or(payload.get("semantic_basis"), "semantic_unknown"),
        components=components,
        risk_flags=_str_tuple(payload.get("risk_flags")),
        reasons=_str_tuple(payload.get("reasons")),
    )


def _candidate_payload(candidate: TransitionCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "from_track_id": candidate.from_track_id,
        "from_section_id": candidate.from_section_id,
        "from_role": candidate.from_role,
        "from_start_s": candidate.from_start_s,
        "from_end_s": candidate.from_end_s,
        "from_bpm": candidate.from_bpm,
        "from_camelot": candidate.from_camelot,
        "to_track_id": candidate.to_track_id,
        "to_section_id": candidate.to_section_id,
        "to_role": candidate.to_role,
        "to_start_s": candidate.to_start_s,
        "to_end_s": candidate.to_end_s,
        "to_bpm": candidate.to_bpm,
        "to_camelot": candidate.to_camelot,
        "recommended_cue_slot": candidate.cue_slot,
        "start_in_bars": candidate.start_in_bars,
        "score": candidate.score,
        "confidence": candidate.confidence,
        "semantic_basis": candidate.semantic_basis,
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


def _required_str(raw: Any) -> str | None:
    value = _optional_str(raw)
    return value if value else None


def _optional_str(raw: Any) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _str_or(raw: Any, default: str) -> str:
    return _optional_str(raw) or default


def _float_or(raw: Any, default: float) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _optional_float(raw: Any) -> float | None:
    if raw is None:
        return None
    value = _float_or(raw, 0.0)
    return value if value > 0.0 else None


def _optional_int(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _score_component(scores: dict[str, Any], key: str, default: float) -> float:
    return max(0.0, min(1.0, _float_or(scores.get(key), default)))


def _str_tuple(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(str(item) for item in raw if isinstance(item, str) and item)


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
        _add_section_role_claim(
            ledger,
            candidate_ref,
            section_id=candidate.from_section_id,
            role=candidate.from_role,
            confidence=candidate.confidence,
        )
        _add_section_role_claim(
            ledger,
            candidate_ref,
            section_id=candidate.to_section_id,
            role=candidate.to_role,
            confidence=candidate.confidence,
        )
        _add_section_boundary_claims(
            ledger,
            candidate_ref,
            section_id=candidate.from_section_id,
            role=candidate.from_role,
            start_s=candidate.from_start_s,
            end_s=candidate.from_end_s,
            confidence=candidate.confidence,
        )
        _add_section_boundary_claims(
            ledger,
            candidate_ref,
            section_id=candidate.to_section_id,
            role=candidate.to_role,
            start_s=candidate.to_start_s,
            end_s=candidate.to_end_s,
            confidence=candidate.confidence,
        )
        if "semantic_unknown" not in candidate.risk_flags:
            ledger.add(
                "semantic_match",
                subject_id=candidate.candidate_id,
                value="close" if candidate.components.semantic >= 0.78 else "tentative",
                evidence_refs=(candidate_ref, f"score:{candidate.candidate_id}:semantic"),
                confidence=candidate.components.semantic,
                scope="transition",
                allowed_phrases=("section texture is close",)
                if candidate.components.semantic >= 0.78
                else ("section texture is tentative",),
                forbidden_phrases=("sounds identical",),
                reason_codes=(candidate.semantic_basis,),
                provenance_ref=f"score:{candidate.candidate_id}:semantic",
            )
        if "energy_unknown" not in candidate.risk_flags:
            ledger.add(
                "energy_shape",
                subject_id=candidate.candidate_id,
                value="matched" if candidate.components.energy_shape >= 0.78 else "risky",
                evidence_refs=(candidate_ref, f"score:{candidate.candidate_id}:energy_shape"),
                confidence=candidate.components.energy_shape,
                scope="transition",
                allowed_phrases=("energy shape fits",)
                if candidate.components.energy_shape >= 0.78
                else ("energy shape is risky",),
                forbidden_phrases=("energy is identical",),
                reason_codes=tuple(
                    flag for flag in candidate.risk_flags if flag.startswith("energy")
                ),
                provenance_ref=f"score:{candidate.candidate_id}:energy_shape",
            )
        if "phrase_unknown" not in candidate.risk_flags:
            ledger.add(
                "phrase_fit",
                subject_id=candidate.candidate_id,
                value="phrase_clean" if candidate.components.phrase_alignment >= 0.82 else "risky",
                evidence_refs=(candidate_ref, f"score:{candidate.candidate_id}:phrase_alignment"),
                confidence=candidate.components.phrase_alignment,
                scope="transition",
                allowed_phrases=("phrase boundary", "phrase clean")
                if candidate.components.phrase_alignment >= 0.82
                else ("phrase risk",),
                forbidden_phrases=("perfect phrase",),
                reason_codes=tuple(
                    flag
                    for flag in candidate.risk_flags
                    if flag in {"off_phrase", "phrase_short", "timing_low_confidence"}
                ),
                provenance_ref=f"score:{candidate.candidate_id}:phrase_alignment",
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
        ledger.add(
            "cue_operability",
            subject_id=candidate.candidate_id,
            value="reliable" if candidate.components.cue_operability >= 0.82 else "review",
            evidence_refs=(candidate_ref, f"score:{candidate.candidate_id}:cue_operability"),
            confidence=candidate.components.cue_operability,
            scope="cue",
            allowed_phrases=("reliable cue",)
            if candidate.components.cue_operability >= 0.82
            else ("cue needs review",),
            forbidden_phrases=("overwrite cue",),
            reason_codes=tuple(flag for flag in candidate.risk_flags if "cue" in flag),
            provenance_ref=f"score:{candidate.candidate_id}:cue_operability",
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


def _add_section_role_claim(
    ledger: MusicClaimLedger,
    candidate_ref: str,
    *,
    section_id: str,
    role: str,
    confidence: float,
) -> None:
    ledger.add(
        "section_role",
        subject_id=section_id,
        value=role,
        evidence_refs=(f"section:{section_id}", candidate_ref),
        confidence=confidence,
        scope="section",
        allowed_phrases=(role,),
        forbidden_phrases=("main drop",) if role != "drop" else (),
        reason_codes=(),
        provenance_ref=f"section:{section_id}",
    )


def _add_section_boundary_claims(
    ledger: MusicClaimLedger,
    candidate_ref: str,
    *,
    section_id: str,
    role: str,
    start_s: float,
    end_s: float,
    confidence: float,
) -> None:
    start_label = _format_mmss(start_s)
    end_label = _format_mmss(end_s)
    ledger.add(
        "section_boundary",
        subject_id=section_id,
        value=round(max(0.0, float(start_s)), 3),
        unit="seconds",
        evidence_refs=(f"section:{section_id}", candidate_ref),
        confidence=confidence,
        scope="section",
        allowed_phrases=(f"{role} starts at {start_label}", start_label),
        forbidden_phrases=("exact waveform boundary",),
        reason_codes=("section_start",),
        provenance_ref=f"section:{section_id}",
    )
    ledger.add(
        "section_boundary",
        subject_id=section_id,
        value=round(max(0.0, float(end_s)), 3),
        unit="seconds",
        evidence_refs=(f"section:{section_id}", candidate_ref),
        confidence=confidence,
        scope="section",
        allowed_phrases=(f"{role} ends at {end_label}", end_label),
        forbidden_phrases=("exact waveform boundary",),
        reason_codes=("section_end",),
        provenance_ref=f"section:{section_id}",
    )


def _format_mmss(seconds: float) -> str:
    total = max(0, round(float(seconds)))
    return f"{total // 60}:{total % 60:02d}"


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
    "compile_suggestion_context",
    "compile_transition_context",
    "transition_candidates_from_suggestion",
]
