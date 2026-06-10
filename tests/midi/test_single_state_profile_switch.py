# SPDX-License-Identifier: Apache-2.0
"""2026-06-10 audit (E-midi findings 2+3) — the single-state hot-plug callback
re-profiles the shared ControllerState for the watcher-resolved profile,
refuses generic-port binding steals, pins the spawned listener to the exact
port, and reports whether an event actually changed the binding (the
composition hook for __main__'s MidiMirror envelopes).

Reuses the holder/stub pattern from tests/midi/test_disconnect_reconnect.py
so no real mido port opens.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

from vibemix.midi import load_profile
from vibemix.midi.generic import make_generic_profile
from vibemix.midi.state import ControllerState
from vibemix.platform import _midi_common
from vibemix.platform._midi_common import (
    ListenerHolder,
    handle_port_change_single_state,
    make_single_state_on_change,
)

_FLX4_PORT = "DDJ-FLX4 USB MIDI"
_INPULSE_PORT = "DJControl Inpulse 500"


def _cc(channel, control, value):
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)


def _profile(profile_id):
    p = load_profile(profile_id)
    assert p is not None
    return p


class _RecordingSpawn:
    """spawn_listener stub that records (profile, stop_event) per call."""

    def __init__(self):
        self.calls = []

    def __call__(self, controller_state, stop_event, profile, mido_module):
        self.calls.append((profile, stop_event))
        return SimpleNamespace(join=lambda timeout=None: None)


def _make_holder() -> ListenerHolder:
    cs = ControllerState(profile=_profile("pioneer_ddj_flx4"))
    fake_mido = SimpleNamespace(get_input_names=lambda: [])
    return ListenerHolder(
        controller_state=cs,
        listener_thread=None,
        listener_stop=None,
        mido_module=fake_mido,
    )


def test_connect_rebinds_decode_to_watcher_resolved_profile(monkeypatch):
    """FLX4-built state + Inpulse-500 plug -> the Inpulse's (ch=1, cc=4)
    eq_low_a decodes (it is NOT an FLX4 binding), through the SAME object."""
    spawn = _RecordingSpawn()
    monkeypatch.setattr(_midi_common, "spawn_listener", spawn)
    holder = _make_holder()
    orig_id = id(holder.controller_state)

    applied = handle_port_change_single_state(
        holder, ("connected", _INPULSE_PORT, _profile("hercules_inpulse_500"))
    )

    assert applied is True
    assert id(holder.controller_state) == orig_id  # single-state preserved
    holder.controller_state.handle_msg(_cc(1, 4, 2))  # eq_low_a flat->killed
    assert holder.controller_state.moves_since(0.0), (
        "Inpulse-500 binding must decode after rebind — the FLX4 lookup drops it"
    )


def test_spawned_listener_is_pinned_to_the_exact_port(monkeypatch):
    spawn = _RecordingSpawn()
    monkeypatch.setattr(_midi_common, "spawn_listener", spawn)
    holder = _make_holder()

    handle_port_change_single_state(
        holder, ("connected", _INPULSE_PORT, _profile("hercules_inpulse_500"))
    )

    assert len(spawn.calls) == 1
    profile, stop = spawn.calls[0]
    assert profile.port_name_hints == (_INPULSE_PORT,)
    assert profile.id == "hercules_inpulse_500"
    assert isinstance(stop, threading.Event)


def test_generic_port_binds_when_nothing_is_bound(monkeypatch):
    spawn = _RecordingSpawn()
    monkeypatch.setattr(_midi_common, "spawn_listener", spawn)
    holder = _make_holder()

    applied = handle_port_change_single_state(
        holder, ("connected", "IAC Driver Bus 1", make_generic_profile())
    )

    assert applied is True
    assert holder.bound_port == "IAC Driver Bus 1"
    # The generic profile carries no port_name_hints — exact-port pinning is
    # what makes it bindable at all.
    assert spawn.calls[0][0].port_name_hints == ("IAC Driver Bus 1",)
    holder.controller_state.handle_msg(_cc(5, 77, 100))
    assert holder.controller_state.moves_since(0.0), "generic positional decode active"


def test_generic_port_never_steals_a_live_curated_binding(monkeypatch):
    spawn = _RecordingSpawn()
    monkeypatch.setattr(_midi_common, "spawn_listener", spawn)
    holder = _make_holder()
    handle_port_change_single_state(
        holder, ("connected", _FLX4_PORT, _profile("pioneer_ddj_flx4"))
    )
    flx4_stop = holder.listener_stop

    applied = handle_port_change_single_state(
        holder, ("connected", "IAC Driver Bus 1", make_generic_profile())
    )

    assert applied is False
    assert holder.bound_port == _FLX4_PORT
    assert holder.listener_stop is flx4_stop and not flx4_stop.is_set()
    assert len(spawn.calls) == 1  # no second spawn
    holder.controller_state.handle_msg(_cc(0, 19, 110))  # vol_a still FLX4-decoded
    assert holder.controller_state.moves_since(0.0)


def test_replug_stops_old_listener_and_spawns_fresh_one(monkeypatch):
    """Finding 3 — unplug sets the old listener's stop event; replug spawns a
    NEW listener with a NEW stop event (the callback-mode loop has no port
    liveness check, so the watcher owns the restart)."""
    spawn = _RecordingSpawn()
    monkeypatch.setattr(_midi_common, "spawn_listener", spawn)
    holder = _make_holder()

    handle_port_change_single_state(
        holder, ("connected", _FLX4_PORT, _profile("pioneer_ddj_flx4"))
    )
    first_stop = spawn.calls[0][1]

    assert handle_port_change_single_state(holder, ("disconnected", _FLX4_PORT)) is True
    assert first_stop.is_set(), "old listener told to stop on unplug"

    assert (
        handle_port_change_single_state(
            holder, ("connected", _FLX4_PORT, _profile("pioneer_ddj_flx4"))
        )
        is True
    )
    assert len(spawn.calls) == 2
    second_stop = spawn.calls[1][1]
    assert second_stop is not first_stop and not second_stop.is_set()
    assert holder.bound_port == _FLX4_PORT
    assert holder.controller_state.is_connected() is True


def test_noop_events_return_false(monkeypatch):
    spawn = _RecordingSpawn()
    monkeypatch.setattr(_midi_common, "spawn_listener", spawn)
    holder = _make_holder()
    handle_port_change_single_state(
        holder, ("connected", _FLX4_PORT, _profile("pioneer_ddj_flx4"))
    )

    assert (
        handle_port_change_single_state(
            holder, ("connected", _FLX4_PORT, _profile("pioneer_ddj_flx4"))
        )
        is False
    ), "repeat connect for the bound port"
    assert (
        handle_port_change_single_state(holder, ("disconnected", "Some Other Device")) is False
    ), "disconnect of an unrelated port"


def test_make_single_state_on_change_gates_hook_on_applied(monkeypatch):
    spawn = _RecordingSpawn()
    monkeypatch.setattr(_midi_common, "spawn_listener", spawn)
    holder = _make_holder()
    seen: list[tuple] = []
    on_change = make_single_state_on_change(holder, on_applied=seen.append)

    on_change(("connected", _FLX4_PORT, _profile("pioneer_ddj_flx4")))  # applied
    on_change(("connected", _FLX4_PORT, _profile("pioneer_ddj_flx4")))  # repeat: no-op
    on_change(("disconnected", "Some Other Device"))  # unrelated: no-op
    on_change(("connected", "IAC Driver Bus 1", make_generic_profile()))  # steal blocked
    on_change(("disconnected", _FLX4_PORT))  # applied

    assert [e[0] for e in seen] == ["connected", "disconnected"]
    assert seen[0][1] == _FLX4_PORT and seen[1][1] == _FLX4_PORT
