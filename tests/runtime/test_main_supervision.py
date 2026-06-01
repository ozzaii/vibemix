# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import asyncio

from vibemix import __main__ as main_mod


class _Tracer:
    def __init__(self) -> None:
        self.errors: list[tuple[str, dict]] = []

    def error(self, event: str, **detail: object) -> None:
        self.errors.append((event, detail))


def test_ws_broadcast_supervisor_restarts_after_crash() -> None:
    tracer = _Tracer()

    async def _run() -> int:
        stop = asyncio.Event()
        calls = 0

        async def broadcast_once() -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("bus boom")
            stop.set()

        async def sleep(_delay: float) -> None:
            await asyncio.sleep(0)

        await main_mod._run_ws_broadcast_supervised(
            broadcast_once,
            stop,
            tracer,
            retry_delay_s=0.01,
            sleep=sleep,
        )
        return calls

    assert asyncio.run(_run()) == 2
    assert tracer.errors == [
        ("ws_broadcast_crashed", {"err": "RuntimeError('bus boom')"})
    ]


def test_ws_broadcast_supervisor_propagates_cancellation() -> None:
    async def _run() -> None:
        stop = asyncio.Event()

        async def broadcast_once() -> None:
            raise asyncio.CancelledError

        await main_mod._run_ws_broadcast_supervised(
            broadcast_once,
            stop,
            _Tracer(),
            retry_delay_s=0.01,
        )

    try:
        asyncio.run(_run())
    except asyncio.CancelledError:
        return
    raise AssertionError("CancelledError should propagate")


def test_task_crash_observer_records_original_task_name() -> None:
    tracer = _Tracer()

    async def _run() -> None:
        async def fail(label: str) -> None:
            raise RuntimeError(label)

        first = asyncio.create_task(fail("first"))
        second = asyncio.create_task(fail("second"))
        main_mod._attach_task_crash_observers(
            tracer,
            (("first_task", first), ("second_task", second)),
        )
        await asyncio.gather(first, second, return_exceptions=True)
        await asyncio.sleep(0)

    asyncio.run(_run())

    assert tracer.errors == [
        ("task_crashed", {"task": "first_task", "err": "RuntimeError('first')"}),
        ("task_crashed", {"task": "second_task", "err": "RuntimeError('second')"}),
    ]


def test_task_crash_observer_ignores_cancelled_and_successful_tasks() -> None:
    tracer = _Tracer()

    async def _run() -> None:
        async def ok() -> None:
            return None

        async def wait_forever() -> None:
            await asyncio.Event().wait()

        success = asyncio.create_task(ok())
        cancelled = asyncio.create_task(wait_forever())
        main_mod._attach_task_crash_observers(
            tracer,
            (("success", success), ("cancelled", cancelled)),
        )
        await success
        cancelled.cancel()
        await asyncio.gather(cancelled, return_exceptions=True)
        await asyncio.sleep(0)

    asyncio.run(_run())

    assert tracer.errors == []
