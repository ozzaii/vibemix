# SPDX-License-Identifier: Apache-2.0
"""Phase 37 Plan 37-05 — Grey-Area Decisions log contract tests (P87)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "integration_audit.py"


def _run() -> str:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--grey-area-log"],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def test_grey_area_scan_finds_recommended_marker(tmp_path) -> None:
    """A phase file containing 'recommended:' MUST surface in the log."""
    sys.path.insert(0, str(REPO))
    try:
        from scripts.integration_audit import collect_grey_area_decisions
    finally:
        sys.path.pop(0)

    # Real repo scan finds at least one entry (v2.1 phases all use
    # gsd-autonomous fully — their CONTEXT.md headers contain markers).
    entries = collect_grey_area_decisions()
    assert len(entries) > 0, "real repo should have grey-area entries"
    rationales = {e.rationale for e in entries}
    # At least one of the canonical markers must surface.
    canonical = {"recommended", "deferred per autonomous mode", "grey-area",
                 "gsd-autonomous fully — recommended", "accepted per gsd-autonomous fully"}
    assert any(r in canonical or "recommended" in r or "grey-area" in r for r in rationales), (
        f"no canonical grey-area markers in rationales: {rationales}"
    )


def test_grey_area_scan_finds_deferred_per_autonomous(tmp_path) -> None:
    """The 'deferred per autonomous mode' marker is detected."""
    sys.path.insert(0, str(REPO))
    try:
        from scripts.integration_audit import GREY_AREA_MARKERS
    finally:
        sys.path.pop(0)
    assert "deferred per autonomous mode" in GREY_AREA_MARKERS


def test_grey_area_scan_emits_required_columns() -> None:
    """The output table MUST have exactly the columns Phase / Decision /
    Rationale / Reversible? / Source."""
    body = _run()
    header = body.splitlines()[0]
    for col in ("Phase", "Decision", "Rationale", "Reversible?", "Source"):
        assert col in header, f"missing column: {col}"


def test_grey_area_log_includes_at_least_one_real_phase_entry() -> None:
    """v2.1 phases use gsd-autonomous fully — the scan MUST surface ≥1
    real entry from a real phase file (live ``.planning/phases/*`` OR
    archived ``.planning/milestones/<version>-phases/*``)."""
    body = _run()
    lines = body.splitlines()
    # header + separator + ≥1 data row
    assert len(lines) >= 3, f"empty grey-area log:\n{body}"
    data_rows = lines[2:]
    assert any(
        ".planning/phases/" in r or ".planning/milestones/" in r for r in data_rows
    ), "data rows must point to phase files (live or archived milestone dir)"


def test_grey_area_log_reversible_field_uses_yes_no_question() -> None:
    """The Reversible? column MUST emit yes / no / ? — P87 contract."""
    body = _run()
    # Find at least one row with a yes/no/? in the reversible slot.
    data_rows = body.splitlines()[2:]
    assert data_rows, "no data rows to check"
    valid_rev_seen = False
    for row in data_rows:
        for tok in ("| yes |", "| no |", "| ? |"):
            if tok in row:
                valid_rev_seen = True
                break
        if valid_rev_seen:
            break
    assert valid_rev_seen, "no valid reversible-flag value in any row"
