# SPDX-License-Identifier: Apache-2.0
"""discovery — Mode A library-local candidate-pool builder.

Pure-compute tests: fake store + in-memory library, no network, no embedder.
Pins the centroid math (weighted blend + text α-blend + L2-norm), the
hard-filter both-known degrade discipline (missing key/bpm = PASS), MMR
diversity, and the end-to-end grounding (store/library skew ids dropped).
"""

from __future__ import annotations

import numpy as np
import pytest

from vibemix.library.discovery import (
    PoolItem,
    discover_pool,
    hard_filter,
    intent_centroid,
    mmr_rerank,
)
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry


# --------------------------------------------------------------------------- #
# Fixtures — mirror tests/library/test_next_suggestion.py's fake pattern.
# --------------------------------------------------------------------------- #


def _track(
    tid: str,
    bpm: float = 124.0,
    key: str = "8A",
    duration_s: float = 300.0,
) -> TrackEntry:
    return TrackEntry(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        album="A",
        bpm=bpm,
        key=key,
        duration_s=duration_s,
        cues=(),
        filepath=f"/tmp/{tid}.mp3",
    )


class _FakeBackend:
    def __init__(self, ids, vectors):
        self._ids, self._vectors = ids, vectors
        self.load_all_calls = 0

    def load_all(self):
        self.load_all_calls += 1
        return self._ids, self._vectors


class _FakeStore:
    """Scripted search_centered + load_all-via-backend, like test_next_suggestion."""

    def __init__(self, ranked, ids=None, vectors=None):
        self._ranked = ranked  # list[(track_id, sim)] in rank order
        n = len(ranked)
        self._backend = _FakeBackend(
            ids if ids is not None else [t for t, _ in ranked],
            vectors
            if vectors is not None
            else np.eye(max(n, 1), 4, dtype=np.float32),
        )

    def search_centered(self, qvec, k=10):
        return self._ranked[:k]


def _unit(*xs) -> np.ndarray:
    v = np.asarray(xs, dtype=np.float32)
    return v / np.linalg.norm(v)


# --------------------------------------------------------------------------- #
# intent_centroid
# --------------------------------------------------------------------------- #


def test_intent_centroid_single_ref_is_normalized_passthrough():
    ref = np.array([3.0, 4.0, 0.0], dtype=np.float32)  # norm 5
    out = intent_centroid([ref])
    assert np.allclose(out, [0.6, 0.8, 0.0], atol=1e-6)
    assert abs(np.linalg.norm(out) - 1.0) < 1e-6


def test_intent_centroid_default_weights_favour_first_ref():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)
    out = intent_centroid([a, b])  # default weights [0.5, 0.3...]-style → a heavier
    assert out[0] > out[1]
    assert abs(np.linalg.norm(out) - 1.0) < 1e-6


def test_intent_centroid_explicit_weights():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)
    # equal weights → symmetric blend
    out = intent_centroid([a, b], weights=[1.0, 1.0])
    assert np.allclose(out, _unit(1.0, 1.0), atol=1e-6)


def test_intent_centroid_text_alpha_blend():
    centroid_src = np.array([1.0, 0.0], dtype=np.float32)
    text = np.array([0.0, 1.0], dtype=np.float32)
    # alpha=0.5 → equal pull from centroid vs text → 45deg, then normalized
    out = intent_centroid([centroid_src], text_vector=text, alpha=0.5)
    assert np.allclose(out, _unit(1.0, 1.0), atol=1e-6)
    assert abs(np.linalg.norm(out) - 1.0) < 1e-6


def test_intent_centroid_high_alpha_leans_to_refs():
    centroid_src = np.array([1.0, 0.0], dtype=np.float32)
    text = np.array([0.0, 1.0], dtype=np.float32)
    out = intent_centroid([centroid_src], text_vector=text, alpha=0.9)
    assert out[0] > out[1]  # refs dominate


def test_intent_centroid_text_only_returns_normalized_text():
    text = np.array([0.0, 6.0, 8.0], dtype=np.float32)  # norm 10
    out = intent_centroid([], text_vector=text)
    assert np.allclose(out, [0.0, 0.6, 0.8], atol=1e-6)
    assert abs(np.linalg.norm(out) - 1.0) < 1e-6


