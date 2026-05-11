# SPDX-License-Identifier: Apache-2.0
"""classify_phase — verbatim port of cohost_v4.py:1065-1090.

Free function (not a method) so Phase 6 can swap in a percentile-per-genre
detector without touching MusicState or EventDetector. Constants SILENT_RMS,
LOW_RMS, PEAK_RMS are IMPORTED from ``vibemix.audio.constants`` so retuning
happens in one place (and Phase 6's override mechanism can monkey-patch the
import).

Returns one of seven labels: silent / low / groove / build / drop / peak /
breakdown. ``audible=False`` short-circuits to ``silent`` (anti-hallucination
gate — RMS thresholds are only meaningful when sustained music is playing).
"""

from __future__ import annotations

from vibemix.audio.constants import LOW_RMS, PEAK_RMS, SILENT_RMS


def classify_phase(curve: list, audible: bool) -> str:
    """Phase tag from energy curve. Returns 'silent' if not audible."""
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
