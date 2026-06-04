# SPDX-License-Identifier: Apache-2.0
"""Phase 92 CR-01 (P92 REVIEW) regression — inbound ipc.learn.* dispatch.

The :class:`LessonRuntime` FSM was wired in ``__main__.py`` but no
inbound IPC handler was registered for any of the 5 shell→sidecar learn
envelopes. ``IpcRouterBus.dispatch()`` returned False silently and the
FSM stayed parked in ``idle`` — the "press play" demo failed at the
very first envelope.

This module pins the inbound boundary: dispatching a synthetic envelope
through :class:`IpcRouterBus` MUST drive the FSM past ``idle`` (for
``start_lesson`` / ``start_course``) AND emit the expected response
envelopes (for ``progress_state`` action=reset).

REQ-ID: P92 REVIEW CR-01.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibemix.learn.ipc_handlers import register_learn_handlers
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.skill_tree import SKILL_MANIFEST
from vibemix.learn.state import LearnState
from vibemix.runtime.ws_bus import IpcRouterBus


@pytest.fixture
def progress_path_in_tmp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    """Redirect ``progress_path()`` to a tmp dir so each test starts with a
    clean canvas. Mirrors the fixture in
    ``test_progress_persistence.py``."""
    target = tmp_path / "learn-progress.json"
    monkeypatch.setattr(
        "vibemix.learn.progress.progress_path",
        lambda: target,
    )
    return target


def _make_runtime() -> tuple[LessonRuntime, LearnProgress, MagicMock]:
    """Build a LessonRuntime + real LearnProgress + Mock ipc_router.

    The ipc_router here is the LessonRuntime's emit sink (the sync
    adapter); the actual inbound dispatch goes through a separate
    IpcRouterBus instance in the test bodies below.
    """
    learn_state = LearnState()
    midi_mirror = MagicMock(name="midi_mirror")
    midi_mirror.current_profile.return_value = None
    controller_state = MagicMock(name="controller_state")
    runtime_emit_sink = MagicMock(name="runtime_emit_sink")
    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=learn_state,
        midi_mirror=midi_mirror,
        controller_state=controller_state,
        ipc_router=runtime_emit_sink,
        progress_store=progress,
    )
    return runtime, progress, runtime_emit_sink


def _hint_payloads(runtime_emit_sink: MagicMock) -> list[dict]:
    return [
        call.args[0]["payload"]
        for call in runtime_emit_sink.emit.call_args_list
        if call.args
        and call.args[0].get("type") == "ipc.learn.tutor_speak"
        and call.args[0].get("payload", {}).get("data_state") == "hint"
    ]


def _make_competent(progress: LearnProgress, skill_id: str) -> None:
    spec = SKILL_MANIFEST[skill_id]
    for lesson_id in spec.lesson_ids:
        progress.lessons[lesson_id] = {
            "completed": True,
            "completed_at": "2026-06-03T00:00:00Z",
            "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)


def test_start_lesson_dispatch_advances_fsm() -> None:
    """``ipc.learn.start_lesson`` envelope must drive idle → awaiting_action.

    Before CR-01 fix: ``IpcRouterBus.dispatch()`` returned False because
    no handler was registered; the FSM stayed parked in idle.
    """
    runtime, progress, runtime_emit_sink = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    assert runtime.current_state.id == "idle", "fresh runtime starts idle"

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L0.00-press-play",
                    "level": "fresh",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True, (
        "CR-01 regression — ipc.learn.start_lesson must be recognized "
        "by IpcRouterBus.dispatch (handler registered)"
    )
    # After the 2-step load → begin sequence, the FSM is in
    # awaiting_action waiting for MIDI.
    assert runtime.current_state.id == "awaiting_action", (
        f"start_lesson should drive FSM to awaiting_action; "
        f"state={runtime.current_state.id!r}"
    )
    lesson_loaded = [
        call.args[0]
        for call in runtime_emit_sink.emit.call_args_list
        if call.args and call.args[0].get("type") == "ipc.learn.lesson_loaded"
    ]
    assert lesson_loaded[-1]["payload"]["controller_id"] == "pioneer_ddj_flx4"


def test_start_lesson_accepts_legacy_slugged_id() -> None:
    """Slugged frontend ids normalize to the Python curriculum key."""
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L1.01-opening-dialog",
                    "level": "fresh",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id == "awaiting_action"
    assert runtime._learn.current_lesson_id == "L1.01"


def test_start_course_dispatch_advances_fsm() -> None:
    """``ipc.learn.start_course`` resolves the first lesson of the course
    and drives the FSM to awaiting_action.
    """
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_course",
                "payload": {
                    "course_id": "course_0",
                    "controller_id": "pioneer_ddj_flx4",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id == "awaiting_action"


def test_start_course_uses_zpd_frontier_when_course_contains_aim() -> None:
    """Course starts replay the current Competent-not-Mastered skill drill."""
    runtime, progress, _ = _make_runtime()
    progress.course_2_unlocked = True
    _make_competent(progress, "eq_mixing")
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_course",
                "payload": {
                    "course_id": "course_2",
                    "controller_id": "pioneer_ddj_flx4",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id == "awaiting_action"
    assert runtime._learn.current_lesson_id == "L2.04"


def test_start_lesson_unknown_id_silent_noop() -> None:
    """An unknown lesson_id must NOT raise and MUST leave the FSM idle.

    WR-02 mitigation — the FSM previously advanced through transitions
    on a None/unknown lesson_id with no visible error; the handler
    catches the invalid input at the boundary.
    """
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L99.99-from-the-future",
                    "level": "fresh",
                },
            }
        )

    handled = asyncio.run(go())
    # Dispatch returned True (handler ran) but rejected the invalid
    # lesson — FSM is still idle.
    assert handled is True
    assert runtime.current_state.id == "idle", (
        "unknown lesson_id must NOT advance the FSM; "
        f"state={runtime.current_state.id!r}"
    )


def test_start_lesson_rejects_locked_course_2_until_unlocked() -> None:
    """Course 2 lessons stay server-locked until the recital unlock flag."""
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L2.01",
                    "level": "fresh",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id == "idle"


def test_start_lesson_allows_course_2_after_unlock() -> None:
    """The same canonical lesson starts once progress unlocks course 2."""
    runtime, progress, _ = _make_runtime()
    progress.course_2_unlocked = True
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L2.01",
                    "level": "fresh",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id == "awaiting_action"


def test_start_lesson_replays_completed_locked_course_2_lesson() -> None:
    """Completed lessons remain replayable even if the course gate is locked."""
    runtime, progress, _ = _make_runtime()
    progress.lessons["L2.01"] = {
        "completed": True,
        "completed_at": "2026-05-28T00:00:00Z",
        "strikes_used": 0,
    }
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L2.01",
                    "level": "replay",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id == "awaiting_action"
    assert runtime._learn.current_lesson_id == "L2.01"


def test_start_course_rejects_locked_course() -> None:
    """Course-level starts use the same progress gate as lesson jumps."""
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_course",
                "payload": {
                    "course_id": "course_2_transitions",
                    "controller_id": "pioneer_ddj_flx4",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id == "idle"


def test_ack_dispatch_drives_action_match() -> None:
    """A matching ``ipc.learn.ack`` MUST drive the FSM past awaiting_action.

    The runtime's action_matches guard checks the midi dict against the
    lesson's expected_action. For L0.00-press-play that's a play_a button
    press-down — the ack should match and advance.
    """
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    # Drive to awaiting_action first.
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    assert runtime.current_state.id == "awaiting_action"

    # Read the actual expected_action from CURRICULUM so this test stays
    # in sync with the lesson fixture without hardcoding the control.
    from vibemix.learn.curriculum import CURRICULUM

    expected = CURRICULUM["L0.00-press-play"].script["expected_action"]

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": (
                        f"{expected['control']}:{expected.get('deck', '')}"
                        if expected.get("deck")
                        else expected["control"]
                    ),
                    "source": "midi",
                    "value": 127,
                    "direction": expected.get("direction", ""),
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    # ack matched → FSM advances; either advancing or completed depending
    # on whether the post-advance auto-finish task fires in the test
    # event loop. Both states are acceptable observations of "advanced".
    assert runtime.current_state.id in {"advancing", "completed"}, (
        "matching ack should advance FSM past awaiting_action; "
        f"state={runtime.current_state.id!r}"
    )
    assert progress.lessons["L0.00-press-play"]["practice_sources"] == {
        "hardware": 1,
        "screen": 0,
    }
    assert progress.lessons["L0.00-press-play"]["last_practice_source"] == "hardware"


def test_ack_dispatch_uses_real_prev_value_for_cc_actions() -> None:
    """CC acks stay CC events and use the wire prev_value for min_delta."""
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    assert runtime.current_state.id == "awaiting_action"

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "eq_hi:A",
                    "source": "midi",
                    "value": 110,
                    "prev_value": 20,
                    "direction": "down",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id in {"advancing", "completed"}


def test_hardware_cc_ack_keeps_small_sample_delta_as_near_miss() -> None:
    """Small real hardware deltas cite practice but do not complete the lesson."""
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    assert runtime.current_state.id == "awaiting_action"

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "eq_hi:A",
                    "source": "midi",
                    "value": 65,
                    "prev_value": 64,
                    "direction": "down",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id == "awaiting_action"
    assert progress.lessons["L1.03"]["practice_sources"] == {
        "hardware": 1,
        "screen": 0,
    }


def test_ack_dispatch_normalizes_jog_touch_to_jog_cc() -> None:
    """Physical jog-touch events satisfy the curriculum's jog action."""
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    runtime.send(
        "load",
        lesson_id="L1.07",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    assert runtime.current_state.id == "awaiting_action"

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "jog_touched:A",
                    "source": "midi",
                    "value": 1,
                    "prev_value": 0,
                    "direction": "down",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id in {"advancing", "completed"}


def test_ack_dispatch_normalizes_filter_fx_to_echo_button() -> None:
    """Controllers with a generic FX button can satisfy echo-out lessons."""
    runtime, progress, _ = _make_runtime()
    progress.course_2_unlocked = True
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    runtime.send(
        "load",
        lesson_id="L2.07",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    assert runtime.current_state.id == "awaiting_action"

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "filter_fx",
                    "source": "midi",
                    "value": 127,
                    "prev_value": 0,
                    "direction": "down",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id in {"advancing", "completed"}


def test_ack_dispatch_delegates_to_active_lesson_observer(
    progress_path_in_tmp: Path,
) -> None:
    """Observer lessons consume their own multi-step acks.

    Recital/exemplar lessons run several prompts under one canonical
    lesson id. Their active observer must own matching so the outer FSM
    does not complete the whole lesson after the first matching control.
    """
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    observer = MagicMock(name="lesson_observer")
    observer.matches.side_effect = (
        lambda midi: midi.get("control") == "eq_hi" and midi.get("deck") == "A"
    )
    runtime.register_lesson_observer("L1.16", observer)
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def start() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L1.16",
                    "level": "fresh",
                },
            }
        )

    assert asyncio.run(start()) is True
    assert runtime.current_state.id == "awaiting_action"
    observer.start.assert_called_once()

    async def send_ack(control_id: str) -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": control_id,
                    "source": "click",
                    "value": 127,
                    "prev_value": 0,
                    "direction": "down",
                },
            }
        )

    assert asyncio.run(send_ack("lesson_continue")) is True
    observer.ack.assert_not_called()
    assert runtime.current_state.id == "awaiting_action"

    assert asyncio.run(send_ack("eq_hi:A")) is True
    observer.ack.assert_called_once_with(lesson_id="L1.16")
    assert runtime.current_state.id == "awaiting_action"

    runtime.complete_observer_lesson(completed=True)
    assert runtime.current_state.id == "completed"
    observer.stop.assert_called_once_with(lesson_id="L1.16")
    assert progress.lessons["L1.16"]["completed"] is True


