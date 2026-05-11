# SPDX-License-Identifier: Apache-2.0
"""vibemix.state.genre — genre-aware phase detection subpackage.

Phase 6 Wave 1: GenreProfile dataclass + JSON loader + active-profile singleton.
Phase 6 Wave 2: crest_factor + EmaSmoother + validate_bpm + VocalDetector.
Phase 6 Wave 3 (this commit): classify_phase_percentile + HysteresisState.
"""

from __future__ import annotations

from vibemix.state.genre.bpm_validator import validate_bpm
from vibemix.state.genre.crest_factor import EmaSmoother, crest_factor
from vibemix.state.genre.detector import HysteresisState, classify_phase_percentile
from vibemix.state.genre.profile import (
    GenreProfile,
    get_active_profile,
    list_profiles,
    load_profile,
    set_active_profile,
)
from vibemix.state.genre.vocal_detector import VocalDetector

__all__ = [
    "EmaSmoother",
    "GenreProfile",
    "HysteresisState",
    "VocalDetector",
    "classify_phase_percentile",
    "crest_factor",
    "get_active_profile",
    "list_profiles",
    "load_profile",
    "set_active_profile",
    "validate_bpm",
]
