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

- [x] **DIST-01**: PyInstaller `--onedir` build for both OSes (avoid `--onefile` Defender false-positives)
- [x] **DIST-02**: macOS signed + notarized DMG via Apple Developer ID + `notarytool` + Hardened Runtime + entitlements
- [x] **DIST-03**: Windows OV-signed MSI via SignPath Foundation (free OSS cert) + Inno Setup 6
- [ ] **DIST-04**: SignPath Foundation OSS application filed on day 1 of Phase 1 (3-week lead time)
- [x] **DIST-05**: Tauri 2.x desktop shell wrapping the Python sidecar (10× smaller than Electron)
- [x] **DIST-06**: Auto-update via Tauri updater (signed manifest, opt-out in settings)
- [x] **DIST-07**: Fresh-machine install tested on non-dev macOS + Windows before each release
- [ ] **DIST-08**: GitHub Actions CI matrix (macos-14 + windows-latest) building signed binaries on tag push

### Verification — Pre-Release Gates

- [ ] **VERIFY-01**: 30-session offline hallucination verification suite — replay recorded sets, score grounding ≥95% before any installer build
- [ ] **VERIFY-02**: Hand-graded "reaction reel" — 30 min varied DJing, blind-rated 1-5 by Kaan + Francesco + 2 DJ network friends; pass requires ≥4.0 average with zero 1-2 ratings
- [ ] **VERIFY-03**: 60-minute soak test passing zero `session_error` events
- [x] **VERIFY-04**: Binary attack verification — `strings` + `pyinstxtractor` against final binary, zero `AIza`-pattern matches (key-leak gate)
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
- [x] **GH-17**: Repo description + topics tags (`dj`, `livekit`, `gemini`, `ai-assistant`, `audio`, `midi`, `pioneer-ddj`, `realtime-ai`)
- [x] **GH-18**: No rough edges in public repo — no `_test_*.py` scratch files, no `.bak` files, no committed `.env`, no large binaries in tree

### Recording & Session Capture

- [x] **REC-01**: Per-session directory `recordings/<YYYYMMDD-HHMMSS>/`
- [x] **REC-02**: `input.wav` — 16kHz mono int16 (music + mic mix sent to Gemini)
- [x] **REC-03**: `voice.wav` — 24kHz mono int16 (Gemini TTS PCM output)
- [x] **REC-04**: `events.jsonl` — session timeline (triggers, AI text, errors, MIDI events)
- [x] **REC-05**: Recording browser UI — list past sessions, replay, delete
- [x] **REC-06**: Retention policy enforcement (default 7d, configurable in Settings)

---

## v2.0 Research-Driven Ship Requirements

**Milestone:** v2.0 — Research-driven feature ship + absorbed v0.1.0 outstanding ship infrastructure.
**Generated:** 2026-05-14 from PROJECT.md v2.0 milestone + research/SUMMARY.md + 12 v2-bucket artifacts.
**Absorbs:** Outstanding v0.1.0 ship work (Phases 15-20 — recording browser, hallucination gate, sign+notarize, README, day-zero ops) folded into v2.0's 12-phase plan.

### Detection & Grounding — Generalized Event Detector

- [ ] **SENSE-11**: `GenreRouter` class — atomic detector-dict swap on `MusicState.active_genre` change without restarting session
- [ ] **SENSE-12**: 6 cross-genre event detectors landed in v2.0 core: `KICK_SWAP`, `SUB_LAYER_ARRIVAL`, `BREAKDOWN_KICK_KILL`, `REENTRY_KICK_LAND`, `KICK_DENSITY_SHIFT`, `PHRASE_BOUNDARY`
- [ ] **SENSE-13**: `MusicState` extended with `buildup_score`, `predicted_drop_in_sec`, `beat_phase`, `active_genre` fields (backward-compat defaults so Phase 3 golden equivalence holds)
- [ ] **SENSE-14**: `PHRASE_BOUNDARY` detector via band-limited (40-120Hz) autocorrelation locking downbeat phase, ±1 bar accuracy, self-corrects on `BREAKDOWN_KICK_KILL`
- [ ] **SENSE-15**: Per-genre detector dispatch architecture — `vibemix/events/genres/<genre>.py` registry + `_impl/` shared DSP primitives; baseline detectors byte-identical to v4 when no genre-specific detector fires
- [ ] **SENSE-16**: Reference-WAV tuning harness — `scripts/tune_detectors.py` plays curated tracks through detector chain + emits per-fire CSV for Kaan ear-audit

### Detection & Grounding — Evidence Registry + Citation Linter

