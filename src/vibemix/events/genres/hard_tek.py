# SPDX-License-Identifier: Apache-2.0
"""Hard Tek chain — techno baseline + 2 genre-specific overlay detectors.

Per Phase 30 (v2.1 — SENSE-17 + SENSE-18): Hard Tek extends the 5 baseline
kick-side + structural detectors with two genre-specific overlays:

    - ``DistortionClimbDetector`` — captures the "wall is getting taller"
      moment where band-limited spectral flatness rises + odd-harmonic
      energy spikes + kick density sustains.
    - ``AcidLineEntryDetector`` — captures TB-303-style formant sweep +
      resonance-rise envelope.

These two NEVER appear in the techno / house chains — they're Hard Tek-
specific musical events. Hard Tek genre detection (Phase 17 SENSE-15) gates
the chain swap; once swapped, the active_genre IS the gate (no per-detector
``if genre != hard_tek`` check needed).

CRITICAL CHAIN ORDER:
    1. ``kill`` MUST come BEFORE ``reentry`` and ``phrase`` so they observe
       the freshly-set ``kill.last_kill_at`` on the same tick.
    2. ``distortion`` + ``acid`` come AFTER the kick-side detectors so a
       single tick where the kick character changes claims that moment as
       KICK_SWAP rather than DISTORTION_CLIMB (anti-double-fire — the
       cooldown gates make this a soft contract, but ordering makes it
       deterministic).
"""

from __future__ import annotations

from vibemix.state.detectors import (
    AcidLineEntryDetector,
    BreakdownKickKillDetector,
    DistortionClimbDetector,
    KickDensityShiftDetector,
    KickSwapDetector,
    PhraseBoundaryDetector,
    ReentryKickLandDetector,
)


def build_hard_tek_chain() -> list:
    """Return the Hard Tek detector chain — 5 kick-side + structural detectors
    plus 2 Hard Tek-specific overlays (DISTORTION_CLIMB + ACID_LINE_ENTRY).
    """
    kick_swap = KickSwapDetector()
    kick_density = KickDensityShiftDetector()
    kill = BreakdownKickKillDetector()
    reentry = ReentryKickLandDetector(kill_detector=kill)
    phrase = PhraseBoundaryDetector(kill_detector=kill)
    distortion = DistortionClimbDetector()
    acid = AcidLineEntryDetector()
    return [kick_swap, kick_density, kill, reentry, phrase, distortion, acid]
