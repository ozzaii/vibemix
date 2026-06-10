# SPDX-License-Identifier: Apache-2.0
"""WizardLoop.ipc.telemetry.set_consent persistence coverage."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from tests.wizard.conftest import FakeBus
from vibemix.runtime.config_store import ConfigStore, load_config, save_config
from vibemix.runtime.wizard import WizardLoop


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    if sys.platform == "win32":
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("APPDATA", str(tmp_path))
    yield


def _drive(bus: FakeBus, msg: dict) -> None:
    handler = bus.handlers[msg["type"]]
    asyncio.run(handler(msg))


def test_telemetry_set_consent_persists_true(fake_bus: FakeBus) -> None:
    loop = WizardLoop(fake_bus)
    loop.register_handlers()

    _drive(
        fake_bus,
        {
            "type": "ipc.telemetry.set_consent",
            "ts": "2026-06-02T00:00:00+00:00",
            "payload": {"consent": True},
        },
    )

    assert load_config().telemetry_consent is True


def test_telemetry_set_consent_persists_false(fake_bus: FakeBus) -> None:
    save_config(ConfigStore(telemetry_consent=True))
    loop = WizardLoop(fake_bus)
    loop.register_handlers()

    _drive(
        fake_bus,
        {
            "type": "ipc.telemetry.set_consent",
            "ts": "2026-06-02T00:00:00+00:00",
            "payload": {"consent": False},
        },
    )

    assert load_config().telemetry_consent is False


def test_telemetry_consent_stays_default_off_without_message() -> None:
    assert load_config().telemetry_consent is False
