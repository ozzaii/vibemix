# SPDX-License-Identifier: Apache-2.0
"""Phase 22 Plan 02 — ws_broadcast 30Hz payload extension.

Adds two MusicState fields to the mascot bus:
  - beat_phase (Phase 17 alias of downbeat_phase, ∈ [0, 1))
  - active_genre ("house" / "techno" / "hard_tek" / "unknown")

The renderer (Wave 2) subscribes to beat_phase per CONTEXT; downbeat_phase
stays on the wire for Phase 13-06 dispatcher backward-compat.

Pattern mirrors test_ws_bus.py — mock websockets.serve so we don't actually
bind to 127.0.0.1:8765; drive a LongLivedClient through the captured
handler to capture a real outbound payload from the broadcast loop.

Anti-hallucination: bpm_confidence < 0.6 → beat_phase is still emitted
as-is. The renderer is responsible for ignoring beat-locked behavior under
low confidence (existing Plan 13-04 contract preserved — Open Q 4).
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from vibemix.runtime.ws_bus import ws_broadcast
from vibemix.state import MusicState

_REAL_SLEEP = asyncio.sleep


def _build_mock_server() -> MagicMock:
    """Mock WebSocket server with close + wait_closed (AsyncMock)."""
    server = MagicMock()
    server.close = MagicMock()
    server.wait_closed = AsyncMock(return_value=None)
    return server


def _capture_payload(state: MusicState, mocker) -> dict:
    """Drive ws_broadcast through a single tick + capture the first
    outbound payload. Returns the parsed JSON dict.

    Same approach as test_ws_06_broadcast_payload_shape in test_ws_bus.py
    — a LongLivedClient registered via the captured handler stays in the
    `clients` set across broadcast ticks so its `send` fires.
    """
    mock_server = _build_mock_server()
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(
        return_value={"music": 0.05, "voice": 0.02, "mic": 0.01}
    )
    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()

    sent_payloads: list[str] = []
    release_handler = asyncio.Event()

    class LongLivedClient:
        async def send(self, payload):
            sent_payloads.append(payload)
            stop_event.set()
            release_handler.set()

        def __aiter__(self):
            client = self

            async def gen():
                await release_handler.wait()
                if False:  # pragma: no cover
                    yield client

            return gen()

    sleep_counter = {"n": 0}

    async def fast_sleep(_s):
        sleep_counter["n"] += 1
        if sleep_counter["n"] >= 50:  # safety net
            stop_event.set()
            release_handler.set()
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    async def driver():
        bg = asyncio.create_task(
            ws_broadcast(fake_levels, state, manual_trigger, stop_event)
        )
        await _REAL_SLEEP(0)
        await _REAL_SLEEP(0)
        handler = serve_mock.await_args.args[0]

        client = LongLivedClient()
        handler_task = asyncio.create_task(handler(client))

        await bg
        try:
            await asyncio.wait_for(handler_task, timeout=0.5)
        except Exception:
            handler_task.cancel()

    asyncio.run(driver())

    assert len(sent_payloads) >= 1, "expected at least one broadcast payload"
    return json.loads(sent_payloads[0])


def test_phase22_payload_includes_beat_phase_and_active_genre(mocker):
    """The 30Hz mascot bus payload exposes Phase 17 fields beat_phase +
    active_genre so the renderer (Wave 2) can subscribe to a single
    stream without reaching into Phase 17 internals."""
    state = MusicState()
    state.audible = True
    state.beat_phase = 0.42
    state.active_genre = "techno"
    state.bpm_confidence = 0.85

    payload = _capture_payload(state, mocker)

    assert "beat_phase" in payload, (
        f"missing 'beat_phase' in payload — got keys: {sorted(payload.keys())}"
    )
    assert "active_genre" in payload, (
        f"missing 'active_genre' in payload — got keys: {sorted(payload.keys())}"
    )
    assert payload["beat_phase"] == 0.42
    assert payload["active_genre"] == "techno"


def test_phase22_payload_preserves_downbeat_phase(mocker):
    """downbeat_phase (the Phase 13-05 field) stays on the wire alongside
    beat_phase — Phase 13-06 dispatcher backward-compat (the renderer
    can migrate to beat_phase incrementally without breaking existing
    subscribers)."""
    state = MusicState()
    state.audible = True
    state.downbeat_phase = 0.31
    state.beat_phase = 0.31
    state.active_genre = "house"

    payload = _capture_payload(state, mocker)

    assert "downbeat_phase" in payload, "downbeat_phase regressed off the wire"
    assert "beat_phase" in payload, "beat_phase missing"
    assert payload["downbeat_phase"] == 0.31
    assert payload["beat_phase"] == 0.31


def test_phase22_payload_emits_beat_phase_even_under_low_confidence(mocker):
    """Anti-hallucination invariant: when bpm_confidence < 0.6 the bus
    still emits beat_phase as-is — the renderer (NOT the bus) is
    responsible for ignoring beat-locked behavior under low confidence
    (Plan 13-04 Open Q 4, CONTEXT D-LOCKED). The bus is a dumb wire."""
    state = MusicState()
    state.audible = True
    state.beat_phase = 0.7
    state.active_genre = "unknown"
    state.bpm_confidence = 0.2  # below the 0.6 threshold

    payload = _capture_payload(state, mocker)

    # The bus must not mutate/zero the value — that's the renderer's job.
    assert payload["beat_phase"] == 0.7
    assert payload["active_genre"] == "unknown"
    assert payload["bpm_confidence"] == 0.2


def test_phase22_payload_default_active_genre_is_unknown(mocker):
    """A fresh MusicState defaults active_genre to 'unknown' (mirrors the
    Phase 17 dataclass default — anti-hallucination: no fabricated genre
    during BPM lock-up)."""
    state = MusicState()
    # Don't override active_genre — read the dataclass default.
    payload = _capture_payload(state, mocker)
    assert payload["active_genre"] == "unknown"
    assert payload["beat_phase"] == 0.0  # default
