# Phase 1: Platform Protocol Firewall — POC Pattern Map

**Date:** 2026-05-11
**Mapper:** gsd-pattern-mapper
**Scope:** Define the four Protocol surfaces (`AudioBackend`, `ScreenBackend`, `MidiBackend`, `TrackInfoBackend`) under `src/vibemix/platform/`. No concrete impls this phase.

---

## How to Read This File

The POC files (`cohost.py`, `cohost_v2.py`, `cohost_v3.py`, `cohost_lk.py`) already contain the *natural shape* of every method these Protocols will declare. Each section below:

1. Lists the POC call sites that downstream phases will refactor against the Protocol.
2. Distills the natural method signature(s) that pop out when you look at the call site neutrally.
3. Suggests a `typing.Protocol` block ready for `src/vibemix/platform/<file>.py`.

**Do not copy the suggested code blocks verbatim into PLAN.md actions** — the planner will refine names, docstrings, and exact types. Treat these as load-bearing shape, not load-bearing prose.

---

## Per-Protocol Natural Shape

### 1. AudioBackend (consumed by Phase 2 macOS + Phase 7 Windows)

**POC call sites:**

| Reference | File | Lines | What it does |
|-----------|------|-------|--------------|
| Device lookup | `cohost.py` | 139–148 | `find_device(name_substring, kind)` — searches `sd.query_devices()` for first input/output device whose name contains a substring; raises `RuntimeError` if none. Identical copy in `cohost_v2.py:196–205` and `cohost_v3.py:219–228`. |
| Master capture (HTTP variant) | `cohost.py` | 391–437 | `start_input_stream()` — opens 48kHz stereo float32 InputStream on BlackHole, callback resamples → 16k mono, writes to `AudioBuffer` + `PassthroughBuffer` + `MicBuffer` (mic mix). |
| Master capture (LiveKit variant) | `cohost_v2.py` | 821–869 | `start_input_to_session()` — same as v1 but the callback *also* synthesizes `rtc.AudioFrame` and calls `session.push_audio(frame)`. AI talk gate (`levels.voice > AI_TALK_THRESHOLD`) skips push. |
| Master capture (v3 pull-model) | `cohost_v3.py` | 873–927 | `start_input_capture()` — adds dual buffers: `audio_buf` (8x gain for state features) + `clean_audio_buf` (natural level for Gemini snapshot WAV). No network push — invoke loop pulls. **Canonical baseline.** |
| Speaker passthrough | `cohost.py` | 479–505 | `start_passthrough_stream()` — 48kHz stereo OutputStream at `output_idx`, callback drains `PassthroughBuffer`. |
| AI voice playback | `cohost.py` | 508–528 | `start_playback_stream()` — 24kHz mono `RawOutputStream`, callback drains `PlaybackQueue`. |
| Mic capture inline | `cohost_v3.py` | 1870–1886 | mic stream opened inline in `main()`, not via a factory — single-deck float32 callback feeding `MicBuffer.push(mono)`. Graceful fallback wraps `find_device` in try/except. |

**Constants the callbacks depend on** (`cohost_v3.py:98–119`):
- `INPUT_SR_NATIVE = 48000`, `INPUT_SR_TARGET = 16000`, `OUTPUT_SR = 24000`
- `INPUT_CHUNK_FRAMES = 480` (v2/v3) vs `256` (v1)
- `OUTPUT_BLOCKSIZE = 256`, `VOICE_BLOCKSIZE = 1024`
- Gain tuning: `MUSIC_GAIN_TO_GEMINI`, `PASSTHROUGH_GAIN`, `MIC_GAIN`, `AI_TALK_THRESHOLD`, `MIC_HOLD_AFTER_AI_MS`

**Natural Protocol shape:**

