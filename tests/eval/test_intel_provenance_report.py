# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.intel_provenance_report import main, validate_scorecard_provenance
from scripts.eval.intel_scorecard import DEFAULT_FIXTURE_DIR, score_fixture_dir

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTEL_LOCK_PATH = PROJECT_ROOT / "eval" / "INTEL-THRESHOLD-LOCK.md"


def _scorecard() -> dict[str, object]:
    return score_fixture_dir(DEFAULT_FIXTURE_DIR, threshold_lock_path=INTEL_LOCK_PATH)


def test_validate_scorecard_provenance_accepts_locked_fixture_scorecard() -> None:
    report = validate_scorecard_provenance(
        _scorecard(),
        fixture_dir=DEFAULT_FIXTURE_DIR,
        threshold_lock=INTEL_LOCK_PATH,
    )

    assert report.valid is True
    assert report.errors == ()
    assert report.summary["schema"] == "intel_provenance_report_v1"
    assert report.summary["eval_run_id"].startswith("eval_intel_scorecard_")
    assert report.summary["dataset_card_id"] == "dataset_intel_synthetic_v1"


def test_validate_scorecard_provenance_rejects_missing_provenance() -> None:
    scorecard = _scorecard()
    scorecard.pop("provenance")

    report = validate_scorecard_provenance(scorecard)

    assert report.valid is False
    assert "missing provenance object" in report.errors
    assert "provenance.eval_run_id must be a non-empty string" in report.errors


def test_validate_scorecard_provenance_rejects_local_path_leak() -> None:
    scorecard = _scorecard()
    scorecard["provenance"]["replay_command"] += " --debug-path /Users/ozai/private.wav"  # type: ignore[index]

    report = validate_scorecard_provenance(scorecard)

    assert report.valid is False
    assert any("local/private path pattern" in error for error in report.errors)


def test_validate_scorecard_provenance_rejects_hash_drift() -> None:
    scorecard = _scorecard()
    scorecard["thresholds"]["section_role_hit_at_5_delta_min"] = 0.99  # type: ignore[index]

    report = validate_scorecard_provenance(scorecard)

    assert report.valid is False
    assert "provenance.thresholds_hash does not match scorecard thresholds" in report.errors


def test_intel_provenance_report_cli_json(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    scorecard_path = tmp_path / "scorecard.json"
    scorecard_path.write_text(json.dumps(_scorecard()), encoding="utf-8")

    assert (
        main(
            [
                "validate",
                str(scorecard_path),
                "--fixture-dir",
                str(DEFAULT_FIXTURE_DIR),
                "--threshold-lock",
                str(INTEL_LOCK_PATH),
                "--json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert payload["errors"] == []
    assert payload["eval_run_id"].startswith("eval_intel_scorecard_")
