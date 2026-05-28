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
from pathlib import Path

import pytest

from vibemix.learn.curriculum import CURRICULUM
from vibemix.learn.progress import LearnProgress, load_progress, save_progress
from vibemix.learn.skill_tree import (
    COMPETENT_THRESHOLD,
    SKILL_MANIFEST,
    SkillProgress,
    SkillTree,
    WEIGHT_FIRST_TRY,
    WEIGHT_FLOOR,
    WEIGHT_WITH_STRIKES,
    record_live_demo,
)

# A fixed injected timestamp — record_live_demo never calls a clock; the caller
# supplies ``now`` so the mutator stays deterministic (102 precedent).
_NOW = "2026-05-29T12:00:00Z"
# The lessons + recital gate that make eq_mixing Competent (its gate is
# course_3_unlocked; lessons L1.14/L2.04/L2.05). Used as the primary Competent
# fixture across the record_live_demo tests.
_EQ_LESSONS = SKILL_MANIFEST["eq_mixing"].lesson_ids


def _competent_eq_progress() -> LearnProgress:
    """A LearnProgress where eq_mixing is Competent (lessons done first-try
    AND the gating recital passed) — so record_live_demo is NOT a no-op."""
    progress = LearnProgress()
    _complete_all(progress, _EQ_LESSONS, strikes=0)
    progress.course_3_unlocked = True  # the eq_mixing recital gate
    assert SkillTree().compute(progress)["eq_mixing"].competent is True
    return progress

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


def test_import_time_assertion_catches_typod_gate() -> None:
    """IN-03: a typo'd gate must fail LOUD at the import-time anti-drift check
    (``_assert_manifest_matches_curriculum``) exactly like a lesson-id typo —
    not fail silent at runtime by pinning the skill locked forever via
    ``getattr(progress, gate, False)``'s False fallback."""
    from vibemix.learn.skill_tree import (
        SkillSpec,
        _assert_manifest_matches_curriculum,
    )

    good = dict(SKILL_MANIFEST)
    # Swap in a gate that is NOT a LearnProgress field.
    bad_spec = SkillSpec(
        lesson_ids=SKILL_MANIFEST["deck_control"].lesson_ids,
        gate="course_99_unlocked",
    )
    patched = {**good, "deck_control": bad_spec}

    import vibemix.learn.skill_tree as mod

    original = mod.SKILL_MANIFEST
    try:
        mod.SKILL_MANIFEST = patched
        with pytest.raises(AssertionError, match="course_99_unlocked"):
            _assert_manifest_matches_curriculum()
    finally:
        mod.SKILL_MANIFEST = original


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


def test_compute_never_raises_on_non_numeric_live_proof_count() -> None:
    """WR-01: a parseable v2 JSON carrying a non-numeric ``live_proof_count``
    (hand-edit / partial Phase-103 write / future drift) must NOT crash
    ``compute()``. ``from_dict`` only isinstance-checks the top-level ``skills``
    dict, not inner value types, so a string flows straight through to the
    engine — which mirrors ``_weight_for``'s guard and degrades it to 0 instead
    of raising the uncaught ``ValueError`` that contradicts the never-raises
    contract."""
    raw = {
        "schema_version": 2,
        "lessons": {},
        "skills": {
            "deck_control": {
                "live_proof_count": "x",  # non-numeric — would crash a bare int()
                "mastered": False,
                "first_mastered_at": None,
            }
        },
    }
    progress = LearnProgress.from_dict(raw)  # survives — no inner type sanitisation

    result = SkillTree().compute(progress)  # must NOT raise

    assert result["deck_control"].live_proof_count == 0  # garbage → safe default


# ---------------------------------------------------------------------------
# Phase 103 (MAST-01 / MAST-04): record_live_demo writes the live-portion
# ---------------------------------------------------------------------------
def test_record_live_demo_flips_mastered_at_threshold() -> None:
    """MAST-04: a Competent skill flips ``mastered=True`` at exactly the
    skill's ``mastered_threshold`` (3) grounded demos — and not before.

    The flip-at-N behaviour is the contract, not the literal N (102 precedent:
    the ordering is the contract, not the numbers) — so we read the threshold
    off the manifest rather than hard-coding 3."""
    progress = _competent_eq_progress()
    threshold = SKILL_MANIFEST["eq_mixing"].mastered_threshold

    # Each call below the threshold increments the count but stays NOT mastered.
    for i in range(1, threshold):
        record_live_demo(progress, "eq_mixing", now=_NOW)
        block = progress.skills["eq_mixing"]
        assert block["live_proof_count"] == i
        assert block["mastered"] is False, f"flipped early at demo {i}"
        assert block["first_mastered_at"] is None

    # The Nth grounded demo flips it.
    record_live_demo(progress, "eq_mixing", now=_NOW)
    block = progress.skills["eq_mixing"]
    assert block["live_proof_count"] == threshold
    assert block["mastered"] is True
    assert block["first_mastered_at"] == _NOW


