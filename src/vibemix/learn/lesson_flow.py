# SPDX-License-Identifier: Apache-2.0
"""Canonical structured lesson flows for Learn.

The transcript JSON fixtures are the authored copy source. This module
compiles those fixtures into a deterministic backstage teaching contract:
which step is active, which control is observable, how it is verified, and
which adaptive hints belong to the step.

The frontstage can remain simple because this structure is available behind
it. No generative text is produced here; prompt and hint copy still comes
from the fixtures.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from vibemix.learn.curriculum import CURRICULUM, LessonMeta, beginner_lesson_ids

_CC_DEFAULT_MIN_DELTA = 38
MAX_FRONTSTAGE_PROMPT_CHARS = 150
MAX_FRONTSTAGE_PROMPT_WORDS = 24
MAX_FRONTSTAGE_PROMPT_SENTENCES = 2
TONE_LOCKED_PROMPT_CONTRACT_EXEMPT_STEP_IDS = frozenset({"L1.01.beat.3"})
_FRONTSTAGE_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?")
_FRONTSTAGE_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_FRONTSTAGE_INLINE_LIST_RE = re.compile(r"(^|\s)(?:[-*]|\d+[.)])\s+")
_SCREEN_ONLY_CONTROLS = frozenset(
    {
        "headphone_cue",
        "lesson_continue",
        "master_vol",
    }
)

StepKind = Literal["practice", "exemplar_band", "recital_prompt"]
VerificationKind = Literal["button_press", "cc_delta"]
InputSurface = Literal["hardware", "screen"]
BackstageLens = Literal[
    "controller_state",
    "cue_section_lookahead",
    "debrief",
    "dj_profile",
    "evidence_registry",
    "live_audio",
    "library_exemplars",
    "prepared_pool",
    "library_suggestions",
    "session_state",
    "session_recording",
    "recital_observer",
    "recovery_drill",
]


@dataclass(frozen=True, slots=True)
class BackstageDrill:
    """One authored Course 3 recovery drill shape."""

    drill: str
    deck: str
    shape: str


@dataclass(frozen=True, slots=True)
class AdaptiveHint:
    """One deterministic hint attached to a lesson step."""

    strike: int
    text: str
    tts_marker: str
    citations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VerificationSpec:
    """Deterministic action verifier derived from an expected_action."""

    kind: VerificationKind
    control: str
    deck: str
    observable_control_ids: tuple[str, ...]
    input_surfaces: tuple[InputSurface, ...]
    direction: Literal["", "up", "down"] = ""
    min_delta: int = 0


@dataclass(frozen=True, slots=True)
class LessonStep:
    """One backstage practice step in a lesson flow."""

    step_id: str
    kind: StepKind
    prompt: str
    tts_marker: str
    citations: tuple[str, ...]
    expected_action: dict[str, Any]
    verification: VerificationSpec
    hints: tuple[AdaptiveHint, ...]
    backstage_lenses: tuple[BackstageLens, ...] = ()


@dataclass(frozen=True, slots=True)
class LessonFlow:
    """Compiled per-lesson step flow."""

    lesson_id: str
    course_id: str
    title: str
    primary_expected_action: dict[str, Any]
    steps: tuple[LessonStep, ...]
    backstage_lenses: tuple[BackstageLens, ...] = ()
    proactive_lens_active: bool = False
    exemplar_audio_forbidden: bool = False
    drill_shapes: tuple[BackstageDrill, ...] = ()


def observable_control_id(action: dict[str, Any]) -> str:
    """Return the UI/SVG control id for an expected action."""
    control = str(action.get("control", "")).strip()
    deck = str(action.get("deck", "") or "").strip()
    return f"{control}:{deck}" if deck else control


def input_surfaces_for_action(action: dict[str, Any]) -> tuple[InputSurface, ...]:
    """Return where Learn can honestly observe this action.

    Most curriculum controls can be attempted on hardware or on the rendered
    deck. A few are screen-only in vibemix today because the bundled controller
    profiles do not expose reliable MIDI for them, or because they are lesson UI
    controls rather than deck controls.
    """
    control = str(action.get("control", "")).strip()
    if control in _SCREEN_ONLY_CONTROLS:
        return ("screen",)
    return ("hardware", "screen")


def frontstage_prompt_metrics(prompt: str) -> dict[str, int | bool]:
    """Return deterministic UX metrics for one learner-facing prompt."""
    text = prompt.strip()
    sentence_count = len(
        [part for part in _FRONTSTAGE_SENTENCE_RE.split(text) if part.strip()]
    )
    if text and sentence_count == 0:
        sentence_count = 1
    single_line = "\n" not in text and "\r" not in text
    has_inline_list = bool(_FRONTSTAGE_INLINE_LIST_RE.search(text))
    word_count = len(_FRONTSTAGE_WORD_RE.findall(text))
    within_contract = (
        len(text) <= MAX_FRONTSTAGE_PROMPT_CHARS
        and word_count <= MAX_FRONTSTAGE_PROMPT_WORDS
        and sentence_count <= MAX_FRONTSTAGE_PROMPT_SENTENCES
        and single_line
        and not has_inline_list
    )
    return {
        "chars": len(text),
        "words": word_count,
        "sentences": sentence_count,
        "single_line": single_line,
        "has_inline_list": has_inline_list,
        "within_contract": within_contract,
    }


def frontstage_prompt_contract_exempt(step_id: str) -> bool:
    """Return true for verbatim-locked dialog that is not a practice prompt."""
    return step_id in TONE_LOCKED_PROMPT_CONTRACT_EXEMPT_STEP_IDS


def verification_for_action(action: dict[str, Any]) -> VerificationSpec:
    """Compile an expected_action into a deterministic verifier spec."""
    action_type = action.get("type")
    control = str(action.get("control", "")).strip()
    deck = str(action.get("deck", "") or "").strip()
    control_id = observable_control_id(action)
    input_surfaces = input_surfaces_for_action(action)
    if action_type == "button":
        direction = str(action.get("direction", "down") or "down")
        if direction not in {"", "up", "down"}:
            direction = "down"
        return VerificationSpec(
            kind="button_press",
            control=control,
            deck=deck,
            observable_control_ids=(control_id,),
            input_surfaces=input_surfaces,
            direction=direction,  # type: ignore[arg-type]
            min_delta=0,
        )
    return VerificationSpec(
        kind="cc_delta",
        control=control,
        deck=deck,
        observable_control_ids=(control_id,),
        input_surfaces=input_surfaces,
        direction="",
        min_delta=int(action.get("min_delta", _CC_DEFAULT_MIN_DELTA)),
    )


def primary_expected_action(lesson_id: str) -> dict[str, Any]:
    """Return the fixture-level action the outer lesson FSM expects."""
    meta = CURRICULUM[lesson_id]
    return primary_expected_action_from_script(lesson_id, meta.script)


def primary_expected_action_from_script(
    lesson_id: str,
    script: dict[str, Any],
) -> dict[str, Any]:
    """Return the fixture-level expected action from an already-loaded script."""
    expected = script.get("expected_action")
    if not isinstance(expected, dict):
        raise ValueError(f"{lesson_id}: expected_action missing or non-dict")
    return dict(expected)


def build_lesson_flow(lesson_id: str) -> LessonFlow:
    """Compile one canonical lesson flow from the authored fixture."""
    if lesson_id not in CURRICULUM:
        raise KeyError(lesson_id)
    meta = CURRICULUM[lesson_id]
    return build_lesson_flow_from_meta(lesson_id, meta, meta.script)


def build_lesson_flow_from_meta(
    lesson_id: str,
    meta: LessonMeta,
    script: dict[str, Any],
) -> LessonFlow:
    """Compile one lesson flow from supplied metadata and script data.

    ``build_lesson_flow`` is the production path and still reads from the
    canonical curriculum table. This lower-level helper lets course-pack
    preflight validate future course drafts before they are merged into
    :data:`CURRICULUM` or written to ``transcripts/``.
    """
    hints = _compile_hints(script)
    primary = primary_expected_action_from_script(lesson_id, script)

    if isinstance(script.get("exemplar_cycle"), list):
        steps = _compile_exemplar_steps(lesson_id, script, hints)
    elif isinstance(script.get("recital_pool"), list):
        steps = _compile_recital_steps(lesson_id, script, hints)
    else:
        steps = _compile_single_practice_steps(lesson_id, script, primary, hints)

    if not steps:
        raise ValueError(f"{lesson_id}: compiled lesson flow is empty")
    backstage_lenses = _compile_backstage_lenses(meta.course_id, lesson_id, script, steps)
    steps = tuple(
        _with_backstage_lenses(step, backstage_lenses)
        for step in steps
    )
    return LessonFlow(
        lesson_id=lesson_id,
        course_id=meta.course_id,
        title=meta.title,
        primary_expected_action=primary,
        steps=steps,
        backstage_lenses=backstage_lenses,
        proactive_lens_active=bool(script.get("proactive_lens_active", False)),
        exemplar_audio_forbidden=bool(script.get("exemplar_audio_forbidden", False)),
        drill_shapes=_compile_drill_shapes(script),
    )


def build_all_beginner_flows() -> tuple[LessonFlow, ...]:
    """Compile the 36 beginner lessons, excluding the legacy L0 smoke demo."""
    return tuple(
        build_lesson_flow(lesson_id)
        for lesson_id in beginner_lesson_ids()
    )


def _compile_hints(script: dict[str, Any]) -> tuple[AdaptiveHint, ...]:
    rows = script.get("hints") or []
    hints: list[AdaptiveHint] = []
    if not isinstance(rows, list):
        return ()
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        hints.append(
            AdaptiveHint(
                strike=idx,
                text=str(row.get("text", "")).strip(),
                tts_marker=str(row.get("tts_marker", "")).strip(),
                citations=tuple(str(c) for c in row.get("citations", ())),
            )
        )
    return tuple(hints)


def _first_tutor_line(script: dict[str, Any], fallback: str) -> str:
    rows = script.get("tutor_speak") or []
    if isinstance(rows, list) and rows:
        first = rows[0]
        if isinstance(first, dict):
            text = str(first.get("text", "")).strip()
            if text:
                return text
    return fallback


def _last_tutor_row(script: dict[str, Any]) -> dict[str, Any] | None:
    rows = script.get("tutor_speak") or []
    if not isinstance(rows, list):
        return None
    for row in reversed(rows):
        if isinstance(row, dict) and str(row.get("text", "")).strip():
            return row
    return None


def _row_citations(row: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(c) for c in row.get("citations", ()))


def _compile_single_practice_steps(
    lesson_id: str,
    script: dict[str, Any],
    expected: dict[str, Any],
    hints: tuple[AdaptiveHint, ...],
) -> tuple[LessonStep, ...]:
    tutor_rows = script.get("tutor_speak") or []
    if expected.get("control") == "lesson_continue" and isinstance(tutor_rows, list):
        steps: list[LessonStep] = []
        for idx, row in enumerate(tutor_rows):
            if not isinstance(row, dict):
                continue
            prompt = str(row.get("text", "")).strip()
            if not prompt:
                continue
            steps.append(
                LessonStep(
                    step_id=f"{lesson_id}.beat.{idx}",
                    kind="practice",
                    prompt=prompt,
                    tts_marker=str(row.get("tts_marker", "")).strip()
                    or f"{lesson_id}.beat.{idx}",
                    citations=_row_citations(row),
                    expected_action=dict(expected),
                    verification=verification_for_action(expected),
                    hints=hints,
                    backstage_lenses=(),
                )
            )
        if steps:
            return tuple(steps)

    last_row = _last_tutor_row(script) or {}
    return (
        LessonStep(
            step_id=f"{lesson_id}.practice",
            kind="practice",
            prompt=str(last_row.get("text", "")).strip()
            or _first_tutor_line(script, lesson_id),
            tts_marker=str(last_row.get("tts_marker", "")).strip()
            or f"{lesson_id}.practice",
            citations=_row_citations(last_row),
            expected_action=dict(expected),
            verification=verification_for_action(expected),
            hints=hints,
            backstage_lenses=(),
        ),
    )


def _compile_exemplar_steps(
    lesson_id: str,
    script: dict[str, Any],
    hints: tuple[AdaptiveHint, ...],
) -> tuple[LessonStep, ...]:
    steps: list[LessonStep] = []
    for idx, row in enumerate(script.get("exemplar_cycle") or [], start=1):
        if not isinstance(row, dict):
            continue
        expected = row.get("expected_action")
        if not isinstance(expected, dict):
            continue
        band = str(row.get("band", idx)).strip() or str(idx)
        prompt = str(row.get("tutor_speak", "")).strip() or _first_tutor_line(
            script,
            lesson_id,
        )
        steps.append(
            LessonStep(
                step_id=f"{lesson_id}.band.{band}",
                kind="exemplar_band",
                prompt=prompt,
                tts_marker=f"{lesson_id}.band.{band}",
                citations=tuple(str(c) for c in row.get("citations", ())),
                expected_action=dict(expected),
                verification=verification_for_action(expected),
                hints=hints,
                backstage_lenses=(),
            )
        )
    return tuple(steps)


def _compile_recital_steps(
    lesson_id: str,
    script: dict[str, Any],
    hints: tuple[AdaptiveHint, ...],
) -> tuple[LessonStep, ...]:
    steps: list[LessonStep] = []
    for idx, row in enumerate(script.get("recital_pool") or [], start=1):
        if not isinstance(row, dict):
            continue
        expected = row.get("expected_action")
        if not isinstance(expected, dict):
            continue
        steps.append(
            LessonStep(
                step_id=f"{lesson_id}.recital.{idx:02d}",
                kind="recital_prompt",
                prompt=str(row.get("prompt", "")).strip(),
                tts_marker=f"{lesson_id}.recital.{idx:02d}",
                citations=(),
                expected_action=dict(expected),
                verification=verification_for_action(expected),
                hints=hints,
                backstage_lenses=(),
            )
        )
    return tuple(steps)


def _unique_lenses(rows: list[BackstageLens]) -> tuple[BackstageLens, ...]:
    seen: set[BackstageLens] = set()
    ordered: list[BackstageLens] = []
    for row in rows:
        if row in seen:
            continue
        seen.add(row)
        ordered.append(row)
    return tuple(ordered)


def _compile_backstage_lenses(
    course_id: str,
    lesson_id: str,
    script: dict[str, Any],
    steps: tuple[LessonStep, ...],
) -> tuple[BackstageLens, ...]:
    """Compile the non-visual systems that make a flow observable.

    The UI can show a single prompt and a single action, but Course 3 still
    needs explicit backstage proof of the live systems it depends on.
    """
    lenses: list[BackstageLens] = ["evidence_registry"]
    if any("hardware" in step.verification.input_surfaces for step in steps):
        lenses.append("controller_state")
    if isinstance(script.get("exemplar_cycle"), list):
        lenses.append("library_exemplars")
    if isinstance(script.get("recital_pool"), list):
        lenses.append("recital_observer")

    if course_id == "course_3_play_mode":
        if bool(script.get("proactive_lens_active", False)):
            lenses.extend(
                [
                    "live_audio",
                    "cue_section_lookahead",
                    "library_suggestions",
                    "session_state",
                ]
            )
        if lesson_id == "L3.02":
            lenses.append("prepared_pool")
        if lesson_id == "L3.04":
            lenses.extend(["session_recording", "debrief"])
        if isinstance(script.get("drill_shapes"), list):
            lenses.append("recovery_drill")
        if lesson_id == "L3.06":
            lenses.extend(["debrief", "dj_profile"])

    return _unique_lenses(lenses)


def _compile_drill_shapes(script: dict[str, Any]) -> tuple[BackstageDrill, ...]:
    rows = script.get("drill_shapes") or []
    if not isinstance(rows, list):
        return ()
    drills: list[BackstageDrill] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        drill = str(row.get("drill", "")).strip()
        deck = str(row.get("deck", "")).strip()
        shape = str(row.get("shape", "")).strip()
        if not drill or not shape:
            continue
        drills.append(BackstageDrill(drill=drill, deck=deck, shape=shape))
    return tuple(drills)


def _with_backstage_lenses(
    step: LessonStep,
    lenses: tuple[BackstageLens, ...],
) -> LessonStep:
    return LessonStep(
        step_id=step.step_id,
        kind=step.kind,
        prompt=step.prompt,
        tts_marker=step.tts_marker,
        citations=step.citations,
        expected_action=step.expected_action,
        verification=step.verification,
        hints=step.hints,
        backstage_lenses=lenses,
    )


__all__ = [
    "MAX_FRONTSTAGE_PROMPT_CHARS",
    "MAX_FRONTSTAGE_PROMPT_SENTENCES",
    "MAX_FRONTSTAGE_PROMPT_WORDS",
    "TONE_LOCKED_PROMPT_CONTRACT_EXEMPT_STEP_IDS",
    "AdaptiveHint",
    "BackstageDrill",
    "BackstageLens",
    "LessonFlow",
    "LessonStep",
    "VerificationSpec",
    "build_all_beginner_flows",
    "build_lesson_flow",
    "build_lesson_flow_from_meta",
    "frontstage_prompt_contract_exempt",
    "frontstage_prompt_metrics",
    "input_surfaces_for_action",
    "observable_control_id",
    "primary_expected_action",
    "primary_expected_action_from_script",
    "verification_for_action",
]
