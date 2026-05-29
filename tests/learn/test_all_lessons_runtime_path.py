# SPDX-License-Identifier: Apache-2.0
"""All-lesson runtime traversal for the beginner Learn module.

This is intentionally stronger than the structured-flow compiler contract:
each beginner lesson starts through the same inbound IPC handler the UI uses,
receives its canonical action shape, reaches the runtime completion state, and
persists a completed progress row. Observer lessons ride their real observer
controllers so the marquee EQ cycle and recital gates are covered too.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest

from vibemix.learn.curriculum import CURRICULUM
from vibemix.learn.exemplar import ExemplarPick
from vibemix.learn.exemplar_lesson import ExemplarLessonController
from vibemix.learn.graduation import GraduationSummary
from vibemix.learn.ipc_handlers import register_learn_handlers
from vibemix.learn.lesson_flow import LessonFlow, build_all_beginner_flows, build_lesson_flow
from vibemix.learn.progress import LearnProgress, load_progress
from vibemix.learn.recital import RecitalRuntime
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.runtime.ws_bus import IpcRouterBus

BEGINNER_LESSON_IDS = tuple(flow.lesson_id for flow in build_all_beginner_flows())
_RECITAL_SUBSET_SIZE = 5


class _FakeFinder:
    """Deterministic exemplar finder for the observer lesson path."""

    def find(self, band: str, **_kwargs: Any) -> list[ExemplarPick]:
        return [
            ExemplarPick(
                track_id=f"test:{band}:0",
                file_path=f"/tmp/vibemix-test-{band}.wav",
                band_score=0.75,
                reason=f"test {band} exemplar",
            )
        ]


class _NoopPlayer:
    def play(self, _file_path: str) -> None:
        return None

    def stop(self) -> None:
        return None


def _graduation_summary(_progress: LearnProgress) -> GraduationSummary:
    return GraduationSummary(
        completed_lessons=0,
        total_lessons=len(BEGINNER_LESSON_IDS),
        profile_consent=False,
        profile_available=False,
        debrief_available=False,
    )


def _ack_payload_for_action(action: dict[str, Any]) -> dict[str, Any]:
    control = str(action["control"])
    deck = str(action.get("deck", "") or "")
    control_id = f"{control}:{deck}" if deck else control
    if action.get("type") == "cc":
        return {
            "control_id": control_id,
            "source": "click",
            "value": 127,
            "prev_value": 0,
            "direction": "",
        }
    return {
        "control_id": control_id,
        "source": "click",
        "value": 127,
        "prev_value": 0,
        "direction": str(action.get("direction", "down") or "down"),
    }


def _emitted(sink: MagicMock, event_type: str) -> list[dict[str, Any]]:
    return [
        call.args[0]
        for call in sink.emit.call_args_list
        if call.args
        and isinstance(call.args[0], dict)
        and call.args[0].get("type") == event_type
    ]


def _complete_if_advancing(runtime: LessonRuntime) -> None:
    if runtime.current_state.id == "advancing":
        runtime.send("finish")


def _build_harness() -> tuple[
    LessonRuntime,
    LearnProgress,
    IpcRouterBus,
    MagicMock,
    dict[str, Any],
]:
    progress = LearnProgress(course_2_unlocked=True, course_3_unlocked=True)
    sink = MagicMock(name="learn_runtime_emit_sink")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=sink,
        progress_store=progress,
        graduation_summary_loader=_graduation_summary,
    )
    observers: dict[str, Any] = {}

    def observer_emit(envelope: dict[str, Any]) -> None:
        sink.emit(envelope)
        if envelope.get("type") != "ipc.learn.complete_lesson":
            return
        payload = envelope.get("payload", {})
        reason = payload.get("reason") if isinstance(payload, dict) else None
        runtime.complete_observer_lesson(completed=reason == "completed")

    exemplar = ExemplarLessonController(
        finder=_FakeFinder(),
        player=_NoopPlayer(),
        ipc_emit=observer_emit,
    )
    c1_recital = RecitalRuntime(
        ipc_emit=observer_emit,
        progress=progress,
        seed=42,
    )
    c2_recital = RecitalRuntime(
        ipc_emit=observer_emit,
        progress=progress,
        seed=42,
    )
    observers["L1.14"] = exemplar
    observers["L1.16"] = c1_recital
    observers["L2.14"] = c2_recital
    runtime.register_lesson_observer("L1.14", exemplar)
    runtime.register_lesson_observer("L1.16", c1_recital)
    runtime.register_lesson_observer("L2.14", c2_recital)

    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )
    return runtime, progress, router, sink, observers


async def _dispatch(router: IpcRouterBus, envelope_type: str, payload: dict[str, Any]) -> bool:
    return await router.dispatch({"type": envelope_type, "payload": payload})


async def _start_lesson(router: IpcRouterBus, lesson_id: str) -> bool:
    return await _dispatch(
        router,
        "ipc.learn.start_lesson",
        {"lesson_id": lesson_id, "level": "fresh"},
    )


async def _ack(router: IpcRouterBus, action: dict[str, Any]) -> bool:
    return await _dispatch(router, "ipc.learn.ack", _ack_payload_for_action(action))


async def _drive_standard_flow(
    *,
    runtime: LessonRuntime,
    router: IpcRouterBus,
    flow: LessonFlow,
) -> None:
    for index, step in enumerate(flow.steps):
        assert runtime.current_state.id == "awaiting_action"
        assert runtime.current_step_id == step.step_id
        assert await _ack(router, step.expected_action) is True
        if index < len(flow.steps) - 1:
            assert runtime.current_state.id == "awaiting_action"
            assert runtime.current_step_id == flow.steps[index + 1].step_id

    _complete_if_advancing(runtime)


async def _drive_exemplar_flow(
    *,
    runtime: LessonRuntime,
    router: IpcRouterBus,
    flow: LessonFlow,
) -> None:
    for step in flow.steps:
        assert runtime.current_state.id == "awaiting_action"
        assert await _ack(router, step.expected_action) is True


async def _drive_recital_flow(
    *,
    runtime: LessonRuntime,
    router: IpcRouterBus,
    observer: RecitalRuntime,
) -> None:
    assert len(observer._sampled) == _RECITAL_SUBSET_SIZE
    for _ in range(_RECITAL_SUBSET_SIZE):
        assert runtime.current_state.id == "awaiting_action"
        entry = observer._sampled[observer._active_idx]
        expected = entry["expected_action"]
        assert await _ack(router, expected) is True


@pytest.mark.parametrize("lesson_id", BEGINNER_LESSON_IDS)
def test_every_beginner_lesson_completes_through_ipc_runtime_path(
    lesson_id: str,
) -> None:
    """Every 36-lesson row must survive the real start/ack runtime boundary."""
    runtime, progress, router, sink, observers = _build_harness()
    flow = build_lesson_flow(lesson_id)

    assert asyncio.run(_start_lesson(router, lesson_id)) is True
    assert runtime.current_state.id == "awaiting_action"
    assert runtime.current_step_id == flow.steps[0].step_id
    assert _emitted(sink, "ipc.learn.lesson_loaded")
    assert _emitted(sink, "ipc.learn.highlight")
    assert _emitted(sink, "ipc.learn.tutor_speak")

    if lesson_id == "L1.14":
        asyncio.run(_drive_exemplar_flow(runtime=runtime, router=router, flow=flow))
        assert len(_emitted(sink, "ipc.learn.exemplar_play")) == len(flow.steps)
    elif lesson_id in {"L1.16", "L2.14"}:
        observer = observers[lesson_id]
        assert isinstance(observer, RecitalRuntime)
        asyncio.run(
            _drive_recital_flow(
                runtime=runtime,
                router=router,
                observer=observer,
            )
        )
    else:
        asyncio.run(_drive_standard_flow(runtime=runtime, router=router, flow=flow))

    assert runtime.current_state.id == "completed"
    assert progress.lessons[lesson_id]["completed"] is True
    assert _emitted(sink, "ipc.learn.complete_lesson")

    reloaded, was_corrupt = load_progress()
    assert was_corrupt is False
    assert reloaded.lessons[lesson_id]["completed"] is True
    assert CURRICULUM[lesson_id].course_id == flow.course_id
