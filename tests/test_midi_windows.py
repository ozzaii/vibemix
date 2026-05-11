# SPDX-License-Identifier: Apache-2.0
"""MidiWindows tests — Protocol satisfaction + listener-thread integration.

Pins:
- Module imports cleanly on macOS without requiring Windows-only deps (mido +
  python-rtmidi are cross-platform — top-level import is fine, the firewall
  guard exempts underscore-prefixed concrete-impl files).
- ``MidiWindows()`` structurally satisfies the Phase 1 ``MidiBackend`` Protocol.
- ``MidiWindows.controller_state`` is a ``ControllerState`` instance (the SAME
  class as ``MidiMacOS`` — reused verbatim via cross-file import). This is the
  "no decoder drift between OSes" gate: if the import wiring is wrong,
  ``isinstance`` fails immediately.
- ``MidiWindows._PORT_HINT == "DDJ-FLX4"`` — locked per CONTEXT Decisions
  §MidiWindows. Phase 9 will swap this for the curated controller library.
- ``start_listener_thread`` delegates to ``vibemix.platform._midi_common.spawn_listener``
  with ``(controller_state, stop_event, "DDJ-FLX4", mido)`` args.
- ``list_input_ports`` proxies to ``mido.get_input_names()``; ``open_input``
  wraps ``mido.open_input(name)`` in a ``_MidoPortAdapter`` (reused verbatim
  from ``_midi_macos`` — same Protocol-satisfying shape).
- No-mido graceful fallback: ``list_input_ports() == []`` and
  ``start_listener_thread`` returns a started-then-exited daemon thread (no
  crash, callers can ``.join()`` without special-casing).
- Byte-identical decoder behavior vs. ``MidiMacOS`` — feeding the same MIDI
  message sequence into both backends' ``controller_state`` yields equal
  ``deck_snapshot`` outputs. Proves the cross-file ``ControllerState`` import
  in ``_midi_windows`` is wired correctly.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.platform import MidiBackend
from vibemix.platform._midi_macos import ControllerState, _MidoPortAdapter
from vibemix.platform._midi_windows import MidiWindows


# ---------- Module import discipline ----------


def test_module_imports_on_macos():
    """``from vibemix.platform._midi_windows import MidiWindows`` must succeed
    on darwin. mido + python-rtmidi are cross-platform; the firewall guard
    exempts underscore-prefixed concrete-impl files from the no-OS-leak rule.
    """
    # Import succeeded at the top of this test module — assertion is the
    # presence of the symbol after that import.
    assert MidiWindows is not None
    assert callable(MidiWindows)


# ---------- Protocol satisfaction ----------


def test_midi_windows_satisfies_protocol():
    """structural ``isinstance`` check — MidiWindows must satisfy the
    @runtime_checkable MidiBackend Protocol on every platform."""
    assert isinstance(MidiWindows(), MidiBackend) is True


def test_midi_windows_exposes_controller_state():
    """state_refresh_loop reads via ``controller_state.deck_snapshot()`` and
    ``.moves_since(t)`` directly — must be a ControllerState instance reused
    verbatim from _midi_macos (no Windows-side fork)."""
    backend = MidiWindows()
    assert isinstance(backend.controller_state, ControllerState)


def test_controller_state_is_imported_from_midi_macos():
    """The IMPORT IDENTITY check — MidiWindows must reuse the exact
    ControllerState class object from _midi_macos (not subclass, not duplicate).

    This pins that any future Phase-9 refactor that moves ControllerState into
    a shared module (e.g. _midi_common or vibemix.controllers) updates BOTH
    backends in lock-step; if the import drifts, this test fails.
    """
    from vibemix.platform._midi_macos import ControllerState as MacControllerState
    from vibemix.platform._midi_windows import ControllerState as WinControllerState

    assert MacControllerState is WinControllerState


# ---------- _PORT_HINT locked ----------


def test_midi_windows_default_port_hint_is_ddj_flx4():
    """Locked per CONTEXT Decisions §MidiWindows — DDJ-FLX4 is the v1
    baseline on both OSes. Phase 9 expands the controller library."""
    assert MidiWindows._PORT_HINT == "DDJ-FLX4"
    # Class attribute (not instance) so Phase 9 subclasses / instantiation
    # variants can override without mutating instances.
    assert isinstance(MidiWindows._PORT_HINT, str)


# ---------- start_listener_thread delegates to _midi_common.spawn_listener ----------


def test_start_listener_thread_calls_spawn_listener(monkeypatch):
    """``MidiWindows.start_listener_thread`` MUST call
    ``_midi_common.spawn_listener(controller_state, stop_event, "DDJ-FLX4", mido)``
    exactly once and return its result. Wave 4 contract: zero new listener
    code in _midi_windows; full delegation to the cross-platform Wave 1
    helper."""
    from vibemix.platform import _midi_common, _midi_windows

    fake_thread = MagicMock(spec=threading.Thread)
    spy = MagicMock(return_value=fake_thread)
    monkeypatch.setattr(_midi_common, "spawn_listener", spy)

    backend = _midi_windows.MidiWindows()
    stop_event = threading.Event()
    result = backend.start_listener_thread(stop_event)

    assert result is fake_thread
    spy.assert_called_once()
    args, kwargs = spy.call_args
    # spawn_listener(controller_state, stop_event, port_hint, mido_module)
    assert args[0] is backend.controller_state
    assert args[1] is stop_event
    assert args[2] == "DDJ-FLX4"
    # The 4th positional must be the mido module the impl imported at top.
    assert args[3] is _midi_windows.mido


# ---------- list_input_ports + open_input proxy mido ----------


def test_list_input_ports_proxies_to_mido(monkeypatch):
    """``MidiWindows.list_input_ports()`` returns ``mido.get_input_names()``
    coerced to ``list``. Test injects a fake by patching the ``mido`` symbol
    on the module."""
    from vibemix.platform import _midi_windows

    fake_mido = SimpleNamespace(
        get_input_names=lambda: ("DDJ-FLX4 USB MIDI", "Other Port"),
    )
    monkeypatch.setattr(_midi_windows, "mido", fake_mido)
    monkeypatch.setattr(_midi_windows, "_HAS_MIDO", True)

    backend = _midi_windows.MidiWindows()
    out = backend.list_input_ports()

    assert out == ["DDJ-FLX4 USB MIDI", "Other Port"]
    assert isinstance(out, list)


def test_open_input_wraps_mido_port_in_adapter(monkeypatch):
    """``MidiWindows.open_input(name)`` must call ``mido.open_input(name)``
    and wrap the result in a ``_MidoPortAdapter`` (Phase 1 MidiPort Protocol
    surface — name + poll + close)."""
    from vibemix.platform import _midi_windows

    fake_port = MagicMock()
    open_calls: list[str] = []

    def _open_input(name):
        open_calls.append(name)
        return fake_port

    fake_mido = SimpleNamespace(open_input=_open_input)
    monkeypatch.setattr(_midi_windows, "mido", fake_mido)
    monkeypatch.setattr(_midi_windows, "_HAS_MIDO", True)

    backend = _midi_windows.MidiWindows()
    result = backend.open_input("DDJ-FLX4 USB MIDI")

    assert isinstance(result, _MidoPortAdapter)
    assert result.name == "DDJ-FLX4 USB MIDI"
    assert open_calls == ["DDJ-FLX4 USB MIDI"]


# ---------- No-mido graceful fallback ----------


def test_list_input_ports_returns_empty_without_mido(monkeypatch):
    """When mido isn't installed, ``list_input_ports()`` returns ``[]``
    (matches MidiMacOS pattern — no exception, just degraded surface)."""
    from vibemix.platform import _midi_windows

    monkeypatch.setattr(_midi_windows, "mido", None)
    monkeypatch.setattr(_midi_windows, "_HAS_MIDO", False)

    backend = _midi_windows.MidiWindows()
    assert backend.list_input_ports() == []


def test_open_input_raises_without_mido(monkeypatch):
    """When mido isn't installed, ``open_input`` raises ``RuntimeError`` with
    a clear message — opening a port without the backend installed is a hard
    error (matches MidiMacOS pattern)."""
    from vibemix.platform import _midi_windows

    monkeypatch.setattr(_midi_windows, "mido", None)
    monkeypatch.setattr(_midi_windows, "_HAS_MIDO", False)

    backend = _midi_windows.MidiWindows()
    with pytest.raises(RuntimeError, match="mido"):
        backend.open_input("DDJ-FLX4")


def test_start_listener_thread_returns_noop_thread_without_mido(monkeypatch):
    """No-mido fallback: ``start_listener_thread`` must return a started-
    then-exited daemon thread so callers can ``.join()`` without special-
    casing the no-mido path. Mirrors MidiMacOS behavior verbatim."""
    from vibemix.platform import _midi_windows

    monkeypatch.setattr(_midi_windows, "mido", None)
    monkeypatch.setattr(_midi_windows, "_HAS_MIDO", False)

    backend = _midi_windows.MidiWindows()
    stop_event = threading.Event()
    t = backend.start_listener_thread(stop_event)

    assert isinstance(t, threading.Thread)
    assert t.daemon is True
    t.join(timeout=1.0)
    assert not t.is_alive()


# ---------- Byte-identical decoder vs. MidiMacOS ----------


def test_byte_identical_to_macos_for_same_messages():
    """Feed the same v4 DDJ-FLX4 message sequence through both
    ``MidiMacOS().controller_state`` and ``MidiWindows().controller_state``;
    assert ``deck_snapshot()`` outputs are equal byte-for-byte.

    Proves there's no decoder drift between OSes — the ControllerState IS
    literally the same class, reused via cross-file import. If
    ``_midi_windows`` ever forks the decoder, this test fails immediately.
    """
    from vibemix.platform import MidiMacOS

    # Scripted DDJ-FLX4 traffic exercising the four payload categories
    # (mirrors the v4 sequence in tests/test_midi_common.py to keep tests
    # consistent across the wave).
    msgs = [
        SimpleNamespace(type="control_change", channel=0, control=0x0F, value=8),  # A eq_low
        SimpleNamespace(type="control_change", channel=0, control=0x13, value=100),  # A vol
        SimpleNamespace(type="note_on", channel=0, note=0x0B, velocity=127),  # A play
        SimpleNamespace(type="note_on", channel=0, note=0x0C, velocity=127),  # A cue
        SimpleNamespace(type="control_change", channel=6, control=0x1F, value=0),  # xfader full-A
    ]

    mac = MidiMacOS()
    win = MidiWindows()
    for m in msgs:
        mac.controller_state.handle_msg(m)
        win.controller_state.handle_msg(m)

    mac_snap = mac.controller_state.deck_snapshot()
    win_snap = win.controller_state.deck_snapshot()
    assert mac_snap == win_snap, (
        f"controller_state decoder drift between OSes:\n"
        f"  macOS:   {mac_snap}\n"
        f"  Windows: {win_snap}"
    )

    mac_labels = [label for _, label in mac.controller_state.moves_since(0.0)]
    win_labels = [label for _, label in win.controller_state.moves_since(0.0)]
    assert mac_labels == win_labels, (
        f"moves_since labels diverged:\n"
        f"  macOS:   {mac_labels}\n"
        f"  Windows: {win_labels}"
    )
