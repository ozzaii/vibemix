# SPDX-License-Identifier: Apache-2.0
"""Aggregate INTEL eval artifacts into one thresholded scorecard."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_FIXTURE_DIR = ROOT / "tests" / "intel" / "fixtures"

DEFAULT_THRESHOLDS: dict[str, float] = {
    "anlz_complete_rate_min": 0.70,
    "anlz_parse_error_rate_max": 0.00,
    "cue_exact_or_near_rate_min": 0.40,
    "section_role_hit_at_5_delta_min": 0.15,
    "section_mixable_window_hit_at_5_delta_min": 0.10,
    "section_low_confidence_result_rate_max": 0.15,
    "transition_accept_at_3_min": 0.80,
    "transition_pairwise_accuracy_min": 0.80,
    "transition_unknown_candidate_label_count_max": 0.00,
    "decision_validator_fallback_rate_max": 0.20,
    "decision_exact_timing_floor_violation_rate_max": 0.00,
    "gold_validation_error_count_max": 0.00,
    "taste_accepted_suggestion_lift_min": 0.10,
    "taste_consent_off_long_term_write_rate_max": 0.00,
    "taste_single_session_hard_negative_rate_max": 0.00,
    "taste_technical_bad_candidate_rescued_count_max": 0.00,
    "taste_profile_projection_privacy_leak_count_max": 0.00,
    "taste_unknown_preference_claim_rate_max": 0.00,
}

INTEL_THRESHOLD_LOCK_KEY = "intel_thresholds"


def score_fixture_dir(
    fixture_dir: Path | str = DEFAULT_FIXTURE_DIR,
    *,
    thresholds: dict[str, float] | None = None,
    threshold_lock_path: Path | str | None = None,
) -> dict[str, Any]:
    from scripts.eval.intel_anlz_audit import audit_fixture_dir
    from scripts.eval.intel_cue_baseline_compare import compare_fixture_dir
    from scripts.eval.intel_decision_runtime_replay import replay_fixture_dir
    from scripts.eval.intel_gold import validate_gold_file
    from scripts.eval.intel_section_retrieval import score_fixture_dir as score_sections
    from scripts.eval.intel_taste_scorecard import score_fixture_dir as score_taste
    from scripts.eval.intel_transition_scorecard import score_fixture_dir as score_transitions

    base = Path(fixture_dir)
    active_thresholds = dict(thresholds or DEFAULT_THRESHOLDS)
    anlz = audit_fixture_dir(base)
    cue = compare_fixture_dir(base)
    section_retrieval = score_sections(base)
    transition = score_transitions(base)
    decision = replay_fixture_dir(base)
    gold = validate_gold_file(base / "gold_labels_redacted.jsonl", fixture_dir=base)
    taste = score_taste(base)
    return build_intel_scorecard(
        anlz=anlz,
        cue=cue,
        section_retrieval=section_retrieval,
        transition=transition,
        decision=decision,
        gold=gold,
        taste=taste,
        thresholds=active_thresholds,
        source=f"fixture:{base.name}",
        provenance=build_scorecard_provenance(
            fixture_dir=base,
            thresholds=active_thresholds,
            threshold_lock_path=threshold_lock_path,
        ),
    )


def load_intel_thresholds_from_lock(path: Path | str) -> dict[str, float]:
    """Load the INTEL threshold namespace from eval/INTEL-THRESHOLD-LOCK.md."""
    from scripts.eval.threshold_lock import parse_threshold_lock_frontmatter

    parsed = parse_threshold_lock_frontmatter(path)
    raw = parsed.get(INTEL_THRESHOLD_LOCK_KEY)
    if not isinstance(raw, dict):
        raise ValueError(f"threshold lock missing `{INTEL_THRESHOLD_LOCK_KEY}` mapping: {path}")

    expected = set(DEFAULT_THRESHOLDS)
    actual = set(raw)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise ValueError(
            f"`{INTEL_THRESHOLD_LOCK_KEY}` key mismatch in {path}: missing={missing} extra={extra}"
        )

    try:
        return {key: float(raw[key]) for key in DEFAULT_THRESHOLDS}
    except (TypeError, ValueError) as exc:
        raise ValueError(f"`{INTEL_THRESHOLD_LOCK_KEY}` contains a non-numeric value") from exc


def build_intel_scorecard(
    *,
    anlz: dict[str, Any],
    cue: dict[str, Any],
    section_retrieval: dict[str, Any],
    transition: dict[str, Any],
    decision: dict[str, Any],
    gold: dict[str, Any],
    taste: dict[str, Any],
    thresholds: dict[str, float],
    source: str,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_thresholds = dict(thresholds)
    metrics = {
        "anlz_complete_rate": _float(anlz, ("coverage", "complete", "rate")),
        "anlz_parse_error_rate": _float(anlz, ("coverage", "parse_error_rate")),
        "cue_exact_or_near_rate": _cue_exact_or_near_rate(cue),
        "section_role_hit_at_5_delta": _float(
            section_retrieval, ("metrics", "section_minus_whole_track_role_hit_at_5")
        ),
        "section_mixable_window_hit_at_5_delta": _float(
            section_retrieval,
            ("metrics", "section_minus_whole_track_mixable_window_hit_at_5"),
        ),
        "section_low_confidence_result_rate": _float(
            section_retrieval, ("metrics", "section_low_confidence_result_rate")
        ),
        "transition_accept_at_3": _float(transition, ("metrics", "accepted_transition_rate_at_3")),
        "transition_pairwise_accuracy": _float(transition, ("metrics", "pairwise_accuracy")),
        "transition_unknown_candidate_label_count": _float(
            transition, ("metrics", "unknown_candidate_label_count")
        ),
        "decision_validator_fallback_rate": _float(
            decision, ("metrics", "validator_fallback_rate")
        ),
        "decision_exact_timing_floor_violation_rate": _float(
            decision, ("metrics", "exact_timing_floor_violation_rate")
        ),
        "gold_validation_error_count": float(len(gold.get("errors", ()))),
        "taste_accepted_suggestion_lift": _float(taste, ("metrics", "accepted_suggestion_lift")),
        "taste_consent_off_long_term_write_rate": _float(
            taste, ("metrics", "consent_off_long_term_write_rate")
        ),
        "taste_single_session_hard_negative_rate": _float(
            taste, ("metrics", "single_session_hard_negative_rate")
        ),
        "taste_technical_bad_candidate_rescued_count": _float(
            taste, ("metrics", "technical_bad_candidate_rescued_by_taste")
        ),
        "taste_profile_projection_privacy_leak_count": _float(
            taste, ("metrics", "profile_projection_privacy_leak_count")
        ),
        "taste_unknown_preference_claim_rate": _float(
            taste, ("metrics", "unknown_preference_claim_rate")
        ),
    }
    gates = (
        _min_gate("anlz_complete_rate", metrics, active_thresholds, "anlz_complete_rate_min"),
        _max_gate("anlz_parse_error_rate", metrics, active_thresholds, "anlz_parse_error_rate_max"),
        _min_gate(
            "cue_exact_or_near_rate", metrics, active_thresholds, "cue_exact_or_near_rate_min"
        ),
        _min_gate(
            "section_role_hit_at_5_delta",
            metrics,
            active_thresholds,
            "section_role_hit_at_5_delta_min",
        ),
        _min_gate(
            "section_mixable_window_hit_at_5_delta",
            metrics,
            active_thresholds,
            "section_mixable_window_hit_at_5_delta_min",
        ),
        _max_gate(
            "section_low_confidence_result_rate",
            metrics,
            active_thresholds,
            "section_low_confidence_result_rate_max",
        ),
        _min_gate(
            "transition_accept_at_3", metrics, active_thresholds, "transition_accept_at_3_min"
        ),
        _min_gate(
            "transition_pairwise_accuracy",
            metrics,
            active_thresholds,
            "transition_pairwise_accuracy_min",
        ),
        _max_gate(
            "transition_unknown_candidate_label_count",
            metrics,
            active_thresholds,
            "transition_unknown_candidate_label_count_max",
        ),
        _max_gate(
            "decision_validator_fallback_rate",
            metrics,
            active_thresholds,
            "decision_validator_fallback_rate_max",
        ),
        _max_gate(
            "decision_exact_timing_floor_violation_rate",
            metrics,
            active_thresholds,
            "decision_exact_timing_floor_violation_rate_max",
        ),
        _max_gate(
            "gold_validation_error_count",
            metrics,
            active_thresholds,
            "gold_validation_error_count_max",
        ),
        _min_gate(
            "taste_accepted_suggestion_lift",
            metrics,
            active_thresholds,
            "taste_accepted_suggestion_lift_min",
        ),
        _max_gate(
            "taste_consent_off_long_term_write_rate",
            metrics,
            active_thresholds,
            "taste_consent_off_long_term_write_rate_max",
        ),
        _max_gate(
            "taste_single_session_hard_negative_rate",
            metrics,
            active_thresholds,
            "taste_single_session_hard_negative_rate_max",
        ),
        _max_gate(
            "taste_technical_bad_candidate_rescued_count",
            metrics,
            active_thresholds,
            "taste_technical_bad_candidate_rescued_count_max",
        ),
        _max_gate(
            "taste_profile_projection_privacy_leak_count",
            metrics,
            active_thresholds,
            "taste_profile_projection_privacy_leak_count_max",
        ),
        _max_gate(
            "taste_unknown_preference_claim_rate",
            metrics,
            active_thresholds,
            "taste_unknown_preference_claim_rate_max",
        ),
    )
    return {
        "schema": "intel_scorecard_v1",
        "source": source,
        "valid": all(
            artifact.get("valid", False)
            for artifact in (anlz, cue, section_retrieval, transition, decision, gold, taste)
        ),
        "passed": all(gate["status"] == "PASS" for gate in gates),
        "privacy": {"local_paths_redacted": True},
        "metrics": metrics,
        "thresholds": active_thresholds,
        "provenance": provenance
        or {
            "suite": "intel_scorecard",
            "source": source,
            "replay_tier": "untracked_unit_eval",
        },
        "gates": gates,
        "artifact_status": {
            "anlz": bool(anlz.get("valid")),
            "cue_baseline": bool(cue.get("valid")),
            "section_retrieval": bool(section_retrieval.get("valid")),
            "transition_scorecard": bool(transition.get("valid")),
            "decision_replay": bool(decision.get("valid")),
            "gold_labels": bool(gold.get("valid")),
            "taste_scorecard": bool(taste.get("valid")),
        },
    }


def build_scorecard_provenance(
    *,
    fixture_dir: Path | str,
    thresholds: dict[str, float],
    threshold_lock_path: Path | str | None,
) -> dict[str, Any]:
    base = Path(fixture_dir)
    manifest_path = base / "MANIFEST.json"
    manifest = _load_json_file(manifest_path) if manifest_path.exists() else {}
    threshold_lock = _threshold_lock_provenance(threshold_lock_path)
    thresholds_hash = _mapping_hash(thresholds)
    manifest_hash = _file_sha256(manifest_path) if manifest_path.exists() else None
    eval_hash = _mapping_hash(
        {
            "suite": "intel_scorecard",
            "dataset_card_id": manifest.get("dataset_card_id"),
            "fixture_version": manifest.get("fixture_version"),
            "manifest_hash": manifest_hash,
            "threshold_lock_hash": threshold_lock.get("hash"),
            "thresholds_hash": thresholds_hash,
        }
    )[7:19]
    replay_command = [
        "uv",
        "run",
        "python",
        "scripts/eval/intel_scorecard.py",
        "--fixture-dir",
        _safe_path_label(base),
    ]
    if threshold_lock_path is not None:
        replay_command.extend(["--threshold-lock", _safe_path_label(Path(threshold_lock_path))])
    replay_command.append("--json")
    return {
        "eval_run_id": f"eval_intel_scorecard_{eval_hash}",
        "suite": "intel_scorecard",
        "scorecard_schema": "intel_scorecard_v1",
        "dataset_card_id": manifest.get("dataset_card_id"),
        "fixture_version": manifest.get("fixture_version"),
        "fixture_manifest_hash": manifest_hash,
        "thresholds_hash": thresholds_hash,
        "threshold_lock": threshold_lock,
        "replay_tier": "tier0_fixture_replay",
        "replay_command": " ".join(replay_command),
        "privacy": {
            "local_paths_redacted": True,
            "contains_raw_audio": False,
            "contains_raw_vectors": False,
        },
    }


def _threshold_lock_provenance(path: Path | str | None) -> dict[str, Any]:
    if path is None:
        return {
            "source": "default_thresholds",
            "namespace": INTEL_THRESHOLD_LOCK_KEY,
            "path": None,
            "hash": None,
        }
    target = Path(path)
    return {
        "source": "threshold_lock",
        "namespace": INTEL_THRESHOLD_LOCK_KEY,
        "path": _safe_path_label(target),
        "hash": _file_sha256(target) if target.exists() else None,
    }


def _safe_path_label(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def _load_json_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _min_gate(
    metric: str,
    metrics: dict[str, float],
    thresholds: dict[str, float],
    threshold_key: str,
) -> dict[str, Any]:
    actual = metrics[metric]
    threshold = thresholds[threshold_key]
    return {
        "metric": metric,
        "threshold": f">= {threshold}",
        "actual": actual,
        "status": "PASS" if actual >= threshold else "FAIL",
    }


def _max_gate(
    metric: str,
    metrics: dict[str, float],
    thresholds: dict[str, float],
    threshold_key: str,
) -> dict[str, Any]:
    actual = metrics[metric]
    threshold = thresholds[threshold_key]
    return {
        "metric": metric,
        "threshold": f"<= {threshold}",
        "actual": actual,
        "status": "PASS" if actual <= threshold else "FAIL",
    }


def _cue_exact_or_near_rate(cue: dict[str, Any]) -> float:
    bands = dict(cue.get("distance_bands") or {})
    total = sum(int(value) for value in bands.values())
    if total <= 0:
        return 0.0
    exact_or_near = int(bands.get("exact", 0)) + int(bands.get("near", 0))
    return round(exact_or_near / total, 6)


def _float(data: dict[str, Any], path: tuple[str, ...], default: float = 0.0) -> float:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    try:
        return float(cur)
    except (TypeError, ValueError):
        return default


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument(
        "--threshold-lock",
        type=Path,
        help="Read INTEL thresholds from a markdown frontmatter `intel_thresholds` mapping.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)

    thresholds = (
        load_intel_thresholds_from_lock(args.threshold_lock)
        if args.threshold_lock
        else DEFAULT_THRESHOLDS
    )
    result = score_fixture_dir(
        args.fixture_dir,
        thresholds=thresholds,
        threshold_lock_path=args.threshold_lock,
    )
    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print(
            "INTEL scorecard: "
            f"valid={result['valid']} passed={result['passed']} "
            f"failed={[gate['metric'] for gate in result['gates'] if gate['status'] == 'FAIL']}"
        )
    return 0 if result["valid"] and result["passed"] else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
