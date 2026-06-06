# SPDX-License-Identifier: Apache-2.0
"""The derived skill-wall IPC payload (Earned Wall, backend half).

`skill_wall_payload(progress)` folds `SkillTree.compute()` into a JSON-safe,
manifest-ordered list — the paint-ready block the webview renders as the Earned
Wall. The STAGE RULE stays single-sourced in Python (no TS re-derivation of
COMPETENT_THRESHOLD/weights). This payload is IPC-only: it is NEVER persisted to
`learn-progress.json` (the derived learn-portion is recomputed on every load).
"""
from __future__ import annotations

import json

from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import SKILL_MANIFEST, skill_wall_payload


def test_fresh_progress_is_six_locked_skills_in_manifest_order():
    wall = skill_wall_payload(LearnProgress())
    assert [row["skill_id"] for row in wall] == list(SKILL_MANIFEST.keys())
    for row in wall:
        assert row["stage"] == "locked"
        assert row["competent"] is False
        assert row["learn_fill"] == 0.0
        assert row["live_proof_count"] == 0
        assert row["mastered"] is False
        assert row["first_mastered_at"] is None


def test_payload_is_json_serializable():
    # It rides ipc.learn.progress_state — it MUST round-trip through json.
    wall = skill_wall_payload(LearnProgress())
    back = json.loads(json.dumps(wall))
    assert isinstance(back, list) and len(back) == len(SKILL_MANIFEST)
    assert set(back[0]) == {
        "skill_id", "stage", "learn_fill", "competent",
        "live_proof_count", "mastered", "first_mastered_at",
        "what_remains",  # SURF-01 — the plain "what remains to advance" line
    }


def test_competent_skill_surfaces_competent_stage():
    # deck_control fills from L1.02-L1.09 first-try + course_2_unlocked recital gate.
    progress = LearnProgress()
    for lid in SKILL_MANIFEST["deck_control"].lesson_ids:
        progress.lessons[lid] = {"completed": True}
    progress.course_2_unlocked = True
    row = next(r for r in skill_wall_payload(progress) if r["skill_id"] == "deck_control")
    assert row["stage"] == "competent"
    assert row["competent"] is True
    assert row["learn_fill"] >= 0.6


def test_banked_practice_reps_surface_without_granting_fill():
    progress = LearnProgress()
    progress.mark_practice_source("course_1_anatomy", "L1.03", "click")
    progress.mark_practice_source("course_1_anatomy", "L1.03", "midi")
    progress.mark_practice_source("course_1_anatomy", "L1.04", "click")

    row = next(r for r in skill_wall_payload(progress) if r["skill_id"] == "deck_control")

    assert row["stage"] == "locked"
    assert row["learn_fill"] == 0.0
    assert row["what_remains"] == (
        "3 banked practice reps; finish the matching lesson to keep them"
    )


def test_mastered_live_portion_surfaces_in_payload():
    # A cited live demo (Phase 103) stamps the live-portion; the wall must show it.
    progress = LearnProgress()
    progress.skills["harmonic_mixing"] = {
        "live_proof_count": 3,
        "mastered": True,
        "first_mastered_at": "2026-05-30T11:00:00Z",
    }
    row = next(r for r in skill_wall_payload(progress) if r["skill_id"] == "harmonic_mixing")
    assert row["stage"] == "mastered"
    assert row["mastered"] is True
    assert row["live_proof_count"] == 3
    assert row["first_mastered_at"] == "2026-05-30T11:00:00Z"
