# Technology Stack

**Analysis Date:** 2026-05-11

## Languages

**Primary:**
- Python 3.14 - All application logic (cohost.py, cohost_v2.py, cohost_lk.py)

**Secondary:**
- JavaScript (vanilla, no framework) - Mascot overlay UI (`mascot.html`)
- HTML/CSS - Mascot overlay (`mascot.html`)

## Runtime

**Environment:**
- CPython 3.14 (confirmed via `.venv/lib/python3.14/`)
- macOS only — hard dependency on BlackHole virtual audio, macOS Now Playing API, optional Quartz window APIs

**Package Manager:**
- pip (no requirements.txt or pyproject.toml — dependencies installed directly into `.venv`)
- Lockfile: absent (no requirements.txt committed)
- Virtual env: `.venv/` at project root

## Frameworks

**Core:**
- `asyncio` (stdlib) - Async event loop driving all three cohost variants
- `livekit-agents==1.5.8` - Agent framework wrapping Gemini Live API for `cohost_lk.py` and `cohost_v2.py`
- `livekit==1.1.7` - LiveKit RTC client (`livekit.rtc.AudioFrame` for audio push)
- `livekit-plugins-google==1.5.8` - `livekit.plugins.google.realtime.RealtimeModel` — Gemini Live via LiveKit

**AI/LLM:**
- `google-genai==2.0.1` - Google Generative AI Python SDK (`from google import genai`, `from google.genai import types`)
- `google-cloud-speech==2.39.0` - Installed but not directly imported in main cohost files
- `google-cloud-texttospeech==2.36.0` - Installed but not directly imported in main cohost files
- `openai==2.36.0` - Installed as livekit-agents transitive dep; not used directly in cohost code

**Audio DSP:**
- `numpy==2.4.4` - All audio buffer math, RMS, FFT, onset detection, BPM estimation
- `scipy==1.17.1` - `scipy.signal.resample_poly` for 48kHz→16kHz downsampling
- `sounddevice==0.5.5` - macOS CoreAudio I/O: BlackHole input, headphones + speakers output
- `av==17.0.1` - Installed (livekit dep); handles media container codecs in LiveKit pipeline

**MIDI:**
- `mido==1.3.3` - MIDI message parsing for Pioneer DDJ-FLX4 controller input
- `python-rtmidi==1.5.8` - Low-level MIDI port access (mido backend)

**Screen Capture (optional):**
- `mss==10.2.0` - macOS screen capture (`import mss`) for djay Pro screen grabs
- `pillow==12.2.0` - PIL Image resize/crop before sending screenshot to Gemini
- `pyobjc-framework-Quartz==12.1` - `Quartz.CGWindowListCopyWindowInfo` to find and crop djay Pro window bounds

**Frontend (Mascot):**
- Vanilla JS with Canvas 2D API — no build step, no bundler, opened directly via `file://` URL
- WebSocket client at `ws://127.0.0.1:8765` — receives `{music, voice, mic}` levels at 30Hz

**Async/Networking:**
- `websockets==16.0` - WebSocket server (mascot bus) and used by LiveKit internals
- `aiohttp==3.13.5` - HTTP async client (livekit-agents dep)
- `httpx==0.28.1` - HTTP client (google-genai dep)

**Infrastructure/Utilities:**
- `python-dotenv==1.2.2` - `load_dotenv()` to source `GEMINI_API_KEY` from `.env`
- `pydantic==2.13.4` - Data validation (livekit-agents dep)
- `rich==15.0.0` - Terminal output formatting (livekit-agents dep)
- `opentelemetry-*` (1.39.1) - Observability stack installed as livekit-agents dep; not configured

**macOS-specific:**
- `pyobjc-core==12.1` - PyObjC bridge for macOS APIs
- `pyobjc-framework-Cocoa==12.1` - Cocoa framework bindings
- `pyobjc-framework-Quartz==12.1` - Quartz window listing
- `nowplaying-cli` (Homebrew binary at `/opt/homebrew/bin/nowplaying-cli`) - macOS MediaRemote polling for djay Pro track title/duration via `subprocess`

## Key Dependencies

**Critical:**
- `google-genai==2.0.1` - All Gemini API calls (Live/multimodal/TTS/image); the sole AI provider
- `livekit-agents==1.5.8` + `livekit-plugins-google==1.5.8` - Gemini 2.5 Native Audio via RealtimeModel (used in `cohost_lk.py` and `cohost_v2.py`)
- `sounddevice==0.5.5` - The entire audio I/O pipeline; without it nothing plays or records
- `mido==1.3.3` - DDJ-FLX4 MIDI controller input; optional but gracefully degrades

**Infrastructure:**
- `scipy==1.17.1` - Resampling; required for 48kHz→16kHz conversion
- `numpy==2.4.4` - All audio math; cannot run without it
- `websockets==16.0` - Mascot bus server; degrades gracefully if absent (`_HAS_WS` guard)
- `mss==10.2.0` + `pillow==12.2.0` - Screen capture; degrades gracefully (`_HAS_VISION` guard)
- `pyobjc-framework-Quartz==12.1` - djay window cropping; degrades gracefully (`_HAS_QUARTZ` guard)

## Configuration

**Environment:**
- Single `.env` file at project root (55 bytes — contains `GEMINI_API_KEY` only)
- Loaded via `load_dotenv()` at top of each cohost script
- Required env var: `GEMINI_API_KEY`
- No other env vars observed in code

**Build:**
- No build step; Python scripts run directly
- Run scripts: `run.sh` (cohost.py), `run_v2.sh` (cohost_v2.py), `run_lk.sh` (cohost_lk.py)
- Each script: `source .venv/bin/activate && exec python3 <script>.py`
- Mascot opened via `open file://$(pwd)/mascot.html` before starting the Python process

## Platform Requirements

**Development:**
- macOS only (BlackHole virtual audio driver, macOS MediaRemote via `nowplaying-cli`, CoreAudio via `sounddevice`, optional Quartz)
- BlackHole 2ch virtual audio driver (system-level install, not pip)
- djay Pro app running as audio source
- Pioneer DDJ-FLX4 MIDI controller (optional — graceful fallback)
- `nowplaying-cli` installed via Homebrew (`/opt/homebrew/bin/nowplaying-cli`)
- Python 3.14 in `.venv/`

**Production:**
- Single-machine local app — no server deployment, no network exposure
- All services run on localhost

---

*Stack analysis: 2026-05-11*
