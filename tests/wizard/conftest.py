# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures for the Phase 11 Wave 4 wizard test suite.

The WizardLoop talks to an injected ``WizardBus``. Tests use ``FakeBus``
(below) — same surface as the real bus, but ``emit`` just appends the
message to a list and ``register_handler`` records the mapping. This lets
tests assert on emitted payloads and drive the loop by calling registered
handlers directly without standing up a real WebSocket server.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import pytest


class FakeBus:
    """In-memory stand-in for ``vibemix.runtime.ws_bus.WizardBus``.

    Records ``register_handler`` calls + every ``emit`` payload. Tests use
    ``emitted_by_type(name)`` to find a specific reply, or
    ``last_emitted_type()`` for sequencing assertions.
    """

    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[dict], Awaitable[None]]] = {}
        self.emitted: list[dict] = []
        self.started = False
        self.stopped = False

    def register_handler(
        self, message_type: str, handler: Callable[[dict], Awaitable[None]]
    ) -> None:
        self.handlers[message_type] = handler

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def emit(self, msg: dict) -> None:
        # Validate against the real schema so any schema-shape regression
        # in the wizard handlers surfaces here too.
        from vibemix.ui_bus.validator import validate_message

        validate_message(msg)
        # Deep-copy via json roundtrip so a frozen dataclass can be
        # asserted on later without test-order coupling.
        self.emitted.append(json.loads(json.dumps(msg)))

    def emitted_by_type(self, msg_type: str) -> list[dict]:
        return [m for m in self.emitted if m.get("type") == msg_type]


@pytest.fixture
def fake_bus() -> FakeBus:
    """Fresh FakeBus per test."""
    return FakeBus()


@pytest.fixture
def mock_permissions(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Patch ``vibemix.platform.permissions`` so tests don't probe the OS.

    Returns a dict the test can mutate to switch the next probe's return.
    Default: both authorized (matches Kaan's rig).
    """
    state: dict[str, str] = {
        "screen_recording": "authorized",
        "microphone": "authorized",
    }

    def _check_screen() -> str:
        return state["screen_recording"]

    def _check_mic() -> str:
        return state["microphone"]

    def _request_mic() -> None:
        return None

    import sys

    # Patch the selector module (vibemix.platform.permissions resolves at
    # module import time). Re-bind the functions in-place.
    permissions = pytest.importorskip("vibemix.platform.permissions")
    monkeypatch.setattr(permissions, "check_screen_recording_permission", _check_screen)
    monkeypatch.setattr(permissions, "check_microphone_permission", _check_mic)
    monkeypatch.setattr(permissions, "request_microphone_permission", _request_mic)
    # Some handlers do ``from vibemix.platform import permissions`` inside
    # function bodies — the monkeypatch above hits the same module instance.
    _ = sys  # silence-unused
    return state


@pytest.fixture
def mock_platform_windows(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Patch ``vibemix.platform.windows.enumerate_windows`` to return an
    injectable list (Warning #4 — WS path coverage).

    Returns the list the test mutates; default is empty.
    """
    from vibemix.platform import windows as platform_windows

    injected: list[Any] = []

    def _fake_enumerate():
        return list(injected)

    monkeypatch.setattr(platform_windows, "enumerate_windows", _fake_enumerate)
    return injected


@pytest.fixture
def mock_sounddevice(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch ``sounddevice.query_devices`` + ``play`` + ``wait`` so tests
    don't touch real audio. Mutate ``devices`` to control what list_devices
    returns; mutate ``query_device_info`` to control probe_audio's
    sample-rate read.
    """
    import sounddevice as sd

    state: dict[str, Any] = {
        "devices": [
            {"name": "BlackHole 2ch", "max_output_channels": 2, "default_samplerate": 48000.0},
            {"name": "AirPods Pro", "max_output_channels": 2, "default_samplerate": 48000.0},
        ],
        "query_device_info": {"name": "AirPods Pro", "default_samplerate": 48000.0},
        "play_called": False,
        "wait_called": False,
    }

    def _query_devices(idx: int | None = None):
        if idx is None:
            return state["devices"]
        return state["query_device_info"]

    def _play(*_args, **_kwargs) -> None:
        state["play_called"] = True

    def _wait() -> None:
        state["wait_called"] = True

    monkeypatch.setattr(sd, "query_devices", _query_devices)
    monkeypatch.setattr(sd, "play", _play)
    monkeypatch.setattr(sd, "wait", _wait)
    return state
