# SPDX-License-Identifier: Apache-2.0
"""ws_broadcast — verbatim port of cohost_v4.py:1872-1918.

Mascot WebSocket bus on ``127.0.0.1:8765``. Inbound: ``{"action":
"trigger"}`` sets ``manual_trigger``. Outbound: 30Hz state snapshot
(levels + audible/deck/phase) to all connected clients. Dead clients are
removed lazily on send failure.

The v4 ``_HAS_WS`` feature flag is dropped — ``websockets`` is now an
explicit pyproject dep (Phase 2 declared it). On import failure the
program fails loud with ImportError; this matches the Phase 2
anti-pattern note in ``02-PATTERNS.md §AntiPatterns-2``.
"""

from __future__ import annotations

import asyncio
import json

import websockets

from vibemix.audio import WS_HOST, WS_PORT, Levels
from vibemix.state import MusicState


async def ws_broadcast(
    levels: Levels,
    state: MusicState,
    manual_trigger: asyncio.Event,
    stop_event: asyncio.Event,
) -> None:
    """30Hz outbound mascot broadcast + inbound manual-trigger handler.

    Verbatim port of cohost_v4.py:1872-1918 with the ``_HAS_WS``
    early-return removed (Phase 2 anti-pattern note — fail loud).
    """
    clients: set = set()

    async def handler(ws):
        clients.add(ws)
        try:
            async for msg in ws:
                try:
                    data = json.loads(msg) if isinstance(msg, str) else {}
                except Exception:
                    data = {}
                if data.get("action") == "trigger":
                    print("\n[ws] manual trigger requested")
                    manual_trigger.set()
        except Exception:
            pass
        finally:
            clients.discard(ws)

    server = await websockets.serve(handler, WS_HOST, WS_PORT)
    print(f"-> mascot bus on ws://{WS_HOST}:{WS_PORT} (send {{action: trigger}} for manual fire)")

    try:
        while not stop_event.is_set():
            # Phase 13-05 — extend the 30Hz snapshot with mood +
            # bpm_confidence + downbeat_phase so the mascot renderer
            # (Plan 13-04) can subscribe to a single stream. Anti-
            # hallucination: bpm_confidence < 0.6 → renderer skips
            # beat-locked entry; mood drives clip-pool + voice swap.
            #
            # Phase 22-02 — extend further with `beat_phase` +
            # `active_genre`. `beat_phase` is a Phase-17-named alias of
            # `downbeat_phase` (both ∈ [0, 1) — fraction-through-current-
            # bar). Both ride on the wire simultaneously because the
            # Plan 13-06 dispatcher binds to `downbeat_phase` and the
            # Phase 22 anticipation/hip-bob layers bind to `beat_phase`;
            # carrying both lets the renderer migrate incrementally
            # without breaking existing subscribers. `active_genre`
            # ("house"/"techno"/"hard_tek"/"unknown") feeds the
            # GenreRouter on the renderer side. Anti-hallucination is
            # the renderer's job (the bus is a dumb wire) — under low
            # bpm_confidence the bus still emits beat_phase as-is and
            # the renderer (Plan 13-04 Open Q 4) ignores beat-locked
            # behavior.
            payload = json.dumps(
                {
                    **levels.snapshot(),
                    "audible": state.audible,
                    "deck": state.audible_deck,
                    "phase": state.phase,
                    "bpm": state.bpm,
                    "mood": state.mood,
                    "bpm_confidence": state.bpm_confidence,
                    "downbeat_phase": state.downbeat_phase,
                    "beat_phase": state.beat_phase,
                    "active_genre": state.active_genre,
                }
            )
            dead = []
            for c in clients:
                try:
                    await c.send(payload)
                except Exception:
                    dead.append(c)
            for c in dead:
                clients.discard(c)
            await asyncio.sleep(1 / 30)
    finally:
        server.close()
        await server.wait_closed()


# ---------------------------------------------------------------------------
# Phase 11 Wave 4 — WizardBus: handler-registration + ipc.* dispatch.
# ---------------------------------------------------------------------------
#
# The WizardBus runs ONLY in ``--wizard`` mode (the live-runtime ``main()``
# uses ``ws_broadcast`` above which has a different lifecycle and is
# mascot-only). Both bind ``127.0.0.1:8765`` — they never run at the same
# time because the Tauri shell spawns ``vibemix --wizard`` first, waits for
# ``ipc.wizard.done``, then respawns ``vibemix`` without the flag.
#
# Inbound message dispatch:
#   1. Parse JSON → dict.
#   2. ``vibemix.ui_bus.validator.validate_message(dict)`` — drop frame on
#      ValidationError; do NOT close the socket (T-11-W4-04 mitigation).
#   3. Route to a handler registered for ``msg["type"]``; if none, log + drop.
#
# Outbound: ``emit(dict)`` validates the schema before broadcasting (catches
# Python-side schema drift at runtime — RESEARCH Pitfall 10).
#
# The mascot.html broadcast contract is NOT extended here. The wizard does
# not broadcast levels/state — those are computed by the live-runtime
# ``state_refresh_loop`` which only exists in the non-wizard process.