def test_first_mastered_at_idempotent() -> None:
    """MAST-04 / Pitfall 2: ``first_mastered_at`` is stamped ONLY on the
    not-mastered→mastered transition; later demos never overwrite it, but
    ``live_proof_count`` keeps incrementing past N."""
    progress = _competent_eq_progress()
    threshold = SKILL_MANIFEST["eq_mixing"].mastered_threshold

    # Reach the flip.
    for _ in range(threshold):
        record_live_demo(progress, "eq_mixing", now=_NOW)
    stamped_at = progress.skills["eq_mixing"]["first_mastered_at"]
    assert stamped_at == _NOW

    # Two MORE demos at a DIFFERENT timestamp must NOT re-stamp first_mastered_at.
    later = "2026-06-01T09:30:00Z"
    record_live_demo(progress, "eq_mixing", now=later)
    record_live_demo(progress, "eq_mixing", now=later)
    block = progress.skills["eq_mixing"]
    assert block["first_mastered_at"] == stamped_at  # byte-equal, never moved
    assert block["mastered"] is True
    assert block["live_proof_count"] == threshold + 2  # count keeps climbing


def test_live_demo_noop_when_not_competent() -> None:
    """MAST-01: a sub-Competent skill (lessons done but recital gate False)
    ignores live events entirely — record_live_demo writes NOTHING, no matter
    how many times it is called (no buffered backfill)."""
    progress = LearnProgress()
    _complete_all(progress, _EQ_LESSONS, strikes=0)
    progress.course_3_unlocked = False  # recital NOT passed → NOT Competent
    assert SkillTree().compute(progress)["eq_mixing"].competent is False

    for _ in range(10):
        record_live_demo(progress, "eq_mixing", now=_NOW)

    # No buffered backfill: the live-portion stays at its safe defaults.
    block = progress.skills["eq_mixing"]
    assert block["live_proof_count"] == 0
    assert block["mastered"] is False
    assert block["first_mastered_at"] is None


def test_mastered_persists_across_reload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """MAST-04: the flipped live-portion survives a save→load round-trip and
    ``SkillTree.compute`` reads ``stage='mastered'`` from the reloaded file
    (complements test_mastered_live_portion_promotes_stage with the WRITE path).

    Routed through the monkeypatched ``progress_path`` so the real
    ``~/.cache/vibemix/learn-progress.json`` is never touched."""
    target = tmp_path / "learn-progress.json"
    monkeypatch.setattr("vibemix.learn.progress.progress_path", lambda: target)

    progress = _competent_eq_progress()
    threshold = SKILL_MANIFEST["eq_mixing"].mastered_threshold
    for _ in range(threshold):
        record_live_demo(progress, "eq_mixing", now=_NOW)
    save_progress(progress)

    loaded, was_corrupt = load_progress()
    assert was_corrupt is False
    sp = SkillTree().compute(loaded)["eq_mixing"]
    assert sp.stage == "mastered"
    assert sp.mastered is True
    assert sp.live_proof_count == threshold
    assert sp.first_mastered_at == _NOW


def test_record_live_demo_degrades_garbage_count() -> None:
    """WR-01 / Pitfall (DoS): a Competent skill whose stored
    ``live_proof_count`` is non-numeric (hand-edit / partial write) must NOT
    crash record_live_demo — it treats garbage as 0 and increments to 1
    (mirrors compute's ``int(... or 0)`` + try/except guard)."""
    progress = _competent_eq_progress()
    # Hand-corrupt the live-portion count with a non-numeric value.
    progress.skills["eq_mixing"] = {
        "live_proof_count": "x",
        "mastered": False,
        "first_mastered_at": None,
    }

    record_live_demo(progress, "eq_mixing", now=_NOW)  # must NOT raise

    assert progress.skills["eq_mixing"]["live_proof_count"] == 1
