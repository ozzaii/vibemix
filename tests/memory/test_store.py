# SPDX-License-Identifier: Apache-2.0
"""Phase 63 Plan 63-01 (Wave 0, RED-first) — MemoryStore unit contract.

Pins the STORE-01/02/03 behaviors of the (not-yet-built)
``vibemix.memory.store.MemoryStore``:

    * STORE-02  test_add_query_roundtrip     — add a record, query it back; the
                                               raw signature is returned verbatim
                                               and unmodified (raw-in/raw-out).
    * STORE-01  test_numpy_fallback          — forced ``prefer_sqlite_vec=False``;
                                               the store is fully functional on the
                                               numpy backend (Win-ARM64 parity path).
    * STORE-03  test_delete_cascade          — delete_session removes that session's
                                               vectors AND metadata atomically; the
                                               other session is untouched; no orphan
                                               record is retrievable.
    * STORE-03  test_session_id_path_traversal — a crafted session_id (``../`` /
                                               absolute path) is rejected before it
                                               reaches the filesystem (mirrors the
                                               recordings_index two-layer gate).

RED-first contract: ``from vibemix.memory.store import MemoryStore`` fails on
collection until Plans 02/03 build the package. That is the pinned contract.

Ranking everywhere routes through ``cosine_topk`` (imported from
``vibemix.library._cosine``) — no test here defines a bespoke KNN.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.memory.ingest_artifacts import ensure_ingest_db_for_store_path
from vibemix.memory.store import MemoryStore


def _vec(seed: int) -> np.ndarray:
    """A single active-dim L2-normalized float32 vector (deterministic)."""
    rng = np.random.default_rng(seed)
    return l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))


def test_add_query_roundtrip(tmp_path: Path) -> None:
    """STORE-02 — add one record, query it back; raw signature is verbatim.

    Raw-in/raw-out: whatever text signature went in comes back EXACTLY (no
    summarization, no LLM-extraction, no trimming). The self-query by the
    record's own vector ranks it #1.
    """
    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    raw_signature = "  build → 132 BPM, F#min → Am, layered hat at bar 17 (RAW)\n"
    vec = _vec(1)
    store.add_record("s1:0", "s1", 1234.5, "moment", raw_signature, vec)

    hits = store.query_topk(vec, k=1)
    assert len(hits) == 1
    rec = hits[0]
    assert rec.record_id == "s1:0"
    assert rec.session_id == "s1"
    assert rec.ts == 1234.5
    assert rec.kind == "moment"
    # The load-bearing raw-in/raw-out assertion: byte-for-byte unmodified.
    assert rec.signature == raw_signature


def test_numpy_fallback(tmp_path: Path) -> None:
    """STORE-01 — the store is fully functional on the numpy backend.

    ``prefer_sqlite_vec=False`` forces the numpy fallback (the Win-ARM64 path
    where the vec0 extension has no wheel). add_record + query_topk +
    delete_session must all work identically — there is no correctness penalty
    to the fallback (it shares the ``cosine_topk`` chokepoint).
    """
    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    for i in range(5):
        store.add_record(f"s1:{i}", "s1", float(i), "moment", f"sig {i}", _vec(i))

    q = _vec(2)
    hits = store.query_topk(q, k=3)
    assert len(hits) == 3
    # The exact-match self-query ranks the seeded record first.
    assert hits[0].record_id == "s1:2"
    assert store.delete_session("s1") == 5
    assert store.query_topk(q, k=3) == []


def test_delete_cascade(tmp_path: Path) -> None:
    """STORE-03 — delete_session removes vectors + metadata atomically.

    Two sessions are added; ``delete_session("s1")`` removes every s1 record
    from BOTH the vector backend and the moments metadata, leaves s2 fully
    intact, and leaves NO orphan retrievable by any query (no dangling vector
    with no metadata).
    """
    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    for i in range(3):
        store.add_record(f"s1:{i}", "s1", float(i), "moment", f"s1 {i}", _vec(i))
    for i in range(2):
        store.add_record(f"s2:{i}", "s2", float(i), "moment", f"s2 {i}", _vec(100 + i))

    removed = store.delete_session("s1")
    assert removed == 3

    # s2 survives intact, queryable.
    q = _vec(100)
    survivors = store.query_topk(q, k=10)
    survivor_ids = {r.record_id for r in survivors}
    assert survivor_ids == {"s2:0", "s2:1"}
    # No s1 record is retrievable from any query — no orphaned vectors.
    assert all(not r.record_id.startswith("s1:") for r in survivors)
    # Deleting an already-gone session is a no-op (idempotent), returns 0.
    assert store.delete_session("s1") == 0


def _seed_ingest_sidecar(db_path: Path, *session_ids: str) -> None:
    conn = ensure_ingest_db_for_store_path(db_path)
    try:
        for session_id in session_ids:
            conn.execute(
                "INSERT OR REPLACE INTO memory_ingested "
                "(session_id, ingested_at, sig_template_version) VALUES (?, ?, ?)",
                (session_id, 123.0, "test"),
            )
        for idx, session_id in enumerate(session_ids):
            conn.execute(
                "INSERT OR REPLACE INTO embed_cache (key, vector, ts) VALUES (?, ?, ?)",
                (
                    f"cache-{session_id}",
                    np.zeros(EMBEDDING_DIM, dtype=np.float32).tobytes(),
                    idx,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _sidecar_counts(db_path: Path) -> tuple[set[str], int]:
    conn = sqlite3.connect(str(db_path.parent / "memory_ingest.db"))
    try:
        markers = {
            str(row[0])
            for row in conn.execute("SELECT session_id FROM memory_ingested").fetchall()
        }
        cache_count = int(conn.execute("SELECT COUNT(*) FROM embed_cache").fetchone()[0])
        return markers, cache_count
    finally:
        conn.close()


def test_delete_cascade_purges_ingest_marker_and_content_hash_cache(tmp_path: Path) -> None:
    """STORE-03 — session erasure also clears ingest sidecar personal vectors.

    ``embed_cache`` is content-addressed, not session-addressed, so deleting one
    live session clears the whole ingest cache while leaving other session
    markers intact. Cache hits are cheaper than privacy surprises.
    """
    db_path = tmp_path / "memory.db"
    store = MemoryStore(db_path=db_path, prefer_sqlite_vec=False)
    store.add_record("s1:0", "s1", 1.0, "moment", "s1", _vec(1))
    store.add_record("s2:0", "s2", 2.0, "moment", "s2", _vec(2))
    _seed_ingest_sidecar(db_path, "s1", "s2")

    assert store.delete_session("s1") == 1

    markers, cache_count = _sidecar_counts(db_path)
    assert markers == {"s2"}
    assert cache_count == 0
    assert {row.session_id for row in store.query_topk(_vec(2), k=10)} == {"s2"}


def test_delete_session_purges_stale_ingest_marker_without_live_moments(tmp_path: Path) -> None:
    """STORE-03 — an already-evicted session can still shed stale ingest artifacts."""
    db_path = tmp_path / "memory.db"
    store = MemoryStore(db_path=db_path, prefer_sqlite_vec=False)
    _seed_ingest_sidecar(db_path, "s1")

    assert store.delete_session("s1") == 0

    markers, cache_count = _sidecar_counts(db_path)
    assert markers == set()
    assert cache_count == 0


@pytest.mark.parametrize(
    "bad_session_id",
    [
        "../etc/passwd",
        "../../s2",
        "/absolute/path",
        "s1/../s2",
        "..",
        "s1\x00",
    ],
)
def test_session_id_path_traversal(tmp_path: Path, bad_session_id: str) -> None:
    """STORE-03 security — a crafted session_id is rejected, never reaches FS.

    Mirrors the recordings_index two-layer gate (regex shape +
    ``is_relative_to`` after resolve). A traversal-shaped session_id passed to
    a path-touching operation must raise (ValueError) or be rejected — it must
    NOT escape ``app_data_dir()`` and must NOT silently create/delete files
    outside the sanctioned store.
    """
    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    with pytest.raises((ValueError, OSError)):
        store.add_record(
            f"{bad_session_id}:0", bad_session_id, 0.0, "moment", "x", _vec(0)
        )
