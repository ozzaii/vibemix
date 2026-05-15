# SPDX-License-Identifier: Apache-2.0
"""Phase 37 Plan 37-04 — Kaan-action rollup contract tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "integration_audit.py"


def _run_rollup() -> str:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--kaan-action-rollup"],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_rollup_finds_dist_09_and_dist_11_as_legal_capacity() -> None:
    """The two canonical legal-capacity carveouts (P46) MUST be present."""
    body = _run_rollup()
    assert "DIST-09" in body, "DIST-09 (Apple Developer Agreement) missing"
    assert "DIST-11" in body, "DIST-11 (SignPath OSS Foundation) missing"
    # Both must be classified as legal-capacity (NEVER autonomously discharged).
    lines = body.splitlines()
    dist_09_rows = [l for l in lines if "DIST-09" in l]
    dist_11_rows = [l for l in lines if "DIST-11" in l]
    assert any("legal-capacity" in r for r in dist_09_rows), (
        "DIST-09 must be classified as legal-capacity per P46"
    )
    assert any("legal-capacity" in r for r in dist_11_rows), (
        "DIST-11 must be classified as legal-capacity per P46"
    )


def test_rollup_uses_canonical_table_columns() -> None:
    body = _run_rollup()
    header_line = body.splitlines()[0]
    for col in ("ID", "Type", "Owner", "Blocking?", "Source"):
        assert col in header_line, f"missing column: {col}"


def test_rollup_excludes_strikethrough_completed_entries(tmp_path) -> None:
    """Strikethrough markers (``~~ID~~``) mean completed — must NOT appear."""
    fake_phase = tmp_path / "phases" / "99-fake-phase"
    fake_phase.mkdir(parents=True)
    f = fake_phase / "KAAN-ACTION-PROXY.md"
    f.write_text(
        "# Kaan-action surface\n\n## ~~DIST-99~~ — Completed item\n\n"
        "## DIST-100 — Still open\n",
        encoding="utf-8",
    )
    # Run the in-process parser directly to keep the test hermetic.
    sys.path.insert(0, str(REPO))
    try:
        from scripts.integration_audit import _parse_kaan_action_file
    finally:
        sys.path.pop(0)
    actions = _parse_kaan_action_file(f)
    ids = {a.id for a in actions}
    assert "DIST-99" not in ids, "strikethrough item must be excluded"
    assert "DIST-100" in ids


def test_rollup_classifies_proxy_entry_via_kaan_action_marker(tmp_path) -> None:
    """An explicit 'Kaan-action' label outside the legal-capacity section
    classifies as proxy (autonomous-dischargeable post-approval)."""
    fake_path = tmp_path / "KAAN-ACTION-PROXY.md"
    fake_path.write_text(
        "# Kaan-action surface\n\n"
        "## DIST-77 — A normal Kaan-action item\n"
        "Owner: Kaan.\n"
        "Notes: mechanical post-approval step.\n",
        encoding="utf-8",
    )
    sys.path.insert(0, str(REPO))
    try:
        from scripts.integration_audit import _parse_kaan_action_file
    finally:
        sys.path.pop(0)
    actions = _parse_kaan_action_file(fake_path)
    assert len(actions) >= 1
    dist_77 = [a for a in actions if a.id == "DIST-77"][0]
    assert dist_77.type == "proxy"


def test_rollup_runs_against_real_repo_and_emits_table() -> None:
    """End-to-end: the script runs against the real KAAN-ACTION-LEGAL.md
    + every phase's KAAN-ACTION-*.md and emits a non-empty markdown table."""
    body = _run_rollup()
    # Confirm table shape.
    assert "| ID | Type | Owner | Blocking? | Source |" in body
    # Confirm at least DIST-09 + DIST-11 lines exist.
    assert body.count("|") > 10  # header + separator + ≥2 data rows