def test_lesson_continue_walks_authored_tutor_beats_before_completion() -> None:
    """Continue-style lessons speak every authored fixture beat."""
    runtime, progress, runtime_emit_sink = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def start() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L1.01",
                    "level": "fresh",
                },
            }
        )

    async def continue_once() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "lesson_continue",
                    "source": "click",
                    "value": 127,
                    "prev_value": 0,
                    "direction": "down",
                },
            }
        )

    assert asyncio.run(start()) is True
    assert runtime.current_state.id == "awaiting_action"
    assert runtime.current_step_id == "L1.01.beat.0"
    for idx in range(3):
        assert asyncio.run(continue_once()) is True
        assert runtime.current_state.id == "awaiting_action"
        assert runtime.current_step_id == f"L1.01.beat.{idx + 1}"

    tutor_lines = [
        call.args[0]["payload"]["text"]
        for call in runtime_emit_sink.emit.call_args_list
        if call.args and call.args[0].get("type") == "ipc.learn.tutor_speak"
    ]
    assert tutor_lines[:4] == [
        "Hello vibemix, what are you?",
        "I'm the best DJ app in the world.",
        "If you are the best, then who the fuck am I?",
        "Oh bestie, don't worry. You know why? "
        "Because I'm the beginner module of vibemix. Let's go.",
    ]

    assert asyncio.run(continue_once()) is True
    assert runtime.current_state.id in {"advancing", "completed"}


