# SPDX-License-Identifier: Apache-2.0
"""Skill-tree engine unit suite — fill math + Competent gate + drift.

Phase 102 Plan 02 (v11.0 "Earned"). The engine ``skill_tree.SkillTree.compute``
DERIVES a quality-weighted Competent ``learn_fill`` per skill from the persisted
lesson/recital history and AND-gates Competent behind the recital honest-score
flag (``course_N_unlocked``). The decisive product spine is COMP-02: a 100%
click-through (every lesson done, but the gating recital never passed) can NEVER
reach Competent — the stage stays ``"locked"``. This is the "nothing is given;
every notch is earned" anti-slop gate in executable form.

REQ-IDs: SKILL-01 (6 skills resolve a stage), SKILL-02 (pure / no side effects),
SKILL-03 (manifest↔curriculum drift), COMP-01 (quality-weighted fill ordering +
monotonic), COMP-02 (HEADLINE recital AND-gate).
"""
from __future__ import annotations

import copy

from vibemix.learn.curriculum import CURRICULUM
from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import (
    COMPETENT_THRESHOLD,
    SKILL_MANIFEST,
    SkillProgress,
    SkillTree,
    WEIGHT_FIRST_TRY,
    WEIGHT_FLOOR,
    WEIGHT_WITH_STRIKES,
)

# The 6 REQ-locked skill ids (CONTEXT GA1 order). Mirrors progress._SKILL_IDS.
_EXPECTED_SKILLS = {
    "deck_control",
    "beatmatching",
    "eq_mixing",
    "harmonic_mixing",
    "transitions",
    "phrasing_performance",
}


def _complete_all(progress: LearnProgress, lesson_ids, *, strikes: int) -> None:
    """First-try (``strikes=0``) or with-strikes completion of each lesson."""
    for lid in lesson_ids:
        progress.lessons[lid] = {
            "completed": True,
            "completed_at": "2026-05-29T00:00:00Z",
            "strikes_used": int(strikes),
        }


# ---------------------------------------------------------------------------
# SKILL-01: 6 skills, each resolving a stage from a LearnProgress
# ---------------------------------------------------------------------------
def test_six_skills_present_with_stage() -> None:
    """``compute`` returns exactly the 6 skill ids, each with a valid stage."""
    result = SkillTree().compute(LearnProgress())
    assert set(result) == _EXPECTED_SKILLS
    for skill_id, sp in result.items():
        assert isinstance(sp, SkillProgress)
        assert sp.skill_id == skill_id
        assert sp.stage in {"locked", "competent", "mastered"}


# ---------------------------------------------------------------------------
# SKILL-02: compute is pure — deterministic + no input mutation
# ---------------------------------------------------------------------------
def test_compute_is_pure_no_side_effects() -> None:
    """Twice on the same progress returns equal results; input unmutated."""
    progress = LearnProgress()
    _complete_all(progress, ("L1.02", "L1.03"), strikes=0)
    before = copy.deepcopy(progress.to_dict())

    tree = SkillTree()
    first = tree.compute(progress)
    second = tree.compute(progress)

    assert first == second  # deterministic — no clock, no I/O
    assert progress.to_dict() == before  # input not mutated


# ---------------------------------------------------------------------------
# SKILL-03: every manifest lesson id exists in CURRICULUM (anti-drift)
# ---------------------------------------------------------------------------
def test_manifest_lesson_ids_exist_in_curriculum() -> None:
    """No SKILL_MANIFEST lesson id may dangle off the real curriculum."""
    for skill_id, spec in SKILL_MANIFEST.items():
        for lesson_id in spec.lesson_ids:
            assert lesson_id in CURRICULUM, (
                f"{skill_id} references {lesson_id!r} which is not in CURRICULUM"
            )


def test_manifest_declares_exactly_six_skills() -> None:
    """The manifest is the 6-skill REQ-locked set — no more, no less."""
    assert set(SKILL_MANIFEST) == _EXPECTED_SKILLS


