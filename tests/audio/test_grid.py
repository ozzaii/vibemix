# SPDX-License-Identifier: Apache-2.0
"""Tests for the constant-tempo beatgrid — the phase oracle for the Judge.

Ported from Mixxx ``src/track/beats.cpp`` (scar dossier 02). The key model fact:
a beatgrid does NOT store beat positions — for constant tempo it is just
``(anchor_frame, bpm)`` and beat *k* is computed as ``anchor + k·beat_len``,
extrapolated infinitely in both directions. That computed phase is what lets the
owned deck report its exact beat position at any sample.
"""

from __future__ import annotations

import pytest

from vibemix.audio.grid import BeatGrid


def test_const_grid_beat_positions_and_indices() -> None:
    grid = BeatGrid(anchor_frame=0.0, bpm=120.0, sample_rate=44100)

    # 120 BPM @ 44.1k -> one beat = 60*44100/120 = 22050 frames.
    assert grid.beat_len_frames == pytest.approx(22050.0)
    assert grid.beat_at(0) == pytest.approx(0.0)
    assert grid.beat_at(4) == pytest.approx(88200.0)
    assert grid.beat_at(-1) == pytest.approx(-22050.0)  # extrapolates both ways, no stored list
    assert grid.beat_index(22050.0) == pytest.approx(1.0)
    assert grid.beat_index(11025.0) == pytest.approx(0.5)


def test_closest_beat_biases_to_next_on_exact_midpoint() -> None:
    grid = BeatGrid(anchor_frame=0.0, bpm=120.0, sample_rate=44100)  # beat_len 22050

    assert grid.closest_beat(1000.0) == pytest.approx(0.0)       # hugs beat 0
    assert grid.closest_beat(21000.0) == pytest.approx(22050.0)  # hugs beat 1
    # exact midpoint -> biased to the NEXT beat (scar 02 §5, strict `>`)
    assert grid.closest_beat(11025.0) == pytest.approx(22050.0)
    # already on a beat -> returns itself
    assert grid.closest_beat(44100.0) == pytest.approx(44100.0)


def test_beat_distance_is_fractional_phase_in_unit_interval() -> None:
    grid = BeatGrid(anchor_frame=0.0, bpm=120.0, sample_rate=44100)

    assert grid.beat_distance(0.0) == pytest.approx(0.0)
    assert grid.beat_distance(11025.0) == pytest.approx(0.5)
    assert grid.beat_distance(22050.0) == pytest.approx(0.0)    # wraps at the next beat
    assert grid.beat_distance(-11025.0) == pytest.approx(0.5)   # negatives wrap cleanly to [0,1)


def test_anchor_floored_to_whole_frame_and_bpm_validated() -> None:
    grid = BeatGrid(anchor_frame=100.7, bpm=120.0, sample_rate=44100)
    assert grid.anchor_frame == 100.0  # markers sit on whole frames (scar 02 §2)

    for bad_bpm in (0.0, -5.0, float("inf"), float("nan")):
        with pytest.raises(ValueError):
            BeatGrid(anchor_frame=0.0, bpm=bad_bpm, sample_rate=44100)
