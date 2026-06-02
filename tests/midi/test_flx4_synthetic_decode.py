# SPDX-License-Identifier: Apache-2.0
"""Phase 53 BRINGUP-03 — FLX4 synthetic-stream end-to-end decode proof.

This drives a realistic, LIVE-SHAPED multi-control MIDI sequence (deck A/B
volume + EQ + tempo + filter CCs, the crossfader CC, and jog/play/cue/sync
note messages) through a real ControllerState bound to the profiles/ FLX4
profile, and asserts the decode reflects the right per-deck values, the
expected move labels, and typed events with the right kind/deck/field/
magnitude.

It is the DETERMINISTIC ENGINEERING PROXY for Kaan's "moves register" hardware
sign-off: if a real FLX4 sends these exact ch/cc/note bytes (verified against
profiles/pioneer_ddj_flx4.json), the live decode produces these exact results.

Complementary to (NOT a re-run of) test_profile_flx4_golden.py — that pins the
golden byte-equivalence of a small fixed sequence; this exercises a broad
live-shaped stream across every control class.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from vibemix.midi import load_profile
from vibemix.midi.state import ControllerState, MidiEvent

# ---------- mido-shaped message factories (match handle_msg's attr surface) ----------


def _cc(channel: int, control: int, value: int):
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)


def _note_on(channel: int, note: int, velocity: int = 127):
    return SimpleNamespace(type="note_on", channel=channel, note=note, velocity=velocity)


def _note_off(channel: int, note: int):
    return SimpleNamespace(type="note_off", channel=channel, note=note, velocity=0)


def _flx4_state() -> ControllerState:
    profile = load_profile("pioneer_ddj_flx4")
    assert profile is not None
    return ControllerState(profile=profile)


def _labels(cs: ControllerState) -> list[str]:
    return [label for _, label in cs.moves_since(0.0)]


# ---------- The live-shaped decode proof ----------


def test_flx4_synthetic_stream_decodes_end_to_end():
    cs = _flx4_state()
    cs.mark_connected("DDJ-FLX4 USB MIDI")  # explicit: assert connected=True later

    # 1. deck A volume up: ch0 cc19 = vol_a, unipolar, 0 -> 110.
    cs.handle_msg(_cc(0, 19, 110))
    snap = cs.deck_snapshot()
    assert snap["A"]["vol"] == 110
    vol_events = [e for e in cs.events_since(0.0) if e.field == "vol" and e.deck == "A"]
    assert vol_events, "vol_a CC must emit a typed event"
    assert vol_events[-1].kind == "cc"
    assert vol_events[-1].value_raw == 110
    # unipolar magnitude = (110 - 0) / 127 ~ 0.866 (positive direction).
    assert vol_events[-1].magnitude == pytest.approx((110 - 0) / 127.0, abs=1e-3)
    # 0 -> 110 is delta 110 > 15, so a "A_vol up (big)" move is recorded.
    assert any("A_vol up" in lbl for lbl in _labels(cs))

    # 2. deck A EQ low killed: ch0 cc15 = eq_low_a, 64 -> 2 (flat -> killed tier).
    cs.handle_msg(_cc(0, 15, 2))
    assert cs.deck_snapshot()["A"]["eq_low"] == 2
    assert any("A_low:" in lbl and "killed" in lbl for lbl in _labels(cs))

    # 3. deck A tempo nudged: ch0 cc0 = tempo_a, bipolar, default 64 -> 90.
    cs.handle_msg(_cc(0, 0, 90))
    assert cs.deck_snapshot()["A"]["tempo"] == 90
    tempo_events = [e for e in cs.events_since(0.0) if e.field == "tempo" and e.deck == "A"]
    assert tempo_events, "tempo_a CC must emit a typed event"
    # bipolar magnitude = (90 - 64) / 63 ~ 0.413 (positive).
    assert tempo_events[-1].magnitude == pytest.approx((90 - 64) / 63.0, abs=1e-3)
    assert tempo_events[-1].magnitude > 0
    # 64 -> 90 is delta 26 > 15, so an "A_tempo up" move is recorded.
    assert any("A_tempo up" in lbl for lbl in _labels(cs))

    # 4. crossfader to B: ch6 cc31 = xfader (deck None), bipolar, 64 -> 120.
    cs.handle_msg(_cc(6, 31, 120))
    assert cs.deck_snapshot()["xfader"] == 120
    assert any("xfader" in lbl and "full-B" in lbl for lbl in _labels(cs))
    xfader_events = [e for e in cs.events_since(0.0) if e.field == "xfader"]
    assert xfader_events, "xfader CC must emit a typed event"
    assert xfader_events[-1].deck is None

    # 5. jog A touched then released: ch0 note54 = jog_a (jog_touch).
    cs.handle_msg(_note_on(0, 54, velocity=100))
    assert cs.deck_snapshot()["A"]["jog_touched"] is True
    cs.handle_msg(_note_off(0, 54))
    assert cs.deck_snapshot()["A"]["jog_touched"] is False

    # 6. play A pressed: ch0 note11 = play_a (toggles False -> True).
    cs.handle_msg(_note_on(0, 11, velocity=127))
    assert cs.deck_snapshot()["A"]["play"] is True
    assert any("A_play→ON" in lbl for lbl in _labels(cs))
    play_events = [e for e in cs.events_since(0.0) if e.kind == "play" and e.deck == "A"]
    assert play_events and play_events[-1].magnitude is None

    # 7. cue B pressed: ch1 note12 = cue_b.
    cs.handle_msg(_note_on(1, 12, velocity=127))
    assert any("B_cue_hit" in lbl for lbl in _labels(cs))
    cue_events = [e for e in cs.events_since(0.0) if e.kind == "cue" and e.deck == "B"]
    assert cue_events

    # 8. sync A pressed: ch0 note96 = sync_a.
    cs.handle_msg(_note_on(0, 96, velocity=127))
    assert any("A_sync_hit" in lbl for lbl in _labels(cs))

    activity = cs.activity_snapshot()
    assert activity["connected"] is True
    assert activity["messages_seen_total"] >= 8
    assert activity["events_seen_total"] >= 8
    assert activity["moves_seen_total"] >= 7

    # ----- whole-stream invariants -----
    assert cs.deck_snapshot()["connected"] is True  # we called mark_connected
    events = cs.events_since(0.0)
    assert events and all(isinstance(e, MidiEvent) for e in events)
    # Event ids are monotonic (assigned in dispatch order).
    ids = [e.id for e in events]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids), "event ids must be unique + monotonic"


def test_flx4_decode_deck_b_independent_from_deck_a():
    """Deck B controls (channel 1) decode into deck B, leaving deck A defaults
    intact — proves per-deck channel separation in the live profile."""
    cs = _flx4_state()
    cs.handle_msg(_cc(1, 19, 100))  # vol_b
    cs.handle_msg(_cc(1, 7, 120))  # eq_hi_b
    snap = cs.deck_snapshot()
    assert snap["B"]["vol"] == 100
    assert snap["B"]["eq_hi"] == 120
    # Deck A untouched (defaults: vol=0, eq_hi=64).
    assert snap["A"]["vol"] == 0
    assert snap["A"]["eq_hi"] == 64


def test_flx4_decode_live_discovered_b_jog_cc34_variant():
    """The 2026-06-01 FLX4 proof emitted B jog ticks as ch1/CC34.

    The older live-discovered map already keeps ch1/CC33 for B jog. Accepting
    this additive variant keeps hardware jog movement visible to websocket
    snapshots instead of surfacing only the jog-touch note with no move label.
    """
    cs = _flx4_state()

    cs.handle_msg(_cc(1, 0x22, 65))

    events = [e for e in cs.events_since(0.0) if e.field == "jog" and e.deck == "B"]
    assert events
    assert events[-1].kind == "cc"
    assert events[-1].value_raw == 65
    assert events[-1].magnitude == pytest.approx(1.0, abs=1e-3)
    assert "B_jog nudge forward" in _labels(cs)


def test_flx4_decode_unmapped_cc_is_noop():
    """An unmapped CC (ch0 cc99 — not in the FLX4 profile) is a no-op: no deck
    change, no event, no raise."""
    cs = _flx4_state()
    before = cs.deck_snapshot()
    cs.handle_msg(_cc(0, 99, 64))  # not in profile
    after = cs.deck_snapshot()
    assert before == after
    assert cs.events_since(0.0) == []


def test_flx4_decode_malformed_message_does_not_raise():
    """A malformed message (control_change missing the .value attr) is swallowed
    by handle_msg's try/except — the live decode never crashes the listener
    thread on garbage input."""
    cs = _flx4_state()
    bad = SimpleNamespace(type="control_change", channel=0, control=19)  # no .value
    cs.handle_msg(bad)  # must not raise
    # Nothing recorded (the AttributeError is caught before any mutation lands).
    assert cs.events_since(0.0) == []