def test_beginner_path_dispatch_continue_finish_persists(
    progress_path_in_tmp: Path,
) -> None:
    """The first beginner lesson survives the real sidecar dispatch path.

    This pins the screen contract to the Python boundary: start lesson,
    click through authored beats, complete the runtime, emit terminal
    envelopes, and persist progress to disk.
    """
    runtime, progress, runtime_emit_sink = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def dispatch(msg: dict) -> bool:
        return await router.dispatch(msg)

    start_msg = {
        "type": "ipc.learn.start_lesson",
        "payload": {
            "lesson_id": "L1.01",
            "level": "fresh",
        },
    }
    continue_msg = {
        "type": "ipc.learn.ack",
        "payload": {
            "control_id": "lesson_continue",
            "source": "click",
            "value": 127,
            "prev_value": 0,
            "direction": "down",
        },
    }

    assert asyncio.run(dispatch(start_msg)) is True
    assert runtime.current_state.id == "awaiting_action"
    assert runtime.current_step_id == "L1.01.beat.0"

    for expected_step in (
        "L1.01.beat.1",
        "L1.01.beat.2",
        "L1.01.beat.3",
    ):
        assert asyncio.run(dispatch(continue_msg)) is True
        assert runtime.current_state.id == "awaiting_action"
        assert runtime.current_step_id == expected_step

    assert asyncio.run(dispatch(continue_msg)) is True
    assert runtime.current_state.id in {"advancing", "completed"}
    if runtime.current_state.id == "advancing":
        runtime.send("finish")
    assert runtime.current_state.id == "completed"

    emitted = [
        call.args[0]
        for call in runtime_emit_sink.emit.call_args_list
        if call.args and isinstance(call.args[0], dict)
    ]
    emitted_types = [env.get("type") for env in emitted]
    assert "ipc.learn.lesson_loaded" in emitted_types
    assert "ipc.learn.complete_lesson" in emitted_types
    assert "ipc.learn.progress_state" in emitted_types

    assert progress_path_in_tmp.exists()
    assert progress.lessons["L1.01"]["completed"] is True
    assert progress.lessons["L1.01"]["practice_sources"] == {
        "hardware": 0,
        "screen": 4,
    }
    assert progress.lessons["L1.01"]["last_practice_source"] == "screen"

    from vibemix.learn.progress import load_progress

    reloaded, was_corrupt = load_progress()
    assert was_corrupt is False
    assert reloaded.lessons["L1.01"]["practice_sources"] == {
        "hardware": 0,
        "screen": 4,
    }
    assert reloaded.lessons["L1.01"]["last_practice_source"] == "screen"
    assert reloaded.lessons["L1.01"]["completed"] is True


