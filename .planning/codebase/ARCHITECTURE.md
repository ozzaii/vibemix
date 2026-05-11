<!-- refreshed: 2026-05-11 -->
# Architecture

**Analysis Date:** 2026-05-11

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                         macOS Audio Layer                            │
│   djay Pro ──► BlackHole 2ch (virtual cable)    MacBook Pro Mic      │
└──────────────────┬───────────────────────────────────┬──────────────┘
                   │ 48kHz stereo float32              │ 48kHz mono float32
                   ▼                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       Audio Capture Layer                            │
│  sounddevice InputStream callback                                    │
│  → PassthroughBuffer (48k stereo, muted)                             │
│  → resample 48k→16k mono int16                                       │
│  → MicBuffer (gate: silent during AI talk)                           │
│  → AudioBuffer (rolling ring: 12-140s of 16k PCM)                   │
│  → Levels (smoothed EMA RMS: music / voice / mic)                    │
│  → VoiceRecorder.push_input() (disk: input.wav)                      │
└───────────────┬─────────────────────────────────────────────────────┘
                │
    ┌───────────┴──────────────────────────────────────────────────┐
    │                      Sensing Layer                            │
    │  AudioBuffer.snapshot_features()  → rms, bands, onsets, BPM  │
    │  ScreenBuffer (mss JPEG @1fps, djay Pro window crop)          │
    │  TrackInfo (nowplaying-cli poll @1Hz → track title)           │
    │  ControllerState (mido DDJ-FLX4 MIDI @USB → knob/fader/play) │
    └───────────┬──────────────────────────────────────────────────┘
                │
                ▼ (v2 only)
┌──────────────────────────────────────────────────────────────────────┐
│             MusicState  (single source of truth — v2)                │
│  state_refresh_loop @10Hz writes:                                    │
│    audible (debounced), rms, bands, onset_density, bpm,              │
│    phase (silent/low/groove/build/drop/peak/breakdown),              │
│    phase_history, energy_curve, long_arc,                            │
│    audible_deck (A/B/mix/none), deck_confidence,                     │
│    audible_track + confidence, track_history, recent_moves           │
└───────────┬──────────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     Event Detection Layer                             │
│                                                                       │
│  cohost.py     → trigger_loop() — heuristic thresholds on Levels     │
│  cohost_lk.py  → trigger_loop() — same + controller-aware events     │
│  cohost_v2.py  → EventDetector.detect() + coach_loop @10Hz           │
│                   event types: TRACK_CHANGE / PHASE / LAYER_ARRIVAL  │
│                                MIX_MOVE / HEARTBEAT / KAAN_SPOKE     │
└───────────┬──────────────────────────────────────────────────────────┘
            │ one event at a time (cooldown gated, in_flight locked)
            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        AI Inference Layer                             │
│                                                                       │
│  cohost.py:                                                           │
│    → run_one_turn(): Gemini 3 Flash multimodal (audio+JPEG+history)  │
│      → text reaction → Gemini 3.1 TTS → 24kHz PCM                   │
│                                                                       │
│  cohost_lk.py / cohost_v2.py:                                        │
│    → session.generate_reply(instructions=prompt)                     │
│      LiveKit RealtimeModel wraps Gemini 2.5 Flash Native Audio       │
│      (persistent WebSocket — audio in/out simultaneously)            │
└───────────┬──────────────────────────────────────────────────────────┘
            │ 24kHz mono int16 PCM chunks (streaming)
            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        Playback Layer                                 │
│  PlaybackQueue (thread-safe PCM ring)                                │
│  sounddevice RawOutputStream @24kHz → External Headphones            │
│  Levels.update_voice() → voice RMS used to gate mic input            │
│  VoiceRecorder.push_voice() → disk: voice.wav                        │
└──────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Frontend Bus (mascot.html)                      │
│  ws_broadcast() @30fps → ws://127.0.0.1:8765                         │
│  sends: {music, voice, [mic], [audible], [deck], [phase]}            │
│  mascot.html: canvas sprite animation reacts to music/voice RMS      │
│  v2 also receives: {action: "trigger"} for manual fire               │
└──────────────────────────────────────────────────────────────────────┘
            │
            ▼ (always)
┌──────────────────────────────────────────────────────────────────────┐
│                     Recording Layer (disk)                            │
│  recordings/<YYYYMMDD-HHMMSS>/                                       │
│    input.wav   — 16kHz mono int16 (music+mic mix sent to Gemini)     │
│    voice.wav   — 24kHz mono int16 (Gemini AI reply PCM)              │
│    events.jsonl — session timeline: triggers, AI text, errors        │
└──────────────────────────────────────────────────────────────────────┘
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

