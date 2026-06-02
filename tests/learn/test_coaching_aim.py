# SPDX-License-Identifier: Apache-2.0

from vibemix.learn.coaching_aim import resolve_coaching_aim, resolve_coaching_aim_skill
from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import SKILL_MANIFEST


def _make_competent(progress: LearnProgress, skill_id: str) -> None:
    spec = SKILL_MANIFEST[skill_id]
    for lesson_id in spec.lesson_ids:
        progress.lessons[lesson_id] = {
            "completed": True,
            "completed_at": "2026-06-02T00:00:00Z",
            "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)


def test_resolve_coaching_aim_picks_competent_not_mastered_frontier() -> None:
    progress = LearnProgress()
    _make_competent(progress, "harmonic_mixing")

    aim = resolve_coaching_aim(progress)

    assert aim is not None
    assert aim.skill_id == "harmonic_mixing"
    assert "harmonic blends" in aim.phrase
    assert resolve_coaching_aim_skill(progress) == "harmonic_mixing"


def test_resolve_coaching_aim_uses_fixed_priority_when_multiple_are_ready() -> None:
    progress = LearnProgress()
    _make_competent(progress, "deck_control")
    _make_competent(progress, "eq_mixing")

    aim = resolve_coaching_aim(progress)

    assert aim is not None
    assert aim.skill_id == "eq_mixing"


def test_resolve_coaching_aim_abstains_when_none_or_all_mastered() -> None:
    assert resolve_coaching_aim(None) is None
    assert resolve_coaching_aim(LearnProgress()) is None

    progress = LearnProgress()
    _make_competent(progress, "harmonic_mixing")
    progress.skills["harmonic_mixing"]["mastered"] = True
    progress.skills["harmonic_mixing"]["live_proof_count"] = 3

    assert resolve_coaching_aim(progress) is None
