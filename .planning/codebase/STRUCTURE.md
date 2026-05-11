# Codebase Structure

**Analysis Date:** 2026-05-11

## Directory Layout

```
dj-set-ai/
├── cohost.py               # Mainline v1 (47KB) — stateless Gemini HTTP cascade
├── cohost_lk.py            # LiveKit variant (81KB) — streaming Live API, more sensors
├── cohost_v2.py            # v2 unified-state (68KB) — MusicState + EventDetector
├── cohost.streaming.py.bak # Archived streaming prototype (34KB) — do not run
├── run.sh                  # Launch cohost.py + mascot.html
├── run_v2.sh               # Launch cohost_v2.py + mascot.html
├── run_lk.sh               # Launch cohost_lk.py + mascot.html
├── mascot.html             # Animated frontend sprite (standalone HTML)
├── sprite-1.png            # Bat mascot spritesheet — idle tier (2.3MB)
├── sprite-2.png            # Bat mascot spritesheet — mid energy tier (2.5MB)
├── sprite-3.png            # Bat mascot spritesheet — peak energy tier (2.3MB)
├── generate_bat.py         # Gemini image gen helper — regenerates sprite art
├── _test_multimodal.py     # Smoke test: sends recorded audio to Gemini, checks response
├── _test_tts.py            # Smoke test: TTS API call
├── test_voice.py           # Early voice test script
├── .env                    # GEMINI_API_KEY (not committed)
├── .gitignore
├── .venv/                  # Python 3.14 virtualenv (not committed)
├── __pycache__/            # Python bytecache for all three variants
├── recordings/             # Session recordings — one subdirectory per run
│   └── <YYYYMMDD-HHMMSS>/
│       ├── input.wav       # 16kHz mono int16 — what Gemini heard
│       ├── voice.wav       # 24kHz mono int16 — Gemini's reply
│       └── events.jsonl    # Session timeline (triggers, AI text, errors)
└── .planning/
    └── codebase/           # GSD codebase map documents
```

## Directory Purposes

**Root (source files):**
- Purpose: All source code lives at the project root — no subdirectories for source
- Contains: Three cohost variants, three launch scripts, frontend HTML + spritesheets, two test scripts, one utility script
- Key files: `cohost_v2.py` (newest), `cohost_lk.py` (most sensors), `cohost.py` (simplest/most reliable)

