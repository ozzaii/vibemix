# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.intel_gold import DEFAULT_FIXTURE_DIR, report_gold_file
from scripts.eval.intel_recalibration_log_validate import (
    main,
    validate_recalibration_log,
)
from scripts.eval.intel_recalibration_note import APPEND_MARKER, build_recalibration_note
from scripts.eval.intel_scorecard import score_fixture_dir
from scripts.eval.intel_taste_scorecard import score_fixture_dir as score_taste_fixture_dir

REPO_ROOT = Path(__file__).resolve().parents[2]
LOG = REPO_ROOT / "eval" / "INTEL-THRESHOLD-RECALIBRATION-LOG.md"
INTEL_LOCK_PATH = REPO_ROOT / "eval" / "INTEL-THRESHOLD-LOCK.md"


def test_validate_current_public_recalibration_log() -> None:
    report = validate_recalibration_log(LOG)

    assert report.valid is True
    assert report.errors == ()
    assert report.summary["schema"] == "intel_recalibration_log_validation_v1"


def test_validate_generated_recalibration_entry(tmp_path: Path) -> None:
    log = _write_log(tmp_path, _valid_entry())

    report = validate_recalibration_log(log)

    assert report.valid is True
    assert report.errors == ()
    assert report.summary["entry_count"] == 1


def test_validate_rejects_entry_without_report_hashes(tmp_path: Path) -> None:
    entry = "\n".join(
        line for line in _valid_entry().splitlines() if not line.startswith("- report_hashes:")
    )
    log = _write_log(tmp_path, entry)

    report = validate_recalibration_log(log)

    assert report.valid is False
    assert "entry[1].missing:report_hashes" in report.errors
    assert "entry[1].report_hashes.gold_report" in report.errors


def test_validate_rejects_null_core_report_hashes(tmp_path: Path) -> None:
    entry = _replace_key_value(_valid_entry(), "- reports:", "scorecard", "null")
    entry = _replace_key_value(entry, "- report_hashes:", "scorecard", "null")
    log = _write_log(tmp_path, entry)

    report = validate_recalibration_log(log)

    assert report.valid is False
    assert "entry[1].reports.scorecard.required" in report.errors
    assert "entry[1].report_hashes.scorecard.required" in report.errors


def test_validate_rejects_missing_required_metric(tmp_path: Path) -> None:
    entry = _replace_field(
        _valid_entry(),
        "measured",
        "section_role_hit_at_5_delta=0.20 transition_accept_at_3=1.00 "
        "decision_exact_timing_floor_violation_rate=0.00",
    )
    log = _write_log(tmp_path, entry)

    report = validate_recalibration_log(log)

    assert report.valid is False
    assert "entry[1].measured.taste_accepted_suggestion_lift" in report.errors


def test_validate_rejects_delta_mismatch(tmp_path: Path) -> None:
    entry = _replace_field(
        _valid_entry(),
        "delta",
        "section_role_hit_at_5_delta=+9.99 transition_accept_at_3=+0.20 "
        "decision_exact_timing_floor_violation_rate=+0.00 "
        "taste_accepted_suggestion_lift=+0.08",
    )
    log = _write_log(tmp_path, entry)

    report = validate_recalibration_log(log)

    assert report.valid is False
    assert "entry[1].delta.section_role_hit_at_5_delta.mismatch" in report.errors


def test_validate_rejects_unsigned_delta(tmp_path: Path) -> None:
    entry = _replace_field(
        _valid_entry(),
        "delta",
        "section_role_hit_at_5_delta=0.05 transition_accept_at_3=+0.20 "
        "decision_exact_timing_floor_violation_rate=+0.00 "
        "taste_accepted_suggestion_lift=+0.08",
    )
    log = _write_log(tmp_path, entry)

    report = validate_recalibration_log(log)

    assert report.valid is False
    assert "entry[1].delta.section_role_hit_at_5_delta.numeric" in report.errors


