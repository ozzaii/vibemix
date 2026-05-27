# SPDX-License-Identifier: Apache-2.0
"""Tiny numpy resampling helpers for live/audio-buffer paths.

This replaces the previous ``scipy.signal.resample_poly`` dependency. The
common live path is 48 kHz -> 16 kHz, handled by a windowed-sinc low-pass
decimator. Less common arbitrary ratios use linear interpolation; those paths
trim/pad at the caller boundary and are for voice monitoring/test fixtures, not
library embeddings. File/model decode uses FFmpeg via PyAV instead.
"""

from __future__ import annotations

import math

import numpy as np

_DECIMATE3_KERNEL: np.ndarray | None = None


def _decimate3_kernel() -> np.ndarray:
    global _DECIMATE3_KERNEL
    if _DECIMATE3_KERNEL is not None:
        return _DECIMATE3_KERNEL

    taps = 63
    mid = (taps - 1) / 2.0
    n = np.arange(taps, dtype=np.float32) - mid
    cutoff = 1.0 / 6.0  # output Nyquist (16 kHz) in 48 kHz cycles/sample.
    kernel = 2.0 * cutoff * np.sinc(2.0 * cutoff * n)
    kernel *= np.hamming(taps).astype(np.float32)
    kernel /= np.sum(kernel)
    _DECIMATE3_KERNEL = kernel.astype(np.float32)
    return _DECIMATE3_KERNEL


def _linear_resample(samples: np.ndarray, *, source_sr: int, target_sr: int) -> np.ndarray:
    if samples.size == 0:
        return samples.astype(np.float32, copy=False)
    out_len = max(1, round(samples.size * float(target_sr) / float(source_sr)))
    if out_len == samples.size:
        return samples.astype(np.float32, copy=False)
    src_x = np.arange(samples.size, dtype=np.float32)
    dst_x = np.arange(out_len, dtype=np.float32) * (float(source_sr) / float(target_sr))
    return np.interp(dst_x, src_x, samples.astype(np.float32, copy=False)).astype(np.float32)


def resample_audio(
    samples: np.ndarray,
    *,
    source_sr: int,
    target_sr: int,
) -> np.ndarray:
    """Resample mono audio to ``target_sr`` as float32.

    The function is intentionally small and dependency-free. It preserves exact
    length for the product's 48 kHz -> 16 kHz live path when input block sizes
    are divisible by 3.
    """
    if source_sr <= 0 or target_sr <= 0:
        raise ValueError("source_sr and target_sr must be positive")

    arr = np.asarray(samples, dtype=np.float32)
    if source_sr == target_sr or arr.size == 0:
        return arr.astype(np.float32, copy=False)

    gcd = math.gcd(int(source_sr), int(target_sr))
    up = int(target_sr) // gcd
    down = int(source_sr) // gcd

    if up == 1 and down == 3:
        filtered = np.convolve(arr, _decimate3_kernel(), mode="same")
        return filtered[::3].astype(np.float32, copy=False)

    return _linear_resample(arr, source_sr=source_sr, target_sr=target_sr)
