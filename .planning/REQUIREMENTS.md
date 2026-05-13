# vibemix — v1 Requirements

**Milestone:** v1 — Bravoh's first open-source release, marketing wedge ahead of Bravoh public launch.
**Generated:** 2026-05-11 from PROJECT.md + research/SUMMARY.md.
**Target ship:** ~3-4 weeks (before Bravoh public launch, ~early June 2026).

---

## v1 Requirements

### Architecture & AI Pipeline

- [x] **ARCH-01**: Consolidate three POC variants (`cohost.py` / `cohost_v2.py` / `cohost_lk.py`) into a single shipping `vibemix` Python package
- [ ] **ARCH-02**: `platform/` protocol firewall — no OS-specific imports leak past the abstraction boundary
- [ ] **ARCH-03**: LiveKit `AgentSession` cascade pipeline (`stt=None`, `vad=None`, `llm=google.LLM(...)`, `tts=google.beta.gemini_tts.TTS(...)`) replacing the POC's `RealtimeModel` path
- [ ] **ARCH-04**: `DJCoHostAgent(Agent)` with `llm_node()` override using Gemini 3 Flash multimodal (audio bytes + screen JPEG + history)
- [ ] **ARCH-05**: Gemini TTS streaming output via `livekit-plugins-google.beta.gemini_tts.TTS` chunked HTTP
- [ ] **ARCH-06**: Bundled local `livekit-server --dev` binary on `127.0.0.1:7880` as the audio room transport
- [x] **ARCH-07**: Pre-allocated audio ring buffer — no `np.concatenate` in the sounddevice callback (fixes the POC dropout regression) _(Phase 2 — 62413e9)_
- [ ] **ARCH-08**: All Gemini calls routed via FastAPI proxy on `api.altidus.world` — client never holds a raw Gemini key
- [ ] **ARCH-09**: Install-UUID JWT issued on first launch, stored in OS keychain (Keychain on macOS, CredLocker on Windows)
- [ ] **ARCH-10**: Per-IP + per-install-UUID rate limiting (slowapi + Redis): 60 rpm, 2000 rpd per UUID

### Audio I/O — Cross-Platform

- [x] **AUDIO-01**: macOS audio capture via `sounddevice` from system loopback (auto-detect BlackHole / virtual cable) _(Phase 2 — 62413e9)_
- [ ] **AUDIO-02**: Windows audio capture via `PyAudioWPatch` (WASAPI loopback) — no virtual-cable requirement on Windows
- [ ] **AUDIO-03**: Auto-detect master output device cross-platform (no hardcoded device names)
- [ ] **AUDIO-04**: Sample-rate sanity tone test (1kHz round-trip) at startup — catches BlackHole Sonoma half-rate bug
- [ ] **AUDIO-05**: Output destination picker — headphones (in-ear) vs speakers (mic disabled in speakers mode)
- [x] **AUDIO-06**: Master-output-only listening — headphone cue input is NOT consumed (intentional) _(Phase 2 — 62413e9)_
- [x] **AUDIO-07**: Mic gating during AI talk (mute mic while Avery speaks — port from POC) _(Phase 2 — 59fdb62)_
- [x] **AUDIO-08**: TTS playback at 24kHz to user-selected output (sounddevice cross-platform output) _(Phase 2 — 62413e9)_
- [x] **AUDIO-09**: Voice-aware mic resumption + buffer flush after AI finishes _(Phase 2 — 59fdb62)_

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

- [x] **UX-01**: Calibration wizard on first run — 3-step fast path: permissions → output device + sample-rate test → controller detect + smoke test
- [ ] **UX-02**: Voice picker — male / female + named character (Gemini TTS 30 prebuilt voices, curated to ~6 in-app)
- [ ] **UX-03**: Genre picker at session start — techno / house / D&B / disco / pop
- [ ] **UX-04**: Mode picker — Beginner / Intermediate / Pro
- [ ] **UX-05**: Interaction picker — Hype-man / Coach
- [ ] **UX-06**: Output destination picker — headphones / speakers (changes mic gating policy)
- [ ] **UX-07**: Push-to-mute / quick-disable hotkey (system-wide while app focused)
- [ ] **UX-08**: Live session UI — meters, phase tape, AI transcript, drop countdown, MIDI event ribbon (per the `mocks/vibemix-app-ui.html` design contract)
- [ ] **UX-09**: Settings panel — change voice / mode / genre / output mid-session (some settings require restart)
- [ ] **UX-10**: Settings — recording retention policy (default 7d, configurable)
- [x] **UX-11**: Status badges — LiveKit ok / Gemini ok / MIDI ok / screen ok (visible failure indicators)