def test_control_lesson_speaks_action_prompt_before_verification() -> None:
    """Non-continue lessons surface setup plus the action prompt on start."""
    runtime, progress, runtime_emit_sink = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def start() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L1.03",
                    "level": "fresh",
                },
            }
        )

    assert asyncio.run(start()) is True
    assert runtime.current_state.id == "awaiting_action"
    assert runtime.current_step_id == "L1.03.practice"

    tutor_lines = [
        call.args[0]["payload"]["text"]
        for call in runtime_emit_sink.emit.call_args_list
        if call.args and call.args[0].get("type") == "ipc.learn.tutor_speak"
    ]
    assert tutor_lines[:2] == [
        "the channel strip is the vertical column above each deck: "
        "gain on top, three EQ knobs, fader at the bottom.",
        "twist the top EQ knob on deck A and listen for the cymbals "
        "getting brighter or darker.",
    ]


def test_wrong_action_ack_emits_adaptive_hint_without_advancing() -> None:
    """A wrong control should produce coaching, not silence."""
    runtime, progress, runtime_emit_sink = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def start() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L1.03",
                    "level": "fresh",
                },
            }
        )

    async def wrong_ack() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "eq_mid:A",
                    "source": "click",
                    "value": 127,
                    "prev_value": 0,
                    "direction": "down",
                },
            }
        )

    assert asyncio.run(start()) is True
    assert asyncio.run(wrong_ack()) is True
    assert runtime.current_state.id == "awaiting_action"

    hints = _hint_payloads(runtime_emit_sink)
    assert hints[-1]["text"] == "that was deck A mid EQ. use deck A high EQ."
    assert hints[-1]["citations"] == ["[screen:eq_mid:A]", "[screen:eq_hi:A]"]
    assert progress.lessons["L1.03"]["practice_sources"] == {
        "hardware": 0,
        "screen": 1,
    }
    assert progress.lessons["L1.03"]["last_practice_source"] == "screen"


