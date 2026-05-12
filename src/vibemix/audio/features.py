# SPDX-License-Identifier: Apache-2.0
"""DSP free functions over AudioBuffer.

Verbatim math port of cohost_v4.py:304-436 — FFT pipeline, BPM autocorr,
peak-normalize, RMS, onset detection, band-share split. Refactored from v4's
``AudioBuffer`` methods into free functions so tests can build a tiny synthetic
buffer and pin the dict shape without standing up the whole audio package
(RESEARCH.md A1).

No algorithmic changes from v4. Only structural change: functions take
``(buf: AudioBuffer, ...)`` instead of being methods on AudioBuffer; the read
goes through ``buf.snapshot(n)`` instead of v4's direct ``_buf[-n:]`` access.
"""

from __future__ import annotations

import io
import math
import wave

import numpy as np

from vibemix.audio.buffers import AudioBuffer
from vibemix.audio.constants import SILENT_RMS


def snapshot_features(buf: AudioBuffer, seconds: float = 5.0) -> dict:
    """Compute RMS / onset rate / 4-band share for the most recent `seconds`.

    Returns the v4 dict shape:
        {"silent": bool, "rms": float, "onsets_per_sec": float,
         "sub_share": float, "low_share": float, "mid_share": float,
         "high_share": float}

    OR the early-out shape `{"silent": True, "rms": 0.0}` when fewer than
    `sr // 4` samples are available (v4:335-336).

    Verbatim math port of cohost_v4.py:333-381.
    """
    sr = buf._sr
    n = int(sr * seconds)
    arr_int16 = buf.snapshot(n)
    if arr_int16.size < sr // 4:
        return {"silent": True, "rms": 0.0}
    arr = arr_int16.astype(np.float32) / 32768.0

    rms = float(np.sqrt(np.mean(arr * arr)))

    win = sr // 50
    if arr.size > win * 4:
        energies = np.array(
            [
                float(np.sqrt(np.mean(arr[i : i + win] * arr[i : i + win])))
                for i in range(0, arr.size - win, win)
            ]
        )
        deltas = np.diff(energies).clip(min=0)
        thr = max(0.005, deltas.mean() + deltas.std())
        onsets_per_sec = float(np.sum(deltas > thr) / seconds)
    else:
        onsets_per_sec = 0.0

    spec_win = 1 << 14  # 16384 samples
    if arr.size >= spec_win:
        x = arr[-spec_win:] * np.hanning(spec_win)
    else:
        x = np.pad(arr, (0, spec_win - arr.size)) * np.hanning(spec_win)
    spec = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(spec_win, d=1.0 / sr)

    def band_energy(lo: float, hi: float) -> float:
        mask = (freqs >= lo) & (freqs < hi)
        return float(np.sqrt(np.mean(spec[mask] * spec[mask]))) if mask.any() else 0.0

    sub = band_energy(20, 100)
    low = band_energy(100, 300)
    mid_low = band_energy(300, 1000)
    mid_hi = band_energy(1000, 4000)
    high = band_energy(4000, 8000)
    total = sub + low + mid_low + mid_hi + high + 1e-9

    return {
        "silent": rms < SILENT_RMS,
        "rms": round(rms, 4),
        "onsets_per_sec": round(onsets_per_sec, 1),
        "sub_share": round(sub / total, 2),
        "low_share": round(low / total, 2),
        "mid_share": round((mid_low + mid_hi) / total, 2),
        "high_share": round(high / total, 2),
    }


