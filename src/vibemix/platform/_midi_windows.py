# SPDX-License-Identifier: Apache-2.0
"""MidiWindows — MidiBackend impl for Windows via mido + python-rtmidi.

Near-copy of MidiMacOS — mido + python-rtmidi are cross-platform, so the only
Windows-specific difference is the class name + module location (the platform
selector in ``vibemix.platform.__init__`` dispatches by ``sys.platform``). Wave
1 already extracted the listener-thread body into ``_midi_common.py``; Wave 4
ships the thin Windows wrapper that:

1. Imports ``ControllerState`` + ``_MidoPortAdapter`` verbatim from
   ``_midi_macos`` (the v4 DDJ-FLX4 decoder + Phase 1 ``MidiPort`` adapter
   are OS-agnostic; they happen to live in the macOS file post-Wave-1).
2. Delegates ``start_listener_thread`` to ``_midi_common.spawn_listener``
   with ``(controller_state, stop_event, "DDJ-FLX4", mido)`` args.
3. Exposes ``_PORT_HINT = "DDJ-FLX4"`` as a class attribute for Phase 9
   swap-out (curated 10-controller library).

Why ``ControllerState`` is imported across the macOS/Windows split (rather than
duplicated):
    Wave 1 left the v4 DDJ-FLX4 maps + ControllerState in ``_midi_macos.py``
    rather than moving them to ``_midi_common.py`` — to keep Wave 1's surface
    minimal. Wave 4 imports them across the OS split because the decoder is
    genuinely OS-agnostic. Phase 9 may move the maps into a controller-profile
    module under ``vibemix.controllers/``; for now this cross-file import is
    the simplest correct shape.

Critical Constraint 3 note: the Phase 1 firewall test (``test_no_os_leaks``)
exempts underscore-prefixed concrete-impl files from the no-top-level-OS-import
rule. ``mido`` is cross-platform (works on darwin via CoreMIDI and win32 via
winmm once ``python-rtmidi`` is installed) — it's safe to import at module top
with the standard ``_HAS_MIDO`` guard, mirroring ``_midi_macos.py`` exactly.

No-mido graceful fallback: matches MidiMacOS — ``list_input_ports() -> []``,
``open_input(...) -> RuntimeError``, ``start_listener_thread(...) -> inert
started-then-exited daemon thread``. Callers can ``.join()`` on the returned
thread without special-casing the no-mido path.

Phase 9 expands the controller library + adds hot-plug re-enumeration; Wave 4
ships the FLX4 baseline for Windows-side feature parity with macOS. Phase 20
runs ``tests/test_midi_windows_live.py`` against a real DDJ-FLX4 plugged into
Kaan's Windows machine for end-to-end smoke validation.
"""

from __future__ import annotations

import sys
import threading

try:
    import mido

    _HAS_MIDO = True
except ImportError:
    mido = None  # type: ignore[assignment]
    _HAS_MIDO = False

# Phase 9 Wave 1: ControllerState now hosted in ``vibemix.midi.state`` — the
# OS-agnostic decoder + magnitude-aware MidiEvent emission. ``_MidoPortAdapter``
# still lives in ``_midi_macos`` (the cross-file import is harmless; the adapter
# is OS-agnostic).
from vibemix.midi import load_profile
from vibemix.midi.state import ControllerState
from vibemix.platform._midi_macos import _MidoPortAdapter
from vibemix.platform.midi import MidiPort

# NOTE: ``_midi_common`` is imported lazily inside ``start_listener_thread``
# below — top-level ``from vibemix.platform import _midi_common`` would re-enter
# the package ``__init__.py`` (which on win32 imports ``_midi_windows`` itself)
# and risk a circular-import deadlock. Lazy import sidesteps the cycle entirely
# (mirrors the pattern in ``_midi_macos.py``).


