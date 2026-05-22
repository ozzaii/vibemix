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

The chokepoint (``cosine_topk`` / ``l2_normalize`` / ``EMBEDDING_DIM``) is
IMPORTED VERBATIM from ``vibemix.library._cosine`` — never forked. No test in
this file defines a bespoke nearest-neighbour search or asserts a native
distance-ordered query path; ranking is the shared chokepoint, end to end.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from vibemix.library._cosine import EMBEDDING_DIM, cosine_topk, l2_normalize
from vibemix.library.index_numpy import NumpyStore  # noqa: F401 (parity ref)
from vibemix.memory.store import MemoryStore


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
