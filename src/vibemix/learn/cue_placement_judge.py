# SPDX-License-Identifier: Apache-2.0
"""Cue placement judge — grade hot-cue timing against an owned beatgrid.

This is the cue half of the owned-deck Learn moat: when Learn loaded the track,
it can judge whether a cue sits on the beat without guessing from live audio.
No runtime speech or skill credit is emitted here; this module is an offline
primitive for later practice packages.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from vibemix.audio.grid import BeatGrid

_BEAT_LOCK_TOL = 1.0 / 32.0
_TARGET_LOCK_TOL = 1.0 / 8.0
_ZERO_SCORE_TOL = 1.0 / 4.0


@dataclass(frozen=True)
class CuePlacementGrade:
    """Measured cue timing relative to the nearest beat and optional target frame."""

    cue_frame: float
    nearest_beat_frame: float
    beat_error_beats: float  # signed: >0 cue is late, <0 cue is early
    beat_aligned: bool
    target_error_beats: float | None  # signed absolute target error when target_frame is provided
    target_aligned: bool | None
    verdict: str  # beat_locked | drop_locked | off_beat | wrong_drop
    score: float


def grade_cue_placement(
    grid: BeatGrid,
    cue_frame: float,
    *,
    target_frame: float | None = None,
    beat_lock_tolerance_beats: float = _BEAT_LOCK_TOL,
    target_tolerance_beats: float = _TARGET_LOCK_TOL,
) -> CuePlacementGrade:
    """Grade whether ``cue_frame`` lands on the beat, and optionally on a target drop.

    ``target_frame`` is an absolute event/drop frame. Beat alignment is modular
    against the closest beat; target alignment is not modular because a cue one
    beat away from the intended drop is still the wrong drop.
    """
    cue = _finite_frame(cue_frame, "cue_frame")
    beat_tol = _positive_tolerance(beat_lock_tolerance_beats, "beat_lock_tolerance_beats")
    target_tol = _positive_tolerance(target_tolerance_beats, "target_tolerance_beats")

    nearest = grid.closest_beat(cue)
    beat_error = (cue - nearest) / grid.beat_len_frames
    beat_aligned = abs(beat_error) <= beat_tol

    target_error: float | None = None
    target_aligned: bool | None = None
    if target_frame is not None:
        target = _finite_frame(target_frame, "target_frame")
        target_error = (cue - target) / grid.beat_len_frames
        target_aligned = abs(target_error) <= target_tol

    if not beat_aligned:
        verdict = "off_beat"
    elif target_aligned is None:
        verdict = "beat_locked"
    elif target_aligned:
        verdict = "drop_locked"
    else:
        verdict = "wrong_drop"

    beat_score = _component_score(abs(beat_error), _ZERO_SCORE_TOL)
    target_score = 1.0 if target_error is None else _component_score(abs(target_error), target_tol)

    return CuePlacementGrade(
        cue_frame=cue,
        nearest_beat_frame=nearest,
        beat_error_beats=beat_error,
        beat_aligned=beat_aligned,
        target_error_beats=target_error,
        target_aligned=target_aligned,
        verdict=verdict,
        score=round(beat_score * target_score, 4),
    )


def _finite_frame(value: float, name: str) -> float:
    try:
        frame = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(frame):
        raise ValueError(f"{name} must be finite")
    return frame


def _positive_tolerance(value: float, name: str) -> float:
    try:
        tol = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite and > 0") from exc
    if not math.isfinite(tol) or tol <= 0.0:
        raise ValueError(f"{name} must be finite and > 0")
    return tol


def _component_score(error_beats: float, zero_score_at: float) -> float:
    return max(0.0, 1.0 - error_beats / zero_score_at)
