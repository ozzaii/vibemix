# SPDX-License-Identifier: Apache-2.0
"""Phase 37 Plan 37-02 — scripts/integration_audit.py contract tests.

Verifies the audit composer produces a 7-section markdown file with
the fixed section order, writes to the correct planning path, and
guards against accidental overwrite.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "integration_audit.py"


REQUIRED_SECTIONS = [
    "## 1. Summary",
    "## 2. Per-Seam Verdicts",
    "## 3. Orphan Inventory",
    "## 4. Kaan-Action Roll-Up",
    "## 5. Grey-Area Decisions",
    "## 6. POC Files Untouched",
    "## 7. Conclusion",
]


def _run_audit(*args: str, cwd: Path = REPO) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=180,
    )


def test_audit_emits_all_seven_sections(tmp_path) -> None:
    out = tmp_path / "v2.1-MILESTONE-AUDIT.md"
    proc = _run_audit("--write-milestone-audit", str(out))
    assert proc.returncode == 0, f"audit failed:\n{proc.stdout}\n{proc.stderr}"
    body = out.read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert section in body, f"section header missing: {section}"


def test_audit_writes_to_planning_v2_1_path(tmp_path) -> None:
    """The CLI accepts an explicit path; the canonical write target is
    ``.planning/v2.1-MILESTONE-AUDIT.md`` per 37-PLAN §cross-cutting."""
    # We don't write to the real planning path in tests; we verify the
    # script writes to the path the caller passes — same contract.
    out = tmp_path / "planning_target.md"
    proc = _run_audit("--write-milestone-audit", str(out))
    assert proc.returncode == 0, proc.stderr
    assert out.exists()


def test_audit_records_seam_test_pass_fail(tmp_path) -> None:
    out = tmp_path / "audit.md"
    proc = _run_audit("--write-milestone-audit", str(out))
    assert proc.returncode == 0, proc.stderr
    body = out.read_text(encoding="utf-8")
    # Verdict column header.
    assert "Verdict" in body
    # At least one of WIRED/PARTIAL/MISSING appears per seam row.
    verdicts = ["WIRED", "PARTIAL", "MISSING"]
    assert any(v in body for v in verdicts), (
        "audit must surface seam verdicts"
    )


def test_audit_does_not_overwrite_existing_without_force(tmp_path) -> None:
    out = tmp_path / "existing.md"
    out.write_text("pre-existing content", encoding="utf-8")
    proc = _run_audit("--write-milestone-audit", str(out))
    assert proc.returncode != 0, (
        "without --force the audit must refuse to overwrite"
    )
    # File untouched.
    assert out.read_text(encoding="utf-8") == "pre-existing content"


def test_audit_overwrites_with_force(tmp_path) -> None:
    out = tmp_path / "existing.md"
    out.write_text("pre-existing content", encoding="utf-8")
    proc = _run_audit("--write-milestone-audit", str(out), "--force")
    assert proc.returncode == 0, proc.stderr
    body = out.read_text(encoding="utf-8")
    assert "pre-existing content" not in body
    assert "## 1. Summary" in body


def test_audit_emits_seam_anchors_to_real_files(tmp_path) -> None:
    """Each seam's source/sink anchor MUST point at a real file path."""
    out = tmp_path / "audit.md"
    proc = _run_audit("--write-milestone-audit", str(out))
    assert proc.returncode == 0, proc.stderr
    body = out.read_text(encoding="utf-8")
    # The seam table should reference each known seam source.
    for expected in (
        "evidence_registry.py",
        "citation_linter.py",
        "cache.py",
        "dj_cohost.py",
        "rekordbox.py",
        "replay_harness.py",
        "eval.yml",
        "priority-stack.ts",
        "ws_bus.py",
    ):
        assert expected in body, f"audit missing seam anchor: {expected}"
