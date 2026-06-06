# SPDX-License-Identifier: Apache-2.0
"""Compact three-band display peaks for Learn waveforms."""

from __future__ import annotations

import numpy as np


def _mono(audio: np.ndarray) -> np.ndarray:
    block = np.asarray(audio, dtype=np.float32)
    if block.ndim == 1:
        return block
    if block.ndim == 2 and block.shape[1] > 0:
        return np.mean(block, axis=1, dtype=np.float32)
    return np.zeros(0, dtype=np.float32)


def compute_three_band_peaks(
    audio: np.ndarray,
    *,
    sample_rate: int,
    buckets: int = 512,
) -> list[list[int]]:
    """Return ``[[low, mid, high], ...]`` display peaks scaled to ``0..255``."""

    mono = _mono(audio)
    if mono.size == 0:
        return [[0, 0, 0] for _ in range(max(1, int(buckets)))]
    bucket_count = max(1, int(buckets))
    samples_per_bucket = max(64, int(np.ceil(mono.size / bucket_count)))
    window = np.hanning(samples_per_bucket).astype(np.float32)
    freqs = np.fft.rfftfreq(samples_per_bucket, d=1.0 / float(sample_rate))
    bands = (
        (freqs < 250.0),
        (freqs >= 250.0) & (freqs < 2_500.0),
        (freqs >= 2_500.0),
    )
    matrix = np.zeros((bucket_count, 3), dtype=np.float32)
    for bucket_idx in range(bucket_count):
        start = bucket_idx * samples_per_bucket
        end = start + samples_per_bucket
        frame = mono[start:end]
        if frame.size < samples_per_bucket:
            frame = np.pad(frame, (0, samples_per_bucket - frame.size), mode="constant")
        spectrum = np.abs(np.fft.rfft(frame * window))
        for band_idx, band in enumerate(bands):
            if not np.any(band):
                continue
            matrix[bucket_idx, band_idx] = np.sqrt(
                np.mean(np.square(spectrum[band]), dtype=np.float64)
            )
    peak = float(np.max(matrix))
    if peak <= 1e-9 or not np.isfinite(peak):
        return [[0, 0, 0] for _ in range(bucket_count)]
    scaled = np.clip(np.sqrt(matrix / peak) * 255.0, 0.0, 255.0).astype(np.uint8)
    return scaled.astype(int).tolist()


__all__ = ["compute_three_band_peaks"]
