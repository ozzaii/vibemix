# SPDX-License-Identifier: Apache-2.0
"""Learn beginner path over the real ws_broadcast IPC route."""

from __future__ import annotations

import asyncio
import contextlib
import json
import socket
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import websockets

from vibemix.audio import WS_HOST, Levels
from vibemix.learn.ipc_handlers import register_learn_handlers
from vibemix.learn.progress import LearnProgress, load_progress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.runtime import ws_bus as ws_bus_mod
from vibemix.runtime.ws_bus import IpcRouterBus, ws_broadcast
from vibemix.state import MusicState


@pytest.fixture
def progress_path_in_tmp(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Path:
    target = tmp_path / "learn-progress.json"
    monkeypatch.setattr(
        "vibemix.learn.progress.progress_path",
        lambda: target,
    )
    return target


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((WS_HOST, 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


class _RuntimeEmitAdapter:
    """Sync emit facade matching the live __main__.py LessonRuntime adapter."""

    def __init__(self, router: IpcRouterBus) -> None:
        self._router = router
        self._tasks: set[asyncio.Task] = set()

    def emit(self, msg: dict) -> None:
        task = asyncio.create_task(self._router.emit(msg))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)


def _make_runtime(router: IpcRouterBus) -> tuple[LessonRuntime, LearnProgress]:
    progress = LearnProgress()
    midi_mirror = MagicMock(name="midi_mirror")
    midi_mirror.current_profile.return_value = None
    controller_state = MagicMock(name="controller_state")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=midi_mirror,
        controller_state=controller_state,
        ipc_router=_RuntimeEmitAdapter(router),
        progress_store=progress,
    )
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )
    return runtime, progress


def _envelope(message_type: str, payload: dict) -> str:
    return json.dumps(
        {
            "type": message_type,
            "ts": datetime.now(UTC).isoformat(),
            "payload": payload,
        },
        separators=(",", ":"),
    )


async def _recv_type(ws: websockets.WebSocketClientProtocol, message_type: str) -> dict:
    deadline = asyncio.get_event_loop().time() + 3.0
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise AssertionError(f"timed out waiting for {message_type}")
        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        msg = json.loads(raw)
        if msg.get("type") == message_type:
            return msg


async def _continue(ws: websockets.WebSocketClientProtocol) -> None:
    await ws.send(
        _envelope(
            "ipc.learn.ack",
            {
                "control_id": "lesson_continue",
                "source": "click",
                "value": 127,
                "prev_value": 0,
                "direction": "down",
            },
        )
    )


def test_beginner_path_completes_over_real_ws_bus(
    monkeypatch: pytest.MonkeyPatch,
    progress_path_in_tmp: Path,
) -> None:
    """Start and complete L1.01 through a real WebSocket client."""

    async def run() -> None:
        port = _free_port()
        monkeypatch.setattr(ws_bus_mod, "WS_PORT", port)

        router = IpcRouterBus()
        runtime, progress = _make_runtime(router)
        stop_event = asyncio.Event()
        server_task = asyncio.create_task(
            ws_broadcast(
                Levels(),
                MusicState(),
                asyncio.Event(),
                stop_event,
                ipc_router=router,
            )
        )
        await asyncio.sleep(0.1)

        try:
            async with websockets.connect(f"ws://{WS_HOST}:{port}") as ws:
                await ws.send(
                    _envelope(
                        "ipc.learn.start_lesson",
                        {"lesson_id": "L1.01", "level": "fresh"},
                    )
                )

                loaded = await _recv_type(ws, "ipc.learn.lesson_loaded")
                assert loaded["payload"]["lesson_id"] == "L1.01"
                assert await _recv_type(ws, "ipc.learn.highlight")
                first_tutor = await _recv_type(ws, "ipc.learn.tutor_speak")
                assert first_tutor["payload"]["text"] == "Hello vibemix, what are you?"

                for expected_step in (
                    "L1.01.beat.1",
                    "L1.01.beat.2",
                    "L1.01.beat.3",
                ):
                    await _continue(ws)
                    advance = await _recv_type(ws, "ipc.learn.advance")
                    assert advance["payload"]["lesson_id"] == "L1.01"
                    assert await _recv_type(ws, "ipc.learn.highlight")
                    await _recv_type(ws, "ipc.learn.tutor_speak")
                    assert runtime.current_step_id == expected_step

                runtime._learn.lesson_started_at = time.monotonic() - 45.0
                await _continue(ws)
                await _recv_type(ws, "ipc.learn.advance")
                complete = await _recv_type(ws, "ipc.learn.complete_lesson")
                progress_state = await _recv_type(ws, "ipc.learn.progress_state")

                assert complete["payload"] == {
                    "lesson_id": "L1.01",
                    "reason": "completed",
                }
                assert progress_state["payload"]["progress"]["lessons"]["L1.01"][
                    "completed"
                ] is True
        finally:
            stop_event.set()
            await server_task
            if runtime._finish_task is not None and not runtime._finish_task.done():
                runtime._finish_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await runtime._finish_task

        assert progress_path_in_tmp.exists()
        assert progress.lessons["L1.01"]["completed"] is True
        reloaded, was_corrupt = load_progress()
        assert was_corrupt is False
        assert reloaded.lessons["L1.01"]["completed"] is True

    asyncio.run(run())