from collections.abc import Awaitable, Callable
import sys as _sys

import jsonschema as _jsonschema

from vibemix.audio import WS_HOST, WS_PORT
from vibemix.ui_bus.validator import validate_message as _validate_outbound

IpcHandler = Callable[[dict], Awaitable[None]]


class WizardBus:
    """ipc.* WS bus for the calibration wizard (Phase 11 Wave 4).

    Wraps ``websockets.serve(127.0.0.1:8765)`` with a per-message-type
    handler dispatch table. Handlers are registered via ``register_handler``
    and invoked when an inbound frame matches their ``type``. Outbound
    broadcasts via ``emit`` validate the schema before send.

    Single-writer assumption: this class is constructed once per wizard
    process. ``start()`` opens the server; ``stop()`` closes it. The
    sidecar exits cleanly when the WizardLoop sets its stop event after
    receiving ``ipc.wizard.done``.
    """

    def __init__(self) -> None:
        self._clients: set = set()
        self._handlers: dict[str, IpcHandler] = {}
        self._server: object | None = None

    def register_handler(self, message_type: str, handler: IpcHandler) -> None:
        """Register an async handler for a given ipc.* message type.

        Multiple registrations for the same type overwrite — last-write
        wins. The WizardLoop registers all 8 handlers up front, so this
        case shouldn't fire in production.
        """
        self._handlers[message_type] = handler

    async def start(self) -> None:
        """Open the WS server on 127.0.0.1:8765. Idempotent — second
        call is a no-op if already running."""
        if self._server is not None:
            return
        self._server = await websockets.serve(self._handler, WS_HOST, WS_PORT)
        print(
            f"-> wizard bus on ws://{WS_HOST}:{WS_PORT} "
            f"(handlers: {len(self._handlers)})"
        )

    async def stop(self) -> None:
        """Close the server. Safe to call multiple times."""
        if self._server is None:
            return
        self._server.close()  # type: ignore[attr-defined]
        await self._server.wait_closed()  # type: ignore[attr-defined]
        self._server = None
        self._clients.clear()

    async def emit(self, msg: dict) -> None:
        """Broadcast an ipc.* message to all connected clients.

        Validates against the schema first — Python-side schema drift
        surfaces here at runtime (NOT just at codegen / CI). Validation
        failure raises; the WizardLoop wraps emits in try/except so a
        bad outbound frame doesn't crash the wizard.
        """
        _validate_outbound(msg)
        payload = json.dumps(msg, separators=(",", ":"))
        dead = []
        for c in self._clients:
            try:
                await c.send(payload)
            except Exception:
                dead.append(c)
        for c in dead:
            self._clients.discard(c)

    async def _handler(self, ws) -> None:
        """Per-connection inbound loop. Accepts ipc.* frames, dispatches
        to the registered handler, drops invalid frames without closing
        the socket (T-11-W4-04)."""
        self._clients.add(ws)
        try:
            async for raw in ws:
                if not isinstance(raw, str):
                    # Binary frames are not part of the ipc.* contract; ignore.
                    continue
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError as e:
                    print(f"[wizard bus] non-JSON frame: {e}", file=_sys.stderr)
                    continue
                if not isinstance(msg, dict):
                    print(
                        f"[wizard bus] top-level not object: {type(msg).__name__}",
                        file=_sys.stderr,
                    )
                    continue
                try:
                    validate_message(msg)
                except _jsonschema.ValidationError as e:
                    print(f"[wizard bus] schema violation: {e.message}", file=_sys.stderr)
                    continue
                msg_type = msg.get("type", "")
                handler = self._handlers.get(msg_type)
                if handler is None:
                    print(
                        f"[wizard bus] no handler for {msg_type}",
                        file=_sys.stderr,
                    )
                    continue
                try:
                    await handler(msg)
                except Exception as e:
                    # Handler-internal failure must not close the WS.
                    print(
                        f"[wizard bus] handler {msg_type} failed: {e}",
                        file=_sys.stderr,
                    )
        except Exception:
            pass
        finally:
            self._clients.discard(ws)


def validate_message(msg: dict) -> None:
    """Thin re-export of ``vibemix.ui_bus.validator.validate_message`` for
    internal use. Exposed at this scope so ``WizardBus`` can be tested
    with monkey-patched validation without reaching into ``ui_bus``.
    """
    from vibemix.ui_bus.validator import validate_message as _v
    _v(msg)


# Phase 12 — ``IpcBus`` is the neutral alias for ``WizardBus`` used by
# ``SessionLoop``. The bus is mutually exclusive with the wizard at
# runtime (Tauri spawns one process at a time) and the dispatch surface
# is identical — so we share the class instead of forking it.
IpcBus = WizardBus


__all__ = ["IpcBus", "IpcHandler", "WizardBus", "validate_message", "ws_broadcast"]
