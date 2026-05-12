# SPDX-License-Identifier: Apache-2.0
"""ipc.calibration.probe_audio + ipc.calibration.user_heard_tone handler coverage."""

from __future__ import annotations

import asyncio

from tests.wizard.conftest import FakeBus
from vibemix.runtime.wizard import WizardLoop


def _drive_probe(
    bus: FakeBus, loop: WizardLoop, *, user_heard: bool | None = True
) -> None:
    """Fire the probe_audio request + (optionally) the user_heard_tone reply."""

    async def _orchestrate() -> None:
        async def _probe() -> None:
            await bus.handlers["ipc.calibration.probe_audio"](
                {
                    "type": "ipc.calibration.probe_audio",
                    "ts": "2026-05-12T08:00:00+00:00",
                    "payload": {
                        "output_device_id": "42",
                        "expected_rate": 48000,
                    },
                }
            )

        task = asyncio.create_task(_probe())
        # Give the probe a moment to install the user-confirm await.
        await asyncio.sleep(0.05)
        if user_heard is not None:
            await bus.handlers["ipc.calibration.user_heard_tone"](
                {
                    "type": "ipc.calibration.user_heard_tone",
                    "ts": "2026-05-12T08:00:00+00:00",
                    "payload": {"heard": user_heard},
                }
            )
        await task

    asyncio.run(_orchestrate())


def test_probe_audio_user_says_yes(fake_bus: FakeBus, mock_sounddevice) -> None:
    """User Yes + matching sample rate → audible_confirmed + programmatic_pass."""
    mock_sounddevice["query_device_info"] = {
        "name": "AirPods Pro",
        "default_samplerate": 48000.0,
    }
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive_probe(fake_bus, loop, user_heard=True)
    results = fake_bus.emitted_by_type("ipc.calibration.audio_result")
    assert len(results) == 1
    payload = results[0]["payload"]
    assert payload["audible_confirmed"] is True
    assert payload["programmatic_pass"] is True
    assert payload["actual_rate"] == 48000


def test_probe_audio_user_says_retry(fake_bus: FakeBus, mock_sounddevice) -> None:
    """User Retry → audible_confirmed false; programmatic still passes."""
    mock_sounddevice["query_device_info"] = {
        "name": "AirPods Pro",
        "default_samplerate": 48000.0,
    }
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive_probe(fake_bus, loop, user_heard=False)
    payload = fake_bus.emitted_by_type("ipc.calibration.audio_result")[0]["payload"]
    assert payload["audible_confirmed"] is False
    assert payload["programmatic_pass"] is True


def test_probe_audio_programmatic_fails_when_rate_mismatch(
    fake_bus: FakeBus, mock_sounddevice
) -> None:
    """Device reports 24kHz → programmatic_pass false; actual_rate surfaces."""
    mock_sounddevice["query_device_info"] = {
        "name": "Bad Output",
        "default_samplerate": 24000.0,
    }
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive_probe(fake_bus, loop, user_heard=True)
    payload = fake_bus.emitted_by_type("ipc.calibration.audio_result")[0]["payload"]
    assert payload["audible_confirmed"] is True
    assert payload["programmatic_pass"] is False
    assert payload["actual_rate"] == 24000


def test_probe_audio_invalid_device_id(fake_bus: FakeBus, mock_sounddevice) -> None:
    """Garbage output_device_id surfaces as error without playback attempt."""
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    asyncio.run(
        fake_bus.handlers["ipc.calibration.probe_audio"](
            {
                "type": "ipc.calibration.probe_audio",
                "ts": "2026-05-12T08:00:00+00:00",
                "payload": {
                    "output_device_id": "not_an_int",
                    "expected_rate": 48000,
                },
            }
        )
    )
    payload = fake_bus.emitted_by_type("ipc.calibration.audio_result")[0]["payload"]
    assert payload["playback_ok"] is False
    assert payload["error"] is not None
    assert "invalid output_device_id" in payload["error"]
