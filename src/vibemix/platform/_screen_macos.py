# SPDX-License-Identifier: Apache-2.0
"""ScreenMacOS — ScreenBackend implementation for macOS via mss + Quartz.

Verbatim port of cohost_v4.py:220-242 (find_djay_window_bounds), v4:759-772
(ScreenBuffer), and v4:956-1002 (screen_capture_loop).

Quartz API deprecation notice
-----------------------------
``Quartz.CGWindowListCopyWindowInfo`` is deprecated in macOS 14+ in favor of
ScreenCaptureKit. Phase 3 ships the Quartz path verbatim; **Phase 8 migrates
to ScreenCaptureKit** (deprecation chase).

CPU save: ``run_capture_loop`` pauses (1s sleep + continue) when
``state.audible`` is False — there's no point capturing screen frames when no
music is playing. Verbatim from v4:993-997.
"""

from __future__ import annotations

import asyncio
import io
import sys
import threading

try:
    import mss

    _HAS_MSS = True
except ImportError:
    mss = None  # type: ignore[assignment]
    _HAS_MSS = False

try:
    from PIL import Image

    _HAS_PIL = True
except ImportError:
    Image = None  # type: ignore[assignment]
    _HAS_PIL = False

try:
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGNullWindowID,
        kCGWindowListOptionOnScreenOnly,
    )

    _HAS_QUARTZ = True
except ImportError:
    CGWindowListCopyWindowInfo = None  # type: ignore[assignment]
    kCGNullWindowID = None  # type: ignore[assignment]
    kCGWindowListOptionOnScreenOnly = None  # type: ignore[assignment]
    _HAS_QUARTZ = False

from vibemix.platform.screen import CapturedFrame, WindowBounds
from vibemix.state.music_state import MusicState


class _ScreenBuffer:
    """Thread-safe latest-frame holder (v4:759-772 verbatim)."""

    def __init__(self):
        self._jpeg: bytes | None = None
        self._dims: tuple[int, int] = (0, 0)
        self._lock = threading.Lock()

    def push(self, jpeg: bytes, w: int, h: int):
        with self._lock:
            self._jpeg = jpeg
            self._dims = (w, h)

    def latest(self) -> tuple[bytes | None, tuple[int, int]]:
        with self._lock:
            return self._jpeg, self._dims


def _find_djay_window_bounds(app_name_substring: str = "djay") -> WindowBounds | None:
    """Return WindowBounds of djay Pro's main window, or None.

    Verbatim port of cohost_v4.py:220-242 with two adaptations:
    1. Substring is parameterized (v4 hard-coded "djay") so the same impl
       can find other DJ apps later.
    2. Return type is the Phase 1 WindowBounds dataclass, not a tuple.
    """
    if not _HAS_QUARTZ:
        return None
    try:
        infos = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    except Exception:
        return None
    needle = app_name_substring.lower()
    best: tuple[int, int, int, int] | None = None
    for w in infos:
        owner = (w.get("kCGWindowOwnerName") or "").lower()
        title = (w.get("kCGWindowName") or "").lower()
        if needle not in owner and needle not in title:
            continue
        b = w.get("kCGWindowBounds")
        if not b:
            continue
        x, y, ww, hh = (
            int(b.get("X", 0)),
            int(b.get("Y", 0)),
            int(b.get("Width", 0)),
            int(b.get("Height", 0)),
        )
        if ww < 200 or hh < 200:
            continue
        if best is None or ww * hh > best[2] * best[3]:
            best = (x, y, ww, hh)
    if best is None:
        return None
    return WindowBounds(x=best[0], y=best[1], width=best[2], height=best[3])


