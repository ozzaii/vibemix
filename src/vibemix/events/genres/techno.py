# SPDX-License-Identifier: Apache-2.0
"""Techno chain — all 5 kick-side + structural detectors.

The full grammar of techno structure:
    KickSwap → KickDensityShift → BreakdownKickKill → ReentryKickLand →
    PhraseBoundary

Each detector targets a moment a techno DJ actually responds to:

- ``KickSwapDetector``         — kick CHARACTER changes (clean → distorted,
  soft → punchy) without disturbing rhythm. The thing v4 ``LAYER_ARRIVAL``
  misses (LAYER_ARRIVAL only watches mid/high band jumps).

- ``KickDensityShiftDetector`` — half-time → 4-on-floor regime change. The
  hardstyle moment, or a tribal track shifting to a peak-time kick pattern.

- ``BreakdownKickKillDetector`` — kick disappears mid-track (filter sweep
  or breakdown). The setup for the drop.

- ``ReentryKickLandDetector``  — kick LANDS back near a downbeat after a
  recent kill. The drop. Paired with the kill detector via DI — reads
  ``kill.last_kill_at`` on every tick.

- ``PhraseBoundaryDetector``   — downbeat that closes an 8/16/32-bar
  phrase. Paired with the kill detector for self-correction (the breakdown
  IS where the next phrase starts, per Plan 17-04 self-correction
  protocol).

CRITICAL CHAIN ORDER: ``kill`` MUST come BEFORE ``reentry`` and ``phrase``
in the returned list. Reason: on a single tick where the kill fires, the
reentry/phrase detectors observe the freshly-set ``kill.last_kill_at`` on
the same instance — but ONLY if the chain iterator visits ``kill`` first.
EventDetector iterates the chain in list order on every tick.
"""

from __future__ import annotations

from vibemix.state.detectors import (
    BreakdownKickKillDetector,
    KickDensityShiftDetector,
    KickSwapDetector,
    PhraseBoundaryDetector,
    ReentryKickLandDetector,
)


def build_techno_chain() -> list:
    """Return the techno detector chain — 5 kick-side + structural detectors.

    Pair contracts:
      - ``ReentryKickLandDetector(kill_detector=kill)`` — required dep.
      - ``PhraseBoundaryDetector(kill_detector=kill)`` — optional dep,
        used here so the breakdown self-correction protocol fires.

    Order matters: kill MUST be in the chain BEFORE reentry + phrase.
    """
    kick_swap = KickSwapDetector()
    kick_density = KickDensityShiftDetector()
    kill = BreakdownKickKillDetector()
    reentry = ReentryKickLandDetector(kill_detector=kill)
    phrase = PhraseBoundaryDetector(kill_detector=kill)
    return [kick_swap, kick_density, kill, reentry, phrase]
