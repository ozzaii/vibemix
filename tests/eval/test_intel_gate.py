# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.intel_gate import (
    DEFAULT_FIXTURE_DIR,
    DEFAULT_THRESHOLD_LOCK,
    main,
    render_markdown_summary,
    run_intel_gate,
)
from scripts.eval.intel_scorecard import DEFAULT_THRESHOLDS


def _write_threshold_lock(path: Path, *, overrides: dict[str, float] | None = None) -> None:
    thresholds = {**DEFAULT_THRESHOLDS, **(overrides or {})}
    body = ["---", "schema: intel_threshold_lock_v1", "intel_thresholds:"]
    body.extend(f"  {key}: {value}" for key, value in thresholds.items())
    body.extend(["---", "", "# Test INTEL lock", ""])
    path.write_text("\n".join(body), encoding="utf-8")


def test_run_intel_gate_passes_public_fixture_corpus() -> None:
    result = run_intel_gate(
        fixture_dir=DEFAULT_FIXTURE_DIR,
        threshold_lock=DEFAULT_THRESHOLD_LOCK,
    )

    assert result["schema"] == "intel_gate_v1"
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["stages"]["fixture_audit"]["valid"] is True
    assert result["stages"]["scorecard"]["passed"] is True
    assert result["stages"]["provenance"]["valid"] is True
    assert result["stages"]["scorecard"]["eval_run_id"].startswith("eval_intel_scorecard_")
    assert "section_role_hit_at_5_delta" in result["stages"]["scorecard"]["metrics"]
    assert result["stages"]["scorecard"]["artifact_status"]["section_retrieval"] is True
    assert result["stages"]["scorecard"]["gates"]
    assert result["stages"]["scorecard"]["provenance"]["fixture_manifest_hash"].startswith(
        "sha256:"
    )
    assert result["stages"]["scorecard"]["provenance"]["threshold_lock_hash"].startswith("sha256:")


def test_run_intel_gate_fails_on_locked_threshold_regression(tmp_path: Path) -> None:
    lock = tmp_path / "INTEL-THRESHOLD-LOCK.md"
    _write_threshold_lock(lock, overrides={"section_role_hit_at_5_delta_min": 0.99})

    result = run_intel_gate(fixture_dir=DEFAULT_FIXTURE_DIR, threshold_lock=lock)

    assert result["valid"] is False
    assert result["stages"]["fixture_audit"]["valid"] is True
    assert result["stages"]["scorecard"]["passed"] is False
    assert any("section_role_hit_at_5_delta" in error for error in result["errors"])


def test_intel_gate_cli_json(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "--fixture-dir",
                str(DEFAULT_FIXTURE_DIR),
                "--threshold-lock",
                str(DEFAULT_THRESHOLD_LOCK),
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert payload["stages"]["provenance"]["valid"] is True


def test_intel_gate_cli_writes_output_file(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    output = tmp_path / "reports" / "intel_gate.json"

    assert (
        main(
            [
                "--fixture-dir",
                str(DEFAULT_FIXTURE_DIR),
                "--threshold-lock",
                str(DEFAULT_THRESHOLD_LOCK),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "intel_gate_v1"
    assert payload["valid"] is True
    assert payload["stages"]["scorecard"]["eval_run_id"].startswith("eval_intel_scorecard_")
    assert "transition_pairwise_accuracy" in payload["stages"]["scorecard"]["metrics"]
    assert payload["stages"]["scorecard"]["provenance"]["replay_tier"] == "tier0_fixture_replay"
    assert "INTEL gate passed" in capsys.readouterr().out


def test_render_markdown_summary_reports_stage_status() -> None:
    result = run_intel_gate(
        fixture_dir=DEFAULT_FIXTURE_DIR,
        threshold_lock=DEFAULT_THRESHOLD_LOCK,
    )

    markdown = render_markdown_summary(result)

    assert "# INTEL Fixture Gate" in markdown
    assert "**Status:** PASS" in markdown
    assert "| `fixture_audit` | PASS |" in markdown
    assert "| `scorecard` | PASS |" in markdown
    assert "| `provenance` | PASS |" in markdown
    assert "eval_intel_scorecard_" in markdown


def test_intel_gate_cli_writes_markdown_summary(tmp_path: Path) -> None:
    summary = tmp_path / "reports" / "intel_gate.md"

    assert (
        main(
            [
                "--fixture-dir",
                str(DEFAULT_FIXTURE_DIR),
                "--threshold-lock",
                str(DEFAULT_THRESHOLD_LOCK),
                "--summary-markdown",
                str(summary),
            ]
        )
        == 0
    )

    markdown = summary.read_text(encoding="utf-8")
    assert "**Status:** PASS" in markdown
    assert "| `scorecard` | PASS |" in markdown
