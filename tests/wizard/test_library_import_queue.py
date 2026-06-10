# SPDX-License-Identifier: Apache-2.0
"""WizardLoop ipc.library.import → pending-marker queue (lane A 2026-06-10).

The wizard sidecar exits on ipc.wizard.done, so it must NOT run the real
multi-minute CLAP import. It queues the chosen source under
ConfigStore.extra["pending_library_import"] for the live runtime's first
boot and acks with a terminal import_progress frame so the wizard card
resolves instead of hanging forever.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from tests.wizard.conftest import FakeBus
from vibemix.runtime.config_store import PENDING_LIBRARY_IMPORT_KEY, load_config
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


def _import_msg(path: str) -> dict:
    return {
        "type": "ipc.library.import",
        "ts": "2026-06-10T00:00:00+00:00",
        "payload": {"path": path, "schema_version": "1"},
    }


def test_import_persists_pending_marker_and_acks_terminal(fake_bus: FakeBus) -> None:
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    assert "ipc.library.import" in fake_bus.handlers
    assert "ipc.library.import_cancel" in fake_bus.handlers

    _drive(fake_bus, _import_msg("/Users/x/Music/crates"))

    assert load_config().extra[PENDING_LIBRARY_IMPORT_KEY] == "/Users/x/Music/crates"
    frames = fake_bus.emitted_by_type("ipc.library.import_progress")
    assert len(frames) == 1
    # total=0 + cancelled=False is the wizard card's terminal "music feed
    # started" shape (step-library-feed.ts progressCopy).
    assert frames[0]["payload"]["total"] == 0
    assert frames[0]["payload"]["cancelled"] is False


def test_import_rejects_missing_path_with_ipc_error(fake_bus: FakeBus) -> None:
    loop = WizardLoop(fake_bus)
    loop.register_handlers()

    _drive(
        fake_bus,
        {
            "type": "ipc.library.import",
            "ts": "2026-06-10T00:00:00+00:00",
            "payload": {"path": " ", "schema_version": "1"},
        },
    )

    errors = fake_bus.emitted_by_type("ipc.error")
    assert errors and "path" in errors[0]["payload"]["reason"]
    assert PENDING_LIBRARY_IMPORT_KEY not in load_config().extra


def test_cancel_clears_pending_marker(fake_bus: FakeBus) -> None:
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(fake_bus, _import_msg("/Users/x/Music/crates"))

    _drive(
        fake_bus,
        {
            "type": "ipc.library.import_cancel",
            "ts": "2026-06-10T00:00:01+00:00",
            "payload": {"schema_version": "1"},
        },
    )

    assert PENDING_LIBRARY_IMPORT_KEY not in load_config().extra
    frames = fake_bus.emitted_by_type("ipc.library.import_progress")
    assert frames[-1]["payload"]["cancelled"] is True
