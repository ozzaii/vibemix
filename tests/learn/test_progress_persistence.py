# SPDX-License-Identifier: Apache-2.0
"""LESSON-03 progress persistence regression tests.

Six small tests cover the atomic-write + corruption-recovery + reset
flow of ``learn-progress.json`` (the schema_version 1 file at
``~/.cache/vibemix/learn-progress.json``):

1. ``test_atomic_write`` — ``save_progress(...)`` leaves zero ``.tmp``
   files in the directory (atomic via ``os.replace``).
2. ``test_corrupt_file_recovers_clean`` — garbage bytes on disk
   surface as ``(fresh_progress, was_corrupt=True)``.
3. ``test_schema_version_mismatch_returns_fresh_empty`` — a stored
   ``schema_version`` ≠ 1 yields a fresh empty progress without raising.
4. ``test_reset_progress_unlinks_file`` — ``reset_progress()`` removes
   the on-disk file.
5. ``test_mark_completed_updates_lesson`` — ``mark_completed`` carries
   ``completed=True`` into the ``lessons[<id>]`` dict.
6. ``test_reset_cli`` — ``vibemix learn reset`` exits 0 + the file is
   absent afterwards (subprocess marker: ``cli`` test).

The pattern mirrors ``src/vibemix/runtime/config_store.py`` lines
266-278 verbatim — POSIX rename is atomic; Windows ReplaceFileW is
atomic.

REQ-ID: LESSON-03 (progress persistence + corruption recovery + reset CLI).
"""
from __future__ import annotations

from pathlib import Path

import pytest

try:
    from vibemix.learn.progress import (
        LearnProgress,
        load_progress,
        reset_progress,
        save_progress,
    )
except ImportError:
    pytest.skip(
        "Learn progress persistence is unavailable in this partial Learn build.",
        allow_module_level=True,
    )


@pytest.fixture
def progress_path_in_tmp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    """Redirect ``progress_path()`` to a tmp dir so each test starts
    with a clean canvas. Returns the redirected path."""
    target = tmp_path / "learn-progress.json"
    monkeypatch.setattr(
        "vibemix.learn.progress.progress_path",
        lambda: target,
    )
    return target


def test_atomic_write(progress_path_in_tmp: Path) -> None:
    """``save_progress`` leaves NO ``*.json.tmp`` residue (the temp
    file is renamed via ``os.replace``)."""
    progress = LearnProgress()
    progress.mark_completed("course_0", "L0.00-press-play")
    save_progress(progress)
    parent = progress_path_in_tmp.parent
    leftover = list(parent.glob("*.tmp"))
    assert not leftover, (
        f"atomic-write leaked a temp file: {leftover!r}. "
        "save_progress MUST use os.replace(tmp, target) without "
        "leaving the .json.tmp behind."
    )
    assert progress_path_in_tmp.exists(), "target file missing after save"


def test_corrupt_file_recovers_clean(progress_path_in_tmp: Path) -> None:
    """Garbage bytes on disk → ``(fresh_empty, was_corrupt=True)``."""
    progress_path_in_tmp.parent.mkdir(parents=True, exist_ok=True)
    progress_path_in_tmp.write_bytes(b"not json{{{")
    progress, was_corrupt = load_progress()
    assert was_corrupt is True, (
        "load_progress should flag garbage bytes via was_corrupt=True"
    )
    assert progress.lessons == {} and progress.courses == {}, (
        "corruption recovery should return a fresh empty LearnProgress, "
        f"got lessons={progress.lessons!r} courses={progress.courses!r}"
    )


