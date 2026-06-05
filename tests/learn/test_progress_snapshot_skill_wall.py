# SPDX-License-Identifier: Apache-2.0
"""snapshot() folds the derived Earned-Wall block; to_dict() stays pure-file.

The IPC envelope (`ipc.learn.progress_state`) is built from `snapshot()`, so the
derived `skill_wall` rides the wire there. `to_dict()` is the JSON-FILE shape and
the persistence path (`save_progress` / `from_dict` round-trip) — it must NEVER
carry the derived block, or the recomputed-on-load contract breaks.
"""

from __future__ import annotations

from vibemix.learn.progress import LearnProgress
from vibemix.learn.skill_tree import SKILL_MANIFEST, skill_wall_payload


def test_snapshot_carries_derived_skill_wall():
    progress = LearnProgress()
    snap = progress.snapshot()
    assert "skill_wall" in snap
    assert snap["skill_wall"] == skill_wall_payload(progress)
    assert [r["skill_id"] for r in snap["skill_wall"]] == list(SKILL_MANIFEST.keys())


def test_snapshot_still_carries_the_file_fields():
    # The wall is ADDITIVE — the existing persisted fields are untouched.
    snap = LearnProgress().snapshot()
    for key in ("schema_version", "courses", "lessons", "skills"):
        assert key in snap


def test_to_dict_stays_pure_file_shape_without_skill_wall():
    # Persistence must not see the derived block (recomputed on every load).
    assert "skill_wall" not in LearnProgress().to_dict()


def test_snapshot_carries_next_practice_mission_without_persisting_it():
    snap = LearnProgress().snapshot()
    assert snap["next_practice_mission"]["lesson_id"] == "L1.02"
    assert snap["next_practice_mission"]["mode"] == "start"
    assert [step["lesson_id"] for step in snap["next_practice_mission"]["chain"]][:2] == [
        "L1.02",
        "L1.03",
    ]

    stored = LearnProgress().to_dict()
    assert "next_practice_mission" not in stored


def test_mastered_demo_reaches_the_envelope_wall():
    progress = LearnProgress()
    skill_id = "harmonic_mixing"
    spec = SKILL_MANIFEST[skill_id]
    for lesson_id in spec.lesson_ids:
        progress.lessons[lesson_id] = {"completed": True}
    setattr(progress, spec.gate, True)
    progress.skills[skill_id] = {
        "live_proof_count": 3,
        "mastered": True,
        "first_mastered_at": "2026-05-30T11:00:00Z",
    }
    row = next(r for r in progress.snapshot()["skill_wall"] if r["skill_id"] == skill_id)
    assert row["stage"] == "mastered"
