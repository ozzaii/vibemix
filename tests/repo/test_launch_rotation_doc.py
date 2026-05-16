# SPDX-License-Identifier: Apache-2.0
"""Phase 39 / Plan 39-07 — launch-rotation.md sanity gate.

REQ-IDs: SHIP-07
Pitfall: P79 (monitoring-gap detection).

Asserts:
- The 24h rotation doc exists at docs/launch-rotation.md.
- Every hour 00:00–23:00 is covered (or T+0..T+23 in the table).
- Each hour assigned to Kaan / Francesco / Bravoh-team.
- Escalation paths section includes showstopper / abuse / traffic-spike.
- References to seed_stars protocol + day-zero-rota predecessor.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "docs" / "launch-rotation.md"


def _body() -> str:
    assert DOC.exists(), f"missing {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC.exists()


def test_rotation_doc_covers_24_hours():
    """Either 24 hour rows or 24 distinct T+offset entries must appear."""
    body = _body()
    # Count rows matching pipes around an hour or T-offset.
    hour_rows = re.findall(r"^\|\s*(\d{2}:\d{2})\s*\|", body, re.MULTILINE)
    # Should be at least 25 (08:00 T-1 + 09:00 T+0 ... + 09:00 T+24).
    assert len(hour_rows) >= 24, (
        f"only {len(hour_rows)} hour rows found in launch-rotation.md; expected ≥24"
    )


def test_rotation_doc_assigns_each_hour_to_kaan_francesco_or_bravoh():
    """Every hour row must include one of Kaan / Francesco / Bravoh-team
    in its responder cell."""
    body = _body()
    # Find the schedule table by matching rows with T-offset.
    rows = re.findall(
        r"^\|\s*\d{2}:\d{2}\s*\|\s*T[+\-]\d+\s*\|\s*([^|]+?)\s*\|",
        body,
        re.MULTILINE,
    )
    assert rows, "no schedule rows parsed"
    valid_responders = {"Kaan", "Francesco", "Bravoh-team"}
    invalid: list[str] = []
    for cell in rows:
        cell_strip = cell.strip()
        if not any(v in cell_strip for v in valid_responders):
            invalid.append(cell_strip)
    assert not invalid, (
        f"rows without Kaan/Francesco/Bravoh-team assignment: {invalid}"
    )


def test_rotation_doc_includes_escalation_paths():
    body = _body()
    assert "Escalation paths" in body or "Escalation path" in body
    # Tier-1/2/3 structure or table columns.
    body_lower = body.lower()
    for scenario in (
        "showstopper", "abuse", "traffic spike", "hallucination",
    ):
        assert scenario in body_lower, (
            f"escalation table missing '{scenario}' row"
        )


def test_rotation_doc_references_seed_stars_protocol():
    body = _body()
    assert "seed_stars" in body, "seed_stars.md protocol not referenced"


def test_rotation_doc_references_day_zero_rota_predecessor():
    body = _body()
    assert "day-zero-rota" in body or "day_zero_rota" in body


def test_rotation_doc_references_kaan_action_legal_ship():
    body = _body()
    assert "KAAN-ACTION-LEGAL.md" in body
    assert "SHIP" in body


def test_rotation_doc_includes_per_hour_checklist():
    body = _body()
    # Each responder gets a per-hour checklist.
    for item in ("Discord triage", "GitHub Issues", "healthz", "Star velocity"):
        assert item in body, f"per-hour checklist missing '{item}'"


def test_rotation_doc_lists_launch_slot_09_cet():
    """P78 — 09:00 CET / HN front-page sweet spot. Doc must declare it."""
    body = _body()
    assert "09:00" in body
    assert "CET" in body or "TRT" in body


def test_rotation_doc_post_24h_handoff_to_async_rota():
    body = _body()
    assert "Post-24h" in body or "T+24" in body
    # Hand off to async cadence (day-zero-rota predecessor).
    assert "async" in body.lower() or "v2.1.0-launch-retro" in body
