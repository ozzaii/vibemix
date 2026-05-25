"""Offline `library stats --json` CLI — indexed/backend/failed for the desktop header.

The handler must read ONLY the local store row count (no Gemini / genai /
httpx), emit valid JSON even when the store is empty/unavailable, and report
``indexed: N`` for an N-row store. These tests isolate ALL on-disk caches to
a tmp dir per CLAUDE.md (never touch the real ~/.cache/vibemix/library.db or
library.pkl).
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import numpy as np
import pytest

import vibemix.__main__ as m
from vibemix.library._cosine import EMBEDDING_DIM
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import LibraryStore


@pytest.fixture(autouse=True)
def _isolate_caches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # CLAUDE.md hard rule: never overwrite the real library.pkl.
    monkeypatch.setattr(
        RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl", raising=False
    )


def _seed_sqlite_store(db_path: Path, n: int) -> None:
    from vibemix.library.index_sqlite_vec import SqliteVecStore

    s = SqliteVecStore(db_path=db_path)
    items = [
        (f"t{i}", np.ones(EMBEDDING_DIM, dtype=np.float32) * (i + 1))
        for i in range(n)
    ]
    s.add_batch(items)
    s.close()


def _run_handler(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Invoke _cmd_library_stats with --json, capture + parse stdout."""
    buf = io.StringIO()
    monkeypatch.setattr(m.sys, "stdout", buf)
    rc = m._cmd_library_stats(argparse.Namespace(json=True))
    assert rc == 0
    return json.loads(buf.getvalue())


def test_seeded_store_reports_indexed_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vibemix.library.index_sqlite_vec import SqliteVecStore

    db_path = tmp_path / "library.db"
    _seed_sqlite_store(db_path, 5)

    # open_store() defaults to the real ~/.cache path; redirect it to our tmp
    # sqlite-vec store so the test is fully isolated + offline.
    monkeypatch.setattr(
        m,
        "open_store",
        lambda *a, **k: LibraryStore(SqliteVecStore(db_path=db_path)),
        raising=False,
    )
    monkeypatch.setattr(
        "vibemix.library.store.open_store",
        lambda *a, **k: LibraryStore(SqliteVecStore(db_path=db_path)),
    )

    payload = _run_handler(monkeypatch)
    assert payload == {"indexed": 5, "backend": "sqlite-vec", "failed": 0}


def test_empty_store_reports_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vibemix.library.index_sqlite_vec import SqliteVecStore

    db_path = tmp_path / "library.db"  # never seeded → empty table
    monkeypatch.setattr(
        "vibemix.library.store.open_store",
        lambda *a, **k: LibraryStore(SqliteVecStore(db_path=db_path)),
    )

    payload = _run_handler(monkeypatch)
    assert payload["indexed"] == 0
    assert payload["backend"] == "sqlite-vec"
    assert payload["failed"] == 0


def test_store_unavailable_emits_valid_json_no_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*a, **k):
        raise RuntimeError("store probe blew up")

    monkeypatch.setattr("vibemix.library.store.open_store", _boom)

    payload = _run_handler(monkeypatch)
    # Never crashes, never networks — header must still render.
    assert payload == {"indexed": 0, "backend": "unknown", "failed": 0}


def test_json_shape_keys_exact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vibemix.library.index_sqlite_vec import SqliteVecStore

    db_path = tmp_path / "library.db"
    _seed_sqlite_store(db_path, 2)
    monkeypatch.setattr(
        "vibemix.library.store.open_store",
        lambda *a, **k: LibraryStore(SqliteVecStore(db_path=db_path)),
    )

    payload = _run_handler(monkeypatch)
    assert set(payload.keys()) == {"indexed", "backend", "failed"}
    assert isinstance(payload["indexed"], int)
    assert isinstance(payload["failed"], int)
    assert payload["failed"] == 0


def test_subcommand_routes_through_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """End-to-end: `library stats --json` parses + dispatches to the handler."""
    from vibemix.library.index_sqlite_vec import SqliteVecStore

    db_path = tmp_path / "library.db"
    _seed_sqlite_store(db_path, 3)
    monkeypatch.setattr(
        "vibemix.library.store.open_store",
        lambda *a, **k: LibraryStore(SqliteVecStore(db_path=db_path)),
    )

    rc = m._run_library_cli(["stats", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload == {"indexed": 3, "backend": "sqlite-vec", "failed": 0}
