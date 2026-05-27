# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.intel_transition_scorecard import (
    DEFAULT_FIXTURE_DIR,
    main,
    score_fixture_dir,
    score_paths,
    score_transition_labels,
)

from vibemix.intel.gold_labels import parse_gold_label


def test_transition_scorecard_scores_fixture_labels() -> None:
    result = score_fixture_dir(DEFAULT_FIXTURE_DIR)

    assert result["schema"] == "intel_transition_scorecard_v1"
    assert result["valid"] is True
    assert result["privacy"] == {"local_paths_redacted": True}
    assert result["totals"]["candidates"] == 5
    assert result["totals"]["transition_labels"] == 2
    assert result["metrics"]["accepted_transition_rate_at_3"] == 1.0
    assert result["metrics"]["pairwise_accuracy"] == 1.0
    assert result["metrics"]["ndcg_at_5"] == 1.0
    assert result["metrics"]["risk_flag_precision"] == 1.0
    assert result["metrics"]["leakage_rate"] == 0.2
    assert [row["candidate_id"] for row in result["ranked_labeled"]] == ["tr_001", "tr_004"]


def test_transition_scorecard_catches_unknown_label_candidate() -> None:
    candidates = ({"candidate_id": "tr_001", "score": 0.9, "risk_flags": []},)
    labels = (
        parse_gold_label(
            {
                "label_id": "lbl_001",
                "candidate_id": "tr_999",
                "label": "would_play",
            }
        ),
    )

    result = score_transition_labels(candidates=candidates, labels=labels, source="unit")

    assert result["valid"] is False
    assert "lbl_001:unknown_candidate_id:tr_999" in result["errors"]
    assert result["metrics"]["unknown_candidate_label_count"] == 1.0


def test_transition_scorecard_catches_nan_scores() -> None:
    candidates = ({"candidate_id": "tr_001", "score": "nan", "risk_flags": []},)
    labels = (
        parse_gold_label(
            {
                "label_id": "lbl_001",
                "candidate_id": "tr_001",
                "label": "would_play",
            }
        ),
    )

    result = score_transition_labels(candidates=candidates, labels=labels, source="unit")

    assert result["valid"] is False
    assert "tr_001:nan_score" in result["errors"]
    assert result["metrics"]["nan_score_count"] == 1.0


def test_transition_scorecard_private_paths() -> None:
    result = score_paths(
        candidates_path=DEFAULT_FIXTURE_DIR / "transition_pairs.json",
        labels_path=DEFAULT_FIXTURE_DIR / "gold_labels_redacted.jsonl",
    )

    assert result["source"] == "private:redacted"
    assert result["valid"] is True


def test_transition_scorecard_cli_json(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["--fixture-dir", str(DEFAULT_FIXTURE_DIR), "--json"]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "intel_transition_scorecard_v1"
    assert out["metrics"]["accepted_transition_rate_at_3"] == 1.0


def test_transition_scorecard_cli_requires_paths_together(capsys) -> None:  # type: ignore[no-untyped-def]
    try:
        main(["--candidates", str(DEFAULT_FIXTURE_DIR / "transition_pairs.json")])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should always exit
        raise AssertionError("expected argparse to reject incomplete scorecard paths")

    assert "must be provided together" in capsys.readouterr().err


def test_transition_scorecard_json_inputs_roundtrip(tmp_path: Path) -> None:
    candidates = tmp_path / "pairs.json"
    labels = tmp_path / "labels.jsonl"
    candidates.write_text(
        json.dumps(
            [
                {"candidate_id": "tr_a", "score": 0.2, "risk_flags": ["bad"]},
                {"candidate_id": "tr_b", "score": 0.9, "risk_flags": []},
            ]
        ),
        encoding="utf-8",
    )
    labels.write_text(
        "\n".join(
            [
                json.dumps({"label_id": "lbl_a", "candidate_id": "tr_a", "label": "no"}),
                json.dumps({"label_id": "lbl_b", "candidate_id": "tr_b", "label": "would_play"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = score_paths(candidates_path=candidates, labels_path=labels)

    assert result["metrics"]["pairwise_accuracy"] == 1.0
    assert result["metrics"]["accepted_transition_rate_at_3"] == 1.0
