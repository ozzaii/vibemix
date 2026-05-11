# vibemix — v1 Roadmap

**Milestone:** v1 — Bravoh's first open-source release, marketing wedge ahead of Bravoh public launch.
**Generated:** 2026-05-11 from PROJECT.md + REQUIREMENTS.md (128 v1 reqs) + research/SUMMARY.md.
**Target ship:** ~3-4 weeks (before Bravoh public launch, ~early June 2026).
**Granularity:** fine (Kaan directive — minimum 12 phases, slice 7 research-suggested phases into finer waves at parallelization/dependency seams).
**Project mode:** standard.

---

## Phases

- [x] **Phase 1: Platform Protocol Firewall** - `platform/` Protocol classes + package skeleton + dependency lockfile + SignPath OSS application filed (day-1, 3-week lead time). _**Complete 2026-05-11.** SignPath form submission Kaan-side pending (reCAPTCHA)._
- [x] **Phase 2: Audio Core Port + Ring Buffer Fix** - Port `AudioBuffer`/`MicBuffer`/`Levels`/`PlaybackQueue` from POC into pre-allocated ring buffers (fixes `np.concatenate` callback regression). _**Complete 2026-05-11.**_
- [x] **Phase 3: Sensing & State Port** - Port `MusicState` 10Hz writer + `EventDetector` + `AICoach` + `audible-deck` detection + screen/track sense from POC. _**Complete 2026-05-11.**_
- [x] **Phase 4: LiveKit Cascade Agent Pivot** (completed 2026-05-11) - Replace `RealtimeModel` with `AgentSession` cascade (`stt=None`, `vad=None`, `llm=google.LLM`, `tts=FallbackAdapter[OpenRouter Gemini TTS + Gemini native]`) + `DJCoHostAgent.llm_node()` multimodal override + headless session (no LiveKit Room — ARCH-06 re-mapped). 346 tests green; 12/12 acceptance gates PASS.
- [ ] **Phase 5: FastAPI Proxy + Install-UUID JWT** - `api.altidus.world` Gemini proxy with slowapi rate limit + Redis quota + OS-keychain JWT storage (parallelizes with Phases 1-4).
- [ ] **Phase 6: Genre-Aware Phase Detection** - Percentile-based phase detector + 5-genre profile JSON + crest-factor compression detect + BPM half/double validator + vocal-section detector.
- [ ] **Phase 7: Windows Port (Audio + Screen)** - `PyAudioWPatch` WASAPI loopback + `mss` + `pywin32` window enum + Windows sample-rate sanity test (parallelizes with Phase 6).
- [ ] **Phase 8: macOS ScreenCaptureKit Migration** - Replace deprecated Quartz `CGWindowListCreateImageFromArray` with `pyobjc-framework-ScreenCaptureKit` (parallelizes with Phases 6-7).
- [ ] **Phase 9: MIDI Controller Library (10 + Generic Fallback)** - Curated mappings for DDJ-FLX4/400/FLX6/FLX10/1000/SX3, XDJ-RX3, Numark Party Mix Live, Hercules Inpulse 300/500 + generic positional fallback + hot-plug re-enumeration (parallelizes with Phases 6-8).
- [ ] **Phase 10: Prompt Template Matrix (6 cells + Anti-Slop)** - 6 prompt templates (3 skill × 2 mode) + negative dictionary + `TurnHistory` anti-repetition + `<silence/>` short-circuit + describe-before-infer + past-tense framing.
- [ ] **Phase 11: Tauri Shell + Calibration Wizard** - Tauri 2.x scaffold + Python sidecar wiring + IPC contract + 3-step calibration wizard UI (permissions → output/sample-rate → controller probe).
- [ ] **Phase 12: Live Session UI + Settings Panel** - Meters + phase tape + AI transcript + drop countdown + MIDI event ribbon + voice/mode/genre/output pickers + push-to-mute hotkey + status badges + recording retention policy.
- [ ] **Phase 13: Reactive Mascot (Avery)** - SVG mascot with named pose vocabulary + idle animation + magnitude-aware MIDI pose dispatch + TTS-synced mouth + eye-tracking + beat-sync bounce.
- [ ] **Phase 14: FL-Studio Polish Phase (Critique → Execute Loop)** - Dedicated polish pass with `gsd-ui-checker` + `gsd-ui-auditor` iterations until retro-futurist-hardware bar passes (20/80 rule, textured materials, no web-app residue).
- [ ] **Phase 15: Recording & Session Capture Finalization** - Per-session dir + `input.wav`/`voice.wav`/`events.jsonl` + recording browser UI + retention enforcement (carries POC; lock UX).
- [ ] **Phase 16: Hallucination Verification Gate** - 30-session offline replay suite ≥95% grounded + per-genre phase-detection ≥85% F1 + 60-min soak test zero `session_error`.
- [ ] **Phase 17: Reaction-Reel Slop Grading Gate** - Hand-graded 30-min reaction reel blind-rated 1-5 by Kaan + Francesco + 2 DJ network friends; pass requires ≥4.0 average with zero 1-2 ratings.
- [ ] **Phase 18: Distribution — Signing, Notarization, Installers** - PyInstaller `--onedir` macOS DMG (Apple Dev ID + notarytool + stapler) + Windows MSI (SignPath OSS cert + Inno Setup 6) + Tauri auto-update + binary attack verification (`strings` + `pyinstxtractor` for `AIza` patterns).
- [ ] **Phase 19: GitHub Launch Presence** - Hero banner + demo video/GIF + install buttons + feature matrix + controller grid + screenshots + FAQ + Bravoh footer + Apache 2.0 LICENSE + DCO CONTRIBUTING + SECURITY/CODE_OF_CONDUCT/NOTICE/TRADEMARKS + issue templates + OG image + repo hygiene scrub.
- [ ] **Phase 20: Day-Zero Operations** - GitHub Actions CI matrix (macos-14 + windows-latest) tagged builds + fresh-machine install rehearsal on non-dev macOS + Windows + second-responder rota for first 72h.

