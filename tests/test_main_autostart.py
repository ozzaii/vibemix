# SPDX-License-Identifier: Apache-2.0
"""Headless autostart (``VIBEMIX_AUTOSTART=1``) coverage.

The packaged GUI activates the live co-host only on a user Start click; the
start gate stays armed otherwise. Replay/soak QA has no UI to click, so the
replay runner relied on an auto-activation that did not exist — every replay sat
at the armed gate and produced zero events (``recorded_input_duration_s == 0``).

These tests pin a single, opt-in, env-gated autostart: when ``VIBEMIX_AUTOSTART``
is truthy the app fires exactly one ``session.start`` after the gate arms. The
flag is never set by the packaged app (and ``open -a`` strips env), so a user
click stays the only activation path in production.
"""

from __future__ import annotations

import asyncio

from vibemix.__main__ import _autostart_enabled, _autostart_session


def test_autostart_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("VIBEMIX_AUTOSTART", raising=False)
    assert _autostart_enabled() is False


def test_autostart_enabled_when_flag_truthy(monkeypatch) -> None:
    for value in ("1", "true", "YES", "on"):
        monkeypatch.setenv("VIBEMIX_AUTOSTART", value)
        assert _autostart_enabled() is True


def test_autostart_disabled_when_flag_falsey(monkeypatch) -> None:
    for value in ("0", "false", "no", "off", ""):
        monkeypatch.setenv("VIBEMIX_AUTOSTART", value)
        assert _autostart_enabled() is False


def test_autostart_session_fires_start_once() -> None:
    calls: list[str] = []

    async def _start() -> None:
        calls.append("start")

    async def _drive() -> None:
        stop = asyncio.Event()
        await _autostart_session(_start, stop_event=stop, settle_s=0.0)

    asyncio.run(_drive())
    assert calls == ["start"]


def test_autostart_session_skips_when_already_stopping() -> None:
    calls: list[str] = []

    async def _start() -> None:
        calls.append("start")

    async def _drive() -> None:
        stop = asyncio.Event()
        stop.set()  # app already shutting down → must NOT activate
        await _autostart_session(_start, stop_event=stop, settle_s=0.0)

    asyncio.run(_drive())
    assert calls == []


def test_autostart_session_never_crashes_on_start_failure() -> None:
    async def _start() -> None:
        raise RuntimeError("activation boom")

    async def _drive() -> None:
        stop = asyncio.Event()
        # Must swallow — a failed autostart can never take down the app.
        await _autostart_session(_start, stop_event=stop, settle_s=0.0)

    asyncio.run(_drive())  # no exception propagates
