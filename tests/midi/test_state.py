# SPDX-License-Identifier: Apache-2.0
"""ControllerState extraction + magnitude-aware MidiEvent emission tests.

Phase 9 Wave 1 Task 2 — extract ControllerState from `_midi_macos.py` into
`vibemix.midi.state`, parameterize by ControllerProfile, add magnitude-aware
MidiEvent emission ([-1.0, 1.0] axis), preserve v4 byte-equivalence.

Pins:
- ControllerState re-exported from vibemix.midi (and vibemix.midi.state).
- Legacy imports `from vibemix.platform._midi_macos import ControllerState`
  AND `from vibemix.platform._midi_windows import ControllerState` keep working
  via re-export shim.
- Constructor requires a ControllerProfile.
- deck_snapshot keys derive from profile.decks (FLX4 → A, B; synthetic 4-deck
  → A, B, C, D).
- MidiEvent.magnitude semantics: unipolar = (v - prev)/127, bipolar =
  (v - 64)/63 (signed; clamp to [-1.0, 1.0]).
- Buttons emit MidiEvent without magnitude.
- Unmapped CCs are silent.
- v4 byte-equivalence preserved for moves_since(), _knob_label, _xfader_label,
  loop_in→play workaround, jog_touch velocity gate, dedup-within-400ms,
  12s ring trim.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from vibemix.midi import ControllerProfile, ControllerState, MidiEvent, load_profile
from vibemix.midi.profile import ButtonBinding, ControlBinding

# ---------- Helpers ----------


def _cc(channel: int, control: int, value: int):
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)


def _note_on(channel: int, note: int, velocity: int = 127):
    return SimpleNamespace(type="note_on", channel=channel, note=note, velocity=velocity)


def _note_off(channel: int, note: int):
    return SimpleNamespace(type="note_off", channel=channel, note=note, velocity=0)


def _flx4() -> ControllerProfile:
    p = load_profile("pioneer_ddj_flx4")
    assert p is not None
    return p


# ---------- Re-export identity ----------


def test_controller_state_re_exported_from_vibemix_midi():
    from vibemix.midi import ControllerState as MidiControllerState
    from vibemix.midi.state import ControllerState as StateControllerState

    assert MidiControllerState is StateControllerState


def test_legacy_imports_still_work():
    from vibemix.midi.state import ControllerState as CanonicalControllerState
    from vibemix.platform._midi_macos import ControllerState as MacControllerState
    from vibemix.platform._midi_windows import ControllerState as WinControllerState

    assert MacControllerState is CanonicalControllerState
    assert WinControllerState is CanonicalControllerState


# ---------- Construction ----------


def test_controller_state_constructor_requires_profile():
    cs = ControllerState(profile=_flx4())
    assert cs is not None
    with pytest.raises(TypeError) as exc:
        ControllerState()  # type: ignore[call-arg]
    assert "profile" in str(exc.value)


def test_controller_state_decks_match_profile():
    cs = ControllerState(profile=_flx4())
    snap = cs.deck_snapshot()
    assert set(snap.keys()) == {"A", "B", "xfader", "connected"}

    # Synthetic 4-deck profile.
    four_deck = ControllerProfile(
        id="synthetic_4deck",
        display_name="Synthetic 4-Deck",
        port_name_hints=("SYN",),
        decks=("A", "B", "C", "D"),
        controls={},
        buttons={},
    )
    cs4 = ControllerState(profile=four_deck)
    snap4 = cs4.deck_snapshot()
    assert set(snap4.keys()) == {"A", "B", "C", "D", "xfader", "connected"}


# ---------- Magnitude-aware MidiEvent emission ----------


def test_handle_msg_unipolar_eq_emits_magnitude_in_unit_interval():
    cs = ControllerState(profile=_flx4())
    cs.handle_msg(_cc(0, 7, 64))  # eq_hi A 64 → 64 (no change from default 64)
    cs.handle_msg(_cc(0, 7, 127))  # eq_hi A 64 → 127 → mag = 63/127 ≈ 0.496
    events = cs.events_since(0.0)
    cc_events = [e for e in events if e.kind == "cc" and e.field == "eq_hi"]
    assert len(cc_events) >= 1
    last = cc_events[-1]
    assert isinstance(last, MidiEvent)
    assert last.value_raw == 127
    assert last.magnitude is not None
    assert 0.49 < last.magnitude < 0.50


def test_handle_msg_unipolar_eq_emits_negative_magnitude_on_decrease():
    cs = ControllerState(profile=_flx4())
    cs.handle_msg(_cc(0, 7, 64))  # baseline; same as default → no delta
    # Now reset baseline cleanly
    cs.handle_msg(_cc(0, 7, 64))  # delta=0
    cs.handle_msg(_cc(0, 7, 0))  # 64 → 0 → mag = -64/127 ≈ -0.504
    events = [e for e in cs.events_since(0.0) if e.kind == "cc" and e.field == "eq_hi"]
    last = events[-1]
    assert last.magnitude is not None
    assert -0.51 < last.magnitude < -0.50


def test_handle_msg_bipolar_xfader_emits_signed_magnitude():
    cs = ControllerState(profile=_flx4())
    cs.handle_msg(_cc(6, 31, 0))  # full-A → mag ≈ -1.0
    cs.handle_msg(_cc(6, 31, 64))  # center → mag ≈ 0.0
    cs.handle_msg(_cc(6, 31, 127))  # full-B → mag ≈ +1.0

    events = [e for e in cs.events_since(0.0) if e.field == "xfader"]
    assert len(events) == 3
    assert events[0].magnitude is not None and events[0].magnitude <= -1.0
    assert events[1].magnitude is not None and abs(events[1].magnitude) < 0.02
    assert events[2].magnitude is not None and events[2].magnitude >= 1.0
    # Clamped to [-1.0, 1.0].
    for e in events:
        assert e.magnitude is not None
        assert -1.0 <= e.magnitude <= 1.0


def test_handle_msg_bipolar_tempo_emits_signed_magnitude():
    cs = ControllerState(profile=_flx4())
    cs.handle_msg(_cc(0, 0, 64))  # center
    cs.handle_msg(_cc(0, 0, 127))  # +max
    cs.handle_msg(_cc(0, 0, 0))  # -max
    events = [e for e in cs.events_since(0.0) if e.field == "tempo"]
    assert len(events) == 3
    assert abs(events[0].magnitude) < 0.02  # type: ignore[operator]
    assert events[1].magnitude is not None and events[1].magnitude >= 1.0
    assert events[2].magnitude is not None and events[2].magnitude <= -1.0


def test_handle_msg_button_emits_event_without_magnitude():
    cs = ControllerState(profile=_flx4())
    cs.handle_msg(_note_on(0, 11, velocity=127))  # play_a
    events = [e for e in cs.events_since(0.0) if e.kind == "play"]
    assert len(events) == 1
    assert events[0].deck == "A"
    assert events[0].magnitude is None


def test_handle_msg_unmapped_cc_does_not_crash_or_record():
    cs = ControllerState(profile=_flx4())
    snap_before = cs.deck_snapshot()
    cs.handle_msg(_cc(0, 99, 64))  # unmapped CC
    snap_after = cs.deck_snapshot()
    assert snap_before == snap_after
    assert cs.events_since(0.0) == []


# ---------- v4 byte-equivalence preservation ----------


def test_moves_since_v4_byte_equivalent():
    """Mirror the Phase 7 golden sequence — the labels list must match v4 exactly."""
    cs = ControllerState(profile=_flx4())
    msgs = [
        _cc(0, 0x0F, 8),  # A eq_low 64→8 = flat→deep-cut
        _cc(0, 0x13, 100),  # A vol 0→100 = up big
        _note_on(0, 0x0B, velocity=127),  # A play
        _note_on(0, 0x0C, velocity=127),  # A cue
    ]
    for m in msgs:
        cs.handle_msg(m)
    labels = [label for _, label in cs.moves_since(0.0)]
    # These labels are byte-identical to the v4 golden output (Phase 7
    # test_midi_macos_golden_unchanged_behavior_after_refactor).
    assert any("A_low: flat→deep-cut" in lbl for lbl in labels)
    assert any("A_vol up (big)" in lbl for lbl in labels)
    assert any("A_play→ON" in lbl for lbl in labels)
    assert any("A_cue_hit" in lbl for lbl in labels)


def test_v4_knob_label_boundaries_preserved():
    from vibemix.midi.state import _knob_label

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


def test_v4_xfader_label_boundaries_preserved():
    from vibemix.midi.state import _xfader_label

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


def test_handle_msg_loop_in_implicit_play_workaround_preserved():
    cs = ControllerState(profile=_flx4())
    cs.handle_msg(_note_on(0, 16, velocity=127))  # loop_in_a → sets play=True
    assert cs.deck_snapshot()["A"]["play"] is True


def test_handle_msg_jog_touch_velocity_gates_jog_touched():
    cs = ControllerState(profile=_flx4())
    cs.handle_msg(_note_on(0, 54, velocity=127))
    assert cs.deck_snapshot()["A"]["jog_touched"] is True
    cs.handle_msg(_note_off(0, 54))
    assert cs.deck_snapshot()["A"]["jog_touched"] is False
    cs.handle_msg(_note_on(0, 54, velocity=0))
    assert cs.deck_snapshot()["A"]["jog_touched"] is False


def test_dedup_within_400ms_collapses_repeated_label(mocker):
    cs = ControllerState(profile=_flx4())
    mocker.patch("vibemix.midi.state.time.time", return_value=1000.0)
    cs.handle_msg(_cc(6, 31, 0))  # xfader→full-A
    mocker.patch("vibemix.midi.state.time.time", return_value=1000.2)
    cs.handle_msg(_cc(6, 31, 0))
    assert len(cs._moves) == 1


def test_moves_ring_drops_entries_older_than_12s(mocker):
    cs = ControllerState(profile=_flx4())
    mocker.patch("vibemix.midi.state.time.time", return_value=1000.0)
    cs.handle_msg(_cc(6, 31, 0))  # xfader→full-A
    mocker.patch("vibemix.midi.state.time.time", return_value=1015.0)
    cs.handle_msg(_cc(6, 31, 127))  # xfader→full-B; trims older
    assert len(cs._moves) == 1
    assert cs._moves[0][1] == "xfader→full-B"


# ---------- ControlBinding / ButtonBinding lookups built from profile ----------


def test_controller_state_lookup_tables_built_from_profile():
    cs = ControllerState(profile=_flx4())
    # 13 cc entries from FLX4 profile.
    assert len(cs._cc_lookup) == 13
    # 12 note entries.
    assert len(cs._note_lookup) == 12
    # Validate one binding identity.
    binding = cs._cc_lookup[(0, 19)]
    assert isinstance(binding, ControlBinding)
    assert binding.field == "vol" and binding.deck == "A"
    note_binding = cs._note_lookup[(0, 11)]
    assert isinstance(note_binding, ButtonBinding)
    assert note_binding.kind == "play" and note_binding.deck == "A"


# ---------- Phase 9 Wave 2 — mark_disconnected (symmetric to mark_connected) ----------


def test_mark_disconnected_clears_connected_flag():
    cs = ControllerState(profile=_flx4())
    cs.mark_connected("DDJ-FLX4 USB MIDI")
    assert cs.is_connected() is True
    cs.mark_disconnected()
    assert cs.is_connected() is False
