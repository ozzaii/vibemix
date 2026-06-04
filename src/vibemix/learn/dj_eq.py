# SPDX-License-Identifier: Apache-2.0
"""Learn-owned DJ EQ, resonant filter, and constant-power fader.

Clean-room DSP from the RBJ Audio EQ Cookbook formulae plus standard one-pole
parameter smoothing. No GPL/AGPL implementation source is copied here: the
crossovers are product tuning facts, the coefficients are reimplemented from
published equations, and the local SOS loop uses the same negative-feedback
DF2T state layout as ``scipy.signal.sosfilt`` without adding scipy to the
one-click runtime.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np

FilterMode = Literal["lowpass", "highpass"]

_Coeff = tuple[float, float, float, float, float, float]
_IDENTITY: _Coeff = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
_BOOST_DB = 12.0
_CUT_DB = 26.0
_DEFAULT_CONTROL_CHUNK = 32


def initial_zi(n_sections: int) -> np.ndarray:
    """Return the verified zero initial state for DF2T SOS sections."""

    return np.zeros((max(1, int(n_sections)), 2), dtype=np.float64)


def cc_to_gain_db(value: float | int | None) -> float:
    """Map a 0..127 DJ EQ CC to asymmetric cut/boost dB, with 64 == noon."""

    if value is None:
        return 0.0
    try:
        cc = float(value)
    except (TypeError, ValueError):
        return 0.0
    cc = min(127.0, max(0.0, cc))
    if cc >= 64.0:
        return ((cc - 64.0) / 63.0) * _BOOST_DB
    return ((cc - 64.0) / 64.0) * _CUT_DB


def knob_to_gain_db(value: float | int | None) -> float:
    """Map a 0..2 DJ EQ knob (1 == noon) to asymmetric cut/boost dB."""

    if value is None:
        return 0.0
    try:
        knob = float(value)
    except (TypeError, ValueError):
        return 0.0
    knob = min(2.0, max(0.0, knob))
    delta = knob - 1.0
    if delta >= 0.0:
        return delta * _BOOST_DB
    return delta * _CUT_DB


def _sanitize_sample_rate(sample_rate: int | float) -> int:
    try:
        sr = int(sample_rate)
    except (TypeError, ValueError):
        sr = 44_100
    return max(1_000, sr)


def _sanitize_block(block: np.ndarray) -> tuple[np.ndarray, bool]:
    x = np.asarray(block, dtype=np.float32)
    if x.ndim == 1:
        return x[:, None], True
    if x.ndim != 2:
        raise ValueError(f"audio block must be 1D or 2D, got shape={x.shape!r}")
    return x, False


def _restore_shape(block: np.ndarray, was_mono: bool) -> np.ndarray:
    if was_mono:
        return block[:, 0].astype(np.float32, copy=False)
    return block.astype(np.float32, copy=False)


def _normalize(b0: float, b1: float, b2: float, a0: float, a1: float, a2: float) -> _Coeff:
    if not math.isfinite(a0) or abs(a0) < 1e-12:
        return _IDENTITY
    return (b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0)


def _terms(freq_hz: float, sample_rate: int, q: float) -> tuple[float, float, float]:
    nyquist = float(sample_rate) / 2.0
    freq = min(nyquist * 0.98, max(10.0, float(freq_hz)))
    w0 = 2.0 * math.pi * (freq / float(sample_rate))
    sinw0 = math.sin(w0)
    return math.cos(w0), sinw0, sinw0 / (2.0 * max(1e-6, float(q)))


def _rbj_peaking(freq_hz: float, q: float, gain_db: float, sample_rate: int) -> _Coeff:
    if abs(gain_db) < 1e-9:
        return _IDENTITY
    cosw0, _sinw0, alpha = _terms(freq_hz, sample_rate, q)
    amp = 10.0 ** (gain_db / 40.0)
    return _normalize(
        1.0 + alpha * amp,
        -2.0 * cosw0,
        1.0 - alpha * amp,
        1.0 + alpha / amp,
        -2.0 * cosw0,
        1.0 - alpha / amp,
    )


def _shelf_alpha(freq_hz: float, sample_rate: int, gain_db: float, slope: float) -> tuple[
    float,
    float,
    float,
    float,
]:
    cosw0, sinw0, _alpha = _terms(freq_hz, sample_rate, 0.7071)
    amp = 10.0 ** (gain_db / 40.0)
    slope = max(1e-6, float(slope))
    root = max(0.0, (amp + (1.0 / amp)) * ((1.0 / slope) - 1.0) + 2.0)
    alpha = (sinw0 / 2.0) * math.sqrt(root)
    return amp, cosw0, alpha, 2.0 * math.sqrt(amp) * alpha


def _rbj_low_shelf(freq_hz: float, slope: float, gain_db: float, sample_rate: int) -> _Coeff:
    if abs(gain_db) < 1e-9:
        return _IDENTITY
    amp, cosw0, _alpha, two_sqrt_a_alpha = _shelf_alpha(
        freq_hz,
        sample_rate,
        gain_db,
        slope,
    )
    return _normalize(
        amp * ((amp + 1.0) - (amp - 1.0) * cosw0 + two_sqrt_a_alpha),
        2.0 * amp * ((amp - 1.0) - (amp + 1.0) * cosw0),
        amp * ((amp + 1.0) - (amp - 1.0) * cosw0 - two_sqrt_a_alpha),
        (amp + 1.0) + (amp - 1.0) * cosw0 + two_sqrt_a_alpha,
        -2.0 * ((amp - 1.0) + (amp + 1.0) * cosw0),
        (amp + 1.0) + (amp - 1.0) * cosw0 - two_sqrt_a_alpha,
    )


def _rbj_high_shelf(freq_hz: float, slope: float, gain_db: float, sample_rate: int) -> _Coeff:
    if abs(gain_db) < 1e-9:
        return _IDENTITY
    amp, cosw0, _alpha, two_sqrt_a_alpha = _shelf_alpha(
        freq_hz,
        sample_rate,
        gain_db,
        slope,
    )
    return _normalize(
        amp * ((amp + 1.0) + (amp - 1.0) * cosw0 + two_sqrt_a_alpha),
        -2.0 * amp * ((amp - 1.0) + (amp + 1.0) * cosw0),
        amp * ((amp + 1.0) + (amp - 1.0) * cosw0 - two_sqrt_a_alpha),
        (amp + 1.0) - (amp - 1.0) * cosw0 + two_sqrt_a_alpha,
        2.0 * ((amp - 1.0) - (amp + 1.0) * cosw0),
        (amp + 1.0) - (amp - 1.0) * cosw0 - two_sqrt_a_alpha,
    )


def _rbj_lowpass(freq_hz: float, q: float, sample_rate: int) -> _Coeff:
    cosw0, _sinw0, alpha = _terms(freq_hz, sample_rate, q)
    return _normalize(
        (1.0 - cosw0) / 2.0,
        1.0 - cosw0,
        (1.0 - cosw0) / 2.0,
        1.0 + alpha,
        -2.0 * cosw0,
        1.0 - alpha,
    )


def _rbj_highpass(freq_hz: float, q: float, sample_rate: int) -> _Coeff:
    cosw0, _sinw0, alpha = _terms(freq_hz, sample_rate, q)
    return _normalize(
        (1.0 + cosw0) / 2.0,
        -(1.0 + cosw0),
        (1.0 + cosw0) / 2.0,
        1.0 + alpha,
        -2.0 * cosw0,
        1.0 - alpha,
    )


def _coeff_to_sos(coeff: _Coeff) -> np.ndarray:
    return np.asarray([coeff], dtype=np.float64)


def _sosfilt_df2t(
    sos: np.ndarray,
    block: np.ndarray,
    zi: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Process ``block`` with a negative-feedback DF2T SOS cascade.

    ``zi`` is shaped like scipy's axis-0 multichannel state:
    ``(n_sections, 2, n_channels)``. Coefficients are normalized so ``a0`` is
    1.0; the feedback signs are the RBJ/scipy convention:
    ``z1 = b1*x - a1*y + z2`` and ``z2 = b2*x - a2*y``.
    """

    x = np.asarray(block, dtype=np.float64)
    out = x.copy()
    next_zi = zi
    for section_idx, (b0, b1, b2, _a0, a1, a2) in enumerate(np.asarray(sos, dtype=np.float64)):
        section_out = np.empty_like(out)
        for frame_idx in range(out.shape[0]):
            for ch in range(out.shape[1]):
                sample = out[frame_idx, ch]
                z1, z2 = next_zi[section_idx, :, ch]
                y = b0 * sample + z1
                next_zi[section_idx, 0, ch] = b1 * sample - a1 * y + z2
                next_zi[section_idx, 1, ch] = b2 * sample - a2 * y
                section_out[frame_idx, ch] = y
        out = section_out
    return out, next_zi


