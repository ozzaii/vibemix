# SPDX-License-Identifier: Apache-2.0
"""Deterministic move grading for live transition suggestions.

This is UI/cohost language over already-grounded transition evidence. It does
not score audio itself; it compresses the section-scorer result into a small,
stable vocabulary the pill can animate and the cohost can cite.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from vibemix.intel.transition_scorer import TransitionCandidate

MoveGradeSlug = str

_LABELS: dict[MoveGradeSlug, str] = {
    "negative": "NEG",
    "mid": "MID",
    "clean": "CLEAN",
    "sexy": "SEXY",
    "bomb": "BOMB",
    "lit_aff": "LIT AFF",
}

_XP: dict[MoveGradeSlug, int] = {
    "negative": 0,
    "mid": 8,
    "clean": 28,
    "sexy": 48,
    "bomb": 72,
    "lit_aff": 100,
}

_INTENSITY: dict[MoveGradeSlug, int] = {
    "negative": 0,
    "mid": 24,
    "clean": 48,
    "sexy": 66,
    "bomb": 84,
    "lit_aff": 100,
}

_SEVERE_RISKS = frozenset(
    {
        "harmonic_clash",
        "tempo_jump",
        "cue_unusable",
        "section_too_short",
        "played_track",
    }
)

_CARE_RISKS = frozenset(
    {
        "timing_low_confidence",
        "phrase_unknown",
        "phrase_short",
        "cue_low_confidence",
        "key_unknown",
        "bpm_unknown",
        "source_loop_recent",
        "blend_active",
        "role_unknown",
        "role_tension",
    }
)

_REASON_BY_RISK: tuple[tuple[str, str], ...] = (
    ("harmonic_clash", "key clash"),
    ("tempo_jump", "tempo jump"),
    ("cue_unusable", "cue not ready"),
    ("section_too_short", "section too short"),
    ("timing_low_confidence", "timing needs care"),
    ("phrase_unknown", "phrase needs care"),
    ("phrase_short", "short phrase"),
    ("cue_low_confidence", "cue needs care"),
    ("key_unknown", "key unknown"),
    ("bpm_unknown", "bpm unknown"),
    ("blend_active", "blend already active"),
    ("source_loop_recent", "loop held"),
)


@dataclass(frozen=True, slots=True)
class MoveGrade:
    slug: MoveGradeSlug
    label: str
    xp: int
    intensity: int
    sentiment: str
    reason: str
    deserved: bool
    overdrive: bool
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def grade_transition_candidate(candidate: TransitionCandidate) -> dict[str, Any]:
    """Return the wire grade for a grounded ``TransitionCandidate``."""
    return grade_transition(
        score=candidate.score,
        confidence=candidate.confidence,
        components=asdict(candidate.components),
        risk_flags=candidate.risk_flags,
    ).to_dict()


def grade_transition_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a move-grade dict for a transition payload, or ``None`` for no payload."""
    if payload is None:
        return None
    components = payload.get("scores")
    risk_flags = payload.get("risk_flags")
    return grade_transition(
        score=payload.get("score"),
        confidence=payload.get("confidence"),
        components=components if isinstance(components, dict) else {},
        risk_flags=risk_flags if isinstance(risk_flags, (list, tuple, set)) else (),
    ).to_dict()


