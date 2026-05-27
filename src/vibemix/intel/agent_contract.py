# SPDX-License-Identifier: Apache-2.0
"""Agent-facing musical context and decision contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ContextMode = Literal["prep", "live"]
ContextIntent = Literal[
    "smart_hot_cues",
    "transition_slate",
    "live_next_pill",
    "explain_transition",
    "chat",
]
DecisionAction = Literal["select", "hold", "suppress", "ask"]

SCHEMA_VERSION = "intel_context_v1"


@dataclass(frozen=True, slots=True)
class AgentContextEnvelope:
    """The bounded packet a model may see for one musical decision."""

    schema_version: str
    packet_id: str
    mode: ContextMode
    intent: ContextIntent
    current: dict[str, Any]
    candidates: tuple[dict[str, Any], ...]
    constraints: dict[str, Any]
    allowed_actions: tuple[str, ...]
    allowed_claims: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    citation_scope: dict[str, tuple[str, ...]]
    confidence_policy: dict[str, float | bool]
    claim_ids: tuple[str, ...] = ()
    claim_summary: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class AgentDecision:
    """Structured model or deterministic decision over an issued context."""

    schema_version: str
    action: DecisionAction
    candidate_id: str | None = None
    cue_slot: str | None = None
    timing_text: str | None = None
    spoken_text: str = ""
    cited_claims: tuple[str, ...] = ()
    cited_claim_ids: tuple[str, ...] = ()
    confidence: float = 0.0


__all__ = [
    "SCHEMA_VERSION",
    "AgentContextEnvelope",
    "AgentDecision",
    "ContextIntent",
    "ContextMode",
    "DecisionAction",
]
