# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

from vibemix.intel.gold_labels import (
    RUBRIC_VERSION,
    load_gold_labels,
    parse_gold_label,
)
from vibemix.intel.gold_validation import (
    GoldKnownIds,
    redacted_gold_report,
    validate_gold_labels,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_legacy_redacted_fixture_normalizes_transition_labels() -> None:
    labels = load_gold_labels(FIXTURES / "gold_labels_redacted.jsonl")

    assert [label.label_id for label in labels] == ["gold_001", "gold_002"]
    assert [label.kind for label in labels] == ["transition", "transition"]
    assert [label.label for label in labels] == ["would_play", "no"]
    assert all(label.split == "calibration" for label in labels)


def test_parse_canonical_transition_label() -> None:
    label = parse_gold_label(
        {
            "label_id": "lbl_010",
            "review_session_id": "rs_20260527_001",
            "review_item_id": "rev_010",
            "split": "holdout",
            "rubric_version": RUBRIC_VERSION,
            "candidate_id": "tr_001",
            "transition_key": "transition_key_001",
            "from_track_id": "t1",
            "to_track_id": "t2",
            "label": "maybe",
        }
    )

    assert label.kind == "transition"
    assert label.split == "holdout"
    assert label.label == "maybe"
    assert label.candidate_id == "tr_001"
    assert label.rubric_version == RUBRIC_VERSION


def test_validate_gold_labels_requires_all_splits_and_known_ids() -> None:
    labels = (
        parse_gold_label(
            {
                "label_id": "lbl_001",
                "split": "calibration",
                "rubric_version": RUBRIC_VERSION,
                "candidate_id": "tr_001",
                "label": "would_play",
            }
        ),
        parse_gold_label(
            {
                "label_id": "lbl_002",
                "split": "holdout",
                "rubric_version": RUBRIC_VERSION,
                "candidate_id": "tr_002",
                "label": "maybe",
            }
        ),
        parse_gold_label(
            {
                "label_id": "lbl_003",
                "split": "canary",
                "rubric_version": RUBRIC_VERSION,
                "candidate_id": "tr_003",
                "label": "no",
            }
        ),
    )

    result = validate_gold_labels(
        labels,
        known_ids=GoldKnownIds(candidate_ids=frozenset({"tr_001", "tr_002", "tr_003"})),
    )

    assert result.valid
    assert result.counts["splits"] == {"calibration": 1, "canary": 1, "holdout": 1}


def test_invalid_split_survives_parse_for_validation() -> None:
    labels = (
        parse_gold_label(
            {
                "label_id": "lbl_bad_split",
                "split": "holdot",
                "rubric_version": RUBRIC_VERSION,
                "candidate_id": "tr_001",
                "label": "would_play",
            }
        ),
    )

    result = validate_gold_labels(labels, require_all_splits=False)

    assert labels[0].split == "holdot"
    assert result.valid is False
    assert "lbl_bad_split:invalid_split:holdot" in result.errors


def test_validate_gold_labels_catches_unknown_candidate_and_action_id_leak() -> None:
    labels = (
        parse_gold_label(
            {
                "label_id": "lbl_001",
                "split": "calibration",
                "rubric_version": RUBRIC_VERSION,
                "candidate_id": "lbl_001",
                "label": "would_play",
            }
        ),
    )

    result = validate_gold_labels(
        labels,
        known_ids=GoldKnownIds(candidate_ids=frozenset({"tr_001"})),
        require_all_splits=False,
    )

    assert not result.valid
    assert "lbl_001:label_id_used_as_action_id" in result.errors
    assert "lbl_001:label_like_action_id:lbl_001" in result.errors
    assert "lbl_001:unknown_candidate_id:lbl_001" in result.errors


def test_holdout_correction_must_use_supersedes_and_stay_holdout() -> None:
    labels = (
        parse_gold_label(
            {
                "label_id": "lbl_001",
                "split": "holdout",
                "rubric_version": RUBRIC_VERSION,
                "candidate_id": "tr_001",
                "label": "maybe",
            }
        ),
        parse_gold_label(
            {
                "label_id": "lbl_002",
                "split": "calibration",
                "rubric_version": RUBRIC_VERSION,
                "candidate_id": "tr_001",
                "label": "would_play",
                "supersedes": "lbl_001",
            }
        ),
    )

    result = validate_gold_labels(labels, require_all_splits=False)

    assert not result.valid
    assert "lbl_002:holdout_correction_must_remain_holdout" in result.errors


def test_redacted_gold_report_hashes_ids_and_omits_notes() -> None:
    labels = (
        parse_gold_label(
            {
                "label_id": "lbl_001",
                "split": "calibration",
                "rubric_version": RUBRIC_VERSION,
                "candidate_id": "tr_001",
                "track_id": "private-track",
                "section_id": "private-section",
                "label": "would_play",
                "note": "private note",
            }
        ),
    )
    validation = validate_gold_labels(labels, require_all_splits=False)

    report = redacted_gold_report(labels, validation, salt="salt")
    report_text = str(report)

    assert report["schema"] == "intel_gold_report_v1"
    assert "private-track" not in report_text
    assert "private-section" not in report_text
    assert "private note" not in report_text
    assert report["examples"][0]["track_hash"]
