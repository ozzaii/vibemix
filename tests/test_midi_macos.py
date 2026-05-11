# SPDX-License-Identifier: Apache-2.0
"""MidiMacOS tests — _CC_MAP / _NOTE_MAP byte-equality + ControllerState decode.

Pins:
- _CC_MAP and _NOTE_MAP are byte-identical to v4:582-598 (the LOAD-BEARING
  DDJ-FLX4 controller IP).
- _knob_label and _xfader_label boundaries are byte-identical to v4:601-615.
- ControllerState.handle_msg decodes the 6 message types correctly.
- deck_snapshot returns a deep-copy dict (caller cannot mutate listener state).
- moves_since returns (seconds_ago_rounded, label) — time-relative.
- isinstance(MidiBackend).
"""

from __future__ import annotations

from types import SimpleNamespace

from vibemix.platform import MidiBackend, MidiMacOS
from vibemix.platform._midi_macos import (
    _CC_MAP,
    _NOTE_MAP,
    ControllerState,
    _knob_label,
    _xfader_label,
)

# ---------- Protocol satisfaction ----------


def test_midi_macos_satisfies_protocol():
    assert isinstance(MidiMacOS(), MidiBackend) is True


def test_midi_macos_exposes_controller_state():
    """state_refresh_loop reads via controller_state.deck_snapshot() and
    .moves_since(t) directly — must be exposed."""
    m = MidiMacOS()
    assert isinstance(m.controller_state, ControllerState)


# ---------- Maps byte-equality (LOAD-BEARING DDJ-FLX4 IP) ----------


def test_cc_map_byte_identical_to_v4():
    expected = {
        (0, 0x13): ("A", "vol"),
        (1, 0x13): ("B", "vol"),
        (0, 0x07): ("A", "eq_hi"),
        (1, 0x07): ("B", "eq_hi"),
        (0, 0x0B): ("A", "eq_mid"),
        (1, 0x0B): ("B", "eq_mid"),
        (0, 0x0F): ("A", "eq_low"),
        (1, 0x0F): ("B", "eq_low"),
        (0, 0x00): ("A", "tempo"),
        (1, 0x00): ("B", "tempo"),
        (6, 0x17): ("A", "filter"),
        (6, 0x18): ("B", "filter"),
        (6, 0x1F): ("M", "xfader"),
    }
    assert _CC_MAP == expected


def test_note_map_byte_identical_to_v4():
    expected = {
        (0, 0x0B): ("A", "play"),
        (1, 0x0B): ("B", "play"),
        (0, 0x0C): ("A", "cue"),
        (1, 0x0C): ("B", "cue"),
        (0, 0x60): ("A", "sync"),
        (1, 0x60): ("B", "sync"),
        (0, 0x36): ("A", "jog_touch"),
        (1, 0x36): ("B", "jog_touch"),
        (0, 0x10): ("A", "loop_in"),
        (1, 0x10): ("B", "loop_in"),
        (0, 0x11): ("A", "loop_out"),
        (1, 0x11): ("B", "loop_out"),
    }
    assert _NOTE_MAP == expected


# ---------- Label helpers boundaries ----------


def test_knob_label_boundaries():
    """v4:601-607 — six tiers."""
    assert _knob_label(0) == "killed"
    assert _knob_label(7) == "killed"
    assert _knob_label(8) == "deep-cut"
    assert _knob_label(29) == "deep-cut"
    assert _knob_label(30) == "cut"
    assert _knob_label(54) == "cut"
    assert _knob_label(55) == "flat"
    assert _knob_label(73) == "flat"
    assert _knob_label(74) == "boost"
    assert _knob_label(100) == "boost"
    assert _knob_label(101) == "max"
    assert _knob_label(127) == "max"


def test_xfader_label_boundaries():
    """v4:610-615 — five tiers."""
    assert _xfader_label(0) == "full-A"
    assert _xfader_label(15) == "full-A"
    assert _xfader_label(16) == "A-side"
    assert _xfader_label(47) == "A-side"
    assert _xfader_label(48) == "center"
    assert _xfader_label(80) == "center"
    assert _xfader_label(81) == "B-side"
    assert _xfader_label(112) == "B-side"
    assert _xfader_label(113) == "full-B"
    assert _xfader_label(127) == "full-B"


