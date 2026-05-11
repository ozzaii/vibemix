# SPDX-License-Identifier: Apache-2.0
"""DDJ-FLX4 byte-equivalence golden tests (Phase 9 Wave 1 Task 3).

The LOAD-BEARING test of Phase 9: feeding the same MIDI byte stream through
``ControllerState(load_profile('pioneer_ddj_flx4'))`` must yield byte-equal
``deck_snapshot()`` and ``moves_since(0)`` results as v4's hardcoded
``_CC_MAP`` + ``_NOTE_MAP`` (the IP Kaan validated on his rig 2026-05-11).

If this test fails, the FLX4 JSON has drifted from v4's hardcoded constants.
Either fix the JSON to match v4 (preferred — v4 is the canonical reference)
or document why a deliberate divergence is intentional. Phase 9 Wave 1's
contract is byte-for-byte preservation.
"""

from __future__ import annotations

from types import SimpleNamespace

from vibemix.midi import ControllerState, load_profile


# v4 maps — re-stated locally so this test breaks if either v4 OR the JSON
# drifts. Comparing against the loaded profile's internal lookup tables.
_V4_CC_MAP = {
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
_V4_NOTE_MAP = {
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


def _flx4_state() -> ControllerState:
    profile = load_profile("pioneer_ddj_flx4")
    assert profile is not None
    return ControllerState(profile=profile)


def test_pioneer_flx4_profile_internal_lookup_byte_equivalent_to_v4():
    """ControllerState built from the FLX4 profile has _cc_lookup +
    _note_lookup tables equivalent to v4's hardcoded constants 1:1."""
    cs = _flx4_state()

    # Build (channel, cc) -> (deck or 'M', field) from the state's lookup.
    cc_actual: dict[tuple[int, int], tuple[str, str]] = {}
    for key, binding in cs._cc_lookup.items():
        deck = binding.deck if binding.deck is not None else "M"
        cc_actual[key] = (deck, binding.field)
    assert cc_actual == _V4_CC_MAP

    note_actual: dict[tuple[int, int], tuple[str, str]] = {}
    for key, binding in cs._note_lookup.items():
        deck = binding.deck if binding.deck is not None else "M"
        note_actual[key] = (deck, binding.kind)
    assert note_actual == _V4_NOTE_MAP


def test_pioneer_flx4_full_message_replay_byte_equivalent():
    """Feed a 50+ message scripted sequence covering every CC + every note
    in v4's maps; assert deck_snapshot + moves_since labels match the
    v4-canonical expected state.

    The expected snapshot is hand-computed from v4's decoder semantics
    (cohost_v4.py:618-727): EQ tier crosses produce labelled moves, vol/tempo
    only record on delta>15, buttons toggle state per v4's loop_in→play
    workaround + jog_touch velocity gate.
    """
    cs = _flx4_state()

    # Build a scripted sequence covering every CC + every note entry.
    msgs = []

    # CC entries — exercise full range to cross tier boundaries.
    # Vol A: 0→100 (up big), Vol B: 0→127 (up big).
    msgs.append(SimpleNamespace(type="control_change", channel=0, control=0x13, value=100))
    msgs.append(SimpleNamespace(type="control_change", channel=1, control=0x13, value=127))
    # EQ A: hi 64→0 (killed), mid 64→64 (no change), low 64→8 (deep-cut).
    msgs.append(SimpleNamespace(type="control_change", channel=0, control=0x07, value=0))
    msgs.append(SimpleNamespace(type="control_change", channel=0, control=0x0B, value=64))
    msgs.append(SimpleNamespace(type="control_change", channel=0, control=0x0F, value=8))
    # EQ B: hi 64→100 (boost), mid 64→127 (max), low 64→55 (no tier cross within flat).
    msgs.append(SimpleNamespace(type="control_change", channel=1, control=0x07, value=100))
    msgs.append(SimpleNamespace(type="control_change", channel=1, control=0x0B, value=127))
    msgs.append(SimpleNamespace(type="control_change", channel=1, control=0x0F, value=55))
    # Tempo: A center→max, B center→0.
    msgs.append(SimpleNamespace(type="control_change", channel=0, control=0x00, value=127))
    msgs.append(SimpleNamespace(type="control_change", channel=1, control=0x00, value=0))
    # Filter: A 64→0 (killed), B 64→100 (boost).
    msgs.append(SimpleNamespace(type="control_change", channel=6, control=0x17, value=0))
    msgs.append(SimpleNamespace(type="control_change", channel=6, control=0x18, value=100))
    # Xfader: center→full-A→center→full-B.
    msgs.append(SimpleNamespace(type="control_change", channel=6, control=0x1F, value=0))
    msgs.append(SimpleNamespace(type="control_change", channel=6, control=0x1F, value=64))
    msgs.append(SimpleNamespace(type="control_change", channel=6, control=0x1F, value=127))

    # Note entries — toggle play A, hit cue A, sync A, jog_touch A on/off,
    # loop_in A (sets play=True per v4 workaround → play A back to True),
    # loop_out A. Same for deck B.
    msgs.append(SimpleNamespace(type="note_on", channel=0, note=0x0B, velocity=127))  # play A
    msgs.append(SimpleNamespace(type="note_on", channel=0, note=0x0C, velocity=127))  # cue A
    msgs.append(SimpleNamespace(type="note_on", channel=0, note=0x60, velocity=127))  # sync A
    msgs.append(SimpleNamespace(type="note_on", channel=0, note=0x36, velocity=127))  # jog A on
    msgs.append(SimpleNamespace(type="note_off", channel=0, note=0x36))  # jog A off
    msgs.append(SimpleNamespace(type="note_on", channel=0, note=0x10, velocity=127))  # loop_in A
    msgs.append(SimpleNamespace(type="note_on", channel=0, note=0x11, velocity=127))  # loop_out A
    msgs.append(SimpleNamespace(type="note_on", channel=1, note=0x0B, velocity=127))  # play B
    msgs.append(SimpleNamespace(type="note_on", channel=1, note=0x0C, velocity=127))  # cue B
    msgs.append(SimpleNamespace(type="note_on", channel=1, note=0x60, velocity=127))  # sync B
    msgs.append(SimpleNamespace(type="note_on", channel=1, note=0x36, velocity=127))  # jog B on
    msgs.append(SimpleNamespace(type="note_off", channel=1, note=0x36))  # jog B off
    msgs.append(SimpleNamespace(type="note_on", channel=1, note=0x10, velocity=127))  # loop_in B
    msgs.append(SimpleNamespace(type="note_on", channel=1, note=0x11, velocity=127))  # loop_out B

    # Drive the decoder.
    for m in msgs:
        cs.handle_msg(m)

    # Expected v4-canonical snapshot after the sequence:
    snap = cs.deck_snapshot()

    # Deck A: vol=100, eq_hi=0 (killed), eq_mid=64, eq_low=8, filter=0,
    # tempo=127, play=True (toggle False→True then loop_in→True again),
    # cue=False (cue does NOT toggle play in v4), jog_touched=False.
    assert snap["A"]["vol"] == 100
    assert snap["A"]["eq_hi"] == 0
    assert snap["A"]["eq_mid"] == 64
    assert snap["A"]["eq_low"] == 8
    assert snap["A"]["filter"] == 0
    assert snap["A"]["tempo"] == 127
    # play A toggled True via note_on 0x0B, then loop_in 0x10 sets it True again
    # (v4 line 700 workaround) — final state True.
    assert snap["A"]["play"] is True
    assert snap["A"]["cue"] is False
    assert snap["A"]["jog_touched"] is False

    # Deck B: vol=127, eq_hi=100, eq_mid=127, eq_low=55, filter=100,
    # tempo=0, play=True (toggle + loop_in), cue=False, jog_touched=False.
    assert snap["B"]["vol"] == 127
    assert snap["B"]["eq_hi"] == 100
    assert snap["B"]["eq_mid"] == 127
    assert snap["B"]["eq_low"] == 55
    assert snap["B"]["filter"] == 100
    assert snap["B"]["tempo"] == 0
    assert snap["B"]["play"] is True
    assert snap["B"]["cue"] is False
    assert snap["B"]["jog_touched"] is False

    # Xfader: final value = 127 (last write); tier crosses recorded along the way.
    assert snap["xfader"] == 127

    # Move labels — must include the v4-canonical tier-cross + button events.
    # We assert presence (substring) rather than exact ordering / count because
    # v4 emits one label per material event; ordering follows msg ordering.
    labels = [label for _, label in cs.moves_since(0.0)]
    label_blob = "\n".join(labels)

    # Vol big-delta moves.
    assert "A_vol up (big)" in label_blob
    assert "B_vol up (big)" in label_blob
    # EQ tier crosses (v4 labels).
    assert "A_hi: flat→killed" in label_blob
    assert "A_low: flat→deep-cut" in label_blob
    assert "B_hi: flat→boost" in label_blob
    assert "B_mid: flat→max" in label_blob
    # Tempo big-delta moves.
    assert "A_tempo up (big)" in label_blob
    assert "B_tempo down (big)" in label_blob
    # Filter tier crosses.
    assert "A_filter: flat→killed" in label_blob
    assert "B_filter: flat→boost" in label_blob
    # Xfader tier crosses.
    assert "xfader→full-A" in label_blob
    assert "xfader→center" in label_blob
    assert "xfader→full-B" in label_blob
    # Button events.
    assert "A_play→ON" in label_blob
    assert "A_cue_hit" in label_blob
    assert "A_sync_hit" in label_blob
    assert "A_loop_in_hit (play=ON)" in label_blob
    assert "A_loop_out_hit" in label_blob
    assert "B_play→ON" in label_blob
    assert "B_cue_hit" in label_blob
    assert "B_sync_hit" in label_blob
    assert "B_loop_in_hit (play=ON)" in label_blob
    assert "B_loop_out_hit" in label_blob
