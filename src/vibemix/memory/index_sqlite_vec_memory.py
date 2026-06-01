# SPDX-License-Identifier: Apache-2.0
"""SqliteVecMemoryStore — sqlite-vec vec0 virtual table backend for memory.db.

A near-verbatim COPY of ``vibemix.library.index_sqlite_vec.SqliteVecStore``
(Phase 28 Plan 02) with exactly two deltas:

    1. The vec0 virtual table is named ``vec_memory`` instead of
       ``vec_library`` (every SQL string renamed). The memory layer lives in
       its own ``memory.db`` file with its own lifecycle — see
       ``63-RESEARCH.md`` §"Library vs Memory" — so its table must not collide
       with the library's ``vec_library``.
    2. A plain ``moments`` sibling table (record metadata) is created on the
       SAME connection in ``__init__`` so ``MemoryStore.add_record`` writes the
       vec0 vector and the metadata row over one connection. Note: ``add_batch``
       commits the vector BEFORE ``add_record`` writes the moments row — two
       commits, NOT one transaction. The ordering is vector-first, so a crash
       between them leaves at worst a reconcilable orphan vector (swept by
       ``reconcile_orphans``), never a metadata row pointing at a missing
       vector. (``delete_session`` IS one transaction here, because it stages
       the moments DELETE and lets ``delete``'s single commit close both.)
       See 63-RESEARCH.md §Pattern 2.

Per RESEARCH §Summary + Pitfall P55: sqlite-vec is **storage-only** in v1.
We do NOT use the extension's built-in KNN-style index lookup — that path can
produce platform-divergent rank orders for tied similarities. Instead we
``SELECT record_id, embedding ORDER BY record_id ASC``, deserialize blobs to
numpy, and run the shared ``cosine_topk`` from ``library/_cosine.py`` (imported
verbatim by ``MemoryStore`` — never forked here). No ``MATCH``, no
``vec_distance_cosine``, no ``ORDER BY distance`` appears in this module.

Wave 0 sqlite-vec ARM64 Win probe (Assumption A2): if ``sqlite_vec.load(db)``
raises (no extension wheel for the host), the constructor re-raises so
``store.open_memory_store()`` can fall through to the numpy backend. The load
happens in ``__init__``, NOT at import — importing this module never requires
the extension.

Single-writer invariant: ``self.db`` is the one connection owned by this
backend AND reused by ``MemoryStore`` for the ``moments`` table. There is no
second connection to ``memory.db`` on the sqlite-vec path, so vec0 + moments
writes share one transaction and never deadlock against each other.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
from pathlib import Path

import numpy as np
import sqlite_vec

from vibemix.library._cosine import EMBEDDING_DIM

logger = logging.getLogger(__name__)


class SqliteVecMemoryStore:
    """vec0-virtual-table backed memory store (sibling of ``SqliteVecStore``).

    Public interface (must match ``NumpyStore`` — the fallback backend):
        - ``add_batch(items)``
        - ``load_all() -> (list[str], np.ndarray)`` — ORDER BY record_id ASC
        - ``delete(record_ids)``
        - ``snapshot_hash() -> str``
        - ``close()``

    The ``moments`` sibling table created in ``__init__`` is owned/read/written
    by ``MemoryStore`` over ``self.db`` — this class only ensures it exists.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: the recall path (MemoryRecall.on_event) and
        # the post-session ingest run OFF the asyncio loop in
        # ``loop.run_in_executor`` worker threads (dj_cohost.py:_maybe_dispatch_
        # recall), while this connection is opened on the constructing thread.
        # Both touch ``self.db`` (vec_memory load_all/add/delete) and the shared
        # ``moments`` table from a DIFFERENT thread than the one that opened it.
        # Access is SERIALIZED by the caller (one recall dispatch at a time,
        # gated by the per-generation token + the single in-flight reaction), so
        # the connection is never used concurrently — only cross-thread. Mirrors
        # library/index_sqlite_vec.py:51 (the identical Viber-agent rationale).
        self.db = sqlite3.connect(str(self._db_path), check_same_thread=False)
        # Guard all post-connect work: on a host with no sqlite-vec extension
        # wheel (Win ARM64, Assumption A2 — the EXPECTED fallback path), the
        # ``sqlite_vec.load`` below re-raises so ``open_memory_store`` can fall
        # through to NumpyStore. The connection is already open by then, so we
        # MUST close it before the exception propagates — otherwise the
        # partially-constructed object is discarded with a live sqlite handle
        # (a leaked file handle on ``memory.db``, which on Windows can block a
        # later delete/replace). Close-then-re-raise on ANY failure here.
        try:
            self.db.enable_load_extension(True)
            # If the host has no sqlite-vec extension wheel, this raises and the
            # caller (open_memory_store) catches → numpy fallback. Assumption A2.
            sqlite_vec.load(self.db)
            self.db.enable_load_extension(False)
            self._create_vec_table(if_not_exists=True)
            # moments sibling table on the SAME connection so add_record commits
            # the vec0 vector and metadata row downstream. Plain sqlite — no
            # vec0 syntax.
            self._ensure_moments_schema()
            self._reconcile_declared_dim()
            self.db.commit()
        except Exception:
            try:
                self.db.close()
            finally:
                raise

    def _create_vec_table(self, *, if_not_exists: bool) -> None:
        clause = "IF NOT EXISTS " if if_not_exists else ""
        self.db.execute(
            f"CREATE VIRTUAL TABLE {clause}vec_memory USING vec0("
            f"record_id TEXT PRIMARY KEY, "
            f"embedding FLOAT[{EMBEDDING_DIM}] distance_metric=cosine"
            f")"
        )

    def _ensure_moments_schema(self) -> None:
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS moments ("
            "record_id  TEXT PRIMARY KEY, "
            "session_id TEXT NOT NULL, "
            "ts         REAL NOT NULL, "
            "kind       TEXT NOT NULL, "
            "signature  TEXT NOT NULL"
            ")"
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_moments_session "
            "ON moments(session_id)"
        )

    def _reconcile_declared_dim(self) -> None:
        declared = self.vector_dim()
        if declared is None or declared == EMBEDDING_DIM:
            return

        count = self.row_count()
        if count == 0:
            logger.warning(
                "memory vec table is empty but pinned at dim %s != EMBEDDING_DIM=%s "
                "— recreating it and clearing unbacked moments rows.",
                declared,
                EMBEDDING_DIM,
            )
            self.recreate_table()
            return

        raise RuntimeError(
            f"Memory store holds {count} vectors at dim {declared}, but current "
            f"ingest produces dim {EMBEDDING_DIM}. Refusing to mix dimensions "
            f"silently; migrate or wipe the stale memory.db before sqlite-vec "
            f"memory ingest resumes."
        )

    def add_batch(self, items: list[tuple[str, np.ndarray]]) -> None:
        if not items:
            return
        rows: list[tuple[str, bytes]] = []
        for rid, vec in items:
            assert vec.dtype == np.float32, (
                f"SqliteVecMemoryStore.add_batch: {rid!r} vector must be "
                f"float32, got {vec.dtype}"
            )
            assert vec.shape == (EMBEDDING_DIM,), (
                f"SqliteVecMemoryStore.add_batch: {rid!r} vector must be "
                f"({EMBEDDING_DIM},), got {vec.shape}"
            )
            rows.append((rid, vec.tobytes()))
        # vec0 doesn't support INSERT OR REPLACE on the virtual-table layer
        # uniformly; do delete-then-insert to make replace deterministic.
        ids_to_replace = [rid for rid, _ in rows]
        placeholders = ",".join("?" for _ in ids_to_replace)
        self.db.execute(
            f"DELETE FROM vec_memory WHERE record_id IN ({placeholders})",
            ids_to_replace,
        )
        self.db.executemany(
            "INSERT INTO vec_memory(record_id, embedding) VALUES (?, ?)",
            rows,
        )
        self.db.commit()

    def load_all(self) -> tuple[list[str], np.ndarray]:
        """Return (ids, vectors). ORDER BY record_id ASC for stable iteration."""
        rows = self.db.execute(
            "SELECT record_id, embedding FROM vec_memory ORDER BY record_id ASC"
        ).fetchall()
        if not rows:
            return [], np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
        ids = [r[0] for r in rows]
        vectors = np.stack(
            [np.frombuffer(r[1], dtype=np.float32) for r in rows]
        )
        return ids, vectors

    def vector_dim(self) -> int | None:
        """Return the declared ``FLOAT[N]`` dim of ``vec_memory``, or None."""
        row = self.db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='vec_memory'"
        ).fetchone()
        if not row or not row[0]:
            return None
        match = re.search(r"FLOAT\[(\d+)\]", row[0])
        return int(match.group(1)) if match else None

    def row_count(self) -> int:
        """Number of stored memory vectors."""
        return int(self.db.execute("SELECT COUNT(*) FROM vec_memory").fetchone()[0])

    def recreate_table(self) -> None:
        """Drop + recreate an empty stale vec table at the current EMBEDDING_DIM."""
        self.db.execute("DROP TABLE IF EXISTS vec_memory")
        self._create_vec_table(if_not_exists=False)
        # A clean vec wipe leaves any moments rows unbacked and unretrievable.
        self.db.execute("DELETE FROM moments")
        self.db.commit()

    def delete(self, record_ids: list[str]) -> None:
        if not record_ids:
            return
        placeholders = ",".join("?" for _ in record_ids)
        self.db.execute(
            f"DELETE FROM vec_memory WHERE record_id IN ({placeholders})",
            list(record_ids),
        )
        self.db.commit()

    def snapshot_hash(self) -> str:
        rows = self.db.execute(
            "SELECT record_id FROM vec_memory ORDER BY record_id ASC"
        ).fetchall()
        ids = [r[0] for r in rows]
        return hashlib.sha256(json.dumps(ids).encode("utf-8")).hexdigest()

    def close(self) -> None:
        try:
            self.db.close()
        except Exception:
            pass
