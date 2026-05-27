# SPDX-License-Identifier: Apache-2.0
"""Phase 63 Plan 63-03 (Wave 2) — memory retention sweep (STORE-03).

A behavioral mirror of ``runtime/recordings_index.py::run_retention_sweep``
applied to the memory layer: when a per-install budget is exceeded, evict WHOLE
sessions OLDEST-FIRST (never partial-session) so ``memory.db`` cannot grow
unbounded (T-63-10) and so embeddings are subject to the same durable-data
retention contract as the raw recordings artifacts (T-63-09).

Two budget axes, both optional:

    * ``max_age_days`` — evict any session whose NEWEST moment is older than the
      cutoff (the session is stale wholesale).
    * ``max_moments`` — after the age pass, while the total moment count still
      exceeds the cap, evict the oldest remaining session, one whole session at
      a time. Whole-session granularity can overshoot the raw count cap (a cap
      of 2 with 3-record sessions retains the single newest 3-record session) —
      that is correct: a session is atomic, never split.

Both-caps-``None``/∞ short-circuits to a zero-eviction no-op (mirrors the
recordings ``∞``-sentinel stop) without touching the store.

Every eviction routes EXCLUSIVELY through ``store.delete_session`` — there is no
second ranking path and no partial-session delete. The sweep is best-effort:
a single ``delete_session`` failure logs and continues (one stuck session must
not abort the whole sweep). It is intended to be called at boot + session-close
by the runtime; the call-site wiring is the runtime's concern (deferred — see
63-03-PLAN §scope note). This module imports NOTHING from the live reaction
path (coach loop / MusicState / ws_bus / agent / prompts) — pure storage spine.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:  # pragma: no cover - typing only, no runtime import
    from vibemix.memory.store import MemoryStore

logger = logging.getLogger(__name__)

# Claude's-discretion defaults (63-03-PLAN / CONTEXT recommended ranges):
# ~10,000 moments and ~180 days. Per-install overridable by the caller.
DEFAULT_MAX_MOMENTS = 10_000
DEFAULT_MAX_AGE_DAYS = 180

_SECONDS_PER_DAY = 86_400.0


class RetentionSweepResult(NamedTuple):
    """Result of one memory retention sweep pass.

    Mirrors ``recordings_index.RetentionSweepResult`` in spirit (a thin,
    tuple-iterable summary of what was pruned), adapted to whole-session
    eviction:

    Attributes:
        deleted: total number of MOMENTS pruned across all evicted sessions
            (the headline count the retention UI / events line surfaces). 0 on
            the ∞-sentinel short-circuit or when already under budget.
        deleted_sessions: the session_ids that were evicted, oldest-first.
    """

    deleted: int
    deleted_sessions: list[str]


def run_memory_retention_sweep(
    store: MemoryStore,
    *,
    max_moments: int | None = DEFAULT_MAX_MOMENTS,
    max_age_days: int | None = DEFAULT_MAX_AGE_DAYS,
    now: float | None = None,
) -> RetentionSweepResult:
    """Evict whole sessions oldest-first until under the count/age budget.

    Args:
        store: the ``MemoryStore`` to sweep. Eviction routes through
            ``store.delete_session`` (atomic cascade — vectors + moments).
        max_moments: count cap. While the total moment count exceeds this,
            evict the oldest remaining whole session. ``None`` disables the
            count axis.
        max_age_days: age cap. Evict any session whose newest moment ts is
            older than ``now - max_age_days``. ``None`` disables the age axis.
        now: unix epoch seconds for the age cutoff (defaults to
            ``time.time()``; injectable for tests).

    Returns:
        ``RetentionSweepResult(deleted, deleted_sessions)``.

    Both caps ``None`` ⇒ ∞ short-circuit (no-op). Best-effort per session:
    a ``delete_session`` failure on one session logs and the sweep continues.
    """
    # ∞-sentinel short-circuit: nothing to bound → never read the store.
    if max_moments is None and max_age_days is None:
        return RetentionSweepResult(0, [])

    # Group the moments table by session: (oldest_ts, newest_ts, count).
    # Read-only aggregate over the connection MemoryStore owns; no live path.
    rows = store._moments.execute(
        "SELECT session_id, MIN(ts) AS min_ts, MAX(ts) AS max_ts, "
        "COUNT(*) AS n FROM moments GROUP BY session_id"
    ).fetchall()
    if not rows:
        return RetentionSweepResult(0, [])

    # sessions sorted OLDEST-FIRST by oldest ts (the eviction order).
    sessions = sorted(
        ((sid, float(min_ts), float(max_ts), int(n)) for sid, min_ts, max_ts, n in rows),
        key=lambda s: s[1],
    )
    total_moments = sum(s[3] for s in sessions)

    current = now if now is not None else time.time()
    evicted: list[str] = []
    pruned_moments = 0

    # ── Age pass: evict any whole session staler than the age cutoff ──────────
    # A session is stale when its NEWEST moment is older than the cutoff (the
    # whole session has had no activity since). Conservative: a session with any
    # recent moment is retained whole.
    #
    # Never-empty guard (IN-03): like the count pass, the age pass must NEVER
    # leave the store empty. ``sessions`` is oldest-first, so when EVERY session
    # is stale we still keep the newest one standing (the last element) — even a
    # fully-stale install retains its most-recent session rather than wiping to
    # zero. The newest session is the most likely to be re-touched and the
    # safest to preserve. A genuinely abandoned install simply keeps one stale
    # session until new activity ages it out via the normal path.
    remaining: list[tuple[str, float, float, int]] = []
    if max_age_days is not None:
        cutoff = current - (max_age_days * _SECONDS_PER_DAY)
        # The newest session (last, since sessions is oldest-first) is never
        # eligible for age eviction — it is the floor that keeps the store
        # non-empty.
        protected_sid = sessions[-1][0] if sessions else None
        for sid, min_ts, max_ts, n in sessions:
            if max_ts < cutoff and sid != protected_sid:
                if _evict(store, sid):
                    evicted.append(sid)
                    pruned_moments += n
                    total_moments -= n
                else:
                    remaining.append((sid, min_ts, max_ts, n))
            else:
                remaining.append((sid, min_ts, max_ts, n))
    else:
        remaining = list(sessions)

    # ── Count pass: while over the moment cap, drop the oldest whole session ──
    # Whole-session granularity: evict oldest-first, but NEVER evict the last
    # surviving session — when sessions are coarser than the cap (e.g. cap=2,
    # 3-record sessions) the newest whole session is retained even though it
    # overshoots the raw count. A retention sweep must never empty the store.
    if max_moments is not None:
        # remaining is already oldest-first (preserved from the sorted input).
        # survivors: sessions not evicted in the age pass, oldest-first.
        survivors = [s for s in remaining if s[0] not in set(evicted)]
        idx = 0
        # Leave at least one session standing: stop at len(survivors) - 1.
        while total_moments > max_moments and idx < len(survivors) - 1:
            sid, _min_ts, _max_ts, n = survivors[idx]
            idx += 1
            if _evict(store, sid):
                evicted.append(sid)
                pruned_moments += n
                total_moments -= n
            # On a failed delete, leave it and move on (best-effort) — the next
            # session may still bring us under the cap; if not, the next sweep
            # retries the stuck one.

    return RetentionSweepResult(pruned_moments, evicted)


def _evict(store: MemoryStore, session_id: str) -> bool:
    """Whole-session eviction via the store cascade. Best-effort (never raises)."""
    try:
        store.delete_session(session_id)
        return True
    except Exception as e:  # pragma: no cover - best-effort per-session
        logger.warning(
            "memory retention: delete_session(%r) failed, skipping: %s",
            session_id,
            e,
        )
        return False


__all__ = [
    "DEFAULT_MAX_AGE_DAYS",
    "DEFAULT_MAX_MOMENTS",
    "RetentionSweepResult",
    "run_memory_retention_sweep",
]
