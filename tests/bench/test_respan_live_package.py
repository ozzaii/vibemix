# SPDX-License-Identifier: Apache-2.0
"""Live Sven Respan package metadata tests."""

from __future__ import annotations

import json
from pathlib import Path

from vibemix.bench.respan import (
    build_live_respan_package,
    local_actionability_audit,
    write_live_respan_package,
)


def _live_span(response_id: str, output: str) -> dict:
    return {
        "schema": "vibemix_live_sven_respan_span_v1",
        "custom_identifier": response_id,
        "model": "gemini-3.5-flash",
        "log_type": "chat",
        "input": [{"role": "user", "content": "event=TRACK_CHANGE evidence=single_deck_A"}],
        "output": {"role": "assistant", "content": output},
        "status": "success",
        "metadata": {
            "session_id": "20260606-180051",
            "event": "TRACK_CHANGE",
            "live_decision": "spoke",
            "should_evaluate_five_dim": True,
            "privacy": {
                "contains_audio_bytes": False,
                "contains_screen_frames": False,
                "contains_full_prompt": False,
            },
        },
    }


def test_live_next_nudge_scores_as_move_named_metadata() -> None:
    audit = local_actionability_audit("Heavy sub-weight on this one, slide a girl like u next.")

    assert audit["status"] == "metadata_only_not_a_respan_verdict"
    assert audit["move_named"] is True
    assert audit["move_specific_score_0_to_3"] == 2
    assert audit["should_not_have_spoken_hint"] is False
    assert "slide" in audit["move_terms"]


def test_live_grounded_narration_without_move_is_should_not_hint() -> None:
    audit = local_actionability_audit("This new track brought a much heavier, driving low end.")

    assert audit["status"] == "metadata_only_not_a_respan_verdict"
    assert audit["move_named"] is False
    assert audit["move_specific_score_0_to_3"] == 1
    assert audit["should_not_have_spoken_hint"] is True
    assert audit["flags"] == ["no_move_named"]


def test_live_package_summary_surfaces_local_actionability() -> None:
    package = build_live_respan_package(
        [
            _live_span(
                "0001_180155",
                "Heavy sub-weight on this one, slide a girl like u next.",
            ),
            _live_span("0002_empty", ""),
        ],
        [{"response_id": "0001_180155", "label": "good", "score": 1}],
        session_dir=Path("/tmp/20260606-180051"),
    )

    summary = package["summary"]
    actionability = summary["local_actionability"]
    assert summary["dataset_rows"] == 1
    assert summary["labeled_responses"] == 1
    assert actionability["status"] == "metadata_only_not_a_respan_verdict"
    assert actionability["audited_rows"] == 2
    assert actionability["move_named_rows"] == 1
    assert actionability["should_not_have_spoken_hints"] == 1
    assert actionability["mean_move_specific_score_0_to_3"] == 1.0
    assert actionability["flag_counts"] == {"empty_output": 1}


def test_write_live_package_readme_includes_actionability_summary(tmp_path: Path) -> None:
    session_dir = tmp_path / "20260606-180051"
    session_dir.mkdir()
    span = _live_span(
        "0001_180155",
        "Heavy sub-weight on this one, slide a girl like u next.",
    )
    (session_dir / "respan_spans.jsonl").write_text(
        json.dumps(span, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "pkg"
    manifest = write_live_respan_package(session_dir, out_dir)

    assert manifest["summary"]["local_actionability"]["move_named_rows"] == 1
    readme = (out_dir / "README.md").read_text(encoding="utf-8")
    assert "local_actionability_move_named_rows: 1" in readme
    assert "local_actionability_should_not_have_spoken_hints: 0" in readme
    assert "local_actionability_mean_move_specific_score_0_to_3: 2.0" in readme
