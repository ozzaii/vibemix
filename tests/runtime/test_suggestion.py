# SPDX-License-Identifier: Apache-2.0
"""SuggestionService + the additive ``next_suggestion`` flat-frame field.

Two halves:
  * the service (seed resolution from MusicState, played-set, holder) with a
    fake store/library — no network, no real vectors;
  * the ws_bus serialize edge merging ``suggestion_holder.current()`` onto the
    flat mascot frame (honest-null when None; absent when no holder), mirroring
    the deck_state field test harness.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import numpy as np

from vibemix.runtime.suggestion import SuggestionService, resolve_seed
from vibemix.runtime.ws_bus import ws_broadcast
from vibemix.state import MusicState
from vibemix.state.deck_state import DeckState, DeckTrack

_REAL_SLEEP = asyncio.sleep


# --------------------------------------------------------------------------- #
# SuggestionService                                                           #
# --------------------------------------------------------------------------- #


class _FakeBackend:
    def __init__(self, ids, vectors):
        self._ids, self._vectors = ids, vectors

    def load_all(self):
        return self._ids, self._vectors


class _FakeStore:
    def __init__(self, ids, ranked):
        self._backend = _FakeBackend(
            ids, np.eye(len(ids), 4, dtype=np.float32)
        )
        self._ranked = ranked

    def search_centered(self, qvec, k=10):
        return self._ranked[:k]


def _lib(ids):
    from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry

    lib = RekordboxLibrary()
    lib.tracks = {
        t: TrackEntry(
            track_id=t, title=f"T{t}", artist="A", album="X",
            bpm=124.0, key="8A", duration_s=300.0, cues=(), filepath=f"/{t}.mp3",
        )
        for t in ids
    }
    return lib


def test_compute_returns_grounded_suggestion():
    store = _FakeStore(["s", "a", "b"], [("s", 0.99), ("a", 0.9), ("b", 0.8)])
    svc = SuggestionService(store, _lib(["s", "a", "b"]))
    out = svc.compute("s")
    assert out is not None and out["track_id"] == "a"
    assert svc.current() == out  # holder updated


def test_seed_marked_played_across_runs():
    store = _FakeStore(["s", "a", "b"], [("s", 0.99), ("a", 0.9), ("b", 0.8)])
    svc = SuggestionService(store, _lib(["s", "a", "b"]))
    svc.compute("s")          # seed s played
    out = svc.compute("a")    # now a is seed; s already played
    # next must be b (s is played, a is the new seed)
    assert out is not None and out["track_id"] == "b"


def test_compute_unknown_seed_keeps_current():
    store = _FakeStore(["s", "a"], [("s", 0.99), ("a", 0.9)])
    svc = SuggestionService(store, _lib(["s", "a"]))
    svc.compute("s")
    before = svc.current()
    out = svc.compute("not-in-store")  # seed vector missing → no-op
    assert out == before and svc.current() == before


def test_resolve_seed_from_audible_deck():
    state = MusicState()
    state.audible_deck = "A"
    state.deck_state = DeckState(
        decks={"A": DeckTrack(title="X", track_id="t42", camelot="8A", bpm=128.0)}
    )
    assert resolve_seed(state) == ("t42", "8A", 128.0)


def test_resolve_seed_none_without_track_id():
    state = MusicState()
    state.audible_deck = "A"
    state.deck_state = DeckState(decks={"A": DeckTrack(title="X")})  # no track_id
    assert resolve_seed(state) is None
    # no deck_state at all → None
    assert resolve_seed(MusicState()) is None


def test_compute_from_state_no_op_when_unresolved():
    store = _FakeStore(["s"], [("s", 0.99)])
    svc = SuggestionService(store, _lib(["s"]))
    # MusicState with no resolvable track_id → returns current (None), no crash.
    assert svc.compute_from_state(MusicState()) is None


# --------------------------------------------------------------------------- #
# ws_bus next_suggestion field                                                #
# --------------------------------------------------------------------------- #


def _capture_payload(state, mocker, *, suggestion_holder=None) -> dict:
    mock_server = MagicMock()
    mock_server.close = MagicMock()
    mock_server.wait_closed = AsyncMock(return_value=None)
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(
        return_value={"music": 0.05, "voice": 0.02, "mic": 0.01}
    )
    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()
    sent: list[str] = []
    release = asyncio.Event()

    class Client:
        async def send(self, payload):
            sent.append(payload)
            stop_event.set()
            release.set()

        def __aiter__(self):
            async def gen():
                await release.wait()
                if False:  # pragma: no cover
                    yield self

            return gen()

    counter = {"n": 0}

    async def fast_sleep(_s):
        counter["n"] += 1
        if counter["n"] >= 50:
            stop_event.set()
            release.set()
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    async def driver():
        bg = asyncio.create_task(
            ws_broadcast(
                fake_levels, state, manual_trigger, stop_event,
                suggestion_holder=suggestion_holder,
            )
        )
        await _REAL_SLEEP(0)
        await _REAL_SLEEP(0)
        handler = serve_mock.await_args.args[0]
        ht = asyncio.create_task(handler(Client()))
        await bg
        try:
            await asyncio.wait_for(ht, timeout=0.5)
        except Exception:
            ht.cancel()

    asyncio.run(driver())
    assert sent, "expected a broadcast payload"
    return json.loads(sent[0])


class _Holder:
    def __init__(self, value):
        self._value = value

    def current(self):
        return self._value


def test_payload_carries_suggestion(mocker):
    state = MusicState()
    state.audible = True
    sugg = {
        "track_id": "t1", "title": "Next One", "artist": "Rhadoo",
        "similarity": 0.83, "why": "similar vibe", "camelot": None, "bpm": None,
    }
    payload = _capture_payload(state, mocker, suggestion_holder=_Holder(sugg))
    assert payload["next_suggestion"] == sugg


def test_payload_honest_null_when_no_suggestion(mocker):
    state = MusicState()
    state.audible = True
    payload = _capture_payload(state, mocker, suggestion_holder=_Holder(None))
    # Present but null — honest silence, never a fabricated track.
    assert "next_suggestion" in payload
    assert payload["next_suggestion"] is None


def test_payload_absent_without_holder(mocker):
    """No holder wired → field absent → golden-equivalent for existing subs."""
    state = MusicState()
    state.audible = True
    payload = _capture_payload(state, mocker, suggestion_holder=None)
    assert "next_suggestion" not in payload
    # meter keys still present (guard not tripped)
    for k in ("music", "voice", "mic"):
        assert k in payload
