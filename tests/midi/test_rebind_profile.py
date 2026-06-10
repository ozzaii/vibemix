# SPDX-License-Identifier: Apache-2.0
"""2026-06-10 audit (E-midi finding 2) — ControllerState.rebind_profile.

The single-state hot-plug invariant keeps ONE ControllerState object alive
across the whole session (ws_broadcast / state_refresh_loop / MidiMirror all
capture it once). rebind_profile is the in-place re-profile that lets that
same object decode whichever controller the watcher resolved — without it,
a DDJ-400/Hercules/XDJ user keeps the boot-time FLX4 lookup tables and
decodes nothing.
"""

from __future__ import annotations

from types import SimpleNamespace

from vibemix.midi import load_profile
from vibemix.midi.generic import make_generic_profile
from vibemix.midi.state import ControllerState


def _cc(channel, control, value):
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)


def _profile(profile_id):
    p = load_profile(profile_id)
    assert p is not None
    return p


def _flx4_state() -> ControllerState:
    return ControllerState(profile=_profile("pioneer_ddj_flx4"))


def test_rebind_same_profile_is_a_noop():
    cs = _flx4_state()
    cs.handle_msg(_cc(0, 19, 110))  # vol_a up big — FLX4 binding
    labels_before = [label for _, label in cs.moves_since(0.0)]
    assert labels_before

    cs.rebind_profile(_profile("pioneer_ddj_flx4"))

    assert [label for _, label in cs.moves_since(0.0)] == labels_before, (
        "same-id rebind must not clear anything"
    )
    assert cs.deck_snapshot()["A"]["vol"] == 110, "deck values survive same-controller rebind"


def test_rebind_switches_decode_to_new_profile_bindings():
    cs = _flx4_state()

    cs.rebind_profile(_profile("hercules_inpulse_500"))

    # (ch=1, cc=4) is eq_low_a on the Inpulse-500 and unmapped on the FLX4.
    cs.handle_msg(_cc(1, 4, 2))
    assert cs.moves_since(0.0), "Inpulse-500 binding must decode after rebind"
    events = cs.events_since(0.0)
    assert events and events[-1].field == "eq_low" and events[-1].deck == "A"


def test_rebind_clears_rings_and_resets_positions():
    cs = _flx4_state()
    cs.handle_msg(_cc(0, 19, 110))
    assert cs.moves_since(0.0) and cs.events_since(0.0)

    cs.rebind_profile(_profile("pioneer_ddj_400"))

    assert cs.moves_since(0.0) == [], (
        "controller-A moves must never ground a reaction after controller B binds"
    )
    assert cs.events_since(0.0) == []
    snap = cs.deck_snapshot()
    assert snap["A"]["vol"] == 0 and snap["xfader"] == 64, "positions reset to boot defaults"
    assert cs.control_touched_snapshot()["A"] == ()


def test_rebind_to_generic_switches_to_positional_decode():
    cs = _flx4_state()

    cs.rebind_profile(make_generic_profile())

    cs.handle_msg(_cc(5, 77, 100))  # unmapped anywhere — generic positional decode
    moves = cs.moves_since(0.0)
    assert moves and "cc_5_77" in moves[0][1]
    events = cs.events_since(0.0)
    assert events and events[-1].kind == "generic_cc"


def test_rebind_preserves_on_move_hook_and_monotonic_counters():
    cs = _flx4_state()
    seen: list[str] = []
    cs.on_move = lambda label, ts: seen.append(label)
    cs.handle_msg(_cc(0, 19, 110))
    assert seen
    before = cs.activity_snapshot()["messages_seen_total"]

    cs.rebind_profile(_profile("pioneer_ddj_400"))

    cs.handle_msg(_cc(0, 19, 100))  # vol_a on the DDJ-400 too
    assert len(seen) >= 2, "tracer hook survives rebind"
    assert cs.activity_snapshot()["messages_seen_total"] == before + 1, (
        "counters stay monotonic (no reset)"
    )
