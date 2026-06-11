# SPDX-License-Identifier: Apache-2.0
"""Saved-pool re-anchor — the prepared set keeps steering an off-plan night.

``next_track_id_after`` is exact-membership: before the re-anchor, ONE track
outside the saved plan killed the pool's influence on the pill for the rest of
the session. These tests pin the verified seam:

* exact plan hit → unchanged (``matched="exact"``, same reason prefix);
* off-plan seed → nearest UNPLAYED pool track by the engine's cosine, fed as
  the SAME soft ``source="prepared_pool"`` target the exact hit produces (so
  the downstream transition-evidence requirement — Invariant #2 — still holds);
* played pool tracks excluded; exhausted pool / missing vectors → None
  (behave exactly as before);
* Invariant #2 — a persisted pool id absent from the LIVE library this process
  can never enter the grounding set, even when its vector is nearest;
* the 0.75s refresh/broadcast edge does ZERO re-anchor vector work.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from vibemix.library.next_suggestion import nearest_track_id_by_cosine
from vibemix.library.prepared_pool import PreparedPool, PreparedPoolTrack
from vibemix.runtime.suggestion import ResolvedSeed, SuggestionService
from vibemix.state import MusicState
from vibemix.state.deck_state import DeckState, DeckTrack

# Cosine fixture geometry (4-dim): "p2" is clearly nearest to the live seed
# "x"; "p1" is orthogonal to it; "ghost" ties with the seed exactly so the
# library-grounding filter (not similarity) must be what rejects it.
_VECTORS = {
    "x": [1.0, 0.0, 0.0, 0.0],
    "y": [0.0, 1.0, 0.0, 0.0],
    "a": [0.6, 0.8, 0.0, 0.0],
    "s": [0.9, 0.1, 0.0, 0.0],
    "b": [0.7, 0.2, 0.0, 0.0],
    "p1": [0.0, 1.0, 0.0, 0.0],
    "p2": [0.8, 0.6, 0.0, 0.0],
    "ghost": [1.0, 0.0, 0.0, 0.0],
}


class _FakeBackend:
    def __init__(self, ids):
        self._ids = list(ids)
        self._vectors = [np.asarray(_VECTORS[i], dtype=np.float32) for i in self._ids]
        self.load_count = 0

    def load_all(self):
        self.load_count += 1
        return self._ids, self._vectors


class _FakeStore:
    def __init__(self, ids, ranked, section_vectors=None):
        self._backend = _FakeBackend(ids)
        self._ranked = ranked
        self.section_vectors = section_vectors or {}

    def search_centered(self, qvec, k=10):
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


def _pool(*track_ids):
    return PreparedPool(
        name="Saved Pool",
        created_at=1.0,
        json_path=Path("pool.json"),
        tracks=tuple(PreparedPoolTrack(t) for t in track_ids),
    )


def _seed(track_id="x"):
    return ResolvedSeed(track_id=track_id, camelot="8A", bpm=120.0)


def _service(store_ids, lib_ids, pool, ranked=(("x", 0.99), ("a", 0.92))):
    store = _FakeStore(list(store_ids), list(ranked))
    return SuggestionService(store, _lib(list(lib_ids)), prepared_pool_loader=lambda: pool), store


# --------------------------------------------------------------------------- #
# _prepared_target_for_seed contract                                          #
# --------------------------------------------------------------------------- #


def test_exact_pool_hit_unchanged_and_marked_exact():
    svc, _ = _service(["s", "b", "a"], ["s", "b", "a"], _pool("s", "b", "a"))

    target = svc._prepared_target_for_seed(_seed("s"), allow_reanchor=True)

    assert target is not None
    assert target.track_id == "b"
    assert target.reason_prefix == "next in saved pool"
    assert target.source == "prepared_pool"
    assert target.strict is False
    assert target.matched == "exact"


def test_off_plan_without_reanchor_flag_returns_none():
    svc, _ = _service(["x", "p1", "p2"], ["x", "p1", "p2"], _pool("p1", "p2"))

    # Default = the refresh-edge semantics: exact-membership only, no vector
    # work, exactly the pre-reanchor behavior.
    assert svc._prepared_target_for_seed(_seed("x")) is None


def test_off_plan_reanchors_to_nearest_pool_track():
    svc, _ = _service(["x", "p1", "p2"], ["x", "p1", "p2"], _pool("p1", "p2"))

    target = svc._prepared_target_for_seed(_seed("x"), allow_reanchor=True)

    assert target is not None
    assert target.track_id == "p2"  # cos(x, p2)=0.8 beats cos(x, p1)=0.0
    assert target.source == "prepared_pool"  # same soft shape as the exact hit
    assert target.strict is False
    assert target.matched == "reanchored"
    assert target.reason_prefix != "next in saved pool"  # honest receipt


def test_reanchor_excludes_played_pool_tracks():
    svc, _ = _service(["x", "p1", "p2"], ["x", "p1", "p2"], _pool("p1", "p2"))
    with svc._lock:
        svc._played.add("p2")

    target = svc._prepared_target_for_seed(_seed("x"), allow_reanchor=True)

    assert target is not None
    assert target.track_id == "p1"
    assert target.matched == "reanchored"


def test_reanchor_skips_pool_ids_missing_from_live_library():
    # "ghost" has a PERFECT vector match but is absent from the live library —
    # Invariant #2: persisted ids re-validate against the live store before
    # entering any grounding set.
    svc, _ = _service(
        ["x", "ghost", "p2"],
        ["x", "p2"],
        _pool("ghost", "p2"),
    )

    target = svc._prepared_target_for_seed(_seed("x"), allow_reanchor=True)

    assert target is not None
    assert target.track_id == "p2"


def test_reanchor_exhausted_pool_returns_none():
    svc, _ = _service(["x", "p1", "p2"], ["x", "p1", "p2"], _pool("p1", "p2"))
    with svc._lock:
        svc._played.update({"p1", "p2"})

    assert svc._prepared_target_for_seed(_seed("x"), allow_reanchor=True) is None


def test_reanchor_without_pool_vectors_returns_none():
    # Pool tracks exist in the live library but have no stored vectors.
    svc, _ = _service(["x"], ["x", "p1", "p2"], _pool("p1", "p2"))

    assert svc._prepared_target_for_seed(_seed("x"), allow_reanchor=True) is None


def test_reanchor_without_seed_vector_returns_none():
    # The live seed itself has no stored vector → nothing to rank against.
    svc, _ = _service(["p1", "p2"], ["x", "p1", "p2"], _pool("p1", "p2"))

    assert svc._prepared_target_for_seed(_seed("x"), allow_reanchor=True) is None


# --------------------------------------------------------------------------- #
# engine helper                                                               #
# --------------------------------------------------------------------------- #


def test_nearest_track_id_by_cosine_picks_highest_similarity():
    seed = np.array([1.0, 0.0], dtype=np.float32)
    vectors = {
        "far": np.array([0.0, 1.0], dtype=np.float32),
        "near": np.array([0.9, 0.1], dtype=np.float32),
    }

    assert (
        nearest_track_id_by_cosine(seed, vectors, ordered_track_ids=["far", "near"]) == "near"
    )


def test_nearest_track_id_by_cosine_breaks_ties_by_plan_order():
    seed = np.array([1.0, 0.0], dtype=np.float32)
    same = np.array([1.0, 0.0], dtype=np.float32)
    vectors = {"second": same.copy(), "first": same.copy()}

    assert (
        nearest_track_id_by_cosine(seed, vectors, ordered_track_ids=["first", "second"])
        == "first"
    )


def test_nearest_track_id_by_cosine_returns_none_when_unrankable():
    seed = np.array([1.0, 0.0], dtype=np.float32)

    assert nearest_track_id_by_cosine(seed, {}, ordered_track_ids=["missing"]) is None
    assert nearest_track_id_by_cosine(seed, {}, ordered_track_ids=[]) is None


# --------------------------------------------------------------------------- #
# full-compute integration + the refresh-edge guarantee                       #
# --------------------------------------------------------------------------- #


def _transition_fixture():
    """Store/library wired so the pool target carries real transition evidence
    (mirrors the exact-hit saved-pool test in test_suggestion.py)."""
    from vibemix.library.rekordbox import CuePoint

    store = _FakeStore(
        ["x", "a", "p1", "p2"],
        [("x", 0.99), ("a", 0.92)],
        section_vectors={
            "x#s000": np.array([1.0, 0.0], dtype=np.float32),
            "x#s001": np.array([0.0, 1.0], dtype=np.float32),
            "p1#s000": np.array([1.0, 0.0], dtype=np.float32),
            "p2#s000": np.array([1.0, 0.0], dtype=np.float32),
        },
    )
    lib = _lib(["x", "a", "p1", "p2"])
    lib.tracks["x"] = replace(
        lib.tracks["x"],
        bpm=120.0,
        cues=(
            CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),
            CuePoint(name="OUT", type="cue", start_s=224.0, end_s=None, number=5),
        ),
    )
    for tid in ("p1", "p2"):
        lib.tracks[tid] = replace(
            lib.tracks[tid],
            bpm=120.0,
            key="9A",
            cues=(CuePoint(name="IN", type="cue", start_s=0.0, end_s=None, number=0),),
        )
    # "a" stays without section vectors → no transition evidence, so the
    # reanchored target must win on evidence, not on shortlist order.
    return store, lib


def _state(seed_track_id="x"):
    state = MusicState()
    state.audible_deck = "A"
    state.deck_state = DeckState(
        decks={
            "A": DeckTrack(title="Live", track_id=seed_track_id, camelot="8A", bpm=120.0)
        }
    )
    return state


def test_off_plan_compute_selects_reanchored_pool_track():
    store, lib = _transition_fixture()
    svc = SuggestionService(store, lib, prepared_pool_loader=lambda: _pool("p1", "p2"))
    state = _state("x")

    out = svc.compute_from_state(state)
    envelope = svc.context_for_state(state, packet_id="ctx_live_pool_reanchor")

    assert out is not None
    assert out["track_id"] == "p2"
    assert out["why"].startswith("closest in saved pool")
    assert out["transition"]["to_track_id"] == "p2"  # Invariant #2: evidence attached
    assert out["transition_alternatives"][0]["track_id"] == "p2"
    assert envelope is not None
    assert envelope.current["prepared_target_track_id"] == "p2"


def test_compute_excludes_already_played_pool_tracks():
    store, lib = _transition_fixture()
    svc = SuggestionService(store, lib, prepared_pool_loader=lambda: _pool("p1", "p2"))

    svc.compute("p2")  # the DJ already played p2 this session
    out = svc.compute_from_state(_state("x"))

    assert out is not None
    assert out["track_id"] == "p1"
    assert out["why"].startswith("closest in saved pool")


def test_exhausted_pool_falls_back_to_plain_search():
    store, lib = _transition_fixture()
    svc = SuggestionService(store, lib, prepared_pool_loader=lambda: _pool("p1", "p2"))

    svc.compute("p1")
    svc.compute("p2")
    out = svc.compute_from_state(_state("x"))
    envelope = svc.context_for_state(_state("x"), packet_id="ctx_live_pool_spent")

    assert out is not None
    assert out["track_id"] == "a"  # exactly the pre-reanchor off-plan behavior
    assert not out["why"].startswith("closest in saved pool")
    assert envelope is not None
    assert envelope.current.get("prepared_target_track_id") is None


def test_refresh_edge_does_no_reanchor_vector_work(monkeypatch):
    store, lib = _transition_fixture()
    svc = SuggestionService(store, lib, prepared_pool_loader=lambda: _pool("p1", "p2"))
    state = _state("x")

    out = svc.compute_from_state(state)
    assert out is not None and out["track_id"] == "p2"

    def _bomb(*args, **kwargs):  # the heavy ranking must never run from refresh
        pytest.fail("reanchor vector work ran on the refresh/broadcast edge")

    monkeypatch.setattr(svc, "_reanchored_pool_target", _bomb)
    store._backend.load_count = 0

    refreshed = svc.refresh_from_state(state, now=10.0, min_interval_s=0.0)
    envelope = svc.context_for_state(state, packet_id="ctx_live_pool_refresh")

    assert refreshed is not None
    assert refreshed["track_id"] == "p2"  # the re-anchored pick survives refresh
    assert store._backend.load_count == 0
    assert envelope is not None
    assert envelope.current["prepared_target_track_id"] == "p2"


def test_seed_change_drops_the_sticky_reanchored_target():
    store, lib = _transition_fixture()
    svc = SuggestionService(store, lib, prepared_pool_loader=lambda: _pool("p1", "p2"))

    out = svc.compute_from_state(_state("x"))
    assert out is not None and out["track_id"] == "p2"

    # The DJ moves on to another off-plan track: the old anchor must not leak
    # into the new seed's context.
    state = _state("y")
    assert svc.refresh_from_state(state, now=10.0, min_interval_s=0.0) is None
    assert svc._prepared_target_for_context(_seed("y")) is None
