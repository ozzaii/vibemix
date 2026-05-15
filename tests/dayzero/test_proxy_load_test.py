"""Tests for `scripts/dayzero/proxy_load_test.py`.

Asserts the autonomous-safety contract:
- Default --target is `local-mock` (NEVER prod URL).
- Local-mock + dry-run never call httpx.
- Verdict artifact lands as JSON under the artifact dir.
- PASS/FAIL math is correct against deterministic synthetic samples.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dayzero" / "proxy_load_test.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("proxy_load_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    assert spec is not None and spec.loader is not None
    sys.modules["proxy_load_test"] = mod
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def test_loadtest_defaults_to_local_mock():
    """HARD GATE: argparse default for --target MUST be 'local-mock'.

    This is the autonomous-mode safety invariant — accidental CI runs of
    the script must never DDOS prod.
    """
    mod = _load_module()
    parser = mod._build_argparser()
    args = parser.parse_args([])
    assert args.target == "local-mock"
    assert args.target == mod.LOCAL_MOCK_TARGET


def test_loadtest_pass_fail_logic_pass():
    """Synthetic samples with seed=42 + default budgets => PASS."""
    mod = _load_module()
    samples = mod.synthesize_samples(rps=10, duration_s=2.0, seed=42)
    verdict = mod.compute_verdict(
        samples=samples,
        p99_budget_ms=2000.0,
        error_rate_budget=0.05,
        duration_s=2.0,
        rps=10,
        target="local-mock",
    )
    assert verdict.verdict == "PASS"
    assert verdict.total_samples == 20
    assert verdict.p99_ms <= verdict.p99_budget_ms


def test_loadtest_pass_fail_logic_fail():
    """Tight p99 budget => FAIL."""
    mod = _load_module()
    samples = mod.synthesize_samples(rps=10, duration_s=2.0, seed=42)
    verdict = mod.compute_verdict(
        samples=samples,
        p99_budget_ms=1.0,  # impossibly tight
        error_rate_budget=0.05,
        duration_s=2.0,
        rps=10,
        target="local-mock",
    )
    assert verdict.verdict == "FAIL"


def test_loadtest_writes_artifact(tmp_path):
    """write_artifact() lands JSON file + parses to all Verdict fields."""
    mod = _load_module()
    samples = mod.synthesize_samples(rps=5, duration_s=1.0, seed=7)
    verdict = mod.compute_verdict(
        samples=samples,
        p99_budget_ms=2000.0,
        error_rate_budget=0.05,
        duration_s=1.0,
        rps=5,
        target="local-mock",
    )
    out = mod.write_artifact(verdict, tmp_path)
    assert out.is_file()
    payload = json.loads(out.read_text())
    # Every Verdict field must round-trip.
    for k in (
        "verdict",
        "p99_ms",
        "p95_ms",
        "median_ms",
        "error_rate",
        "total_samples",
        "p99_budget_ms",
        "error_rate_budget",
        "target",
    ):
        assert k in payload
    assert payload["target"] == "local-mock"


def test_loadtest_cli_local_mock_writes_artifact(tmp_path):
    """End-to-end CLI: --target=local-mock + --artifact-dir => JSON appears."""
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--rps", "5",
            "--duration", "1",
            "--dry-run-seed", "7",
            "--artifact-dir", str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    # Either PASS (0) or FAIL (1) is acceptable — we only care that the
    # script ran end-to-end + wrote the artifact.
    assert proc.returncode in (0, 1), proc.stderr
    artifacts = list(tmp_path.glob("loadtest_*.json"))
    assert len(artifacts) == 1
    payload = json.loads(artifacts[0].read_text())
    assert payload["target"] == "local-mock"


def test_loadtest_no_artifact_flag(tmp_path):
    """--no-artifact suppresses the JSON write."""
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--rps", "5",
            "--duration", "1",
            "--dry-run-seed", "7",
            "--artifact-dir", str(tmp_path),
            "--no-artifact",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1), proc.stderr
    artifacts = list(tmp_path.glob("loadtest_*.json"))
    assert len(artifacts) == 0


def test_local_mock_target_never_hits_network(monkeypatch):
    """Sanity: live_load is never called when target == local-mock.

    Replace live_load with a sentinel that raises if invoked; run main()
    with default args and assert it completes without raising.
    """
    mod = _load_module()

    def _boom(*a, **kw):
        raise AssertionError(
            "live_load was called for local-mock target — autonomous-safety "
            "invariant violated"
        )

    monkeypatch.setattr(mod, "live_load", _boom)
    rc = mod.main(["--rps", "5", "--duration", "1", "--dry-run-seed", "1", "--no-artifact"])
    assert rc in (0, 1)
