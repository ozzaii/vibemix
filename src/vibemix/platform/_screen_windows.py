# SPDX-License-Identifier: Apache-2.0
"""ScreenWindows — ScreenBackend impl for Windows via mss + pywin32 + Pillow.

Mirrors ScreenMacOS shape (Phase 3): is_available + find_window_bounds + capture
+ async run_capture_loop with state.audible gating + 1Hz cadence. The win32-
specific code (EnumWindows + GetWindowText + GetWindowRect) replaces macOS's
Quartz CGWindowListCopyWindowInfo; mss + Pillow are cross-platform and reused.

DJ-software hint list expanded from macOS's "djay"-only to the locked Windows
tuple per CONTEXT Decisions §ScreenWindows — Serato/Traktor/rekordbox/VirtualDJ
are the Windows DJ ecosystem reality (djay Pro is macOS-leaning).

Critical Constraint 3: ``import win32gui`` lives ONLY inside method bodies.
This module imports cleanly on macOS (mss + PIL are cross-platform) for the
Wave 3 mocked test suite. The lazy-import discipline mirrors what Wave 1 did
for ``_midi_common`` ↔ ``__init__`` and is verified by the platform-selector
no-leak guard in tests/test_platform_selector.py.

ScreenBuffer copy-paste: ``_ScreenBuffer`` is intentionally duplicated from
``_screen_macos.py`` (thread-safe latest-frame holder). A ``_screen_common.py``
extraction would be appropriate in Phase 8 (when ScreenCaptureKit lands and
both impls converge); Wave 3 keeps the duplication so the firewall blast-radius
stays small.
"""

from __future__ import annotations

import asyncio
import io
import sys
import threading

# mss + PIL are cross-platform — already in the macOS impl, already shipping
# on darwin. Per the no-leak test in tests/test_platform.py, they're fine to
# import at module top because the AST guard exempts underscore-prefixed
# concrete impls. Mirrors _screen_macos.py exactly.
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

# NO top-level `import win32gui` — Critical Constraint 3. Resolved lazily
# inside method bodies so importing this module on macOS does NOT pull
# pywin32 into sys.modules.

from vibemix.platform.screen import CapturedFrame, WindowBounds
from vibemix.state.music_state import MusicState

# Locked Windows DJ-software hint list (CONTEXT Decisions §ScreenWindows).
# Case-insensitive substring matched against window title text. Tuple (not
# list) so callers + tests can rely on immutability. Order is priority order
# for ``find_dj_window`` — earlier entries hit first.
_DJ_HINTS: tuple[str, ...] = ("djay", "serato", "traktor", "rekordbox", "virtualdj")


class _ScreenBuffer:
    """Thread-safe latest-frame holder.

    Duplicated from ``_screen_macos.py``. See module docstring for the
    extraction-deferred rationale.
    """

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