def test_wrong_deck_ack_points_back_to_expected_deck() -> None:
    """The same control on the wrong deck should not be called a small move."""
    runtime, progress, runtime_emit_sink = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def start() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L1.03",
                    "level": "fresh",
                },
            }
        )

    async def wrong_deck_ack() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "eq_hi:B",
                    "source": "click",
                    "value": 127,
                    "prev_value": 0,
                    "direction": "down",
                },
            }
        )

    assert asyncio.run(start()) is True
    assert asyncio.run(wrong_deck_ack()) is True
    assert runtime.current_state.id == "awaiting_action"

    hints = _hint_payloads(runtime_emit_sink)
    assert hints[-1]["text"] == "use deck A high EQ."
    assert hints[-1]["citations"] == ["[screen:eq_hi:B]", "[screen:eq_hi:A]"]


def test_tiny_screen_cc_ack_asks_for_a_larger_movement() -> None:
    """A synthetic/screen CC nudge with too little delta gets a hint."""
    runtime, progress, runtime_emit_sink = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def start() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L1.03",
                    "level": "fresh",
                },
            }
        )

    async def small_ack() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "eq_hi:A",
                    "source": "click",
                    "value": 45,
                    "prev_value": 20,
                    "direction": "down",
                },
            }
        )

    assert asyncio.run(start()) is True
    assert asyncio.run(small_ack()) is True
    assert runtime.current_state.id == "awaiting_action"

    hints = _hint_payloads(runtime_emit_sink)
    assert hints[-1]["text"] == "move deck A high EQ farther."
    assert hints[-1]["citations"] == ["[screen:eq_hi:A]"]


def test_button_release_ack_restates_the_press_action() -> None:
    """A button release on the correct button should ask for the press."""
    runtime, progress, runtime_emit_sink = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def start() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L0.00-press-play",
                    "level": "fresh",
                },
            }
        )

    async def release_ack() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "play:A",
                    "source": "click",
                    "value": 0,
                    "prev_value": 127,
                    "direction": "up",
                },
            }
        )

    assert asyncio.run(start()) is True
    assert asyncio.run(release_ack()) is True
    assert runtime.current_state.id == "awaiting_action"

    hints = _hint_payloads(runtime_emit_sink)
    assert hints[-1]["text"] == "press deck A play."
    assert hints[-1]["citations"] == ["[screen:play:A]"]


def test_button_wrong_deck_ack_restates_the_expected_press() -> None:
    """The right button on the wrong deck should keep the action verb."""
    runtime, progress, runtime_emit_sink = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def start() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {
                    "lesson_id": "L0.00-press-play",
                    "level": "fresh",
                },
            }
        )

    async def wrong_deck_ack() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "play:B",
                    "source": "click",
                    "value": 127,
                    "prev_value": 0,
                    "direction": "down",
                },
            }
        )

    assert asyncio.run(start()) is True
    assert asyncio.run(wrong_deck_ack()) is True
    assert runtime.current_state.id == "awaiting_action"

    hints = _hint_payloads(runtime_emit_sink)
    assert hints[-1]["text"] == "press deck A play."
    assert hints[-1]["citations"] == ["[screen:play:B]", "[screen:play:A]"]


