# SPDX-License-Identifier: Apache-2.0
"""vibemix.state — single source of truth for the live DJ session.

This package is THE sensing + state layer ported from cohost_v4.py:1005-1751.

- ``MusicState`` (music_state.py) is the mutable, lock-protected dataclass written
  ONCE every 100ms by ``state_refresh_loop`` (refresh.py — wave 4) and read by
  ``EventDetector`` (event_detector.py — wave 2) and ``AICoach`` (coach.py — wave 3).
- ``classify_phase`` (phase.py) is kept as a free function so Phase 6 can swap in
  the percentile-per-genre detector without touching the class hierarchy.
- ``derive_audible_deck`` + ``derive_audible_track`` (track_resolver.py) are the
  v4 deck-weight + track-cross-reference ladders — pure functions, no I/O.

Wave layout:
- Wave 1 (this commit): MusicState + classify_phase + derive_audible_deck/track
- Wave 2: Event + EventDetector
- Wave 3: AICoach
- Wave 4: state_refresh_loop (the 10Hz single writer)

- (Phase 6) Genre-aware extensions in vibemix.state.genre.* — re-exported here:
  GenreProfile + load_profile/list_profiles/set_active_profile/get_active_profile,
  classify_phase_percentile + HysteresisState, crest_factor + EmaSmoother,
  validate_bpm, VocalDetector.
"""

from __future__ import annotations

from vibemix.state.coach import AICoach
from vibemix.state.event import Event
from vibemix.state.event_detector import EventDetector
from vibemix.state.genre import (
    EmaSmoother,
    GenreProfile,
    HysteresisState,
    VocalDetector,
    classify_phase_percentile,
    crest_factor,
    get_active_profile,
    list_profiles,
    load_profile,
    set_active_profile,
    validate_bpm,
)
from vibemix.state.music_state import MusicState
from vibemix.state.phase import classify_phase
from vibemix.state.refresh import state_refresh_loop
from vibemix.state.track_resolver import derive_audible_deck, derive_audible_track

__all__ = [
    "AICoach",
    "EmaSmoother",
    "Event",
    "EventDetector",
    "GenreProfile",
    "HysteresisState",
    "MusicState",
    "VocalDetector",
    "classify_phase",
    "classify_phase_percentile",
    "crest_factor",
    "derive_audible_deck",
    "derive_audible_track",
    "get_active_profile",
    "list_profiles",
    "load_profile",
    "set_active_profile",
    "state_refresh_loop",
    "validate_bpm",
]
