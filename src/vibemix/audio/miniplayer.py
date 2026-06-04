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


def _do_scale_block(
    src: np.ndarray,
    next_frame: float,
    rate: float,
    n: int,
    *,
    prev_rate: float | None = None,
    loop: bool = False,
) -> tuple[np.ndarray, float]:
    """Resample ``n`` output frames from ``src`` at playback ``rate``.

    :param src: ``(M, 2)`` float32 source frames (a whole-track stereo slab),
        indexed by frame — never flat-interleaved (the C++ ``do_scale`` 05/12 trap).
    :param next_frame: fractional read cursor into ``src``, in source frames.
    :param rate: playback rate. ``1.0`` = normal, ``0.5`` = half-speed (pitch
        down an octave), ``2.0`` = double. Pitch moves with tempo — keylock-off
        vinyl/CDJ behaviour, which is what beatmatching teaches.
    :param n: number of output frames to produce this block.
    :param prev_rate: optional rate from the previous block. When provided and
        different from ``rate``, the rate is linearly ramped across this block
        and integrated into the carried cursor.
    :returns: ``(out, next_frame_after)`` — ``out`` is ``(n, 2)`` float32 and
        ``next_frame_after`` is the carried cursor (the persistent accumulator).
    """
    # Output frames in SOURCE-frame coordinates — the vectorized form of the
    # C++ per-frame ``m_dNextFrame += rate_add`` accumulator loop.
    m = src.shape[0]
    rate = float(rate)
    prev_rate = rate if prev_rate is None else float(prev_rate)
    if prev_rate == rate:
        pos = next_frame + rate * np.arange(n, dtype=np.float64)
        next_frame_after = next_frame + rate * n
    else:
        rate_ramp = np.linspace(prev_rate, rate, n, dtype=np.float64)
        pos = next_frame + np.cumsum(rate_ramp) - rate_ramp
        next_frame_after = next_frame + float(np.sum(rate_ramp))
    if loop:
        wrapped_pos = np.mod(pos, m)
        floor = np.floor(wrapped_pos).astype(np.int64)
        frac = (wrapped_pos - floor).astype(np.float32)[:, None]
        lo = floor
        hi = (floor + 1) % m
        out = src[lo] + frac * (src[hi] - src[lo])
        return out.astype(np.float32, copy=False), next_frame_after

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

    return out.astype(np.float32, copy=False), next_frame_after


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


def _gain_to_unit(value: float | int | None, *, default: float = 1.0) -> float:
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return min(1.0, max(0.0, default))
    if raw <= 1.0:
        return min(1.0, max(0.0, raw))
    return min(1.0, max(0.0, raw / 127.0))


