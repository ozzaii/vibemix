# SPDX-License-Identifier: Apache-2.0
"""Real-library CLAP zero-shot auto-tag bench.

Upgrade #2 proof harness: score cached whole-track CLAP vectors against a fixed
mood/texture/instrument prompt bank, then evaluate template prompts vs bare
labels when a small hand-labeled JSONL exists.

Default labels path:

    eval/private/library/auto_tag_labels.jsonl

Rows may be either category columns:

    {"track_id": "rb-1", "mood": ["dark"], "texture": ["raw"], "instrument": []}

or a nested ``tags`` object:

    {"track_id": "rb-1", "split": "holdout", "tags": {"mood": ["dark"]}}

When the file is absent, the bench still emits a JSON artifact with prediction
coverage and abstention rates, but returns an honest
``unproven_no_hand_labels`` status and makes no precision/recall claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.library_similarity_tagging import _git_head, _unit_rows  # noqa: E402
from vibemix.library.auto_tags import (  # noqa: E402
    DEFAULT_MARGIN,
    DEFAULT_THRESHOLDS,
    AutoTagCategory,
    AutoTagDecision,
    PromptMode,
    accepted_tags,
    build_prompt_matrix,
    known_tags_by_category,
    score_auto_tag_categories,
)
from vibemix.library.clap_engine import ClapEngine  # noqa: E402
from vibemix.library.store import open_store  # noqa: E402

SCHEMA = "library_auto_tags_bench_v1"
DEFAULT_LABELS_PATH = ROOT / "eval" / "private" / "library" / "auto_tag_labels.jsonl"
DEFAULT_MAX_EXAMPLES = 16
THRESHOLD_GRID = tuple(round(x / 1000, 3) for x in range(80, 321, 10))
CATEGORIES: tuple[AutoTagCategory, ...] = ("mood", "texture", "instrument")


@dataclass(frozen=True)
class HandLabelRow:
    track_id: str
    split: str
    labels: dict[AutoTagCategory, set[str]]


def _as_tag_set(raw: Any) -> set[str]:
    if raw is None:
        return set()
    if isinstance(raw, str):
        values: Sequence[Any] = [raw]
    elif isinstance(raw, Sequence) and not isinstance(raw, (bytes, bytearray)):
        values = raw
    else:
        values = [raw]
    return {
        str(value).strip().lower().replace(" ", "_").replace("-", "_")
        for value in values
        if str(value).strip()
    }


def _read_json_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    raw = json.loads(text)
    if isinstance(raw, dict):
        raw = raw.get("labels", raw.get("rows", []))
    if not isinstance(raw, list):
        raise ValueError("auto-tag labels must be JSONL, a list, or {labels:[...]}")
    return [row for row in raw if isinstance(row, dict)]


def load_hand_labels(path: Path) -> dict[str, Any]:
    known = known_tags_by_category()
    if not path.exists():
        return {
            "status": "missing",
            "path": str(path),
            "rows": [],
            "usable_rows": 0,
            "unknown_tags": {},
        }

    rows: list[HandLabelRow] = []
    unknown_tags: dict[str, list[str]] = defaultdict(list)
    for raw in _read_json_rows(path):
        track_id = str(raw.get("track_id", "") or raw.get("id", "")).strip()
        if not track_id:
            continue
        split = str(raw.get("split", "") or "eval").strip().lower()
        tags_obj = raw.get("tags") if isinstance(raw.get("tags"), Mapping) else raw
        labels: dict[AutoTagCategory, set[str]] = {}
        for category in CATEGORIES:
            tags = _as_tag_set(tags_obj.get(category))  # type: ignore[union-attr]
            accepted = tags & known[category]
            unknown = sorted(tags - known[category])
            if unknown:
                unknown_tags[category].extend(unknown)
            if tags or category in tags_obj:  # type: ignore[operator]
                labels[category] = accepted
        if labels:
            rows.append(HandLabelRow(track_id=track_id, split=split, labels=labels))

    return {
        "status": "ok" if rows else "empty",
        "path": str(path),
        "rows": rows,
        "usable_rows": len(rows),
        "unknown_tags": {
            category: sorted(set(tags)) for category, tags in sorted(unknown_tags.items())
        },
    }


def _score_track_vectors(
    ids: Sequence[str],
    vectors: np.ndarray,
    *,
    mode: PromptMode,
    embed_query,
    thresholds: Mapping[AutoTagCategory, float] | None = None,
    margin: float = DEFAULT_MARGIN,
) -> dict[str, tuple[AutoTagDecision, ...]]:
    prompt_matrix = build_prompt_matrix(embed_query, mode=mode)
    unit = _unit_rows(vectors)
    return {
        str(tid): score_auto_tag_categories(
            unit[i],
            prompt_matrix,
            thresholds=thresholds,
            margin=margin,
        )
        for i, tid in enumerate(ids)
    }


def prediction_summary(
    predictions: Mapping[str, Sequence[AutoTagDecision]],
) -> dict[str, Any]:
    accepted_counts: dict[str, Counter[str]] = {category: Counter() for category in CATEGORIES}
    abstentions: Counter[str] = Counter()
    evaluated: Counter[str] = Counter()
    for decisions in predictions.values():
        for decision in decisions:
            evaluated[decision.category] += 1
            if decision.accepted and decision.tag:
                accepted_counts[decision.category][decision.tag] += 1
            else:
                abstentions[decision.category] += 1

    categories: dict[str, Any] = {}
    for category in CATEGORIES:
        total = int(evaluated[category])
        abstained = int(abstentions[category])
        categories[category] = {
            "evaluated": total,
            "accepted": total - abstained,
            "abstained": abstained,
            "abstention_rate": round(abstained / total, 6) if total else None,
            "top_tags": [
                {"tag": tag, "count": count}
                for tag, count in accepted_counts[category].most_common(12)
            ],
        }
    return {
        "track_count": len(predictions),
        "categories": categories,
    }


def _rows_by_split(rows: Sequence[HandLabelRow]) -> tuple[list[HandLabelRow], list[HandLabelRow], str]:
    calibration = [r for r in rows if r.split in {"calibration", "train"}]
    holdout = [r for r in rows if r.split in {"holdout", "eval", "test"}]
    if calibration and holdout:
        return calibration, holdout, "split_calibration_holdout"
    return list(rows), list(rows), "in_sample_threshold_grid"


def _metric_counts(
    rows: Sequence[HandLabelRow],
    predictions: Mapping[str, Sequence[AutoTagDecision]],
    *,
    category: AutoTagCategory | None = None,
) -> dict[str, Any]:
    tp = fp = fn = abstained = evaluated = missing_predictions = 0
    for row in rows:
        decisions = predictions.get(row.track_id)
        if decisions is None:
            missing_predictions += 1
            continue
        pred_by_cat = accepted_tags(decisions)
        categories = (category,) if category is not None else tuple(row.labels)
        for cat in categories:
            if cat not in row.labels:
                continue
            evaluated += 1
            gold = row.labels[cat]
            pred = pred_by_cat.get(cat, set())
            if not pred:
                abstained += 1
            tp += len(pred & gold)
            fp += len(pred - gold)
            fn += len(gold - pred)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "evaluated_decisions": evaluated,
        "missing_predictions": missing_predictions,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "abstentions": abstained,
        "abstention_rate": round(abstained / evaluated, 6) if evaluated else None,
    }


def evaluate_labeled_predictions(
    rows: Sequence[HandLabelRow],
    predictions: Mapping[str, Sequence[AutoTagDecision]],
) -> dict[str, Any]:
    return {
        "micro": _metric_counts(rows, predictions),
        "categories": {
            category: _metric_counts(rows, predictions, category=category)
            for category in CATEGORIES
        },
        "labeled_tracks": len({row.track_id for row in rows}),
    }


def calibrate_thresholds(
    ids: Sequence[str],
    vectors: np.ndarray,
    *,
    mode: PromptMode,
    embed_query,
    rows: Sequence[HandLabelRow],
    grid: Sequence[float] = THRESHOLD_GRID,
    margin: float = DEFAULT_MARGIN,
) -> dict[AutoTagCategory, float]:
    thresholds: dict[AutoTagCategory, float] = dict(DEFAULT_THRESHOLDS)
    for category in CATEGORIES:
        best_key: tuple[float, float, float, float] | None = None
        best_threshold = thresholds[category]
        for threshold in grid:
            candidate = dict(thresholds)
            candidate[category] = float(threshold)
            preds = _score_track_vectors(
                ids,
                vectors,
                mode=mode,
                embed_query=embed_query,
                thresholds=candidate,
                margin=margin,
            )
            metrics = _metric_counts(rows, preds, category=category)
            key = (
                float(metrics["f1"]),
                float(metrics["precision"]),
                float(metrics["recall"]),
                -float(threshold),
            )
            if best_key is None or key > best_key:
                best_key = key
                best_threshold = float(threshold)
        thresholds[category] = best_threshold
    return thresholds


def _example_predictions(
    predictions: Mapping[str, Sequence[AutoTagDecision]],
    *,
    max_examples: int,
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for track_id in sorted(predictions)[:max_examples]:
        examples.append(
            {
                "track_id": track_id,
                "tags": {
                    category: sorted(tags)
                    for category, tags in sorted(accepted_tags(predictions[track_id]).items())
                },
                "abstained": [
                    decision.category
                    for decision in predictions[track_id]
                    if not decision.accepted
                ],
            }
        )
    return examples


def _load_store() -> tuple[list[str], np.ndarray, str, str]:
    store = open_store()
    try:
        ids, vectors = store._backend.load_all()
        snapshot = store.snapshot_hash()
        backend = store.backend_name
    finally:
        store.close()
    return ids, _unit_rows(vectors), backend, snapshot


def build_report(
    *,
    labels_path: Path = DEFAULT_LABELS_PATH,
    margin: float = DEFAULT_MARGIN,
    max_examples: int = DEFAULT_MAX_EXAMPLES,
) -> dict[str, Any]:
    ids, vectors, backend, snapshot = _load_store()
    engine = ClapEngine()
    labels = load_hand_labels(labels_path)
    rows: list[HandLabelRow] = labels["rows"]
    calibration_rows, eval_rows, calibration_strategy = _rows_by_split(rows)

    mode_reports: dict[str, Any] = {}
    for mode in ("bare", "template"):
        if rows:
            thresholds = calibrate_thresholds(
                ids,
                vectors,
                mode=mode,  # type: ignore[arg-type]
                embed_query=engine.embed_query,
                rows=calibration_rows,
                margin=margin,
            )
        else:
            thresholds = dict(DEFAULT_THRESHOLDS)
        predictions = _score_track_vectors(
            ids,
            vectors,
            mode=mode,  # type: ignore[arg-type]
            embed_query=engine.embed_query,
            thresholds=thresholds,
            margin=margin,
        )
        mode_reports[mode] = {
            "thresholds": {k: round(v, 6) for k, v in sorted(thresholds.items())},
            "prediction_summary": prediction_summary(predictions),
            "example_predictions": _example_predictions(predictions, max_examples=max_examples),
            "metrics": evaluate_labeled_predictions(eval_rows, predictions) if rows else None,
        }

    comparison: dict[str, Any] | None = None
    status = "unproven_no_hand_labels"
    if rows:
        bare_f1 = float(mode_reports["bare"]["metrics"]["micro"]["f1"])
        template_f1 = float(mode_reports["template"]["metrics"]["micro"]["f1"])
        comparison = {
            "primary_metric": "micro_f1",
            "template_value": round(template_f1, 6),
            "bare_value": round(bare_f1, 6),
            "template_minus_bare": round(template_f1 - bare_f1, 6),
            "template_beats_bare": template_f1 > bare_f1,
        }
        status = "ok" if len(eval_rows) >= 50 else "measured_small_hand_label_subset"

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_head": _git_head(),
        "status": status,
        "store": {
            "backend": backend,
            "snapshot_hash": snapshot,
            "embedded_tracks": len(ids),
        },
        "prompt_bank": {
            "categories": list(CATEGORIES),
            "prompt_count": sum(len(tags) for tags in known_tags_by_category().values()),
            "modes": ["bare", "template"],
        },
        "label_set": {
            "path": labels["path"],
            "status": labels["status"],
            "usable_rows": labels["usable_rows"],
            "evaluation_rows": len(eval_rows),
            "calibration_rows": len(calibration_rows),
            "calibration_strategy": calibration_strategy if rows else None,
            "unknown_tags": labels["unknown_tags"],
            "hook": "create eval/private/library/auto_tag_labels.jsonl with track_id + mood/texture/instrument tags",
        },
        "margin": margin,
        "modes": mode_reports,
        "comparison": comparison,
        "notes": {
            "no_audio_decode": True,
            "no_torch_or_librosa": True,
            "cached_audio_vectors_only": True,
            "no_accuracy_claim_without_labels": labels["status"] != "ok",
            "honest_caveat": (
                "precision/recall and template-vs-bare claims require the private "
                "hand-labeled auto_tag_labels.jsonl set"
            ),
        },
    }


def default_output_path() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return ROOT / ".planning" / "eval-runs" / f"library-auto-tags-{stamp}" / "report.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS_PATH)
    parser.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    parser.add_argument("--max-examples", type=int, default=DEFAULT_MAX_EXAMPLES)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--require-labels",
        action="store_true",
        help="exit nonzero when the hand-label file is missing/empty",
    )
    args = parser.parse_args(argv)

    report = build_report(
        labels_path=args.labels,
        margin=args.margin,
        max_examples=args.max_examples,
    )
    out_path = args.out or default_output_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        template = report["modes"]["template"]["prediction_summary"]
        print(f"wrote {out_path}")
        print(
            f"status={report['status']} embedded_tracks={report['store']['embedded_tracks']} "
            f"labels={report['label_set']['usable_rows']} "
            f"template_abstention="
            f"{ {k: v['abstention_rate'] for k, v in template['categories'].items()} }"
        )
        if report["comparison"] is not None:
            comparison = report["comparison"]
            print(
                "template_vs_bare "
                f"{comparison['primary_metric']}={comparison['template_value']} vs "
                f"{comparison['bare_value']} delta={comparison['template_minus_bare']}"
            )
    if args.require_labels and report["label_set"]["usable_rows"] == 0:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
