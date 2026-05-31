# SPDX-License-Identifier: Apache-2.0
"""Tests for the Beatmatch Judge — the moat.

In the live co-host vibemix can only *observe* and infer; in the learning module
it OWNS both decks, so it knows each deck's exact beat phase and can grade a
beatmatch attempt against ground truth no observer-only competitor can match.

The two primitives are ported verbatim from Mixxx sync (scar dossier 07):
  * modular-1.0 beat-phase error  ``(target-cur+0.5) % 1 - 0.5``  (bpmcontrol.cpp:479, B1)
  * √2 octave-fold tempo multiplier  ``2 / 0.5 / 1``              (synccontrol.cpp:290, A1)
"""

from __future__ import annotations

import pytest

from vibemix.audio.grid import BeatGrid
from vibemix.audio.miniplayer import DeckState
from vibemix.learn.beatmatch_judge import (
    BeatmatchGrade,
    _octave_fold_multiplier,
    _phase_error,
    grade_beatmatch,
)

SR = 44100


def _state(a_frame: float, b_frame: float, *, rate_a: float = 1.0, rate_b: float = 1.0) -> DeckState:
    return DeckState(a_frame=a_frame, b_frame=b_frame, rate_a=rate_a, rate_b=rate_b, xfader=0.5)


def test_phase_error_takes_the_short_way_around_the_beat_circle() -> None:
    # Beat distance is modular in [0,1): 0.99 vs 0.01 is 0.02 apart, NOT 0.98.
    assert _phase_error(0.99, 0.01) == pytest.approx(0.02)
    assert _phase_error(0.01, 0.99) == pytest.approx(-0.02)
    # Perfectly aligned -> zero error.
    assert _phase_error(0.25, 0.25) == pytest.approx(0.0)
    # Half a beat apart is the max magnitude, always within [-0.5, 0.5].
    assert abs(_phase_error(0.0, 0.5)) == pytest.approx(0.5)
    for cur in (0.0, 0.13, 0.5, 0.77, 0.999):
        for tgt in (0.0, 0.2, 0.49, 0.8, 0.95):
            assert -0.5 <= _phase_error(cur, tgt) <= 0.5


def test_octave_fold_multiplier_folds_double_and_half_at_sqrt2() -> None:
    # 128 vs 64 -> ratio 2.0, r^2=4 > 2 -> fold by 2 (octave-equivalent tempo).
    assert _octave_fold_multiplier(2.0) == 2.0
    # 64 vs 128 -> ratio 0.5, r^2=0.25 < 0.5 -> fold by 0.5.
    assert _octave_fold_multiplier(0.5) == 0.5
    # Same tempo -> no fold.
    assert _octave_fold_multiplier(1.0) == 1.0
    # The split is strict on r^2 vs 2.0 / 0.5. Just below √2 stays unity, just above folds:
    assert _octave_fold_multiplier(1.41) == 1.0  # 1.41^2 = 1.9881 < 2
    assert _octave_fold_multiplier(1.42) == 2.0  # 1.42^2 = 2.0164 > 2
    assert _octave_fold_multiplier(0.71) == 1.0  # 0.71^2 = 0.5041 > 0.5
    assert _octave_fold_multiplier(0.70) == 0.5  # 0.70^2 = 0.49 < 0.5
    # Float trap (faithful to Mixxx's C++ double): sqrt(2)**2 == 2.0000000000000004,
    # which IS > 2.0, so an exact-√2 ratio tips over and folds rather than staying unity.
    assert _octave_fold_multiplier(2.0**0.5) == 2.0


def test_grade_perfect_match_is_locked() -> None:
    grid = BeatGrid(anchor_frame=0.0, bpm=128.0, sample_rate=SR)
    grade = grade_beatmatch(grid, grid, _state(0.0, 0.0))

    assert isinstance(grade, BeatmatchGrade)
    assert grade.abstain is False
    assert grade.tempo_matched is True
    assert grade.phase_locked is True
    assert grade.tempo_error == pytest.approx(0.0)
    assert grade.phase_error_beats == pytest.approx(0.0)
    assert grade.verdict == "locked"
    assert grade.score == pytest.approx(1.0)


def test_grade_octave_apart_but_aligned_counts_as_matched() -> None:
    # 128 vs 64 BPM, both on the 1 -> √2 fold makes them octave-equivalent tempo.
    grid_a = BeatGrid(anchor_frame=0.0, bpm=128.0, sample_rate=SR)
    grid_b = BeatGrid(anchor_frame=0.0, bpm=64.0, sample_rate=SR)

    grade = grade_beatmatch(grid_a, grid_b, _state(0.0, 0.0))

    assert grade.tempo_matched is True       # folded ratio == 1.0
    assert grade.tempo_error == pytest.approx(0.0)
    assert grade.verdict == "locked"


def test_grade_tempo_off_is_not_matched() -> None:
    grid_a = BeatGrid(anchor_frame=0.0, bpm=120.0, sample_rate=SR)
    grid_b = BeatGrid(anchor_frame=0.0, bpm=128.0, sample_rate=SR)

    grade = grade_beatmatch(grid_a, grid_b, _state(0.0, 0.0))

    assert grade.tempo_matched is False
    assert grade.tempo_error == pytest.approx(128.0 / 120.0 - 1.0)  # 6.67% off
    assert grade.verdict == "tempo_off"
    assert grade.score < 0.5


def test_grade_abstains_when_a_deck_is_stopped() -> None:
    grid = BeatGrid(anchor_frame=0.0, bpm=128.0, sample_rate=SR)

    grade = grade_beatmatch(grid, grid, _state(0.0, 0.0, rate_b=0.0))

    assert grade.abstain is True
    assert grade.verdict == "abstain"
    assert grade.score == 0.0


def test_grade_small_phase_offset_is_drifting_not_locked() -> None:
    grid = BeatGrid(anchor_frame=0.0, bpm=128.0, sample_rate=SR)
    beat_len = grid.beat_len_frames
    # deck B sits 0.05 beat AHEAD of deck A.
    grade = grade_beatmatch(grid, grid, _state(0.0, 0.05 * beat_len))

    assert grade.tempo_matched is True
    assert grade.phase_locked is False
    assert grade.phase_error_beats == pytest.approx(-0.05)  # B ahead -> negative
    assert grade.recoverable_late is False                  # ahead, not behind
    assert grade.verdict == "drifting"


def test_grade_slightly_behind_within_eighth_beat_is_recoverable() -> None:
    grid = BeatGrid(anchor_frame=0.0, bpm=128.0, sample_rate=SR)
    beat_len = grid.beat_len_frames
    # deck B sits 0.1 beat BEHIND deck A (dist_b = 0.9 -> phase +0.1, within 1/8).
    grade = grade_beatmatch(grid, grid, _state(0.0, 0.9 * beat_len))

    assert grade.phase_error_beats == pytest.approx(0.1)
    assert grade.recoverable_late is True   # behind by <= 1/8 beat -> catch the prev beat
    assert grade.verdict == "drifting"
