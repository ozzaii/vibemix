# SPDX-License-Identifier: Apache-2.0
"""Ingest-owned memory artifact storage.

The memory ingest path keeps two sqlite tables next to ``memory.db``:

* ``memory_ingested`` marks a session as already processed.
* ``embed_cache`` stores content-hash vectors for deterministic signatures.

The cache key is intentionally content-addressed, not session-addressed, so a
single cache row may have been reused by multiple sessions. When a session is
erased we therefore clear the whole ingest embed cache rather than pretend we
can identify only that session's rows. This is conservative, cheap, and keeps
right-to-erasure semantics stronger than cache-hit performance.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import NamedTuple


class IngestArtifactPurgeResult(NamedTuple):
    """Rows removed from the ingest-owned sidecar database."""

    markers_deleted: int
    cache_rows_deleted: int


def ingest_db_path_for_store_path(store_db_path: Path) -> Path:
    """Return the ingest sidecar path for a ``memory.db`` path."""
    return Path(store_db_path).parent / "memory_ingest.db"


def ensure_ingest_db_for_store_path(store_db_path: Path) -> sqlite3.Connection:
    """Open the ingest sidecar sqlite DB and ensure its schema exists."""
    db_path = ingest_db_path_for_store_path(store_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    ensure_ingest_schema(conn)
    return conn


def ensure_ingest_schema(conn: sqlite3.Connection) -> None:
    """Create ingest marker/cache tables if absent."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS memory_ingested ("
        "session_id           TEXT PRIMARY KEY, "
        "ingested_at          REAL NOT NULL, "
        "sig_template_version TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS embed_cache ("
        "key TEXT PRIMARY KEY, "
        "vector BLOB NOT NULL, "
        "ts REAL NOT NULL"
        ")"
    )
    conn.commit()


def purge_session_ingest_artifacts(
    store_db_path: Path,
    session_id: str,
    *,
    clear_embed_cache: bool = False,
) -> IngestArtifactPurgeResult:
    """Delete ingest marker/cache artifacts associated with a session erasure.

    Args:
        store_db_path: Path to the owning ``memory.db``.
        session_id: Session being erased.
        clear_embed_cache: Force full cache clear because the caller erased live
            moments/vectors for this session. The cache is content-addressed,
            so selective per-session deletion is not sound.

    Returns:
        Counts of marker rows and cache rows removed. Missing sidecar DBs are a
        no-op and never create a new empty file.
    """
    db_path = ingest_db_path_for_store_path(store_db_path)
    if not db_path.exists():
        return IngestArtifactPurgeResult(0, 0)

    conn = sqlite3.connect(str(db_path))
    try:
        ensure_ingest_schema(conn)
        marker_cur = conn.execute(
            "DELETE FROM memory_ingested WHERE session_id = ?",
            (session_id,),
        )
        markers_deleted = max(0, marker_cur.rowcount)
        cache_rows_deleted = 0
        if clear_embed_cache or markers_deleted:
            cache_cur = conn.execute("DELETE FROM embed_cache")
            cache_rows_deleted = max(0, cache_cur.rowcount)
        conn.commit()
        return IngestArtifactPurgeResult(markers_deleted, cache_rows_deleted)
    finally:
        conn.close()


__all__ = [
    "IngestArtifactPurgeResult",
    "ensure_ingest_db_for_store_path",
    "ensure_ingest_schema",
    "ingest_db_path_for_store_path",
    "purge_session_ingest_artifacts",
]