@dataclass
class _OnePole:
    value: float
    target: float
    sample_rate: int
    tau_s: float

    def set_target(self, value: float) -> None:
        self.target = float(value)

    def snap(self, value: float) -> None:
        self.value = float(value)
        self.target = float(value)

    def advance(self, frames: int) -> float:
        if frames <= 0:
            return self.value
        tau = max(1e-6, float(self.tau_s))
        decay = math.exp(-float(frames) / (tau * float(self.sample_rate)))
        self.value = self.target + (self.value - self.target) * decay
        return self.value

    @property
    def moving(self) -> bool:
        return abs(self.value - self.target) > 1e-5


class _SmoothedBiquad:
    """One SOS section whose raw parameter is smoothed before coefficient rebuild."""

    def __init__(
        self,
        *,
        sample_rate: int,
        channels: int,
        initial: float,
        smoothing_ms: float,
        design: Callable[[float], _Coeff],
        control_chunk: int = _DEFAULT_CONTROL_CHUNK,
    ) -> None:
        self._sample_rate = sample_rate
        self._channels = max(1, int(channels))
        self._design = design
        self._smoother = _OnePole(
            value=float(initial),
            target=float(initial),
            sample_rate=sample_rate,
            tau_s=max(0.001, float(smoothing_ms) / 1000.0),
        )
        self._sos = _coeff_to_sos(self._design(self._smoother.value))
        self._zi = np.repeat(initial_zi(1)[:, :, None], self._channels, axis=2)
        self._control_chunk = max(1, int(control_chunk))

    @property
    def value(self) -> float:
        return self._smoother.value

    @property
    def target(self) -> float:
        return self._smoother.target

    def set_target(self, value: float, *, snap: bool = False) -> None:
        if snap:
            self._smoother.snap(value)
            self._sos = _coeff_to_sos(self._design(self._smoother.value))
            self.reset()
        else:
            self._smoother.set_target(value)

    def reset(self) -> None:
        self._zi = np.repeat(initial_zi(1)[:, :, None], self._channels, axis=2)

    def process(self, block: np.ndarray) -> np.ndarray:
        x, was_mono = _sanitize_block(block)
        if x.shape[1] != self._channels:
            self._channels = x.shape[1]
            self.reset()
        if self._sos_is_identity() and not self._smoother.moving:
            return _restore_shape(x, was_mono)

        out = np.empty_like(x, dtype=np.float32)
        start = 0
        while start < x.shape[0]:
            stop = min(x.shape[0], start + self._control_chunk)
            frames = stop - start
            value = self._smoother.advance(frames)
            self._sos = _coeff_to_sos(self._design(value))
            segment, self._zi = _sosfilt_df2t(
                self._sos,
                x[start:stop],
                self._zi,
            )
            out[start:stop] = segment.astype(np.float32, copy=False)
            start = stop
        return _restore_shape(out, was_mono)

    def _sos_is_identity(self) -> bool:
        return bool(np.allclose(self._sos, _coeff_to_sos(_IDENTITY), atol=1e-12, rtol=0.0))


