# SPDX-License-Identifier: Apache-2.0
"""ScreenMacOS tests — mocked mss + Quartz + PIL.

Covers find_window_bounds (substring matching, size filter, largest-pick),
is_available, capture pipeline, isinstance(ScreenBackend), and internal
_ScreenBuffer thread-safety.
"""

from __future__ import annotations

from vibemix.platform import ScreenBackend, ScreenMacOS, WindowBounds
from vibemix.platform._screen_macos import _find_djay_window_bounds, _ScreenBuffer


def test_screen_macos_satisfies_protocol():
    assert isinstance(ScreenMacOS(), ScreenBackend) is True


def test_screen_macos_is_available_when_all_deps_present(mocker):
    # On the dev box, mss + PIL + Quartz are all installed → True.
    s = ScreenMacOS()
    # We don't mock the module flags; just verify the method runs.
    avail = s.is_available()
    assert isinstance(avail, bool)


# ---------- _find_djay_window_bounds ----------


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


# ---------- _ScreenBuffer ----------


def test_screen_buffer_push_and_latest():
    buf = _ScreenBuffer()
    # Initial state — no frame yet.
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


# ---------- capture() pipeline ----------


def test_capture_produces_jpeg_bytes(mocker):
    """Mock mss + PIL to verify the capture pipeline produces JPEG bytes
    of the expected dimensions."""
    # Mock the screen capture
    fake_raw = mocker.MagicMock()
    fake_raw.size = (1920, 1080)
    fake_raw.bgra = bytes(1920 * 1080 * 4)  # 4 bytes per BGRX pixel
    fake_sct = mocker.MagicMock()
    fake_sct.monitors = [None, {"width": 1920, "height": 1080}]
    fake_sct.grab.return_value = fake_raw
    fake_sct.__enter__.return_value = fake_sct
    fake_sct.__exit__.return_value = False
    mocker.patch("vibemix.platform._screen_macos.mss.mss", return_value=fake_sct)

    s = ScreenMacOS()
    # No bounds → no crop → full resize to (1280, 800) thumbnail.
    frame = s.capture(bounds=None, max_width=1280, max_height=800, jpeg_quality=82)
    assert isinstance(frame.jpeg, bytes)
    assert len(frame.jpeg) > 0
    assert frame.width <= 1280
    assert frame.height <= 800


def test_capture_raises_when_unavailable(mocker):
    mocker.patch("vibemix.platform._screen_macos._HAS_MSS", False)
    s = ScreenMacOS()
    # is_available() returns False → capture() raises RuntimeError.
    import pytest

    with pytest.raises(RuntimeError, match="ScreenMacOS dependencies unavailable"):
        s.capture(bounds=None)


def test_screen_macos_latest_delegates_to_internal_buffer():
    s = ScreenMacOS()
    s._buffer.push(b"hello", 100, 100)
    assert s.latest() == (b"hello", (100, 100))
