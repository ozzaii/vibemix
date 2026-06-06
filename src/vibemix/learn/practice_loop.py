# SPDX-License-Identifier: Apache-2.0
"""Owned-deck beatmatch practice producer.

This is the production source for the ``BEATMATCH_GRADED`` event the Learn
skill recognizer was waiting for. It only credits a measured LOCKED grade from
owned decks: both tempo and phase must match, and stopped/abstain states emit
nothing creditable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from vibemix.audio.grid import BeatGrid
from vibemix.audio.miniplayer import DeckState, MiniDeck
from vibemix.learn.beatmatch_judge import (
    BeatmatchGrade,
    grade_beatmatch,
    grade_to_event_extra,
)
from vibemix.learn.skill_recognizer import recognize

BEATMATCH_GRADED_EVENT = "BEATMATCH_GRADED"
BEATMATCH_EVIDENCE_SOURCE = "ev"


class EvidenceRegistryLike(Protocol):
    """The minimal EvidenceRegistry surface this producer needs."""

    def write(self, source: str, key: str, t_session: float) -> None: ...

    def has(self, source: str, key: str, t_target: float, tol: float = 1.0) -> bool: ...


@dataclass(frozen=True)
class BeatmatchPracticeEvent:
    """Small event object with the shape ``skill_recognizer`` consumes."""

    extra: dict[str, object]
    type: str = BEATMATCH_GRADED_EVENT


@dataclass(frozen=True)
class BeatmatchPracticeResult:
    """One evaluation tick from the owned-deck beatmatch practice loop."""

    grade: BeatmatchGrade
    event: BeatmatchPracticeEvent | None
    credited: tuple[str, ...]
    t_session: float
    save_landed: bool = False
    save_from_verdict: str | None = None
    save_from_phase_error_beats: float | None = None
    save_recovery_delta_beats: float | None = None
    save_attempt_active: bool = False
    save_floor_seconds_total: float | None = None
    save_floor_seconds_remaining: float | None = None
    save_floor_expired: bool = False
    save_difficulty_level: int = 1
    save_streak: int = 0
    practice_source: str | None = None
    deck_a_track_id: str | None = None
    deck_b_track_id: str | None = None
    deck_a_title: str | None = None
    deck_b_title: str | None = None


def grade_owned_beatmatch_attempt(
    grid_a: BeatGrid,
    grid_b: BeatGrid,
    state: DeckState,
    *,
    evidence_registry: EvidenceRegistryLike,
    t_session: float,
    progress: Any | None = None,
    now: str | None = None,
    seen: set[tuple[str, float]] | None = None,
    citation_tolerance_s: float = 1.0,
) -> BeatmatchPracticeResult:
    """Grade an owned-deck attempt and emit/credit only a citable LOCKED grade.

    ``evidence_registry.write("ev", "BEATMATCH_GRADED", t_session)`` happens
    before the recognizer is called, so the Mastered-credit path resolves through
    the same citation gate as every other live skill. Drift, trainwreck,
    tempo-off, and abstain grades return the measured grade but no creditable
    event.
    """

    t = float(t_session)
    grade = grade_owned_beatmatch_state(grid_a, grid_b, state)
    if not is_creditable_locked_grade(grade):
        return BeatmatchPracticeResult(grade=grade, event=None, credited=(), t_session=t)

    event = BeatmatchPracticeEvent(extra=grade_to_event_extra(grade))
    evidence_registry.write(BEATMATCH_EVIDENCE_SOURCE, BEATMATCH_GRADED_EVENT, t)

    credited: tuple[str, ...] = ()
    if progress is not None and now is not None:
        def citation_check(source: str, key: str, t_target: float) -> bool:
            return evidence_registry.has(source, key, t_target, tol=citation_tolerance_s)

        credited = tuple(
            recognize(
                event,
                citation_check=citation_check,
                progress=progress,
                now=now,
                event_t=t,
                _seen=seen,
            )
        )

    return BeatmatchPracticeResult(grade=grade, event=event, credited=credited, t_session=t)


def grade_owned_beatmatch_state(
    grid_a: BeatGrid,
    grid_b: BeatGrid,
    state: DeckState,
) -> BeatmatchGrade:
    """Measure the owned-deck beatmatch grade without writing credit evidence."""

    return grade_beatmatch(grid_a, grid_b, state)


def is_creditable_locked_grade(grade: BeatmatchGrade) -> bool:
    """Return True only for the measured LOCKED grade that may earn credit."""

    return bool(grade.tempo_matched and grade.phase_locked and not grade.abstain)


def grade_minideck_beatmatch_attempt(
    deck: MiniDeck,
    grid_a: BeatGrid,
    grid_b: BeatGrid,
    *,
    evidence_registry: EvidenceRegistryLike,
    t_session: float,
    progress: Any | None = None,
    now: str | None = None,
    seen: set[tuple[str, float]] | None = None,
    citation_tolerance_s: float = 1.0,
) -> BeatmatchPracticeResult:
    """Evaluate the current two-deck MiniDeck state."""

    return grade_owned_beatmatch_attempt(
        grid_a,
        grid_b,
        deck.state(),
        evidence_registry=evidence_registry,
        t_session=t_session,
        progress=progress,
        now=now,
        seen=seen,
        citation_tolerance_s=citation_tolerance_s,
    )


def _is_creditable_locked_grade(grade: BeatmatchGrade) -> bool:
    return is_creditable_locked_grade(grade)


__all__ = [
    "BEATMATCH_EVIDENCE_SOURCE",
    "BEATMATCH_GRADED_EVENT",
    "BeatmatchPracticeEvent",
    "BeatmatchPracticeResult",
    "grade_minideck_beatmatch_attempt",
    "grade_owned_beatmatch_attempt",
    "grade_owned_beatmatch_state",
    "is_creditable_locked_grade",
]