def test_schema_version_mismatch_returns_fresh_empty(
    progress_path_in_tmp: Path,
) -> None:
    """A forward-incompatible ``schema_version`` (3+/garbage) yields a fresh
    empty ``LearnProgress`` — the wipe seam.

    Phase 102 (v11.0) bumped ``SCHEMA_VERSION`` to 2 and made v1 a real
    migration target (``_migrate_v1_to_v2``), so v2 is now the CURRENT
    schema. The old assertion (``schema_version: 2`` → fresh-empty) is no
    longer valid — v2 LOADS. This test is deliberately rewritten to
    ``schema_version: 3`` (a genuine future/garbage version) so it still
    exercises the wipe seam (RESEARCH finding #1 / Pitfall 1 — a rewrite,
    not a regression). The lesson rows below MUST be wiped, proving the
    wipe seam fires (a non-empty v3 dict does not silently load)."""
    import json

    progress_path_in_tmp.parent.mkdir(parents=True, exist_ok=True)
    progress_path_in_tmp.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "courses": {},
                "lessons": {"L1.01": {"completed": True}},
            }
        ),
        encoding="utf-8",
    )
    progress, _was_corrupt = load_progress()
    assert progress.lessons == {} and progress.courses == {}, (
        "a forward-incompatible schema_version (3+) must surface as fresh "
        "empty (the wipe seam) — the v1->v2 upgrader only handles v1"
    )


def test_reset_progress_unlinks_file(progress_path_in_tmp: Path) -> None:
    """``reset_progress()`` removes the file from disk."""
    progress = LearnProgress()
    progress.mark_completed("course_0", "L0.00-press-play")
    save_progress(progress)
    assert progress_path_in_tmp.exists(), "save_progress did not write the file"
    reset_progress()
    assert not progress_path_in_tmp.exists(), (
        "reset_progress did not unlink the file"
    )


def test_mark_completed_updates_lesson() -> None:
    """``mark_completed`` flips ``lessons[<id>]['completed']`` to True."""
    progress = LearnProgress()
    progress.mark_completed("course_0", "L0.00-press-play")
    entry = progress.lessons.get("L0.00-press-play")
    assert entry is not None, "lesson entry was not created"
    assert entry.get("completed") is True, (
        f"completed flag not set; entry={entry!r}"
    )
    assert entry.get("demonstrated") is True


def test_mark_completed_can_record_skip_without_demonstration() -> None:
    """A timeout/user-skip may finish the row without awarding demo credit."""
    progress = LearnProgress()
    progress.mark_completed(
        "course_0",
        "L0.00-press-play",
        demonstrated=False,
    )

    entry = progress.lessons["L0.00-press-play"]
    assert entry["completed"] is True
    assert entry["demonstrated"] is False


def test_mark_started_creates_incomplete_schema_row() -> None:
    """Started lessons are visible to snapshots before completion."""
    progress = LearnProgress()
    progress.mark_started("course_1_anatomy", "L1.03")

    assert progress.courses["course_1_anatomy"] == {}
    assert progress.lessons["L1.03"] == {
        "completed": False,
        "completed_at": None,
        "strikes_used": 0,
    }


def test_hint_strike_updates_unfinished_attempt() -> None:
    """Hint count persists while the lesson is still in progress."""
    progress = LearnProgress()
    progress.mark_hint_strike("course_1_anatomy", "L1.03", 2)

    assert progress.lessons["L1.03"]["completed"] is False
    assert progress.lessons["L1.03"]["completed_at"] is None
    assert progress.lessons["L1.03"]["strikes_used"] == 2


def test_practice_source_memory_tracks_hardware_and_screen() -> None:
    """Progress remembers the learner's practice surface without UI clutter."""
    progress = LearnProgress()

    progress.mark_practice_source("course_1_anatomy", "L1.03", "midi")
    progress.mark_practice_source("course_1_anatomy", "L1.03", "click")

    assert progress.lessons["L1.03"] == {
        "completed": False,
        "completed_at": None,
        "strikes_used": 0,
        "practice_sources": {"hardware": 1, "screen": 1},
        "last_practice_source": "screen",
        "last_practice_seq": 2,
    }


