# External Integrations

**Analysis Date:** 2026-05-11

## APIs & External Services

**Google Gemini AI (primary AI provider):**
- Service: Google Gemini API (not Vertex AI — all calls use `genai.Client(api_key=...)` directly)
- Used in all three cohost variants
- Auth: `GEMINI_API_KEY` env var, sourced from `.env`
- SDK: `google-genai==2.0.1` (`from google import genai`, `from google.genai import types`)

  **Models in use:**
  - `gemini-3-flash-preview` — multimodal LLM (text + audio reasoning) in `cohost.py` line 58
  - `gemini-3.1-flash-tts-preview` — text-to-speech, 24kHz mono PCM output, voice `Achird` in `cohost.py` line 59
  - `gemini-3.1-flash-live-preview` — Live API (streaming audio), used in `test_voice.py`
  - `gemini-2.5-flash-native-audio-preview-12-2025` — Native audio Live API; used in `cohost_lk.py` line 103 and `cohost_v2.py` line 71 via `livekit.plugins.google.realtime.RealtimeModel`
  - `gemini-3.1-flash-image-preview` — Image generation in `generate_bat.py` line 31 (`response_modalities=["IMAGE"]`)
  - `gemini-3-flash-preview` — Multimodal audio reasoning smoke test in `_test_multimodal.py` line 29

  **API usage patterns:**
  - `cohost.py`: `client.aio.live.connect(model=..., config=LiveConnectConfig)` → streaming session; sends raw PCM via `session.send_client_content`, receives audio stream
  - `cohost_lk.py` / `cohost_v2.py`: `RealtimeModel(model=..., api_key=..., voice=VOICE)` via LiveKit agents layer; calls `session.generate_reply(instructions=...)` to trigger turns
  - `_test_tts.py`: `client.models.generate_content(model=TTS_MODEL, config=GenerateContentConfig(response_modalities=["AUDIO"]))` — synchronous TTS

**LiveKit (WebRTC/audio transport layer):**
- Service: LiveKit RTC (used as local audio frame transport layer — no LiveKit server/cloud required)
- SDK: `livekit==1.1.7`, `livekit-agents==1.5.8`, `livekit-api==1.1.0`, `livekit-plugins-google==1.5.8`
- Auth: No LiveKit server auth observed — used as pure local agent SDK wrapper
- Key import: `from livekit import rtc` for `rtc.AudioFrame` construction; `from livekit.agents import llm`; `from livekit.plugins.google.realtime import RealtimeModel`
- Used in: `cohost_lk.py` and `cohost_v2.py` only; `cohost.py` uses raw `google-genai` Live API directly

## Data Storage

**Databases:**
- None — no database, no ORM, no SQLite

**File Storage:**
- Local filesystem only
- Session recordings written to `recordings/<YYYYMMDD-HHMMSS>/` per session:
  - `voice.wav` — AI voice output PCM (24kHz mono int16)
  - `input.wav` — music input PCM (16kHz mono int16) — present in later sessions
  - `events.jsonl` — newline-delimited JSON event log per session turn
- Sprite images: `sprite-1.png`, `sprite-2.png`, `sprite-3.png` — static assets for mascot animation

**Caching:**
- None — no Redis, no in-memory cache layer beyond in-process rolling audio buffers

## Authentication & Identity

**Auth Provider:**
- None — single-user local app, no user auth
- Only credential: `GEMINI_API_KEY` in `.env` file

## Audio Hardware Integrations

**BlackHole 2ch (virtual audio driver):**
- macOS system-level virtual audio device (not a Python package)
- Receives djay Pro master output routed via macOS Multi-Output
- `cohost.py` / `cohost_lk.py` / `cohost_v2.py` open it as `INPUT_DEVICE = "BlackHole 2ch"` via `sounddevice`
- Audio at 48kHz stereo → downsampled to 16kHz mono before sending to Gemini

**Pioneer DDJ-FLX4 MIDI Controller:**
- Physical DJ controller connected via USB MIDI
- Polled via `mido` in a daemon thread (`midi_listener_thread` in `cohost_lk.py:884` and `cohost_v2.py:652`)
- Decodes CC/note messages to `ControllerState` (EQ knobs, faders, filter, play/cue, loop buttons)
- MIDI mapping: Pioneer DDJ-FLX4 spec (referenced in `cohost_lk.py:695`)
- Integration is optional — prints warning and continues if `mido` not available or no MIDI port found

**macOS Now Playing (MediaRemote):**
- Polls djay Pro's currently-loaded track title and duration
- Mechanism: subprocess call to `nowplaying-cli` Homebrew binary (`/opt/homebrew/bin/nowplaying-cli`)
- Called with `["nowplaying-cli", "get", "title", "duration"]` every 1 second in `track_poll_loop`
- `TrackInfo` class in `cohost_lk.py:622` and `cohost_v2.py:457` wraps this
- Gracefully fails if `nowplaying-cli` not installed

**macOS Quartz (window capture):**
- `pyobjc-framework-Quartz==12.1` — `CGWindowListCopyWindowInfo` to find djay Pro's window bounds
- Used to crop `mss` screenshots to just the djay Pro window before sending to Gemini
- Functions: `find_djay_window_bounds()` in `cohost_lk.py:66` and `cohost_v2.py:171`
- Optional (`_HAS_QUARTZ` guard); falls back to full-screen capture if not available

**Screen Capture (mss):**
- `mss==10.2.0` captures macOS display as PNG/PIL Image
- Cropped to djay Pro window bounds if Quartz available
- Resized before being encoded as inline_data `image/png` in Gemini multimodal prompt
- Optional (`_HAS_VISION` guard); used only in `cohost.py` and `cohost_lk.py` (not `cohost_v2.py`)

## Local WebSocket Bus (Mascot)

**Server:**
- `websockets==16.0` server bound to `ws://127.0.0.1:8765`
- Broadcasts `{music, voice, mic}` level JSON at ~30Hz from Python to browser
- Started in `cohost.py:1061`, `cohost_lk.py`, and `cohost_v2.py` if `_HAS_WS`

**Client:**
- `mascot.html` — vanilla JS `WebSocket('ws://127.0.0.1:8765')` in browser
- Drives bat sprite animation speed and glow effects from live audio levels
- Auto-reconnects every 1s on disconnect

## Monitoring & Observability

**Error Tracking:**
- None — no Sentry, no Datadog

**Logs:**
- `print()` to stdout/stderr only
- Per-session `events.jsonl` in `recordings/<session>/` for AI turn event logging

**OpenTelemetry:**
- `opentelemetry-*` packages installed (livekit-agents transitive dep) but not configured in any cohost script — effectively unused

## CI/CD & Deployment

**Hosting:**
- Local macOS machine only — no server, no container, no cloud deployment

**CI Pipeline:**
- None

## Environment Configuration

**Required env vars:**
- `GEMINI_API_KEY` — Google Gemini API key (only required secret; sourced from `.env`)

**Secrets location:**
- `.env` file at project root (55 bytes); loaded by `python-dotenv` via `load_dotenv()` at startup in all cohost scripts

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None — all external calls are outbound API requests to Google Gemini over HTTPS, no webhooks

---

*Integration audit: 2026-05-11*