class ScreenWindows:
    """ScreenBackend impl for Windows. Holds an internal ``_ScreenBuffer`` for
    the async capture loop's output, exposed via ``latest()``.

    Public surface (Phase 1 Protocol + macOS-impl parity):
    - ``is_available() -> bool`` — True iff mss + PIL + win32gui all import.
    - ``find_window_bounds(substr) -> WindowBounds | None`` — case-insensitive
      substring match against window title; ≥200x200 floor; largest by area.
    - ``find_dj_window() -> WindowBounds | None`` — convenience: iterates
      ``_DJ_HINTS`` and returns the first match (priority order).
    - ``capture(bounds, ...) -> CapturedFrame`` — synchronous mss grab → optional
      crop with scale-factor → thumbnail (1280, 800) → JPEG quality 82.
    - ``async run_capture_loop(state, stop_event)`` — ~1Hz background loop with
      ``state.audible`` gating. Pushes JPEGs into the internal _ScreenBuffer.
    - ``latest() -> (bytes | None, (w, h))`` — read the latest pushed frame.
    """

    _DJ_HINTS = _DJ_HINTS  # exposed on the class too for callers that prefer
    # ``ScreenWindows._DJ_HINTS`` over the module symbol.

    def __init__(self):
        self._buffer = _ScreenBuffer()

    # ---------- pywin32 lazy-import helper ----------

    @staticmethod
    def _import_win32gui():
        """Lazy importer for ``win32gui``. Returns the module on success or
        None if pywin32 is not installed (graceful fallback on darwin and on
        Windows boxes missing pywin32).

        Critical Constraint 3: this is the ONLY place in the module that
        names ``win32gui``. Tests inject a fake by ``monkeypatch.setitem(
        sys.modules, "win32gui", fake)`` and the import below resolves to it.
        """
        try:
            import win32gui

            return win32gui
        except ImportError:
            return None

    def _has_pywin32(self) -> bool:
        return self._import_win32gui() is not None

    # ---------- Phase 1 Protocol surface ----------

    def is_available(self) -> bool:
        return _HAS_MSS and _HAS_PIL and self._has_pywin32()

    def find_window_bounds(self, app_name_substring: str) -> WindowBounds | None:
        """Walk visible top-level windows via win32gui.EnumWindows; pick the
        largest matching window with sides ≥200px.

        Returns None when pywin32 is unavailable, no windows match the
        substring, or all matches fail the size floor.
        """
        win32gui = self._import_win32gui()
        if win32gui is None:
            return None

        needle = app_name_substring.lower()
        # Each entry: (hwnd, title, (left, top, right, bottom)).
        results: list[tuple[int, str, tuple[int, int, int, int]]] = []

        def _callback(hwnd: int, accum: list) -> bool:
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                title = win32gui.GetWindowText(hwnd) or ""
                rect = win32gui.GetWindowRect(hwnd)
                accum.append((hwnd, title, rect))
            except Exception:
                # Per-window enumeration errors are non-fatal; skip & continue.
                pass
            return True  # continue enumeration

        try:
            win32gui.EnumWindows(_callback, results)
        except Exception:
            return None

        best: tuple[int, int, int, int] | None = None
        best_area = 0
        for _hwnd, title, rect in results:
            if needle not in title.lower():
                continue
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top
            if width < 200 or height < 200:
                continue
            area = width * height
            if area > best_area:
                best = (left, top, width, height)
                best_area = area

        if best is None:
            return None
        x, y, w, h = best
        return WindowBounds(x=x, y=y, width=w, height=h)

    def find_dj_window(self) -> WindowBounds | None:
        """Iterate _DJ_HINTS in priority order; return the first match.

        Used by ``run_capture_loop`` to crop screenshots to the active DJ
        application's window. Returns None when no DJ app is visible (the
        capture loop falls back to full-monitor capture).
        """
        for hint in _DJ_HINTS:
            bounds = self.find_window_bounds(hint)
            if bounds is not None:
                return bounds
        return None

    def capture(
        self,
        bounds: WindowBounds | None,
        *,
        max_width: int = 1280,
        max_height: int = 800,
        jpeg_quality: int = 82,
    ) -> CapturedFrame:
        """Synchronous full-monitor grab → optional window crop with scale
        factor → thumbnail to (max_width, max_height) → JPEG.

        Mirrors ``ScreenMacOS.capture`` (cohost_v4.py:973-991 verbatim with
        the macOS-impl wrapping). Caller offloads to an executor when in an
        async context (mss + Pillow are blocking).
        """
        if not self.is_available():
            raise RuntimeError(
                "ScreenWindows dependencies unavailable (mss/PIL/pywin32). "
                "Install via `pip install vibemix[windows]` on Windows."
            )
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
        """~1Hz capture loop with ``state.audible`` gating. Pushes JPEG bytes
        into the internal _ScreenBuffer.

        Mirrors ``ScreenMacOS.run_capture_loop`` (cohost_v4.py:956-1002):
        - CPU save: pauses (1s sleep + continue) when ``not state.audible``.
        - Crops to the active DJ application's window when one is visible
          (via ``find_dj_window``); falls back to full-monitor.
        - mss grab + PIL crop + JPEG offloaded via run_in_executor (blocking).
        """
        if not self.is_available():
            print("-> mss/PIL/pywin32 not installed, screen vision disabled")
            return

        sct = mss.mss()
        monitor = sct.monitors[1]
        print(
            f"-> screen vision: {monitor['width']}x{monitor['height']} @ ~1fps -> screen_buf"
            f" (DJ-app crop via {len(_DJ_HINTS)}-app hint list)"
        )

        loop = asyncio.get_running_loop()

        def grab() -> tuple[bytes, int, int]:
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            bounds = self.find_dj_window()
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


__all__ = ["ScreenWindows"]
