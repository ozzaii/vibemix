# Architecture Research

**Domain:** Cross-platform desktop AI co-host (local audio/MIDI/screen capture + LiveKit Agents + Gemini Flash multimodal + Gemini TTS streaming)
**Researched:** 2026-05-11
**Confidence:** MEDIUM-HIGH (LiveKit Agents internals: HIGH; cross-platform audio: HIGH; Gemini TTS streaming plugin: HIGH; LiveKit standalone-no-room option: MEDIUM — documented but underdocumented edge case; proxy security model: MEDIUM — multiple viable patterns, recommendation reasoned not benchmarked)

## Standard Architecture

### System Overview — vibemix three-process layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  PROCESS 1: vibemix-shell  (Tauri Rust binary — UI host)                  │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │  Webview UI (React + Vite, bundled into Tauri)                    │   │
│  │  • Calibration wizard  • Mode/voice/genre pickers                 │   │
│  │  • Live status (RMS meters, current event, mascot canvas)         │   │
│  │  • Session list + recording browser                               │   │
│  └────────┬──────────────────────────────────────────────────────────┘   │
│           │  Tauri IPC commands (start/stop session, set config)         │
│           │  + WS @127.0.0.1:8765 (high-rate telemetry: RMS, events)     │
│           ▼                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │  Rust shell: spawns + supervises Python sidecar; owns tray icon, │   │
│  │  window picker (native), auto-update, signed installer.          │   │
│  └────────┬──────────────────────────────────────────────────────────┘   │
└───────────┼──────────────────────────────────────────────────────────────┘
            │ spawn() — PyInstaller --onedir bundle, sidecar binary
            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PROCESS 2: vibemix-core  (Python — single sidecar, single process)       │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  HOST PROCESS — owns asyncio loop, RTC connection, all state       │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  Capture Layer  (cross-platform abstraction)                 │  │  │
│  │  │  • audio.macos.LoopbackInput  (sounddevice + BlackHole)      │  │  │
│  │  │  • audio.windows.LoopbackInput (PyAudioWPatch WASAPI loop)   │  │  │
│  │  │  • audio.output.PlaybackSink   (sounddevice both OSes)       │  │  │
│  │  │  • midi.Controller             (mido — works on both)        │  │  │
│  │  │  • screen.macos.WindowGrab     (mss + Quartz CGWindowList)   │  │  │
│  │  │  • screen.windows.WindowGrab   (mss + pywin32 EnumWindows)   │  │  │
│  │  │  • track.macos.NowPlaying      (nowplaying-cli wrapper)      │  │  │
│  │  │  • track.windows.NowPlaying    (GSMTC via winsdk-py)         │  │  │
│  │  └────┬─────────────────────────────────────────────────────────┘  │  │
│  │       │                                                            │  │
│  │       ▼                                                            │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  Sensing + State Layer  (port of existing v2 code)           │  │  │
│  │  │  • AudioBuffer    • ScreenBuffer    • ControllerState        │  │  │
│  │  │  • TrackInfo      • Levels          • MusicState (10Hz)      │  │  │
│  │  │  • EventDetector (track/phase/layer/mix/heartbeat/spoke)     │  │  │
│  │  └────┬─────────────────────────────────────────────────────────┘  │  │
│  │       │ Event objects (typed, evidence-bundled)                    │  │
│  │       ▼                                                            │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  Agent Layer  (LiveKit Agents 1.5+)                          │  │  │
│  │  │  • DJCoHostAgent(Agent)                                      │  │  │
│  │  │    - overrides llm_node() — calls Gemini 3 Flash multimodal  │  │  │
│  │  │      with audio bytes + screen JPEG + history                │  │  │
│  │  │    - keeps default tts_node() — google.TTS(model_name=       │  │  │
│  │  │      "gemini-2.5-flash-tts", voice_name=...)                 │  │  │
│  │  │    - STT path is unused (no STT plugin in AgentSession)      │  │  │
│  │  │  • AgentSession orchestrates llm_node → tts_node streaming   │  │  │
│  │  │  • EventDetector triggers via session.generate_reply(        │  │  │
│  │  │      instructions=AICoach.build_prompt(event))               │  │  │
│  │  └────┬─────────────────────────────────────────────────────────┘  │  │
│  │       │ AudioFrame stream (24kHz PCM mono)                          │  │
│  │       ▼                                                            │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  Room I/O  (LiveKit Python SDK)                              │  │  │
│  │  │  • Local in-process LiveKit server (livekit-server --dev,    │  │  │
│  │  │    bundled binary, listens on 127.0.0.1:7880)                │  │  │
│  │  │    OR — for v1 simplicity — direct AudioSource→PlaybackSink  │  │  │
│  │  │    bypass with no SFU (see "Process Model" below)            │  │  │
│  │  │  • PlaybackSink drains AudioStream into sounddevice output   │  │  │
│  │  └────┬─────────────────────────────────────────────────────────┘  │  │
│  │       │                                                            │  │
│  │       ▼                                                            │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  Output Layer                                                │  │  │
│  │  │  • PlaybackQueue → sounddevice OutputStream (24kHz PCM)      │  │  │
│  │  │  • VoiceRecorder → recordings/<session>/{input,voice}.wav    │  │  │
│  │  │  • Telemetry WS @127.0.0.1:8765 → Tauri webview              │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
            │ HTTPS (Authorization: Bearer <signed-client-token>)
            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  PROCESS 3 (REMOTE):  bravoh-api / vibemix-proxy                          │
