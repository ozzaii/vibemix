# SPDX-License-Identifier: Apache-2.0
"""tests/launch/test_check_bravoh_org_ready.py — LAUNCH-06 polling gate.

Plan 44-06 ships `scripts/launch/check_bravoh_org_ready.sh` — a bash
poller that returns 0 iff `https://api.github.com/orgs/bravoh` exists.
Plan 45 SHIP-TRANSFER consumes this as the org-ready gate.

This test wrapper is the project-conventional `.py` (matches
`test_storyboard_palette.py`, `test_readme_grids_a11y.py`, etc.). It
exercises three things:

  1. The script file exists, has the executable bit set, and passes
     `bash -n` syntax check.
  2. Quick smoke against a well-known existing org (`github`) →
     expected exit 0 (marked `@pytest.mark.network` so CI can skip
     when offline).
  3. Smoke against the target org (`bravoh`) which doesn't exist yet
     (the entire point of the §LAUNCH-06 Kaan-discharge) → expected
     exit 1, also `@pytest.mark.network`.

Both `network` tests are skipped under `-m 'not network'` (the default
CI invocation in the plan verification step), so the offline mode
exercises only the syntax + executable bit invariants.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "launch" / "check_bravoh_org_ready.sh"


# ---------------------------------------------------------------------
# Static invariants (offline; always run)
# ---------------------------------------------------------------------


def test_script_file_exists():
    """LAUNCH-06: the polling script must ship at the documented path."""
    assert SCRIPT.exists(), f"missing script: {SCRIPT}"
    assert SCRIPT.is_file()


def test_script_has_executable_bit():
    """`bash scripts/launch/check_bravoh_org_ready.sh ...` works from
    KAAN-ACTION-LEGAL.md runbook + Plan 45 SHIP-TRANSFER consumer
    even without `bash` prefix."""
    mode = SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, (
        f"script not executable for user: {oct(mode)}"
    )


def test_script_has_strict_bash_header():
    """`set -euo pipefail` is the standard for scripts/launch/*.sh."""
    body = SCRIPT.read_text(encoding="utf-8")
    assert body.startswith("#!/"), "missing shebang"
    assert "set -euo pipefail" in body, (
        "script must have `set -euo pipefail` for fail-safe semantics"
    )


def test_script_syntax_clean():
    """`bash -n` must accept the script."""
    proc = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"bash -n syntax check failed:\n{proc.stderr}"
    )


def test_script_supports_org_flag():
    """Script must accept `--org NAME` for test injection."""
    body = SCRIPT.read_text(encoding="utf-8")
    assert "--org" in body, (
        "script must accept --org flag for test injection / Plan 45 "
        "polling against alt org names"
    )


def test_script_supports_quiet_flag():
    """Script must accept `--quiet` to silence the OK / FAIL chatter."""
    body = SCRIPT.read_text(encoding="utf-8")
    assert "--quiet" in body, (
        "script must accept --quiet to suppress output for CI consumers"
    )


def test_script_default_org_is_bravoh():
    """Default org name is `bravoh` per CONTEXT §LAUNCH-06."""
    body = SCRIPT.read_text(encoding="utf-8")
    # We accept either an explicit assignment OR an argparse-style
    # default — both forms are bashic.
    assert "bravoh" in body, (
        "script must default to org=bravoh (LAUNCH-06 target)"
    )


def test_script_targets_github_api_orgs_path():
    """Endpoint = `orgs/<org>` per LAUNCH-06 verify oneliner."""
    body = SCRIPT.read_text(encoding="utf-8")
    assert "orgs/" in body or "/orgs/" in body, (
        "script must hit the GitHub orgs/<name> endpoint"
    )


def test_help_flag_works():
    """`--help` (or `-h`) prints usage and exits 0."""
    if not shutil.which("bash"):
        pytest.skip("bash not available")
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert proc.returncode == 0, (
        f"--help should exit 0; got {proc.returncode}\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    combined = proc.stdout + proc.stderr
    assert "--org" in combined or "Usage" in combined or "usage" in combined


# ---------------------------------------------------------------------
# Live network smokes (marked @pytest.mark.network — skipped by default)
# ---------------------------------------------------------------------


@pytest.mark.network
def test_well_known_org_returns_exit_zero():
    """`--org github` against the well-known existing GitHub org → exit 0."""
    if not shutil.which("bash"):
        pytest.skip("bash not available")
    proc = subprocess.run(
        ["bash", str(SCRIPT), "--org", "github", "--quiet"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 0, (
        f"well-known org `github` should exist; got exit "
        f"{proc.returncode}\nstderr: {proc.stderr}"
    )


@pytest.mark.network
def test_missing_org_returns_exit_one():
    """A guaranteed-missing org → exit 1.

    Uses a long random-looking name to minimize collision risk against
    a real org. If somebody actually squats this, swap the literal."""
    if not shutil.which("bash"):
        pytest.skip("bash not available")
    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--org",
            "vibemix-launch-06-canary-org-does-not-exist-xyz",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 1, (
        f"missing org should exit 1; got {proc.returncode}\n"
        f"stderr: {proc.stderr}"
    )
