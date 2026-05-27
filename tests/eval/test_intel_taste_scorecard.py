# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.intel_taste_scorecard import (
    DEFAULT_FIXTURE_DIR,
    main,
    score_fixture_dir,
    score_path,
)


def test_taste_scorecard_scores_fixture_privacy_and_poisoning_gates() -> None:
    result = score_fixture_dir(DEFAULT_FIXTURE_DIR)

    assert result["schema"] == "intel_taste_scorecard_v1"
    assert result["valid"] is True
    assert result["privacy"] == {"local_paths_redacted": True, "profile_ids_redacted": True}
    assert result["metrics"]["accepted_suggestion_lift"] >= 0.10
    assert result["metrics"]["consent_off_long_term_write_rate"] == 0.0
    assert result["metrics"]["single_session_hard_negative_rate"] == 0.0
    assert result["metrics"]["technical_bad_candidate_rescued_by_taste"] == 0.0
    assert result["metrics"]["profile_projection_privacy_leak_count"] == 0.0


def test_taste_scorecard_catches_private_payload(tmp_path: Path) -> None:
    feedback = tmp_path / "taste.jsonl"
    feedback.write_text(
        json.dumps(
            {
                "event_id": "evt_private",
                "session_id": "s1",
                "surface": "prep_chat",
                "action": "transition_labeled",
                "label": "would_play",
                "role_from": "outro",
                "role_to": "intro",
                "local_path": "/Users/ozai/Music/private.wav",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = score_path(feedback)

    assert result["valid"] is False
    assert result["errors"] == ("evt_private:private_payload_present",)


def test_taste_scorecard_catches_invalid_split_and_label(tmp_path: Path) -> None:
    feedback = tmp_path / "taste.jsonl"
    feedback.write_text(
        json.dumps(
            {
                "event_id": "evt_bad",
                "session_id": "s1",
                "surface": "prep_chat",
                "action": "transition_labeled",
                "label": "would_playy",
                "split": "holdot",
                "role_from": "outro",
                "role_to": "intro",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = score_path(feedback)

    assert result["valid"] is False
    assert "evt_bad:invalid_split:holdot" in result["errors"]
    assert "evt_bad:unknown_label:would_playy" in result["errors"]
    assert result["counts"]["calibration_events"] == 0
    assert result["profile_projection"]["transition_style_tags"] == ()


def test_taste_scorecard_cli_json(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["--fixture-dir", str(DEFAULT_FIXTURE_DIR), "--json"]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "intel_taste_scorecard_v1"
    assert out["valid"] is True
    assert out["metrics"]["accepted_suggestion_lift"] >= 0.10


def test_taste_scorecard_cli_returns_nonzero_for_invalid_feedback(
    tmp_path: Path,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    feedback = tmp_path / "taste.jsonl"
    feedback.write_text(
        json.dumps(
            {
                "event_id": "evt_bad",
                "session_id": "s1",
                "surface": "prep_chat",
                "action": "transition_labeled",
                "label": "would_play",
                "split": "holdot",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert main(["--feedback", str(feedback), "--json"]) == 1

    out = json.loads(capsys.readouterr().out)
    assert out["valid"] is False
    assert "evt_bad:invalid_split:holdot" in out["errors"]
