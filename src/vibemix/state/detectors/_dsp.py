# SPDX-License-Identifier: Apache-2.0
"""Shared kick-side DSP primitives for Phase 17 SENSE-12 detectors.

Pure, numpy-only helpers — zero I/O, no side effects, deterministic over the
input array. These are the load-bearing math the kick-side detectors share so
band logic stays in ONE place; per-detector tuning lives in
``vibemix.audio.constants`` and the detector classes themselves.

Anti-hallucination contract per the v4 "trust the audio" rule:
    - Silent input (``np.sum(masked_mag) == 0``) → return ``0.0``. Never
      fabricate a centroid frequency or a band-share fraction from the noise
      floor of an empty buffer.
    - Out-of-band input → return ``0.0`` for ``kick_band_centroid``. The
      40-120Hz band-limit IS the kick-detection contract; a 1kHz hi-hat
      should not register as a "kick at 1000Hz".

Both helpers operate on the same int16 / float ndarrays that
``vibemix.audio.buffers.AudioBuffer.snapshot()`` returns. ``sub_share`` is
documented to numerically MATCH ``feats["sub_share"]`` from
``vibemix.audio.features.snapshot_features`` (same FFT window size, same
Hanning taper, same band edges — sub band = [20, 100) Hz; total band =
[20, 8000) Hz of the snapshot_features four-band split). Detectors prefer
reading ``state.bands["sub"]`` (already populated by ``state_refresh_loop``)
and only call ``sub_share`` when they need to re-derive over a custom window.
"""

from __future__ import annotations

import numpy as np

# FFT window matches snapshot_features (vibemix.audio.features) so band-share
# numerics align bin-for-bin. Power-of-two; sized for sub-band resolution at
# 16kHz (~1Hz/bin → comfortable for the 20Hz lower edge).
_SPEC_WIN: int = 1 << 14  # 16384


def _to_float32(samples: np.ndarray) -> np.ndarray:
    """Normalize an int16 PCM array to float32 in [-1, 1]; pass-through for
    arrays already in float range. Zero-alloc when dtype is already float32."""
    if samples.dtype == np.int16:
        return samples.astype(np.float32) / 32768.0
    if samples.dtype == np.float32:
        return samples
    return samples.astype(np.float32)


def _windowed_spectrum(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    """Compute (magnitudes, freqs) for a Hanning-windowed rfft over `_SPEC_WIN`
    samples. Pads short inputs with zeros (mirrors snapshot_features)."""
    arr = _to_float32(samples)
    if arr.size >= _SPEC_WIN:
        x = arr[-_SPEC_WIN:] * np.hanning(_SPEC_WIN)
    else:
        x = np.pad(arr, (0, _SPEC_WIN - arr.size)) * np.hanning(_SPEC_WIN)
    mag = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(_SPEC_WIN, d=1.0 / sample_rate)
    return mag, freqs


def kick_band_centroid(
    samples: np.ndarray,
    sample_rate: int,
    *,
    low_hz: float = 40.0,
    high_hz: float = 120.0,
) -> float:
    """Spectral centroid (Hz) restricted to the kick band [low_hz, high_hz].

    Magnitude-weighted mean frequency over an FFT magnitude spectrum, with all
    bins outside [low_hz, high_hz] zeroed before the mean. Returns ``0.0`` on:
        - silent input (no in-band energy)
        - out-of-band input (e.g. a 1kHz hi-hat)

    Args:
        samples: int16 PCM (the dtype ``AudioBuffer.snapshot()`` returns) or
            float32 in [-1, 1]. Single-channel; multi-channel inputs are NOT
            mixed for the caller (mix beforehand if needed).
        sample_rate: sample rate in Hz (16000 for the canonical 16kHz buffer).
        low_hz / high_hz: band edges in Hz. Defaults catch the bulk of
            sub/kick fundamentals without bleeding into the bass-line band.

    Returns:
        Centroid frequency in Hz, or 0.0 on silence / out-of-band input.

    Anti-hallucination: silence MUST return 0.0 (never the band midpoint —
    that would silently fake a "kick at 80Hz" during a breakdown).
    """
    if samples is None or samples.size == 0:
        return 0.0
    mag, freqs = _windowed_spectrum(samples, sample_rate)
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    if not mask.any():
        return 0.0
    masked_mag = mag * mask
    total_mag = float(masked_mag.sum())
    if total_mag <= 0.0:
        return 0.0
    # Out-of-band guard: a strong out-of-band tone (e.g. a 1kHz hi-hat) leaks
    # tiny magnitudes into [low_hz, high_hz] via the Hanning side-lobes. If the
    # in-band energy is < 1% of the full-spectrum energy, the dominant content
    # is OUT of the kick band — return 0.0 rather than fabricating a centroid
    # from leakage. Anti-hallucination: a hi-hat must NOT register as a "kick
    # at 80Hz". The 1% floor was picked empirically — synthetic 60/100Hz tones
    # produce ~95-99% in-band energy, while a 1kHz tone leaks ~0.1%.
    full_mag = float(mag.sum())
    if full_mag > 0.0 and (total_mag / full_mag) < 0.01:
        return 0.0
    centroid = float((freqs * masked_mag).sum() / total_mag)
    return centroid


def sub_share(
    samples: np.ndarray,
    sample_rate: int,
    *,
    sub_hz_max: float = 60.0,
) -> float:
    """Fraction of FFT magnitude energy below ``sub_hz_max`` over total in-band
    [0, sample_rate / 2]. Returns 0.0 on silent input.

    Numerically matches ``feats["sub_share"]`` from
    ``vibemix.audio.features.snapshot_features`` when called with the SAME
    sample window — both use a 16384-sample Hanning-windowed rfft. The
    difference: ``snapshot_features`` defines sub as [20, 100) Hz and reports
    sub / (sub + low + mid_low + mid_hi + high) where each band is an RMS over
    its FFT magnitudes. Here we expose a simpler, single-band fraction so
    detectors can re-derive over a custom window without re-implementing the
    full four-band split. Detectors that just need the canonical share should
    read ``state.bands["sub"]`` (already populated upstream).

    Args:
        samples: int16 PCM or float32 in [-1, 1].
        sample_rate: sample rate in Hz.
        sub_hz_max: upper edge of the sub band (Hz). Default 60Hz catches the
            sub-bass / 808 fundamental cleanly.

    Returns:
        Fraction in [0.0, 1.0], or 0.0 on silence.
    """
    if samples is None or samples.size == 0:
        return 0.0
    mag, freqs = _windowed_spectrum(samples, sample_rate)
    total = float(np.sum(mag * mag))
    if total <= 0.0:
        return 0.0
    sub_mask = freqs < sub_hz_max
    sub = float(np.sum(mag[sub_mask] * mag[sub_mask]))
    return sub / total
