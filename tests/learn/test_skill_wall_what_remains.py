# SPDX-License-Identifier: Apache-2.0
"""SURF-01 — the plain "what remains to advance" line on each Earned-Wall row.

`skill_wall_payload` folds a deterministic, single-source-in-Python `what_remains`
string into every row so the frontend never re-derives the stage rule. The copy is
factual UI affordance labelling (not co-host speech): honest for the one
v11.0-uncreditable skill (beatmatching has no live Mastered path), and it states the
real next step at every stage.
"""
from __future__ import annotations

from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import SKILL_MANIFEST, skill_wall_payload


def _row(progress: LearnProgress, skill_id: str) -> dict:
    return next(r for r in skill_wall_payload(progress) if r["skill_id"] == skill_id)


def _compete(progress: LearnProgress, skill_id: str) -> None:
    """Drive a skill to Competent: first-try-complete its lessons + pass its gate."""
    spec = SKILL_MANIFEST[skill_id]
    for lid in spec.lesson_ids:
        progress.lessons[lid] = {"completed": True}
    setattr(progress, spec.gate, True)


def test_every_row_carries_a_what_remains_string():
    wall = skill_wall_payload(LearnProgress())
    for row in wall:
        assert "what_remains" in row
        assert isinstance(row["what_remains"], str)


def test_locked_no_lessons_says_finish_the_lessons():
    # Fresh user: no lessons, no recital → the next step is the lessons.
    row = _row(LearnProgress(), "deck_control")
    assert row["stage"] == "locked"
    assert row["what_remains"] == "Finish the lessons to reach Competent"


def test_locked_lessons_done_recital_pending_says_pass_the_recital():
    # COMP-02: lessons fully done (fill >= threshold) but the gate recital not passed
    # → still locked, and the honest next step is the recital, not more lessons.
    progress = LearnProgress()
    for lid in SKILL_MANIFEST["deck_control"].lesson_ids:
        progress.lessons[lid] = {"completed": True}
    # deliberately DO NOT set the course_2_unlocked gate
    row = _row(progress, "deck_control")
    assert row["stage"] == "locked"
    assert row["learn_fill"] >= 0.6
    assert row["what_remains"] == "Pass the recital to reach Competent"


def test_competent_creditable_counts_down_remaining_demos():
    # eq_mixing IS live-creditable (MIX_MOVE EQ-band). At Competent with 1 of 3 demos,
    # exactly 2 remain — plural phrasing.
    progress = LearnProgress()
    _compete(progress, "eq_mixing")
    progress.skills["eq_mixing"] = {
        "live_proof_count": 1, "mastered": False, "first_mastered_at": None,
    }
    row = _row(progress, "eq_mixing")
    assert row["stage"] == "competent"
    assert row["what_remains"] == "2 more cited live demos to Master"


def test_competent_creditable_singular_when_one_demo_left():
    progress = LearnProgress()
    _compete(progress, "eq_mixing")
    progress.skills["eq_mixing"] = {
        "live_proof_count": 2, "mastered": False, "first_mastered_at": None,
    }
    row = _row(progress, "eq_mixing")
    assert row["what_remains"] == "1 more cited live demo to Master"


def test_competent_beatmatching_states_no_live_grade_path_yet():
    # The owned-deck Beatmatch Judge exists, but no production emitter can fire
    # BEATMATCH_GRADED yet. The wall must cap at Competent instead of promising
    # a Mastered path the app cannot observe.
    progress = LearnProgress()
    _compete(progress, "beatmatching")
    row = _row(progress, "beatmatching")
    assert row["stage"] == "competent"
    assert row["what_remains"] == "Mastered isn't live-graded for this skill"


def test_uncreditable_stored_mastery_is_not_displayed_as_mastered():
    # A prior/stale profile entry must not make the product claim a live Mastered
    # beatmatch while the production emitter is still absent.
    progress = LearnProgress()
    _compete(progress, "beatmatching")
    progress.skills["beatmatching"] = {
        "live_proof_count": 3,
        "mastered": True,
        "first_mastered_at": "2026-05-30T11:00:00Z",
    }
    row = _row(progress, "beatmatching")
    assert row["stage"] == "competent"
    assert row["mastered"] is False
    assert row["first_mastered_at"] is None
    assert row["what_remains"] == "Mastered isn't live-graded for this skill"


def test_mastered_has_empty_what_remains():
    # The cited-proof line carries a Mastered skill; nothing "remains".
    progress = LearnProgress()
    _compete(progress, "harmonic_mixing")
    progress.skills["harmonic_mixing"] = {
        "live_proof_count": 3, "mastered": True, "first_mastered_at": "2026-05-30T11:00:00Z",
    }
    row = _row(progress, "harmonic_mixing")
    assert row["stage"] == "mastered"
    assert row["what_remains"] == ""


def test_what_remains_never_leaks_anti_slop_tokens():
    # Cheap inline guard: the affordance copy must stay sober across all stages.
    _SLOP = ("awesome", "amazing", "great job", "you got this", "congrats", "achievement unlocked")
    progress = LearnProgress()
    _compete(progress, "eq_mixing")
    for row in skill_wall_payload(progress):
        low = row["what_remains"].lower()
        for tok in _SLOP:
            assert tok not in low, f"slop token {tok!r} in what_remains: {row['what_remains']!r}"
