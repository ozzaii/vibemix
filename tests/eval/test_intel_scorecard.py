# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.intel_scorecard import (
    DEFAULT_FIXTURE_DIR,
    DEFAULT_THRESHOLDS,
    build_intel_scorecard,
    load_intel_thresholds_from_lock,
    main,
    score_fixture_dir,
)

INTEL_LOCK_PATH = Path(__file__).resolve().parents[2] / "eval" / "INTEL-THRESHOLD-LOCK.md"


def _write_threshold_lock(path: Path, *, overrides: dict[str, float] | None = None) -> None:
    thresholds = {**DEFAULT_THRESHOLDS, **(overrides or {})}
    body = ["---", "schema: intel_threshold_lock_v1", "intel_thresholds:"]
    body.extend(f"  {key}: {value}" for key, value in thresholds.items())
    body.extend(["---", "", "# Test INTEL lock", ""])
    path.write_text("\n".join(body), encoding="utf-8")


def test_score_fixture_dir_aggregates_intel_artifacts() -> None:
    result = score_fixture_dir(DEFAULT_FIXTURE_DIR)

    assert result["schema"] == "intel_scorecard_v1"
    assert result["valid"] is True
    assert result["privacy"] == {"local_paths_redacted": True}
    assert result["artifact_status"] == {
        "anlz": True,
        "cue_baseline": True,
        "section_retrieval": True,
        "transition_scorecard": True,
        "decision_replay": True,
        "gold_labels": True,
        "taste_scorecard": True,
    }
    assert set(result["metrics"]) == {
        "anlz_complete_rate",
        "anlz_parse_error_rate",
        "cue_exact_or_near_rate",
        "section_role_hit_at_5_delta",
        "section_mixable_window_hit_at_5_delta",
        "section_low_confidence_result_rate",
        "transition_accept_at_3",
        "transition_pairwise_accuracy",
        "transition_unknown_candidate_label_count",
        "decision_validator_fallback_rate",
        "decision_exact_timing_floor_violation_rate",
        "gold_validation_error_count",
        "taste_accepted_suggestion_lift",
        "taste_consent_off_long_term_write_rate",
        "taste_single_session_hard_negative_rate",
        "taste_technical_bad_candidate_rescued_count",
        "taste_profile_projection_privacy_leak_count",
        "taste_unknown_preference_claim_rate",
    }
    assert {gate["status"] for gate in result["gates"]} == {"PASS"}
    assert result["passed"] is True


def test_score_fixture_dir_includes_redacted_replay_provenance() -> None:
    result = score_fixture_dir(
        DEFAULT_FIXTURE_DIR,
        threshold_lock_path=INTEL_LOCK_PATH,
    )

    provenance = result["provenance"]
    assert provenance["eval_run_id"].startswith("eval_intel_scorecard_")
    assert provenance["dataset_card_id"] == "dataset_intel_synthetic_v1"
    assert provenance["fixture_version"] == "intel_fixture_v1"
    assert provenance["fixture_manifest_hash"].startswith("sha256:")
    assert provenance["threshold_lock"] == {
        "source": "threshold_lock",
        "namespace": "intel_thresholds",
        "path": "eval/INTEL-THRESHOLD-LOCK.md",
        "hash": provenance["threshold_lock"]["hash"],
    }
    assert provenance["threshold_lock"]["hash"].startswith("sha256:")
    assert provenance["thresholds_hash"].startswith("sha256:")
    assert "eval/INTEL-THRESHOLD-LOCK.md" in provenance["replay_command"]
    assert "/Users/" not in json.dumps(provenance, sort_keys=True)


def test_locked_intel_thresholds_match_scorecard_defaults() -> None:
    assert load_intel_thresholds_from_lock(INTEL_LOCK_PATH) == DEFAULT_THRESHOLDS


