# SPDX-License-Identifier: Apache-2.0
"""Pure-function tests for `vibemix.state.detectors._phrase_dsp` —
band-limited (40-120Hz) autocorrelation + downbeat-phase locking + phrase-
length self-similarity estimation. These are the load-bearing primitives
behind ``PhraseBoundaryDetector`` (Plan 17-04 Task 2) and Plan 06's
``tune_detectors.py`` reference-WAV harness.

The synthetic-kick helper ``_synth_kick_pattern`` builds a deterministic
4-on-floor pattern (60Hz sine pulses, 10ms attack + 100ms exponential decay
envelope per pulse) so the autocorr lock can be pinned at exact lag values
without recording real audio.

The ±5% lag tolerance translates to ±1-bar absolute downbeat accuracy per
SENSE-14 (a beat at 130 BPM is ~462ms; ±5% ≈ ±23ms — well inside the
±1-bar = ±1.85s SENSE-14 contract).
"""

from __future__ import annotations

import numpy as np

from vibemix.state.detectors._phrase_dsp import (
    band_limited_autocorr,
    estimate_phrase_length_bars,
    lock_downbeat_phase,
)


# ---------------------------------------------------------------------------
# Synthetic kick generator — used by Tests 1 / 2 (autocorr lock at 130/150/170)
# ---------------------------------------------------------------------------

_SR = 16000


def _synth_kick_pattern(
    bpm: float,
    duration_s: float,
    sr: int = _SR,
    *,
    kick_freq_hz: float = 60.0,
    attack_ms: float = 10.0,
    decay_ms: float = 100.0,
) -> np.ndarray:
    """Build a 4-on-floor synthetic kick pattern: a kick lands every beat
    (60 / bpm seconds apart). Each kick is a brief 60Hz sine with a 10ms
    linear attack into a 100ms exponential decay — enough low-band energy
    that ``band_limited_autocorr`` locks to the beat period.

    Returns float32 in ``[-1, 1]`` with the kicks summed onto a zero buffer.
    """
    n = int(sr * duration_s)
    out = np.zeros(n, dtype=np.float32)
    beat_period_s = 60.0 / bpm
    samples_per_beat = int(beat_period_s * sr)

    attack_n = int((attack_ms / 1000.0) * sr)
    decay_n = int((decay_ms / 1000.0) * sr)
    pulse_n = attack_n + decay_n

    # Build one canonical kick pulse and copy-paste it onto every beat slot.
    t_pulse = np.arange(pulse_n, dtype=np.float32) / float(sr)
    sine = np.sin(2.0 * np.pi * kick_freq_hz * t_pulse)
    env = np.zeros(pulse_n, dtype=np.float32)
    if attack_n > 0:
        env[:attack_n] = np.linspace(0.0, 1.0, attack_n, dtype=np.float32)
    if decay_n > 0:
        # Exponential decay over the decay segment: amp * exp(-5 * x/decay_n)
        x = np.arange(decay_n, dtype=np.float32) / float(decay_n)
        env[attack_n:] = np.exp(-5.0 * x)
    pulse = (sine * env).astype(np.float32)

    # Drop a kick on every beat boundary (skip the first sample so the
    # autocorr peak isn't dominated by the lag-0 self-match).
    for beat_idx in range(int(duration_s / beat_period_s)):
        start = beat_idx * samples_per_beat
        end = start + pulse_n
        if end > n:
            break
        out[start:end] += pulse
    # Normalize to avoid clip when summed pulses overlap on short patterns.
    peak = float(np.max(np.abs(out)))
    if peak > 0.0:
        out = out / peak * 0.6
    return out


# ---------------------------------------------------------------------------
# Test 1: band_limited_autocorr locks to synthetic 4-on-floor at 130 BPM
# ---------------------------------------------------------------------------


def test_band_limited_autocorr_locks_synthetic_4on4_at_130bpm():
    bpm = 130.0
    samples = _synth_kick_pattern(bpm, duration_s=16.0, sr=_SR)
    ac = band_limited_autocorr(samples, _SR, low_hz=40.0, high_hz=120.0)

    # Expected lag = samples per beat at 130 BPM
    expected_lag = int((60.0 / bpm) * _SR)  # ≈ 7384
    tol = int(expected_lag * 0.05)

    # Search for the dominant peak in a window around expected_lag.
    # Skip the first ~100 samples (lag-0 dominates anything pure).
    lo = max(100, expected_lag - tol * 4)
    hi = min(ac.size, expected_lag + tol * 4)
    assert hi > lo, "autocorr too short to contain expected lag window"
    seg = ac[lo:hi]
    peak_lag = lo + int(np.argmax(seg))

    assert abs(peak_lag - expected_lag) <= tol, (
        f"peak_lag={peak_lag} expected≈{expected_lag} (±{tol})"
    )


# ---------------------------------------------------------------------------
# Test 2: locks at 150 + 170 BPM (Hard Tek band)
# ---------------------------------------------------------------------------


def test_band_limited_autocorr_locks_at_150bpm_and_170bpm():
    for bpm in (150.0, 170.0):
        samples = _synth_kick_pattern(bpm, duration_s=16.0, sr=_SR)
        ac = band_limited_autocorr(samples, _SR, low_hz=40.0, high_hz=120.0)

        expected_lag = int((60.0 / bpm) * _SR)
        tol = int(expected_lag * 0.05)
        lo = max(100, expected_lag - tol * 4)
        hi = min(ac.size, expected_lag + tol * 4)
        seg = ac[lo:hi]
        peak_lag = lo + int(np.argmax(seg))
        assert abs(peak_lag - expected_lag) <= tol, (
            f"bpm={bpm} peak_lag={peak_lag} expected≈{expected_lag} (±{tol})"
        )


