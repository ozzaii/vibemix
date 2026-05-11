# SPDX-License-Identifier: Apache-2.0
"""vibemix.midi — declarative MIDI controller profiles + the live decoder.

Phase 9 Wave 1 (this commit): ControllerProfile dataclass + JSON loader +
DDJ-FLX4 reference profile. Wave 2 adds 9 more profiles + generic-MIDI
fallback. Wave 3 wires the hot-plug port watcher.

This subpackage is the natural extraction point Phase 7 deferred: the v4
DDJ-FLX4 ``_CC_MAP`` / ``_NOTE_MAP`` constants + ``ControllerState`` decoder
all move out of ``vibemix.platform._midi_macos`` so they can be parameterized
by JSON-defined ControllerProfile objects (instead of hardcoded per-controller
Python). Mirrors the Phase 6 ``vibemix.state.genre`` pattern exactly.

Top-level surface:
- ``ControllerProfile`` — frozen dataclass mirroring the locked JSON schema.
- ``load_profile(name) -> ControllerProfile | None`` — returns None on missing
  JSON file (sentinel for "no controller mapping"); raises ValueError on
  schema drift in a present file.
- ``list_profiles() -> list[str]`` — sorted profile-stem names from the
  bundled ``profiles/*.json`` resource directory.

Tasks 2 + 3 of Wave 1 land:
- ``ControllerState`` (extracted from ``_midi_macos``) + ``MidiEvent`` (Task 2)
- ``find_mapping(port_name) -> ControllerProfile | None`` (Task 3 — registry)
"""

from __future__ import annotations

from vibemix.midi.profile import (
    ButtonBinding,
    ControlBinding,
    ControllerProfile,
    list_profiles,
    load_profile,
)
from vibemix.midi.registry import find_mapping
from vibemix.midi.state import ControllerState, MidiEvent

__all__ = [
    "ButtonBinding",
    "ControlBinding",
    "ControllerProfile",
    "ControllerState",
    "MidiEvent",
    "find_mapping",
    "list_profiles",
    "load_profile",
]
