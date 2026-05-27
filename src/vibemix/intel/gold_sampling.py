# SPDX-License-Identifier: Apache-2.0
"""Small stratified-active sampler for INTEL-15 review queues."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GoldSampleItem:
    review_item_id: str
    sample_reason: str
    candidate_id: str
    payload: dict[str, Any]


def sample_transition_candidates(
    candidates: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    n: int,
    threshold: float = 0.62,
) -> tuple[GoldSampleItem, ...]:
    """Select a review pool that is useful, not merely flattering."""
    if n <= 0:
        return ()
    remaining = [dict(candidate) for candidate in candidates if candidate.get("candidate_id")]
    selected: list[tuple[str, dict[str, Any]]] = []

    strategies = (
        ("top_scorer", lambda row: -_float(row.get("score"), 0.0)),
        ("near_threshold", lambda row: abs(_float(row.get("score"), 0.0) - threshold)),
        ("high_score_high_risk", _high_risk_sort_key),
        ("low_confidence_or_negative", _low_confidence_sort_key),
        ("coverage_candidate_id", lambda row: str(row.get("candidate_id"))),
    )
    for reason, key_fn in strategies:
        for row in sorted(remaining, key=key_fn):
            if _already_selected(row, selected):
                continue
            selected.append((reason, row))
            if len(selected) >= n:
                return _to_items(selected)
            break
    for row in sorted(remaining, key=lambda item: str(item.get("candidate_id"))):
        if _already_selected(row, selected):
            continue
        selected.append(("coverage_candidate_id", row))
        if len(selected) >= n:
            break
    return _to_items(selected)


def _to_items(selected: list[tuple[str, dict[str, Any]]]) -> tuple[GoldSampleItem, ...]:
    return tuple(
        GoldSampleItem(
            review_item_id=f"rev_{index:03d}",
            sample_reason=reason,
            candidate_id=str(row["candidate_id"]),
            payload=row,
        )
        for index, (reason, row) in enumerate(selected, start=1)
    )


def _already_selected(row: dict[str, Any], selected: list[tuple[str, dict[str, Any]]]) -> bool:
    candidate_id = str(row.get("candidate_id"))
    return any(candidate_id == str(existing.get("candidate_id")) for _, existing in selected)


def _high_risk_sort_key(row: dict[str, Any]) -> tuple[float, float, str]:
    risk_count = len(row.get("risk_flags") or [])
    score = _float(row.get("score"), 0.0)
    return (-score if risk_count else 1.0, -risk_count, str(row.get("candidate_id")))


def _low_confidence_sort_key(row: dict[str, Any]) -> tuple[float, float, str]:
    confidence = _float(row.get("confidence"), 1.0)
    score = _float(row.get("score"), 1.0)
    return (confidence, score, str(row.get("candidate_id")))


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


__all__ = ["GoldSampleItem", "sample_transition_candidates"]
