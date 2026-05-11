# SPDX-License-Identifier: Apache-2.0
"""LIVE-01 — opt-in live smoke test (Kaan-only).

This test is GATED behind both ``@pytest.mark.macos_audio`` AND the
``VIBEMIX_LIVE_SMOKE=1`` env var. By default it skips with a clear
instruction message. When enabled it spawns ``python -m vibemix`` as a
subprocess, lets it run for ~5 seconds with real BlackHole + DDJ-FLX4 +
AI Capture devices, then sends SIGINT and asserts:

1. Process exits cleanly within 10s (no orphan threads or stuck loops).
2. A new ``recordings/<YYYYMMDD-HHMMSS>/`` session directory appears.

To run manually:
    VIBEMIX_LIVE_SMOKE=1 uv run pytest -m macos_audio tests/test_main_live.py
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.mark.macos_audio
def test_live_startup_shutdown():
    """LIVE-01: live smoke — Kaan-only opt-in via env var."""
    if not os.environ.get("VIBEMIX_LIVE_SMOKE"):
        pytest.skip(
            "Live smoke is opt-in. Run with: "
            "VIBEMIX_LIVE_SMOKE=1 uv run pytest -m macos_audio tests/test_main_live.py"
        )

    rec_dir = Path("recordings")
    pre_existing = set()
    if rec_dir.is_dir():
        pre_existing = {p.name for p in rec_dir.iterdir() if p.is_dir()}

    # Spawn python -m vibemix
    proc = subprocess.Popen(
        [sys.executable, "-m", "vibemix"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        time.sleep(5.0)
        # Process should still be running after 5s
        assert proc.poll() is None, (
            f"vibemix exited too early: code={proc.returncode}, "
            f"stderr={proc.stderr.read().decode() if proc.stderr else ''}"
        )

        # Send SIGINT
        proc.send_signal(signal.SIGINT)

        # Wait up to 10s for clean exit
        try:
            ret = proc.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("vibemix did not exit within 10s of SIGINT")

        # SIGINT typically returns 0 (KeyboardInterrupt swallowed by cli_entry)
        assert ret == 0, f"unexpected exit code {ret}"

        # Verify a new session dir appeared
        assert rec_dir.is_dir(), "recordings/ directory missing"
        post = {p.name for p in rec_dir.iterdir() if p.is_dir()}
        new_sessions = post - pre_existing
        assert len(new_sessions) >= 1, "no new session directory created"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
