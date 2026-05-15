# SPDX-License-Identifier: Apache-2.0
"""Phase 33 / INSTALL-03 — BlackHole 2ch CoreAudio probe.

Returns a structured dict the IPC layer can serialize back to the
wizard. The wizard renders an "Install BlackHole 2ch" affordance when
the probe reports the device is absent.

We accept any BlackHole variant (2ch / 16ch / 64ch) as "installed" —
they are functionally identical for vibemix's audio-routing surface;
only the channel count differs. The variant tag surfaces in the
diagnostic payload but the wizard only branches on the boolean
``installed`` flag.

The probe never raises. If ``sounddevice.query_devices()`` itself
fails (no audio backend, permissions revoked mid-poll, etc.), we
return ``installed=False`` with ``device_name=None`` and the caller
gracefully advances with a warning.
"""

from __future__ import annotations

from typing import Any, TypedDict


class BlackHoleProbeResult(TypedDict):
    installed: bool
    device_name: str | None


def _query_devices() -> list[dict[str, Any]]:
    """Indirection point — tests monkeypatch ``sounddevice.query_devices``
    via the existing ``mock_sounddevice`` fixture. Returns an empty list
    when the import or query fails."""
    try:
        import sounddevice as sd  # local import — keep module import-safe
    except Exception:
        return []
    try:
        devices = sd.query_devices()
    except Exception:
        return []
    # sounddevice can return a single dict (one device), a list, or a
    # DeviceList; normalize to a plain list of dicts.
    if isinstance(devices, dict):
        return [devices]
    try:
        return list(devices)
    except Exception:
        return []


def probe_blackhole() -> BlackHoleProbeResult:
    """Probe CoreAudio for a BlackHole device.

    Returns:
        {"installed": bool, "device_name": str | None}

    ``installed`` is True iff at least one device name contains the
    case-sensitive substring ``"BlackHole"``. ``device_name`` is the
    first matching name, or None.
    """
    for entry in _query_devices():
        name = entry.get("name")
        if isinstance(name, str) and "BlackHole" in name:
            return {"installed": True, "device_name": name}
    return {"installed": False, "device_name": None}


# Public install URL — opens in the OS default browser via the Tauri
# shell.open command. The capability allowlist already permits
# https://existential.audio/blackhole.
BLACKHOLE_INSTALL_URL = "https://existential.audio/blackhole/"