def test_hint_and_completion_preserve_practice_source_memory() -> None:
    """Row rewrites must not erase the user's hardware/screen history."""
    progress = LearnProgress()

    progress.mark_practice_source("course_1_anatomy", "L1.03", "midi")
    progress.mark_hint_strike("course_1_anatomy", "L1.03", 2)
    progress.mark_completed("course_1_anatomy", "L1.03", strikes_used=2)

    assert progress.lessons["L1.03"]["completed"] is True
    assert progress.lessons["L1.03"]["strikes_used"] == 2
    assert progress.lessons["L1.03"]["practice_sources"] == {
        "hardware": 1,
        "screen": 0,
    }
    assert progress.lessons["L1.03"]["last_practice_source"] == "hardware"
    assert progress.lessons["L1.03"]["last_practice_seq"] == 1


def test_practice_feedback_is_bounded_and_cleared_by_completion() -> None:
    """Measured misses can steer retry missions without becoming progress."""
    progress = LearnProgress()

    changed = progress.mark_practice_feedback(
        "course_2_transitions",
        "L2.01",
        kind="beatmatch",
        label="phase drift",
        message="Deck B is late; nudge it forward before chasing proof.",
        detail="0.05 beats from lock",
    )
    progress.mark_hint_strike("course_2_transitions", "L2.01", 1)

    assert changed is True
    assert progress.lessons["L2.01"]["practice_feedback"] == {
        "kind": "beatmatch",
        "label": "phase drift",
        "message": "Deck B is late; nudge it forward before chasing proof.",
        "detail": "0.05 beats from lock",
    }
    assert progress.lessons["L2.01"]["last_feedback_seq"] == 1
    assert progress.lessons["L2.01"]["strikes_used"] == 1
    assert progress.clear_practice_feedback("L2.01") is True
    assert "practice_feedback" not in progress.lessons["L2.01"]
    assert "last_feedback_seq" not in progress.lessons["L2.01"]

    progress.mark_practice_feedback(
        "course_2_transitions",
        "L2.01",
        kind="beatmatch",
        label="phase drift",
        message="Deck B is late; nudge it forward before chasing proof.",
    )
    progress.mark_completed("course_2_transitions", "L2.01")

    assert "practice_feedback" not in progress.lessons["L2.01"]
    assert "last_feedback_seq" not in progress.lessons["L2.01"]


def test_practice_feedback_recency_is_monotonic() -> None:
    """Multiple recovery targets get a deterministic recency receipt."""
    progress = LearnProgress()

    progress.mark_practice_feedback(
        "course_2_transitions",
        "L2.01",
        kind="beatmatch",
        label="phase drift",
        message="Deck B is late.",
    )
    progress.mark_practice_feedback(
        "course_2_transitions",
        "L2.10",
        kind="cue_placement",
        label="drop timing",
        message="Aim at the drop.",
    )

    assert progress.lessons["L2.01"]["last_feedback_seq"] == 1
    assert progress.lessons["L2.10"]["last_feedback_seq"] == 2


def test_mark_started_does_not_erase_completed_replay() -> None:
    """Replaying a completed lesson must not demote the completed row."""
    progress = LearnProgress()
    progress.mark_completed("course_1_anatomy", "L1.03", strikes_used=1)

    completed_at = progress.lessons["L1.03"]["completed_at"]
    progress.mark_started("course_1_anatomy", "L1.03")
    progress.mark_hint_strike("course_1_anatomy", "L1.03", 3)

    assert progress.lessons["L1.03"] == {
        "completed": True,
        "completed_at": completed_at,
        "strikes_used": 1,
        "demonstrated": True,
    }


