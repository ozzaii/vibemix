# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.intel_gate import run_intel_gate
from scripts.eval.intel_gold import DEFAULT_FIXTURE_DIR, report_gold_file
from scripts.eval.intel_recalibration_note import (
    APPEND_MARKER,
    append_recalibration_note,
    build_recalibration_note,
    main,
)
from scripts.eval.intel_scorecard import score_fixture_dir
from scripts.eval.intel_taste_scorecard import score_fixture_dir as score_taste_fixture_dir

INTEL_LOCK_PATH = Path("eval/INTEL-THRESHOLD-LOCK.md").resolve()


def _scorecard() -> dict:
    return score_fixture_dir(DEFAULT_FIXTURE_DIR, threshold_lock_path=INTEL_LOCK_PATH)


def _gold_report() -> dict:
    return report_gold_file(DEFAULT_FIXTURE_DIR / "gold_labels_redacted.jsonl", salt="test")


def _gold_report_with_all_splits() -> dict:
    report = _gold_report()
    report["counts"]["splits"] = {"calibration": 7, "holdout": 5, "canary": 3}
    return report


def test_build_recalibration_note_renders_redacted_tier1_entry() -> None:
    result = build_recalibration_note(
        scorecard=_scorecard(),
        gold_report=_gold_report(),
        taste_scorecard=score_taste_fixture_dir(DEFAULT_FIXTURE_DIR),
        evidence_tier="tier1_private_calibration",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
        run_id="intel_private_test",
    )

    assert result["valid"] is True
    assert result["verdict"] == "private_in_tolerance"
    assert result["action"] == "none"
    entry = result["entry"]
    assert "### 2026-05-27T12:00:00Z - verdict=private_in_tolerance" in entry
    assert "- evidence_tier: tier1_private_calibration" in entry
    assert "gold_report=private:redacted" in entry
    assert "section_role_hit_at_5_delta=" in entry
    assert "/Users/" not in entry
    assert "file://" not in entry


def test_tier2_release_evidence_requires_holdout_and_canary_splits() -> None:
    result = build_recalibration_note(
        scorecard=_scorecard(),
        gold_report=_gold_report(),
        evidence_tier="tier2_private_holdout_canary",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
    )

    assert result["valid"] is False
    assert "missing_private_split:holdout" in result["errors"]
    assert "missing_private_split:canary" in result["errors"]


def test_release_promotion_requires_tier2_and_all_splits() -> None:
    result = build_recalibration_note(
        scorecard=_scorecard(),
        gold_report=_gold_report_with_all_splits(),
        taste_scorecard=score_taste_fixture_dir(DEFAULT_FIXTURE_DIR),
        gate_report=run_intel_gate(fixture_dir=DEFAULT_FIXTURE_DIR, threshold_lock=INTEL_LOCK_PATH),
        evidence_tier="tier2_private_holdout_canary",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
        promote_release=True,
    )

    assert result["valid"] is True
    assert result["verdict"] == "release_promoted"
    assert result["action"] == "PROMOTE_LOCK_WITH_PR"
    assert "calibration=7 holdout=5 canary=3" in result["entry"]


def test_release_promotion_requires_gate_report() -> None:
    result = build_recalibration_note(
        scorecard=_scorecard(),
        gold_report=_gold_report_with_all_splits(),
        evidence_tier="tier2_private_holdout_canary",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
        promote_release=True,
    )

    assert result["valid"] is False
    assert "release_promotion_requires_gate_report" in result["errors"]


def test_release_promotion_rejects_stale_gate_lock_hash() -> None:
    gate = run_intel_gate(fixture_dir=DEFAULT_FIXTURE_DIR, threshold_lock=INTEL_LOCK_PATH)
    gate["stages"]["scorecard"]["provenance"]["threshold_lock_hash"] = "sha256:" + ("0" * 64)

    result = build_recalibration_note(
        scorecard=_scorecard(),
        gold_report=_gold_report_with_all_splits(),
        gate_report=gate,
        evidence_tier="tier2_private_holdout_canary",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
        promote_release=True,
    )

    assert result["valid"] is False
    assert "gate.scorecard.threshold_lock_hash" in result["errors"]


def test_release_promotion_rejects_failed_scorecard_report() -> None:
    scorecard = _scorecard()
    scorecard["passed"] = False

    result = build_recalibration_note(
        scorecard=scorecard,
        gold_report=_gold_report_with_all_splits(),
        gate_report=run_intel_gate(fixture_dir=DEFAULT_FIXTURE_DIR, threshold_lock=INTEL_LOCK_PATH),
        evidence_tier="tier2_private_holdout_canary",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
        promote_release=True,
    )

    assert result["valid"] is False
    assert "scorecard.passed" in result["errors"]


def test_release_promotion_rejects_scorecard_lock_hash_mismatch() -> None:
    scorecard = _scorecard()
    scorecard["provenance"]["threshold_lock"]["hash"] = "sha256:" + ("1" * 64)

    result = build_recalibration_note(
        scorecard=scorecard,
        gold_report=_gold_report_with_all_splits(),
        gate_report=run_intel_gate(fixture_dir=DEFAULT_FIXTURE_DIR, threshold_lock=INTEL_LOCK_PATH),
        evidence_tier="tier2_private_holdout_canary",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
        promote_release=True,
    )

    assert result["valid"] is False
    assert "scorecard.provenance.threshold_lock.hash" in result["errors"]