```python
# src/vibemix/platform/audio.py
from __future__ import annotations
from typing import Callable, Literal, Protocol, runtime_checkable

Kind = Literal["input", "output"]
# Callback signature mirrors sounddevice exactly so impls can wire it without translation:
# (indata: np.ndarray, frames: int, time_info, status) -> None
AudioCallback = Callable[..., None]


class AudioStream(Protocol):
    """Handle to an opened audio stream. Closeable / inspectable."""
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...
    @property
    def latency_ms(self) -> float: ...


@runtime_checkable
class AudioBackend(Protocol):
    """OS-specific I/O for: master loopback capture, speaker passthrough,
    AI-voice playback, and optional system mic capture.

    Buffer ownership: the caller owns the np.ndarray / bytes objects;
    the backend MUST NOT retain references after the callback returns.
    """

    def find_device(self, name_substring: str, kind: Kind) -> int: ...

    def open_capture(
        self,
        device_index: int,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream: ...

    def open_passthrough_output(
        self,
        device_index: int,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream: ...

    def open_voice_output(
        self,
        device_index: int,
        *,
        sample_rate: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream: ...
```

**Why this shape:** All three POC factories (`start_input_stream`, `start_passthrough_stream`, `start_playback_stream`) share the same `(device_index, sample_rate, blocksize, callback) -> sd.Stream` skeleton — only the dtype/channel count differs. The Protocol collapses them into three methods that name their *role* (capture / passthrough / voice). The callback signature stays raw-sounddevice-shaped so existing POC callbacks port with zero massaging — Phase 2 just wraps `sd.InputStream` and Phase 7 wraps `pyaudiowpatch.PyAudio` open() behind the same surface.

---

### 2. ScreenBackend (consumed by Phase 3 macOS + Phase 7 Windows + Phase 8 ScreenCaptureKit migration)

**POC call sites:**

| Reference | File | Lines | What it does |
|-----------|------|-------|--------------|
| Window enumeration | `cohost_v2.py` / `cohost_v3.py` | 171–193 / 194–216 | `find_djay_window_bounds()` — calls `CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)`, filters by `kCGWindowOwnerName` / `kCGWindowName` containing `"djay"`, picks largest valid bounds. Returns `(x, y, w, h)` or `None`. |
| Full-screen grab + crop | `cohost_v3.py` | 947–965 | Inside `screen_capture_loop`: `sct.grab(monitor)` → `PIL.Image.frombytes("RGB", ..., "BGRX")` → if `find_djay_window_bounds()` non-None, crop to those bounds → `thumbnail((1280, 800))` → JPEG @ quality 82. |
| Loop driver | `cohost_v3.py` | 930–976 | `async def screen_capture_loop(screen_buf, state, stop_event, recorder)` — 1fps, skipped when `state.audible == False`, offloads `grab()` via `loop.run_in_executor(None, grab)`. |
| Feature-flag guard | `cohost_v3.py` | 47–62 | `_HAS_VISION` (mss + PIL) + `_HAS_QUARTZ` (CGWindowList) — set via try/except ImportError at module top. |

**Natural Protocol shape:**

```python
# src/vibemix/platform/screen.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class WindowBounds:
    """Logical screen-space rect of a target app window."""
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class CapturedFrame:
    """Single captured screen frame as JPEG bytes + final pixel dimensions."""
    jpeg: bytes
    width: int
    height: int


@runtime_checkable
class ScreenBackend(Protocol):
    """OS-specific screen capture targeted at a single app window (djay Pro).

    The backend MUST gracefully report unavailable (returning None / raising
    a recognised exception) when its system APIs are missing — the caller
    handles degraded mode (full-screen fallback or no vision at all).
    """

    def is_available(self) -> bool: ...

    def find_window_bounds(self, app_name_substring: str) -> WindowBounds | None: ...

    def capture(
        self,
        bounds: WindowBounds | None,
        *,
        max_width: int = 1280,
        max_height: int = 800,
        jpeg_quality: int = 82,
    ) -> CapturedFrame: ...
```