Three active variants exist in the repo — they are not separate modules, each is a self-contained single-file program:

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
All variants follow: **sense → detect event → snapshot context → call AI → play audio**.
The AI is never called on a timer. Every call is gated by: (1) a detected audio/MIDI event, (2) no in-flight generation, (3) AI not currently speaking, (4) per-type cooldown elapsed.

```python
# Shared in-flight lock pattern (all variants)
trigger_state = {"in_flight": False, "in_flight_at": float}

# cohost.py / cohost_lk.py
if trigger_state.get("in_flight"):
    age = now - trigger_state.get("in_flight_at", 0)
    if age > 12.0:
        trigger_state["in_flight"] = False  # stale guard
    else:
        continue  # skip this tick
```

### Pattern: Feedback suppression (mic gating)
`MicBuffer._current_gain()` returns 0.0 when `Levels.voice > AI_TALK_THRESHOLD` or within `MIC_HOLD_AFTER_AI_MS` (350ms) after AI stops talking. This prevents Gemini's own voice output (coming through speakers/headphones) from leaking back into the mic and triggering spurious reactions.

### Pattern: Audio evidence grounding
Before every AI call, `AudioBuffer.snapshot_features()` extracts cheap numpy FFT features (rms, peak, band shares, onset density). These are serialized into the prompt as `[audio_evidence: ...]` or `hearing[...]` to prevent the model from hallucinating musical events that aren't in the signal.

```python
# cohost.py style
feat_line = f"[audio_evidence: rms={feats['rms']} ... sub={feats['sub_bass_share']} ...]"
framed_prompt = f"[last {audio_secs:.0f}s of audio + screen]\n{feat_line}\n{prompt}"
```

### Pattern: Thread/async boundary
Audio capture (sounddevice callbacks) runs on sounddevice's real-time thread. All Python logic including AI calls runs on the asyncio event loop. The bridge is `threading.Lock`-protected buffer classes (`push`/`pull` methods) that are safe to call from either side.

```python
# Sounddevice callback (real-time thread) → pushes to thread-safe ring
def callback(indata, frames, time_info, status):
    audio_buf.push(pcm16)        # lock-protected push
    levels.update_music(pcm16)   # lock-protected EMA update
```

## Data Flow

### Primary Reaction Path (cohost.py)

1. sounddevice callback fires at ~5ms intervals → `start_input_stream()` (`cohost.py:391`)
2. Resample 48k→16k, push to `AudioBuffer` and `Levels`
3. `trigger_loop()` polls `Levels` @200ms (`cohost.py:888`)
4. On event detected, calls `run_one_turn()` (`cohost.py:674`)
5. `run_one_turn()` snapshots `AudioBuffer.snapshot_bytes()` + `ScreenBuffer.latest()`
6. Calls `client.models.generate_content_stream()` (LLM) → streams text
7. Calls `client.models.generate_content_stream()` (TTS) with text → streams PCM
8. PCM chunks pushed to `PlaybackQueue` as they arrive
9. sounddevice output callback drains `PlaybackQueue` → headphones

### Primary Reaction Path (cohost_v2.py)

1. sounddevice callback → `start_input_to_session()` — pushes `rtc.AudioFrame` to LiveKit session (`cohost_v2.py:821`)
2. `state_refresh_loop()` @100ms reads `AudioBuffer` features + MIDI + track → writes `MusicState` (`cohost_v2.py:1331`)
3. `coach_loop()` @100ms calls `EventDetector.detect(state)` (`cohost_v2.py:1438`)
4. On event: `AICoach.build_prompt(ev)` assembles evidence+task string (`cohost_v2.py:1320`)
5. `session.generate_reply(instructions=prompt)` fires async (`cohost_v2.py:1523`)
6. `on_gen` event handler fires → `consume_response()` drains `msg.audio_stream` → `PlaybackQueue` (`cohost_v2.py:940`)
7. sounddevice output callback drains PCM → headphones

### Mascot Frontend Path

1. `ws_broadcast()` runs as asyncio task @30fps
2. Snapshots `Levels` (+ `MusicState` in v2) → JSON broadcast to all connected WebSocket clients
3. `mascot.html` JS receives `{music, voice}` → smoothed EMA → CSS vars `--music-scale`, `--voice-opacity`
4. Canvas renders 36-frame sprite at BPM-responsive FPS (14-30fps); glowing aura reacts to voice level

