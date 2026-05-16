# SPDX-License-Identifier: Apache-2.0
"""Plan 42-04 Task 1 — contract tests for ``scripts/release/check_gate.sh``.

Invokes the bash gate via :mod:`subprocess` with ``EVAL_RUNS_DIR``,
``THRESHOLD_LOCK`` and ``EAR_TEST_GATE`` pointed at ``tmp_path``
fixtures. Pins:
    - 7 consecutive nightly green + ear-test green => exit 0
    - any nightly metric below lock OR ear-test fail => exit 1
    - fewer than 7 nightly runs => exit 1
    - only the most-recent 7 are considered
    - jq missing => clear stderr
    - structured ``BLOCKED_BY=nightly|ear-test`` lines on failure
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import time
from pathlib import Path

import pytest


SCRIPT_PATH = Path("scripts/release/check_gate.sh").resolve()


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


CANONICAL_THRESHOLDS = {
    "f1_min": 0.80,
    "substance_min": 0.65,
    "cited_cosine_min": 0.40,
    "bypass_max": 0.15,
    "per_genre_f1_min": 0.70,
}


def _make_threshold_lock(tmp_path: Path, **overrides: float) -> Path:
    """Write a minimal valid THRESHOLD-LOCK.md (frontmatter only)."""
    th = dict(CANONICAL_THRESHOLDS)
    th.update(overrides)
    body = (
        "---\n"
        "kaan_signed: autonomous_phase27\n"
        'kaan_signed_at: "2026-05-15T08:55:00Z"\n'
        "phase: 27\n"
        "milestone: v2.1\n"
        "thresholds:\n"
        f"  f1_min: {th['f1_min']}\n"
        f"  substance_min: {th['substance_min']}\n"
        f"  cited_cosine_min: {th['cited_cosine_min']}\n"
        f"  bypass_max: {th['bypass_max']}\n"
        f"  per_genre_f1_min: {th['per_genre_f1_min']}\n"
        "---\n\n"
        "# Test THRESHOLD-LOCK\n"
    )
    out = tmp_path / "THRESHOLD-LOCK.md"
    out.write_text(body, encoding="utf-8")
    return out


def _make_nightly_run(
    base: Path,
    name: str,
    *,
    f1: float = 0.85,
    substance: float = 0.70,
    cited_cosine: float = 0.50,
    bypass: float = 0.10,
    mtime: float | None = None,
) -> Path:
    """Create ``base/<name>/eval_report.json`` with the given metrics.

    Mirrors the schema written by ``scripts.eval.scorecard.render_scorecard``
    (top-level ``.overall.{f1,useful_response_ratio,cited_cosine,bypass_rate}``).
    """
    run = base / name
    run.mkdir(parents=True, exist_ok=True)
    payload = {
        "phase": 27,
        "generated_at": "2026-05-15T00:00:00Z",
        "thresholds": CANONICAL_THRESHOLDS,
        "overall": {
            "f1": f1,
            "useful_response_ratio": substance,
            "cited_cosine": cited_cosine,
            "bypass_rate": bypass,
        },
        "threshold_status": [],
        "per_detector": {},
        "per_detector_per_genre": {},
        "sessions": [],
    }
    out = run / "eval_report.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if mtime is not None:
        os.utime(run, (mtime, mtime))
        os.utime(out, (mtime, mtime))
    return run


def _make_stub_gate(path: Path, *, pass_: bool) -> Path:
    """Write a tiny bash script that exits 0 (pass) or 1 (fail)."""
    body = "#!/usr/bin/env bash\nexit 0\n" if pass_ else "#!/usr/bin/env bash\nexit 1\n"
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _run(
    eval_runs_dir: Path,
    threshold_lock: Path,
    ear_test_gate: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["EVAL_RUNS_DIR"] = str(eval_runs_dir)
    env["THRESHOLD_LOCK"] = str(threshold_lock)
    env["EAR_TEST_GATE"] = str(ear_test_gate)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        cwd=str(Path(__file__).resolve().parents[2]),
    )


def _seven_green_runs(base: Path) -> None:
    """Populate base/ with 7 fully-green nightly runs at distinct mtimes."""
    base.mkdir(parents=True, exist_ok=True)
    now = time.time()
    for i in range(7):
        _make_nightly_run(base, f"run_{i:02d}", mtime=now - (i * 3600))


# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------


def test_script_exists_and_executable():
    assert SCRIPT_PATH.is_file()
    assert os.access(SCRIPT_PATH, os.X_OK), "check_gate.sh not +x"


@pytest.fixture(autouse=True)
def _skip_if_no_jq():
    if shutil.which("jq") is None:
        pytest.skip("jq not on PATH — check_gate.sh requires it")


# ---------------------------------------------------------------------------
# Reject paths
# ---------------------------------------------------------------------------


def test_fewer_than_7_nightly_runs_fails(tmp_path: Path):
    """6 nightly dirs → exit 1, BLOCKED_BY=nightly."""
    runs = tmp_path / "eval-runs"
    runs.mkdir()
    now = time.time()
    for i in range(6):
        _make_nightly_run(runs, f"run_{i:02d}", mtime=now - (i * 3600))
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)
    assert result.returncode == 1
    assert "BLOCKED_BY=nightly" in result.stderr
    assert "only 6 consecutive nightly runs" in result.stderr


def test_one_nightly_below_f1_fails(tmp_path: Path):
    """7 dirs, one with f1=0.75 → exit 1 + names the failing dir."""
    runs = tmp_path / "eval-runs"
    runs.mkdir()
    now = time.time()
    for i in range(6):
        _make_nightly_run(runs, f"run_{i:02d}", mtime=now - (i * 3600))
    _make_nightly_run(runs, "run_bad", f1=0.75, mtime=now - (6 * 3600))
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)
    assert result.returncode == 1
    assert "BLOCKED_BY=nightly" in result.stderr
    assert "run_bad" in result.stderr
    assert "f1=" in result.stderr


def test_one_nightly_above_bypass_fails(tmp_path: Path):
    """bypass=0.20 on one of 7 → exit 1 (lock is 0.15 max)."""
    runs = tmp_path / "eval-runs"
    runs.mkdir()
    now = time.time()
    for i in range(6):
        _make_nightly_run(runs, f"run_{i:02d}", mtime=now - (i * 3600))
    _make_nightly_run(runs, "run_bypass", bypass=0.20, mtime=now - (6 * 3600))
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)
    assert result.returncode == 1
    assert "BLOCKED_BY=nightly" in result.stderr
    assert "bypass=" in result.stderr
    assert "run_bypass" in result.stderr


def test_one_nightly_below_substance_fails(tmp_path: Path):
    """useful_response_ratio=0.50 < lock 0.65 → exit 1."""
    runs = tmp_path / "eval-runs"
    runs.mkdir()
    now = time.time()
    for i in range(6):
        _make_nightly_run(runs, f"run_{i:02d}", mtime=now - (i * 3600))
    _make_nightly_run(runs, "run_sub", substance=0.50, mtime=now - (6 * 3600))
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)
    assert result.returncode == 1
    assert "substance=" in result.stderr


def test_one_nightly_below_cited_cosine_fails(tmp_path: Path):
    """cited_cosine=0.20 < lock 0.40 → exit 1."""
    runs = tmp_path / "eval-runs"
    runs.mkdir()
    now = time.time()
    for i in range(6):
        _make_nightly_run(runs, f"run_{i:02d}", mtime=now - (i * 3600))
    _make_nightly_run(runs, "run_cos", cited_cosine=0.20, mtime=now - (6 * 3600))
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)
    assert result.returncode == 1
    assert "cited_cosine=" in result.stderr


def test_ear_test_fail_blocks_even_when_nightly_green(tmp_path: Path):
    """7 green nightly + ear-test fail stub → exit 1, BLOCKED_BY=ear-test."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_fail.sh", pass_=False)

    result = _run(runs, tl, ear)
    assert result.returncode == 1
    assert "BLOCKED_BY=ear-test" in result.stderr