def test_manifest_gates_are_recital_unlock_flags() -> None:
    """Every skill gate names a real ``course_N_unlocked`` LearnProgress attr."""
    fresh = LearnProgress()
    for skill_id, spec in SKILL_MANIFEST.items():
        assert spec.gate in {"course_2_unlocked", "course_3_unlocked"}
        assert hasattr(fresh, spec.gate), (
            f"{skill_id} gate {spec.gate!r} is not a LearnProgress attribute"
        )


# ---------------------------------------------------------------------------
# COMP-01: quality-weighted fill — first-try > with-strikes > click-through
# ---------------------------------------------------------------------------
def test_quality_weighted_fill_ordering() -> None:
    """All-first-try fills strictly MORE than all-with-strikes, which fills
    strictly MORE than all-click-through (absent)."""
    spec = SKILL_MANIFEST["deck_control"]
    lessons = spec.lesson_ids
    tree = SkillTree()

    first_try = LearnProgress()
    _complete_all(first_try, lessons, strikes=0)
    with_strikes = LearnProgress()
    _complete_all(with_strikes, lessons, strikes=2)
    click_through = LearnProgress()  # no lessons recorded = floor

    fill_first = tree.compute(first_try)["deck_control"].learn_fill
    fill_strikes = tree.compute(with_strikes)["deck_control"].learn_fill
    fill_click = tree.compute(click_through)["deck_control"].learn_fill

    # All fills in [0, 1].
    for f in (fill_first, fill_strikes, fill_click):
        assert 0.0 <= f <= 1.0
    # Strict ordering — quality matters.
    assert fill_first > fill_strikes > fill_click
    # Endpoints land on the weight constants.
    assert fill_first == WEIGHT_FIRST_TRY
    assert fill_strikes == WEIGHT_WITH_STRIKES
    assert fill_click == WEIGHT_FLOOR


