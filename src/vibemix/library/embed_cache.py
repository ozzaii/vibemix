# SPDX-License-Identifier: Apache-2.0
"""Shared SQLite cache helpers for library embeddings."""

from __future__ import annotations

import sqlite3

from vibemix.library.cache_paths import EMBED_CACHE_DB_PATH


def open_default_cache_db() -> sqlite3.Connection:
    """Open the default ~/.cache/vibemix/embeddings.db with schema init."""
    EMBED_CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(EMBED_CACHE_DB_PATH))
    init_cache_schema(conn)
    return conn


def init_cache_schema(conn: sqlite3.Connection) -> None:
    """Create the embed_cache table if it is absent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embed_cache (
            key TEXT PRIMARY KEY,
            vector BLOB NOT NULL,
            ts REAL NOT NULL
        )
        """
    )
    conn.commit()


__all__ = ["init_cache_schema", "open_default_cache_db"]