class ThreeBandEQ:
    """Three RBJ sections: low shelf, mid peaking bell, high shelf."""

    smoothing_ms = 70.0

    def __init__(
        self,
        *,
        sample_rate: int = 44_100,
        channels: int = 2,
        low_hz: float = 246.0,
        high_hz: float = 2_500.0,
        mid_q: float = 0.9,
        shelf_slope: float = 1.0,
        smoothing_ms: float = 70.0,
    ) -> None:
        self._sample_rate = _sanitize_sample_rate(sample_rate)
        self._low_hz = float(low_hz)
        self._high_hz = float(high_hz)
        self._mid_hz = math.sqrt(max(10.0, self._low_hz) * max(self._low_hz, self._high_hz))
        self._mid_q = float(mid_q)
        self._shelf_slope = float(shelf_slope)
        self.smoothing_ms = float(smoothing_ms)
        self._low = _SmoothedBiquad(
            sample_rate=self._sample_rate,
            channels=channels,
            initial=0.0,
            smoothing_ms=self.smoothing_ms,
            design=lambda gain: _rbj_low_shelf(
                self._low_hz,
                self._shelf_slope,
                gain,
                self._sample_rate,
            ),
        )
        self._mid = _SmoothedBiquad(
            sample_rate=self._sample_rate,
            channels=channels,
            initial=0.0,
            smoothing_ms=self.smoothing_ms,
            design=lambda gain: _rbj_peaking(
                self._mid_hz,
                self._mid_q,
                gain,
                self._sample_rate,
            ),
        )
        self._high = _SmoothedBiquad(
            sample_rate=self._sample_rate,
            channels=channels,
            initial=0.0,
            smoothing_ms=self.smoothing_ms,
            design=lambda gain: _rbj_high_shelf(
                self._high_hz,
                self._shelf_slope,
                gain,
                self._sample_rate,
            ),
        )

    @property
    def gains_db(self) -> dict[str, float]:
        return {
            "low": self._low.target,
            "mid": self._mid.target,
            "high": self._high.target,
        }

    def set_gain_db(
        self,
        *,
        low: float | None = None,
        mid: float | None = None,
        high: float | None = None,
        snap: bool = False,
    ) -> None:
        if low is not None:
            self._low.set_target(float(low), snap=snap)
        if mid is not None:
            self._mid.set_target(float(mid), snap=snap)
        if high is not None:
            self._high.set_target(float(high), snap=snap)

    def set_cc(
        self,
        *,
        low: float | int | None = None,
        mid: float | int | None = None,
        high: float | int | None = None,
        snap: bool = False,
    ) -> None:
        self.set_gain_db(
            low=cc_to_gain_db(low) if low is not None else None,
            mid=cc_to_gain_db(mid) if mid is not None else None,
            high=cc_to_gain_db(high) if high is not None else None,
            snap=snap,
        )

    def set_knobs(
        self,
        *,
        low: float | int | None = None,
        mid: float | int | None = None,
        high: float | int | None = None,
        snap: bool = False,
    ) -> None:
        self.set_gain_db(
            low=knob_to_gain_db(low) if low is not None else None,
            mid=knob_to_gain_db(mid) if mid is not None else None,
            high=knob_to_gain_db(high) if high is not None else None,
            snap=snap,
        )

    def process(self, block: np.ndarray) -> np.ndarray:
        out = np.asarray(block, dtype=np.float32)
        out = self._low.process(out)
        out = self._mid.process(out)
        out = self._high.process(out)
        return np.asarray(out, dtype=np.float32)

    def reset(self) -> None:
        self._low.reset()
        self._mid.reset()
        self._high.reset()


