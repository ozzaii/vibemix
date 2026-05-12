# SPDX-License-Identifier: Apache-2.0
# vibemix-core.macos.spec — PyInstaller --onedir spec for the macOS sidecar.
#
# [VERIFIED: PyInstaller Context7 /pyinstaller/pyinstaller]
# [VERIFIED: 11-RESEARCH.md §Pitfall 2 — hidden-import misses]
# [VERIFIED: 11-RESEARCH.md §Pitfall 5 — AIza key leak]
#
# Phase 11 Wave 1 — produces ``dist/vibemix-core/vibemix-core`` (no extension
# on macOS). ``scripts/build_sidecar.py`` then renames + moves the bundle
# into ``tauri/src-tauri/binaries/vibemix-core-<rustc target triple>/``
# with the inner binary suffixed by the target triple — that's what Tauri's
# ``externalBin`` configuration expects (RESEARCH Pitfall 4).
#
# NEVER set ``--onefile`` or ``upx=True`` (RESEARCH Pitfall 1: AV / Defender
# false positives). NEVER set ``console=True`` (Tauri spawns this headless;
# we don't want a stray terminal window during normal user runs).
#
# Run via: ``uv run pyinstaller vibemix-core.macos.spec --clean --noconfirm``.

# ruff: noqa: F821  # PyInstaller injects Analysis / PYZ / EXE / COLLECT at
# spec-file exec time; the linter doesn't know about them.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

# ---------------------------------------------------------------------------
# Hidden imports — packages whose ``__import__`` is dynamic and therefore
# invisible to PyInstaller's AST walker (RESEARCH Pitfall 2).
# ---------------------------------------------------------------------------

hiddenimports: list[str] = []
binaries: list[tuple[str, str]] = []
datas: list[tuple[str, str]] = []

# Third-party deps with dynamic dispatch / plugin discovery.
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
)
for _pkg in _DYNAMIC_PKGS:
    try:
        hiddenimports.extend(collect_submodules(_pkg))
    except Exception as exc:  # pragma: no cover — defensive
        print(f"[spec] collect_submodules({_pkg!r}) skipped: {exc}", file=sys.stderr)

# vibemix sub-packages — explicit so PyInstaller picks up every Phase 2-10
# leaf module (cohost*.py POC files are intentionally NOT bundled).
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

# pyobjc frameworks — ``collect_all`` returns (binaries, datas, hiddenimports)
# Try each individually; some frameworks may not be present on every macOS
# version. Graceful degradation per RESEARCH Pitfall 2.
_PYOBJC_FRAMEWORKS = (
    "ScreenCaptureKit",
    "Quartz",
    "Cocoa",
    "AVFoundation",
    "CoreAudio",
)
for _fw in _PYOBJC_FRAMEWORKS:
    try:
        b, d, h = collect_all(f"pyobjc.framework.{_fw}")
        binaries.extend(b)
        datas.extend(d)
        hiddenimports.extend(h)
    except Exception as exc:  # pragma: no cover — graceful per Pitfall 2
        print(f"[spec] collect_all(pyobjc.framework.{_fw}) skipped: {exc}", file=sys.stderr)

# ---------------------------------------------------------------------------
# Data files — JSON profiles, prompts, IPC schema. Explicitly excludes
# secrets-bearing patterns (RESEARCH Pitfall 5 — API key leak gate).
# ---------------------------------------------------------------------------

datas += collect_data_files(
    "vibemix",
    includes=["**/*.json", "**/*.txt"],
    excludes=["*.env", ".env*", "*credentials*", "*.key", "*.pem"],
)

# The ipc messages schema lives outside the package tree (under tauri/ui/);
# include it explicitly so vibemix.ui_bus can locate it inside the bundle.
_IPC_SCHEMA = Path("tauri/ui/src/ipc/messages.schema.json")
if not _IPC_SCHEMA.exists():
    raise RuntimeError(
        f"vibemix-core.macos.spec: expected IPC schema at {_IPC_SCHEMA} — "
        "Phase 11 Wave 0 should have created it."
    )
datas += [(str(_IPC_SCHEMA), "tauri/ui/src/ipc")]

# Phase 9 controller profiles (10 JSONs) — already picked up by
# ``collect_data_files('vibemix', includes=['**/*.json'])`` above, but list
# them explicitly so a missing-file regression fails the build loudly.
_MIDI_PROFILES = Path("src/vibemix/midi/profiles")
if not _MIDI_PROFILES.is_dir():
    raise RuntimeError(f"vibemix-core.macos.spec: missing {_MIDI_PROFILES}")

# Phase 6 genre profiles (5 JSONs) — same defensive check.
_GENRE_PROFILES = Path("src/vibemix/state/genre/profiles")
if not _GENRE_PROFILES.is_dir():
    raise RuntimeError(f"vibemix-core.macos.spec: missing {_GENRE_PROFILES}")

# ---------------------------------------------------------------------------
# Binaries — bundled native executables.
# ---------------------------------------------------------------------------

# nowplaying-cli is required by ``vibemix.platform._track_macos`` (Phase 3)
# to poll the macOS NowPlaying framework. Apple Silicon brew lives under
# /opt/homebrew/bin/; Intel Macs land at /usr/local/bin/. Either is fine.
_NOWPLAYING_CANDIDATES = (
    Path("/opt/homebrew/bin/nowplaying-cli"),  # Apple Silicon
    Path("/usr/local/bin/nowplaying-cli"),  # Intel Mac fallback
)
_nowplaying = next((p for p in _NOWPLAYING_CANDIDATES if p.exists()), None)
if _nowplaying is None:
    raise RuntimeError(
        "vibemix-core.macos.spec: nowplaying-cli not found at /opt/homebrew/bin/ or "
        "/usr/local/bin/. Install via: `brew install nowplaying-cli` "
        "(documented in CLAUDE.md Platform Requirements)."
    )
binaries += [(str(_nowplaying), ".")]

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
    # Exclude dev / test tooling so they never accidentally land in the
    # shipping bundle. ``pyinstaller`` itself is in dev deps; explicit
    # exclude blocks recursive bundling.
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
    upx=False,  # NEVER True — AV false positives (RESEARCH Pitfall 1)
    console=False,  # Tauri spawns headless; no stray terminal
    disable_windowed_traceback=False,
    target_arch=None,  # PyInstaller auto-detects host arch
    codesign_identity=None,  # Phase 18 signs the entire bundle
    entitlements_file=None,  # see tauri/src-tauri/entitlements.plist
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
