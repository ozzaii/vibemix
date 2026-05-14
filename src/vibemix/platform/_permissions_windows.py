# SPDX-License-Identifier: Apache-2.0
"""Windows permission probes for the Phase 11 calibration wizard.

Per CONTEXT D-Area-2.1: Windows = Microphone via standard runtime permission.
There is no system-wide screen-recording permission gate on Windows — screen
capture works by default. We return ``"authorized"`` for both so the wizard
Step 1 UI on Windows shows a single Microphone card (the OS-aware renderer
treats screen_recording as a no-op on win32).

Real WinRT capability probes via
``winsdk.Windows.Devices.Enumeration.DeviceAccessInformation`` are deferred
to Phase 18 hardening — they require an MSIX-packaged install context to
return meaningful values. For the dev build + Phase 20 fresh-VM rehearsal,
the audio-capture path itself surfaces failure if mic is blocked (the user
hears nothing and the wizard Step 2 1-kHz test catches it).

Per Phase 7 convention: this module exports the same surface as
``_permissions_macos.py`` so the ``vibemix.platform.permissions`` selector
can dispatch transparently.
"""

from __future__ import annotations

from typing import Literal

PermissionStatus = Literal["authorized", "denied", "notDetermined", "restricted"]


def check_microphone_permission() -> PermissionStatus:
    """Windows MVP: assume authorized — runtime permission surfaces on capture.

    Returning ``"authorized"`` lets the Step 2 1-kHz playback proceed; if
    the OS actually blocks mic capture at that step, the failure manifests
    as a silent / failed audio probe and the user is routed to Windows
    Settings via the same flow as denied permissions.
    """
    return "authorized"


def check_screen_recording_permission() -> PermissionStatus:
    """Windows has no system-wide screen-recording gate — always authorized."""
    return "authorized"


def request_microphone_permission() -> None:
    """Windows: no explicit prompt API needed. First capture triggers it."""
    return None


def request_screen_recording_permission() -> bool:
    """Windows: no system-wide gate. Return True so the macOS-parity API holds."""
    return True


__all__ = [
    "PermissionStatus",
    "check_microphone_permission",
    "check_screen_recording_permission",
    "request_microphone_permission",
    "request_screen_recording_permission",
]
