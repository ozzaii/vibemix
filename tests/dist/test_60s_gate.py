"""Behavioral tests for scripts/dist/check_60s_gate.py.

Phase 49 Plan 05 — INSTALL-06 60s median gate.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# Import via path manipulation (scripts/ isn't on PYTHONPATH by default).
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.dist.check_60s_gate import check_gate, _p95, _normalize_rows  # noqa: E402


def test_all_rows_pass_returns_pass_true():
    rows = [
        {"name": "macos-12.3", "onboarding_ms": 52000},
        {"name": "macos-14", "onboarding_ms": 38000},
        {"name": "macos-15", "onboarding_ms": 35000},
        {"name": "windows-10", "onboarding_ms": 48000},
        {"name": "windows-11", "onboarding_ms": 41000},
    ]
    result = check_gate(rows, budget_ms=60000)
    assert result["pass"] is True
    assert result["median_ms"] == 41000
    assert result["slowest_row"] == "macos-12.3"
    assert result["fastest_row"] == "macos-15"


def test_one_row_over_budget_median_passes_if_median_still_ok():
    """1 over, 4 under → median is the middle value (sorted), passes."""
    rows = [
        {"name": "a", "onboarding_ms": 70000},  # over
        {"name": "b", "onboarding_ms": 30000},
        {"name": "c", "onboarding_ms": 35000},
        {"name": "d", "onboarding_ms": 40000},
        {"name": "e", "onboarding_ms": 45000},
    ]
    result = check_gate(rows, budget_ms=60000)
    assert result["pass"] is True  # median is 40000
    assert result["median_ms"] == 40000
    assert result["slowest_row"] == "a"


def test_three_rows_over_budget_returns_pass_false():
    """3 of 5 over budget → median > budget → fail."""
    rows = [
        {"name": "a", "onboarding_ms": 70000},
        {"name": "b", "onboarding_ms": 75000},
        {"name": "c", "onboarding_ms": 80000},
        {"name": "d", "onboarding_ms": 50000},
        {"name": "e", "onboarding_ms": 55000},
    ]
    result = check_gate(rows, budget_ms=60000)
    assert result["pass"] is False
    assert result["median_ms"] == 70000


def test_p95_calculation_for_5_rows():
    """p95 of 5 values: nearest-rank → index ceil(0.95*5)-1 = ceil(4.75)-1 = 5-1 = 4 → max value."""
    values = [30000.0, 40000.0, 50000.0, 60000.0, 70000.0]
    p = _p95(values)
    assert p == 70000.0  # nearest-rank @ p95 of 5 = max


def test_empty_rows_returns_fail():
    result = check_gate([], budget_ms=60000)
    assert result["pass"] is False
    assert result["reason"] == "no_rows"


def test_normalize_rows_from_simulated_runs_block():
    """Matrix-declaration shape with simulated_runs dict."""
    payload = {
        "simulated_runs": {
            "_doc": "ignored",
            "macos-12.3": {"onboarding_ms": 50000, "auto_install_attempted": True},
            "windows-11": {"onboarding_ms": 45000, "auto_install_attempted": True},
        },
    }
    rows = _normalize_rows(payload)
    assert len(rows) == 2
    names = {r["name"] for r in rows}
    assert names == {"macos-12.3", "windows-11"}


def test_normalize_rows_from_concrete_rows_array():
    """Run-output shape: top-level rows[] with onboarding_ms."""
    payload = {
        "rows": [
            {"name": "macos-14", "onboarding_ms": 36000, "status": "ok"},
            {"name": "windows-10", "onboarding_ms": 49000, "status": "ok"},
        ]
    }
    rows = _normalize_rows(payload)
    assert len(rows) == 2
    assert rows[0]["onboarding_ms"] == 36000


def test_check_gate_against_actual_matrix_file():
    """Integration: check_gate against the simulated_runs in the canonical matrix."""
    matrix_path = ROOT / "scripts" / "dist" / "install_vm_matrix.json"
    payload = json.loads(matrix_path.read_text())
    rows = _normalize_rows(payload)
    assert len(rows) == 5  # 5-row matrix
    result = check_gate(rows, budget_ms=payload.get("onboarding_ms_budget", 60000))
    assert result["pass"] is True, f"matrix simulated_runs must pass 60s gate; got {result}"
    assert result["median_ms"] <= 60000
