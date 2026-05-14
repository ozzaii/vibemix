# SPDX-License-Identifier: Apache-2.0
"""Phase 17 SENSE-14 — band-limited (40-120Hz) autocorrelation + downbeat
phase locking + phrase-length self-similarity primitives.

Pure, numpy-only helpers — zero I/O, no side effects, deterministic over the
input array. These are the load-bearing math behind ``PhraseBoundaryDetector``
(Plan 17-04 Task 2) AND the Plan 06 ``tune_detectors.py`` reference-WAV
harness (which calls them directly on a WAV without instantiating the
detector class — pure functions are the right shape for a CLI tuning tool).

Sibling to ``_dsp.py`` per the SENSE-15 ``_impl/`` shared-primitives
convention (kick-side primitives in ``_dsp.py``; phrase-side in this module).

Design rationale (per the plan's <interfaces> + threat register):
    - ``band_limited_autocorr`` applies an FFT-based 40-120Hz band-pass BEFORE
      autocorrelation so vocals / leads / hi-hats can NEVER influence the lock.
      The kick band is the only honest signal for phrase structure.
    - ``lock_downbeat_phase`` is a band-limited variant of
      ``vibemix.audio.features.compute_downbeat_phase`` — same anti-
      hallucination contract: invalid BPM → ``(0.0, 0.0)`` (T-13-05-02 +
      T-17-04-01 mitigation). Use this instead of the bare features.py
      function when you need PHRASE-grade lock honesty (vs Phase 13's
      mascot-grade lock that's content-agnostic).
    - ``estimate_phrase_length_bars`` defaults to 16 when the curve is too
      short or no peak dominates — 16 bars is the most common dance-music
      phrase, documented as the conservative-fallback contract (T-17-04-02
      accept disposition).

scipy is a project dep (CLAUDE.md tech stack — `scipy==1.17.1`); we use
``scipy.signal.fftconvolve`` for the autocorr step (faster than
``numpy.correlate`` for the windows we hand it).
"""

from __future__ import annotations

import math

import numpy as np
from scipy.signal import fftconvolve

# Match the Phase 13 BPM-validity ceiling (vibemix.audio.features._BPM_MAX_VALID).
# Anti-hallucination: anything outside (0, _BPM_MAX_VALID] yields (0.0, 0.0)
# from lock_downbeat_phase — never a fabricated lock.
_BPM_MAX_VALID: float = 220.0

# Default upper bound on autocorr lag — 4 seconds worth. At 16kHz that's
# 64000 samples; comfortably long enough to capture beat periods at 60 BPM
# (1.0s / beat) without paying for 100x lag values that no DJ BPM can hit.
_DEFAULT_MAX_LAG_SECONDS: float = 4.0


def _band_limit_fft(samples: np.ndarray, sample_rate: int, low_hz: float, high_hz: float) -> np.ndarray:
    """FFT band-pass: zero the spectrum outside [low_hz, high_hz] then IFFT.

    Returns float32 in the same shape as the input (irfft length-aligned).
    Pure numpy; no scipy filter design. Faster than IIR for our typical
    16k-64k-sample windows and avoids transient ringing of a short-order
    Butterworth at the band edges.
    """
    arr = samples.astype(np.float32) if samples.dtype != np.float32 else samples
    # Normalize int16-range inputs to ±1 for numerical stability.
    if np.max(np.abs(arr)) > 2.0:
        arr = arr / 32768.0

    n = arr.size
    if n == 0:
        return arr
    spec = np.fft.rfft(arr)
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)
    mask = (freqs >= low_hz) & (freqs <= high_hz)
    spec_masked = spec * mask
    return np.fft.irfft(spec_masked, n=n).astype(np.float32)