def test_intent_centroid_empty_raises():
    with pytest.raises(ValueError):
        intent_centroid([])
    with pytest.raises(ValueError):
        intent_centroid([], text_vector=None)


def test_intent_centroid_zero_text_vector_raises():
    """WR-04: a zero text embedding cannot ground a direction → ValueError, not
    a silently-returned zero/un-normalized vector."""
    zero = np.zeros(8, dtype=np.float32)
    with pytest.raises(ValueError, match="zero embedding"):
        intent_centroid([], text_vector=zero)


def test_intent_centroid_zero_refs_raises():
    """WR-04 (blended/ref path): all-zero refs yield a degenerate centroid →
    ValueError rather than a zero vector that grounds nothing."""
    zeros = [np.zeros(8, dtype=np.float32), np.zeros(8, dtype=np.float32)]
    with pytest.raises(ValueError, match="zero embedding"):
        intent_centroid(zeros)


# --------------------------------------------------------------------------- #
# hard_filter
# --------------------------------------------------------------------------- #


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {f"t{i}": _track(f"t{i}") for i in range(8)}
    return lib


def test_hard_filter_bpm_range(library):
    library.tracks["t1"] = _track("t1", bpm=128.0)
    library.tracks["t2"] = _track("t2", bpm=140.0)  # out of range
    cands = [("t1", 0.9), ("t2", 0.8)]
    out = hard_filter(cands, library=library, bpm_min=120.0, bpm_max=132.0)
    ids = [c[0] for c in out]
    assert ids == ["t1"]


def test_hard_filter_missing_bpm_passes(library):
    library.tracks["t1"] = _track("t1", bpm=0.0)  # unknown bpm
    cands = [("t1", 0.9)]
    out = hard_filter(cands, library=library, bpm_min=120.0, bpm_max=132.0)
    assert [c[0] for c in out] == ["t1"]  # missing bpm = PASS


def test_hard_filter_camelot_both_known_drop(library):
    # ref 8A, candidate 5A → incompatible (1 semitone clash) → drop
    library.tracks["t1"] = _track("t1", key="5A")
    library.tracks["t2"] = _track("t2", key="9A")  # adjacent fifth → compatible
    cands = [("t1", 0.9), ("t2", 0.8)]
    out = hard_filter(cands, library=library, ref_camelots=["8A"])
    assert [c[0] for c in out] == ["t2"]


def test_hard_filter_missing_key_passes(library):
    # candidate has no key → must NOT be dropped (both-known gate).
    library.tracks["t1"] = _track("t1", key="")
    cands = [("t1", 0.9)]
    out = hard_filter(cands, library=library, ref_camelots=["8A"])
    assert [c[0] for c in out] == ["t1"]


def test_hard_filter_camelot_compatible_with_any_ref(library):
    # incompatible with first ref but compatible with second → keep.
    library.tracks["t1"] = _track("t1", key="5A")  # clashes 8A, ok vs 5A
    cands = [("t1", 0.9)]
    out = hard_filter(cands, library=library, ref_camelots=["8A", "5A"])
    assert [c[0] for c in out] == ["t1"]


def test_hard_filter_duration_window(library):
    library.tracks["t1"] = _track("t1", duration_s=120.0)  # too short
    library.tracks["t2"] = _track("t2", duration_s=300.0)
    library.tracks["t3"] = _track("t3", duration_s=900.0)  # too long
    cands = [("t1", 0.9), ("t2", 0.8), ("t3", 0.7)]
    out = hard_filter(
        cands, library=library, min_duration_s=180.0, max_duration_s=600.0
    )
    assert [c[0] for c in out] == ["t2"]


def test_hard_filter_missing_duration_passes(library):
    library.tracks["t1"] = _track("t1", duration_s=0.0)
    cands = [("t1", 0.9)]
    out = hard_filter(
        cands, library=library, min_duration_s=180.0, max_duration_s=600.0
    )
    assert [c[0] for c in out] == ["t1"]


def test_hard_filter_exclude_ids(library):
    cands = [("t1", 0.9), ("t2", 0.8)]
    out = hard_filter(cands, library=library, exclude_ids={"t1"})
    assert [c[0] for c in out] == ["t2"]


