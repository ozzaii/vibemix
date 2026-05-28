# SPDX-License-Identifier: Apache-2.0
"""Phase 92 Plan 02 — LESSON-03 progress persistence (RED-state stub).

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
    from vibemix.learn.progress import (  # Plan 92-04
        LearnProgress,
        load_progress,
        progress_path,
        reset_progress,
        save_progress,
    )
except ImportError:
    pytest.skip(
        "tests/learn/test_progress_persistence.py awaits Plan 92-04 "
        "(LESSON-03 progress.py with atomic write + corruption "
        "recovery). When progress.py lands, this module-level skip "
        "flips to live assertions.",
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
    """A stored ``schema_version`` != 1 yields a fresh empty
    ``LearnProgress`` — the migration seam."""
    import json

    progress_path_in_tmp.parent.mkdir(parents=True, exist_ok=True)
    progress_path_in_tmp.write_text(
        json.dumps({"schema_version": 2, "courses": {}, "lessons": {}}),
        encoding="utf-8",
    )
    progress, _was_corrupt = load_progress()
    assert progress.lessons == {} and progress.courses == {}, (
        "future schema_version must surface as fresh empty (the v9.0 "
        "migration seam)"
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
      * dots_for_course("course_1") → 0 dots (no lesson registered)
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
        "course_1 should have 0 dots — its lessons aren't registered "
        "in CURRICULUM yet (P94 lands them). Without filtering, the "
        f"unfiltered walk leaked into course_1: {course_1_dots!r}"
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
    import time
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
