# SPDX-License-Identifier: Apache-2.0
"""Contracts for the live Learn socket jog probe."""

from __future__ import annotations

import asyncio
import contextlib
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from scripts import live_learn_socket_jog_probe as probe

from vibemix.audio import WS_HOST, Levels
from vibemix.learn.ipc_handlers import register_learn_handlers
from vibemix.learn.midi_mirror import MidiMirror
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.midi import ControllerState, load_profile
from vibemix.runtime import ws_bus as ws_bus_mod
from vibemix.runtime.ws_bus import IpcRouterBus, ws_broadcast
from vibemix.state import MusicState


class _RuntimeEmitAdapter:
    def __init__(self, router: IpcRouterBus) -> None:
        self._router = router
        self._tasks: set[asyncio.Task] = set()

    def emit(self, msg: dict) -> None:
        task = asyncio.create_task(self._router.emit(msg))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def drain(self) -> None:
        if not self._tasks:
            return
        await asyncio.gather(*list(self._tasks), return_exceptions=True)


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((WS_HOST, 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def _flx4_runtime(
    router: IpcRouterBus,
) -> tuple[LessonRuntime, ControllerState, MidiMirror, _RuntimeEmitAdapter]:
    profile = load_profile("pioneer_ddj_flx4")
    assert profile is not None
    controller_state = ControllerState(profile=profile)
    controller_state.mark_connected("DDJ-FLX4")
    midi_mirror = MidiMirror(controller_state=controller_state)
    midi_mirror.bind_profile(profile)
    progress = LearnProgress()
    adapter = _RuntimeEmitAdapter(router)
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=midi_mirror,
        controller_state=controller_state,
        ipc_router=adapter,
        progress_store=progress,
    )
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
        ipc_adapter=adapter,
    )
    return runtime, controller_state, midi_mirror, adapter


async def _wait_until(predicate, timeout_s: float = 2.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_s
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition did not become true before timeout")


def test_position_matcher_requires_left_jog_pulse() -> None:
    assert probe.is_left_jog_position(
        {
            "type": "ipc.learn.midi_position",
            "payload": {"controller_id": "pioneer_ddj_flx4", "positions": {"jog:A": 127}},
        }
    )
    assert not probe.is_left_jog_position(
        {
            "type": "ipc.learn.midi_position",
            "payload": {"controller_id": "pioneer_ddj_flx4", "positions": {"jog:A": 0}},
        }
    )
    assert not probe.is_left_jog_position(
        {
            "type": "ipc.learn.midi_position",
            "payload": {"controller_id": "pioneer_ddj_flx4", "positions": {"jog:B": 127}},
        }
    )


def test_probe_help_runs_when_invoked_by_script_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "scripts/live_learn_socket_jog_probe.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert proc.returncode == 0
    assert "ws://127.0.0.1:8765" in proc.stdout


def test_physical_probe_diagnosis_reports_lesson_not_loaded() -> None:
    diagnosis = probe.physical_probe_diagnosis(
        lesson_loaded=False,
        jog_position_seen=False,
        ack_sent=False,
        advance_seen=False,
        start_messages_sent=3,
    )

    assert diagnosis["code"] == "learn_lesson_not_loaded"
    assert "3 start_lesson" in diagnosis["message"]
    assert diagnosis["operator_action"]["prompt"] == "Restart the proof from a clean Learn sidecar socket."


def test_physical_probe_diagnosis_reports_loaded_but_no_jog() -> None:
    diagnosis = probe.physical_probe_diagnosis(
        lesson_loaded=True,
        jog_position_seen=False,
        ack_sent=False,
        advance_seen=False,
        start_messages_sent=1,
        midi_position_count=3,
        jog_values=[0, 0, 0],
    )

    assert diagnosis["code"] == "left_jog_not_observed"
    assert "Nudge the left jog wheel" in diagnosis["operator_action"]["prompt"]
    assert "3 midi_position" in diagnosis["message"]
    assert "jog:A values were [0]" in diagnosis["message"]


def test_say_prompt_uses_macos_say_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    class _Proc:
        pass

    def _popen(cmd, **_kwargs):
        calls.append(cmd)
        return _Proc()

    monkeypatch.setattr(probe.sys, "platform", "darwin")
    monkeypatch.setattr(probe.subprocess, "Popen", _popen)

    assert probe._say_prompt("Move the left jog wheel now.", enabled=True) is True
    assert calls == [["say", "Move the left jog wheel now."]]


def test_say_prompt_is_quiet_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    def _popen(_cmd, **_kwargs):  # pragma: no cover - should never run
        raise AssertionError("say should not be invoked")

    monkeypatch.setattr(probe.sys, "platform", "darwin")
    monkeypatch.setattr(probe.subprocess, "Popen", _popen)

    assert probe._say_prompt("Move the left jog wheel now.", enabled=False) is False


def test_socket_probe_completes_l1_07_over_real_ws_bus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        port = _free_port()
        monkeypatch.setattr(ws_bus_mod, "WS_PORT", port)
        router = IpcRouterBus()
        runtime, controller_state, midi_mirror, adapter = _flx4_runtime(router)
        stop_event = asyncio.Event()
        bus_task = asyncio.create_task(
            ws_broadcast(
                Levels(),
                MusicState(),
                asyncio.Event(),
                stop_event,
                controller_state=controller_state,
                ipc_router=router,
                midi_mirror=midi_mirror,
            )
        )
        await asyncio.sleep(0.1)

        probe_task = asyncio.create_task(
            probe.run_socket_probe(
                url=f"ws://{WS_HOST}:{port}",
                seconds=3.0,
            )
        )
        try:
            await _wait_until(
                lambda: runtime.current_state.id == "awaiting_action",
                timeout_s=5.0,
            )
            controller_state.handle_msg(
                SimpleNamespace(
                    type="control_change",
                    channel=0,
                    control=0x21,
                    value=65,
                )
            )
            summary = await probe_task
        finally:
            stop_event.set()
            await adapter.drain()
            if runtime._finish_task is not None and not runtime._finish_task.done():
                runtime._finish_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await runtime._finish_task
            await bus_task

        assert summary["passed"] is True
        assert summary["start_messages_sent"] >= 1
        assert summary["lesson_loaded"] is True
        assert summary["lesson_loaded_controller_id"] == "pioneer_ddj_flx4"
        assert summary["jog_position_seen"] is True
        assert summary["ack_sent"] is True
        assert summary["advance_seen"] is True
        assert summary["midi_position_count"] >= 1
        assert 127 in summary["jog_values"]
        assert summary["midi_position_samples"]
        assert summary["operator_prompt_spoken"] is False
        assert summary["diagnosis"]["code"] == "physical_l1_07_proven"
        assert summary["operator_action"]["prompt"] == "Physical L1.07 proof is complete."
        assert runtime.current_state.id in {"advancing", "completed"}

    asyncio.run(run())