def test_dots_for_course_filters_by_course_id() -> None:
    """CR-03 (P92 REVIEW) regression — ``dots_for_course(course_id)`` MUST
    only return dots for lessons owned by that course.

    Before CR-03 fix: the function deleted its course_id parameter and
    walked every completed lesson; an L0.* completion would surface as a
    dot on every course (course_1, course_2, …). With one course shipped
    (v9.0) this is silently correct; with two courses (P94+) the HUD
    paints 30+ dots when Course 1 should show 16.

    Test setup: complete the L0.00-press-play lesson (which belongs to
    course_0 per CURRICULUM). Then:

      * dots_for_course("course_0") → 1 dot
      * dots_for_course("course_1") → 0 dots (legacy alias is not canonical)
      * dots_for_course(None) → 0 dots (defensive None branch)
    """
    progress = LearnProgress()
    progress.mark_completed("course_0", "L0.00-press-play")

    course_0_dots = progress.dots_for_course("course_0")
    assert len(course_0_dots) == 1, (
        f"course_0 should have 1 dot, got {len(course_0_dots)}: "
        f"{course_0_dots!r}"
    )
    assert course_0_dots[0]["lesson_id"] == "L0.00-press-play"
    assert course_0_dots[0]["status"] == "completed"

    course_1_dots = progress.dots_for_course("course_1")
    assert course_1_dots == (), (
        "course_1 should have 0 dots — live Course 1 is keyed by "
        "course_1_anatomy. Without filtering, the unfiltered walk leaked "
        f"into course_1: {course_1_dots!r}"
    )

    none_dots = progress.dots_for_course(None)
    assert none_dots == (), (
        f"None course_id should return empty tuple, got {none_dots!r}"
    )


def test_dots_for_course_skips_unknown_lessons() -> None:
    """Stale lesson rows that no longer appear in CURRICULUM must be
    silently skipped. Future-proofing: if a prior CURRICULUM exported a
    lesson id that has since been pruned, the on-disk progress may still
    carry the row, but the HUD cannot paint a dot for a lesson it
    doesn't know about.
    """
    progress = LearnProgress()
    # Inject a stale row directly (bypasses mark_completed's normal
    # path — simulates a progress file from a prior CURRICULUM).
    progress.lessons["L9.99-from-the-future"] = {
        "completed": True,
        "completed_at": "2026-01-01T00:00:00Z",
        "strikes_used": 0,
    }
    progress.mark_completed("course_0", "L0.00-press-play")

    course_0_dots = progress.dots_for_course("course_0")
    assert len(course_0_dots) == 1, (
        f"only the known lesson should produce a dot; got {course_0_dots!r}"
    )
    assert course_0_dots[0]["lesson_id"] == "L0.00-press-play"


def test_dots_for_course_renders_current_and_pending_curriculum_rows() -> None:
    """The live HUD needs every lesson in the active course, not just
    completed rows. A fresh Course 1 lesson should say ``OF 16`` and mark
    the active row current instead of opening with an empty dot strip.
    """
    progress = LearnProgress()
    progress.mark_completed("course_1_anatomy", "L1.01")

    dots = progress.dots_for_course(
        "course_1_anatomy",
        current_lesson_id="L1.03",
    )

    assert len(dots) == 16
    by_id = {dot["lesson_id"]: dot["status"] for dot in dots}
    assert by_id["L1.01"] == "completed"
    assert by_id["L1.03"] == "current"
    assert by_id["L1.04"] == "pending"


