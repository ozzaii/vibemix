# SPDX-License-Identifier: Apache-2.0
# vibemix-core.windows.spec — PyInstaller --onedir spec for the Windows sidecar.
#
# [VERIFIED: PyInstaller Context7 /pyinstaller/pyinstaller]
# [VERIFIED: 11-RESEARCH.md §Pitfall 2 — hidden-import misses]
# [VERIFIED: 11-RESEARCH.md §Pitfall 5 — AIza key leak]
#
# Phase 11 Wave 1 — produces ``dist/vibemix-core/vibemix-core.exe``.
# ``scripts/build_sidecar.py`` then renames + moves the bundle into
# ``tauri/src-tauri/binaries/vibemix-core-<rustc target triple>/`` with the
# inner binary suffixed by the target triple (e.g.
# ``vibemix-core-x86_64-pc-windows-msvc.exe``).
#
# NEVER set ``--onefile`` or ``upx=True`` (RESEARCH Pitfall 1: Defender
# false positives). NEVER set ``console=True`` — Tauri spawns this headless
# and stdout/stderr are captured by the Rust shell's log file.
#
# This spec is verified compile-only on macOS (Kaan's dev rig). The
# authoritative Windows build runs in Phase 20 CI matrix.

# ruff: noqa: F821  # PyInstaller injects Analysis / PYZ / EXE / COLLECT.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ---------------------------------------------------------------------------
# Hidden imports — packages whose ``__import__`` is dynamic and therefore
# invisible to PyInstaller's AST walker (RESEARCH Pitfall 2).
# ---------------------------------------------------------------------------

hiddenimports: list[str] = []
binaries: list[tuple[str, str]] = []
datas: list[tuple[str, str]] = []

# Third-party deps with dynamic dispatch / plugin discovery. mss IS bundled
# on Windows (Phase 8 left mss on Windows; macOS migrated to
# ScreenCaptureKit). PIL ships on both.
_DYNAMIC_PKGS = (
    "scipy",
    "scipy.signal",
    "sounddevice",
    "mido",
    "rtmidi",
    "livekit",
    "livekit.agents",
    "livekit.plugins.google",
    "livekit.plugins.openai",
    "google.genai",
    "google.cloud",
    "mss",
    "PIL",
    "jsonschema",
    # Phase 7 Windows-only deps. Hidden imports because each uses dynamic
    # extension loading the AST walker misses.
    "pyaudiowpatch",
    "pywin32",
    "win32api",
    "win32gui",
    "win32process",
    "win32con",
    "winsdk",
    "winsdk.windows.media.control",
)
for _pkg in _DYNAMIC_PKGS:
    try:
        hiddenimports.extend(collect_submodules(_pkg))
    except Exception as exc:  # pragma: no cover — defensive
        print(f"[spec] collect_submodules({_pkg!r}) skipped: {exc}", file=sys.stderr)

# vibemix sub-packages — Phase 1-10 leaf modules. pyobjc.framework.* is
# NOT included on Windows (no macOS frameworks).
for _pkg in (
    "vibemix",
    "vibemix.agent",
    "vibemix.audio",
    "vibemix.midi",
    "vibemix.platform",
    "vibemix.prompts",
    "vibemix.runtime",
    "vibemix.state",
    "vibemix.ui_bus",
):
    try:
        hiddenimports.extend(collect_submodules(_pkg))
    except Exception as exc:  # pragma: no cover
        print(f"[spec] collect_submodules({_pkg!r}) skipped: {exc}", file=sys.stderr)

# pyobjc IS NOT collected on Windows. Guard belt-and-braces in case the
# spec is accidentally executed on macOS — log + skip rather than crash.
if sys.platform == "darwin":
    print(
        "[spec] WARNING: vibemix-core.windows.spec executed on macOS; pyobjc "
        "collect_all intentionally skipped — use vibemix.spec.macos instead.",
        file=sys.stderr,
    )

# ---------------------------------------------------------------------------
# Data files — JSON profiles, prompts, IPC schema. Explicit excludes guard
# against accidental .env bundling (RESEARCH Pitfall 5).
# ---------------------------------------------------------------------------

datas += collect_data_files(
    "vibemix",
    includes=["**/*.json", "**/*.txt"],
    excludes=["*.env", ".env*", "*credentials*", "*.key", "*.pem"],
)

# IPC schema lives outside the package tree.
_IPC_SCHEMA = Path("tauri/ui/src/ipc/messages.schema.json")
if not _IPC_SCHEMA.exists():
    raise RuntimeError(
        f"vibemix-core.windows.spec: expected IPC schema at {_IPC_SCHEMA} — "
        "Phase 11 Wave 0 should have created it."
    )
datas += [(str(_IPC_SCHEMA), "tauri/ui/src/ipc")]

# Defensive checks on JSON profile dirs (same as macOS spec).
_MIDI_PROFILES = Path("src/vibemix/midi/profiles")
if not _MIDI_PROFILES.is_dir():
    raise RuntimeError(f"vibemix-core.windows.spec: missing {_MIDI_PROFILES}")
_GENRE_PROFILES = Path("src/vibemix/state/genre/profiles")
if not _GENRE_PROFILES.is_dir():
    raise RuntimeError(f"vibemix-core.windows.spec: missing {_GENRE_PROFILES}")

# ---------------------------------------------------------------------------
# Binaries — no nowplaying-cli on Windows (TrackWindows uses SMTC via
# winsdk; Phase 7 Wave 3).
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Analysis — entry-point script + paths + excludes.
# ---------------------------------------------------------------------------

a = Analysis(
    ["src/vibemix/__main__.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "IPython",
        "pytest",
        "ruff",
        "black",
        "pyinstaller",
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="vibemix-core",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # NEVER True — Defender false positives (RESEARCH Pitfall 1)
    console=False,  # Tauri owns stdout/stderr; no extra console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="vibemix-core",  # produces dist/vibemix-core/
)
