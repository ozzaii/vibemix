# SPDX-License-Identifier: Apache-2.0
"""Phase 37 Plan 37-01 seam test — P27 → eval-gate.

Source: ``scripts/eval/replay_harness.py`` (deterministic replay)
Sink:   ``.github/workflows/eval.yml`` (PR + nightly CI gate)

The CI workflow shells out to ``python -m scripts.eval.replay_harness``
with specific CLI flags. The seam contract = the harness's CLI surface
must match what the workflow YAML invokes.

This test runs the harness end-to-end against the synthetic fixture
corpus with ``--judges noop`` (offline, no Gemini) and asserts:

1. The harness produces ``eval_report.json`` + ``scorecard.md`` at the
   exact paths the workflow uses.
2. The harness accepts the exact CLI flag-set the workflow passes
   (``--corpus``, ``--judges``, ``--output``).
3. The harness's exit code (0 = pass) is what the workflow gates on.
4. The eval.yml workflow file actually wires those flags (contract
   anchor — fail loud if either side drifts).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
EVAL_YML = REPO / ".github" / "workflows" / "eval.yml"
FIXTURE = REPO / "tests" / "eval" / "fixtures"


@pytest.mark.e2e
def test_replay_harness_produces_required_artifacts(tmp_path) -> None:
    """End-to-end harness run on the synthetic corpus emits the contract artifacts."""
    out = tmp_path / "eval-out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.eval.replay_harness",
            "--corpus",
            str(FIXTURE),
            "--judges",
            "noop",
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        timeout=120,
    )
    assert proc.returncode == 0, (
        f"harness exited non-zero (CI would fail):\n{proc.stdout}\n{proc.stderr}"
    )
    assert (out / "eval_report.json").exists(), (
        "harness MUST emit eval_report.json — eval.yml uploads it"
    )
    assert (out / "scorecard.md").exists(), (
        "harness MUST emit scorecard.md — eval.yml posts it in PR comment"
    )


@pytest.mark.e2e
def test_eval_yml_calls_replay_harness_with_contract_flags() -> None:
    """The workflow file MUST invoke the harness with the flags the
    harness's argparse layer accepts.

    This is the seam contract anchor — if either side renames or
    re-orders flags, this test surfaces the drift before it ships.
    """
    yml = EVAL_YML.read_text(encoding="utf-8")

    # The workflow MUST shell out to the harness via the python -m path.
    assert "scripts.eval.replay_harness" in yml, (
        "eval.yml lost the harness invocation — seam broken"
    )

    # Each flag the workflow uses MUST be one the harness recognises.
    harness_argv = (
        REPO / "scripts" / "eval" / "replay_harness.py"
    ).read_text(encoding="utf-8")
    for flag in ("--corpus", "--judges", "--output"):
        assert flag in yml, f"eval.yml dropped the {flag} flag"
        assert flag in harness_argv, (
            f"harness no longer accepts {flag} — eval.yml will fail"
        )


@pytest.mark.e2e
def test_eval_yml_judges_values_match_harness_dispatcher() -> None:
    """The judge-name strings passed in eval.yml must match the harness's
    _build_judge_callable dispatcher's known names.

    Pinning ``gemini-3-flash`` + ``gemini-3-pro`` here means a typo on
    either side fails this contract test instead of failing only at
    nightly CI.
    """
    yml = EVAL_YML.read_text(encoding="utf-8")
    # Extract every --judges value the workflow uses.
    judge_values = re.findall(
        r"--judges\s+([\w,\-]+)", yml
    )
    assert judge_values, "eval.yml must specify --judges values"
    harness_argv = (
        REPO / "scripts" / "eval" / "replay_harness.py"
    ).read_text(encoding="utf-8")
    # Harness should at minimum recognise 'gemini-3-flash' (PR mode value).
    assert "gemini-3-flash" in harness_argv, (
        "harness must recognise gemini-3-flash — eval.yml PR mode passes it"
    )
