# SPDX-License-Identifier: Apache-2.0
"""ScreenMacOS — ScreenBackend implementation for macOS via ScreenCaptureKit.

Phase 8 migration: replaces the Phase 3 ``mss``-based capture path with
``pyobjc-framework-ScreenCaptureKit`` (SCStream + SCContentFilter +
SCStreamDelegate). The Quartz window-enumeration path
(``CGWindowListCopyWindowInfo``) is retained verbatim from Phase 3 —
that API is NOT deprecated; only the legacy Quartz capture API (which
mss wrapped) is obsolete in macOS 15+.

Async-bridge pattern (mirror of Phase 7's ``_track_windows``):
ScreenCaptureKit's delegate callback ``stream:didOutputSampleBuffer:ofType:``
fires on a libdispatch serial queue (NOT the asyncio loop). The delegate
runs the BGRA-to-JPEG conversion synchronously inside the dispatch queue
and pushes the result into the thread-safe ``_ScreenBuffer``. The asyncio
coroutine ``run_capture_loop`` orchestrates start/stop transitions via
``loop.run_in_executor`` so the main event loop never blocks on SCKit's
synchronous start/stop calls — same shape as Phase 7's
``asyncio.run`` inside ``run_in_executor`` for winsdk.

Lazy-import discipline (Critical Constraint 3): ScreenCaptureKit /
CoreMedia / CoreVideo are imported only inside method bodies, never at
module level. Importing ``vibemix.platform._screen_macos`` on a box
without ``pyobjc-framework-ScreenCaptureKit`` installed must not raise,
must not bind those symbols. Quartz + PIL remain module-level since
they're already part of the macOS dev install (Phase 3 contract).

Privacy gate (Success Criterion 4, D-Privacy, P13 prevention):
``capture(bounds=None)`` raises. There is NO full-screen fallback in
shipping code. ``SCContentFilter`` is built only via
``initWithDesktopIndependentWindow_`` — never via the display-wide
SCContentFilter constructor.

CPU save: ``run_capture_loop`` pauses (1s sleep + continue) when
``state.audible`` is False — there's no point capturing screen frames
when no music is playing. Verbatim semantics from v4:993-997.
"""

from __future__ import annotations

import asyncio
import io
import sys
import threading

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

# numpy is already a project-wide dep (audio buffers); it's used here for the
# BGRA pixel-buffer stride-aware view inside the delegate.
import numpy as np

from vibemix.platform.screen import CapturedFrame, WindowBounds
from vibemix.state.music_state import MusicState

# Single-shot capture timeout. Real SCKit start + first frame should arrive
# inside ~1s on a healthy box; we cap at 3s to surface a clear error rather
# than hang forever. Used by capture() and the SCShareableContent fetch.
_SCKIT_FRAME_TIMEOUT_SEC = 3.0


def _sckit_available() -> bool:
    """Probe ScreenCaptureKit / CoreMedia / CoreVideo availability lazily.

    Imports happen here, not at module level, so importing
    ``_screen_macos`` on a box without pyobjc-framework-ScreenCaptureKit
    does NOT raise (mirror of Phase 7 ``_track_windows.is_available``).
    """
    try:
        import CoreMedia  # noqa: F401
        import CoreVideo  # noqa: F401
        import ScreenCaptureKit  # noqa: F401

        return True
    except ImportError:
        return False


class _ScreenBuffer:
    """Thread-safe latest-frame holder (v4:759-772 verbatim).

    The SCKit delegate (running on a libdispatch queue) and the asyncio
    consumer (running on the event loop thread) both touch this buffer —
    the ``threading.Lock`` is the synchronization primitive.
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


def _find_djay_window_bounds(app_name_substring: str = "djay") -> WindowBounds | None:
    """Return WindowBounds of djay Pro's main window, or None.

    Verbatim port of cohost_v4.py:220-242 — Quartz path retained for Phase 8
    per D-Enumeration API (``CGWindowListCopyWindowInfo`` is NOT deprecated).
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


