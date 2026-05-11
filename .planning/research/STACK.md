# Stack Research

**Domain:** Cross-platform real-time AI desktop app (audio + screen + MIDI + LLM/TTS streaming)
**Researched:** 2026-05-11
**Confidence:** HIGH (LiveKit pipeline pieces, Windows loopback, OSS code signing); MEDIUM (PyInstaller-on-livekit edge cases, ScreenCaptureKit migration timeline)

---

## TL;DR

Keep almost everything that's already running. Swap two things, add three.

- **Brain:** keep `livekit-agents` + `livekit-plugins-google`, but drop `realtime.RealtimeModel` (Native Audio) and assemble an `AgentSession` from `google.LLM` (Gemini 3 Flash) + `google.beta.gemini_tts.TTS` (Gemini TTS Flash). VAD off, STT off, audio fed via session APIs not via the STT path.
- **Audio capture:** keep `sounddevice` on macOS, add **PyAudioWPatch** for Windows (sounddevice has no WASAPI loopback — upstream issue #281, never landed).
- **Screen capture:** add **`pyobjc-framework-ScreenCaptureKit`** on macOS (`CGWindowList` is obsoleted on macOS 15+), add **`mss`** on Windows for full-display + **`pywin32`** for window enumeration.
- **Packaging:** **PyInstaller** + **`create-dmg`** (macOS, notarized) + **Inno Setup 6** (Windows, signed). Briefcase and Nuitka rejected (rationale below).
- **API-key protection:** **FastAPI proxy on the existing Bravoh API host (`api.altidus.world`)** with **`slowapi` + Redis token-bucket** per-IP + per-install-UUID. Gemini key stays server-side; client ships only its install UUID, never the Google key.
- **Code signing:** Apple Developer ID (existing) + **SignPath Foundation** (free OV cert for OSS — vibemix qualifies).
- **CUA:** **REJECT.** Wrong abstraction (sandbox/VM-oriented), no MIDI, no audio capture. Adds dependency surface without solving a vibemix problem.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | **3.12.x** | Runtime | Drop from 3.14 → 3.12. PyInstaller, PyAudioWPatch wheels, and notarization tooling all have mature 3.12 support; 3.14 wheels exist but lag for some C-extension deps (still hitting source-build paths on Windows). 3.12 is the safest "shipping" floor for cross-platform binaries in mid-2026. Verified via PyPI wheel availability for all required packages. Confidence: HIGH |
| `livekit-agents` | **1.5.8** (released 2026-05-05) | Voice agent framework — rooms, sessions, audio bus, lifecycle | Already in use. The `AgentSession` cascade pattern (`stt` + `llm` + `tts` constructor args) is exactly the shape we need to swap the brain from Native Audio to Flash+TTS while keeping all the room/track/streaming plumbing. Apache-2.0. Python 3.10-3.14 supported. Verified via PyPI page and GitHub. Confidence: HIGH |
| `livekit` | **1.1.7** | RTC client (`rtc.AudioFrame`, `rtc.VideoFrame`) | Already in use, transitive of `livekit-agents`. No change. Confidence: HIGH |
| `livekit-plugins-google` | **1.5.8** | Gemini bindings for AgentSession | Exports `LLM` (Gemini cascade), `TTS` (Google Cloud TTS — **not what we want**), `STT` (Chirp), `realtime.RealtimeModel` (Native Audio — what we're moving away from), and **`beta.gemini_tts.TTS`** which is the Gemini 3 TTS class we actually want. Source confirmed at `livekit-plugins-google/livekit/plugins/google/beta/gemini_tts.py`. 30 prebuilt voices including `Achird` (current default), `Kore`, `Puck`, etc. 24 kHz mono PCM output. Confidence: HIGH |
| `google-genai` | **2.0.1** (released 2026-05-09) | Direct Gemini SDK (auth, models.generate_content, streaming) | Already a transitive dep of `livekit-plugins-google`, also used directly for the proxy-backend half (where Gemini calls actually originate after the rate-limit gate). Python 3.10+. Confidence: HIGH |

### Supporting Libraries

#### Audio Capture (the cross-platform split)

| Library | Version | Platform | Purpose | When to Use |
|---------|---------|----------|---------|-------------|
| `sounddevice` | **0.5.5** (released 2026-01-23) | macOS, Windows output | Input capture on macOS via BlackHole; output stream (PCM playback to headphones/speakers) on both OSes | Already in use. CoreAudio backend is rock-solid. Keep for macOS input + cross-platform output. **Does NOT support WASAPI loopback** (upstream issue #281 open since 2020, never resolved — confirmed via GitHub). Confidence: HIGH |
| `PyAudioWPatch` | **0.2.12.8** (released 2026-01-14) | Windows input ONLY | WASAPI loopback capture from speakers/master output | The Windows answer to BlackHole. PortAudio fork with `get_default_wasapi_loopback()` and `get_wasapi_loopback_analogue_by_index()` — captures the system default playback device as an input. No virtual audio cable required, no user driver install. Wheels for Python 3.7-3.14 on Windows. Confidence: HIGH |
| `numpy` | **2.4.4** | both | Audio math (RMS, FFT, bands, BPM autocorr) | Already in use. PyInstaller 6.14+ has solid numpy 2.x hooks. Confidence: HIGH |
| `scipy` | **1.17.1** | both | `signal.resample_poly` for 48k→16k | Already in use. PyInstaller bundles scipy with known-fragile hidden imports; document the `--collect-submodules scipy` PyInstaller flag explicitly. Confidence: HIGH |

#### Screen Capture (also cross-platform split)

| Library | Version | Platform | Purpose | When to Use |
|---------|---------|----------|---------|-------------|
| `pyobjc-framework-ScreenCaptureKit` | **12.1** (released 2025-11-14) | macOS | Modern screen + window capture, replaces Quartz CGWindowList | **CGWindowListCreateImageFromArray was obsoleted in macOS 15.0** — Quartz path is on borrowed time. ScreenCaptureKit is Apple's forward-compatible replacement (also handles per-app capture and system audio capture in one API surface). Callback-based, more complex than `mss`, but mandatory for macOS 15+ longevity. Python 3.10-3.15 supported. Confidence: HIGH |
| `pyobjc-framework-Quartz` | **12.1** | macOS | Window enumeration (`CGWindowListCopyWindowInfo`) | Keep for window picker enumeration (still works on macOS 15, just `CreateImageFromArray` is gone). For the actual screen *capture* operation, use ScreenCaptureKit. Confidence: HIGH |
| `mss` | **10.2.0** | macOS + Windows | Fast full-display capture fallback | Already in use on mac. On Windows, `mss` gives us full-display capture via Desktop Duplication API. Use as the Windows screen-capture path; window-cropping comes from pywin32. Confidence: HIGH |
| `pywin32` | **308+** | Windows | Window enumeration (`EnumWindows`, `GetWindowRect`, `GetWindowText`) | Windows equivalent of `CGWindowListCopyWindowInfo` — enumerate running app windows for the picker UI, get window bounds for cropping the `mss` screenshot to the DJ-app window. Standard, MIT, ships with Anaconda. Confidence: HIGH |
| `pillow` | **12.2.0** | both | Image resize + JPEG encode before sending to Gemini | Already in use. No change. Confidence: HIGH |

#### MIDI (one library, both OSes)

| Library | Version | Platform | Purpose | When to Use |
|---------|---------|----------|---------|-------------|
| `mido` | **1.3.3** | both | MIDI message parsing, port discovery | Already in use. Confidence: HIGH |
| `python-rtmidi` | **1.5.8** | both | RtMidi C++ backend for mido — CoreMIDI on mac, WinMM on Windows | Already in use. Cross-platform wheels (macOS arm64+x86_64, Windows). Confidence: HIGH |

#### "Now Playing" — track metadata

| Library | Version | Platform | Purpose | When to Use |
|---------|---------|----------|---------|-------------|
| `nowplaying-cli` (Homebrew binary) | latest | macOS only | MediaRemote poll for current track title/duration | Already in use, but **must be bundled in the macOS DMG** (not a runtime `brew install` dep — friction kills installs). Add it as a "Resources" file in the PyInstaller spec and call via subprocess against the bundled path. Confidence: HIGH |
| Windows `MediaSession` via `winrt-Windows.Media.Control` | **3.x** | Windows | Equivalent of MediaRemote — Windows 10/11 system media session API | Same role as `nowplaying-cli`. Pure-Python WinRT bindings. **Defer to v1.1 if it's a time sink** — the audible-deck detection from MIDI + audio is already the primary signal; track title is a nice-to-have. Mark optional. Confidence: MEDIUM (WinRT bindings work but ergonomics are clunky) |

#### LiveKit pipeline assembly

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `livekit.plugins.google.LLM` | bundled | Gemini 3 Flash via cascade `AgentSession` | The non-realtime Gemini LLM class. Model arg: `"gemini-3-flash-preview"` (or whatever the GA name is at ship time — currently named with version suffix in google-genai). Pass tool definitions for any function-calling needs. |
| `livekit.plugins.google.beta.gemini_tts.TTS` | bundled | Gemini TTS Flash streaming | 30 prebuilt voices, 24 kHz mono PCM. **Capability flag is `streaming=False`** — it's chunked-HTTP, not WebSocket-streaming. LiveKit wraps it in a `ChunkedStream` internally and the agent session handles playback. For our use case (reaction-driven, not turn-by-turn dialogue) this is *fine* — chunked playback latency is < 500ms. |
| `livekit.agents.AgentSession` | bundled | Wires LLM + TTS + room together, manages turn lifecycle | The cascade-mode constructor takes `llm=`, `tts=`, optional `stt=`, optional `vad=`. **Pass `stt=None` and `vad=None`** — we don't want LiveKit running STT on our music input. Trigger reactions with `session.generate_reply(instructions=...)` (the same call we already use with RealtimeModel). |

#### Async/HTTP/util (unchanged from current)

| Library | Version | Purpose |
|---------|---------|---------|
| `websockets` | **16.0** | Mascot WebSocket bus (localhost) |
| `aiohttp` | **3.13.5** | LiveKit transitive |
| `httpx` | **0.28.1** | google-genai transitive |
| `pydantic` | **2.13.4** | LiveKit transitive |
| `python-dotenv` | **1.2.2** | `.env` loading — dev only; production binary reads `APP_KEY` from OS keychain (mac) / DPAPI (Windows) |

### Distribution & Backend Infrastructure (NEW)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **PyInstaller** | **6.20.0** (stable as of 2026-05) | Build cross-platform executables (`.app` + `.exe`) | Mainstream choice, fastest build times, mature numpy/scipy hooks (6.14+), well-documented `--onedir` + code-signing flow for macOS notarization. Build-host-must-match-target — separate macOS and Windows GitHub Actions runners. |
| **create-dmg** | latest (npm/Homebrew) | Package signed `.app` into notarized DMG | Standard macOS-DMG generator. Works with notarytool (altool deprecated). Confidence: HIGH |
| **Inno Setup** | **6.x** | Windows installer | De facto Windows installer for Python projects. Free, scriptable, pre-installed on `windows-latest` GitHub Actions, supports code-signing via `SignTool` post-build hook. Smaller and simpler than NSIS for our needs. Confidence: HIGH |
| **Apple Developer ID** | $99/yr (Kaan already has) | macOS signing + notarization | Required for Gatekeeper non-block. notarytool (not altool — altool is deprecated). |
| **SignPath Foundation** | FREE for OSS | Windows code signing (OV cert) | **The answer to the Windows signing cost question.** SignPath Foundation grants free OV code-signing certificates to qualifying open-source projects. vibemix qualifies (MIT/Apache, GitHub-hosted, OSI-compatible). Avoids the $277-560/yr Sectigo/DigiCert EV cost in v1. EV ladder upgrade later if SmartScreen reputation needs a boost. Confidence: HIGH |
| **FastAPI** | **0.115.x+** | Bravoh-side Gemini proxy backend | Already the Bravoh backend's framework — reuse the same Python stack, same deployment pipeline (`api.altidus.world` / PM2). The proxy is a thin pass-through that injects the Gemini key server-side. |
| **`slowapi`** | **0.1.9+** | Token-bucket rate limiting decorator | Decorator-based rate limiter for FastAPI/Starlette. Combine with Redis storage backend (already deployed for Bravoh) for distributed enforcement across PM2 workers. Per-IP for the unauthenticated path, per-install-UUID once the client registers. Confidence: HIGH |
| **Redis** | **7.x** (already on the Bravoh box) | Rate-limit counters, install-UUID quota tracking | Reuse Bravoh's existing Redis. Confidence: HIGH |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` | Fast pip replacement, lockfile generation | Use `uv pip compile` to generate a `requirements.lock` per OS (mac arm64, mac x86_64, win64). Reproducible builds for the binary pipeline. |
| `pyproject.toml` + `setuptools` | Declarative project metadata | Replace the ad-hoc `.venv`-with-no-requirements current state. Even if we never publish to PyPI, this enables PyInstaller spec discovery and clean dep management. |
| `pre-commit` | Lint/format hooks | `ruff` + `ruff format` (replaces black + flake8). Standard 2026 Python tooling. |
| `ruff` | **0.7+** | Linter + formatter, single tool replaces flake8/isort/black |
| `pytest` | Tests | For the deterministic pieces (MIDI mapping, RMS extraction, prompt construction). Audio + LiveKit integration tested manually + in recordings. |
| GitHub Actions | CI: build + sign on each tag | Two matrix jobs (`macos-14` for Apple Silicon, `windows-latest` for x64). Notarization in macOS job, SignPath integration in Windows job (via their GitHub Action). |

---

## Architectural Patterns (the things downstream consumers actually need)

### Pattern 1 — LiveKit cascade pipeline (replaces RealtimeModel)

```python
from livekit.agents import AgentSession, Agent
from livekit.plugins import google
from livekit.plugins.google.beta import gemini_tts

session = AgentSession(
    stt=None,                                    # we don't STT music
    vad=None,                                    # we drive turns via event detector, not voice activity
    llm=google.LLM(
        model="gemini-3-flash-preview",          # multimodal, accepts our audio+screen evidence
        api_key=os.environ["GEMINI_KEY_PROXIED"],  # actually the proxy token, see API-key protection
    ),
    tts=gemini_tts.TTS(
        model="gemini-2.5-flash-preview-tts",    # 24kHz PCM, 30 voices
        voice_name="Achird",                     # or user-picked male/female default
        api_key=os.environ["GEMINI_KEY_PROXIED"],
    ),
)
# Audio input → session.input.audio.push_frame(rtc.AudioFrame(...))  (same as RealtimeModel)
# Event detector → session.generate_reply(instructions=prompt)        (same call signature)
# TTS PCM out → playback queue (existing PlaybackQueue class works as-is)
```

The migration from `cohost_v2.py` is shallower than it looks because both code paths already use `session.generate_reply(instructions=...)`. The replacement is the constructor, not the loop.

### Pattern 2 — Windows audio capture (the BlackHole replacement)

```python
import pyaudiowpatch as pyaudio

p = pyaudio.PyAudio()
loopback = p.get_default_wasapi_loopback()      # speaker → loopback input
stream = p.open(
    format=pyaudio.paInt16,
    channels=loopback["maxInputChannels"],       # usually 2
    rate=int(loopback["defaultSampleRate"]),
    input=True,
    input_device_index=loopback["index"],
    frames_per_buffer=512,
    stream_callback=on_audio,                    # same shape as sounddevice callback
)
```

The audio frame shape after this callback is identical to the sounddevice mac path, so `AudioBuffer.push()` etc. work unchanged. The platform abstraction lives in one file (`audio_capture.py`): on darwin use sounddevice, on win32 use pyaudiowpatch.

### Pattern 3 — API key protection (the architecture)

```
[vibemix client]
   │  POST /v1/gemini/generate { install_uuid, audio_b64, screen_b64, history, prompt }
   │  POST /v1/gemini/tts { install_uuid, text, voice }
   │  (Bearer: install-jwt-from-first-launch)
   ▼
[api.altidus.world (existing Bravoh FastAPI)]
   ├─ slowapi rate-limit: 60 req/min per install_uuid, 200 req/min per IP
   ├─ Redis quota: 1000 req/day per install_uuid (Gemini cost cap)
   ├─ inject GEMINI_API_KEY from server env
   ├─ proxy to google-genai
   └─ stream PCM/text back to client (chunked HTTP, no buffering)
   ▼
[Google Gemini API]
```

**Install-UUID flow:** on first launch, client POSTs `/v1/install` → server returns a JWT containing `install_uuid` (random UUIDv4) + signed expiry. Client stores in OS keychain (mac Keychain Access, Windows Credential Locker). Every subsequent request bears that JWT. No user account, no email, no friction — anonymity preserved while still giving us a unit to rate-limit.

**Why not just embed the key:** embedded keys *will* be extracted from the binary within hours of release (strings(1), reverse-engineering Discord, etc.). Once leaked, they're scraped and used for unrelated abuse, blowing the Gemini quota for everyone. The proxy pattern is the only architecturally honest answer.

**Libraries that implement this:** `fastapi` + `slowapi` (rate limiting) + `redis` (counters) + `pyjwt` (install JWTs) + `httpx` (proxy stream). All already in the Bravoh stack. Net new code: ~300 lines of FastAPI routes.

### Pattern 4 — Packaging (PyInstaller, two specs)

```
vibemix/
├── pyproject.toml
├── requirements.lock              # uv pip compile output
├── vibemix.spec.macos              # PyInstaller spec, --onedir, hidden imports for scipy/numpy/livekit
├── vibemix.spec.windows            # same shape, Windows-specific (no nowplaying-cli binary)
├── installer/
│   ├── create_dmg.sh              # create-dmg + notarytool + stapler
│   └── inno_setup.iss             # Inno Setup script, signs with SignPath
└── .github/workflows/release.yml  # macos-14 + windows-latest matrix on tag push
```

PyInstaller flags that *will* bite us if forgotten (document explicitly): `--collect-submodules scipy`, `--collect-all livekit`, `--collect-all livekit.plugins.google`, `--osx-bundle-identifier world.bravoh.vibemix`, `--codesign-identity "Developer ID Application: ..."`, `--osx-entitlements-file entitlements.plist` (must allow `com.apple.security.cs.allow-unsigned-executable-memory` for Python).

---

## Installation

```bash
# macOS development
brew install nowplaying-cli portaudio
python3.12 -m venv .venv
source .venv/bin/activate
uv pip install -e .                           # installs from pyproject.toml

# Windows development
# (PortAudio bundled by PyAudioWPatch wheel — no separate install)
py -3.12 -m venv .venv
.venv\Scripts\activate
uv pip install -e .

# Build (macOS)
pyinstaller vibemix.spec.macos
./installer/create_dmg.sh dist/vibemix.app

# Build (Windows)
pyinstaller vibemix.spec.windows
iscc installer/inno_setup.iss
```

### Core pyproject.toml dependencies

```toml
[project]
name = "vibemix"
requires-python = ">=3.12,<3.13"
dependencies = [
  "livekit-agents==1.5.8",
  "livekit==1.1.7",
  "livekit-plugins-google==1.5.8",
  "google-genai==2.0.1",
  "numpy==2.4.4",
  "scipy==1.17.1",
  "sounddevice==0.5.5",
  "mido==1.3.3",
  "python-rtmidi==1.5.8",
  "mss==10.2.0",
  "pillow==12.2.0",
  "websockets==16.0",
  "python-dotenv==1.2.2",
  "httpx==0.28.1",
  "pyjwt==2.10.1",
  "keyring==25.6.0",                          # OS-native secret storage (Keychain/CredLocker)
]

[project.optional-dependencies]
macos = [
  "pyobjc-framework-Quartz==12.1",
  "pyobjc-framework-ScreenCaptureKit==12.1",
]
windows = [
  "PyAudioWPatch==0.2.12.8",
  "pywin32>=308",
]
dev = [
  "pyinstaller==6.20.0",
  "ruff==0.7.4",
  "pytest==8.3.4",
  "uv==0.5.11",
]
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `livekit-plugins-google.beta.gemini_tts.TTS` | `livekit-plugins-google.TTS` (Google Cloud TTS) | Never for vibemix — Cloud TTS is a different product with different voices and we're committed to the Gemini-only stack. Cloud TTS is fine for boring IVR-style voice; loses the Gemini personality. |
| `livekit-plugins-google.LLM` (cascade) | `livekit-plugins-google.realtime.RealtimeModel` (Native Audio) | Already tried, already rejected — grounding is worse than explicit Flash + TTS per Kaan's testing. Code path stays in repo as opt-in. |
| `PyAudioWPatch` (Windows) | `SoundCard` (cross-platform) | SoundCard is genuinely cross-platform (one API for mac + win + linux) but its WASAPI loopback support is unofficial/best-effort. PyAudioWPatch is purpose-built for loopback. SoundCard would be the choice if we wanted *one* library for both OSes, but the macOS path is already battle-tested with sounddevice — splitting the abstraction at the OS line is simpler than rewriting the mac side. |
| `PyAudioWPatch` (Windows) | `ProcTap` (per-process WASAPI loopback) | ProcTap is newer and lets you capture audio from a *specific process* (rekordbox.exe) rather than the system master. Powerful but adds a moving target — version 0.4+ adds macOS, but cross-platform parity isn't stable enough for v1. Re-evaluate for v1.1 if "users hear their AI co-host through the AI co-host" feedback loops become an issue. |
| `PyInstaller` | `Briefcase` (BeeWare) | Briefcase produces nicer-looking native packages (real MSI, real `.app`, signed by default) — but it's optimized for GUI-toolkit-Python (Toga, etc.) and stumbles on heavy C-extension stacks like ours (livekit + scipy + numpy + pyobjc + portaudio). PyInstaller has known-good recipes for every one of these. Use Briefcase if vibemix ever has a real GUI in Toga; today there's no GUI, just a system-tray menu. |
| `PyInstaller` | `Nuitka` | Nuitka compiles Python to C — produces 2-4× faster startup and harder-to-reverse binaries. Two reasons not to: (1) build time grows 5-10×, killing iteration speed during the 3-week sprint; (2) Nuitka's hooks for the same numpy/scipy/livekit stack are *less* mature than PyInstaller's. Revisit post-launch if startup time becomes a complaint. |
| `Tauri + Python sidecar` | (full Electron + Python sidecar) | If/when vibemix grows a real settings GUI: Tauri (Rust shell, system webview, ~10MB) is the right call over Electron (~150MB). For v1 the UI is a tray-icon + native dialogs — no webview needed at all. |
| `Inno Setup` (Windows) | `NSIS` | Both work, both free. Inno Setup has cleaner Pascal-script and is pre-installed on `windows-latest` GH runners; NSIS scripts age into write-only territory. No technical difference at our scale. |
| `SignPath Foundation` (OSS cert) | Buy a commercial OV cert (Sectigo $277/yr, DigiCert $560/yr) | If SignPath rejects vibemix's application (unlikely — MIT/Apache, OSS, GitHub-hosted, real product, real maintainer). Or if we need EV (instant SmartScreen reputation) — but EV is overkill for v1. |
| FastAPI + slowapi proxy | API Gateway (Kong, Envoy, NGINX rate-limit-zone) | Gateway-level rate limit is more performant at scale but adds a moving piece. We're already running FastAPI on `api.altidus.world` for Bravoh — adding two routes is cheaper than introducing Kong. Migrate to gateway if vibemix gets out of hand (>10k DAU). |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `sounddevice` for Windows loopback capture | Upstream issue #281 has been open since 2020 — WASAPI loopback has never landed and isn't on the roadmap. Trying to use `WasapiSettings` for loopback will silently fail or capture mic instead. Confirmed via the spatialaudio/python-sounddevice repo. | `PyAudioWPatch` on Windows; keep sounddevice for macOS input + cross-platform output. |
| `Quartz.CGWindowListCreateImageFromArray` for screen capture on macOS 15+ | **Obsoleted in macOS 15.0** per Apple Developer Documentation. Will be removed in a future macOS. Apps shipping this in 2026 will break in 2027. | `pyobjc-framework-ScreenCaptureKit` for the capture; keep `Quartz.CGWindowListCopyWindowInfo` for window *enumeration* (still supported). |
| `altool` for macOS notarization | Deprecated. Apple migrated to `notarytool` (built into Xcode 13+). Several Apple Developer Forum threads from 2024-2026 confirm altool no longer accepts new submissions. | `xcrun notarytool submit ... --wait` then `xcrun stapler staple`. |
| Embedding `GEMINI_API_KEY` in the distributed binary | The string `AIza...` is grep-able. Within hours of release, scrapers will harvest it from binary releases on GitHub. Once leaked, the key gets used for unrelated abuse, Gemini suspends it, *all* vibemix users go offline. Non-negotiable. | FastAPI proxy on `api.altidus.world` with install-UUID JWT + per-UUID rate-limit. Key never leaves the server. |
| `RealtimeModel` (Gemini 2.5/3 Native Audio) as the default brain | Empirically worse grounding than the cascade in Kaan's testing on real DJ sets. Lower-level: Native Audio's persistent WebSocket pattern is harder to recover from when sessions drop mid-set. | `google.LLM` + `google.beta.gemini_tts.TTS` cascade. Keep RealtimeModel as a future opt-in toggle. |
| `python-dotenv` in production | `.env` files in distributed binaries leak secrets. Used only in dev. | OS keychain (mac Keychain via `keyring` package, Windows Credential Locker via same package) for the install JWT. No secrets stored in app bundle. |
| CUA (trycua/cua) | Wrong abstraction layer. CUA is sandbox/VM-oriented agent infrastructure (think: AI controlling a virtualized desktop for benchmark tasks). It does not solve our problems: no MIDI ingestion, no audio capture (it's screen + keyboard/mouse for UI automation), and its assumption of a virtualized environment is the opposite of what vibemix needs (raw access to the user's real audio/MIDI hardware). The `cua-driver` background-Mac-access piece is interesting but solves a problem we don't have. Tracking on the roadmap for "AI-controls-the-DJ-app" features (v2+), not for the listening co-host. | (nothing — direct OS APIs via `mido`, `sounddevice`, `ScreenCaptureKit` are the right shape) |
| `Briefcase` for v1 packaging | Less mature with heavy C-extension stacks (livekit, scipy, portaudio, pyobjc). 1-2 weeks of yak-shaving to get a working build. | `PyInstaller` + `create-dmg` + `Inno Setup`. Reconsider Briefcase if a GUI toolkit (Toga) gets added later. |
| `Nuitka` for v1 packaging | 5-10× longer build times kill iteration during the 3-week sprint. | `PyInstaller`. Revisit if startup time becomes a complaint post-launch. |
| `nowplaying-cli` as a runtime Homebrew dep | Adds an install step (`brew install nowplaying-cli`) that breaks the "one-click DMG" promise. | Bundle the `nowplaying-cli` binary as a Resources file inside the `.app` and call it via subprocess against the bundled path. |

---

## Stack Patterns by Variant

**If user is on macOS:**
- Audio in: `sounddevice` + BlackHole 2ch (or system loopback when ScreenCaptureKit-based audio capture is wired up — defer to v1.1; BlackHole works today)
- Screen capture: `pyobjc-framework-ScreenCaptureKit` (modern) with `Quartz.CGWindowListCopyWindowInfo` for window picker enumeration
- Track metadata: bundled `nowplaying-cli` binary via subprocess
- Packaging: PyInstaller `--onedir` → codesign with Apple Developer ID → create-dmg → notarytool → stapler
- Distribution: notarized DMG, downloaded from GitHub Releases

**If user is on Windows:**
- Audio in: `PyAudioWPatch` WASAPI loopback (auto-grabs default playback device — no driver install)
- Screen capture: `mss` (full-display) + `pywin32` (window enumeration + bounds for cropping)
- Track metadata: defer to v1.1 (WinRT MediaSession) OR skip entirely if MIDI+audio audible-deck detection is sufficient
- Packaging: PyInstaller `--onedir` → SignPath OV-cert signing → Inno Setup compile → SignPath sign installer
- Distribution: signed installer EXE on GitHub Releases

**If user runs Linux:**
- Out of scope. Document clearly in README.

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `livekit-agents==1.5.8` | `livekit-plugins-google==1.5.8` | Always match minor versions — LiveKit pins the plugin API across minor bumps. |
| `livekit-plugins-google==1.5.8` | `google-genai==2.0.1` | google-genai 2.x is the current major; livekit-plugins-google's `beta.gemini_tts` imports `from google.genai import Client, types`. |
| `numpy==2.4.4` | `scipy==1.17.1` | scipy 1.13+ supports numpy 2.x; older scipy will silently break on numpy 2 array protocol. |
| `numpy==2.4.4` | `PyInstaller==6.20.0` | PyInstaller 6.14+ has known-good numpy 2.x hooks; earlier versions hit `numpy.libs` missing-DLL on Windows. |
| `PyAudioWPatch==0.2.12.8` | Python 3.12 on Windows | Wheels available for 3.7-3.14; macOS not supported (Windows-only fork). |
| `sounddevice==0.5.5` | PortAudio 19.7+ | sounddevice wheels bundle PortAudio on Windows; on macOS, system PortAudio (via brew or bundled) is required. |
| `pyobjc-framework-ScreenCaptureKit==12.1` | macOS 12.3+ | ScreenCaptureKit was introduced in macOS 12.3. **Drop macOS 11 support** in README. |
| `livekit-agents` | Python 3.10-3.14 | We target 3.12. |
| `google-genai==2.0.1` | Python 3.10-3.14 | We target 3.12. |
| `mido==1.3.3` | `python-rtmidi==1.5.8` | rtmidi is the default and recommended mido backend. Both must be installed for cross-platform reliability. |

---

## Trade-offs Called Out

- **PyInstaller binary size** — vibemix bundle will land in the 150-250 MB range per platform (numpy + scipy + livekit + pyobjc/pywin32 are heavy). Acceptable for desktop, ugly compared to a Rust binary but standard for Python ML/audio apps. Mitigation: PyInstaller `--exclude-module` for unused submodules (e.g. `livekit.plugins.openai` if we don't import it). Probably trims 30-50 MB.
- **PyInstaller AV false positives** — `pyinstaller --onefile` binaries trigger heuristic AV detection. We use `--onedir` (the recommended mitigation) and rely on SignPath OV signing for SmartScreen trust. Some Avast/AVG installs will still complain in the first weeks until reputation builds. Documented gotcha.
- **GeminiTTS `streaming=False` capability** — Gemini TTS is currently chunked-HTTP not WebSocket-streaming. Latency is ~300-500ms per response. For DJ co-host (event-triggered, < 1/min reactions) this is well within "feels live". Would matter for a Siri-style turn-by-turn chatbot; doesn't matter here. If/when Google ships true streaming Gemini TTS via Live API, the cascade pattern accommodates a hot-swap.
- **macOS ScreenCaptureKit complexity** — Callback-based API (multiple nested `getShareableContentWithCompletionHandler` calls before you get a `CGImage`) is heavier than `mss`. Reference implementation gist exists (mr-linch on GitHub). Budget 1-2 days for the migration, vs. the alternative of shipping deprecated APIs that will break on macOS 16.
- **Windows screen capture without window cropping** — `mss` captures whole displays. `pywin32.EnumWindows` gets bounds; client-side crop in Pillow. Slight perf cost vs. native Direct3D window-level capture, irrelevant at 1 fps.
- **SignPath OSS application latency** — applications take 1-3 weeks to be reviewed. **Start the SignPath application TODAY** so it's approved by ship time, even if not used until then. Free fallback during the wait: ship unsigned with a documented SmartScreen warning, accept the user-trust hit for the first release wave.
- **Cross-compilation impossible** — PyInstaller can't build a Windows binary on a Mac. Need GitHub Actions matrix or a dedicated Windows machine. GitHub Actions `windows-latest` is free for OSS public repos — use it.
- **Bravoh proxy = single point of failure** — if `api.altidus.world` goes down, every vibemix client goes mute. Already protected by PM2 auto-restart + nginx upstream; add a status-page check on the client (`/v1/health`) so the app shows a clear "Bravoh services unreachable" state instead of cryptic timeouts.

---

## Sources

- [livekit-agents on PyPI](https://pypi.org/project/livekit-agents/) — version 1.5.8, released 2026-05-05, Python 3.10-3.14, Apache-2.0. **HIGH confidence.**
- [livekit-plugins-google on PyPI](https://pypi.org/project/livekit-plugins-google/) — version 1.5.8, released 2026-05-05. **HIGH confidence.**
- [livekit-plugins-google source `__init__.py`](https://github.com/livekit/agents/blob/main/livekit-plugins/livekit-plugins-google/livekit/plugins/google/__init__.py) — confirmed exports: `LLM`, `TTS`, `STT`, `realtime`, `beta`. **HIGH confidence.**
- [livekit-plugins-google `beta/gemini_tts.py` source](https://github.com/livekit/agents/blob/main/livekit-plugins/livekit-plugins-google/livekit/plugins/google/beta/gemini_tts.py) — full class signature, 30 voice names, 24kHz output, `streaming=False` capability. Read directly via GitHub raw API. **HIGH confidence.**
- [LiveKit Agents models overview](https://docs.livekit.io/agents/models/) — AgentSession cascade pattern (`stt`/`llm`/`tts` constructor args). **HIGH confidence.**
- [LiveKit Google AI integration page](https://docs.livekit.io/agents/integrations/google/) — confirms separate `google.LLM` and `google.TTS` classes. **HIGH confidence.**
- [google-genai on PyPI](https://pypi.org/project/google-genai/) — version 2.0.1, released 2026-05-09, Python 3.10-3.14. **HIGH confidence.**
- [PyAudioWPatch on PyPI](https://pypi.org/project/PyAudioWPatch/) — version 0.2.12.8, released 2026-01-14, Windows-only, Python 3.7-3.14, WASAPI loopback confirmed. **HIGH confidence.**
- [python-sounddevice issue #281](https://github.com/spatialaudio/python-sounddevice/issues/281) — confirms sounddevice does NOT support WASAPI loopback, open since 2020, no planned implementation. **HIGH confidence (negative claim verified against official upstream issue).**
- [sounddevice on PyPI](https://pypi.org/project/sounddevice/) — version 0.5.5, released 2026-01-23. **HIGH confidence.**
- [pyobjc-framework-ScreenCaptureKit on PyPI](https://pypi.org/project/pyobjc-framework-ScreenCaptureKit/) — version 12.1, released 2025-11-14, Python 3.10-3.15, macOS 10.15+ wheels (ScreenCaptureKit itself requires macOS 12.3+). **HIGH confidence.**
- [pyobjc issue #627: Quartz CGWindowListCreateImageFromArray obsoleted on macOS 15](https://github.com/ronaldoussoren/pyobjc/issues/627) — confirms the deprecation. **HIGH confidence.**
- [Apple ScreenCaptureKit documentation](https://developer.apple.com/documentation/screencapturekit/) — Apple's recommended replacement for CGWindowList. **HIGH confidence.**
- [mido docs — RtMidi backend](https://mido.readthedocs.io/en/latest/backends/rtmidi.html) — confirms python-rtmidi is the default/recommended mido backend, cross-platform via CoreMIDI/WinMM. **HIGH confidence.**
- [trycua/cua repo](https://github.com/trycua/cua) — confirms sandbox/VM orientation, no MIDI/audio support, MIT license, Python 3.11+ required. **HIGH confidence (read repo directly).**
- [SignPath Foundation for OSS](https://signpath.org/foundation) — free OV code signing for qualifying OSS projects. **MEDIUM confidence** (page was unreachable mid-research; cross-referenced through SignMyCode and developer community references — verify the application form when starting the v1 milestone).
- [PyInstaller stable docs](https://pyinstaller.org/en/stable/CHANGES.html) — version 6.20.0 stable, numpy 2.x + scipy hooks present from 6.14+. **HIGH confidence.**
- [Inno Setup official site](https://jrsoftware.org/isinfo.php) — free Windows installer, code-signing supported via SignTool. **HIGH confidence (training data + cross-referenced).**
- [Apple notarytool migration](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow) — altool deprecated, notarytool replaces it. **HIGH confidence.**
- [slowapi on GitHub](https://github.com/laurentS/slowapi) — FastAPI/Starlette rate limiter with Redis backend. **HIGH confidence.**
- [Tauri vs Electron in 2026](https://blog.nishikanta.in/tauri-vs-electron-the-complete-developers-guide-2026) — confirms Tauri's Python-sidecar viability if/when vibemix grows a real GUI. **MEDIUM confidence** (single source, but corroborated by official Tauri docs).
- [LiveKit custom TTS implementation (issue #1724)](https://github.com/livekit/agents/issues/1724) — confirms `TTSCapabilities(streaming=False)` + `ChunkedStream` pattern used by GeminiTTS, AWS Polly, Camb.ai. **HIGH confidence.**

---

*Stack research for: vibemix — cross-platform real-time AI DJ co-host*
*Researched: 2026-05-11*
