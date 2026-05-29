# SPDX-License-Identifier: Apache-2.0
"""Backstage observe -> decide -> teach -> verify -> adapt contract."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from vibemix.learn.lesson_flow import build_all_beginner_flows, build_lesson_flow
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.learn.teaching_loop import (
    LEARN_TUTOR_ROUTE,
    TEACHING_LOOP_STAGES,
    plan_adaptive_turn,
    plan_hint_turn,
    plan_teaching_turn,
    resolve_tutor_route,
    step_grounding_citations,
    teaching_turn_is_grounded,
)
from vibemix.llm.model_router import resolve_model


def test_teaching_loop_resolves_learn_tutor_route() -> None:
    """The tutor route is decided through model_router, not a literal."""
    route = resolve_tutor_route()

    assert route.path == LEARN_TUTOR_ROUTE == "learn_tutor"
    assert route.model_id == resolve_model("learn_tutor")
    assert route.service_tier


def test_teaching_turn_observes_verifies_and_keeps_authored_copy() -> None:
    step = build_lesson_flow("L1.03").steps[0]

    turn = plan_teaching_turn(
        lesson_id="L1.03",
        step=step,
        strikes_used=0,
    )

    assert turn.loop == TEACHING_LOOP_STAGES
    assert turn.turn_kind == "teach"
    assert turn.text == step.prompt
    assert turn.tts_marker == step.tts_marker
    assert turn.observation.lesson_id == "L1.03"
    assert turn.observation.step_id == step.step_id
    assert turn.observation.control_id == "eq_hi:A"
    assert turn.observation.input_surfaces == ("hardware", "screen")
    assert turn.observation.backstage_lenses == (
        "evidence_registry",
        "controller_state",
    )
    assert turn.verification == step.verification
    assert turn.citations == ("[screen:eq_hi:A]",)


def test_step_grounding_citations_use_the_highlighted_screen_control() -> None:
    step = build_lesson_flow("L1.03").steps[0]

    assert step.citations == ()
    assert step_grounding_citations(step) == ("[screen:eq_hi:A]",)


def test_hint_and_adaptive_turns_share_the_same_verification_ground() -> None:
    step = build_lesson_flow("L1.03").steps[0]

    hint = plan_hint_turn(lesson_id="L1.03", step=step, strike=2)
    adaptive = plan_adaptive_turn(
        lesson_id="L1.03",
        step=step,
        text="move deck A high EQ farther.",
        tts_marker="L1.03.adapt.mismatch",
        citations=("[midi:eq_hi:A@12.0]", "[screen:eq_hi:A]"),
        strikes_used=2,
    )

    assert hint is not None
    assert hint.turn_kind == "hint"
    assert hint.observation.strikes_used == 2
    assert adaptive.turn_kind == "adapt"
    assert adaptive.observation.strikes_used == 2
    assert adaptive.citations == ("[midi:eq_hi:A@12.0]", "[screen:eq_hi:A]")
    assert adaptive.verification == hint.verification == step.verification


def test_all_36_beginner_steps_can_become_teaching_turns() -> None:
    turns = [
        plan_teaching_turn(lesson_id=flow.lesson_id, step=step)
        for flow in build_all_beginner_flows()
        for step in flow.steps
    ]

    assert len(turns) == 76
    assert {turn.route.path for turn in turns} == {"learn_tutor"}
    assert all(turn.text for turn in turns)
    assert all(teaching_turn_is_grounded(turn) for turn in turns)
    assert all(turn.citations for turn in turns)
    assert all(turn.verification.observable_control_ids for turn in turns)
    assert all("evidence_registry" in turn.observation.backstage_lenses for turn in turns)


def test_all_beginner_hint_turns_are_grounded_by_step_verifiers() -> None:
    hint_turn_count = 0

    for flow in build_all_beginner_flows():
        for step in flow.steps:
            for strike in (1, 2, 3):
                turn = plan_hint_turn(
                    lesson_id=flow.lesson_id,
                    step=step,
                    strike=strike,
                )

                assert turn is not None, (flow.lesson_id, step.step_id, strike)
                assert teaching_turn_is_grounded(turn), (
                    flow.lesson_id,
                    step.step_id,
                    strike,
                )
                assert turn.turn_kind == "hint"
                assert turn.verification == step.verification
                assert turn.observation.control_id in step.verification.observable_control_ids
                assert turn.observation.input_surfaces == tuple(
                    str(surface) for surface in step.verification.input_surfaces
                )
                assert turn.citations
                assert all(citation.startswith("[screen:") for citation in turn.citations)
                hint_turn_count += 1

    assert hint_turn_count == 228


def test_course3_teaching_turn_observes_live_backstage_lenses() -> None:
    step = build_lesson_flow("L3.04").steps[0]

    turn = plan_teaching_turn(lesson_id="L3.04", step=step)

    assert {
        "live_audio",
        "cue_section_lookahead",
        "library_suggestions",
        "session_recording",
        "debrief",
    } <= set(turn.observation.backstage_lenses)


def test_runtime_calls_teaching_loop_for_step_and_hint_turns(
    monkeypatch,
) -> None:
    """LessonRuntime uses the first-class loop for live teach/hint turns."""
    from vibemix.learn import runtime as runtime_mod

    real_teach = runtime_mod.plan_teaching_turn
    real_hint = runtime_mod.plan_hint_turn
    calls: list[str] = []

    def spy_teach(**kwargs):
        calls.append("teach")
        return real_teach(**kwargs)

    def spy_hint(**kwargs):
        calls.append("hint")
        return real_hint(**kwargs)

    monkeypatch.setattr(runtime_mod, "plan_teaching_turn", spy_teach)
    monkeypatch.setattr(runtime_mod, "plan_hint_turn", spy_hint)

    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=MagicMock(name="progress_store"),
    )
    runtime.send(
        "load",
        lesson_id="L1.01",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime.handle_step_ack(
        {
            "type": "button",
            "control": "lesson_continue",
            "direction": "down",
            "source": "click",
            "value": 127,
            "prev_value": 0,
        }
    )
    runtime.send("strike")

    assert calls == ["teach", "teach", "hint"]


def test_runtime_tutor_speak_carries_backstage_loop_metadata() -> None:
    """The socket carries the loop record; the frontstage can ignore it."""
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=MagicMock(name="progress_store"),
    )

    runtime.send(
        "load",
        lesson_id="L1.01",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    speak = next(
        call.args[0]
        for call in runtime._ipc.emit.call_args_list
        if call.args and call.args[0].get("type") == "ipc.learn.tutor_speak"
    )
    loop = speak["payload"]["teaching_loop"]

    assert loop["stages"] == list(TEACHING_LOOP_STAGES)
    assert loop["turn_kind"] == "teach"
    assert loop["route_path"] == LEARN_TUTOR_ROUTE
    assert loop["observation"]["lesson_id"] == "L1.01"
    assert loop["observation"]["step_id"] == "L1.01.beat.0"
    assert loop["observation"]["control_id"] == "lesson_continue"
    assert loop["verification"]["kind"] == "button_press"
    assert loop["verification"]["observable_control_ids"] == ["lesson_continue"]


def test_runtime_hint_and_adaptive_speak_carry_loop_kind() -> None:
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=MagicMock(name="progress_store"),
    )
    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime.send("strike")
    runtime.handle_mismatch_ack(
        {
            "type": "button",
            "control": "play",
            "deck": "A",
            "direction": "down",
            "source": "click",
            "value": 127,
            "prev_value": 0,
        }
    )

    speaks = [
        call.args[0]["payload"]
        for call in runtime._ipc.emit.call_args_list
        if call.args and call.args[0].get("type") == "ipc.learn.tutor_speak"
    ]
    loop_kinds = [
        payload.get("teaching_loop", {}).get("turn_kind")
        for payload in speaks
        if payload.get("teaching_loop")
    ]

    assert "hint" in loop_kinds
    assert "adapt" in loop_kinds


def test_teaching_loop_source_has_no_model_literal() -> None:
    source = (
        Path(__file__).resolve().parent.parent.parent
        / "src"
        / "vibemix"
        / "learn"
        / "teaching_loop.py"
    ).read_text(encoding="utf-8")

    assert "gemini" not in source.lower()
