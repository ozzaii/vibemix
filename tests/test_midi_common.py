# SPDX-License-Identifier: Apache-2.0
"""_midi_common.py tests — cross-platform MIDI listener thread (Phase 7 Wave 1).

The listener body was lifted out of `_midi_macos.py::MidiMacOS.start_listener_thread`
verbatim so that Wave 4's `_midi_windows.py` can reuse it. The function accepts
`mido_module` as a parameter (NOT a top-level import) so unit tests inject a fake
mido and exercise the loop deterministically without an actual MIDI device.

Pins:
- listener finds the substring-matched port (case-insensitive), calls
  `mark_connected`, then dispatches every polled message to `handle_msg` until
  the stop_event is set.
- when no port matches, listener sleeps then retries; no mark_connected, no
  handle_msg.
- when `open_input` raises, listener prints `[midi listener err]` to stderr and
  retries; second iteration succeeds.
- substring match is case-insensitive (port_hint="DDJ-FLX4" matches
  "ddj-flx4 USB MIDI").
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

from vibemix.platform import _midi_common


# ---------- Fake mido module (test injection seam) ----------


class _FakePort:
    """Mimics ``mido.IOPort`` minimum surface used by the listener loop:
    ``poll() -> msg | None`` and context-manager support (``__enter__`` /
    ``__exit__``)."""

    def __init__(self, scripted_msgs: list):
        # scripted_msgs: list of (msg | None) — listener consumes one per poll.
        self._scripted = list(scripted_msgs)
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True
        return False

    def poll(self):
        if not self._scripted:
            return None
        return self._scripted.pop(0)


def _make_fake_mido(
    input_names: list[str],
    port: _FakePort | None = None,
    open_input_raises: Exception | None = None,
):
    """Builds a SimpleNamespace mimicking the mido module surface used by
    `midi_listener_thread`: ``get_input_names()`` and ``open_input(name)``."""
    open_calls: list[str] = []

    def _get_input_names():
        return list(input_names)

    def _open_input(name):
        open_calls.append(name)
        if open_input_raises is not None:
            raise open_input_raises
        return port

    fake = SimpleNamespace(get_input_names=_get_input_names, open_input=_open_input)
    fake._open_calls = open_calls  # test introspection
    return fake


class _RecordingControllerState:
    """Minimal ControllerState stand-in capturing connect + handle calls."""

    def __init__(self):
        self.connected_to: str | None = None
        self.handled: list = []

    def mark_connected(self, name: str):
        self.connected_to = name

    def handle_msg(self, msg):
        self.handled.append(msg)


# ---------- Test 1: happy path — port match + dispatch + clean exit ----------


def test_midi_common_listener_finds_port_and_dispatches(monkeypatch):
    msg = SimpleNamespace(type="control_change", channel=0, control=0x13, value=120)
    port = _FakePort([msg])
    fake_mido = _make_fake_mido(["Foo", "DDJ-FLX4 Bus 1"], port=port)
    cs = _RecordingControllerState()
    stop_event = threading.Event()

    # Short-circuit the inner-loop sleep so the test runs fast.
    monkeypatch.setattr(_midi_common.time, "sleep", lambda _s: None)

    t = _midi_common.spawn_listener(cs, stop_event, "DDJ-FLX4", fake_mido)
    # Give the daemon thread a moment to enumerate, open, poll, dispatch.
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        if cs.handled:
            break
        time.sleep(0.005)
    stop_event.set()
    t.join(timeout=1.0)

    assert cs.connected_to == "DDJ-FLX4 Bus 1"
    assert len(cs.handled) == 1
    assert cs.handled[0] is msg
    assert port.closed is True
    assert not t.is_alive()


# ---------- Test 2: no port match → retry loop, no side effects ----------


def test_midi_common_listener_retries_when_no_port_match(monkeypatch):
    fake_mido = _make_fake_mido([])  # no ports
    cs = _RecordingControllerState()
    stop_event = threading.Event()

    sleep_calls: list[float] = []

    def _record_sleep(seconds):
        sleep_calls.append(seconds)
        # On first sleep call, set the stop event so the loop exits next iteration.
        if len(sleep_calls) >= 1:
            stop_event.set()

    monkeypatch.setattr(_midi_common.time, "sleep", _record_sleep)

    t = _midi_common.spawn_listener(cs, stop_event, "DDJ-FLX4", fake_mido)
    t.join(timeout=1.0)

    assert cs.connected_to is None
    assert cs.handled == []
    assert 2.0 in sleep_calls  # the retry-on-no-match sleep
    assert not t.is_alive()


# ---------- Test 3: open_input exception → swallow + retry ----------


def test_midi_common_listener_swallows_open_input_exception(monkeypatch, capsys):
    cs = _RecordingControllerState()
    stop_event = threading.Event()

    # First iteration: open_input raises. Second iteration: succeeds with a port
    # that immediately polls None (nothing to dispatch), then we set stop_event.
    success_port = _FakePort([])

    iteration = {"n": 0}

    def _get_input_names():
        return ["DDJ-FLX4 Real Device"]

    def _open_input(name):
        iteration["n"] += 1
        if iteration["n"] == 1:
            raise RuntimeError("simulated open failure")
        return success_port

    fake_mido = SimpleNamespace(get_input_names=_get_input_names, open_input=_open_input)

    sleep_calls: list[float] = []

    def _record_sleep(seconds):
        sleep_calls.append(seconds)
        # After second open succeeds and listener enters the inner poll loop
        # (which sleeps 0.005s when poll() returns None), set stop.
        if seconds < 0.01:
            stop_event.set()

    monkeypatch.setattr(_midi_common.time, "sleep", _record_sleep)

    t = _midi_common.spawn_listener(cs, stop_event, "DDJ-FLX4", fake_mido)
    t.join(timeout=2.0)

    captured = capsys.readouterr()
    assert "[midi listener err]" in captured.err
    assert "simulated open failure" in captured.err
    # Second open succeeded — controller marked connected.
    assert cs.connected_to == "DDJ-FLX4 Real Device"
    assert iteration["n"] == 2  # exactly 2 attempts
    assert 2.0 in sleep_calls  # retry-after-exception sleep
    assert not t.is_alive()


# ---------- Test 4: substring match case-insensitive ----------


def test_midi_common_listener_substring_match_case_insensitive(monkeypatch):
    port = _FakePort([])
    fake_mido = _make_fake_mido(["ddj-flx4 USB MIDI"], port=port)
    cs = _RecordingControllerState()
    stop_event = threading.Event()

    sleep_calls: list[float] = []

    def _record_sleep(seconds):
        sleep_calls.append(seconds)
        # Once the inner poll loop's first sleep happens (0.005s), exit.
        if seconds < 0.01:
            stop_event.set()

    monkeypatch.setattr(_midi_common.time, "sleep", _record_sleep)

    t = _midi_common.spawn_listener(cs, stop_event, "DDJ-FLX4", fake_mido)
    t.join(timeout=1.0)

    # Lowercase port name matched the uppercase port_hint.
    assert cs.connected_to == "ddj-flx4 USB MIDI"
    assert fake_mido._open_calls == ["ddj-flx4 USB MIDI"]


# ---------- Test 5: golden — _midi_common produces identical mutations to v4 ----------


def test_midi_macos_golden_unchanged_behavior_after_refactor(monkeypatch):
    """Regression: feeding the same scripted CC sequence through (a) the v4
    `MidiMacOS.controller_state.handle_msg` directly AND (b) through
    `_midi_common.midi_listener_thread` (with a fake mido) yields byte-equal
    `deck_snapshot()` and `moves_since(0)` results.

    Proves the listener-thread extraction preserves Phase 3 byte-identical
    behavior — the v4 ControllerState IP was untouched.
    """
    from vibemix.platform import MidiMacOS

    # Scripted DDJ-FLX4 traffic exercising the four payload categories:
    # - control_change with tier crossing (eq_low 64→8 = flat→deep-cut)
    # - control_change vol with delta > 15 (vol 0→100 = up big)
    # - note_on play (toggles A_play False→True)
    # - note_on cue (records hit, no state change)
    msgs = [
        SimpleNamespace(type="control_change", channel=0, control=0x0F, value=8),  # A eq_low
        SimpleNamespace(type="control_change", channel=0, control=0x13, value=100),  # A vol
        SimpleNamespace(type="note_on", channel=0, note=0x0B, velocity=127),  # A play
        SimpleNamespace(type="note_on", channel=0, note=0x0C, velocity=127),  # A cue
    ]

    # Pin time so moves_since deltas line up.
    monkeypatch.setattr("vibemix.platform._midi_macos.time.time", lambda: 1000.0)

    # Path A: direct handle_msg.
    direct = MidiMacOS()
    for m in msgs:
        direct.controller_state.handle_msg(m)
    direct_snap = direct.controller_state.deck_snapshot()
    direct_moves = direct.controller_state.moves_since(0.0)

    # Path B: through midi_listener_thread.
    via_listener = MidiMacOS()
    port = _FakePort(list(msgs))
    fake_mido = _make_fake_mido(["DDJ-FLX4"], port=port)
    stop_event = threading.Event()

    monkeypatch.setattr(_midi_common.time, "sleep", lambda _s: None)

    # Pump the thread directly (don't spawn — keeps test deterministic).
    # Set stop_event AFTER the messages are exhausted so the inner loop exits
    # on the next None-poll → 0.005s sleep → stop check.
    def _stop_after_drain():
        # Wait until the fake port is fully drained, then stop.
        while port._scripted:
            time.sleep(0.001)
        # one more tick for the listener to finish dispatching the last msg
        time.sleep(0.01)
        stop_event.set()

    drainer = threading.Thread(target=_stop_after_drain, daemon=True)
    drainer.start()

    _midi_common.midi_listener_thread(
        via_listener.controller_state, stop_event, "DDJ-FLX4", fake_mido
    )
    drainer.join(timeout=1.0)

    listener_snap = via_listener.controller_state.deck_snapshot()
    listener_moves = via_listener.controller_state.moves_since(0.0)

    # Strip `connected` field — it differs because the listener path calls
    # mark_connected (True) while the direct path skips it (False). All other
    # fields must match byte-for-byte.
    direct_snap.pop("connected")
    listener_snap.pop("connected")
    assert direct_snap == listener_snap, (
        f"deck_snapshot diverged after refactor:\n"
        f"  direct:   {direct_snap}\n"
        f"  listener: {listener_snap}"
    )
    # Move labels must match (ages may differ by sub-tick if `time.time` shifts;
    # we pinned it above, so labels alone are the cleanest equality check).
    direct_labels = [label for _, label in direct_moves]
    listener_labels = [label for _, label in listener_moves]
    assert direct_labels == listener_labels, (
        f"moves_since diverged after refactor:\n"
        f"  direct:   {direct_labels}\n"
        f"  listener: {listener_labels}"
    )
