# SPDX-License-Identifier: Apache-2.0
"""ScreenWindows tests — mocked mss + pywin32 + PIL.

Pins:
- Module imports cleanly on macOS without pulling win32gui into sys.modules
  (Critical Constraint 3: pywin32 lives only inside method bodies).
- ScreenWindows() structurally satisfies the ScreenBackend Protocol when
  pywin32 is mocked.
- ``_DJ_HINTS`` is the locked Windows-DJ-software hint list (case-insensitive
  substring matched against window titles).
- ``find_window_bounds`` enumerates visible windows via win32gui.EnumWindows,
  filters by substring + size floor, and picks the largest match by area.
- ``capture`` mirrors ScreenMacOS — full-monitor mss grab → optional crop with
  scale-factor → thumbnail to (1280, 800) → JPEG quality 82.

Patched surfaces:
- ``vibemix.platform._screen_windows.mss`` (Phase 8: mss is win32-only in
  pyproject; on macOS dev boxes it isn't installed and ``_HAS_MSS`` is
  False, so capture tests must restore ``_HAS_MSS=True`` and inject a
  fake ``mss`` module attribute via ``mocker.patch``).
- ``vibemix.platform._screen_windows.Image`` (PIL Image — module top).
- ``win32gui`` via ``monkeypatch.setitem(sys.modules, "win32gui", fake)`` so
  the lazy-import inside method bodies resolves to the fake.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from vibemix.platform import ScreenBackend, WindowBounds
from vibemix.platform._screen_windows import _DJ_HINTS, ScreenWindows

# ---------- Module import discipline ----------


def test_module_imports_on_macos_without_pulling_win32gui():
    """Critical Constraint 3 — importing _screen_windows must NOT add
    win32gui (or any win32*) to sys.modules. The lazy-import pattern
    keeps the firewall intact on darwin."""
    # Re-importing here (already imported at test-module top) is a no-op;
    # the assertion is on sys.modules state AFTER the top-of-file import.
    assert "win32gui" not in sys.modules
    win32_leaks = [m for m in sys.modules if m.startswith("win32")]
    assert win32_leaks == [], f"win32* leaked into sys.modules: {win32_leaks}"


# ---------- _DJ_HINTS locked tuple ----------


def test_dj_hints_locked():
    """Locked per CONTEXT Decisions §ScreenWindows — case-insensitive
    substrings matched against window titles."""
    assert _DJ_HINTS == ("djay", "serato", "traktor", "rekordbox", "virtualdj")
    # Must be an immutable tuple, not a list (no in-place mutation).
    assert isinstance(_DJ_HINTS, tuple)


# ---------- Protocol satisfaction ----------


def test_screen_windows_satisfies_protocol():
    """structural isinstance check — ScreenWindows must satisfy ScreenBackend
    even on darwin. The Protocol is @runtime_checkable so this only checks
    method presence + signature, not types."""
    assert isinstance(ScreenWindows(), ScreenBackend) is True


# ---------- find_window_bounds ----------


def _make_fake_win32gui(windows_data: list[tuple[int, str, tuple[int, int, int, int]]]):
    """Build a MagicMock structured like the win32gui module.

    ``windows_data`` is a list of (hwnd, title, (left, top, right, bottom))
    tuples representing the visible top-level windows the EnumWindows
    callback will visit.
    """
    fake = MagicMock()
    # Lookup maps so per-hwnd metadata queries return the right thing.
    title_map = {hwnd: title for hwnd, title, _rect in windows_data}
    rect_map = {hwnd: rect for hwnd, _title, rect in windows_data}

    fake.IsWindowVisible.return_value = True
    fake.GetWindowText.side_effect = lambda hwnd: title_map.get(hwnd, "")
    fake.GetWindowRect.side_effect = lambda hwnd: rect_map.get(hwnd, (0, 0, 0, 0))

    def _enum_windows(callback, results):
        for hwnd, _title, _rect in windows_data:
            # pywin32 callback contract: return True to continue enumeration.
            if callback(hwnd, results) is False:
                break

    fake.EnumWindows.side_effect = _enum_windows
    return fake


def test_find_window_bounds_matches_serato(monkeypatch):
    """Plain substring match — Serato window returned, others filtered out."""
    fake_win32gui = _make_fake_win32gui(
        [
            (101, "Untitled - Notepad", (0, 0, 800, 600)),
            (102, "Serato DJ Pro", (100, 100, 1900, 1100)),
            (103, "Chrome", (50, 50, 1200, 800)),
        ]
    )
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)

    out = ScreenWindows().find_window_bounds("serato")
    # rect (100, 100, 1900, 1100) → x=100, y=100, w=1800, h=1000
    assert out == WindowBounds(x=100, y=100, width=1800, height=1000)


def test_find_window_bounds_case_insensitive(monkeypatch):
    """Substring match must be case-insensitive on BOTH sides — TRAKTOR
    title vs lowercase 'traktor' needle."""
    fake_win32gui = _make_fake_win32gui(
        [
            (201, "TRAKTOR PRO 3 - Deck A", (0, 0, 1280, 1024)),
        ]
    )
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)

    out = ScreenWindows().find_window_bounds("traktor")
    assert out == WindowBounds(x=0, y=0, width=1280, height=1024)


def test_find_window_bounds_returns_none_when_no_match(monkeypatch):
    fake_win32gui = _make_fake_win32gui(
        [
            (301, "Safari", (0, 0, 1200, 800)),
            (302, "Mail", (100, 100, 900, 700)),
        ]
    )
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)

    assert ScreenWindows().find_window_bounds("djay") is None


def test_find_window_bounds_skips_too_small_windows(monkeypatch):
    """Mirrors macOS — windows narrower than 200px or shorter than 200px
    are skipped (probably mini/overlay/icon windows, not real DJ UIs)."""
    fake_win32gui = _make_fake_win32gui(
        [
            (401, "djay Pro Mini", (0, 0, 199, 199)),  # too small → skipped
        ]
    )
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)

    assert ScreenWindows().find_window_bounds("djay") is None


def test_find_window_bounds_picks_largest_on_multi_match(monkeypatch):
    """Two matching windows — must return the one with the larger area."""
    fake_win32gui = _make_fake_win32gui(
        [
            (501, "djay Pro Main", (0, 0, 1200, 800)),  # 1200x800 = 960000
            (502, "djay Pro Mini", (0, 0, 200, 200)),  # 200x200 = 40000
        ]
    )
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)

    out = ScreenWindows().find_window_bounds("djay")
    assert out == WindowBounds(x=0, y=0, width=1200, height=800)


def test_find_window_bounds_skips_invisible_windows(monkeypatch):
    """IsWindowVisible(hwnd) == False → window ignored even if title matches."""
    fake_win32gui = _make_fake_win32gui(
        [
            (601, "Serato DJ Pro (hidden)", (0, 0, 1600, 1000)),
        ]
    )
    # Override IsWindowVisible to return False for hwnd 601.
    fake_win32gui.IsWindowVisible.side_effect = lambda hwnd: hwnd != 601
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)

    assert ScreenWindows().find_window_bounds("serato") is None


def test_find_window_bounds_returns_none_when_pywin32_unavailable(monkeypatch):
    """No win32gui in sys.modules + ImportError on lazy import → None
    (graceful fallback, not crash)."""
    # Remove any existing win32gui entry to force ImportError.
    monkeypatch.delitem(sys.modules, "win32gui", raising=False)

    # Block the import by inserting a meta-path finder that refuses win32gui.
    class _Blocker:
        def find_spec(self, name, _path=None, _target=None):
            if name == "win32gui":
                raise ImportError("blocked for test")
            return None

    monkeypatch.setattr(sys, "meta_path", [_Blocker(), *sys.meta_path])
    out = ScreenWindows().find_window_bounds("djay")
    assert out is None


# ---------- find_dj_window convenience ----------


def test_find_dj_window_returns_first_hint_match(monkeypatch):
    """find_dj_window iterates _DJ_HINTS and returns the FIRST match
    (priority order = the tuple order)."""
    fake_win32gui = _make_fake_win32gui(
        [
            (701, "rekordbox 7", (0, 0, 1200, 800)),
            (702, "VirtualDJ 2026", (0, 0, 1400, 900)),
        ]
    )
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)
    # _DJ_HINTS order: djay, serato, traktor, rekordbox, virtualdj
    # → rekordbox hits first.
    out = ScreenWindows().find_dj_window()
    assert out == WindowBounds(x=0, y=0, width=1200, height=800)


def test_find_dj_window_returns_none_when_no_dj_app_present(monkeypatch):
    fake_win32gui = _make_fake_win32gui(
        [
            (801, "Visual Studio Code", (0, 0, 1400, 900)),
        ]
    )
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)
    assert ScreenWindows().find_dj_window() is None


# ---------- capture() ----------


def test_capture_no_bounds_produces_jpeg(mocker, monkeypatch):
    """Mock mss + PIL + win32gui to verify the capture pipeline produces JPEG.

    Phase 8: mss is win32-only in pyproject; on a macOS dev box mss is no
    longer installed, so the module-top ``import mss`` block falls into the
    ImportError branch (``_HAS_MSS=False``). Tests that exercise the capture
    pipeline must restore ``_HAS_MSS=True`` AND patch the ``mss`` attribute
    on the module to a fake — without those, ``is_available()`` returns
    False and ``capture()`` raises before reaching the mss call.
    """
    # win32gui must be in sys.modules so is_available() passes the pywin32
    # check (otherwise capture() raises RuntimeError).
    monkeypatch.setitem(sys.modules, "win32gui", MagicMock())
    # Phase 8 compat: restore the _HAS_MSS gate + bind a fake mss attribute.
    fake_mss_module = MagicMock()
    mocker.patch("vibemix.platform._screen_windows._HAS_MSS", True)
    mocker.patch("vibemix.platform._screen_windows.mss", fake_mss_module)
    fake_raw = MagicMock()
    fake_raw.size = (1920, 1080)
    fake_raw.bgra = bytes(1920 * 1080 * 4)
    fake_sct = MagicMock()
    fake_sct.monitors = [None, {"width": 1920, "height": 1080}]
    fake_sct.grab.return_value = fake_raw
    fake_sct.__enter__.return_value = fake_sct
    fake_sct.__exit__.return_value = False
    fake_mss_module.mss.return_value = fake_sct

    s = ScreenWindows()
    frame = s.capture(bounds=None, max_width=1280, max_height=800, jpeg_quality=82)
    assert isinstance(frame.jpeg, bytes)
    assert len(frame.jpeg) > 0
    assert frame.width <= 1280
    assert frame.height <= 800
    # PIL JPEG magic header (0xff 0xd8).
    assert frame.jpeg.startswith(b"\xff\xd8")


def test_capture_with_bounds_invokes_crop(mocker, monkeypatch):
    """When bounds is supplied AND scaled crop > 200x200, Image.crop is called.

    Phase 8 compat: same pattern as ``test_capture_no_bounds_produces_jpeg``
    — restore ``_HAS_MSS=True`` and bind a fake mss module attribute, since
    mss is no longer installed on macOS dev boxes after the win32-only
    marker landed.
    """
    monkeypatch.setitem(sys.modules, "win32gui", MagicMock())
    # Phase 8 compat: restore the _HAS_MSS gate + bind a fake mss attribute.
    fake_mss_module = MagicMock()
    mocker.patch("vibemix.platform._screen_windows._HAS_MSS", True)
    mocker.patch("vibemix.platform._screen_windows.mss", fake_mss_module)
    # Build a fake mss grab pipeline.
    fake_raw = MagicMock()
    fake_raw.size = (1920, 1080)
    fake_raw.bgra = bytes(1920 * 1080 * 4)
    fake_sct = MagicMock()
    fake_sct.monitors = [None, {"width": 1920, "height": 1080}]
    fake_sct.grab.return_value = fake_raw
    fake_sct.__enter__.return_value = fake_sct
    fake_sct.__exit__.return_value = False
    fake_mss_module.mss.return_value = fake_sct

    # Mock PIL.Image so we can spy on .crop().
    fake_img = MagicMock()
    fake_img.size = (1920, 1080)
    fake_cropped = MagicMock()
    fake_cropped.size = (1600, 900)
    # crop returns a cropped MagicMock whose subsequent .thumbnail / .save
    # behaviour we don't care about — we ASSERT crop was called once.
    fake_img.crop.return_value = fake_cropped

    def _fake_save(buf, *_args, **_kwargs):
        buf.write(b"\xff\xd8\xfffake-jpeg-bytes")

    fake_cropped.save.side_effect = _fake_save
    fake_img.save.side_effect = _fake_save
    mocker.patch(
        "vibemix.platform._screen_windows.Image.frombytes",
        return_value=fake_img,
    )

    s = ScreenWindows()
    bounds = WindowBounds(x=100, y=50, width=1600, height=900)
    s.capture(bounds=bounds)

    # crop was called once with (px, py, px+pw, py+ph) — scale = 1.0 because
    # raw_size == monitor_size.
    fake_img.crop.assert_called_once_with((100, 50, 100 + 1600, 50 + 900))


def test_capture_raises_when_unavailable(mocker):
    """is_available() False → capture() raises RuntimeError (parity with
    macOS impl which raises 'ScreenMacOS dependencies unavailable...')."""
    mocker.patch("vibemix.platform._screen_windows._HAS_MSS", False)
    s = ScreenWindows()
    with pytest.raises(RuntimeError, match="ScreenWindows dependencies unavailable"):
        s.capture(bounds=None)


# ---------- is_available() ----------


def test_is_available_true_when_all_mocked(monkeypatch, mocker):
    """is_available() returns True iff mss + PIL + win32gui all import
    successfully. PIL + win32gui can be mocked directly; mss is win32-only
    in pyproject (Phase 8) so on macOS dev boxes the module-top
    ``_HAS_MSS`` is False — restore it to True for this test to exercise
    the all-deps-present path."""
    fake_win32gui = MagicMock()
    monkeypatch.setitem(sys.modules, "win32gui", fake_win32gui)
    # Phase 8 compat: restore _HAS_MSS to True (mss is uninstalled on macOS).
    mocker.patch("vibemix.platform._screen_windows._HAS_MSS", True)
    assert ScreenWindows().is_available() is True


def test_is_available_false_when_pywin32_missing(monkeypatch):
    """When win32gui import fails → is_available() returns False
    (graceful fallback path used at startup to decide whether to spawn
    the capture loop)."""
    monkeypatch.delitem(sys.modules, "win32gui", raising=False)

    class _Blocker:
        def find_spec(self, name, _path=None, _target=None):
            if name == "win32gui":
                raise ImportError("blocked for test")
            return None

    monkeypatch.setattr(sys, "meta_path", [_Blocker(), *sys.meta_path])
    assert ScreenWindows().is_available() is False


# ---------- latest() ----------


def test_latest_delegates_to_internal_buffer():
    s = ScreenWindows()
    s._buffer.push(b"hello-jpeg", 100, 100)
    assert s.latest() == (b"hello-jpeg", (100, 100))
