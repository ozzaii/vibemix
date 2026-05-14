"""Tests for scripts/dayzero/* — Day-Zero ops scripts.

All tests use the scripts' --dry-run modes; no real network calls. The
synthetic generators are deterministic when seeded (proxy_load_test) or
deterministic by construction (healthz_check's "every 3rd iteration alerts"
schedule).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PROXY_LOAD_TEST = REPO_ROOT / "scripts" / "dayzero" / "proxy_load_test.py"
HEALTHZ_CHECK = REPO_ROOT / "scripts" / "dayzero" / "healthz_check.sh"


def _run_proxy(*extra_args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(PROXY_LOAD_TEST), *extra_args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=REPO_ROOT,
    )


def _run_healthz(*extra_args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    bash = shutil.which("bash") or "/bin/bash"
    return subprocess.run(
        [bash, str(HEALTHZ_CHECK), *extra_args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=REPO_ROOT,
    )


# ---------------------------------------------------------------------------
# proxy_load_test.py
# ---------------------------------------------------------------------------

def test_proxy_load_test_dry_run_passes_with_loose_budget():
    """Default budget (p99 < 500ms) should pass against synthetic gaussian@200ms."""
    result = _run_proxy(
        "--dry-run",
        "--dry-run-seed", "42",
        "--duration", "2",
        "--rps", "10",
    )
    assert result.returncode == 0, (
        f"expected PASS exit 0 — got {result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "PASS" in result.stdout, "PASS verdict missing from human report"


def test_proxy_load_test_dry_run_forced_fail_on_tight_budget():
    """p99 budget tighter than any plausible synthetic latency forces FAIL."""
    result = _run_proxy(
        "--dry-run",
        "--dry-run-seed", "42",
        "--duration", "2",
        "--rps", "10",
        "--p99-budget-ms", "50",
    )
    assert result.returncode == 1, (
        f"expected FAIL exit 1 — got {result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "FAIL" in result.stdout, "FAIL verdict missing from human report"


def test_proxy_load_test_json_output_shape():
    """--json emits a single JSON object on stdout with expected keys."""
    result = _run_proxy(
        "--dry-run",
        "--dry-run-seed", "42",
        "--duration", "1",
        "--rps", "5",
        "--json",
    )
    # Should still pass with these settings; exit 0 expected.
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    expected_keys = {
        "verdict", "p99_ms", "p95_ms", "median_ms",
        "min_ms", "max_ms",
        "error_rate", "total_samples", "success_count",
        "error_count", "p99_budget_ms", "error_rate_budget",
        "duration_s", "rps", "target",
    }
    missing = expected_keys - set(parsed.keys())
    assert not missing, f"missing keys in JSON output: {missing}"
    assert parsed["verdict"] in {"PASS", "FAIL"}


# ---------------------------------------------------------------------------
# healthz_check.sh
# ---------------------------------------------------------------------------

def test_healthz_check_dry_run_alert_schedule():
    """--dry-run produces exactly 2 ALERTs and 4 OKs over 6 iterations."""
    result = _run_healthz(
        "--dry-run",
        "--interval", "0",
        "--max-iterations", "6",
    )
    assert result.returncode == 0, (
        f"expected exit 0 — got {result.returncode}\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
    alerts = [line for line in result.stderr.splitlines() if line.startswith("[ALERT]")]
    oks = [line for line in result.stdout.splitlines() if line.startswith("[OK]")]
    assert len(alerts) == 2, f"expected 2 ALERTs, got {len(alerts)}: {alerts}"
    assert len(oks) == 4, f"expected 4 OKs, got {len(oks)}: {oks}"
    # SUMMARY must appear on clean shutdown.
    assert "[SUMMARY] iterations=6 ok=4 alerts=2" in result.stderr


def test_healthz_check_help_exits_clean():
    """--help exits 0 with usage on stdout."""
    result = _run_healthz("--help")
    assert result.returncode == 0
    assert "healthz_check.sh" in result.stdout or "healthz watchdog" in result.stdout.lower()
