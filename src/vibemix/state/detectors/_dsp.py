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


def band_spectral_flatness(
    samples: np.ndarray,
    sample_rate: int,
    *,
    low_hz: float = 200.0,
    high_hz: float = 2000.0,
) -> float:
    """Wiener entropy (spectral flatness) restricted to [low_hz, high_hz].

    Returns ``geometric_mean(mag) / arithmetic_mean(mag)`` over the in-band
    FFT magnitudes. Pure tones / harmonic signals → close to 0. White noise
    / heavily-distorted / saturated signals → close to 1. The 200–2000Hz
    band is the Hard Tek "distortion smear" region (sub band 40-120Hz isn't
    saturated by the same hardware-clipping signature; >2kHz is dominated by
    hi-hats which always sit high-flatness regardless of distortion).

    Numerical stability: uses log-sum trick (``exp(mean(log(mag + ε)))``)
    so a zero-magnitude bin doesn't collapse the geometric mean to 0.

    Anti-hallucination: silent input (no in-band energy) → 0.0. Never
    fabricate a flatness value from the noise floor of an empty buffer.

    Phase 30 SENSE-17 primitive. Used by DistortionClimbDetector.
    """
    if samples is None or samples.size == 0:
        return 0.0
    mag, freqs = _windowed_spectrum(samples, sample_rate)
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    if not mask.any():
        return 0.0
    band_mag = mag[mask]
    total = float(band_mag.sum())
    if total <= 0.0:
        return 0.0
    eps = 1e-12
    # Log-sum trick for geometric mean: GM = exp(mean(log(x))). Adding eps
    # before the log keeps zero-magnitude bins from collapsing the result.
    geo = float(np.exp(np.mean(np.log(band_mag + eps))))
    arith = float(np.mean(band_mag))
    if arith <= 0.0:
        return 0.0
    return geo / arith


def harmonic_distortion_proxy(
    samples: np.ndarray,
    sample_rate: int,
    *,
    fundamental_hz: float = 60.0,
    n_harmonics: int = 6,
    bin_window_hz: float = 5.0,
) -> float:
    """Ratio of odd-harmonic energy to even-harmonic energy of ``fundamental_hz``.

    Distortion — especially hard-clipping / saturation that Hard Tek kicks
    are run through — emphasises odd harmonics (3rd, 5th) over even
    (2nd, 4th, 6th). A clean sine has near-zero harmonic content; a
    saturated kick has odd-dominant content. Ratio in [0.0, ∞]; baseline
    pure-tone ≈ 0.0, mild distortion ≈ 0.5-1.5, hard saturation ≥ 1.5.

    ``bin_window_hz`` widens the per-harmonic energy integration so an FFT
    bin that doesn't exactly straddle the harmonic frequency still picks up
    its energy (Hanning side-lobes spread peaks across ~2-3 bins).

    Anti-hallucination: silent input → 0.0. No fabricated harmonic content.

    Phase 30 SENSE-17 primitive. Used by DistortionClimbDetector.
    """
    if samples is None or samples.size == 0:
        return 0.0
    mag, freqs = _windowed_spectrum(samples, sample_rate)
    total = float(mag.sum())
    if total <= 0.0:
        return 0.0
    odd_energy = 0.0
    even_energy = 0.0
    for h in range(2, n_harmonics + 1):  # start at 2 (skip fundamental)
        target = fundamental_hz * h
        if target >= sample_rate / 2.0:
            break
        mask = (freqs >= target - bin_window_hz) & (freqs <= target + bin_window_hz)
        if not mask.any():
            continue
        energy = float(np.sum(mag[mask] ** 2))
        if h % 2 == 1:
            odd_energy += energy
        else:
            even_energy += energy
    return odd_energy / (even_energy + 1e-12)


def dominant_freq_in_band(
    samples: np.ndarray,
    sample_rate: int,
    *,
    low_hz: float = 200.0,
    high_hz: float = 800.0,
) -> float:
    """Frequency (Hz) of the highest-magnitude FFT bin within [low_hz, high_hz].

    Used by AcidLineEntryDetector to track a TB-303 formant sweep. Returns
    0.0 on silence OR when the in-band energy is < 1% of the total spectrum
    (out-of-band guard mirrors ``kick_band_centroid`` — a hi-hat at 4kHz
    must NOT register as a "dominant in-band freq" via FFT leakage).

    Phase 30 SENSE-18 primitive.
    """
    if samples is None or samples.size == 0:
        return 0.0
    mag, freqs = _windowed_spectrum(samples, sample_rate)
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    if not mask.any():
        return 0.0
    full_total = float(mag.sum())
    if full_total <= 0.0:
        return 0.0
    band_mag = mag * mask
    band_total = float(band_mag.sum())
    if band_total <= 0.0:
        return 0.0
    # Out-of-band guard — same 1% floor as kick_band_centroid.
    if band_total / full_total < 0.01:
        return 0.0
    peak_idx = int(np.argmax(band_mag))
    return float(freqs[peak_idx])


def band_resonance_q(
    samples: np.ndarray,
    sample_rate: int,
    *,
    low_hz: float = 200.0,
    high_hz: float = 800.0,
) -> float:
    """Peak-to-mean magnitude ratio within [low_hz, high_hz] — proxy for Q.

    A high-Q resonant peak (TB-303 self-oscillation territory) → ratio > 8.
    Flat band noise → ratio ≈ 1. The proxy is monotonic in resonance Q
    without needing a full bandwidth measurement.

    Returns 0.0 on silence.

    Phase 30 SENSE-18 primitive. Used by AcidLineEntryDetector.
    """
    if samples is None or samples.size == 0:
        return 0.0
    mag, freqs = _windowed_spectrum(samples, sample_rate)
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    if not mask.any():
        return 0.0
    band_mag = mag[mask]
    mean_mag = float(np.mean(band_mag))
    if mean_mag <= 0.0:
        return 0.0
    peak_mag = float(np.max(band_mag))
    return peak_mag / (mean_mag + 1e-12)


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
