# SPDX-License-Identifier: Apache-2.0
"""Phase 50 / E2E — tests for the anti-slop sibling checker.

Exercises 4 cases:
  (a) clean report.html → exit 0
  (b) report.html containing a banned token → exit 1 with location reported
  (c) report.html containing 'deep' (substring of 'deeply') → exit 0 (word-boundary)
  (d) no report.html in target → exit 0 (CI no-op)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "audit" / "check_no_slop_e2e.py"


def _run(target_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--dir", str(target_dir)],
        capture_output=True,
        text=True,
    )


def _write_report(run_dir: Path, body_inner_html: str) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    report = run_dir / "report.html"
    report.write_text(
        "<!doctype html><html><body>"
        f"<main>{body_inner_html}</main>"
        "</body></html>",
        encoding="utf-8",
    )
    return report


def test_clean_report_exits_zero(tmp_path: Path) -> None:
    runs = tmp_path / "e2e-macbook-runs" / "2026-05-18T10-00-00Z"
    _write_report(runs, "Functional PASS · 12/12 assertions · all green")
    proc = _run(tmp_path / "e2e-macbook-runs")
    assert proc.returncode == 0, proc.stderr


def test_banned_token_exits_one_with_location(tmp_path: Path) -> None:
    runs = tmp_path / "e2e-macbook-runs" / "2026-05-18T10-00-00Z"
    _write_report(runs, "Functional deeply tested across all dimensions")
    proc = _run(tmp_path / "e2e-macbook-runs")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "deeply" in proc.stderr, proc.stderr
    # Line-number annotation present in error string.
    assert "report.html:" in proc.stderr, proc.stderr


def test_substring_does_not_trigger_word_boundary_token(tmp_path: Path) -> None:
    runs = tmp_path / "e2e-macbook-runs" / "2026-05-18T10-00-00Z"
    # 'deepwater' contains 'deep' as substring but not 'deeply' as full word.
    _write_report(runs, "Visual deepwater snapshot diff in band")
    proc = _run(tmp_path / "e2e-macbook-runs")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_no_report_html_exits_zero_with_message(tmp_path: Path) -> None:
    # Directory exists but has no report.html.
    runs = tmp_path / "e2e-macbook-runs"
    runs.mkdir()
    proc = _run(runs)
    assert proc.returncode == 0
    assert "no report.html" in proc.stderr.lower() or "no e2e runs" in proc.stderr.lower()


def test_missing_directory_exits_zero_ci_noop(tmp_path: Path) -> None:
    # Directory doesn't exist — CI no-op path.
    proc = _run(tmp_path / "does-not-exist")
    assert proc.returncode == 0


def test_script_imports_canonical_blocklist() -> None:
    """Verify the sibling imports BLOCKLIST from canonical, never redefines."""
    script_text = SCRIPT.read_text(encoding="utf-8")
    # Sibling pattern: import from canonical via importlib.
    assert "importlib" in script_text
    assert "check_no_ai_slop.py" in script_text
    # Hard rule from CONTEXT: no inline BLOCKLIST = (...) tuple definition.
    # Defensive fallback is allowed as a string literal block inside the
    # _import_blocklist function; we check that the active blocklist is set
    # from the imported module.
    assert "AI_SLOP_BLOCKLIST: tuple[str, ...] = _import_blocklist()" in script_text
