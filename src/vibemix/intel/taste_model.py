# SPDX-License-Identifier: Apache-2.0
"""Deterministic taste aggregates from structured feedback events."""

from __future__ import annotations

from dataclasses import dataclass

from vibemix.intel.feedback import FeedbackEvent
from vibemix.intel.musical_ontology import clamp01, normalize_role

TASTE_MODEL_VERSION = "taste_model_v1"
MIN_EVENTS_FOR_ANY_TASTE = 10
MIN_POSITIVE_PAIR_EVENTS = 3
MIN_NEGATIVE_PAIR_EVENTS = 2
MIN_SESSIONS_FOR_HARD_NEGATIVE = 2
MAX_ABS_ROLE_PAIR_WEIGHT = 0.18

TASTE_LABEL_WEIGHTS: dict[str, float] = {
    "would_play": 1.00,
    "maybe": 0.35,
    "no": -1.00,
    "vibe_no": -0.70,
    "played_next": 0.65,
    "accepted": 1.00,
    "rejected": -0.70,
    "ignored_timeout": -0.20,
    "different_track": -0.30,
    "cue_kept": 0.35,
    "cue_edited": -0.45,
}

TECHNICAL_LABELS: frozenset[str] = frozenset({"technical_no", "timing_no", "wrong_timing"})


@dataclass(frozen=True, slots=True)
class TasteConstraint:
    role_pair: tuple[str, str]
    reason: str
    support_event_count: int
    session_count: int


@dataclass(frozen=True, slots=True)
class TasteModel:
    version: str
    event_count: int
    taste_event_count: int
    role_pair_weights: dict[tuple[str, str], float]
    risk_flag_penalties: dict[str, float]
    negative_constraints: tuple[TasteConstraint, ...]

    def taste_score_for(self, role_pair: tuple[str, str] | None) -> float:
        if role_pair is None:
            return 0.50
        normalized = (normalize_role(role_pair[0]), normalize_role(role_pair[1]))
        return clamp01(0.50 + self.role_pair_weights.get(normalized, 0.0))

    def taste_scores(self) -> dict[tuple[str, str], float]:
        return {role_pair: self.taste_score_for(role_pair) for role_pair in self.role_pair_weights}


def build_taste_model(events: tuple[FeedbackEvent, ...]) -> TasteModel:
    taste_events = tuple(event for event in events if _taste_weight(event) is not None)
    if len(taste_events) < MIN_EVENTS_FOR_ANY_TASTE:
        return TasteModel(
            version=TASTE_MODEL_VERSION,
            event_count=len(events),
            taste_event_count=len(taste_events),
            role_pair_weights={},
            risk_flag_penalties=_risk_penalties(events),
            negative_constraints=(),
        )

    by_pair: dict[tuple[str, str], list[FeedbackEvent]] = {}
    for event in taste_events:
        pair = _role_pair(event)
        if pair is not None:
            by_pair.setdefault(pair, []).append(event)

    weights: dict[tuple[str, str], float] = {}
    constraints: list[TasteConstraint] = []
    for pair, rows in sorted(by_pair.items()):
        sessions = {row.session_id for row in rows}
        positives = sum(1 for row in rows if (_taste_weight(row) or 0.0) > 0)
        negatives = sum(1 for row in rows if (_taste_weight(row) or 0.0) < 0)
        if len(sessions) < 2:
            continue
        if positives < MIN_POSITIVE_PAIR_EVENTS and negatives < MIN_NEGATIVE_PAIR_EVENTS:
            continue
        net = sum(_taste_weight(row) or 0.0 for row in rows)
        total_abs = sum(abs(_taste_weight(row) or 0.0) for row in rows)
        if total_abs <= 0:
            continue
        weight = round(
            max(
                -MAX_ABS_ROLE_PAIR_WEIGHT,
                min(MAX_ABS_ROLE_PAIR_WEIGHT, net / total_abs * MAX_ABS_ROLE_PAIR_WEIGHT),
            ),
            6,
        )
        if weight:
            weights[pair] = weight
        if (
            negatives >= MIN_NEGATIVE_PAIR_EVENTS
            and len(sessions) >= MIN_SESSIONS_FOR_HARD_NEGATIVE
        ):
            constraints.append(
                TasteConstraint(
                    role_pair=pair,
                    reason="repeated_negative_transition_feedback",
                    support_event_count=negatives,
                    session_count=len(sessions),
                )
            )

    return TasteModel(
        version=TASTE_MODEL_VERSION,
        event_count=len(events),
        taste_event_count=len(taste_events),
        role_pair_weights=weights,
        risk_flag_penalties=_risk_penalties(events),
        negative_constraints=tuple(constraints),
    )


def _risk_penalties(events: tuple[FeedbackEvent, ...]) -> dict[str, float]:
    by_flag: dict[str, set[str]] = {}
    for event in events:
        if event.label not in TECHNICAL_LABELS and event.label not in {"no", "vibe_no"}:
            continue
        for flag in event.risk_flags:
            by_flag.setdefault(flag, set()).add(event.session_id)
    return {
        flag: round(-min(0.15, 0.04 * len(sessions)), 6)
        for flag, sessions in sorted(by_flag.items())
        if len(sessions) >= 2
    }


def _taste_weight(event: FeedbackEvent) -> float | None:
    if event.label is None or event.label in TECHNICAL_LABELS:
        return None
    weight = TASTE_LABEL_WEIGHTS.get(event.label)
    if weight is None:
        return None
    return weight * (0.55 if event.inferred else 1.0)


def _role_pair(event: FeedbackEvent) -> tuple[str, str] | None:
    if event.role_pair is None:
        return None
    return (normalize_role(event.role_pair[0]), normalize_role(event.role_pair[1]))


__all__ = [
    "MAX_ABS_ROLE_PAIR_WEIGHT",
    "MIN_EVENTS_FOR_ANY_TASTE",
    "MIN_NEGATIVE_PAIR_EVENTS",
    "MIN_POSITIVE_PAIR_EVENTS",
    "MIN_SESSIONS_FOR_HARD_NEGATIVE",
    "TASTE_MODEL_VERSION",
    "TasteConstraint",
    "TasteModel",
    "build_taste_model",
]
