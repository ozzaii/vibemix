# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.intel_decision_runtime_replay import (
    DEFAULT_FIXTURE_DIR,
    main,
    replay_fixture_dir,
    replay_paths,
)


def _write_replay_fixture(tmp_path: Path) -> tuple[Path, Path]:
    contexts = tmp_path / "contexts.json"
    decisions = tmp_path / "decisions.jsonl"
    contexts.write_text(
        json.dumps(
            [
                {
                    "schema_version": "intel_context_v1",
                    "packet_id": "ctx_001",
                    "mode": "live",
                    "intent": "live_next_pill",
                    "current": {"track_id": "t1"},
                    "candidates": [
                        {
                            "candidate_id": "tr_001",
                            "recommended_cue_slot": "A",
                            "start_in_bars": 16,
                        }
                    ],
                    "constraints": {
                        "exact_timing_allowed": True,
                        "strict_claim_validation": True,
                    },
                    "allowed_actions": ["select", "hold", "suppress"],
                    "allowed_claims": ["cue_operability"],
                    "forbidden_claims": [],
                    "citation_scope": {"candidate": ["tr_001"], "claim": ["clm_ctx_001_000"]},
                    "confidence_policy": {"exact_timing_allowed": True},
                    "claim_ids": ["clm_ctx_001_000", "clm_ctx_001_001"],
                    "claim_summary": [
                        {
                            "claim_id": "clm_ctx_001_000",
                            "type": "cue_slot",
                            "subject_id": "tr_001",
                            "value": "A",
                            "status": "allowed",
                            "forbidden_phrases": [],
                        },
                        {
                            "claim_id": "clm_ctx_001_001",
                            "type": "bars_until_event",
                            "subject_id": "tr_001",
                            "value": 16,
                            "unit": "bars",
                            "status": "allowed",
                            "forbidden_phrases": [],
                        },
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    decisions.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "decision_id": "dec_001",
                        "packet_id": "ctx_001",
                        "schema_version": "intel_context_v1",
                        "action": "select",
                        "candidate_id": "tr_001",
                        "cue_slot": "A",
                        "timing_text": "in 16 bars",
                        "spoken_text": "Use cue A in 16 bars.",
                        "cited_claim_ids": ["clm_ctx_001_000", "clm_ctx_001_001"],
                        "cited_claims": ["cue_operability"],
                        "confidence": 0.9,
                    }
                ),
                json.dumps(
                    {
                        "decision_id": "dec_002",
                        "packet_id": "ctx_001",
                        "schema_version": "intel_context_v1",
                        "action": "select",
                        "candidate_id": "tr_999",
                        "cue_slot": "A",
                        "spoken_text": "Take this one.",
                        "confidence": 0.8,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return contexts, decisions


def test_replay_reports_validator_metrics(tmp_path: Path) -> None:
    contexts, decisions = _write_replay_fixture(tmp_path)

    result = replay_paths(contexts_path=contexts, decisions_path=decisions)

    assert result["schema"] == "intel_decision_runtime_replay_v1"
    assert result["valid"] is True
    assert result["totals"] == {
        "contexts": 1,
        "decisions": 2,
        "accepted": 1,
        "rejected": 1,
    }
    assert result["metrics"]["unknown_id_rejection_rate"] == 0.5
    assert result["metrics"]["validator_fallback_rate"] == 0.5
    assert result["error_counts"] == {
        "cue_slot_requires_selected_candidate": 1,
        "unknown_candidate_id": 1,
    }


def test_fixture_replay_hydrates_candidate_and_claim_ledgers() -> None:
    result = replay_fixture_dir(DEFAULT_FIXTURE_DIR)

    assert result["valid"] is True
    assert result["totals"]["accepted"] == 2
    assert result["metrics"]["validator_fallback_rate"] == 0.0
    assert result["metrics"]["exact_timing_floor_violation_rate"] == 0.0
    assert result["error_counts"] == {}


def test_replay_counts_timing_floor_violation(tmp_path: Path) -> None:
    contexts, decisions = _write_replay_fixture(tmp_path)
    raw = json.loads(contexts.read_text(encoding="utf-8"))
    raw[0]["constraints"]["exact_timing_allowed"] = False
    contexts.write_text(json.dumps(raw), encoding="utf-8")

    result = replay_paths(contexts_path=contexts, decisions_path=decisions)

    assert result["metrics"]["exact_timing_floor_violation_rate"] == 0.5
    assert result["error_counts"]["timing_not_allowed"] == 1


def test_replay_cli_json(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    contexts, decisions = _write_replay_fixture(tmp_path)

    assert main(["--contexts", str(contexts), "--decisions", str(decisions), "--json"]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["schema"] == "intel_decision_runtime_replay_v1"
    assert out["totals"]["decisions"] == 2


def test_replay_cli_requires_contexts_and_decisions_together(capsys) -> None:  # type: ignore[no-untyped-def]
    try:
        main(["--contexts", "only-contexts.json"])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should always exit
        raise AssertionError("expected argparse to reject incomplete replay paths")

    assert "must be provided together" in capsys.readouterr().err
