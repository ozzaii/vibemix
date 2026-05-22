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
      ``self.db`` connection (atomic vec0 + metadata writes, single-writer). On
      the numpy path (no sqlite file in the ``.npy`` sidecars) it lives in a
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
import sys
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
            print(
                "-> memory store: backend=SqliteVecMemoryStore reason=ok",
                file=sys.stdout,
                flush=True,
            )
            return backend
        except Exception as e:
            logger.warning(
                "memory backend probe failed: backend_probe_failed=sqlite_vec "
                "reason=%s — falling back to NumpyStore",
                e,
            )
            print(
                f"-> memory store: backend=NumpyStore "
                f"reason=sqlite_vec_unavailable ({e})",
                file=sys.stdout,
                flush=True,
            )

    parent = db_path.parent
    backend = NumpyStore(
        vectors_path=parent / "memory_vectors.npy",
        ids_path=parent / "memory_ids.json",
    )
    print(
        "-> memory store: backend=NumpyStore reason=preferred",
        file=sys.stdout,
        flush=True,
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
            self._moments = sqlite3.connect(str(moments_path))
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

        Vector-first ordering (63-RESEARCH.md §Pattern 2 / Pitfall 3): write the
        vector via the backend FIRST, then the moments row, then commit. A crash
        between the two leaves at worst a vector with no metadata (reconcilable
        by a boot sweep), never a metadata row pointing at a missing vector.

        The float32 + (768,) dimension-drift guard lives in the backend's
        add_batch assert (and cosine_topk re-asserts at query time).
        """
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

        Minimal correct cascade: look up the session's record_ids in moments,
        delete them from the vector backend, delete the moments rows, single
        commit. Idempotent — deleting an already-gone session returns 0.

        Plan 03 (Wave 2) extends this with the path-traversal guard, the
        retention sweep, and orphan reconciliation.
        """
        rows = self._moments.execute(
            "SELECT record_id FROM moments WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        record_ids = [r[0] for r in rows]
        if not record_ids:
            return 0
        self._backend.delete(record_ids)
        self._moments.execute(
            "DELETE FROM moments WHERE session_id = ?", (session_id,)
        )
        self._moments.commit()
        return len(record_ids)

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