### Recording Path (runs continuously, all turns)

- Every PCM chunk from BlackHole → `VoiceRecorder.push_input()` → `input.wav`
- Every PCM chunk from Gemini reply → `VoiceRecorder.push_voice()` → `voice.wav`
- Every trigger/AI text/error → `VoiceRecorder.log_event()` → `events.jsonl` (JSONL, timestamped from session start)

## Layers

**Audio Capture Layer:**
- Purpose: Convert physical audio signals to Python buffers
- Implemented via: `sounddevice` callbacks (real-time thread)
- Key path: `start_input_stream()` / `start_input_to_session()`
- Outputs: `AudioBuffer`, `MicBuffer`, `PassthroughBuffer`, `Levels`

**Sensing Layer:**
- Purpose: Extract musical meaning from raw streams
- Runs on: asyncio tasks (non-real-time, offloaded to executor for CPU work)
- Key objects: `AudioBuffer.snapshot_features()`, `ScreenBuffer`, `TrackInfo`, `ControllerState`
- Note: `ControllerState` is updated from a `threading.Thread` (mido is blocking-only)

**State Layer (v2 only):**
- Purpose: Unified, debounced musical state
- File: `cohost_v2.py`, class `MusicState` (~line 965)
- Writer: `state_refresh_loop()` @100ms — the ONLY writer
- Consumers: `EventDetector`, `coach_loop`, `AICoach`

**Event Detection Layer:**
- Purpose: Decide WHEN the AI should react
- v1/lk: procedural heuristics in `trigger_loop()`
- v2: `EventDetector.detect()` with typed events and per-type cooldowns
- Event types (v2): `TRACK_CHANGE`, `PHASE`, `LAYER_ARRIVAL`, `MIX_MOVE`, `HEARTBEAT`, `KAAN_SPOKE`, `MANUAL`

**AI Inference Layer:**
- Purpose: Generate text + audio reaction
- cohost.py: Two Gemini HTTP calls per turn (LLM → TTS cascade), stateless
- cohost_lk.py / v2: LiveKit `RealtimeModel` session, one persistent WebSocket, `generate_reply()`
- All: single in-flight generation enforced by `trigger_state["in_flight"]` flag

**Playback Layer:**
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
**What happens (cohost.py old / cohost_lk.py):** The trigger tag (`LEVEL→peak`, `EVENT`, `MIC`) is passed into the prompt as a hint (`[react]`, `[Kaan just spoke. Reply to him.]`).
**Why it's wrong:** The model gets told what kind of event happened before it can listen, which biases it to confirm the trigger hypothesis even when the audio has moved on.
**Do this instead:** cohost_v2.py's `AICoach.task_for_event()` passes only the *task* for each event type (what to focus on), not the musical claim. The audio + evidence packet is the ground truth.

### Feature extraction in trigger callback
**What happens (cohost_lk.py trigger_loop ~line 1340):** `audio_buf.snapshot_features()` is called inline in the trigger polling loop, running FFT on every 0.5s tick.
**Why it's wrong:** FFT on a 5s window is ~5-10ms of CPU. Running it synchronously inside the asyncio event loop blocks the loop.
**Do this instead:** cohost_v2.py's `state_refresh_loop` runs this on a background async task; in cohost.py it's run at trigger-fire time only (lower frequency).

## Error Handling

**Strategy:** Print-and-continue. Errors in buffer pushes, screen capture, MIDI, and WS are caught individually and logged to stderr. Critical errors in the AI call path are propagated up to the trigger/coach loop where `trigger_state["in_flight"]` is reset in a `finally` block.

**Patterns:**
- `try/except Exception as e: print(..., file=sys.stderr)` — used everywhere
- `finally: trigger_state["in_flight"] = False` — ensures new events can fire after any error
- Stale in-flight guard: if `in_flight` age > 12s, force-cleared on next tick
- `VoiceRecorder.log_event("session_error", ...)` / `"turn_error"` — errors captured in events.jsonl

## Cross-Cutting Concerns

**Logging:** `print()` to stdout/stderr + `VoiceRecorder.log_event()` to `events.jsonl`. No structured logging framework. `diag_loop()` prints live RMS meters to stdout using `\r` overwrites.

**Validation:** None beyond `GEMINI_API_KEY` check at startup and device discovery assertions.

**Authentication:** `GEMINI_API_KEY` read from `.env` via `python-dotenv`. Passed directly to `genai.Client()` or `RealtimeModel()`.

---

*Architecture analysis: 2026-05-11*