def test_both_fail_lists_both_blockers(tmp_path: Path):
    """Nightly fail + ear-test fail → BOTH BLOCKED_BY lines in stderr."""
    runs = tmp_path / "eval-runs"
    runs.mkdir()
    now = time.time()
    for i in range(6):
        _make_nightly_run(runs, f"run_{i:02d}", mtime=now - (i * 3600))
    _make_nightly_run(runs, "run_bad", f1=0.10, mtime=now - (6 * 3600))
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_fail.sh", pass_=False)

    result = _run(runs, tl, ear)
    assert result.returncode == 1
    assert "BLOCKED_BY=nightly" in result.stderr
    assert "BLOCKED_BY=ear-test" in result.stderr


def test_missing_eval_report_json_fails(tmp_path: Path):
    """7 dirs but one has no eval_report.json → exit 1."""
    runs = tmp_path / "eval-runs"
    runs.mkdir()
    now = time.time()
    for i in range(6):
        _make_nightly_run(runs, f"run_{i:02d}", mtime=now - (i * 3600))
    empty = runs / "run_empty"
    empty.mkdir()
    os.utime(empty, (now - (6 * 3600), now - (6 * 3600)))
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)
    assert result.returncode == 1
    assert "BLOCKED_BY=nightly" in result.stderr
    assert "eval_report.json missing" in result.stderr


