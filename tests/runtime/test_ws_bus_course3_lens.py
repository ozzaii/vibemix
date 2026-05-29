# SPDX-License-Identifier: Apache-2.0
"""Course 3 live lens on the existing flat ws bus frame."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from vibemix.runtime.ws_bus import _serialize_course3_lens, ws_broadcast
from vibemix.state import MusicState
from vibemix.state.deck_state import DeckState, DeckTrack

_REAL_SLEEP = asyncio.sleep


def test_course3_lens_cold_state_is_honest_null() -> None:
    lens = _serialize_course3_lens(MusicState())

    assert lens == {
        "session_active": False,
        "phrase_position_confidence": 0.0,
        "next_phrase_at": None,
        "next_phrase_cue_id": None,
        "audio_active": False,
        "deck_attributed": False,
        "deck_track_citable": False,
        "cue_ready": False,
        "blockers": [
            "waiting_for_audio",
            "waiting_for_deck",
            "waiting_for_deck_track",
            "waiting_for_cue",
        ],
    }


def test_course3_lens_carries_count_in_ready_fields() -> None:
    state = MusicState(
        session_active=True,
        phrase_position_confidence=0.85,
        next_phrase_at=108.0,
        next_phrase_cue_id="track-1:breakdown@64.0",
    )
    state.audible = True
    state.rms = 0.05
    state.audible_deck = "A"
    state.deck_state = DeckState(decks={"A": DeckTrack(track_id="track-1", confidence=0.85)})

    assert _serialize_course3_lens(state) == {
        "session_active": True,
        "phrase_position_confidence": 0.85,
        "next_phrase_at": 108.0,
        "next_phrase_cue_id": "track-1:breakdown@64.0",
        "audio_active": True,
        "deck_attributed": True,
        "deck_track_citable": True,
        "cue_ready": True,
        "blockers": [],
    }


def test_course3_lens_clamps_bad_confidence_and_bad_boundary() -> None:
    state = MusicState(
        session_active=True,
        phrase_position_confidence=9.0,
        next_phrase_at="not-a-number",  # type: ignore[arg-type]
        next_phrase_cue_id="cue-a",
    )

    assert _serialize_course3_lens(state) == {
        "session_active": True,
        "phrase_position_confidence": 1.0,
        "next_phrase_at": None,
        "next_phrase_cue_id": "cue-a",
        "audio_active": False,
        "deck_attributed": False,
        "deck_track_citable": False,
        "cue_ready": False,
        "blockers": [
            "waiting_for_audio",
            "waiting_for_deck",
            "waiting_for_deck_track",
            "waiting_for_cue",
        ],
        "operator_action": {
            "prompt": "Press play on deck.",
            "steps": [
                "Route Rekordbox to the routed master audio path selected by readiness.",
                "Load and play a real Rekordbox library track.",
                "Raise the playing channel fader and master until the status changes.",
            ],
        },
    }


def test_course3_lens_explains_audible_audio_without_deck_attribution() -> None:
    state = MusicState()
    state.audible = True
    state.rms = 0.05
    state.audible_deck = "none"
    state.deck_state = DeckState(decks={"A": DeckTrack(track_id="track-1", confidence=0.9)})

    lens = _serialize_course3_lens(state)

    assert lens["audio_active"] is True
    assert lens["deck_attributed"] is False
    assert lens["deck_track_citable"] is False
    assert lens["cue_ready"] is False
    assert lens["blockers"] == [
        "waiting_for_deck",
        "waiting_for_deck_track",
        "waiting_for_cue",
    ]
    assert lens["operator_action"] == {
        "prompt": "Open one channel.",
        "steps": [
            "Open one deck channel so the coach can attribute deck A or B.",
            "Keep the master up while the live lens listens.",
        ],
    }


def test_course3_lens_rejects_stale_audible_flag_without_rms() -> None:
    state = MusicState()
    state.audible = True
    state.rms = 0.0
    state.audible_deck = "none"

    lens = _serialize_course3_lens(state)

    assert lens["audio_active"] is False
    assert "waiting_for_audio" in lens["blockers"]


def test_course3_lens_requires_the_audible_deck_track_to_be_citable() -> None:
    state = MusicState()
    state.audible = True
    state.rms = 0.05
    state.audible_deck = "A"
    state.deck_state = DeckState(
        decks={
            "A": DeckTrack(track_id="quiet-side", confidence=0.2),
            "B": DeckTrack(track_id="other-side", confidence=0.95),
        }
    )

    lens = _serialize_course3_lens(state)

    assert lens["deck_attributed"] is True
    assert lens["deck_track_citable"] is False
    assert "waiting_for_deck_track" in lens["blockers"]
    assert lens["operator_action"] == {
        "prompt": "Load a track.",
        "steps": [
            "Load a Rekordbox library track on the audible deck so the coach can cite it.",
        ],
    }


def test_course3_lens_carries_keep_playing_action_until_cue_locks() -> None:
    state = MusicState(
        session_active=True,
        phrase_position_confidence=0.42,
        next_phrase_at=None,
        next_phrase_cue_id=None,
    )
    state.audible = True
    state.rms = 0.05
    state.audible_deck = "A"
    state.deck_state = DeckState(decks={"A": DeckTrack(track_id="track-1", confidence=0.85)})

    lens = _serialize_course3_lens(state)

    assert lens["operator_action"] == {
        "prompt": "Keep playing.",
        "steps": [
            "Keep the phrase playing until cue-section lookahead locks the next phrase.",
        ],
    }


def _build_mock_server() -> MagicMock:
    server = MagicMock()
    server.close = MagicMock()
    server.wait_closed = AsyncMock(return_value=None)
    return server


def _capture_payload(state: MusicState, mocker) -> dict:
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
            async def gen():
                await release_handler.wait()
                if False:  # pragma: no cover
                    yield self

            return gen()

    sleep_counter = {"n": 0}

    async def fast_sleep(_s):
        sleep_counter["n"] += 1
        if sleep_counter["n"] >= 50:
            stop_event.set()
            release_handler.set()
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    async def driver():
        bg = asyncio.create_task(ws_broadcast(fake_levels, state, manual_trigger, stop_event))
        await _REAL_SLEEP(0)
        await _REAL_SLEEP(0)
        handler = serve_mock.await_args.args[0]
        handler_task = asyncio.create_task(handler(LongLivedClient()))
        await bg
        try:
            await asyncio.wait_for(handler_task, timeout=0.5)
        except Exception:
            handler_task.cancel()

    asyncio.run(driver())
    assert sent_payloads
    return json.loads(sent_payloads[0])


def test_flat_ws_frame_includes_course3_lens(mocker) -> None:
    state = MusicState(
        session_active=True,
        phrase_position_confidence=0.85,
        next_phrase_at=108.0,
        next_phrase_cue_id="track-1:breakdown@64.0",
    )
    state.audible = True
    state.rms = 0.05
    state.audible_deck = "A"
    state.deck_state = DeckState(decks={"A": DeckTrack(track_id="track-1", confidence=0.85)})

    payload = _capture_payload(state, mocker)

    assert payload["course3_lens"] == {
        "session_active": True,
        "phrase_position_confidence": 0.85,
        "next_phrase_at": 108.0,
        "next_phrase_cue_id": "track-1:breakdown@64.0",
        "audio_active": True,
        "deck_attributed": True,
        "deck_track_citable": True,
        "cue_ready": True,
        "blockers": [],
    }
    for key in ("music", "voice", "mic"):
        assert key in payload
