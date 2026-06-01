# SPDX-License-Identifier: Apache-2.0
"""Phase 63 Plan 63-01 (Wave 0, RED-first) — Mac/Win parity gate for memory.db.

Clone of ``tests/library/test_store_parity.py`` retargeted at the (not-yet-built)
``vibemix.memory.store.MemoryStore``. Asserts the SAME guarantees the library
store proves, on the separate ``memory.db``:

    1. sqlite-vec and numpy backends return bit-identical top-K rank order
       (the Mac↔Win parity gate, Pitfall P55) — both route ranking through the
       single ``cosine_topk`` chokepoint, never a native vec0 KNN.
    2. Tie-break is deterministic (record_id ASC) via ``cosine_topk``.
    3. float32 round-trips bit-identically through the numpy backend.

RED-first contract: ``from vibemix.memory.store import MemoryStore`` fails on
collection until Plans 02/03 build the package. That collection error IS the
pinned contract — it proves these tests target the unbuilt package, not a stub.

Synthetic 768-dim L2-normalized vectors are generated IN-TEST via
``np.random.default_rng(seed)`` (no new fixture file — keeps the repo lean).

The chokepoint (``cosine_topk`` inside ``MemoryStore``, plus the shared
``l2_normalize`` / ``EMBEDDING_DIM`` imported here) lives in
``vibemix.library._cosine`` — never forked. No test in this file defines a
bespoke nearest-neighbour search or asserts a native distance-ordered query
path; ranking is the shared chokepoint, end to end.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.library.index_numpy import NumpyStore  # noqa: F401 (parity ref)
from vibemix.memory.store import MemoryStore


def _sqlite_vec_available() -> bool:
    try:
        import sqlite_vec

        db = sqlite3.connect(":memory:")
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.close()
        return True
    except Exception:
        return False


SQLITE_VEC_AVAILABLE = _sqlite_vec_available()


def _stale_dim() -> int:
    return 768 if EMBEDDING_DIM != 768 else 512


def _create_stale_sqlite_vec_memory_db(
    db_path: Path,
    *,
    with_vector: bool,
    with_moment: bool,
) -> int:
    """Create a memory.db whose vec0 table is pinned to the previous dim."""
    import sqlite_vec

    stale_dim = _stale_dim()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(db_path))
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    db.execute(
        f"CREATE VIRTUAL TABLE vec_memory USING vec0("
        f"record_id TEXT PRIMARY KEY, "
        f"embedding FLOAT[{stale_dim}] distance_metric=cosine"
        f")"
    )
    db.execute(
        "CREATE TABLE moments ("
        "record_id  TEXT PRIMARY KEY, "
        "session_id TEXT NOT NULL, "
        "ts         REAL NOT NULL, "
        "kind       TEXT NOT NULL, "
        "signature  TEXT NOT NULL"
        ")"
    )
    if with_vector:
        old_vec = np.zeros(stale_dim, dtype=np.float32)
        old_vec[0] = 1.0
        db.execute(
            "INSERT INTO vec_memory(record_id, embedding) VALUES (?, ?)",
            ("old:0", old_vec.tobytes()),
        )
    if with_moment:
        db.execute(
            "INSERT INTO moments(record_id, session_id, ts, kind, signature) "
            "VALUES (?, ?, ?, ?, ?)",
            ("old:0", "old", 0.0, "moment", "old stale signature"),
        )
    db.commit()
    db.close()
    return stale_dim


def _synthetic_records(seed: int, n: int = 100):
    """N synthetic memory records with 768-dim L2-normalized float32 vectors.

    Returns a list of ``(record_id, session_id, ts, kind, signature, vec)``
    tuples in the locked ``MemoryStore.add_record`` argument order.
    """
    rng = np.random.default_rng(seed)
    records = []
    for i in range(n):
        vec = l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))
        records.append((f"s1:{i}", "s1", float(i), "moment", f"sig {i}", vec))
    return records


@pytest.mark.parity
@pytest.mark.skipif(not SQLITE_VEC_AVAILABLE, reason="sqlite-vec extension unavailable")
def test_memory_sqlite_vec_recreates_empty_stale_dim_table(tmp_path: Path) -> None:
    """An empty 768-dim ``vec_memory`` table self-heals before first 512-d insert."""
    db_path = tmp_path / "memory.db"
    stale_dim = _create_stale_sqlite_vec_memory_db(
        db_path, with_vector=False, with_moment=True
    )
    assert stale_dim != EMBEDDING_DIM

    store = MemoryStore(db_path=db_path, prefer_sqlite_vec=True)
    try:
        assert store.backend_name == "SqliteVecMemoryStore"
        assert store._backend.vector_dim() == EMBEDDING_DIM
        assert (
            store._moments.execute("SELECT COUNT(*) FROM moments").fetchone()[0]
            == 0
        )

        vec = l2_normalize(np.ones(EMBEDDING_DIM, dtype=np.float32))
        store.add_record("s1:0", "s1", 0.0, "moment", "fresh", vec)

        assert store._backend.row_count() == 1
        assert [r.record_id for r in store.query_topk(vec, k=1)] == ["s1:0"]
    finally:
        store.close()


@pytest.mark.parity
@pytest.mark.skipif(not SQLITE_VEC_AVAILABLE, reason="sqlite-vec extension unavailable")
def test_memory_sqlite_vec_populated_stale_dim_falls_back(tmp_path: Path) -> None:
    """A populated stale table is not wiped; the store falls back to fresh numpy."""
    db_path = tmp_path / "memory.db"
    stale_dim = _create_stale_sqlite_vec_memory_db(
        db_path, with_vector=True, with_moment=True
    )
    assert stale_dim != EMBEDDING_DIM

    store = MemoryStore(db_path=db_path, prefer_sqlite_vec=True)
    try:
        assert store.backend_name == "NumpyStore"
        vec = l2_normalize(np.ones(EMBEDDING_DIM, dtype=np.float32))
        store.add_record("fresh:0", "fresh", 0.0, "moment", "fresh", vec)

        assert [r.record_id for r in store.query_topk(vec, k=5)] == ["fresh:0"]
    finally:
        store.close()


@pytest.mark.parity
@pytest.mark.skipif(not SQLITE_VEC_AVAILABLE, reason="sqlite-vec extension unavailable")
def test_memory_sqlite_vec_topk_matches_numpy(tmp_path: Path) -> None:
    """STORE-01 gate: sqlite-vec and numpy MemoryStore produce identical top-K.

    Two MemoryStore instances over tmp paths — one ``prefer_sqlite_vec=True``,
    one ``False`` — receive the same 100 records; ``query_topk(q, k=10)`` must
    return identical ``record_id`` rank order. Divergence = Mac↔Win parity
    break (P55).
    """
    records = _synthetic_records(seed=7)

    sq = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=True)
    np_ = MemoryStore(db_path=tmp_path / "memory_np.db", prefer_sqlite_vec=False)
    for rid, sid, ts, kind, sig, vec in records:
        sq.add_record(rid, sid, ts, kind, sig, vec)
        np_.add_record(rid, sid, ts, kind, sig, vec)

    rng = np.random.default_rng(11)
    q = l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))
    a = [r.record_id for r in sq.query_topk(q, k=10)]
    b = [r.record_id for r in np_.query_topk(q, k=10)]
    assert a == b, "Mac<->Win parity broken on memory.db"


@pytest.mark.parity
def test_tie_break_record_id_asc(tmp_path: Path) -> None:
    """Two records with identical cosine similarity tie-break record_id ASC.

    Pins that MemoryStore's ranking inherits ``cosine_topk``'s deterministic
    tie-break (id ASC via Timsort) — the same contract the library store has.
    Built over a numpy-backed MemoryStore so it runs everywhere (no extension).
    """
    v1 = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    v1[0] = 1.0  # orthogonal to the query
    v2 = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    v2[0] = -1.0  # also orthogonal to the query
    query = np.zeros(EMBEDDING_DIM, dtype=np.float32)
    query[1] = 1.0

    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    # "s1:zebra" / "s1:apple" — both cosine 0.0 → ASC by record_id.
    store.add_record("s1:zebra", "s1", 0.0, "moment", "z", v1)
    store.add_record("s1:apple", "s1", 1.0, "moment", "a", v2)
    result = [r.record_id for r in store.query_topk(query, k=2)]
    assert result == ["s1:apple", "s1:zebra"]


@pytest.mark.parity
def test_float32_round_trip_bit_identical(tmp_path: Path) -> None:
    """A stored 768-dim float32 vector round-trips byte-exact through MemoryStore.

    The stored vector that ``cosine_topk`` ranks against must be the same bytes
    that went in — any re-normalize/truncate inside ``memory/`` would introduce
    the 1-ULP drift the parity gate exists to catch. Asserted indirectly: the
    self-query of a record by its own (normalized) vector ranks that record #1
    with similarity ~1.0.
    """
    rng = np.random.default_rng(99)
    arr = l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))

    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    store.add_record("s1:0", "s1", 0.0, "moment", "only", arr)
    top = store.query_topk(arr, k=1)
    assert top[0].record_id == "s1:0"
    assert round(float(top[0].score), 5) == 1.0