def _filter_cutoff_from_cc(value: float | int | None, sample_rate: int) -> tuple[str, float]:
    """Map centered DJ filter CC to high-pass/low-pass mode and cutoff."""

    try:
        cc = float(value)
    except (TypeError, ValueError):
        cc = 64.0
    cc = min(127.0, max(0.0, cc))
    nyquist = float(sample_rate) / 2.0
    if abs(cc - 64.0) <= 1.0:
        return "lowpass", nyquist * 0.94
    if cc < 64.0:
        # Left sweep: high-pass from barely audible to roughly 1 kHz.
        amount = (64.0 - cc) / 64.0
        return "highpass", 24.0 * ((1_000.0 / 24.0) ** amount)
    amount = (cc - 64.0) / 63.0
    # Right sweep: low-pass down from open air to roughly 650 Hz.
    return "lowpass", (nyquist * 0.94) * ((650.0 / (nyquist * 0.94)) ** amount)


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
    vol_a: float = 1.0
    vol_b: float = 1.0


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
        vol_a: float = 1.0,
        vol_b: float = 1.0,
        sample_rate: int = 44_100,
        loop: bool = False,
    ) -> None:
        from vibemix.learn.dj_eq import ResonantFilter, ThreeBandEQ

        self._src_a = np.asarray(src_a, dtype=np.float32)
        self._src_b = np.asarray(src_b, dtype=np.float32)
        self.rate_a = float(rate_a)
        self.rate_b = float(rate_b)
        self.xfader = float(xfader)
        self.vol_a = _gain_to_unit(vol_a, default=float(vol_a))
        self.vol_b = _gain_to_unit(vol_b, default=float(vol_b))
        self._sample_rate = int(sample_rate)
        self._loop = bool(loop)
        self._frame_a = 0.0
        self._frame_b = 0.0
        self._eq_a = ThreeBandEQ(sample_rate=sample_rate)
        self._eq_b = ThreeBandEQ(sample_rate=sample_rate)
        self._filter_a = ResonantFilter(sample_rate=sample_rate, mode="lowpass")
        self._filter_b = ResonantFilter(sample_rate=sample_rate, mode="lowpass")
        self._filter_a_active = False
        self._filter_b_active = False
        self._prev_rate_a = self.rate_a
        self._prev_rate_b = self.rate_b
        xfader_gain_a, xfader_gain_b = _equal_power_gains(self.xfader)
        self._prev_gain_a = xfader_gain_a * self.vol_a
        self._prev_gain_b = xfader_gain_b * self.vol_b

    def render_block(self, n: int) -> np.ndarray:
        """Render ``n`` mixed output frames, advancing both deck cursors."""
        rate_a = float(self.rate_a)
        rate_b = float(self.rate_b)
        out_a, self._frame_a = _do_scale_block(
            self._src_a,
            self._frame_a,
            rate_a,
            n,
            prev_rate=self._prev_rate_a,
            loop=self._loop,
        )
        out_b, self._frame_b = _do_scale_block(
            self._src_b,
            self._frame_b,
            rate_b,
            n,
            prev_rate=self._prev_rate_b,
            loop=self._loop,
        )
        out_a = self._eq_a.process(out_a)
        out_b = self._eq_b.process(out_b)
        if self._filter_a_active:
            out_a = self._filter_a.process(out_a)
        if self._filter_b_active:
            out_b = self._filter_b.process(out_b)
        xfader_gain_a, xfader_gain_b = _equal_power_gains(self.xfader)
        gain_a = xfader_gain_a * min(1.0, max(0.0, float(self.vol_a)))
        gain_b = xfader_gain_b * min(1.0, max(0.0, float(self.vol_b)))
        if self._prev_gain_a == gain_a and self._prev_gain_b == gain_b:
            mixed = gain_a * out_a + gain_b * out_b
        else:
            gain_a_ramp = np.linspace(self._prev_gain_a, gain_a, n, dtype=np.float32)[:, None]
            gain_b_ramp = np.linspace(self._prev_gain_b, gain_b, n, dtype=np.float32)[:, None]
            mixed = gain_a_ramp * out_a + gain_b_ramp * out_b
        self._prev_rate_a = rate_a
        self._prev_rate_b = rate_b
        self._prev_gain_a = gain_a
        self._prev_gain_b = gain_b
        return mixed.astype(np.float32)

    def set_rates(
        self,
        *,
        rate_a: float | None = None,
        rate_b: float | None = None,
        smooth: bool = True,
    ) -> None:
        """Set deck rates, optionally latching the ramp state immediately."""

        if rate_a is not None:
            self.rate_a = float(rate_a)
            if not smooth:
                self._prev_rate_a = self.rate_a
        if rate_b is not None:
            self.rate_b = float(rate_b)
            if not smooth:
                self._prev_rate_b = self.rate_b

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

    def set_volume(self, deck: str, value: float | int | None) -> None:
        """Set one channel fader from controller CC values (0..127)."""

        if deck.upper() == "A":
            self.vol_a = _gain_to_unit(value, default=self.vol_a)
        else:
            self.vol_b = _gain_to_unit(value, default=self.vol_b)

    def set_filter(self, deck: str, value: float | int | None) -> None:
        """Set one deck's centered color filter from controller CC values."""

        mode, cutoff = _filter_cutoff_from_cc(value, self._sample_rate)
        deck_id = deck.upper()
        target = self._filter_a if deck_id == "A" else self._filter_b
        target.set_mode(mode)
        target.set_cutoff_hz(cutoff)
        try:
            cc = float(value)
        except (TypeError, ValueError):
            cc = 64.0
        active = abs(min(127.0, max(0.0, cc)) - 64.0) > 1.0
        if deck_id == "A":
            self._filter_a_active = active
        else:
            self._filter_b_active = active

    def state(self) -> DeckState:
        """Snapshot the two decks for the asyncio loop / Judge to read."""
        return DeckState(
            a_frame=self._frame_a,
            b_frame=self._frame_b,
            rate_a=self.rate_a,
            rate_b=self.rate_b,
            xfader=self.xfader,
            vol_a=self.vol_a,
            vol_b=self.vol_b,
        )
