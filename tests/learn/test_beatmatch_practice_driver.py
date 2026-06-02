# SPDX-License-Identifier: Apache-2.0
"""Learn-owned beatmatch practice driver tests."""

from __future__ import annotations

from vibemix.learn.beatmatch_practice_driver import BeatmatchPracticeDriver
from vibemix.learn.practice_loop import grade_owned_beatmatch_state


def _grade(driver: BeatmatchPracticeDriver):
    snapshot = driver.snapshot()
    assert snapshot is not None
    return grade_owned_beatmatch_state(
        snapshot.grid_a,
        snapshot.grid_b,
        snapshot.deck_state,
    )


def test_driver_is_honest_null_until_a_beatmatch_lesson_action() -> None:
    driver = BeatmatchPracticeDriver()

    assert driver.snapshot() is None
    assert driver.record_action("L1.03", {"control": "tempo", "deck": "B", "value": 64}) is False
    assert driver.snapshot() is None


def test_ear_practice_centered_pitch_fader_produces_locked_owned_deck_state() -> None:
    driver = BeatmatchPracticeDriver()

    assert driver.record_action("L2.01", {"control": "tempo", "deck": "B", "value": 64}) is True
    grade = _grade(driver)

    assert grade.verdict == "locked"
    assert grade.tempo_matched is True
    assert grade.phase_locked is True


def test_ear_practice_large_pitch_move_does_not_credit_as_locked() -> None:
    driver = BeatmatchPracticeDriver()

    assert driver.record_action("L2.01", {"control": "tempo", "deck": "B", "value": 100}) is True
    grade = _grade(driver)

    assert grade.verdict == "tempo_off"
    assert grade.tempo_matched is False


def test_sync_practice_snaps_owned_deck_to_locked_state() -> None:
    driver = BeatmatchPracticeDriver()

    assert (
        driver.record_action(
            "L2.02",
            {"type": "button", "control": "sync", "deck": "B", "direction": "down"},
        )
        is True
    )
    grade = _grade(driver)

    assert grade.verdict == "locked"
    assert grade.tempo_matched is True
    assert grade.phase_locked is True
