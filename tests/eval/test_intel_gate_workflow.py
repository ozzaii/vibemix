# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

import yaml

EVAL_YML = Path(".github/workflows/eval.yml")


def _steps() -> list[dict]:
    data = yaml.safe_load(EVAL_YML.read_text(encoding="utf-8"))
    return data["jobs"]["eval"]["steps"]


def test_eval_workflow_runs_intel_fixture_gate() -> None:
    steps = _steps()
    matches = [step for step in steps if step.get("name") == "Run INTEL fixture gate"]
    assert len(matches) == 1

    run_body = matches[0].get("run", "")
    assert "scripts/eval/intel_gate.py" in run_body
    assert "--fixture-dir tests/intel/fixtures" in run_body
    assert "--threshold-lock eval/INTEL-THRESHOLD-LOCK.md" in run_body
    assert "--output .planning/eval-runs/${{ github.sha }}/intel_gate.json" in run_body
    assert "--summary-markdown .planning/eval-runs/${{ github.sha }}/intel_gate.md" in run_body
    assert "--json" in run_body
    assert (
        'cat .planning/eval-runs/${{ github.sha }}/intel_gate.md >> "$GITHUB_STEP_SUMMARY"'
        in run_body
    )


def test_eval_workflow_validates_intel_recalibration_log() -> None:
    steps = _steps()
    matches = [step for step in steps if step.get("name") == "Validate INTEL recalibration log"]
    assert len(matches) == 1

    run_body = matches[0].get("run", "")
    assert "scripts/eval/intel_recalibration_log_validate.py" in run_body
    assert "eval/INTEL-THRESHOLD-RECALIBRATION-LOG.md" in run_body
    assert "--json" in run_body


def test_eval_workflow_runs_intel_gate_before_replay_harness() -> None:
    names = [step.get("name", "") for step in _steps()]
    recalibration_idx = names.index("Validate INTEL recalibration log")
    intel_idx = names.index("Run INTEL fixture gate")
    pr_replay_idx = names.index("Run replay harness (PR mode — Flash only)")
    nightly_replay_idx = names.index("Run replay harness (nightly canary — Pro + Flash)")

    assert recalibration_idx < intel_idx
    assert intel_idx < pr_replay_idx
    assert intel_idx < nightly_replay_idx


def test_eval_workflow_threshold_guard_covers_intel_lock() -> None:
    steps = _steps()
    target = next(
        step
        for step in steps
        if step.get("name") == "Threshold-lowering diff guard (Pitfall tampering)"
    )
    run_body = target.get("run", "")

    assert "eval/THRESHOLD-LOCK.md" in run_body
    assert "eval/INTEL-THRESHOLD-LOCK.md" in run_body
    assert "eval/INTEL gates re-ran" in run_body


def test_eval_workflow_dco_signs_nightly_evidence_commits() -> None:
    steps = _steps()
    target = next(
        step for step in steps if step.get("name") == "Commit eval-run artifact (nightly only)"
    )
    run_body = target.get("run", "")

    assert 'git config user.name "vibemix-eval-bot"' in run_body
    assert 'git config user.email "noreply@vibemix.dev"' in run_body
    assert "git commit -s -m" in run_body
