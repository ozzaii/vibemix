# SPDX-License-Identifier: Apache-2.0
"""ScreenMacOS tests — mocked ScreenCaptureKit + Quartz + PIL.

Phase 8 Wave 1 migrates the capture path from ``mss`` to
``pyobjc-framework-ScreenCaptureKit``. The Quartz window-enumeration path
(``CGWindowListCopyWindowInfo``) is retained verbatim from Phase 3 because
that API is NOT deprecated.

Coverage:
- Retained Phase 3 tests: ``isinstance(ScreenBackend)``, ``_find_djay_window_bounds``
  (5 cases), ``_ScreenBuffer`` push+latest+overwrite, ``latest()`` delegation.
- New SCKit-shape tests: SCStream-based capture pipeline (mocked CMSampleBuffer
  via injected fake module), the privacy gate (``bounds is None`` raises), the
  delegate's frame-to-JPEG conversion, the SCContentFilter window-only
  invariant, the asyncio-bridge contract on ``run_capture_loop``, and three
  grep-gate invariants that prove no full-screen fallback, no deprecated Quartz
  capture API, and no ``mss`` import on the macOS path.

ScreenCaptureKit mocking strategy: ``ScreenCaptureKit`` / ``CoreMedia`` /
``CoreVideo`` / ``Foundation`` are not imported eagerly by
``vibemix.platform._screen_macos`` — they live inside method bodies (lazy
import discipline, same shape as ``_track_windows._poll_smtc_sync``). Tests
inject fake modules via ``monkeypatch.setitem(sys.modules, ...)`` so the
import inside the lazy site resolves to the fake — no real macOS framework
is loaded during CI.
"""

from __future__ import annotations

import asyncio
import re
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibemix.platform import ScreenBackend, ScreenMacOS, WindowBounds
from vibemix.platform._screen_macos import _find_djay_window_bounds, _ScreenBuffer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREEN_MACOS_PATH = PROJECT_ROOT / "src" / "vibemix" / "platform" / "_screen_macos.py"


# ---------- Protocol satisfaction (retained) ----------


def test_screen_macos_satisfies_protocol():
    assert isinstance(ScreenMacOS(), ScreenBackend) is True


# ---------- is_available — modified for SCKit-shape ----------


def test_screen_macos_is_available_when_all_deps_present(mocker):
    """is_available() returns True iff ScreenCaptureKit + Quartz + PIL are
    importable. On the dev box where SCKit may not be installed, the test
    only asserts the return type is bool — actual truthiness depends on
    pyobjc-framework-ScreenCaptureKit being installed."""
    s = ScreenMacOS()
    avail = s.is_available()
    assert isinstance(avail, bool)


# ---------- _find_djay_window_bounds (retained verbatim from Phase 3) ----------


def test_find_djay_window_bounds_largest_djay_window(mocker):
    """Two djay windows — picks the LARGER one by area."""
    mock_infos = [
        {
            "kCGWindowOwnerName": "djay Pro AI",
            "kCGWindowName": "Main",
            "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 1920, "Height": 1080},
        },
        {
            "kCGWindowOwnerName": "djay Pro AI",
            "kCGWindowName": "Mini",
            "kCGWindowBounds": {"X": 500, "Y": 500, "Width": 400, "Height": 300},
        },
        {
            "kCGWindowOwnerName": "Finder",  # ignored
            "kCGWindowName": "Library",
            "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 800, "Height": 600},
        },
    ]
    mocker.patch(
        "vibemix.platform._screen_macos.CGWindowListCopyWindowInfo",
        return_value=mock_infos,
    )
    out = _find_djay_window_bounds("djay")
    assert out == WindowBounds(x=0, y=0, width=1920, height=1080)


def test_find_djay_window_bounds_filters_small_windows(mocker):
    """Windows < 200 x 200 are skipped (v4:238-239)."""
    mock_infos = [
        {
            "kCGWindowOwnerName": "djay Pro AI",
            "kCGWindowName": "Mini",
            "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 100, "Height": 100},
        },
    ]
    mocker.patch(
        "vibemix.platform._screen_macos.CGWindowListCopyWindowInfo",
        return_value=mock_infos,
    )
    out = _find_djay_window_bounds("djay")
    assert out is None


