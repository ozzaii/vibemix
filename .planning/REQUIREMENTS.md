# vibemix — v1 Requirements

**Milestone:** v1 — Bravoh's first open-source release, marketing wedge ahead of Bravoh public launch.
**Generated:** 2026-05-11 from PROJECT.md + research/SUMMARY.md.
**Target ship:** ~3-4 weeks (before Bravoh public launch, ~early June 2026).

---

## v1 Requirements

### Architecture & AI Pipeline

- [ ] **ARCH-01**: Consolidate three POC variants (`cohost.py` / `cohost_v2.py` / `cohost_lk.py`) into a single shipping `vibemix` Python package
- [ ] **ARCH-02**: `platform/` protocol firewall — no OS-specific imports leak past the abstraction boundary
- [ ] **ARCH-03**: LiveKit `AgentSession` cascade pipeline (`stt=None`, `vad=None`, `llm=google.LLM(...)`, `tts=google.beta.gemini_tts.TTS(...)`) replacing the POC's `RealtimeModel` path
- [ ] **ARCH-04**: `DJCoHostAgent(Agent)` with `llm_node()` override using Gemini 3 Flash multimodal (audio bytes + screen JPEG + history)
- [ ] **ARCH-05**: Gemini TTS streaming output via `livekit-plugins-google.beta.gemini_tts.TTS` chunked HTTP
- [ ] **ARCH-06**: Bundled local `livekit-server --dev` binary on `127.0.0.1:7880` as the audio room transport
- [ ] **ARCH-07**: Pre-allocated audio ring buffer — no `np.concatenate` in the sounddevice callback (fixes the POC dropout regression)
- [ ] **ARCH-08**: All Gemini calls routed via FastAPI proxy on `api.altidus.world` — client never holds a raw Gemini key
- [ ] **ARCH-09**: Install-UUID JWT issued on first launch, stored in OS keychain (Keychain on macOS, CredLocker on Windows)
- [ ] **ARCH-10**: Per-IP + per-install-UUID rate limiting (slowapi + Redis): 60 rpm, 2000 rpd per UUID

### Audio I/O — Cross-Platform

- [ ] **AUDIO-01**: macOS audio capture via `sounddevice` from system loopback (auto-detect BlackHole / virtual cable)
- [ ] **AUDIO-02**: Windows audio capture via `PyAudioWPatch` (WASAPI loopback) — no virtual-cable requirement on Windows
- [ ] **AUDIO-03**: Auto-detect master output device cross-platform (no hardcoded device names)
- [ ] **AUDIO-04**: Sample-rate sanity tone test (1kHz round-trip) at startup — catches BlackHole Sonoma half-rate bug
- [ ] **AUDIO-05**: Output destination picker — headphones (in-ear) vs speakers (mic disabled in speakers mode)
- [ ] **AUDIO-06**: Master-output-only listening — headphone cue input is NOT consumed (intentional)
- [ ] **AUDIO-07**: Mic gating during AI talk (mute mic while Avery speaks — port from POC)
- [ ] **AUDIO-08**: TTS playback at 24kHz to user-selected output (sounddevice cross-platform output)
- [ ] **AUDIO-09**: Voice-aware mic resumption + buffer flush after AI finishes

### Screen Capture & Track Detection

- [ ] **SCREEN-01**: macOS screen capture via `pyobjc-framework-ScreenCaptureKit` (replaces obsoleted Quartz `CGWindowListCreateImageFromArray`)
- [ ] **SCREEN-02**: Windows screen capture via `mss` + `pywin32` window enumeration
- [ ] **SCREEN-03**: Window picker UI — user selects their DJ-app window (no full-screen fallback, privacy gate)
- [ ] **SCREEN-04**: Cropped JPEG capture at 1 Hz, fed to Gemini multimodal
- [ ] **SCREEN-05**: macOS now-playing via `nowplaying-cli` subprocess (track title + duration)
- [ ] **SCREEN-06**: Windows now-playing via `winsdk` GSMTC — defer to v1.1 if ergonomics block; v1 ships without title metadata on Windows

### MIDI — Controller Library

