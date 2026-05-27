# SPDX-License-Identifier: Apache-2.0
"""Plan 42-04 Task 1 — contract tests for ``scripts/release/check_gate.sh``.

Invokes the bash gate via :mod:`subprocess` with ``EVAL_RUNS_DIR``,
``THRESHOLD_LOCK`` and ``EAR_TEST_GATE`` pointed at ``tmp_path``
fixtures. Pins:
    - 7 consecutive nightly green + ear-test green => exit 0
    - any nightly metric below lock OR ear-test fail => exit 1
    - missing/failing INTEL gate artifacts => exit 1
    - fewer than 7 nightly runs => exit 1
    - only the most-recent 7 are considered
    - jq missing => clear stderr
    - structured ``BLOCKED_BY=nightly|ear-test`` lines on failure
      (plus ``BLOCKED_BY=intel`` for INTEL fixture-gate regressions)
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import time
from pathlib import Path

import pytest

SCRIPT_PATH = Path("scripts/release/check_gate.sh").resolve()
INTEL_LOCK_PATH = Path("eval/INTEL-THRESHOLD-LOCK.md").resolve()
INTEL_FIXTURE_MANIFEST = Path("tests/intel/fixtures/MANIFEST.json").resolve()


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


def _intel_threshold_lock_hash() -> str:
    return "sha256:" + hashlib.sha256(INTEL_LOCK_PATH.read_bytes()).hexdigest()


def _intel_thresholds_hash() -> str:
    from scripts.eval.intel_scorecard import load_intel_thresholds_from_lock

    thresholds = load_intel_thresholds_from_lock(INTEL_LOCK_PATH)
    blob = json.dumps(thresholds, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def _intel_fixture_manifest_hash() -> str:
    return "sha256:" + hashlib.sha256(INTEL_FIXTURE_MANIFEST.read_bytes()).hexdigest()


def _intel_fixture_manifest() -> dict:
    return json.loads(INTEL_FIXTURE_MANIFEST.read_text(encoding="utf-8"))


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
    intel_gate_valid: bool = True,
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
    intel_manifest = _intel_fixture_manifest()
    intel = run / "intel_gate.json"
    intel.write_text(
        json.dumps(
            {
                "schema": "intel_gate_v1",
                "valid": intel_gate_valid,
                "errors": [] if intel_gate_valid else ["fixture regression"],
                "stages": {
                    "fixture_audit": {
                        "valid": intel_gate_valid,
                        "manifest_hash": _intel_fixture_manifest_hash(),
                    },
                    "scorecard": {
                        "valid": intel_gate_valid,
                        "passed": intel_gate_valid,
                        "artifact_status": {
                            "anlz": intel_gate_valid,
                            "cue_baseline": intel_gate_valid,
                            "section_retrieval": intel_gate_valid,
                            "transition_scorecard": intel_gate_valid,
                            "decision_replay": intel_gate_valid,
                            "gold_labels": intel_gate_valid,
                            "taste_scorecard": intel_gate_valid,
                        },
                        "metrics": {
                            "anlz_complete_rate": 1.0,
                            "section_role_hit_at_5_delta": 0.2,
                            "transition_pairwise_accuracy": 1.0,
                            "decision_exact_timing_floor_violation_rate": 0.0,
                            "taste_accepted_suggestion_lift": 0.18,
                        },
                        "gates": [
                            {
                                "metric": "section_role_hit_at_5_delta",
                                "status": "PASS" if intel_gate_valid else "FAIL",
                            }
                        ],
                        "provenance": {
                            "dataset_card_id": intel_manifest["dataset_card_id"],
                            "fixture_version": intel_manifest["fixture_version"],
                            "fixture_manifest_hash": _intel_fixture_manifest_hash(),
                            "thresholds_hash": _intel_thresholds_hash(),
                            "threshold_lock_hash": _intel_threshold_lock_hash(),
                            "replay_tier": "tier0_fixture_replay",
                        },
                    },
                    "provenance": {
                        "valid": intel_gate_valid,
                        "dataset_card_id": intel_manifest["dataset_card_id"],
                        "fixture_version": intel_manifest["fixture_version"],
                    },
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if mtime is not None:
        os.utime(run, (mtime, mtime))
        os.utime(out, (mtime, mtime))
        os.utime(intel, (mtime, mtime))
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


def test_missing_intel_gate_json_fails(tmp_path: Path):
    """7 dirs but one has no intel_gate.json -> exit 1, BLOCKED_BY=intel."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    (target / "intel_gate.json").unlink()
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "intel_gate.json missing" in result.stderr


