# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.intel_gold import (
    DEFAULT_FIXTURE_DIR,
    main,
    report_gold_file,
    sample_gold_items,
    validate_gold_file,
)


def test_validate_fixture_gold_labels_accepts_legacy_redacted_rows() -> None:
    result = validate_gold_file(DEFAULT_FIXTURE_DIR / "gold_labels_redacted.jsonl")

    assert result["schema"] == "intel_gold_validation_v1"
    assert result["valid"] is True
    assert result["counts"]["total"] == 2
    assert result["counts"]["labels"] == {"no": 1, "would_play": 1}
    assert result["warnings"]


def test_validate_fixture_gold_labels_can_require_all_splits() -> None:
    result = validate_gold_file(
        DEFAULT_FIXTURE_DIR / "gold_labels_redacted.jsonl",
        require_all_splits=True,
    )

    assert result["valid"] is False
    assert "missing_split:holdout" in result["errors"]
    assert "missing_split:canary" in result["errors"]


def test_validate_gold_file_rejects_invalid_split_name(tmp_path: Path) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        json.dumps(
            {
                "label_id": "lbl_bad_split",
                "split": "holdot",
                "rubric_version": "kaan_gold_v1",
                "candidate_id": "tr_001",
                "label": "would_play",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = validate_gold_file(labels)

    assert result["valid"] is False
    assert "lbl_bad_split:invalid_split:holdot" in result["errors"]


def test_report_gold_file_redacts_ids() -> None:
    report = report_gold_file(DEFAULT_FIXTURE_DIR / "gold_labels_redacted.jsonl", salt="test")
    text = json.dumps(report, sort_keys=True)

    assert report["schema"] == "intel_gold_report_v1"
    assert report["privacy"] == {"ids_hashed": True, "local_paths_redacted": True}
    assert "tr_001" not in text
    assert "ctx_001" not in text


def test_sample_gold_items_uses_transition_pairs_fixture() -> None:
    result = sample_gold_items(DEFAULT_FIXTURE_DIR / "transition_pairs.json", n=3)

    assert result["schema"] == "intel_gold_sample_v1"
    assert result["kind"] == "transition"
    assert result["n"] == 3
    assert {item["sample_reason"] for item in result["items"]} >= {
        "top_scorer",
        "near_threshold",
    }


def test_gold_cli_validate_json(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "validate",
                str(DEFAULT_FIXTURE_DIR / "gold_labels_redacted.jsonl"),
                "--json",
            ]
        )
        == 0
    )

    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "intel_gold_validation_v1"
    assert out["valid"] is True


def test_gold_cli_validate_returns_nonzero_for_invalid_labels(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        json.dumps(
            {
                "label_id": "lbl_bad_split",
                "split": "holdot",
                "rubric_version": "kaan_gold_v1",
                "candidate_id": "tr_001",
                "label": "would_play",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert main(["validate", str(labels), "--json"]) == 1

    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "intel_gold_validation_v1"
    assert out["valid"] is False
    assert "lbl_bad_split:invalid_split:holdot" in out["errors"]


def test_gold_cli_report_returns_nonzero_for_invalid_labels(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        json.dumps(
            {
                "label_id": "lbl_bad_split",
                "split": "holdot",
                "rubric_version": "kaan_gold_v1",
                "candidate_id": "tr_001",
                "label": "would_play",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert main(["report", str(labels), "--json"]) == 1

    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "intel_gold_report_v1"
    assert out["valid"] is False
    assert out["error_count"] > 0


def test_gold_cli_sample_json(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "sample",
                str(DEFAULT_FIXTURE_DIR / "transition_pairs.json"),
                "--n",
                "2",
                "--json",
            ]
        )
        == 0
    )

    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "intel_gold_sample_v1"
    assert out["n"] == 2


def test_gold_cli_report_json(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        json.dumps(
            {
                "label_id": "lbl_001",
                "split": "calibration",
                "rubric_version": "kaan_gold_v1",
                "candidate_id": "tr_001",
                "label": "would_play",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert main(["report", str(labels), "--json"]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "intel_gold_report_v1"
    assert out["privacy"]["ids_hashed"] is True
