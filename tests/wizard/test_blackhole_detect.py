# SPDX-License-Identifier: Apache-2.0
"""ipc.calibration.list_devices BlackHole detection coverage.

Per D-Area-4.1: BlackHole variants 2ch / 16ch / 64ch are all accepted as
"present" — they are functionally identical at the audio-routing layer,
just different channel counts. The variant tag surfaces in the wire
payload for diagnostics; the install-flow UI only branches on the boolean
``blackhole_present`` flag.
"""

from __future__ import annotations

import asyncio
from typing import Any

from tests.wizard.conftest import FakeBus
from vibemix.runtime.wizard import WizardLoop


def _drive_list_devices(bus: FakeBus) -> dict:
    asyncio.run(
        bus.handlers["ipc.calibration.list_devices"](
            {
                "type": "ipc.calibration.list_devices",
                "ts": "2026-05-12T08:00:00+00:00",
                "payload": {},
            }
        )
    )
    return bus.emitted_by_type("ipc.calibration.device_list")[0]["payload"]


def test_blackhole_2ch_detected(fake_bus: FakeBus, mock_sounddevice) -> None:
    """BlackHole 2ch present → blackhole_present + variant=2ch."""
    mock_sounddevice["devices"] = [
        {"name": "BlackHole 2ch", "max_output_channels": 2, "default_samplerate": 48000.0},
        {"name": "AirPods Pro", "max_output_channels": 2, "default_samplerate": 48000.0},
    ]
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    payload = _drive_list_devices(fake_bus)
    assert payload["blackhole_present"] is True
    bh = next(d for d in payload["devices"] if d["is_blackhole"])
    assert bh["variant"] == "2ch"


def test_blackhole_16ch_detected(fake_bus: FakeBus, mock_sounddevice) -> None:
    """BlackHole 16ch present → variant=16ch."""
    mock_sounddevice["devices"] = [
        {"name": "BlackHole 16ch", "max_output_channels": 16, "default_samplerate": 48000.0},
    ]
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    payload = _drive_list_devices(fake_bus)
    assert payload["blackhole_present"] is True
    bh = payload["devices"][0]
    assert bh["variant"] == "16ch"


def test_blackhole_64ch_detected(fake_bus: FakeBus, mock_sounddevice) -> None:
    """BlackHole 64ch present → variant=64ch."""
    mock_sounddevice["devices"] = [
        {"name": "BlackHole 64ch", "max_output_channels": 64, "default_samplerate": 48000.0},
    ]
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    payload = _drive_list_devices(fake_bus)
    assert payload["blackhole_present"] is True
    bh = payload["devices"][0]
    assert bh["variant"] == "64ch"


def test_blackhole_missing(fake_bus: FakeBus, mock_sounddevice) -> None:
    """No BlackHole device → blackhole_present false (banner surfaces)."""
    mock_sounddevice["devices"] = [
        {"name": "AirPods Pro", "max_output_channels": 2, "default_samplerate": 48000.0},
        {"name": "Built-in Output", "max_output_channels": 2, "default_samplerate": 48000.0},
    ]
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    payload = _drive_list_devices(fake_bus)
    assert payload["blackhole_present"] is False
    assert all(not d["is_blackhole"] for d in payload["devices"])


def test_input_only_devices_filtered(fake_bus: FakeBus, mock_sounddevice) -> None:
    """Pure-input devices (mic interfaces) skip the output picker."""
    mock_sounddevice["devices"] = [
        {"name": "USB Microphone", "max_output_channels": 0, "default_samplerate": 48000.0},
        {"name": "AirPods Pro", "max_output_channels": 2, "default_samplerate": 48000.0},
    ]
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    payload = _drive_list_devices(fake_bus)
    names = [d["name"] for d in payload["devices"]]
    assert "USB Microphone" not in names
    assert "AirPods Pro" in names


def test_query_devices_failure_emits_empty_list(
    fake_bus: FakeBus, monkeypatch
) -> None:
    """sd.query_devices raising → empty list emitted (no crash, no hang)."""
    import sounddevice as sd

    def _boom(*_args, **_kwargs) -> Any:
        raise RuntimeError("query_devices stubbed")

    monkeypatch.setattr(sd, "query_devices", _boom)
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    payload = _drive_list_devices(fake_bus)
    assert payload["devices"] == []
    assert payload["blackhole_present"] is False
