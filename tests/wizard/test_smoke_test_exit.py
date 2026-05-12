# SPDX-License-Identifier: Apache-2.0
"""ipc.calibration.smoke_test handler coverage.

The smoke test exit step plays the HYPE_BEGINNER greeting via the cascade
agent and falls back to a bundled offline-greeting WAV when Gemini is
down on first launch (Open Q2). Wave 4's WizardLoop deliberately routes
to the offline path on Phase 11 — the full cascade-greeting wiring lives
in Phase 12's settings-panel "Re-run calibration" surface.

These tests pin:
  1. smoke_test_started + smoke_test_done emission order.
  2. Cascade failure → offline fallback path is exercised (logged, no crash).
  3. Schema validity of both emitted messages.
"""

from __future__ import annotations

import asyncio

from tests.wizard.conftest import FakeBus
from vibemix.runtime.wizard import WizardLoop


def _drive_smoke(bus: FakeBus) -> None:
    asyncio.run(
        bus.handlers["ipc.calibration.smoke_test"](
            {
                "type": "ipc.calibration.smoke_test",
                "ts": "2026-05-12T08:00:00+00:00",
                "payload": {"template": "HYPE_BEGINNER"},
            }
        )
    )


def test_smoke_test_emits_started_then_done(fake_bus: FakeBus, monkeypatch) -> None:
    """Two messages in order: smoke_test_started, then smoke_test_done."""
    # Don't actually play audio in this test — patch the offline-greeting
    # playback to a no-op.
    loop = WizardLoop(fake_bus)
    loop.register_handlers()

    async def _noop_play(self: WizardLoop) -> None:  # type: ignore[no-untyped-def]
        return

    monkeypatch.setattr(WizardLoop, "_play_offline_greeting", _noop_play)

    _drive_smoke(fake_bus)
    started = fake_bus.emitted_by_type("ipc.calibration.smoke_test_started")
    done = fake_bus.emitted_by_type("ipc.calibration.smoke_test_done")
    assert len(started) == 1
    assert len(done) == 1
    # Ordering — started arrives first.
    types = [m["type"] for m in fake_bus.emitted]
    assert types.index("ipc.calibration.smoke_test_started") < types.index(
        "ipc.calibration.smoke_test_done"
    )


def test_smoke_test_offline_fallback_path(fake_bus: FakeBus, monkeypatch) -> None:
    """Cascade unavailable → offline fallback called, transcript labeled."""
    offline_invocations: list[bool] = []
    loop = WizardLoop(fake_bus)
    loop.register_handlers()

    async def _track_play(self: WizardLoop) -> None:  # type: ignore[no-untyped-def]
        offline_invocations.append(True)

    monkeypatch.setattr(WizardLoop, "_play_offline_greeting", _track_play)

    _drive_smoke(fake_bus)
    assert offline_invocations == [True]
    done = fake_bus.emitted_by_type("ipc.calibration.smoke_test_done")[0]
    assert "offline fallback" in done["payload"]["transcript"]


def test_smoke_test_messages_schema_valid() -> None:
    """Schema check: the two emitted messages roundtrip cleanly."""
    import json

    from vibemix.ui_bus.messages import (
        CalibrationSmokeTestDone,
        CalibrationSmokeTestStarted,
    )
    from vibemix.ui_bus.validator import validate_message

    started = json.loads(CalibrationSmokeTestStarted.make().to_json())
    done = json.loads(
        CalibrationSmokeTestDone.make(transcript="yo we're live").to_json()
    )
    validate_message(started)
    validate_message(done)
    assert started["type"] == "ipc.calibration.smoke_test_started"
    assert done["type"] == "ipc.calibration.smoke_test_done"
    assert done["payload"]["transcript"] == "yo we're live"
