# SPDX-License-Identifier: Apache-2.0
"""Plan 28-02 Task 3 — per-backend smoke tests for the library store."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from vibemix.library import EMBEDDING_DIM, l2_normalize
from vibemix.library.index_numpy import NumpyStore
from vibemix.library.store import LibraryStore, open_store


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


def _rand_normalized(rng: np.random.Generator, n: int) -> list[np.ndarray]:
    arr = rng.standard_normal((n, EMBEDDING_DIM)).astype(np.float32)
    return [l2_normalize(row) for row in arr]


# ─── Per-backend smoke ───────────────────────────────────────────────────────


def test_numpy_round_trip(tmp_path: Path) -> None:
    s = NumpyStore(
        vectors_path=tmp_path / "v.npy", ids_path=tmp_path / "i.json"
    )
    rng = np.random.default_rng(0)
    vecs = _rand_normalized(rng, 100)
    items = [(f"t{i:04d}", v) for i, v in enumerate(vecs)]
    s.add_batch(items)

    s2 = NumpyStore(
        vectors_path=tmp_path / "v.npy", ids_path=tmp_path / "i.json"
    )
    ids, loaded = s2.load_all()
    assert ids == [f"t{i:04d}" for i in range(100)]
    assert loaded.shape == (100, EMBEDDING_DIM)
    assert loaded.dtype == np.float32
    np.testing.assert_array_equal(loaded, np.stack(vecs))


@pytest.mark.skipif(not SQLITE_VEC_AVAILABLE, reason="sqlite-vec extension unavailable")
def test_sqlite_vec_round_trip(tmp_path: Path) -> None:
    from vibemix.library.index_sqlite_vec import SqliteVecStore

    s = SqliteVecStore(db_path=tmp_path / "library.db")
    rng = np.random.default_rng(1)
    vecs = _rand_normalized(rng, 50)
    items = [(f"t{i:04d}", v) for i, v in enumerate(vecs)]
    s.add_batch(items)

    s2 = SqliteVecStore(db_path=tmp_path / "library.db")
    ids, loaded = s2.load_all()
    assert ids == sorted([f"t{i:04d}" for i in range(50)])
    np.testing.assert_array_equal(
        loaded, np.stack([v for _, v in sorted(items, key=lambda p: p[0])])
    )
    s.close()
    s2.close()


def test_float32_contract_enforced(tmp_path: Path) -> None:
    s = NumpyStore(
        vectors_path=tmp_path / "v.npy", ids_path=tmp_path / "i.json"
    )
    bad = np.ones(EMBEDDING_DIM, dtype=np.float64)
    with pytest.raises(AssertionError):
        s.add_batch([("t000", bad)])


def test_open_store_falls_back_to_numpy_when_sqlite_vec_load_fails() -> None:
    """Wave 0 ARM64 Win probe — Assumption A2."""
    with patch(
        "vibemix.library.index_sqlite_vec.sqlite_vec.load",
        side_effect=RuntimeError("no extension wheel for win-arm64"),
    ):
        store = open_store(prefer_sqlite_vec=True)
    assert store.backend_name == "NumpyStore"
    store.close()


def test_search_uses_cosine_topk(tmp_path: Path) -> None:
    s = LibraryStore(
        NumpyStore(
            vectors_path=tmp_path / "v.npy", ids_path=tmp_path / "i.json"
        )
    )
    rng = np.random.default_rng(2)
    vecs = _rand_normalized(rng, 20)
    items = [(f"t{i:03d}", v) for i, v in enumerate(vecs)]
    s.add_batch(items)
    q = vecs[0]
    with patch(
        "vibemix.library.store.cosine_topk", wraps=__import__(
            "vibemix.library._cosine", fromlist=["cosine_topk"]
        ).cosine_topk
    ) as spy:
        result = s.search(q, k=5)
    assert spy.called
    args = spy.call_args.args
    assert args[0].shape == (EMBEDDING_DIM,)
    assert args[1].shape == (20, EMBEDDING_DIM)
    assert isinstance(args[2], list)
    assert len(result) == 5
    # Top result is itself (cosine=1.0 with L2-normalized vectors).
    assert result[0][0] == "t000"


def test_delete_removes_rows(tmp_path: Path) -> None:
    s = LibraryStore(
        NumpyStore(
            vectors_path=tmp_path / "v.npy", ids_path=tmp_path / "i.json"
        )
    )
    rng = np.random.default_rng(3)
    vecs = _rand_normalized(rng, 10)
    items = [(f"t{i:03d}", v) for i, v in enumerate(vecs)]
    s.add_batch(items)
    s.delete(["t002", "t005", "t009"])
    ids, vectors = s._backend.load_all()
    assert ids == [f"t{i:03d}" for i in range(10) if i not in {2, 5, 9}]
    assert vectors.shape == (7, EMBEDDING_DIM)


def test_snapshot_hash_stable_across_reloads(tmp_path: Path) -> None:
    s1 = NumpyStore(
        vectors_path=tmp_path / "v.npy", ids_path=tmp_path / "i.json"
    )
    rng = np.random.default_rng(4)
    items = [(f"t{i:03d}", v) for i, v in enumerate(_rand_normalized(rng, 50))]
    s1.add_batch(items)
    h1 = s1.snapshot_hash()

    s2 = NumpyStore(
        vectors_path=tmp_path / "v.npy", ids_path=tmp_path / "i.json"
    )
    h2 = s2.snapshot_hash()
    assert h1 == h2