- [x] **GROUND-01**: `EvidenceRegistry` — in-memory dict `(source, key) → list[t_session]`, written synchronously from `state_refresh_loop` and `EventDetector._fire`; SIBLING write-target alongside MusicState, never separate writer (Phase 18-01 + 18-02)
- [x] **GROUND-02**: Citation grammar (EBNF locked) — `[ev:<TYPE>@<t>]`, `[aud:<key>@<t>]`, `[midi:<event>@<t>]`, `[track:<id>]`, `[screen:<key>]`, `[mix:<derived>]`, `[tend:<profile-fact>]` + multi-citation `[ev:DROP@04:22; aud:peak_rms=0.91]` (Phase 18-01); citation_count telemetry per AI turn shipped (Phase 18-04)
- [x] **GROUND-03**: Citation grammar baked into Gemini system instruction (v1.0 prompt-only, no enforcement — corpus seeding) (Phase 18-03)
- [x] **GROUND-04**: `CitationLinter` Python class — stdlib `re` only, no third-party dep, in-memory validate against EvidenceRegistry
- [x] **GROUND-05**: Live-mode citation enforcement — response-level strip; total-strip falls back to ack bank via `PROMPT-09` integration
- [x] **GROUND-06**: Citation linter telemetry — `stripped_rate_15s > 0.4` triggers next-response bypass with `[unverified]` log marker; per-session `slop_ratio` metric surfaced via `ipc.session.citation`
- [x] **GROUND-07**: Per-mode tolerance bands — ±1.0s live, ±2.0s debrief (rolling-latency-aware optional)
- [ ] **GROUND-08**: Prompt-side mitigation — "If you cannot cite, say 'I'm listening' — never reply with empty text" appended to live system instruction

### Latency & Liveness — The Latency Stack

- [x] **LATENCY-01**: Pre-canned ack bank — 40 OPUS samples (Achird voice, generated offline once + pinned to TTS model version), bypass LiveKit TTS path via direct `PlaybackQueue.push()`
- [x] **LATENCY-02**: Ack rotation deque (maxlen=10) prevents same-sample-within-30s collision per event class
- [x] **LATENCY-03**: Per-event-class ack buckets — `drop_hit/`, `track_change/`, `mix_move/`, `silence_break/`, `generic_filler/`
- [x] **LATENCY-04**: Ack fires only when `rolling_ttft_avg_ms > 800`; suppresses when LLM is fast that turn
- [x] **LATENCY-05**: Min-ack-to-response gap = 400ms to prevent awkward overlap
- [x] **LATENCY-06**: `CachedLLM` subclass injecting `cached_content` via `extra_kwargs`; ~500-1500ms TTFT win per call
- [x] **LATENCY-07**: System instruction padded with deterministic context (MIDI map dump + event taxonomy enum + persona spec) to stay above Gemini's 1024-token cache floor when prompt-dieting
- [x] **LATENCY-08**: Cache lifecycle manager — creates cache on session start, refreshes every 4 min (TTL 5min minimum)
- [ ] **LATENCY-09**: Prompt diet — audio Part trimmed 18s → 6s on non-PHASE events; screen Part skipped on MIX_MOVE/HEARTBEAT
- [ ] **LATENCY-10**: `SpeechHandle.interrupt(force=True)` wrapper for programmatic cancel-and-refire (bypasses `allow_interruptions=False` user-mic gate)
- [ ] **LATENCY-11**: Cancel cooldown hard cap — `CANCEL_COOLDOWN_S = 8.0` (Pitfall 1 mitigation)
- [ ] **LATENCY-12**: Cancel soft cap — 30/session telemetry assertion auto-disables cancel-and-refire if `interrupted_rate > 3/min sustained`
- [ ] **LATENCY-13**: Priority-gated cancel — higher-priority event (DROP=10 > MIX_MOVE=5) preempts in-flight generation; lower-priority queued or dropped

### Personality & Anticipation — Mascot

- [ ] **MASCOT-10**: 4-layer additive state machine refactor (simplified for v2.0 — mood baseline + anticipation overlay + speak/react; full effect layer deferred to v2.1)
- [ ] **MASCOT-11**: Anticipation layer fires T+50ms from `EventDetector.detect()` — BEFORE Gemini round-trip — masks 400-1200ms of perceived latency
- [ ] **MASCOT-12**: 5 new `prep_*` GLB clips authored with idle-zero lower-body delta (additive blend layer)
- [ ] **MASCOT-13**: 2.5s anticipation timeout crossfades prep → `prep_settle` (NOT snap-back-to-idle on Gemini misfire — Pitfall 9)
- [ ] **MASCOT-14**: Cancel-aware anticipation crossfade — `SpeechHandle.interrupt(force=True)` triggers prep-fadeout
- [ ] **MASCOT-15**: Linter-strip-aware crossfade — total-strip triggers prep-fadeout + ack-only fallback
- [ ] **MASCOT-16**: Beat-coupled procedural hip-bob — `Hips` bone Y offset weighted by RMS, locked to `MusicState.bpm + beat_phase`; two modes (phase-locked at >150 BPM, amplitude-driven at <130 BPM)
- [ ] **MASCOT-17**: Three.js `AnimationUtils.makeClipAdditive` pass on all prep clips; p99 frame budget ≤22ms verified via vitest perf test
- [ ] **MASCOT-18**: BPM phase drift mitigation — re-sync on every downbeat detection from `MusicState.beat_phase`
- [ ] **MASCOT-19**: GLB clip total budget ≤15MB CI gate (anticipation adds ~6MB; remaining headroom for v2.1 emote-tag clips)

