# SPDX-License-Identifier: Apache-2.0
"""MidiMacOS — MidiBackend implementation for macOS via ``mido`` + python-rtmidi.

Phase 9 Wave 1 extraction: the v4 ``_CC_MAP`` / ``_NOTE_MAP`` constants and
the ``ControllerState`` / ``_knob_label`` / ``_xfader_label`` decoder body
have moved to ``vibemix.midi.state`` (canonical source of truth) and
``vibemix.midi.profiles/pioneer_ddj_flx4.json`` (declarative mapping). This
file is now a thin wrapper that:

1. Re-exports ``ControllerState`` / ``MidiEvent`` / ``_knob_label`` /
   ``_xfader_label`` from ``vibemix.midi.state`` so legacy imports
   (``from vibemix.platform._midi_macos import ControllerState``) keep working
   for Phase 7 downstream tests + state_refresh_loop call sites.
2. Instantiates ``MidiMacOS().controller_state = ControllerState(profile=
   load_profile('pioneer_ddj_flx4'))`` — Wave 2 makes this dynamic via
   ``find_mapping(port_name)`` once the hot-plug watcher fires (Wave 3).
3. Hosts the ``_MidoPortAdapter`` Phase-1 MidiPort wrapper (cross-OS — also
   imported by ``_midi_windows`` for the same reason).

KNOWN ISSUE (still — Phase 9 docket): Pioneer DDJ-FLX4 play-state
propagation. When djay Pro is the active controlling app, the FLX4 firmware
sometimes consumes play presses locally without forwarding ``note_on`` to
other listeners. ``deck['play']`` stays at boot-default ``False`` →
``derive_audible_deck`` returns ``"none"`` → ``derive_audible_track``
confidence capped at ``0.3`` → ``TRACK_CHANGE`` event never fires. Tracked
for Phase 9 follow-up — likely cross-reference with nowplaying-cli's
playback-state, IAC port if available, or audio-side "deck has signal energy"
fallback.

Phase 7 Wave 1: the listener-thread body lives in
``vibemix.platform._midi_common``; ``start_listener_thread`` delegates to
``_midi_common.spawn_listener``. (Task 3 of Wave 1 swaps the third arg from
the legacy ``port_hint: str`` to a ``ControllerProfile`` — this method's
internal call is updated in Task 3.)
"""

from __future__ import annotations

import sys
import threading
import time  # noqa: F401 — re-exported for backward compat: Phase 7's golden

# test (tests/test_midi_common.py::test_midi_macos_golden_unchanged_behavior_after_refactor)
# patches "vibemix.platform._midi_macos.time.time" to pin the moves_since
# timestamps. Keeping `time` importable from this module preserves that mock
# target. The actual decoder body lives in vibemix.midi.state and patches
# there via "vibemix.midi.state.time.time".

try:
    import mido

    _HAS_MIDO = True
except ImportError:
    mido = None  # type: ignore[assignment]
    _HAS_MIDO = False

from vibemix.midi import load_profile

# Re-export shim — Phase 9 Wave 1 moved ControllerState + MidiEvent + the v4
# label helpers to vibemix.midi.state. The legacy import path stays a shim so
# Phase 7 downstream tests + state_refresh_loop call sites keep working.
from vibemix.midi.state import (  # noqa: F401  (re-export)
    ControllerState,
    MidiEvent,
    _knob_label,
    _xfader_label,
)
from vibemix.platform.midi import MidiMessage, MidiPort

# NOTE: ``_midi_common`` is imported lazily inside ``start_listener_thread``
# below — top-level ``from vibemix.platform import _midi_common`` would re-enter
# the package ``__init__.py`` (which imports ``_midi_macos`` itself) and risk a
# circular-import deadlock. Lazy import sidesteps the cycle entirely.


class _MidoPortAdapter:
    """Wraps ``mido.IOPort`` to satisfy the Phase 1 ``MidiPort`` Protocol.

    Phase 1 Protocol requires: ``name: str``, ``poll() -> MidiMessage | None``,
    ``close() -> None``. mido provides ``poll`` and ``close`` directly; we just
    pin ``name`` as an attribute. Cross-OS — ``_midi_windows`` imports this
    class verbatim (mido is itself cross-OS).
    """

    def __init__(self, port, name: str):
        self._port = port
        self.name = name

    def poll(self) -> MidiMessage | None:
        return self._port.poll()

    def close(self) -> None:
        self._port.close()


class MidiMacOS:
    """MidiBackend impl wrapping ``mido`` + the canonical ControllerState
    (now hosted in ``vibemix.midi.state``).

    Exposes:
    - ``controller_state`` — ``ControllerState`` instance (FLX4 profile by
      default; Wave 2 makes selection dynamic). state_refresh_loop reads via
      ``.deck_snapshot()`` and ``.moves_since(t)`` directly.
    - ``list_input_ports()`` / ``open_input(name)`` — Phase 1 Protocol surface.
    - ``start_listener_thread(stop_event)`` — spawns the v4 daemon thread for
      DDJ-FLX4 polling. Returns the Thread for ``join()`` on shutdown.
    """

    def __init__(self):
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
        """Spawn the v4 daemon thread. Retries every 2s on disconnect.

        Phase 7 Wave 1: the listener body lives in
        ``vibemix.platform._midi_common.midi_listener_thread``; this method
        injects the macOS ``mido`` module + the FLX4 ControllerProfile
        (Phase 9 Wave 1 Task 3 — port hints derive from
        ``profile.port_name_hints``: ``("DDJ-FLX4",)``).

        Wave 2 swaps the static FLX4 profile for dynamic ``find_mapping(
        port_name)`` resolution once the hot-plug watcher fires.
        """
        if not _HAS_MIDO:
            print("-> mido not installed, MIDI controller disabled", file=sys.stderr)
            t = threading.Thread(target=lambda: None, name="midi-listener-noop", daemon=True)
            t.start()
            return t

        # Lazy import — see top-of-file note about avoiding the package
        # ``__init__.py`` re-entry cycle.
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
        running event loop.

        Phase 9 Wave 2 Task 3 — exposes hot-plug detection on macOS. Polls
        ``mido.get_input_names()`` every ``poll_seconds`` seconds; emits
        connected / disconnected events to ``on_change`` (default:
        ``functools.partial(handle_port_change, holder)`` wired by Phase 4
        ``__main__.py`` — the production callback restarts the listener
        thread on hot-plug). For unit tests + lower-level callers, pass any
        callable accepting a ``(kind, port, profile)`` / ``(kind, port)``
        tuple.

        Args:
            stop_event: ``asyncio.Event`` cooperative shutdown signal.
            on_change: callback for the watcher. If None, builds a default
                production callback bound to a ListenerHolder seeded from
                the current ``self.controller_state``.
            poll_seconds: sweep cadence (default 2.0 per CONTEXT).

        Returns:
            The ``asyncio.Task`` running the watcher coroutine.
        """
        # Lazy imports — see top-of-file note about avoiding cycles.
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
