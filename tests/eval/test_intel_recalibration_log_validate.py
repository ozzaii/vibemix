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
