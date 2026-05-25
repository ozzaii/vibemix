# SPDX-License-Identifier: Apache-2.0
"""MemoryStore — backend-agnostic facade for the Phase 63 session-memory layer.

The single API surface for downstream plans (the recordings-index cascade hook,
the Phase 65 retrieval seam):

    store = MemoryStore()                       # durable memory.db, sqlite-vec primary
    store.add_record(rid, sid, ts, kind, sig, vec)
    hits = store.query_topk(query_vec, k=8)     # list[Record], raw signature verbatim
    store.delete_session(sid)                   # cascade vectors + metadata

Architecture (63-RESEARCH.md §Pattern 1, "compose-not-subclass"):
    * A ``library``-style vector backend (``SqliteVecMemoryStore`` primary,
      ``NumpyStore`` fallback) chosen by ``open_memory_store()`` — a clone of
      ``library/store.py::open_store`` pointed at ``memory.db``.
    * A ``moments`` metadata table. On the sqlite-vec path it lives in the SAME
      ``memory.db`` file and ``MemoryStore`` reuses the backend's single
      ``self.db`` connection (single-writer). NOTE: ``add_record`` is NOT one
      transaction — ``add_batch`` commits the vector first, then the moments row
      is written and committed (two commits). The ordering is vector-first, so a
      crash between them leaves at worst a reconcilable orphan vector. (Only
      ``delete_session`` is genuinely one transaction on this path.) On the numpy
      path (no sqlite file in the ``.npy`` sidecars) the moments table lives in a
      sibling ``memory_moments.db`` connection owned here.

Hard invariants (objective + 63-PATTERNS.md):
    * Ranking ALWAYS routes through the imported ``cosine_topk`` (P55 Mac/Win
      bit-identity). NEVER a native vec0 KNN / ``ORDER BY distance`` / ``MATCH``.
    * Raw-in/raw-out: a ``Record`` carries only the raw text signature +
      (session_id, ts, kind). No LLM-extracted "insight" — the store makes NO
      generation-model call; its only model call is the embedding call via the
      reused ``LibraryEmbedder`` (resolve("embedding") on FLEX, never a literal).
    * No live-reaction-path import (coach loop, MusicState, ws_bus, agent,
      prompts) — this module is a pure storage spine.
    * ``memory.db`` is durable user data: ``app_data_dir() / "memory.db"`` —
      NOT ``~/.cache`` (the library default is the anti-pattern we override).
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

# The single ranking chokepoint — IMPORTED VERBATIM, never forked (P55).
from vibemix.library._cosine import EMBEDDING_DIM, cosine_topk

# Embedding seam (the ONLY model call the store may make). Re-export so callers
# embed via resolve("embedding")/FLEX without reaching into library internals
# and without a hardcoded model literal. noqa: F401 — surfaced for downstream.
from vibemix.library.embed import LibraryEmbedder  # noqa: F401
from vibemix.library.index_numpy import NumpyStore

logger = logging.getLogger(__name__)

# Sentinel for run_retention_sweep: distinguishes "caller omitted this cap"
# (fall through to the retention module's production default) from an explicit
# ``None`` (disable that axis — the ∞-sentinel). Using a sentinel keeps the real
# budget constants off this module's import surface (they live in
# vibemix.memory.retention, imported lazily inside the method).
_UNSET: object = object()


def _memory_db_path() -> Path:
    """Resolve the durable ``memory.db`` path under ``app_data_dir()``.

    ``app_data_dir`` is imported LAZILY (function-local) on purpose: a
    module-level ``from vibemix.runtime.config_store import app_data_dir``
    triggers ``vibemix.runtime.__init__``, which eagerly imports the entire
    live reaction path (coach loop, ws_bus, state.refresh). That would violate
    the no-live-path import-boundary invariant (test_no_live_path_import.py).
    Deferring the import keeps ``import vibemix.memory.store`` a pure storage
    spine — no live-path module leaks into sys.modules.
    """
    from vibemix.runtime.config_store import app_data_dir

    # Durable user data — same base as recordings/. NOT ~/.cache (the library
    # default is the anti-pattern we override; see 63-PATTERNS.md drift note).
    return app_data_dir() / "memory.db"


def _validate_session_id(session_id: str, db_path: Path) -> None:
    """Reject a crafted ``session_id`` BEFORE it touches the filesystem.

    Two-layer path-traversal defense (mirrors
    ``recordings_index.py:388-401``):

      1. **Shape floor (generic).** Reject any ``session_id`` that is not a
         plain str, or that contains a path separator (``/`` or ``\\``), a
         ``..`` parent-dir token, a NUL byte, or a leading absolute/drive
         marker. This is the floor: the memory store does NOT shape-constrain
         ids to the recordings ``YYYYMMDD-HHMMSS`` form (any separator-free,
         non-``..``, non-NUL string is accepted), because it does not require
         recordings ids — but ANY id that reaches the filesystem (a sibling-DB
         filename, an ``app_data_dir`` subpath) must be a single safe path
         component, which this floor guarantees.

      2. **Containment check (defense in depth).** Resolve the id as a child of
         the store's parent dir and assert it stays inside that root via
         ``Path.resolve().is_relative_to(root.resolve())`` (symlink-escape-proof
         — ``resolve()`` follows symlinks before the comparison). Refuse the
         root itself.

    Raises ``ValueError`` on rejection — callers (``add_record`` /
    ``delete_session``) propagate it; the FS is never touched on a bad id.
    """
    if not isinstance(session_id, str) or not session_id:
        raise ValueError(f"invalid session_id (not a non-empty str): {session_id!r}")
    if (
        "/" in session_id
        or "\\" in session_id
        or ".." in session_id
        or "\x00" in session_id
        or session_id in (".", "")
    ):
        raise ValueError(
            f"session_id rejected (path-traversal shape): {session_id!r}"
        )
    # Defense in depth: it must resolve to a direct child of the store root and
    # never escape it. (The shape floor above already excludes separators/``..``
    # /absolute markers; this catches anything the floor missed, e.g. a
    # platform-specific drive token, and refuses the root itself.)
    root = db_path.parent
    try:
        candidate = (root / session_id).resolve()
        root_resolved = root.resolve()
    except OSError as e:  # pragma: no cover - resolve rarely raises here
        raise ValueError(f"session_id failed to resolve: {session_id!r}") from e
    if not candidate.is_relative_to(root_resolved) or candidate == root_resolved:
        raise ValueError(
            f"session_id escapes the store root: {session_id!r}"
        )


class _Backend(Protocol):  # pragma: no cover - protocol
    def add_batch(self, items: list[tuple[str, np.ndarray]]) -> None: ...
    def load_all(self) -> tuple[list[str], np.ndarray]: ...
    def delete(self, record_ids: list[str]) -> None: ...
    def snapshot_hash(self) -> str: ...
    def close(self) -> None: ...


@dataclass
class Record:
    """A single retrieved memory moment — raw fields only.

    Raw-in/raw-out: ``signature`` is the verbatim text that was stored, never
    an LLM-extracted summary. ``score`` is the cosine similarity from
    ``cosine_topk`` (only populated on query results). Signature *builders*
    live in Phase 64 — this is a passive data carrier.
    """

    record_id: str
    session_id: str
    ts: float
    kind: str
    signature: str
    score: float = 0.0


def open_memory_store(
    db_path: Path | None = None,
    prefer_sqlite_vec: bool = True,
) -> _Backend:
    """Probe sqlite-vec on the host; fall through to numpy on failure.

    Clone of ``library/store.py::open_store`` pointed at ``memory.db``. On any
    failure during ``SqliteVecMemoryStore`` construction (the
    ``sqlite_vec.load`` re-raise on a host with no extension wheel — Wave 0
    ARM64 Win probe, Assumption A2), log structured diagnostics and return a
    NumpyStore backend.

    ``db_path=None`` resolves the durable ``app_data_dir()/"memory.db"`` lazily
    (see ``_memory_db_path`` — the import is deferred to keep the live path out
    of ``import vibemix.memory.store``). Sidecar paths for the numpy fallback
    derive from ``db_path``'s parent so tests over ``tmp_path`` stay isolated
    (never touch the real app dir).
    """
    db_path = Path(db_path) if db_path is not None else _memory_db_path()
    if prefer_sqlite_vec:
        try:
            from vibemix.memory.index_sqlite_vec_memory import (
                SqliteVecMemoryStore,
            )

            backend: _Backend = SqliteVecMemoryStore(db_path=db_path)
            logger.info("memory store: backend=SqliteVecMemoryStore reason=ok")
            return backend
        except Exception as e:
            logger.warning(
                "memory backend probe failed: backend_probe_failed=sqlite_vec "
                "reason=%s — falling back to NumpyStore",
                e,
            )

    parent = db_path.parent
    backend = NumpyStore(
        vectors_path=parent / "memory_vectors.npy",
        ids_path=parent / "memory_ids.json",
    )
    logger.info(
        "memory store: backend=NumpyStore reason=%s",
        "preferred" if prefer_sqlite_vec is False else "sqlite_vec_unavailable",
    )
    return backend


class MemoryStore:
    """Storage-agnostic facade. Single chokepoint for top-K math (P55).

    Composes a vector backend (vec0 primary / numpy fallback) with a ``moments``
    metadata table. The store's ONLY model call is the embedding call (via the
    reused ``LibraryEmbedder``); it imports no live-reaction-path surface and
    calls no generation model.
    """

    def __init__(
        self,
        db_path: Path | None = None,
        prefer_sqlite_vec: bool = True,
    ) -> None:
        self._db_path = Path(db_path) if db_path is not None else _memory_db_path()
        self._backend = open_memory_store(
            self._db_path, prefer_sqlite_vec=prefer_sqlite_vec
        )

        # Own the moments connection. On the sqlite-vec path reuse the
        # backend's single connection (one file, one transaction, atomic). On
        # the numpy path open a sibling memory_moments.db (the .npy sidecars
        # can't hold a table).
        backend_db = getattr(self._backend, "db", None)
        if backend_db is not None:
            self._moments = backend_db
            self._owns_moments = False
        else:
            moments_path = self._db_path.parent / "memory_moments.db"
            moments_path.parent.mkdir(parents=True, exist_ok=True)
            # check_same_thread=False: the numpy-path moments connection is read
            # cross-thread for the same reason the sqlite-vec path is — the
            # recall/ingest paths run in run_in_executor worker threads while the
            # store is constructed on the loop thread. Serialized by the caller
            # (one recall dispatch / one ingest at a time), so cross-thread but
            # never concurrent. Mirrors SqliteVecMemoryStore.db + library store.
            self._moments = sqlite3.connect(
                str(moments_path), check_same_thread=False
            )
            self._owns_moments = True
            self._ensure_moments_schema()

    def _ensure_moments_schema(self) -> None:
        """Create the moments table on the numpy-path sibling connection.

        On the sqlite-vec path the backend already created this in __init__ on
        the shared connection; this only runs for the numpy fallback.
        """
        self._moments.execute(
            "CREATE TABLE IF NOT EXISTS moments ("
            "record_id  TEXT PRIMARY KEY, "
            "session_id TEXT NOT NULL, "
            "ts         REAL NOT NULL, "
            "kind       TEXT NOT NULL, "
            "signature  TEXT NOT NULL"
            ")"
        )
        self._moments.execute(
            "CREATE INDEX IF NOT EXISTS idx_moments_session "
            "ON moments(session_id)"
        )
        self._moments.commit()

    @property
    def backend_name(self) -> str:
        return type(self._backend).__name__

    def add_record(
        self,
        record_id: str,
        session_id: str,
        ts: float,
        kind: str,
        signature: str,
        embedding: np.ndarray,
    ) -> None:
        """Persist one moment: its embedding + raw metadata.

        Vector-first ordering, TWO commits — NOT one transaction (63-RESEARCH.md
        §Pattern 2 / Pitfall 3). ``add_batch`` writes AND commits the vector
        first; this method then writes and commits the moments row. So the
        sequence is: commit vector → write moments row → commit moments. There is
        no single transaction spanning both (``add_batch`` owns its own
        ``commit()``, and ``NumpyStore`` cannot honor a shared transaction
        anyway). Because the order is vector-first, a crash between the two
        commits leaves at worst a dangling vector with no metadata — reconcilable
        by ``reconcile_orphans`` (the documented-safe direction), never a
        metadata row pointing at a missing vector. Phase 64/65 maintainers MUST
        NOT assume atomicity here. (Contrast ``delete_session``, which IS one
        transaction on the sqlite-vec path.)

        The float32 + (768,) dimension-drift guard lives in the backend's
        add_batch assert (and cosine_topk re-asserts at query time).

        Path-traversal gate (T-63-07): ``session_id`` is validated BEFORE any
        write — a crafted id (``../``, absolute, separator, NUL) raises
        ``ValueError`` and nothing is persisted.
        """
        _validate_session_id(session_id, self._db_path)
        self._backend.add_batch([(record_id, embedding)])
        self._moments.execute(
            "INSERT OR REPLACE INTO moments "
            "(record_id, session_id, ts, kind, signature) "
            "VALUES (?, ?, ?, ?, ?)",
            (record_id, session_id, float(ts), kind, signature),
        )
        self._moments.commit()

    def query_topk(
        self,
        query_embedding: np.ndarray,
        k: int = 8,
        *,
        exclude_session: str | None = None,
    ) -> list[Record]:
        """Top-K cosine search → list[Record] (raw signature verbatim).

        Loads all vectors from the backend and ranks SOLELY through the imported
        ``cosine_topk`` (P55 — never ``ORDER BY distance``). ``exclude_session``
        omits one session's records before ranking; the parameter is part of the
        locked signature (Phase 65 uses it for current-session exclusion) and is
        correctly implemented now, accepted-and-usable.
        """
        ids, vectors = self._backend.load_all()

        if exclude_session is not None and ids:
            sessions = self._sessions_for(ids)
            keep = [
                i
                for i, rid in enumerate(ids)
                if sessions.get(rid) != exclude_session
            ]
            ids = [ids[i] for i in keep]
            vectors = vectors[keep] if keep else vectors[:0]

        hits = cosine_topk(query_embedding, vectors, ids, k)
        return [self._join_moment(rid, cos) for rid, cos in hits]

    def delete_session(self, session_id: str) -> int:
        """Remove every record of ``session_id`` from vectors + metadata.

        Path-traversal-defended (T-63-07): a crafted ``session_id`` is rejected
        by ``_validate_session_id`` BEFORE any lookup or delete — it never
        touches the filesystem.

        Atomic cascade (T-63-08, 63-RESEARCH.md §Pattern 4): look up the
        session's record_ids in ``moments``, ``DELETE FROM moments`` rows, then
        ``backend.delete(record_ids)`` — and on the sqlite-vec path both deletes
        live on the SAME connection (``self._moments is backend.db``) so the
        backend's commit closes ONE transaction covering both. On the numpy
        fallback (separate ``.npy`` + ``memory_moments.db`` files) a true shared
        transaction is impossible; the order (moments-row delete first, then
        vector delete) leaves at worst a reconcilable orphan vector — never a
        metadata row pointing at a missing vector — which ``reconcile_orphans``
        sweeps up (Pitfall 3). Idempotent: deleting an already-gone session
        returns 0 without a write.
        """
        _validate_session_id(session_id, self._db_path)
        rows = self._moments.execute(
            "SELECT record_id FROM moments WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        record_ids = [r[0] for r in rows]
        if not record_ids:
            return 0
        # Delete the moments rows on the moments connection WITHOUT committing
        # yet, so that on the sqlite-vec path (shared connection) the backend's
        # delete-commit below closes a single transaction over both deletes.
        self._moments.execute(
            "DELETE FROM moments WHERE session_id = ?", (session_id,)
        )
        if self._owns_moments:
            # numpy path: separate files — commit the metadata delete here; the
            # vector delete (a different file) commits independently below. The
            # vector-after-metadata ordering keeps any crash window reconcilable.
            self._moments.commit()
        # backend.delete commits its connection. On the sqlite-vec path that IS
        # self._moments, so this single commit also flushes the moments delete
        # staged above — one atomic transaction, no orphaned vectors.
        self._backend.delete(record_ids)
        return len(record_ids)

    def reconcile_orphans(self) -> int:
        """Drop vec records that have no matching ``moments`` row.

        The defensive backstop for the numpy-path vector-first write ordering
        (63-RESEARCH.md Pitfall 3) and any partially-applied cascade: a vector
        whose ``moments`` row is gone is a dangling, un-joinable record that
        ``query_topk`` would surface with an empty signature. Intended to run at
        boot.

        Loads all vec record_ids via ``backend.load_all()``, finds those with no
        ``moments`` row, and ``backend.delete(...)`` them in one transaction.
        Best-effort and transactional: it never raises on a single bad entry —
        a reconciliation pass must never block boot. Returns the count dropped.

        Direction is one-way by design: a ``moments`` row whose vector is
        missing is NOT touched here (that direction should not occur given the
        vector-first ``add_record`` ordering, and dropping live metadata would
        be the more destructive error). Imports nothing from the recordings
        index or the live reaction path.
        """
        try:
            ids, _vectors = self._backend.load_all()
        except Exception as e:  # pragma: no cover - load failure is non-fatal
            logger.warning("reconcile_orphans: backend load_all failed: %s", e)
            return 0
        if not ids:
            return 0
        live = self._sessions_for(ids)  # record_id -> session_id for ids WITH a row
        orphans = [rid for rid in ids if rid not in live]
        if not orphans:
            return 0
        try:
            self._backend.delete(orphans)
        except Exception as e:  # pragma: no cover - best-effort
            logger.warning(
                "reconcile_orphans: dropping %d orphan vectors failed: %s",
                len(orphans),
                e,
            )
            return 0
        logger.info("reconcile_orphans: dropped %d orphan vectors", len(orphans))
        return len(orphans)

    def run_retention_sweep(
        self,
        *,
        max_moments: int | None | object = _UNSET,
        max_age_days: int | None | object = _UNSET,
    ):
        """Evict whole sessions oldest-first under a count/age budget.

        Thin instance-method seam over ``vibemix.memory.retention``'s
        ``run_memory_retention_sweep`` — the eviction logic lives there (the
        recordings-sweep analog), this is the ergonomic call site
        (``store.run_retention_sweep(...)``). Imported lazily to keep
        ``retention`` off the ``import vibemix.memory.store`` hot path.

        Budget defaults: a no-arg ``store.run_retention_sweep()`` (the obvious
        boot call) MUST enforce the real ~10k/180d budget, NOT a silent no-op.
        Each cap is only forwarded when explicitly provided, so an omitted cap
        falls through to the module function's production default
        (``DEFAULT_MAX_MOMENTS`` / ``DEFAULT_MAX_AGE_DAYS``). Passing ``None``
        explicitly still disables that axis (the documented ∞-sentinel).
        """
        from vibemix.memory.retention import run_memory_retention_sweep

        kwargs = {}
        if max_moments is not _UNSET:
            kwargs["max_moments"] = max_moments
        if max_age_days is not _UNSET:
            kwargs["max_age_days"] = max_age_days
        return run_memory_retention_sweep(self, **kwargs)

    def close(self) -> None:
        if self._owns_moments:
            try:
                self._moments.close()
            except Exception:
                pass
        self._backend.close()

    # ─── Internal: moments joins ───────────────────────────────────────────

    def _sessions_for(self, record_ids: list[str]) -> dict[str, str]:
        """Map record_id → session_id for the given ids (exclude_session seam)."""
        if not record_ids:
            return {}
        placeholders = ",".join("?" for _ in record_ids)
        rows = self._moments.execute(
            f"SELECT record_id, session_id FROM moments "
            f"WHERE record_id IN ({placeholders})",
            list(record_ids),
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    def _join_moment(self, record_id: str, score: float) -> Record:
        """Join a ranked record_id back to its raw moments row → Record."""
        row = self._moments.execute(
            "SELECT session_id, ts, kind, signature FROM moments "
            "WHERE record_id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            # Orphaned vector (no metadata) — surface as a minimal Record so the
            # ranking stays honest; Plan 03's boot sweep reconciles these.
            return Record(
                record_id=record_id,
                session_id="",
                ts=0.0,
                kind="",
                signature="",
                score=float(score),
            )
        session_id, ts, kind, signature = row
        return Record(
            record_id=record_id,
            session_id=session_id,
            ts=float(ts),
            kind=kind,
            signature=signature,
            score=float(score),
        )


__all__ = [
    "MemoryStore",
    "Record",
    "open_memory_store",
    "EMBEDDING_DIM",
]
