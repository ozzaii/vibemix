# SPDX-License-Identifier: Apache-2.0
"""Drum & Bass chain — bass/drop structure without Hard Tek overlays.

The useful live moments in D&B / jungle / neurofunk are bass arrivals,
breakdown kick kills, re-entry lands, and phrase boundaries. Do not reuse the
Hard Tek overlays: acid/distortion climbs are not a safe default just because
the BPM is high.
"""

from __future__ import annotations

from vibemix.state.detectors import (
    BreakdownKickKillDetector,
    PhraseBoundaryDetector,
    ReentryKickLandDetector,
    SubLayerArrivalDetector,
)


def build_drum_and_bass_chain() -> list:
    """Return the D&B detector chain — bass arrival + paired drop structure."""
    sub = SubLayerArrivalDetector()
    kill = BreakdownKickKillDetector()
    reentry = ReentryKickLandDetector(kill_detector=kill)
    phrase = PhraseBoundaryDetector(kill_detector=kill)
    return [sub, kill, reentry, phrase]
