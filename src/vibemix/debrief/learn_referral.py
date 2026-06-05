# SPDX-License-Identifier: Apache-2.0
"""Deterministic Learn referrals for post-session debrief drills.

The drills are model-authored, but the practice route is not. This module maps
grounded drill text onto existing authored Learn lessons so the debrief can
say "practice this next" without letting the LLM invent lesson ids.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from vibemix.learn.curriculum import COURSE_REGISTRY, CURRICULUM
from vibemix.learn.skill_tree import SKILL_MANIFEST

__all__ = ["LearnReferral", "learn_referral_for_drill"]


@dataclass(frozen=True, slots=True)
class LearnReferral:
    """Visible debrief -> Learn bridge for one authored lesson."""

    lesson_id: str
    course_id: str
    course_label: str
    skill_id: str
    skill_label: str
    title: str
    reason: str
    cta: str


@dataclass(frozen=True, slots=True)
class _ReferralRule:
    lesson_id: str
    reason: str
    tokens: tuple[str, ...]


_SKILL_LABELS: dict[str, str] = {
    "deck_control": "deck control",
    "beatmatching": "beatmatching",
    "eq_mixing": "EQ mixing",
    "harmonic_mixing": "harmonic mixing",
    "transitions": "transitions",
    "phrasing_performance": "phrasing",
}

_LESSON_SKILL_IDS: dict[str, str] = {
    lesson_id: skill_id
    for skill_id, spec in SKILL_MANIFEST.items()
    for lesson_id in spec.lesson_ids
}

_RULES: tuple[_ReferralRule, ...] = (
    _ReferralRule(
        "L2.13",
        "Debrief found a train-wreck or recovery moment; rehearse diagnosing it calmly.",
        ("train wreck", "trainwreck", "recovery", "bail out", "bailout"),
    ),
    _ReferralRule(
        "L2.01",
        "Debrief found tempo or phase drift; rehearse locking the owned decks by ear.",
        (
            "beatmatch",
            "beatmatching",
            "beatmatch_graded",
            "off-bpm",
            "off bpm",
            "tempo drift",
            "phase drift",
            "drift",
            "kicks",
            "kick alignment",
            "bpm",
        ),
    ),
    _ReferralRule(
        "L2.11",
        "Debrief found a harmonic clash; rehearse Camelot decisions with real library pairs.",
        ("camelot", "key clash", "harmonic", "off-key", "off key", "melody clash"),
    ),
    _ReferralRule(
        "L2.08",
        "Debrief found drop-timing pressure; rehearse clean drop swaps before the next set.",
        ("drop swap", "drop timing", "missed drop", "at the drop", "drop hit"),
    ),
    _ReferralRule(
        "L2.12",
        "Debrief found phrase timing drift; rehearse counting the entry window.",
        ("phrase", "off-phrase", "off phrase", "bar count", "32-bar", "16-bar"),
    ),
    _ReferralRule(
        "L2.05",
        "Debrief found low-end collision; rehearse handing basslines over one at a time.",
        (
            "bassline",
            "two bass",
            "both bass",
            "bass collision",
            "low-end mud",
            "low end mud",
            "stacked lows",
            "kick handoff",
        ),
    ),
    _ReferralRule(
        "L2.06",
        "Debrief found filter-transition work; rehearse a controlled filter fade.",
        ("filter", "high-pass", "low-pass", "high pass", "low pass"),
    ),
    _ReferralRule(
        "L2.07",
        "Debrief found echo-out timing; rehearse using echo as a deliberate exit.",
        ("echo-out", "echo out", "echo"),
    ),
    _ReferralRule(
        "L2.10",
        "Debrief found cue-point planning work; rehearse hot cues before the next live pass.",
        ("hot cue", "hot-cue", "memory cue", "cue point"),
    ),
    _ReferralRule(
        "L2.04",
        "Debrief found EQ handoff work; rehearse one-band ownership during the blend.",
        ("eq", "equalizer", "mid", "mids", "high", "highs", "band"),
    ),
    _ReferralRule(
        "L2.03",
        "Debrief found blend-control work; rehearse a long transition with stable phrasing.",
        ("long blend", "crossfader", "transition"),
    ),
)


def learn_referral_for_drill(drill: Mapping[str, object]) -> LearnReferral | None:
    """Map one debrief drill to an authored Learn lesson, when confident."""
    text = _drill_text(drill)
    if not text:
        return None
    lowered = f" {text.lower()} "
    for rule in _RULES:
        if not any(token in lowered for token in rule.tokens):
            continue
        meta = CURRICULUM.get(rule.lesson_id)
        if meta is None:
            continue
        course = COURSE_REGISTRY.get(meta.course_id)
        skill_id = _LESSON_SKILL_IDS.get(rule.lesson_id, "phrasing_performance")
        skill_label = _SKILL_LABELS.get(skill_id, "DJ skill")
        return LearnReferral(
            lesson_id=rule.lesson_id,
            course_id=meta.course_id,
            course_label=course.label if course is not None else meta.course_id,
            skill_id=skill_id,
            skill_label=skill_label,
            title=meta.title,
            reason=rule.reason,
            cta=f"Practice {meta.title}",
        )
    return None


def _drill_text(drill: Mapping[str, object]) -> str:
    fields = (
        drill.get("situation"),
        drill.get("behavior"),
        drill.get("impact"),
        drill.get("action_recommended"),
        drill.get("citation"),
    )
    parts: list[str] = []
    for value in fields:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(text)
    return " ".join(parts)
