# SPDX-License-Identifier: Apache-2.0
"""2026-06-10 audit (E-midi findings 2+3) — MidiMacOS.start_port_watcher
composes the single-state listener manager with __main__'s on_applied hook
and seeds the holder with the boot listener for a clean first-sweep handoff.

mido is monkeypatched at module level so no real CoreMIDI client opens;
spawn_listener is stubbed so no thread starts.
"""

from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

from vibemix.platform import _midi_common
from vibemix.platform._midi_macos import MidiMacOS

_PORT = "DDJ-400"


class _DummyThread:
    def __init__(self):
        self.join_called = False

    def join(self, timeout=None):
        self.join_called = True


def test_start_port_watcher_seeds_holder_and_fires_on_applied(monkeypatch):
    fake_mido = SimpleNamespace(get_input_names=lambda: [_PORT])
    monkeypatch.setattr("vibemix.platform._midi_macos.mido", fake_mido)
    spawned = []

    def fake_spawn(controller_state, stop_event, profile, mido_module):
        spawned.append((profile, stop_event))
        return _DummyThread()

    monkeypatch.setattr(_midi_common, "spawn_listener", fake_spawn)

    backend = MidiMacOS()
    boot_thread = _DummyThread()
    boot_stop = threading.Event()
    applied: list[tuple] = []

    async def run():
        watcher_stop = asyncio.Event()

        def on_applied(event):
            applied.append(event)
            watcher_stop.set()

        task = backend.start_port_watcher(
            watcher_stop,
            on_applied=on_applied,
            listener_thread=boot_thread,
            listener_stop=boot_stop,
            poll_seconds=0.01,
        )
        holder = backend._watcher_holder
        assert holder.listener_thread is boot_thread
        assert holder.listener_stop is boot_stop
        await asyncio.wait_for(task, timeout=5.0)
        return holder

    holder = asyncio.run(run())

    # First sweep: DDJ-400 appeared -> the single-state manager applied it.
    assert applied and applied[0][0] == "connected" and applied[0][1] == _PORT
    assert boot_stop.is_set(), "boot listener handed off (stopped) before respawn"
    assert boot_thread.join_called
    assert holder.bound_port == _PORT
    assert backend.controller_state.is_connected() is True
    # The watcher-resolved DDJ-400 profile drives the fresh listener, pinned
    # to the exact port.
    assert spawned and spawned[0][0].id == "pioneer_ddj_400"
    assert spawned[0][0].port_name_hints == (_PORT,)