def test_runtime_completion_persists_across_load(
    progress_path_in_tmp: Path,
) -> None:
    """CR-02 (P92 REVIEW) regression — LessonRuntime.on_enter_completed
    must call ``save_progress`` so completion survives a process restart.

    Sequence:
      1. Drive a fresh LessonRuntime through the full FSM lifecycle so it
         enters ``completed``.
      2. Call ``load_progress()`` directly — simulating a fresh boot
         reading from the same on-disk file.
      3. Assert the lesson is still marked ``completed=True``.

    Before CR-02 fix: the runtime mutated only the in-memory progress
    dict — the on-disk file stayed empty — the second load_progress()
    returned a fresh-empty LearnProgress and the assertion failed.
    """
    from unittest.mock import MagicMock

    from vibemix.learn.runtime import LessonRuntime
    from vibemix.learn.state import LearnState

    learn_state = LearnState()
    midi_mirror = MagicMock(name="midi_mirror")
    controller_state = MagicMock(name="controller_state")
    ipc_router = MagicMock(name="ipc_router")
    # Real LearnProgress instance — this is what live __main__.py wires
    # via load_progress(). The Mock version of progress_store in other
    # smoke tests intentionally side-steps this path; CR-02 cares about
    # the real-progress branch.
    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=learn_state,
        midi_mirror=midi_mirror,
        controller_state=controller_state,
        ipc_router=ipc_router,
        progress_store=progress,
    )

    # Drive to advancing, then synthesize finish (the live path waits
    # ~45s + 0.7s before send("finish"); the test path doesn't have an
    # async loop running so the scheduling falls back to a no-op; we
    # finalize manually).
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime.send(
        "ack_action",
        midi={
            "type": "button",
            "control": "play",
            "deck": "A",
            "direction": "down",
        },
    )
    # If the smoke test ended in ``advancing``, finalize to completed.
    if runtime.current_state.id == "advancing":
        runtime.send("finish")
    assert runtime.current_state.id == "completed", (
        f"runtime did not reach completed; state={runtime.current_state.id!r}"
    )

    # Now simulate a process restart — read fresh from disk.
    reloaded, was_corrupt = load_progress()
    assert was_corrupt is False, "fresh save should not be flagged corrupt"
    entry = reloaded.lessons.get("L0.00-press-play")
    assert entry is not None, (
        "CR-02 fix missing — runtime did not persist completion; the "
        "on-disk file is empty after the lifecycle. Verify "
        "on_enter_completed calls save_progress(self._progress)."
    )
    assert entry.get("completed") is True, (
        f"completion flag not persisted; entry={entry!r}"
    )
    assert entry.get("demonstrated") is True


def test_runtime_user_skip_persists_without_demonstration(
    progress_path_in_tmp: Path,
) -> None:
    """The 45s skip escape completes the row without full demo credit."""
    import time
    from unittest.mock import MagicMock

    from vibemix.learn.runtime import LessonRuntime
    from vibemix.learn.state import LearnState

    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=progress,
    )

    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime._learn.lesson_started_at = time.monotonic() - 46.0
    runtime.send("skip")
    if runtime.current_state.id == "advancing":
        runtime.send("finish")

    reloaded, was_corrupt = load_progress()
    assert was_corrupt is False
    entry = reloaded.lessons["L0.00-press-play"]
    assert entry["completed"] is True
    assert entry["demonstrated"] is False


def test_runtime_start_persists_in_progress_across_load(
    progress_path_in_tmp: Path,
) -> None:
    """Starting a lesson writes the unfinished attempt to disk immediately."""
    from unittest.mock import MagicMock

    from vibemix.learn.runtime import LessonRuntime
    from vibemix.learn.state import LearnState

    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=progress,
    )

    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    reloaded, was_corrupt = load_progress()
    assert was_corrupt is False
    assert reloaded.courses["course_1_anatomy"] == {}
    assert reloaded.lessons["L1.03"] == {
        "completed": False,
        "completed_at": None,
        "strikes_used": 0,
    }


def test_runtime_completion_persists_strikes_used(
    progress_path_in_tmp: Path,
) -> None:
    """Completed lesson rows preserve how many timed hints fired."""
    from unittest.mock import MagicMock

    from vibemix.learn.runtime import LessonRuntime
    from vibemix.learn.state import LearnState

    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=progress,
    )

    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime.send("strike")
    runtime.send("strike")
    assert runtime._learn.strike_count == 2

    runtime.send(
        "ack_action",
        midi={
            "type": "button",
            "control": "play",
            "deck": "A",
            "direction": "down",
        },
    )
    if runtime.current_state.id == "advancing":
        runtime.send("finish")

    reloaded, was_corrupt = load_progress()
    assert was_corrupt is False
    assert reloaded.lessons["L0.00-press-play"]["strikes_used"] == 2
    assert reloaded.lessons["L0.00-press-play"]["demonstrated"] is True


