# SPDX-License-Identifier: Apache-2.0
"""Phase 33 / Plan 33-08 — Fresh-VM rehearsal scaffold gate.

Real VM execution is Kaan-action (disk space + macOS license + fresh
ISOs). This test gate verifies the SCAFFOLD pieces are in place:

  - mac_vm_setup.sh exists, is executable, and refuses to spin VMs
    without INSTALL_REHEARSAL_REAL=1 in the env.
  - win_vm_setup.ps1 exists with the matching env-var double-gate.
  - rehearsal_runner.py --dry-run prints a plan without invoking
    tart / VBoxManage.
  - .github/workflows/install-rehearsal.yml is workflow_dispatch +
    nightly cron only (never on every PR — VM resources cost).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
REHEARSAL_DIR = REPO_ROOT / "scripts" / "install_rehearsal"
MAC_SH = REHEARSAL_DIR / "mac_vm_setup.sh"
WIN_PS1 = REHEARSAL_DIR / "win_vm_setup.ps1"
RUNNER = REHEARSAL_DIR / "rehearsal_runner.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "install-rehearsal.yml"


def test_mac_vm_setup_sh_exists_and_guards_real_runs() -> None:
    assert MAC_SH.exists(), f"missing: {MAC_SH}"
    body = MAC_SH.read_text(encoding="utf-8")
    # Hard guard: env-var double-gate present.
    assert "INSTALL_REHEARSAL_REAL" in body, (
        "mac_vm_setup.sh missing INSTALL_REHEARSAL_REAL guard"
    )
    # Executable bit set.
    assert os.access(MAC_SH, os.X_OK), "mac_vm_setup.sh is not executable"


def test_win_vm_setup_ps1_exists_and_guards_real_runs() -> None:
    assert WIN_PS1.exists(), f"missing: {WIN_PS1}"
    body = WIN_PS1.read_text(encoding="utf-8")
    assert "INSTALL_REHEARSAL_REAL" in body, (
        "win_vm_setup.ps1 missing INSTALL_REHEARSAL_REAL guard"
    )


def test_rehearsal_runner_dry_run_does_not_invoke_tart() -> None:
    """Default invocation prints the plan + exits 0 with no real ops."""
    assert RUNNER.exists(), f"missing: {RUNNER}"
    # Default (no flags) is dry-run.
    result = subprocess.run(
        [sys.executable, str(RUNNER), "--matrix", "all"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, f"dry-run failed: {result.stderr}"
    assert "dry-run" in result.stdout.lower()
    # Plan output must list the macOS matrix.
    assert "macos-12.3" in result.stdout
    assert "macos-14" in result.stdout
    assert "macos-15" in result.stdout
    # Output must NOT mention real tart invocation (subprocess line).
    assert "tart clone" not in result.stdout.lower() or "would" in result.stdout.lower()


def test_rehearsal_runner_real_without_env_var_refuses() -> None:
    """--real flag WITHOUT INSTALL_REHEARSAL_REAL=1 → exit non-zero."""
    env = dict(os.environ)
    env.pop("INSTALL_REHEARSAL_REAL", None)
    result = subprocess.run(
        [sys.executable, str(RUNNER), "--matrix", "mac", "--real"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=10,
    )
    assert result.returncode != 0, (
        "--real without env var must refuse"
    )
    assert "INSTALL_REHEARSAL_REAL" in result.stderr or "INSTALL_REHEARSAL_REAL" in result.stdout


def test_workflow_yml_is_workflow_dispatch_or_nightly_only() -> None:
    assert WORKFLOW.exists(), f"missing: {WORKFLOW}"
    body = WORKFLOW.read_text(encoding="utf-8")
    # MUST have workflow_dispatch.
    assert "workflow_dispatch" in body, (
        "install-rehearsal.yml missing workflow_dispatch trigger"
    )
    # Must have nightly cron (or some schedule).
    assert "schedule:" in body, (
        "install-rehearsal.yml missing schedule: trigger"
    )
    # MUST NOT have pull_request trigger (VM cost).
    assert "pull_request" not in body, (
        "install-rehearsal.yml must NOT run on pull_request — VM cost"
    )


def test_kaan_action_legal_documents_install_vm_run() -> None:
    legal = REPO_ROOT / "KAAN-ACTION-LEGAL.md"
    assert legal.exists()
    body = legal.read_text(encoding="utf-8")
    assert "INSTALL-VM-RUN" in body, (
        "KAAN-ACTION-LEGAL.md must document INSTALL-VM-RUN per Plan 33-08"
    )
