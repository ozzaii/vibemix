# SPDX-License-Identifier: Apache-2.0
"""Contracts for the live on-screen Learn socket probe."""

from __future__ import annotations

import asyncio
import contextlib
import socket
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

from scripts import live_learn_screen_probe as probe

from vibemix.audio import WS_HOST, Levels
from vibemix.learn.ipc_handlers import register_learn_handlers
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
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


def _runtime(router: IpcRouterBus) -> tuple[LessonRuntime, _RuntimeEmitAdapter]:
    progress = LearnProgress()
    midi_mirror = MagicMock(name="midi_mirror")
    midi_mirror.current_profile.return_value = None
    adapter = _RuntimeEmitAdapter(router)
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=midi_mirror,
        controller_state=MagicMock(name="controller_state"),
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
    return runtime, adapter


async def _keep_dwell_unlocked(runtime: LessonRuntime, stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        if runtime._learn.current_lesson_id:
            runtime._learn.lesson_started_at = time.monotonic() - 45.0
        await asyncio.sleep(0.02)


def test_progress_matcher_requires_completed_lesson_row() -> None:
    assert probe.progress_marks_completed(
        {
            "type": "ipc.learn.progress_state",
            "payload": {
                "progress": {
                    "lessons": {
                        "L1.01": {
                            "completed": True,
                            "completed_at": "2026-05-29T00:00:00Z",
                            "strikes_used": 0,
                        }
                    }
                }
            },
        }
    )
    assert not probe.progress_marks_completed(
        {
            "type": "ipc.learn.progress_state",
            "payload": {"progress": {"lessons": {"L1.01": {"completed": False}}}},
        }
    )
    assert not probe.progress_marks_completed({"type": "ipc.learn.tutor_speak"})


def test_probe_help_runs_when_invoked_by_script_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "scripts/live_learn_screen_probe.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert proc.returncode == 0
    assert "ws://127.0.0.1:8765" in proc.stdout
    assert "45s Learn dwell" in proc.stdout


def test_screen_probe_completes_l1_01_over_real_ws_bus(
    monkeypatch,
) -> None:
    async def run() -> None:
        port = _free_port()
        monkeypatch.setattr(ws_bus_mod, "WS_PORT", port)
        router = IpcRouterBus()
        runtime, adapter = _runtime(router)
        stop_event = asyncio.Event()
        bus_task = asyncio.create_task(
            ws_broadcast(
                Levels(),
                MusicState(),
                asyncio.Event(),
                stop_event,
                ipc_router=router,
            )
        )
        dwell_task = asyncio.create_task(_keep_dwell_unlocked(runtime, stop_event))
        await asyncio.sleep(0.1)

        try:
            summary = await probe.run_screen_probe(
                url=f"ws://{WS_HOST}:{port}",
                seconds=4.0,
            )
        finally:
            stop_event.set()
            dwell_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await dwell_task
            await adapter.drain()
            if runtime._finish_task is not None and not runtime._finish_task.done():
                runtime._finish_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await runtime._finish_task
            await bus_task

        assert summary["passed"] is True
        assert summary["lesson_loaded"] is True
        assert summary["lesson_loaded_controller_id"] == "pioneer_ddj_flx4"
        assert summary["acks_sent"] == probe.CONTINUE_ACKS_REQUIRED
        assert summary["advance_count"] >= probe.CONTINUE_ACKS_REQUIRED
        assert summary["complete_seen"] is True
        assert summary["progress_completed"] is True
        assert runtime.current_state.id == "completed"

    asyncio.run(run())
