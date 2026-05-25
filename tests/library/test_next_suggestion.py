# SPDX-License-Identifier: Apache-2.0
"""next_suggestion — the pill "what's next" engine. Fake store + in-memory
library; no network, no real vectors. Pins grounding (only library-resolved
ids), seed/played exclusion, honest-null, and the Phase-2 harmonic refine.
"""

from __future__ import annotations

import numpy as np
import pytest

from vibemix.library.next_suggestion import (
    NextSuggestion,
    next_suggestion,
    seed_vector_for_track_id,
)
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry


def _track(tid: str, bpm: float = 124.0, key: str = "8A") -> TrackEntry:
    return TrackEntry(
        track_id=tid, title=f"Title {tid}", artist=f"Artist {tid}", album="A",
        bpm=bpm, key=key, duration_s=300.0, cues=(), filepath=f"/tmp/{tid}.mp3",
    )


class _FakeBackend:
    def __init__(self, ids, vectors):
        self._ids, self._vectors = ids, vectors

    def load_all(self):
        return self._ids, self._vectors


class _FakeStore:
    """Returns a scripted ranked list from search_centered; load_all via backend."""

    def __init__(self, ranked, ids=None, vectors=None):
        self._ranked = ranked  # list[(track_id, sim)] in rank order
        self._backend = _FakeBackend(
            ids or [t for t, _ in ranked],
            vectors if vectors is not None else np.eye(len(ranked), 4, dtype=np.float32),
        )

    def search_centered(self, qvec, k=10):
        return self._ranked[:k]


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {f"t{i}": _track(f"t{i}") for i in range(6)}
    return lib


SEED = np.ones(4, dtype=np.float32)


def test_returns_top_grounded_neighbour(library):
    store = _FakeStore([("t0", 0.99), ("t1", 0.88), ("t2", 0.77)])
    s = next_suggestion(
        store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set()
    )
    assert isinstance(s, NextSuggestion)
    assert s.track_id == "t1"  # t0 is the seed → skipped
    assert s.similarity == 0.88
    assert s.why == "similar vibe · 8A · 124"  # key+bpm resolved from library


def test_excludes_played(library):
    store = _FakeStore([("t0", 0.99), ("t1", 0.88), ("t2", 0.77)])
    s = next_suggestion(
        store, library, seed_vector=SEED, seed_track_id="t0",
        played_ids={"t1"},
    )
    assert s is not None and s.track_id == "t2"


def test_skips_ids_absent_from_library(library):
    # GHOST is in the store ranking but not the library → ungrounded, skipped.
    store = _FakeStore([("t0", 0.99), ("GHOST", 0.95), ("t3", 0.80)])
    s = next_suggestion(
        store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set()
    )
    assert s is not None and s.track_id == "t3"


def test_none_when_nothing_qualifies(library):
    store = _FakeStore([("t0", 0.99)])  # only the seed
    s = next_suggestion(
        store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set()
    )
    assert s is None


def test_honest_null_when_no_metadata():
    lib = RekordboxLibrary()
    lib.tracks = {
        "t0": _track("t0"),
        "f1": TrackEntry(
            track_id="f1", title="Folder Track", artist="", album="",
            bpm=0.0, key="", duration_s=0.0, cues=(), filepath="/tmp/f1.mp3",
        ),
    }
    store = _FakeStore([("t0", 0.99), ("f1", 0.90)])
    s = next_suggestion(
        store, lib, seed_vector=SEED, seed_track_id="t0", played_ids=set()
    )
    assert s is not None and s.track_id == "f1"
    assert s.why == "similar vibe"  # no key/bpm → honest, no fabricated values
    assert s.camelot is None and s.bpm is None


def test_phase2_harmonic_filter_drops_incompatible(library):
    # seed 8A; t1 is also 8A (compatible), but make t1 a BPM clash to force the
    # filter to fall through to the next compatible candidate.
    library.tracks["t1"] = _track("t1", bpm=150.0, key="8A")  # far BPM
    library.tracks["t2"] = _track("t2", bpm=126.0, key="8A")  # compatible
    store = _FakeStore([("t0", 0.99), ("t1", 0.92), ("t2", 0.80)])
    s = next_suggestion(
        store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set(),
        seed_camelot="8A", seed_bpm=124.0, bpm_window=15.0,
    )
    assert s is not None and s.track_id == "t2"  # t1 dropped on BPM
    assert s.camelot == "8A" and s.bpm == 126.0


def test_phase2_keeps_candidate_missing_metadata(library):
    # A candidate with no key/bpm must NOT be dropped by the refine filter.
    library.tracks["t1"] = TrackEntry(
        track_id="t1", title="No Meta", artist="X", album="",
        bpm=0.0, key="", duration_s=0.0, cues=(), filepath="/tmp/t1.mp3",
    )
    store = _FakeStore([("t0", 0.99), ("t1", 0.92)])
    s = next_suggestion(
        store, library, seed_vector=SEED, seed_track_id="t0", played_ids=set(),
        seed_camelot="8A", seed_bpm=124.0,
    )
    assert s is not None and s.track_id == "t1"  # kept despite missing meta
    assert s.why == "similar vibe"


def test_seed_vector_helper(library):
    vectors = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float32)
    store = _FakeStore([], ids=["t0", "t1"], vectors=vectors)
    v = seed_vector_for_track_id(store, "t1")
    assert v is not None and np.allclose(v, [0, 1, 0, 0])
    assert seed_vector_for_track_id(store, "missing") is None