- [ ] **MIDI-01**: `mido` + `python-rtmidi` MIDI ingest layer, hot-plug re-enumeration every 2s
- [ ] **MIDI-02**: Controller auto-detect via MIDI port name matching
- [ ] **MIDI-03**: Curated mapping — Pioneer DDJ-FLX4 (port from POC)
- [ ] **MIDI-04**: Curated mapping — Pioneer DDJ-400
- [ ] **MIDI-05**: Curated mapping — Pioneer DDJ-FLX6
- [ ] **MIDI-06**: Curated mapping — Pioneer DDJ-FLX10
- [ ] **MIDI-07**: Curated mapping — Pioneer DDJ-1000
- [ ] **MIDI-08**: Curated mapping — Pioneer DDJ-SX3
- [ ] **MIDI-09**: Curated mapping — Pioneer XDJ-RX3
- [ ] **MIDI-10**: Curated mapping — Numark Party Mix Live
- [ ] **MIDI-11**: Curated mapping — Hercules DJControl Inpulse 300
- [ ] **MIDI-12**: Curated mapping — Hercules DJControl Inpulse 500
- [ ] **MIDI-13**: Generic MIDI fallback with positional inference for unmapped controllers
- [ ] **MIDI-14**: Magnitude-aware EQ/fader event capture (delta semantic: "small high boost" vs "kill the lows")

### Sensing & Phase Detection

- [ ] **SENSE-01**: `MusicState` single-source-of-truth at 10 Hz (port from `cohost_v2.py`)
- [ ] **SENSE-02**: `EventDetector` event taxonomy (TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT / KAAN_SPOKE)
- [ ] **SENSE-03**: Percentile-based phase detector replacing absolute RMS thresholds (genre-agnostic)
- [ ] **SENSE-04**: Genre profile JSON for techno / house / D&B / disco / pop (BPM range, drop RMS, build duration, sub share)
- [ ] **SENSE-05**: Audible-deck detection (A / B / mix / none) — port from `cohost_v2.py`
- [ ] **SENSE-06**: Crest-factor compression detection (avoids inflating phase scores on heavily-mastered tracks)
- [ ] **SENSE-07**: BPM half/double validation window (avoids 70 vs 140 confusion)
- [ ] **SENSE-08**: Vocal-section detection — gates AI from talking over lyrics (hard etiquette gate)
- [ ] **SENSE-09**: Absolute set-timeline awareness ("you're at 2:44; drop hit at 2:33") encoded in evidence packet
- [ ] **SENSE-10**: Per-genre replay validation harness — 30-minute recorded sets for techno/house/D&B/disco/pop blind-tested

### User Modes & Prompting

- [ ] **PROMPT-01**: 6 prompt templates — Beginner × Hype-man, Beginner × Coach, Intermediate × Hype-man, Intermediate × Coach, Pro × Hype-man, Pro × Coach
- [ ] **PROMPT-02**: "Describe before infer" anchoring pattern in every template (model must echo the observed evidence before forming a reaction)
- [ ] **PROMPT-03**: Negative-dictionary hard bans — "amazing", "awesome", "great mix", "let me know", "delve", "leverage", "as an AI" (and ~30 more)
- [ ] **PROMPT-04**: Per-session anti-repetition ring (`TurnHistory` — port from POC) — model can't reuse the same opener twice in a session
- [ ] **PROMPT-05**: `<silence/>` short-circuit — model is given explicit permission to say nothing if no event warrants a reaction
- [ ] **PROMPT-06**: Past-tense framing in every template ("yo, that mix you just did" — never "you're doing", "you're about to")
- [ ] **PROMPT-07**: Reaction frequency throttle — per-event-type cooldown, max-rate cap, no-talking during vocals
- [ ] **PROMPT-08**: Coach scorecard at session end — qualitative bands only (never numeric "8.4/10")

### UX — Calibration, Pickers, Session UI

- [ ] **UX-01**: Calibration wizard on first run — 3-step fast path: permissions → output device + sample-rate test → controller detect + smoke test
- [ ] **UX-02**: Voice picker — male / female + named character (Gemini TTS 30 prebuilt voices, curated to ~6 in-app)
- [ ] **UX-03**: Genre picker at session start — techno / house / D&B / disco / pop
- [ ] **UX-04**: Mode picker — Beginner / Intermediate / Pro
- [ ] **UX-05**: Interaction picker — Hype-man / Coach
- [ ] **UX-06**: Output destination picker — headphones / speakers (changes mic gating policy)
- [ ] **UX-07**: Push-to-mute / quick-disable hotkey (system-wide while app focused)
- [ ] **UX-08**: Live session UI — meters, phase tape, AI transcript, drop countdown, MIDI event ribbon (per the `mocks/vibemix-app-ui.html` design contract)
- [ ] **UX-09**: Settings panel — change voice / mode / genre / output mid-session (some settings require restart)
- [ ] **UX-10**: Settings — recording retention policy (default 7d, configurable)
- [ ] **UX-11**: Status badges — LiveKit ok / Gemini ok / MIDI ok / screen ok (visible failure indicators)