class MidiWindows:
    """MidiBackend impl wrapping ``mido`` + the v4 ControllerState (reused
    verbatim from ``_midi_macos``).

    Public surface (matches MidiMacOS for cross-platform parity):
    - ``controller_state`` — ``ControllerState`` instance; state_refresh_loop
      reads via ``.deck_snapshot()`` + ``.moves_since(t)`` directly.
    - ``list_input_ports() -> list[str]`` — proxies ``mido.get_input_names()``;
      returns ``[]`` when mido is missing.
    - ``open_input(name) -> MidiPort`` — wraps ``mido.open_input(name)`` in a
      ``_MidoPortAdapter``; raises ``RuntimeError`` when mido is missing.
    - ``start_listener_thread(stop_event) -> threading.Thread`` — delegates to
      ``_midi_common.spawn_listener`` with the DDJ-FLX4 port hint and the
      module-top ``mido``. Returns the started daemon thread so callers can
      ``.join(timeout=...)`` on shutdown.

    Phase 9 Wave 1 Task 3: the ``_PORT_HINT`` class attribute was removed —
    port hints now derive from the bound ControllerProfile's
    ``port_name_hints`` tuple (``("DDJ-FLX4", "FLX4")`` for the default FLX4
    profile). Wave 2 makes profile selection dynamic via
    ``find_mapping(port_name)`` once the hot-plug watcher fires.
    """

    def __init__(self) -> None:
        self.controller_state = ControllerState(profile=load_profile("pioneer_ddj_flx4"))

    def list_input_ports(self) -> list[str]:
        if not _HAS_MIDO:
            return []
        return list(mido.get_input_names())

    def open_input(self, port_name: str) -> MidiPort:
        if not _HAS_MIDO:
            raise RuntimeError("mido not installed; cannot open MIDI input")
        port = mido.open_input(port_name)
        return _MidoPortAdapter(port, port_name)

    def start_listener_thread(self, stop_event: threading.Event) -> threading.Thread:
        """Spawn the DDJ-FLX4 listener via ``_midi_common.spawn_listener``.

        Phase 7 Wave 4 contract: zero new listener code in this file. The full
        device-enumerate + open-input + poll-loop body lives in
        ``vibemix.platform._midi_common.midi_listener_thread`` (Phase 7 Wave 1
        extracted from the macOS impl). This method injects the
        Windows-side ``mido`` module + the FLX4 ControllerProfile (Phase 9
        Wave 1 Task 3 — port hints derive from
        ``profile.port_name_hints = ("DDJ-FLX4", "FLX4")``).

        Returns:
            The started ``threading.Thread`` (daemon=True). Callers may
            ``.join(timeout=...)`` on shutdown; without mido installed,
            returns an inert thread that exits immediately.
        """
        if not _HAS_MIDO:
            print("-> mido not installed, MIDI controller disabled", file=sys.stderr)
            # Return an inert started-then-exited thread so callers can
            # ``.join()`` without special-casing the no-mido path.
            t = threading.Thread(
                target=lambda: None,
                name="midi-listener-windows-noop",
                daemon=True,
            )
            t.start()
            return t

        # Lazy import — see module-top note about avoiding the package
        # ``__init__.py`` re-entry cycle. ``_midi_common.spawn_listener`` is
        # the Wave 1 helper that wraps ``midi_listener_thread`` in a daemon
        # ``threading.Thread`` and starts it.
        from vibemix.platform import _midi_common

        return _midi_common.spawn_listener(
            self.controller_state,
            stop_event,
            load_profile("pioneer_ddj_flx4"),
            mido,
        )

    def start_port_watcher(
        self,
        stop_event,
        on_change=None,
        *,
        poll_seconds: float = 2.0,
    ):
        """Spawn the asyncio port_watcher_task as a background task on the
        running event loop. Mirrors ``MidiMacOS.start_port_watcher``.

        Phase 9 Wave 2 Task 3 — Windows-side hot-plug detection. Same
        contract as macOS: polls ``mido.get_input_names()`` every
        ``poll_seconds`` seconds; emits connected / disconnected events to
        the production ``handle_port_change`` callback (which restarts the
        listener thread on hot-plug).

        Args:
            stop_event: ``asyncio.Event`` cooperative shutdown signal.
            on_change: callback for the watcher. If None, builds a default
                production callback bound to a ListenerHolder.
            poll_seconds: sweep cadence (default 2.0 per CONTEXT).

        Returns:
            The ``asyncio.Task`` running the watcher coroutine.
        """
        # Lazy imports — see module-top note about avoiding cycles.
        import asyncio
        import functools

        from vibemix.midi.watcher import port_watcher_task
        from vibemix.platform import _midi_common

        if on_change is None:
            holder = _midi_common.ListenerHolder(
                controller_state=self.controller_state,
                listener_thread=None,
                listener_stop=None,
                mido_module=mido,
                bound_port=None,
            )
            on_change = functools.partial(_midi_common.handle_port_change, holder)
            self._watcher_holder = holder  # retain so callers can introspect

        return asyncio.get_event_loop().create_task(
            port_watcher_task(
                stop_event,
                on_change,
                mido,
                poll_seconds=poll_seconds,
            )
        )


__all__ = ["MidiWindows"]
