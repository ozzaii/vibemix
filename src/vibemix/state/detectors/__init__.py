# SPDX-License-Identifier: Apache-2.0
"""Phase 17 SENSE-12 / SENSE-14 — kick-side + structural cross-genre detector
subpackage.

Each detector lives in its own module so the SENSE-15 ``GenreRouter`` (Plan 05)
can register/swap them atomically per active genre. Shared band-limited DSP
primitives live in ``_dsp.py`` (kick-side: centroid + sub-share) and
``_phrase_dsp.py`` (phrase-side: band-limited autocorr + downbeat lock +
phrase-length self-similarity) per the SENSE-15 ``_impl/`` shared-primitives
convention.

Detectors are READ-ONLY consumers of ``MusicState`` — Phase 3 single-writer
invariant is preserved (only ``state_refresh_loop._tick_once`` writes inside
``state._lock``).

Wave 2 ships all six baseline detectors:
    - ``KickSwapDetector``            — within-track kick character change (centroid shift)
    - ``SubLayerArrivalDetector``     — sub bass / 808 arrival on stable BPM
    - ``KickDensityShiftDetector``    — half-time → 4-on-floor regime change
    - ``BreakdownKickKillDetector``   — kick disappears mid-track (filter sweep / breakdown)
    - ``ReentryKickLandDetector``     — kick comes back near a downbeat (paired with kill)
    - ``PhraseBoundaryDetector``      — downbeat closes 8/16/32-bar phrase (paired with kill, optional)

Pair contracts:
    - ``ReentryKickLandDetector`` takes a ``BreakdownKickKillDetector``
      instance as a REQUIRED constructor argument and reads its public
      ``.last_kill_at`` attribute on every tick.
    - ``PhraseBoundaryDetector`` takes a ``BreakdownKickKillDetector``
      instance as an OPTIONAL constructor argument; when provided, the
      detector self-corrects its phrase counter on every fresh kill (the
      breakdown IS where the next phrase starts). Plan 05's GenreRouter MAY
      pass ``None`` for genres where kick-kill self-correction isn't
      relevant (e.g. disco / pop).

Plan 17-05's ``GenreRouter`` is responsible for wiring exactly one re-entry
detector per active genre with the matching kill instance — no globals, no
shared mutable state across genre swaps.
"""

from __future__ import annotations

from vibemix.state.detectors.acid_line_entry import AcidLineEntryDetector
from vibemix.state.detectors.breakdown_kick_kill import BreakdownKickKillDetector
from vibemix.state.detectors.distortion_climb import DistortionClimbDetector
from vibemix.state.detectors.kick_density_shift import KickDensityShiftDetector
from vibemix.state.detectors.kick_swap import KickSwapDetector
from vibemix.state.detectors.phrase_boundary import PhraseBoundaryDetector
from vibemix.state.detectors.reentry_kick_land import ReentryKickLandDetector
from vibemix.state.detectors.sub_layer_arrival import SubLayerArrivalDetector

__all__: list[str] = [
    "AcidLineEntryDetector",
    "BreakdownKickKillDetector",
    "DistortionClimbDetector",
    "KickDensityShiftDetector",
    "KickSwapDetector",
    "PhraseBoundaryDetector",
    "ReentryKickLandDetector",
    "SubLayerArrivalDetector",
]
