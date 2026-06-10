# SPDX-License-Identifier: Apache-2.0
"""Tests for the dependency-light audio resampler."""

from __future__ import annotations

import numpy as np

from vibemix.audio.resample import resample_audio


def test_resample_48k_to_16k_preserves_one_second_length() -> None:
    sr = 48_000
    t = np.arange(sr, dtype=np.float32) / sr
    tone = 0.5 * np.sin(2.0 * np.pi * 440.0 * t)

    out = resample_audio(tone, source_sr=48_000, target_sr=16_000)

    assert out.dtype == np.float32
    assert out.shape == (16_000,)
    assert 0.1 < float(np.sqrt(np.mean(out * out))) < 0.5


def test_resample_arbitrary_ratio_returns_expected_length() -> None:
    src = np.linspace(-1.0, 1.0, 24_000, dtype=np.float32)

    out = resample_audio(src, source_sr=24_000, target_sr=44_100)

    assert out.dtype == np.float32
    assert out.shape == (44_100,)
    assert np.isfinite(out).all()


def _tone(sr: int, freq: float, seconds: float = 0.5) -> np.ndarray:
    t = np.arange(int(sr * seconds), dtype=np.float32) / sr
    return (0.5 * np.sin(2.0 * np.pi * freq * t)).astype(np.float32)


def _band_rms(x: np.ndarray, sr: int, freq: float, width_hz: float = 150.0) -> float:
    spec = np.abs(np.fft.rfft(x * np.hanning(x.size)))
    freqs = np.fft.rfftfreq(x.size, d=1.0 / sr)
    band = (freqs >= freq - width_hz) & (freqs <= freq + width_hz)
    return float(np.sqrt(np.mean(spec[band] ** 2)))


def test_resample_44k1_to_16k_rejects_aliasing() -> None:
    # 12 kHz at 44.1k sits ABOVE the 8 kHz output Nyquist; the un-anti-aliased
    # np.interp path folds it to 16k - 12k = 4 kHz inside the analysis band at
    # near-full amplitude. The FIR bridge must suppress that alias.
    out = resample_audio(_tone(44_100, 12_000.0), source_sr=44_100, target_sr=16_000)
    alias = _band_rms(out, 16_000, 4_000.0)
    ref = resample_audio(_tone(44_100, 1_000.0), source_sr=44_100, target_sr=16_000)
    passband = _band_rms(ref, 16_000, 1_000.0)
    assert alias < passband * 0.05  # > 26 dB rejection; old path leaves ~0.78x


def test_resample_44k1_to_16k_preserves_passband_and_length() -> None:
    out = resample_audio(_tone(44_100, 1_000.0, seconds=1.0), source_sr=44_100, target_sr=16_000)
    assert out.dtype == np.float32
    assert out.shape == (16_000,)
    rms = float(np.sqrt(np.mean(out * out)))
    assert abs(rms - 0.5 / np.sqrt(2.0)) < 0.05


def test_resample_96k_to_16k_pre_decimates_without_alias() -> None:
    # Above 3x target the linear bridge would downsample; the FIR pre-pass
    # must keep a 12 kHz tone out of the 4 kHz alias bin too.
    out = resample_audio(_tone(96_000, 12_000.0), source_sr=96_000, target_sr=16_000)
    ref = resample_audio(_tone(96_000, 1_000.0), source_sr=96_000, target_sr=16_000)
    assert out.shape[0] == 8_000
    assert _band_rms(out, 16_000, 4_000.0) < _band_rms(ref, 16_000, 1_000.0) * 0.05