---

## Phase Details

### Phase 1: Platform Protocol Firewall
**Goal**: A unified `vibemix` Python package exists with the `platform/` protocol surface in place, so all downstream phases import OS abstractions instead of OS-specific symbols. SignPath Foundation OSS code-signing application is filed on day 1 (3-week approval lead time aligns with installer phase).
**Depends on**: Nothing (foundation).
**Requirements**: ARCH-01, ARCH-02, DIST-04.
**Success Criteria** (what must be TRUE):
  1. `from vibemix.platform import audio_input, screen, nowplaying, midi` resolves without OS-specific imports leaking into client code; `grep -RE "import (Quartz|win32|sounddevice|pyaudio|mss)" src/vibemix/ | grep -v platform/` returns zero matches outside `platform/`.
  2. Three POC variants (`cohost.py` / `cohost_v2.py` / `cohost_lk.py`) are archived under `archive/poc/` and the canonical entry point is `python -m vibemix`.
  3. `pyproject.toml` + `requirements.lock` exist with verified version pins (Python 3.12, livekit-agents 1.5.8, google-genai 2.0.1, etc.); `uv pip install -e .` succeeds on a clean macOS Python 3.12 venv.
  4. SignPath Foundation OSS application is submitted and confirmation email is in Kaan's inbox; tracking ticket exists in the planning notes with the expected approval window.
**Plans:** 1 plan
Plans:
- [ ] 01-01-PLAN.md — Package skeleton + four typing.Protocol firewall surfaces + uv lockfile + Apache 2.0 LICENSE + SignPath OSS application checklist (Kaan-only submit) + public repo creation at github.com/ozzaii/vibemix (Kaan-only)

### Phase 2: Audio Core Port + Ring Buffer Fix
**Goal**: Pre-allocated audio ring buffers replace the POC's `np.concatenate`-per-callback pattern, killing the dropout regression flagged in CONCERNS.md / PITFALLS.md P5. macOS audio I/O works end-to-end via `platform/_audio_macos.py`.
**Depends on**: Phase 1.
**Requirements**: AUDIO-01, AUDIO-06, AUDIO-07, AUDIO-08, AUDIO-09, ARCH-07.
**Success Criteria** (what must be TRUE):
  1. Audio sounddevice callbacks perform zero allocations (verified by `cProfile` + `tracemalloc` showing zero allocations in the callback path over a 60-second capture).
  2. A 60-minute macOS capture session emits zero PortAudio `input_overflow` or `output_underflow` status flags in logs.
  3. Mic gating (`MicBuffer._current_gain()`) mutes during AI TTS playback and resumes 350ms after AI finishes, verified by inspecting `voice.wav` boundaries against `input.wav` mic-level windows.
  4. TTS PCM playback at 24kHz routes to the user-selected output device via cross-platform `sounddevice.OutputStream`; sample-rate mismatch never causes chipmunk/molasses artifacts.
**Plans:** 5 plans
Plans:
- [x] 02-01-PLAN.md — Audio package skeleton + 14 v4 tuning constants + Levels (verbatim) + SampleRateMismatchError + pytest-mock dev dep + macos_audio pytest marker
- [x] 02-02-PLAN.md — Pre-allocated ring buffers (AudioBuffer/MicBuffer/PassthroughBuffer/PlaybackQueue + BufferRegistry) — fixes np.concatenate at v4:300 + v4:462
- [x] 02-03-PLAN.md — features.py DSP math (FFT/RMS/BPM/peak-normalize) + VoiceRecorder (0o700 sessions + configurable root)
- [x] 02-04-PLAN.md — AudioMacOS impl (Phase 1 AudioBackend Protocol) + sample-rate sanity guard (pre + post-open) + mocked sounddevice tests + opt-in live smoke
- [x] 02-05-PLAN.md — 8-gate verification + phase SUMMARY + ROADMAP/STATE advance to Phase 3

### Phase 3: Sensing & State Port
**Goal**: `MusicState` is the single source of truth at 10Hz, written by `state_refresh_loop` and read by `EventDetector` and `AICoach`. Audible-deck detection, screen capture, and track-info plumbing work on macOS, ported verbatim from `cohost_v2.py`.
**Depends on**: Phase 2.
**Requirements**: SENSE-01, SENSE-02, SENSE-05, SENSE-09, SCREEN-01, SCREEN-03, SCREEN-04, SCREEN-05.
**Success Criteria** (what must be TRUE):
  1. `MusicState` is mutated only inside `state_refresh_loop`; a lint rule + audit confirms no other writer exists in the codebase.
  2. `EventDetector.detect()` emits the 6-type event taxonomy (TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT / KAAN_SPOKE) with evidence bundled per event, matching the POC's `cohost_v2.py` semantics.
  3. Audible-deck detection (A / B / mix / none) classifies correctly on a recorded FLX4 session compared to ground-truth MIDI deck activity (≥90% agreement on a 10-minute clip).
  4. Set-timeline awareness is encoded in the evidence packet — `evidence_line()` includes "you are at MM:SS; last phase at MM:SS" and reads correctly across a 30-minute replay.