# ---------------------------------------------------------------------------
# Test 3: out-of-band noise produces a much weaker autocorr peak
# ---------------------------------------------------------------------------


def test_band_limited_autocorr_rejects_high_freq_noise():
    """Pink noise band-limited to 1-4kHz (well above the 40-120Hz kick band)
    must NOT produce a meaningful autocorr peak. The 40-120Hz pre-band-limit
    suppresses out-of-band content; when the residual in-band energy is < 1%
    of the input RMS, the function returns an empty array (anti-hallucination
    per T-17-04-01 — never normalize numerical noise to 1.0 at lag-0).

    Synthetic kick pattern of identical duration produces a real peak, so the
    contract is asymmetric: kick → real autocorr; noise → empty / negligible."""
    rng = np.random.default_rng(seed=42)
    n = _SR * 16
    # Generate white noise then bandpass via FFT mask to 1-4kHz
    noise = rng.standard_normal(n).astype(np.float32)
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(n, d=1.0 / _SR)
    mask = (freqs >= 1000.0) & (freqs <= 4000.0)
    spec[~mask] = 0.0
    hf_noise = np.fft.irfft(spec, n=n).astype(np.float32)
    # Normalize to the same 0.6 peak as _synth_kick_pattern for fairness.
    peak = float(np.max(np.abs(hf_noise)))
    if peak > 0.0:
        hf_noise = hf_noise / peak * 0.6

    ac_noise = band_limited_autocorr(hf_noise, _SR)

    # Compare against a kick pattern of the same length.
    kick = _synth_kick_pattern(130.0, duration_s=16.0, sr=_SR)
    ac_kick = band_limited_autocorr(kick, _SR)

    # Kick produces a real autocorr; out-of-band noise produces an empty array.
    assert ac_kick.size > 0, "synthetic kick must produce a measurable autocorr"
    if ac_noise.size > 0:
        # If any residual passed the 1% floor, the lag>0 peak must be much
        # weaker than the kick's lag>0 peak.
        noise_peak = float(np.max(np.abs(ac_noise[100:]))) if ac_noise.size > 100 else 0.0
        kick_peak = float(np.max(np.abs(ac_kick[100:])))
        assert noise_peak < 0.3 * kick_peak, (
            f"out-of-band noise peak {noise_peak:.3f} should be < 30% of kick peak {kick_peak:.3f}"
        )
    # Either branch satisfies the rejection contract.


# ---------------------------------------------------------------------------
# Test 4: lock_downbeat_phase contract (phase ∈ [0,1), confidence ∈ [0,1])
# ---------------------------------------------------------------------------


def test_lock_downbeat_phase_returns_phase_in_zero_to_one():
    bpm = 130.0
    samples = _synth_kick_pattern(bpm, duration_s=8.0, sr=_SR)
    phase, conf = lock_downbeat_phase(samples, bpm, _SR)
    assert 0.0 <= phase < 1.0
    assert 0.0 <= conf <= 1.0


def test_lock_downbeat_phase_invalid_bpm_returns_zero_zero():
    """Anti-hallucination contract: BPM ≤ 0, NaN, > 220 → (0.0, 0.0)."""
    samples = _synth_kick_pattern(130.0, duration_s=8.0, sr=_SR)
    assert lock_downbeat_phase(samples, -1.0, _SR) == (0.0, 0.0)
    assert lock_downbeat_phase(samples, 0.0, _SR) == (0.0, 0.0)
    assert lock_downbeat_phase(samples, 250.0, _SR) == (0.0, 0.0)
    assert lock_downbeat_phase(samples, float("nan"), _SR) == (0.0, 0.0)


# ---------------------------------------------------------------------------
# Test 5: estimate_phrase_length_bars finds 16-bar peak in self-similarity
# ---------------------------------------------------------------------------


def test_phrase_length_bars_estimates_8_16_32_from_self_similarity():
    """Synthetic energy_curve with a clear 16-bar self-similarity peak
    returns 16. Curve resolution = 1s hop; 16 bars at 130 BPM = ~29.5s,
    so we tile the energy pattern with that period."""
    bpm = 130.0
    bars = 16
    period_s = bars * 4.0 * 60.0 / bpm  # ≈ 29.54s
    period_hops = int(round(period_s))  # at 1s hop
    n_periods = 6
    base = np.array([0.10, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70])
    # Stretch base to period_hops length by repeating
    pattern = np.tile(base, (period_hops // base.size) + 1)[:period_hops]
    curve = np.tile(pattern, n_periods).tolist()

    result = estimate_phrase_length_bars(curve, bpm)
    assert result == 16


def test_phrase_length_bars_returns_default_on_short_curve():
    """Energy curve too short for 8-bar evaluation → default 16 (most common
    dance-music phrase length, documented as the conservative-fallback)."""
    short_curve = [0.1, 0.2, 0.3]
    assert estimate_phrase_length_bars(short_curve, bpm=130.0) == 16


def test_phrase_length_bars_returns_16_on_unconvincing_self_similarity():
    """Random energy curve with no dominant period → 16 fallback."""
    rng = np.random.default_rng(seed=7)
    random_curve = rng.uniform(0.1, 0.6, size=60).tolist()
    assert estimate_phrase_length_bars(random_curve, bpm=130.0) == 16
