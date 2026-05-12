# SPDX-License-Identifier: Apache-2.0
"""``vibemix.platform.windows`` — sys.platform-dispatched window-enumeration selector.

Typing-only public surface for the WizardLoop's
``ipc.calibration.list_windows`` handler (Warning #4 — WS-path only; there
is no Rust ``enumerate_windows`` Tauri command).

Phase 1 firewall: this module imports zero OS-specific packages. The
concrete enumerations live in ``_windows_macos.py`` (Quartz) and
``_windows_windows.py`` (EnumWindows + GetWindowText). The selector
imports the right one at module import time and re-exports
``enumerate_windows`` + ``WindowInfoNative``.
"""

from __future__ import annotations

import sys

if sys.platform == "darwin":
    from vibemix.platform._windows_macos import WindowInfoNative, enumerate_windows
elif sys.platform == "win32":
    from vibemix.platform._windows_windows import WindowInfoNative, enumerate_windows
else:
    raise RuntimeError(
        f"Unsupported platform: {sys.platform}. vibemix supports macOS and Windows only."
    )

__all__ = ["WindowInfoNative", "enumerate_windows"]