**`recordings/`:**
- Purpose: Automatic per-session recording for post-analysis and debugging
- Contains: One subdirectory per run, named `YYYYMMDD-HHMMSS` (e.g. `20260510-141722`)
- Each session: `input.wav` (what Gemini heard), `voice.wav` (Gemini's reply), `events.jsonl` (JSONL timeline)
- Generated: Yes — created at startup by `VoiceRecorder.__init__()`, writable at runtime
- Committed: No (should be in `.gitignore`)
- Note: Sessions accumulate; no automatic cleanup

**`.venv/`:**
- Purpose: Python 3.14 virtualenv with all dependencies
- Generated: Yes — `python -m venv .venv && pip install -r requirements.txt` (no requirements.txt present; deps installed manually)
- Committed: No

**`.planning/codebase/`:**
- Purpose: GSD codebase map documents consumed by planner/executor
- Committed: Yes

## Key File Locations

**Entry Points (all via `asyncio.run(main())`):**
- `cohost.py:1172` — `if __name__ == "__main__": asyncio.run(main())`
- `cohost_lk.py:1806` — same pattern
- `cohost_v2.py:1733` — same pattern

**Core Async Main Functions:**
- `cohost.py:1081` — `async def main()` — wires all buffers + streams + tasks
- `cohost_lk.py:1670` — `async def main()`
- `cohost_v2.py:1605` — `async def main()`

**Audio I/O:**
- `cohost.py:391` — `start_input_stream()` — sounddevice input callback (BlackHole)
- `cohost.py:479` — `start_passthrough_stream()` — djay→speakers passthrough output
- `cohost.py:508` — `start_playback_stream()` — AI voice 24kHz output
- `cohost_v2.py:821` — `start_input_to_session()` — pushes `rtc.AudioFrame` to LiveKit session
- `cohost_v2.py:783` — `start_passthrough_stream()` (same pattern as v1)
- `cohost_v2.py:806` — `start_playback_stream()` (same pattern as v1)

**LLM Call Sites:**
- `cohost.py:745` — `client.models.generate_content_stream()` (LLM, inside `run_one_turn()`)
- `cohost.py:753` — `client.models.generate_content_stream()` (TTS, inside `run_one_turn()`)
- `cohost_lk.py:1592` — `session.generate_reply(instructions=prompt)`
- `cohost_v2.py:1523` — `session.generate_reply(instructions=prompt)`

**Event/Trigger Detection:**
- `cohost.py:888` — `async def trigger_loop()` — RMS delta + mic + level-state heuristics
- `cohost_lk.py:1289` — `async def trigger_loop()` — same + band-shift, controller, heartbeat
- `cohost_v2.py:1125` — `class EventDetector` with `detect()` method
- `cohost_v2.py:1438` — `async def coach_loop()` — polls EventDetector @10Hz

**State Objects:**
- `cohost.py:151` — `class Levels`
- `cohost.py:187` — `class MicBuffer`
- `cohost.py:233` — `class AudioBuffer`
- `cohost.py:323` — `class ScreenBuffer`
- `cohost.py:366` — `class PlaybackQueue`
- `cohost.py:531` — `class VoiceRecorder`
- `cohost_v2.py:456` — `class TrackInfo`
- `cohost_v2.py:540` — `class ControllerState` (MIDI decode)
- `cohost_v2.py:965` — `@dataclass class MusicState` (v2 unified state)

**Prompt/System Instructions:**
- `cohost.py:82` — `SYSTEM_INSTRUCTION` — "drunk buddy in the booth" persona
- `cohost_lk.py:126` — `SYSTEM_INSTRUCTION` — "studio friend, free tek, honest feedback"
- `cohost_v2.py:120` — `SYSTEM_INSTRUCTION` — "latency-aware, past tense, Hard Tek / Acidcore"

**Frontend:**
- `mascot.html` — Self-contained HTML + JS, no build step. Opens as `file://` URL.
- `mascot.html:192` — `connect()` — WebSocket reconnect loop to `ws://127.0.0.1:8765`
- `mascot.html:99` — Sprite sheet definitions (3 tiers, 36 frames, 6 columns)

**Testing:**
- `_test_multimodal.py` — Hardcoded to `recordings/20260510-132307/input.wav`; sends 15s to `gemini-3-flash-preview`
- `_test_tts.py` — TTS smoke test
- `test_voice.py` — Early voice/TTS exploration

**Configuration:**
- `cohost.py:58-80` — Top-level constants (device names, SR, gains, thresholds)
- `cohost_lk.py:102-124` — Same layout
- `cohost_v2.py:70-113` — Same + event engine tuning constants

## Naming Conventions

**Files:**
- `cohost.py` — base name = purpose (co-host script)
- `cohost_<suffix>.py` — suffix encodes variant: `_lk` (LiveKit), `_v2` (version 2)
- `cohost.*.py.bak` — `.bak` suffix = archived/retired, do not run
- `_test_*.py` — leading underscore = dev-only test scripts, not part of the system
- `generate_*.py` — utility/generator scripts (one-shot tools)
- `run*.sh` — launch scripts named to match their target cohost variant
- `sprite-<N>.png` — numbered sprite sheets (energy tiers 1=idle, 2=mid, 3=peak)

**Functions:**
- `start_*_stream()` — functions that open and return a sounddevice stream
- `*_loop()` — async functions meant to run as asyncio tasks indefinitely
- `*_callback` — sounddevice audio thread callbacks (inner functions)
- `snapshot_*()` — non-destructive read of a buffer's current state
- `push()` / `pull()` — write/read for thread-safe buffer classes
- `find_device()` — device lookup helpers

**Classes:**
- PascalCase throughout: `Levels`, `AudioBuffer`, `MicBuffer`, `PlaybackQueue`, `VoiceRecorder`, `MusicState`, `EventDetector`, `AICoach`, `ControllerState`, `TrackInfo`

**Constants:**
- SCREAMING_SNAKE_CASE: `INPUT_SR_NATIVE`, `SILENT_RMS`, `HEARTBEAT_SEC`, `SYSTEM_INSTRUCTION`
- Grouped at top of file with `# ---- Category ----` comments

**Events (v2):**
- Typed string constants: `"TRACK_CHANGE"`, `"PHASE"`, `"LAYER_ARRIVAL"`, `"MIX_MOVE"`, `"HEARTBEAT"`, `"KAAN_SPOKE"`, `"MANUAL"`

**Event log kinds (events.jsonl):**
- snake_case: `"trigger"`, `"ai_text"`, `"turn_complete"`, `"session_error"`, `"tts_done"`, `"generation_created"`, `"event"`, `"session_start"`

## Where to Add New Code

**New trigger event type:**
- v2: Add to `MIN_EVENT_GAP_PER_TYPE` dict (`cohost_v2.py:105`), add detection branch in `EventDetector.detect()` (`cohost_v2.py:1143`), add task string in `AICoach.task_for_event()` (`cohost_v2.py:1288`)

**New audio feature:**
- Add to `AudioBuffer.snapshot_features()` in the relevant variant file (e.g. `cohost_v2.py:261`)
- Add to `AICoach.evidence_line()` output string (`cohost_v2.py:1237`) if it should reach the prompt

**New sensor / external signal:**
- Create a thread-safe class like `TrackInfo` or `ControllerState`
- Wire into `state_refresh_loop()` (`cohost_v2.py:1331`) as a new field on `MusicState`
- Start its polling task in `main()`

**New MIDI CC or note mapping (DDJ-FLX4):**
- `_CC_MAP` dict (`cohost_v2.py:504`) for continuous controls
- `_NOTE_MAP` dict (`cohost_v2.py:513`) for buttons/pads
- Add handling in `ControllerState.handle_msg()` (`cohost_v2.py:576`)

**New WebSocket message type (mascot → backend):**
- Add parsing in `ws_broadcast()` handler inner function (`cohost_v2.py:1560`)
- Currently only `{action: "trigger"}` is handled

**New recording field:**
- Add a `log_event()` call in `VoiceRecorder` (`cohost_v2.py:757`) or add a new WAV file in `VoiceRecorder.__init__()`

**New cohost variant:**
- Copy `cohost_v2.py` as the base (most complete)
- Name as `cohost_<descriptor>.py`
- Add corresponding `run_<descriptor>.sh`

## Special Directories

**`recordings/`:**
- Purpose: Runtime-generated session archives
- Generated: Yes, at every startup
- Committed: No (large WAV files)
- Contents: timestamped subdirs with `input.wav`, `voice.wav`, `events.jsonl`

**`__pycache__/`:**
- Purpose: Python bytecode cache for cohost.py, cohost_lk.py, cohost_v2.py
- Generated: Yes
- Committed: No

**`.venv/`:**
- Purpose: Isolated Python 3.14 environment
- Generated: Yes
- Committed: No
- Key packages present: `google-genai`, `livekit`, `livekit-agents`, `livekit-plugins-google`, `sounddevice`, `numpy`, `scipy`, `mido`, `websockets`, `mss`, `Pillow`, `pyobjc-framework-Quartz`, `python-dotenv`

---

*Structure analysis: 2026-05-11*
