# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**vibemix — AI DJ Co-Host**

A free, open-source AI co-host for live DJ sets. Runs locally on macOS or Windows: listens to your master output, watches your DJ software's screen, ingests your controller actions over MIDI, and talks back into your headphones or speakers as either a hype-man (party mode) or a coach (feedback mode). Three user levels — Beginner / Intermediate / Pro — with prompt templates tuned to each, plus a curated library of ~10 popular MIDI controllers mapped out of the box.

Bravoh's first open-source release. Built as a polished, narrow-scope utility that warms an audience converting into Bravoh's waitlist.

**Core Value:** The AI reacts to your set in a way that feels alive and grounded — never hallucinating, never breaking the flow, never sounding like generic AI slop. If reactions feel forced, late, fake, or scripted, the product fails. The bar is "real DJ friend in your ear", not "voice assistant doing music commentary".

### Constraints

- **Timeline**: No hard calendar target — ship-when-ready per `gsd-autonomous fully` mode. External Apple + SignPath approvals are the critical path; engineering parallelizes around the external clock.
- **Quality bar**: "Real DJ friend in your ear, no AI slop" — Kaan will block release if reactions feel scripted, late, hallucinated, or generic.
- **Budget**: 150-200 € launch marketing (IG ads, paid posts), ~50 €/month ongoing Gemini API for end-user requests. Reassess if usage scales.
- **Tech stack**: Locked on LiveKit pipeline + Gemini 3 Flash + Gemini TTS streaming. No other LLM providers (Bravoh is Gemini-only).
- **Platforms**: macOS + Windows in v1. Linux explicitly excluded.
- **Team**: Kaan (engineering + product), Francesco (cofounder — product/marketing/DJ network for outreach), Momo (Bravoh team). Bravoh main product takes priority — vibemix runs alongside.
- **Open-source license**: TBD (likely MIT or Apache 2.0). Must allow Bravoh to use the same code internally if needed.
- **Security**: API key embedded in distributed binary is the API-key-protection problem of the year — solve via Bravoh-side proxy with per-client rate limit, not by shipping a raw key.
- **Hallucination grounding**: No release until verification phase confirms reactions are tied to real events. This is a hard gate.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.14 - All application logic (cohost.py, cohost_v2.py, cohost_lk.py)
- JavaScript (vanilla, no framework) - Mascot overlay UI (`mascot.html`)
- HTML/CSS - Mascot overlay (`mascot.html`)
## Runtime
- CPython 3.14 (confirmed via `.venv/lib/python3.14/`)
- macOS only — hard dependency on BlackHole virtual audio, macOS Now Playing API, optional Quartz window APIs
- pip (no requirements.txt or pyproject.toml — dependencies installed directly into `.venv`)
- Lockfile: absent (no requirements.txt committed)
- Virtual env: `.venv/` at project root
## Frameworks
- `asyncio` (stdlib) - Async event loop driving all three cohost variants
- `livekit-agents==1.5.8` - Agent framework wrapping Gemini Live API for `cohost_lk.py` and `cohost_v2.py`
- `livekit==1.1.7` - LiveKit RTC client (`livekit.rtc.AudioFrame` for audio push)
- `livekit-plugins-google==1.5.8` - `livekit.plugins.google.realtime.RealtimeModel` — Gemini Live via LiveKit
- `google-genai==2.0.1` - Google Generative AI Python SDK (`from google import genai`, `from google.genai import types`)
- `google-cloud-speech==2.39.0` - Installed but not directly imported in main cohost files
- `google-cloud-texttospeech==2.36.0` - Installed but not directly imported in main cohost files
- `openai==2.36.0` - Installed as livekit-agents transitive dep; not used directly in cohost code
- `numpy==2.4.4` - All audio buffer math, RMS, FFT, onset detection, BPM estimation
- `scipy==1.17.1` - `scipy.signal.resample_poly` for 48kHz→16kHz downsampling
- `sounddevice==0.5.5` - macOS CoreAudio I/O: BlackHole input, headphones + speakers output
- `av==17.0.1` - Installed (livekit dep); handles media container codecs in LiveKit pipeline
- `mido==1.3.3` - MIDI message parsing for Pioneer DDJ-FLX4 controller input
- `python-rtmidi==1.5.8` - Low-level MIDI port access (mido backend)
- `mss==10.2.0` - macOS screen capture (`import mss`) for djay Pro screen grabs
- `pillow==12.2.0` - PIL Image resize/crop before sending screenshot to Gemini
- `pyobjc-framework-Quartz==12.1` - `Quartz.CGWindowListCopyWindowInfo` to find and crop djay Pro window bounds
- Vanilla JS with Canvas 2D API — no build step, no bundler, opened directly via `file://` URL
- WebSocket client at `ws://127.0.0.1:8765` — receives `{music, voice, mic}` levels at 30Hz
- `websockets==16.0` - WebSocket server (mascot bus) and used by LiveKit internals
- `aiohttp==3.13.5` - HTTP async client (livekit-agents dep)
- `httpx==0.28.1` - HTTP client (google-genai dep)
- `python-dotenv==1.2.2` - `load_dotenv()` to source `GEMINI_API_KEY` from `.env`
- `pydantic==2.13.4` - Data validation (livekit-agents dep)
- `rich==15.0.0` - Terminal output formatting (livekit-agents dep)
- `opentelemetry-*` (1.39.1) - Observability stack installed as livekit-agents dep; not configured
- `pyobjc-core==12.1` - PyObjC bridge for macOS APIs
- `pyobjc-framework-Cocoa==12.1` - Cocoa framework bindings
- `pyobjc-framework-Quartz==12.1` - Quartz window listing
- `nowplaying-cli` (Homebrew binary at `/opt/homebrew/bin/nowplaying-cli`) - macOS MediaRemote polling for djay Pro track title/duration via `subprocess`
## Key Dependencies
- `google-genai==2.0.1` - All Gemini API calls (Live/multimodal/TTS/image); the sole AI provider
- `livekit-agents==1.5.8` + `livekit-plugins-google==1.5.8` - Gemini 2.5 Native Audio via RealtimeModel (used in `cohost_lk.py` and `cohost_v2.py`)
- `sounddevice==0.5.5` - The entire audio I/O pipeline; without it nothing plays or records
- `mido==1.3.3` - DDJ-FLX4 MIDI controller input; optional but gracefully degrades
- `scipy==1.17.1` - Resampling; required for 48kHz→16kHz conversion
- `numpy==2.4.4` - All audio math; cannot run without it
- `websockets==16.0` - Mascot bus server; degrades gracefully if absent (`_HAS_WS` guard)
- `mss==10.2.0` + `pillow==12.2.0` - Screen capture; degrades gracefully (`_HAS_VISION` guard)
- `pyobjc-framework-Quartz==12.1` - djay window cropping; degrades gracefully (`_HAS_QUARTZ` guard)
## Configuration
- Single `.env` file at project root (55 bytes — contains `GEMINI_API_KEY` only)
- Loaded via `load_dotenv()` at top of each cohost script
- Required env var: `GEMINI_API_KEY`
- No other env vars observed in code
- No build step; Python scripts run directly
- Run scripts: `run.sh` (cohost.py), `run_v2.sh` (cohost_v2.py), `run_lk.sh` (cohost_lk.py)
- Each script: `source .venv/bin/activate && exec python3 <script>.py`
- Mascot opened via `open file://$(pwd)/mascot.html` before starting the Python process
## Platform Requirements
- macOS only (BlackHole virtual audio driver, macOS MediaRemote via `nowplaying-cli`, CoreAudio via `sounddevice`, optional Quartz)
- BlackHole 2ch virtual audio driver (system-level install, not pip)
- djay Pro app running as audio source
- Pioneer DDJ-FLX4 MIDI controller (optional — graceful fallback)
- `nowplaying-cli` installed via Homebrew (`/opt/homebrew/bin/nowplaying-cli`)
- Python 3.14 in `.venv/`
- Single-machine local app — no server deployment, no network exposure
- All services run on localhost
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- `snake_case.py` throughout — `cohost.py`, `cohost_v2.py`, `cohost_lk.py`, `generate_bat.py`
- Leading underscore prefix = manual smoke-test scripts not intended for automated execution: `_test_tts.py`, `_test_multimodal.py`
- No underscore prefix = lightweight integration smoke test meant to be run: `test_voice.py`
- `.bak` suffix for superseded snapshots kept for reference: `cohost.streaming.py.bak`
- `snake_case` throughout — `find_device`, `start_input_stream`, `receive_audio`, `classify_phase`, `derive_audible_deck`
- Private helper methods use single leading underscore: `_current_gain`, `_is_session_dead`, `_knob_label`, `_write_event_locked`, `_cooldown_ok`, `_fire`
- Async coroutines named with `_loop` suffix for long-running background tasks: `trigger_loop`, `screen_capture_loop`, `track_poll_loop`, `diag_loop`, `ws_broadcast`
- Module-level private helpers use `_` prefix: `_HAS_VISION`, `_HAS_WS`, `_HAS_QUARTZ`
- Inner callback functions always named `callback` (defined inside stream factory functions)
- `snake_case` — `input_idx`, `levels`, `audio_buf`, `trigger_state`, `stop_event`
- Module-level constants in `UPPER_SNAKE_CASE` — `INPUT_SR_NATIVE`, `OUTPUT_SR`, `MIC_GAIN`, `SILENT_RMS`
- Short temporary names for local signal processing: `rms`, `arr`, `pcm`, `spec`, `freqs`
- Loop state dicts use string keys: `state["last_trigger"]`, `trigger_state["in_flight"]`
- `PascalCase` for all classes — `Levels`, `AudioBuffer`, `MicBuffer`, `PassthroughBuffer`, `PlaybackQueue`, `ScreenBuffer`, `VoiceRecorder`, `TurnHistory`, `MusicState`, `EventDetector`, `AICoach`, `TrackInfo`, `ControllerState`
- Custom exceptions use `PascalCase` with `Exception` suffix: `SessionDead`
- Dataclass fields use `snake_case` matching the pattern of other vars
## Code Style
- No formatter config file present (no `.black`, `.ruff.toml`, `pyproject.toml`)
- Consistent 4-space indentation observed throughout
- 79-100 char informal line length — no enforced limit
- Blank lines between top-level defs and class methods follow PEP 8 (2 between top-level, 1 between methods)
- No linting config detected (no `.flake8`, `.eslintrc`, `ruff.toml`)
- Project relies on developer discipline, not automated enforcement
## Import Organization
- None. All imports are absolute package names.
## Error Handling
## Logging
- Startup info uses `->` prefix: `print(f"-> listening to {name} @ {sr}Hz")`
- Error output goes to `sys.stderr`: `print(f"[receive err] {e}", file=sys.stderr)`
- Error prefixes use bracketed category tags: `[input status]`, `[turn err]`, `[coach err]`, `[screen err]`, `[mic status]`
- AI transcription output uses `AI> ` prefix: `print(f"\nAI> {txt}", flush=True)`
- Trigger events use `\n` prefix to break out of overwrite line: `print(f"\n[trigger {tag}] ...")`
- Live diagnostic uses `\r` overwrite: `sys.stdout.write(f"\r[live] music=...")` with `sys.stdout.flush()`
- Structured event logging via `VoiceRecorder.log_event()` to `events.jsonl` — separate from console output
## Comments
- Inline comments explain *why* a value or gate exists, not what the code does — especially for audio DSP constants and thresholds
- Multi-line inline comments on decisions that have been deliberately changed (e.g., AI talk gate removal at `cohost.py` lines 419–422)
- Section dividers use `# ----` or `# =====` in `cohost_v2.py` and `cohost_lk.py`
- Module-level docstrings present in all files — describes purpose and audio/data flow with ASCII diagrams where helpful
- Class docstrings: single-line or short multi-line describing thread safety and role — present on most classes in `cohost.py`; absent or minimal on equivalent classes in `cohost_v2.py` (they carry forward without re-documenting)
- Method docstrings: used on non-trivial methods (`snapshot_features`, `run_one_turn`, `start_input_stream`) but not on simple accessors (`push`, `pull`, `snapshot`)
- Async loop functions (`trigger_loop`, `receive_audio`) have docstrings describing the trigger logic and reconnect strategy
- No Google-style, NumPy-style, or Sphinx-style formatting — plain prose only
## Function Design
- Short utility functions: 5–15 lines (`find_device`, `_knob_label`, `_cooldown_ok`)
- Medium business logic: 20–50 lines (`run_one_turn`, `detect`, `classify_phase`, `snapshot_features`)
- Long orchestration coroutines: `trigger_loop` (cohost.py ~120 lines), `main` (cohost_v2.py ~200 lines) — not split into sub-functions
- Audio stream callbacks defined as inner closures inside factory functions (`start_input_stream`, `start_passthrough_stream`, `start_playback_stream`)
- Positional for required objects, keyword-only for tuning values: `snapshot_features(self, seconds: float = 7.0)`
- Dependency injection over globals: `Levels`, `AudioBuffer`, `PlaybackQueue` etc. are always passed explicitly
- `stop_event: asyncio.Event` passed to every long-running coroutine as cooperative shutdown signal
- Explicit `None` return for early exits in guard clauses
- Dict return for feature snapshots: `snapshot_features` returns `dict` with well-defined keys
- `bytes` / `np.ndarray` for audio data
- `bool` from `run_one_turn` to indicate success/failure
## Module Design
## Type Hints
- All public function signatures use type hints in `cohost.py` — `find_device(name_substring: str, kind: str) -> int`
- `cohost_v2.py` uses `from __future__ import annotations` (line 18) enabling PEP 604 union syntax (`str | None`, `bytes | None`, `dict | None`)
- Numpy arrays typed as `np.ndarray`, never as `list`
- Forward references use string literal form where needed: `levels: "Levels"` in `cohost.py`
- `cohost_lk.py` class methods mostly untyped internally; public function signatures have hints
- `@dataclass` used only in `cohost_v2.py` for `MusicState` (line 965) and `Event` (line 1119)
- No `mypy` or `pyright` config present — hints are documentation, not enforced
## Async vs Sync
- Main loop is `asyncio` with `asyncio.run(main())`
- Audio I/O callbacks are synchronous (sounddevice requires it) — called from separate OS audio threads
- Shared state (buffers, levels) uses `threading.Lock` for thread safety between audio threads and asyncio event loop
- Blocking operations offloaded via `loop.run_in_executor(None, fn)`: screen capture, track polling
- Long-running background tasks registered as `asyncio.create_task(...)` at startup
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## System Overview
```text
```
## Component Responsibilities
| Component | Responsibility | File |
|-----------|----------------|------|
| `Levels` | Smoothed EMA RMS for music/voice/mic; shared gating state | all variants |
| `AudioBuffer` | Rolling 16kHz int16 PCM ring; FFT feature extraction; BPM autocorr | all variants |
| `MicBuffer` | 200ms mic ring; auto-mutes during AI talk + hold window | all variants |
| `PassthroughBuffer` | 48kHz stereo ring for djay→speakers path (disabled at gain=0) | all variants |
| `PlaybackQueue` | 24kHz PCM ring fed to sounddevice output callback | all variants |
| `ScreenBuffer` | Latest JPEG of djay Pro window; updated ~1fps by mss | cohost.py, cohost_lk.py, cohost_v2.py |
| `TrackInfo` | nowplaying-cli poll; current + previous track title | cohost_lk.py, cohost_v2.py |
| `ControllerState` | Live DDJ-FLX4 MIDI decode; recent moves ring (12s) | cohost_lk.py, cohost_v2.py |
| `MusicState` | Single source of truth dataclass; written by state_refresh_loop | cohost_v2.py only |
| `EventDetector` | Reads MusicState diffs; emits typed events with cooldowns | cohost_v2.py only |
| `AICoach` | Builds evidence+task prompt string per event type | cohost_v2.py only |
| `VoiceRecorder` | Writes input.wav + voice.wav + events.jsonl per session | all variants |
| `TurnHistory` | Text-only ring of last N user+model turns for context | cohost.py only |
| `trigger_loop` | Event detection polling loop (v1/lk approach) | cohost.py, cohost_lk.py |
| `run_one_turn` | Stateless Gemini HTTP call: multimodal LLM → TTS (cascade) | cohost.py only |
| `ws_broadcast` | WebSocket server @30fps; feeds mascot.html; v2 receives manual trigger | all variants |
## Variant Overview
### `cohost.py` — Mainline (stateless HTTP cascade)
- **Gemini strategy:** Two-call cascade per turn: `gemini-3-flash-preview` (multimodal text) → `gemini-3.1-flash-tts-preview` (TTS)
- **Session model:** Stateless HTTP. No persistent websocket. `TurnHistory` ring maintained in Python.
- **Audio to Gemini:** Snapshot from `AudioBuffer` (7s PCM inline in request), not streaming
- **Vision:** Screen JPEG inline in each request
- **Trigger detection:** `trigger_loop()` — RMS delta + level-state transitions + mic detection
- **Entry point:** `main()` at line ~1081, `asyncio.run(main())`
### `cohost_lk.py` — LiveKit variant (streaming Live API)
- **Gemini strategy:** `gemini-2.5-flash-native-audio-preview-12-2025` via LiveKit `RealtimeModel`. Persistent WebSocket. Audio streams in continuously via `session.push_audio(rtc.AudioFrame)`. Reactions triggered via `session.generate_reply(instructions=prompt)`.
- **Session model:** One persistent session per run. Reconnects are not implemented (relies on LiveKit stability).
- **Audio to Gemini:** Streaming 48kHz frames pushed from sounddevice callback in real time
- **Vision:** Screen JPEG pushed to session via `session.push_video(rtc.VideoFrame)` ~1fps
- **Trigger detection:** `trigger_loop()` — more elaborate than v1: level bands, controller moves (significance filtered), BPM, band-shift detection, heartbeat
- **Response handler:** `on_gen` event listener on `session.on("generation_created")`
- **Entry point:** `main()` at line ~1670
### `cohost_v2.py` — Unified state architecture (latest)
- **Gemini strategy:** Same as lk: `gemini-2.5-flash-native-audio-preview-12-2025` via LiveKit `RealtimeModel`
- **Architecture improvement:** Single `MusicState` dataclass replaced scattered per-function state. `state_refresh_loop` @10Hz is the only writer. `EventDetector` reads diffs to emit typed `Event` objects. `AICoach` builds event-specific prompts.
- **Controller:** DDJ-FLX4 MIDI decode shared with lk (same `ControllerState`, `_CC_MAP`, `_NOTE_MAP`)
- **Track confidence:** `derive_audible_track()` cross-references nowplaying-cli with MIDI deck weights; emits `(unsure)` tag when confidence < 0.6, `unknown` when not determinable
- **Entry point:** `main()` at line ~1605
### `cohost.streaming.py.bak` — Archived streaming prototype
- Oldest version. Used `gemini-3.1-flash-live-preview` with Gemini Live API directly (no LiveKit). Audio streamed via `session.send_client_content`. Abandoned due to 1007/1008 errors and `mutable_chat_context=False` on Gemini 3.1 (blocking generate_reply pattern).
## Key Architectural Patterns
### Pattern: Event-gated inference
```python
```
### Pattern: Feedback suppression (mic gating)
### Pattern: Audio evidence grounding
```python
```
### Pattern: Thread/async boundary
```python
```
## Data Flow
### Primary Reaction Path (cohost.py)
### Primary Reaction Path (cohost_v2.py)
### Mascot Frontend Path
### Recording Path (runs continuously, all turns)
- Every PCM chunk from BlackHole → `VoiceRecorder.push_input()` → `input.wav`
- Every PCM chunk from Gemini reply → `VoiceRecorder.push_voice()` → `voice.wav`
- Every trigger/AI text/error → `VoiceRecorder.log_event()` → `events.jsonl` (JSONL, timestamped from session start)
## Layers
- Purpose: Convert physical audio signals to Python buffers
- Implemented via: `sounddevice` callbacks (real-time thread)
- Key path: `start_input_stream()` / `start_input_to_session()`
- Outputs: `AudioBuffer`, `MicBuffer`, `PassthroughBuffer`, `Levels`
- Purpose: Extract musical meaning from raw streams
- Runs on: asyncio tasks (non-real-time, offloaded to executor for CPU work)
- Key objects: `AudioBuffer.snapshot_features()`, `ScreenBuffer`, `TrackInfo`, `ControllerState`
- Note: `ControllerState` is updated from a `threading.Thread` (mido is blocking-only)
- Purpose: Unified, debounced musical state
- File: `cohost_v2.py`, class `MusicState` (~line 965)
- Writer: `state_refresh_loop()` @100ms — the ONLY writer
- Consumers: `EventDetector`, `coach_loop`, `AICoach`
- Purpose: Decide WHEN the AI should react
- v1/lk: procedural heuristics in `trigger_loop()`
- v2: `EventDetector.detect()` with typed events and per-type cooldowns
- Event types (v2): `TRACK_CHANGE`, `PHASE`, `LAYER_ARRIVAL`, `MIX_MOVE`, `HEARTBEAT`, `KAAN_SPOKE`, `MANUAL`
- Purpose: Generate text + audio reaction
- cohost.py: Two Gemini HTTP calls per turn (LLM → TTS cascade), stateless
- cohost_lk.py / v2: LiveKit `RealtimeModel` session, one persistent WebSocket, `generate_reply()`
- All: single in-flight generation enforced by `trigger_state["in_flight"]` flag
- Purpose: Deliver AI voice to headphones in real time
- `PlaybackQueue` → `sounddevice.RawOutputStream` @ 24kHz
- `Levels.update_voice()` tracks AI speech RMS (used by mic gate)
## Architectural Constraints
- **Threading model:** Two-thread hybrid. sounddevice callbacks run on OS audio thread. All asyncio logic (AI calls, WS, screen capture, state loops) runs on the Python event loop. MIDI listener runs on a third daemon thread (mido is blocking). Thread safety relies exclusively on `threading.Lock` in buffer classes — no async-safe queues between audio thread and event loop (direct lock-protected push is used instead).
- **Single in-flight generation:** All variants enforce at most one active Gemini generation at a time via `trigger_state["in_flight"]`. New triggers detected while in-flight are either queued (cohost.py) or dropped (cohost_lk.py, cohost_v2.py).
- **No retry/reconnect for Live API:** The LiveKit session is opened once in `main()`. If the session errors or drops, the program must be restarted. `cohost.py` implemented reconnect logic (it was the Live API variant before being refactored to stateless HTTP) but lk/v2 do not.
- **macOS-only dependencies:** `mss` (screen capture via CoreGraphics), `Quartz` (`CGWindowListCopyWindowInfo` for djay window crop), `nowplaying-cli` (MediaPlayer framework). Will not run on Linux/Windows without replacement.
- **Global state:** All state is held in objects allocated in `main()` and passed explicitly as arguments. No module-level mutable singletons except `_HAS_VISION`, `_HAS_WS`, `_HAS_QUARTZ` feature flags.
- **Circular imports:** None — each variant is a single file.
## Anti-Patterns
### Heuristic trigger leaking prompt framing
### Feature extraction in trigger callback
## Error Handling
- `try/except Exception as e: print(..., file=sys.stderr)` — used everywhere
- `finally: trigger_state["in_flight"] = False` — ensures new events can fire after any error
- Stale in-flight guard: if `in_flight` age > 12s, force-cleared on next tick
- `VoiceRecorder.log_event("session_error", ...)` / `"turn_error"` — errors captured in events.jsonl
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| frontend-enforcement | Project-local enforcement of vibemix frontend design standards. Loaded automatically by GSD agents that touch frontend code or UI design — frontend-design discipline, 20/80 rule, textured material feel, no AI slop. | `.claude/skills/frontend-enforcement/SKILL.md` |
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

