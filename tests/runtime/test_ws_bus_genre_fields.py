# SPDX-License-Identifier: Apache-2.0
"""Phase 52 (GENRE-02) — detected_genre + genre_confidence on the ws bus.

Adds two additive MusicState fields to the 30Hz mascot bus frame:
  - detected_genre (full-library auto-detected name, or "unknown" when unsure)
  - genre_confidence (the detector's score in [0, 1])

Anti-slop on the wire: when the detector is unsure, detected_genre is "unknown"
(never a hallucinated label) and genre_confidence carries the low score —
surfaced honestly, mirroring the existing active_genre "unknown" honesty. The
fields are STRICTLY ADDITIVE so they cannot trip the Phase-51 empty-frame guard
(it checks only music/voice/mic) or alter the 30Hz cadence.

Pattern mirrors test_ws_bus_phase22_fields.py exactly — mock websockets.serve so
nothing binds; drive a LongLivedClient through the captured handler to capture a
real outbound payload.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from vibemix.runtime.ws_bus import ws_broadcast
from vibemix.state import MusicState

_REAL_SLEEP = asyncio.sleep


def _build_mock_server() -> MagicMock:
    server = MagicMock()
    server.close = MagicMock()
    server.wait_closed = AsyncMock(return_value=None)
    return server


def _capture_payload(state: MusicState, mocker) -> dict:
    """Drive ws_broadcast through one tick + capture the first outbound mascot
    payload as a parsed dict. Same approach as test_ws_bus_phase22_fields."""
    mock_server = _build_mock_server()
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(return_value={"music": 0.05, "voice": 0.02, "mic": 0.01})
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
        bg = asyncio.create_task(ws_broadcast(fake_levels, state, manual_trigger, stop_event))
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


def test_payload_includes_detected_genre_and_confidence(mocker):
    """A confident detection rides the mascot frame with the exact MusicState
    values."""
    state = MusicState()
    state.audible = True
    state.detected_genre = "psytrance"
    state.genre_confidence = 0.82

    payload = _capture_payload(state, mocker)

    assert "detected_genre" in payload, (
        f"missing 'detected_genre' — got keys: {sorted(payload.keys())}"
    )
    assert "genre_confidence" in payload, (
        f"missing 'genre_confidence' — got keys: {sorted(payload.keys())}"
    )
    assert payload["detected_genre"] == "psytrance"
    assert payload["genre_confidence"] == 0.82


def test_payload_unknown_honesty_case(mocker):
    """Anti-slop on the wire: a low-confidence pick is surfaced as 'unknown'
    (never a fabricated label) with its low confidence carried as-is. The honesty
    is enforced at the SOURCE (Plan 03 scorer); the bus carries it verbatim."""
    state = MusicState()
    state.audible = True
    state.detected_genre = "unknown"
    state.genre_confidence = 0.30

    payload = _capture_payload(state, mocker)

    assert payload["detected_genre"] == "unknown", "a label leaked instead of 'unknown'"
    assert payload["genre_confidence"] == 0.30


def test_genre_fields_do_not_trip_empty_frame_guard(mocker):
    """The new keys are strictly additive — the captured frame still has the
    meter keys (music/voice/mic) so the Phase-51 empty-frame guard would not
    have skipped it, and active_genre is still present (parallel field, not
    replaced)."""
    state = MusicState()
    state.audible = True
    state.detected_genre = "techno"
    state.genre_confidence = 0.71
    state.active_genre = "techno"

    payload = _capture_payload(state, mocker)

    # A frame was actually captured (no silent no-op).
    assert payload, "no frame captured — the guard may have skipped the send"
    # Meter keys present -> guard not tripped.
    for k in ("music", "voice", "mic"):
        assert k in payload, f"meter key {k!r} missing — guard would have skipped this frame"
    # Parallel field intact.
    assert payload["active_genre"] == "techno", "active_genre regressed off the wire"
    # New fields present.
    assert payload["detected_genre"] == "techno"
    assert payload["genre_confidence"] == 0.71


def test_payload_default_detected_genre_is_unknown(mocker):
    """A fresh MusicState defaults detected_genre to 'unknown' / confidence 0.0
    — the additive defaults preserve the no-fabricated-label contract before any
    tick writes a real detection."""
    state = MusicState()
    payload = _capture_payload(state, mocker)
    assert payload["detected_genre"] == "unknown"
    assert payload["genre_confidence"] == 0.0
