# SPDX-License-Identifier: Apache-2.0
"""Pure backstage teaching-loop records for Learn.

The frontstage remains one prompt and one action. This module makes the
backstage loop explicit and testable without introducing runtime generation:
observe the active structured step, decide the tutor route, teach the authored
line, verify with deterministic metadata, and adapt with grounded hints.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from vibemix.learn.lesson_flow import LessonStep, VerificationSpec
from vibemix.llm.model_router import resolve

TEACHING_LOOP_STAGES: tuple[str, ...] = (
    "observe",
    "decide",
    "teach",
    "verify",
    "adapt",
)
LEARN_TUTOR_ROUTE = "learn_tutor"

TurnKind = Literal["teach", "hint", "adapt"]


@dataclass(frozen=True, slots=True)
class TutorRoute:
    """Resolved tutor model route for this teaching turn."""

    path: str
    model_id: str
    service_tier: str | None


@dataclass(frozen=True, slots=True)
class TeachingObservation:
    """The observable step facts the tutor is allowed to reason from."""

    lesson_id: str
    step_id: str
    kind: str
    control_id: str
    input_surfaces: tuple[str, ...]
    backstage_lenses: tuple[str, ...]
    strikes_used: int


@dataclass(frozen=True, slots=True)
class TeachingTurn:
    """A complete observe -> decide -> teach -> verify -> adapt turn."""

    loop: tuple[str, ...]
    turn_kind: TurnKind
    route: TutorRoute
    observation: TeachingObservation
    text: str
    tts_marker: str
    citations: tuple[str, ...]
    verification: VerificationSpec


def resolve_tutor_route() -> TutorRoute:
    """Resolve the Learn tutor path through the shared model router."""
    model_id, tier = resolve(LEARN_TUTOR_ROUTE)
    tier_name = getattr(tier, "name", None) if tier is not None else None
    if tier_name is None and tier is not None:
        tier_name = str(tier)
    return TutorRoute(
        path=LEARN_TUTOR_ROUTE,
        model_id=model_id,
        service_tier=tier_name,
    )


def plan_teaching_turn(
    *,
    lesson_id: str,
    step: LessonStep,
    strikes_used: int = 0,
) -> TeachingTurn:
    """Build the normal authored teaching turn for a structured step."""
    return _turn(
        lesson_id=lesson_id,
        step=step,
        turn_kind="teach",
        text=step.prompt,
        tts_marker=step.tts_marker,
        citations=_citations_or_step_ground(step.citations, step),
        strikes_used=strikes_used,
    )


def plan_hint_turn(
    *,
    lesson_id: str,
    step: LessonStep,
    strike: int,
) -> TeachingTurn | None:
    """Build the authored timed-hint turn for a structured step."""
    for hint in step.hints:
        if hint.strike == strike:
            return _turn(
                lesson_id=lesson_id,
                step=step,
                turn_kind="hint",
                text=hint.text,
                tts_marker=hint.tts_marker,
                citations=_citations_or_step_ground(hint.citations, step),
                strikes_used=strike,
            )
    return None


def plan_adaptive_turn(
    *,
    lesson_id: str,
    step: LessonStep,
    text: str,
    tts_marker: str,
    citations: tuple[str, ...],
    strikes_used: int,
) -> TeachingTurn:
    """Build a grounded adaptive turn after a specific observed mismatch."""
    return _turn(
        lesson_id=lesson_id,
        step=step,
        turn_kind="adapt",
        text=text,
        tts_marker=tts_marker,
        citations=citations,
        strikes_used=strikes_used,
    )


def teaching_turn_is_grounded(turn: TeachingTurn) -> bool:
    """Return whether a tutor turn is backed by deterministic step evidence."""
    observation = turn.observation
    verification = turn.verification
    if turn.loop != TEACHING_LOOP_STAGES:
        return False
    if turn.route.path != LEARN_TUTOR_ROUTE or not turn.route.model_id.strip():
        return False
    if not turn.text.strip() or not turn.tts_marker.strip():
        return False
    if not observation.lesson_id.strip() or not observation.step_id.strip():
        return False
    if not verification.observable_control_ids or not verification.input_surfaces:
        return False
    if observation.control_id not in verification.observable_control_ids:
        return False
    expected_surfaces = tuple(str(surface) for surface in verification.input_surfaces)
    if observation.input_surfaces != expected_surfaces:
        return False
    if "evidence_registry" not in observation.backstage_lenses:
        return False
    return 0 <= observation.strikes_used <= 3


def step_grounding_citations(step: LessonStep) -> tuple[str, ...]:
    """Return deterministic screen citations for the step's highlighted control."""
    verification = step.verification
    if "screen" not in verification.input_surfaces:
        return ()
    citations: list[str] = []
    for control_id in verification.observable_control_ids:
        if not _citation_body_is_safe(control_id):
            continue
        citation = f"[screen:{control_id}]"
        if citation not in citations:
            citations.append(citation)
        if len(citations) >= 4:
            break
    return tuple(citations)


def _citations_or_step_ground(
    citations: tuple[str, ...],
    step: LessonStep,
) -> tuple[str, ...]:
    return citations or step_grounding_citations(step)


def _citation_body_is_safe(value: str) -> bool:
    return bool(value) and not any(ch.isspace() or ch in ",]" for ch in value)


def _turn(
    *,
    lesson_id: str,
    step: LessonStep,
    turn_kind: TurnKind,
    text: str,
    tts_marker: str,
    citations: tuple[str, ...],
    strikes_used: int,
) -> TeachingTurn:
    verification = step.verification
    control_id = verification.observable_control_ids[0]
    return TeachingTurn(
        loop=TEACHING_LOOP_STAGES,
        turn_kind=turn_kind,
        route=resolve_tutor_route(),
        observation=TeachingObservation(
            lesson_id=lesson_id,
            step_id=step.step_id,
            kind=step.kind,
            control_id=control_id,
            input_surfaces=tuple(str(surface) for surface in verification.input_surfaces),
            backstage_lenses=tuple(str(lens) for lens in step.backstage_lenses),
            strikes_used=max(0, min(3, int(strikes_used))),
        ),
        text=text,
        tts_marker=tts_marker,
        citations=citations,
        verification=verification,
    )


__all__ = [
    "LEARN_TUTOR_ROUTE",
    "TEACHING_LOOP_STAGES",
    "TeachingObservation",
    "TeachingTurn",
    "TutorRoute",
    "plan_adaptive_turn",
    "plan_hint_turn",
    "plan_teaching_turn",
    "resolve_tutor_route",
    "step_grounding_citations",
    "teaching_turn_is_grounded",
]
