# SPDX-License-Identifier: Apache-2.0
"""Score transition ranking quality against INTEL-15 gold labels."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_FIXTURE_DIR = ROOT / "tests" / "intel" / "fixtures"
RELEVANCE: dict[str, int] = {"would_play": 2, "maybe": 1, "no": 0}


def score_fixture_dir(fixture_dir: Path | str = DEFAULT_FIXTURE_DIR) -> dict[str, Any]:
    base = Path(fixture_dir)
    return score_paths(
        candidates_path=base / "transition_pairs.json",
        labels_path=base / "gold_labels_redacted.jsonl",
        source=f"fixture:{base.name}",
    )


def score_paths(
    *,
    candidates_path: Path | str,
    labels_path: Path | str,
    source: str = "private:redacted",
) -> dict[str, Any]:
    from vibemix.intel.gold_labels import load_gold_labels

    candidates = _load_json(Path(candidates_path))
    labels = load_gold_labels(labels_path)
    return score_transition_labels(candidates=tuple(candidates), labels=labels, source=source)


def score_transition_labels(
    *,
    candidates: tuple[dict[str, Any], ...],
    labels: tuple[Any, ...],
    source: str,
) -> dict[str, Any]:
    errors: list[str] = []
    candidate_map: dict[str, dict[str, Any]] = {}
    for row in candidates:
        candidate_id = str(row.get("candidate_id") or "")
        if not candidate_id:
            errors.append("candidate_missing_id")
            continue
        score = _float(row.get("score"), math.nan)
        if math.isnan(score):
            errors.append(f"{candidate_id}:nan_score")
        candidate_map[candidate_id] = row

    transition_labels = tuple(label for label in labels if label.kind == "transition")
    labeled_rows: list[tuple[Any, dict[str, Any], int]] = []
    for label in transition_labels:
        if not label.candidate_id:
            errors.append(f"{label.label_id}:missing_candidate_id")
            continue
        candidate = candidate_map.get(label.candidate_id)
        if candidate is None:
            errors.append(f"{label.label_id}:unknown_candidate_id:{label.candidate_id}")
            continue
        relevance = RELEVANCE.get(label.label)
        if relevance is None:
            errors.append(f"{label.label_id}:unscored_transition_label:{label.label}")
            continue
        labeled_rows.append((label, candidate, relevance))

    ranked_candidates = sorted(
        candidate_map.values(), key=lambda row: _float(row.get("score"), 0.0), reverse=True
    )
    rank_by_id = {
        str(row["candidate_id"]): index
        for index, row in enumerate(ranked_candidates, start=1)
        if row.get("candidate_id")
    }
    positives = [row for row in labeled_rows if row[2] > 0]
    accepted_at_3 = sum(
        1 for label, _candidate, _rel in positives if rank_by_id[label.candidate_id] <= 3
    )
    risk_flagged = [row for row in labeled_rows if row[1].get("risk_flags")]
    risk_rejections = sum(1 for _label, _candidate, relevance in risk_flagged if relevance == 0)
    leakage = [
        str(row.get("candidate_id"))
        for row in candidates
        if "same_track_demo" in tuple(row.get("risk_flags") or ())
        or _section_track(row.get("from_section_id")) == _section_track(row.get("to_section_id"))
    ]

    metrics = {
        "pairwise_accuracy": _pairwise_accuracy(labeled_rows, rank_by_id),
        "ndcg_at_5": _ndcg_at_k(labeled_rows, rank_by_id, 5),
        "accepted_transition_rate_at_3": round(accepted_at_3 / len(positives), 6)
        if positives
        else 0.0,
        "risk_flag_precision": round(risk_rejections / len(risk_flagged), 6)
        if risk_flagged
        else 0.0,
        "leakage_rate": round(len(leakage) / len(candidates), 6) if candidates else 0.0,
        "unknown_candidate_label_count": float(
            sum(1 for error in errors if "unknown_candidate_id" in error)
        ),
        "nan_score_count": float(sum(1 for error in errors if error.endswith(":nan_score"))),
    }
    return {
        "schema": "intel_transition_scorecard_v1",
        "source": source,
        "valid": not errors,
        "privacy": {"local_paths_redacted": True},
        "totals": {
            "candidates": len(candidates),
            "transition_labels": len(transition_labels),
            "scored_labels": len(labeled_rows),
            "positive_labels": len(positives),
            "risk_flagged_labels": len(risk_flagged),
            "leakage_candidates": len(leakage),
        },
        "metrics": metrics,
        "errors": tuple(errors),
        "ranked_labeled": tuple(
            {
                "candidate_id": label.candidate_id,
                "rank": rank_by_id[label.candidate_id],
                "label": label.label,
                "relevance": relevance,
                "score": _float(candidate.get("score"), 0.0),
                "risk_flags": tuple(candidate.get("risk_flags") or ()),
            }
            for label, candidate, relevance in sorted(
                labeled_rows, key=lambda item: rank_by_id[item[0].candidate_id]
            )
        ),
    }


def _pairwise_accuracy(
    labeled_rows: list[tuple[Any, dict[str, Any], int]],
    rank_by_id: dict[str, int],
) -> float:
    total = 0
    correct = 0
    for i, (a_label, _a_candidate, a_rel) in enumerate(labeled_rows):
        for b_label, _b_candidate, b_rel in labeled_rows[i + 1 :]:
            if a_rel == b_rel:
                continue
            total += 1
            a_rank = rank_by_id[a_label.candidate_id]
            b_rank = rank_by_id[b_label.candidate_id]
            if (a_rel > b_rel and a_rank < b_rank) or (b_rel > a_rel and b_rank < a_rank):
                correct += 1
    return round(correct / total, 6) if total else 0.0


def _ndcg_at_k(
    labeled_rows: list[tuple[Any, dict[str, Any], int]],
    rank_by_id: dict[str, int],
    k: int,
) -> float:
    gains = sorted(
        (
            (rank_by_id[label.candidate_id], relevance)
            for label, _candidate, relevance in labeled_rows
        ),
        key=lambda item: item[0],
    )
    dcg = _dcg([relevance for rank, relevance in gains if rank <= k])
    ideal = _dcg(
        sorted((relevance for _label, _candidate, relevance in labeled_rows), reverse=True)[:k]
    )
    return round(dcg / ideal, 6) if ideal > 0 else 0.0


def _dcg(relevances: list[int]) -> float:
    return sum((2**rel - 1) / math.log2(index + 2) for index, rel in enumerate(relevances))


def _section_track(section_id: Any) -> str | None:
    if not isinstance(section_id, str) or "#s" not in section_id:
        return None
    return section_id.split("#s", 1)[0]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument("--candidates", type=Path, help="Transition candidate JSON")
    parser.add_argument("--labels", type=Path, help="Gold-label JSONL")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)

    if args.candidates or args.labels:
        if not args.candidates or not args.labels:
            parser.error("--candidates and --labels must be provided together")
        result = score_paths(
            candidates_path=args.candidates,
            labels_path=args.labels,
            source="private:redacted",
        )
    else:
        result = score_fixture_dir(args.fixture_dir)
    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        metrics = result["metrics"]
        print(
            "Transition scorecard: "
            f"valid={result['valid']} "
            f"accept@3={metrics['accepted_transition_rate_at_3']} "
            f"ndcg@5={metrics['ndcg_at_5']}"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
