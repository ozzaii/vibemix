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

from vibemix.midi.generic import make_generic_profile
from vibemix.midi.profile import ControllerProfile, list_profiles, load_profile


def find_mapping(port_name: str) -> ControllerProfile | None:
    """Resolve a controller profile by port name (case-insensitive substring).

    Iterates every bundled profile, finds every hint that is a
    case-insensitive substring of ``port_name``, and returns the profile
    whose matching hint is LONGEST. Alphabetic profile-id is the tiebreak
    when multiple profiles tie on hint length.

    The longest-hint rule is the Phase 97 / ONBOARD-03 disambiguation —
    sibling profiles like ``hercules_inpulse_300`` and
    ``hercules_inpulse_300_mk2`` carry hints that overlap as substrings
    (the legacy 300's "DJControl Inpulse 300" IS a substring of the MK2's
    "DJControl Inpulse 300 MK2"). Under pure first-match-alphabetic the
    MK2 port would always resolve to the legacy profile. Longest-hint-
    wins picks the more specific profile deterministically and is
    forward-compatible: adding a new sibling SKU only requires extending
    that sibling's hints, never editing the registry.

    Returns ``None`` when no profile matches OR when ``port_name`` is
    empty / non-str.
    """
    if not port_name or not isinstance(port_name, str):
        return None
    port_lower = port_name.lower()
    best: tuple[int, str, ControllerProfile] | None = None  # (hint_len, profile_id, profile)
    for profile_id in sorted(list_profiles()):
        profile = load_profile(profile_id)
        if profile is None:  # defensive — list_profiles is the source of truth
            continue
        # Find the LONGEST matching hint within this profile, then compare
        # against the running best across profiles. Picking the longest hint
        # per-profile first means a profile with both ['MK2', 'DJControl
        # Inpulse 300 MK2'] is scored by its strongest match, not its first
        # one (deterministic regardless of hint-array order).
        profile_best_hint_len = -1
        for hint in profile.port_name_hints:
            hint_lower = hint.lower()
            if hint_lower in port_lower:
                hint_len = len(hint_lower)
                if hint_len > profile_best_hint_len:
                    profile_best_hint_len = hint_len
        if profile_best_hint_len < 0:
            continue  # no hint matched this port
        if best is None or profile_best_hint_len > best[0]:
            best = (profile_best_hint_len, profile_id, profile)
        # Tie on hint length → alphabetic-id tiebreak. The sorted loop
        # order keeps the earlier-id in `best` (strict-greater above).
    return best[2] if best is not None else None


def find_mapping_or_generic(port_name: str) -> ControllerProfile:
    """Like ``find_mapping`` but never returns None — falls back to the
    synthesized ``GENERIC_MIDI`` profile when no curated mapping matches.

    Used by the port watcher when binding to an unknown port. The Coach
    prompt context (Phase 10) will surface "controller is unmapped —
    magnitude semantics not available; reactions limited to track audio
    + screen" when the bound profile is ``generic_midi``.

    Always returns a ControllerProfile (never None). Empty / non-str
    ``port_name`` -> generic profile.
    """
    match = find_mapping(port_name)
    if match is not None:
        return match
    return make_generic_profile()
