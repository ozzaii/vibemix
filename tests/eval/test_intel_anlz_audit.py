# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json

import pytest
from scripts.eval.intel_anlz_audit import (
    DEFAULT_FIXTURE_DIR,
    BundleRecord,
    PhraseRecord,
    audit_fixture_dir,
    main,
    summarize_records,
)


def test_intel_anlz_audit_passes_public_fixture_corpus() -> None:
    result = audit_fixture_dir(DEFAULT_FIXTURE_DIR)

    assert result["schema"] == "intel_anlz_audit_v1"
    assert result["valid"] is True
    assert result["totals"]["bundles"] == 8
    assert result["totals"]["parsed_bundles"] == 6
    assert result["totals"]["skipped_bundles"] == 2
    assert result["coverage"]["pssi"]["rate"] == 1.0
    assert result["coverage"]["pqtz"]["rate"] == 0.75
    assert result["coverage"]["complete"]["rate"] == 0.75
    assert result["phrase_quality"]["roles"]["drop"] >= 1
    assert result["privacy"]["local_paths_redacted"] is True

    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "fixture://tracks/" not in serialized


def test_intel_anlz_audit_summarizes_collisions_and_confidence_buckets() -> None:
    records = [
        BundleRecord(
            source_id="a",
            ppth_path="fixture://tracks/same.wav",
            has_ppth=True,
            has_pssi=True,
            has_pqtz=True,
            parsed=True,
            phrases=(
                PhraseRecord(role="drop", confidence=0.91, mood="high"),
                PhraseRecord(role="build", confidence=0.62, mood="high"),
            ),
        ),
        BundleRecord(
            source_id="b",
            ppth_path="fixture://other/same.wav",
            has_ppth=True,
            has_pssi=True,
            has_pqtz=True,
            parsed=True,
            phrases=(
                PhraseRecord(role="breakdown", confidence=0.50, mood="mid"),
                PhraseRecord(role="build", confidence=0.40, mood="mid"),
            ),
        ),
        BundleRecord(
            source_id="c",
            ppth_path=None,
            has_ppth=False,
            has_pssi=False,
            has_pqtz=False,
            parsed=False,
            phrases=(),
            parse_error="ParseError",
        ),
    ]

    result = summarize_records(records, source="unit")

    assert result["valid"] is False
    assert result["totals"]["bundles"] == 3
    assert result["totals"]["parsed_bundles"] == 2
    assert result["totals"]["parse_errors"] == 1
    assert result["coverage"]["ppth"]["count"] == 2
    assert result["coverage"]["parse_error_rate"] == pytest.approx(1 / 3)
    assert result["path_collisions"]["collision_count"] == 1
    assert len(result["path_collisions"]["collision_key_hashes"][0]) == 12
    assert result["phrase_quality"]["roles"]["build"] == 2
    assert result["phrase_quality"]["confidence_buckets"] == {
        "high": 1,
        "medium": 1,
        "low": 1,
        "below_anchor_floor": 1,
        "unknown": 0,
    }


def test_intel_anlz_audit_cli_json(capsys) -> None:
    code = main(["--fixture-dir", str(DEFAULT_FIXTURE_DIR), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    result = json.loads(captured.out)
    assert result["schema"] == "intel_anlz_audit_v1"
    assert result["valid"] is True
