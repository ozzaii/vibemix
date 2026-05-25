# SPDX-License-Identifier: Apache-2.0
"""Cross-thread connection safety for the memory store (recall runs off-loop).

The recall path (``MemoryRecall.on_event``) and post-session ingest are
dispatched via ``loop.run_in_executor`` (see
``agent/dj_cohost.py::_maybe_dispatch_recall``) — i.e. they run on a worker
thread that is NOT the thread that constructed the ``MemoryStore``. Python's
``sqlite3`` rejects cross-thread use of a connection opened with the default
``check_same_thread=True``, raising ``ProgrammingError``. The library store
already opens with ``check_same_thread=False`` for the identical reason; these
tests pin the same posture for ``memory.db`` on BOTH backends.

Access is serialized by the caller (one recall dispatch at a time, gated by the
per-generation token + single in-flight reaction), so the connection is used
cross-thread but never concurrently — exactly the contract the library store
documents. We therefore assert single-worker cross-thread use does not raise,
not concurrent hammering.

Offline: no genai client, no network — synthetic float32 vectors only.
"""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.memory.store import MemoryStore


def _vec(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))


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


@pytest.mark.parametrize(
    "prefer_sqlite_vec",
    [
        pytest.param(
            True,
            marks=pytest.mark.skipif(
                not SQLITE_VEC_AVAILABLE,
                reason="sqlite-vec extension unavailable",
            ),
        ),
        False,
    ],
)
def test_query_topk_from_worker_thread(
    tmp_path: Path, prefer_sqlite_vec: bool
) -> None:
    """A store built on the main thread is queried from a worker thread.

    Mirrors the production recall dispatch: construct + seed on the main thread,
    then ``query_topk`` inside a ``run_in_executor``-style worker. With the
    default ``check_same_thread=True`` this raises ``sqlite3.ProgrammingError``;
    with the fix it returns the seeded record. Exercised on BOTH the sqlite-vec
    and numpy backends (the numpy path uses a sibling ``memory_moments.db``
    connection that needs the same flag).
    """
    store = MemoryStore(
        db_path=tmp_path / "memory.db", prefer_sqlite_vec=prefer_sqlite_vec
    )
    vec = _vec(1)
    # Seed on the main (constructing) thread.
    store.add_record("s1:0", "s1", 10.0, "coach_line", "past blend", vec)

    def _worker() -> list:
        # query_topk touches BOTH the vector backend (load_all) AND the moments
        # connection (_join_moment) — the cross-thread surfaces.
        return store.query_topk(vec, k=1, exclude_session="other-session")

    with ThreadPoolExecutor(max_workers=1) as pool:
        hits = pool.submit(_worker).result()

    assert len(hits) == 1
    assert hits[0].record_id == "s1:0"
    assert hits[0].signature == "past blend"
    store.close()


@pytest.mark.parametrize(
    "prefer_sqlite_vec",
    [
        pytest.param(
            True,
            marks=pytest.mark.skipif(
                not SQLITE_VEC_AVAILABLE,
                reason="sqlite-vec extension unavailable",
            ),
        ),
        False,
    ],
)
def test_add_and_delete_from_worker_thread(
    tmp_path: Path, prefer_sqlite_vec: bool
) -> None:
    """Write + cascade-delete from a worker thread do not raise cross-thread.

    The ingest path writes on an executor thread; pin that ``add_record`` /
    ``delete_session`` over the cross-thread connection succeed (the
    ``check_same_thread=False`` posture), not just reads.
    """
    store = MemoryStore(
        db_path=tmp_path / "memory.db", prefer_sqlite_vec=prefer_sqlite_vec
    )

    def _worker() -> int:
        for i in range(3):
            store.add_record(
                f"s9:{i}", "s9", float(i), "coach_line", f"sig {i}", _vec(50 + i)
            )
        return store.delete_session("s9")

    with ThreadPoolExecutor(max_workers=1) as pool:
        removed = pool.submit(_worker).result()

    assert removed == 3
    assert store.query_topk(_vec(50), k=5) == []
    store.close()
