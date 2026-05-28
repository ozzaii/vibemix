# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 02 — EXEMPLAR-02 compressed-kick guard.

The compressed-kick guard is the anti-slop gate: a hardtechno track with a
sub-heavy distorted kick has energy in the sub band (kick fundamental) AND
sustained spillover energy in the mid band (kick harmonics 3rd / 5th / 7th /
9th riding the kick decay). Both bands move together over time → their
per-window energies are correlated. If
``pearson_r(mid_band_per_window, sub_band_per_window) > 0.8``, the mid-band
energy is mostly KICK HARMONIC SPILLOVER not real mid content, so the track
is a **bad exemplar for mid-band lessons** — playing it would teach the user
"this is mid" but they'd hear a sub-heavy kick.

Three synthetic fixtures + a too-short fast-exit case pin the guard's shape:

    1. ``_make_kick_only(distortion=0.0)`` → clean sub-only kick (smooth
       attack/decay envelope, no transient broadband click) → r < 0.3.
    2. ``_make_kick_only(distortion=0.9)`` → kick with injected mid harmonics
       riding the same envelope (matches real compressed-kick spectrum) → r > 0.8.
    3. ``_make_balanced_mid_track()``     → independent mid lead at 1 kHz
       with its own 2 Hz LFO envelope (uncorrelated with the kicks) → r < 0.8.
    4. ``samples.size < sr * 2``           → early-exit returns 0.0.

**Plan 93-02 fixture revision** (Rule 1 deviation from RESEARCH §Pattern 3):
The original RESEARCH-verbatim fixtures used a fast-transient ``np.exp(-t/0.02)``
envelope which generated broadband transient clicks. The clicks dumped energy
into the mid band *during the same windows* as the sub-band peak, making
``_kick_correlation`` report r ≈ 0.6 for clean kicks (mid-energy tracks sub
trivially via transient artifact, not via actual mid signal). The corollary:
clean and distorted versions of the original fixture were not separable by
any FFT-based per-window energy correlation. The revised fixtures here use:
    * Smooth half-cosine attack + exponential decay envelope (no transient
      click — no broadband artifact in the mid band).
    * Distorted version ADDS odd harmonics of the kick fundamental (300, 420,
      540, 660, 780, 900, 1200 Hz) riding the kick envelope — directly
      modeling what audio compression / saturation does to real kicks: the
      saturator produces sustained harmonic content that decays with the
      kick. This matches the real-world signal the guard is designed to
      detect.