class ResonantFilter:
    """RBJ low-pass/high-pass sweep filter with faster raw-cutoff smoothing."""

    smoothing_ms = 15.0

    def __init__(
        self,
        *,
        sample_rate: int = 44_100,
        channels: int = 2,
        mode: FilterMode = "lowpass",
        cutoff_hz: float = 18_000.0,
        q: float = 0.7071,
        smoothing_ms: float = 15.0,
    ) -> None:
        self._sample_rate = _sanitize_sample_rate(sample_rate)
        self._mode: FilterMode = "highpass" if mode == "highpass" else "lowpass"
        self._q = max(0.05, float(q))
        self.smoothing_ms = float(smoothing_ms)
        initial = self._clamp_cutoff(cutoff_hz)
        self._filter = _SmoothedBiquad(
            sample_rate=self._sample_rate,
            channels=channels,
            initial=initial,
            smoothing_ms=self.smoothing_ms,
            design=self._design,
        )

    @property
    def mode(self) -> FilterMode:
        return self._mode

    @property
    def cutoff_hz(self) -> float:
        return self._filter.target

    def set_mode(self, mode: FilterMode) -> None:
        self._mode = "highpass" if mode == "highpass" else "lowpass"

    def set_cutoff_hz(self, cutoff_hz: float, *, snap: bool = False) -> None:
        self._filter.set_target(self._clamp_cutoff(cutoff_hz), snap=snap)

    def process(self, block: np.ndarray) -> np.ndarray:
        return self._filter.process(block)

    def reset(self) -> None:
        self._filter.reset()

    def _design(self, cutoff_hz: float) -> _Coeff:
        if self._mode == "highpass":
            return _rbj_highpass(cutoff_hz, self._q, self._sample_rate)
        return _rbj_lowpass(cutoff_hz, self._q, self._sample_rate)

    def _clamp_cutoff(self, cutoff_hz: float) -> float:
        nyquist = float(self._sample_rate) / 2.0
        try:
            cutoff = float(cutoff_hz)
        except (TypeError, ValueError):
            cutoff = 1_000.0
        return min(nyquist * 0.96, max(20.0, cutoff))


class ConstantPowerFader:
    """Sin/cos constant-power fader, 0.0 full A → 1.0 full B."""

    @staticmethod
    def gains(position: float) -> tuple[float, float]:
        try:
            pos = float(position)
        except (TypeError, ValueError):
            pos = 0.5
        pos = min(1.0, max(0.0, pos))
        theta = pos * (math.pi / 2.0)
        return math.cos(theta), math.sin(theta)

    @staticmethod
    def mix(deck_a: np.ndarray, deck_b: np.ndarray, *, position: float) -> np.ndarray:
        a, a_was_mono = _sanitize_block(deck_a)
        b, b_was_mono = _sanitize_block(deck_b)
        frames = min(a.shape[0], b.shape[0])
        channels = min(a.shape[1], b.shape[1])
        ga, gb = ConstantPowerFader.gains(position)
        out = ga * a[:frames, :channels] + gb * b[:frames, :channels]
        return _restore_shape(out.astype(np.float32, copy=False), a_was_mono and b_was_mono)


__all__ = [
    "ConstantPowerFader",
    "ResonantFilter",
    "ThreeBandEQ",
    "cc_to_gain_db",
    "initial_zi",
    "knob_to_gain_db",
]
