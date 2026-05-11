# SPDX-License-Identifier: Apache-2.0
"""classify_phase — dispatching entry point.

Phase 3: ``classify_phase(curve, audible) -> str`` was the v4-verbatim
absolute-threshold port.

Phase 6 (this file): ``classify_phase`` becomes a DISPATCH function. When
called without a profile (positional, or ``profile=None``), the original v4
body executes and returns a plain ``str`` — byte-equivalent to Phase 3
(pinned via golden test).

When called with a profile (and optionally features + hysteresis_state), the
percentile-per-genre path executes and returns a ``(label, HysteresisState)``
tuple.

This conditional-return shape preserves backward compatibility — existing
callers (``state_refresh_loop`` Phase 3 path, tests in
``tests/state/test_phase.py``) keep working unchanged.

Constants SILENT_RMS / LOW_RMS / PEAK_RMS are imported from
``vibemix.audio.constants`` for the v4 path. Phase 6's percentile path uses
the active profile's per-genre overrides instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vibemix.audio.constants import LOW_RMS, PEAK_RMS, SILENT_RMS

if TYPE_CHECKING:
    from vibemix.state.genre.detector import HysteresisState
    from vibemix.state.genre.profile import GenreProfile


def _classify_phase_v4(curve: list, audible: bool) -> str:
    """Phase 3 v4-verbatim path. Kept as the fallback when no genre profile is
    active. Body byte-equivalent to the original phase.py classify_phase from
    commit 8106a16/8e04dfc — golden-equivalent pinned via test_phase.py."""
    if not audible or not curve:
        return "silent"
    last = curve[-1]
    if last < SILENT_RMS:
        return "silent"
    if last < LOW_RMS:
        return "low"
    if len(curve) < 5:
        return "groove"
    recent = curve[-5:]
    earlier = curve[-10:-5] if len(curve) >= 10 else curve[: max(0, len(curve) - 5)]
    earlier_max = max(earlier) if earlier else 0.0

    diffs = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
    monotonic_climbs = sum(1 for d in diffs if d > 0)
    if monotonic_climbs >= 3 and (recent[-1] - recent[0]) > 0.020:
        return "build"
    if last >= PEAK_RMS and any(v < LOW_RMS for v in recent[:3]):
        return "drop"
    if earlier_max >= 0.040 and last < 0.5 * earlier_max:
        return "breakdown"
    if all(v >= 0.045 for v in recent):
        return "peak"
    return "groove"


def classify_phase(
    curve: list,
    audible: bool,
    *,
    profile: GenreProfile | None = None,
    features: dict | None = None,
    hysteresis_state: HysteresisState | None = None,
):
    """Phase classification with optional genre-aware percentile dispatch.

    - ``profile=None`` (default, Phase 3 path): returns plain ``str`` — the v4
      absolute-threshold body. Backward-compatible with all existing call sites.
    - ``profile=<GenreProfile>`` (Phase 6 path): returns
      ``(label, HysteresisState)`` tuple. Caller threads the state through
      subsequent calls. ``audible=False`` short-circuits to ``'silent'`` and
      commits the hysteresis state immediately (anti-hallucination).
    """
    if profile is None:
        return _classify_phase_v4(curve, audible)

    # Percentile-per-genre path. Lazy-import to avoid cycles.
    from vibemix.state.genre.detector import HysteresisState as _HS
    from vibemix.state.genre.detector import classify_phase_percentile

    if hysteresis_state is None:
        hysteresis_state = _HS()

    if not audible or not curve:
        hysteresis_state.current_label = "silent"
        hysteresis_state.pending_label = None
        hysteresis_state.pending_ticks = 0
        return ("silent", hysteresis_state)

    return classify_phase_percentile(curve, features, profile, hysteresis_state)
