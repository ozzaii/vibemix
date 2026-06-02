# SPDX-License-Identifier: Apache-2.0
"""Cue placement practice driver regression tests."""
from __future__ import annotations

from vibemix.learn.cue_placement_practice_driver import CuePlacementPracticeDriver
from vibemix.learn.cue_practice import grade_owned_cue_placement_state


def test_driver_is_honest_null_until_authored_hotcue_action() -> None:
    driver = CuePlacementPracticeDriver()

    assert driver.snapshot() is None
    assert driver.record_action(
        "L1.03",
        {"type": "button", "control": "hotcue", "deck": "B", "direction": "down"},
    ) is False
    assert driver.snapshot() is None


def test_driver_arms_l2_hotcue_b_as_drop_locked_practice() -> None:
    driver = CuePlacementPracticeDriver()

    assert driver.record_action(
        "L2.10",
        {"type": "button", "control": "hotcue", "deck": "B", "direction": "down"},
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


def test_driver_ignores_wrong_deck_and_preserves_honest_null() -> None:
    driver = CuePlacementPracticeDriver()

    assert driver.record_action(
        "L2.10",
        {"type": "button", "control": "hotcue", "deck": "A", "direction": "down"},
    ) is False

    assert driver.snapshot() is None
