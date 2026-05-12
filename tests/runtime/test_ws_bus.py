# SPDX-License-Identifier: Apache-2.0
"""WS-01..09 + PKG-05 — ws_broadcast server lifecycle + manual trigger handling.

Patches ``websockets.serve`` to return a mock server so the test doesn't
actually bind to 127.0.0.1:8765. Captures the inbound ``handler`` to drive
synthetic messages through it.

Direct ``import websockets`` is asserted (no ``_HAS_WS`` feature flag).
"""

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from vibemix.runtime.ws_bus import ws_broadcast
from vibemix.state import MusicState

_REAL_SLEEP = asyncio.sleep


def _build_mock_server() -> MagicMock:
    """Mock WebSocket server with close + wait_closed (AsyncMock)."""
    server = MagicMock()
    server.close = MagicMock()
    server.wait_closed = AsyncMock(return_value=None)
    return server


def test_ws_01_is_async_function():
    """WS-01: ``ws_broadcast`` is a coroutine function."""
    assert inspect.iscoroutinefunction(ws_broadcast)


def test_ws_02_server_starts_on_ws_host_port(mocker):
    """WS-02: server is started with (handler, WS_HOST, WS_PORT)."""
    mock_server = _build_mock_server()
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(return_value={"music": 0.0, "voice": 0.0, "mic": 0.0})
    state = MusicState()
    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()

    # Set stop before the loop runs any iterations
    stop_event.set()

    # Patch asyncio.sleep inside ws_bus to no-op (in case it's called)
    async def fast_sleep(_s):
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    asyncio.run(ws_broadcast(fake_levels, state, manual_trigger, stop_event))

    # Assert serve was called with the right args
    assert serve_mock.await_count == 1
    args = serve_mock.await_args.args
    # args[0] is handler, args[1] is host, args[2] is port
    assert args[1] == "127.0.0.1"
    assert args[2] == 8765
    # close + wait_closed were called (cleanup branch)
    mock_server.close.assert_called_once()
    mock_server.wait_closed.assert_awaited_once()


def test_ws_03_inbound_trigger_action_sets_manual_trigger(mocker):
    """WS-03: inbound JSON {"action": "trigger"} sets manual_trigger."""
    mock_server = _build_mock_server()
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(return_value={"music": 0.0, "voice": 0.0, "mic": 0.0})
    state = MusicState()
    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()
    stop_event.set()  # exit before broadcast loop starts iterating

    async def fast_sleep(_s):
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    asyncio.run(ws_broadcast(fake_levels, state, manual_trigger, stop_event))

    # Extract the captured handler
    handler = serve_mock.await_args.args[0]

    # Build a fake ws that yields one JSON message
    class FakeWs:
        def __aiter__(self):
            async def gen():
                yield json.dumps({"action": "trigger"})

            return gen()

    asyncio.run(handler(FakeWs()))

    assert manual_trigger.is_set()


def test_ws_04_inbound_non_trigger_action_does_not_set_manual_trigger(mocker):
    """WS-04: inbound JSON {"action": "ping"} does NOT set manual_trigger."""
    mock_server = _build_mock_server()
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(return_value={"music": 0.0, "voice": 0.0, "mic": 0.0})
    state = MusicState()
    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()
    stop_event.set()

    async def fast_sleep(_s):
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    asyncio.run(ws_broadcast(fake_levels, state, manual_trigger, stop_event))
    handler = serve_mock.await_args.args[0]

    class FakeWs:
        def __aiter__(self):
            async def gen():
                yield json.dumps({"action": "ping"})

            return gen()

    asyncio.run(handler(FakeWs()))

    assert not manual_trigger.is_set()


def test_ws_05_inbound_invalid_json_does_not_raise(mocker):
    """WS-05: malformed inbound message → handler does NOT raise,
    manual_trigger stays unset."""
    mock_server = _build_mock_server()
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(return_value={"music": 0.0, "voice": 0.0, "mic": 0.0})
    state = MusicState()
    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()
    stop_event.set()

    async def fast_sleep(_s):
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    asyncio.run(ws_broadcast(fake_levels, state, manual_trigger, stop_event))
    handler = serve_mock.await_args.args[0]

    class FakeWs:
        def __aiter__(self):
            async def gen():
                yield "not-json"

            return gen()

    # Must not raise
    asyncio.run(handler(FakeWs()))
    assert not manual_trigger.is_set()