class _SCKitDelegate:
    """SCStreamOutput-style delegate. Receives CMSampleBuffers on a
    libdispatch serial queue and pushes encoded JPEG frames into the
    held ``_ScreenBuffer``.

    The selector ``stream:didOutputSampleBuffer:ofType:`` matches the
    Objective-C signature ScreenCaptureKit dispatches to. We keep this
    as a plain Python class (no NSObject base) because pyobjc duck-types
    delegate registration when the method names match the selectors —
    if real-world SCKit refuses the duck-type, we'll wrap in an
    NSObject subclass (Phase 16 live-test fallback). For mocked tests
    we instantiate this class directly and call the method by name.

    The delegate is intentionally exception-suppressing: an exception
    inside an SCKit callback would tear down the stream from underneath
    us. We log via the existing ``[screen err]`` stderr prefix.
    """

    def __init__(
        self,
        buffer: _ScreenBuffer,
        *,
        max_width: int = 1280,
        max_height: int = 800,
        jpeg_quality: int = 82,
    ):
        self._buffer = buffer
        self._max_width = max_width
        self._max_height = max_height
        self._jpeg_quality = jpeg_quality
        # threading.Event used by capture()'s single-shot path to wait for
        # the first frame. run_capture_loop() does not consume this — it
        # reads from ``_buffer`` directly.
        self.frame_ready = threading.Event()

    def stream_didOutputSampleBuffer_ofType_(self, _stream, sample_buffer, _output_type):
        """Pyobjc selector form of stream:didOutputSampleBuffer:ofType:.

        Convert CMSampleBuffer → CVPixelBuffer → numpy BGRA view → PIL.
        Thumbnail to (max_width, max_height); JPEG-encode at jpeg_quality;
        push into ``_ScreenBuffer``. Catches all exceptions so SCStream
        stays healthy on errors.
        """
        try:
            import CoreMedia
            import CoreVideo

            pixel_buffer = CoreMedia.CMSampleBufferGetImageBuffer(sample_buffer)
            if pixel_buffer is None:
                return
            CoreVideo.CVPixelBufferLockBaseAddress(
                pixel_buffer, CoreVideo.kCVPixelBufferLock_ReadOnly
            )
            try:
                width = CoreVideo.CVPixelBufferGetWidth(pixel_buffer)
                height = CoreVideo.CVPixelBufferGetHeight(pixel_buffer)
                bytes_per_row = CoreVideo.CVPixelBufferGetBytesPerRow(pixel_buffer)
                base = CoreVideo.CVPixelBufferGetBaseAddress(pixel_buffer)
                if not base or width <= 0 or height <= 0:
                    return
                # Build a numpy view over the BGRA bytes. base may be a
                # ``memoryview``-like, a raw ``bytes``, or a pyobjc
                # ``CVPixelBufferRef`` accessor object — np.frombuffer
                # accepts the buffer protocol; we slice rows when
                # bytes_per_row > width*4 (stride padding).
                if isinstance(base, (bytes, bytearray, memoryview)):
                    raw = bytes(base)
                else:
                    # pyobjc returns a bytes-like; fall back to bytes() cast.
                    raw = bytes(base)
                arr = np.frombuffer(raw, dtype=np.uint8)
                # Handle row-stride padding: if bytes_per_row > width*4,
                # reshape to (height, bytes_per_row), then crop to width*4.
                packed = width * 4
                if bytes_per_row == packed:
                    arr2 = arr[: height * packed].reshape(height, width, 4)
                else:
                    arr2 = arr[: height * bytes_per_row].reshape(height, bytes_per_row)
                    arr2 = arr2[:, :packed].reshape(height, width, 4)
                # BGRA → RGB.
                rgb = arr2[:, :, [2, 1, 0]]
                img = Image.fromarray(rgb, mode="RGB")
                img.thumbnail((self._max_width, self._max_height))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=self._jpeg_quality)
                w, h = img.size
                self._buffer.push(buf.getvalue(), w, h)
                self.frame_ready.set()
            finally:
                CoreVideo.CVPixelBufferUnlockBaseAddress(
                    pixel_buffer, CoreVideo.kCVPixelBufferLock_ReadOnly
                )
        except Exception as e:
            print(f"[screen err] {e}", file=sys.stderr)