│  • Issues signed short-lived JWT to each installed client                 │
│  • Proxies POST /v1/gemini/generate-content (Flash multimodal)            │
│  • Proxies POST /v1/gemini/tts (streaming PCM, SSE/chunked)               │
│  • Rate-limits per client_id (Redis token bucket)                         │
│  • Owns the real GEMINI_API_KEY (never leaves server)                     │
│  • Optional: anonymous usage telemetry (sessions/day, controller types)   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `vibemix-shell` (Tauri) | UI host, installer, auto-update, native window picker, signed binary | Rust + Vite-bundled React webview |
| `vibemix-core` (Python sidecar) | All capture, sensing, state, AI orchestration, audio output | Python 3.12, PyInstaller `--onedir`, asyncio + livekit-agents |
| `audio.<os>.LoopbackInput` | Capture system master output as 48kHz stereo PCM | macOS: sounddevice + BlackHole; Windows: PyAudioWPatch WASAPI loopback |
| `screen.<os>.WindowGrab` | Crop named app window to JPEG @1fps | macOS: mss + Quartz `CGWindowListCopyWindowInfo`; Windows: mss + pywin32 `EnumWindows`/`BitBlt` |
| `midi.Controller` | MIDI ingest with per-controller CC/note map registry | `mido` + `python-rtmidi` (cross-platform identical) |
| `track.<os>.NowPlaying` | Current track title polling | macOS: `nowplaying-cli` subprocess; Windows: `winsdk` GSMTC bindings |
| `MusicState` | Single source of truth for music + controller + screen state (10Hz writer) | Port from `cohost_v2.py:965` dataclass — unchanged contract |
| `EventDetector` | Diff MusicState → typed Events (TRACK_CHANGE/PHASE/LAYER_ARRIVAL/MIX_MOVE/HEARTBEAT/KAAN_SPOKE) | Port from `cohost_v2.py:1125` — unchanged |
| `AICoach` | Build event-specific prompt strings with audio evidence | Port from `cohost_v2.py:1237` |
| `DJCoHostAgent` | LiveKit `Agent` subclass; `llm_node` override calls Gemini 3 Flash multimodal | New — replaces `cohost_v2.py`'s `RealtimeModel` usage |
| `GeminiFlashLLM` | Wraps `client.models.generate_content_stream()` with multimodal Parts (audio bytes + JPEG inlineData + text) | New — uses `google-genai` directly, not livekit-plugins-google's LLM class |
| `google.TTS` plugin | Streaming Gemini TTS — `gemini-2.5-flash-tts`, voice_name, PCM @24kHz | From `livekit-plugins-google ≥1.3.7` (PR #4189 merged 2025-12-08) |
| `vibemix-proxy` (Bravoh-side) | Issues JWTs, proxies + rate-limits Gemini calls, hides real API key | FastAPI on `api.altidus.world` (Bravoh's existing infra), Redis for rate limit |

## Recommended Project Structure

```
vibemix/                                  # GitHub: bravoh/vibemix
├── pyproject.toml                       # Python deps (uv-style)
├── README.md
├── LICENSE                              # MIT or Apache-2.0
├── .github/workflows/
│   ├── build-macos.yml                  # signed + notarized DMG
│   └── build-windows.yml                # signed .exe installer
│
├── tauri/                               # Rust shell (Tauri 2.x)
│   ├── src-tauri/
│   │   ├── Cargo.toml
│   │   ├── tauri.conf.json              # externalBin: vibemix-core sidecar
│   │   ├── capabilities/default.json    # allow shell:spawn for sidecar
│   │   ├── binaries/
│   │   │   ├── vibemix-core-aarch64-apple-darwin
│   │   │   ├── vibemix-core-x86_64-apple-darwin
│   │   │   └── vibemix-core-x86_64-pc-windows-msvc.exe
│   │   └── src/
│   │       ├── main.rs                  # spawn sidecar, IPC handlers
│   │       ├── sidecar.rs               # lifecycle, logs, restart
│   │       └── windows.rs               # native window-picker bridge
│   └── ui/                              # Vite + React
│       ├── src/
│       │   ├── App.tsx
│       │   ├── routes/
│       │   │   ├── Calibration.tsx      # 5-step wizard
│       │   │   ├── Session.tsx          # live mascot + meters
│       │   │   └── Settings.tsx
│       │   ├── stores/                  # Zustand
│       │   └── ipc/                     # Tauri invoke + WS client
│       └── package.json
│
├── src/vibemix/                          # Python package — single sidecar
│   ├── __init__.py
│   ├── __main__.py                      # `python -m vibemix` entry
│   ├── app.py                           # main() — asyncio.run wiring
│   │
│   ├── platform/                        # OS abstraction surface
│   │   ├── __init__.py                  # `from vibemix.platform import audio_input, screen, nowplaying`
│   │   ├── detect.py                    # is_macos(), is_windows()
│   │   ├── _audio_macos.py              # sounddevice + BlackHole detection
│   │   ├── _audio_windows.py            # PyAudioWPatch WASAPI loopback
│   │   ├── _screen_macos.py             # mss + Quartz
│   │   ├── _screen_windows.py           # mss + pywin32
│   │   ├── _nowplaying_macos.py         # nowplaying-cli
│   │   └── _nowplaying_windows.py       # winsdk GSMTC
│   │
│   ├── audio/                           # OS-agnostic audio classes
│   │   ├── buffer.py                    # AudioBuffer (16k mono ring)
│   │   ├── mic.py                       # MicBuffer (gated)
│   │   ├── levels.py                    # Levels (EMA RMS)
│   │   ├── playback.py                  # PlaybackQueue + sounddevice OutputStream
│   │   └── features.py                  # snapshot_features (FFT, bands, BPM)
│   │
│   ├── midi/                            # MIDI ingest + controller library
│   │   ├── controller.py                # ControllerState (generic state)
│   │   ├── library/                     # one file per supported controller
│   │   │   ├── __init__.py              # registry: model_name → mapping
│   │   │   ├── ddj_flx4.py              # CC_MAP, NOTE_MAP, deck assignment
│   │   │   ├── ddj_400.py
│   │   │   ├── ddj_flx6.py
│   │   │   ├── ddj_flx10.py
│   │   │   ├── ddj_1000.py
│   │   │   ├── ddj_sx3.py
│   │   │   ├── xdj_rx3.py
│   │   │   ├── numark_party_mix_live.py
│   │   │   ├── hercules_inpulse_300.py
│   │   │   ├── hercules_inpulse_500.py
│   │   │   └── generic.py               # fallback (positional, no semantics)
│   │   └── auto_detect.py               # mido.get_input_names() → match library
│   │
│   ├── sense/                           # sensing layer
│   │   ├── screen.py                    # ScreenBuffer (cross-platform via platform/)
│   │   └── track.py                     # TrackInfo (cross-platform via platform/)
│   │
│   ├── state/                           # unified state + events
│   │   ├── music_state.py               # MusicState dataclass + state_refresh_loop
│   │   ├── events.py                    # Event types + EventDetector
│   │   └── coach.py                     # AICoach (prompt builder, evidence_line)
│   │
│   ├── agent/                           # LiveKit Agents integration
│   │   ├── dj_agent.py                  # DJCoHostAgent(Agent) + llm_node override
│   │   ├── gemini_flash.py              # GeminiFlashLLM — google-genai wrapper
│   │   ├── session.py                   # AgentSession setup + lifecycle
│   │   └── prompts/
│   │       ├── system.py                # SYSTEM_INSTRUCTION variants
│   │       ├── beginner_hype.py
│   │       ├── beginner_coach.py
│   │       ├── intermediate_hype.py
│   │       ├── intermediate_coach.py
│   │       ├── pro_hype.py
│   │       └── pro_coach.py
│   │
│   ├── proxy/                           # Bravoh-proxy client
│   │   ├── client.py                    # signed-token fetch, request signing
│   │   └── token.py                     # JWT decode, refresh logic
│   │
│   ├── ui_bus/                          # WS bridge to Tauri webview
│   │   ├── server.py                    # WS server on 127.0.0.1:8765
│   │   └── messages.py                  # typed message schemas
│   │
│   ├── recording/                       # session recording
│   │   ├── recorder.py                  # VoiceRecorder (input.wav, voice.wav, events.jsonl)
│   │   └── session_dir.py               # session dir naming + cleanup
│   │
│   ├── calibration/                     # first-run wizard backend
│   │   ├── audio_devices.py             # enumerate + score candidates
│   │   ├── permissions_macos.py         # check Screen Recording + Microphone TCC
│   │   ├── permissions_windows.py       # mic permission check
│   │   └── controller_probe.py          # listen for MIDI input, match library
│   │
│   └── config/
│       ├── schema.py                    # pydantic config types
│       └── store.py                     # ~/Library/Application Support/vibemix/ or %APPDATA%
│
├── tests/                               # pytest
│   ├── unit/
│   │   ├── test_event_detector.py
│   │   ├── test_music_state.py
│   │   ├── test_midi_mappings.py
│   │   └── test_audio_features.py
│   ├── integration/
│   │   ├── test_agent_pipeline.py       # mock Gemini, real AgentSession
│   │   └── test_calibration.py
│   └── fixtures/
│       ├── audio_samples/               # WAVs for replay tests
│       └── midi_traces/                 # recorded MIDI sequences
│
└── scripts/
    ├── build_sidecar.sh                 # PyInstaller --onedir per platform
    ├── package_macos.sh                 # codesign + notarize DMG
    └── package_windows.ps1              # signtool + Inno Setup
```

### Structure Rationale

- **`platform/` is the OS-abstraction firewall.** Anything that touches Quartz, ScreenCaptureKit, Win32, WASAPI, PyAudioWPatch, nowplaying-cli, or winsdk GSMTC lives here and is imported via `from vibemix.platform import audio_input, screen, nowplaying`. The rest of the code never imports OS-specific symbols. Each platform module exports the same protocol (e.g. `AudioInput.start(callback) -> Stream`, `AudioInput.list_loopback_devices() -> list[Device]`).
- **`midi/library/` is data, not logic.** Each controller mapping is a Python file with two dicts (`CC_MAP`, `NOTE_MAP`) and a `DECK_ASSIGNMENT` rule. Adding the 11th controller is one new file + one line in the registry. This is the dominant maintenance surface — keep it grep-able.
- **`state/` is unchanged from `cohost_v2.py`.** MusicState + EventDetector + AICoach have proven semantics. They're ported verbatim into a subpackage. This is the load-bearing intellectual property.
- **`agent/` is the only place that knows about LiveKit Agents.** `dj_agent.py` subclasses `livekit.agents.Agent` and overrides `llm_node`. `gemini_flash.py` is plain `google-genai`. The rest of the code emits Event objects and never directly touches the Agent/Session.
- **`proxy/` isolates the auth surface.** Swapping from "fetch ephemeral key from Bravoh" to "send request to Bravoh proxy and stream response back" is a single-file change.
- **`ui_bus/` keeps the UI integration point trivial.** Tauri webview consumes JSON over WS — same pattern as `mascot.html` does today. No protocol negotiation.
- **`tauri/` is its own world.** Rust + TypeScript developers don't need to touch Python. Python developers don't need to touch Rust. Communication is one IPC contract documented in `ui_bus/messages.py` and mirrored in `tauri/ui/src/ipc/`.

## Architectural Patterns

### Pattern 1: LiveKit `Agent.llm_node` override for non-realtime multimodal LLM

**What:** Subclass `livekit.agents.Agent` and override `llm_node()`. The override yields `str` chunks (or `llm.ChatChunk` objects) which AgentSession pipes into `tts_node()` automatically. This is the canonical way to plug a non-realtime LLM into the streaming pipeline — confirmed by the LiveKit recipe "LLM Output Replacement" and by the `Agent` class signature in `livekit/agents/voice/agent.py`.

**When to use:** When the LLM call is not a chat-completion-shaped request — e.g. a multimodal request with audio bytes + image + custom evidence framing. Gemini 3 Flash via `google-genai` doesn't fit the OpenAI-style chat contract that the default `google.LLM` plugin assumes.

**Trade-offs:**
- Pro: Full control over request construction (we feed Gemini exactly the audio_evidence + screen JPEG + history + task that v1/v2 prompting proved works).
- Pro: AgentSession still owns turn management, interruption (mic gate), TTS streaming, and AudioFrame plumbing — we don't reinvent any of it.
- Con: `llm_node` is called by AgentSession when a turn is generated. Since we use `generate_reply(instructions=...)` (event-gated, no STT), we feed the instructions through chat_ctx. The override must read `chat_ctx` for the prompt the EventDetector built, then assemble the multimodal request out-of-band by reading directly from `MusicState`/`AudioBuffer`/`ScreenBuffer`.

**Example:**
```python
# vibemix/agent/dj_agent.py
from livekit.agents import Agent, llm
from livekit.agents.voice import ModelSettings
from typing import AsyncIterable
from vibemix.agent.gemini_flash import call_gemini_flash_multimodal
from vibemix.state.music_state import MusicState

class DJCoHostAgent(Agent):
    def __init__(self, *, music_state: MusicState, audio_buf, screen_buf, **kw):
        super().__init__(instructions=SYSTEM_INSTRUCTION, **kw)
        self._music = music_state
        self._audio = audio_buf
        self._screen = screen_buf

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[llm.Tool],
        model_settings: ModelSettings,
    ) -> AsyncIterable[str]:
        # The most recent user message is the EventDetector-built prompt
        prompt = chat_ctx.items[-1].content[0]  # type: ignore[index]

        # Snapshot grounding context AT THE MOMENT THE EVENT FIRED.
        # MusicState is the single source of truth; AudioBuffer snapshot
        # gives the actual PCM Gemini will hear; ScreenBuffer gives the JPEG.
        audio_bytes = self._audio.snapshot_bytes(seconds=7)
        screen_jpeg = self._screen.latest_jpeg()
        evidence = self._music.evidence_line()

        # Stream tokens from Gemini Flash multimodal.
        async for chunk in call_gemini_flash_multimodal(
            audio_pcm=audio_bytes,
            screen_jpeg=screen_jpeg,
            evidence=evidence,
            prompt=prompt,
            history=chat_ctx.items[:-1],
        ):
            yield chunk  # AgentSession.tts_node() consumes these and synthesizes via google.TTS

# vibemix/agent/session.py
from livekit.agents import AgentSession
from livekit.plugins import google

session = AgentSession(
    # NO STT — we never transcribe user speech in v1
    # NO VAD — we have our own EventDetector
    llm=None,                            # llm_node override supplies generation
    tts=google.TTS(
        model_name="gemini-2.5-flash-tts",
        voice_name="Kore",               # configurable male/female
        prompt="Speak conversationally, with the energy of a DJ friend",
        sample_rate=24000,
    ),
)

agent = DJCoHostAgent(
    music_state=music_state,
    audio_buf=audio_buf,
    screen_buf=screen_buf,
)

await session.start(room=room, agent=agent, ...)

# EventDetector fires → trigger fires → we call:
await session.generate_reply(instructions=AICoach.build_prompt(event))
# Internally: AgentSession constructs chat_ctx with `instructions` as user message,
# calls agent.llm_node(chat_ctx, ...), pipes yielded str into tts_node, which
# emits AudioFrames into the room's playback track.
```

**Reference confirmation:**
- LiveKit recipe "LLM Output Replacement" (docs.livekit.io/reference/recipes/replacing_llm_output) explicitly documents overriding `llm_node` to intercept/replace streaming LLM output.
- The `Agent.llm_node()` signature `AsyncIterable[ChatChunk | str]` from the Agent class definition (confirmed in livekit/agents repo `livekit-agents/livekit/agents/voice/agent.py`) accepts plain strings as a streaming protocol.
- The `google.TTS(model_name="gemini-2.5-flash-tts", voice_name="Kore", prompt=...)` signature is from livekit-plugins-google ≥1.3.7 (PR #4189, merged 2025-12-08).

### Pattern 2: Local in-process LiveKit (room) vs no-room standalone

**What:** AgentSession requires a `room` argument in production usage. The room is a WebRTC SFU connection — designed for multi-participant scenarios. For vibemix's single-user-on-desktop case, there are two viable shapes:

(a) **Bundled local `livekit-server --dev` binary**, started by the sidecar at launch on `127.0.0.1:7880`. The Python agent connects to it as a "participant" alongside a virtual capture participant that publishes the AudioFrame stream we produce from sounddevice. Gemini TTS output frames are subscribed back into the room and played out.

(b) **Skip the room entirely** — instantiate Agent + AgentSession but never call `session.start(room=...)`. Instead, directly invoke `agent.llm_node()` and pipe its output through a TTS stream we manage ourselves. This loses AgentSession's turn/interrupt orchestration but cuts WebRTC complexity.

**When to use:**
- (a) is the canonical, documented path. LiveKit's whole agent lifecycle (interruptions, mic-gate, turn timing) assumes a Room. Choosing (a) means we get the proven plumbing.
- (b) is tempting because there's only ever one local user — but we then re-implement what AgentSession does. Not recommended.

**Trade-offs (recommendation: (a)):**
- Pro (a): All LiveKit features work as documented. Tested code path. Mic-gate via `AudioOutput` listener works.
- Pro (a): If we later want a web-based remote spectator mode, it's already there.
- Con (a): Bundles `livekit-server` binary (~30 MB) inside the installer. Adds a port (7880 TCP, 7881 TCP, 7882 UDP) the user must not have blocked.
- Con (a): WebRTC adds ~5-15ms of latency vs direct in-memory passthrough. Tolerable for this domain (Gemini Flash inference + TTS dominates latency budget at ~500-1500ms).

**Recommendation: ship (a). Bundle `livekit-server` from the official Go binary release.**

### Pattern 3: Sidecar process model (Tauri + Python)

**What:** The Tauri Rust shell launches the Python sidecar as a child process via Tauri's externalBin mechanism. Tauri owns the UI; Python owns the realtime work. They communicate via:
- **Tauri commands → Python**: command-line args on launch + IPC over a Unix socket / Named Pipe (Tauri's `sidecar.spawn()` returns a handle with stdin/stdout/stderr). Use stdin for config JSON delivered on startup.
- **Python → UI**: WebSocket on `ws://127.0.0.1:8765` (same protocol as today's mascot.html). High-rate telemetry (RMS @30fps, events as they fire, AI text streams) goes here.
- **Tauri-shell-only concerns**: Tray icon, auto-update, signed installer, native file-system permissions, native window-picker (Tauri can enumerate windows via OS APIs in Rust faster than Python).

**When to use:** When you have a Python-heavy realtime stack (numpy, scipy, sounddevice, mido, mss, livekit-agents) that doesn't gracefully embed in a single-language framework, AND you want web-quality UI without shipping Electron's ~150MB Chromium.

**Trade-offs:**
- Pro: Tauri installers are 5-15 MB shell + system webview. The Python sidecar is the size driver (~80-120 MB with PyInstaller bundling numpy/scipy/livekit).
- Pro: Rust shell handles all OS native concerns (signing, notarization, auto-update via Tauri Updater, file dialogs).
- Pro: UI is React + Vite — fast dev loop, hot-reload, web-quality animations for the mascot canvas.
- Con: Two-language toolchain. Rust + Python both need to build in CI.
- Con: PyInstaller + numpy + scipy has known headaches (especially with the new Python 3.14 in the repo — pin to 3.12 for shipping).
- Con: macOS notarization of an unsigned Python sidecar inside a notarized Tauri shell requires the sidecar to also be ad-hoc-signed.

**Comparison matrix:**

| Option | Bundle size | Latency to UI | UI quality | Dev complexity | Native feel |
|--------|-------------|---------------|------------|----------------|-------------|
| **Tauri + Python sidecar** (recommended) | 90-130 MB | <5ms (WS local) | High (web) | High (2 langs) | High |
| Electron + Python sidecar | 200-250 MB | <5ms (WS local) | High (web) | Medium (1.5 langs) | Medium |
| PyQt6 single process | 80-100 MB | direct | Medium-High | Low (1 lang) | Medium |
| customtkinter single process | 60-80 MB | direct | Low-Medium | Lowest | Low |
| Native UI per OS (Cocoa + WinUI) | 50-80 MB | direct | Highest | Highest | Highest |

**Why Tauri wins for vibemix:**
- Bravoh team already builds React + Vite + TypeScript daily — UI velocity matches existing skill.
- The mascot canvas, RMS meters, calibration wizard all benefit from web rendering (CSS animations, SVG, easy theming).
- PyQt6's GPL-vs-commercial-license question is a blocker for an open-source-with-commercial-Bravoh-relationship product.
- customtkinter is too low-fidelity for the polish bar Kaan sets ("no AI slop aesthetics").
- Native-per-OS doubles UI engineering — incompatible with the 3-4-week timeline.

### Pattern 4: Cross-platform OS abstraction via protocol classes

**What:** Each platform-specific concern (audio input, screen capture, now-playing track) is fronted by a Protocol-shaped interface. The `platform/` package picks the right implementation at import time based on `sys.platform`.

**When to use:** Whenever there's an OS-API difference that doesn't have a single cross-platform library covering both with identical semantics.

**Trade-offs:**
- Pro: One import statement in client code (`from vibemix.platform import audio_input`). Tests can swap in a fake.
- Pro: New platform (Linux, if we ever cave) = one new module, no client changes.
- Con: Easy to drift — must enforce that both implementations satisfy the protocol via runtime checks in CI.

**Example:**
```python
# vibemix/platform/__init__.py
import sys
from typing import Protocol, Callable

class AudioInput(Protocol):
    def list_loopback_devices(self) -> list[dict]: ...
    def open(self, device_id: str, on_frame: Callable[[bytes], None]) -> "Stream": ...

if sys.platform == "darwin":
    from ._audio_macos import MacAudioInput as _AudioInput
elif sys.platform == "win32":
    from ._audio_windows import WindowsAudioInput as _AudioInput
else:
    raise RuntimeError("vibemix supports macOS and Windows only in v1")

audio_input: AudioInput = _AudioInput()
```

### Pattern 5: Bravoh-side proxy for API-key protection

**What:** vibemix never holds the real Gemini API key. Instead, vibemix-core boots, derives an anonymous `client_id` (stored in `~/Library/Application Support/vibemix/client_id` on first run — a UUID4 + machine fingerprint hash), and POSTs to `https://api.altidus.world/vibemix/v1/auth/token` for a signed short-lived JWT (15-30 min TTL). Every Gemini call is routed through `https://api.altidus.world/vibemix/v1/gemini/generate-content` and `/v1/gemini/tts` with the JWT as Bearer token. The proxy:
1. Validates JWT signature and expiry.
2. Checks Redis token bucket: `vibemix:rl:{client_id}` — e.g. 60 requests / 5 minutes, 2000 requests / day.
3. Forwards the request to Google's Gemini API using Bravoh's real API key.
4. Streams the response back (chunked transfer-encoding for TTS PCM, SSE for generate-content stream).

**When to use:** Whenever an open-source desktop app needs access to a paid API without exposing the key. Standard pattern, well-understood threat model.

**Why not ephemeral tokens directly?** Gemini's ephemeral-token feature is **Live API only** (verified in https://ai.google.dev/gemini-api/docs/ephemeral-tokens). Since vibemix uses `generate_content` (non-realtime Flash) + Gemini TTS streaming, ephemeral tokens don't apply. The proxy is the only viable pattern for the chosen Flash+TTS architecture.

**Trade-offs:**
- Pro: Real key never leaves Bravoh server. Compromised desktop binary cannot leak it.
- Pro: Per-client rate limiting is enforceable. Abuse cap protects budget (Kaan's hard constraint: ~€50/mo Gemini spend).
- Pro: Anonymous usage telemetry is free (logs already exist on the proxy).
- Pro: Future kill-switch: revoke a client_id if it abuses.
- Con: Adds 50-100ms RTT to every Gemini call (Frankfurt/EU servers → Bravoh server → Gemini). Within budget given Gemini's own 500-1500ms latency.
- Con: Bravoh server is now a single point of failure for vibemix. Acceptable: open-source users can fork and bring-their-own-key as the fallback escape valve.
- Con: One more service to operate. But Bravoh already runs FastAPI + PostgreSQL + Redis + nginx on `api.altidus.world` — adding two endpoints is trivial.

**JWT scope contents:**
```json
{
  "sub": "vibemix:client:<uuid4>",
  "iat": 1715450000,
  "exp": 1715451800,
  "tier": "free",
  "rate_limit": { "rpm": 12, "rpd": 2000 },
  "machine_fp": "<sha256 hash of stable machine attrs>"
}
```

## Data Flow

### End-to-end: crossfader move → AI speaks (latency budget)

```
T+0ms:    User moves crossfader on DDJ-FLX4
T+~1ms:   USB MIDI → mido callback → ControllerState.handle_msg()
          → updates ControllerState.recent_moves ring
T+~10ms:  state_refresh_loop next tick (10Hz)
          → reads ControllerState.recent_moves
          → MusicState.recent_moves updated
T+~10ms:  EventDetector.detect() called
          → diffs MusicState.recent_moves
          → emits MIX_MOVE event (magnitude=0.4, direction=right)
T+~11ms:  coach_loop wakes
          → checks cooldown (MIN_EVENT_GAP_PER_TYPE[MIX_MOVE] = 8s)
          → checks trigger_state["in_flight"] (false)
          → AICoach.build_prompt(event) → "[evidence: rms=0.41 bands=...]\nThe crossfader just moved to B by 40%..."
T+~12ms:  session.generate_reply(instructions=prompt)
          → AgentSession constructs chat_ctx (system + history + instructions as user msg)
          → calls DJCoHostAgent.llm_node(chat_ctx, ...)
T+~13ms:  llm_node:
          → snapshots AudioBuffer.snapshot_bytes(seconds=7) (~225 KB, 16k mono int16)
          → reads ScreenBuffer.latest_jpeg() (~30-80 KB)
          → reads MusicState.evidence_line()
T+~14ms:  POST https://api.altidus.world/vibemix/v1/gemini/generate-content
          { contents: [audio_part, image_part, text_evidence, instructions], stream: true }
          + Authorization: Bearer <JWT>
T+~80ms:  Proxy validates JWT, checks rate limit, forwards to Google Gemini
T+~500-1200ms:  Gemini Flash multimodal first text token arrives
          → proxy streams SSE back to llm_node
T+~500-1200ms:  llm_node yields first str chunk
          → AgentSession routes to tts_node (default google.TTS)
T+~520-1220ms:  tts_node calls google.TTS streaming synth API via proxy
          POST https://api.altidus.world/vibemix/v1/gemini/tts
          { input: "yo that crossfader move", model: "gemini-2.5-flash-tts", voice: "Kore" }
T+~800-1500ms:  First PCM chunk arrives
          → AgentSession emits AudioFrame to local audio output track
          → PlaybackQueue receives, sounddevice OutputStream plays to headphones
T+~800-1500ms:  USER HEARS FIRST SYLLABLE
T+~1500-2500ms:  Full reaction streamed (2-4 sec of speech)

Total perceived latency: ~800-1500ms (Gemini Flash multimodal inference dominates).
Local capture + state + event-detect overhead: <15ms.
Proxy hop overhead: ~80-150ms RTT.
TTS first-byte: ~100-300ms after LLM first-token.
```

**This is the latency reality.** Kaan's prompts already operate in past tense ("yo that mix you just did") because by the time the AI speaks, the moment is 1-1.5s in the past. This is documented in `cohost_v2.py:120` SYSTEM_INSTRUCTION ("latency-aware, past tense").

**To stay under perceived 1.5s budget:**
- Stream first TTS chunk as soon as the first sentence-boundary in the LLM stream is reached. (`google.TTS` in livekit-plugins-google does this — sentence buffering via `SynthesizeStream`.)
- Cap LLM output at ~12-20 words (≈ 2-3 sec of speech). Configured via `model_settings.temperature` and prompt constraint.
- Keep proxy in same region as Bravoh server (already EU/Frankfurt).
- Use `gemini-2.5-flash-tts` not `chirp_3` (faster first-byte).

### Calibration flow (data flow)

```
On first launch (Tauri spawns vibemix-core --calibrate):

Step 1 — Permissions:
  vibemix-core checks (macOS: TCC for Screen Recording + Microphone)
  → if missing: emit ws msg {step: "perm", status: "blocked", needs: ["screen_record"]}
  → Tauri UI shows "Open System Settings" button → opens via tauri-plugin-shell
  → vibemix-core polls TCC every 500ms; on grant emits {step: "perm", status: "ok"}

Step 2 — Audio loopback device:
  vibemix-core calls platform.audio_input.list_loopback_devices()
  → macOS: scan sounddevice device list; score those matching /blackhole|loopback|virtual/i highest
  → Windows: scan PyAudioWPatch loopback devices; score WASAPI loopback for default output device
  → emit ws msg {step: "audio_in", candidates: [{id, name, score}, ...]}
  → Tauri UI shows ranked list, user picks one (or accepts top)
  → on macOS, if no BlackHole detected: emit {step: "audio_in", missing: "blackhole", install_url: "..."}

Step 3 — Audio output device:
  vibemix-core calls platform.audio_output.list_devices()
  → score: headphone/in-ear devices (USB DAC, AirPods) > speakers > virtual cables
  → emit {step: "audio_out", candidates: [...]}
  → Tauri UI picker, user picks "Headphones" or "Speakers"

Step 4 — DJ app window picker:
  vibemix-core calls platform.screen.list_windows()
  → macOS: Quartz CGWindowListCopyWindowInfo, filter by app name (djay, Rekordbox, Serato, Traktor, VirtualDJ)
  → Windows: pywin32 EnumWindows, filter by window title
  → emit {step: "window", candidates: [{pid, title, app_name, thumbnail_b64}, ...]}
  → Tauri UI grid of thumbnails, user clicks one

Step 5 — Controller probe:
  vibemix-core opens all MIDI input ports via mido.get_input_names()
  → emits {step: "midi", probing: true}
  → user is asked to "wiggle any knob on your controller"
  → vibemix-core listens for first MIDI message → matches port name against controller library
  → emit {step: "midi", detected: "DDJ-FLX4", mapping_source: "library"}
  → if no match: {step: "midi", detected: null, suggest: "generic", port_name: "..."}
  → Tauri UI confirms detected controller or shows generic-fallback option

Step 6 — Genre + mode:
  Pure UI step in Tauri. User picks Beginner/Intermediate/Pro × Hype/Coach × Genre.
  Tauri sends config JSON to vibemix-core via stdin (or tauri command → WS).

Step 7 — Smoke test:
  vibemix-core starts a 10-second test session.
  → user is asked to "press play on a track"
  → on first detected audio: emit {step: "smoke", audio_ok: true}
  → fire one manual event → AI generates a short greeting via real Flash+TTS path
  → user confirms they heard it in their headphones
  → emit {step: "done"}

Config persists to ~/Library/Application Support/vibemix/config.json (or %APPDATA%/vibemix/).
```

### Recording layer (data flow)

```
Per session:
  SessionDir = recordings/<YYYYMMDD-HHMMSS>/

  Audio input → VoiceRecorder.push_input(pcm_16k_mono) → input.wav (appended)
  Gemini TTS output → VoiceRecorder.push_voice(pcm_24k_mono) → voice.wav (appended)
  Every event → VoiceRecorder.log_event(kind, payload, ts) → events.jsonl

  On session end:
    - Close WAV files (write final header).
    - Compute session metadata (duration, event count, AI turn count) → session.json
    - Optional: cloud upload (post-v1) — gated by user opt-in in Settings.

Recording is ALWAYS ON in v1 (matches existing POC behavior). Storage hygiene:
  - On startup, vibemix-core enumerates recordings/ subdirs.
  - If total size > 5 GB, delete oldest until under 4 GB. Surface in Settings:
    "Recordings: 12 sessions, 3.4 GB used. [Open folder] [Delete all]"

Post-v1 cloud upload sketch:
  - Sessions uploaded to MinIO bucket on Bravoh infra (s3://altidus-vibemix-sessions/)
  - URL signed for 7 days, returned to user as "share this session"
  - Used for "I made my AI co-host roast me, watch this" social loops
```

### State Management

```
MusicState (single dataclass, written only by state_refresh_loop @10Hz)
    ↓ (read-only)
EventDetector.detect(state) → Event[]
    ↓
coach_loop @10Hz checks cooldowns + in_flight → fires
    ↓
session.generate_reply(instructions=AICoach.build_prompt(event))
    ↓
DJCoHostAgent.llm_node — yields token stream
    ↓
AgentSession.tts_node (google.TTS plugin) — yields AudioFrame stream
    ↓
PlaybackQueue → sounddevice OutputStream
    ↓
Headphones / Speakers
```

### Key Data Flows

1. **Audio capture → state:** sounddevice callback (real-time thread) → AudioBuffer.push() + Levels.update_music() → state_refresh_loop (asyncio @10Hz) → MusicState. Cross-thread safety via threading.Lock in buffer classes (unchanged from POC).
2. **MIDI → event:** mido thread (blocking) → ControllerState.handle_msg() → recent_moves ring → state_refresh_loop reads → EventDetector.detect() → MIX_MOVE event.
3. **Event → AI:** EventDetector → AICoach.build_prompt() → session.generate_reply() → llm_node (gemini-3-flash-preview multimodal) → tts_node (gemini-2.5-flash-tts) → AudioFrame stream → PlaybackQueue.
4. **AI → mascot UI:** AgentSession AudioOutput event → Levels.update_voice() → ws_broadcast @30fps → Tauri webview canvas.
5. **Calibration → config:** Tauri UI → IPC → vibemix-core stdin → config.store → ~/Library/Application Support/vibemix/config.json. Next launch reads it; if missing, runs calibration wizard.

## Build Order Implications (what blocks what)

```
Phase A — Foundation (must come first; nothing else works without these)
  1. platform/ abstraction protocols (signatures, no implementations yet)
  2. audio/ classes (port AudioBuffer, MicBuffer, Levels, PlaybackQueue from cohost_v2.py)
  3. platform/_audio_macos.py implementation (we have this working in POC)
  4. PyInstaller --onedir build script for macOS sidecar
  → blocks: everything downstream

Phase B — Sensing + State (port from POC, well-understood)
  5. state/music_state.py (port MusicState dataclass)
  6. state/events.py (port EventDetector)
  7. state/coach.py (port AICoach)
  8. sense/screen.py + platform/_screen_macos.py (port from POC)
  9. midi/controller.py + midi/library/ddj_flx4.py (port from POC)
  → blocks: agent layer (needs MusicState to read)

Phase C — Agent Pipeline (NEW — the architectural pivot)
  10. agent/gemini_flash.py — google-genai multimodal call wrapper
  11. agent/dj_agent.py — DJCoHostAgent with llm_node override
  12. agent/session.py — wire AgentSession with google.TTS plugin
  13. Local livekit-server bundling decision (bundle binary OR skip server)
  → blocks: end-to-end test

Phase D — Cross-platform Windows port (parallel to C if Musa picks it up)
  14. platform/_audio_windows.py (PyAudioWPatch WASAPI loopback)
  15. platform/_screen_windows.py (mss + pywin32 EnumWindows)
  16. platform/_nowplaying_windows.py (winsdk GSMTC)
  17. PyInstaller build script for Windows sidecar
  → blocks: Windows installer

Phase E — Tauri Shell + UI
  18. Tauri 2.x project scaffold, sidecar wiring, IPC contracts
  19. Calibration wizard UI (7 steps from above)
  20. Live session UI (mascot canvas + meters)
  21. Settings panel
  → blocks: installer

Phase F — MIDI Library (parallel to D, E)
  22. 10 controller mapping files
  23. Generic-MIDI fallback with positional inference
  24. Auto-detect + library matching
  → can start any time after step 9

Phase G — Proxy + Auth
  25. FastAPI endpoints on api.altidus.world: /vibemix/v1/auth/token, /v1/gemini/generate-content, /v1/gemini/tts
  26. Redis rate limit (token bucket)
  27. JWT signing key rotation
  28. vibemix/proxy/ client code
  → can start any time; integrate after C is functional

Phase H — Recording + Telemetry
  29. recording/ port from POC
  30. ui_bus/ WS server with new message schemas
  31. Anonymous usage telemetry to Bravoh (opt-out in settings)

Phase I — Distribution
  32. macOS DMG signing + notarization
  33. Windows installer + code signing
  34. Auto-updater (Tauri Updater plugin)
  35. Public GitHub Enterprise repo setup + README + hero video
  → final phase
```

**Critical path:** A → B → C → E (with G integrated) → I. Total estimated ~3-4 weeks if Kaan + Musa work in parallel (C, E, G assigned different).

**Parallel opportunities:** D (Windows port) can run alongside C+E once protocols are pinned in A. F (MIDI library) is data entry — Yasin can do it in parallel after step 9.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-100 daily-active users | Current architecture. Bravoh proxy on existing infra. ~€10-30/mo Gemini spend. |
| 100-1,000 DAU | Bump Redis to dedicated instance. Add per-region proxy (US East) for latency. Consider Gemini's batch tier for non-realtime requests (not applicable to live sessions). ~€100-300/mo. |
| 1,000-10,000 DAU | Multi-project key pool on Bravoh proxy (rotate across N Google Cloud projects to avoid per-project rate caps). CDN-cache TTS responses for repeated phrases. Background queue for recording uploads if cloud-upload ships. ~€1,000-3,000/mo — at this scale we charge or partner. |
| 10,000+ DAU | Beyond v1 scope. Either monetize (Bravoh Pro upsell) or rate-limit harder. |

### Scaling Priorities

1. **First bottleneck: Gemini per-project rate limit (RPM).** Mitigation: maintain a pool of 3-5 Google Cloud projects on Bravoh side; round-robin requests. Documented pattern from CLI-proxy projects.
2. **Second bottleneck: Bravoh proxy CPU/network.** Mitigation: TTS streaming is bytes-passthrough — uvicorn + httpx with streaming response handles ~500 concurrent streams on the existing API server. Beyond that, scale horizontally.
3. **Third bottleneck: User-side disk for recordings.** Mitigation: auto-delete old sessions over 4 GB. Already in plan.

## Anti-Patterns

### Anti-Pattern 1: Routing audio through LiveKit Cloud

**What people do:** Spin up a LiveKit Cloud project, give every desktop app a cloud token, send audio to cloud SFU and back.
**Why it's wrong:** vibemix is single-user desktop. There's only one participant. LiveKit Cloud adds 80-200ms WAN round-trip for audio that never needs to leave the user's machine. Cost scales with bandwidth.
**Do this instead:** Bundle `livekit-server --dev` locally OR use the local-loop AudioSource→AgentSession→AudioOutput pattern. WebRTC is the framework, not the requirement.

### Anti-Pattern 2: Calling Gemini Flash directly from desktop binary

**What people do:** Embed the GEMINI_API_KEY in the PyInstaller bundle (or read from .env shipped alongside).
**Why it's wrong:** Anyone can `strings` the binary, extract the key, drain Bravoh's quota in hours. Also exposes Bravoh's billing relationship to whoever wants to abuse it.
**Do this instead:** Proxy pattern. Real key on Bravoh server. Per-client JWT with rate limits. Documented above.

### Anti-Pattern 3: Letting Tauri handle audio/MIDI

**What people do:** Use Tauri plugins (or Rust crates like `cpal`, `midir`) to capture audio and MIDI in the Rust shell, send to Python only for AI.
**Why it's wrong:** Doubles the audio plumbing — now we have audio buffers in two languages, two threading models, IPC serialization of every PCM chunk. The existing POC code is Python, proven, and tightly integrated with state/event/AI loops. Tauri's job is UI shell, not realtime media.
**Do this instead:** Python sidecar owns *all* media. Tauri only renders the UI and forwards user commands. WS @30fps for telemetry is enough for the UI to feel reactive.

### Anti-Pattern 4: Single global asyncio loop with blocking I/O

**What people do:** Call `mido.input_callback(...)` directly in the asyncio loop, or call sounddevice OutputStream blocking write.
**Why it's wrong:** Blocks the loop, kills event timing, makes state_refresh_loop drift. Already documented in the POC's known-issues (feature extraction in trigger callback, line 1340 of cohost_lk.py).
**Do this instead:** Use the POC's existing pattern — sounddevice callbacks on the real-time OS audio thread, mido on a daemon thread, threading.Lock-protected buffer classes for cross-thread state. Only the AI call path runs on asyncio.

### Anti-Pattern 5: Bundling Electron for the UI

**What people do:** Pick Electron because "everyone knows web tech".
**Why it's wrong:** Bundles 150+ MB Chromium. Cold-start is 800-1500ms. Memory baseline is 200+ MB before our Python sidecar even starts.
**Do this instead:** Tauri uses the system webview (WebKit on macOS, WebView2 on Windows). 10x smaller installer, half the RAM, faster cold start. For our UI complexity (calibration + meters + session list) the system webview is fully sufficient.

### Anti-Pattern 6: Skipping AgentSession and rolling custom LLM→TTS plumbing

**What people do:** "We don't need LiveKit Agents — just call Gemini Flash, get text, call Gemini TTS, play PCM."
**Why it's wrong:** Re-implements turn management, interruption handling, mic-gate-during-AI-speech, audio frame slicing, sentence-boundary TTS chunking, error recovery. AgentSession already does all this and is battle-tested.
**Do this instead:** Use AgentSession with `llm_node` override (Pattern 1). You write only the Gemini multimodal request construction; everything else is provided.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Gemini 3 Flash (generate-content streaming) | HTTPS POST via Bravoh proxy → google-genai `generate_content_stream` | Multimodal: audio bytes + inline_data JPEG + text. Pin model `gemini-3-flash-preview` |
| Gemini 2.5 Flash TTS (streaming) | livekit-plugins-google `google.TTS(model_name="gemini-2.5-flash-tts")` → goes through Bravoh proxy via custom HTTP transport | 24kHz PCM output. Voice prompts on first chunk only |
| nowplaying-cli (macOS) | Subprocess poll @1Hz → parse JSON | Already wrapped in POC. Won't work on macOS without MediaPlayer framework |
| Windows GSMTC (Global System Media Transport Controls) | `winsdk.windows.media.control` async API | Direct equivalent to nowplaying-cli on Windows |
| BlackHole (macOS virtual audio) | sounddevice device by name match | Must be installed by user — calibration wizard prompts with install URL `existential.audio/blackhole/` |
| WASAPI loopback (Windows) | PyAudioWPatch — no user install needed | Built into Windows since Vista |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Tauri UI ↔ vibemix-core | Tauri stdin (config JSON on launch) + WS @127.0.0.1:8765 (telemetry up) + tauri::Command (control down) | Schemas typed in `ui_bus/messages.py` |
| vibemix-core ↔ Bravoh proxy | HTTPS, Bearer JWT | Retried with backoff; offline mode falls back to "no AI" status indicator |
| platform/* ↔ rest of Python | Protocol imports (no `if sys.platform`) outside platform/ | Enforced by lint rule |
| state/ ↔ agent/ | One-way reads (state→agent never writes back to state) | Prevents accidental coupling |
| agent/ ↔ recording/ | Event hooks on AgentSession (`on_generation_created`, `on_audio_frame`) | Same pattern as cohost_v2.py:on_gen |

## Sources

**LiveKit Agents framework:**
- [LiveKit Agents documentation — Models overview](https://docs.livekit.io/agents/models/) — AgentSession composition of stt/llm/tts
- [Agent speech | LiveKit Docs](https://docs.livekit.io/agents/build/speech/) — session.say() vs generate_reply(), audio-only playback
- [Agent dispatch | LiveKit Documentation](https://docs.livekit.io/agents/server/agent-dispatch/) — worker/job model
- [LLM Output Replacement recipe](https://docs.livekit.io/reference/recipes/replacing_llm_output/) — llm_node override pattern (HIGH-confidence reference for Pattern 1)
- [LiveKit Agents Python — voice module reference](https://docs.livekit.io/reference/python/livekit/agents/voice/index.html) — Agent class, AgentSession class signatures
- [agents/livekit-agents/livekit/agents/worker.py source](https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/worker.py) — worker process model
- [TTS and STT Plugins | livekit/agents | DeepWiki](https://deepwiki.com/livekit/agents/6-tts-and-stt-plugins) — abstract LLM/TTS interface details
- [LLM Providers | DeepWiki](https://deepwiki.com/livekit/agents/5.1-llm-providers) — LLMStream contract
- [PR #4189 — Gemini TTS streaming](https://github.com/livekit/agents/pull/4189) — merged 2025-12-08, released in livekit-plugins-google 1.3.7
- [Voice Agent Architecture: STT, LLM, and TTS Pipelines Explained](https://livekit.com/blog/voice-agent-architecture-stt-llm-tts-pipelines-explained)
- [Issue #1673 — Hybrid Gemini Realtime + VoicePipelineAgent](https://github.com/livekit/agents/issues/1673)
- [Issue #3864 — Google TTS (Gemini) streaming](https://github.com/livekit/agents/issues/3864) — closed by PR #4189

**LiveKit local server:**
- [Running LiveKit locally](https://docs.livekit.io/transport/self-hosting/local/) — `livekit-server --dev` on 127.0.0.1:7880
- [livekit-server-sdk-python](https://github.com/livekit/livekit-server-sdk-python)
- [livekit/python-sdks — AudioSource, LocalAudioTrack](https://github.com/livekit/python-sdks)
- [livekit.rtc.audio_source API](https://docs.livekit.io/python/livekit/rtc/audio_source.html) — `capture_frame` for pushing custom audio
- [Processing raw media tracks](https://docs.livekit.io/transport/media/raw-tracks/)

**Gemini API:**
- [Gemini 3 Flash docs](https://ai.google.dev/gemini-api/docs/gemini-3) — multimodal generateContent
- [Ephemeral tokens | Gemini API](https://ai.google.dev/gemini-api/docs/ephemeral-tokens) — confirmed Live API only
- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) — per-project, not per-key
- [Google Gemini LLM plugin guide | LiveKit](https://docs.livekit.io/agents/integrations/llm/gemini/)

**Cross-platform audio + screen + MIDI:**
- [BlackHole — macOS virtual audio](https://existential.audio/blackhole/) — install pattern for calibration wizard
- [PyAudioWPatch (WASAPI loopback for Windows)](https://github.com/s0d3s/PyAudioWPatch)
- [SoundCard (cross-platform Python audio)](https://github.com/bastibe/SoundCard) — alternative to PyAudioWPatch, supports all three OSes
- [python-mss (cross-platform screen capture)](https://github.com/BoboTiG/python-mss)
- [Loopback Recording — Win32 apps | Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording)

**Tauri + Python sidecar:**
- [Tauri Embedding External Binaries (sidecar)](https://v2.tauri.app/develop/sidecar/) — externalBin + per-target-triple naming
- [example-tauri-v2-python-server-sidecar](https://github.com/dieharders/example-tauri-v2-python-server-sidecar) — reference template
- [Building Production-Ready Desktop LLM Apps: Tauri, FastAPI, PyInstaller](https://aiechoes.substack.com/p/building-production-ready-desktop)
- [Which Python GUI library should you use in 2026?](https://www.pythonguis.com/faq/which-python-gui-library/) — PyQt6 vs alternatives comparison

**API-key protection:**
- [Hands on Mobile API Security — Using a Proxy to Protect API Keys](https://approov.io/blog/hands-on-mobile-api-security-using-a-proxy-to-protect-api-keys)
- [Decoded: How Google AI Studio Securely Proxies Gemini API Requests](https://glaforge.dev/posts/2026/02/09/decoded-how-google-ai-studio-securely-proxies-gemini-api-requests/) — Google's own proxy pattern reference
- [LLM-API-Key-Proxy](https://github.com/Mirrowel/LLM-API-Key-Proxy) — open-source pool-rotation reference

**JWT auth in FastAPI:**
- [Securing FastAPI with JWT Token-based Authentication | TestDriven](https://testdriven.io/blog/fastapi-jwt-auth/)
- [Bulletproof JWT Authentication in FastAPI](https://medium.com/@ancilartech/bulletproof-jwt-authentication-in-fastapi-a-complete-guide-2c5602a38b4f)

---
*Architecture research for: vibemix — cross-platform AI DJ co-host*
*Researched: 2026-05-11*
