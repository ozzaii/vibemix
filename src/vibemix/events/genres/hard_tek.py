# SPDX-License-Identifier: Apache-2.0
"""Hard Tek chain — same composition as techno.

Per CONTEXT (Phase 17 v2.0): the 6 baseline detectors carry hard_tek too.
The 2 Hard Tek-specific overlay detectors (DISTORTION_CLIMB +
ACID_LINE_ENTRY) are deferred to v2.1.

Per-detector tuning overrides for Hard Tek (tighter cooldowns to keep up
with 140-180 BPM moves) land in Plan 06's ``tune_detectors.py`` harness;
this builder ships the techno-baseline chain. The override mechanism is in
place — Plan 06 will pass ``cooldown_override=`` kwargs (or per-genre
constant lookups) to the detector constructors here without touching the
detector classes themselves.

CRITICAL CHAIN ORDER (same as techno): ``kill`` MUST come BEFORE
``reentry`` and ``phrase`` so they observe the freshly-set
``kill.last_kill_at`` on the same tick.
"""

from __future__ import annotations

from vibemix.state.detectors import (
    BreakdownKickKillDetector,
    KickDensityShiftDetector,
    KickSwapDetector,
    PhraseBoundaryDetector,
    ReentryKickLandDetector,
)


def build_hard_tek_chain() -> list:
    """Return the Hard Tek detector chain — 5 kick-side + structural detectors.

    v2.1 will add DISTORTION_CLIMB + ACID_LINE_ENTRY here. v2.0 ships the
    techno-baseline chain — Hard Tek tracks already get the full grammar
    of kick-side + phrase-boundary detection from the shared chain.
    """
    kick_swap = KickSwapDetector()
    kick_density = KickDensityShiftDetector()
    kill = BreakdownKickKillDetector()
    reentry = ReentryKickLandDetector(kill_detector=kill)
    phrase = PhraseBoundaryDetector(kill_detector=kill)
    return [kick_swap, kick_density, kill, reentry, phrase]
