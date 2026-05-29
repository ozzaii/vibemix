# SPDX-License-Identifier: Apache-2.0
"""Raw controller movement -> Learn teaching-loop integration proofs."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from vibemix.learn.ipc_handlers import register_learn_handlers
from vibemix.learn.midi_mirror import MidiMirror
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.midi import ControllerState, load_profile
from vibemix.runtime.ws_bus import IpcRouterBus


class _EmitSink:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    def emit(self, msg: dict) -> None:
        self.messages.append(msg)


def _cc(channel: int, control: int, value: int) -> SimpleNamespace:
    return SimpleNamespace(
        type="control_change",
        channel=channel,
        control=control,
        value=value,
    )


def _runtime_with_flx4() -> tuple[LessonRuntime, LearnProgress, ControllerState, MidiMirror]:
    profile = load_profile("pioneer_ddj_flx4")
    assert profile is not None
    controller_state = ControllerState(profile=profile)
    controller_state.mark_connected("DDJ-FLX4")
    midi_mirror = MidiMirror(controller_state=controller_state)
    midi_mirror.bind_profile(profile)
    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=midi_mirror,
        controller_state=controller_state,
        ipc_router=_EmitSink(),
        progress_store=progress,
    )
    return runtime, progress, controller_state, midi_mirror


async def _dispatch(router: IpcRouterBus, msg: dict) -> bool:
    return await router.dispatch(msg)


def test_raw_flx4_relative_jog_tick_advances_jog_wheel_lesson() -> None:
    """A raw FLX4 jog-wheel CC33 tick can complete the L1.07 action gate.

    This is the deterministic version of the physical-controller promise:
    hardware callback -> ControllerState -> MidiMirror -> UI-shaped Learn ACK
    -> LessonRuntime action verifier. No browser timing or human movement
    window is needed, but the bytes match the real FLX4 callback sniff
    (channel 0, CC33, value 65).
    """
    runtime, progress, controller_state, midi_mirror = _runtime_with_flx4()
    router = IpcRouterBus()
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    handled = asyncio.run(
        _dispatch(
            router,
            {
                "type": "ipc.learn.start_lesson",
                "payload": {"lesson_id": "L1.07", "level": "fresh"},
            },
        )
    )
    assert handled is True
    assert runtime.current_state.id == "awaiting_action"

    baseline = midi_mirror.snapshot()
    assert baseline is not None
    assert baseline["payload"]["positions"]["jog:A"] == 0

    controller_state.handle_msg(_cc(0, 0x21, 65))
    pulse = midi_mirror.snapshot()
    assert pulse is not None
    assert pulse["payload"]["positions"]["jog:A"] == 127

    handled = asyncio.run(
        _dispatch(
            router,
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "jog:A",
                    "source": "midi",
                    "value": 127,
                    "prev_value": 0,
                    "direction": "down",
                },
            },
        )
    )
    assert handled is True
    assert runtime.current_state.id in {"advancing", "completed"}

    reset = midi_mirror.snapshot()
    assert reset is not None
    assert reset["payload"]["positions"]["jog:A"] == 0


def test_start_lesson_uses_bound_physical_profile_for_lesson_loaded() -> None:
    """The sidecar stamps lesson_loaded with the currently bound controller."""
    runtime, progress, _, midi_mirror = _runtime_with_flx4()
    runtime_emit_sink = MagicMock(name="runtime_emit_sink")
    runtime._ipc = runtime_emit_sink
    router = IpcRouterBus()
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    handled = asyncio.run(
        _dispatch(
            router,
            {
                "type": "ipc.learn.start_lesson",
                "payload": {"lesson_id": "L1.07", "level": "fresh"},
            },
        )
    )
    assert handled is True

    lesson_loaded = [
        call.args[0]
        for call in runtime_emit_sink.emit.call_args_list
        if call.args and call.args[0].get("type") == "ipc.learn.lesson_loaded"
    ]
    assert lesson_loaded
    assert lesson_loaded[-1]["payload"]["controller_id"] == "pioneer_ddj_flx4"
