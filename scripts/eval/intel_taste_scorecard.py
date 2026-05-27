# SPDX-License-Identifier: Apache-2.0
"""Score deterministic taste learning privacy and poisoning gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vibemix.intel.feedback import (  # noqa: E402
    FeedbackEvent,
    feedback_validation_errors,
    load_feedback_events,
    persistable_events,
)
from vibemix.intel.profile_projection import (  # noqa: E402
    ALLOWED_TRANSITION_STYLE_TAGS,
    profile_projection_privacy_errors,
    project_profile,
)
from vibemix.intel.taste_model import TECHNICAL_LABELS, build_taste_model  # noqa: E402

DEFAULT_FIXTURE_DIR = ROOT / "tests" / "intel" / "fixtures"
LIVE_SELECT_FLOOR = 0.62


def score_fixture_dir(fixture_dir: Path | str = DEFAULT_FIXTURE_DIR) -> dict[str, Any]:
    base = Path(fixture_dir)
    return score_path(base / "taste_feedback.jsonl", source=f"fixture:{base.name}")


def score_path(path: Path | str, *, source: str = "private:redacted") -> dict[str, Any]:
    events = load_feedback_events(path)
    return score_taste_feedback(events, source=source)


def score_taste_feedback(events: tuple[FeedbackEvent, ...], *, source: str) -> dict[str, Any]:
    event_errors = feedback_validation_errors(events)
    scored_events = () if event_errors else events
    calibration = tuple(event for event in scored_events if event.split == "calibration")
    holdout = tuple(event for event in scored_events if event.split == "holdout")
    poison = tuple(event for event in scored_events if event.split == "poison")
    model = build_taste_model(calibration)
    poison_model = build_taste_model(poison)
    profile = project_profile(model, consent=True)
    validation_errors = (
        *event_errors,
        *profile_projection_privacy_errors(profile),
    )
    metrics = {
        "accepted_suggestion_lift": _accepted_suggestion_lift(model, holdout),
        "false_negative_rate_after_taste": _false_negative_rate(model, holdout),
        "single_session_hard_negative_rate": _single_session_hard_negative_rate(poison_model),
        "consent_off_long_term_write_rate": _rate(
            len(persistable_events(events, profile_consent=False)), len(events)
        ),
        "profile_projection_privacy_leak_count": float(
            len(profile_projection_privacy_errors(profile))
        ),
        "unknown_preference_claim_rate": _unknown_preference_claim_rate(profile),
        "technical_bad_candidate_rescued_by_taste": float(
            _technical_bad_candidate_rescued_by_taste(model, holdout)
        ),
    }
    return {
        "schema": "intel_taste_scorecard_v1",
        "source": source,
        "valid": bool(events) and not validation_errors,
        "privacy": {"local_paths_redacted": True, "profile_ids_redacted": True},
        "counts": {
            "events": len(events),
            "calibration_events": len(calibration),
            "holdout_events": len(holdout),
            "poison_events": len(poison),
            "learned_role_pairs": len(model.role_pair_weights),
            "hard_negative_constraints": len(model.negative_constraints),
        },
        "metrics": metrics,
        "profile_projection": {
            "transition_style_tags": tuple(profile.get("transition_style_tags") or ()),
            "suggestion_cadence": profile.get("suggestion_cadence"),
        },
        "errors": tuple(validation_errors),
    }


def _accepted_suggestion_lift(model: Any, events: tuple[FeedbackEvent, ...]) -> float:
    positives = tuple(event for event in events if event.label in {"would_play", "played_next"})
    if not positives:
        return 0.0
    return round(
        sum(model.taste_score_for(event.role_pair) - 0.50 for event in positives) / len(positives),
        6,
    )


def _false_negative_rate(model: Any, events: tuple[FeedbackEvent, ...]) -> float:
    positives = tuple(event for event in events if event.label in {"would_play", "played_next"})
    return _rate(
        sum(1 for event in positives if model.taste_score_for(event.role_pair) < 0.50),
        len(positives),
    )


def _single_session_hard_negative_rate(model: Any) -> float:
    if not model.negative_constraints:
        return 0.0
    single_session = sum(
        1 for constraint in model.negative_constraints if constraint.session_count <= 1
    )
    return _rate(single_session, len(model.negative_constraints))


def _unknown_preference_claim_rate(profile: dict[str, Any]) -> float:
    tags = tuple(profile.get("transition_style_tags") or ())
    if not tags:
        return 0.0
    unknown = sum(1 for tag in tags if tag not in ALLOWED_TRANSITION_STYLE_TAGS)
    return _rate(unknown, len(tags))


def _technical_bad_candidate_rescued_by_taste(model: Any, events: tuple[FeedbackEvent, ...]) -> int:
    rescued = 0
    for event in events:
        if event.label not in TECHNICAL_LABELS or not event.risk_flags:
            continue
        base = event.score or 0.0
        taste_delta = 0.05 * (model.taste_score_for(event.role_pair) - 0.50)
        if base + taste_delta >= LIVE_SELECT_FLOOR:
            rescued += 1
    return rescued


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument("--feedback", type=Path, help="Taste feedback JSON/JSONL")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)

    result = (
        score_path(args.feedback)
        if args.feedback is not None
        else score_fixture_dir(args.fixture_dir)
    )
    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        metrics = result["metrics"]
        print(
            "Taste scorecard: "
            f"valid={result['valid']} "
            f"lift={metrics['accepted_suggestion_lift']} "
            f"poison={metrics['single_session_hard_negative_rate']}"
        )
    return 0 if result.get("valid") is True else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
