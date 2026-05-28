# SPDX-License-Identifier: Apache-2.0
"""band_share_store — side-car sqlite table for per-track band-share scalars.

Lives INSIDE the same library-clap.db that the sqlite-vec store uses (single
backup/rotate lifecycle). NOT a vec0 virtual table — vec0 does not support
ALTER TABLE ADD COLUMN (verified at library/index_sqlite_vec.py:122-127), so
the band-share scalars live in a plain sqlite row table joined by track_id.

Phase 93 EXEMPLAR-01 + EXEMPLAR-02. Mirrors library/embed_cache.py shape.

Single-DB / two-tables rationale (Pitfall §M2):
  * The dim-mismatch wipe at index_sqlite_vec.py:145-160 (recreate_table) is
    table-scoped (``DROP TABLE IF EXISTS vec_library``) — it leaves
    ``band_shares`` alone. Orphaned rows are cheap (7 floats per row) and a
    re-ingest re-writes them.
  * Backup/rotate stays a single-file operation.
  * Future grounded queries can JOIN ``vec_library`` and ``band_shares`` on
    ``track_id`` for "tracks similar to X AND with high low-band" composite
    queries.

Security (STRIDE T-93-02-01 — SQL injection at top_for_band):
  * The ``band`` argument controls a COLUMN name, so pure ``?`` placeholder
    binding is impossible. Instead the band string is validated against a
    4-element allowlist (``_BAND_TO_COL``) BEFORE any SQL is built; the
    column name is only interpolated from that internal allowlist, never
    from user input.
  * ``k`` and ``max_kick_corr`` are bound through sqlite ``?`` placeholders.
"""
from __future__ import annotations

import sqlite3

from vibemix.library.index_sqlite_vec import DB_PATH  # shared library-clap.db

BAND_SHARE_TABLE = "band_shares"

# Allowlist mapping user-supplied band labels to the persisted column names.
# The dictionary-key lookup pattern validates THEN interpolates — never
# f-strings user input into the SQL body (STRIDE T-93-02-01 mitigation).
_BAND_TO_COL: dict[str, str] = {
    "sub": "sub_share",
    "low": "low_share",
    "mid": "mid_share",
    "high": "high_share",
}


def init_schema(conn: sqlite3.Connection) -> None:
    """Create the ``band_shares`` side-car table if it is absent.

    Mirror of library/embed_cache.py::init_cache_schema. NOT a vec0 virtual
    table — plain sqlite3 row table. Joined to ``vec_library`` by ``track_id``.
    Idempotent: ``CREATE TABLE IF NOT EXISTS`` is a no-op on the second call.
    """
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {BAND_SHARE_TABLE} (
            track_id   TEXT PRIMARY KEY,
            sub_share  REAL NOT NULL,
            low_share  REAL NOT NULL,
            mid_share  REAL NOT NULL,
            high_share REAL NOT NULL,
            kick_corr  REAL NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    conn.commit()


def open_default_db() -> sqlite3.Connection:
    """Open the shared ``library-clap.db`` with ``band_shares`` schema initialized.

    Path is the SAME as ``vibemix.library.index_sqlite_vec.DB_PATH`` —
    single-DB / two-tables (per the module docstring rationale). The
    sqlite-vec extension is NOT loaded here because ``band_shares`` is a
    plain row table; the vec0 virtual table only sees its own DDL.

    ``check_same_thread=False`` mirrors the SqliteVecStore connection at
    ``index_sqlite_vec.py:43-50`` so the Viber agent's tool-dispatch worker
    threads can read this store the same way they read the CLAP store.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    init_schema(conn)
    return conn


def upsert(
    conn: sqlite3.Connection,
    track_id: str,
    sub: float,
    low: float,
    mid: float,
    high: float,
    kick_corr: float,
    ts: float,
) -> None:
    """Insert or replace the band-share row for one track. Idempotent.

    Second call with the same ``track_id`` replaces all 5 floats + ``updated_at``
    via the ``ON CONFLICT(track_id) DO UPDATE SET ...`` clause — re-ingests
    therefore never duplicate rows.
    """
    conn.execute(
        f"""
        INSERT INTO {BAND_SHARE_TABLE}
            (track_id, sub_share, low_share, mid_share, high_share,
             kick_corr, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(track_id) DO UPDATE SET
            sub_share=excluded.sub_share,
            low_share=excluded.low_share,
            mid_share=excluded.mid_share,
            high_share=excluded.high_share,
            kick_corr=excluded.kick_corr,
            updated_at=excluded.updated_at
        """,
        (track_id, sub, low, mid, high, kick_corr, ts),
    )
    conn.commit()


def top_for_band(
    conn: sqlite3.Connection,
    band: str,
    k: int = 3,
    max_kick_corr: float = 0.8,
) -> list[tuple[str, float, float]]:
    """Top-k tracks for a band, excluding compressed-kick false-positives.

    Returns ``[(track_id, band_share, kick_corr), ...]`` ordered by
    ``band_share`` DESC, ties broken by ``track_id`` ASC for determinism
    (CONTEXT.md §discretion lock).

    Args:
        band: One of ``{"sub", "low", "mid", "high"}``. ``ValueError`` on
            anything else (V5 input validation; T-93-02-01 mitigation).
        k: Maximum number of rows to return.
        max_kick_corr: Compressed-kick guard threshold (CONTEXT 0.8 lock).
            Rows with ``kick_corr >= max_kick_corr`` are excluded. For
            ``mid`` lessons the guard is the load-bearing anti-slop gate;
            for ``sub``/``low`` it's still applied because a sub-heavy kick
            on a "low-band" lesson would teach the wrong band relationship
            (kick fundamentals dominate, not bass synth).
    """
    if band not in _BAND_TO_COL:
        raise ValueError(
            f"unknown band {band!r}; must be one of sub/low/mid/high"
        )
    # Column name is interpolated from the validated allowlist, NOT from
    # ``band`` directly — STRIDE T-93-02-01 mitigated.
    col = _BAND_TO_COL[band]
    sql = (
        f"SELECT track_id, {col}, kick_corr FROM {BAND_SHARE_TABLE} "
        "WHERE kick_corr < ? "
        f"ORDER BY {col} DESC, track_id ASC LIMIT ?"
    )
    rows = conn.execute(sql, (max_kick_corr, k)).fetchall()
    return [(r[0], float(r[1]), float(r[2])) for r in rows]


__all__ = [
    "BAND_SHARE_TABLE",
    "DB_PATH",
    "init_schema",
    "open_default_db",
    "top_for_band",
    "upsert",
]