def band_limited_autocorr(
    samples: np.ndarray,
    sample_rate: int,
    *,
    low_hz: float = 40.0,
    high_hz: float = 120.0,
    max_lag_seconds: float = _DEFAULT_MAX_LAG_SECONDS,
) -> np.ndarray:
    """Autocorrelation of `samples` AFTER an FFT band-pass to [low_hz, high_hz].

    Used to find the dominant beat period in the kick band — vocals, leads,
    and hi-hats are zeroed before the autocorr so their periodicity can NEVER
    influence the lock.

    Args:
        samples: int16 PCM (the dtype ``AudioBuffer.snapshot()`` returns) or
            float32 in [-1, 1]. Single-channel.
        sample_rate: sample rate in Hz (typically 16000).
        low_hz / high_hz: band edges in Hz. Defaults match SENSE-14 +
            ``vibemix.audio.constants.PHRASE_AUTOCORR_LOW_HZ`` /
            ``PHRASE_AUTOCORR_HIGH_HZ``.
        max_lag_seconds: longest lag (in seconds) the returned correlation
            covers. 4.0s @ 16kHz = 64000 samples — comfortable for 60-220 BPM.

    Returns:
        1D float32 ndarray of normalized correlation values, indexed by lag
        in samples (lag-0 = 1.0 by definition; subsequent lags are normalized
        by the lag-0 amplitude). Length is ``min(samples.size,
        int(max_lag_seconds * sample_rate))``.

    Empty / silent input returns a zero-length array.
    """
    if samples is None or samples.size == 0:
        return np.zeros(0, dtype=np.float32)

    band = _band_limit_fft(samples, sample_rate, low_hz, high_hz)
    if band.size == 0 or float(np.max(np.abs(band))) == 0.0:
        # Silence after band-limit — no honest correlation to compute.
        return np.zeros(0, dtype=np.float32)

    # Out-of-band guard: if the band-limited signal carries < 1% of the
    # original RMS, the dominant input content is OUT of the kick band —
    # autocorrelating the residual would just normalize numerical noise to
    # 1.0 at lag-0 and produce spurious peaks at every other lag. Return
    # an empty array instead. Anti-hallucination per T-17-04-01.
    # The 1% floor mirrors `kick_band_centroid`'s in-band-leakage gate
    # in `_dsp.py`.
    arr_for_ratio = samples.astype(np.float32) if samples.dtype != np.float32 else samples
    if np.max(np.abs(arr_for_ratio)) > 2.0:
        arr_for_ratio = arr_for_ratio / 32768.0
    in_band_rms = float(np.sqrt(np.mean(band * band)))
    full_rms = float(np.sqrt(np.mean(arr_for_ratio * arr_for_ratio)))
    if full_rms > 0.0 and in_band_rms / full_rms < 0.01:
        return np.zeros(0, dtype=np.float32)

    # Full autocorr via FFT convolution (signal cross-correlated with reverse).
    full = fftconvolve(band, band[::-1], mode="full")
    # Take the second half (lag ≥ 0) — symmetrical autocorr.
    mid = full.size // 2
    half = full[mid:]
    # Normalize by lag-0 amplitude.
    lag0 = float(half[0]) if half.size > 0 else 0.0
    if lag0 == 0.0:
        return np.zeros(0, dtype=np.float32)
    norm = (half / lag0).astype(np.float32)
    # Clip to the requested max lag.
    max_lag_samples = int(max_lag_seconds * sample_rate)
    if max_lag_samples < norm.size:
        norm = norm[:max_lag_samples]
    return norm