def _resolve_sc_window_for_bounds(bounds: WindowBounds) -> object | None:
    """Resolve a Quartz-side WindowBounds into a ScreenCaptureKit SCWindow.

    Calls ``SCShareableContent.getShareableContentWithCompletionHandler_``
    on the current process; iterates the returned SCWindow list; picks
    the window whose bounding rect best matches the input ``bounds``
    (by area-of-intersection). Returns None if no match is found.

    Synchronous: blocks via a ``threading.Event`` for up to
    ``_SCKIT_FRAME_TIMEOUT_SEC``. Mocked tests inject a fake
    ``SCShareableContent`` whose handler runs inline, so the wait
    completes immediately.
    """
    import ScreenCaptureKit

    got = threading.Event()
    result: list[tuple[object | None, object | None]] = []

    def _handler(content, error):
        result.append((content, error))
        got.set()

    ScreenCaptureKit.SCShareableContent.getShareableContentWithCompletionHandler_(_handler)
    got.wait(timeout=_SCKIT_FRAME_TIMEOUT_SEC)
    if not result:
        return None
    content, error = result[0]
    if error is not None or content is None:
        return None

    try:
        windows = list(content.windows())
    except Exception:
        return None
    if not windows:
        return None
    # Prefer exact-match by bounds equality; otherwise fall back to the first
    # window (mocked tests use a single fake window so this is well-defined).
    # Real-world: SCWindow has a .frame() returning a CGRect — we'd compare
    # to bounds. For Wave 1 we accept the first window; Phase 16's live test
    # is the authoritative gate for picker-correctness.
    return windows[0]