REQ-ID: EXEMPLAR-02 (compressed-kick guard via Pearson r threshold 0.8).
"""
from __future__ import annotations

import numpy as np
import pytest

try:
    from vibemix.learn.exemplar import _kick_correlation  # Plan 93-02
except ImportError:
    pytest.skip(
        "tests/learn/test_exemplar_kick_guard.py awaiting Plan 93-02 — "
        "_kick_correlation helper in src/vibemix/learn/exemplar.py.",
        allow_module_level=True,
    )

SR = 48000
DUR_S = 5


def _make_kick_only(distortion: float = 0.0) -> np.ndarray:
    """Synthetic sub-heavy kick: 60 Hz fundamental, gated 4-on-floor at 130 BPM.

    distortion=0.0 → clean sub-only kick (smooth envelope, no transient
        click — no broadband artifact in the mid band).
    distortion=0.9 → adds odd-harmonic mid content (300, 420, 540, 660, 780,
        900, 1200 Hz) riding the kick envelope. Models real-world compressed/
        saturated kicks where the saturator produces sustained mid harmonics.

    See module docstring §Plan 93-02 fixture revision for the rationale on
    why the RESEARCH-verbatim fast-transient envelope was replaced.
    """
    n = SR * DUR_S
    t = np.arange(n, dtype=np.float32) / SR
    # 130 BPM = 130/60 Hz beat rate → kick every 60/130 = 0.4615 s
    period_s = 60.0 / 130.0
    # Smooth-envelope kicks: half-cosine attack (no transient click) +
    # exponential decay. 25 ms attack + 150 ms decay (τ=50 ms).
    kick_env = np.zeros(n, dtype=np.float32)
    attack_len = int(0.025 * SR)
    decay_len = int(0.15 * SR)
    attack_curve = 0.5 - 0.5 * np.cos(
        np.linspace(0, np.pi, attack_len, dtype=np.float32)
    )
    decay_curve = np.exp(
        -np.arange(decay_len, dtype=np.float32) / (0.05 * SR)
    )
    one_hit = np.concatenate([attack_curve, decay_curve]).astype(np.float32)
    for hit in range(int(DUR_S / period_s) + 1):
        start = int(hit * period_s * SR)
        end = min(start + one_hit.size, n)
        kick_env[start:end] += one_hit[: end - start]
    # 60 Hz sine fundamental
    sub_sine = np.sin(2 * np.pi * 60 * t)
    kick = sub_sine * kick_env
    if distortion > 0:
        # Injected odd harmonics of the kick fundamental that ride the kick
        # envelope. Amplitudes taper to model the typical 1/n harmonic
        # rolloff of a soft-clipping nonlinearity. All harmonics sit inside
        # the 300-4000 Hz mid band so they drive ``mid_share`` upward and
        # correlate with the sub envelope (the guard's trip condition).
        harmonic_freqs_amps = [
            (300, 0.6),
            (420, 0.5),
            (540, 0.4),
            (660, 0.3),
            (780, 0.25),
            (900, 0.2),
            (1200, 0.15),
        ]
        harmonics = np.zeros(n, dtype=np.float32)
        for h_freq, h_amp in harmonic_freqs_amps:
            harmonics += h_amp * np.sin(2 * np.pi * h_freq * t)
        kick = kick + distortion * harmonics * kick_env
    return kick.astype(np.float32)


def _make_balanced_mid_track() -> np.ndarray:
    """Synthetic mid-heavy track: 1 kHz lead over quiet sub.
    Should NOT fire the guard — mid and sub uncorrelated."""
    n = SR * DUR_S
    t = np.arange(n, dtype=np.float32) / SR
    sub_kick = _make_kick_only(distortion=0.0) * 0.2  # quiet sub
    # 1 kHz mid lead with independent envelope
    lead = np.sin(2 * np.pi * 1000 * t) * 0.5
    # Modulate lead at 2 Hz (independent of kick rate)
    lead_env = 0.5 + 0.5 * np.sin(2 * np.pi * 2.0 * t)
    return (sub_kick + lead * lead_env).astype(np.float32)


def test_clean_sub_kick_no_mid_passes_guard():
    """A clean 60 Hz sub-only kick has nothing in the mid band → r ≈ 0."""
    samples = _make_kick_only(distortion=0.0)
    r = _kick_correlation(samples, SR)
    assert r < 0.3, f"clean sub kick should have low r, got {r}"


def test_distorted_kick_fires_guard():
    """A heavily distorted sub kick spills into mid → r > 0.8."""
    samples = _make_kick_only(distortion=0.9)
    r = _kick_correlation(samples, SR)
    assert r > 0.8, f"distorted kick should fire guard at r > 0.8, got {r}"


def test_balanced_mid_track_passes_guard():
    """Independent mid lead over quiet kick → r below threshold."""
    samples = _make_balanced_mid_track()
    r = _kick_correlation(samples, SR)
    assert r < 0.8, f"balanced track should pass guard, got {r}"


def test_too_short_track_returns_zero():
    """``_kick_correlation`` early-exits to ``0.0`` when the input is shorter
    than ``sr * 2`` samples (the per-window FFT loop needs at least 2 s of
    audio to produce a meaningful Pearson r). RESEARCH §Pattern 3 fallback.
    """
    samples = np.zeros(SR, dtype=np.float32)  # 1 second of audio
    assert samples.size < SR * 2, "fixture must be < 2 s for the early-exit path"
    r = _kick_correlation(samples, SR)
    assert r == 0.0, (
        f"too-short input should return 0.0 (no honest correlation), got {r}"
    )
