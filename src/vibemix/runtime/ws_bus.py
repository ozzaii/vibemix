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
            payload = json.dumps(
                {
                    **levels.snapshot(),
                    "audible": state.audible,
                    "deck": state.audible_deck,
                    "phase": state.phase,
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
