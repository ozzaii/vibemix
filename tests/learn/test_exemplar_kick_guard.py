# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 02 — EXEMPLAR-02 compressed-kick guard (RED-state stub).

The compressed-kick guard is the anti-slop gate: a hardtechno track with a
sub-heavy distorted kick has energy in the sub band (kick fundamental) AND
spillover energy in the mid band (kick harmonics). Both bands move together
over time → their per-window energies are correlated. If
``pearson_r(mid_band_per_window, sub_band_per_window) > 0.8``, the mid-band
energy is mostly KICK SPILLOVER not real mid content, so the track is a
**bad exemplar for mid-band lessons** — playing it would teach the user
"this is mid" but they'd hear a sub-heavy kick.

Three synthetic fixtures + a too-short fast-exit case pin the guard's shape:

    1. ``_make_kick_only(distortion=0.0)`` → clean sub-only kick → r ≈ 0.
    2. ``_make_kick_only(distortion=0.9)`` → heavily distorted kick → r > 0.8.
    3. ``_make_balanced_mid_track()``     → independent mid lead → r below threshold.
    4. ``samples.size < sr * 2``           → early-exit returns 0.0.

The fixture functions + first three sub-tests are copied VERBATIM from
93-RESEARCH.md §Pattern 3 so Plan 93-02's implementation is unambiguously
the reference.

REQ-ID: EXEMPLAR-02 (compressed-kick guard via Pearson r threshold).
Downstream plan that flips this skip: **Plan 93-02**.
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

    distortion=0.0 → pure sine sub kick (mid bands quiet).
    distortion=0.8 → soft-clipped (mid bands track sub bands — should fire guard).
    """
    n = SR * DUR_S
    t = np.arange(n, dtype=np.float32) / SR
    # 130 BPM = 130/60 Hz beat rate → kick every 60/130 = 0.4615 s
    period_s = 60.0 / 130.0
    # Kick envelope: exponential decay 0.1 s per hit
    kick_env = np.zeros(n, dtype=np.float32)
    for hit in range(int(DUR_S / period_s) + 1):
        start = int(hit * period_s * SR)
        end = min(start + int(0.1 * SR), n)
        decay = np.exp(-np.arange(end - start) / (0.02 * SR))
        kick_env[start:end] += decay
    # 60 Hz sine fundamental
    sub_sine = np.sin(2 * np.pi * 60 * t)
    kick = sub_sine * kick_env
    if distortion > 0:
        kick = np.tanh(kick * (1 + 10 * distortion)) / (1 + distortion)
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
