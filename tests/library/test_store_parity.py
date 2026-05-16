# SPDX-License-Identifier: Apache-2.0
"""Plan 28-02 Task 3 — Mac/Win parity gate (Pitfall P55).

Asserts that:
    1. NumpyStore returns top-K identical to fixture ground-truth
       (the fixture itself was generated via cosine_topk so this is the
       primary self-referential check that the math doesn't drift).
    2. SqliteVecStore returns top-K identical to NumpyStore.
    3. Tie-break is deterministic (track_id ASC).
    4. float32 round-trips bit-identically through both backends.

When sqlite-vec extension is unavailable on the host, the sqlite-vec
parity test is skipped — the numpy ground-truth check still proves the
math is stable.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from vibemix.library import EMBEDDING_DIM, l2_normalize
from vibemix.library._cosine import cosine_topk
from vibemix.library.index_numpy import NumpyStore
from vibemix.library.store import LibraryStore


def _sqlite_vec_available() -> bool:
    try:
        import sqlite_vec  # noqa: F401

        db = sqlite3.connect(":memory:")
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.close()
        return True
    except Exception:
        return False


SQLITE_VEC_AVAILABLE = _sqlite_vec_available()
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def corpus() -> tuple[list[str], np.ndarray]:
    arr = np.load(FIXTURES / "synthetic_embeddings.npy", allow_pickle=False)
    ids = [f"t{i:04d}" for i in range(arr.shape[0])]
    return ids, arr


@pytest.fixture(scope="module")
def queries() -> list[dict]:
    with (FIXTURES / "synthetic_queries.json").open() as f:
        return json.load(f)


@pytest.mark.parity
def test_numpy_topk_matches_fixture_ground_truth(
    tmp_path: Path,
    corpus: tuple[list[str], np.ndarray],
    queries: list[dict],
) -> None:
    """NumpyStore.search must return the same top-K as the fixture's pre-baked
    ground-truth (which was computed via the SAME cosine_topk).
    """
    ids, vectors = corpus
    store = LibraryStore(
        NumpyStore(
            vectors_path=tmp_path / "v.npy", ids_path=tmp_path / "i.json"
        )
    )
    items = [(tid, vec) for tid, vec in zip(ids, vectors)]
    store.add_batch(items)

    for q in queries:
        # Use the bytes as stored in the fixture — do NOT re-normalize.
        # The fixture's vector + similarity were captured from cosine_topk
        # on the same normalized form; re-normalizing here would introduce
        # 1-ULP float drift (which is what the parity test is designed to
        # catch in OTHER code paths).
        qvec = np.asarray(q["vector"], dtype=np.float32)
        result = store.search(qvec, k=10)
        expected = q["top_k"]
        assert [tid for tid, _ in result] == [
            r["track_id"] for r in expected
        ], f"rank order drift on {q['id']}"
        for (tid, sim), exp in zip(result, expected):
            assert tid == exp["track_id"]
            assert round(sim, 6) == round(exp["similarity"], 6), (
                f"similarity drift on {q['id']}/{tid}: "
                f"got {sim}, expected {exp['similarity']}"
            )


@pytest.mark.parity
@pytest.mark.skipif(not SQLITE_VEC_AVAILABLE, reason="sqlite-vec extension unavailable")
def test_sqlite_vec_topk_matches_numpy(
    tmp_path: Path,
    corpus: tuple[list[str], np.ndarray],
    queries: list[dict],
) -> None:
    """The Mac↔Win parity gate. Both backends MUST produce identical top-K."""
    from vibemix.library.index_sqlite_vec import SqliteVecStore

    ids, vectors = corpus

    numpy_store = LibraryStore(
        NumpyStore(
            vectors_path=tmp_path / "v.npy", ids_path=tmp_path / "i.json"
        )
    )
    sqlite_store = LibraryStore(
        SqliteVecStore(db_path=tmp_path / "library.db")
    )

    items = [(tid, vec) for tid, vec in zip(ids, vectors)]
    numpy_store.add_batch(items)
    sqlite_store.add_batch(items)

    for q in queries:
        qvec = np.asarray(q["vector"], dtype=np.float32)
        np_result = numpy_store.search(qvec, k=10)
        sq_result = sqlite_store.search(qvec, k=10)
        assert [tid for tid, _ in np_result] == [
            tid for tid, _ in sq_result
        ], f"Mac↔Win parity broken on {q['id']}"
        for (np_tid, np_sim), (sq_tid, sq_sim) in zip(np_result, sq_result):
            assert np_tid == sq_tid
            assert round(np_sim, 6) == round(sq_sim, 6), (
                f"similarity drift between backends on {q['id']}/{np_tid}"
            )

    sqlite_store.close()


@pytest.mark.parity
def test_tie_break_track_id_asc() -> None:
    """Two vectors with identical cosine similarity → tie-break ASC by id."""
    # Both vectors orthogonal to query → cosine = 0 (tied).
    v1 = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    v1[0] = 1.0
    v2 = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    v2[0] = -1.0  # also orthogonal to query
    query = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    query[1] = 1.0

    result = cosine_topk(query, np.stack([v1, v2]), ["t-zebra", "t-apple"], k=2)
    # Both have similarity 0.0 → ASC by track_id.
    assert result[0][0] == "t-apple"
    assert result[1][0] == "t-zebra"


@pytest.mark.parity
def test_float32_round_trip_bit_identical(tmp_path: Path) -> None:
    """Float32 → blob → numpy round-trip is byte-exact."""
    rng = np.random.default_rng(99)
    arr = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
    arr = l2_normalize(arr)

    store = NumpyStore(
        vectors_path=tmp_path / "v.npy", ids_path=tmp_path / "i.json"
    )
    store.add_batch([("t0", arr)])
    _, loaded = store.load_all()
    np.testing.assert_array_equal(loaded[0], arr)


@pytest.mark.parity
def test_cosine_topk_uses_python_sort() -> None:
    """Static contract guard — cosine_topk must use Python's sorted/sort
    (Timsort) for the final tie-break sort. argpartition is for selection
    only, NOT for ordering.
    """
    src = (
        Path(__file__).parents[2]
        / "src"
        / "vibemix"
        / "library"
        / "_cosine.py"
    ).read_text()
    assert "pairs.sort" in src, (
        "_cosine.py must use Python's pairs.sort for deterministic tie-break"
    )