## Commands

This repo is pre-package: no `pyproject.toml`, no lockfile, no test runner wired. Phase 1 of the roadmap is what introduces the unified `vibemix` package + lockfile.

**Run a POC variant** (each launches the mascot overlay first, then the Python script):

```bash
./run.sh       # cohost.py     — stateless HTTP cascade (Gemini 3 Flash + TTS)
./run_v2.sh    # cohost_v2.py  — LiveKit + MusicState (most evolved)
./run_lk.sh    # cohost_lk.py  — LiveKit + heuristic triggers
```

Each script does `source .venv/bin/activate && exec python3 <variant>.py`. The `.venv/` is Python 3.14; deps were installed ad-hoc via `pip install` (no `requirements.txt` — see CONCERNS.md).

**Smoke tests** (single-file, no runner — invoke directly):

```bash
python3 test_voice.py          # TTS round-trip
python3 _test_tts.py           # TTS API smoke test
python3 _test_multimodal.py    # multimodal LLM — edit hardcoded recording path at line 14 first
```

**Mascot overlay only** (no Python needed; the overlay is standalone HTML):

```bash
open "file://$(pwd)/mascot.html"
```

**Required environment:** `.env` at repo root with `GEMINI_API_KEY=...`. Read via `python-dotenv`.

**macOS prerequisites:** BlackHole 2ch (system audio driver, `brew install blackhole-2ch`), `nowplaying-cli` (`brew install nowplaying-cli`), djay Pro running as the audio source, Pioneer DDJ-FLX4 over USB (optional, graceful fallback).

