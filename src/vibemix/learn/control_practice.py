# SPDX-License-Identifier: Apache-2.0
"""Learn-owned control practice receipts for Skill Wall credit.

This is deliberately smaller than the beatmatch/cue graders: the runtime has
already matched the lesson's expected action, so this module only classifies
which Learn skill that real control action demonstrates, writes a citable
``ev`` receipt, and lets ``skill_recognizer`` apply the existing Competent /
Mastered gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from vibemix.learn.skill_recognizer import CONTROL_PRACTICE_GRADED_EVENT, recognize

CONTROL_PRACTICE_EVIDENCE_SOURCE = "ev"

_EQ_MIXING_CONTROLS = frozenset({"eq_low", "eq_mid", "eq_hi", "filter"})
_DECK_CONTROL_CONTROLS = frozenset(
    {
        "cue",
        "headphone_cue",
        "jog",
        "jog_touch",
        "jog_touched",
        "loop_in",
        "loop_out",
        "master_vol",
        "play",
        "sync",
        "vol",
        "xfader",
    }
)


@dataclass(frozen=True, slots=True)
class ControlPracticeResult:
    """Outcome of one matched Learn control action."""

    event: Any | None
    credited: tuple[str, ...]
    t_session: float
    skill_id: str | None = None
    control: str = ""
    deck: str = ""


def classify_control_skill(control: str) -> str | None:
    """Return the Learn skill a matched control action demonstrates, if any."""

    head = str(control or "").split(":", 1)[0].strip()
    if head in _EQ_MIXING_CONTROLS:
        return "eq_mixing"
    if head in _DECK_CONTROL_CONTROLS:
        return "deck_control"
    return None


def grade_matched_control_practice(
    *,
    expected: dict[str, Any] | None,
    midi: dict[str, Any],
    evidence_registry: Any,
    t_session: float,
    progress: Any,
    now: str,
    lesson_id: str,
) -> ControlPracticeResult:
    """Write and recognize a grounded control-practice receipt.

    ``expected`` is optional because observer lessons own their own multi-step
    matcher. When supplied, this function refuses to write evidence unless the
    normalized control/deck line up with the MIDI payload. Delta and direction
    checks stay in ``LessonRuntime.action_matches`` / observer ``matches``.
    """

    control, deck = _control_and_deck(midi)
    expected_control = ""
    expected_deck = ""
    if expected is not None:
        expected_control, expected_deck = _control_and_deck(expected)
        if expected_control and control != expected_control:
            return ControlPracticeResult(
                event=None,
                credited=(),
                t_session=t_session,
                control=control,
                deck=deck,
            )
        if expected_deck and deck != expected_deck:
            return ControlPracticeResult(
                event=None,
                credited=(),
                t_session=t_session,
                control=control,
                deck=deck,
            )

    skill_id = classify_control_skill(control)
    if skill_id is None:
        return ControlPracticeResult(
            event=None,
            credited=(),
            t_session=t_session,
            control=control,
            deck=deck,
        )

    extra = {
        "lesson_id": lesson_id,
        "control": control,
        "deck": deck,
        "expected_control": expected_control,
        "expected_deck": expected_deck,
        "source": str(midi.get("source", "midi") or "midi"),
        "skill_id": skill_id,
        "matched": True,
    }
    event = SimpleNamespace(type=CONTROL_PRACTICE_GRADED_EVENT, extra=extra)
    evidence_registry.write(
        CONTROL_PRACTICE_EVIDENCE_SOURCE,
        CONTROL_PRACTICE_GRADED_EVENT,
        t_session,
    )
    credited = tuple(
        recognize(
            event,
            citation_check=lambda source, key, t: evidence_registry.has(
                source,
                key,
                t,
                tol=1.0,
            ),
            progress=progress,
            now=now,
            event_t=t_session,
        )
    )
    return ControlPracticeResult(
        event=event,
        credited=credited,
        t_session=t_session,
        skill_id=skill_id,
        control=control,
        deck=deck,
    )


def _control_and_deck(action: dict[str, Any]) -> tuple[str, str]:
    control = str(action.get("control", "")).strip()
    deck = str(action.get("deck", "") or "").strip()
    if not deck and ":" in control:
        control, _, parsed_deck = control.rpartition(":")
        deck = parsed_deck.strip()
    return control, deck
