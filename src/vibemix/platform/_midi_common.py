# SPDX-License-Identifier: Apache-2.0
"""Cross-platform MIDI listener thread — extracted from _midi_macos.py.

Phase 7 Wave 1 lifts the device-enumeration + open-input + poll-loop body out of
``MidiMacOS.start_listener_thread`` so Wave 4's ``_midi_windows.py`` can reuse
it verbatim. The listener body is platform-agnostic: ``mido`` works on both
macOS (CoreMIDI) and Windows (winmm) once ``python-rtmidi`` is installed.

Design:
- ``midi_listener_thread`` is a top-level function (NOT a method) — it accepts
  ``controller_state`` (any object with ``mark_connected(name)`` +
  ``handle_msg(msg)`` methods, satisfied by Phase 3's ``ControllerState``) and a
  ``mido_module`` parameter so unit tests inject a fake mido without
  monkeypatching the real one.
- ``spawn_listener`` is the convenience helper: wraps the function in a daemon
  ``threading.Thread``, calls ``.start()``, returns the Thread for ``join()``
  on shutdown.
- The retry-every-2s-on-exception pattern, the substring-case-insensitive port
  match, and the 5ms inner-loop sleep are all carried over verbatim from v4
  (cohost_v4.py:730-756 / Phase 3 _midi_macos.py:302-327) — those tuning values
  were validated in Kaan's real DJ session 2026-05-11 and stay unchanged.

Test injection seam: ``mido_module`` is the third positional parameter so tests
can pass a ``types.SimpleNamespace`` with ``get_input_names()`` and
``open_input(name)`` callables, exercising the loop deterministically without
a physical MIDI device.
"""

from __future__ import annotations

import sys
import threading
import time


def midi_listener_thread(controller_state, stop_event, port_hint, mido_module):
    """Run the MIDI device enumerate-open-poll loop until ``stop_event`` is set.

    Lifted verbatim from ``_midi_macos.py::MidiMacOS.start_listener_thread._run``
    (Phase 3) which was a verbatim port of cohost_v4.py:730-756. Behavior:

    1. Enumerate input ports via ``mido_module.get_input_names()``.
    2. Find first port whose name contains ``port_hint`` (case-insensitive).
    3. If no match: sleep 2s, retry. If stop_event was set during the sleep,
       exit.
    4. If match: ``open_input(match)`` (context-managed), call
       ``controller_state.mark_connected(match)``, then enter the inner poll
       loop.
    5. Inner loop: ``port.poll()``; if None sleep 5ms and re-check
       stop_event; otherwise call ``controller_state.handle_msg(msg)``.
    6. On any exception in the outer try: print ``[midi listener err]`` to
       stderr, sleep 2s, restart from step 1.

    Args:
        controller_state: anything with ``mark_connected(str)`` and
            ``handle_msg(msg)`` — typically ``ControllerState`` from
            ``_midi_macos.py``.
        stop_event: ``threading.Event`` cooperative shutdown signal.
        port_hint: substring matched case-insensitively against port names.
            Production callers pass ``"DDJ-FLX4"`` for both macOS and Windows.
        mido_module: the ``mido`` module (or a test fake exposing the same
            ``get_input_names`` + ``open_input`` surface).
    """
    while not stop_event.is_set():
        try:
            ports = mido_module.get_input_names()
            match = next((p for p in ports if port_hint.lower() in p.lower()), None)
            if not match:
                time.sleep(2.0)
                continue
            with mido_module.open_input(match) as port:
                controller_state.mark_connected(match)
                print(f"-> MIDI controller in: {match!r}")
                while not stop_event.is_set():
                    msg = port.poll()
                    if msg is None:
                        time.sleep(0.005)
                        continue
                    controller_state.handle_msg(msg)
        except Exception as e:
            print(f"[midi listener err] {e} — retrying in 2s", file=sys.stderr)
            time.sleep(2.0)


def spawn_listener(controller_state, stop_event, port_hint, mido_module) -> threading.Thread:
    """Spawn ``midi_listener_thread`` as a daemon thread and return it.

    Daemon=True matches the v4 / Phase 3 contract: the listener never blocks
    process shutdown.

    Args:
        controller_state: see ``midi_listener_thread``.
        stop_event: see ``midi_listener_thread``.
        port_hint: see ``midi_listener_thread``.
        mido_module: see ``midi_listener_thread``.

    Returns:
        The started ``threading.Thread`` so callers can ``join(timeout=...)``
        on shutdown.
    """
    t = threading.Thread(
        target=midi_listener_thread,
        args=(controller_state, stop_event, port_hint, mido_module),
        name="midi-listener",
        daemon=True,
    )
    t.start()
    return t