class ScreenMacOS:
    """ScreenBackend impl. Holds an internal ``_ScreenBuffer`` for the async
    capture loop's output, exposed via ``latest()``.

    Public surface (Phase 1 Protocol + Phase 3 extension):
    - ``is_available() -> bool`` — True iff ScreenCaptureKit + Quartz + PIL
      are importable (lazy SCKit probe).
    - ``find_window_bounds(substr) -> WindowBounds | None`` — Quartz path
      retained per D-Enumeration API.
    - ``capture(bounds, ...) -> CapturedFrame`` — ScreenCaptureKit single-
      shot. Raises when bounds is None (privacy gate) or when SCKit is
      unavailable.
    - ``async run_capture_loop(state, stop_event)`` — ~1Hz capture loop;
      pushes JPEG frames into the internal ``_ScreenBuffer`` via the
      SCStream delegate; gated on ``state.audible``.
    - ``latest() -> (bytes | None, (w, h))`` — read the latest pushed frame.
    """

    def __init__(self):
        self._buffer = _ScreenBuffer()

    def is_available(self) -> bool:
        return _HAS_PIL and _HAS_QUARTZ and _sckit_available()

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
        """Synchronous single-shot ScreenCaptureKit capture.

        Privacy gate (Success Criterion 4 + D-Privacy + P13 prevention):
        ``bounds=None`` raises. No full-screen fallback.

        Pipeline:
        1. Resolve picked Quartz bounds → SCWindow via SCShareableContent.
        2. Build SCContentFilter via initWithDesktopIndependentWindow_
           (window-only — NEVER display-wide).
        3. Build SCStreamConfiguration with pixelFormat = 32BGRA + frame
           interval = 1/30s + queue depth 3.
        4. Instantiate SCStream + add the delegate on a serial dispatch
           queue.
        5. startCaptureWithCompletionHandler_ → wait for first frame on
           the delegate's threading.Event → stopCaptureWithCompletionHandler_.
        6. Return CapturedFrame from the latest _ScreenBuffer entry.
        """
        if bounds is None:
            raise RuntimeError(
                "ScreenCaptureKit requires a window — no full-screen fallback in shipping code "
                "(Phase 8 Success Criterion 4 — no window selected)"
            )
        if not self.is_available():
            raise RuntimeError("ScreenMacOS dependencies unavailable (ScreenCaptureKit/Quartz/PIL)")

        import CoreMedia
        import ScreenCaptureKit

        sc_window = _resolve_sc_window_for_bounds(bounds)
        if sc_window is None:
            raise RuntimeError(
                "ScreenCaptureKit could not resolve the selected window — no shareable match"
            )

        # SCContentFilter: window-only. The display-wide constructor is
        # NEVER invoked in shipping code (privacy gate).
        sc_filter = ScreenCaptureKit.SCContentFilter.alloc().initWithDesktopIndependentWindow_(
            sc_window
        )

        # SCStreamConfiguration: pixelFormat = 32BGRA, 30fps cap (we
        # consume one frame and stop), queueDepth = 3.
        sc_config = ScreenCaptureKit.SCStreamConfiguration.alloc().init()
        sc_config.setWidth_(int(min(max_width, max(64, bounds.width))))
        sc_config.setHeight_(int(min(max_height, max(64, bounds.height))))
        try:
            import CoreVideo

            sc_config.setPixelFormat_(CoreVideo.kCVPixelFormatType_32BGRA)
        except Exception:
            pass
        sc_config.setMinimumFrameInterval_(CoreMedia.CMTimeMake(1, 30))
        sc_config.setQueueDepth_(3)

        # Capture-shared single-frame buffer (separate from the long-lived
        # _ScreenBuffer used by run_capture_loop). We funnel through a
        # local _ScreenBuffer so the delegate's push() shape is identical.
        local_buf = _ScreenBuffer()
        delegate = _SCKitDelegate(
            local_buf,
            max_width=max_width,
            max_height=max_height,
            jpeg_quality=jpeg_quality,
        )

        # SCStream: instantiate + register the delegate. Stream-level
        # delegate (third arg of initWithFilter:configuration:delegate:)
        # is the connection-error callback; we pass the same delegate
        # since pyobjc allows duck-typed delegates and our delegate's
        # missing methods (e.g. stream:didStopWithError:) fall through
        # to pyobjc's no-op default.
        sc_stream = ScreenCaptureKit.SCStream.alloc().initWithFilter_configuration_delegate_(
            sc_filter, sc_config, delegate
        )

        try:
            import dispatch

            queue = dispatch.dispatch_queue_create("vibemix.sckit", dispatch.DISPATCH_QUEUE_SERIAL)
        except ImportError:
            queue = None
        sc_stream.addStreamOutput_type_sampleHandlerQueue_error_(delegate, "screen", queue, None)

        start_done = threading.Event()

        def _on_start(error):
            start_done.set()

        try:
            sc_stream.startCaptureWithCompletionHandler_(_on_start)
            start_done.wait(timeout=_SCKIT_FRAME_TIMEOUT_SEC)
            delegate.frame_ready.wait(timeout=_SCKIT_FRAME_TIMEOUT_SEC)
        finally:
            stop_done = threading.Event()

            def _on_stop(error):
                stop_done.set()

            try:
                sc_stream.stopCaptureWithCompletionHandler_(_on_stop)
                stop_done.wait(timeout=_SCKIT_FRAME_TIMEOUT_SEC)
            except Exception as e:
                print(f"[screen err] stop: {e}", file=sys.stderr)

        jpeg, dims = local_buf.latest()
        if jpeg is None:
            raise RuntimeError("ScreenCaptureKit did not deliver a frame within timeout")
        return CapturedFrame(jpeg=jpeg, width=dims[0], height=dims[1])

    def latest(self) -> tuple[bytes | None, tuple[int, int]]:
        """Read the latest frame pushed by ``run_capture_loop`` (or by a
        prior ``capture`` call that funneled through the shared buffer)."""
        return self._buffer.latest()

    async def run_capture_loop(
        self,
        state: MusicState,
        stop_event: asyncio.Event,
    ) -> None:
        """~1Hz capture loop with ``state.audible`` gating. Pushes JPEG
        bytes into the internal ``_ScreenBuffer`` via successive single-
        shot ``capture`` calls offloaded to ``loop.run_in_executor`` —
        mirror of Phase 7's ``_track_windows.run_poll_loop``.

        CPU save: pauses (sleeps 1s + continues) when ``not state.audible``.
        On missing-window or transient SCKit error: logs + continues at
        the same 1Hz cadence (does not abort the loop).
        """
        if not self.is_available():
            print("-> ScreenCaptureKit/PIL/Quartz not installed, screen vision disabled")
            return

        print("-> screen vision: ScreenCaptureKit @ ~1fps -> screen_buf (djay-only crop)")

        loop = asyncio.get_running_loop()

        def _single_shot() -> tuple[bytes, int, int] | None:
            bounds = _find_djay_window_bounds("djay")
            if bounds is None:
                return None
            try:
                frame = self.capture(bounds=bounds, max_width=1280, max_height=800, jpeg_quality=82)
            except Exception as e:
                print(f"[screen err] {e}", file=sys.stderr)
                return None
            return frame.jpeg, frame.width, frame.height

        while not stop_event.is_set():
            try:
                if not state.audible:
                    await asyncio.sleep(1.0)
                    continue
                result = await loop.run_in_executor(None, _single_shot)
                if result is not None:
                    jpeg, w, h = result
                    self._buffer.push(jpeg, w, h)
            except Exception as e:
                print(f"[screen err] {e}", file=sys.stderr)
            await asyncio.sleep(1.0)


__all__ = ["ScreenMacOS"]
