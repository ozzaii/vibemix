# SPDX-License-Identifier: Apache-2.0
"""Learn runtime evidence grounding regression tests."""
from __future__ import annotations

from unittest.mock import MagicMock

from vibemix.coach.citation_linter import CitationLinter
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.state.evidence_registry import EvidenceRegistry


def _runtime_with_evidence(
    *,
    clock_value: float,
) -> tuple[LessonRuntime, EvidenceRegistry, MagicMock]:
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=LearnProgress(),
        evidence_registry=registry,
        evidence_clock=lambda: clock_value,
    )
    return runtime, registry, ipc


def _hint_payloads(ipc: MagicMock) -> list[dict]:
    return [
        call.args[0]["payload"]
        for call in ipc.emit.call_args_list
        if call.args
        and call.args[0].get("type") == "ipc.learn.tutor_speak"
        and call.args[0].get("payload", {}).get("data_state") == "hint"
    ]


def test_adaptive_midi_hint_writes_registry_and_time_keyed_citation() -> None:
    """MIDI adaptive coaching cites the exact registry-backed action."""
    runtime, registry, ipc = _runtime_with_evidence(clock_value=12.7)
    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    handled = runtime.handle_mismatch_ack(
        {
            "type": "cc",
            "control": "eq_hi",
            "deck": "A",
            "value": 45,
            "prev_value": 20,
            "source": "midi",
            "direction": "down",
        }
    )

    assert handled is True
    hints = _hint_payloads(ipc)
    assert hints[-1]["citations"] == ["[midi:eq_hi:A@12.7]", "[screen:eq_hi:A]"]

    snapshot = registry.snapshot()
    assert 12.7 in snapshot["midi"]["eq_hi:A"]
    assert 12.7 in snapshot["screen"]["eq_hi:A"]

    result = CitationLinter().check(
        " ".join(hints[-1]["citations"]),
        snapshot,
        mode="live",
    )
    assert result.valid is True


def test_timed_hint_cites_the_registry_backed_highlight() -> None:
    """No-action hints cite the control the screen already highlighted."""
    runtime, registry, ipc = _runtime_with_evidence(clock_value=18.0)
    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime.send("strike")

    hint = _hint_payloads(ipc)[-1]
    assert hint["citations"] == ["[screen:eq_hi:A]"]

    snapshot = registry.snapshot()
    assert 18.0 in snapshot["screen"]["eq_hi:A"]
    result = CitationLinter().check(
        " ".join(hint["citations"]),
        snapshot,
        mode="live",
    )
    assert result.valid is True


def test_matching_action_writes_registry_for_debrief_grounding() -> None:
    """A successful lesson action is also recorded for later debrief/profile use."""
    runtime, registry, _ipc = _runtime_with_evidence(clock_value=33.3)
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    runtime.send(
        "ack_action",
        midi={
            "type": "button",
            "control": "play",
            "deck": "A",
            "direction": "down",
            "source": "midi",
        },
    )

    snapshot = registry.snapshot()
    assert 33.3 in snapshot["midi"]["play:A"]
    assert 33.3 in snapshot["screen"]["play:A"]
    result = CitationLinter().check(
        "[midi:play:A@33.3] [screen:play:A]",
        snapshot,
        mode="live",
    )
    assert result.valid is True


def test_runtime_logs_learn_milestones_to_session_event_sink() -> None:
    """Learn leaves a lesson timeline in the existing recordings spine."""
    events: list[tuple[str, dict]] = []
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=LearnProgress(),
        session_event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )

    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime.send(
        "ack_action",
        midi={
            "type": "cc",
            "control": "eq_hi",
            "deck": "A",
            "value": 127,
            "prev_value": 0,
            "source": "midi",
        },
    )

    kinds = [kind for kind, _fields in events]
    assert "learn_lesson_loaded" in kinds
    assert "learn_tutor_speak" in kinds
    assert "ai_message" in kinds
    assert "learn_action_observed" in kinds

    ai_message = next(fields for kind, fields in events if kind == "ai_message")
    assert ai_message["engine"] == "learn_tutor"
    assert ai_message["surface"] == "learn"
    assert ai_message["direction"] == "assistant"
    assert ai_message["event"] == "learn_tutor_speak"
    assert ai_message["provider"] == "authored_fixture"
    assert ai_message["stop_reason"] == "authored_fixture"
    assert ai_message["message"]
    assert ai_message["extra"]["lesson_id"] == "L1.03"
    assert ai_message["extra"]["course_id"] == "course_1_anatomy"
    assert ai_message["extra"]["step_id"] == "L1.03.practice"
    assert ai_message["extra"]["tts_marker"]
    assert ai_message["extra"]["source"] == "learn_runtime"

    action = next(fields for kind, fields in events if kind == "learn_action_observed")
    assert action["lesson_id"] == "L1.03"
    assert action["step_id"] == "L1.03.practice"
    assert action["observed_control_id"] == "eq_hi:A"
    assert action["expected_control_id"] == "eq_hi:A"
    assert action["matched"] is True
    assert isinstance(action["evidence_time"], float)
