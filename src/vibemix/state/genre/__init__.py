# SPDX-License-Identifier: Apache-2.0
"""vibemix.state.genre — genre-aware phase detection subpackage.

Phase 6 Wave 1 surface (this file): GenreProfile dataclass + JSON loader +
active-profile singleton.

Later waves extend with: classify_phase_percentile, crest_factor, validate_bpm,
VocalDetector, HysteresisState, EmaSmoother.
"""

from __future__ import annotations

from vibemix.state.genre.profile import (
    GenreProfile,
    get_active_profile,
    list_profiles,
    load_profile,
    set_active_profile,
)

__all__ = [
    "GenreProfile",
    "get_active_profile",
    "list_profiles",
    "load_profile",
    "set_active_profile",
]