class ScreenMacOS:
    """ScreenBackend impl. Holds an internal ``_ScreenBuffer`` for the async
    capture loop's output, exposed via ``latest()``.

    Public surface:
    - ``is_available() -> bool`` (Phase 1 Protocol)
    - ``find_window_bounds(substr) -> WindowBounds | None`` (Phase 1 Protocol)
    - ``capture(bounds, ...) -> CapturedFrame`` (Phase 1 Protocol) — synchronous
      single-frame grab; suitable for low-frequency callers.
    - ``async run_capture_loop(state, stop_event)`` — v4:956-1002 verbatim;
      ~1Hz background loop that pushes into the internal _ScreenBuffer.
    - ``latest() -> (bytes | None, (w, h))`` — read the latest pushed frame.
    """

    def __init__(self):
        self._buffer = _ScreenBuffer()

    def is_available(self) -> bool:
        return _HAS_MSS and _HAS_PIL and _HAS_QUARTZ

    def find_window_bounds(self, app_name_substring: str) -> WindowBounds | None:
        return _find_djay_window_bounds(app_name_substring)

    def capture(
        self,
        bounds: WindowBounds | None,
        *,
        max_width: int = 1280,
        max_height: int = 800,
        jpeg_quality: int = 82,
    ) -> CapturedFrame:
        """Synchronous full-screen grab → optional window crop → thumbnail →
        JPEG. Refactor of v4:973-991 ``grab()`` into a stand-alone method.

        Caller offloads to an executor when in an async context (mss + Pillow
        are blocking).
        """
        if not self.is_available():
            raise RuntimeError("ScreenMacOS dependencies unavailable (mss/PIL/Quartz)")
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            if bounds is not None:
                scale_x = img.size[0] / monitor["width"]
                scale_y = img.size[1] / monitor["height"]
                px = max(0, int(bounds.x * scale_x))
                py = max(0, int(bounds.y * scale_y))
                pw = min(img.size[0] - px, int(bounds.width * scale_x))
                ph = min(img.size[1] - py, int(bounds.height * scale_y))
                if pw > 200 and ph > 200:
                    img = img.crop((px, py, px + pw, py + ph))
            img.thumbnail((max_width, max_height))
            w, h = img.size
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=jpeg_quality)
            return CapturedFrame(jpeg=buf.getvalue(), width=w, height=h)

    def latest(self) -> tuple[bytes | None, tuple[int, int]]:
        """Read the latest frame pushed by ``run_capture_loop``."""
        return self._buffer.latest()

    async def run_capture_loop(
        self,
        state: MusicState,
        stop_event: asyncio.Event,
    ) -> None:
        """v4:956-1002 verbatim — ~1Hz capture loop with ``state.audible``
        gating. Pushes JPEG bytes into the internal _ScreenBuffer.

        CPU save: pauses (sleeps 1s + continues) when ``not state.audible``.
        """
        if not self.is_available():
            print("-> mss/PIL/Quartz not installed, screen vision disabled")
            return

        sct = mss.mss()
        monitor = sct.monitors[1]
        print(
            f"-> screen vision: {monitor['width']}x{monitor['height']} @ ~1fps -> screen_buf"
            f" (djay-only crop)"
        )

        loop = asyncio.get_running_loop()

        def grab() -> tuple[bytes, int, int]:
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            bounds = _find_djay_window_bounds("djay")
            if bounds is not None:
                scale_x = img.size[0] / monitor["width"]
                scale_y = img.size[1] / monitor["height"]
                px = max(0, int(bounds.x * scale_x))
                py = max(0, int(bounds.y * scale_y))
                pw = min(img.size[0] - px, int(bounds.width * scale_x))
                ph = min(img.size[1] - py, int(bounds.height * scale_y))
                if pw > 200 and ph > 200:
                    img = img.crop((px, py, px + pw, py + ph))
            img.thumbnail((1280, 800))
            w, h = img.size
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82)
            return buf.getvalue(), w, h

        while not stop_event.is_set():
            try:
                if not state.audible:
                    await asyncio.sleep(1.0)
                    continue
                jpeg, w, h = await loop.run_in_executor(None, grab)
                self._buffer.push(jpeg, w, h)
            except Exception as e:
                print(f"[screen err] {e}", file=sys.stderr)
            await asyncio.sleep(1.0)
