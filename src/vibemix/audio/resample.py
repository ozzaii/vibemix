# SPDX-License-Identifier: Apache-2.0
"""Tiny numpy resampling helpers for live/audio-buffer paths.

This replaces the previous ``scipy.signal.resample_poly`` dependency. The
common live path is 48 kHz -> 16 kHz, handled by a windowed-sinc low-pass
decimator. Every other DOWNSAMPLE (the 44.1 kHz factory-default BlackHole rig)
bridges to 3x the target rate with linear interpolation and reuses the same
windowed-sinc /3 decimator, so content above the output Nyquist is filtered
out BEFORE samples are discarded. Pure upsamples keep plain linear
interpolation (no aliasing on an upsample; those paths are voice monitoring /
test fixtures). File/model decode uses FFmpeg via PyAV instead.
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


_GENERIC_LP_KERNELS: dict[float, np.ndarray] = {}


def _lowpass_kernel(cutoff: float) -> np.ndarray:
    """63-tap Hamming windowed-sinc low-pass at ``cutoff`` cycles/sample.

    Same design as ``_decimate3_kernel`` with a parametric cutoff — used to
    band-limit the generic-downsample work signal to the output Nyquist
    BEFORE the linear bridge (see ``resample_audio``). Cached per cutoff;
    the generic path only ever sees a handful of rates.
    """
    kernel = _GENERIC_LP_KERNELS.get(cutoff)
    if kernel is None:
        taps = 63
        mid = (taps - 1) / 2.0
        n = np.arange(taps, dtype=np.float32) - mid
        k = 2.0 * cutoff * np.sinc(2.0 * cutoff * n)
        k *= np.hamming(taps).astype(np.float32)
        k /= np.sum(k)
        kernel = k.astype(np.float32)
        _GENERIC_LP_KERNELS[cutoff] = kernel
    return kernel


def _linear_resample(samples: np.ndarray, *, source_sr: int, target_sr: int) -> np.ndarray:
    if samples.size == 0:
        return samples.astype(np.float32, copy=False)
    out_len = max(1, round(samples.size * float(target_sr) / float(source_sr)))
    if out_len == samples.size:
        return samples.astype(np.float32, copy=False)
    src_x = np.arange(samples.size, dtype=np.float32)
    dst_x = np.arange(out_len, dtype=np.float32) * (float(source_sr) / float(target_sr))
    return np.interp(dst_x, src_x, samples.astype(np.float32, copy=False)).astype(np.float32)


def _linear_to_length(samples: np.ndarray, out_len: int) -> np.ndarray:
    """Map ``samples`` onto exactly ``out_len`` points via linear interpolation."""
    arr = samples.astype(np.float32, copy=False)
    if out_len == arr.size:
        return arr
    src_x = np.arange(arr.size, dtype=np.float64)
    dst_x = np.arange(out_len, dtype=np.float64) * (arr.size / float(out_len))
    return np.interp(dst_x, src_x, arr).astype(np.float32)


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

    if target_sr < source_sr:
        # Generic anti-aliased downsample (the 44.1k BlackHole rig): bridge to
        # 3x the target rate with linear interpolation, then reuse the
        # windowed-sinc /3 decimator. The kernel's 1/6-cycles-per-sample cutoff
        # at the 3x-target bridge rate IS the output Nyquist, so everything
        # above it is filtered out before samples are discarded. Plain
        # np.interp had no low-pass — on 44.1k captures, 8-22k content folded
        # straight into the analysis band and Gemini's clean buffer.
        out_len = max(1, round(arr.size * float(target_sr) / float(source_sr)))
        work = arr
        src = float(source_sr)
        # Above 3x target (96k/88.2k interfaces) the linear bridge would itself
        # downsample — its only aliasing direction. Pre-decimate with the same
        # FIR stage; each pass low-passes at in-rate/6, at or above the final
        # band edge, so the product band is untouched.
        while src > 3.0 * float(target_sr) and work.size >= 3:
            work = np.convolve(work, _decimate3_kernel(), mode="same")[::3]
            src /= 3.0
        # The linear bridge folds images of out-of-band content (f above
        # target/2 at the work rate) straight into the band — e.g. a 12 kHz
        # tone at a 32k work rate images to 44 kHz, which sampling at the 48k
        # bridge folds to 4 kHz, inside the final FIR's passband where nothing
        # can remove it. Band-limit the work signal to the output Nyquist
        # first; passband content's own bridge images land in the final FIR's
        # stopband (benign).
        work = np.convolve(
            work, _lowpass_kernel(float(target_sr) / (2.0 * src)), mode="same"
        )
        mid = _linear_to_length(work, out_len * 3)
        filtered = np.convolve(mid, _decimate3_kernel(), mode="same")
        return filtered[::3].astype(np.float32, copy=False)

    return _linear_resample(arr, source_sr=source_sr, target_sr=target_sr)