def test_hard_filter_drops_ungrounded(library):
    cands = [("GHOST", 0.99), ("t1", 0.8)]
    out = hard_filter(cands, library=library)
    assert [c[0] for c in out] == ["t1"]  # GHOST absent from library → dropped


# --------------------------------------------------------------------------- #
# mmr_rerank
# --------------------------------------------------------------------------- #


def test_mmr_lambda_one_is_pure_relevance():
    # Three near-identical vectors with descending scores; λ=1 ignores diversity
    # so order follows score.
    vbi = {
        "a": _unit(1.0, 0.0),
        "b": _unit(0.99, 0.01),
        "c": _unit(0.98, 0.02),
    }
    scored = [("a", 0.9), ("b", 0.85), ("c", 0.8)]
    out = mmr_rerank(scored, vbi, k=3, lambda_=1.0)
    assert out == ["a", "b", "c"]


def test_mmr_lambda_zero_spreads_diversity():
    # 'a' and 'b' are near-dupes; 'c' is orthogonal. λ=0 → after the first pick,
    # the most-different candidate wins. The orthogonal 'c' must rank above the
    # near-dupe of the first selection.
    vbi = {
        "a": _unit(1.0, 0.0, 0.0),
        "b": _unit(0.999, 0.001, 0.0),  # near-dupe of a
        "c": _unit(0.0, 0.0, 1.0),  # orthogonal
    }
    scored = [("a", 0.9), ("b", 0.89), ("c", 0.5)]
    out = mmr_rerank(scored, vbi, k=2, lambda_=0.0)
    assert out[0] == "a"
    assert out[1] == "c"  # diversity beats the near-dupe b


def test_mmr_does_not_return_a_cluster_of_near_dupes():
    # A tight cluster of 4 near-identical + 2 diverse. A balanced λ should
    # surface the diverse ones, not 3 clones of the top.
    vbi = {
        "c0": _unit(1.0, 0.001, 0.0),
        "c1": _unit(1.0, 0.002, 0.0),
        "c2": _unit(1.0, 0.003, 0.0),
        "c3": _unit(1.0, 0.004, 0.0),
        "d0": _unit(0.0, 1.0, 0.0),
        "d1": _unit(0.0, 0.0, 1.0),
    }
    scored = [
        ("c0", 0.95),
        ("c1", 0.94),
        ("c2", 0.93),
        ("c3", 0.92),
        ("d0", 0.6),
        ("d1", 0.55),
    ]
    out = mmr_rerank(scored, vbi, k=3, lambda_=0.5)
    assert out[0] == "c0"  # top relevance still leads
    assert "d0" in out and "d1" in out  # both diverse picks surfaced
    # at most one of the remaining cluster members slipped in
    assert sum(1 for x in out if x.startswith("c")) == 1


def test_mmr_returns_up_to_k():
    vbi = {"a": _unit(1.0, 0.0), "b": _unit(0.0, 1.0)}
    scored = [("a", 0.9), ("b", 0.8)]
    out = mmr_rerank(scored, vbi, k=5, lambda_=0.7)
    assert set(out) == {"a", "b"}
    assert len(out) == 2


def test_mmr_empty():
    assert mmr_rerank([], {}, k=5) == []


# --------------------------------------------------------------------------- #
# discover_pool — end-to-end (no embedder, ref_track_ids path)
# --------------------------------------------------------------------------- #


def test_discover_pool_ref_ids_no_embedder(library):
    # Store has a seed t0 + several candidates. ref_track_ids=[t0].
    ids = [f"t{i}" for i in range(6)]
    vectors = np.eye(6, 8, dtype=np.float32)
    ranked = [("t0", 0.99), ("t1", 0.9), ("t2", 0.85), ("t3", 0.8)]
    store = _FakeStore(ranked, ids=ids, vectors=vectors)

    pool = discover_pool(
        store,
        library,
        ref_track_ids=["t0"],
        k=10,
        exclude_ids={"t0"},
    )
    assert all(isinstance(p, PoolItem) for p in pool)
    tids = [p.track_id for p in pool]
    assert "t0" not in tids  # excluded seed
    assert tids  # non-empty
    # PoolItem carries resolved metadata
    first = pool[0]
    assert first.title.startswith("Title")
    assert first.bpm == 124.0
    assert first.camelot == "8A"