### Cross-Software Integration — djay Pro Mac Overlay

- [ ] **OVERLAY-01**: AX bridge in Tauri Rust parent (`tauri/src-tauri/src/ax_bridge.rs`) — sidecar requests rect via `ipc.overlay.ax_position` query; AX NEVER called from Python (Tauri #8329 mitigation, codebase grep gate)
- [ ] **OVERLAY-02**: Day-1 AX-from-Rust-parent feasibility spike on code-signed bundle (Pitfall 3 prevention) — verifies kyleawayan/djay-pro-bridge pattern works on installed signed app, not just dev
- [ ] **OVERLAY-03**: Second Tauri `WebviewWindow` (`label="overlay"`, transparent, always_on_top, set_ignore_cursor_events(true), decorations=false)
- [ ] **OVERLAY-04**: Window tracker @10Hz follows djay Pro window bounds (move/resize/fullscreen-Spaces detection)
- [ ] **OVERLAY-05**: 12 hand-mapped pointable elements in `tauri/ui/src/overlay/elements.json` — per-deck (mid/high/low EQ, gain, filter, fader, jog, play, cue, sync, tempo slider, hot cues) for djay Pro v5
- [ ] **OVERLAY-06**: Canvas 2D ring renderer (amber `--ring-active` token, fade-in 200ms, hold 800ms, fade-out 300ms); 8s cooldown per element, at-most-one-ring-per-3s utterance
- [ ] **OVERLAY-07**: Fullscreen-Spaces toast (Pitfall 4 mitigation) — overlay vanishes when DJ goes fullscreen on macOS; surface "Windowed mode for ring highlights" inline notice
- [ ] **OVERLAY-08**: Dual-monitor coord-space consistency — all-Quartz no-NSScreen (Pitfall 13 mitigation, multi-monitor Y-flip)
- [ ] **OVERLAY-09**: `#[cfg(target_os = "macos")]` gate — Windows + Rekordbox/Serato overlay deferred to v2.1+; README flags Mac-only scope at launch

### Cross-Software Integration — Pyrekordbox XML Library Import

- [ ] **LIBRARY-01**: `RekordboxLibrary` class with `pyrekordbox==0.4.4` XML parser (handles Rekordbox 5/6/7 schema variations, TEMPO + POSITION_MARK nested elements)
- [ ] **LIBRARY-02**: SQLite cache at `$APPDATA/vibemix/library/rekordbox.db` — 3 tables (tracks, cues, beat_grid)
- [ ] **LIBRARY-03**: 4-tier fuzzy lookup confidence ladder — exact → BPM-disambiguated → partial+artist → partial-only; artist OR BPM required for ≥0.7 confidence (Pitfall 16 mitigation)
- [ ] **LIBRARY-04**: Confidence-aware grounding — "I think this is X" when <0.5; full citation `[track:<id>]` when ≥0.7
- [ ] **LIBRARY-05**: Drag-drop + file-picker UX in Settings → Library tab
- [ ] **LIBRARY-06**: 30-day staleness nudge + lookup-fail counter (Pitfall 15 mitigation)
- [ ] **LIBRARY-07**: SQLCipher path explicitly skipped (broken post-Rekordbox 6.6.5)
- [ ] **LIBRARY-08**: Sqlite-vec architectural slot reserved for v2.1 library intelligence; v2.0 ships only the SOURCE path, not the embed pipeline

### Cross-Software Integration — MIDI Library Extension

- [ ] **MIDI-15**: `MidiMapLoader` class replaces hardcoded `_CC_MAP`/`_NOTE_MAP` dicts; loads from `vibemix/midi/library/<sku>.json`
- [ ] **MIDI-16**: DDJ-FLX4 Sync note disambiguation — 0x60 (v4) vs 0x58 (Mixxx canonical) resolved via 5-min mido sniff with Kaan present
- [ ] **MIDI-17**: Verified mido-sniff data for DDJ-400, FLX6, FLX10, SX3, XDJ-RX3, Hercules Inpulse 300/500, Numark Party Mix Live, Numark Mixstream Pro+
- [ ] **MIDI-18**: Community sniff tooling at `scripts/sniff_controller.py` — captures CC + note + value-range for PR contribution path
- [ ] **MIDI-19**: Generic-MIDI fallback "observes, classifies conservatively, never invents" — logs activity, no aggressive role inference

### Coaching & Memory — Post-Session Debrief (Architectural Slot Only — v2.0)

- [ ] **DEBRIEF-01**: Sidecar `--debrief <session_dir>` flag spawns separate child process on WS bus port 8766 (avoids 8765 collision with live sidecar); architectural slot only, full UI feature deferred to v2.1
- [ ] **DEBRIEF-02**: IPC schema reservations for `ipc.debrief.start`, `ipc.debrief.status`, `ipc.debrief.result` (3 messages, hidden in v2.0, surfaced in v2.1)

### Ship & Distribution — Absorbed from v0.1.0

- [ ] **REC-07**: Recording browser UI surface (REC-05 was marked complete but UX needs v2.0 polish — Phase 15 in absorbed plan)
- [ ] **REC-08**: Retention enforcement cron worker (REC-06 hooks)
- [ ] **DIST-09**: Apple Developer ID DMG sign + notarize (Issuer ID `3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b` supplied 2026-05-14; key URMDRP5M3P — Apple Developer Program Agreement update outstanding, Francesco-action-required)
- [ ] **DIST-10**: notarytool `--keychain-profile vibemix-URMDRP5M3P` configured; staple + validate against `spctl --assess` after sign
- [ ] **DIST-11**: SignPath OSS Windows MSI sign — application filed Day-1 of v2.0 (~1-week SLA)
- [ ] **DIST-12**: GitHub release matrix (macos-14 arm64 + macos-14 intel + windows-latest x86_64 + windows-latest arm64) with AIza-scan-clean across new bundle paths
- [ ] **DIST-13**: Tauri Updater `latest.json` ed25519-signed; secret-name audit (`TAURI_UPDATER_KEY_PASSWORD` vs `TAURI_UPDATER_PRIVATE_KEY_PASSWORD` — Pitfall 7)
- [ ] **DIST-14**: Updater manifest POST to `api.altidus.world/vibemix/updates/upload` (Bravoh ops deploys this endpoint as carry-forward)
- [ ] **GH-19**: README full rewrite — value-prop paragraph above the fold, 30s demo GIF embedded, 12-question FAQ pre-seeded (anti-slop, anti-API-key, why-Gemini), 8-controller logo grid, badges row, install one-liner
- [ ] **GH-20**: Hero PNG already shipped (Phase 19 absorbed); architecture SVG already shipped; 30s demo GIF NEW asset required
- [ ] **GH-21**: CONTRIBUTING.md controller-mapping path with `scripts/sniff_controller.py` reference

### Ship & Distribution — Day-Zero Operations

- [ ] **OPS-01**: Fresh-macOS-VM rehearsal — clean macOS 14+ install, no dev cruft, screencast recorded (Pitfall 31 mitigation — Kaan's rig has BlackHole pre-installed + TCC granted, false-pass risk if used)
- [ ] **OPS-02**: Fresh-Windows-VM rehearsal — clean Windows 11 install, AV/Defender SmartScreen reputation building check
- [ ] **OPS-03**: `api.altidus.world/healthz` curl gate Day-0 (Pitfall 32 mitigation — endpoint must be deployed before first user installs)
- [ ] **OPS-04**: Discord server setup — roles + channels + bot (Pitfall 34 mitigation — first 100 stars can't gather without it)
- [ ] **OPS-05**: GitHub issue templates + auto-labeler (`.github/workflows/issue-triage.yml`) — Pitfall 35 mitigation
- [ ] **OPS-06**: Bravoh proxy load test (100 RPS for 5 min, p99 <500ms) — Pitfall 30 / 39 mitigation
- [ ] **OPS-07**: Adaptive cap + dashboard for proxy budget — soft cap auto-throttles per-user when 50€/mo per-user nears breach
- [ ] **OPS-08**: Pre-seeded friend/dev stars (15+) before public launch to bootstrap social proof

### Viral Wave — Demo Film + Channel Posts

- [ ] **VIRAL-01**: 30s viral demo film — single take or curated multi-take, djay Pro 5 windowed mode, CDJ Whisper color, Kaan + DDJ-FLX4 + HD25 headphones
- [ ] **VIRAL-02**: Beat A (T+8s): "AI points at the knob" — amber overlay ring on mid EQ deck A synchronized with Gemini voice line citing the move
- [ ] **VIRAL-03**: Beat B (T+14s): "Anticipation lean-in BEFORE voice" — mascot leans forward 200ms before Gemini audio arrives
- [ ] **VIRAL-04**: Beat C (T+22-25s): "3 seconds of deliberate silence" — AI stays quiet because nothing meaningful happened; anti-slop made visual
- [ ] **VIRAL-05**: Twitter thread post — technical breakdown, Beat A hero image, code snippets, GitHub link
- [ ] **VIRAL-06**: IG Reels post (IT + EN dual-track) — cinematic cut, music swell, Beat B hero
- [ ] **VIRAL-07**: Reddit r/Beatmatch + r/DJs post — Beat C hero, open-source angle, EULA-friendly framing
- [ ] **VIRAL-08**: HN "Show HN" post — engineering breakdown, anti-slop story, Beat A hero
- [ ] **VIRAL-09**: Pre-seeded FAQ per channel — anti-slop, anti-API-key, why-Gemini, Rekordbox-in-v2-roadmap
- [ ] **VIRAL-10**: GitHub stars ticker outro frame — frames the call-to-action against 15+ pre-seeded star count

### Hallucination Verification Gate — Kaan's DJ Ear

- [ ] **VERIFY-07**: Hallucination Verification Gate is Kaan's personal DJ-set testing (3-5 real sessions across the milestone) — NOT a 30-session formal eval suite per memory `project_phase_16_kaan_dj_testing`; supersedes VERIFY-01/02/03/05 from v0.1.0 plan
- [ ] **VERIFY-08**: Phase 16 ear-test runs against shipped detector + linter + ack bank + mascot anticipation as they land in subsequent phases; tuning CSV from `scripts/tune_detectors.py` is the audit surface
- [ ] **VERIFY-09**: Stretch — Francesco + 5-tester beta pool inside Phase 16 (Pitfall 40 sample-size-of-1 mitigation)
- [ ] **VERIFY-10**: Phase 16 ear-test MUST replay sessions with `linter_silence_streak > 2` and assert it doesn't happen on real DJ sets (Pitfall 2 ground-truth)

---

## v2.1+ Deferred

These features have research-locked implementation paths but are explicitly OUT of v2.0 scope. Move into next milestone after v2.0 ships.

- [ ] Predictive drop firing — gated on Kaan ear-test telemetry from v2.0 baseline (A-bucket open Q1)
- [ ] 4-layer mascot additive state machine full structural rewrite (~14 E-days; v2.0 ships only simplified anticipation subset)
- [ ] Inline emote-tag vocabulary (15 tags) — gated on 1-day Gemini text-channel-timing spike (D-bucket A3 risk)
- [ ] Post-session debrief MVP UI — chaptered + voiced TL;DR + 3 drills + clickable timeline (~7 E-days); architectural slot DEBRIEF-01/02 ships in v2.0
- [ ] Long-term DJ profile — ~2KB JSON regenerated each session, injected verbatim into next live prompt; profile_*.json schema
- [ ] Cross-mode citation enforcement — extend live linter to debrief + library + genre sentence-level (E-followup §3)
- [ ] Library intelligence v1 — file watcher (watchdog) → Gemini Embedding 2 audio embed → sqlite-vec store (or numpy fallback on Win) → "what should I play next?" + transition critique queries
- [ ] Library-aware drill cards — "3 tracks from your library that fix this" — depends on library intel + debrief
- [ ] Hard Tek-specific detectors `DISTORTION_CLIMB` + `ACID_LINE_ENTRY` — ship as Wave 2 of P17 if v2.0 timeline allows; else v2.1
- [ ] Rekordbox / Serato overlay via template matching (canvas-rendered apps, AX returns nothing)
- [ ] Windows overlay parity — DPI virtualization + EnumWindows + WS_EX_LAYERED+TRANSPARENT
- [ ] VirtualDJ OSC integration (paid Pro license required upstream)
- [ ] Genre expansion: Techno → Tech House → DnB → Trance → UKG → Trap → Disco (per-genre detector + reaction-vocab + 1 weekend each)
- [ ] Mixxx OSC as first-class integration (currently behind `--enable-mixxx-osc` flag, gated on PR #14388 upstream merge)
- [ ] Highlight reel export (auto-generate shareable clips from recordings)
- [ ] Session replay UI with timeline scrubber
- [ ] "Coach this moment" manual trigger
- [ ] Live mid-mix Coach nudges (Pro mode opt-in only)
- [ ] Windows now-playing via winsdk GSMTC (if SCREEN-06 deferred)
- [ ] Additional controller mappings beyond the curated 10
- [ ] Auto-detect genre (replaces manual picker — research-grade)
- [ ] Multi-language UI chrome (currently English only)
- [ ] Procedural mascot mouth from audio amplitude (3 talk variants — calm/loop/hype)

## Out of Scope

**v0.1.0 Out-of-Scope (preserved):**

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

**v2.0 additions to Out-of-Scope (memory-locked, anti-slop / scope-creep guards):**

- **30-session formal hallucination eval suite (supersedes v0.1.0 VERIFY-01/02/03/05)** — Kaan's personal DJ-set testing IS the hallucination gate per memory `project_phase_16_kaan_dj_testing`. No replay harness, no LLM scorer, no F1 validator.
- **CLAP / OpenL3 / MERT / LAION-CLAP audio embedding models** — Gemini-only product per memory `feedback_no_clap_use_gemini_embedding`. Gemini Embedding 2 is the embedding model.
- **mem0 / motorhead / Chroma / Qdrant for long-term DJ profile** — solves wrong problem (cross-conversation retrieval) + violates one-click-install per memory `project_v2_open_candidates`. DJ tendencies = ~2KB structured JSON, regenerated each session.
- **Multi-provider LLM abstraction layer** — Gemini-only, no OpenAI / Anthropic / Whisper / Replicate codepath per memory `feedback_no_scope_creep_clean_utility`.
- **Stem separation (Demucs / spleeter / open-unmix)** — ~500MB model bundle violates one-click-install hard requirement.
- **Pioneer ProDJ Link (`python-prodj-link` / `beat-link`)** — requires CDJ hardware on Ethernet; bedroom DJ audience doesn't have CDJs. Wrong market.
- **Rekordbox SQLCipher direct DB path** — Pioneer broke automatic key extraction at v6.6.5+; XML export path is the durable alternative.
- **Mixamo ARKit blendshape lip-sync for mascot** — Mixamo killed blendshape export 2020; current rig has no blendshapes; re-rigging is 2-3 weeks + uncanny valley risk. Use 3 amplitude-banded talk variants instead.
- **pydantic in IPC layer** — Phase 6 D-Area-4.4 constraint; hand-written `@dataclass(frozen=True, slots=True)` + jsonschema Draft-07 is the IPC contract.
- **Predictive drop firing default-on in v2.0** — gated on Kaan ear-test telemetry; ships off-by-default + per-genre toggle.
- **AX from Python sidecar for djay overlay** — Tauri #8329; AX MUST run in Rust parent. Codebase grep gate fails CI if AX called from Python.
- **Rekordbox / Serato / Traktor / djay / VirtualDJ-Home real-time deck telemetry** — no public real-time API; deferred to v2.1+ template-matching attempts or never.
- **Mixxx OSC as a v2.0 first-class integration** — PR #14388 still draft upstream; ships behind `--enable-mixxx-osc` flag if at all; promote when upstream merges.
- **Rekordbox overlay highlight (template-matching)** — v2.1+; canvas-rendered UI requires fragile per-version coord mapping.
- **Windows overlay highlight parity** — v2.1+; DPI virtualization + EnumWindows + WS_EX_LAYERED+TRANSPARENT.
- **Library intelligence file-watcher + embed pipeline** — v2.1+; v2.0 ships only the SOURCE path (Pyrekordbox XML one-shot import).
- **Post-session debrief UI surface** — v2.1+; v2.0 ships only the architectural slot (sidecar --debrief flag + port 8766 + IPC reservations).
- **Long-term DJ profile injection into live prompt** — v2.1+; depends on debrief UI.
- **Cross-mode citation enforcement (debrief + library + genre)** — v2.1+; v2.0 ships live-mode enforcement only.
- **30+ controller mappings** — curated 10-SKU library is the v2.0 cap; community-PR path opens via `scripts/sniff_controller.py`.
- **Auto-detect genre via on-device classifier** — v2.1+; v2.0 uses user-declared genre + nowplaying-cli metadata.
- **Discord bot full automation** — v2.0 ships only Discord server + manual moderation; bot moderation v2.1+.
- **Custom Gemini fine-tunes** — Gemini Pro/Flash off-the-shelf only; no fine-tuning infrastructure in v2.0.

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

## v2.0 Traceability

*Populated by `gsd-roadmapper` 2026-05-14 — each v2.0 REQ-ID maps to exactly one phase.*

| REQ-ID | Phase | Notes |
|--------|-------|-------|
| SENSE-11 | Phase 17 | `GenreRouter` atomic detector-dict swap. |
| SENSE-12 | Phase 17 | 6 cross-genre detectors: KICK_SWAP / SUB_LAYER_ARRIVAL / BREAKDOWN_KICK_KILL / REENTRY_KICK_LAND / KICK_DENSITY_SHIFT / PHRASE_BOUNDARY. |
| SENSE-13 | Phase 17 | MusicState +4 fields with backward-compat defaults. |
| SENSE-14 | Phase 17 | PHRASE_BOUNDARY 40-120Hz band-limited autocorr, ±1 bar, self-correct on BREAKDOWN_KICK_KILL. |
| SENSE-15 | Phase 17 | Per-genre detector dispatch architecture. |
| SENSE-16 | Phase 17 | `scripts/tune_detectors.py` reference-WAV tuning harness. |
| GROUND-01 | Phase 18 | EvidenceRegistry as SIBLING write-target, never separate writer. |
| GROUND-02 | Phase 18 | Citation grammar EBNF locked (8 forms + multi-citation). |
| GROUND-03 | Phase 18 | Grammar baked into Gemini system instruction (v1.0 prompt-only seeding). |
| GROUND-04 | Phase 20 | `CitationLinter` stdlib `re` only, no third-party dep. |
| GROUND-05 | Phase 20 | Live-mode response-level strip + ack-bank fallback. |
| GROUND-06 | Phase 20 | Telemetry guard `stripped_rate_15s > 0.4` bypass + `slop_ratio` metric. |
| GROUND-07 | Phase 20 | Per-mode tolerance ±1.0s live / ±2.0s debrief. |
| GROUND-08 | Phase 20 | Prompt-side "I'm listening" mitigation appended to live system instruction. |
| LATENCY-01 | Phase 19 | 40 OPUS ack samples (Achird voice, offline-generated, TTS-version-pinned). |
| LATENCY-02 | Phase 19 | Ack rotation deque maxlen=10, no same-sample-within-30s. |
| LATENCY-03 | Phase 19 | Per-event-class ack buckets (drop_hit / track_change / mix_move / silence_break / generic_filler). |
| LATENCY-04 | Phase 19 | Ack fires only when `rolling_ttft_avg_ms > 800`. |
| LATENCY-05 | Phase 19 | Min-ack-to-response gap = 400ms. |
| LATENCY-06 | Phase 19 | `CachedLLM` subclass injecting `cached_content` via `extra_kwargs`. |
| LATENCY-07 | Phase 19 | System instruction padded with deterministic context above 1024-token cache floor. |
| LATENCY-08 | Phase 19 | Cache lifecycle manager refreshes every 4 min (TTL 5 min minimum). |
| LATENCY-09 | Phase 19 | Prompt diet — audio Part 18s→6s on non-PHASE, screen skipped on MIX_MOVE/HEARTBEAT. |
| LATENCY-10 | Phase 19 | `SpeechHandle.interrupt(force=True)` wrapper bypasses `allow_interruptions=False`. |
| LATENCY-11 | Phase 19 | `CANCEL_COOLDOWN_S = 8.0` hard cap (Pitfall 1 mitigation). |
| LATENCY-12 | Phase 19 | 30/session soft cap telemetry assertion auto-disable. |
| LATENCY-13 | Phase 19 | Priority-gated cancel (DROP=10 > MIX_MOVE=5). |
| MASCOT-10 | Phase 22 | 4-layer additive simplified subset (mood + anticipation + speak/react); full effect layer v2.1. |
| MASCOT-11 | Phase 22 | Anticipation fires T+50ms from `EventDetector.detect()` — BEFORE Gemini round-trip. |
| MASCOT-12 | Phase 22 | 5 `prep_*` GLB clips with idle-zero lower-body delta. |
| MASCOT-13 | Phase 22 | 2.5s anticipation timeout crossfades prep → `prep_settle` (Pitfall 9). |
| MASCOT-14 | Phase 22 | Cancel-aware anticipation crossfade on `interrupt(force=True)`. |
| MASCOT-15 | Phase 22 | Linter-strip-aware crossfade on total-strip + ack-only fallback. |
| MASCOT-16 | Phase 22 | Beat-coupled procedural hip-bob; phase-locked >150 BPM, amplitude-driven <130 BPM. |
| MASCOT-17 | Phase 22 | `AnimationUtils.makeClipAdditive` on all prep clips; p99 frame budget ≤22ms vitest perf. |
| MASCOT-18 | Phase 22 | BPM phase drift mitigation — re-sync on every downbeat. |
| MASCOT-19 | Phase 22 | GLB clip total budget ≤15MB CI gate. |
| OVERLAY-01 | Phase 24 | AX bridge in Tauri Rust parent; AX NEVER called from Python (codebase grep gate). |
| OVERLAY-02 | Phase 24 | Day-1 AX-from-Rust-parent feasibility spike on code-signed bundle (Pitfall 3). |
| OVERLAY-03 | Phase 24 | Second Tauri `WebviewWindow` label="overlay" with transparent + always_on_top + click-through. |
| OVERLAY-04 | Phase 24 | Window tracker @10Hz following djay Pro window bounds. |
| OVERLAY-05 | Phase 24 | 12 hand-mapped pointable elements in `elements.json` for djay Pro v5. |
| OVERLAY-06 | Phase 24 | Canvas 2D ring renderer with 8s per-element cooldown + ≤1 ring/3s utterance. |
| OVERLAY-07 | Phase 24 | Fullscreen-Spaces toast (Pitfall 4 mitigation). |
| OVERLAY-08 | Phase 24 | Dual-monitor all-Quartz no-NSScreen coord consistency (Pitfall 13). |
| OVERLAY-09 | Phase 24 | `#[cfg(target_os = "macos")]` gate; Win + Rekordbox/Serato deferred v2.1. |
| LIBRARY-01 | Phase 25 | `RekordboxLibrary` class with `pyrekordbox==0.4.4` XML parser. |
| LIBRARY-02 | Phase 25 | SQLite cache `$APPDATA/vibemix/library/rekordbox.db` (tracks + cues + beat_grid). |
| LIBRARY-03 | Phase 25 | 4-tier fuzzy lookup confidence ladder; artist OR BPM required for ≥0.7 (Pitfall 16). |
| LIBRARY-04 | Phase 25 | Confidence-aware grounding rendering. |
| LIBRARY-05 | Phase 25 | Drag-drop + file-picker UX in Settings → Library tab. |
| LIBRARY-06 | Phase 25 | 30-day staleness nudge + lookup-fail counter (Pitfall 15). |
| LIBRARY-07 | Phase 25 | SQLCipher path explicitly skipped. |
| LIBRARY-08 | Phase 25 | Sqlite-vec architectural slot reserved for v2.1 (v2.0 ships only SOURCE path). |
| MIDI-15 | Phase 23 | `MidiMapLoader` replaces hardcoded `_CC_MAP`/`_NOTE_MAP`. |
| MIDI-16 | Phase 23 | DDJ-FLX4 Sync note disambiguation via 5-min mido sniff (Pitfall 25). |
| MIDI-17 | Phase 23 | Verified mido-sniff data for 9 SKUs. |
| MIDI-18 | Phase 23 | `scripts/sniff_controller.py` community contribution tooling. |
| MIDI-19 | Phase 23 | Generic-MIDI fallback "observes, classifies conservatively, never invents." |
| DEBRIEF-01 | Phase 25 | Sidecar `--debrief <session_dir>` flag, separate child process on WS bus port 8766. |
| DEBRIEF-02 | Phase 25 | IPC schema reservations `ipc.debrief.start/.status/.result` (hidden in v2.0, surfaced v2.1). |
| REC-07 | Phase 15 | Recording browser UI surface (v2.0 polish over REC-05). |
| REC-08 | Phase 15 | Retention enforcement cron worker (REC-06 hooks). |
| DIST-09 | Phase 21 | Apple Developer ID DMG sign + notarize (Issuer ID supplied; agreement update outstanding — Francesco-action). |
| DIST-10 | Phase 21 | notarytool `--keychain-profile vibemix-URMDRP5M3P` + staple + spctl assess. |
| DIST-11 | Phase 21 | SignPath OSS Windows MSI sign — application filed Day-1 (~1-week SLA). |
| DIST-12 | Phase 21 | GitHub release matrix 4 binaries + AIza-scan-clean across new bundle paths. |
| DIST-13 | Phase 21 | Tauri Updater latest.json ed25519-signed + secret-name audit (Pitfall 7). |
| DIST-14 | Phase 21 | Updater manifest POST to `api.altidus.world/vibemix/updates/upload` (Bravoh ops carry-forward). |
| GH-19 | Phase 26 | README full rewrite (value-prop above the fold + 30s demo GIF + 12-question FAQ + 8-controller logo grid + badges + install one-liner). |
| GH-20 | Phase 26 | 30s demo GIF NEW asset (hero PNG + architecture SVG already shipped Phase 19 absorbed). |
| GH-21 | Phase 26 | CONTRIBUTING.md controller-mapping path with `scripts/sniff_controller.py`. |
| OPS-01 | Phase 26 | Fresh-macOS-VM rehearsal (no BlackHole pre-install, no TCC pre-grant — Pitfall 31). |
| OPS-02 | Phase 26 | Fresh-Windows-VM rehearsal (AV/Defender SmartScreen reputation check). |
| OPS-03 | Phase 26 | `api.altidus.world/healthz` curl gate Day-0 (Pitfall 32). |
| OPS-04 | Phase 26 | Discord server setup — roles + channels + bot (Pitfall 34). |
| OPS-05 | Phase 26 | GitHub issue templates + auto-labeler (Pitfall 35). |
| OPS-06 | Phase 26 | Bravoh proxy load test 100 RPS for 5 min, p99 <500ms (Pitfall 30/39). |
| OPS-07 | Phase 26 | Adaptive cap + dashboard for proxy budget. |
| OPS-08 | Phase 26 | Pre-seeded friend/dev stars (15+) before public launch. |
| VIRAL-01 | Phase 26 | 30s viral demo film — djay Pro 5 windowed mode, CDJ Whisper color, Kaan + DDJ-FLX4 + HD25. |
| VIRAL-02 | Phase 26 | Beat A (T+8s) — amber overlay ring on mid EQ deck A. |
| VIRAL-03 | Phase 26 | Beat B (T+14s) — anticipation lean-in BEFORE voice. |
| VIRAL-04 | Phase 26 | Beat C (T+22-25s) — 3 seconds of deliberate silence. |
| VIRAL-05 | Phase 26 | Twitter thread post — Beat A hero. |
| VIRAL-06 | Phase 26 | IG Reels post (IT + EN) — Beat B hero. |
| VIRAL-07 | Phase 26 | Reddit r/Beatmatch + r/DJs post — Beat C hero. |
| VIRAL-08 | Phase 26 | HN Show HN post — Beat A hero. |
| VIRAL-09 | Phase 26 | Pre-seeded FAQ per channel. |
| VIRAL-10 | Phase 26 | GitHub stars ticker outro frame. |
| VERIFY-07 | Phase 16 | Hallucination Verification Gate = Kaan's personal DJ-set testing (3-5 sessions); supersedes v0.1.0 VERIFY-01/02/03/05. |
| VERIFY-08 | Phase 16 | Phase 16 runs against shipped detector + linter + ack bank + mascot anticipation as they land. |
| VERIFY-09 | Phase 16 | Stretch — Francesco + 5-tester beta pool (Pitfall 40 mitigation). |
| VERIFY-10 | Phase 16 | Replay sessions with `linter_silence_streak > 2` and assert it doesn't happen (Pitfall 2 ground-truth). |

**v2.0 Coverage:** 94 / 94 v2.0 requirements mapped. No orphans. No duplicates.

---
*Last updated: 2026-05-14 after v2.0 roadmap synthesis (gsd-roadmapper traceability pass)*
