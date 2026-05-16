# SPDX-License-Identifier: Apache-2.0
"""Phase 33 / Plan 33-03 — BlackHole probe coverage.

Mocks sounddevice.query_devices via monkeypatch and asserts the probe
returns the expected ``{installed, device_name}`` payload for the
three states the wizard branches on:

  - BlackHole present (2ch variant) → installed=True + device_name
  - BlackHole present (16ch / 64ch variants accepted) → installed=True
  - BlackHole absent → installed=False, device_name=None
  - query_devices raises → installed=False, no crash
"""

from __future__ import annotations

from typing import Any

import pytest

from vibemix.install import blackhole_probe


def _patch_devices(monkeypatch: pytest.MonkeyPatch, devices: list[dict[str, Any]]) -> None:
    import sounddevice as sd

    def _fake_query(idx: int | None = None) -> Any:
        if idx is None:
            return devices
        return devices[idx] if 0 <= idx < len(devices) else {}

    monkeypatch.setattr(sd, "query_devices", _fake_query)


def test_blackhole_2ch_present(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_devices(monkeypatch, [
        {"name": "BlackHole 2ch", "max_output_channels": 2},
        {"name": "AirPods Pro", "max_output_channels": 2},
    ])
    result = blackhole_probe.probe_blackhole()
    assert result["installed"] is True
    assert result["device_name"] == "BlackHole 2ch"


def test_blackhole_16ch_variant_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_devices(monkeypatch, [
        {"name": "BlackHole 16ch", "max_output_channels": 16},
    ])
    result = blackhole_probe.probe_blackhole()
    assert result["installed"] is True
    assert result["device_name"] == "BlackHole 16ch"


def test_blackhole_absent_surfaces_install_button(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_devices(monkeypatch, [
        {"name": "AirPods Pro", "max_output_channels": 2},
        {"name": "Built-in Output", "max_output_channels": 2},
    ])
    result = blackhole_probe.probe_blackhole()
    assert result["installed"] is False
    assert result["device_name"] is None


def test_blackhole_query_failure_returns_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """query_devices raising → installed=False (no crash, no hang)."""
    import sounddevice as sd

    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("CoreAudio not available")

    monkeypatch.setattr(sd, "query_devices", _boom)
    result = blackhole_probe.probe_blackhole()
    assert result["installed"] is False
    assert result["device_name"] is None


def test_blackhole_install_url_is_official() -> None:
    """The wizard install button must point at the official installer."""
    assert blackhole_probe.BLACKHOLE_INSTALL_URL == "https://existential.audio/blackhole/"
