# SPDX-License-Identifier: Apache-2.0
"""Test-only Learn sidecar harness for browser integration checks."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal
import time
from pathlib import Path
from unittest.mock import MagicMock

from vibemix.audio import Levels
from vibemix.learn import progress as progress_mod
from vibemix.learn.ipc_handlers import register_learn_handlers
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.runtime import ws_bus as ws_bus_mod
from vibemix.runtime.ws_bus import IpcRouterBus, ws_broadcast
from vibemix.state import MusicState


class RuntimeEmitAdapter:
    """Sync emit facade matching the live __main__.py LessonRuntime adapter."""

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


def build_runtime(router: IpcRouterBus) -> tuple[LessonRuntime, LearnProgress, RuntimeEmitAdapter]:
    progress = LearnProgress()
    midi_mirror = MagicMock(name="midi_mirror")
    midi_mirror.current_profile.return_value = None
    controller_state = MagicMock(name="controller_state")
    adapter = RuntimeEmitAdapter(router)
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
    return runtime, progress, adapter


async def keep_dwell_unlocked(
    runtime: LessonRuntime,
    stop_event: asyncio.Event,
) -> None:
    """Keep lesson completion fast in browser tests without product edits."""
    while not stop_event.is_set():
        if runtime._learn.current_lesson_id:
            runtime._learn.lesson_started_at = time.monotonic() - 45.0
        await asyncio.sleep(0.05)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--progress-path", type=Path, required=True)
    parser.add_argument("--unlock-dwell", action="store_true")
    args = parser.parse_args()

    args.progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_mod.progress_path = lambda: args.progress_path
    ws_bus_mod.WS_PORT = args.port

    router = IpcRouterBus()
    runtime, _progress, adapter = build_runtime(router)
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    bus_task = asyncio.create_task(
        ws_broadcast(
            Levels(),
            MusicState(),
            asyncio.Event(),
            stop_event,
            ipc_router=router,
        )
    )
    dwell_task: asyncio.Task | None = None
    if args.unlock_dwell:
        dwell_task = asyncio.create_task(keep_dwell_unlocked(runtime, stop_event))

    await asyncio.sleep(0.15)
    print(f"READY {args.port}", flush=True)
    try:
        await stop_event.wait()
    finally:
        stop_event.set()
        if dwell_task is not None:
            dwell_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await dwell_task
        await adapter.drain()
        if runtime._finish_task is not None and not runtime._finish_task.done():
            runtime._finish_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await runtime._finish_task
        await bus_task
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
