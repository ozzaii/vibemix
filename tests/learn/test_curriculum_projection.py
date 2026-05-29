# SPDX-License-Identifier: Apache-2.0
"""Course registry and frontend curriculum projection contracts."""
from __future__ import annotations

from pathlib import Path

from vibemix.learn import curriculum_projection
from vibemix.learn.curriculum import (
    COURSE_FRAMES,
    COURSE_REGISTRY,
    CURRICULUM,
    CourseMeta,
    beginner_course_ids,
    beginner_lesson_ids,
    course_lesson_ids,
)
from vibemix.learn.curriculum_projection import (
    beginner_curriculum_projection,
    render_curriculum_meta_ts,
)

FRONTEND_CURRICULUM_META = (
    Path(__file__).resolve().parent.parent.parent
    / "tauri"
    / "ui"
    / "src"
    / "learn"
    / "lesson"
    / "curriculum-meta.ts"
)


def test_course_registry_covers_frames_and_curriculum() -> None:
    """Adding a course should happen through the registry, not stray literals."""
    assert set(COURSE_FRAMES) == set(COURSE_REGISTRY)
    for lesson_id, meta in CURRICULUM.items():
        assert meta.course_id in COURSE_REGISTRY, (
            f"{lesson_id} points at unregistered course {meta.course_id!r}"
        )
    for course_id in COURSE_REGISTRY:
        assert course_lesson_ids(course_id), f"{course_id} has no lessons"
        assert COURSE_REGISTRY[course_id].frontstage_mode
        assert COURSE_REGISTRY[course_id].capabilities


def test_beginner_projection_is_the_36_lesson_module() -> None:
    projection = beginner_curriculum_projection()

    assert beginner_course_ids() == (
        "course_1_anatomy",
        "course_2_transitions",
        "course_3_play_mode",
    )
    assert len(beginner_lesson_ids()) == 36
    assert [course["course_id"] for course in projection["courses"]] == [
        "course_1_anatomy",
        "course_2_transitions",
        "course_3_play_mode",
    ]
    assert projection["courses"][0]["frontstage_mode"] == "practice_booth"
    assert "library_exemplars" in projection["courses"][0]["capabilities"]
    assert projection["courses"][2]["frontstage_mode"] == "live_play_mode"
    assert "live_audio" in projection["courses"][2]["capabilities"]
    assert [lesson["lesson_id"] for lesson in projection["lessons"]] == list(
        beginner_lesson_ids()
    )
    assert "L0.00-press-play" not in {
        str(lesson["lesson_id"]) for lesson in projection["lessons"]
    }


def test_frontend_curriculum_meta_is_generated_from_python_projection() -> None:
    current = FRONTEND_CURRICULUM_META.read_text(encoding="utf-8")
    assert current == render_curriculum_meta_ts()


def test_frontend_projection_progress_fields_follow_declared_unlock_gates(
    monkeypatch,
) -> None:
    monkeypatch.setitem(
        curriculum_projection.COURSE_REGISTRY,
        "course_2_transitions",
        CourseMeta(
            label="Course 2 · Transitions",
            hud_label="COURSE 2 · TRANSITIONS",
            unlock_gate="course_4_unlocked",
            lock_reason="pass the prior course to unlock transitions",
            capabilities=("evidence_registry", "controller_state", "on_screen_deck"),
        ),
    )

    rendered = render_curriculum_meta_ts()

    assert 'type CourseUnlockGate = "course_3_unlocked" | "course_4_unlocked";' in rendered
    assert "  course_4_unlocked?: boolean;\n" in rendered
    assert "  course_2_unlocked?: boolean;\n" not in rendered
