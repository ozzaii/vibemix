# SPDX-License-Identifier: Apache-2.0
"""Plan 28-03 — CLI integration tests for `vibemix library search`.

Subprocess-based; uses pre-populated query_cache so no Gemini API call is
ever attempted (proxy JWT can be a dummy when the cache short-circuits).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.cli


def _seed_query_cache(
    db_path: Path,
    query: str,
    snapshot: str,
    results: list[dict],
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS query_cache "
        "(key TEXT PRIMARY KEY, query_text TEXT NOT NULL, "
        "result_json TEXT NOT NULL, ts REAL NOT NULL)"
    )
    cache_key = hashlib.sha256(f"{query}|{snapshot}".encode()).hexdigest()
    conn.execute(
        "INSERT OR REPLACE INTO query_cache "
        "(key, query_text, result_json, ts) VALUES (?, ?, ?, ?)",
        (cache_key, query, json.dumps(results), time.time()),
    )
    conn.commit()
    conn.close()


def test_cli_does_not_break_help(tmp_path: Path) -> None:
    """`python -m vibemix library --help` exits 0."""
    proc = subprocess.run(
        [sys.executable, "-m", "vibemix", "library", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0
    assert "search" in proc.stdout
    assert "similar" in proc.stdout
    assert "budget" in proc.stdout


def test_cli_search_help(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "vibemix", "library", "search", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0
    assert "query" in proc.stdout
    assert "--k" in proc.stdout


def test_no_client_returns_json_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With NEITHER GEMINI_API_KEY nor VIBEMIX_PROXY_JWT, the client resolver
    returns a structured error (the CLI emits it as JSON + exits 1).

    In-process (not subprocess): ``_load_env_robust`` loads the repo-root
    ``.env`` for any ``python -m vibemix`` spawned from the repo (find_dotenv
    walks up from ``__main__.py``'s location, not CWD), so a subprocess can't
    reliably hit the no-creds branch. We test the resolver directly with a
    cleared env — the same code both ``search`` and ``similar`` route through
    (Fix 1).
    """
    from vibemix.__main__ import _library_genai_client

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("VIBEMIX_PROXY_JWT", raising=False)

    client, err = _library_genai_client()
    assert client is None
    assert err is not None
    # Error message names both supported credential sources.
    assert "GEMINI_API_KEY" in err["error"]
    assert "VIBEMIX_PROXY_JWT" in err["error"]
    assert err["results"] == []


def test_direct_key_builds_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fix 1: a bare GEMINI_API_KEY (no proxy JWT) yields a direct client —
    the local-user path that previously hard-failed with exit 1."""
    from vibemix.__main__ import _library_genai_client

    monkeypatch.setenv("GEMINI_API_KEY", "AIza-test-dummy-key")
    monkeypatch.delenv("VIBEMIX_PROXY_JWT", raising=False)

    client, err = _library_genai_client()
    assert err is None
    assert client is not None


def test_cli_no_library_cache_exits_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No library.pkl → exit 1 with JSON 'No library cache' error."""
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "VIBEMIX_PROXY_JWT": "test-token",
        "VIBEMIX_PROXY_BASE_URL": "http://test",
    }
    proc = subprocess.run(
        [sys.executable, "-m", "vibemix", "library", "search", "x"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert proc.returncode == 1
    parsed = json.loads(proc.stderr.strip())
    assert "No library cache" in parsed["error"]


def test_top_level_help_still_works(tmp_path: Path) -> None:
    """Verify `python -m vibemix --help` still works (live session path)."""
    proc = subprocess.run(
        [sys.executable, "-m", "vibemix", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0
    assert "--debrief" in proc.stdout
    assert "--wizard" in proc.stdout
