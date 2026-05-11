# Phase 7: Windows Port (Audio + Screen) - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the Windows-side concrete implementations of the four `vibemix.platform` Protocols from Phase 1, so vibemix runs end-to-end on Windows 10/11 with feature parity to macOS. macOS code (`_audio_macos.py`, `_screen_macos.py`, `_midi_macos.py`, `_track_macos.py`) stays untouched; Phase 7 adds parallel `_*_windows.py` files. The platform selector (`vibemix.platform.__init__` factory) routes by `sys.platform`.

**In scope:**
- `src/vibemix/platform/_audio_windows.py` — `AudioWindows` implementing `AudioBackend`. Uses **PyAudioWPatch** (WASAPI loopback fork of PyAudio) to capture the default playback device — **no virtual cable required**. Plus standard PyAudio for mic input and AI-voice output.
- `src/vibemix/platform/_screen_windows.py` — `ScreenWindows` implementing `ScreenBackend`. Uses **mss** (already in stack) for screen pixel grab + **pywin32** `EnumWindows` to find djay/Serato/Traktor/rekordbox/VirtualDJ window bounds. JPEG encoding via Pillow.
- `src/vibemix/platform/_track_windows.py` — `TrackWindows` implementing `TrackInfoBackend`. Uses **winsdk** (Microsoft's official Python winrt bindings, replaces deprecated `winrt`) to read **SMTC** (System Media Transport Controls) — Windows' equivalent of macOS Now Playing. Subscribes to `GlobalSystemMediaTransportControlsSessionManager` and reads `GetCurrentSession().TryGetMediaPropertiesAsync()`.
- `src/vibemix/platform/_midi_windows.py` — `MidiWindows` implementing `MidiBackend`. Reuses Phase 3's `ControllerState` + DDJ-FLX4 `_CC_MAP`/`_NOTE_MAP` verbatim; `mido` + `python-rtmidi` work cross-platform. Only the device-enumeration string changes (Windows MIDI device names differ from macOS).
- Platform selector update: `src/vibemix/platform/__init__.py` exposes factory `AudioBackend = AudioMacOS if sys.platform == "darwin" else AudioWindows`, etc., for all four Protocols. **NEW**: the platform module currently has bare `__init__.py` from Phase 1 with Protocols only; Phase 7 adds the import-by-platform dispatch.
- `src/vibemix/platform/_audio_windows.py` includes a **WASAPI sample-rate sanity check** equivalent to the macOS BlackHole guard: query the device's current sample rate via PyAudio's `get_device_info_by_index` BEFORE opening the stream; raise `SampleRateMismatchError` (from Phase 2) with actionable Windows-specific message ("Open Control Panel → Sound → Properties → Advanced → set Default Format to 48000 Hz, 16-bit").
- Cross-platform `find_input_device(name_substring)` selector — uses `sys.platform` to pick the right backend's `find_input_device` impl.
- `pyproject.toml` adds Windows-only dependency markers: `pyaudiowpatch ; sys_platform == "win32"`, `pywin32 ; sys_platform == "win32"`, `winsdk ; sys_platform == "win32"`. These don't install on macOS — `uv sync` skips them. Phase 11's Tauri / Phase 18's PyInstaller binary on Windows includes them.
- Tests for each Windows impl behind `@pytest.mark.windows_only` (skip on non-Windows hosts). Plus mocked tests (`pytest-mock` over `pyaudiowpatch`, `winsdk`, `win32gui`) that run on macOS CI too. Skip strategy: `pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")` for the live tests; mocked tests run everywhere.

**Out of scope:**
- Hot-plug MIDI re-enumeration → Phase 9
- Curated 10-controller MIDI library beyond DDJ-FLX4 → Phase 9
- Tauri Windows shell + PyInstaller `--onedir` Windows build → Phase 11 / 18
- GitHub Actions Windows CI matrix → Phase 20
- Real-Windows smoke test by Kaan → Phase 20 fresh-machine rehearsal
- Linux platform impls — Linux explicitly out of v1 scope (PROJECT.md)

## Verification Reality Check

Kaan is on macOS. He cannot run Windows code locally. Phase 7 ships:
- **Compiling code** — `python -c "from vibemix.platform import AudioBackend"` works on macOS (the platform selector imports `_audio_macos.py`, ignoring `_audio_windows.py` which only imports its Windows-only deps at function-call time, NOT at module-import time)
- **Mocked unit tests** — pass on macOS CI by mocking PyAudioWPatch, pywin32, winsdk surfaces
- **Live integration tests** — Phase 20's GitHub Actions matrix runs them on `windows-latest`; Kaan's Phase 20 fresh-Windows-machine rehearsal validates manually

Phase 7's "shipped" = code + tests + deployment doc. "Real Windows working" = Phase 20.

</domain>

<decisions>
## Implementation Decisions

### AudioWindows — PyAudioWPatch WASAPI Loopback (locked)
- **Capture path:** WASAPI loopback on the **default playback device** — captures everything routed to system speakers/headphones, no virtual cable. This is the v1 win: Windows users don't need a BlackHole equivalent.
- **Library:** PyAudioWPatch (`pyaudiowpatch` on PyPI) — drop-in PyAudio replacement with WASAPI loopback support added.
- **Sample rate:** 48000 Hz (matches macOS). Sanity check: query `get_default_wasapi_loopback_device()` info BEFORE opening; raise `SampleRateMismatchError` if it reports a non-48000 default.
- **Format:** `paInt16` for the resampled buffer (matches AudioBuffer's int16 dtype). Internal PyAudio capture is `paFloat32`; convert in the callback.
- **Stream params:** matching macOS — frames_per_buffer = INPUT_CHUNK_FRAMES (480), channels = 2 (loopback returns stereo).
- **Output (AI voice + passthrough):** standard PyAudio output streams to the user-selected output device. Same dual-stream pattern as macOS (`start_playback_stream` for 24kHz AI voice; `start_passthrough_stream` for 48kHz stereo passthrough at PASSTHROUGH_GAIN=0.0 — currently disabled).
- **Mic input:** standard PyAudio input stream on the user-selected mic device.
- **Device naming:** Windows device names include things like `"Speakers (Realtek(R) Audio)"`. The platform protocol's `find_input_device(name_substring)` does substring match — caller supplies "Realtek" or similar.

### ScreenWindows — mss + pywin32 EnumWindows (locked)
- **Pixel capture:** `mss` (same as macOS) — cross-platform.
- **Window enumeration:** `win32gui.EnumWindows` + `win32gui.GetWindowText` + `win32gui.GetWindowRect` to find djay/Serato/Traktor/rekordbox/VirtualDJ window bounds.
- **DJ software hint list (locked):** match window titles against `["djay", "serato", "traktor", "rekordbox", "virtualdj"]` (case-insensitive). Same surface as macOS — Phase 7 expands the list since Windows DJ software ecosystem is broader.
- **Crop + JPEG:** Pillow thumbnail to 1280x800 + JPEG quality 82 — same params as macOS.
- **Refresh cadence:** ~1Hz, gated on `state.audible` — same as macOS.

### TrackWindows — SMTC via winsdk (locked)
- **Library:** `winsdk` ≥1.0 (Microsoft's official Python winrt successor — `winrt` is deprecated).
- **API path:** `winsdk.windows.media.control.GlobalSystemMediaTransportControlsSessionManager.request_async()` → `manager.get_current_session()` → `session.try_get_media_properties_async()` → `props.title`, `props.artist`.
- **Polling cadence:** 1Hz (same as macOS `nowplaying-cli`).
- **Format:** match macOS — `f"{artist} - {title}"` when both present.
- **Graceful fallback:** when SMTC is unavailable (e.g., djay doesn't expose to SMTC, or no media session active) → return empty title. Logged once at startup.

### MidiWindows — mido + python-rtmidi (locked, mostly carry-forward)
- **No new logic** — `MidiMacOS` from Phase 3 is the template. `_midi_windows.py` is a near-copy with only:
  - Default device port hint: still `"DDJ-FLX4"` (matches both OSes' MIDI device naming).
  - Threading: same `threading.Thread` daemon pattern.
- **Recommended refactor (Phase 7):** extract the shared MIDI listener into `vibemix.platform._midi_common.py` — both macOS and Windows impl call it. Less duplication; controller-library Phase 9 benefits.

### Platform Selector (locked)
```python
# src/vibemix/platform/__init__.py
import sys
from .audio import AudioBackend as _AudioBackendProtocol
from .screen import ScreenBackend as _ScreenBackendProtocol
from .midi import MidiBackend as _MidiBackendProtocol
from .track import TrackInfoBackend as _TrackInfoBackendProtocol

# Re-export Protocols (Phase 1 contract)
AudioBackend = _AudioBackendProtocol
ScreenBackend = _ScreenBackendProtocol
MidiBackend = _MidiBackendProtocol
TrackInfoBackend = _TrackInfoBackendProtocol

# Concrete impl selector
if sys.platform == "darwin":
    from ._audio_macos import AudioMacOS as AudioImpl
    from ._screen_macos import ScreenMacOS as ScreenImpl
    from ._midi_macos import MidiMacOS as MidiImpl
    from ._track_macos import TrackMacOS as TrackImpl
elif sys.platform == "win32":
    from ._audio_windows import AudioWindows as AudioImpl
    from ._screen_windows import ScreenWindows as ScreenImpl
    from ._midi_windows import MidiWindows as MidiImpl
    from ._track_windows import TrackWindows as TrackImpl
else:
    raise RuntimeError(f"Unsupported platform: {sys.platform}. vibemix supports macOS and Windows only.")
```

### Windows-Only Dependencies (locked)
- `pyaudiowpatch ; sys_platform == "win32"` — WASAPI loopback
- `pywin32 ; sys_platform == "win32"` — Win32 API access (EnumWindows, etc.)
- `winsdk ; sys_platform == "win32"` — SMTC bindings

Mocked tests on macOS use `pytest-mock` to patch these — never actually imported.

### Test Strategy (locked)
- **Live tests** (`@pytest.mark.windows_only` + `pytestmark = pytest.mark.skipif(sys.platform != "win32", ...)`): smoke test each Windows backend against a real Windows runtime. Run only on `windows-latest` GitHub Actions matrix (Phase 20).
- **Mocked tests** (no marker — run everywhere): import each Windows module with all platform deps mocked; assert the AudioBackend/ScreenBackend/MidiBackend/TrackInfoBackend Protocol interface is satisfied; assert key methods (e.g., `find_input_device`, `start_capture`) call the mocked deps with expected args.
- **Cross-platform smoke**: `from vibemix.platform import AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend` works on macOS (current host) without importing any Windows-only deps. Verify the platform selector lazy-imports correctly.

### File Layout
```
src/vibemix/platform/
├── __init__.py             # extended: platform selector
├── audio.py                # Phase 1 Protocol
├── screen.py               # Phase 1 Protocol
├── midi.py                 # Phase 1 Protocol
├── track.py                # Phase 1 Protocol
├── _midi_common.py         # NEW: shared MIDI listener (cross-platform)
├── _audio_macos.py         # Phase 2
├── _audio_windows.py       # NEW
├── _screen_macos.py        # Phase 3
├── _screen_windows.py      # NEW
├── _midi_macos.py          # Phase 3 (refactor to use _midi_common)
├── _midi_windows.py        # NEW (uses _midi_common)
├── _track_macos.py         # Phase 3
└── _track_windows.py       # NEW
```

### Claude's Discretion
- Whether `_midi_common.py` refactor lands in Phase 7 or stays separate. **Recommend YES in Phase 7** — Windows port creates the natural pressure for it; refusing leaves drift between mac and Windows MIDI code.
- Whether to add `keyboard` or `pynput` for global push-to-mute hotkey on Windows. **Recommend defer to Phase 12** (Settings UI scope).
- Whether `winsdk` async APIs need an asyncio bridge or can be `asyncio.run_in_executor`-wrapped. **Recommend executor wrap** — simpler, matches macOS `nowplaying-cli` subprocess pattern.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (from Phases 1-6)
- All 4 Phase 1 Protocols in `vibemix.platform.{audio,screen,midi,track}`.
- Phase 2's `vibemix.audio.AudioBuffer` + `Levels` + `MicBuffer` + `PassthroughBuffer` + `PlaybackQueue` + constants — cross-platform. Phase 7's Windows audio impl pushes int16 PCM to the same buffers.
- Phase 2's `SampleRateMismatchError` from `vibemix.audio.errors` — reused with Windows-specific message text.
- Phase 3's `MidiMacOS` + `ControllerState` + `_CC_MAP`/`_NOTE_MAP` — Phase 7 lifts most of the mido handling into `_midi_common.py` and the Windows backend reuses it.
- Phase 3's screen-capture pattern (gate on `state.audible`, 1Hz refresh, run_in_executor) — Phase 7 mirrors on Windows.
- Phase 3's `TrackMacOS` polling pattern (1Hz, graceful fallback) — Phase 7 mirrors via SMTC.

### Integration Points
- **Phase 11 (Tauri shell + Calibration Wizard)** — calibration step #1 detects platform and walks the user through OS-specific permissions (macOS Screen Recording permission; Windows WASAPI device selection). Phase 7 ships the underlying detection.
- **Phase 18 (Distribution)** — Windows MSI ships the Windows-only deps via PyInstaller `--onedir`. SignPath OSS approval signs the MSI.
- **Phase 20 (Day-Zero Operations)** — CI matrix `windows-latest` runs all Phase 7 windows_only marker tests. Fresh-machine rehearsal on real Windows 11 validates.

</code_context>

<specifics>
## Specific Ideas

- **PyAudioWPatch is the choice** because it's the maintained fork — pyaudio itself hasn't had WASAPI loopback support; pyaudiowpatch adds it. Verify it's still on PyPI in 2026 with Python 3.12 wheel.
- **`winsdk` over `winrt`** — `winrt` package on PyPI is deprecated; Microsoft moved to `winsdk` (auto-generated bindings).
- **Window-title hint list** for Windows screen capture is broader than macOS because Windows is where Serato/Traktor/rekordbox/VirtualDJ users live (djay Pro is macOS-leaning).
- **PASSTHROUGH_GAIN = 0.0** stays — Windows users also don't want djay→speakers passthrough since they're already hearing it via the system mix.
- **Device naming gotcha**: Windows' default playback device can change mid-session (e.g., user plugs in headphones). Phase 7 doesn't auto-re-bind — restarting vibemix is the fix. Document. Phase 9 / Phase 11 may revisit.
- **`pywin32` install gotcha**: needs post-install script `python Scripts/pywin32_postinstall.py -install` on some Windows systems. PyInstaller --onedir bundles fix this; uv sync on dev box doesn't (Kaan won't dev on Windows for v1 — that's Phase 20 rehearsal territory).

</specifics>

<deferred>
## Deferred Ideas

- Linux platform impls — out of v1 scope per PROJECT.md
- Hot-plug audio device re-binding when default playback device changes mid-session → post-v1
- Hot-plug MIDI re-enumeration every 2s → Phase 9
- Curated 10-controller MIDI library on Windows → Phase 9 (same impl as macOS)
- Windows ScreenCaptureKit equivalent (Graphics.Capture API) → only if mss perf is insufficient
- Windows-side push-to-mute global hotkey → Phase 12 (Settings UI)
- Real-Windows smoke test — Phase 20

</deferred>
