# SPDX-License-Identifier: Apache-2.0
"""Phase 53 BRINGUP-03 — disconnect->reconnect integration through the
PRODUCTION single-state callback (handle_port_change_single_state).

This is the deterministic engineering proxy for Kaan's physical FLX4
unplug/replug. It drives the real production callback (not an isolated stub)
through connected -> disconnected -> connected and asserts:

  - on disconnect: is_connected() False, the moves AND events rings are cleared
    (Plan 01's mark_disconnected ring-clear), bound_port None, the SAME
    ControllerState object is preserved (NOT rebuilt — single-state ownership),
    and nothing raises.
  - on reconnect: is_connected() True again, the object identity is STILL the
    original, and decode resumes on a fresh ring.
  - a churn loop (rapid connect/disconnect) leaves the state internally
    consistent with no exception.

spawn_listener is monkeypatched to a dummy so no real MIDI port is opened — the
assertions are about state transitions + object identity, not the listener
thread itself.
"""

from __future__ import annotations

from types import SimpleNamespace

from vibemix.midi import load_profile
from vibemix.midi.state import ControllerState
from vibemix.platform import _midi_common
from vibemix.platform._midi_common import ListenerHolder, handle_port_change_single_state

_PORT = "DDJ-FLX4 USB MIDI"


def _cc(channel: int, control: int, value: int):
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)


def _flx4_profile():
    p = load_profile("pioneer_ddj_flx4")
    assert p is not None
    return p


class _DummyThread:
    """Stand-in for the listener thread — supports join() so the callback's
    teardown path runs without a real thread."""

    def __init__(self):
        self.joined = False

    def join(self, timeout=None):
        self.joined = True


def _make_holder() -> ListenerHolder:
    """A ListenerHolder seeded with a REAL ControllerState (FLX4 profile) + a
    fake mido. spawn_listener is stubbed by the test fixtures so this holder's
    mido_module is never actually opened."""
    cs = ControllerState(profile=_flx4_profile())
    fake_mido = SimpleNamespace(
        get_input_names=lambda: [_PORT],
        open_input=lambda name: SimpleNamespace(
            __enter__=lambda self: self, __exit__=lambda *a: False, poll=lambda: None
        ),
    )
    return ListenerHolder(
        controller_state=cs,
        listener_thread=None,
        listener_stop=None,
        mido_module=fake_mido,
    )


def _stub_spawn_listener(monkeypatch):
    """Replace spawn_listener with a dummy so no real port opens."""
    monkeypatch.setattr(_midi_common, "spawn_listener", lambda *a, **k: _DummyThread())


# ---------- The full disconnect->reconnect cycle ----------


def test_disconnect_reconnect_preserves_single_state_and_clears_rings(monkeypatch):
    _stub_spawn_listener(monkeypatch)
    holder = _make_holder()
    original_id = id(holder.controller_state)

    # 1. Connect.
    handle_port_change_single_state(holder, ("connected", _PORT, _flx4_profile()))
    assert holder.bound_port == _PORT
    assert holder.controller_state.is_connected() is True
    assert id(holder.controller_state) == original_id  # not rebuilt

    # 2. Record real moves + events on the bound state.
    holder.controller_state.handle_msg(_cc(0, 19, 110))  # vol_a up big
    holder.controller_state.handle_msg(_cc(0, 15, 2))  # eq_low_a flat->killed
    assert holder.controller_state.moves_since(0.0), "moves recorded while connected"
    assert holder.controller_state.events_since(0.0), "events recorded while connected"
    assert holder.controller_state.is_connected() is True

    # 3. Disconnect — production callback path.
    handle_port_change_single_state(holder, ("disconnected", _PORT))
    cs = holder.controller_state
    assert cs.is_connected() is False
    assert cs.moves_since(0.0) == [], "moves ring cleared on disconnect (Plan 01)"
    assert cs.events_since(0.0) == [], "events ring cleared on disconnect (Plan 01)"
    assert holder.bound_port is None
    assert id(holder.controller_state) == original_id  # single-state: NOT rebuilt

    # 4. Reconnect — same object, decode resumes on a fresh ring.
    handle_port_change_single_state(holder, ("connected", _PORT, _flx4_profile()))
    assert holder.controller_state.is_connected() is True
    assert id(holder.controller_state) == original_id  # STILL the original
    assert holder.controller_state.moves_since(0.0) == []  # fresh ring after rebind
    holder.controller_state.handle_msg(_cc(0, 19, 90))  # vol_a up big again
    assert holder.controller_state.moves_since(0.0), "decode resumes after reconnect"


def test_disconnect_for_other_port_is_noop(monkeypatch):
    """Disconnecting a port we are NOT bound to must not tear down our state."""
    _stub_spawn_listener(monkeypatch)
    holder = _make_holder()
    handle_port_change_single_state(holder, ("connected", _PORT, _flx4_profile()))

    handle_port_change_single_state(holder, ("disconnected", "Some Other Device"))

    assert holder.bound_port == _PORT
    assert holder.controller_state.is_connected() is True


def test_repeat_connect_same_port_is_noop(monkeypatch):
    """A second connect for the already-bound port must not respawn the listener
    nor re-toggle state."""
    _stub_spawn_listener(monkeypatch)
    holder = _make_holder()
    handle_port_change_single_state(holder, ("connected", _PORT, _flx4_profile()))
    first_stop = holder.listener_stop
    first_thread = holder.listener_thread

    handle_port_change_single_state(holder, ("connected", _PORT, _flx4_profile()))

    assert holder.listener_stop is first_stop
    assert holder.listener_thread is first_thread


# ---------- Churn: rapid alternation stays consistent + never raises ----------


def test_rapid_connect_disconnect_churn_stays_consistent(monkeypatch):
    _stub_spawn_listener(monkeypatch)
    holder = _make_holder()
    original_id = id(holder.controller_state)

    sequence = [
        ("connected", _PORT, _flx4_profile()),
        ("disconnected", _PORT),
        ("connected", _PORT, _flx4_profile()),
        ("disconnected", _PORT),
        ("connected", _PORT, _flx4_profile()),
        ("disconnected", _PORT),
        ("connected", _PORT, _flx4_profile()),
    ]
    for event in sequence:  # must never raise
        handle_port_change_single_state(holder, event)

    # Final event was a connect → consistent: connected True, bound to the port.
    assert holder.controller_state.is_connected() is True
    assert holder.bound_port == _PORT
    # Single-state object preserved across the entire churn.
    assert id(holder.controller_state) == original_id

    # Now end on a disconnect → connected False, bound_port None, rings clear.
    handle_port_change_single_state(holder, ("disconnected", _PORT))
    assert holder.controller_state.is_connected() is False
    assert holder.bound_port is None
    assert holder.controller_state.moves_since(0.0) == []
    assert id(holder.controller_state) == original_id
