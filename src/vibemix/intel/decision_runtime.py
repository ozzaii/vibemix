# SPDX-License-Identifier: Apache-2.0
"""Bounded runtime for deterministic/model-assisted musical decisions."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Protocol

from vibemix.intel.agent_contract import (
    SCHEMA_VERSION,
    AgentContextEnvelope,
    AgentDecision,
    ContextIntent,
    ContextMode,
)
from vibemix.intel.decision_trace import (
    AgentDecisionTrace,
    DecisionSource,
    GateResult,
    stable_payload_hash,
)
from vibemix.intel.decision_validator import ValidationResult, validate_agent_decision


class DecisionModel(Protocol):
    def decide(self, envelope: AgentContextEnvelope) -> AgentDecision: ...


@dataclass(frozen=True, slots=True)
class DecisionRuntimePolicy:
    deterministic_live_default: bool = True
    allow_model_in_live: bool = False
    use_model_when_available: bool = True


@dataclass(frozen=True, slots=True)
class RuntimeInputSnapshot:
    input_snapshot_id: str
    envelope: AgentContextEnvelope


@dataclass(frozen=True, slots=True)
class RuntimeDecisionResult:
    decision_id: str
    decision_source: DecisionSource
    final_decision: AgentDecision
    emitted: bool
    validation_result: ValidationResult
    trace: AgentDecisionTrace
    model_decision: AgentDecision | None = None


def decide(
    mode: ContextMode,
    intent: ContextIntent,
    snapshot: RuntimeInputSnapshot,
    *,
    model_backend: DecisionModel | None = None,
    policy: DecisionRuntimePolicy | None = None,
    trace_id: str = "trace_001",
    decision_id: str = "dec_001",
) -> RuntimeDecisionResult:
    """Turn one issued context packet into a safe runtime decision."""
    started = time.perf_counter()
    active_policy = policy or DecisionRuntimePolicy()
    envelope = snapshot.envelope
    if envelope.mode != mode or envelope.intent != intent:
        raise ValueError("mode/intent must match the issued context envelope")
    gates = _gate_envelope(envelope)
    hard_gate = next((gate for gate in gates if gate.status in {"suppress", "hold"}), None)
    deterministic = _deterministic_decision(envelope, gates)

    if hard_gate is not None:
        validation = validate_agent_decision(envelope, deterministic)
        return _result(
            decision_id=decision_id,
            trace_id=trace_id,
            snapshot=snapshot,
            decision_source="deterministic",
            final_decision=deterministic,
            validation_result=validation,
            gates=gates,
            started=started,
        )

    should_use_model = (
        model_backend is not None
        and active_policy.use_model_when_available
        and (mode != "live" or active_policy.allow_model_in_live)
        and not (mode == "live" and active_policy.deterministic_live_default)
    )
    if not should_use_model:
        validation = validate_agent_decision(envelope, deterministic)
        return _result(
            decision_id=decision_id,
            trace_id=trace_id,
            snapshot=snapshot,
            decision_source="deterministic",
            final_decision=deterministic,
            validation_result=validation,
            gates=gates,
            started=started,
        )

    try:
        model_decision = model_backend.decide(envelope)
    except Exception as exc:  # pragma: no cover - exact backend failure is tested via behavior
        degraded = validate_agent_decision(envelope, deterministic)
        gates = (
            *gates,
            GateResult("model_call", "reject", f"model_unavailable:{type(exc).__name__}"),
        )
        return _result(
            decision_id=decision_id,
            trace_id=trace_id,
            snapshot=snapshot,
            decision_source=_degraded_source(deterministic.action),
            final_decision=deterministic,
            validation_result=degraded,
            gates=gates,
            started=started,
        )

    return validate_and_degrade(
        envelope,
        model_decision,
        deterministic,
        snapshot=snapshot,
        decision_id=decision_id,
        trace_id=trace_id,
        started=started,
        gates=gates,
    )


def validate_and_degrade(
    envelope: AgentContextEnvelope,
    decision: AgentDecision,
    deterministic_fallback: AgentDecision | None,
    *,
    snapshot: RuntimeInputSnapshot | None = None,
    decision_id: str = "dec_001",
    trace_id: str = "trace_001",
    started: float | None = None,
    gates: tuple[GateResult, ...] = (),
) -> RuntimeDecisionResult:
    """Validate model output and degrade without emitting unsafe copy."""
    started = time.perf_counter() if started is None else started
    snapshot = snapshot or RuntimeInputSnapshot("snapshot_inline", envelope)
    validation = validate_agent_decision(envelope, decision)
    if validation.accepted:
        return _result(
            decision_id=decision_id,
            trace_id=trace_id,
            snapshot=snapshot,
            decision_source="model_validated",
            final_decision=decision,
            validation_result=validation,
            gates=(*gates, GateResult("model_validation", "pass", "accepted")),
            started=started,
            model_decision=decision,
        )

    fallback = deterministic_fallback or _suppress_decision()
    if deterministic_fallback is not None and _is_language_only_failure(validation.errors):
        fallback_validation = validate_agent_decision(envelope, fallback)
        if fallback_validation.accepted:
            return _result(
                decision_id=decision_id,
                trace_id=trace_id,
                snapshot=snapshot,
                decision_source="model_degraded_to_deterministic",
                final_decision=fallback,
                validation_result=fallback_validation,
                gates=(
                    *gates,
                    GateResult("model_validation", "reject", "|".join(validation.errors)),
                ),
                started=started,
                model_decision=decision,
            )

    rejected = _safe_rejection_decision(envelope)
    rejected_validation = validate_agent_decision(envelope, rejected)
    return _result(
        decision_id=decision_id,
        trace_id=trace_id,
        snapshot=snapshot,
        decision_source=_degraded_source(rejected.action),
        final_decision=rejected,
        validation_result=rejected_validation,
        gates=(*gates, GateResult("model_validation", "reject", "|".join(validation.errors))),
        started=started,
        model_decision=decision,
    )


def _gate_envelope(envelope: AgentContextEnvelope) -> tuple[GateResult, ...]:
    gates: list[GateResult] = []
    current_track = envelope.current.get("track_id") or envelope.current.get("active_track_id")
    if envelope.mode == "live" and not current_track:
        gates.append(GateResult("current_track", "suppress", "no_current_track"))
    else:
        gates.append(GateResult("current_track", "pass", "grounded_or_not_required"))

    blend = bool(
        envelope.current.get("blend_suppressed")
        or envelope.current.get("blend_active")
        or envelope.constraints.get("blend_suppressed")
        or envelope.constraints.get("blend_active")
    )
    if envelope.mode == "live" and blend:
        gates.append(GateResult("blend", "suppress", "blend_active"))
    else:
        gates.append(GateResult("blend", "pass", "not_blending"))

    if not envelope.candidates:
        status = "suppress" if envelope.mode == "live" else "hold"
        gates.append(GateResult("candidate_slate", status, "no_candidates"))
    else:
        gates.append(GateResult("candidate_slate", "pass", "candidates_available"))
        prepared_target_mismatch = _prepared_target_mismatch(envelope)
        if prepared_target_mismatch is not None:
            gates.append(
                GateResult(
                    "prepared_target",
                    "suppress",
                    f"prepared_target_mismatch:{prepared_target_mismatch}",
                )
            )
        else:
            gates.append(GateResult("prepared_target", "pass", "matched_or_empty"))
    return tuple(gates)


def _deterministic_decision(
    envelope: AgentContextEnvelope, gates: tuple[GateResult, ...]
) -> AgentDecision:
    hard_gate = next((gate for gate in gates if gate.status in {"suppress", "hold"}), None)
    if hard_gate is not None:
        if hard_gate.status == "hold" and "hold" in envelope.allowed_actions:
            return AgentDecision(
                schema_version=SCHEMA_VERSION,
                action="hold",
                spoken_text="Holding until a grounded candidate is available.",
                confidence=0.0,
            )
        return _suppress_decision()

    candidate = envelope.candidates[0]
    cue_slot = candidate.get("recommended_cue_slot")
    if not cue_slot:
        if "hold" in envelope.allowed_actions:
            return AgentDecision(
                schema_version=SCHEMA_VERSION,
                action="hold",
                spoken_text="Holding because the candidate has no usable cue.",
                confidence=float(candidate.get("confidence") or 0.0),
            )
        return _suppress_decision()

    bars = candidate.get("start_in_bars")
    exact_timing_allowed = bool(envelope.constraints.get("exact_timing_allowed", False))
    timing_text = f"in {int(bars)} bars" if exact_timing_allowed and bars is not None else None
    cue_start_label = _format_mmss(candidate.get("to_start_s"))
    cue_text = _cue_text(str(cue_slot), cue_start_label)
    role_pair = _role_pair_text(candidate.get("from_role"), candidate.get("to_role"))
    role_suffix = f", {role_pair}" if role_pair else ""
    track_short = str(candidate.get("to_track_id") or "next track")
    if timing_text:
        spoken = f"Next good entry: {track_short} {cue_text}{role_suffix}, {timing_text}."
    else:
        spoken = f"Next good entry: {track_short} from {cue_text}{role_suffix}."
    cited_claim_ids = _claim_ids_for_candidate(
        envelope,
        candidate,
        include_timing=timing_text is not None,
        include_structure=role_pair is not None,
        include_boundary=cue_start_label is not None,
    )
    return AgentDecision(
        schema_version=SCHEMA_VERSION,
        action="select",
        candidate_id=str(candidate["candidate_id"]),
        cue_slot=str(cue_slot),
        timing_text=timing_text,
        spoken_text=spoken,
        cited_claims=_claim_types_for_ids(envelope, cited_claim_ids),
        cited_claim_ids=cited_claim_ids,
        confidence=float(candidate.get("confidence") or 0.0),
    )


def _claim_ids_for_candidate(
    envelope: AgentContextEnvelope,
    candidate: dict,
    *,
    include_timing: bool,
    include_structure: bool,
    include_boundary: bool,
) -> tuple[str, ...]:
    candidate_id = str(candidate.get("candidate_id"))
    candidate_claims = {"transition_fit", "cue_slot"}
    if include_timing:
        candidate_claims.add("bars_until_event")
    section_claims: set[str] = set()
    if include_structure:
        section_claims.add("section_role")
    if include_boundary:
        section_claims.add("section_boundary")
    section_ids = {
        section_id
        for section_id in (
            candidate.get("from_section_id"),
            candidate.get("to_section_id"),
        )
        if isinstance(section_id, str) and section_id
    }
    ids: list[str] = []
    for row in envelope.claim_summary:
        claim_type = row.get("type")
        subject_id = row.get("subject_id")
        if subject_id == candidate_id and claim_type in candidate_claims:
            ids.append(str(row["claim_id"]))
        elif claim_type in section_claims and subject_id in section_ids:
            ids.append(str(row["claim_id"]))
    return tuple(ids)


def _prepared_target_mismatch(envelope: AgentContextEnvelope) -> str | None:
    if envelope.mode != "live":
        return None
    prepared = _nonempty_str(envelope.current.get("prepared_target_track_id"))
    if prepared is None or not envelope.candidates:
        return None
    selected = _nonempty_str(envelope.candidates[0].get("to_track_id"))
    if selected == prepared:
        return None
    return prepared


def _nonempty_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _claim_types_for_ids(
    envelope: AgentContextEnvelope, claim_ids: tuple[str, ...]
) -> tuple[str, ...]:
    wanted = set(claim_ids)
    types = [
        str(row["type"])
        for row in envelope.claim_summary
        if row.get("claim_id") in wanted and row.get("type")
    ]
    return tuple(dict.fromkeys(types))


def _cue_text(cue_slot: str, start_label: str | None) -> str:
    cue = f"cue {cue_slot}"
    return f"{cue} at {start_label}" if start_label is not None else cue


def _role_pair_text(from_role: object, to_role: object) -> str | None:
    source = _role_label(from_role)
    destination = _role_label(to_role)
    if source is None or destination is None:
        return None
    return f"{source} into {destination}"


def _role_label(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    role = raw.strip().lower()
    if not role or role == "unknown":
        return None
    return role.replace("_", " ").replace("-", " ")


def _format_mmss(raw: object) -> str | None:
    try:
        seconds = float(raw)
    except (TypeError, ValueError):
        return None
    if not seconds >= 0:
        return None
    total = round(seconds)
    return f"{total // 60}:{total % 60:02d}"


def _safe_rejection_decision(envelope: AgentContextEnvelope) -> AgentDecision:
    if envelope.mode == "prep" and "hold" in envelope.allowed_actions:
        return AgentDecision(
            schema_version=SCHEMA_VERSION,
            action="hold",
            spoken_text="Holding because the model output was not grounded.",
            confidence=0.0,
        )
    return _suppress_decision()


def _suppress_decision() -> AgentDecision:
    return AgentDecision(schema_version=SCHEMA_VERSION, action="suppress", confidence=0.0)


def _is_language_only_failure(errors: tuple[str, ...]) -> bool:
    language_prefixes = (
        "missing_claim_id_for_",
        "forbidden_phrase:",
        "unsupported_claim:",
    )
    return bool(errors) and all(error.startswith(language_prefixes) for error in errors)


def _degraded_source(action: str) -> DecisionSource:
    if action == "select":
        return "model_degraded_to_deterministic"
    if action == "hold":
        return "model_rejected_hold"
    return "model_rejected_suppress"


def _result(
    *,
    decision_id: str,
    trace_id: str,
    snapshot: RuntimeInputSnapshot,
    decision_source: DecisionSource,
    final_decision: AgentDecision,
    validation_result: ValidationResult,
    gates: tuple[GateResult, ...],
    started: float,
    model_decision: AgentDecision | None = None,
) -> RuntimeDecisionResult:
    latency = max(0, round((time.perf_counter() - started) * 1000))
    candidate_ids = tuple(
        str(candidate["candidate_id"]) for candidate in snapshot.envelope.candidates
    )
    suppressed = tuple(
        gate.reason for gate in gates if gate.status in {"hold", "suppress", "reject"}
    )
    trace = AgentDecisionTrace(
        trace_id=trace_id,
        mode=snapshot.envelope.mode,
        intent=snapshot.envelope.intent,
        decision_source=decision_source,
        input_snapshot_id=snapshot.input_snapshot_id,
        context_packet_id=snapshot.envelope.packet_id,
        candidate_ids=candidate_ids,
        selected_candidate_id=final_decision.candidate_id,
        selected_proposal_id=None,
        gate_results=gates,
        model_call_id="model:injected" if model_decision is not None else None,
        validation_status=validation_result.status,
        validation_errors=validation_result.errors,
        final_action=final_decision.action,
        final_payload_hash=stable_payload_hash(asdict(final_decision)),
        suppressed_reasons=suppressed,
        latency_ms={"total": latency},
    )
    return RuntimeDecisionResult(
        decision_id=decision_id,
        decision_source=decision_source,
        final_decision=final_decision,
        emitted=final_decision.action == "select" and validation_result.accepted,
        validation_result=validation_result,
        trace=trace,
        model_decision=model_decision,
    )


__all__ = [
    "DecisionModel",
    "DecisionRuntimePolicy",
    "RuntimeDecisionResult",
    "RuntimeInputSnapshot",
    "decide",
    "validate_and_degrade",
]