# ---------------------------------------------------------------------------
# Plan 94-03 — LESSON-03 extension: course_2_unlocked field (CURR-1.16 binding)
# ---------------------------------------------------------------------------


def test_progress_default_course_2_unlocked_false() -> None:
    """A fresh ``LearnProgress()`` has ``course_2_unlocked = False``.

    Plan 94-03 adds the field as an additive default-False extension to
    schema_version 1 — the migration seam still short-circuits on
    schema_version != 1; existing schema_version=1 JSON without the field
    loads as False (forward-compat).
    """
    progress = LearnProgress()
    assert progress.course_2_unlocked is False, (
        f"LearnProgress.course_2_unlocked must default to False; "
        f"got {progress.course_2_unlocked!r}"
    )


def test_progress_round_trips_course_2_unlocked_true() -> None:
    """Setting ``course_2_unlocked = True``, serialising via to_dict,
    and round-tripping through from_dict preserves the value.
    """
    progress = LearnProgress()
    progress.course_2_unlocked = True
    raw = progress.to_dict()
    assert raw.get("course_2_unlocked") is True, (
        f"to_dict must serialise course_2_unlocked; got {raw!r}"
    )
    reloaded = LearnProgress.from_dict(raw)
    assert reloaded.course_2_unlocked is True, (
        f"from_dict must read course_2_unlocked back; "
        f"got {reloaded.course_2_unlocked!r}"
    )


def test_progress_legacy_json_loads_with_default_false() -> None:
    """A legacy schema_version=1 JSON dict WITHOUT the
    ``course_2_unlocked`` field (pre-Plan-94-03 disk format) must load
    as False — no KeyError, no migration prompt.

    Forward-compat guarantee: a user who upgrades from v9.0 RC1
    (pre-Plan-94-03) to a build that ships the recital must NOT see
    their existing progress nuked. The default-False additive extension
    is invisible to the migration seam.
    """
    legacy_raw = {
        "schema_version": 1,
        "courses": {},
        "lessons": {
            "L0.00-press-play": {
                "completed": True,
                "completed_at": "2026-05-27T00:00:00Z",
                "strikes_used": 0,
            },
        },
    }
    progress = LearnProgress.from_dict(legacy_raw)
    assert progress.course_2_unlocked is False, (
        f"legacy JSON missing the field must load with course_2_unlocked=False; "
        f"got {progress.course_2_unlocked!r}"
    )
    # And the pre-existing lessons survive unchanged.
    assert "L0.00-press-play" in progress.lessons
    assert progress.lessons["L0.00-press-play"]["completed"] is True


@pytest.mark.cli
def test_reset_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``uv run python -m vibemix learn reset`` exits 0 and leaves the
    progress file absent.

    Marked ``cli`` (subprocess-tagged) — runs under the ``-m cli`` opt-in
    selector per pyproject.toml [tool.pytest.ini_options].
    """
    import subprocess
    import sys

    # Point HOME at a clean tmp dir so the CLI writes its own progress
    # file under tmp_path/.cache/vibemix/.
    monkeypatch.setenv("HOME", str(tmp_path))
    # Pre-create the cache dir + write a sentinel progress file.
    cache_dir = tmp_path / ".cache" / "vibemix"
    cache_dir.mkdir(parents=True, exist_ok=True)
    sentinel = cache_dir / "learn-progress.json"
    sentinel.write_text(
        '{"schema_version": 1, "courses": {}, "lessons": {}}',
        encoding="utf-8",
    )

    # Use the test interpreter's vibemix package — works in either
    # `.venv/bin/activate && pytest -m cli` or `uv run pytest -m cli`.
    proc = subprocess.run(
        [sys.executable, "-m", "vibemix", "learn", "reset"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"learn reset CLI exited {proc.returncode}\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )
    assert not sentinel.exists(), (
        "learn reset CLI ran exit 0 but the file remained on disk"
    )
