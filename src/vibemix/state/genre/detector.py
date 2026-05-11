# SPDX-License-Identifier: Apache-2.0
"""Percentile-based phase detector + HysteresisState.

Phase 6 Wave 3. The replacement for the absolute-threshold ``classify_phase``
when a genre profile is active. Adapts thresholds to the track's own loudness
distribution (30th/70th/95th percentiles over the rolling 120s energy curve)
rather than relying on globally-tuned RMS constants.

Algorithm (06-CONTEXT.md §Percentile-Based Phase Detector):

    1. Cold start (curve < 30 samples): fall back to profile's absolute
       thresholds (silent / low / groove / peak / drop, NO percentiles).
    2. Silent gate (post-warmup): last < profile.silent_rms → 'silent'.
    3. Build detection: last 5 monotonically climbing AND span > profile
       build_climb_threshold → 'build'. STRICTER than v4 (4 climbs, not 3).
    4. Compute p30 / p70 / p95 over the full curve.
    5. Breakdown detection: last < profile.breakdown_ratio * recent_peak
       AND recent_peak > p70 → 'breakdown'.
    6. Drop detection: last >= p95 AND (last - prev) > profile.drop_jump_threshold
       → 'drop'. Otherwise sustained peak → 'peak'.
    7. Tier mapping (otherwise):
         last < p30 → 'low'
         p30 ≤ last < p70 → 'groove'
         p70 ≤ last < p95 → 'peak'

3-tick hysteresis prevents flicker between adjacent labels. ``silent`` commits
immediately (anti-hallucination — audio death is unambiguous).

No new heavy DSP deps — numpy only (Critical Constraint 6).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vibemix.state.genre.profile import GenreProfile

_HYSTERESIS_DWELL_TICKS = 3
_MIN_CURVE_FOR_PERCENTILES = 30


@dataclass
class HysteresisState:
    """3-tick hysteresis state. The detector returns the CURRENT committed
    phase + the (possibly mutated) HysteresisState. Caller threads the state
    object through subsequent calls.

    Implementation: track ``pending_label`` and ``pending_ticks``. When the
    raw classifier output differs from ``current_label``, set/increment
    ``pending_ticks``. When ``pending_ticks >= 3``, commit. ``silent`` is a
    special case — commits immediately (CONTEXT anti-hallucination rule).
    """

    current_label: str = "silent"
    pending_label: str | None = None
    pending_ticks: int = 0


def _cold_start_phase(curve: list, profile: GenreProfile) -> str:
    """Phase 3-style absolute-threshold path, using the profile's own
    silent_rms / low_rms / peak_rms (not the global v4 constants).
    Used when the curve has fewer than 30 samples (first ~30s of session).
    """
    if not curve:
        return "silent"
    last = curve[-1]
    if last < profile.silent_rms:
        return "silent"
    if last < profile.low_rms:
        return "low"
    if (
        last >= profile.peak_rms
        and len(curve) >= 5
        and any(v < profile.low_rms for v in curve[-5:-2])
    ):
        return "drop"
    if last >= profile.peak_rms:
        return "peak"
    return "groove"


def _apply_hysteresis(raw: str, hs: HysteresisState) -> str:
    """Mutate ``hs`` in place. Returns the committed phase label.

    - ``silent`` commits immediately (no dwell required — anti-hallucination).
    - If raw matches current, reset pending and return current.
    - If raw matches pending, increment counter; commit at >= 3 ticks.
    - If raw is a new pending value, reset counter to 1.
    """
    if raw == "silent":
        hs.current_label = "silent"
        hs.pending_label = None
        hs.pending_ticks = 0
        return "silent"
    if raw == hs.current_label:
        hs.pending_label = None
        hs.pending_ticks = 0
        return hs.current_label
    if hs.pending_label == raw:
        hs.pending_ticks += 1
        if hs.pending_ticks >= _HYSTERESIS_DWELL_TICKS:
            hs.current_label = raw
            hs.pending_label = None
            hs.pending_ticks = 0
        return hs.current_label
    # New pending value or oscillation — reset counter to 1.
    hs.pending_label = raw
    hs.pending_ticks = 1
    return hs.current_label


def classify_phase_percentile(
    curve: list,
    features: dict | None,
    profile: GenreProfile,
    hysteresis_state: HysteresisState,
) -> tuple[str, HysteresisState]:
    """Percentile-based phase tag with 3-tick hysteresis.

    Returns (committed_label, hysteresis_state). The state is mutated in place
    and also returned for explicit threading.

    ``features`` parameter is reserved for future per-genre band-share gates;
    not used by v1 heuristics (heuristics genre-agnostic in v1).
    """
    # Step 1: cold-start fallback.
    if len(curve) < _MIN_CURVE_FOR_PERCENTILES:
        raw = _cold_start_phase(curve, profile)
        return _apply_hysteresis(raw, hysteresis_state), hysteresis_state

    last = curve[-1]

    # Step 2: silent gate (overrides everything else).
    if last < profile.silent_rms:
        return _apply_hysteresis("silent", hysteresis_state), hysteresis_state

    # Step 3: build detection — ALL 4 deltas positive (stricter than v4's >= 3).
    recent5 = curve[-5:]
    diffs = [recent5[i] - recent5[i - 1] for i in range(1, len(recent5))]
    monotonic_climbs = sum(1 for d in diffs if d > 0)
    if monotonic_climbs >= 4 and (recent5[-1] - recent5[0]) > profile.build_climb_threshold:
        return _apply_hysteresis("build", hysteresis_state), hysteresis_state

    # Step 4: compute percentiles + recent peak.
    arr = np.asarray(curve, dtype=float)
    p30 = float(np.percentile(arr, 30))
    p70 = float(np.percentile(arr, 70))
    p95 = float(np.percentile(arr, 95))
    recent_peak = float(np.max(arr[-10:]) if len(arr) >= 10 else np.max(arr))

    # Step 5: breakdown detection (after build, before tier mapping).
    if last < profile.breakdown_ratio * recent_peak and recent_peak > p70:
        return _apply_hysteresis("breakdown", hysteresis_state), hysteresis_state

    # Step 6: drop / peak at top tier (>= p95).
    if last >= p95:
        prev = curve[-2] if len(curve) >= 2 else 0.0
        jump = last - prev
        if jump > profile.drop_jump_threshold:
            return _apply_hysteresis("drop", hysteresis_state), hysteresis_state
        return _apply_hysteresis("peak", hysteresis_state), hysteresis_state

    # Step 7: tier mapping.
    if last < p30:
        raw = "low"
    elif last < p70:
        raw = "groove"
    else:  # p70 <= last < p95
        raw = "peak"
    return _apply_hysteresis(raw, hysteresis_state), hysteresis_state