def test_complete_lesson_user_skip_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``ipc.learn.complete_lesson { reason: user_skip }`` drives send("skip").

    With the 45 s min-dwell guard satisfied, skip advances the FSM.
    """
    import time

    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    base = 1_700_000_000.0
    fake_now = {"t": base}

    def fake_monotonic() -> float:
        return fake_now["t"]

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    # Load + begin at t=base.
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    # Jump past the 45 s anti-speedrun floor.
    fake_now["t"] = base + 46.0

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.complete_lesson",
                "payload": {
                    "lesson_id": "L0.00-press-play",
                    "reason": "user_skip",
                },
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    assert runtime.current_state.id in {"advancing", "completed"}, (
        "user_skip with min-dwell elapsed should advance FSM; "
        f"state={runtime.current_state.id!r}"
    )


def test_progress_state_reset_emits_ack_and_wipes_progress(
    progress_path_in_tmp: Path,
) -> None:
    """``ipc.learn.progress_state { action: reset }`` MUST:

      * unlink the on-disk file
      * clear the in-memory progress dicts
      * emit a ``reset_ack`` envelope through the ipc_router
    """
    runtime, progress, _ = _make_runtime()

    # Seed some progress to verify the wipe path actually runs.
    from vibemix.learn.progress import save_progress

    progress.mark_completed("course_0", "L0.00-press-play")
    progress.course_2_unlocked = True
    progress.course_3_unlocked = True
    save_progress(progress)
    assert progress_path_in_tmp.exists()
    assert "L0.00-press-play" in progress.lessons

    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    # Capture every emit through the bus's emit binding so we can
    # inspect the reset_ack frame.
    emitted: list[dict] = []

    async def _capture(d: dict) -> None:
        emitted.append(d)

    router.bind_emit(_capture)

    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
        # No ipc_adapter — handler awaits router.emit directly.
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.progress_state",
                "payload": {"action": "reset"},
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    # On-disk file rewritten with empty progress (save_progress fires
    # after reset_progress unlinks + we re-save the empty state).
    assert progress_path_in_tmp.exists(), (
        "reset path should re-save an empty progress file"
    )
    # In-memory dicts wiped.
    assert progress.lessons == {}, (
        f"in-memory lessons not cleared on reset; lessons={progress.lessons!r}"
    )
    assert progress.courses == {}
    assert progress.course_2_unlocked is False
    assert progress.course_3_unlocked is False
    # reset_ack emitted.
    ack_types = [e.get("type") for e in emitted]
    assert "ipc.learn.progress_state" in ack_types, (
        f"reset_ack envelope was not emitted; emitted types={ack_types!r}"
    )
    # Verify it's specifically a reset_ack (not snapshot etc).
    ack_actions = [
        e.get("payload", {}).get("action")
        for e in emitted
        if e.get("type") == "ipc.learn.progress_state"
    ]
    assert "reset_ack" in ack_actions, (
        f"action=reset_ack missing from emitted progress_state envelopes; "
        f"actions={ack_actions!r}"
    )
    reset_acks = [
        e
        for e in emitted
        if e.get("type") == "ipc.learn.progress_state"
        and e.get("payload", {}).get("action") == "reset_ack"
    ]
    assert len(reset_acks) == 1
    ack_progress = reset_acks[0]["payload"]["progress"]
    assert ack_progress["lessons"] == {}
    assert ack_progress["courses"] == {}
    assert ack_progress["course_2_unlocked"] is False
    assert ack_progress["course_3_unlocked"] is False
    assert all(
        row["live_proof_count"] == 0 and row["mastered"] is False
        for row in ack_progress["skills"].values()
    )


def test_progress_state_snapshot_emits_current_state() -> None:
    """``ipc.learn.progress_state { action: snapshot }`` emits the current
    persisted state as a snapshot envelope."""
    runtime, progress, _ = _make_runtime()
    progress.mark_completed("course_0", "L0.00-press-play")

    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    emitted: list[dict] = []

    async def _capture(d: dict) -> None:
        emitted.append(d)

    router.bind_emit(_capture)

    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch(
            {
                "type": "ipc.learn.progress_state",
                "payload": {"action": "snapshot"},
            }
        )

    handled = asyncio.run(go())
    assert handled is True
    snapshots = [
        e
        for e in emitted
        if e.get("type") == "ipc.learn.progress_state"
        and e.get("payload", {}).get("action") == "snapshot"
    ]
    assert len(snapshots) == 1, (
        f"expected one snapshot envelope, got {len(snapshots)}: {emitted!r}"
    )
    snap = snapshots[0]["payload"]["progress"]
    assert "L0.00-press-play" in snap.get("lessons", {})


def test_dispatch_unknown_type_returns_false() -> None:
    """Sanity check — unknown types still return False (handler bag is
    type-keyed). CR-01 only registers our 5; everything else stays
    unrecognized."""
    runtime, progress, _ = _make_runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def go() -> bool:
        return await router.dispatch({"type": "ipc.notalearntype"})

    assert asyncio.run(go()) is False