**Why this shape:** The POC mixes two responsibilities in `screen_capture_loop` — *finding the window* and *capturing pixels*. Splitting them at the Protocol level lets Phase 7 (Windows `EnumWindows` + GDI) and Phase 8 (macOS ScreenCaptureKit, which has its own window picker model) implement each half independently. `is_available()` replaces the `_HAS_VISION` / `_HAS_QUARTZ` module-level globals — the loop driver checks the backend instead of bare flags.

---

### 3. MidiBackend (consumed by Phase 9 — 10-controller library + generic fallback + hot-plug)

**POC call sites:**

| Reference | File | Lines | What it does |
|-----------|------|-------|--------------|
| Port enumeration + open | `cohost_v3.py` | 704–730 | `midi_listener_thread()` — daemon thread loops: `mido.get_input_names()` → find port matching `"DDJ-FLX4"` → `mido.open_input(match)` → poll messages → `controller_state.handle_msg(msg)`. 2s sleep when no match found = **hot-plug rescan interval**. |
| Connection state writeback | `cohost_v3.py` | 611–620 | `ControllerState.mark_connected(port_name)` + `is_connected()`. |
| Message decode (DDJ-FLX4 maps) | `cohost_v3.py` | 556–572 | `_CC_MAP` (7 entries: vol, eq_low/mid/hi, tempo, filter, xfader) + `_NOTE_MAP` (6 entries: play, cue, sync, jog_touch, loop_in, loop_out). **These are controller-specific data, not Protocol surface.** |
| Decoded state read | `cohost_v3.py` | 688–702 | `ControllerState.deck_snapshot()` → `dict` shape `{'A': {...}, 'B': {...}, 'xfader': int, 'connected': bool}`. `moves_since(t)` → `list[(seconds_ago, label)]`. |
| Magnitude-aware emission | `cohost_v3.py` | 595–605 | Inside `handle_msg`: classifies move size as `"small"` / `"medium"` / `"big"` based on absolute CC delta. Only records a move if it crosses a label boundary or magnitude threshold. |
| Consumer wiring | `cohost_v3.py` | 1625, 1656 | `controller_state.deck_snapshot()` and `.moves_since(now - 12.0)` are called from `state_refresh_loop`. |

**Natural Protocol shape:**

```python
# src/vibemix/platform/midi.py
from __future__ import annotations
from typing import Protocol, runtime_checkable


@runtime_checkable
class MidiMessage(Protocol):
    """Structural minimum of a MIDI message (mido-compatible)."""
    type: str           # 'control_change' | 'note_on' | 'note_off'
    channel: int
    # 'control_change' has .control + .value; 'note_*' has .note + .velocity.
    # Backends MUST emit messages with mido's attribute names so existing
    # POC decoders port wholesale.


@runtime_checkable
class MidiPort(Protocol):
    """Open MIDI input port; iterable for messages."""
    name: str
    def poll(self) -> MidiMessage | None: ...
    def close(self) -> None: ...


@runtime_checkable
class MidiBackend(Protocol):
    """OS-specific MIDI input enumeration + port open.

    Hot-plug: the caller re-invokes list_input_ports() on a ~2s cadence
    (POC pattern). The backend does NOT push events — it exposes a port
    that the caller polls.
    """

    def list_input_ports(self) -> list[str]: ...

    def open_input(self, port_name: str) -> MidiPort: ...
```

**Why this shape:** The POC's `midi_listener_thread` already separates "find a port matching a hint" from "decode the messages flowing through it". `ControllerState` (which holds CC/Note maps, deck weights, recent-moves ring) is **not** part of the Protocol — it's a sensor/state-layer concern that lives in `src/vibemix/sensing/` (Phase 3) and reads from whatever `MidiBackend.open_input()` returns. This split also matches Phase 9's controller-library design: the backend stays platform-only; per-controller CC/Note maps become first-class data structures alongside it.

**Anti-pattern to avoid in the Protocol:** Do not put `deck_snapshot()` / `moves_since()` / DDJ-specific maps on `MidiBackend`. Those belong to a *controller profile* abstraction (Phase 9), not the OS firewall.

---

### 4. TrackInfoBackend (consumed by Phase 3 macOS + Phase 7 Windows SMTC)

