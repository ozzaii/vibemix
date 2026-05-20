# SPDX-License-Identifier: Apache-2.0
"""Phase 53 BRINGUP-03 — port_watcher_task + the REAL single-state callback,
composed (the exact seam ``__main__`` runs).

The two unit-test files prove the pieces in isolation: ``test_watcher.py`` pins
``port_watcher_task`` against a scripted mido; ``test_disconnect_reconnect.py``
pins ``handle_port_change_single_state``. This file proves they WORK TOGETHER —
the real watcher driving the real single-state callback over a scripted device
timeline ``[FLX4] -> [] -> [FLX4]`` — connect -> disconnect (ring cleared) ->
reconnect, with no exception propagating out of ``asyncio.run``.

Reuses the deterministic drive helpers from ``test_watcher.py`` (``_make_scripted_mido``
+ ``_patch_watcher_sleep``). spawn_listener is stubbed so no real port opens.
"""

from __future__ import annotations

import asyncio
import functools
from types import SimpleNamespace

from vibemix.midi import load_profile
from vibemix.midi.state import ControllerState
from vibemix.midi.watcher import port_watcher_task
from vibemix.platform import _midi_common
from vibemix.platform._midi_common import ListenerHolder, handle_port_change_single_state

# Reuse the proven deterministic drive helpers from the watcher unit tests.
from tests.midi.test_watcher import _make_scripted_mido, _patch_watcher_sleep

_PORT = "DDJ-FLX4 USB MIDI"


def _cc(channel: int, control: int, value: int):
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)


def _flx4_profile():
    p = load_profile("pioneer_ddj_flx4")
    assert p is not None
    return p


class _DummyThread:
    def join(self, timeout=None):
        return None


def _make_holder() -> ListenerHolder:
    cs = ControllerState(profile=_flx4_profile())
    fake_mido = SimpleNamespace(get_input_names=lambda: [_PORT])
    return ListenerHolder(
        controller_state=cs,
        listener_thread=None,
        listener_stop=None,
        mido_module=fake_mido,
    )


def test_watcher_drives_single_state_callback_connect_disconnect_reconnect(mocker):
    """Scripted [FLX4] -> [] -> [FLX4] through the REAL watcher + REAL
    single-state callback. Assert the transition sequence
    connected -> disconnected -> connected with is_connected() reflecting each,
    the moves ring cleared on disconnect, and asyncio.run completing cleanly."""
    mocker.patch.object(_midi_common, "spawn_listener", lambda *a, **k: _DummyThread())

    holder = _make_holder()
    fake_mido = _make_scripted_mido([[_PORT], [], [_PORT]])
    stop = asyncio.Event()

    # Spy that records (event_kind, is_connected_after) after each callback call,
    # and injects a move on the FIRST connected sweep so we can prove the move is
    # cleared when the disconnect sweep fires.
    transitions: list[tuple[str, bool]] = []
    real_cb = functools.partial(handle_port_change_single_state, holder)

    def spy(payload):
        kind = payload[0]
        if kind == "connected" and not transitions:
            # First connect — let the callback bind, then inject a move so the
            # next (disconnect) sweep has something stale to clear.
            real_cb(payload)
            holder.controller_state.handle_msg(_cc(0, 19, 110))  # vol_a move
            assert holder.controller_state.moves_since(0.0), "move injected post-connect"
        else:
            real_cb(payload)
        transitions.append((kind, holder.controller_state.is_connected()))

    def on_each(n, timeout):
        if n >= 3:
            stop.set()

    _patch_watcher_sleep(mocker, on_each)

    # No exception must propagate (the watcher swallows callback errors, but a
    # clean run should have none — assert by simply completing).
    asyncio.run(port_watcher_task(stop, spy, fake_mido, poll_seconds=0.05))

    # Sweep 1: [FLX4] present  -> connected(True)
    # Sweep 2: [] empty        -> disconnected(False)
    # Sweep 3: [FLX4] present  -> connected(True)
    assert transitions == [
        ("connected", True),
        ("disconnected", False),
        ("connected", True),
    ], transitions

    # The stale move injected after the first connect was cleared by the
    # disconnect sweep's mark_disconnected (Plan 01 ring-clear), and the final
    # reconnect left a fresh ring + connected state.
    assert holder.controller_state.is_connected() is True
    assert holder.bound_port == _PORT
    assert holder.controller_state.moves_since(0.0) == []
