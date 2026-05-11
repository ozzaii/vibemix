# SPDX-License-Identifier: Apache-2.0
"""port_watcher_task — async polling loop for MIDI port hot-plug detection.

Polls ``mido.get_input_names()`` every ``poll_seconds`` seconds (default
2.0 per success criterion #4 in 09-CONTEXT.md). On diff vs the previous
sweep, invokes a user-supplied callback with one of:

    ('connected', port_name: str, profile: ControllerProfile)
    ('disconnected', port_name: str)

The watcher does NOT directly mutate ControllerState or restart the
listener thread — those are caller concerns. The production wiring lives
in ``vibemix.platform._midi_common.handle_port_change``. This separation
lets unit tests inject a synchronous callback without dragging in the
threading + mido stack.

The callback may be sync (returning None) or async (returning a coroutine
that the watcher awaits transparently). Exceptions raised by the callback
are caught + logged to stderr; the watcher continues polling.

Hot-plug latency:
    The first time a previously-unseen port appears in
    ``get_input_names()``, the connected event fires on that same sweep
    (no extra debounce). With the default ``poll_seconds=2.0``, the
    worst-case detection latency is ~2.0 seconds; per success criterion
    #4 the bound is poll_seconds * 1.5 = 3.0 seconds.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Awaitable, Callable
from typing import Any

from vibemix.midi.registry import find_mapping_or_generic

OnChange = Callable[[tuple], Awaitable[None] | None]


async def port_watcher_task(
    stop_event: asyncio.Event,
    on_change: OnChange,
    mido_module: Any,
    *,
    poll_seconds: float = 2.0,
) -> None:
    """Run the MIDI port hot-plug poll loop until ``stop_event`` is set.

    Args:
        stop_event: ``asyncio.Event`` cooperative shutdown signal.
        on_change: callback invoked on every port diff. Receives a tuple:
            ``('connected', port_name, profile)`` or
            ``('disconnected', port_name)``. May be sync or async.
        mido_module: the ``mido`` module (or a test fake exposing
            ``get_input_names() -> list[str]``).
        poll_seconds: sweep cadence in seconds. Default 2.0 per CONTEXT.

    Behavior on every sweep:
        1. Call ``mido_module.get_input_names()`` (catch + log + skip on
           exception).
        2. Diff against the previous sweep:
           - For every port in ``previous - current``: emit
             ``('disconnected', port)`` (sorted).
           - For every port in ``current - previous``: resolve profile
             via ``find_mapping_or_generic(port)`` and emit
             ``('connected', port, profile)`` (sorted).
        3. Wait up to ``poll_seconds`` for ``stop_event.wait()`` (returns
           early if stop_event is set; otherwise fires after timeout).

    First sweep:
        Treated as a normal diff vs an empty initial last_seen set —
        every port present on sweep #1 emits a ``connected`` event.
    """
    last_seen: set[str] = set()
    while not stop_event.is_set():
        try:
            current = set(mido_module.get_input_names())
        except Exception as e:
            print(f"[port watcher err] {e}", file=sys.stderr)
            await _wait(stop_event, poll_seconds)
            continue

        connected = current - last_seen
        disconnected = last_seen - current

        for port in sorted(disconnected):
            await _safe_invoke(on_change, ("disconnected", port))
        for port in sorted(connected):
            profile = find_mapping_or_generic(port)
            await _safe_invoke(on_change, ("connected", port, profile))

        last_seen = current
        await _wait(stop_event, poll_seconds)


async def _wait(stop_event: asyncio.Event, seconds: float) -> None:
    """Sleep ``seconds`` returning early if ``stop_event`` is set.

    Implemented via ``asyncio.wait_for(stop_event.wait(), timeout=seconds)``
    which raises TimeoutError when the stop event is NOT set within the
    window — that's the normal "wait fired, keep polling" path.
    """
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=seconds)
    except TimeoutError:
        pass


async def _safe_invoke(callback: OnChange, payload: tuple) -> None:
    """Invoke ``callback(payload)``; if it returns a coroutine, await it.
    Swallow any exception (logged to stderr) so the watcher loop survives
    callback bugs.
    """
    try:
        result = callback(payload)
        if asyncio.iscoroutine(result):
            await result
    except Exception as e:
        print(f"[port watcher callback err] {e}", file=sys.stderr)


__all__ = ["port_watcher_task"]
