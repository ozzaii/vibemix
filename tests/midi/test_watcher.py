# SPDX-License-Identifier: Apache-2.0
"""Phase 9 Wave 2 Task 3 — port_watcher_task hot-plug detection.

Pins:
- port_watcher_task is an async coroutine; polls mido.get_input_names()
  every poll_seconds; emits ('connected', port, profile) /
  ('disconnected', port) tuples to the on_change callback.
- Connected event resolves the profile via find_mapping_or_generic
  (real profile for known ports; generic for unknown).
- Unchanged port lists do not re-emit.
- Port swap (a -> b in same window) emits both disconnected for a and
  connected for b.
- stop_event ends the loop within one additional poll cycle.
- Callback exceptions are swallowed; the loop keeps polling.
- get_input_names() raises -> watcher logs and continues (does not crash).

Test pattern follows tests/runtime/test_diag.py — no pytest-asyncio
dependency; uses asyncio.run + mocker.patch for the sleep.
"""

from __future__ import annotations

import asyncio
import inspect

from types import SimpleNamespace

from vibemix.midi.watcher import port_watcher_task


_REAL_SLEEP = asyncio.sleep


# ---------- Helpers ----------


def _make_scripted_mido(scripts: list[list[str]]) -> SimpleNamespace:
    """Builds a fake mido whose get_input_names() returns each list in
    ``scripts`` in order. After the script is exhausted, the last list
    is repeated.
    """
    state = {"calls": 0}

    def _get_input_names():
        i = min(state["calls"], len(scripts) - 1)
        state["calls"] += 1
        return list(scripts[i])

    fake = SimpleNamespace(get_input_names=_get_input_names)
    fake._state = state
    return fake


def _make_raising_mido(exc: Exception) -> SimpleNamespace:
    def _get_input_names():
        raise exc

    return SimpleNamespace(get_input_names=_get_input_names)


def _patch_watcher_sleep(mocker, on_each):
    """Patch ``asyncio.wait_for`` inside vibemix.midi.watcher so each tick
    calls ``on_each`` (which receives the call count). Must be a coroutine.

    The watcher uses asyncio.wait_for(stop_event.wait(), timeout=seconds)
    rather than plain asyncio.sleep, so we patch wait_for to control the
    loop pacing.
    """
    state = {"n": 0}

    async def fake_wait_for(coro, *, timeout):
        # Cancel the stop_event.wait() coroutine so it doesn't leak.
        if hasattr(coro, "close"):
            coro.close()
        state["n"] += 1
        result = on_each(state["n"], timeout)
        if asyncio.iscoroutine(result):
            await result
        else:
            await _REAL_SLEEP(0)
        # Watcher's _wait swallows TimeoutError to mean "timeout fired,
        # stop_event not set" — raise it here unless on_each instructs
        # otherwise via state["raise"].
        if state.get("raise") is None or state["raise"]:
            raise asyncio.TimeoutError

    mocker.patch("vibemix.midi.watcher.asyncio.wait_for", side_effect=fake_wait_for)
    return state


# ---------- Coroutine-shape pin ----------


def test_port_watcher_is_async_function():
    assert inspect.iscoroutinefunction(port_watcher_task)


# ---------- Connected event on first sweep ----------


def test_port_watcher_emits_connected_on_first_sweep_finding_a_port(mocker):
    """Sweep 1: empty. Sweep 2: ['DDJ-FLX4 USB MIDI']. Callback fires with
    ('connected', port, flx4_profile)."""
    fake_mido = _make_scripted_mido([[], ["DDJ-FLX4 USB MIDI"]])
    stop = asyncio.Event()
    events = []

    def callback(payload):
        events.append(payload)

    def on_each(n, timeout):
        if n >= 2:
            stop.set()

    _patch_watcher_sleep(mocker, on_each)

    asyncio.run(port_watcher_task(stop, callback, fake_mido, poll_seconds=0.05))

    # First sweep: empty -> no events. Second sweep: connected.
    assert len(events) == 1
    kind, port, profile = events[0]
    assert kind == "connected"
    assert port == "DDJ-FLX4 USB MIDI"
    assert profile.id == "pioneer_ddj_flx4"


# ---------- Disconnected event ----------


def test_port_watcher_emits_disconnected_when_port_disappears(mocker):
    fake_mido = _make_scripted_mido([["DDJ-FLX4 USB"], []])
    stop = asyncio.Event()
    events = []

    def callback(payload):
        events.append(payload)

    def on_each(n, timeout):
        if n >= 2:
            stop.set()

    _patch_watcher_sleep(mocker, on_each)
    asyncio.run(port_watcher_task(stop, callback, fake_mido, poll_seconds=0.05))

    # Sweep 1: connected. Sweep 2: disconnected.
    kinds = [e[0] for e in events]
    assert "connected" in kinds
    assert "disconnected" in kinds
    disc = [e for e in events if e[0] == "disconnected"][0]
    assert disc[1] == "DDJ-FLX4 USB"
    # Disconnected event has no profile arg.
    assert len(disc) == 2


# ---------- Generic profile for unknown ports ----------


def test_port_watcher_emits_generic_for_unknown_port(mocker):
    fake_mido = _make_scripted_mido([["Bose USB Audio"]])
    stop = asyncio.Event()
    events = []

    def callback(payload):
        events.append(payload)

    def on_each(n, timeout):
        if n >= 1:
            stop.set()

    _patch_watcher_sleep(mocker, on_each)
    asyncio.run(port_watcher_task(stop, callback, fake_mido, poll_seconds=0.05))

    assert len(events) == 1
    kind, port, profile = events[0]
    assert kind == "connected"
    assert port == "Bose USB Audio"
    assert profile.id == "generic_midi"


