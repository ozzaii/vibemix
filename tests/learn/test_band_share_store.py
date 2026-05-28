# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 02 — EXEMPLAR-01 ``band_share_store`` schema + upsert + top_for_band (RED-state stub).

The side-car ``band_shares`` table lives inside the EXISTING
``library-clap.db`` (single-DB lifecycle — same backup/rotate as the CLAP
vec0 table). vec0 virtual tables don't support ``ALTER TABLE ADD COLUMN``
(verified at ``index_sqlite_vec.py:122-127``); we use a plain sqlite3
side-car table joined by ``track_id``:

    CREATE TABLE IF NOT EXISTS band_shares (
        track_id   TEXT PRIMARY KEY,
        sub_share  REAL NOT NULL,
        low_share  REAL NOT NULL,
        mid_share  REAL NOT NULL,
        high_share REAL NOT NULL,
        kick_corr  REAL NOT NULL,
        updated_at REAL NOT NULL
    )

The 5 tests pin the upsert + top-K + kick-guard + band-allowlist + ordering
contract from 93-RESEARCH.md §Pattern 4.

REQ-ID: EXEMPLAR-01 (band-share scalar persistence + ranker query).
Downstream plan that flips this skip: **Plan 93-02**.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

try:
    from vibemix.learn.band_share_store import (  # Plan 93-02
        init_schema,
        open_default_db,
        top_for_band,
        upsert,
    )
except ImportError:
    pytest.skip(
        "tests/learn/test_band_share_store.py awaiting Plan 93-02 — "
        "band_share_store.py (schema + upsert + top_for_band).",
        allow_module_level=True,
    )


@pytest.fixture
def isolated_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> sqlite3.Connection:
    """Redirect ``DB_PATH`` to a tmp file so we never touch
    ``~/.cache/vibemix/library-clap.db``. Returns the initialized connection.
    """
    db_path = tmp_path / "library-clap.db"
    monkeypatch.setattr("vibemix.learn.band_share_store.DB_PATH", db_path)
    conn = sqlite3.connect(str(db_path))
    init_schema(conn)
    return conn


def test_upsert_then_top_for_band_roundtrip(isolated_db: sqlite3.Connection) -> None:
    """Insert 3 synthetic rows with varying ``low_share``; ``top_for_band``
    returns the two highest in DESC order with the kick-guard filter applied.
    """
    # Three rows with varying low_share; all under the kick_corr guard.
    upsert(isolated_db, "track:alpha", 0.10, 0.55, 0.25, 0.10, 0.20, 100.0)
    upsert(isolated_db, "track:beta",  0.05, 0.70, 0.15, 0.10, 0.30, 100.0)
    upsert(isolated_db, "track:gamma", 0.20, 0.30, 0.30, 0.20, 0.10, 100.0)

    rows = top_for_band(isolated_db, "low", k=2)
    assert len(rows) == 2, f"expected 2 rows, got {len(rows)}: {rows!r}"
    # Highest-low-share first: beta (0.70) > alpha (0.55) > gamma (0.30)
    assert rows[0][0] == "track:beta", f"top row should be track:beta, got {rows[0]!r}"
    assert rows[1][0] == "track:alpha", f"second row should be track:alpha, got {rows[1]!r}"
    # band_share + kick_corr returned as floats
    assert abs(rows[0][1] - 0.70) < 1e-6
    assert abs(rows[0][2] - 0.30) < 1e-6


def test_top_for_band_kick_guard_filters_correlated_tracks(
    isolated_db: sqlite3.Connection,
) -> None:
    """A track with ``kick_corr=0.95`` (above the 0.8 guard threshold)
    must be EXCLUDED even if it has the highest mid_share."""
    # The kick-spillover track — high mid_share, BUT kick_corr too high.
    upsert(isolated_db, "track:kicky", 0.40, 0.30, 0.80, 0.10, 0.95, 100.0)
    # The legit mid-band track — similar mid_share, kick_corr below guard.
    upsert(isolated_db, "track:legit", 0.10, 0.20, 0.70, 0.30, 0.30, 100.0)

    rows = top_for_band(isolated_db, "mid")
    track_ids = [r[0] for r in rows]
    assert "track:legit" in track_ids, "legit mid-band track must be present"
    assert "track:kicky" not in track_ids, (
        "compressed-kick track (kick_corr=0.95) must be excluded by the "
        "kick guard at top_for_band"
    )


def test_top_for_band_unknown_band_raises_value_error(
    isolated_db: sqlite3.Connection,
) -> None:
    """``top_for_band(conn, 'ultrasonic')`` must raise ``ValueError`` —
    the band-allowlist is ``{'sub', 'low', 'mid', 'high'}`` only."""
    with pytest.raises(ValueError, match="ultrasonic"):
        top_for_band(isolated_db, "ultrasonic")


def test_top_for_band_tie_break_by_track_id_alphabetical(
    isolated_db: sqlite3.Connection,
) -> None:
    """Two rows identical on the band-share column → alphabetically
    earliest ``track_id`` wins. Determinism contract per CONTEXT §discretion.
    """
    upsert(isolated_db, "track:zulu",   0.10, 0.50, 0.30, 0.10, 0.20, 100.0)
    upsert(isolated_db, "track:alpha",  0.10, 0.50, 0.30, 0.10, 0.20, 100.0)
    rows = top_for_band(isolated_db, "low", k=2)
    assert rows[0][0] == "track:alpha", (
        f"tie-break should pick alphabetically earliest track_id; got {rows!r}"
    )
    assert rows[1][0] == "track:zulu"


def test_upsert_idempotent_on_conflict(isolated_db: sqlite3.Connection) -> None:
    """Second upsert with the same ``track_id`` overwrites the first row —
    the ``ON CONFLICT(track_id) DO UPDATE SET ...`` clause from Pattern 4.
    Re-ingests must NOT duplicate rows.
    """
    upsert(isolated_db, "track:x", 0.10, 0.20, 0.30, 0.40, 0.5, 100.0)
    upsert(isolated_db, "track:x", 0.99, 0.01, 0.00, 0.00, 0.1, 200.0)
    rows = top_for_band(isolated_db, "sub", k=10)
    # Only one row for track:x, and it reflects the LATEST values.
    matching = [r for r in rows if r[0] == "track:x"]
    assert len(matching) == 1, f"upsert must be idempotent on PK; got {rows!r}"
    assert abs(matching[0][1] - 0.99) < 1e-6, (
        f"second upsert must overwrite sub_share; got {matching[0]!r}"
    )
