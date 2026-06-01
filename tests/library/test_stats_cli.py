"""Offline `library stats --json` CLI for the desktop header.

The handler must read ONLY the local store row count (no Gemini / genai /
httpx), emit valid JSON even when the store is empty/unavailable, report
``indexed: N`` for an N-row store, and surface the active embedding
backend/dimension for the UI header. These tests isolate ALL on-disk caches to a
tmp dir per CLAUDE.md (never touch the real ~/.cache/vibemix/library.db or
library.pkl).
"""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path

import numpy as np
import pytest

import vibemix.__main__ as m
from vibemix.library._cosine import EMBED_BACKEND, EMBEDDING_DIM
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import LibraryStore

_TEST_CLAP_MODEL_PATH = "/tmp/vibemix-test-clap-onnx"


@pytest.fixture(autouse=True)
def _isolate_caches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # CLAUDE.md hard rule: never overwrite the real library.pkl.
    monkeypatch.setattr(
        RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl", raising=False
    )
    import vibemix.library.clap_engine as clap_engine

    monkeypatch.setattr(
        clap_engine,
        "onnx_model_status",
        lambda: {
            "installed": True,
            "path": _TEST_CLAP_MODEL_PATH,
            "missing": [],
        },
    )
    import vibemix.library.codex_curate as codex_curate
    import vibemix.library.setup_discovery as setup_discovery

    codex_home = tmp_path / "codex"
    codex_home.mkdir()
    (codex_home / "auth.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.delenv("VIBEMIX_LIBRARY_AGENT_BACKEND", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("VIBEMIX_PROXY_JWT", raising=False)
    monkeypatch.setattr(codex_curate, "find_codex", lambda codex_path=None: "/usr/bin/codex")
    monkeypatch.setattr(
        setup_discovery,
        "discover_library_setup_candidate_dicts",
        lambda *, max_candidates=5: [],
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


def _expected_payload(indexed: int, backend: str) -> dict:
    freshness = {
        "status": "not_indexed",
        "stale": False,
        "reason": "library_cache_missing",
        "age_days": 0,
        "cache_path": str(RekordboxLibrary.CACHE_PATH),
        "source_path": None,
        "source_age_days": None,
        "cache_mtime": None,
        "source_mtime": None,
    }
    return {
        "indexed": indexed,
        "backend": backend,
        "embedding_backend": EMBED_BACKEND,
        "embedding_dim": EMBEDDING_DIM,
        "clap_model_installed": True,
        "clap_model_path": _TEST_CLAP_MODEL_PATH,
        "clap_model_missing": [],
        "library_freshness": freshness,
        "library_freshness_status": "not_indexed",
        "library_stale": False,
        "library_staleness_reason": "library_cache_missing",
        "library_age_days": 0,
        "library_setup_candidates": [],
        "agent_backend": "codex",
        "agent_ready": True,
        "agent_status": "ready",
        "agent_hint": "",
        "failed": 0,
    }


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
    assert payload == _expected_payload(5, "sqlite-vec")


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
    assert payload["embedding_backend"] == EMBED_BACKEND
    assert payload["embedding_dim"] == EMBEDDING_DIM
    assert payload["failed"] == 0


def test_store_unavailable_emits_valid_json_no_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*a, **k):
        raise RuntimeError("store probe blew up")

    monkeypatch.setattr("vibemix.library.store.open_store", _boom)

    payload = _run_handler(monkeypatch)
    # Never crashes, never networks — header must still render.
    assert payload == _expected_payload(0, "unknown")


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
    assert set(payload.keys()) == {
        "indexed",
        "backend",
        "embedding_backend",
        "embedding_dim",
        "clap_model_installed",
        "clap_model_path",
        "clap_model_missing",
        "library_freshness",
        "library_freshness_status",
        "library_stale",
        "library_staleness_reason",
        "library_age_days",
        "library_setup_candidates",
        "agent_backend",
        "agent_ready",
        "agent_status",
        "agent_hint",
        "failed",
    }
    assert isinstance(payload["indexed"], int)
    assert isinstance(payload["embedding_backend"], str)
    assert isinstance(payload["embedding_dim"], int)
    assert isinstance(payload["clap_model_installed"], bool)
    assert isinstance(payload["clap_model_path"], str)
    assert isinstance(payload["clap_model_missing"], list)
    assert isinstance(payload["library_freshness"], dict)
    assert isinstance(payload["library_freshness_status"], str)
    assert isinstance(payload["library_stale"], bool)
    assert isinstance(payload["library_staleness_reason"], str)
    assert isinstance(payload["library_age_days"], int)
    assert isinstance(payload["library_setup_candidates"], list)
    assert isinstance(payload["agent_backend"], str)
    assert isinstance(payload["agent_ready"], bool)
    assert isinstance(payload["agent_status"], str)
    assert isinstance(payload["agent_hint"], str)
    assert isinstance(payload["failed"], int)
    assert payload["failed"] == 0


def test_agent_status_reports_codex_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibemix.library.codex_curate as codex_curate
    from vibemix.library.index_sqlite_vec import SqliteVecStore

    db_path = tmp_path / "library.db"
    monkeypatch.setattr(
        "vibemix.library.store.open_store",
        lambda *a, **k: LibraryStore(SqliteVecStore(db_path=db_path)),
    )
    monkeypatch.setattr(codex_curate, "find_codex", lambda codex_path=None: None)

    payload = _run_handler(monkeypatch)
    assert payload["agent_backend"] == "codex"
    assert payload["agent_ready"] is False
    assert payload["agent_status"] == "codex_not_installed"
    assert "codex login" in payload["agent_hint"]


def test_agent_status_ignores_stale_gemini_backend_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vibemix.library.index_sqlite_vec import SqliteVecStore

    db_path = tmp_path / "library.db"
    monkeypatch.setenv("VIBEMIX_LIBRARY_AGENT_BACKEND", "gemini")
    monkeypatch.setattr(
        "vibemix.library.store.open_store",
        lambda *a, **k: LibraryStore(SqliteVecStore(db_path=db_path)),
    )

    payload = _run_handler(monkeypatch)
    assert payload["agent_backend"] == "codex"
    assert payload["agent_ready"] is True
    assert payload["agent_status"] == "ready"
    assert payload["agent_hint"] == ""


def test_stats_surfaces_user_approved_library_setup_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibemix.library.setup_discovery as setup_discovery
    from vibemix.library.index_sqlite_vec import SqliteVecStore

    db_path = tmp_path / "library.db"
    candidate = {
        "kind": "music_folder",
        "path": str(tmp_path / "PSYMIND"),
        "confidence": "high",
        "reason": "bounded scan saw 42 supported audio files",
        "command": "uv run python -m vibemix library embed-folder PSYMIND",
        "audio_files_seen": 42,
        "import_action": {
            "type": "ipc.library.import",
            "payload": {"path": str(tmp_path / "PSYMIND"), "schema_version": "1"},
        },
    }
    monkeypatch.setattr(
        setup_discovery,
        "discover_library_setup_candidate_dicts",
        lambda *, max_candidates=5: [candidate],
    )
    monkeypatch.setattr(
        "vibemix.library.store.open_store",
        lambda *a, **k: LibraryStore(SqliteVecStore(db_path=db_path)),
    )

    payload = _run_handler(monkeypatch)

    assert payload["indexed"] == 0
    assert payload["library_freshness_status"] == "not_indexed"
    assert payload["library_setup_candidates"] == [candidate]


def test_stats_reports_stale_when_source_newer_than_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vibemix.library.index_sqlite_vec import SqliteVecStore

    db_path = tmp_path / "library.db"
    source = tmp_path / "collection.xml"
    source.write_text("<DJ_PLAYLISTS />", encoding="utf-8")
    old_mtime = 1_700_000_000.0
    new_mtime = old_mtime + 10.0
    os.utime(source, (old_mtime, old_mtime))
    lib = RekordboxLibrary()
    lib._write_cache(str(source), old_mtime)
    os.utime(source, (new_mtime, new_mtime))
    monkeypatch.setattr(
        "vibemix.library.store.open_store",
        lambda *a, **k: LibraryStore(SqliteVecStore(db_path=db_path)),
    )

    payload = _run_handler(monkeypatch)

    assert payload["library_freshness_status"] == "stale"
    assert payload["library_stale"] is True
    assert payload["library_staleness_reason"] == "source_newer_than_cache"
    assert payload["library_freshness"]["source_path"] == str(source)


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
    assert payload == _expected_payload(3, "sqlite-vec")