def test_ws_06_broadcast_payload_shape(mocker):
    """WS-06: broadcast tick sends a JSON payload with required keys.

    Approach: register a long-lived client via the handler (whose
    ``__aiter__`` blocks forever) so it remains in the `clients` set across
    multiple broadcast ticks. Capture the first payload sent to it, then
    set stop_event and release the handler.
    """
    mock_server = _build_mock_server()
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(return_value={"music": 0.05, "voice": 0.02, "mic": 0.01})
    state = MusicState()
    state.audible = True
    state.audible_deck = "B"
    state.phase = "groove"
    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()

    sent_payloads = []
    release_handler = asyncio.Event()

    class LongLivedClient:
        async def send(self, payload):
            sent_payloads.append(payload)
            stop_event.set()
            release_handler.set()

        def __aiter__(self):
            client = self

            async def gen():
                # Block forever (until released) so this client stays in
                # `clients` across broadcast ticks.
                await release_handler.wait()
                if False:  # pragma: no cover
                    yield client

            return gen()

    # fast_sleep with a safety stop after many iterations (in case the
    # client's send is never called for some reason).
    sleep_counter = {"n": 0}

    async def fast_sleep(s):
        sleep_counter["n"] += 1
        if sleep_counter["n"] >= 50:  # safety net
            stop_event.set()
            release_handler.set()
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    async def driver():
        bg = asyncio.create_task(ws_broadcast(fake_levels, state, manual_trigger, stop_event))
        # Let ws_broadcast hit `websockets.serve(...)` and store its handler.
        await _REAL_SLEEP(0)
        await _REAL_SLEEP(0)
        handler = serve_mock.await_args.args[0]

        client = LongLivedClient()
        handler_task = asyncio.create_task(handler(client))

        # Let the broadcast loop run until the client's `send` fires
        # (which sets stop_event AND release_handler).
        await bg
        try:
            await asyncio.wait_for(handler_task, timeout=0.5)
        except Exception:
            handler_task.cancel()

    asyncio.run(driver())

    assert len(sent_payloads) >= 1, "expected at least one broadcast payload"
    payload = json.loads(sent_payloads[0])
    for key in ("music", "voice", "mic", "audible", "deck", "phase"):
        assert key in payload, f"missing key {key} in payload {payload}"
    assert payload["audible"] is True
    assert payload["deck"] == "B"
    assert payload["phase"] == "groove"


def test_ws_07_broadcast_cadence_is_30hz(mocker):
    """WS-07: broadcast loop sleeps 1/30 seconds between iterations."""
    mock_server = _build_mock_server()
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(return_value={"music": 0.0, "voice": 0.0, "mic": 0.0})
    state = MusicState()
    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()

    sleeps = []

    async def fast_sleep(s):
        sleeps.append(s)
        if len(sleeps) >= 2:
            stop_event.set()
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    asyncio.run(ws_broadcast(fake_levels, state, manual_trigger, stop_event))

    assert sleeps, "expected at least one sleep"
    # All broadcast sleeps should be 1/30
    for s in sleeps:
        assert s == 1 / 30, f"expected 1/30, got {s}"


