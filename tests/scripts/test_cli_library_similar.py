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


def test_cli_similar_no_jwt_exits_clean(tmp_path) -> None:
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
    assert "VIBEMIX_PROXY_JWT" in parsed["error"]


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