### 3D Mascot Screen Overlay

- [ ] **MASCOT-01**: Single 3D rigged mascot character — Meshy-AI-generated GLB with biped skeleton + named animation clip library (~5-10 clips covering idle/dance/talk/react states), normalized via Blender MCP. NOT a multi-character pet system — one mascot, mood variation via animation pool swap.
- [ ] **MASCOT-02**: Superwhisper-style sticky floating overlay window — transparent background, always-on-top, **persistent across macOS Spaces / Windows virtual desktops**, drag-repositionable, resizable within bounds, click-through option toggleable in Settings. Separate Tauri window from main session UI; position persists across sessions.
- [ ] **MASCOT-03**: Three.js scene + `AnimationMixer.crossFadeTo` state machine — every state transition crossfades (200-400ms blend); no T-pose snaps, no hard cuts except explicit particle-masked mood swap.
- [ ] **MASCOT-04**: Beat-locked clip entry — when transitioning into idle/dance states, the new clip begins on bar boundary 1 using BPM + downbeat phase from `MusicState` (grounding stack). Talk/react states are interrupt-class and start immediately.
- [ ] **MASCOT-05**: AI event → animation state dispatch — `track_change`, `drop`, `ai_generating_reply`, `ai_reply_done`, `manual_fire`, `phase_change`, `mood_swap` all map to specific named clip transitions with documented priority order.
- [ ] **MASCOT-06**: Talk-state animation during AI TTS utterances — mascot plays `talk_loop` (or mood-specific equivalent) while `ai_generating_reply` is active; resumes prior idle/dance state on `ai_reply_done`.
- [ ] **MASCOT-07**: Mood state system — hype-man / teacher / coach moods hot-swap the active Gemini TTS voice + animation clip pool + prompt vocabulary on the same rig within 500ms; transition masked by particle/puff effect; default mood = hype-man.
- [ ] **MASCOT-08**: WS:8765 event bus subscription — mascot overlay window subscribes to vibemix's existing `levels` / `events` / `state` streams with <100ms AI-event-to-state-transition-start latency; reconnects on disconnect with 1s/2s/4s/8s backoff.
- [ ] **MASCOT-09**: Menu-bar / system-tray icon — macOS top-right menu bar (NSStatusItem) + Windows notification area icon. Persistent always-running entry point — left-click toggles mascot overlay visibility, right-click popover surfaces mood selector + mute + open session UI + settings + quit. Icon state communicates session status (idle / live / ai_thinking / error). Closing the main session UI does NOT quit — quit requires explicit tray menu action.

### Distribution & Installer

- [ ] **DIST-01**: PyInstaller `--onedir` build for both OSes (avoid `--onefile` Defender false-positives)
- [ ] **DIST-02**: macOS signed + notarized DMG via Apple Developer ID + `notarytool` + Hardened Runtime + entitlements
- [ ] **DIST-03**: Windows OV-signed MSI via SignPath Foundation (free OSS cert) + Inno Setup 6
- [ ] **DIST-04**: SignPath Foundation OSS application filed on day 1 of Phase 1 (3-week lead time)
- [x] **DIST-05**: Tauri 2.x desktop shell wrapping the Python sidecar (10× smaller than Electron)
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

### Polish — CDJ Whisper v5 UI Quality Phase

> **Visual contract baseline:** `mocks/vibemix-direction-final.html` (CDJ Whisper v5). Supersedes the prior FL-Studio retro-tactile direction (rejected as "too generic / no character"). v5 spec captured in `[[project_visual_direction_cdj_whisper]]` memory and `.planning/HANDOFF-cdj-whisper-v5-ui-migration.md`.

