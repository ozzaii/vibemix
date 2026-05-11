# Windows Setup — Running vibemix from Source

## 1. What this doc is for

Phases 1–7 ship a cross-platform Python package. Phase 11 (Tauri shell) and Phase 18 (PyInstaller + SignPath MSI) ship the real end-user installer. **This doc is for running vibemix on Windows from source today** — before the installer exists.

Audiences:

1. Kaan's Phase 20 fresh-Windows-machine rehearsal.
2. Early Windows DJ-friend testers running vibemix from source before Phase 18.

Out of scope: end-user installer, auto-update, signed binary. Those land in Phases 11 + 18.

## 2. Prerequisites

- **Windows 10 build 19041+ or Windows 11** — required for WASAPI loopback (PyAudioWPatch) and Global System Media Transport Controls (winsdk).
- **Python 3.12.x from python.org** — *not* the Microsoft Store version. The Store version has PATH issues with PyInstaller (relevant for Phase 18, easier to fix early).
- **uv (Astral)** — the project's Python package manager:
  ```powershell
  winget install astral-sh.uv
  # or: irm https://astral.sh/uv/install.ps1 | iex
  ```
- **A DJ controller** — Pioneer DDJ-FLX4 is the v1 reference. Phase 9 expands the controller library.
- **Default playback device at 48000 Hz, 16-bit**: Control Panel → Sound → Properties → Advanced → Default Format. This is the Windows equivalent of macOS Audio MIDI Setup.

## 3. Install steps

Paste-able PowerShell block:

```powershell
git clone https://github.com/ozzaii/vibemix.git
cd vibemix

# uv sync picks up Windows-only deps automatically via sys_platform markers in pyproject.toml.
uv sync

# pywin32 sometimes needs a post-install step on Windows.
# The script ships inside the installed pywin32 package — locate via:
$pywin32Dir = uv run python -c "import os, win32api; print(os.path.dirname(os.path.dirname(win32api.__file__)))"
uv run python "$pywin32Dir\pywin32_system32\pywin32_postinstall.py" -install

# API key — get one from https://aistudio.google.com/apikey
Set-Content .env "GEMINI_API_KEY=your_key_here"
```

If `uv run python` complains about a missing `pyaudiowpatch` wheel, run `uv pip install pyaudiowpatch` manually.

## 4. Sample-rate calibration

Control Panel → Sound → Playback → (your default playback device) → Properties → Advanced → Default Format → **48000 Hz, 16-bit, Stereo**.

This is the Windows analogue of macOS's Audio MIDI Setup. Phase 7's `AudioWindows.assert_wasapi_loopback_rate` will refuse to start if the loopback device reports a mismatched rate — same guard as macOS's BlackHole-Sonoma rate-halving detector.

## 5. Run

Sanity check that the platform selector resolved to the Windows backends:

```powershell
uv run python -c "import vibemix.platform; print(vibemix.platform.AudioImpl.__name__)"
# expected: AudioWindows
```

Smoke run (Phase 11 ships the full entry point — for now the smoke main is the entry):

```powershell
uv run python -m vibemix
```

## 6. DJ controller setup

1. Plug in the DDJ-FLX4 via USB.
2. Windows auto-installs the Pioneer driver. (No manual driver download needed for FLX4.)
3. vibemix's `MidiWindows` finds the controller via substring match on the port name `"DDJ-FLX4"`.
4. Confirm detection: `uv run python -c "from vibemix.platform import MidiImpl; print(MidiImpl().list_input_ports())"`. The DDJ-FLX4 port should appear.

Phase 9 expands this to a 10-controller library (DDJ-200, DDJ-400, DDJ-FLX6, Hercules Inpulse 300, NI Traktor S2 MK3, Reloop Beatmix 2/4, Numark Mixtrack, etc.) with generic-MIDI fallback for unmapped controllers.

## 7. Troubleshooting

- **`WASAPI loopback device not found`** — confirm default playback device is set and not muted. Reboot may help after a driver install. Check via `uv run python -c "import pyaudiowpatch as pya; p = pya.PyAudio(); print(p.get_default_wasapi_loopback())"`.
- **`SampleRateMismatchError`** — repeat Section 4 and set Default Format = 48000 Hz, 16-bit, Stereo.
- **`pywin32 ImportError`** — re-run the `pywin32_postinstall.py -install` step from Section 3.
- **`winsdk ImportError`** — `uv pip install winsdk` manually if the sys_platform marker didn't fire. Rare; report as an issue if it happens on a clean Windows install.
- **SMTC returns no title** — expected for some DJ apps. Serato / Traktor / rekordbox / VirtualDJ all expose to SMTC differently; djay Pro on Windows is known to not expose to SMTC in all builds. This is a documented v1 limitation; `TrackWindows` gracefully returns `None` and the AI runs without track-title context (still works on audio + screen + MIDI).

## 8. What's deferred to future phases

- **Tauri shell + auto-install**: Phase 11.
- **MSI installer with SignPath OSS code signing**: Phase 18.
- **CI matrix on `windows-latest`** (live tests run against real hardware): Phase 20.
- **Hot-plug device re-binding** (default playback changes mid-session): post-v1.
- **App-specific SMTC scrapers** for DJ apps that don't expose: Phase 9 / 11 if it becomes a real friction point.
