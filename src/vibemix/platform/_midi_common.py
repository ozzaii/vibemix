# SPDX-License-Identifier: Apache-2.0
"""Cross-platform MIDI listener thread — parameterized by ControllerProfile.

Phase 7 Wave 1 lifted the device-enumerate + open-input + poll-loop body out
of ``MidiMacOS.start_listener_thread`` so Wave 4's ``_midi_windows.py`` could
reuse it. Phase 9 Wave 1 Task 3 swaps the third positional from a single
``port_hint: str`` to a full ``ControllerProfile`` so the listener can:

1. Iterate ``profile.port_name_hints`` (in order) on every enumeration sweep —
   so a controller exposing itself as either ``"DDJ-FLX4 USB MIDI"`` OR
   ``"FLX4 USB MIDI"`` (depending on firmware revision) binds without the
   caller knowing which hint will hit.
2. Carry profile metadata (id, display_name) into log lines / future
   diagnostic surfaces without an out-of-band ``find_mapping`` call.

Backward compatibility:
    For one release boundary (Phase 9 → Phase 10), a ``str`` third positional
    is accepted and wrapped as a synthetic single-hint ControllerProfile +
    a ``DeprecationWarning``. Phase 10 drops the shim entirely.

Test injection seam: ``mido_module`` is the fourth positional parameter so
tests can pass a ``types.SimpleNamespace`` with ``get_input_names()`` and
``open_input(name)`` callables, exercising the loop deterministically without
a physical MIDI device.
"""

from __future__ import annotations

import sys
import threading
import time
import warnings

from vibemix.midi.profile import ControllerProfile


def _coerce_profile_arg(profile_or_hint) -> ControllerProfile:
    """Accept a ControllerProfile OR (legacy) a str port-hint.

    Phase 9 Wave 1 Task 3 — backward-compat shim. A str third-arg fires a
    ``DeprecationWarning`` and is wrapped as a synthetic single-hint profile
    so Phase 7 tests stay green. Phase 10 deletes this shim.
    """
    if isinstance(profile_or_hint, ControllerProfile):
        return profile_or_hint
    if isinstance(profile_or_hint, str):
        warnings.warn(
            "midi_listener_thread/spawn_listener: passing a str port_hint is "
            "deprecated; pass a ControllerProfile instead (e.g. "
            "load_profile('pioneer_ddj_flx4')). Shim removed in Phase 10.",
            DeprecationWarning,
            stacklevel=3,
        )
        return ControllerProfile(
            id="_legacy",
            display_name="_legacy",
            port_name_hints=(profile_or_hint,),
            decks=("A", "B"),
            controls={},
            buttons={},
        )
    raise TypeError(
        "midi_listener_thread/spawn_listener: third arg must be ControllerProfile "
        f"(or str — deprecated), got {type(profile_or_hint).__name__}"
    )


def _find_first_port_match(port_names: list[str], port_name_hints: tuple[str, ...]) -> str | None:
    """Search every hint (in order) against the port list (case-insensitive
    substring). Returns the first matching port name, or None if no hint
    matches any port.
    """
    for hint in port_name_hints:
        needle = hint.lower()
        for p in port_names:
            if needle in p.lower():
                return p
    return None


def midi_listener_thread(controller_state, stop_event, profile, mido_module):
    """Run the MIDI device enumerate-open-poll loop until ``stop_event`` is set.

    Phase 9 Wave 1 Task 3: third positional is now a ``ControllerProfile``
    (with a one-release ``str`` shim — see ``_coerce_profile_arg``).

    Behavior:

    1. Enumerate input ports via ``mido_module.get_input_names()``.
    2. For each hint in ``profile.port_name_hints`` (in order), find the first
       port whose name contains the hint (case-insensitive).
    3. If no hint matches any port: sleep 2s, retry. If stop_event was set
       during the sleep, exit.
    4. If a match: ``open_input(match)`` (context-managed), call
       ``controller_state.mark_connected(match)``, then enter the inner poll
       loop.
    5. Inner loop: ``port.poll()``; if None sleep 5ms and re-check
       stop_event; otherwise call ``controller_state.handle_msg(msg)``.
    6. On any exception in the outer try: print ``[midi listener err]`` to
       stderr, sleep 2s, restart from step 1.

    Args:
        controller_state: anything with ``mark_connected(str)`` and
            ``handle_msg(msg)`` — typically ``ControllerState`` from
            ``vibemix.midi.state``.
        stop_event: ``threading.Event`` cooperative shutdown signal.
        profile: ``ControllerProfile`` whose ``port_name_hints`` drive the
            substring match. Legacy ``str`` accepted with DeprecationWarning.
        mido_module: the ``mido`` module (or a test fake exposing the same
            ``get_input_names`` + ``open_input`` surface).
    """
    profile_obj = _coerce_profile_arg(profile)
    hints = profile_obj.port_name_hints

    while not stop_event.is_set():
        try:
            ports = list(mido_module.get_input_names())
            match = _find_first_port_match(ports, hints)
            if not match:
                time.sleep(2.0)
                continue
            with mido_module.open_input(match) as port:
                controller_state.mark_connected(match)
                print(f"-> MIDI controller in: {match!r} (profile={profile_obj.id})")
                while not stop_event.is_set():
                    msg = port.poll()
                    if msg is None:
                        time.sleep(0.005)
                        continue
                    controller_state.handle_msg(msg)
        except Exception as e:
            print(f"[midi listener err] {e} — retrying in 2s", file=sys.stderr)
            time.sleep(2.0)


def spawn_listener(controller_state, stop_event, profile, mido_module) -> threading.Thread:
    """Spawn ``midi_listener_thread`` as a daemon thread and return it.

    Daemon=True matches the v4 / Phase 3 contract: the listener never blocks
    process shutdown.

    Args:
        controller_state: see ``midi_listener_thread``.
        stop_event: see ``midi_listener_thread``.
        profile: ``ControllerProfile`` (or legacy ``str`` — deprecated).
        mido_module: see ``midi_listener_thread``.

    Returns:
        The started ``threading.Thread`` so callers can ``join(timeout=...)``
        on shutdown.
    """
    t = threading.Thread(
        target=midi_listener_thread,
        args=(controller_state, stop_event, profile, mido_module),
        name="midi-listener",
        daemon=True,
    )
    t.start()
    return t