def test_discover_pool_grounding_drops_store_library_skew(library):
    # GHOST exists in the store ranking but not the library → dropped.
    ids = ["t0", "GHOST", "t1"]
    vectors = np.eye(3, 8, dtype=np.float32)
    ranked = [("t0", 0.99), ("GHOST", 0.95), ("t1", 0.8)]
    store = _FakeStore(ranked, ids=ids, vectors=vectors)
    pool = discover_pool(
        store, library, ref_track_ids=["t0"], k=10, exclude_ids={"t0"}
    )
    tids = [p.track_id for p in pool]
    assert "GHOST" not in tids
    assert "t1" in tids


def test_discover_pool_applies_hard_filter(library):
    # t1 out of BPM range, t2 in range → only t2 survives.
    library.tracks["t1"] = _track("t1", bpm=160.0)
    library.tracks["t2"] = _track("t2", bpm=126.0)
    ids = ["t0", "t1", "t2"]
    vectors = np.eye(3, 8, dtype=np.float32)
    ranked = [("t0", 0.99), ("t1", 0.9), ("t2", 0.85)]
    store = _FakeStore(ranked, ids=ids, vectors=vectors)
    pool = discover_pool(
        store,
        library,
        ref_track_ids=["t0"],
        k=10,
        bpm_min=120.0,
        bpm_max=132.0,
        exclude_ids={"t0"},
    )
    tids = [p.track_id for p in pool]
    assert tids == ["t2"]


def test_discover_pool_requires_a_query(library):
    store = _FakeStore([("t0", 0.99)], ids=["t0"], vectors=np.eye(1, 8, dtype=np.float32))
    with pytest.raises(ValueError):
        discover_pool(store, library, k=10)  # no refs, no text


class _FakeEmbedder:
    """Offline embedder stub — returns a fixed query vector via embed_query."""

    def __init__(self, vec):
        self._vec = np.asarray(vec, dtype=np.float32)
        self.calls: list[str] = []

    def embed_query(self, text: str) -> np.ndarray:
        self.calls.append(text)
        return self._vec


def test_discover_pool_text_query_uses_embedder(library):
    ids = ["t0", "t1"]
    vectors = np.eye(2, 8, dtype=np.float32)
    ranked = [("t1", 0.9), ("t0", 0.5)]
    store = _FakeStore(ranked, ids=ids, vectors=vectors)
    emb = _FakeEmbedder(np.eye(1, 8, dtype=np.float32)[0])
    pool = discover_pool(
        store, library, embedder=emb, text_query="dark warehouse", k=10
    )
    assert emb.calls == ["dark warehouse"]  # embedder invoked once
    assert [p.track_id for p in pool]  # produced a grounded pool


def test_discover_pool_text_query_without_embedder_raises(library):
    store = _FakeStore(
        [("t0", 0.99)], ids=["t0"], vectors=np.eye(1, 8, dtype=np.float32)
    )
    with pytest.raises(ValueError):
        discover_pool(store, library, text_query="anything", k=10)


def test_discover_pool_missing_ref_vector_raises(library):
    # ref_track_id not present in store → cannot build a centroid → ValueError.
    store = _FakeStore([("t0", 0.99)], ids=["t0"], vectors=np.eye(1, 8, dtype=np.float32))
    with pytest.raises(ValueError):
        discover_pool(store, library, ref_track_ids=["nope"], k=10)


def test_discover_pool_loads_store_once(library):
    """WR-05: the store is loaded ONCE per call, not once per ref + per filtered
    candidate. With several candidates the load_all count must stay O(1)."""
    ids = [f"t{i}" for i in range(6)]
    vectors = np.eye(6, 8, dtype=np.float32)
    ranked = [("t0", 0.99), ("t1", 0.9), ("t2", 0.85), ("t3", 0.8), ("t4", 0.7)]
    store = _FakeStore(ranked, ids=ids, vectors=vectors)

    pool = discover_pool(
        store, library, ref_track_ids=["t0"], k=10, exclude_ids={"t0"}
    )
    assert pool  # several candidates survived (so the old code would re-load)
    # The whole store is read exactly once regardless of candidate count.
    assert store._backend.load_all_calls == 1
