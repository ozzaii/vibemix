# SPDX-License-Identifier: Apache-2.0
"""Phase 17 SENSE-12 — kick-side cross-genre detector subpackage.

Each detector lives in its own module so the SENSE-15 ``GenreRouter`` (Plan 05)
can register/swap them atomically per active genre. Shared band-limited DSP
primitives live in ``_dsp.py`` (the ``_impl/`` shared-primitives sibling per
SENSE-15 dispatch architecture).

Detectors are READ-ONLY consumers of ``MusicState`` — Phase 3 single-writer
invariant is preserved (only ``state_refresh_loop._tick_once`` writes inside
``state._lock``).

Wave 2 ships three of the six baseline detectors (re-exports added by Tasks 2-3):
    - ``KickSwapDetector``        — within-track kick character change (centroid shift)
    - ``SubLayerArrivalDetector`` — sub bass / 808 arrival on stable BPM
    - ``KickDensityShiftDetector`` — half-time → 4-on-floor regime change

Wave 2 Plan 03 will add:
    - ``BreakdownKickKillDetector``
    - ``ReentryKickLandDetector``
    - ``PhraseBoundaryDetector``
"""

from __future__ import annotations

from vibemix.state.detectors.kick_density_shift import KickDensityShiftDetector
from vibemix.state.detectors.kick_swap import KickSwapDetector
from vibemix.state.detectors.sub_layer_arrival import SubLayerArrivalDetector

__all__: list[str] = [
    "KickDensityShiftDetector",
    "KickSwapDetector",
    "SubLayerArrivalDetector",
]
