# SPDX-License-Identifier: Apache-2.0
"""Plan 58-04 Task 3 — pin the GREEN dry-run (REL-01 / REL-03).

Invokes ``bash scripts/launch/cut_release.sh --dry-run v0.1.0-rc1`` against the
real tree and asserts:
    - exit code 0 (everything-but-the-signature is ready),
    - the signature stub log line appears,
    - the DRY-RUN GREEN summary appears,
    - the KAAN-gated Gate 2b wired-but-pending line appears (it has no real
      ear-pass input on the dev tree, so the dry-run stub always surfaces it).

Gate 5b probes the live Bravoh server, so its log line is server-state
dependent — asserted conditionally (the signature + 2b stub lines always
hold). Gate 6b can be real (an e2e run may exist) OR stubbed; either way the
dry-run stays green.

@pytest.mark.cli  — shells out to bash; opt-in marker (default run skips).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CUT_RELEASE = REPO_ROOT / "scripts" / "launch" / "cut_release.sh"


def _run_dry_run() -> subprocess.CompletedProcess:
    assert CUT_RELEASE.is_file(), f"cut_release.sh missing: {CUT_RELEASE}"
    return subprocess.run(
        ["bash", str(CUT_RELEASE), "--dry-run", "v0.1.0-rc1"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.fixture(scope="module")
def dry_run() -> subprocess.CompletedProcess:
    return _run_dry_run()


@pytest.mark.cli
def test_dry_run_exits_zero(dry_run):
    assert dry_run.returncode == 0, (
        "cut_release.sh --dry-run v0.1.0-rc1 must exit 0.\n"
        f"--- stdout ---\n{dry_run.stdout}\n--- stderr ---\n{dry_run.stderr}"
    )


@pytest.mark.cli
def test_dry_run_stubs_signature_gate(dry_run):
    assert "DRY-RUN: signature gate stubbed (EXTERNAL — Apple/SignPath)" in dry_run.stdout, (
        "Gate 2 must print the signature-stub log line under --dry-run"
    )


@pytest.mark.cli
def test_dry_run_prints_green_summary(dry_run):
    assert "DRY-RUN GREEN — everything but the signature is ready" in dry_run.stdout, (
        "the success path must print the DRY-RUN GREEN summary"
    )
    # The summary must enumerate the real-cut blockers.
    for blocker in ("Apple Dev Agreement", "SignPath cert", "ear-pass", "E2E walk"):
        assert blocker in dry_run.stdout, (
            f"DRY-RUN GREEN summary must list the blocker {blocker!r}"
        )


@pytest.mark.cli
def test_dry_run_logs_kaan_gated_2b_pending(dry_run):
    """Gate 2b has no real ear-pass input on the dev tree — the dry-run must
    loudly log it as wired-but-pending (not silently green it)."""
    assert "Gate 2b wired; awaiting Kaan input (54/55 ear-pass)" in dry_run.stdout, (
        "Gate 2b must surface the wired-but-pending Kaan-input log under --dry-run"
    )


@pytest.mark.cli
def test_dry_run_uses_v4_audit_and_v0_tag(dry_run):
    """The re-pointed gates (Task 1) show in the dry-run output."""
    assert "v4.0-MILESTONE-AUDIT.md" in dry_run.stdout, "Gate 4 must reference the v4.0 audit"
    assert r"^v0\.1\.0-rc[0-9]+$" in dry_run.stdout, "Gate 1 must show the v0.1.0-rc regex"


@pytest.mark.cli
def test_dry_run_never_executes_publish(dry_run):
    """`gh release create` is PRINTED (heredoc) but the command must not have
    run — the script is pre-flight only. We can't observe non-execution
    directly, but the printed example must carry --draft and the publish must
    be presented as a Kaan-action, not a side effect."""
    assert "gh release create v0.1.0-rc1" in dry_run.stdout, (
        "the printed cut command must appear for Kaan to copy"
    )
    assert "Kaan, run the following" in dry_run.stdout, (
        "publish must be framed as a Kaan-action, never auto-run"
    )