- [x] **POLISH-01**: Dedicated polish phase (NOT a final-week sweep) — explicit phase with critique → execute loop until the CDJ Whisper v5 contract passes on every surface
- [x] **POLISH-02**: Component-level audit removes the backward-compat shim — `--phosphor*`, `--brushed-*`, `--bezel-*`, `--col-mascot` aliases deleted from `tokens.css`; every component references v5 primitives (`--void-*`, `--glass-*`, `--silk-*`, `--amber*`, `--rave-*`, `--glow-*`) directly
- [x] **POLISH-03**: Mascot overlay window (Phase 13) renders inside the v5 chrome with the animated-border sweep applied to its frame; mood swap (hype-man / teacher / coach) visibly composes with the CDJ Whisper palette, not against it
- [x] **POLISH-04**: No FL-Studio tactile residue anywhere — no `--brushed-aluminum` / `--bezel` / skeuomorphic 3D bevel shadows; no Tailwind shadow-lg / rounded-2xl-p-6 cards; no Inter / no system-ui (Geist for chrome + Fraunces for headlines); no purple gradients on chrome (rave ambient washes are body-only)
- [x] **POLISH-05**: All copy passes the "no AI slop" filter (per `frontend-enforcement` skill) — and explicitly: "knob/fader physics", "brushed aluminum", "anodised charcoal", "retro-futurist hardware" microcopy purged from chrome + tooltips + transcripts
- [x] **POLISH-06**: `gsd-ui-checker` + `gsd-ui-auditor` runs between iterations with the CDJ Whisper baseline as visual reference; phase only completes when both pass on every surface (calibration wizard, live session UI, settings drawer, mascot overlay window, recording browser if it exists by then). Backdrop-filter perf verified on a non-dev machine (`blur(32px) saturate(140%)` fallback to `blur(16px)` documented if measured stutter)

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
- [x] **REC-05**: Recording browser UI — list past sessions, replay, delete
- [x] **REC-06**: Retention policy enforcement (default 7d, configurable in Settings)

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

*Populated by `gsd-roadmapper` 2026-05-11 — each v1 REQ-ID maps to exactly one phase.*

