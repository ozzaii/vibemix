# SPDX-License-Identifier: Apache-2.0
"""Phase 27-01 — F1 / precision / recall over event timestamp lists.

Greedy nearest-neighbor pairing per detector type within ±tolerance window
(per RESEARCH §F1 math). Pure stdlib + numpy — no scikit-learn (CONTEXT
"Test discipline": no new test runners; we keep the dependency surface lean).

Event shape (the contract the harness + corpus enforce):
    {
        "id": str,            # ground-truth event id (used for joining responses/<id>.txt)
        "type": str,          # detector type — TRACK_CHANGE, PHRASE_BOUNDARY, MIX_MOVE, ...
        "t_session": float,   # seconds since session start
        "session": str,       # session id (joined into per_detector_per_genre)
        ...                   # other payload fields ignored for F1 math
    }

The matching algorithm:
    For each event type, pair predicted ↔ ground_truth events greedily by
    smallest |Δt| <= tolerance_s. Each ground_truth event matches at most one
    predicted event; unmatched predictions become FP, unmatched ground_truth
    become FN.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _safe_div(a: float, b: float) -> float:
    return a / b if b > 0 else 0.0


def _f1(precision: float, recall: float) -> float:
    return _safe_div(2 * precision * recall, precision + recall)


def _pair_within_tolerance(
    predicted: list[dict[str, Any]],
    ground_truth: list[dict[str, Any]],
    tolerance_s: float,
) -> tuple[int, int, int]:
    """Greedy nearest-neighbor match within ±tolerance_s. Returns (tp, fp, fn).

    Both lists must already be filtered to a single event ``type``.
    Ground-truth events are matched at most once.
    """
    # Sort by timestamp for deterministic pairing.
    pred_sorted = sorted(enumerate(predicted), key=lambda x: x[1]["t_session"])
    gt_sorted = sorted(enumerate(ground_truth), key=lambda x: x[1]["t_session"])

    matched_gt: set[int] = set()
    tp = 0

    for _, p in pred_sorted:
        # Find nearest unmatched ground_truth within tolerance.
        best_idx = -1
        best_dt = tolerance_s + 1.0
        for gi, g in gt_sorted:
            if gi in matched_gt:
                continue
            dt = abs(p["t_session"] - g["t_session"])
            if dt <= tolerance_s and dt < best_dt:
                best_dt = dt
                best_idx = gi
        if best_idx >= 0:
            matched_gt.add(best_idx)
            tp += 1

    fp = len(predicted) - tp
    fn = len(ground_truth) - len(matched_gt)
    return tp, fp, fn


def _cell(tp: int, fp: int, fn: int) -> dict[str, float | int]:
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(_f1(precision, recall), 4),
    }


def compute_f1(
    predicted: list[dict[str, Any]],
    ground_truth: list[dict[str, Any]],
    tolerance_s: float = 2.0,
    genre_lookup: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Compute overall + per-detector + per-detector-per-genre F1.

    Parameters
    ----------
    predicted, ground_truth
        Lists of event dicts. Each must have ``type`` and ``t_session`` keys.
        For per-genre matrix output, each event must also have a ``session``
        key that ``genre_lookup`` can resolve.
    tolerance_s
        Match window in seconds. Default 2.0 per CONTEXT EVAL-01.
    genre_lookup
        Optional ``session_id -> genre`` callable. When provided, the result
        includes a ``per_detector_per_genre`` matrix. When omitted, only
        overall + ``per_detector`` are computed.

    Returns
    -------
    {
        "tp": int, "fp": int, "fn": int,
        "precision": float, "recall": float, "f1": float,
        "per_detector": { "TRACK_CHANGE": {...}, ... },
        "per_detector_per_genre": {  # only when genre_lookup provided
            "TRACK_CHANGE": { "techno": {...}, "house": {...}, ... },
            ...
        },
    }
    """
    # Group by type.
    types = sorted(set(e["type"] for e in predicted) | set(e["type"] for e in ground_truth))

    per_detector: dict[str, dict[str, float | int]] = {}
    total_tp = total_fp = total_fn = 0

    for t in types:
        pred_t = [e for e in predicted if e["type"] == t]
        gt_t = [e for e in ground_truth if e["type"] == t]
        tp, fp, fn = _pair_within_tolerance(pred_t, gt_t, tolerance_s)
        per_detector[t] = _cell(tp, fp, fn)
        total_tp += tp
        total_fp += fp
        total_fn += fn

    out: dict[str, Any] = _cell(total_tp, total_fp, total_fn)
    out["per_detector"] = per_detector

    if genre_lookup is not None:
        per_dpg: dict[str, dict[str, dict[str, float | int]]] = {}
        # Collect all genres from both lists' sessions.
        all_sessions = sorted(
            set(e.get("session", "") for e in predicted)
            | set(e.get("session", "") for e in ground_truth)
        )
        all_genres = sorted({genre_lookup(s) for s in all_sessions if s})

        for t in types:
            per_dpg[t] = {}
            for genre in all_genres:
                pred_tg = [
                    e
                    for e in predicted
                    if e["type"] == t
                    and e.get("session") is not None
                    and genre_lookup(e["session"]) == genre
                ]
                gt_tg = [
                    e
                    for e in ground_truth
                    if e["type"] == t
                    and e.get("session") is not None
                    and genre_lookup(e["session"]) == genre
                ]
                if pred_tg or gt_tg:
                    tp, fp, fn = _pair_within_tolerance(pred_tg, gt_tg, tolerance_s)
                    per_dpg[t][genre] = _cell(tp, fp, fn)
                else:
                    per_dpg[t][genre] = {
                        "tp": 0,
                        "fp": 0,
                        "fn": 0,
                        "precision": 0.0,
                        "recall": 0.0,
                        "f1": 0.0,
                    }
        out["per_detector_per_genre"] = per_dpg

    return out
