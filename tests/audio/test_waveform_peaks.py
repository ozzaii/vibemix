# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import numpy as np

from vibemix.audio.waveform_peaks import compute_three_band_peaks


def test_compute_three_band_peaks_returns_bounded_requested_buckets() -> None:
    sample_rate = 16_000
    t = np.arange(sample_rate, dtype=np.float32) / sample_rate
    audio = (
        0.42 * np.sin(2.0 * np.pi * 90.0 * t)
        + 0.22 * np.sin(2.0 * np.pi * 900.0 * t)
        + 0.08 * np.sin(2.0 * np.pi * 4_000.0 * t)
    ).astype(np.float32)

    peaks = compute_three_band_peaks(audio, sample_rate=sample_rate, buckets=24)

    assert len(peaks) == 24
    assert all(len(row) == 3 for row in peaks)
    assert all(0 <= value <= 255 for row in peaks for value in row)
    assert max(row[0] for row in peaks) > max(row[2] for row in peaks)


def test_compute_three_band_peaks_handles_empty_audio() -> None:
    peaks = compute_three_band_peaks(np.zeros(0, dtype=np.float32), sample_rate=16_000, buckets=5)

    assert peaks == [[0, 0, 0]] * 5


def test_compute_three_band_peaks_downmixes_stereo() -> None:
    sample_rate = 16_000
    t = np.arange(sample_rate // 2, dtype=np.float32) / sample_rate
    left = 0.35 * np.sin(2.0 * np.pi * 120.0 * t)
    right = 0.35 * np.sin(2.0 * np.pi * 1_200.0 * t)
    stereo = np.stack([left, right], axis=1).astype(np.float32)

    peaks = compute_three_band_peaks(stereo, sample_rate=sample_rate, buckets=12)

    assert len(peaks) == 12
    assert max(max(row) for row in peaks) > 0
