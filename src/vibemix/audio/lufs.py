# SPDX-License-Identifier: Apache-2.0
"""Short-term BS.1770 loudness receipts for live grounding.

This module is intentionally tiny and dependency-free. It applies the
ITU-R BS.1770-4 K-weighting coefficients specified for 48 kHz, after resampling
non-48 kHz inputs through the local live-runtime resampler. The live master
buffer is mono, so the exported helper returns a mono LKFS/LUFS value or
``None`` when the window is too short or effectively silent.
"""

from __future__ import annotations

import math

import numpy as np

from vibemix.audio.resample import resample_audio

BS1770_SAMPLE_RATE = 48_000
SHORT_TERM_WINDOW_S = 3.0
_ABSOLUTE_GATE_LKFS = -70.0
_LKFS_OFFSET = -0.691

# ITU-R BS.1770-4 Annex 1 Tables 1-2, 48 kHz coefficients.
_STAGE1 = (
    1.53512485958697,
    -2.69169618940638,
    1.19839281085285,
    -1.69065929318241,
    0.73248077421585,
)
_STAGE2 = (
    1.0,
    -2.0,
    1.0,
    -1.99004745483398,
    0.99007225036621,
)

__all__ = ["BS1770_SAMPLE_RATE", "SHORT_TERM_WINDOW_S", "short_term_lufs"]


def short_term_lufs(
    samples: np.ndarray,
    sample_rate: int,
    *,
    window_s: float = SHORT_TERM_WINDOW_S,
) -> float | None:
    """Return short-term mono LKFS/LUFS over the last ``window_s`` seconds.

    ``None`` is the honest-null path: not enough samples, invalid sample rate,
    silence below the BS.1770 absolute gate, or non-finite input.
    """
    if sample_rate <= 0 or window_s <= 0:
        return None
    arr = _as_mono_float(samples)
    window_samples = round(sample_rate * window_s)
    if arr.size < window_samples:
        return None
    arr = arr[-window_samples:]
    if sample_rate != BS1770_SAMPLE_RATE:
        arr = resample_audio(arr, source_sr=sample_rate, target_sr=BS1770_SAMPLE_RATE)
    if arr.size == 0 or not np.isfinite(arr).all():
        return None
    weighted = _biquad(_biquad(arr.astype(np.float64, copy=False), _STAGE1), _STAGE2)
    mean_square = float(np.mean(weighted * weighted)) if weighted.size else 0.0
    if mean_square <= 0.0:
        return None
    loudness = _LKFS_OFFSET + 10.0 * math.log10(mean_square)
    if not math.isfinite(loudness) or loudness <= _ABSOLUTE_GATE_LKFS:
        return None
    return round(loudness, 2)


def _as_mono_float(samples: np.ndarray) -> np.ndarray:
    arr = np.asarray(samples)
    if arr.size == 0:
        return np.zeros(0, dtype=np.float32)
    if arr.ndim > 1:
        # Accept common audio layouts: (frames, channels) or (channels, frames).
        if arr.shape[0] <= 8 and arr.shape[1] > arr.shape[0]:
            arr = arr.mean(axis=0)
        else:
            arr = arr.mean(axis=1)
    if np.issubdtype(arr.dtype, np.integer):
        info = np.iinfo(arr.dtype)
        scale = float(max(abs(info.min), abs(info.max)))
        return (arr.astype(np.float32) / scale).astype(np.float32, copy=False)
    return arr.astype(np.float32, copy=False)


def _biquad(samples: np.ndarray, coeffs: tuple[float, float, float, float, float]) -> np.ndarray:
    b0, b1, b2, a1, a2 = coeffs
    out = np.empty_like(samples, dtype=np.float64)
    x1 = x2 = y1 = y2 = 0.0
    for idx, value in enumerate(samples):
        y0 = b0 * value + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        out[idx] = y0
        x2 = x1
        x1 = float(value)
        y2 = y1
        y1 = float(y0)
    return out
