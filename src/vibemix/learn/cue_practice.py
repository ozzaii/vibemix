# SPDX-License-Identifier: Apache-2.0
"""Owned-deck cue placement practice producer.

The cue placement judge is an offline timing primitive. This module turns that
measured grade into the same cited Learn-progress shape as beatmatch practice:
only an owned-deck, beat-locked cue writes a receipt and asks the recognizer for
credit. Nothing here speaks, touches MusicState, or infers from live audio.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from vibemix.audio.grid import BeatGrid
from vibemix.learn.cue_placement_judge import CuePlacementGrade, grade_cue_placement
from vibemix.learn.skill_recognizer import recognize

CUE_PLACEMENT_GRADED_EVENT = "CUE_PLACEMENT_GRADED"
CUE_PLACEMENT_EVIDENCE_SOURCE = "ev"


class EvidenceRegistryLike(Protocol):
    """The minimal EvidenceRegistry surface this producer needs."""

    def write(self, source: str, key: str, t_session: float) -> None: ...

    def has(self, source: str, key: str, t_target: float, tol: float = 1.0) -> bool: ...


@dataclass(frozen=True)
class CuePlacementPracticeEvent:
    """Small event object with the shape ``skill_recognizer`` consumes."""

    extra: dict[str, object]
    type: str = CUE_PLACEMENT_GRADED_EVENT


@dataclass(frozen=True)
class CuePlacementPracticeResult:
    """One evaluation tick from the owned-deck cue-placement practice loop."""

    grade: CuePlacementGrade
    event: CuePlacementPracticeEvent | None
    credited: tuple[str, ...]
    t_session: float


def cue_grade_to_event_extra(grade: CuePlacementGrade) -> dict[str, object]:
    """Return a JSON-safe event payload for the measured cue-placement grade."""

    return {
        "cue_frame": round(float(grade.cue_frame), 3),
        "nearest_beat_frame": round(float(grade.nearest_beat_frame), 3),
        "beat_error_beats": round(float(grade.beat_error_beats), 6),
        "beat_aligned": bool(grade.beat_aligned),
        "target_error_beats": (
            None
            if grade.target_error_beats is None
            else round(float(grade.target_error_beats), 6)
        ),
        "target_aligned": grade.target_aligned,
        "verdict": grade.verdict,
        "score": float(grade.score),
    }


def is_creditable_cue_placement_grade(grade: CuePlacementGrade) -> bool:
    """Return True only for cue placements that prove phrase/timing discipline."""

    if not grade.beat_aligned:
        return False
    if grade.target_aligned is False:
        return False
    return grade.verdict in {"beat_locked", "drop_locked"}


def grade_owned_cue_placement_state(
    grid: BeatGrid,
    cue_frame: float,
    *,
    target_frame: float | None = None,
) -> CuePlacementGrade:
    """Measure cue placement without writing credit evidence."""

    return grade_cue_placement(grid, cue_frame, target_frame=target_frame)


def grade_owned_cue_placement_attempt(
    grid: BeatGrid,
    cue_frame: float,
    *,
    target_frame: float | None = None,
    evidence_registry: EvidenceRegistryLike,
    t_session: float,
    progress: Any | None = None,
    now: str | None = None,
    seen: set[tuple[str, float]] | None = None,
    citation_tolerance_s: float = 1.0,
) -> CuePlacementPracticeResult:
    """Grade an owned cue and emit/credit only a citable beat/drop-locked cue."""

    t = float(t_session)
    grade = grade_owned_cue_placement_state(grid, cue_frame, target_frame=target_frame)
    if not is_creditable_cue_placement_grade(grade):
        return CuePlacementPracticeResult(grade=grade, event=None, credited=(), t_session=t)

    event = CuePlacementPracticeEvent(extra=cue_grade_to_event_extra(grade))
    evidence_registry.write(CUE_PLACEMENT_EVIDENCE_SOURCE, CUE_PLACEMENT_GRADED_EVENT, t)

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

    return CuePlacementPracticeResult(grade=grade, event=event, credited=credited, t_session=t)


__all__ = [
    "CUE_PLACEMENT_EVIDENCE_SOURCE",
    "CUE_PLACEMENT_GRADED_EVENT",
    "CuePlacementPracticeEvent",
    "CuePlacementPracticeResult",
    "cue_grade_to_event_extra",
    "grade_owned_cue_placement_attempt",
    "grade_owned_cue_placement_state",
    "is_creditable_cue_placement_grade",
]