### Reactive Mascot (Avery)

- [ ] **MASCOT-01**: Mascot SVG character with named pose vocabulary (idle / alert / speaking / squint / cover-ears / puff-up / wavy / lean-left / lean-right / punch-up / freeze / bounce / zipped / shocked / dancing / sleeping / winking)
- [ ] **MASCOT-02**: Idle animation — breathing, blinking, gentle sway, occasional ear-wiggle
- [ ] **MASCOT-03**: Reactive pose dispatching — MIDI events trigger named poses with magnitude-aware intensity
- [ ] **MASCOT-04**: Mouth animation synced to AI TTS audio level (mascot "speaks" with Avery)
- [ ] **MASCOT-05**: Eye-tracking — eyes follow the most-recent control the user touched (cross-modal feedback)
- [ ] **MASCOT-06**: Beat-sync subtle bounce on the kick (when phase = groove/peak/drop)
- [ ] **MASCOT-07**: Mascot in main session UI (corner placement, not blocking) + larger render in calibration wizard

### Distribution & Installer

- [ ] **DIST-01**: PyInstaller `--onedir` build for both OSes (avoid `--onefile` Defender false-positives)
- [ ] **DIST-02**: macOS signed + notarized DMG via Apple Developer ID + `notarytool` + Hardened Runtime + entitlements
- [ ] **DIST-03**: Windows OV-signed MSI via SignPath Foundation (free OSS cert) + Inno Setup 6
- [ ] **DIST-04**: SignPath Foundation OSS application filed on day 1 of Phase 1 (3-week lead time)
- [ ] **DIST-05**: Tauri 2.x desktop shell wrapping the Python sidecar (10× smaller than Electron)
- [ ] **DIST-06**: Auto-update via Tauri updater (signed manifest, opt-out in settings)
- [ ] **DIST-07**: Fresh-machine install tested on non-dev macOS + Windows before each release
- [ ] **DIST-08**: GitHub Actions CI matrix (macos-14 + windows-latest) building signed binaries on tag push

### Verification — Pre-Release Gates

- [ ] **VERIFY-01**: 30-session offline hallucination verification suite — replay recorded sets, score grounding ≥95% before any installer build
- [ ] **VERIFY-02**: Hand-graded "reaction reel" — 30 min varied DJing, blind-rated 1-5 by Kaan + Francesco + 2 DJ network friends; pass requires ≥4.0 average with zero 1-2 ratings
- [ ] **VERIFY-03**: 60-minute soak test passing zero `session_error` events
- [ ] **VERIFY-04**: Binary attack verification — `strings` + `pyinstxtractor` against final binary, zero `AIza`-pattern matches (key-leak gate)
- [ ] **VERIFY-05**: Per-genre phase-detection accuracy validation (≥85% event-timing F1 on the validation harness)
- [ ] **VERIFY-06**: Critique → execute → critique → execute loop per phase — every phase passes plan-check before execute and verifier after; UI phases run ui-checker between polish iterations

### Polish — FL-Studio UI Quality Phase

- [ ] **POLISH-01**: Dedicated polish phase (NOT a final-week sweep) — explicit phase with critique → execute loop until the bar passes
- [ ] **POLISH-02**: Knob/fader physics — momentum, detent feel, magnitude-mapped visual response (match pro-audio software hierarchy: FL Studio / Ableton / Bitwig / Native Instruments)
- [ ] **POLISH-03**: Mascot pose vocabulary visually refined to character-design-document quality (every pose deliberate, no procedural rigidity)
- [ ] **POLISH-04**: No "web app residue" anywhere — no default Tailwind shadows, no rounded-2xl-p-6 cards, no Inter, no purple gradients
- [ ] **POLISH-05**: All copy passes the "no AI slop" filter (per `frontend-enforcement` skill)
- [ ] **POLISH-06**: `gsd-ui-checker` + `gsd-ui-auditor` runs between iterations; phase only completes when both pass

### GitHub Launch Presence

