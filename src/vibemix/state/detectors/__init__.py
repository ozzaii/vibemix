# SPDX-License-Identifier: Apache-2.0
"""Phase 17 SENSE-12 — kick-side cross-genre detector subpackage.

Each detector lives in its own module so the SENSE-15 ``GenreRouter`` (Plan 05)
can register/swap them atomically per active genre. Shared band-limited DSP
primitives live in ``_dsp.py`` (the ``_impl/`` shared-primitives sibling per
SENSE-15 dispatch architecture).

Detectors are READ-ONLY consumers of ``MusicState`` — Phase 3 single-writer
invariant is preserved (only ``state_refresh_loop._tick_once`` writes inside
``state._lock``).

Wave 2 ships four of the six baseline detectors so far (Plan 17-03 Task 2
adds the fifth, ``ReentryKickLandDetector``):
    - ``KickSwapDetector``            — within-track kick character change (centroid shift)
    - ``SubLayerArrivalDetector``     — sub bass / 808 arrival on stable BPM
    - ``KickDensityShiftDetector``    — half-time → 4-on-floor regime change
    - ``BreakdownKickKillDetector``   — kick disappears mid-track (filter sweep / breakdown)

Wave 2 Plan 03 Task 2 + Plan 04 will add:
    - ``ReentryKickLandDetector``     — kick comes back near a downbeat (paired with kill)
    - ``PhraseBoundaryDetector``      — bar-multiple structural boundary
"""

from __future__ import annotations

from vibemix.state.detectors.breakdown_kick_kill import BreakdownKickKillDetector
from vibemix.state.detectors.kick_density_shift import KickDensityShiftDetector
from vibemix.state.detectors.kick_swap import KickSwapDetector
from vibemix.state.detectors.sub_layer_arrival import SubLayerArrivalDetector

__all__: list[str] = [
    "BreakdownKickKillDetector",
    "KickDensityShiftDetector",
    "KickSwapDetector",
    "SubLayerArrivalDetector",
]
