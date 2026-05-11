# SPDX-License-Identifier: Apache-2.0
"""Phase 9 Wave 2 Task 2 — Generic-MIDI fallback profile + positional decode.

When `find_mapping(port_name)` returns None (controller not in the curated
10-profile library), the watcher binds to a synthesized `GENERIC_MIDI`
ControllerProfile so the unmapped controller still surfaces positional
events to ControllerState + the Coach.

Pins:
- `make_generic_profile()` returns a frozen ControllerProfile with id
  'generic_midi', empty controls/buttons, decks=('A','B'), notes set.
- `find_mapping_or_generic(port)` returns the real profile on hit,
  the generic profile on miss (NEVER None).
- ControllerState constructs from the generic profile.
- Generic decode emits MidiEvent(kind='generic_cc', field='cc_<ch>_<cc>',
  magnitude=v/127.0) for every CC.
- Generic decode emits MidiEvent(kind='generic_note', field='note_<ch>_<n>',
  magnitude=None) for every note_on (velocity > 0).
- Move ring records label like 'cc_0_42→100 (78%)'.
- Note_off / velocity=0 are silent.
- Unknown message types (pitchwheel, program_change, aftertouch, sysex) are silent.
- Dedup-within-400ms still works.
- `from vibemix.midi import find_mapping_or_generic, make_generic_profile,
  GENERIC_MIDI_ID` works.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from vibemix.midi import (
    ControllerState,
    MidiEvent,
)

# ---------- Helpers ----------


def _cc(channel: int, control: int, value: int):
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)


def _note_on(channel: int, note: int, velocity: int = 127):
    return SimpleNamespace(type="note_on", channel=channel, note=note, velocity=velocity)


def _note_off(channel: int, note: int):
    return SimpleNamespace(type="note_off", channel=channel, note=note, velocity=0)


def _pitchwheel(channel: int, pitch: int = 8000):
    return SimpleNamespace(type="pitchwheel", channel=channel, pitch=pitch)


# ---------- Generic profile factory ----------


def test_make_generic_profile_returns_synthesized_profile():
    from vibemix.midi import make_generic_profile
    from vibemix.midi.profile import ControllerProfile

    g = make_generic_profile()
    assert isinstance(g, ControllerProfile)
    assert g.id == "generic_midi"
    assert g.display_name == "Generic MIDI Controller (unmapped)"
    assert g.port_name_hints == ()  # never matched by find_mapping
    assert g.decks == ("A", "B")
    assert g.controls == {}
    assert g.buttons == {}
    assert isinstance(g.notes, str)
    assert g.notes, "generic profile notes must be non-empty"


def test_make_generic_profile_returns_value_equal_instances():
    from vibemix.midi import make_generic_profile

    a = make_generic_profile()
    b = make_generic_profile()
    assert a == b  # frozen-dataclass equality


# ---------- find_mapping_or_generic ----------


def test_find_mapping_or_generic_returns_real_profile_when_match():
    from vibemix.midi import find_mapping_or_generic

    result = find_mapping_or_generic("DDJ-FLX4 USB MIDI")
    assert result is not None
    assert result.id == "pioneer_ddj_flx4"


def test_find_mapping_or_generic_returns_generic_when_no_match():
    from vibemix.midi import find_mapping_or_generic

    result = find_mapping_or_generic("Bose Bluetooth Speaker")
    assert result is not None
    assert result.id == "generic_midi"


def test_find_mapping_or_generic_never_returns_none_for_empty_port():
    from vibemix.midi import find_mapping_or_generic

    result = find_mapping_or_generic("")
    assert result is not None
    assert result.id == "generic_midi"


# ---------- Re-exports ----------


def test_find_mapping_or_generic_re_exported_from_vibemix_midi():
    from vibemix.midi import (
        GENERIC_MIDI_ID,
        find_mapping_or_generic,
        make_generic_profile,
    )

    assert GENERIC_MIDI_ID == "generic_midi"
    assert callable(find_mapping_or_generic)
    assert callable(make_generic_profile)


# ---------- ControllerState + generic profile ----------


def test_controller_state_with_generic_profile_constructs():
    from vibemix.midi import make_generic_profile

    cs = ControllerState(profile=make_generic_profile())
    snap = cs.deck_snapshot()
    assert set(snap.keys()) == {"A", "B", "xfader", "connected"}
    assert snap["xfader"] == 64
    assert snap["connected"] is False
    assert snap["A"]["vol"] == 0


def test_generic_decode_emits_event_for_any_cc():
    from vibemix.midi import make_generic_profile

    cs = ControllerState(profile=make_generic_profile())
    cs.handle_msg(_cc(channel=0, control=42, value=100))
    events = cs.events_since(0.0)
    cc_events = [e for e in events if e.kind == "generic_cc"]
    assert len(cc_events) == 1
    ev = cc_events[0]
    assert isinstance(ev, MidiEvent)
    assert ev.field == "cc_0_42"
    assert ev.value_raw == 100
    assert ev.magnitude is not None
    assert 0.78 < ev.magnitude < 0.79  # 100/127 ≈ 0.7874
    assert ev.deck is None


def test_generic_decode_records_position_in_moves_ring():
    from vibemix.midi import make_generic_profile

    cs = ControllerState(profile=make_generic_profile())
    cs.handle_msg(_cc(channel=0, control=42, value=100))
    moves = cs.moves_since(0.0)
    assert len(moves) == 1
    _, label = moves[0]
    # Coach-readable label — channel+cc identifier + raw value + magnitude %.
    assert "cc_0_42" in label
    assert "100" in label
    assert "78%" in label


def test_generic_decode_for_note_on_emits_button_event():
    from vibemix.midi import make_generic_profile

    cs = ControllerState(profile=make_generic_profile())
    cs.handle_msg(_note_on(channel=0, note=60, velocity=127))
    events = cs.events_since(0.0)
    note_events = [e for e in events if e.kind == "generic_note"]
    assert len(note_events) == 1
    ev = note_events[0]
    assert ev.field == "note_0_60"
    assert ev.value_raw == 127
    assert ev.magnitude is None  # buttons have no magnitude
    assert ev.deck is None


def test_generic_decode_note_off_is_silent():
    from vibemix.midi import make_generic_profile

    cs = ControllerState(profile=make_generic_profile())
    cs.handle_msg(_note_off(channel=0, note=60))
    assert cs.events_since(0.0) == []
    assert cs.moves_since(0.0) == []


def test_generic_decode_note_on_with_velocity_zero_is_silent():
    """note_on velocity=0 is the standard "release" alias — treat as note_off."""
    from vibemix.midi import make_generic_profile

    cs = ControllerState(profile=make_generic_profile())
    cs.handle_msg(_note_on(channel=0, note=60, velocity=0))
    assert cs.events_since(0.0) == []


def test_generic_decode_dedupes_within_400ms(mocker):
    from vibemix.midi import make_generic_profile

    cs = ControllerState(profile=make_generic_profile())
    mocker.patch("vibemix.midi.state.time.time", return_value=1000.0)
    cs.handle_msg(_cc(channel=0, control=42, value=100))
    mocker.patch("vibemix.midi.state.time.time", return_value=1000.2)
    cs.handle_msg(_cc(channel=0, control=42, value=100))  # same label
    assert len(cs._moves) == 1


def test_generic_decode_does_not_crash_on_unknown_message_type():
    """pitchwheel, program_change, aftertouch, sysex — silent, no event."""
    from vibemix.midi import make_generic_profile

    cs = ControllerState(profile=make_generic_profile())
    cs.handle_msg(_pitchwheel(channel=0, pitch=8000))
    cs.handle_msg(SimpleNamespace(type="program_change", channel=0, program=5))
    cs.handle_msg(SimpleNamespace(type="aftertouch", channel=0, value=64))
    cs.handle_msg(SimpleNamespace(type="sysex", data=(0x7E, 0x7F, 0x06)))
    assert cs.events_since(0.0) == []
    assert cs.moves_since(0.0) == []


def test_generic_decode_handles_multiple_channels_and_ccs():
    """Field name encodes both channel and CC — same CC on different channels
    must yield distinct events."""
    from vibemix.midi import make_generic_profile

    cs = ControllerState(profile=make_generic_profile())
    cs.handle_msg(_cc(channel=0, control=42, value=64))
    cs.handle_msg(_cc(channel=5, control=42, value=64))
    events = [e for e in cs.events_since(0.0) if e.kind == "generic_cc"]
    assert len(events) == 2
    fields = {e.field for e in events}
    assert fields == {"cc_0_42", "cc_5_42"}


# ---------- Pytest marker / pinned import ----------

_ = pytest