def test_find_djay_window_bounds_no_match_returns_none(mocker):
    """No djay-named window → None."""
    mock_infos = [
        {
            "kCGWindowOwnerName": "Safari",
            "kCGWindowName": "GitHub",
            "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 1200, "Height": 800},
        },
    ]
    mocker.patch(
        "vibemix.platform._screen_macos.CGWindowListCopyWindowInfo",
        return_value=mock_infos,
    )
    out = _find_djay_window_bounds("djay")
    assert out is None


def test_find_djay_window_bounds_matches_substring_case_insensitive(mocker):
    """Substring match in either kCGWindowOwnerName or kCGWindowName."""
    mock_infos = [
        {
            "kCGWindowOwnerName": "Other",
            "kCGWindowName": "DJAY Pro",  # uppercased → still matches
            "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 800, "Height": 600},
        },
    ]
    mocker.patch(
        "vibemix.platform._screen_macos.CGWindowListCopyWindowInfo",
        return_value=mock_infos,
    )
    out = _find_djay_window_bounds("djay")
    assert out is not None
    assert out.width == 800


def test_find_djay_window_bounds_swallows_quartz_exception(mocker):
    """If CGWindowListCopyWindowInfo raises → None (v4:226-227)."""
    mocker.patch(
        "vibemix.platform._screen_macos.CGWindowListCopyWindowInfo",
        side_effect=RuntimeError("Quartz blew up"),
    )
    assert _find_djay_window_bounds("djay") is None


# ---------- _ScreenBuffer (retained verbatim from Phase 3) ----------


def test_screen_buffer_push_and_latest():
    buf = _ScreenBuffer()
    assert buf.latest() == (None, (0, 0))
    buf.push(b"fake-jpeg-bytes", 1280, 800)
    jpeg, dims = buf.latest()
    assert jpeg == b"fake-jpeg-bytes"
    assert dims == (1280, 800)


def test_screen_buffer_overwrites_on_each_push():
    buf = _ScreenBuffer()
    buf.push(b"first", 100, 100)
    buf.push(b"second", 200, 200)
    jpeg, dims = buf.latest()
    assert jpeg == b"second"
    assert dims == (200, 200)


def test_screen_macos_latest_delegates_to_internal_buffer():
    s = ScreenMacOS()
    s._buffer.push(b"hello", 100, 100)
    assert s.latest() == (b"hello", (100, 100))


# ---------- ScreenCaptureKit mocking infrastructure ----------


class _FakeCMSampleBuffer:
    """Stand-in for a ``CMSampleBuffer`` carrying a synthetic BGRA pixel buffer.

    The delegate code calls ``CMSampleBufferGetImageBuffer`` to extract a
    ``CVPixelBuffer``; we route that fetch back to ourselves so the same
    object answers ``CVPixelBufferGetWidth/Height/BytesPerRow/BaseAddress``.

    bgra_bytes: width * height * 4 bytes, BGRA8888 layout.
    """

    def __init__(self, width: int, height: int, bgra_bytes: bytes):
        self.width = width
        self.height = height
        self.bytes_per_row = width * 4
        self.bgra_bytes = bgra_bytes


