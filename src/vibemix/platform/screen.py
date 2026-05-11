# SPDX-License-Identifier: Apache-2.0
"""ScreenBackend protocol — DJ-software window discovery + capture.

Lifted from cohost_v3.py:194-216 (find_djay_window_bounds via Quartz CGWindowListCopyWindowInfo)
and cohost_v3.py:947-965 (mss grab + PIL crop + JPEG encode). Phase 3 macOS impl
(_screen_macos.py), Phase 7 Windows impl (_screen_windows.py), and Phase 8 ScreenCaptureKit
impl all satisfy this surface.

is_available() replaces the POC's module-level _HAS_VISION / _HAS_QUARTZ feature flags
(cohost_v3.py:47-62). Callers branch on this method, never on imported module state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class WindowBounds:
    """Pixel rectangle in screen coordinates. Origin = top-left (CG convention)."""

    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class CapturedFrame:
    """JPEG-encoded screenshot + decoded dimensions for downstream inline payloads."""

    jpeg: bytes
    width: int
    height: int


@runtime_checkable
class ScreenBackend(Protocol):
    """Screen capture firewall — find a target window + grab a JPEG of it.

    Hot-paths (Gemini multimodal frames) call capture() at ~1fps. find_window_bounds()
    is cheap and may be re-invoked per capture to follow window movement.
    """

    def is_available(self) -> bool: ...

    def find_window_bounds(self, app_name_substring: str) -> WindowBounds | None: ...

    def capture(
        self,
        bounds: WindowBounds | None,
        *,
        max_width: int = 1280,
        max_height: int = 800,
        jpeg_quality: int = 82,
    ) -> CapturedFrame: ...