**POC call sites:**

| Reference | File | Lines | What it does |
|-----------|------|-------|--------------|
| Subprocess polling | `cohost_v2.py` / `cohost_v3.py` | 466–489 / 518–541 | `TrackInfo.poll_once()` — `subprocess.check_output([nowplaying-cli, "get", "title"], timeout=1.5)`, splits stdout lines, updates `self.title` if changed. CLI resolved via `shutil.which("nowplaying-cli")` with `/opt/homebrew/bin/nowplaying-cli` fallback. |
| Async driver | `cohost_v3.py` | 544–551 | `async def track_poll_loop(track_info, stop_event)` — 1s cadence, blocking poll offloaded to executor. |
| Read API | `cohost_v3.py` | 535–541 | `TrackInfo.snapshot()` → `{"title": str, "prev_title": str, "title_changed_at": float}`. |
| Confidence cross-reference | `cohost_v3.py` | 1112–1133 | `derive_audible_track(track_title, audible_deck, deck_confidence, audio_audible)` — combines nowplaying-cli's title with controller-derived audible-deck weights to produce `(title, confidence)`. **This is sensing-layer logic, NOT Protocol surface.** |

**Natural Protocol shape:**

```python
# src/vibemix/platform/track.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class NowPlayingSnapshot:
    """Single read of the OS's "what's playing" surface.

    All fields are best-effort: backends MUST set unknown fields to None
    rather than empty strings, so the caller can distinguish "no track"
    from "track with no title".
    """
    title: str | None
    artist: str | None
    album: str | None
    duration_sec: float | None
    position_sec: float | None


@runtime_checkable
class TrackInfoBackend(Protocol):
    """OS-specific 'now playing' source.

    macOS impl wraps `nowplaying-cli` (MediaRemote framework).
    Windows impl wraps SystemMediaTransportControls via pywin32 / winrt.

    poll() is synchronous and blocking — the caller offloads to an
    executor (POC pattern, cohost_v3.py:548).
    """

    def is_available(self) -> bool: ...

    def poll(self) -> NowPlayingSnapshot | None: ...
```

**Why this shape:** The POC `TrackInfo` class conflates three responsibilities: (a) the subprocess call to nowplaying-cli, (b) the rolling state (title vs prev_title vs changed_at), (c) the lock for read API. Only (a) is OS-specific — (b) and (c) live in the sensing layer. The Protocol exposes only the *raw read*; the sensing-layer wrapper (Phase 3) keeps the title-change-tracking + prev_title shimmer. `is_available()` lets the sensing layer skip the polling task entirely when `nowplaying-cli` isn't installed (current POC silently fails on `FileNotFoundError`).

**Anti-pattern to avoid:** Do not put `derive_audible_track()` on the Protocol. That function correlates track title with MIDI deck weights — it's pure sensing-layer logic that doesn't depend on the OS.

---

## Naming & Convention Honor List (from `.planning/codebase/CONVENTIONS.md`)

| Decision | Phase 1 application |
|----------|---------------------|
| `snake_case.py` filenames | `audio.py`, `screen.py`, `midi.py`, `track.py` |
| `PascalCase` class names — no `I*` or `*Interface` suffix | `AudioBackend` (not `IAudioBackend`), `ScreenBackend`, `MidiBackend`, `TrackInfoBackend` |
| `from __future__ import annotations` at top of every module | Apply to all four Protocol files for PEP 604 union syntax (`str \| None`) |
| Type hints on every public method | Protocols are pure typing artifacts — every method MUST be fully annotated |
| Module-level constants in `UPPER_SNAKE_CASE` | No constants this phase (concrete impls own their tuning). The four Protocol modules are typing-only. |
| `@dataclass` for value carriers (only in `cohost_v2.py` for `MusicState` / `Event`) | Use `@dataclass(frozen=True)` for `WindowBounds`, `CapturedFrame`, `NowPlayingSnapshot` — immutable read-models |
| Leading `_` for *private* modules | Concrete impls Phase 2+ will be `_audio_macos.py`, `_screen_macos.py`, etc. Phase 1 ships zero `_*.py` modules |
| Single-line docstrings or short prose paragraphs — no Google/NumPy/Sphinx structure | Apply uniformly across all Protocol method docstrings |
| `typing.Protocol` + `@runtime_checkable` (per CONTEXT decision) | Decorate every Protocol class; do NOT use `abc.ABC` / `@abstractmethod` |

