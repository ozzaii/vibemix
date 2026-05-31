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