# ---------------------------------------------------------------------------
# Accept paths
# ---------------------------------------------------------------------------


def test_seven_nightly_green_plus_ear_test_green_passes(tmp_path: Path):
    """7 green nightly + ear-test green → exit 0."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)
    assert result.returncode == 0, (
        f"expected PASS; stdout={result.stdout!r}; stderr={result.stderr!r}"
    )
    assert "PASS check_gate" in result.stdout


def test_only_most_recent_7_considered(tmp_path: Path):
    """10 dirs total; oldest 3 are BAD → exit 0 (oldest outside window)."""
    runs = tmp_path / "eval-runs"
    runs.mkdir()
    now = time.time()
    # 7 recent green
    for i in range(7):
        _make_nightly_run(runs, f"recent_{i:02d}", mtime=now - (i * 3600))
    # 3 older with terrible scores — must be excluded by the window
    for i in range(3):
        _make_nightly_run(
            runs,
            f"old_{i:02d}",
            f1=0.10,
            substance=0.10,
            cited_cosine=0.10,
            bypass=0.99,
            mtime=now - ((10 + i) * 3600),
        )
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)
    assert result.returncode == 0, (
        f"expected PASS; older bad runs should be ignored; "
        f"stderr={result.stderr!r}"
    )


def test_boundary_metric_equal_passes(tmp_path: Path):
    """Metric == lock value passes (≥ / ≤ are inclusive)."""
    runs = tmp_path / "eval-runs"
    runs.mkdir()
    now = time.time()
    for i in range(7):
        _make_nightly_run(
            runs,
            f"run_{i:02d}",
            f1=0.80,            # ==
            substance=0.65,     # ==
            cited_cosine=0.40,  # ==
            bypass=0.15,        # ==
            mtime=now - (i * 3600),
        )
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)
    assert result.returncode == 0, (
        f"boundary metrics should pass; stderr={result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# Tooling absence
# ---------------------------------------------------------------------------


def test_jq_unavailable_clear_error(tmp_path: Path):
    """PATH stripped of jq → exit nonzero with stderr mentioning jq."""
    safe_path = "/bin:/usr/bin:/usr/sbin"
    if shutil.which("jq", path=safe_path) is not None:
        pytest.skip("jq present in minimal PATH; cannot simulate absence")
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear, extra_env={"PATH": safe_path})
    assert result.returncode != 0
    err = result.stderr.lower()
    assert "jq" in err and ("required" in err or "not found" in err)


# ---------------------------------------------------------------------------
# GitHub Actions annotation mode
# ---------------------------------------------------------------------------


def test_github_actions_annotation_on_reject(tmp_path: Path):
    """When GITHUB_ACTIONS=true, rejects use ::error:: prefixes."""
    runs = tmp_path / "eval-runs"
    # Empty / nothing → triggers reject path
    runs.mkdir()
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear, extra_env={"GITHUB_ACTIONS": "true"})
    assert result.returncode == 1
    assert "::error::check_gate:" in result.stderr
