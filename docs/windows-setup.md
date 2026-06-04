# Windows Setup — Running vibemix from Source

## 1. What this doc is for

This doc is for running vibemix on Windows from source. The end-user Windows
release path is the SignPath-signed Inno EXE, `vibemix-installer.exe`; see
`installer/windows/README.md` and `docs/release-process.md` for packaging,
signing, release, and updater details.

Audiences:

1. Kaan's Phase 20 fresh-Windows-machine rehearsal and diagnostics.
2. Early Windows DJ-friend testers running vibemix from source.
3. Contributors who need a debuggable Windows environment without building
   the installer.

This page does not replace the installer runbooks. Use it when you need source
checkout behavior, dependency debugging, or hardware/audio diagnostics.

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

# uv sync picks up Windows-only deps automatically via sys_platform markers.
# --extra ai-local adds the local CLAP/CUE runtime deps used by the
# product path.
uv sync --extra ai-local

# pywin32 sometimes needs a post-install step on Windows.
# The script ships inside the installed pywin32 package — locate via:
$pywin32Dir = uv run python -c "import os, win32api; print(os.path.dirname(os.path.dirname(win32api.__file__)))"
uv run python "$pywin32Dir\pywin32_system32\pywin32_postinstall.py" -install

# Optional agent key for BYO-key testing. Local Library embeddings use CLAP ONNX.
Set-Content .env "GEMINI_API_KEY=your_key_here"
```

If `uv run python` complains about a missing `pyaudiowpatch` wheel, run `uv pip install pyaudiowpatch` manually.

## 4. Local Chatterbox voice

Sven's product voice is local Chatterbox only. There is no Cartesia, Gemini,
OpenAI, or other cloud TTS fallback in the runtime. Chatterbox currently renders
through `mlx-audio` on Apple Silicon, so Windows source runs are expected to be
voiceless until the Windows GPU backend follow-up lands. The app must degrade as
muted/unready rather than silently choosing a paid voice.

Check the local model state:

```powershell
uv run python -m vibemix library models --json
```

The `chatterbox-voice` row reports the production reference clip and local
engine availability. There is no Windows install target for the voice in this
lane. Required setup from source installs CLAP only:

```powershell
uv run python -m vibemix library models --install clap --json
```

On macOS Apple Silicon, release/dev builds place the approved reference clip at
`~/.cache/vibemix/cohost_voice_ref.wav` or set:

```powershell
$env:VIBEMIX_CHATTERBOX_REF = "C:\path\to\cohost_voice_ref.wav"
```

That reference is still not enough for Windows speech until the Windows backend
exists; it only makes the configuration state explicit.

## 5. Sample-rate calibration

Control Panel → Sound → Playback → (your default playback device) → Properties → Advanced → Default Format → **48000 Hz, 16-bit, Stereo**.

This is the Windows analogue of macOS's Audio MIDI Setup. Phase 7's `AudioWindows.assert_wasapi_loopback_rate` will refuse to start if the loopback device reports a mismatched rate — same guard as macOS's BlackHole-Sonoma rate-halving detector.

## 6. Run

Sanity check that the platform selector resolved to the Windows backends:

```powershell
uv run python -c "import vibemix.platform; print(vibemix.platform.AudioImpl.__name__)"
# expected: AudioWindows
```

Smoke run (Phase 11 ships the full entry point — for now the smoke main is the entry):

```powershell
uv run python -m vibemix
```

## 7. DJ controller setup

1. Plug in the DDJ-FLX4 via USB.
2. Windows auto-installs the Pioneer driver. (No manual driver download needed for FLX4.)
3. vibemix's `MidiWindows` finds the controller via substring match on the port name `"DDJ-FLX4"`.
4. Confirm detection: `uv run python -c "from vibemix.platform import MidiImpl; print(MidiImpl().list_input_ports())"`. The DDJ-FLX4 port should appear.

Phase 9 expands this to a 10-controller library (DDJ-200, DDJ-400, DDJ-FLX6, Hercules Inpulse 300, NI Traktor S2 MK3, Reloop Beatmix 2/4, Numark Mixtrack, etc.) with generic-MIDI fallback for unmapped controllers.

## 8. Troubleshooting

- **Sven is silent / voice is unavailable** — run `uv run python -m vibemix library models --json` and inspect the `chatterbox-voice` row. On Windows this is currently expected; the app does not fall back to cloud TTS.
- **`WASAPI loopback device not found`** — confirm default playback device is set and not muted. Reboot may help after a driver install. Check via `uv run python -c "import pyaudiowpatch as pya; p = pya.PyAudio(); print(p.get_default_wasapi_loopback())"`.
- **`SampleRateMismatchError`** — repeat Section 5 and set Default Format = 48000 Hz, 16-bit, Stereo.
- **`pywin32 ImportError`** — re-run the `pywin32_postinstall.py -install` step from Section 3.
- **`winsdk ImportError`** — `uv pip install winsdk` manually if the sys_platform marker didn't fire. Rare; report as an issue if it happens on a clean Windows install.
- **SMTC returns no title** — expected for some DJ apps. Serato / Traktor / rekordbox / VirtualDJ all expose to SMTC differently; djay Pro on Windows is known to not expose to SMTC in all builds. This is a documented v1 limitation; `TrackWindows` gracefully returns `None` and the AI runs without track-title context (still works on audio + screen + MIDI).

## 9. Related release docs

- **Windows installer**: `installer/windows/README.md` builds `vibemix-installer.exe`.
- **Signing**: `docs/signing-windows.md` covers SignPath and Authenticode checks.
- **Release and updater**: `docs/release-process.md` and `docs/updater.md` cover
  release upload and updater artifacts.
- **Install rehearsal**: `docs/install-rehearsal.md` is the stopwatch checklist
  for clean Windows and macOS machines.
