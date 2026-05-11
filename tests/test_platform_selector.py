# SPDX-License-Identifier: Apache-2.0
"""Platform selector tests — sys.platform-dispatched concrete impl re-exports
+ pyproject Windows-only dependency markers (Phase 7 Wave 1).

Pins:
- ``AudioImpl`` / ``ScreenImpl`` / ``MidiImpl`` / ``TrackImpl`` resolve to the
  Phase 2/3 macOS implementations on darwin.
- Importing ``vibemix.platform`` on darwin does NOT pull pyaudiowpatch / win32 /
  winsdk / any ``_*_windows`` module into ``sys.modules``.
- Selector raises ``RuntimeError`` on unsupported platforms (not darwin or
  win32) — Linux is explicitly excluded per PROJECT.md.
- ``pyproject.toml`` has the three Windows-only deps with
  ``sys_platform == 'win32'`` markers.
"""

from __future__ import annotations

import importlib
import sys
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"


# ---------- Selector resolves to macOS impls on darwin ----------


@pytest.mark.skipif(sys.platform != "darwin", reason="darwin-only selector pinning")
def test_selector_resolves_macos_impls_on_darwin():
    """On darwin, ``AudioImpl is AudioMacOS`` etc. — selector picked the
    macOS branch."""
    from vibemix.platform import (
        AudioImpl,
        AudioMacOS,
        MidiImpl,
        MidiMacOS,
        ScreenImpl,
        ScreenMacOS,
        TrackImpl,
        TrackMacOS,
    )

    assert AudioImpl is AudioMacOS
    assert ScreenImpl is ScreenMacOS
    assert MidiImpl is MidiMacOS
    assert TrackImpl is TrackMacOS


@pytest.mark.skipif(sys.platform != "darwin", reason="darwin-only leak check")
def test_selector_does_not_import_windows_only_modules_on_macos():
    """After ``import vibemix.platform`` on darwin, ``sys.modules`` must NOT
    contain any Windows-specific module — proves the elif win32 branch was
    not evaluated and lazy import discipline holds."""
    # Force a fresh import: drop vibemix.platform from sys.modules and
    # re-import.
    for key in list(sys.modules):
        if key == "vibemix.platform" or key.startswith("vibemix.platform."):
            del sys.modules[key]

    importlib.import_module("vibemix.platform")

    forbidden_exact = {"pyaudiowpatch", "winsdk"}
    for mod in forbidden_exact:
        assert mod not in sys.modules, f"{mod} leaked into sys.modules"
    # win32* covers pywin32 surface (win32api, win32gui, win32con, ...).
    win32_leaks = [m for m in sys.modules if m.startswith("win32")]
    assert win32_leaks == [], f"win32* leaked: {win32_leaks}"
    # Concrete Windows impls also must NOT have been imported.
    for win_impl in (
        "vibemix.platform._audio_windows",
        "vibemix.platform._screen_windows",
        "vibemix.platform._midi_windows",
        "vibemix.platform._track_windows",
    ):
        assert win_impl not in sys.modules, f"{win_impl} leaked into sys.modules"


# ---------- Selector raises on unsupported platforms ----------


def test_selector_raises_on_unsupported_platform(monkeypatch):
    """``sys.platform == "linux"`` must raise ``RuntimeError`` from the
    selector ``else`` branch — Linux is explicitly out of v1 scope."""
    monkeypatch.setattr(sys, "platform", "linux")
    # Force a fresh import so the selector re-evaluates against the patched
    # platform.
    for key in list(sys.modules):
        if key == "vibemix.platform" or key.startswith("vibemix.platform."):
            del sys.modules[key]

    with pytest.raises(RuntimeError) as exc_info:
        importlib.import_module("vibemix.platform")

    msg = str(exc_info.value)
    assert "Unsupported platform" in msg
    assert "macOS and Windows" in msg


# ---------- pyproject.toml — Windows-only dep markers ----------


def test_pyproject_contains_windows_only_markers():
    """`pyproject.toml` `[project] dependencies` must list the three Windows-
    only deps each gated on ``sys_platform == 'win32'`` so ``uv sync`` skips
    them on darwin and PyInstaller on Windows picks them up."""
    data = tomllib.loads(PYPROJECT_PATH.read_text())
    deps = data["project"]["dependencies"]
    needed = {"pyaudiowpatch", "pywin32", "winsdk"}
    found_with_marker: dict[str, str] = {}
    for spec in deps:
        # Each entry is "<name><spec> ; <marker>" or just "<name><spec>".
        head = spec.split(";", 1)[0].strip()
        # Pull the bare package name off the head (split on any of <, >, =, !, [, space).
        pkg = ""
        for ch in head:
            if ch in "<>=!~[ ":
                break
            pkg += ch
        if pkg in needed and ";" in spec:
            marker = spec.split(";", 1)[1].strip()
            found_with_marker[pkg] = marker

    missing = needed - set(found_with_marker)
    assert not missing, f"missing Windows-only deps in pyproject.toml: {missing}"
    for pkg, marker in found_with_marker.items():
        assert "sys_platform" in marker and "win32" in marker, (
            f"{pkg} marker missing sys_platform == 'win32': {marker!r}"
        )


def test_pyproject_no_windows_deps_without_marker():
    """Sanity: none of the three Windows-only deps may appear without the
    ``sys_platform == 'win32'`` marker (would force install on macOS)."""
    data = tomllib.loads(PYPROJECT_PATH.read_text())
    deps = data["project"]["dependencies"]
    needed = {"pyaudiowpatch", "pywin32", "winsdk"}
    for spec in deps:
        head = spec.split(";", 1)[0].strip()
        pkg = ""
        for ch in head:
            if ch in "<>=!~[ ":
                break
            pkg += ch
        if pkg in needed:
            assert ";" in spec, (
                f"{pkg} listed without sys_platform marker — would force install on macOS: {spec!r}"
            )