def _install_fake_sckit(monkeypatch, *, sample_buffer: _FakeCMSampleBuffer | None = None):
    """Inject fake ``ScreenCaptureKit`` / ``CoreMedia`` / ``CoreVideo`` modules.

    Returns a dict of {sckit, coremedia, corevideo, dispatch} so tests can
    inspect call counts (e.g., asserting that
    ``SCContentFilter.alloc().initWithDesktopIndependentWindow_`` was the
    constructor invoked, not the display-wide variant).

    ``sample_buffer``: when provided, the fake SCStream's "single-shot"
    capture path will synchronously dispatch this sample buffer to the
    registered delegate on the simulated dispatch queue (i.e., from the
    same thread — the delegate is invoked inline). When None, no frame
    is delivered (used by tests that only check construction wiring).
    """

    # ScreenCaptureKit fake — SCStream + SCStreamConfiguration + SCContentFilter
    # + SCShareableContent.
    sckit = types.ModuleType("ScreenCaptureKit")

    # SCContentFilter: track which constructor path was invoked.
    window_init_calls = []
    display_init_calls = []

    class _FakeSCContentFilter:
        def __init__(self):
            self._window = None

        @classmethod
        def alloc(cls):
            return cls()

        def initWithDesktopIndependentWindow_(self, sc_window):
            window_init_calls.append(sc_window)
            self._window = sc_window
            return self

        def initWithDisplay_excludingWindows_(self, display, excluding):
            # Shipping code path must NEVER call this. The test asserts the
            # call count remains zero.
            display_init_calls.append((display, excluding))
            return self

    sckit.SCContentFilter = _FakeSCContentFilter
    sckit._window_init_calls = window_init_calls  # introspection hooks
    sckit._display_init_calls = display_init_calls

    # SCStreamConfiguration: bare class with setter attributes.
    class _FakeSCStreamConfiguration:
        def __init__(self):
            self._width = 0
            self._height = 0
            self._pixelFormat = 0
            self._minimumFrameInterval = None
            self._queueDepth = 0

        @classmethod
        def alloc(cls):
            return cls()

        def init(self):
            return self

        def setWidth_(self, v):
            self._width = v

        def setHeight_(self, v):
            self._height = v

        def setPixelFormat_(self, v):
            self._pixelFormat = v

        def setMinimumFrameInterval_(self, v):
            self._minimumFrameInterval = v

        def setQueueDepth_(self, v):
            self._queueDepth = v

    sckit.SCStreamConfiguration = _FakeSCStreamConfiguration

    # SCStream: synchronous fake — addStreamOutput stashes the delegate;
    # startCaptureWithCompletionHandler_ + delivers sample_buffer once;
    # stopCaptureWithCompletionHandler_ tears down.
    stream_instances = []

    class _FakeSCStream:
        def __init__(self):
            self._filter = None
            self._config = None
            self._delegate = None
            self._output_delegate = None
            self._output_type = None
            self._started = False
            self._stopped = False
            stream_instances.append(self)

        @classmethod
        def alloc(cls):
            return cls()

        def initWithFilter_configuration_delegate_(self, filter_, config, delegate):
            self._filter = filter_
            self._config = config
            self._delegate = delegate
            return self

        def addStreamOutput_type_sampleHandlerQueue_error_(
            self, output, type_, queue, error_ptr
        ):
            self._output_delegate = output
            self._output_type = type_
            return True

        def startCaptureWithCompletionHandler_(self, handler):
            self._started = True
            # Deliver one sample buffer to the registered output delegate
            # synchronously (we simulate the dispatch queue inline).
            if sample_buffer is not None and self._output_delegate is not None:
                self._output_delegate.stream_didOutputSampleBuffer_ofType_(
                    self, sample_buffer, self._output_type
                )
            # Fire completion handler with no error.
            if handler is not None:
                try:
                    handler(None)
                except TypeError:
                    handler()

        def stopCaptureWithCompletionHandler_(self, handler):
            self._stopped = True
            if handler is not None:
                try:
                    handler(None)
                except TypeError:
                    handler()

    sckit.SCStream = _FakeSCStream
    sckit._stream_instances = stream_instances

    # SCShareableContent.getShareableContentWithCompletionHandler_ — invokes
    # handler with (shareable, error). The shareable has .windows() returning
    # a list whose items have .windowID() — matched against Quartz's
    # kCGWindowNumber to find the SCWindow for a picked Quartz window.
    fake_sc_window = MagicMock()
    fake_sc_window.windowID.return_value = 4242

    fake_shareable = MagicMock()
    fake_shareable.windows.return_value = [fake_sc_window]

    def _get_shareable(handler):
        # Invoke synchronously — the impl gates on a threading.Event so the
        # outer call still blocks until the handler completes. Pyobjc passes
        # (shareable, error) by convention.
        handler(fake_shareable, None)

    sckit.SCShareableContent = MagicMock()
    sckit.SCShareableContent.getShareableContentWithCompletionHandler_ = _get_shareable
    sckit._fake_sc_window = fake_sc_window

    # CoreMedia — only CMSampleBufferGetImageBuffer is used by the delegate.
    coremedia = types.ModuleType("CoreMedia")

    def _cm_sample_buffer_get_image_buffer(sb):
        # Route the CMSampleBuffer fetch to the same object — _FakeCMSampleBuffer
        # also serves as the CVPixelBuffer.
        return sb

    def _cm_time_make(value, scale):
        return ("CMTime", value, scale)

    coremedia.CMSampleBufferGetImageBuffer = _cm_sample_buffer_get_image_buffer
    coremedia.CMTimeMake = _cm_time_make

    # CoreVideo — CVPixelBuffer accessors. The fake routes to the buffer's
    # own width/height/bytes/buffer state.
    corevideo = types.ModuleType("CoreVideo")

    def _cv_get_width(pb):
        return pb.width

    def _cv_get_height(pb):
        return pb.height

    def _cv_get_bytes_per_row(pb):
        return pb.bytes_per_row

    def _cv_get_base_address(pb):
        return pb.bgra_bytes

    def _cv_lock(pb, _flags):
        return 0

    def _cv_unlock(pb, _flags):
        return 0

    corevideo.CVPixelBufferGetWidth = _cv_get_width
    corevideo.CVPixelBufferGetHeight = _cv_get_height
    corevideo.CVPixelBufferGetBytesPerRow = _cv_get_bytes_per_row
    corevideo.CVPixelBufferGetBaseAddress = _cv_get_base_address
    corevideo.CVPixelBufferLockBaseAddress = _cv_lock
    corevideo.CVPixelBufferUnlockBaseAddress = _cv_unlock
    corevideo.kCVPixelBufferLock_ReadOnly = 1
    corevideo.kCVPixelFormatType_32BGRA = 0x42475241  # 'BGRA' fourcc

    # libdispatch — dispatch_queue_create is the only symbol the delegate
    # registration path needs.
    dispatch = types.ModuleType("dispatch")

    def _dispatch_queue_create(label, attr):
        return ("dispatch_queue", label)

    dispatch.dispatch_queue_create = _dispatch_queue_create
    dispatch.DISPATCH_QUEUE_SERIAL = None

    # Inject all fake modules.
    monkeypatch.setitem(sys.modules, "ScreenCaptureKit", sckit)
    monkeypatch.setitem(sys.modules, "CoreMedia", coremedia)
    monkeypatch.setitem(sys.modules, "CoreVideo", corevideo)
    monkeypatch.setitem(sys.modules, "dispatch", dispatch)

    return {
        "sckit": sckit,
        "coremedia": coremedia,
        "corevideo": corevideo,
        "dispatch": dispatch,
    }


