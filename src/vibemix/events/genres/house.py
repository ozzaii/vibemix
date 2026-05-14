# SPDX-License-Identifier: Apache-2.0
"""House chain — SubLayerArrival + PhraseBoundary.

Why these two? House music's defining ear-events:

- The 808 / sub-bass entry — a producer drops the deep low end mid-track,
  or a DJ EQ-restores the bass after a kill. ``SubLayerArrivalDetector``
  catches both with a stable-BPM gate (Plan 17-02) so cross-track sub
  swaps stay owned by ``TRACK_CHANGE`` (anti-double-fire contract
  T-17-02-02).

- Phrase boundaries (8/16/32-bar closes) — house is harmonically rich and
  STRUCTURALLY tight; a DJ planning a blend reaches for the next track on
  the phrase end. ``PhraseBoundaryDetector`` (Plan 17-04) downbeat-locks +
  phrase-counts so the AI can react "we're at the end of the phrase" not
  just "the kick changed".

Why NOT KickSwap / KickDensityShift / BreakdownKickKill / ReentryKickLand?
Because in house, the kick rarely "swaps" in a meaningful way — it's the
backbone, not the message. KickSwap fires would land in 8-bar territory
that house DJs blend through, not on. The kick-side detectors live on the
techno + hard_tek chains where they actually carry information.

PhraseBoundaryDetector here gets ``kill_detector=None`` — house breakdowns
aren't typically kick-killed (they're filter-swept), so the kill-anchored
self-correction protocol (Plan 17-04) isn't useful. The detector falls back
to its pure phrase-counter behavior.
"""

from __future__ import annotations

from vibemix.state.detectors import (
    PhraseBoundaryDetector,
    SubLayerArrivalDetector,
)


def build_house_chain() -> list:
    """Return the house detector chain — SubLayerArrival + PhraseBoundary."""
    sub = SubLayerArrivalDetector()
    # House breakdowns aren't kick-killed; pass None — detector falls back to
    # pure phrase-counter behavior without kill-anchored self-correction.
    phrase = PhraseBoundaryDetector(kill_detector=None)
    return [sub, phrase]