**Plans:** 5 plans
Plans:
- [x] 03-01-PLAN.md — MusicState + classify_phase + audible-deck/track resolvers (v4 verbatim)
- [x] 03-02-PLAN.md — Event + EventDetector (constants imported, no class-attrs)
- [x] 03-03-PLAN.md — AICoach (evidence_line + task_for_event + build_prompt)
- [x] 03-04-PLAN.md — state_refresh_loop + macOS Screen/MIDI/Track backends
- [x] 03-05-PLAN.md — 11-gate verification + phase SUMMARY + ROADMAP/STATE advance

### Phase 4: LiveKit Cascade Agent Pivot
**Goal**: The brain swap from `RealtimeModel` to the cascade `AgentSession` (Gemini 3 Flash multimodal + Gemini TTS streaming) is operational end-to-end on macOS. `DJCoHostAgent.llm_node()` override consumes evidence packets and yields token streams that `tts_node()` synthesizes.
**Depends on**: Phase 3 (needs MusicState/EventDetector to drive reactions); Phase 5 proxy endpoint reachable for client integration testing.
**Requirements**: ARCH-03, ARCH-04, ARCH-05, ARCH-06.
**Success Criteria** (what must be TRUE):
  1. End-to-end macOS demo: user plays a track, MIDI move detected → `session.generate_reply(instructions=...)` → Gemini Flash multimodal → streaming TTS → audible voice in headphones within 1.5s of event (latency-budget-compliant per ARCHITECTURE.md).
  2. Bundled `livekit-server --dev` binary launches on `127.0.0.1:7880` from a PyInstaller bundle path (not a `brew` dependency). _(**Re-mapped during planning** — cascade AgentSession runs headless (no Room) per v4:2031. No livekit-server binary needed for the cascade path. See `04-CONTEXT.md` and the eventual `04-SUMMARY.md` Deviations section. If Phase 11 reveals a Room-based protocol need, ARCH-06 returns there.)_
  3. The `llm_node()` override receives the right `chat_ctx` last-message contents (the EventDetector-built prompt) and reads `MusicState.evidence_line()` / `AudioBuffer.snapshot_bytes(7s)` for grounding. _(Screen JPEG attachment is deliberately disabled per v4:1502-1503 — "Single-modality: audio only. Screen + MIDI metadata caused hallucination." — and ported verbatim.)_
  4. Reconnect-on-error works: a manually-killed Gemini call retries up to 3 times within 6 seconds and logs `session_error` in `events.jsonl` if all retries fail. _(FallbackAdapter `max_retry_per_tts=1` handles TTS-side retries; LLM-side retries are inside `generate_content_stream` exception handling and don't auto-retry — log + skip turn matches v4 behavior. Reconnect semantics revisit in Phase 16 (verification gate) if soak tests reveal a gap.)_
**Plans:** 5 plans
Plans:
- [x] 04-01-PLAN.md — agent persona + config + LLM factory + TTS chain (OpenRouter monkey-patch)
- [x] 04-02-PLAN.md — DJCoHostAgent + PlaybackQueueAudioOutput (multimodal llm_node + TTS sink)
- [x] 04-03-PLAN.md — runtime loops (coach event pump + diag meter + WS mascot bus)
- [x] 04-04-PLAN.md — __main__ orchestrator + CI integration smoke
- [x] 04-05-PLAN.md — 12-gate verification + phase SUMMARY + ROADMAP/STATE advance

### Phase 5: FastAPI Proxy + Install-UUID JWT
**Goal**: `api.altidus.world` hosts the Gemini proxy with install-UUID JWTs, slowapi rate limiting, and Redis quotas. The client never holds a raw Gemini key. (Parallelizable with Phases 1-4 — proxy work is independent FastAPI route work on existing Bravoh infrastructure.)
**Depends on**: Nothing (parallel track; integrate with Phase 4 once routes are deployed).
**Requirements**: ARCH-08, ARCH-09, ARCH-10.
**Success Criteria** (what must be TRUE):
  1. `POST /vibemix/v1/auth/token` issues an install-UUID JWT (15-30 min TTL) on first launch and the client stores it in macOS Keychain / Windows CredLocker via `keyring`.
  2. `POST /vibemix/v1/gemini/generate-content` (SSE) and `POST /vibemix/v1/gemini/tts` (chunked PCM) pass-through Gemini calls with the real `GEMINI_API_KEY` resolved server-side from environment; the client never sees an `AIza` string.
  3. Rate limit kicks in at 60 rpm / 2000 rpd per install-UUID, enforced via slowapi + Redis token bucket; a load test exceeding the cap returns HTTP 429 and the client surfaces a clear "rate limited" status pill.
  4. Server-side cost dashboard logs every request (timestamp, client-UUID, IP, model, prompt size, response size); a daily aggregate alert fires if any UUID exceeds 3σ of baseline.
**Plans:** 5 plans
Plans:
- [ ] 05-01-PLAN.md — proxy scaffold (FastAPI + healthz + pydantic-settings + Redis quota + Dockerfile + compose)
- [ ] 05-02-PLAN.md — JWT auth (HS256 only) + /register + slowapi limiter wiring
- [ ] 05-03-PLAN.md — LLM SSE + TTS PCM proxy routes (gemini-native paths, circuit breaker, secret sanitization)
- [ ] 05-04-PLAN.md — client install_uuid + JWT cache + proxy-mode factory dispatch (no silent fallback)
- [ ] 05-05-PLAN.md — deployment runbook + 8-gate verification + phase close

### Phase 6: Genre-Aware Phase Detection
**Goal**: Per-genre profile JSON (techno / house / D&B / disco / pop) drives a percentile-based phase detector that replaces absolute RMS thresholds. Crest-factor compression detection, BPM half/double validator, and vocal-section gating land here.
**Depends on**: Phase 3 (MusicState/EventDetector exist to be hardened).
**Requirements**: SENSE-03, SENSE-04, SENSE-06, SENSE-07, SENSE-08, SENSE-10, UX-03.
**Success Criteria** (what must be TRUE):
  1. `genre_profiles.json` ships with 5 genres (techno / house / D&B / disco / pop), each with `bpm_range`, `drop_rms_percentile`, `build_dur_s`, `drop_sub_share` calibrated against ≥30 minutes of recorded sets per genre.
  2. Per-genre replay validation harness scores ≥85% event-timing F1 (drop/build/breakdown detected within ±2 seconds of ground-truth) on the held-out validation set for all 5 genres.
  3. Vocal-section detector correctly gates AI talk over lyrics on a 10-minute pop/D&B mixed clip — zero AI utterances start during a vocal segment (verified by overlaying `events.jsonl` AI text events on a manual vocal-segment annotation).
  4. BPM half/double validator stabilizes within 3 seconds of a track change (no 70 / 140 oscillation when track is steady-state 140 BPM).
**Plans**: TBD

### Phase 7: Windows Port (Audio + Screen)
**Goal**: Windows feature parity for audio capture (PyAudioWPatch WASAPI loopback — no virtual cable needed) and screen capture (`mss` + `pywin32` EnumWindows). Sample-rate sanity test catches BlackHole-Sonoma-like rate halving on both OSes. (Parallelizable with Phase 6 — independent platform implementations once Phase 1 protocols are pinned.)
**Depends on**: Phase 1 (protocols), Phase 2 (audio-core port).
**Requirements**: AUDIO-02, AUDIO-03, AUDIO-04, AUDIO-05, SCREEN-02, SCREEN-06.
**Success Criteria** (what must be TRUE):
  1. On a fresh Windows 11 machine with no virtual cable installed, vibemix captures system audio via WASAPI loopback (`get_default_wasapi_loopback()`) without user-driver install.
  2. Master output device auto-detect picks the correct default playback device on both OSes — verified on macOS with built-in speakers, USB DAC, and AirPods + on Windows with built-in speakers, USB DAC, and Bluetooth headphones.
  3. 1kHz sample-rate sanity tone test at startup detects mis-rated loopbacks (peak not at 1kHz ± 5%) and surfaces a recalibration prompt — catches BlackHole Sonoma half-rate bug on macOS and WASAPI sample-rate mismatch on Windows.
  4. Output destination picker disables mic capture in speakers mode (P12 feedback-loop prevention) — verified on Windows speakers test that no `KAAN_SPOKE` events fire during AI TTS playback.
**Plans**: TBD

### Phase 8: macOS ScreenCaptureKit Migration
**Goal**: Replace deprecated `Quartz.CGWindowListCreateImageFromArray` (obsoleted in macOS 15.0) with `pyobjc-framework-ScreenCaptureKit` for forward-compat to macOS 16+. Keep `Quartz.CGWindowListCopyWindowInfo` for window enumeration. (Parallelizable with Phases 6-7.)
**Depends on**: Phase 1 (platform protocols), Phase 3 (screen-buffer consumer).
**Requirements**: SCREEN-01 (macOS-side specifically).
**Success Criteria** (what must be TRUE):
  1. macOS 15.0+ screen capture works via ScreenCaptureKit callback API — verified by capturing a Rekordbox window on macOS Sequoia and getting valid JPEG bytes at 1Hz.
  2. macOS 12.3-14.x compatibility preserved (ScreenCaptureKit available since macOS 12.3); macOS 11 drop is documented in README minimum-OS notes.
  3. Window picker enumeration continues to work via `Quartz.CGWindowListCopyWindowInfo` (the enumeration API was not deprecated; only image-capture was).
  4. Screen-capture privacy gate is enforced — the wizard mandates user picks a specific DJ-app window; no full-screen fallback exists in the shipping code path (P13 prevention).
**Plans**: TBD

### Phase 9: MIDI Controller Library (10 + Generic Fallback)
**Goal**: 10 curated controller mappings ship with magnitude-aware EQ/fader events. Generic-MIDI fallback works for unmapped controllers. Hot-plug re-enumeration every 2 seconds catches devices plugged after launch. (Parallelizable with Phases 6-8 — data-entry-shaped work behind the MIDI base from Phase 3.)
**Depends on**: Phase 3 (`ControllerState` + `midi/` base exists from POC port).
**Requirements**: MIDI-01, MIDI-02, MIDI-03, MIDI-04, MIDI-05, MIDI-06, MIDI-07, MIDI-08, MIDI-09, MIDI-10, MIDI-11, MIDI-12, MIDI-13, MIDI-14.
**Success Criteria** (what must be TRUE):
  1. All 10 controllers auto-detect on plug-in via name matching; each maps EQ low/mid/high knobs, channel faders, crossfader, play/cue/sync buttons, hotcue pads, filter knobs, tempo faders, jog wheel events.
  2. Magnitude-aware EQ events fire with the delta semantic — a small high-boost on FLX4 emits `{"type": "EQ_MOVE", "channel": "A", "band": "high", "magnitude": 0.15}` and Coach prompts can render it as "slight high boost" vs "killed the lows" (`magnitude > 0.7`).
  3. Generic-MIDI fallback ingests any unmapped controller with positional inference (CC numbers fronted as "knob_1 / knob_2 / fader_1") and Hype-man mode still produces grounded reactions (less semantic context but no crashes).
  4. Hot-plug: plugging a DDJ-FLX4 after app launch surfaces "controller connected" status within 2 seconds and binds the mapping without restart.
**Plans**: TBD

### Phase 10: Prompt Template Matrix (6 cells + Anti-Slop)
**Goal**: 6 prompt templates (Beginner/Intermediate/Pro × Hype-man/Coach) ship with the full anti-slop stack: negative dictionary hard bans, `TurnHistory` per-session anti-repetition ring, `<silence/>` short-circuit token, "describe-before-infer" anchoring, past-tense framing, reaction throttle, and Coach scorecard at session end.
**Depends on**: Phase 6 (genre-tuned grounding) + Phase 9 (controller-aware events) — prompt design depends on what evidence is reliably available.
**Requirements**: PROMPT-01, PROMPT-02, PROMPT-03, PROMPT-04, PROMPT-05, PROMPT-06, PROMPT-07, PROMPT-08, UX-02, UX-04, UX-05.
**Success Criteria** (what must be TRUE):
  1. 6 prompt template files exist (one per skill-tier × interaction-mode cell), each anchored to specific vocabulary (not "friendly hype DJ", but concrete phrases per persona) and each enforcing the same negative-dictionary bans ("amazing" / "awesome" / "great mix" / "let me know" / "delve" / "leverage" / "as an AI" + ~30 more).
  2. `TurnHistory` ring (port from `cohost.py`) injects last-N utterances into every prompt and the model demonstrably avoids reusing openers within a 10-minute session (regex grep on `events.jsonl` finds no duplicate opener strings).
  3. `<silence/>` short-circuit fires correctly — feeding the model a low-RMS-variance audio packet produces `<silence/>` instead of filler talk on ≥80% of "nothing happening" probes.
  4. Coach scorecard at session end is qualitative ("clean / decent / abrupt / train-wreck" bands), never numeric (regex grep on Coach output finds zero `\d+\/10` or `\d+\.\d+` score patterns).
  5. Per-event-type cooldown + max-rate cap (e.g. max 1 reaction per 30s) + vocal-section gate result in no AI utterances starting during lyrics on a 10-min mixed-genre test recording.
**Plans**: TBD

### Phase 11: Tauri Shell + Calibration Wizard
**Goal**: Tauri 2.x shell wraps the Python sidecar (PyInstaller `--onedir`) with IPC contracts in place. The 3-step calibration wizard (permissions → output device + sample-rate test → controller probe) runs on first launch on both OSes.
**Depends on**: Phase 7 (Windows platform), Phase 8 (macOS ScreenCaptureKit), Phase 9 (controller library for probe).
**Requirements**: ARCH-01 (Tauri shell aspect), DIST-05, UX-01, UX-11.
**Success Criteria** (what must be TRUE):
  1. Tauri shell launches the Python sidecar via `externalBin`; sidecar lifecycle (spawn, restart, log capture) works on macOS + Windows; sidecar crashes surface in a "vibemix-core stopped — restart?" UI banner.
  2. IPC + WS contracts documented in `ui_bus/messages.py` mirror the TypeScript types in `tauri/ui/src/ipc/`; both languages agree on schemas (verified by a build-time schema check).
  3. 3-step calibration wizard completes on a fresh non-dev macOS machine in under 90 seconds: permissions granted (Screen Recording + Microphone) → output device picked + 1kHz sanity tone passes → controller detected (or generic fallback acknowledged) → smoke test plays one AI greeting in headphones.
  4. Wizard handles missing BlackHole on macOS by offering a one-click install link to existential.audio and re-running the audio detection step.
**UI hint**: yes
**Plans**: TBD

### Phase 12: Live Session UI + Settings Panel
**Goal**: The in-session UI (meters, phase tape, AI transcript, drop countdown, MIDI event ribbon) and Settings panel (voice / mode / genre / output picker + recording retention + push-to-mute hotkey + status badges) ship with the mocks/vibemix-app-ui.html design contract.
**Depends on**: Phase 11 (Tauri shell exists).
**Requirements**: UX-06, UX-07, UX-08, UX-09, UX-10, UX-11.
**Success Criteria** (what must be TRUE):
  1. Live session UI renders real-time meters + phase tape + AI transcript scroll + drop countdown + MIDI event ribbon at 30 fps, driven by the WS bus on `127.0.0.1:8765`; no lag visible on a Retina display during a 60-minute session.
  2. Settings panel allows mid-session changes to voice / mode / genre / output without restart (genre change re-loads the profile, voice change applies on next TTS turn); settings that require restart show a clear "restart to apply" badge.
  3. Push-to-mute hotkey works system-wide while app focused; one keypress silences the AI mid-utterance (drains PlaybackQueue) and a second keypress un-mutes; recording continues regardless.
  4. Status badges (LiveKit ok / Gemini ok / MIDI ok / screen ok) reflect real component health from heartbeats; pulling the controller USB cable flips MIDI badge red within 2 seconds.
  5. UI adheres to the `frontend-enforcement` skill: 20/80 rule (single dominant tone + minority phosphor-amber accent), textured materials (anodised charcoal + brushed-aluminum gradients), retro-futurist hardware vocabulary (segment LEDs, knurled-knob shadows, scanlines) — no Inter / no default Tailwind purple gradients / no rounded-2xl-p-6 cards.
**UI hint**: yes
**Plans**: TBD

### Phase 13: Reactive Mascot (Avery)
**Goal**: Avery the SVG mascot is a first-class feature, not decoration. Lives in the main session UI corner + larger render in the calibration wizard. Reacts physically to MIDI events with magnitude-aware intensity, syncs mouth to TTS audio level, eye-tracks the most-recent control the user touched, and beat-syncs subtle bounce on the kick.
**Depends on**: Phase 12 (UI shell + WS event bus).
**Requirements**: MASCOT-01, MASCOT-02, MASCOT-03, MASCOT-04, MASCOT-05, MASCOT-06, MASCOT-07.
**Success Criteria** (what must be TRUE):
  1. Avery's full pose vocabulary renders distinctly and on-character (idle / alert / speaking / squint / cover-ears / puff-up / wavy / lean-left / lean-right / punch-up / freeze / bounce / zipped / shocked / dancing / sleeping / winking) — every pose deliberate, no procedurally-rigid limb interpolation.
  2. MIDI events trigger named poses with magnitude-aware intensity within 150ms: bass-kill triggers cover-ears, high-EQ slam triggers squint, crossfader sweep triggers lean (left/right per direction), bass-push triggers puff-up.
  3. Mouth animation tracks live TTS audio RMS at ≥30Hz during AI utterances; mouth is closed (idle/zipped pose) when AI is silent.
  4. Eye-tracking visibly follows the most recent control the user touched on the controller — a knob move on Deck B pulls Avery's gaze right; a fader move on Deck A pulls it left.
  5. Beat-sync subtle bounce activates during groove/peak/drop phases at the detected BPM and pauses during silent/low/breakdown.
**UI hint**: yes
**Plans**: TBD

### Phase 14: FL-Studio Polish Phase (Critique → Execute Loop)
**Goal**: Every UI surface is lifted to pro-audio-software realism (FL Studio / Ableton / Bitwig / Native Instruments hierarchy). Critique → execute → critique → execute loop runs inside this phase with `gsd-ui-checker` + `gsd-ui-auditor` between iterations until the retro-futurist-hardware bar passes. This is NOT a final-week sweep — it is an explicit phase that gates Phase 16's verification.
**Depends on**: Phase 12 (live session UI), Phase 13 (mascot).
**Requirements**: POLISH-01, POLISH-02, POLISH-03, POLISH-04, POLISH-05, POLISH-06.
**Success Criteria** (what must be TRUE):
  1. `gsd-ui-checker` passes with zero findings on a fresh capture of every surface (calibration wizard, live session UI, settings panel, recording browser, mascot frames).
  2. `gsd-ui-auditor` passes the 20/80 rule audit (single dominant tone + minority accent — phosphor amber on anodised charcoal), the textured-material audit (no flat #1a1a1a fills), and the typography pairing audit (distinctive display font + intentional body pairing, no Inter / no system-ui).
  3. Knob/fader physics have momentum + detent feel + magnitude-mapped visual response matching pro-audio-software conventions; a side-by-side comparison screenshot against an FL Studio EQ knob is plausibly the same product family.
  4. Mascot pose vocabulary visually refined to character-design-document quality — every pose has deliberate silhouette, no procedural rigidity, no in-between frames that look broken.
  5. All copy passes the "no AI slop" filter per `frontend-enforcement` skill — no purple gradients, no Tailwind defaults, no rounded-2xl shadow-lg cards, no "amazing" / "awesome" / "let me know" microcopy anywhere in the chrome.
  6. Iteration loop is documented in `events.jsonl`-equivalent polish log: each `ui-checker` → fix → `ui-auditor` cycle is captured until both gates green.
**UI hint**: yes
**Plans**: TBD

### Phase 15: Recording & Session Capture Finalization
**Goal**: Per-session recording is locked: `recordings/<YYYYMMDD-HHMMSS>/` with `input.wav` (16kHz mono int16) + `voice.wav` (24kHz mono int16) + `events.jsonl` + `session.json` metadata. Recording browser UI lists/replays/deletes past sessions. Retention policy (default 7 days) is configurable in Settings.
**Depends on**: Phase 12 (Settings UI exists).
**Requirements**: REC-01, REC-02, REC-03, REC-04, REC-05, REC-06.
**Success Criteria** (what must be TRUE):
  1. A 60-minute session writes `input.wav` + `voice.wav` + `events.jsonl` with consistent timestamps; `events.jsonl` lines parse as valid JSON and reference the same session-start epoch as the WAV headers.
  2. Recording browser lists all sessions in `recordings/`, allows in-app replay (plays voice.wav with events.jsonl overlay), and allows delete-with-confirm.
  3. Retention policy: default 7-day expiry runs on startup; sessions older than the configured retention threshold are deleted; the Settings panel allows user to change the threshold and surfaces current disk usage ("Recordings: 12 sessions, 3.4 GB used").
  4. No regressions vs POC recording shape — a recording from the shipping `vibemix` binary opens cleanly in the POC's diagnostic tools.
**UI hint**: yes
**Plans**: TBD

### Phase 16: Hallucination Verification Gate
**Goal**: 30-session offline hallucination replay suite scores ≥95% grounded reactions before any installer build. Per-genre phase-detection F1 ≥85%. 60-minute soak test passes zero `session_error` events. Critique → execute → critique → execute loop runs against the suite until the gate passes.
**Depends on**: Phases 1-15 (verifies the integrated end-to-end product).
**Requirements**: VERIFY-01, VERIFY-03, VERIFY-05, VERIFY-06.
**Success Criteria** (what must be TRUE):
  1. 30-session offline replay suite (varied genres + controllers + skill modes) is graded by a second-pass LLM scorer + spot-checked by Kaan; ≥95% of AI reactions are "grounded in the audio/MIDI/screen evidence" per the rubric.
  2. Per-genre phase-detection accuracy ≥85% event-timing F1 on the validation harness for each of techno / house / D&B / disco / pop.
  3. 60-minute soak test on macOS + Windows passes zero `session_error` and zero `turn_error` entries in `events.jsonl`.
  4. Plan-checker passed before execute and verifier passed after execute for every plan in this phase; the critique-execute loop is documented in the phase's verification log.
**Plans**: TBD

### Phase 17: Reaction-Reel Slop Grading Gate
**Goal**: Hand-graded reaction reel — 30 minutes of varied DJing recorded with vibemix running — is blind-rated 1-5 by Kaan + Francesco + 2 DJ network friends. Pass requires ≥4.0 average with zero 1-2 ratings. This is the existential pre-release gate per PROJECT.md Core Value.
**Depends on**: Phase 16 (hallucination gate passed; otherwise slop grading is wasted on a still-buggy pipeline).
**Requirements**: VERIFY-02.
**Success Criteria** (what must be TRUE):
  1. A 30-minute reaction reel is recorded with all 5 genres + both interaction modes (Hype-man / Coach) + at least 2 skill modes represented.
  2. Reel is graded blind (graders don't see the codepath) by 4 raters (Kaan + Francesco + 2 DJ network friends) on 1-5 "would a real friend say this?" scale per AI reaction.
  3. Average rating ≥4.0 with zero 1-2 ratings across all reactions; if gate fails, Phase 10 (prompt-engineering) re-enters with iteration budget (up to 3 cycles) before considering scope-cut to Hype-man-only.
  4. Grading rubric is documented and the per-reaction scores + comments are archived for post-launch iteration reference.
**Plans**: TBD

### Phase 18: Distribution — Signing, Notarization, Installers
**Goal**: macOS DMG signed + notarized via Apple Developer ID + `notarytool` + Hardened Runtime + entitlements. Windows MSI OV-signed via SignPath Foundation (approved from day-1 application in Phase 1) + Inno Setup 6. Tauri auto-update wired with signed manifest. Binary attack verification confirms zero `AIza` key-leak.
**Depends on**: Phase 17 (gates passed — no signing of a sloppy build), SignPath approval from Phase 1.
**Requirements**: DIST-01, DIST-02, DIST-03, DIST-06, DIST-07, VERIFY-04.
**Success Criteria** (what must be TRUE):
  1. macOS DMG opens on a fresh non-dev macOS Sequoia machine without Gatekeeper modal; `spctl --assess --type execute vibemix.app` reports "accepted source=Notarized Developer ID"; `notarytool log` returns "Accepted".
  2. Windows MSI installs on a fresh non-dev Windows 11 machine without SmartScreen "unknown publisher" modal; `signtool verify /v vibemix-installer.msi` reports the SignPath OV chain valid.
  3. PyInstaller `--onedir` is used on both OSes (NOT `--onefile`); every nested `.exe` / `.dll` / `.dylib` in the bundle is individually signed; `codesign --verify --deep --strict vibemix.app` exits zero.
  4. Tauri auto-updater is signed (signed manifest URL); a manual test patches a 0.0.1 install to 0.0.2 without user intervention beyond the standard updater prompt.
  5. Binary attack verification: `strings vibemix-final-binary | grep -E '^[A-Za-z0-9_-]{39}$'` returns zero matches; `pyinstxtractor` unpack of the bundle reveals no `AIza...` strings anywhere; if any found, ship blocks.
**Plans**: TBD

### Phase 19: GitHub Launch Presence
**Goal**: `github.com/bravoh/vibemix` reads like a real product launch, not a code dump. Hero banner + demo video/GIF + install buttons + feature matrix + controller grid + screenshots + FAQ + Bravoh footer + Apache 2.0 LICENSE + full OSS hygiene (CONTRIBUTING with DCO, SECURITY, CODE_OF_CONDUCT, NOTICE, TRADEMARKS, issue templates, OG image, repo scrub).
**Depends on**: Phase 18 (installer + screenshots from shipping build).
**Requirements**: GH-01, GH-02, GH-03, GH-04, GH-05, GH-06, GH-07, GH-08, GH-09, GH-10, GH-11, GH-12, GH-13, GH-14, GH-15, GH-16, GH-17, GH-18.
**Success Criteria** (what must be TRUE):
  1. README opens with a branded hero banner (custom artwork — vibemix wordmark + tagline + screenshot), one-paragraph value prop above the fold, and a 30-45s demo video/GIF that loops cleanly.
  2. Install section has one-click download buttons for macOS + Windows pointing to the signed binaries on the Releases page; install GIFs demonstrate "from clone to running in <60s".
  3. Supported-controllers grid renders all 10 controller logos/photos; FAQ has 8-12 answered questions covering privacy, data, cost, why no Linux, why no Gemini Live, what's open-source, what isn't.
  4. License + OSS hygiene complete: Apache 2.0 LICENSE, NOTICE file, TRADEMARKS.md, SECURITY.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md with DCO sign-off requirement, bug / feature / new-controller-request issue templates.
  5. Repo scrub passes: zero `_test_*.py` scratch files, zero `.bak` files, zero committed `.env`, no large binaries in tree (mascot sprites + demo media in release assets or external CDN), repo description + topics tags (`dj`, `livekit`, `gemini`, `ai-assistant`, `audio`, `midi`, `pioneer-ddj`, `realtime-ai`) populated.
  6. Custom OG / social-preview image renders correctly when the repo URL is pasted into X / Discord / Slack previews.
**UI hint**: yes
**Plans**: TBD

### Phase 20: Day-Zero Operations
**Goal**: GitHub Actions CI matrix builds signed binaries on tag push for macos-14 + windows-latest. Fresh-machine install rehearsal passes on non-dev macOS + Windows. Second-responder rota covers the first 72 hours after launch for issue tsunami.
**Depends on**: Phase 18 (signed binaries exist), Phase 19 (repo presence complete).
**Requirements**: DIST-08.
**Success Criteria** (what must be TRUE):
  1. `git tag v0.1.0 && git push --tags` triggers the macos-14 + windows-latest CI matrix; both jobs complete green and produce signed binaries attached to the GitHub Release in under 30 minutes.
  2. Fresh-machine install rehearsal: a borrowed non-dev macOS machine + a borrowed non-dev Windows machine both run the signed installer end-to-end, complete calibration wizard, and successfully play one AI reaction within 10 minutes of download click.
  3. Second-responder rota is documented (Kaan + Francesco + Musa coverage windows) for first 72 hours; issue template auto-applies labels (bug / feature / new-controller-request); a Discord channel link is live in the README for community fast-path.
  4. Day-zero analytics dashboard (cost-per-user, error rate, install conversion) is wired on `api.altidus.world` admin panel and alerts on 3σ cost spikes or 1% binary-extraction `AIza` log hits.
**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Platform Protocol Firewall | 0/? | Not started | - |
| 2. Audio Core Port + Ring Buffer Fix | 0/? | Not started | - |
| 3. Sensing & State Port | 0/? | Not started | - |
| 4. LiveKit Cascade Agent Pivot | 5/5 | Complete | 2026-05-11 |
| 5. FastAPI Proxy + Install-UUID JWT | 0/? | Not started | - |
| 6. Genre-Aware Phase Detection | 0/? | Not started | - |
| 7. Windows Port (Audio + Screen) | 0/? | Not started | - |
| 8. macOS ScreenCaptureKit Migration | 0/? | Not started | - |
| 9. MIDI Controller Library (10 + Generic Fallback) | 0/? | Not started | - |
| 10. Prompt Template Matrix (6 cells + Anti-Slop) | 0/? | Not started | - |
| 11. Tauri Shell + Calibration Wizard | 0/? | Not started | - |
| 12. Live Session UI + Settings Panel | 0/? | Not started | - |
| 13. Reactive Mascot (Avery) | 0/? | Not started | - |
| 14. FL-Studio Polish Phase (Critique → Execute Loop) | 0/? | Not started | - |
| 15. Recording & Session Capture Finalization | 0/? | Not started | - |
| 16. Hallucination Verification Gate | 0/? | Not started | - |
| 17. Reaction-Reel Slop Grading Gate | 0/? | Not started | - |
| 18. Distribution — Signing, Notarization, Installers | 0/? | Not started | - |
| 19. GitHub Launch Presence | 0/? | Not started | - |
| 20. Day-Zero Operations | 0/? | Not started | - |

---

## Parallelization Map

Critical path: **1 → 2 → 3 → 4 → 11 → 12 → 14 → 16 → 17 → 18 → 19 → 20**

Parallel tracks (once Phase 1 protocols are pinned):
- **Phase 5 (Proxy)** runs in parallel with Phases 1-4 (independent FastAPI work on `api.altidus.world`).
- **Phase 6 (Genre Sensing)**, **Phase 7 (Windows Port)**, **Phase 8 (ScreenCaptureKit)**, **Phase 9 (MIDI Library)** all parallelize after Phase 3 lands.
- **Phase 13 (Mascot)** runs alongside Phase 12 (Live UI) once Phase 11 shell exists.
- **Phase 15 (Recording UX)** runs alongside Phase 12-13 (carries POC; lock UX).

SignPath OSS application is filed on **day 1 of Phase 1** (3-week approval lead time aligns with Phase 18 distribution).

---

*Last updated: 2026-05-11 after roadmap synthesis*
