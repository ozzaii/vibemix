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
from urllib.parse import unquote, urlparse

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
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry  # noqa: E402
from vibemix.library.store import open_store  # noqa: E402

SCHEMA = "library_auto_tags_bench_v1"
DEFAULT_LABELS_PATH = ROOT / "eval" / "private" / "library" / "auto_tag_labels.jsonl"
DEFAULT_LABEL_TEMPLATE_SIZE = 64
DEFAULT_MAX_EXAMPLES = 16
DEFAULT_MIN_HAND_LABELS = 50
THRESHOLD_GRID = tuple(round(x / 1000, 3) for x in range(80, 321, 10))
CATEGORIES: tuple[AutoTagCategory, ...] = ("mood", "texture", "instrument")
TODO_LABEL_STATUSES = {"draft", "pending", "todo"}


def _local_path_text(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.scheme == "file":
        return unquote(parsed.path)
    return unquote(text)


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
            "pending_rows": 0,
            "usable_rows": 0,
            "unknown_tags": {},
        }

    rows: list[HandLabelRow] = []
    pending_rows = 0
    unknown_tags: dict[str, list[str]] = defaultdict(list)
    for raw in _read_json_rows(path):
        track_id = str(raw.get("track_id", "") or raw.get("id", "")).strip()
        if not track_id:
            continue
        label_status = str(raw.get("label_status", raw.get("status", "")) or "").strip().lower()
        if label_status in TODO_LABEL_STATUSES:
            pending_rows += 1
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
        "pending_rows": pending_rows,
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


def _complete_rows(rows: Sequence[HandLabelRow]) -> list[HandLabelRow]:
    return [row for row in rows if all(category in row.labels for category in CATEGORIES)]


