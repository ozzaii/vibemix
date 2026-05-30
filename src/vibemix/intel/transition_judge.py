# SPDX-License-Identifier: Apache-2.0
"""The Vibe Judge — a deterministic move-quality engine that DECIDES.

Gemini voices; the Judge decides. Every signal is measurable-or-None: a
confidently-wrong score is its own hallucination class, so the engine abstains
by construction. verdict_state='abstained' is a first-class output, not a number.

Import-light (numpy + harmonics + pure scorers). NO audio capture, NO model
client, NO Tauri — same discipline as the rest of intel/.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from vibemix.state.live_signal import LaneObservation, LiveSignalFrame

# At least this many independent non-null signals (incl. >=1 executed-mix signal)
# are required to voice a verdict. Below it -> abstain.
MIN_TRUSTWORTHY_SIGNALS = 2

VerdictState = Literal["judged", "abstained"]


@dataclass(frozen=True, slots=True)
class TransitionVerdict:
    verdict_state: VerdictState
    score: float | None
    confidence: float
    components: dict[str, float] = field(default_factory=dict)
    risk_flags: tuple[str, ...] = ()
    abstain_reason: str | None = None


def judge_transition(frame: LiveSignalFrame) -> TransitionVerdict:
    """Return a measured verdict, or abstain. Abstain is the safe default."""
    # --- Activation gates (honest-null preconditions) ---
    if frame.policy != "supported_verdict":
        return _abstain("policy_not_supported_verdict")
    if not frame.routing_enabled:
        return _abstain("routing_disabled")

    a = frame.lane("A")
    b = frame.lane("B")
    if a is None or b is None:
        return _abstain("missing_lane")

    # --- Signals (each in [0,1] or None=abstain). Scoring lands in later tasks. ---
    components: dict[str, float] = {}
    signals: dict[str, float | None] = {
        "harmonic": _harmonic_signal(a, b),
        "bass_collision": _bass_collision_signal(a, b),
    }
    for name, value in signals.items():
        if value is not None:
            components[name] = value

    if len(components) < MIN_TRUSTWORTHY_SIGNALS:
        return _abstain("insufficient_trustworthy_signals")

    score = sum(components.values()) / len(components)
    confidence = len(components) / float(len(signals))
    return TransitionVerdict(
        verdict_state="judged",
        score=round(score, 4),
        confidence=round(confidence, 4),
        components={k: round(v, 4) for k, v in components.items()},
    )


def _abstain(reason: str) -> TransitionVerdict:
    return TransitionVerdict(
        verdict_state="abstained", score=None, confidence=0.0, abstain_reason=reason
    )


def _harmonic_signal(a: LaneObservation, b: LaneObservation) -> float | None:
    """Stub — real logic in a later task."""
    return None


def _bass_collision_signal(a: LaneObservation, b: LaneObservation) -> float | None:
    """Stub — real logic in a later task."""
    return None
