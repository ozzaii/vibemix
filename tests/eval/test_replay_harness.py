# SPDX-License-Identifier: Apache-2.0
"""Phase 27-01 — replay_harness CLI integration tests."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.eval.replay_harness import (
    DEFAULT_THRESHOLDS,
    call_judges_stub,
    main,
    replay_one_session,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_smoke_writes_eval_report_and_scorecard(tmp_path: Path) -> None:
    """Test 1: invoking the CLI against the synthetic fixture writes valid artifacts."""
    out = tmp_path / "out"
    rc = main(
        [
            "--corpus",
            str(FIXTURES),
            "--judges",
            "noop",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert (out / "eval_report.json").exists()
    assert (out / "scorecard.md").exists()
    data = json.loads((out / "eval_report.json").read_text())
    assert "sessions" in data
    assert len(data["sessions"]) >= 1
    md = (out / "scorecard.md").read_text()
    assert md.startswith("# vibemix Eval Scorecard")


def test_call_judges_stub_returns_deterministic_verdict() -> None:
    """Test 2: noop stub returns the documented verdict shape."""
    verdict = call_judges_stub({"id": "x", "type": "TRACK_CHANGE", "t_session": 1.0}, "")
    assert verdict["pro"]["verdict"] == "pass"
    assert verdict["pro"]["substance"] == 0.7
    assert verdict["pro"]["f1_contribution"] == 1.0
    assert verdict["flash"]["pass"] is True


def test_replay_one_session_constructs_real_primitives(synthetic_session: Path) -> None:
    """Test 3: replay_one_session uses real EvidenceRegistry/EventDetector/CitationLinter.

    We assert the result shape rather than poking the internals — proving the
    constructor calls succeed without mocks.
    """
    result = asyncio.run(replay_one_session(synthetic_session, "noop"))
    assert result["session"] == synthetic_session.name
    assert "predicted_events" in result
    assert "f1" in result
    assert "verdicts" in result
    assert "useful_response_ratio" in result
    assert "bypass_rate" in result
    # noop happy path: predicted = ground_truth, F1 == 1.0
    assert result["f1"]["f1"] == 1.0


def test_scorecard_threshold_block_present(tmp_path: Path) -> None:
    """Test 4: scorecard markdown contains the Threshold Status block."""
    out = tmp_path / "out"
    main(
        [
            "--corpus",
            str(FIXTURES),
            "--judges",
            "noop",
            "--output",
            str(out),
        ]
    )
    md = (out / "scorecard.md").read_text()
    assert "## Threshold Status" in md
    assert "## Per-Detector-Per-Genre F1 Matrix" in md
    assert "## Per-Session Results" in md


def test_default_thresholds_match_context_eval_06() -> None:
    """Test 5: default thresholds dict matches CONTEXT EVAL-06."""
    assert DEFAULT_THRESHOLDS["f1_min"] == 0.80
    assert DEFAULT_THRESHOLDS["substance_min"] == 0.65
    assert DEFAULT_THRESHOLDS["cited_cosine_min"] == 0.4
    assert DEFAULT_THRESHOLDS["bypass_max"] == 0.15
    assert DEFAULT_THRESHOLDS["per_genre_f1_min"] == 0.70


def test_cli_exits_1_when_threshold_violation_injected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 6: CLI exits 1 when any session falls below threshold.

    We monkeypatch DEFAULT_THRESHOLDS to set a substance_min higher than the
    noop stub's ratio (=1.0 per ground_truth pass count, but bypass_rate is
    0.0 — instead bump bypass_max to a sub-zero impossible value).
    """
    out = tmp_path / "out"
    # Force a threshold violation: bypass_max must be exceeded.
    # noop happy path has bypass_rate = 0.0, so we need to make 0.0 > bypass_max.
    # Set bypass_max to -0.1 — 0.0 > -0.1 → fail.
    import scripts.eval.replay_harness as harness_mod

    monkeypatch.setitem(harness_mod.DEFAULT_THRESHOLDS, "bypass_max", -0.1)
    rc = main(
        [
            "--corpus",
            str(FIXTURES),
            "--judges",
            "noop",
            "--output",
            str(out),
        ]
    )
    assert rc == 1


def test_cli_subprocess_invocation_exits_0_on_synth_happy_path(tmp_path: Path) -> None:
    """End-to-end: invoke the harness via subprocess, validate exit code + artifacts."""
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.eval.replay_harness",
            "--corpus",
            str(FIXTURES),
            "--judges",
            "noop",
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parents[2]),
    )
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert (out / "eval_report.json").exists()
    assert (out / "scorecard.md").exists()


def test_empty_corpus_returns_0_with_artifacts(tmp_path: Path) -> None:
    """Defensive: empty corpus exits 0 + writes empty-shape artifacts (Plan 04 owns the gate)."""
    empty = tmp_path / "empty_corpus"
    empty.mkdir()
    out = tmp_path / "out"
    rc = main(
        [
            "--corpus",
            str(empty),
            "--judges",
            "noop",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert (out / "eval_report.json").exists()
    data = json.loads((out / "eval_report.json").read_text())
    assert data["sessions"] == []


def test_judges_unknown_value_raises_not_implemented(tmp_path: Path) -> None:
    """--judges with an unknown name raises NotImplementedError (Plan 02 wires real ones)."""
    from scripts.eval.replay_harness import _build_judge_callable

    with pytest.raises(NotImplementedError):
        _build_judge_callable("gemini-3-flash")  # Plan 02 path