def lock_downbeat_phase(
    samples: np.ndarray, bpm: float, sample_rate: int
) -> tuple[float, float]:
    """Band-limited variant of ``vibemix.audio.features.compute_downbeat_phase``.

    Same anti-hallucination contract: invalid BPM (≤0, NaN, >220) returns
    ``(0.0, 0.0)`` — never a fabricated lock. Algorithm:

        1. Validate BPM; reject invalid → (0.0, 0.0).
        2. Band-limit samples to [PHRASE_AUTOCORR_LOW_HZ, PHRASE_AUTOCORR_HIGH_HZ].
        3. Compute spectral-flux-style onset envelope on the band-limited
           signal (same idiom as `compute_downbeat_phase` step 2-3 but on the
           kick-only band).
        4. Cross-correlate the detected-peak times against a synthetic beat
           comb at `bpm`; lag-of-best-match modulo one bar → phase ∈ [0, 1).
        5. Confidence is the prominence (peak-vs-mean) of the comb-correlation,
           clamped to [0, 1] and capped by peak count.

    Returns:
        (phase, confidence): ``phase`` ∈ [0.0, 1.0); ``confidence`` ∈ [0.0, 1.0].

    Anti-hallucination contract:
        * bpm ≤ 0 / NaN / Inf / > 220 → (0.0, 0.0).
        * fewer than 4 detectable peaks in band-limited window → (0.0, 0.0).
          (Stricter than Phase 13's `compute_downbeat_phase` which preserves
          prior_phase — phrase locking has no prior_phase concept; we either
          have a fresh lock or we don't.)
        * sample_rate ≤ 0 / empty samples → (0.0, 0.0).
    """
    # --- Step 1: validate BPM ---
    if not isinstance(bpm, (int, float)):
        return (0.0, 0.0)
    if bpm <= 0 or math.isnan(bpm) or math.isinf(bpm) or bpm > _BPM_MAX_VALID:
        return (0.0, 0.0)
    if sample_rate <= 0 or samples is None or samples.size == 0:
        return (0.0, 0.0)

    # --- Step 2: band-limit ---
    band = _band_limit_fft(samples, sample_rate, 40.0, 120.0)
    if band.size == 0 or float(np.max(np.abs(band))) == 0.0:
        return (0.0, 0.0)

    samples_per_beat = (60.0 / bpm) * sample_rate
    samples_per_bar = samples_per_beat * 4.0
    if samples_per_bar <= 0:
        return (0.0, 0.0)

    # --- Step 3: onset envelope via short-window RMS deltas on band-limited ---
    win = max(1, sample_rate // 100)  # ~10ms windows
    if band.size < win * 8:
        return (0.0, 0.0)
    n_win = band.size // win
    trimmed = band[: n_win * win].reshape(n_win, win)
    energies = np.sqrt(np.mean(trimmed * trimmed, axis=1))
    deltas = np.diff(energies)
    deltas = np.clip(deltas, a_min=0.0, a_max=None)
    if deltas.size == 0 or float(np.max(deltas)) <= 0.0:
        return (0.0, 0.0)

    # Adaptive threshold (mean + 1σ — same idiom as compute_downbeat_phase).
    thr = max(0.005, float(deltas.mean() + deltas.std()))
    bar_in_windows = int(samples_per_bar / win)
    window_count = min(deltas.size, max(bar_in_windows * 4, 16))
    recent = deltas[-window_count:]
    peak_idx_local = np.flatnonzero(recent > thr)
    if peak_idx_local.size < 4:
        return (0.0, 0.0)

    peak_samples = peak_idx_local.astype(np.float32) * float(win)

    # --- Step 4: cross-correlate against synthetic beat comb @ bpm ---
    n_lags = 64
    lag_step = samples_per_bar / n_lags
    scores = np.zeros(n_lags, dtype=np.float32)
    for i in range(n_lags):
        lag = i * lag_step
        beats_under_peaks = np.round((peak_samples - lag) / samples_per_beat)
        expected = lag + beats_under_peaks * samples_per_beat
        d = np.abs(peak_samples - expected)
        tol = samples_per_beat * 0.1
        scores[i] = float(np.sum(np.exp(-d / max(tol, 1.0))))

    best_lag_idx = int(np.argmax(scores))
    best_score = float(scores[best_lag_idx])
    mean_score = float(scores.mean())
    std_score = float(scores.std()) or 1e-6

    phase_frac = (best_lag_idx * lag_step) / samples_per_bar
    phase = phase_frac - math.floor(phase_frac)

    # --- Step 5: confidence ---
    raw_conf = (best_score - mean_score) / std_score
    norm_conf = max(0.0, min(1.0, raw_conf / 3.0))
    peak_cap = min(1.0, float(peak_idx_local.size) / 8.0)
    confidence = min(norm_conf, peak_cap)

    return (float(phase), float(confidence))


def estimate_phrase_length_bars(
    energy_curve: list[float], bpm: float, *, hop_seconds: float = 1.0
) -> int:
    """Return the dominant phrase length in bars — one of {8, 16, 32}.

    Computes a self-similarity (autocorr) over the energy curve at
    ``hop_seconds`` resolution (typically 1Hz from
    ``vibemix.audio.features.energy_curve``). The autocorr peak whose lag
    best matches one of the three candidate bar counts wins.

    Returns 16 (the most common dance-music phrase length, documented as
    the conservative-fallback contract per T-17-04-02 accept disposition)
    when:
        - the curve is too short for an 8-bar evaluation (< 8 bars worth of
          hops), OR
        - no candidate self-similarity peak is meaningfully larger than the
          autocorr noise floor (no convincing dominant period).

    Bars-to-seconds conversion: ``bars * 4 * 60 / bpm``.
    """
    if not energy_curve or bpm <= 0 or hop_seconds <= 0:
        return 16

    # Convert each candidate bar count to lag-in-hops.
    candidates = (8, 16, 32)
    candidate_lags: dict[int, int] = {}
    for bars in candidates:
        seconds = bars * 4.0 * 60.0 / bpm
        lag_hops = int(round(seconds / hop_seconds))
        if lag_hops > 0:
            candidate_lags[bars] = lag_hops

    if not candidate_lags:
        return 16

    # Need at least the smallest candidate's worth of curve to evaluate at all.
    min_required = min(candidate_lags.values()) + 4  # a few extra hops for hop-aligned slack
    if len(energy_curve) < min_required:
        return 16

    arr = np.asarray(energy_curve, dtype=np.float32)
    arr = arr - float(arr.mean())
    if float(np.max(np.abs(arr))) == 0.0:
        return 16

    # Compute the autocorrelation of the energy curve (1D, fft-based).
    full = fftconvolve(arr, arr[::-1], mode="full")
    mid = full.size // 2
    ac = full[mid:]
    lag0 = float(ac[0]) if ac.size > 0 else 0.0
    if lag0 == 0.0:
        return 16
    ac = ac / lag0  # normalize peak-to-self at 1.0

    # Score each candidate by the local autocorr value at its lag — only
    # accept a candidate if its score clearly clears the autocorr noise floor.
    # Without this gate a random curve could silently latch onto whichever
    # lag has the largest noise hump. The mean + 2σ threshold (not 1σ) is
    # deliberately strict — random uniform curves occasionally produce
    # 1σ excursions at one of the candidate lags by chance, which would
    # silently mis-classify a non-periodic track as having an 8/32-bar
    # phrase. A 2σ floor pushes the false-positive rate well under 5%.
    pos_ac = ac[1:]  # exclude lag-0
    if pos_ac.size == 0:
        return 16
    noise_floor = float(np.mean(np.abs(pos_ac)))
    noise_std = float(np.std(np.abs(pos_ac))) or 1e-6
    convincing_thr = noise_floor + 2.0 * noise_std

    best_bars = 16  # default — overwrite only on a convincing winner
    best_score = -math.inf
    for bars, lag in candidate_lags.items():
        if lag >= ac.size:
            continue
        # Peak-pick a small window around the candidate lag (±2 hops slack).
        lo = max(1, lag - 2)
        hi = min(ac.size, lag + 3)
        local_peak = float(np.max(ac[lo:hi]))
        if local_peak > best_score and local_peak >= convincing_thr:
            best_score = local_peak
            best_bars = bars
    return best_bars
