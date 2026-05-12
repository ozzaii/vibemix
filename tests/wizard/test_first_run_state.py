# SPDX-License-Identifier: Apache-2.0
"""Coverage for the ipc.wizard.done handler.

Rust shell owns config.json persistence (Tauri-plugin-store writes atomically
to ``~/Library/Application Support/vibemix/config.json``). The sidecar only
acknowledges the wizard-done event + sets the stop event so the
PyInstaller-bundled process exits cleanly. These tests pin both sides of
that contract.
"""

from __future__ import annotations

import asyncio
import json

from tests.wizard.conftest import FakeBus
from vibemix.runtime.wizard import WizardLoop
from vibemix.ui_bus.messages import WizardDone


def test_wizard_done_sets_stop_event(fake_bus: FakeBus) -> None:
    """ipc.wizard.done → stop event set, sidecar will exit cleanly."""
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    msg = json.loads(
        WizardDone.make(
            output_device_id="42",
            controller_profile="pioneer-ddj-flx4",
            target_window_id="78001",
        ).to_json()
    )
    assert not loop._stop.is_set()
    asyncio.run(fake_bus.handlers["ipc.wizard.done"](msg))
    assert loop._stop.is_set()


def test_wizard_done_payload_schema_valid() -> None:
    """Wizard-done payload roundtrips through validate_message.

    Rust persists config.json from the same payload shape — pinning the
    schema here catches drift before the persistence layer.
    """
    from vibemix.ui_bus.validator import validate_message

    msg = json.loads(
        WizardDone.make(
            output_device_id="42",
            controller_profile="generic",
            target_window_id=None,
        ).to_json()
    )
    validate_message(msg)
    assert msg["payload"]["target_window_id"] is None


def test_wizard_start_handler_registered(fake_bus: FakeBus) -> None:
    """ipc.wizard.start handler is wired (Phase 12 owns the real re-run UX)."""
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    assert "ipc.wizard.start" in fake_bus.handlers
    # Calling it is a no-op log — should not raise or stop the loop.
    asyncio.run(
        fake_bus.handlers["ipc.wizard.start"](
            {
                "type": "ipc.wizard.start",
                "ts": "2026-05-12T08:00:00+00:00",
                "payload": {},
            }
        )
    )
    assert not loop._stop.is_set()