---

## Anti-Patterns to NOT Carry Forward into the Protocol Surface

The POC has these patterns at the platform boundary. **None of them belong inside Protocol definitions.**

1. **Module-level `_HAS_VISION` / `_HAS_WS` / `_HAS_QUARTZ` flags** (`cohost.py:43-54`, `cohost_v3.py:47-68`)
   - Replace with `Backend.is_available() -> bool` on each Protocol. Callers check the backend, not module globals.

2. **`subprocess` calls hard-coded to `/opt/homebrew/bin/nowplaying-cli`** (`cohost_v3.py:518`)
   - The Protocol declares `poll()` — concrete impl chooses how (subprocess on macOS, pywin32 on Windows).

3. **Conflated I/O + state + locking inside one class** (`TrackInfo`, `ControllerState`)
   - The Protocol is I/O-only. State (prev_title, recent_moves, deck_snapshot) lives in the sensing layer (Phase 3) on top of the Protocol.

4. **`RuntimeError(f"No {kind} device matching {name_substring!r}")`** (`cohost.py:148`)
   - Keep behaviour but the Protocol can declare a typed exception (`DeviceNotFoundError`) in a sibling errors module. Phase 1 may leave this implicit and document it; concrete impls Phase 2 finalise.

5. **`from Quartz import CGWindowListCopyWindowInfo, ...` at module top** (`cohost_v3.py:54-62`)
   - The Protocol module imports zero OS-specific symbols. All `Quartz`, `mss`, `mido`, `sounddevice` imports stay in concrete impls under `_*_macos.py` / `_*_windows.py`.

6. **`mido.Message` attribute access (`msg.type`, `msg.channel`, `msg.control`, `msg.value`)** leaking into consumer code
   - The `MidiMessage` Protocol pins the attribute contract structurally. `mido.Message` happens to satisfy it on macOS; Windows impl can return any object that exposes the same attrs.

---

## Recommended File Map for Phase 1

```text
.
├── LICENSE                                # Apache 2.0 (full text)
├── pyproject.toml                         # [project] + [build-system] + [tool.ruff] + [tool.hatch.*]
├── uv.lock                                # generated by `uv lock`
├── .gitignore                             # python + macos + windows + .env + recordings/
├── README.md                              # minimal; expanded in Phase 19
├── .planning/
│   └── signpath-application.md            # prefilled OSS checklist (Kaan files)
└── src/
    └── vibemix/
        ├── __init__.py                    # SPDX header, __version__ = "0.1.0-dev0"
        ├── py.typed                       # PEP 561 marker (empty file)
        └── platform/
            ├── __init__.py                # re-exports the four Protocols + value dataclasses
            ├── audio.py                   # AudioBackend, AudioStream, AudioCallback, Kind
            ├── screen.py                  # ScreenBackend, WindowBounds, CapturedFrame
            ├── midi.py                    # MidiBackend, MidiPort, MidiMessage
            └── track.py                   # TrackInfoBackend, NowPlayingSnapshot
```

**`src/vibemix/platform/__init__.py` re-export pattern:**

```python
# src/vibemix/platform/__init__.py
"""OS abstraction firewall. All concrete OS-specific code in vibemix
lives behind one of these four Protocols. Downstream modules import
from vibemix.platform — never from sounddevice, mss, Quartz, mido, or
subprocess directly."""

from vibemix.platform.audio import AudioBackend, AudioStream, AudioCallback, Kind
from vibemix.platform.screen import ScreenBackend, WindowBounds, CapturedFrame
from vibemix.platform.midi import MidiBackend, MidiPort, MidiMessage
from vibemix.platform.track import TrackInfoBackend, NowPlayingSnapshot

__all__ = [
    "AudioBackend", "AudioStream", "AudioCallback", "Kind",
    "ScreenBackend", "WindowBounds", "CapturedFrame",
    "MidiBackend", "MidiPort", "MidiMessage",
    "TrackInfoBackend", "NowPlayingSnapshot",
]
```

