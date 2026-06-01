# SPDX-License-Identifier: Apache-2.0
"""Constant-tempo beatgrid — the deck's beat-phase oracle.

In the learning module the deck OWNS the track, so it knows the track's beatgrid
exactly. The grid is the thing the Beatmatch Judge reads to answer "where is the
1, and how far off it is the student?".

Ported from Mixxx ``src/track/beats.cpp`` (scar dossier 02). The model fact: a
constant-tempo grid stores NO beat list — only ``(anchor_frame, bpm)``. Beat *k*
is computed ``anchor + k·beat_len``, extrapolated infinitely both directions
(beats.cpp §17). One beat in frames = ``60·sr/bpm``. Frames are samples per
channel; positions are doubles. Markers sit on whole frames, so the anchor is
floored on store (beats.h §2), and BPM is valid iff finite and > 0 (bpm.h §19).

Non-constant (marker-based) grids + the serialized parsers are pass-2 — the
owned-deck Judge only needs constant tempo.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any


class BeatGrid:
    """A constant-tempo beatgrid: ``anchor + k·beat_len`` for any integer beat k."""

    def __init__(self, *, anchor_frame: float, bpm: float, sample_rate: int) -> None:
        if not math.isfinite(bpm) or bpm <= 0.0:
            # Bpm valid iff finite and > 0; 0.0 is the "undefined" sentinel (bpm.h §19).
            raise ValueError(f"bpm must be finite and > 0, got {bpm!r}")
        self.anchor_frame = float(math.floor(anchor_frame))  # markers on whole frames (§2)
        self.bpm = float(bpm)
        self.sample_rate = int(sample_rate)
        self.beat_len_frames = 60.0 * self.sample_rate / self.bpm

    @classmethod
    def from_anlz(
        cls,
        beatgrid: Any,
        *,
        sample_rate: int,
        prefer_downbeat: bool = True,
    ) -> BeatGrid:
        """Build a constant grid from Rekordbox ANLZ beat-marker metadata.

        ANLZ stores marker times for beats plus beat-in-bar labels. This helper
        gives the owned-deck judge a clean shortcut from that metadata to the
        constant-tempo phase oracle it already understands. When a downbeat is
        present, beat index 0 anchors to the first bar ``1``; otherwise the first
        marker is used. Variable-tempo ANLZ is intentionally reduced to the
        local BPM at the anchor because :class:`BeatGrid` is constant-tempo.
        """
        times_s = _finite_floats(getattr(beatgrid, "times_s", ()))
        if not times_s:
            raise ValueError("ANLZ beatgrid has no finite beat times")

        beat_in_bar = _ints(getattr(beatgrid, "beat_in_bar", ()))
        anchor_idx = 0
        if prefer_downbeat:
            for idx, beat in enumerate(beat_in_bar[: len(times_s)]):
                if beat == 1:
                    anchor_idx = idx
                    break

        bpms = _finite_floats(getattr(beatgrid, "bpms", ()))
        bpm = _nearest_positive_bpm(bpms, anchor_idx)
        if bpm is None:
            bpm = _infer_bpm_from_times(times_s, anchor_idx)
        if bpm is None:
            raise ValueError("ANLZ beatgrid has no usable BPM")

        return cls(
            anchor_frame=times_s[anchor_idx] * int(sample_rate),
            bpm=bpm,
            sample_rate=sample_rate,
        )

    def beat_at(self, k: int) -> float:
        """Frame position of beat index ``k`` (negative extrapolates before the anchor)."""
        return self.anchor_frame + k * self.beat_len_frames

    def beat_index(self, frame: float) -> float:
        """Continuous beat number at ``frame`` (integer == on a beat)."""
        return (frame - self.anchor_frame) / self.beat_len_frames

    def beat_distance(self, frame: float) -> float:
        """Fractional phase within the current beat, in ``[0, 1)``.

        This is the Mixxx ``BpmControl`` "beat distance" the Judge compares
        between decks. Python ``%`` returns the sign of the divisor, so negatives
        wrap cleanly into ``[0, 1)`` without a branch.
        """
        return self.beat_index(frame) % 1.0

    def closest_beat(self, frame: float) -> float:
        """Frame of the nearest beat; an exact midpoint biases to the NEXT beat.

        Mirrors ``findClosestBeat`` (scar 02 §5): ``prev if (next-pos) > (pos-prev)
        else next`` — the strict ``>`` makes a position exactly on the midpoint
        resolve to the later beat, and a position on a beat returns itself.
        """
        prev_k = math.floor(self.beat_index(frame))
        prev_beat = self.beat_at(prev_k)
        next_beat = self.beat_at(prev_k + 1)
        return prev_beat if (next_beat - frame) > (frame - prev_beat) else next_beat


def _finite_floats(values: Sequence[Any]) -> tuple[float, ...]:
    out: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            out.append(number)
    return tuple(out)


def _ints(values: Sequence[Any]) -> tuple[int, ...]:
    out: list[int] = []
    for value in values:
        try:
            out.append(int(value))
        except (TypeError, ValueError):
            continue
    return tuple(out)


def _nearest_positive_bpm(bpms: Sequence[float], anchor_idx: int) -> float | None:
    candidates = [
        (abs(idx - anchor_idx), idx, bpm)
        for idx, bpm in enumerate(bpms)
        if math.isfinite(bpm) and bpm > 0.0
    ]
    if not candidates:
        return None
    _distance, _idx, bpm = min(candidates)
    return float(bpm)


def _infer_bpm_from_times(times_s: Sequence[float], anchor_idx: int) -> float | None:
    for left, right in ((anchor_idx, anchor_idx + 1), (anchor_idx - 1, anchor_idx)):
        if left < 0 or right >= len(times_s):
            continue
        delta = float(times_s[right]) - float(times_s[left])
        if math.isfinite(delta) and delta > 0.0:
            return 60.0 / delta
    return None