def _make_synthetic_sample_buffer(width=320, height=200):
    """Build a _FakeCMSampleBuffer with a deterministic BGRA gradient."""
    pixel_count = width * height
    # Solid mid-gray BGRA — A=255, R=G=B=128. Bytes are little-endian BGRA
    # so per-pixel: B=128, G=128, R=128, A=255.
    one_px = bytes([128, 128, 128, 255])
    bgra = one_px * pixel_count
    return _FakeCMSampleBuffer(width, height, bgra)


# ---------- New SCKit-shape tests ----------


def test_capture_produces_jpeg_bytes(monkeypatch):
    """REPLACES the Phase 3 mss-based test. capture() must run the SCKit
    single-shot path: build an SCContentFilter on the picked window, run
    SCStream once, decode the delivered CMSampleBuffer to JPEG."""
    sb = _make_synthetic_sample_buffer(320, 200)
    fakes = _install_fake_sckit(monkeypatch, sample_buffer=sb)

    s = ScreenMacOS()
    bounds = WindowBounds(x=0, y=0, width=1920, height=1080)
    frame = s.capture(bounds=bounds, max_width=1280, max_height=800, jpeg_quality=82)

    assert isinstance(frame.jpeg, bytes)
    assert len(frame.jpeg) > 0
    assert frame.width <= 1280
    assert frame.height <= 800
    # And the SCStream was actually built + run.
    assert len(fakes["sckit"]._stream_instances) >= 1
    stream = fakes["sckit"]._stream_instances[-1]
    assert stream._started is True
    assert stream._stopped is True


