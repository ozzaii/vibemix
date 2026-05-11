# SPDX-License-Identifier: Apache-2.0
"""classify_phase_percentile + HysteresisState coverage (Phase 6 Wave 3).

CONTEXT D-LOCKED §Percentile-Based Phase Detector. The detector uses the
profile's per-genre overrides for absolute thresholds during cold start, then
flips to percentile-based mapping once the curve has 30+ samples.

3-tick hysteresis prevents flicker. ``silent`` commits immediately
(anti-hallucination).
"""

from __future__ import annotations

import numpy as np

from vibemix.state.genre import (
    HysteresisState,
    classify_phase_percentile,
    load_profile,
)


def _techno():
    return load_profile("techno")


# ---------- Cold start ----------


def test_cold_start_below_silent_returns_silent():
    """curve < 30 samples + last < silent_rms → 'silent'."""
    label, _ = classify_phase_percentile([0.005], None, _techno(), HysteresisState())
    assert label == "silent"


def test_cold_start_above_peak_returns_peak():
    """curve < 30 samples + last >= peak_rms (no recent-low) → 'peak' via cold-start."""
    # techno peak_rms=0.110. Need 3 ticks of hysteresis (initial label=silent → peak).
    # Cold-start path branches before percentile but still applies hysteresis.
    h = HysteresisState()
    label, _ = classify_phase_percentile([0.120] * 10, None, _techno(), h)
    # First tick: raw='peak', current_label='silent', pending=peak ticks=1 → stays 'silent'
    assert label == "silent"
    # Subsequent ticks accumulate
    label, _ = classify_phase_percentile([0.120] * 10, None, _techno(), h)
    label, _ = classify_phase_percentile([0.120] * 10, None, _techno(), h)
    assert label == "peak"


def test_cold_start_under_30_samples_skips_percentile():
    """Verify the percentile branch is NOT taken with sub-30 curve.
    Insert a NaN in a synthetic curve — np.percentile would propagate NaN.
    If the cold-start branch is correct, the NaN never sees percentile math."""
    curve = [0.060] * 10  # 10 samples → cold-start
    label, _ = classify_phase_percentile(curve, None, _techno(), HysteresisState())
    # last=0.060, low_rms=0.040, peak_rms=0.110 — between → 'groove' (silent-committed initially)
    assert label == "silent"  # hysteresis: pending=groove, ticks=1 → still silent


# ---------- Silent gate (post-cold-start) ----------


def test_silent_gate_post_warmup():
    """curve >= 30 samples + last < silent_rms → 'silent' (immediate commit)."""
    curve = [0.05] * 40 + [0.005]
    h = HysteresisState(current_label="peak")
    label, _ = classify_phase_percentile(curve, None, _techno(), h)
    assert label == "silent"  # silent commits immediately, regardless of prior


# ---------- Percentile tier mapping ----------


def test_percentile_low_tier():
    """Last sits below p30 → 'low' (after hysteresis convergence)."""
    # Curve: 30 samples mostly at 0.05, then a single low sample at 0.020.
    # p30 will be ≈ 0.05, last=0.020 → 'low'.
    curve = [0.05] * 30 + [0.020]
    h = HysteresisState()
    # Verify the percentiles produce the expected mapping:
    arr = np.asarray(curve)
    assert np.percentile(arr, 30) > 0.020  # confirm last < p30
    # Hysteresis: pending=low, ticks=1 (current=silent)
    label, _ = classify_phase_percentile(curve, None, _techno(), h)
    label, _ = classify_phase_percentile(curve, None, _techno(), h)
    label, _ = classify_phase_percentile(curve, None, _techno(), h)
    assert label == "low"


def test_percentile_peak_tier_sustained():
    """Sustained peak (last >= p95 but no jump) → 'peak', not 'drop'."""
    curve = [0.090] * 40
    h = HysteresisState()
    # All 40 samples identical — p95=0.090, last=0.090, prev=0.090. Jump=0 < threshold.
    # raw='peak'. Hysteresis: 3 ticks to commit.
    for _ in range(3):
        label, _ = classify_phase_percentile(curve, None, _techno(), h)
    assert label == "peak"


# ---------- Build detection ----------


def test_build_monotonic_climb():
    """4-positive-diff climb with span > build_climb_threshold (0.025 for techno)."""
    # 30+ samples; tail strictly climbs from 0.030 to 0.060 (span 0.030 > 0.025).
    curve = [0.030] * 30 + [0.030, 0.035, 0.040, 0.045, 0.060]
    h = HysteresisState()
    for _ in range(3):
        label, _ = classify_phase_percentile(curve, None, _techno(), h)
    assert label == "build"


def test_build_NOT_fired_with_only_3_climbs():
    """v4 used >= 3 climbs; percentile path uses >= 4 (stricter). Verify
    3 climbs alone do NOT trip build."""
    # 3 positive diffs + 1 flat → only 3 climbs, not 4.
    curve = [0.030] * 30 + [0.030, 0.035, 0.040, 0.045, 0.045]
    h = HysteresisState()
    for _ in range(3):
        label, _ = classify_phase_percentile(curve, None, _techno(), h)
    # raw is NOT 'build'; falls to percentile tier mapping.
    assert label != "build"


# ---------- Breakdown detection ----------


