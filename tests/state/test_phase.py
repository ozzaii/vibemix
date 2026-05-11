# SPDX-License-Identifier: Apache-2.0
"""classify_phase coverage — one canned curve per phase label + the two guards.

Constants from vibemix.audio.constants (v4 verbatim):
    SILENT_RMS = 0.012
    LOW_RMS    = 0.040
    PEAK_RMS   = 0.110
"""

from __future__ import annotations

import vibemix.state.phase as phase_mod
from vibemix.state import classify_phase


def test_empty_curve_returns_silent():
    assert classify_phase([], audible=True) == "silent"


def test_not_audible_returns_silent():
    assert classify_phase([0.1, 0.1, 0.1], audible=False) == "silent"


def test_below_silent_rms_returns_silent():
    # last < SILENT_RMS (0.012) → silent
    assert classify_phase([0.005], audible=True) == "silent"


def test_low_band_returns_low():
    # SILENT_RMS (0.012) <= last < LOW_RMS (0.040) → low
    assert classify_phase([0.020], audible=True) == "low"


def test_short_curve_returns_groove():
    # len(curve) < 5 fallback. last must be >= LOW_RMS so the earlier guard
    # doesn't short-circuit to "silent" / "low".
    assert classify_phase([0.05, 0.05, 0.05], audible=True) == "groove"


def test_build_monotonic_climb():
    # 5 positive diffs over last 5 + total delta > 0.020 → build.
    assert classify_phase([0.02, 0.04, 0.06, 0.08, 0.10, 0.12], audible=True) == "build"


def test_drop_high_peak_with_recent_low():
    # last >= PEAK_RMS (0.110) AND any of recent[:3] < LOW_RMS (0.040) → drop.
    # Must dodge build gate first (need monotonic_climbs < 3 OR total delta <= 0.020).
    # curve = [0.05, 0.05, 0.05, 0.02, 0.05, 0.12]
    # recent = [0.05, 0.05, 0.02, 0.05, 0.12]
    # diffs = [0, -0.03, 0.03, 0.07] → monotonic_climbs = 2 (< 3 → no build)
    # last = 0.12 >= PEAK_RMS, recent[:3] = [0.05, 0.05, 0.02]; 0.02 < 0.040 → drop fires.
    assert classify_phase([0.05, 0.05, 0.05, 0.02, 0.05, 0.12], audible=True) == "drop"


def test_breakdown_recent_below_half_earlier_max():
    # earlier_max >= LOW_RMS (0.040) AND last < 0.5 * earlier_max → breakdown.
    # But last MUST also be >= LOW_RMS (otherwise the early-out returns "low").
    # curve = [0.10]*5 + [0.07, 0.06, 0.05, 0.045, 0.041]
    # last = 0.041 (>= LOW_RMS 0.040 → past the low-band early-out)
    # earlier (curve[-10:-5]) = [0.10]*5; earlier_max = 0.10
    # 0.041 < 0.5 * 0.10 = 0.05 → breakdown fires.
    # Dodges: not silent/low (last >= 0.040); not build (recent diffs all negative);
    # not drop (last < 0.110); not peak (recent has 0.041 < 0.045).
    curve = [0.10] * 5 + [0.07, 0.06, 0.05, 0.045, 0.041]
    assert classify_phase(curve, audible=True) == "breakdown"


def test_peak_all_recent_above_045():
    # all(v >= 0.045 for v in recent) → peak.
    # Flat curve avoids drop (last < 0.110), build (no climbs), breakdown
    # (last not < 0.5 * earlier_max).
    assert classify_phase([0.05] * 10, audible=True) == "peak"


def test_groove_fallback():
    # Default fallback: len >= 5, but no build / drop / breakdown / peak match.
    # last = 0.044 → groove.
    # earlier (curve[-10:-5]) NEEDS len(curve) >= 10. For our 7-element curve,
    # earlier = curve[:2] = [0.05, 0.05]; earlier_max = 0.05.
    # breakdown gate: last (0.044) < 0.5 * 0.05 = 0.025? NO — so no breakdown.
    # peak gate: recent has 0.043 < 0.045 → no peak. Falls through to groove.
    assert classify_phase([0.05, 0.05, 0.05, 0.04, 0.045, 0.043, 0.044], audible=True) == "groove"


def test_constants_imported_not_inlined():
    """The constants are imported from vibemix.audio.constants — Phase 6's override
    mechanism depends on this. Inlining the values would defeat the swap point."""
    assert phase_mod.SILENT_RMS == 0.012
    assert phase_mod.LOW_RMS == 0.040
    assert phase_mod.PEAK_RMS == 0.110