# ---------- ControllerState construction ----------


def test_controller_state_defaults():
    cs = ControllerState()
    assert cs.deck["A"]["vol"] == 0
    assert cs.deck["A"]["eq_low"] == 64
    assert cs.deck["A"]["play"] is False  # v4 boot default
    assert cs.deck["B"]["vol"] == 0
    assert cs.xfader == 64
    assert cs._moves == []
    assert cs.is_connected() is False


def test_controller_state_mark_connected():
    cs = ControllerState()
    cs.mark_connected("DDJ-FLX4 1234")
    assert cs.is_connected() is True
    assert cs.port_name == "DDJ-FLX4 1234"


# ---------- handle_msg: control_change ----------


def _cc(channel: int, control: int, value: int):
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)


def _note_on(channel: int, note: int, velocity: int = 127):
    return SimpleNamespace(type="note_on", channel=channel, note=note, velocity=velocity)


def _note_off(channel: int, note: int):
    return SimpleNamespace(type="note_off", channel=channel, note=note, velocity=0)


def test_handle_msg_xfader_records_tier_change():
    cs = ControllerState()
    # xfader 64 → 0 (full-A): tier "center" → "full-A" → records.
    cs.handle_msg(_cc(6, 0x1F, 0))
    assert cs.xfader == 0
    assert any("xfader→full-A" in label for _, label in cs._moves)


def test_handle_msg_xfader_no_record_when_tier_unchanged():
    cs = ControllerState()
    # xfader 64 → 70: both "center" tier — no record.
    cs.handle_msg(_cc(6, 0x1F, 70))
    assert cs.xfader == 70
    assert cs._moves == []


def test_handle_msg_vol_records_only_above_15_delta():
    cs = ControllerState()
    cs.deck["A"]["vol"] = 100  # set baseline
    # delta = 14 (< 15 threshold) — NO record.
    cs.handle_msg(_cc(0, 0x13, 114))
    assert cs.deck["A"]["vol"] == 114
    assert cs._moves == []
    # delta = 50 (big) — records with magnitude.
    cs.handle_msg(_cc(0, 0x13, 64))
    assert any("A_vol down (big)" in label for _, label in cs._moves)


def test_handle_msg_eq_low_records_tier_change():
    cs = ControllerState()
    # eq_low starts at 64 ("flat"). Move to 8 ("deep-cut") — tier crossed.
    cs.handle_msg(_cc(0, 0x0F, 8))
    assert cs.deck["A"]["eq_low"] == 8
    assert any("A_low: flat→deep-cut" in label for _, label in cs._moves)


def test_handle_msg_eq_kill_label_uses_killed():
    cs = ControllerState()
    # eq_low 64 → 0 ("killed").
    cs.handle_msg(_cc(0, 0x0F, 0))
    assert any("killed" in label for _, label in cs._moves)


def test_handle_msg_unknown_cc_ignored():
    cs = ControllerState()
    cs.handle_msg(_cc(0, 0xFE, 100))
    assert cs._moves == []


# ---------- handle_msg: note_on ----------


def test_handle_msg_play_toggles_state():
    cs = ControllerState()
    assert cs.deck["A"]["play"] is False
    cs.handle_msg(_note_on(0, 0x0B))
    assert cs.deck["A"]["play"] is True
    assert any("A_play→ON" in label for _, label in cs._moves)
    cs.handle_msg(_note_on(0, 0x0B))
    assert cs.deck["A"]["play"] is False
    assert any("A_play→OFF" in label for _, label in cs._moves)


def test_handle_msg_loop_in_sets_play_true():
    """v4:700 — loop_in implicitly starts play."""
    cs = ControllerState()
    cs.handle_msg(_note_on(0, 0x10))
    assert cs.deck["A"]["play"] is True
    assert any("A_loop_in_hit (play=ON)" in label for _, label in cs._moves)