- [ ] **GH-01**: Repo at `github.com/bravoh/vibemix` (GitHub Enterprise under bravoh org)
- [ ] **GH-02**: README with branded hero banner (custom artwork — wordmark + tagline + screenshot)
- [ ] **GH-03**: 30-45s hero demo video / GIF in README (per `mocks/vibemix-cinematic-storyboard.html`)
- [ ] **GH-04**: Install section — one-click download buttons for macOS + Windows, install GIFs, "from clone to running in <60s" promise
- [ ] **GH-05**: Feature matrix table — Beginner/Intermediate/Pro × Hype/Coach with example reactions
- [ ] **GH-06**: Supported controllers grid — 10 controller logos/photos + "calibrate any other" callout
- [ ] **GH-07**: Screenshots gallery — calibration wizard, mode picker, voice picker, in-session UI, recording browser
- [ ] **GH-08**: "How it works" architecture diagram (NOT default-Mermaid ugly — branded clean SVG)
- [ ] **GH-09**: FAQ — 8-12 questions (privacy, data, cost, Linux, why no Gemini Live, etc.)
- [ ] **GH-10**: "Built by Bravoh" footer linking to Bravoh waitlist (the funnel)
- [ ] **GH-11**: Badges row (build status, latest release, license, platform, stars)
- [ ] **GH-12**: Custom OG / social-preview image for X/Discord/Slack shares
- [ ] **GH-13**: CONTRIBUTING.md with DCO sign-off + controller-mapping contribution path + prompt-template contribution path
- [ ] **GH-14**: CODE_OF_CONDUCT.md, SECURITY.md, NOTICE, TRADEMARKS.md, Apache 2.0 LICENSE
- [ ] **GH-15**: Issue templates — bug / feature / new-controller-request
- [ ] **GH-16**: Releases page — every binary tagged with hand-written changelog
- [ ] **GH-17**: Repo description + topics tags (`dj`, `livekit`, `gemini`, `ai-assistant`, `audio`, `midi`, `pioneer-ddj`, `realtime-ai`)
- [ ] **GH-18**: No rough edges in public repo — no `_test_*.py` scratch files, no `.bak` files, no committed `.env`, no large binaries in tree

### Recording & Session Capture

- [ ] **REC-01**: Per-session directory `recordings/<YYYYMMDD-HHMMSS>/`
- [ ] **REC-02**: `input.wav` — 16kHz mono int16 (music + mic mix sent to Gemini)
- [ ] **REC-03**: `voice.wav` — 24kHz mono int16 (Gemini TTS PCM output)
- [ ] **REC-04**: `events.jsonl` — session timeline (triggers, AI text, errors, MIDI events)
- [ ] **REC-05**: Recording browser UI — list past sessions, replay, delete
- [ ] **REC-06**: Retention policy enforcement (default 7d, configurable in Settings)

---

## v2 / Deferred

- [ ] Highlight reel export (auto-generate shareable clips from recordings) — marketing-funnel multiplier
- [ ] Session replay UI with timeline scrubber
- [ ] "Coach this moment" manual trigger (user taps a button to ask Avery about the last 10s)
- [ ] Live mid-mix Coach nudges (Pro mode opt-in only)
- [ ] Windows now-playing via winsdk GSMTC (if `SCREEN-06` deferred)
- [ ] Additional controller mappings beyond the curated 10
- [ ] Track recommendation / library scanner ("pair this with X from your folder")
- [ ] Auto-detect genre (replaces manual picker — research-grade)
- [ ] Multi-language UI chrome (currently English only)

## Out of Scope

- **Gemini Live Native Audio modality** — grounding tested worse than Flash + TTS cascade; codepath stays in repo but not the shipping path
- **Headphone cue listening** — Gemini conflates cue with master, produces wrong reactions
- **User-supplied Gemini API keys** — friction kills virality; we eat the cost as marketing
- **DAW integration** (Logic / Ableton / FL Studio plugins) — "the next conquest", not v1
- **Mobile / iPad / iOS** — desktop only
- **Linux** — niche audience, triples platform-engineering cost
- **Custom voice cloning** — Gemini TTS prebuilt voices only
- **Real-time numeric set-score / leaderboard** — competitive gamification breaks the "DJ friend" frame
- **Twitch / YouTube live streaming integration** — record-for-later is enough for v1
- **Mascot.html (legacy POC overlay)** as a shipped UI surface — superseded by the in-app reactive mascot (MASCOT-01..07)
- **Auto-publish highlight clips** — manual review only (copyright safety)

---

## Traceability

*Populated by `gsd-roadmapper` — each REQ-ID gets mapped to its phase below.*

| REQ-ID | Phase | Notes |
|--------|-------|-------|
| (pending) | — | — |

---
*Last updated: 2026-05-11 after research synthesis*