def test_build_intel_scorecard_pass_path() -> None:
    thresholds = dict(DEFAULT_THRESHOLDS)
    result = build_intel_scorecard(
        anlz={
            "valid": True,
            "coverage": {"complete": {"rate": 0.95}, "parse_error_rate": 0.0},
        },
        cue={"valid": True, "distance_bands": {"exact": 9, "near": 1}},
        section_retrieval={
            "valid": True,
            "metrics": {
                "section_minus_whole_track_role_hit_at_5": 0.5,
                "section_minus_whole_track_mixable_window_hit_at_5": 0.5,
                "section_low_confidence_result_rate": 0.01,
            },
        },
        transition={
            "valid": True,
            "metrics": {
                "accepted_transition_rate_at_3": 1.0,
                "pairwise_accuracy": 1.0,
                "unknown_candidate_label_count": 0.0,
            },
        },
        decision={
            "valid": True,
            "metrics": {
                "validator_fallback_rate": 0.0,
                "exact_timing_floor_violation_rate": 0.0,
            },
        },
        gold={"valid": True, "errors": ()},
        taste={
            "valid": True,
            "metrics": {
                "accepted_suggestion_lift": 0.18,
                "consent_off_long_term_write_rate": 0.0,
                "single_session_hard_negative_rate": 0.0,
                "technical_bad_candidate_rescued_by_taste": 0.0,
                "profile_projection_privacy_leak_count": 0.0,
                "unknown_preference_claim_rate": 0.0,
            },
        },
        thresholds=thresholds,
        source="unit",
    )

    assert result["valid"] is True
    assert result["passed"] is True
    assert {gate["status"] for gate in result["gates"]} == {"PASS"}


def test_build_intel_scorecard_tracks_invalid_artifacts_separately_from_gates() -> None:
    result = build_intel_scorecard(
        anlz={"valid": False, "coverage": {"complete": {"rate": 1.0}, "parse_error_rate": 0.0}},
        cue={"valid": True, "distance_bands": {"exact": 10}},
        section_retrieval={
            "valid": True,
            "metrics": {
                "section_minus_whole_track_role_hit_at_5": 0.5,
                "section_minus_whole_track_mixable_window_hit_at_5": 0.5,
                "section_low_confidence_result_rate": 0.01,
            },
        },
        transition={
            "valid": True,
            "metrics": {
                "accepted_transition_rate_at_3": 1.0,
                "pairwise_accuracy": 1.0,
                "unknown_candidate_label_count": 0.0,
            },
        },
        decision={
            "valid": True,
            "metrics": {
                "validator_fallback_rate": 0.0,
                "exact_timing_floor_violation_rate": 0.0,
            },
        },
        gold={"valid": True, "errors": ()},
        taste={
            "valid": True,
            "metrics": {
                "accepted_suggestion_lift": 0.18,
                "consent_off_long_term_write_rate": 0.0,
                "single_session_hard_negative_rate": 0.0,
                "technical_bad_candidate_rescued_by_taste": 0.0,
                "profile_projection_privacy_leak_count": 0.0,
                "unknown_preference_claim_rate": 0.0,
            },
        },
        thresholds=DEFAULT_THRESHOLDS,
        source="unit",
    )

    assert result["valid"] is False
    assert result["artifact_status"]["anlz"] is False
    assert result["passed"] is True


def test_intel_scorecard_cli_json(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "--fixture-dir",
                str(DEFAULT_FIXTURE_DIR),
                "--threshold-lock",
                str(INTEL_LOCK_PATH),
                "--json",
            ]
        )
        == 0
    )

    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "intel_scorecard_v1"
    assert out["valid"] is True
    assert "section_role_hit_at_5_delta" in out["metrics"]
    assert "transition_accept_at_3" in out["metrics"]
    assert "decision_exact_timing_floor_violation_rate" in out["metrics"]
    assert "taste_accepted_suggestion_lift" in out["metrics"]
    assert out["provenance"]["threshold_lock"]["path"] == "eval/INTEL-THRESHOLD-LOCK.md"


def test_intel_scorecard_cli_fails_when_locked_gate_fails(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    lock = tmp_path / "INTEL-THRESHOLD-LOCK.md"
    _write_threshold_lock(lock, overrides={"section_role_hit_at_5_delta_min": 0.99})

    assert (
        main(
            [
                "--fixture-dir",
                str(DEFAULT_FIXTURE_DIR),
                "--threshold-lock",
                str(lock),
                "--json",
            ]
        )
        == 1
    )

    out = json.loads(capsys.readouterr().out)
    assert out["valid"] is True
    assert out["passed"] is False
    assert any(
        gate["metric"] == "section_role_hit_at_5_delta" and gate["status"] == "FAIL"
        for gate in out["gates"]
    )