def grade_transition(
    *,
    score: float | int | None,
    confidence: float | int | None,
    components: dict[str, Any],
    risk_flags: tuple[str, ...] | list[str] | set[str],
) -> MoveGrade:
    """Compress transition score evidence into the pill's move-grade vocabulary."""
    clean_score = _float01(score)
    clean_confidence = _float01(confidence)
    risks = tuple(str(flag) for flag in risk_flags if isinstance(flag, str) and flag)
    component_scores = _component_scores(components)
    operability_core = min(
        component_scores["harmonic"],
        component_scores["bpm"],
        component_scores["role"],
        component_scores["phrase_alignment"],
        component_scores["cue_operability"],
    )
    payoff_core = min(
        component_scores["semantic"],
        component_scores["harmonic"],
        component_scores["bpm"],
        component_scores["energy_shape"],
        component_scores["role"],
        component_scores["phrase_alignment"],
        component_scores["cue_operability"],
    )
    severe = any(flag in _SEVERE_RISKS for flag in risks)
    risk_penalty = component_scores["risk_penalty"]

    if severe and (clean_score < 0.72 or clean_confidence < 0.78 or risk_penalty >= 0.28):
        return _grade("negative", _reason_for_risks(risks, default="risk too high"), 0.0)
    if clean_score < 0.45 or clean_confidence < 0.35:
        return _grade("negative", _reason_for_risks(risks, default="not enough support"), clean_confidence)

    if (
        clean_score >= 0.90
        and clean_confidence >= 0.86
        and payoff_core >= 0.82
        and not risks
    ):
        return _grade("lit_aff", "everything clicks", clean_confidence)
    if (
        clean_score >= 0.84
        and clean_confidence >= 0.78
        and payoff_core >= 0.74
        and not severe
    ):
        return _grade("bomb", _positive_reason(component_scores, "big payoff"), clean_confidence)
    if (
        clean_score >= 0.76
        and clean_confidence >= 0.70
        and operability_core >= 0.66
        and not severe
    ):
        return _grade("sexy", _positive_reason(component_scores, "smooth blend"), clean_confidence)
    if (
        clean_score >= 0.60
        and clean_confidence >= 0.60
        and operability_core >= 0.70
        and not severe
    ):
        return _grade("clean", _positive_reason(component_scores, "clean fit"), clean_confidence)

    care_reason = _reason_for_risks(
        tuple(flag for flag in risks if flag in _CARE_RISKS),
        default="works with care",
    )
    return _grade("mid", care_reason, clean_confidence)


def _grade(slug: MoveGradeSlug, reason: str, confidence: float) -> MoveGrade:
    return MoveGrade(
        slug=slug,
        label=_LABELS[slug],
        xp=_XP[slug],
        intensity=_INTENSITY[slug],
        sentiment="negative" if slug == "negative" else "neutral" if slug == "mid" else "positive",
        reason=reason,
        deserved=slug not in {"negative", "mid"},
        overdrive=slug == "lit_aff",
        confidence=round(_float01(confidence), 3),
    )


def _component_scores(raw: dict[str, Any]) -> dict[str, float]:
    return {
        "semantic": _float01(raw.get("semantic"), default=0.50),
        "harmonic": _float01(raw.get("harmonic"), default=0.50),
        "bpm": _float01(raw.get("bpm"), default=0.50),
        "energy_shape": _float01(raw.get("energy_shape"), default=0.50),
        "role": _float01(raw.get("role"), default=0.50),
        "phrase_alignment": _float01(raw.get("phrase_alignment"), default=0.50),
        "cue_operability": _float01(raw.get("cue_operability"), default=0.50),
        "taste": _float01(raw.get("taste"), default=0.50),
        "novelty": _float01(raw.get("novelty"), default=0.50),
        "risk_penalty": _float01(raw.get("risk_penalty"), default=0.0),
    }


def _positive_reason(components: dict[str, float], default: str) -> str:
    if components["phrase_alignment"] >= 0.86 and components["cue_operability"] >= 0.82:
        return "phrase and cue locked"
    if components["harmonic"] >= 0.88 and components["bpm"] >= 0.82:
        return "key and tempo locked"
    if components["energy_shape"] >= 0.84 and components["role"] >= 0.80:
        return "energy lift fits"
    if components["semantic"] >= 0.86:
        return "vibe match"
    return default


def _reason_for_risks(risks: tuple[str, ...], *, default: str) -> str:
    for risk, reason in _REASON_BY_RISK:
        if risk in risks:
            return reason
    return default


def _float01(value: Any, *, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed):
        return default
    return max(0.0, min(1.0, parsed))


__all__ = [
    "MoveGrade",
    "grade_transition",
    "grade_transition_candidate",
    "grade_transition_payload",
]
