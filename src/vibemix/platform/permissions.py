# SPDX-License-Identifier: Apache-2.0
"""``vibemix.platform.permissions`` — sys.platform-dispatched permission probe selector.

Typing-only public surface for the WizardLoop. Phase 1 firewall: this
module imports zero OS-specific packages — the concrete impls live in
``_permissions_macos.py`` / ``_permissions_windows.py`` (underscore-prefixed
per the firewall exception). The selector imports the right one at module
import time and re-exports the three functions.

Schema enum: returns ``Literal["authorized", "denied", "notDetermined",
"restricted"]`` matching ``ipc.permission.state.payload.status``.
"""

from __future__ import annotations

import sys
from typing import Literal

PermissionStatus = Literal["authorized", "denied", "notDetermined", "restricted"]

if sys.platform == "darwin":
    from vibemix.platform._permissions_macos import (
        check_microphone_permission,
        check_screen_recording_permission,
        request_microphone_permission,
        request_screen_recording_permission,
    )
elif sys.platform == "win32":
    from vibemix.platform._permissions_windows import (
        check_microphone_permission,
        check_screen_recording_permission,
        request_microphone_permission,
        request_screen_recording_permission,
    )
else:
    raise RuntimeError(
        f"Unsupported platform: {sys.platform}. vibemix supports macOS and Windows only."
    )

__all__ = [
    "PermissionStatus",
    "check_microphone_permission",
    "check_screen_recording_permission",
    "request_microphone_permission",
    "request_screen_recording_permission",
]
