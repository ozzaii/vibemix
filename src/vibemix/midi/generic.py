# SPDX-License-Identifier: Apache-2.0
"""Generic MIDI fallback — when ``find_mapping`` returns None, the watcher binds
to a synthesized ``GENERIC_MIDI`` ControllerProfile so unmapped controllers
still surface positional events to ControllerState + the Coach.

Per 09-CONTEXT.md §Locked Decisions §Generic fallback:

    Any CC becomes a ``{"type": "GENERIC_CC", "cc": N, "value": V,
    "channel": ch}`` event. Coach prompt context for unmapped controllers
    will include "controller is unmapped — magnitude semantics not
    available; reactions limited to track audio + screen" (Phase 10).

Implementation:
    The generic profile carries empty ``controls`` + ``buttons`` dicts. The
    decode path in ``ControllerState.handle_msg`` checks
    ``profile.id == GENERIC_MIDI_ID`` and switches to the positional-decode
    branch (``ControllerState._handle_generic``):

    - Every CC -> ``MidiEvent(kind='generic_cc', field=f'cc_{ch}_{cc}',
      value_raw=v, magnitude=v/127.0)`` + move label
      ``f'cc_{ch}_{cc}->{v} ({pct}%)'``.
    - Every note_on with velocity > 0 -> ``MidiEvent(kind='generic_note',
      field=f'note_{ch}_{n}', value_raw=velocity, magnitude=None)`` +
      move label ``f'note_{ch}_{n}_pressed'``.
    - Note_off / velocity=0 / other message types: silent (graceful
      degradation — the whole point of the generic fallback).

This module is intentionally tiny — only the factory + helpers live here.
The decode logic lives in ``vibemix.midi.state`` so the dispatch boundary
stays in one place.
"""

from __future__ import annotations

from vibemix.midi.profile import ControllerProfile

GENERIC_MIDI_ID = "generic_midi"
GENERIC_MIDI_DISPLAY = "Generic MIDI Controller (unmapped)"
_GENERIC_NOTES = (
    "Unmapped controller — positional decode only; no semantic deck/field "
    "assignment. Coach prompt context will note 'magnitude semantics not "
    "available; reactions limited to track audio + screen'."
)


def make_generic_profile() -> ControllerProfile:
    """Synthesize the generic-MIDI fallback profile.

    Frozen-dataclass equality means repeated calls return value-equal
    instances (and the hash is stable — useful for the watcher's
    last-seen-profile diff).

    Returns a ControllerProfile with:
        - id: 'generic_midi'
        - port_name_hints: () — NEVER matched by find_mapping
          (this profile is only returned by find_mapping_or_generic)
        - decks: ('A', 'B') — default 2-deck assumption; Coach prompt
          context flags that deck assignment is positional only.
        - controls/buttons: {} — empty; the decode path uses the
          GENERIC_MIDI_ID branch in ControllerState.handle_msg.
        - notes: explanatory string for diagnostic surfaces.
    """
    return ControllerProfile(
        id=GENERIC_MIDI_ID,
        display_name=GENERIC_MIDI_DISPLAY,
        port_name_hints=(),
        decks=("A", "B"),
        controls={},
        buttons={},
        notes=_GENERIC_NOTES,
    )


__all__ = [
    "GENERIC_MIDI_DISPLAY",
    "GENERIC_MIDI_ID",
    "make_generic_profile",
]
