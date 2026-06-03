# SPDX-License-Identifier: Apache-2.0
"""Owned-deck mini-player tempo engine (learning module).

In the live co-host vibemix only *observes* the decks; in the learning module it
*owns* them — it loads the tracks, controls the playhead, and therefore knows
each deck's exact beat phase at every sample. That perfect ground truth is what
lets the Beatmatch Judge say "you're 0.06 beats / 14 ms late on the 1".

The spine is a numpy port of Mixxx ``EngineBufferScaleLinear::do_scale``
(``enginebufferscalelinear.cpp``, source-verified in
``~/projects/mixxx-study/MIXXX-SCARS.md`` §6 — math/format facts re-derived
clean-room, no GPL code copied). The one load-bearing trick: the fractional read
cursor (``next_frame``) is carried across audio blocks, so the playhead never
drifts or gaps at a block boundary.

Adaptation vs the C++: Mixxx indexes a per-block read-ahead buffer that restarts
near 0 each block; here ``src`` is the whole-track slab indexed by ABSOLUTE
frame, so the cursor advances absolutely (``next_frame += rate * n``) instead of
resetting.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vibemix.audio.three_band_eq import ThreeBandEQ


def _do_scale_block(
    src: np.ndarray,
    next_frame: float,
    rate: float,
    n: int,
) -> tuple[np.ndarray, float]:
    """Resample ``n`` output frames from ``src`` at playback ``rate``.

    :param src: ``(M, 2)`` float32 source frames (a whole-track stereo slab),
        indexed by frame — never flat-interleaved (the C++ ``do_scale`` 05/12 trap).
    :param next_frame: fractional read cursor into ``src``, in source frames.
    :param rate: playback rate. ``1.0`` = normal, ``0.5`` = half-speed (pitch
        down an octave), ``2.0`` = double. Pitch moves with tempo — keylock-off
        vinyl/CDJ behaviour, which is what beatmatching teaches.
    :param n: number of output frames to produce this block.
    :returns: ``(out, next_frame_after)`` — ``out`` is ``(n, 2)`` float32 and
        ``next_frame_after`` is the carried cursor (the persistent accumulator).
    """
    # Output frames in SOURCE-frame coordinates — the vectorized form of the
    # C++ per-frame ``m_dNextFrame += rate_add`` accumulator loop.
    m = src.shape[0]
    pos = next_frame + rate * np.arange(n, dtype=np.float64)
    floor = np.floor(pos).astype(np.int64)
    frac = (pos - floor).astype(np.float32)[:, None]  # (n, 1), broadcast over channels

    # Clamp the gather indices so we never index out of bounds, then zero any
    # output frame whose true position is off the track — past the last sample
    # (finished/short track) or before the start (reverse/seek). This is the
    # Mixxx do_scale tail SampleUtil::clear "bail to silence" (05/10), vectorized:
    # a realtime callback degrades to silence, it never raises (C5).
    lo = np.clip(floor, 0, m - 1)
    hi = np.clip(floor + 1, 0, m - 1)

    # Two-point linear interpolation == the C++ inner lerp at :331-332.
    out = src[lo] + frac * (src[hi] - src[lo])
    out[(pos > m - 1) | (pos < 0.0)] = 0.0

    return out.astype(np.float32, copy=False), next_frame + rate * n


def _equal_power_gains(xfader: float) -> tuple[float, float]:
    """Equal-power crossfader gains for ``xfader`` in ``[0, 1]`` (0 = full A).

    Ported from the Mixxx ``EngineXfader`` constant-power law (scar 04 C5):
    ``g_a = cos(x·π/2)``, ``g_b = sin(x·π/2)`` so ``g_a² + g_b² == 1`` across the
    whole sweep (0.707 at center). Perceived loudness stays flat through a
    transition instead of dipping the way a naive linear fade does.
    """
    x = min(1.0, max(0.0, xfader))
    theta = x * (np.pi / 2.0)
    return float(np.cos(theta)), float(np.sin(theta))


@dataclass(frozen=True)
class DeckState:
    """Immutable snapshot of both decks for the asyncio loop / Beatmatch Judge.

    Positions are fractional SOURCE-frame cursors (1 frame == 1 sample-time at
    the track's sample rate) — exactly what the Judge needs to compute beat
    phase, since the deck owns the playhead. Snapshot, not a live handle: the
    audio callback advances the real cursors on the OS audio thread.
    """

    a_frame: float
    b_frame: float
    rate_a: float
    rate_b: float
    xfader: float


class MiniDeck:
    """Two owned decks (A/B) mixed through an equal-power crossfader.

    The learning module loads both tracks as whole-track stereo slabs and drives
    playback itself, so it always knows each deck's exact frame position. Each
    block, both decks are resampled by their current ``rate`` (pitch moves with
    tempo — keylock-off) and summed by the equal-power xfader gains. ``rate_a``,
    ``rate_b`` and ``xfader`` are plain attributes the control surface (real
    DDJ-FLX4 or the on-screen deck) writes between blocks.

    This is the state island the Judge reads; it does NOT write ``MusicState``
    (Cardinal Invariant #1, single-writer).
    """

    def __init__(
        self,
        src_a: np.ndarray,
        src_b: np.ndarray,
        *,
        rate_a: float = 1.0,
        rate_b: float = 1.0,
        xfader: float = 0.5,
        sample_rate: int = 44_100,
    ) -> None:
        self._src_a = np.asarray(src_a, dtype=np.float32)
        self._src_b = np.asarray(src_b, dtype=np.float32)
        self.rate_a = float(rate_a)
        self.rate_b = float(rate_b)
        self.xfader = float(xfader)
        self._frame_a = 0.0
        self._frame_b = 0.0
        self._eq_a = ThreeBandEQ(sample_rate=sample_rate)
        self._eq_b = ThreeBandEQ(sample_rate=sample_rate)

    def render_block(self, n: int) -> np.ndarray:
        """Render ``n`` mixed output frames, advancing both deck cursors."""
        out_a, self._frame_a = _do_scale_block(self._src_a, self._frame_a, self.rate_a, n)
        out_b, self._frame_b = _do_scale_block(self._src_b, self._frame_b, self.rate_b, n)
        out_a = self._eq_a.process(out_a)
        out_b = self._eq_b.process(out_b)
        gain_a, gain_b = _equal_power_gains(self.xfader)
        return (gain_a * out_a + gain_b * out_b).astype(np.float32)

    def set_eq(
        self,
        deck: str,
        *,
        low: float | int | None = None,
        mid: float | int | None = None,
        high: float | int | None = None,
    ) -> None:
        """Set one deck's EQ from controller CC values (0..127)."""

        target = self._eq_a if deck.upper() == "A" else self._eq_b
        target.set_cc(low=low, mid=mid, high=high)

    def state(self) -> DeckState:
        """Snapshot the two decks for the asyncio loop / Judge to read."""
        return DeckState(
            a_frame=self._frame_a,
            b_frame=self._frame_b,
            rate_a=self.rate_a,
            rate_b=self.rate_b,
            xfader=self.xfader,
        )