# ---------- Unchanged sweeps -> no re-emit ----------


def test_port_watcher_does_not_re_emit_for_unchanged_ports(mocker):
    fake_mido = _make_scripted_mido([["DDJ-FLX4"]])
    stop = asyncio.Event()
    events = []

    def callback(payload):
        events.append(payload)

    def on_each(n, timeout):
        if n >= 3:
            stop.set()

    _patch_watcher_sleep(mocker, on_each)
    asyncio.run(port_watcher_task(stop, callback, fake_mido, poll_seconds=0.05))

    # Same list 3+ sweeps in a row -> exactly ONE connected event.
    connecteds = [e for e in events if e[0] == "connected"]
    assert len(connecteds) == 1
    assert connecteds[0][1] == "DDJ-FLX4"


# ---------- Port swap ----------


def test_port_watcher_distinguishes_port_swap(mocker):
    fake_mido = _make_scripted_mido([["port_a"], ["port_b"]])
    stop = asyncio.Event()
    events = []

    def callback(payload):
        events.append(payload)

    def on_each(n, timeout):
        if n >= 2:
            stop.set()

    _patch_watcher_sleep(mocker, on_each)
    asyncio.run(port_watcher_task(stop, callback, fake_mido, poll_seconds=0.05))

    # Sweep 1: connected port_a. Sweep 2: disconnected port_a + connected port_b.
    kinds = [(e[0], e[1]) for e in events]
    assert ("connected", "port_a") in kinds
    assert ("disconnected", "port_a") in kinds
    assert ("connected", "port_b") in kinds


# ---------- Poll cadence respect ----------


def test_port_watcher_passes_poll_seconds_to_wait(mocker):
    """The watcher must use the configured poll_seconds as the wait timeout
    on every tick — verifies that hot-plug latency stays bounded."""
    fake_mido = _make_scripted_mido([[]])
    stop = asyncio.Event()
    timeouts: list[float] = []

    def callback(payload):
        pass

    def on_each(n, timeout):
        timeouts.append(timeout)
        if n >= 3:
            stop.set()

    _patch_watcher_sleep(mocker, on_each)
    asyncio.run(port_watcher_task(stop, callback, fake_mido, poll_seconds=2.0))

    assert all(t == 2.0 for t in timeouts), f"expected 2.0s, got {timeouts}"


# ---------- stop_event ends the loop ----------


def test_port_watcher_stops_on_stop_event(mocker):
    fake_mido = _make_scripted_mido([[]])
    stop = asyncio.Event()
    events = []
    state = {"ticks": 0}

    def callback(payload):
        events.append(payload)

    def on_each(n, timeout):
        state["ticks"] = n
        if n == 1:
            stop.set()

    _patch_watcher_sleep(mocker, on_each)
    asyncio.run(port_watcher_task(stop, callback, fake_mido, poll_seconds=0.05))

    # The loop ran exactly 1 sleep tick after stop_event was set.
    assert state["ticks"] == 1


# ---------- Callback exceptions are swallowed ----------


def test_port_watcher_swallows_callback_exceptions(mocker, capsys):
    """A callback that raises must not break the watcher loop — the next
    sweep continues normally."""
    fake_mido = _make_scripted_mido([["DDJ-FLX4"], ["DDJ-FLX4", "XDJ-RX3"]])
    stop = asyncio.Event()
    events = []

    def callback(payload):
        events.append(payload)
        raise RuntimeError("boom")

    def on_each(n, timeout):
        if n >= 2:
            stop.set()

    _patch_watcher_sleep(mocker, on_each)
    asyncio.run(port_watcher_task(stop, callback, fake_mido, poll_seconds=0.05))

    # Both connected events fired; second sweep was not blocked by first
    # callback's exception.
    connected_ports = [e[1] for e in events if e[0] == "connected"]
    assert "DDJ-FLX4" in connected_ports
    assert "XDJ-RX3" in connected_ports
    err = capsys.readouterr().err
    assert "[port watcher callback err]" in err


# ---------- get_input_names() raising ----------


def test_port_watcher_swallows_get_input_names_exception(mocker, capsys):
    """If mido.get_input_names() raises, the watcher logs to stderr and
    continues polling (does not crash the loop)."""
    state = {"calls": 0}

    def _get_input_names():
        state["calls"] += 1
        if state["calls"] == 1:
            raise OSError("simulated mido failure")
        return ["DDJ-FLX4"]

    fake_mido = SimpleNamespace(get_input_names=_get_input_names)
    stop = asyncio.Event()
    events = []

    def callback(payload):
        events.append(payload)

    def on_each(n, timeout):
        if n >= 2:
            stop.set()

    _patch_watcher_sleep(mocker, on_each)
    asyncio.run(port_watcher_task(stop, callback, fake_mido, poll_seconds=0.05))

    err = capsys.readouterr().err
    assert "[port watcher err]" in err
    # Second iteration succeeded -> connected event fired.
    assert any(e[0] == "connected" and e[1] == "DDJ-FLX4" for e in events)


# ---------- Async callback support ----------


def test_port_watcher_supports_async_callback(mocker):
    """on_change may be either a sync callable returning None or an async
    coroutine — the watcher awaits coroutine returns transparently."""
    fake_mido = _make_scripted_mido([["DDJ-FLX4"]])
    stop = asyncio.Event()
    events = []

    async def async_callback(payload):
        events.append(("async", payload))

    def on_each(n, timeout):
        if n >= 1:
            stop.set()

    _patch_watcher_sleep(mocker, on_each)
    asyncio.run(port_watcher_task(stop, async_callback, fake_mido, poll_seconds=0.05))

    assert len(events) == 1
    flag, payload = events[0]
    assert flag == "async"
    assert payload[0] == "connected"
