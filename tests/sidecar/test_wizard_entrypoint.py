# SPDX-License-Identifier: Apache-2.0
"""Pin the ``--wizard`` CLI flag plumbing.

Phase 11 Wave 1 stubbed ``_run_wizard_stub`` and asserted "not yet
implemented" on stderr. Phase 11 Wave 4 replaces the stub with the real
``vibemix.runtime.wizard.run_wizard`` which opens the WS bus on
``127.0.0.1:8765`` and runs until SIGTERM. Consequently:

* ``--help`` and ``--version`` MUST still exit 0 instantly — argparse's
  ``action="version"`` short-circuits before the wizard is touched.
* ``--wizard`` now runs forever. We launch it, confirm the "wizard boot"
  stderr banner appears, then SIGTERM it so the test finishes deterministically.

These invariants survive Wave 4 with the new runtime semantics.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_module(args: list[str], *, timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    """Invoke ``python -m vibemix`` with the given args from the repo root."""
    return subprocess.run(
        [sys.executable, "-m", "vibemix", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=_REPO_ROOT,
        check=False,
    )


def test_help_advertises_wizard_flag() -> None:
    """``python -m vibemix --help`` MUST advertise ``--wizard``."""
    proc = _run_module(["--help"])
    assert proc.returncode == 0, f"--help exited {proc.returncode}: {proc.stderr}"
    assert "--wizard" in proc.stdout, f"--wizard missing from help output:\n{proc.stdout}"


def test_help_exit_code_is_zero() -> None:
    """``--help`` is a standard query — non-zero exit would break CI
    `grep` invocations used by other tests + the build_sidecar smoke test.
    """
    proc = _run_module(["--help"])
    assert proc.returncode == 0


def test_version_flag_still_works() -> None:
    """``--version`` was the original CLI surface; adding ``--wizard``
    must not break it (regression guard)."""
    proc = _run_module(["--version"])
    assert proc.returncode == 0
    assert "vibemix" in proc.stdout.lower(), f"--version stdout: {proc.stdout}"


@pytest.mark.parametrize("args", [["--help"], ["--version"]])
def test_short_running_flags_never_hang(args: list[str]) -> None:
    """``--help`` and ``--version`` MUST return within the short timeout
    — they short-circuit argparse before the wizard runtime is even
    imported."""
    proc = _run_module(args, timeout=10.0)
    assert proc.returncode == 0, f"flag {args!r} exited {proc.returncode}"


@pytest.mark.macos_audio
def test_wizard_starts_and_terminates_cleanly() -> None:
    """``python -m vibemix --wizard`` opens the WS bus, then exits cleanly
    on SIGTERM.

    Marked ``macos_audio`` because it binds port 8765 (live integration
    test, not a CI gate). On CI the test_wizard_loop_ipc.py covers the
    handler dispatch path without standing up the real WS server.
    """
    proc = subprocess.Popen(
        [sys.executable, "-m", "vibemix", "--wizard"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=_REPO_ROOT,
        text=True,
    )
    try:
        # Wait for the boot banner — wizard prints "-> wizard boot" once.
        deadline = time.monotonic() + 5.0
        boot_seen = False
        while time.monotonic() < deadline:
            # Non-blocking poll. We can't readline because the wizard is
            # still running; instead we poll until the process has emitted
            # the banner via a quick check.
            if proc.stderr is None:
                break
            line = proc.stderr.readline()
            if not line:
                time.sleep(0.05)
                continue
            if "wizard boot" in line:
                boot_seen = True
                break
        assert boot_seen, "wizard banner not seen within 5s"
    finally:
        # Deliver SIGTERM so the wizard exits cleanly.
        try:
            os.kill(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5.0)
    # Acceptable exit: 0 (clean asyncio shutdown via signal handler) or
    # -15 (SIGTERM delivered before the asyncio loop could process it —
    # equivalent for our purposes; the wizard never crashed unexpectedly).
    assert proc.returncode in (0, -signal.SIGTERM), (
        f"--wizard exited {proc.returncode} (expected 0 or -SIGTERM)"
    )