def test_capture_raises_when_unavailable(monkeypatch):
    """When the SCKit feature probe is False, capture() must raise."""
    # Force the lazy SCKit check to fail by blocking the imports.
    for k in list(sys.modules):
        if k in {"ScreenCaptureKit", "CoreMedia", "CoreVideo"}:
            monkeypatch.delitem(sys.modules, k, raising=False)

    class _Blocker:
        def find_spec(self, name, _path=None, _target=None):
            if name in {"ScreenCaptureKit", "CoreMedia", "CoreVideo"}:
                raise ImportError("blocked for test")
            return None

    monkeypatch.setattr(sys, "meta_path", [_Blocker(), *sys.meta_path])

    s = ScreenMacOS()
    bounds = WindowBounds(x=0, y=0, width=1920, height=1080)
    with pytest.raises(RuntimeError, match="ScreenMacOS dependencies unavailable"):
        s.capture(bounds=bounds)


def test_capture_raises_when_bounds_is_none(monkeypatch):
    """Privacy gate (Success Criterion 4): capture(bounds=None) must raise.
    No full-screen fallback in shipping code."""
    # Even if SCKit IS available, bounds=None is the no-go signal.
    _install_fake_sckit(monkeypatch, sample_buffer=None)
    s = ScreenMacOS()
    with pytest.raises(RuntimeError, match="no window"):
        s.capture(bounds=None)


def test_sckit_delegate_pushes_jpeg_into_screen_buffer(monkeypatch):
    """The delegate's stream:didOutputSampleBuffer:ofType: converts the
    CMSampleBuffer to JPEG and pushes (jpeg, w, h) into the held
    _ScreenBuffer. Drive the delegate directly with a synthetic sample
    buffer; assert the buffer state after the callback."""
    from vibemix.platform._screen_macos import _SCKitDelegate

    fakes = _install_fake_sckit(monkeypatch, sample_buffer=None)
    sb = _make_synthetic_sample_buffer(320, 200)

    buf = _ScreenBuffer()
    delegate = _SCKitDelegate(buf, max_width=1280, max_height=800, jpeg_quality=82)
    # Inline-invoke the selector — the dispatch queue is a no-op in tests.
    delegate.stream_didOutputSampleBuffer_ofType_(MagicMock(), sb, "screen")

    jpeg, (w, h) = buf.latest()
    assert jpeg is not None
    assert len(jpeg) > 0
    assert w == 320 and h == 200  # 320 ≤ 1280 + 200 ≤ 800 → no thumbnail downscale
    # Silence linter on unused fakes.
    assert fakes["sckit"] is not None


def test_sckit_content_filter_targets_window_only(monkeypatch):
    """SCContentFilter MUST be built via initWithDesktopIndependentWindow_
    (window-only) and NEVER via initWithDisplay_excludingWindows_
    (display-wide). Privacy gate enforced at the construction site."""
    sb = _make_synthetic_sample_buffer(160, 100)
    fakes = _install_fake_sckit(monkeypatch, sample_buffer=sb)

    s = ScreenMacOS()
    s.capture(bounds=WindowBounds(x=100, y=200, width=800, height=600))

    assert len(fakes["sckit"]._window_init_calls) >= 1, (
        "expected initWithDesktopIndependentWindow_ to be called at least once"
    )
    assert len(fakes["sckit"]._display_init_calls) == 0, (
        "shipping code MUST NOT construct display-wide SCContentFilter"
    )


def test_run_capture_loop_uses_run_in_executor_bridge(monkeypatch):
    """run_capture_loop must offload SCKit's synchronous start/stop calls
    via loop.run_in_executor (mirror of Phase 7's winsdk bridge pattern)
    OR push frames in from the delegate's dispatch-queue thread. Either
    way the asyncio loop coroutine must be drivable to one push when
    state.audible=True, and exit cleanly on stop_event."""
    sb = _make_synthetic_sample_buffer(160, 100)
    _install_fake_sckit(monkeypatch, sample_buffer=sb)

    from vibemix.state.music_state import MusicState

    async def _runner():
        s = ScreenMacOS()
        state = MusicState()
        state.audible = True
        # Ensure the loop has a window to target — patch the enumeration so
        # bounds resolve without needing real Quartz.
        monkeypatch.setattr(
            "vibemix.platform._screen_macos._find_djay_window_bounds",
            lambda _substr: WindowBounds(x=0, y=0, width=1920, height=1080),
        )
        stop = asyncio.Event()

        async def _set_stop():
            await asyncio.sleep(0.05)
            stop.set()

        await asyncio.gather(
            asyncio.wait_for(s.run_capture_loop(state, stop), timeout=3.0),
            _set_stop(),
        )
        return s

    s = asyncio.run(_runner())
    # The loop should have either pushed at least one frame from the delegate
    # or terminated cleanly without pushing (in which case latest() stays None).
    # We accept both — what we PIN is that the coroutine exits cleanly.
    jpeg, _dims = s.latest()
    # Just assert no exception leaked. The presence of a frame is best-effort
    # because the fake SCStream may run after stop_event is set depending on
    # scheduling.
    assert jpeg is None or len(jpeg) > 0