| REQ-ID | Phase | Notes |
|--------|-------|-------|
| ARCH-01 | Phase 1 | Consolidate 3 POC variants; canonical entry `python -m vibemix` (Tauri shell aspects in Phase 11). |
| ARCH-02 | Phase 1 | `platform/` protocol firewall. |
| ARCH-03 | Phase 4 | LiveKit cascade pivot. |
| ARCH-04 | Phase 4 | `DJCoHostAgent.llm_node()` multimodal override. |
| ARCH-05 | Phase 4 | Gemini TTS streaming via `beta.gemini_tts.TTS`. |
| ARCH-06 | Phase 4 | Bundled local `livekit-server --dev`. |
| ARCH-07 | Phase 2 | Pre-allocated ring buffer fixes POC dropout regression. |
| ARCH-08 | Phase 5 | FastAPI proxy on `api.altidus.world`. |
| ARCH-09 | Phase 5 | Install-UUID JWT in OS keychain. |
| ARCH-10 | Phase 5 | slowapi + Redis rate limiting. |
| AUDIO-01 | Phase 2 | macOS sounddevice loopback (with BlackHole auto-detect). |
| AUDIO-02 | Phase 7 | Windows WASAPI loopback via PyAudioWPatch. |
| AUDIO-03 | Phase 7 | Cross-platform master output auto-detect. |
| AUDIO-04 | Phase 7 | 1kHz sample-rate sanity test (catches Sonoma BlackHole bug). |
| AUDIO-05 | Phase 7 | Headphones/speakers picker + mic gating policy. |
| AUDIO-06 | Phase 2 | Master-output-only; no cue input. |
| AUDIO-07 | Phase 2 | Mic gating during AI talk (port from POC). |
| AUDIO-08 | Phase 2 | 24kHz TTS playback. |
| AUDIO-09 | Phase 2 | Voice-aware mic resumption + buffer flush. |
| SCREEN-01 | Phase 8 | macOS ScreenCaptureKit migration. |
| SCREEN-02 | Phase 7 | Windows mss + pywin32 enum. |
| SCREEN-03 | Phase 3 | Window-picker privacy gate (initial macOS path); Phase 11 adds Tauri UI. |
| SCREEN-04 | Phase 3 | 1Hz JPEG capture into Gemini multimodal. |
| SCREEN-05 | Phase 3 | macOS nowplaying-cli track metadata. |
| SCREEN-06 | Phase 7 | Windows GSMTC track title (defer to v1.1 if ergonomics block). |
| MIDI-01 | Phase 9 | mido + python-rtmidi + 2s hot-plug re-enum. |
| MIDI-02 | Phase 9 | Controller auto-detect via name matching. |
| MIDI-03 | Phase 9 | DDJ-FLX4 mapping (port from POC). |
| MIDI-04 | Phase 9 | DDJ-400. |
| MIDI-05 | Phase 9 | DDJ-FLX6. |
| MIDI-06 | Phase 9 | DDJ-FLX10. |
| MIDI-07 | Phase 9 | DDJ-1000. |
| MIDI-08 | Phase 9 | DDJ-SX3. |
| MIDI-09 | Phase 9 | XDJ-RX3. |
| MIDI-10 | Phase 9 | Numark Party Mix Live. |
| MIDI-11 | Phase 9 | Hercules Inpulse 300. |
| MIDI-12 | Phase 9 | Hercules Inpulse 500. |
| MIDI-13 | Phase 9 | Generic MIDI fallback + positional inference. |
| MIDI-14 | Phase 9 | Magnitude-aware EQ/fader delta events. |
| SENSE-01 | Phase 3 | `MusicState` 10Hz writer (port from POC). |
| SENSE-02 | Phase 3 | `EventDetector` 6-type taxonomy. |
| SENSE-03 | Phase 6 | Percentile-based phase detector. |
| SENSE-04 | Phase 6 | 5-genre profile JSON. |
| SENSE-05 | Phase 3 | Audible-deck detection (port from POC). |
| SENSE-06 | Phase 6 | Crest-factor compression detection. |
| SENSE-07 | Phase 6 | BPM half/double validation. |
| SENSE-08 | Phase 6 | Vocal-section detector (hard etiquette gate). |
| SENSE-09 | Phase 3 | Set-timeline awareness in evidence packet. |
| SENSE-10 | Phase 6 | Per-genre replay validation harness. |
| PROMPT-01 | Phase 10 | 6 prompt templates (skill × interaction matrix). |
| PROMPT-02 | Phase 10 | Describe-before-infer anchoring. |
| PROMPT-03 | Phase 10 | Negative-dictionary hard bans. |
| PROMPT-04 | Phase 10 | `TurnHistory` anti-repetition ring (port from POC). |
| PROMPT-05 | Phase 10 | `<silence/>` short-circuit token. |
| PROMPT-06 | Phase 10 | Past-tense framing. |
| PROMPT-07 | Phase 10 | Reaction throttle + cooldown + vocal-gate. |
| PROMPT-08 | Phase 10 | Coach scorecard (qualitative bands only). |
| UX-01 | Phase 11 | Calibration wizard (3-step) on first run. |
| UX-02 | Phase 10 | Voice picker (Gemini TTS curated to ~6). |
| UX-03 | Phase 6 | Genre picker (calibrates phase thresholds). |
| UX-04 | Phase 10 | Mode picker (Beginner/Intermediate/Pro). |
| UX-05 | Phase 10 | Interaction picker (Hype-man/Coach). |
| UX-06 | Phase 12 | Output destination picker (headphones/speakers). |
| UX-07 | Phase 12 | Push-to-mute hotkey. |
| UX-08 | Phase 12 | Live session UI (meters, phase tape, AI transcript, drop countdown, MIDI ribbon). |
| UX-09 | Phase 12 | Settings panel — mid-session changes. |
| UX-10 | Phase 12 | Recording retention policy in Settings (storage UX in Phase 15). |
| UX-11 | Phase 11 | Status badges (LiveKit/Gemini/MIDI/screen) — initial wiring in shell; Phase 12 surfaces them in live UI. |
| MASCOT-01 | Phase 13 | Single 3D rigged mascot GLB (Meshy-generated) with biped skeleton + named animation clip library. |
| MASCOT-02 | Phase 13 | Superwhisper-style sticky overlay — transparent, always-on-top, persists across Spaces/virtual desktops. |
| MASCOT-03 | Phase 13 | Three.js + `AnimationMixer.crossFadeTo` state machine (200-400ms blend, no T-pose snaps). |
| MASCOT-04 | Phase 13 | Beat-locked clip entry on bar boundary using BPM + downbeat from `MusicState`. |
| MASCOT-05 | Phase 13 | AI event → animation state dispatch (track_change / drop / ai_reply / manual_fire / phase_change / mood_swap). |
| MASCOT-06 | Phase 13 | Talk-state animation during AI TTS utterances. |
| MASCOT-07 | Phase 13 | Mood state system — voice + clip pool + vocab hot-swap on same rig. |
| MASCOT-08 | Phase 13 | WS:8765 event bus subscription with <100ms latency + reconnect backoff. |
| MASCOT-09 | Phase 13 | Menu-bar (macOS) / tray icon (Windows) — persistent entry point, click toggles overlay, popover quick controls. |
| DIST-01 | Phase 18 | PyInstaller `--onedir` (avoids `--onefile` AV false-positives). |
| DIST-02 | Phase 18 | macOS signed + notarized DMG. |
| DIST-03 | Phase 18 | Windows MSI via SignPath OSS cert + Inno Setup 6. |
| DIST-04 | Phase 1 | SignPath OSS application filed day 1 (3-week lead time). |
| DIST-05 | Phase 11 | Tauri 2.x shell wrapping Python sidecar. |
| DIST-06 | Phase 18 | Tauri auto-update with signed manifest. |
| DIST-07 | Phase 20 | Fresh-machine install rehearsal before release. |
| DIST-08 | Phase 20 | GitHub Actions CI matrix (macos-14 + windows-latest). |
| VERIFY-01 | Phase 16 | 30-session offline hallucination suite ≥95% grounded. |
| VERIFY-02 | Phase 17 | Hand-graded reaction reel ≥4.0 with zero 1-2 ratings. |
| VERIFY-03 | Phase 16 | 60-min soak test zero `session_error`. |
| VERIFY-04 | Phase 18 | Binary attack verification (`strings` + `pyinstxtractor` for `AIza`). |
| VERIFY-05 | Phase 16 | Per-genre phase-detection ≥85% F1. |
| VERIFY-06 | Phase 16 | Critique → execute → critique → execute loop per phase. |
| POLISH-01 | Phase 14 | Dedicated polish phase — critique → execute loop against CDJ Whisper v5 contract. |
| POLISH-02 | Phase 14 | Backward-compat shim removed; components reference v5 primitives (`--void-*` / `--glass-*` / `--silk-*` / `--amber*` / `--rave-*` / `--glow-*`) directly. |
| POLISH-03 | Phase 14 | Mascot overlay (Phase 13) composes with v5 chrome — animated-border sweep on its frame, mood swap visibly fits palette. |
| POLISH-04 | Phase 14 | Zero FL-Studio tactile residue + zero web-app residue (no bezels/brushed-metal, no Tailwind defaults, Geist + Fraunces only). |
| POLISH-05 | Phase 14 | All copy passes `frontend-enforcement` skill filter + FL-Studio vocabulary purged. |
| POLISH-06 | Phase 14 | `gsd-ui-checker` + `gsd-ui-auditor` green against CDJ Whisper baseline before phase completes; backdrop-filter perf verified on non-dev machine. |
| GH-01 | Phase 19 | Repo at `github.com/bravoh/vibemix`. |
| GH-02 | Phase 19 | README hero banner. |
| GH-03 | Phase 19 | Hero demo video/GIF. |
| GH-04 | Phase 19 | Install buttons + GIFs. |
| GH-05 | Phase 19 | Feature matrix table. |
| GH-06 | Phase 19 | Supported controllers grid. |
| GH-07 | Phase 19 | Screenshots gallery. |
| GH-08 | Phase 19 | Branded architecture diagram. |
| GH-09 | Phase 19 | FAQ (8-12 questions). |
| GH-10 | Phase 19 | Built-by-Bravoh footer → waitlist. |
| GH-11 | Phase 19 | Badges row. |
| GH-12 | Phase 19 | Custom OG/social-preview image. |
| GH-13 | Phase 19 | CONTRIBUTING.md + DCO. |
| GH-14 | Phase 19 | CODE_OF_CONDUCT/SECURITY/NOTICE/TRADEMARKS/Apache 2.0 LICENSE. |
| GH-15 | Phase 19 | Issue templates. |
| GH-16 | Phase 19 | Releases with hand-written changelogs. |
| GH-17 | Phase 19 | Repo description + topic tags. |
| GH-18 | Phase 19 | Repo hygiene scrub (no `.bak`, no `_test_*.py`, no `.env`, no large binaries). |
| REC-01 | Phase 15 | Per-session directory naming. |
| REC-02 | Phase 15 | `input.wav` 16kHz mono int16. |
| REC-03 | Phase 15 | `voice.wav` 24kHz mono int16. |
| REC-04 | Phase 15 | `events.jsonl` timeline. |
| REC-05 | Phase 15 | Recording browser UI. |
| REC-06 | Phase 15 | Retention policy enforcement. |

**Coverage:** 128 / 128 v1 requirements mapped. No orphans. No duplicates.

---
*Last updated: 2026-05-11 after roadmap synthesis (gsd-roadmapper traceability pass)*
