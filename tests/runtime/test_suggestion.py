# SPDX-License-Identifier: Apache-2.0
"""SuggestionService + the additive ``next_suggestion`` flat-frame field.

Two halves:
  * the service (seed resolution from MusicState, played-set, holder) with a
    fake store/library — no network, no real vectors;
  * the ws_bus serialize edge merging ``suggestion_holder.current_for_state()``
    onto the flat mascot frame (honest-null when None; absent when no holder),
    mirroring the deck_state field test harness.
"""

from __future__ import annotations

import asyncio
import json
import threading
from unittest.mock import AsyncMock, MagicMock

import numpy as np

from vibemix.runtime.suggestion import (
    SuggestionService,
    resolve_live_timing,
    resolve_seed,
    resolve_seed_context,
)
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
        self.load_count = 0

    def load_all(self):
        self.load_count += 1
        return self._ids, self._vectors


class _FakeStore:
    def __init__(self, ids, ranked, section_vectors=None):
        self._backend = _FakeBackend(ids, np.eye(len(ids), 4, dtype=np.float32))
        self._ranked = ranked
        self.section_vectors = section_vectors or {}
        self.search_count = 0

    def search_centered(self, qvec, k=10):
        self.search_count += 1
        return self._ranked[:k]


def _lib(ids):
    from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry

    lib = RekordboxLibrary()
    lib.tracks = {
        t: TrackEntry(
            track_id=t,
            title=f"T{t}",
            artist="A",
            album="X",
            bpm=124.0,
            key="8A",
            duration_s=300.0,
            cues=(),
            filepath=f"/{t}.mp3",
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
    svc.compute("s")  # seed s played
    out = svc.compute("a")  # now a is seed; s already played
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


def test_resolve_seed_context_names_source_and_target_decks():
    state = MusicState()
    state.audible_deck = "A"
    state.deck_state = DeckState(
        decks={"A": DeckTrack(title="X", track_id="t42", camelot="8A", bpm=128.0)}
    )

    seed = resolve_seed_context(state)

    assert seed is not None
    assert seed.track_id == "t42"
    assert seed.source_deck == "A"
    assert seed.target_deck == "B"


def test_resolve_seed_context_withholds_target_when_audible_side_is_uncertain():
    state = MusicState()
    state.audible_deck = "mix"
    state.deck_state = DeckState(
        decks={
            "A": DeckTrack(title="A", track_id="a", confidence=0.2),
            "B": DeckTrack(title="B", track_id="b", confidence=0.9),
        }
    )

    seed = resolve_seed_context(state)

    assert seed is not None
    assert seed.track_id == "b"
    assert seed.source_deck == "B"
    assert seed.target_deck is None


def test_resolve_seed_none_without_track_id():
    state = MusicState()
    state.audible_deck = "A"
    state.deck_state = DeckState(decks={"A": DeckTrack(title="X")})  # no track_id
    assert resolve_seed(state) is None
    # no deck_state at all → None
    assert resolve_seed(MusicState()) is None


def test_resolve_live_timing_withholds_when_bar_lock_is_weak():
    state = MusicState()
    state.bpm_confidence = 0.55
    state.beat_phase = 0.4

    timing = resolve_live_timing(state)

    assert timing.remaining_bars is None
    assert timing.playhead_confidence == 0.55
    assert timing.blend_active is False
    assert timing.source_position_s is None


def test_resolve_live_timing_uses_next_bar_when_locked():
    state = MusicState()
    state.bpm_confidence = 0.95
    state.beat_phase = 0.5

    timing = resolve_live_timing(state)

    assert timing.remaining_bars == 1
    assert timing.playhead_confidence == 0.95


def test_resolve_live_timing_prefers_grounded_track_position():
    state = MusicState()
    state.bpm_confidence = 0.55
    state.beat_phase = 0.4
    state.audible_track_position_s = 276.0
    state.audible_track_position_confidence = 0.85

    timing = resolve_live_timing(state)

    assert timing.remaining_bars is None
    assert timing.playhead_confidence == 0.85
    assert timing.source_position_s == 276.0


def test_compute_from_state_no_op_when_unresolved():
    store = _FakeStore(["s"], [("s", 0.99)])
    svc = SuggestionService(store, _lib(["s"]))
    # MusicState with no resolvable track_id → returns current (None), no crash.
    assert svc.compute_from_state(MusicState()) is None


def test_compute_from_state_threads_live_bar_timing_into_transition():
    from dataclasses import replace

    from vibemix.library.rekordbox import CuePoint

    store = _FakeStore(["s", "a"], [("s", 0.99), ("a", 0.9)])
    lib = _lib(["s", "a"])
    lib.tracks["s"] = replace(
        lib.tracks["s"],
        cues=(CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),),
    )
    lib.tracks["a"] = replace(
        lib.tracks["a"],
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    svc = SuggestionService(store, lib)
    state = MusicState()
    state.audible_deck = "A"
    state.bpm_confidence = 0.95
    state.beat_phase = 0.5
    state.audible_track_position_s = 276.0
    state.audible_track_position_confidence = 0.85
    state.deck_state = DeckState(
        decks={"A": DeckTrack(title="Source", track_id="s", camelot="8A", bpm=124.0)}
    )

    out = svc.compute_from_state(state)

    assert out is not None
    assert out["track_id"] == "a"
    assert out["transition"]["cue_slot"] == "A"
    assert out["transition"]["source_deck"] == "A"
    assert out["transition"]["target_deck"] == "B"
    assert out["transition"]["from_track_id"] == "s"
    assert out["transition"]["to_track_id"] == "a"
    assert out["transition"]["from_section_id"] == "s#s000"
    assert out["transition"]["from_role"] == "outro"
    assert out["transition"]["to_role"] == "intro"
    assert out["transition"]["from_start_s"] == 224.0
    assert out["transition"]["to_start_s"] == 0.0
    assert out["transition"]["start_in_bars"] == 13
    assert out["transition"]["timing_basis"] == "section_playhead"
    assert out["transition"]["timing_anchor"] == "source_section_end"

    envelope = svc.context_for_state(state, packet_id="ctx_live_001")

    assert envelope is not None
    assert envelope.packet_id == "ctx_live_001"
    assert envelope.current["active_track_id"] == "s"
    assert envelope.candidates[0]["to_track_id"] == "a"
    assert envelope.candidates[0]["recommended_cue_slot"] == "A"
    assert {"cue_slot", "section_role", "bars_until_event"} <= {
        claim["type"] for claim in envelope.claim_summary
    }

    decision = svc.decision_for_state(
        state,
        packet_id="ctx_live_001",
        snapshot_id="snapshot_live_001",
        decision_id="dec_live_001",
        trace_id="trace_live_001",
    )

    assert decision is not None
    assert decision.decision_id == "dec_live_001"
    assert decision.emitted is True
    assert decision.validation_result.accepted is True
    assert decision.final_decision.candidate_id == "tr_001"
    assert decision.final_decision.cue_slot == "A"
    assert decision.final_decision.timing_text == "in 13 bars"
    assert "cue A at 0:00" in decision.final_decision.spoken_text
    assert {"cue_slot", "section_role", "section_boundary", "bars_until_event"} <= set(
        decision.final_decision.cited_claims
    )

    payload = svc.decision_payload_for_state(
        state,
        packet_id="ctx_live_001",
        snapshot_id="snapshot_live_001",
        decision_id="dec_live_001",
        trace_id="trace_live_001",
    )

    assert payload is not None
    assert payload["action"] == "select"
    assert payload["emitted"] is True
    assert payload["validation_status"] == "accepted"
    assert payload["candidate_id"] == "tr_001"
    assert payload["cue_slot"] == "A"
    assert payload["timing_text"] == "in 13 bars"


def test_refresh_from_state_updates_transition_countdown_without_reranking():
    from dataclasses import replace

    from vibemix.library.rekordbox import CuePoint

    store = _FakeStore(["s", "a"], [("s", 0.99), ("a", 0.9)])
    lib = _lib(["s", "a"])
    lib.tracks["s"] = replace(
        lib.tracks["s"],
        cues=(CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),),
    )
    lib.tracks["a"] = replace(
        lib.tracks["a"],
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    svc = SuggestionService(store, lib)
    state = MusicState()
    state.audible_deck = "A"
    state.audible_track_position_s = 276.0
    state.audible_track_position_confidence = 0.85
    state.deck_state = DeckState(
        decks={"A": DeckTrack(title="Source", track_id="s", camelot="8A", bpm=124.0)}
    )

    first = svc.compute_from_state(state)
    assert first is not None
    assert first["transition"]["start_in_bars"] == 13
    assert first["transition"]["selection_basis"] == "section_transition"
    assert first["transition"]["selection_score"] > 0

    # Prove the live refresh is timing-only: neither the ranked list nor a fresh
    # vector load is needed once the chosen next track is held.
    store._ranked = []
    store._backend.load_count = 0
    state.audible_track_position_s = 292.0

    refreshed = svc.refresh_from_state(state, now=10.0, min_interval_s=0.0)

    assert refreshed is not None
    assert refreshed["track_id"] == "a"
    assert refreshed["transition"]["start_in_bars"] == 5
    assert refreshed["transition"]["timing_basis"] == "section_playhead"
    assert refreshed["transition"]["selection_basis"] == "section_transition"
    assert refreshed["transition"]["selection_score"] > 0
    assert refreshed["decision"]["action"] == "select"
    assert refreshed["decision"]["emitted"] is True
    assert refreshed["decision"]["validation_status"] == "accepted"
    assert refreshed["decision"]["candidate_id"] == "tr_001"
    assert refreshed["decision"]["cue_slot"] == "A"
    assert refreshed["decision"]["timing_text"] == "in 5 bars"
    assert "cue A at 0:00" in refreshed["decision"]["spoken_text"]
    assert store._backend.load_count == 0


def test_refresh_from_state_can_reselect_inside_embedding_shortlist():
    from dataclasses import replace

    from vibemix.library.rekordbox import CuePoint

    store = _FakeStore(
        ["s", "a", "b"],
        [("s", 0.99), ("a", 0.92), ("b", 0.91)],
        section_vectors={
            "s#s000": np.array([1.0, 0.0], dtype=np.float32),
            "s#s001": np.array([0.0, 1.0], dtype=np.float32),
            "a#s000": np.array([0.0, 1.0], dtype=np.float32),
            "b#s000": np.array([1.0, 0.0], dtype=np.float32),
        },
    )
    lib = _lib(["s", "a", "b"])
    lib.tracks["s"] = replace(
        lib.tracks["s"],
        bpm=120.0,
        cues=(
            CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),
            CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),
        ),
    )
    lib.tracks["a"] = replace(
        lib.tracks["a"],
        bpm=120.0,
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    lib.tracks["b"] = replace(
        lib.tracks["b"],
        bpm=120.0,
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    svc = SuggestionService(store, lib)
    state = MusicState()
    state.audible_deck = "A"
    state.deck_state = DeckState(
        decks={"A": DeckTrack(title="Source", track_id="s", camelot="8A", bpm=120.0)}
    )

    first = svc.compute_from_state(state)
    assert first is not None
    assert first["track_id"] == "a"
    assert first["transition"]["from_section_id"] == "s#s001"
    assert first["transition_alternatives"][0]["track_id"] == "a"

    store._backend.load_count = 0
    state.audible_track_position_s = 32.0
    state.audible_track_position_confidence = 0.85

    refreshed = svc.refresh_from_state(state, now=10.0, min_interval_s=0.0)

    assert refreshed is not None
    assert refreshed["track_id"] == "b"
    assert refreshed["transition"]["from_section_id"] == "s#s000"
    assert refreshed["transition"]["to_track_id"] == "b"
    assert refreshed["transition"]["candidate_id"] == "tr_001"
    assert refreshed["transition_alternatives"][0]["track_id"] == "b"
    assert refreshed["transition_alternatives"][0]["candidate_id"] == "tr_001"
    assert refreshed["transition_alternatives"][0]["selected"] is True
    assert refreshed["decision"]["action"] == "select"
    assert refreshed["decision"]["candidate_id"] == "tr_001"
    assert refreshed["decision"]["cue_slot"] == "A"
    assert len({alt["candidate_id"] for alt in refreshed["transition_alternatives"]}) == len(
        refreshed["transition_alternatives"]
    )
    assert store._backend.load_count == 0


def test_choose_alternative_pins_visible_backup_without_reranking():
    from dataclasses import replace

    from vibemix.library.rekordbox import CuePoint

    store = _FakeStore(
        ["s", "a", "b"],
        [("s", 0.99), ("a", 0.92), ("b", 0.91)],
        section_vectors={
            "s#s000": np.array([1.0, 0.0], dtype=np.float32),
            "s#s001": np.array([0.0, 1.0], dtype=np.float32),
            "a#s000": np.array([0.0, 1.0], dtype=np.float32),
            "b#s000": np.array([1.0, 0.0], dtype=np.float32),
        },
    )
    lib = _lib(["s", "a", "b"])
    lib.tracks["s"] = replace(
        lib.tracks["s"],
        bpm=120.0,
        cues=(
            CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),
            CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),
        ),
    )
    lib.tracks["a"] = replace(
        lib.tracks["a"],
        bpm=120.0,
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    lib.tracks["b"] = replace(
        lib.tracks["b"],
        bpm=120.0,
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    svc = SuggestionService(store, lib)
    state = MusicState()
    state.audible_deck = "A"
    state.deck_state = DeckState(
        decks={"A": DeckTrack(title="Source", track_id="s", camelot="8A", bpm=120.0)}
    )

    first = svc.compute_from_state(state)
    assert first is not None
    backup = next(alt for alt in first["transition_alternatives"] if alt["track_id"] == "b")

    store.search_count = 0
    store._backend.load_count = 0
    chosen = svc.choose_alternative(candidate_id=backup["candidate_id"], state=state)

    assert chosen is not None
    assert chosen["track_id"] == "b"
    assert chosen["transition"]["candidate_id"] == "tr_001"
    assert chosen["transition_alternatives"][0]["track_id"] == "b"
    assert chosen["transition_alternatives"][0]["candidate_id"] == "tr_001"
    assert chosen["transition_alternatives"][0]["selected"] is True
    assert chosen["transition_alternatives"][1]["track_id"] == "a"
    assert chosen["decision"]["action"] == "select"
    assert chosen["decision"]["candidate_id"] == "tr_001"

    refreshed = svc.refresh_from_state(state, now=10.0, min_interval_s=0.0)

    assert refreshed is not None
    assert refreshed["track_id"] == "b"
    assert refreshed["transition_alternatives"][0]["track_id"] == "b"
    assert refreshed["decision"]["candidate_id"] == "tr_001"
    assert store.search_count == 0
    assert store._backend.load_count == 0

    assert svc.choose_alternative(candidate_id="tr_missing", state=state) is None
    assert svc.current()["track_id"] == "b"


def test_refresh_from_state_clears_stale_pick_when_seed_changes():
    store = _FakeStore(["s", "a", "b"], [("s", 0.99), ("a", 0.9), ("b", 0.8)])
    svc = SuggestionService(store, _lib(["s", "a", "b"]))
    state = MusicState()
    state.audible_deck = "A"
    state.deck_state = DeckState(decks={"A": DeckTrack(track_id="s", confidence=1.0)})

    assert svc.compute_from_state(state) is not None
    state.deck_state = DeckState(decks={"A": DeckTrack(track_id="b", confidence=1.0)})

    assert svc.refresh_from_state(state, now=10.0, min_interval_s=0.0) is None
    assert svc.current() is None


def test_current_for_state_schedules_initial_compute_without_track_change():
    async def scenario():
        store = _FakeStore(["s", "a"], [("s", 0.99), ("a", 0.9)])
        svc = SuggestionService(store, _lib(["s", "a"]))
        state = MusicState()
        state.audible_deck = "A"
        state.deck_state = DeckState(decks={"A": DeckTrack(track_id="s", confidence=1.0)})

        first = svc.current_for_state(state)
        assert first is None or first["track_id"] == "a"
        for _ in range(50):
            await asyncio.sleep(0.01)
            if svc.current() is not None:
                break

        out = svc.current()
        assert out is not None
        assert out["track_id"] == "a"

    asyncio.run(scenario())


def test_current_for_state_does_not_duplicate_inflight_startup_compute():
    async def scenario():
        store = _FakeStore(["s", "a"], [("s", 0.99), ("a", 0.9)])
        svc = SuggestionService(store, _lib(["s", "a"]))
        state = MusicState()
        state.audible_deck = "A"
        state.deck_state = DeckState(decks={"A": DeckTrack(track_id="s", confidence=1.0)})

        original = svc.compute_for_seed
        started = asyncio.Event()
        release = threading.Event()
        calls = {"n": 0}
        loop = asyncio.get_running_loop()

        def blocking_compute(seed, timing):
            calls["n"] += 1
            loop.call_soon_threadsafe(started.set)
            release.wait(timeout=1.0)
            return original(seed, timing)

        svc.compute_for_seed = blocking_compute  # type: ignore[method-assign]

        assert svc.current_for_state(state) is None
        await asyncio.wait_for(started.wait(), timeout=1.0)
        assert svc.current_for_state(state) is None
        assert svc.current_for_state(state) is None
        assert calls["n"] == 1

        release.set()
        for _ in range(50):
            await asyncio.sleep(0.01)
            if svc.current() is not None:
                break
        assert svc.current() is not None
        assert calls["n"] == 1

    asyncio.run(scenario())


def test_track_change_scheduler_and_bus_refresh_share_inflight_guard():
    async def scenario():
        store = _FakeStore(["s", "a"], [("s", 0.99), ("a", 0.9)])
        svc = SuggestionService(store, _lib(["s", "a"]))
        state = MusicState()
        state.audible_deck = "A"
        state.deck_state = DeckState(decks={"A": DeckTrack(track_id="s", confidence=1.0)})

        original = svc.compute_for_seed
        started = asyncio.Event()
        release = threading.Event()
        calls = {"n": 0}
        loop = asyncio.get_running_loop()

        def blocking_compute(seed, timing):
            calls["n"] += 1
            loop.call_soon_threadsafe(started.set)
            release.wait(timeout=1.0)
            return original(seed, timing)

        svc.compute_for_seed = blocking_compute  # type: ignore[method-assign]

        assert svc.maybe_schedule_compute_from_state(state) is True
        await asyncio.wait_for(started.wait(), timeout=1.0)
        assert svc.current_for_state(state) is None
        assert calls["n"] == 1

        release.set()
        for _ in range(50):
            await asyncio.sleep(0.01)
            if svc.current() is not None:
                break
        assert svc.current() is not None
        assert calls["n"] == 1

    asyncio.run(scenario())


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
    fake_levels.snapshot = MagicMock(return_value={"music": 0.05, "voice": 0.02, "mic": 0.01})
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
                fake_levels,
                state,
                manual_trigger,
                stop_event,
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


class _LiveHolder:
    def __init__(self, value):
        self._value = value
        self.seen_state = None

    def current_for_state(self, state):
        self.seen_state = state
        return self._value

    def current(self):  # pragma: no cover - should not be used when live hook exists
        raise AssertionError("ws_broadcast should prefer current_for_state")


def test_payload_carries_suggestion(mocker):
    state = MusicState()
    state.audible = True
    sugg = {
        "track_id": "t1",
        "title": "Next One",
        "artist": "Rhadoo",
        "similarity": 0.83,
        "why": "similar vibe",
        "camelot": None,
        "bpm": None,
    }
    payload = _capture_payload(state, mocker, suggestion_holder=_Holder(sugg))
    assert payload["next_suggestion"] == sugg


def test_payload_uses_live_suggestion_refresh_hook(mocker):
    state = MusicState()
    state.audible = True
    sugg = {
        "track_id": "t1",
        "title": "Next One",
        "artist": "Rhadoo",
        "similarity": 0.83,
        "why": "similar vibe",
        "camelot": None,
        "bpm": None,
        "transition": {"cue_slot": "A", "start_in_bars": 4},
    }
    holder = _LiveHolder(sugg)

    payload = _capture_payload(state, mocker, suggestion_holder=holder)

    assert holder.seen_state is state
    assert payload["next_suggestion"] == sugg


def test_payload_live_refresh_reselects_cached_alternative_when_source_section_moves(mocker):
    from dataclasses import replace

    from vibemix.library.rekordbox import CuePoint

    store = _FakeStore(
        ["s", "a", "b"],
        [("s", 0.99), ("a", 0.92), ("b", 0.91)],
        section_vectors={
            "s#s000": np.array([1.0, 0.0], dtype=np.float32),
            "s#s001": np.array([0.0, 1.0], dtype=np.float32),
            "a#s000": np.array([0.0, 1.0], dtype=np.float32),
            "b#s000": np.array([1.0, 0.0], dtype=np.float32),
        },
    )
    lib = _lib(["s", "a", "b"])
    lib.tracks["s"] = replace(
        lib.tracks["s"],
        bpm=120.0,
        cues=(
            CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),
            CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),
        ),
    )
    lib.tracks["a"] = replace(
        lib.tracks["a"],
        bpm=120.0,
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    lib.tracks["b"] = replace(
        lib.tracks["b"],
        bpm=120.0,
        key="9A",
        cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
    )
    svc = SuggestionService(store, lib)
    state = MusicState()
    state.audible = True
    state.audible_deck = "A"
    state.deck_state = DeckState(
        decks={"A": DeckTrack(title="Source", track_id="s", camelot="8A", bpm=120.0)}
    )

    first = svc.compute_from_state(state)
    assert first is not None
    assert first["track_id"] == "a"
    assert first["transition"]["from_section_id"] == "s#s001"
    assert first["transition_alternatives"][0]["track_id"] == "a"

    store.search_count = 0
    store._backend.load_count = 0
    state.audible_track_position_s = 32.0
    state.audible_track_position_confidence = 0.85

    payload = _capture_payload(state, mocker, suggestion_holder=svc)

    suggestion = payload["next_suggestion"]
    assert suggestion["track_id"] == "b"
    assert suggestion["transition"]["from_section_id"] == "s#s000"
    assert suggestion["transition"]["to_track_id"] == "b"
    assert suggestion["transition"]["candidate_id"] == "tr_001"
    assert suggestion["transition_alternatives"][0]["track_id"] == "b"
    assert suggestion["transition_alternatives"][0]["selected"] is True
    assert suggestion["transition_alternatives"][1]["track_id"] == "a"
    assert suggestion["decision"]["action"] == "select"
    assert suggestion["decision"]["candidate_id"] == "tr_001"
    assert suggestion["decision"]["validation_status"] == "accepted"
    assert store.search_count == 0
    assert store._backend.load_count == 0


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
