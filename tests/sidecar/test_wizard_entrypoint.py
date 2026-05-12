# SPDX-License-Identifier: Apache-2.0
"""Phase 11 Wave 1 — pin the ``--wizard`` CLI flag plumbing.

Wave 4 replaces ``_run_wizard_stub`` with the real ``WizardLoop`` that
emits ``ipc.boot`` + ``ipc.status.tick``. Until then, this test pins:

1. ``--wizard`` appears in ``python -m vibemix --help`` so Wave 2's Tauri
   shell can confidently spawn ``vibemix-core --wizard``.
2. ``python -m vibemix --wizard`` exits cleanly within a short timeout
   with the "not yet implemented" stderr line.

Both invariants are necessary preconditions for the PyInstaller-built
binary to be useful to Wave 2.
"""

from __future__ import annotations

import subprocess
import sys
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
    """``python -m vibemix --help`` MUST advertise ``--wizard``.

    Wave 2's Tauri shell reads this to confirm the sidecar binary is the
    right version before spawning ``--wizard``. If the flag disappears,
    the wizard never launches.
    """
    proc = _run_module(["--help"])
    assert proc.returncode == 0, f"--help exited {proc.returncode}: {proc.stderr}"
    assert "--wizard" in proc.stdout, f"--wizard missing from help output:\n{proc.stdout}"


def test_wizard_stub_exits_cleanly() -> None:
    """``python -m vibemix --wizard`` MUST exit 0 within 5s with the
    "not yet implemented" placeholder line on stderr.

    Wave 4 tightens this assertion to check for ``ipc.boot`` emission.
    """
    proc = _run_module(["--wizard"], timeout=10.0)
    assert proc.returncode == 0, (
        f"--wizard exited {proc.returncode}\n"
        f"stdout: {proc.stdout}\n"
        f"stderr: {proc.stderr}"
    )
    assert "mode not yet implemented" in proc.stderr, (
        f"expected stub message on stderr, got:\n{proc.stderr}"
    )


def test_help_exit_code_is_zero() -> None:
    """``--help`` is a standard query — non-zero exit would break CI
    `grep` invocations used by other tests + the build_sidecar smoke test.
    """
    proc = _run_module(["--help"])
    assert proc.returncode == 0


def test_version_flag_still_works() -> None:
    """Phase 1's ``--version`` was the original CLI surface; ensure adding
    ``--wizard`` didn't break it (regression guard).
    """
    proc = _run_module(["--version"])
    assert proc.returncode == 0
    assert "vibemix" in proc.stdout.lower(), f"--version stdout: {proc.stdout}"


@pytest.mark.parametrize("args", [["--help"], ["--wizard"], ["--version"]])
def test_short_running_flags_never_hang(args: list[str]) -> None:
    """All three flags MUST return within the short timeout — never block
    on stdin/network. This is what makes them safe to use as CI gates and
    Wave 2 spawn smoke-tests.
    """
    proc = _run_module(args, timeout=10.0)
    assert proc.returncode == 0, f"flag {args!r} exited {proc.returncode}"
