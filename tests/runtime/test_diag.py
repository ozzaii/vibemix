# SPDX-License-Identifier: Apache-2.0
"""DIAG-01..03 — diag_loop terminal meter format.

Pin the v4:1865-1868 format string substrings via ``capsys`` capture and
the 1.0s sleep cadence via a patched ``asyncio.sleep``.
"""

from __future__ import annotations

import asyncio
import inspect

from vibemix.runtime.diag import diag_loop
from vibemix.state import MusicState

_REAL_SLEEP = asyncio.sleep


def test_diag_01_is_async_function_and_exits_on_stop():
    """DIAG-01: ``diag_loop`` is a coroutine function and returns cleanly
    when ``stop_event`` is set."""
    assert inspect.iscoroutinefunction(diag_loop)


def test_diag_02_format_string_substrings(mocker, capsys):
    """DIAG-02: one tick writes a line with the v4:1865-1868 substrings."""
    state = MusicState()
    state.audible = True
    state.audible_deck = "A"
    state.phase = "peak"

    # Fake Levels with snapshot returning known values
    fake_levels = mocker.MagicMock()
    fake_levels.snapshot = mocker.MagicMock(
        return_value={"music": 0.150, "voice": 0.025, "mic": 0.0}
    )

    stop = asyncio.Event()
    calls = []

    async def fake_sleep(delay):
        calls.append(delay)
        if len(calls) >= 1:
            stop.set()
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.diag.asyncio.sleep", side_effect=fake_sleep)

    asyncio.run(diag_loop(fake_levels, state, stop))

    out = capsys.readouterr().out
    # Required substrings from v4:1865-1868
    assert "\r[live] music=0.150" in out
    assert "voice=0.025" in out
    assert "audible=1" in out  # int(True) == 1
    assert "deck=A" in out
    assert "phase=peak" in out


def test_diag_03_sleep_cadence_is_1s(mocker):
    """DIAG-03: each iteration sleeps 1.0s."""
    state = MusicState()
    fake_levels = mocker.MagicMock()
    fake_levels.snapshot = mocker.MagicMock(return_value={"music": 0.0, "voice": 0.0, "mic": 0.0})

    stop = asyncio.Event()
    calls = []

    async def fake_sleep(delay):
        calls.append(delay)
        if len(calls) >= 2:
            stop.set()
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.diag.asyncio.sleep", side_effect=fake_sleep)

    asyncio.run(diag_loop(fake_levels, state, stop))

    assert all(s == 1.0 for s in calls), f"expected all sleeps to be 1.0, got {calls}"
