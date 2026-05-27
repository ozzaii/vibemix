"""Behavioral tests for scripts/dist/check_60s_gate.py.

Phase 49 Plan 05 — INSTALL-06 full first-install timing gate.
"""
from __future__ import annotations

import json

# Import via path manipulation (scripts/ isn't on PYTHONPATH by default).
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.dist.check_60s_gate import _normalize_rows, _p95, check_gate  # noqa: E402


def test_all_rows_pass_returns_pass_true():
    rows = [
        {"name": "macos-12.3", "install_ms": 420000},
        {"name": "macos-14", "install_ms": 360000},
        {"name": "macos-15", "install_ms": 340000},
        {"name": "windows-10", "install_ms": 450000},
        {"name": "windows-11", "install_ms": 390000},
    ]
    result = check_gate(rows, budget_ms=600000)
    assert result["pass"] is True
    assert result["median_ms"] == 390000
    assert result["slowest_row"] == "windows-10"
    assert result["fastest_row"] == "macos-15"


def test_one_row_over_budget_median_passes_if_median_still_ok():
    """1 over, 4 under → median is the middle value (sorted), passes."""
    rows = [
        {"name": "a", "install_ms": 700000},  # over
        {"name": "b", "install_ms": 300000},
        {"name": "c", "install_ms": 350000},
        {"name": "d", "install_ms": 400000},
        {"name": "e", "install_ms": 450000},
    ]
    result = check_gate(rows, budget_ms=600000)
    assert result["pass"] is True  # median is 400000
    assert result["median_ms"] == 400000
    assert result["slowest_row"] == "a"


def test_three_rows_over_budget_returns_pass_false():
    """3 of 5 over budget → median > budget → fail."""
    rows = [
        {"name": "a", "install_ms": 700000},
        {"name": "b", "install_ms": 750000},
        {"name": "c", "install_ms": 800000},
        {"name": "d", "install_ms": 500000},
        {"name": "e", "install_ms": 550000},
    ]
    result = check_gate(rows, budget_ms=600000)
    assert result["pass"] is False
    assert result["median_ms"] == 700000


def test_p95_calculation_for_5_rows():
    """p95 of 5 values: nearest-rank → index ceil(0.95*5)-1 = ceil(4.75)-1 = 5-1 = 4 → max value."""
    values = [300000.0, 400000.0, 500000.0, 600000.0, 700000.0]
    p = _p95(values)
    assert p == 700000.0  # nearest-rank @ p95 of 5 = max


def test_empty_rows_returns_fail():
    result = check_gate([], budget_ms=600000)
    assert result["pass"] is False
    assert result["reason"] == "no_rows"


def test_normalize_rows_from_simulated_runs_block():
    """Matrix-declaration shape with simulated_runs dict."""
    payload = {
        "simulated_runs": {
            "_doc": "ignored",
            "macos-12.3": {"install_ms": 500000, "auto_install_attempted": True},
            "windows-11": {"install_ms": 450000, "auto_install_attempted": True},
        },
    }
    rows = _normalize_rows(payload)
    assert len(rows) == 2
    names = {r["name"] for r in rows}
    assert names == {"macos-12.3", "windows-11"}


def test_normalize_rows_from_concrete_rows_array():
    """Run-output shape: top-level rows[] with install_ms."""
    payload = {
        "rows": [
            {"name": "macos-14", "install_ms": 360000, "status": "ok"},
            {"name": "windows-10", "install_ms": 490000, "status": "ok"},
        ]
    }
    rows = _normalize_rows(payload)
    assert len(rows) == 2
    assert rows[0]["install_ms"] == 360000


def test_check_gate_against_actual_matrix_file():
    """Integration: check_gate against the simulated_runs in the canonical matrix."""
    matrix_path = ROOT / "scripts" / "dist" / "install_vm_matrix.json"
    payload = json.loads(matrix_path.read_text())
    rows = _normalize_rows(payload)
    assert len(rows) == 5  # 5-row matrix
    result = check_gate(rows, budget_ms=payload.get("install_ms_budget", 600000))
    assert result["pass"] is True, f"matrix simulated_runs must pass install budget gate; got {result}"
    assert result["median_ms"] <= 600000
