# SPDX-License-Identifier: Apache-2.0
"""Clean-room three-band DJ EQ for owned Learn decks.

The EQ is intentionally small and local: three RBJ-cookbook biquads in series
with a one-block old->new coefficient crossfade when a knob moves. It is used
by the Learn-owned mini deck, not by the live MusicState writer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

_Coeff = tuple[float, float, float, float, float]
_IDENTITY: _Coeff = (1.0, 0.0, 0.0, 0.0, 0.0)
_BOOST_DB = 12.0
_CUT_DB = 26.0
_Q_BOOST = 0.3
_Q_CUT = 0.9
_Q_SHELF = 0.4


def knob_to_gain_db(value: float | int | None) -> float:
    """Map a DJ EQ knob in 0..2 space to asymmetric boost/cut dB."""

    if value is None:
        value = 1.0
    try:
        knob = float(value)
    except (TypeError, ValueError):
        knob = 1.0
    knob = min(2.0, max(0.0, knob))
    delta = knob - 1.0
    if delta >= 0.0:
        return delta * _BOOST_DB
    return delta * _CUT_DB


def cc_to_knob(value: float | int | None) -> float:
    """Map 0..127 controller CC to DJ EQ knob space where 64 is near noon."""

    if value is None:
        return 1.0
    try:
        cc = float(value)
    except (TypeError, ValueError):
        return 1.0
    return min(127.0, max(0.0, cc)) / 63.5


def _normalize(b0: float, b1: float, b2: float, a0: float, a1: float, a2: float) -> _Coeff:
    if not math.isfinite(a0) or abs(a0) < 1e-12:
        return _IDENTITY
    return (b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)


def _frequency_terms(freq_hz: float, sample_rate: int, q: float) -> tuple[float, float, float]:
    nyquist = max(1.0, sample_rate / 2.0)
    freq = min(nyquist * 0.98, max(10.0, float(freq_hz)))
    w0 = 2.0 * math.pi * (freq / float(sample_rate))
    return math.cos(w0), math.sin(w0), math.sin(w0) / (2.0 * max(1e-6, q))


def design_peaking(freq_hz: float, q: float, gain_db: float, sample_rate: int) -> _Coeff:
    if abs(gain_db) < 1e-6:
        return _IDENTITY
    cosw0, _sinw0, alpha = _frequency_terms(freq_hz, sample_rate, q)
    amp = 10.0 ** (gain_db / 40.0)
    return _normalize(
        1.0 + alpha * amp,
        -2.0 * cosw0,
        1.0 - alpha * amp,
        1.0 + alpha / amp,
        -2.0 * cosw0,
        1.0 - alpha / amp,
    )


def design_high_shelf(freq_hz: float, q: float, gain_db: float, sample_rate: int) -> _Coeff:
    if abs(gain_db) < 1e-6:
        return _IDENTITY
    cosw0, sinw0, _alpha = _frequency_terms(freq_hz, sample_rate, q)
    amp = 10.0 ** (gain_db / 40.0)
    beta_sq = max(0.0, ((amp * amp + 1.0) / max(1e-6, q)) - ((amp - 1.0) ** 2))
    beta = math.sqrt(beta_sq)
    return _normalize(
        amp * ((amp + 1.0) + (amp - 1.0) * cosw0 + beta * sinw0),
        -2.0 * amp * ((amp - 1.0) + (amp + 1.0) * cosw0),
        amp * ((amp + 1.0) + (amp - 1.0) * cosw0 - beta * sinw0),
        (amp + 1.0) - (amp - 1.0) * cosw0 + beta * sinw0,
        2.0 * ((amp - 1.0) - (amp + 1.0) * cosw0),
        (amp + 1.0) - (amp - 1.0) * cosw0 - beta * sinw0,
    )


@dataclass
class _FilterSnapshot:
    coeffs: _Coeff
    state: np.ndarray


class Biquad:
    """Stereo transposed-direct-form-II biquad with one-block coefficient fade."""

    def __init__(self, *, channels: int = 2) -> None:
        self._channels = max(1, int(channels))
        self._coeffs: _Coeff = _IDENTITY
        self._state = np.zeros((self._channels, 2), dtype=np.float64)
        self._old: _FilterSnapshot | None = None

    @property
    def coeffs(self) -> _Coeff:
        return self._coeffs

    @property
    def fading(self) -> bool:
        return self._old is not None

    def set_coeffs(self, coeffs: _Coeff) -> None:
        if all(abs(a - b) < 1e-9 for a, b in zip(self._coeffs, coeffs, strict=True)):
            return
        self._old = _FilterSnapshot(self._coeffs, self._state.copy())
        self._coeffs = coeffs
        self._state.fill(0.0)

    def reset(self) -> None:
        self._state.fill(0.0)
        self._old = None

    def process(self, block: np.ndarray) -> np.ndarray:
        x = np.asarray(block, dtype=np.float32)
        if x.ndim != 2:
            return x
        if self._old is None:
            return self._process_with_state(x, self._coeffs, self._state)

        old = self._old
        old_out = self._process_with_state(x, old.coeffs, old.state.copy())
        new_out = self._process_with_state(x, self._coeffs, self._state)
        n = x.shape[0]
        out = old_out.copy()
        half = n // 2
        if n > half:
            mix = np.linspace(0.0, 1.0, n - half, dtype=np.float32)[:, None]
            out[half:] = new_out[half:] * mix + old_out[half:] * (1.0 - mix)
        self._old = None
        return out.astype(np.float32, copy=False)

    def _process_with_state(
        self,
        block: np.ndarray,
        coeffs: _Coeff,
        state: np.ndarray,
    ) -> np.ndarray:
        b0, b1, b2, a1, a2 = coeffs
        if coeffs == _IDENTITY:
            return block.astype(np.float32, copy=False)
        out = np.empty_like(block, dtype=np.float32)
        channels = min(block.shape[1], state.shape[0])
        for i in range(block.shape[0]):
            for ch in range(channels):
                x = float(block[i, ch])
                w0, w1 = state[ch]
                y = b0 * x + w0
                state[ch, 0] = b1 * x - a1 * y + w1
                state[ch, 1] = b2 * x - a2 * y
                out[i, ch] = y
            if block.shape[1] > channels:
                out[i, channels:] = block[i, channels:]
        return out


class ThreeBandEQ:
    """Three overlapping DJ EQ bands with neutral dry passthrough."""

    def __init__(
        self,
        *,
        sample_rate: int = 44_100,
        channels: int = 2,
        low_mid_hz: float = 250.0,
        mid_high_hz: float = 2_500.0,
    ) -> None:
        self._sample_rate = int(sample_rate)
        self._low_center = math.sqrt(20.0 * float(low_mid_hz))
        self._mid_center = math.sqrt(float(low_mid_hz) * float(mid_high_hz))
        self._high_center = math.sqrt(float(mid_high_hz) * (self._sample_rate / 2.0))
        self._low = Biquad(channels=channels)
        self._mid = Biquad(channels=channels)
        self._high = Biquad(channels=channels)
        self._gain_db: dict[str, float] = {"low": 0.0, "mid": 0.0, "high": 0.0}

    def set_knobs(
        self,
        *,
        low: float | int | None = None,
        mid: float | int | None = None,
        high: float | int | None = None,
    ) -> None:
        if low is not None:
            self._set_band("low", knob_to_gain_db(low))
        if mid is not None:
            self._set_band("mid", knob_to_gain_db(mid))
        if high is not None:
            self._set_band("high", knob_to_gain_db(high))

    def set_cc(
        self,
        *,
        low: float | int | None = None,
        mid: float | int | None = None,
        high: float | int | None = None,
    ) -> None:
        self.set_knobs(
            low=cc_to_knob(low) if low is not None else None,
            mid=cc_to_knob(mid) if mid is not None else None,
            high=cc_to_knob(high) if high is not None else None,
        )

    def process(self, block: np.ndarray) -> np.ndarray:
        out = np.asarray(block, dtype=np.float32)
        for name, band in (("low", self._low), ("mid", self._mid), ("high", self._high)):
            if abs(self._gain_db[name]) > 1e-6 or band.fading:
                out = band.process(out)
        return out.astype(np.float32, copy=False)

    def _set_band(self, name: Literal["low", "mid", "high"], gain_db: float) -> None:
        gain = 0.0 if abs(gain_db) < 1e-6 else float(gain_db)
        if abs(self._gain_db[name] - gain) < 1e-6:
            return
        self._gain_db[name] = gain
        q = _Q_BOOST if gain > 0.0 else _Q_CUT
        if name == "low":
            coeffs = design_peaking(self._low_center, q, gain, self._sample_rate)
            self._low.set_coeffs(coeffs)
        elif name == "mid":
            coeffs = design_peaking(self._mid_center, q, gain, self._sample_rate)
            self._mid.set_coeffs(coeffs)
        else:
            if gain < 0.0:
                coeffs = design_high_shelf(self._high_center, _Q_SHELF, gain, self._sample_rate)
            else:
                coeffs = design_peaking(self._high_center, q, gain, self._sample_rate)
            self._high.set_coeffs(coeffs)


__all__ = [
    "Biquad",
    "ThreeBandEQ",
    "cc_to_knob",
    "design_high_shelf",
    "design_peaking",
    "knob_to_gain_db",
]
