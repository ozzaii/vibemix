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
    padded = np.pad(
        mono,
        (0, max(0, samples_per_bucket * bucket_count - mono.size)),
        mode="constant",
    )
    frames = padded.reshape(bucket_count, samples_per_bucket)
    window = np.hanning(samples_per_bucket).astype(np.float32)
    freqs = np.fft.rfftfreq(samples_per_bucket, d=1.0 / float(sample_rate))
    spectrum = np.abs(np.fft.rfft(frames * window[None, :], axis=1))

    bands = (
        (freqs < 250.0),
        (freqs >= 250.0) & (freqs < 2_500.0),
        (freqs >= 2_500.0),
    )
    values: list[np.ndarray] = []
    for band in bands:
        if not np.any(band):
            values.append(np.zeros(bucket_count, dtype=np.float32))
            continue
        values.append(np.sqrt(np.mean(np.square(spectrum[:, band]), axis=1)).astype(np.float32))
    matrix = np.stack(values, axis=1)
    peak = float(np.max(matrix))
    if peak <= 1e-9 or not np.isfinite(peak):
        return [[0, 0, 0] for _ in range(bucket_count)]
    scaled = np.clip(np.sqrt(matrix / peak) * 255.0, 0.0, 255.0).astype(np.uint8)
    return scaled.astype(int).tolist()


__all__ = ["compute_three_band_peaks"]
