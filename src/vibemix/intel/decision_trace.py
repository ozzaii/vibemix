# SPDX-License-Identifier: Apache-2.0
"""Replayable, redacted traces for agentic musical decisions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

from vibemix.intel.agent_contract import ContextIntent, ContextMode

DecisionSource = Literal[
    "deterministic",
    "model_validated",
    "model_degraded_to_deterministic",
    "model_rejected_hold",
    "model_rejected_suppress",
]
GateStatus = Literal["pass", "hold", "suppress", "reject"]


@dataclass(frozen=True, slots=True)
class GateResult:
    name: str
    status: GateStatus
    reason: str


@dataclass(frozen=True, slots=True)
class AgentDecisionTrace:
    trace_id: str
    mode: ContextMode
    intent: ContextIntent
    decision_source: DecisionSource
    input_snapshot_id: str
    context_packet_id: str | None
    candidate_ids: tuple[str, ...]
    selected_candidate_id: str | None
    selected_proposal_id: str | None
    gate_results: tuple[GateResult, ...]
    model_call_id: str | None
    validation_status: str
    validation_errors: tuple[str, ...]
    final_action: str
    final_payload_hash: str
    suppressed_reasons: tuple[str, ...]
    latency_ms: dict[str, int]

    def to_redacted_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["gate_results"] = tuple(asdict(gate) for gate in self.gate_results)
        return _redact(data)


def stable_payload_hash(payload: Any) -> str:
    redacted = _redact(payload)
    raw = json.dumps(redacted, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_s = str(key)
            if key_s.lower() in {
                "path",
                "filepath",
                "file_path",
                "local_path",
                "raw_audio",
                "vector",
            }:
                continue
            redacted_item = _redact(item)
            if redacted_item is not _REDACTED:
                out[key_s] = redacted_item
        return out
    if isinstance(value, (tuple, list)):
        return tuple(item for item in (_redact(item) for item in value) if item is not _REDACTED)
    if isinstance(value, str) and _looks_sensitive(value):
        return _REDACTED
    return value


class _Redacted:
    pass


_REDACTED = _Redacted()


def _looks_sensitive(value: str) -> bool:
    lowered = value.lower()
    return (
        value.startswith("/")
        or lowered.startswith("file://")
        or ":\\" in value
        or lowered.startswith("vector:")
        or lowered.startswith("audio:raw")
    )


__all__ = [
    "AgentDecisionTrace",
    "DecisionSource",
    "GateResult",
    "GateStatus",
    "stable_payload_hash",
]
