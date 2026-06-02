# SPDX-License-Identifier: Apache-2.0
"""Resolve the Learn skill-tree frontier into a live-coach aim.

The aim is a frame, not an evidence claim. It is selected from deterministic
skill-tree state and rendered later through fixed prompt fragments; no user text
or lesson copy enters the live co-host system instruction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vibemix.coach.prompt_fragments import COACHING_AIM_SKILL_PHRASES

from .skill_tree import SkillTree

COACHING_AIM_PRIORITY: tuple[str, ...] = (
    "harmonic_mixing",
    "eq_mixing",
    "transitions",
    "beatmatching",
    "phrasing_performance",
    "deck_control",
)


@dataclass(frozen=True)
class CoachingAim:
    """The current Learn frontier Sven may use as a relevance frame."""

    skill_id: str
    phrase: str


def resolve_coaching_aim(progress: Any | None) -> CoachingAim | None:
    """Return the highest-priority Competent-not-Mastered skill, if any.

    ``SkillTree.compute`` is pure; this helper stays read-only and never writes
    Learn progress. Errors degrade to no aim so a malformed progress object
    cannot wedge live co-host startup.
    """

    if progress is None:
        return None
    try:
        stages = SkillTree().compute(progress)
    except Exception:
        return None
    for skill_id in COACHING_AIM_PRIORITY:
        stage = stages.get(skill_id)
        if stage is None:
            continue
        if stage.stage == "competent" and not stage.mastered:
            phrase = COACHING_AIM_SKILL_PHRASES.get(skill_id)
            if phrase:
                return CoachingAim(skill_id=skill_id, phrase=phrase)
    return None


def resolve_coaching_aim_skill(progress: Any | None) -> str | None:
    """Return only the skill id for prompt builders."""

    aim = resolve_coaching_aim(progress)
    return aim.skill_id if aim is not None else None


__all__ = [
    "COACHING_AIM_PRIORITY",
    "CoachingAim",
    "resolve_coaching_aim",
    "resolve_coaching_aim_skill",
]
