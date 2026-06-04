# SPDX-License-Identifier: Apache-2.0
"""Cue placement practice driver regression tests."""
from __future__ import annotations

from vibemix.learn.cue_placement_practice_driver import CuePlacementPracticeDriver
from vibemix.learn.cue_practice import grade_owned_cue_placement_state

_TARGET_ELAPSED_S = 16.0 * 60.0 / 128.0


def test_driver_is_honest_null_until_authored_hotcue_action() -> None:
    driver = CuePlacementPracticeDriver()

    assert driver.snapshot() is None
    assert driver.record_action(
        "L1.03",
        {"type": "button", "control": "hotcue", "deck": "B", "direction": "down"},
    ) is False
    assert driver.snapshot() is None

    assert driver.record_action(
        "L2.10",
        {"type": "button", "control": "hotcue", "deck": "B", "direction": "down"},
    ) is False
    assert driver.snapshot() is None


def test_driver_arms_l2_hotcue_b_as_drop_locked_practice() -> None:
    driver = CuePlacementPracticeDriver()

    assert driver.record_action(
        "L2.10",
        {
            "type": "button",
            "control": "hotcue",
            "deck": "B",
            "direction": "down",
            "action_elapsed_s": _TARGET_ELAPSED_S,
        },
    ) is True

    snapshot = driver.snapshot()
    assert snapshot is not None
    grade = grade_owned_cue_placement_state(
        snapshot.grid,
        snapshot.cue_frame,
        target_frame=snapshot.target_frame,
    )
    assert grade.verdict == "drop_locked"
    assert grade.beat_aligned is True
    assert grade.target_aligned is True


def test_driver_prefers_cue_frame_over_wall_clock_elapsed() -> None:
    driver = CuePlacementPracticeDriver()
    target_frame = _TARGET_ELAPSED_S * 44_100

    assert driver.record_action(
        "L2.10",
        {
            "type": "button",
            "control": "hotcue",
            "deck": "B",
            "direction": "down",
            "cue_frame": target_frame,
            "action_elapsed_s": 999.0,
        },
    ) is True

    snapshot = driver.snapshot()
    assert snapshot is not None
    grade = grade_owned_cue_placement_state(
        snapshot.grid,
        snapshot.cue_frame,
        target_frame=snapshot.target_frame,
    )
    assert grade.verdict == "drop_locked"
    assert grade.beat_aligned is True
    assert grade.target_aligned is True


def test_driver_grades_real_late_press_as_wrong_drop() -> None:
    driver = CuePlacementPracticeDriver()

    assert driver.record_action(
        "L2.10",
        {
            "type": "button",
            "control": "hotcue",
            "deck": "B",
            "direction": "down",
            "press_offset_beats": 1.0,
        },
    ) is True

    snapshot = driver.snapshot()
    assert snapshot is not None
    grade = grade_owned_cue_placement_state(
        snapshot.grid,
        snapshot.cue_frame,
        target_frame=snapshot.target_frame,
    )
    assert grade.verdict == "wrong_drop"
    assert grade.beat_aligned is True
    assert grade.target_aligned is False


def test_driver_ignores_wrong_deck_and_preserves_honest_null() -> None:
    driver = CuePlacementPracticeDriver()

    assert driver.record_action(
        "L2.10",
        {"type": "button", "control": "hotcue", "deck": "A", "direction": "down"},
    ) is False

    assert driver.snapshot() is None
