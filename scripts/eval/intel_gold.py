# SPDX-License-Identifier: Apache-2.0
"""Validate, sample, and report INTEL-15 gold-label artifacts."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from vibemix.intel.gold_labels import load_gold_labels
from vibemix.intel.gold_sampling import sample_transition_candidates
from vibemix.intel.gold_validation import (
    GoldKnownIds,
    redacted_gold_report,
    validate_gold_labels,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_DIR = ROOT / "tests" / "intel" / "fixtures"
PRIVATE_PAYLOAD_PATTERNS = (
    re.compile(r"/Users/[^\"'\s]+"),
    re.compile(r"/Volumes/[^\"'\s]+"),
    re.compile(r"[A-Za-z]:\\\\[^\"'\s]+"),
    re.compile(r"file://[^\"'\s]+", re.I),
    re.compile(r"\.(?:wav|aiff|aif|mp3|flac)\b", re.I),
    re.compile(r"\braw_(?:audio|vector)s?\b", re.I),
)


def validate_gold_file(
    labels_path: Path | str,
    *,
    fixture_dir: Path | str = DEFAULT_FIXTURE_DIR,
    require_all_splits: bool = False,
) -> dict[str, Any]:
    labels = load_gold_labels(labels_path)
    known = known_ids_from_fixture_dir(Path(fixture_dir))
    result = validate_gold_labels(labels, known_ids=known, require_all_splits=require_all_splits)
    return {
        "schema": "intel_gold_validation_v1",
        "valid": result.valid,
        "privacy": {"local_paths_redacted": True},
        "counts": result.counts,
        "errors": result.errors,
        "warnings": result.warnings,
    }


def report_gold_file(
    labels_path: Path | str,
    *,
    fixture_dir: Path | str = DEFAULT_FIXTURE_DIR,
    salt: str = "intel-gold-report",
    require_all_splits: bool = False,
) -> dict[str, Any]:
    labels = load_gold_labels(labels_path)
    known = known_ids_from_fixture_dir(Path(fixture_dir))
    validation = validate_gold_labels(
        labels, known_ids=known, require_all_splits=require_all_splits
    )
    return redacted_gold_report(labels, validation, salt=salt)


def sample_gold_items(
    candidates_path: Path | str,
    *,
    n: int,
    threshold: float = 0.62,
) -> dict[str, Any]:
    candidates = _load_json(Path(candidates_path))
    errors = _sample_candidate_errors(candidates, n=n, threshold=threshold)
    items = () if errors else sample_transition_candidates(candidates, n=n, threshold=threshold)
    return {
        "schema": "intel_gold_sample_v1",
        "valid": bool(items) and not errors,
        "privacy": {"local_paths_redacted": True},
        "kind": "transition",
        "n": len(items),
        "errors": tuple(errors),
        "items": [
            {
                "review_item_id": item.review_item_id,
                "sample_reason": item.sample_reason,
                "candidate_id": item.candidate_id,
                "payload": item.payload,
            }
            for item in items
        ],
    }


def known_ids_from_fixture_dir(fixture_dir: Path) -> GoldKnownIds:
    contexts = _load_json(fixture_dir / "context_packets.json", default=[])
    transition_pairs = _load_json(fixture_dir / "transition_pairs.json", default=[])
    proposals = _load_json(fixture_dir / "smart_cue_proposals.json", default=[])
    tracks = _load_json(fixture_dir / "tracks.json", default=[])
    sections = _load_json(fixture_dir / "sections.json", default=[])
    return GoldKnownIds(
        candidate_ids=frozenset(
            str(candidate.get("candidate_id"))
            for candidate in transition_pairs
            if candidate.get("candidate_id")
        )
        | frozenset(
            str(candidate_id)
            for context in contexts
            for candidate_id in context.get("candidate_ids", ())
            if candidate_id
        ),
        transition_keys=frozenset(
            str(candidate.get("transition_key"))
            for candidate in transition_pairs
            if candidate.get("transition_key")
        ),
        proposal_ids=frozenset(
            str(proposal.get("proposal_id"))
            for proposal in proposals
            if proposal.get("proposal_id")
        ),
        cue_ids=frozenset(
            str(cue.get("cue_id"))
            for proposal in proposals
            for cue in proposal.get("cues", ())
            if isinstance(cue, dict) and cue.get("cue_id")
        ),
        packet_ids=frozenset(
            str(context.get("packet_id")) for context in contexts if context.get("packet_id")
        ),
        track_ids=frozenset(
            str(track.get("track_id")) for track in tracks if track.get("track_id")
        ),
        section_ids=frozenset(
            str(section.get("section_id")) for section in sections if section.get("section_id")
        ),
    )


def _load_json(path: Path, *, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return [] if default is None else default
    return json.loads(text)


def _sample_candidate_errors(candidates: Any, *, n: int, threshold: float) -> tuple[str, ...]:
    errors: list[str] = []
    if n <= 0:
        errors.append("sample_n_must_be_positive")
    if _finite_float_or_none(threshold) is None:
        errors.append("nonfinite_threshold")
    if not isinstance(candidates, list) or not candidates:
        errors.append("missing_candidates")
        return tuple(errors)
    errors.extend(_private_payload_errors(candidates))
    seen: set[str] = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            errors.append(f"candidate_{index}:invalid_candidate")
            continue
        candidate_id = str(candidate.get("candidate_id") or f"<candidate_{index}>")
        if not candidate.get("candidate_id"):
            errors.append(f"{candidate_id}:missing_candidate_id")
        elif candidate_id in seen:
            errors.append(f"{candidate_id}:duplicate_candidate_id")
        seen.add(candidate_id)
        for field in ("score", "confidence"):
            value = candidate.get(field)
            if value is not None and _finite_float_or_none(value) is None:
                errors.append(f"{candidate_id}:nonfinite_{field}")
        start_in_bars = candidate.get("start_in_bars")
        if start_in_bars is not None and _finite_float_or_none(start_in_bars) is None:
            errors.append(f"{candidate_id}:nonfinite_start_in_bars")
        risk_flags = candidate.get("risk_flags")
        if risk_flags is not None and not isinstance(risk_flags, list | tuple):
            errors.append(f"{candidate_id}:invalid_risk_flags")
        scores = candidate.get("scores")
        if isinstance(scores, dict):
            for score_name, score_value in scores.items():
                if _finite_float_or_none(score_value) is None:
                    errors.append(f"{candidate_id}:scores.{score_name}:nonfinite_score")
    return tuple(errors)


def _private_payload_errors(value: Any) -> tuple[str, ...]:
    text = json.dumps(value, sort_keys=True, default=str)
    return (
        ("private_payload_present",)
        if any(pattern.search(text) for pattern in PRIVATE_PAYLOAD_PATTERNS)
        else ()
    )


def _finite_float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    validate_p = sub.add_parser("validate")
    validate_p.add_argument("labels", type=Path)
    validate_p.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    validate_p.add_argument("--require-all-splits", action="store_true")
    validate_p.add_argument("--json", action="store_true")

    report_p = sub.add_parser("report")
    report_p.add_argument("labels", type=Path)
    report_p.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    report_p.add_argument("--salt", default="intel-gold-report")
    report_p.add_argument("--require-all-splits", action="store_true")
    report_p.add_argument("--json", action="store_true")

    sample_p = sub.add_parser("sample")
    sample_p.add_argument("candidates", type=Path)
    sample_p.add_argument("--n", type=int, default=5)
    sample_p.add_argument("--threshold", type=float, default=0.62)
    sample_p.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "validate":
        result = validate_gold_file(
            args.labels,
            fixture_dir=args.fixture_dir,
            require_all_splits=args.require_all_splits,
        )
    elif args.cmd == "report":
        result = report_gold_file(
            args.labels,
            fixture_dir=args.fixture_dir,
            salt=args.salt,
            require_all_splits=args.require_all_splits,
        )
    else:
        result = sample_gold_items(args.candidates, n=args.n, threshold=args.threshold)

    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print(_summary(result))
    if result["schema"] in {"intel_gold_validation_v1", "intel_gold_report_v1"}:
        return 0 if result.get("valid") is True else 1
    if result["schema"] == "intel_gold_sample_v1":
        return 0 if result.get("valid") is True else 1
    return 0


def _summary(result: dict[str, Any]) -> str:
    if result["schema"] == "intel_gold_sample_v1":
        return f"Gold sample: kind={result['kind']} n={result['n']}"
    counts = result.get("counts", {})
    return f"Gold validation: valid={result['valid']} total={counts.get('total', 0)}"


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
