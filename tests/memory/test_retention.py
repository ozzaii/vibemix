# SPDX-License-Identifier: Apache-2.0
"""Phase 63 Plan 63-01 (Wave 0) — retention contract (STORE-03).

Pins the memory retention sweep: when the per-install moment-count cap is
exceeded, eviction is OLDEST-SESSION-FIRST and WHOLE-SESSION (never partial).
A session is evicted via the same ``delete_session`` cascade (its vectors AND
moments rows go together — no orphans), and the newest sessions survive intact.

Mirrors the shipped recordings retention semantics
(``runtime/recordings_index.py::run_retention_sweep`` → ``RetentionSweepResult``):

    * A result object exposing how much was pruned (count of deleted records /
      sessions). The test reads ``.deleted`` (records pruned) — a thin
      RetentionSweepResult-style return.
    * An ``∞`` sentinel: a generous-enough cap short-circuits to a zero-eviction
      result without touching anything.

RED-first: ``from vibemix.memory.store import MemoryStore`` fails on collection
until Plans 02/03 build the package — that is the pinned contract.

STORE-04 note: the no-hardcoded-model-literal requirement is ALREADY covered by
the shipped ``tests/repo/test_model_literal_gate.py`` (it scans all of
``src/vibemix/`` including ``memory/``). It is intentionally NOT duplicated here.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.memory.store import MemoryStore


def _vec(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return l2_normalize(rng.standard_normal(EMBEDDING_DIM).astype(np.float32))


def _seed_sessions(store: MemoryStore) -> None:
    """Three sessions at strictly-increasing ts: oldest=s_old ... newest=s_new.

    s_old: 3 records (ts 100-102), s_mid: 3 records (ts 200-202),
    s_new: 3 records (ts 300-302). Nine records total.
    """
    for i in range(3):
        store.add_record(f"s_old:{i}", "s_old", 100.0 + i, "moment", f"old {i}", _vec(i))
    for i in range(3):
        store.add_record(f"s_mid:{i}", "s_mid", 200.0 + i, "moment", f"mid {i}", _vec(10 + i))
    for i in range(3):
        store.add_record(f"s_new:{i}", "s_new", 300.0 + i, "moment", f"new {i}", _vec(20 + i))


def _remaining_sessions(store: MemoryStore) -> set[str]:
    """Distinct session_ids still retrievable from the store."""
    q = _vec(99)
    return {r.session_id for r in store.query_topk(q, k=100)}


def test_retention_evicts_oldest_session_first_whole_session(tmp_path: Path) -> None:
    """STORE-03 — sweep evicts the oldest session WHOLE when over the cap.

    Cap = 6 moments; 9 are present across 3 sessions. The oldest session
    (``s_old``, 3 records) is evicted ENTIRELY to bring the count to 6; the two
    newer sessions survive intact. No partial-session state remains.
    """
    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    _seed_sessions(store)

    result = store.run_retention_sweep(max_moments=6)

    # The whole oldest session went — 3 records pruned.
    assert result.deleted == 3
    remaining = _remaining_sessions(store)
    assert remaining == {"s_mid", "s_new"}, "oldest-session-first eviction broken"
    # Whole-session: no partial s_old record survives.
    survivors = store.query_topk(_vec(99), k=100)
    assert all(not r.record_id.startswith("s_old:") for r in survivors)
    # The surviving sessions are still complete (3 each → 6 total).
    assert len(survivors) == 6


def test_retention_evicts_multiple_whole_sessions_when_needed(tmp_path: Path) -> None:
    """STORE-03 — a tight cap evicts as many WHOLE oldest sessions as needed.

    Cap = 2 moments; the only way to get at/under 2 with whole-session
    granularity (3 records each) is to evict the two oldest sessions, leaving
    the single newest session (3 records). Whole-session granularity is never
    violated even when it overshoots the raw count cap.
    """
    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    _seed_sessions(store)

    result = store.run_retention_sweep(max_moments=2)

    assert result.deleted == 6  # s_old + s_mid, whole
    remaining = _remaining_sessions(store)
    assert remaining == {"s_new"}, "should retain only the newest whole session"


def test_retention_infinite_cap_is_noop(tmp_path: Path) -> None:
    """STORE-03 — a generous/∞ cap short-circuits to zero eviction.

    Mirrors ``run_retention_sweep``'s ∞-sentinel: when the store is under the
    cap, the sweep prunes nothing and returns a zero result. Nothing is
    touched.
    """
    store = MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)
    _seed_sessions(store)

    result = store.run_retention_sweep(max_moments=10_000)

    assert result.deleted == 0
    assert _remaining_sessions(store) == {"s_old", "s_mid", "s_new"}
    assert len(store.query_topk(_vec(99), k=100)) == 9