def test_handle_msg_cue_records_no_state_change():
    cs = ControllerState()
    cs.handle_msg(_note_on(0, 0x0C))
    assert cs.deck["A"]["play"] is False  # no state mutation
    assert any("A_cue_hit" in label for _, label in cs._moves)


def test_handle_msg_sync_records_no_state_change():
    cs = ControllerState()
    cs.handle_msg(_note_on(0, 0x60))
    assert any("A_sync_hit" in label for _, label in cs._moves)


def test_handle_msg_jog_touch_on():
    cs = ControllerState()
    cs.handle_msg(_note_on(0, 0x36, velocity=127))
    assert cs.deck["A"]["jog_touched"] is True
    # No move record for jog_touch
    assert not any("jog_touch" in label for _, label in cs._moves)


def test_handle_msg_jog_touch_off():
    cs = ControllerState()
    cs.deck["A"]["jog_touched"] = True
    cs.handle_msg(_note_off(0, 0x36))
    assert cs.deck["A"]["jog_touched"] is False


def test_handle_msg_loop_out_records():
    cs = ControllerState()
    cs.handle_msg(_note_on(0, 0x11))
    assert any("A_loop_out_hit" in label for _, label in cs._moves)


# ---------- deck_snapshot deep-copy ----------


def test_deck_snapshot_returns_deep_copy():
    cs = ControllerState()
    cs.deck["A"]["vol"] = 100
    snap = cs.deck_snapshot()
    snap["A"]["vol"] = 999  # mutate caller's copy
    assert cs.deck["A"]["vol"] == 100  # listener state unchanged
    assert snap["A"] is not cs.deck["A"]


def test_deck_snapshot_shape():
    cs = ControllerState()
    snap = cs.deck_snapshot()
    assert set(snap.keys()) == {"A", "B", "xfader", "connected"}
    assert snap["xfader"] == 64
    assert snap["connected"] is False


# ---------- moves_since time-relative ----------


def test_moves_since_returns_seconds_ago_relative(mocker):
    cs = ControllerState()
    mocker.patch("vibemix.platform._midi_macos.time.time", return_value=1000.0)
    cs.handle_msg(_cc(6, 0x1F, 0))  # xfader→full-A @ t=1000

    mocker.patch("vibemix.platform._midi_macos.time.time", return_value=1005.0)
    out = cs.moves_since(998.0)
    assert len(out) == 1
    age, label = out[0]
    assert age == 5.0  # rounded to 0.1
    assert "xfader→full-A" in label


def test_moves_since_filters_by_threshold(mocker):
    cs = ControllerState()
    mocker.patch("vibemix.platform._midi_macos.time.time", return_value=1000.0)
    cs.handle_msg(_cc(6, 0x1F, 0))
    mocker.patch("vibemix.platform._midi_macos.time.time", return_value=1100.0)
    out = cs.moves_since(1050.0)  # 1000 < 1050 → filtered
    assert out == []


# ---------- _record_move dedupe + ring trim ----------


def test_record_move_dedupes_within_400ms(mocker):
    cs = ControllerState()
    mocker.patch("vibemix.platform._midi_macos.time.time", return_value=1000.0)
    cs.handle_msg(_cc(6, 0x1F, 0))  # xfader→full-A
    mocker.patch("vibemix.platform._midi_macos.time.time", return_value=1000.2)
    cs.handle_msg(_cc(6, 0x1F, 0))  # same label within 0.4s — dedup'd
    assert len(cs._moves) == 1


def test_record_move_trims_after_12s(mocker):
    cs = ControllerState()
    mocker.patch("vibemix.platform._midi_macos.time.time", return_value=1000.0)
    cs.handle_msg(_cc(6, 0x1F, 0))  # xfader→full-A
    mocker.patch("vibemix.platform._midi_macos.time.time", return_value=1015.0)
    cs.handle_msg(_cc(6, 0x1F, 127))  # xfader→full-B — adds new entry AND trims.
    # First entry (age 15s, > 12s cutoff) is dropped.
    assert len(cs._moves) == 1
    assert cs._moves[0][1] == "xfader→full-B"
