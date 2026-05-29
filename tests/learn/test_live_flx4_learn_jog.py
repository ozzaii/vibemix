# SPDX-License-Identifier: Apache-2.0
"""Opt-in live FLX4 jog -> Learn verifier proof.

Default suite skips this file. To discharge the remaining physical L1.07 proof:

    VIBEMIX_LIVE_LEARN_JOG=1 uv run pytest -q -m macos_audio \
        tests/learn/test_live_flx4_learn_jog.py

Then nudge the left jog wheel during the sniff window.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from vibemix.learn.ipc_handlers import register_learn_handlers
from vibemix.learn.midi_mirror import MidiMirror
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.midi import ControllerState, load_profile
from vibemix.runtime.ws_bus import IpcRouterBus

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")


class _EmitSink:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    def emit(self, msg: dict) -> None:
        self.messages.append(msg)


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


def _live_flx4_frames(seconds: int) -> list[dict]:
    repo_root = Path(__file__).resolve().parents[2]
    cmd = [
        sys.executable,
        str(repo_root / "scripts" / "sniff_controller.py"),
        "--port",
        "FLX4",
        "--seconds",
        str(seconds),
        "--mode",
        "callback",
    ]
    proc = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=seconds + 10,
        check=False,
    )
    if proc.returncode == 3:
        pytest.skip("no FLX4 connected")
    assert proc.returncode == 0, (
        f"live FLX4 sniff failed with exit={proc.returncode}\n"
        f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    )
    frames: list[dict] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not row.get("summary"):
            frames.append(row)
    return frames


@pytest.mark.macos_audio
def test_live_flx4_left_jog_reaches_lesson_verifier() -> None:
    """Live CC33 from the left FLX4 jog wheel satisfies L1.07."""
    if not os.environ.get("VIBEMIX_LIVE_LEARN_JOG"):
        pytest.skip(
            "opt-in live jog proof. Run with VIBEMIX_LIVE_LEARN_JOG=1 "
            "and nudge the left FLX4 jog wheel during the sniff window."
        )
    seconds = int(os.environ.get("VIBEMIX_LIVE_LEARN_JOG_SECONDS", "20"))
    frames = _live_flx4_frames(seconds)
    jog_frames = [
        frame
        for frame in frames
        if frame.get("type") == "cc"
        and frame.get("channel") == 0
        and frame.get("data1") == 0x21
        and frame.get("data2") != 64
    ]
    assert jog_frames, (
        "no left-jog FLX4 CC33 frame captured. "
        f"Captured frames={frames!r}. Nudge the left jog wheel during the run."
    )
    frame = jog_frames[0]

    runtime, progress, controller_state, midi_mirror = _runtime_with_flx4()
    router = IpcRouterBus()
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )
    assert asyncio.run(
        _dispatch(
            router,
            {
                "type": "ipc.learn.start_lesson",
                "payload": {"lesson_id": "L1.07", "level": "fresh"},
            },
        )
    ) is True

    controller_state.handle_msg(
        SimpleNamespace(
            type="control_change",
            channel=frame["channel"],
            control=frame["data1"],
            value=frame["data2"],
        )
    )
    pulse = midi_mirror.snapshot()
    assert pulse is not None
    assert pulse["payload"]["positions"]["jog:A"] == 127

    assert asyncio.run(
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
    ) is True
    assert runtime.current_state.id in {"advancing", "completed"}

