# SPDX-License-Identifier: Apache-2.0
"""find_mapping — auto-detect controller from MIDI port name.

Case-insensitive substring match against every loaded
``ControllerProfile.port_name_hints``. Phase 9 Wave 1 ships only the FLX4
profile in the registry; Wave 2 adds 9 more (DDJ-400/FLX6/FLX10/1000/SX3 +
XDJ-RX3 + Numark + Hercules-300/500) and the generic-MIDI fallback.

Locked decisions (09-CONTEXT.md §Auto-detection):
- Case-insensitive substring match (no regex, no fuzzy).
- Multiple-match tiebreak: alphabetic profile-id order — deterministic so
  ``find_mapping`` is referentially transparent.
- Returns ``None`` when nothing matches (Wave 2 swaps this for a synthesized
  generic-MIDI profile via the same call site).
"""

from __future__ import annotations

from vibemix.midi.profile import ControllerProfile, list_profiles, load_profile


def find_mapping(port_name: str) -> ControllerProfile | None:
    """Resolve a controller profile by port name (case-insensitive substring).

    Iterates every bundled profile in alphabetic-id order; returns the FIRST
    profile whose ``port_name_hints`` contains a case-insensitive substring
    of ``port_name``. Returns ``None`` when no profile matches OR when
    ``port_name`` is empty / non-str.
    """
    if not port_name or not isinstance(port_name, str):
        return None
    port_lower = port_name.lower()
    # Sort by id for deterministic tiebreak when multiple hints could match.
    for profile_id in sorted(list_profiles()):
        profile = load_profile(profile_id)
        if profile is None:  # defensive — list_profiles is the source of truth
            continue
        for hint in profile.port_name_hints:
            if hint.lower() in port_lower:
                return profile
    return None
