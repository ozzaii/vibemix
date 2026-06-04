# SPDX-License-Identifier: Apache-2.0
"""Learn DJ EQ / filter DSP regressions."""

from __future__ import annotations

import math

import numpy as np
import pytest

from vibemix.learn.dj_eq import (
    ConstantPowerFader,
    ResonantFilter,
    ThreeBandEQ,
    cc_to_gain_db,
    initial_zi,
)

_SR = 44_100


def _tone(freq_hz: float, n: int = 4096) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / float(_SR)
    mono = np.sin(2.0 * np.pi * freq_hz * t).astype(np.float32)
    return np.column_stack([mono, mono])


def _rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(block[:, 0]))))


def _settle(processor, block: np.ndarray, rounds: int = 24) -> np.ndarray:
    out = block
    for _ in range(rounds):
        out = processor.process(block)
    return out


def test_cc_to_gain_db_is_exactly_centered() -> None:
    assert cc_to_gain_db(0) == pytest.approx(-26.0)
    assert cc_to_gain_db(64) == pytest.approx(0.0)
    assert cc_to_gain_db(127) == pytest.approx(12.0)


def test_sos_state_starts_as_verified_zero_shape() -> None:
    zi = initial_zi(3)

    assert zi.shape == (3, 2)
    assert zi.dtype == np.float64
    assert np.all(zi == 0.0)


def test_neutral_three_band_eq_is_dry_passthrough() -> None:
    block = _tone(440.0)
    eq = ThreeBandEQ(sample_rate=_SR)

    out = eq.process(block)

    np.testing.assert_array_equal(out, block)


def test_low_eq_cut_reduces_bass_after_parameter_smoothing() -> None:
    block = _tone(80.0)
    eq = ThreeBandEQ(sample_rate=_SR)
    eq.set_cc(low=0)

    first = eq.process(block)
    settled = _settle(eq, block)

    assert np.isfinite(settled).all()
    assert _rms(first) > _rms(settled) * 1.2
    assert _rms(settled) < _rms(block) * 0.45


def test_high_eq_boost_raises_air_band_after_parameter_smoothing() -> None:
    block = _tone(8_000.0)
    eq = ThreeBandEQ(sample_rate=_SR)
    eq.set_cc(high=127)

    boosted = _settle(eq, block)

    assert np.isfinite(boosted).all()
    assert _rms(boosted) > _rms(block) * 1.35


def test_resonant_filter_uses_faster_sweep_smoothing_than_eq() -> None:
    eq = ThreeBandEQ(sample_rate=_SR)
    filt = ResonantFilter(sample_rate=_SR, mode="lowpass", cutoff_hz=18_000.0)

    assert eq.smoothing_ms == pytest.approx(70.0)
    assert filt.smoothing_ms == pytest.approx(15.0)


def test_resonant_lowpass_sweep_reduces_high_frequency_energy() -> None:
    high = _tone(8_000.0)
    filt = ResonantFilter(sample_rate=_SR, mode="lowpass", cutoff_hz=18_000.0, q=0.7071)
    filt.set_cutoff_hz(900.0)

    first = filt.process(high)
    settled = _settle(filt, high, rounds=12)

    assert np.isfinite(settled).all()
    assert _rms(first) > _rms(settled) * 1.15
    assert _rms(settled) < _rms(high) * 0.18


def test_resonant_highpass_sweep_reduces_bass_energy() -> None:
    bass = _tone(90.0)
    filt = ResonantFilter(sample_rate=_SR, mode="highpass", cutoff_hz=40.0, q=0.7071)
    filt.set_cutoff_hz(600.0)

    settled = _settle(filt, bass, rounds=12)

    assert np.isfinite(settled).all()
    assert _rms(settled) < _rms(bass) * 0.25


def test_constant_power_fader_invariant_across_sweep() -> None:
    fader = ConstantPowerFader()

    for position in np.linspace(0.0, 1.0, 21):
        ga, gb = fader.gains(float(position))
        assert 0.0 <= ga <= 1.0
        assert 0.0 <= gb <= 1.0
        assert ga * ga + gb * gb == pytest.approx(1.0, abs=1e-12)

    ga, gb = fader.gains(0.5)
    assert ga == pytest.approx(math.sqrt(0.5), abs=1e-12)
    assert gb == pytest.approx(math.sqrt(0.5), abs=1e-12)


def test_constant_power_fader_mixes_stereo_blocks() -> None:
    a = np.ones((128, 2), dtype=np.float32)
    b = np.zeros((128, 2), dtype=np.float32)

    out = ConstantPowerFader.mix(a, b, position=0.5)

    assert out.dtype == np.float32
    np.testing.assert_allclose(out, math.sqrt(0.5), atol=1e-6)
