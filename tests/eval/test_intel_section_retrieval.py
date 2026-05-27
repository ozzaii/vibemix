# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.intel_section_retrieval import (
    DEFAULT_FIXTURE_DIR,
    main,
    score_fixture_dir,
    score_paths,
)


def test_section_retrieval_compare_scores_fixture_delta() -> None:
    result = score_fixture_dir(DEFAULT_FIXTURE_DIR)

    assert result["schema"] == "intel_section_retrieval_compare_v1"
    assert result["valid"] is True
    assert result["privacy"] == {"local_paths_redacted": True, "raw_vectors_redacted": True}
    assert result["by_mode"]["section"]["totals"]["queries"] == 6
    assert result["metrics"]["section_role_hit_at_5"] == 1.0
    assert result["metrics"]["whole_track_role_hit_at_5"] == 0.5
    assert result["metrics"]["section_minus_whole_track_role_hit_at_5"] >= 0.15
    assert result["metrics"]["section_minus_whole_track_mixable_window_hit_at_5"] >= 0.15
    assert result["metrics"]["section_low_confidence_result_rate"] <= 0.15


def test_section_mode_returns_mixable_sections_without_raw_ids() -> None:
    result = score_fixture_dir(DEFAULT_FIXTURE_DIR, mode="section", k=5)

    assert result["schema"] == "intel_section_retrieval_v1"
    assert result["valid"] is True
    drop_query = next(query for query in result["query_results"] if query["target_role"] == "drop")
    assert [row["role"] for row in drop_query["top_results"][:3]] == ["drop", "drop", "drop"]
    assert all("section_id" not in row for row in drop_query["top_results"])
    assert all(row["result_ref"].startswith("ref:") for row in drop_query["top_results"])


def test_whole_track_mode_is_a_pooled_baseline() -> None:
    result = score_fixture_dir(DEFAULT_FIXTURE_DIR, mode="whole-track", k=5)

    assert result["mode"] == "whole_track"
    assert result["metrics"]["role_hit_at_5"] == 0.5
    intro_query = next(
        query for query in result["query_results"] if query["target_role"] == "intro"
    )
    assert "intro" not in [row["role"] for row in intro_query["top_results"]]


def test_section_retrieval_catches_missing_vectors(tmp_path: Path) -> None:
    sections = tmp_path / "sections.json"
    vectors = tmp_path / "vectors.json"
    queries = tmp_path / "queries.jsonl"
    sections.write_text(
        json.dumps(
            [
                {
                    "section_id": "track-a#s000",
                    "role": "drop",
                    "role_confidence": 0.9,
                    "bar_count": 16,
                    "source_detail": "pssi",
                    "semantic_vector_ref": "vec8:missing",
                }
            ]
        ),
        encoding="utf-8",
    )
    vectors.write_text("{}", encoding="utf-8")
    queries.write_text(
        json.dumps(
            {
                "query_id": "q_drop",
                "target_role": "drop",
                "vector": [1.0, 0.0],
                "mixable_roles": ["drop"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = score_paths(
        sections_path=sections,
        vectors_path=vectors,
        queries_path=queries,
        mode="section",
    )

    assert result["valid"] is False
    assert result["totals"]["missing_section_vectors"] == 1
    assert result["errors"] == ("track-a#s000:missing_vector:vec8:missing",)


def test_section_retrieval_cli_json(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["--fixture-dir", str(DEFAULT_FIXTURE_DIR), "--json"]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "intel_section_retrieval_compare_v1"
    assert out["valid"] is True
    assert out["metrics"]["section_minus_whole_track_role_hit_at_5"] >= 0.15


def test_section_retrieval_cli_requires_paths_together(capsys) -> None:  # type: ignore[no-untyped-def]
    try:
        main(["--sections", str(DEFAULT_FIXTURE_DIR / "sections.json")])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should always exit
        raise AssertionError("expected argparse to reject incomplete retrieval paths")

    assert "must be provided together" in capsys.readouterr().err