## Planning Home

`.planning/` is the GSD source of truth — `ROADMAP.md`, `REQUIREMENTS.md`, `PROJECT.md`, `STATE.md`, plus `codebase/*.md` (codebase maps) and `research/*.md` (pre-roadmap research). The codebase maps in `.planning/codebase/` feed the GSD-managed sections of this file. The roadmap is 20 phases; v1 ships before Bravoh's public launch.

When a phase is active, its planning artifacts live under `.planning/phases/<NN>-<slug>/` (CONTEXT.md, RESEARCH.md, PLAN.md, etc.). Read those before touching code on that phase.

## POC = Reference, Devour It

`cohost.py`, `cohost_v2.py`, `cohost_lk.py`, and `cohost.streaming.py.bak` are **trusted intuition to port wholesale**, not legacy to preserve. Kaan iterated on them over real DJ sessions — the encoded decisions (mic gating, evidence-packet shape, event taxonomy, audible-deck heuristics, MIDI maps) are load-bearing IP. Phase 2-13 lift logic out of these into the new package shape.

Default canonical baseline = `cohost_v2.py` (most evolved: `MusicState` + `EventDetector` + audible-deck). Cherry-pick `cohost.py` for `TurnHistory` + the stateless `run_one_turn` cascade pattern. Cherry-pick `cohost_lk.py` for controller-aware triggers + band-shift detection. Tuning constants (e.g. `SILENT_RMS`, `MIC_HOLD_AFTER_AI_MS`, `MUSIC_GAIN_TO_GEMINI`, `MIN_EVENT_GAP_PER_TYPE`) diverge across variants — pick one when porting, document why, don't paper over.

Don't redesign primitives unless `.planning/codebase/CONCERNS.md` or `.planning/research/PITFALLS.md` flags a real bug (e.g., the `np.concatenate`-per-callback regression is genuine — pre-allocate the ring).

## UI Mocks

`mocks/` holds the design contracts referenced by UI phases — notably `vibemix-app-ui.html` (live session UI shape) and `vibemix-cinematic-storyboard.html` (hero demo storyboard). When working on Phases 11–14, treat these as the visual reference, lifted by the `frontend-enforcement` skill.
