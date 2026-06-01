# SPDX-License-Identifier: Apache-2.0
"""Tests for the owned-deck cue placement judge."""

from __future__ import annotations

import pytest

from vibemix.audio.grid import BeatGrid
from vibemix.learn.cue_placement_judge import CuePlacementGrade, grade_cue_placement

SR = 48000


def _grid() -> BeatGrid:
    return BeatGrid(anchor_frame=0.0, bpm=120.0, sample_rate=SR)


def test_exact_beat_cue_is_locked() -> None:
    grid = _grid()

    grade = grade_cue_placement(grid, grid.beat_at(8))

    assert isinstance(grade, CuePlacementGrade)
    assert grade.beat_aligned is True
    assert grade.target_aligned is None
    assert grade.nearest_beat_frame == pytest.approx(grid.beat_at(8))
    assert grade.beat_error_beats == pytest.approx(0.0)
    assert grade.verdict == "beat_locked"
    assert grade.score == pytest.approx(1.0)


def test_small_late_cue_stays_aligned_with_signed_error() -> None:
    grid = _grid()
    cue = grid.beat_at(4) + 0.02 * grid.beat_len_frames

    grade = grade_cue_placement(grid, cue)

    assert grade.beat_aligned is True
    assert grade.beat_error_beats == pytest.approx(0.02)
    assert grade.verdict == "beat_locked"
    assert 0.9 < grade.score < 1.0


def test_offbeat_cue_reports_nearest_beat_and_low_score() -> None:
    grid = _grid()
    cue = grid.beat_at(4) + 0.20 * grid.beat_len_frames

    grade = grade_cue_placement(grid, cue)

    assert grade.beat_aligned is False
    assert grade.nearest_beat_frame == pytest.approx(grid.beat_at(4))
    assert grade.beat_error_beats == pytest.approx(0.20)
    assert grade.verdict == "off_beat"
    assert grade.score < 0.25


def test_exact_midpoint_biases_to_next_beat_like_grid() -> None:
    grid = _grid()
    cue = grid.beat_at(2) + 0.5 * grid.beat_len_frames

    grade = grade_cue_placement(grid, cue)

    assert grade.nearest_beat_frame == pytest.approx(grid.beat_at(3))
    assert grade.beat_error_beats == pytest.approx(-0.5)
    assert grade.verdict == "off_beat"
    assert grade.score == pytest.approx(0.0)


def test_target_drop_must_be_absolute_not_just_on_any_beat() -> None:
    grid = _grid()
    target = grid.beat_at(16)

    locked = grade_cue_placement(grid, target, target_frame=target)
    wrong_drop = grade_cue_placement(grid, grid.beat_at(17), target_frame=target)

    assert locked.target_aligned is True
    assert locked.target_error_beats == pytest.approx(0.0)
    assert locked.verdict == "drop_locked"
    assert locked.score == pytest.approx(1.0)
    assert wrong_drop.beat_aligned is True
    assert wrong_drop.target_aligned is False
    assert wrong_drop.target_error_beats == pytest.approx(1.0)
    assert wrong_drop.verdict == "wrong_drop"
    assert wrong_drop.score == pytest.approx(0.0)


def test_rejects_nonfinite_frames_and_tolerances() -> None:
    grid = _grid()

    with pytest.raises(ValueError, match="cue_frame must be finite"):
        grade_cue_placement(grid, float("nan"))
    with pytest.raises(ValueError, match="target_frame must be finite"):
        grade_cue_placement(grid, 0.0, target_frame=float("inf"))
    with pytest.raises(ValueError, match="beat_lock_tolerance_beats must be finite and > 0"):
        grade_cue_placement(grid, 0.0, beat_lock_tolerance_beats=0.0)
    with pytest.raises(ValueError, match="target_tolerance_beats must be finite and > 0"):
        grade_cue_placement(grid, 0.0, target_tolerance_beats=float("nan"))
