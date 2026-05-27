# SPDX-License-Identifier: Apache-2.0
"""Validate, sample, and report INTEL-15 gold-label artifacts."""

from __future__ import annotations

import argparse
import json
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
    items = sample_transition_candidates(candidates, n=n, threshold=threshold)
    return {
        "schema": "intel_gold_sample_v1",
        "kind": "transition",
        "n": len(items),
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
    return 0


def _summary(result: dict[str, Any]) -> str:
    if result["schema"] == "intel_gold_sample_v1":
        return f"Gold sample: kind={result['kind']} n={result['n']}"
    counts = result.get("counts", {})
    return f"Gold validation: valid={result['valid']} total={counts.get('total', 0)}"


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