def snapshot_wav(
    buf: AudioBuffer, seconds: float, normalize_peak_dbfs: float | None = -3.0
) -> bytes:
    """Return the last `seconds` of audio as RIFF-WAV bytes (mono int16 @ buf._sr).

    Peak-normalize math: scale so peak hits `normalize_peak_dbfs` (default -3 dBFS).
    CLIPS BEFORE CAST when scale > 1.0 (RESEARCH.md Pitfall 4 — int16 overflow
    silently produces -32768 if order inverted). Verbatim port of v4:306-331.
    """
    sr = buf._sr
    n = int(sr * seconds)
    pcm = buf.snapshot(n)

    if normalize_peak_dbfs is not None and pcm.size > 0:
        peak = int(np.abs(pcm).max())
        if peak > 0:
            target = int(32767 * (10 ** (normalize_peak_dbfs / 20.0)))
            scale = target / peak
            if scale > 1.0:
                pcm = np.clip(pcm.astype(np.float32) * scale, -32768, 32767).astype(np.int16)
            elif scale < 1.0:
                pcm = (pcm.astype(np.float32) * scale).astype(np.int16)

    bio = io.BytesIO()
    with wave.open(bio, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return bio.getvalue()


def energy_curve(buf: AudioBuffer, seconds: float = 12.0, hop: float = 1.0) -> list[float]:
    """RMS over the last `seconds`, sliced into `hop`-second windows.

    Returns a list of float RMS values, oldest first. Used by Phase 3 evidence
    packet. Verbatim port of v4:383-394.
    """
    sr = buf._sr
    n = int(sr * seconds)
    arr_int16 = buf.snapshot(n)
    arr = arr_int16.astype(np.float32) / 32768.0
    if arr.size < sr // 2:
        return []
    win = int(sr * hop)
    k = arr.size // win
    if k <= 0:
        return [round(float(np.sqrt(np.mean(arr**2))), 4)]
    windowed = arr[: k * win].reshape(k, win)
    return [round(float(np.sqrt(np.mean(w**2))), 4) for w in windowed]


def long_arc_curve(buf: AudioBuffer, seconds: float = 120.0, hop: float = 10.0) -> list[float]:
    """Coarse 2-minute energy arc, 10s hop. Lets the AI see the SET shape —
    where peaks sat, where breakdowns lived — instead of just the last 12s.

    Returns up to 12 values, oldest first. Verbatim port of v4:396-410.
    """
    sr = buf._sr
    n = int(sr * seconds)
    arr_int16 = buf.snapshot(n)
    arr = arr_int16.astype(np.float32) / 32768.0
    if arr.size < sr * 5:
        return []
    bin_size = int(sr * hop)
    k = arr.size // bin_size
    if k <= 0:
        return []
    windowed = arr[: k * bin_size].reshape(k, bin_size)
    return [round(float(np.sqrt(np.mean(w**2))), 4) for w in windowed]


def estimate_bpm(buf: AudioBuffer, seconds: float = 6.0) -> float:
    """Autocorrelation BPM estimate over the last `seconds`.

    Returns a float ~100-200 BPM (lag 30-60 frames @ 100Hz envelope) or 0.0
    on insufficient data. Verbatim port of v4:412-438.

    Note: low-precision — autocorr is meant to be a "is there a beat?"
    signal, not a precise meter. Phase 3 filters via BPM_VALID_MIN/MAX
    constants for the noise-reject gate.
    """
    sr = buf._sr
    n = int(sr * seconds)
    arr_int16 = buf.snapshot(n)
    arr = arr_int16.astype(np.float32) / 32768.0
    if arr.size < sr * 2:
        return 0.0
    frame = sr // 100
    n_frames = arr.size // frame
    if n_frames < 100:
        return 0.0
    env = np.array(
        [float(np.sqrt(np.mean(arr[i * frame : (i + 1) * frame] ** 2))) for i in range(n_frames)]
    )
    env = env - env.mean()
    ac = np.correlate(env, env, mode="full")
    ac = ac[ac.size // 2 :]
    lo_lag = 30
    hi_lag = 60
    if hi_lag >= ac.size:
        return 0.0
    segment = ac[lo_lag:hi_lag]
    if segment.size == 0 or segment.max() <= 0:
        return 0.0
    best_lag = lo_lag + int(np.argmax(segment))
    bpm = 60.0 * 100.0 / best_lag
    return round(bpm, 1)


# ---------------------------------------------------------------------------
# Phase 13-05 — downbeat-phase + bpm_confidence (mascot beat-locked entry)
# ---------------------------------------------------------------------------


# Range of plausible DJ BPMs we accept for phase analysis. Anything outside
# (0, 220] is treated as invalid and yields (0.0, 0.0) confidence — the
# anti-hallucination guard from CONTEXT.md Open Q 4 + T-13-05-02.
_BPM_MAX_VALID: float = 220.0


def compute_downbeat_phase(
    samples: np.ndarray,
    bpm: float,
    sample_rate: int,
    *,
    prior_phase: float = 0.0,
) -> tuple[float, float]:
    """Estimate (downbeat_phase, bpm_confidence) from an audio buffer + BPM hint.

    Pure function — no globals, no side effects, no caching. Same audio +
    same ``prior_phase`` always returns the same tuple. Tests rely on this.

    Returns:
        (downbeat_phase, bpm_confidence) where:
        * ``downbeat_phase`` ∈ [0.0, 1.0) is the fraction-through-current-bar
          (4 beats). 0.0 = on the downbeat, 0.5 = mid-bar.
        * ``bpm_confidence`` ∈ [0.0, 1.0]. < 0.6 means the renderer (Plan
          13-04) should NOT beat-lock entries — fall back to immediate switch.

    Anti-hallucination contract:
        * bpm ≤ 0 / NaN / > _BPM_MAX_VALID → (0.0, 0.0). No fake confidence.
        * fewer than 4 detectable onsets in the analysis window →
          (prior_phase, 0.0). Preserve the last known phase but flag no
          confidence so the renderer skips beat-lock.

    Algorithm:
        1. Validate BPM. Reject invalid → (0.0, 0.0).
        2. Compute onset envelope via spectral flux (same approach as
           snapshot_features uses for onsets_per_sec, scaled differently).
        3. Find peaks in the last 4-bar window.
        4. If < 4 peaks → (prior_phase, 0.0).
        5. Cross-correlate detected-peak comb vs synthetic comb at `bpm`;
           the lag of the best match modulo one bar → phase ∈ [0, 1).
        6. Confidence = best-match prominence (peak-vs-mean of correlation),
           clamped to [0, 1], then capped at min(1.0, n_peaks / 16.0) so a
           handful of accidental peaks can't fake high confidence.
    """
    # --- Step 1: validate BPM (anti-hallucination guard) ---
    if not isinstance(bpm, (int, float)):
        return (0.0, 0.0)
    if bpm <= 0 or math.isnan(bpm) or math.isinf(bpm) or bpm > _BPM_MAX_VALID:
        return (0.0, 0.0)
    if sample_rate <= 0 or samples is None or samples.size == 0:
        # Defensive — fall through to "preserve prior_phase, zero confidence"
        # to match the few-peak path semantics.
        return (float(prior_phase), 0.0)

    arr = samples.astype(np.float32) if samples.dtype != np.float32 else samples
    # Normalize int16-range inputs (state_refresh_loop hands us snapshot()
    # which is int16 — we cast to float32 above; if values are still in the
    # ±32k range, divide. Otherwise assume already-normalized float in ±1.
    if np.max(np.abs(arr)) > 2.0:
        arr = arr / 32768.0

    samples_per_beat = (60.0 / bpm) * sample_rate
    samples_per_bar = samples_per_beat * 4.0
    if samples_per_bar <= 0:
        return (0.0, 0.0)

    # --- Step 2: onset envelope via short-window RMS deltas ---
    win = max(1, sample_rate // 100)  # ~10ms windows
    if arr.size < win * 8:
        return (float(prior_phase), 0.0)
    n_win = arr.size // win
    # Vectorized per-window RMS (cheap reshape over the full buffer)
    trimmed = arr[: n_win * win].reshape(n_win, win)
    energies = np.sqrt(np.mean(trimmed * trimmed, axis=1))
    deltas = np.diff(energies)
    deltas = np.clip(deltas, a_min=0.0, a_max=None)

    if deltas.size == 0 or float(np.max(deltas)) <= 0.0:
        return (float(prior_phase), 0.0)

    # --- Step 3: pick peaks in deltas above an adaptive threshold ---
    thr = max(0.005, float(deltas.mean() + deltas.std()))
    # Restrict to the last ~4 bars worth of windows for locality.
    bar_in_windows = int(samples_per_bar / win)
    window_count = min(deltas.size, max(bar_in_windows * 4, 16))
    recent = deltas[-window_count:]
    peak_idx_local = np.flatnonzero(recent > thr)

    if peak_idx_local.size < 4:
        return (float(prior_phase), 0.0)

    # Map local indices back to a sample-offset within the recent slice.
    peak_samples = peak_idx_local.astype(np.float32) * float(win)

    # --- Step 4: cross-correlate against a synthetic beat comb @ bpm ---
    # The "lag" we want is the phase offset of the comb that best aligns
    # with the detected peaks. We test lags in [0, samples_per_bar) at
    # bar/64 resolution (~5-15ms depending on BPM — plenty for visual sync).
    n_lags = 64
    lag_step = samples_per_bar / n_lags
    scores = np.zeros(n_lags, dtype=np.float32)
    for i in range(n_lags):
        lag = i * lag_step
        # For each detected peak, distance to the nearest beat at this lag.
        # A perfect comb match → distance 0. Score = exp(-d/tol) summed.
        beats_under_peaks = np.round((peak_samples - lag) / samples_per_beat)
        expected = lag + beats_under_peaks * samples_per_beat
        d = np.abs(peak_samples - expected)
        tol = samples_per_beat * 0.1  # 10% of a beat tolerance
        scores[i] = float(np.sum(np.exp(-d / max(tol, 1.0))))

    best_lag_idx = int(np.argmax(scores))
    best_score = float(scores[best_lag_idx])
    mean_score = float(scores.mean())
    std_score = float(scores.std()) or 1e-6

    # Phase: lag-from-comb / bar → fraction through the bar. By convention
    # phase=0 means the analysis window ends on the 1; positive offsets
    # mean we're partway into the bar.
    phase_frac = (best_lag_idx * lag_step) / samples_per_bar
    # Wrap into [0, 1) for safety against any FP boundary drift.
    phase = phase_frac - math.floor(phase_frac)

    # --- Step 5: confidence from peak prominence + peak-count cap ---
    raw_conf = (best_score - mean_score) / std_score
    # Map z-score-ish prominence into [0, 1] — empirical: prominence ≥ 3σ on
    # ideal synthetic kicks corresponds to ~1.0; <1σ → ~0. Linear clamp.
    norm_conf = max(0.0, min(1.0, raw_conf / 3.0))
    # Few-peak penalty — 8 peaks ≈ 2 bars of kicks at 4/4 (the realistic
    # minimum analysis window state_refresh_loop hands us at 4-second
    # snapshots × 120-140 BPM). Below that, cap confidence so noisy short
    # captures can't fabricate certainty.
    peak_cap = min(1.0, float(peak_idx_local.size) / 8.0)
    confidence = min(norm_conf, peak_cap)

    return (float(phase), float(confidence))