def test_release_promotion_rejects_gate_scorecard_threshold_hash_mismatch() -> None:
    gate = run_intel_gate(fixture_dir=DEFAULT_FIXTURE_DIR, threshold_lock=INTEL_LOCK_PATH)
    gate["stages"]["scorecard"]["provenance"]["thresholds_hash"] = "sha256:" + ("2" * 64)

    result = build_recalibration_note(
        scorecard=_scorecard(),
        gold_report=_gold_report_with_all_splits(),
        gate_report=gate,
        evidence_tier="tier2_private_holdout_canary",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
        promote_release=True,
    )

    assert result["valid"] is False
    assert "gate.scorecard.thresholds_hash_mismatch" in result["errors"]


def test_release_promotion_rejects_invalid_gate_report() -> None:
    gate = run_intel_gate(fixture_dir=DEFAULT_FIXTURE_DIR, threshold_lock=INTEL_LOCK_PATH)
    gate["valid"] = False

    result = build_recalibration_note(
        scorecard=_scorecard(),
        gold_report=_gold_report_with_all_splits(),
        gate_report=gate,
        evidence_tier="tier2_private_holdout_canary",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
        promote_release=True,
    )

    assert result["valid"] is False
    assert "gate.valid" in result["errors"]


def test_private_payload_in_reports_blocks_note() -> None:
    gold = _gold_report()
    gold["examples"].append({"note": "/Users/ozai/Music/private.wav"})

    result = build_recalibration_note(
        scorecard=_scorecard(),
        gold_report=gold,
        evidence_tier="tier1_private_calibration",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
    )

    assert result["valid"] is False
    assert any(str(error).startswith("private_payload_present:") for error in result["errors"])


def test_recalibration_note_cli_writes_markdown_and_json(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    scorecard = tmp_path / "scorecard.json"
    gold = tmp_path / "gold_report.json"
    out = tmp_path / "entry.md"
    scorecard.write_text(json.dumps(_scorecard()), encoding="utf-8")
    gold.write_text(json.dumps(_gold_report()), encoding="utf-8")

    rc = main(
        [
            "--scorecard",
            str(scorecard),
            "--gold-report",
            str(gold),
            "--evidence-tier",
            "tier1_private_calibration",
            "--timestamp",
            "2026-05-27T12:00:00Z",
            "--run-id",
            "intel_private_cli",
            "--output",
            str(out),
            "--json",
        ]
    )

    assert rc == 0
    result = json.loads(capsys.readouterr().out)
    assert result["valid"] is True
    assert out.read_text(encoding="utf-8") == result["entry"]


def test_append_recalibration_note_appends_after_marker(tmp_path: Path) -> None:
    log = tmp_path / "INTEL-THRESHOLD-RECALIBRATION-LOG.md"
    log.write_text(f"# Log\n\n{APPEND_MARKER}\n", encoding="utf-8")
    result = build_recalibration_note(
        scorecard=_scorecard(),
        gold_report=_gold_report(),
        evidence_tier="tier1_private_calibration",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
        run_id="intel_private_append",
    )

    appended = append_recalibration_note(log, result)

    text = appended.read_text(encoding="utf-8")
    assert APPEND_MARKER in text
    assert text.index(APPEND_MARKER) < text.index("intel_private_append")


def test_append_recalibration_note_refuses_invalid_result(tmp_path: Path) -> None:
    log = tmp_path / "INTEL-THRESHOLD-RECALIBRATION-LOG.md"
    log.write_text(f"# Log\n\n{APPEND_MARKER}\n", encoding="utf-8")
    result = build_recalibration_note(
        scorecard=_scorecard(),
        gold_report=_gold_report(),
        evidence_tier="tier2_private_holdout_canary",
        lock_path=INTEL_LOCK_PATH,
        timestamp="2026-05-27T12:00:00Z",
    )

    try:
        append_recalibration_note(log, result)
    except ValueError as exc:
        assert "invalid" in str(exc)
    else:  # pragma: no cover - explicit assertion path for clarity
        raise AssertionError("invalid recalibration note was appended")

    assert "private_recalibration_required" not in log.read_text(encoding="utf-8")


def test_cli_does_not_write_output_or_append_log_for_invalid_note(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    scorecard = tmp_path / "scorecard.json"
    gold = tmp_path / "gold_report.json"
    out = tmp_path / "entry.md"
    log = tmp_path / "INTEL-THRESHOLD-RECALIBRATION-LOG.md"
    scorecard.write_text(json.dumps(_scorecard()), encoding="utf-8")
    gold.write_text(json.dumps(_gold_report()), encoding="utf-8")
    log.write_text(f"# Log\n\n{APPEND_MARKER}\n", encoding="utf-8")

    rc = main(
        [
            "--scorecard",
            str(scorecard),
            "--gold-report",
            str(gold),
            "--evidence-tier",
            "tier2_private_holdout_canary",
            "--timestamp",
            "2026-05-27T12:00:00Z",
            "--output",
            str(out),
            "--append-log",
            str(log),
            "--json",
        ]
    )

    assert rc == 1
    result = json.loads(capsys.readouterr().out)
    assert result["valid"] is False
    assert not out.exists()
    assert log.read_text(encoding="utf-8") == f"# Log\n\n{APPEND_MARKER}\n"