def test_failing_intel_gate_json_fails(tmp_path: Path):
    """A recent intel_gate.json with valid=false blocks release."""
    runs = tmp_path / "eval-runs"
    runs.mkdir()
    now = time.time()
    for i in range(6):
        _make_nightly_run(runs, f"run_{i:02d}", mtime=now - (i * 3600))
    _make_nightly_run(
        runs,
        "run_intel_bad",
        intel_gate_valid=False,
        mtime=now - (6 * 3600),
    )
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "run_intel_bad" in result.stderr
    assert "valid=false" in result.stderr


def test_skinny_intel_gate_json_fails(tmp_path: Path):
    """valid=true is not enough; release gate requires reviewer evidence fields."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    (target / "intel_gate.json").write_text(
        json.dumps(
            {
                "schema": "intel_gate_v1",
                "valid": True,
                "stages": {
                    "fixture_audit": {"valid": True},
                    "scorecard": {"valid": True, "passed": True},
                    "provenance": {"valid": True},
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "scorecard.metrics missing" in result.stderr


def test_intel_gate_json_with_non_pass_gate_fails(tmp_path: Path):
    """A spoofed artifact cannot claim passed=true while hiding a failing gate."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    payload = json.loads((target / "intel_gate.json").read_text(encoding="utf-8"))
    payload["stages"]["scorecard"]["gates"][0]["status"] = "FAIL"
    (target / "intel_gate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "scorecard.gates contain non-PASS" in result.stderr


def test_intel_gate_json_with_false_artifact_status_fails(tmp_path: Path):
    """A spoofed artifact cannot claim passed=true while an input artifact is false."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    payload = json.loads((target / "intel_gate.json").read_text(encoding="utf-8"))
    payload["stages"]["scorecard"]["artifact_status"]["section_retrieval"] = False
    (target / "intel_gate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "scorecard.artifact_status contains false" in result.stderr


def test_intel_gate_json_with_wrong_replay_tier_fails(tmp_path: Path):
    """Release evidence must be the locked Tier 0 fixture replay artifact."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    payload = json.loads((target / "intel_gate.json").read_text(encoding="utf-8"))
    payload["stages"]["scorecard"]["provenance"]["replay_tier"] = "manual_notes"
    (target / "intel_gate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "scorecard.provenance.replay_tier=manual_notes" in result.stderr


def test_intel_gate_json_missing_provenance_hash_fails(tmp_path: Path):
    """Release evidence must carry hashes that explain exactly what passed."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    payload = json.loads((target / "intel_gate.json").read_text(encoding="utf-8"))
    payload["stages"]["scorecard"]["provenance"].pop("threshold_lock_hash")
    (target / "intel_gate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "scorecard.provenance.threshold_lock_hash missing" in result.stderr


def test_intel_gate_json_stale_fixture_manifest_hash_fails(tmp_path: Path):
    """Release evidence must match the current public INTEL fixture manifest."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    payload = json.loads((target / "intel_gate.json").read_text(encoding="utf-8"))
    payload["stages"]["scorecard"]["provenance"]["fixture_manifest_hash"] = "sha256:" + ("e" * 64)
    (target / "intel_gate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "scorecard.provenance.fixture_manifest_hash mismatch" in result.stderr


def test_intel_gate_json_wrong_scorecard_dataset_card_fails(tmp_path: Path):
    """Release evidence must name the current public INTEL dataset card."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    payload = json.loads((target / "intel_gate.json").read_text(encoding="utf-8"))
    payload["stages"]["scorecard"]["provenance"]["dataset_card_id"] = "old_dataset"
    (target / "intel_gate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "scorecard.provenance.dataset_card_id=old_dataset" in result.stderr


def test_intel_gate_json_wrong_provenance_fixture_version_fails(tmp_path: Path):
    """The provenance-validation stage must name the current fixture version."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    payload = json.loads((target / "intel_gate.json").read_text(encoding="utf-8"))
    payload["stages"]["provenance"]["fixture_version"] = "old_fixture"
    (target / "intel_gate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "provenance.fixture_version=old_fixture" in result.stderr


def test_intel_gate_json_missing_fixture_audit_manifest_hash_fails(tmp_path: Path):
    """Fixture audit stage must carry the same manifest evidence as scorecard provenance."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    payload = json.loads((target / "intel_gate.json").read_text(encoding="utf-8"))
    payload["stages"]["fixture_audit"].pop("manifest_hash")
    (target / "intel_gate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "fixture_audit.manifest_hash missing" in result.stderr


def test_intel_gate_json_fixture_audit_manifest_hash_disagreement_fails(tmp_path: Path):
    """The two INTEL stages cannot point at different fixture manifests."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    payload = json.loads((target / "intel_gate.json").read_text(encoding="utf-8"))
    payload["stages"]["fixture_audit"]["manifest_hash"] = "sha256:" + ("f" * 64)
    (target / "intel_gate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "fixture_audit.manifest_hash mismatch" in result.stderr


def test_intel_gate_json_stale_thresholds_hash_fails(tmp_path: Path):
    """Release evidence must match the current parsed INTEL threshold values."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    payload = json.loads((target / "intel_gate.json").read_text(encoding="utf-8"))
    payload["stages"]["scorecard"]["provenance"]["thresholds_hash"] = "sha256:" + ("a" * 64)
    (target / "intel_gate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "scorecard.provenance.thresholds_hash mismatch" in result.stderr


def test_intel_gate_json_stale_threshold_lock_hash_fails(tmp_path: Path):
    """Release evidence must match the current eval/INTEL-THRESHOLD-LOCK.md."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    target = next(runs.iterdir())
    payload = json.loads((target / "intel_gate.json").read_text(encoding="utf-8"))
    payload["stages"]["scorecard"]["provenance"]["threshold_lock_hash"] = "sha256:" + ("d" * 64)
    (target / "intel_gate.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)

    assert result.returncode == 1
    assert "BLOCKED_BY=intel" in result.stderr
    assert "scorecard.provenance.threshold_lock_hash mismatch" in result.stderr


def test_missing_intel_threshold_lock_fails_before_artifact_scan(tmp_path: Path):
    """The release gate must have the INTEL lock it compares artifacts against."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(
        runs,
        tl,
        ear,
        extra_env={"INTEL_THRESHOLD_LOCK": str(tmp_path / "missing-intel-lock.md")},
    )

    assert result.returncode == 1
    assert "INTEL-THRESHOLD-LOCK missing" in result.stderr


def test_missing_intel_fixture_manifest_fails_before_artifact_scan(tmp_path: Path):
    """The release gate must have the fixture manifest it compares artifacts against."""
    runs = tmp_path / "eval-runs"
    _seven_green_runs(runs)
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(
        runs,
        tl,
        ear,
        extra_env={"INTEL_FIXTURE_MANIFEST": str(tmp_path / "missing-MANIFEST.json")},
    )

    assert result.returncode == 1
    assert "INTEL fixture manifest missing" in result.stderr


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
        f"expected PASS; older bad runs should be ignored; stderr={result.stderr!r}"
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
            f1=0.80,  # ==
            substance=0.65,  # ==
            cited_cosine=0.40,  # ==
            bypass=0.15,  # ==
            mtime=now - (i * 3600),
        )
    tl = _make_threshold_lock(tmp_path)
    ear = _make_stub_gate(tmp_path / "ear_test_pass.sh", pass_=True)

    result = _run(runs, tl, ear)
    assert result.returncode == 0, f"boundary metrics should pass; stderr={result.stderr!r}"


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
