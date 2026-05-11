# SPDX-License-Identifier: Apache-2.0
"""crest_factor + EmaSmoother coverage (Phase 6 Wave 2).

Math reference (CONTEXT §Crest Factor Detection):
    sine RMS = amplitude / sqrt(2)  →  crest = peak/rms = sqrt(2) ≈ 1.414
    square wave  →  peak == rms     →  crest ≈ 1.0
    impulse  →  tiny rms vs full peak  →  crest > 20
    silence  →  rms = 0  →  crest = 0.0 (avoid div-by-zero)
"""

from __future__ import annotations

import numpy as np

from vibemix.state.genre import EmaSmoother, crest_factor


def test_silent_buffer_returns_zero():
    assert crest_factor(np.zeros(1000, dtype=np.int16)) == 0.0


def test_empty_buffer_returns_zero():
    assert crest_factor(np.array([], dtype=np.int16)) == 0.0


def test_pure_sine_crest_close_to_sqrt2():
    """Pure sine has peak/rms = sqrt(2) ≈ 1.414."""
    sr = 16000
    n = sr  # 1 second
    t = np.arange(n) / sr
    samples = (np.sin(2.0 * np.pi * 440.0 * t) * 30000).astype(np.int16)
    c = crest_factor(samples)
    assert 1.39 < c < 1.43, f"expected ≈ √2 (1.414), got {c}"


def test_pure_square_crest_close_to_one():
    """Constant-amplitude square wave: peak == rms → crest ≈ 1.0."""
    samples = np.full(1000, 20000, dtype=np.int16)
    c = crest_factor(samples)
    assert 0.99 < c < 1.01, f"expected ≈ 1.0, got {c}"


def test_impulse_crest_high():
    """Single big sample in a sea of zeros: rms tiny vs peak → crest > 20."""
    samples = np.zeros(1000, dtype=np.int16)
    samples[500] = 30000
    c = crest_factor(samples)
    assert c > 20, f"expected > 20 for impulse, got {c}"


def test_uniform_random_crest_close_to_sqrt3():
    """Uniform-random int16 has theoretical crest factor √3 ≈ 1.732."""
    rng = np.random.default_rng(seed=42)
    samples = rng.integers(-10000, 10001, size=4000, dtype=np.int16)
    c = crest_factor(samples)
    assert 1.65 < c < 1.85, f"expected ≈ √3 (1.732), got {c}"


def test_sparse_peaks_synthetic_crest_in_dance_master_range():
    """Sparse peaks (~5% non-zero at full amplitude, rest small) → crest 3-5,
    approximating a compressed dance master where the kick dominates."""
    rng = np.random.default_rng(seed=42)
    n = 4000
    samples = rng.integers(-2000, 2001, size=n, dtype=np.int32)  # small body
    # Place sparse spikes at ±20000 every ~20 samples
    spike_idx = np.arange(0, n, 20)
    samples[spike_idx] = 20000 * rng.choice([-1, 1], size=len(spike_idx))
    samples = samples.astype(np.int16)
    c = crest_factor(samples)
    assert 3.0 < c < 6.0, f"expected 3.0..6.0 for sparse-peaks synthetic, got {c}"


def test_negative_peak_handled():
    """Peak is abs(max), so a buffer with negative max still computes correctly."""
    samples = np.full(1000, -20000, dtype=np.int16)
    c = crest_factor(samples)
    assert 0.99 < c < 1.01


# ---------- EmaSmoother ----------


def test_ema_smoother_first_value_is_pass_through():
    s = EmaSmoother(alpha=0.3)
    assert s.update(5.0) == 5.0
    assert s.value == 5.0


def test_ema_smoother_converges_to_steady_input():
    """After the pass-through first update, subsequent same-value updates are
    a no-op. Test the convergence from a different starting point: warm up
    with 0.0, then feed 10.0 repeatedly."""
    s = EmaSmoother(alpha=0.3)
    s.update(0.0)  # warm-up pass-through
    for _ in range(20):
        s.update(10.0)
    # After 20 updates of 10.0 from a 0.0 baseline: 1 - 0.7^20 ≈ 0.999
    assert 9.5 < s.value < 10.0


def test_ema_smoother_alpha_one_means_no_memory():
    s = EmaSmoother(alpha=1.0)
    s.update(5.0)
    s.update(10.0)
    assert s.value == 10.0


def test_ema_smoother_alpha_zero_means_total_memory():
    s = EmaSmoother(alpha=0.0, initial=42.0)
    s.update(5.0)  # first update is pass-through regardless of alpha
    assert s.value == 5.0
    s.update(100.0)
    # alpha=0 → new contributes nothing; only the warmup value remains.
    assert s.value == 5.0


def test_ema_smoother_value_property_initial_zero():
    s = EmaSmoother()
    assert s.value == 0.0
