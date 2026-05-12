# SPDX-License-Identifier: Apache-2.0
"""ipc.permission.check handler coverage for Step 1.

Per CONTEXT D-Area-2.1:
  - macOS: screen_recording + microphone via TCC.
  - Windows: microphone only; screen_recording always authorized
    (no system-wide gate).
"""

from __future__ import annotations

import asyncio

from tests.wizard.conftest import FakeBus
from vibemix.runtime.wizard import WizardLoop


def _drive(bus: FakeBus, kind: str) -> None:
    asyncio.run(
        bus.handlers["ipc.permission.check"](
            {
                "type": "ipc.permission.check",
                "ts": "2026-05-12T08:00:00+00:00",
                "payload": {"kind": kind},
            }
        )
    )


def test_macos_microphone_authorized(
    fake_bus: FakeBus, mock_permissions: dict[str, str]
) -> None:
    """macOS authorized state surfaces as the schema-valid enum value."""
    mock_permissions["microphone"] = "authorized"
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(fake_bus, "microphone")
    states = fake_bus.emitted_by_type("ipc.permission.state")
    assert len(states) == 1
    assert states[0]["payload"] == {"kind": "microphone", "status": "authorized"}


def test_macos_microphone_denied(
    fake_bus: FakeBus, mock_permissions: dict[str, str]
) -> None:
    """Denied mic state surfaces as denied → wizard Step 1 stays gated."""
    mock_permissions["microphone"] = "denied"
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(fake_bus, "microphone")
    states = fake_bus.emitted_by_type("ipc.permission.state")
    assert states[0]["payload"]["status"] == "denied"


def test_macos_microphone_not_determined(
    fake_bus: FakeBus, mock_permissions: dict[str, str]
) -> None:
    """First-launch notDetermined state flows through cleanly."""
    mock_permissions["microphone"] = "notDetermined"
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(fake_bus, "microphone")
    states = fake_bus.emitted_by_type("ipc.permission.state")
    assert states[0]["payload"]["status"] == "notDetermined"


def test_macos_screen_recording_authorized(
    fake_bus: FakeBus, mock_permissions: dict[str, str]
) -> None:
    """Screen recording authorized — wizard auto-advances Step 1."""
    mock_permissions["screen_recording"] = "authorized"
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(fake_bus, "screen_recording")
    states = fake_bus.emitted_by_type("ipc.permission.state")
    assert states[0]["payload"]["status"] == "authorized"


def test_windows_mic_authorized_default(monkeypatch) -> None:
    """Windows MVP: check_microphone_permission returns authorized.

    Real WinRT DeviceAccessInformation probe deferred to Phase 18 — the
    Step 2 1kHz audio test surfaces actual capture-blocked state.
    """
    from vibemix.platform import _permissions_windows

    assert _permissions_windows.check_microphone_permission() == "authorized"
    assert _permissions_windows.check_screen_recording_permission() == "authorized"
    # request_microphone_permission is a no-op stub on Windows.
    assert _permissions_windows.request_microphone_permission() is None


def test_unknown_kind_short_circuits(
    fake_bus: FakeBus, mock_permissions: dict[str, str]
) -> None:
    """Unknown kind value is ignored — no state emission, no crash."""
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    asyncio.run(
        fake_bus.handlers["ipc.permission.check"](
            {
                "type": "ipc.permission.check",
                "ts": "2026-05-12T08:00:00+00:00",
                "payload": {"kind": "camera"},  # unknown value
            }
        )
    )
    assert fake_bus.emitted_by_type("ipc.permission.state") == []