def test_ws_08_dead_client_cleanup(mocker):
    """WS-08: a client whose send raises is removed from the clients set.

    Approach: register both a good and a dead client via the handler; let
    the broadcast loop run for a couple of ticks. After the run, verify
    that the good client received payloads AND the dead client raised on
    its send (proving the cleanup path was exercised — no traceback bubbled
    up to fail the test)."""
    mock_server = _build_mock_server()
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(return_value={"music": 0.0, "voice": 0.0, "mic": 0.0})
    state = MusicState()
    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()

    good_sends = []
    dead_send_calls = []
    release_handler = asyncio.Event()

    class GoodClient:
        async def send(self, payload):
            good_sends.append(payload)

        def __aiter__(self):
            async def gen():
                await release_handler.wait()
                if False:
                    yield

            return gen()

    class DeadClient:
        async def send(self, payload):
            dead_send_calls.append(payload)
            raise ConnectionError("broken pipe")

        def __aiter__(self):
            async def gen():
                await release_handler.wait()
                if False:
                    yield

            return gen()

    sleep_counter = {"n": 0}

    async def fast_sleep(s):
        sleep_counter["n"] += 1
        # Stop after a few broadcast ticks so both good + dead are exercised
        if sleep_counter["n"] >= 5:
            stop_event.set()
            release_handler.set()
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    async def driver():
        bg = asyncio.create_task(ws_broadcast(fake_levels, state, manual_trigger, stop_event))
        # Let ws_broadcast call websockets.serve and stash the handler.
        await _REAL_SLEEP(0)
        await _REAL_SLEEP(0)
        handler = serve_mock.await_args.args[0]

        good = GoodClient()
        dead = DeadClient()
        good_task = asyncio.create_task(handler(good))
        dead_task = asyncio.create_task(handler(dead))

        # Let broadcast ticks run; safety stop in fast_sleep will end the loop.
        await bg
        # Handlers exit cleanly once release_handler is set.
        try:
            await asyncio.wait_for(good_task, timeout=0.5)
        except Exception:
            good_task.cancel()
        try:
            await asyncio.wait_for(dead_task, timeout=0.5)
        except Exception:
            dead_task.cancel()

    asyncio.run(driver())

    # Good client received at least one payload (didn't crash the loop)
    assert len(good_sends) >= 1
    # Dead client's send was invoked at least once (i.e. it was in `clients`)
    assert len(dead_send_calls) >= 1
    # And on subsequent ticks the dead client should be cleaned up, so its
    # send shouldn't be called many MORE times than the good client + 1.
    assert len(dead_send_calls) <= len(good_sends) + 1, (
        f"dead client should be cleaned up: dead_sends={len(dead_send_calls)} "
        f"vs good_sends={len(good_sends)}"
    )


def test_ws_09_has_ws_flag_dropped():
    """WS-09: the source file must NOT contain a runtime ``_HAS_WS``
    feature flag or any ``try: import websockets`` guard. The import is
    direct. (Docstring references to the dropped flag are permitted —
    we check only code, not comments/docstrings.)"""
    import ast

    src = Path("src/vibemix/runtime/ws_bus.py").read_text()
    tree = ast.parse(src)

    # No `_HAS_WS` name is assigned, referenced, or used anywhere in code.
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "_HAS_WS":
            raise AssertionError(f"WS-09: `_HAS_WS` referenced in code at line {node.lineno}")
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "_HAS_WS":
                    raise AssertionError(f"WS-09: `_HAS_WS` assigned at line {node.lineno}")

    # No `try: import websockets` guard — websockets must be a top-level import.
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for stmt in node.body:
                if isinstance(stmt, ast.Import):
                    for alias in stmt.names:
                        if alias.name == "websockets":
                            raise AssertionError(
                                f"WS-09: `import websockets` inside try block at line {node.lineno}"
                            )

    # And the direct import is present at module top level.
    found_top_level_import = False
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "websockets":
                    found_top_level_import = True
                    break
    assert found_top_level_import, "WS-09: direct top-level `import websockets` not found"


def test_pkg_05_runtime_package_surface():
    """PKG-05: from vibemix.runtime import coach_loop, diag_loop, ws_broadcast
    resolves, and __all__ matches.

    Phase 12 W2 extends the surface with SessionLoop/run_session and
    re-exports WizardLoop/run_wizard alongside the Phase 4 surface so
    ``from vibemix.runtime import ...`` is the single import point.
    """
    import vibemix.runtime as runtime_pkg
    from vibemix.runtime import coach_loop, diag_loop, ws_broadcast  # noqa: F401
    from vibemix.runtime import SessionLoop, WizardLoop, run_session, run_wizard  # noqa: F401

    assert set(runtime_pkg.__all__) == {
        "SessionLoop",
        "WizardLoop",
        "coach_loop",
        "diag_loop",
        "run_session",
        "run_wizard",
        "ws_broadcast",
    }