**`src/vibemix/__init__.py`:**

```python
# SPDX-License-Identifier: Apache-2.0
"""vibemix — AI DJ co-host. Free, open-source, cross-platform."""

__version__ = "0.1.0-dev0"
```

---

## Shared Patterns Across All Four Protocols

### `is_available()` instead of module globals
Every Protocol (where degradation is possible) exposes a synchronous `is_available() -> bool`. Phase 2+ implementations replace the POC's module-level `_HAS_*` flags. Callers branch on `backend.is_available()`, never on imported module state.

### Frozen dataclass value carriers
Read-model returns (`WindowBounds`, `CapturedFrame`, `NowPlayingSnapshot`) are `@dataclass(frozen=True)` — Phase 1 ships them in the same file as the Protocol. They mirror the `@dataclass class MusicState` / `class Event` style established in `cohost_v3.py:983, 1137`.

### Structural Protocol over `abc.ABC`
Per CONTEXT.md decision: `typing.Protocol` + `@runtime_checkable`. `isinstance(backend, AudioBackend)` works at runtime for tests. No `@abstractmethod` decorators anywhere.

### No I/O during import
Protocol modules MUST be safe to import on any platform without side effects. The POC's pattern of try/except ImportError at the module top stays in concrete `_*_macos.py` / `_*_windows.py` files; Protocol files import only `typing` + `dataclasses` (+ `__future__`).

### Type the callback at the boundary, not the body
`AudioCallback = Callable[..., None]` keeps the sounddevice-shaped 4-tuple signature without re-declaring it — Phase 2 macOS impl passes through unchanged; Phase 7 Windows impl wraps PyAudio's `(in_data, frame_count, time_info, status)` to the same shape.

---

## Phase 1 Validation Checklist (for the planner)

| Check | How to verify |
|-------|---------------|
| All four Protocol files import zero OS-specific symbols | `python -c "import vibemix.platform"` must succeed on a fresh venv with no extras |
| `runtime_checkable` works | `isinstance(object(), AudioBackend) == False`; a stub class satisfying the methods returns True |
| `py.typed` present | File exists at `src/vibemix/py.typed`, exactly empty |
| SPDX header in `__init__.py` | First line `# SPDX-License-Identifier: Apache-2.0` |
| `pyproject.toml` requires Python >=3.12,<3.13 | Per CONTEXT specifics |
| `.planning/signpath-application.md` has all six fields filled | repo URL, maintainer name/email, build system (PyInstaller→Inno Setup MSI), description, OSS license confirmation, expected artifacts (`vibemix-setup-{version}.msi`) |
| No POC files touched | `git diff --name-only` lists no `cohost*.py` changes |

---

## Coverage Summary

| Protocol | POC analogs found | Source files |
|----------|-------------------|--------------|
| AudioBackend | 7 call sites (find_device, 3 stream factories x 2 variants, mic inline) | cohost.py, cohost_v2.py, cohost_v3.py |
| ScreenBackend | 4 call sites (window bounds, grab+crop, loop driver, feature flag) | cohost_v2.py, cohost_v3.py |
| MidiBackend | 6 call sites (listener thread, mark/is_connected, decode, snapshot, moves_since, consumer) | cohost_v3.py (+ identical in cohost_v2.py / cohost_lk.py) |
| TrackInfoBackend | 4 call sites (poll_once, async driver, snapshot, derive_audible_track) | cohost_v2.py, cohost_v3.py |

**Files with no analog in the POC:** none — every Protocol surface this phase introduces has at least one concrete call site to anchor against.

---

*Pattern mapping: 2026-05-11*