def _missing_category_counts(rows: Sequence[HandLabelRow]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        for category in CATEGORIES:
            if category not in row.labels:
                counts[category] += 1
    return {category: counts[category] for category in CATEGORIES}


def build_label_audit(
    *,
    labels_path: Path = DEFAULT_LABELS_PATH,
    min_hand_labels: int = DEFAULT_MIN_HAND_LABELS,
) -> dict[str, Any]:
    """Fast audit for the private hand-label file, no CLAP/store work."""
    labels = load_hand_labels(labels_path)
    rows: list[HandLabelRow] = labels["rows"]
    calibration_rows, eval_rows, calibration_strategy = _rows_by_split(rows)
    complete_rows = _complete_rows(rows)
    complete_eval_rows = _complete_rows(eval_rows)
    enough = len(complete_eval_rows) >= min_hand_labels
    return {
        "schema": f"{SCHEMA}_label_audit_v1",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_head": _git_head(),
        "path": labels["path"],
        "label_status": labels["status"],
        "pending_rows": labels["pending_rows"],
        "usable_rows": labels["usable_rows"],
        "complete_rows": len(complete_rows),
        "calibration_rows": len(calibration_rows),
        "evaluation_rows": len(eval_rows),
        "evaluation_complete_rows": len(complete_eval_rows),
        "min_required_rows": min_hand_labels,
        "enough_complete_eval_rows": enough,
        "calibration_strategy": calibration_strategy if rows else None,
        "missing_category_counts": _missing_category_counts(rows),
        "unknown_tags": labels["unknown_tags"],
        "required_categories": list(CATEGORIES),
        "next_action": (
            "run the full auto-tag bench with --require-labels"
            if enough
            else (
                "complete eval/private/library/auto_tag_labels.jsonl rows for "
                "mood, texture, and instrument"
            )
        ),
    }


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


def _decision_payload(decision: AutoTagDecision) -> dict[str, Any]:
    return {
        "accepted": decision.accepted,
        "reason": decision.reason,
        "score": decision.score,
        "tag": decision.tag,
        "runner_up_tag": decision.runner_up_tag,
        "runner_up_score": decision.runner_up_score,
        "margin": decision.margin,
        "threshold": decision.threshold,
    }


def build_label_template_rows(
    predictions: Mapping[str, Sequence[AutoTagDecision]],
    *,
    max_rows: int = DEFAULT_LABEL_TEMPLATE_SIZE,
    exclude_track_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return a diverse TODO label queue, safe to write as JSONL.

    Rows are explicitly marked ``label_status: todo``; ``load_hand_labels`` skips
    them until the reviewer changes the status. That prevents an empty template
    from being mistaken for an all-negative hand-label set.
    """
    if max_rows <= 0:
        return []
    exclude_track_ids = exclude_track_ids or set()
    buckets: dict[tuple[str, str], list[str]] = defaultdict(list)
    for track_id, decisions in predictions.items():
        if track_id in exclude_track_ids:
            continue
        accepted = accepted_tags(decisions)
        mood = sorted(accepted.get("mood", {"mood_unknown"}))[0]
        texture = sorted(accepted.get("texture", {"texture_unknown"}))[0]
        buckets[(mood, texture)].append(track_id)
    for bucket_ids in buckets.values():
        bucket_ids.sort()

    selected: list[str] = []
    bucket_keys = sorted(buckets, key=lambda key: (-len(buckets[key]), key))
    while len(selected) < max_rows:
        progressed = False
        for key in bucket_keys:
            rows = buckets[key]
            if not rows:
                continue
            selected.append(rows.pop(0))
            progressed = True
            if len(selected) >= max_rows:
                break
        if not progressed:
            break

    out: list[dict[str, Any]] = []
    for i, track_id in enumerate(selected):
        decisions = sorted(predictions[track_id], key=lambda d: d.category)
        out.append(
            {
                "track_id": track_id,
                "split": "calibration" if i % 5 == 0 else "holdout",
                "label_status": "todo",
                "tags": {category: [] for category in CATEGORIES},
                "prediction_context": {
                    decision.category: _decision_payload(decision)
                    for decision in decisions
                },
            }
        )
    return out


def _library_cache_candidates() -> tuple[Path, ...]:
    primary = RekordboxLibrary.CACHE_PATH.expanduser()
    return (primary, primary.with_suffix(primary.suffix + ".v1bak"))


def _load_track_contexts(track_ids: set[str]) -> dict[str, TrackEntry]:
    contexts: dict[str, TrackEntry] = {}
    if not track_ids:
        return contexts
    old_cache_path = RekordboxLibrary.CACHE_PATH
    try:
        for cache_path in _library_cache_candidates():
            if not cache_path.exists():
                continue
            RekordboxLibrary.CACHE_PATH = cache_path
            lib = RekordboxLibrary()
            if not lib.try_load_cache():
                continue
            for track_id in track_ids:
                if track_id not in contexts and track_id in lib.tracks:
                    contexts[track_id] = lib.tracks[track_id]
            if len(contexts) == len(track_ids):
                break
    finally:
        RekordboxLibrary.CACHE_PATH = old_cache_path
    return contexts


def _track_private_context(track: TrackEntry | None) -> dict[str, Any]:
    if track is None:
        return {"found": False}
    local = Path(_local_path_text(track.filepath)) if track.filepath else None
    return {
        "found": True,
        "title": track.title,
        "artist": track.artist,
        "album": track.album,
        "genre": track.genre,
        "bpm": track.bpm,
        "key": track.key,
        "duration_s": track.duration_s,
        "folder": local.parent.name if local is not None else "",
        "filename": local.name if local is not None else "",
    }


def build_private_label_template_rows(
    template_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Add local-only review context to template rows.

    The public `.planning/eval-runs` report stays redacted. This helper is used
    only when the operator passes ``--private-label-template-out`` and wants a
    local file that is actually labelable by a human.
    """
    track_ids = {str(row.get("track_id", "")) for row in template_rows}
    contexts = _load_track_contexts(track_ids)
    out: list[dict[str, Any]] = []
    for row in template_rows:
        copied = dict(row)
        track_id = str(copied.get("track_id", ""))
        copied["track_context"] = _track_private_context(contexts.get(track_id))
        out.append(copied)
    return out


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
    label_template_size: int = DEFAULT_LABEL_TEMPLATE_SIZE,
    margin: float = DEFAULT_MARGIN,
    max_examples: int = DEFAULT_MAX_EXAMPLES,
    min_hand_labels: int = DEFAULT_MIN_HAND_LABELS,
) -> dict[str, Any]:
    ids, vectors, backend, snapshot = _load_store()
    engine = ClapEngine()
    labels = load_hand_labels(labels_path)
    rows: list[HandLabelRow] = labels["rows"]
    calibration_rows, eval_rows, calibration_strategy = _rows_by_split(rows)
    complete_rows = _complete_rows(rows)
    complete_eval_rows = _complete_rows(eval_rows)

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
            "_predictions": predictions,
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
        status = (
            "ok"
            if len(complete_eval_rows) >= min_hand_labels
            else "measured_small_hand_label_subset"
        )

    labeled_ids = {row.track_id for row in rows}
    template_rows = (
        build_label_template_rows(
            mode_reports["template"]["_predictions"],
            max_rows=label_template_size,
            exclude_track_ids=labeled_ids,
        )
        if len(complete_eval_rows) < min_hand_labels
        else []
    )
    for mode in mode_reports.values():
        mode.pop("_predictions", None)

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
            "pending_rows": labels["pending_rows"],
            "usable_rows": labels["usable_rows"],
            "complete_rows": len(complete_rows),
            "evaluation_rows": len(eval_rows),
            "evaluation_complete_rows": len(complete_eval_rows),
            "calibration_rows": len(calibration_rows),
            "calibration_strategy": calibration_strategy if rows else None,
            "min_required_rows": min_hand_labels,
            "unknown_tags": labels["unknown_tags"],
            "hook": "create eval/private/library/auto_tag_labels.jsonl with track_id + mood/texture/instrument tags",
        },
        "label_template": {
            "status": "needed" if template_rows else "not_needed",
            "row_count": len(template_rows),
            "path": None,
            "rows": template_rows,
            "safety": "label_status=todo rows are skipped until a reviewer marks them complete",
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
    parser.add_argument("--label-template-size", type=int, default=DEFAULT_LABEL_TEMPLATE_SIZE)
    parser.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    parser.add_argument("--max-examples", type=int, default=DEFAULT_MAX_EXAMPLES)
    parser.add_argument("--min-hand-labels", type=int, default=DEFAULT_MIN_HAND_LABELS)
    parser.add_argument("--no-label-template", action="store_true")
    parser.add_argument(
        "--audit-labels",
        action="store_true",
        help="fast label-file audit only; no CLAP/model/vector-store work",
    )
    parser.add_argument(
        "--private-label-template-out",
        type=Path,
        default=None,
        help=(
            "write a local-only review JSONL with title/artist/folder hints; "
            "keep it under eval/private/ and do not commit it"
        ),
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--require-labels",
        action="store_true",
        help="exit nonzero when the hand-label file is missing/empty",
    )
    args = parser.parse_args(argv)

    if args.audit_labels:
        audit = build_label_audit(
            labels_path=args.labels,
            min_hand_labels=args.min_hand_labels,
        )
        if args.json:
            print(json.dumps(audit, indent=2, sort_keys=True))
        else:
            print(
                "auto-tag labels: "
                f"status={audit['label_status']} "
                f"usable={audit['usable_rows']} "
                f"complete_eval={audit['evaluation_complete_rows']}/"
                f"{audit['min_required_rows']} "
                f"pending={audit['pending_rows']}"
            )
            if audit["missing_category_counts"]:
                print(f"missing_categories={audit['missing_category_counts']}")
        return 0 if audit["enough_complete_eval_rows"] else 2

    report = build_report(
        labels_path=args.labels,
        label_template_size=(0 if args.no_label_template else args.label_template_size),
        margin=args.margin,
        max_examples=args.max_examples,
        min_hand_labels=args.min_hand_labels,
    )
    out_path = args.out or default_output_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    template_rows = report["label_template"]["rows"]
    if template_rows:
        template_path = out_path.with_name("auto_tag_label_template.jsonl")
        template_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in template_rows),
            encoding="utf-8",
        )
        report["label_template"]["path"] = str(template_path)
        if args.private_label_template_out is not None:
            private_rows = build_private_label_template_rows(template_rows)
            args.private_label_template_out.parent.mkdir(parents=True, exist_ok=True)
            args.private_label_template_out.write_text(
                "".join(json.dumps(row, sort_keys=True) + "\n" for row in private_rows),
                encoding="utf-8",
            )
            report["label_template"]["private_path_written"] = str(
                args.private_label_template_out
            )
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        template = report["modes"]["template"]["prediction_summary"]
        print(f"wrote {out_path}")
        print(
            f"status={report['status']} embedded_tracks={report['store']['embedded_tracks']} "
            f"labels={report['label_set']['usable_rows']} "
            f"label_template_rows={report['label_template']['row_count']} "
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
    if (
        args.require_labels
        and report["label_set"]["evaluation_complete_rows"] < args.min_hand_labels
    ):
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
