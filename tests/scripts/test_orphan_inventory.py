# SPDX-License-Identifier: Apache-2.0
"""Phase 37 Plan 37-03 — orphan inventory + CI gate contract tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "integration_audit.py"
BASELINE = REPO / ".planning" / "codebase" / "orphans.csv"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        timeout=120,
    )


def test_orphan_inventory_emits_csv_header() -> None:
    proc = _run("--orphan-inventory")
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert lines[0] == "symbol,file,kind", (
        f"orphan inventory must emit CSV with the canonical header, got: {lines[0]!r}"
    )


def test_orphan_baseline_committed() -> None:
    """The baseline orphan inventory MUST live at the documented path."""
    assert BASELINE.exists(), (
        f"orphan-inventory baseline missing — create at {BASELINE.relative_to(REPO)}"
    )
    header = BASELINE.read_text(encoding="utf-8").splitlines()[0]
    assert header == "symbol,file,kind"


def test_orphan_diff_clean_against_committed_baseline() -> None:
    """Current scan must match the committed baseline — CI gate contract."""
    proc = _run("--orphan-diff", str(BASELINE))
    assert proc.returncode == 0, (
        f"orphan-diff failed — new orphans detected without baseline refresh:\n"
        f"{proc.stdout}\n{proc.stderr}"
    )


def test_orphan_diff_fails_on_new_orphan(tmp_path) -> None:
    """If the baseline is missing an orphan that the live scan finds, the
    diff MUST exit non-zero (CI gate)."""
    # Synthetic baseline with ONLY the header — every detected orphan is "new".
    fake_baseline = tmp_path / "fake_baseline.csv"
    fake_baseline.write_text("symbol,file,kind\n", encoding="utf-8")
    proc = _run("--orphan-diff", str(fake_baseline))
    # If the scan finds ANY orphans, exit code MUST be 1.
    inv = _run("--orphan-inventory")
    has_orphans = len(inv.stdout.splitlines()) > 1
    if has_orphans:
        assert proc.returncode == 1, (
            "synthetic empty baseline + non-empty scan must fail the CI gate"
        )
    else:
        assert proc.returncode == 0


def test_orphan_diff_baseline_missing_errors() -> None:
    proc = _run("--orphan-diff", "/nonexistent/path/orphans.csv")
    assert proc.returncode == 1
    assert "baseline" in proc.stderr.lower()


def test_orphan_inventory_workflow_committed() -> None:
    """`.github/workflows/orphan-inventory.yml` MUST exist and invoke the script."""
    wf = REPO / ".github" / "workflows" / "orphan-inventory.yml"
    assert wf.exists(), "orphan-inventory.yml workflow missing"
    text = wf.read_text(encoding="utf-8")
    assert "integration_audit.py" in text
    assert "--orphan-diff" in text
    assert ".planning/codebase/orphans.csv" in text