def test_validate_rejects_in_tolerance_verdict_with_failed_metric(tmp_path: Path) -> None:
    entry = _replace_field(
        _valid_entry(),
        "measured",
        "section_role_hit_at_5_delta=0.10 transition_accept_at_3=1.00 "
        "decision_exact_timing_floor_violation_rate=0.00 "
        "taste_accepted_suggestion_lift=0.18",
    )
    entry = _replace_field(
        entry,
        "delta",
        "section_role_hit_at_5_delta=-0.05 transition_accept_at_3=+0.20 "
        "decision_exact_timing_floor_violation_rate=+0.00 "
        "taste_accepted_suggestion_lift=+0.08",
    )
    log = _write_log(tmp_path, entry)

    report = validate_recalibration_log(log)

    assert report.valid is False
    assert "entry[1].verdict.metric_failures:section_role_hit_at_5_delta" in report.errors


def test_validate_rejects_action_that_disagrees_with_verdict(tmp_path: Path) -> None:
    entry = _replace_field(_valid_entry(), "action", "RECALIBRATION_REQUIRED")
    log = _write_log(tmp_path, entry)

    report = validate_recalibration_log(log)

    assert report.valid is False
    assert "entry[1].tolerance_action" in report.errors


def test_validate_release_promotion_requires_gate_report_hash(tmp_path: Path) -> None:
    entry = _valid_entry().replace(
        "### 2026-05-27T12:00:00Z - verdict=private_in_tolerance",
        "### 2026-05-27T12:00:00Z - verdict=release_promoted",
    )
    entry = _replace_field(entry, "evidence_tier", "tier2_private_holdout_canary")
    entry = _replace_field(entry, "splits", "calibration=1 holdout=1 canary=1")
    entry = _replace_field(entry, "verdict", "release_promoted")
    entry = _replace_field(entry, "action", "PROMOTE_LOCK_WITH_PR")
    log = _write_log(tmp_path, entry)

    report = validate_recalibration_log(log)

    assert report.valid is False
    assert "entry[1].reports.gate.required" in report.errors
    assert "entry[1].report_hashes.gate.required" in report.errors


def test_validate_rejects_private_payload_marker(tmp_path: Path) -> None:
    entry = _valid_entry().replace(
        "run_id: intel_private_test",
        "run_id: intel_private_test /Users/ozai/Music/private.wav",
    )
    log = _write_log(tmp_path, entry)

    report = validate_recalibration_log(log)

    assert report.valid is False
    assert any(str(error).startswith("private_payload_present:") for error in report.errors)


def test_recalibration_log_validator_cli_json(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    log = _write_log(tmp_path, _valid_entry())

    assert main([str(log), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert payload["entry_count"] == 1


def _valid_entry() -> str:
    result = build_recalibration_note(
        scorecard=score_fixture_dir(DEFAULT_FIXTURE_DIR, threshold_lock_path=INTEL_LOCK_PATH),
        gold_report=report_gold_file(
            DEFAULT_FIXTURE_DIR / "gold_labels_redacted.jsonl", salt="test"
        ),
        taste_scorecard=score_taste_fixture_dir(DEFAULT_FIXTURE_DIR),
        evidence_tier="tier1_private_calibration",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
        run_id="intel_private_test",
    )
    assert result["valid"] is True
    return result["entry"]


def _write_log(tmp_path: Path, entry: str) -> Path:
    log = tmp_path / "INTEL-THRESHOLD-RECALIBRATION-LOG.md"
    log.write_text(f"# Log\n\n{APPEND_MARKER}\n\n{entry.strip()}\n", encoding="utf-8")
    return log


def _replace_field(entry: str, field: str, value: str) -> str:
    return "\n".join(
        f"- {field}: {value}" if line.startswith(f"- {field}: ") else line
        for line in entry.splitlines()
    )


def _replace_key_value(entry: str, line_prefix: str, key: str, value: str) -> str:
    lines: list[str] = []
    for line in entry.splitlines():
        if line.startswith(line_prefix):
            line = " ".join(
                f"{key}={value}" if part.startswith(f"{key}=") else part for part in line.split()
            )
        lines.append(line)
    return "\n".join(lines)