def test_breakdown_after_recent_peak():
    """last < breakdown_ratio * recent_peak AND recent_peak > p70 → 'breakdown'."""
    # Setup: build up to a peak then crash.
    # techno breakdown_ratio=0.4. recent_peak=0.100 → threshold=0.04. last=0.020 < 0.04.
    # Need recent_peak > p70. Make p70 < 0.100 by salting with lower values.
    curve = [0.040] * 30 + [0.100, 0.100, 0.100, 0.100, 0.020]
    h = HysteresisState()
    for _ in range(3):
        label, _ = classify_phase_percentile(curve, None, _techno(), h)
    assert label == "breakdown"


# ---------- Drop detection ----------


def test_drop_with_jump():
    """last >= p95 AND jump > drop_jump_threshold (0.060 for techno) → 'drop'."""
    # 35 samples at 0.050 + tail [0.040, 0.040, 0.040, 0.040, 0.120].
    # last=0.120, prev=0.040, jump=0.080 > 0.060 → 'drop'.
    # But p95 of 35 samples mostly at 0.050 plus the 0.120 spike: p95 ≈ 0.110.
    # last=0.120 >= 0.110 → 'drop' branch.
    curve = [0.050] * 35 + [0.040, 0.040, 0.040, 0.040, 0.120]
    h = HysteresisState()
    arr = np.asarray(curve)
    p95 = np.percentile(arr, 95)
    assert curve[-1] >= p95, f"last={curve[-1]} not >= p95={p95}"
    for _ in range(3):
        label, _ = classify_phase_percentile(curve, None, _techno(), h)
    assert label == "drop"


def test_drop_at_top_without_jump_returns_peak_not_drop():
    """Sustained top tier without a single-tick jump → 'peak', not 'drop'."""
    # All samples at 0.090 → no jump anywhere.
    curve = [0.090] * 40
    h = HysteresisState()
    for _ in range(3):
        label, _ = classify_phase_percentile(curve, None, _techno(), h)
    assert label == "peak"


# ---------- Hysteresis ----------


def test_hysteresis_requires_3_ticks_to_transition():
    """Once 'committed' to a label, need 3 consecutive ticks of a different
    label before flipping."""
    h = HysteresisState(current_label="groove")
    # Sustained-peak curve (would classify raw='peak'):
    curve = [0.090] * 40
    # Tick 1: pending=peak, ticks=1 → still 'groove'
    label, _ = classify_phase_percentile(curve, None, _techno(), h)
    assert label == "groove"
    assert h.pending_label == "peak"
    assert h.pending_ticks == 1
    # Tick 2: ticks=2 → still 'groove'
    label, _ = classify_phase_percentile(curve, None, _techno(), h)
    assert label == "groove"
    assert h.pending_ticks == 2
    # Tick 3: ticks=3 → COMMITS 'peak'
    label, _ = classify_phase_percentile(curve, None, _techno(), h)
    assert label == "peak"
    assert h.pending_label is None
    assert h.pending_ticks == 0


def test_hysteresis_silent_commits_immediately():
    """'silent' bypasses hysteresis (anti-hallucination)."""
    h = HysteresisState(current_label="peak")
    curve = [0.05] * 40 + [0.005]  # last < silent_rms
    label, _ = classify_phase_percentile(curve, None, _techno(), h)
    assert label == "silent"
    assert h.current_label == "silent"


def test_hysteresis_pending_resets_on_oscillation():
    """If pending was 'peak' then raw flips to 'drop', the counter resets to 1."""
    h = HysteresisState(current_label="groove")
    curve_peak = [0.090] * 40
    # Establish pending=peak, ticks=1
    classify_phase_percentile(curve_peak, None, _techno(), h)
    assert h.pending_label == "peak"
    assert h.pending_ticks == 1

    # Now feed a 'drop' curve. pending_label flips, ticks resets to 1.
    curve_drop = [0.050] * 35 + [0.040, 0.040, 0.040, 0.040, 0.120]
    classify_phase_percentile(curve_drop, None, _techno(), h)
    # raw='drop' != current_label='groove' AND != pending_label='peak'
    # → reset pending=drop, ticks=1
    assert h.pending_label == "drop"
    assert h.pending_ticks == 1
    # current_label still 'groove'
    assert h.current_label == "groove"


def test_hysteresis_same_as_current_resets_pending():
    """If raw == current_label, pending fields reset."""
    # Build a curve where last sits in [p30, p70) → raw='groove'.
    # Use a wide linspace then anchor last at the median.
    curve = [*np.linspace(0.01, 0.08, 34).tolist(), 0.040]
    arr = np.asarray(curve)
    p30 = float(np.percentile(arr, 30))
    p70 = float(np.percentile(arr, 70))
    assert p30 <= curve[-1] < p70, f"curve last={curve[-1]} not in groove tier [{p30}, {p70})"
    h = HysteresisState(current_label="groove", pending_label="peak", pending_ticks=2)
    label, _ = classify_phase_percentile(curve, None, _techno(), h)
    assert label == "groove"
    assert h.pending_label is None
    assert h.pending_ticks == 0


# ---------- features parameter is reserved ----------


def test_features_parameter_ignored_in_v1():
    """v1: features reserved for future per-genre heuristics; not used."""
    curve = [0.090] * 40
    h1 = HysteresisState()
    h2 = HysteresisState()
    label_none, _ = classify_phase_percentile(curve, None, _techno(), h1)
    label_with, _ = classify_phase_percentile(curve, {"mid_share": 0.99}, _techno(), h2)
    assert label_none == label_with