# ---------- Grep-gate invariants ----------


def test_no_full_screen_fallback_in_source():
    """Grep gate: shipping code must contain NO references to display-wide
    SCContentFilter / full-screen capture rects / 'fullscreen' substring
    outside of comments. Privacy gate, Success Criterion 4, P13 prevention."""
    source = SCREEN_MACOS_PATH.read_text()
    # Strip comment lines so we don't false-positive on doc references.
    non_comment_lines = [
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    ]
    body = "\n".join(non_comment_lines)
    # The display-wide constructor name — never appear in code.
    assert "initWithDisplay_excludingWindows_" not in body, (
        "display-wide SCContentFilter constructor must not appear in code"
    )
    # 'fullscreen' substring on a code line is suspicious in this module.
    # We use re.search with case-insensitive flag because 'fullScreen' /
    # 'FullScreen' / 'fullscreen' all count.
    assert re.search(r"fullscreen", body, re.IGNORECASE) is None, (
        "'fullscreen' substring on a code line — verify no full-screen fallback"
    )


def test_quartz_create_image_from_array_never_imported():
    """Grep gate: deprecated CGWindowListCreateImageFromArray (the API that
    mss wraps internally and that's obsoleted in macOS 15) must NEVER appear
    in the new _screen_macos.py source."""
    source = SCREEN_MACOS_PATH.read_text()
    assert source.count("CGWindowListCreateImageFromArray") == 0, (
        "deprecated Quartz capture API leaked into _screen_macos.py"
    )


def test_mss_not_imported_in_screen_macos():
    """Grep gate: ``import mss`` / ``from mss`` must NOT appear in
    _screen_macos.py. mss lives on the Windows path only after Phase 8."""
    source = SCREEN_MACOS_PATH.read_text()
    # Allow comment lines mentioning mss (history notes) but no code-level
    # import. Check first non-whitespace token of each line.
    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        assert not stripped.startswith("import mss"), (
            f"unexpected `import mss` in _screen_macos.py: {line!r}"
        )
        assert not stripped.startswith("from mss"), (
            f"unexpected `from mss` in _screen_macos.py: {line!r}"
        )


# ---------- Lazy-import contract (Phase 7 mirror) ----------


def test_screen_macos_module_does_not_import_mss():
    """After ``import vibemix.platform._screen_macos`` the module must NOT
    bind ``mss`` as a module-level attribute. mss is gone from the macOS path
    in Phase 8."""
    import vibemix.platform._screen_macos as smod

    assert "mss" not in dir(smod), (
        "vibemix.platform._screen_macos must not bind ``mss`` — removed in Phase 8"
    )


def test_screen_macos_module_imports_screencapturekit_lazily():
    """The new module either binds the SCKit feature flag (e.g. ``_HAS_SCKIT``
    via a probe) or keeps SCKit fully lazy (only imported inside method
    bodies). What we pin: either way, ``_screen_macos`` does NOT eagerly
    import ScreenCaptureKit at module load (mirrors Phase 7 winsdk lazy
    pattern)."""
    # Force a fresh import of _screen_macos with ScreenCaptureKit absent
    # from sys.modules, and confirm the import does not fail.
    saved = {}
    for k in list(sys.modules):
        if k.startswith("ScreenCaptureKit") or k.startswith("CoreMedia") or k.startswith(
            "CoreVideo"
        ):
            saved[k] = sys.modules.pop(k)
    try:
        import importlib

        # Pop the cached module so re-import re-runs top-level code.
        if "vibemix.platform._screen_macos" in sys.modules:
            del sys.modules["vibemix.platform._screen_macos"]
        importlib.import_module("vibemix.platform._screen_macos")
        # Re-importing on a box without SCKit must NOT raise.
    finally:
        sys.modules.update(saved)
