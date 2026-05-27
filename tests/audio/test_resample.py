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
