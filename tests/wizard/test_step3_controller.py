# SPDX-License-Identifier: Apache-2.0
"""ipc.calibration.start_midi_listen handler coverage.

The controller probe drains 200ms of MIDI bootstrap traffic (Open Q5)
then listens for the first event within ``timeout_s``. On match: emits
ipc.calibration.midi_event with the resolved control_label. On timeout:
emits ipc.calibration.midi_timeout.

The Skip path is webview-side (no ipc.* request is sent); the wizard
state machine just advances to the smoke test without a midi.* response.
"""

from __future__ import annotations

import asyncio

from tests.wizard.conftest import FakeBus
from vibemix.runtime.wizard import WizardLoop


def _drive_listen(bus: FakeBus, *, timeout_s: float = 0.3) -> None:
    asyncio.run(
        bus.handlers["ipc.calibration.start_midi_listen"](
            {
                "type": "ipc.calibration.start_midi_listen",
                "ts": "2026-05-12T08:00:00+00:00",
                "payload": {"timeout_s": timeout_s},
            }
        )
    )


def test_no_midi_ports_emits_timeout(fake_bus: FakeBus, monkeypatch) -> None:
    """No MIDI ports → asyncio.wait_for fires → midi_timeout emitted."""
    import mido

    monkeypatch.setattr(mido, "get_input_names", lambda: [])
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive_listen(fake_bus, timeout_s=0.3)
    timeouts = fake_bus.emitted_by_type("ipc.calibration.midi_timeout")
    assert len(timeouts) == 1


def test_skip_path_emits_nothing(fake_bus: FakeBus) -> None:
    """Skip path: webview never sends start_midi_listen → no emission."""
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    # Don't drive — assert no midi_* messages emitted.
    assert fake_bus.emitted_by_type("ipc.calibration.midi_event") == []
    assert fake_bus.emitted_by_type("ipc.calibration.midi_timeout") == []


def test_midi_event_payload_schema_valid(fake_bus: FakeBus) -> None:
    """Schema check: a CalibrationMidiEvent emitted by the bus is schema-valid.

    The drain_then_listen helper is hard to exercise without real MIDI;
    this test pins the wire shape via the dataclass roundtrip so a
    schema regression would fail here.
    """
    import json

    from vibemix.ui_bus.messages import CalibrationMidiEvent

    msg = CalibrationMidiEvent.make(control_label="play_a", raw="note_on note=1")
    payload = json.loads(msg.to_json())
    assert payload["type"] == "ipc.calibration.midi_event"
    assert payload["payload"]["control_label"] == "play_a"
    assert "note_on" in payload["payload"]["raw"]


def test_midi_timeout_payload_schema_valid() -> None:
    """Schema check: a CalibrationMidiTimeout emit is schema-valid."""
    import json

    from vibemix.ui_bus.messages import CalibrationMidiTimeout

    msg = CalibrationMidiTimeout.make()
    payload = json.loads(msg.to_json())
    assert payload["type"] == "ipc.calibration.midi_timeout"
    assert payload["payload"] == {}
