# SPDX-License-Identifier: Apache-2.0
"""WizardLoop boot + handler-dispatch coverage.

Uses ``asyncio.run`` directly per project convention (Phase 4 onwards
runtime tests use the same pattern; no pytest-asyncio dependency).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from tests.wizard.conftest import FakeBus
from vibemix.runtime.wizard import WizardLoop


def test_boot_emits_ipc_boot(fake_bus: FakeBus) -> None:
    """``boot()`` emits a schema-valid ``ipc.boot {ready: true}``."""
    loop = WizardLoop(fake_bus)
    asyncio.run(loop.boot())
    boots = fake_bus.emitted_by_type("ipc.boot")
    assert len(boots) == 1
    assert boots[0]["payload"] == {"ready": True}


def test_register_handlers_covers_all_request_types(fake_bus: FakeBus) -> None:
    """All inbound types registered. Phase 32 adds ipc.profile.set_consent
    (PROFILE-05) so the wizard's profile-consent step can persist the toggle."""
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    expected = {
        "ipc.permission.check",
        "ipc.calibration.list_devices",
        "ipc.calibration.probe_audio",
        "ipc.calibration.user_heard_tone",
        "ipc.calibration.start_midi_listen",
        "ipc.calibration.list_windows",
        "ipc.calibration.smoke_test",
        "ipc.wizard.done",
        "ipc.wizard.start",
        # Phase 32 / PROFILE-05
        "ipc.profile.set_consent",
    }
    assert expected.issubset(set(fake_bus.handlers.keys()))


def _drive(bus: FakeBus, msg: dict) -> None:
    """Helper — dispatch ``msg`` to the registered handler via asyncio.run."""
    handler = bus.handlers[msg["type"]]
    asyncio.run(handler(msg))


def test_permission_check_microphone_authorized(
    fake_bus: FakeBus, mock_permissions: dict[str, str]
) -> None:
    """``ipc.permission.check {kind: microphone}`` emits ``state {status: authorized}``."""
    mock_permissions["microphone"] = "authorized"
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.permission.check",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"kind": "microphone"},
        },
    )
    states = fake_bus.emitted_by_type("ipc.permission.state")
    assert len(states) == 1
    assert states[0]["payload"] == {"kind": "microphone", "status": "authorized"}


def test_permission_check_screen_denied(
    fake_bus: FakeBus, mock_permissions: dict[str, str]
) -> None:
    """Screen-recording denied surfaces as ``state {status: denied}``."""
    mock_permissions["screen_recording"] = "denied"
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.permission.check",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"kind": "screen_recording"},
        },
    )
    states = fake_bus.emitted_by_type("ipc.permission.state")
    assert len(states) == 1
    assert states[0]["payload"] == {"kind": "screen_recording", "status": "denied"}


def test_permission_check_unknown_kind_ignored(
    fake_bus: FakeBus, mock_permissions: dict[str, str]
) -> None:
    """Unknown kind value short-circuits — no permission.state emitted."""
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    # Bypass the bus's outer schema validation by calling the handler directly
    # with a synthetic dict (handlers must defensively guard their own inputs).
    handler = fake_bus.handlers["ipc.permission.check"]
    asyncio.run(
        handler(
            {
                "type": "ipc.permission.check",
                "ts": "2026-05-12T08:00:00+00:00",
                "payload": {"kind": "something_else"},
            }
        )
    )
    assert fake_bus.emitted_by_type("ipc.permission.state") == []


def test_status_tick_payload_is_schema_valid(
    fake_bus: FakeBus, mock_permissions: dict[str, str]
) -> None:
    """The status_tick payload validates and uses the screen probe."""
    mock_permissions["screen_recording"] = "authorized"
    loop = WizardLoop(fake_bus)
    from vibemix.ui_bus.messages import StatusTick

    tick = StatusTick.make(
        livekit="connecting",
        gemini="down",
        midi=loop._probe_midi_count(),
        screen=loop._probe_screen_status(),
    )
    payload = json.loads(tick.to_json())
    assert payload["type"] == "ipc.status.tick"
    assert payload["payload"]["screen"] == "ok"


def test_invalid_inbound_logged_no_crash() -> None:
    """A schema-invalid inbound frame is dropped, not routed to handlers."""
    from vibemix.runtime.ws_bus import WizardBus

    bus = WizardBus()
    handler_calls: list[dict] = []

    async def _h(msg: dict) -> None:
        handler_calls.append(msg)

    bus.register_handler("ipc.boot", _h)

    class FakeWs:
        def __init__(self, frames: list[str]) -> None:
            self._frames = frames

        def __aiter__(self) -> Any:
            return self

        async def __anext__(self) -> str:
            if not self._frames:
                raise StopAsyncIteration
            return self._frames.pop(0)

        async def send(self, _payload: str) -> None:  # pragma: no cover
            return None

    # Three frames that should all be dropped:
    #   1. Non-JSON garbage.
    #   2. JSON but not an object (number).
    #   3. Schema-invalid envelope: wrong const + extra unknown property
    #      blocked by additionalProperties: false at envelope level.
    frames = [
        "not json {",
        json.dumps(42),
        json.dumps(
            {
                "type": "ipc.unknown.bogus",
                "ts": "2026-05-12T08:00:00+00:00",
                "payload": {},
            }
        ),
    ]
    fake = FakeWs(frames)
    asyncio.run(bus._handler(fake))
    assert handler_calls == []
