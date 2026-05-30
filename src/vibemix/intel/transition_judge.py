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

from vibemix.state import harmonics
from vibemix.state.live_signal import LaneObservation, LiveSignalFrame

# At least this many independent non-null signals (incl. >=1 executed-mix signal)
# are required to voice a verdict. Below it -> abstain.
MIN_TRUSTWORTHY_SIGNALS = 2

# Camelot adjacency is a PRIOR (smart pairing), not audible-quality ground truth.
_HARMONIC_COMPATIBLE_PRIOR = 0.75

# >=25% of a lane's energy in sub+low = "bass is up" on that lane.
_BASS_PRESENT_RATIO = 0.25

VerdictState = Literal["judged", "abstained"]

# events.jsonl event kind for a persisted Judge verdict (debrief/replay/calibration).
TRANSITION_JUDGED_KIND = "transition_judged"


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

    flags: list[str] = []
    if components.get("harmonic") == 0.0:
        flags.append("harmonic_clash")
    if components.get("bass_collision") == 0.0:
        flags.append("bass_collision")

    score = sum(components.values()) / len(components)
    confidence = len(components) / float(len(signals))
    return TransitionVerdict(
        verdict_state="judged",
        score=round(score, 4),
        confidence=round(confidence, 4),
        components={k: round(v, 4) for k, v in components.items()},
        risk_flags=tuple(flags),
    )


def _abstain(reason: str) -> TransitionVerdict:
    return TransitionVerdict(
        verdict_state="abstained", score=None, confidence=0.0, abstain_reason=reason
    )


def verdict_event_fields(
    verdict: TransitionVerdict,
    *,
    track_a: str | None,
    track_b: str | None,
    citation_id: str | None = None,
) -> dict[str, object]:
    """Build the events.jsonl field payload for a Judge verdict.

    The caller logs via ``recorder.log_event(TRANSITION_JUDGED_KIND, **fields)``.
    BOTH judged and abstained verdicts produce a record — abstains are
    load-bearing for calibration (they prove the Judge stays silent correctly,
    and let debrief show "saw the blend, didn't grade it"). Honest-null: `score`
    is None on abstain, never a fabricated number. The result is JSON-serializable
    (events.jsonl is JSONL).
    """
    fields: dict[str, object] = {
        "verdict_state": verdict.verdict_state,
        "score": verdict.score,
        "confidence": verdict.confidence,
        "track_a": track_a,
        "track_b": track_b,
    }
    if verdict.components:
        fields["components"] = dict(verdict.components)
    if verdict.risk_flags:
        fields["risk_flags"] = list(verdict.risk_flags)
    if verdict.abstain_reason is not None:
        fields["abstain_reason"] = verdict.abstain_reason
    if citation_id is not None:
        fields["citation_id"] = citation_id
    return fields


def _harmonic_signal(a: LaneObservation, b: LaneObservation) -> float | None:
    """Camelot compatibility. clash=0.0, compatible=capped prior, else abstain.

    The one structurally-sound dimension: deterministic, metadata-grounded, works
    on every rig. Abstains on untrusted provenance or unknown/cross-letter keys —
    a guess there is exactly the slop we refuse.
    """
    if not (a.source_trusted and b.source_trusted):
        return None
    if a.camelot is None or b.camelot is None:
        return None
    if harmonics.is_clash(a.camelot, b.camelot):
        return 0.0
    if harmonics.compatible(a.camelot, b.camelot):
        return _HARMONIC_COMPATIBLE_PRIOR
    # Neither a proven clash nor a proven compatible (e.g. cross-letter) -> abstain.
    return None


def _bass_energy(lane: LaneObservation) -> float | None:
    if lane.bands is None:
        return None
    sub = lane.bands.get("sub")
    low = lane.bands.get("low")
    if sub is None or low is None:
        return None
    return float(sub) + float(low)


def _bass_collision_signal(a: LaneObservation, b: LaneObservation) -> float | None:
    """Coarse binary: both basslines up = masking mud = 0.0; one killed = clean = 1.0.

    No fine dB/Hz claim — deck features carry no per-band phase. Abstains when
    either lane lacks a per-lane spectrum (master-only / silent lane).
    """
    ba = _bass_energy(a)
    bb = _bass_energy(b)
    if ba is None or bb is None:
        return None
    both_present = ba >= _BASS_PRESENT_RATIO and bb >= _BASS_PRESENT_RATIO
    return 0.0 if both_present else 1.0