def test_partial_completion_fill_is_fractional() -> None:
    """Completing half a skill's lessons first-try yields fill in (0, 1)."""
    spec = SKILL_MANIFEST["transitions"]  # 5 lessons
    lessons = spec.lesson_ids
    half = lessons[: len(lessons) // 2]
    progress = LearnProgress()
    _complete_all(progress, half, strikes=0)
    fill = SkillTree().compute(progress)["transitions"].learn_fill
    expected = WEIGHT_FIRST_TRY * len(half) / len(lessons)
    assert fill == expected
    assert 0.0 < fill < 1.0


def test_fill_monotonic_on_reload() -> None:
    """Once ``completed=True``, contribution is fixed by stored ``strikes_used``;
    a fewer-strikes replay only RAISES fill (never decreases) — Pitfall 4(b)."""
    spec = SKILL_MANIFEST["deck_control"]
    lessons = spec.lesson_ids
    tree = SkillTree()

    # First pass: all with strikes.
    progress = LearnProgress()
    _complete_all(progress, lessons, strikes=2)
    fill_v1 = tree.compute(progress)["deck_control"].learn_fill

    # Reload (round-trip through dict) — deterministic, identical fill.
    reloaded = LearnProgress.from_dict(progress.to_dict())
    fill_v1_reload = tree.compute(reloaded)["deck_control"].learn_fill
    assert fill_v1_reload == fill_v1  # no jiggle across reload

    # Replay one lesson first-try (fewer strikes) — fill must RISE, never fall.
    reloaded.lessons[lessons[0]] = {
        "completed": True,
        "completed_at": "2026-05-29T01:00:00Z",
        "strikes_used": 0,
    }
    fill_v2 = tree.compute(reloaded)["deck_control"].learn_fill
    assert fill_v2 >= fill_v1


# ---------------------------------------------------------------------------
# COMP-02 (HEADLINE): 100% click-through without recital is NOT Competent
# ---------------------------------------------------------------------------
def test_full_clickthrough_without_recital_not_competent() -> None:
    """The product spine: every lesson first-try (fill == 1.0) but the gating
    recital flag is False → the skill is NOT competent and stays ``locked``.

    Nothing is given; every notch is earned. A 100% click-through can never
    cross into Competent regardless of threshold — the recital is AND-ed in.
    """
    spec = SKILL_MANIFEST["deck_control"]  # gate = course_2_unlocked
    progress = LearnProgress()
    _complete_all(progress, spec.lesson_ids, strikes=0)
    progress.course_2_unlocked = False  # recital NOT passed
    progress.course_3_unlocked = False

    sp = SkillTree().compute(progress)["deck_control"]

    assert sp.learn_fill == 1.0  # the lessons are fully done
    assert sp.competent is False  # but Competent is gated on the recital
    assert sp.stage == "locked"  # and the stage stays locked


def test_competent_requires_threshold_and_recital() -> None:
    """Competent iff ``fill >= COMPETENT_THRESHOLD`` AND the gating recital
    flag is True. Toggling either off drops out of Competent."""
    spec = SKILL_MANIFEST["deck_control"]  # gate = course_2_unlocked
    tree = SkillTree()

    # Full fill + recital passed → competent.
    both = LearnProgress()
    _complete_all(both, spec.lesson_ids, strikes=0)
    both.course_2_unlocked = True
    sp_both = tree.compute(both)["deck_control"]
    assert sp_both.learn_fill >= COMPETENT_THRESHOLD
    assert sp_both.competent is True
    assert sp_both.stage == "competent"

    # Recital passed but fill below threshold (no lessons) → NOT competent.
    recital_only = LearnProgress()
    recital_only.course_2_unlocked = True
    sp_recital = tree.compute(recital_only)["deck_control"]
    assert sp_recital.learn_fill < COMPETENT_THRESHOLD
    assert sp_recital.competent is False
    assert sp_recital.stage == "locked"

    # Fill above threshold but recital NOT passed → NOT competent (headline).
    fill_only = LearnProgress()
    _complete_all(fill_only, spec.lesson_ids, strikes=0)
    fill_only.course_2_unlocked = False
    sp_fill = tree.compute(fill_only)["deck_control"]
    assert sp_fill.learn_fill >= COMPETENT_THRESHOLD
    assert sp_fill.competent is False
    assert sp_fill.stage == "locked"


def test_phrasing_performance_gates_on_course_3_unlocked() -> None:
    """Open-Q#1: phrasing_performance (C3 play-mode, no C3 recital) is gated on
    the honest C2-recital pass that earns play-mode entry — course_3_unlocked."""
    assert SKILL_MANIFEST["phrasing_performance"].gate == "course_3_unlocked"


# ---------------------------------------------------------------------------
# Mastered overlay (Phase 103 writes the live-portion; engine reads it)
# ---------------------------------------------------------------------------
def test_mastered_live_portion_promotes_stage() -> None:
    """When the stored live-portion marks a skill ``mastered``, stage is
    ``mastered`` (the live-proof overlay outranks competent/locked)."""
    progress = LearnProgress()
    progress.skills["deck_control"] = {
        "live_proof_count": 3,
        "mastered": True,
        "first_mastered_at": "2026-05-29T02:00:00Z",
    }
    sp = SkillTree().compute(progress)["deck_control"]
    assert sp.mastered is True
    assert sp.live_proof_count == 3
    assert sp.first_mastered_at == "2026-05-29T02:00:00Z"
    assert sp.stage == "mastered"


def test_live_portion_defaults_when_absent() -> None:
    """A skill with no stored live-portion reads safe defaults (count 0,
    not mastered, ts None) — never raises."""
    progress = LearnProgress()
    progress.skills = {}  # simulate a sparse/missing live block
    sp = SkillTree().compute(progress)["deck_control"]
    assert sp.live_proof_count == 0
    assert sp.mastered is False
    assert sp.first_mastered_at is None
