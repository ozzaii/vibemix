# SPDX-License-Identifier: Apache-2.0
"""Plan 28-05 — CLI integration tests for `vibemix library similar`."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest


pytestmark = pytest.mark.cli


def test_cli_similar_help() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "vibemix", "library", "similar", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0
    assert "track_id" in proc.stdout
    assert "USER-ASKED" in proc.stdout


def test_cli_similar_without_jwt_uses_direct_key(tmp_path) -> None:
    """Fix 1: similar no longer hard-requires VIBEMIX_PROXY_JWT. With only a
    direct GEMINI_API_KEY (loaded from the repo-root .env by _load_env_robust,
    which finds it via __main__.py's location regardless of CWD/HOME), the
    command builds a direct client and proceeds — failing only later on the
    empty/missing library cache under the tmp HOME, NOT on a missing JWT.

    The pure no-creds error path is covered in-process by
    tests/scripts/test_cli_library_search.py::test_no_client_returns_json_error.
    """
    env = {**os.environ, "HOME": str(tmp_path)}
    env.pop("VIBEMIX_PROXY_JWT", None)
    proc = subprocess.run(
        [sys.executable, "-m", "vibemix", "library", "similar", "t000"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert proc.returncode == 1
    parsed = json.loads(proc.stderr.strip())
    # No JWT, but a direct key got us past client-build to the cache check.
    assert "VIBEMIX_PROXY_JWT" not in parsed["error"]
    assert "No library cache" in parsed["error"]


def test_cli_similar_no_library_exits_clean(tmp_path) -> None:
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "VIBEMIX_PROXY_JWT": "test-token",
    }
    proc = subprocess.run(
        [sys.executable, "-m", "vibemix", "library", "similar", "t000"],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert proc.returncode == 1
    parsed = json.loads(proc.stderr.strip())
    assert "No library cache" in parsed["error"]
