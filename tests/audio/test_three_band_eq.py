# SPDX-License-Identifier: Apache-2.0
"""Three-band EQ DSP regression tests."""

from __future__ import annotations

import numpy as np

from vibemix.audio.three_band_eq import ThreeBandEQ, cc_to_knob, knob_to_gain_db

_SR = 44_100


def _tone(freq_hz: float, n: int = 4096) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / float(_SR)
    mono = np.sin(2.0 * np.pi * freq_hz * t).astype(np.float32)
    return np.column_stack([mono, mono])


def _rms(block: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(block[:, 0]))))


def test_knob_mapping_is_asymmetric_dj_eq() -> None:
    assert cc_to_knob(0) == 0.0
    assert cc_to_knob(127) == 2.0
    assert knob_to_gain_db(1.0) == 0.0
    assert knob_to_gain_db(2.0) == 12.0
    assert knob_to_gain_db(0.0) == -26.0


def test_neutral_eq_is_dry_passthrough() -> None:
    block = _tone(440.0)
    eq = ThreeBandEQ(sample_rate=_SR)

    out = eq.process(block)

    np.testing.assert_array_equal(out, block)


def test_low_cut_reduces_bass_energy() -> None:
    block = _tone(80.0)
    eq = ThreeBandEQ(sample_rate=_SR)
    eq.set_cc(low=0)
    eq.process(block)  # coefficient-change crossfade block

    cut = eq.process(block)

    assert np.isfinite(cut).all()
    assert _rms(cut) < _rms(block) * 0.45


def test_high_boost_raises_air_band_energy() -> None:
    block = _tone(8_000.0)
    eq = ThreeBandEQ(sample_rate=_SR)
    eq.set_cc(high=127)
    eq.process(block)  # coefficient-change crossfade block

    boosted = eq.process(block)

    assert np.isfinite(boosted).all()
    assert _rms(boosted) > _rms(block) * 1.4


def test_knob_move_crossfade_stays_finite() -> None:
    block = _tone(120.0, n=512)
    eq = ThreeBandEQ(sample_rate=_SR)
    eq.process(block)

    eq.set_cc(low=0)
    moved = eq.process(block)

    assert moved.shape == block.shape
    assert moved.dtype == np.float32
    assert np.isfinite(moved).all()
    assert float(np.max(np.abs(moved))) < 2.0
