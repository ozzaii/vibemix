# vibemix — Roadmap

**Project:** vibemix — AI DJ Co-Host
**Current milestone:** v2.0 Research-Driven Ship
**Roadmap generated:** 2026-05-14 by `gsd-roadmapper` (Opus, fine granularity)
**Phases in this milestone:** 12 (Phase 15 — Phase 26)
**Continues from:** v0.1.0 milestone (Phases 1-14, all shipped by 2026-05-13)
**Target ship:** ~3-4 weeks (before Bravoh public launch, ~early June 2026)

> **Methodology.** v2.0 phases derived from `.planning/REQUIREMENTS.md` v2.0 section (94 REQ-IDs) anchored to `.planning/research/SUMMARY.md` 12-phase decomposition, `.planning/research/FEATURES.md` cross-category dependency graph, `.planning/research/ARCHITECTURE.md` build-order analysis, and `.planning/research/PITFALLS.md` 41 critical/high/medium/low failure modes. Phase numbering CONTINUES from v0.1.0 (Phase 14 closed 2026-05-13).

---

## Critical-Path Note

**P21 (sign + notarize + release matrix) is the "binary becomes shippable" gate.**

Phases AFTER P21 can be cut to v2.0.1 if Bravoh-launch timeline (~early June 2026) is at risk. **Documented cut order if timeline at risk** (cut last-shipped first):

1. P26 (README + Day-Zero ops + Viral demo film) — minimum viable: README PR-ready, demo film as v2.0.1 fast-follow
2. P25 (Pyrekordbox XML + DEBRIEF slot) — DEBRIEF slot is hidden; Pyrekordbox UX-only
3. P24 (djay Pro Mac overlay) — viral demo Beat A; v2.0 ships without overlay but viral demo loses anchor
4. P23 (10-SKU MIDI library) — DDJ-FLX4 already verified; 9 SKUs ship "Mixxx-XML-derived" if not freshly sniffed
5. P22 (Mascot anticipation + hip-bob) — perceived-latency mask; downgrade to single-layer mascot if cut
6. **DO NOT CUT** P20 (linter ENFORCEMENT), P19 (latency stack), P18 (linter PROMPT-only), P17 (Hard Tek detectors), P16 (ear-test gate), P15 (recording browser) — these compound into the anti-slop ship gate.

---

## Phases

- [ ] **Phase 15: Recording Browser + Retention Enforcement** — Surface recording inventory, replay, delete, retention cron worker.
- [ ] **Phase 16: Hallucination Verification Gate (Kaan's DJ Ear)** — Calendar-blocking ear-test against shipped detector + linter + ack bank + mascot anticipation as they land.
- [x] **Phase 17: Hard Tek Detectors v1 + GenreRouter + MusicState Extension** — Six cross-genre detectors landed in v2.0 core, MusicState +4 fields, per-genre dispatch architecture. _Parallel with Phase 18._ (completed 2026-05-14)
- [x] **Phase 18: Evidence Registry + Citation Grammar in Prompts (v1.0 prompt-only)** — EvidenceRegistry sibling write-target, citation grammar EBNF locked, grammar baked into Gemini system instruction, citation_count telemetry shipped (no enforcement yet — corpus seeding). _Parallel with Phase 17._ (completed 2026-05-14)
- [ ] **Phase 19: Latency Stack v1 — Ack Bank + Cached Content + Cancel-and-Refire** — 40 OPUS samples + rotation deque + cached_content + prompt diet + `SpeechHandle.interrupt(force=True)` with hard cancel cooldown.
- [ ] **Phase 20: Citation Linter ENFORCEMENT (Live Mode)** — Response-level strip + ack-bank fallback + telemetry guard + prompt-side mitigation. Anti-slop contract goes live.
- [ ] **Phase 21: Sign + Notarize + GitHub Release Matrix** — Apple Developer ID DMG sign + notarize + SignPath OSS MSI + 4-target release matrix + Tauri updater signature audit. **Binary shippable at phase close.**
- [ ] **Phase 22: Mascot Anticipation Layer + Beat-Coupled Hip-Bob** — 4-layer simplified subset (mood + anticipation + speak/react) + 5 prep_* GLB clips + procedural hip-bob + timeout/cancel-aware crossfades. _Parallel with Phase 23._ Wave 0 = 1-day Gemini text-channel ordering spike.
- [ ] **Phase 23: 10-SKU MIDI Controller Library + MidiMapLoader** — JSON-per-SKU registry + verified sniff data for 9 SKUs + DDJ-FLX4 Sync note resolution + community sniff tooling. _Parallel with Phase 22._
- [ ] **Phase 24: djay Pro Mac Overlay Highlight** — Viral demo Beat A anchor. 12 hand-mapped pointable elements + AX-from-Rust-parent + 2nd Tauri WebviewWindow + window tracker @10Hz. Mac-only in v2.0. Wave 0 = 1-day AX-from-signed-bundle feasibility spike.
- [ ] **Phase 25: Pyrekordbox XML One-Shot Import + DEBRIEF Architectural Slot** — Durable library source (post-SQLCipher-breakage) + 4-tier fuzzy lookup confidence ladder + DEBRIEF `--debrief` sidecar flag + IPC schema reservations (UI feature deferred to v2.1). Wave 0 = `pyrekordbox==0.4.4` SQLCipher dep tree check.
- [ ] **Phase 26: README + Branding + Day-Zero Ops + Viral Demo Film + Channel Posts** — Composite launch phase. README full rewrite, fresh-VM rehearsals, Discord + issue templates + Bravoh proxy load test + 30s viral demo film + Twitter/IG/Reddit/HN posts + pre-seeded FAQ.

---

## Phase Details

### Phase 15: Recording Browser + Retention Enforcement
**Goal**: DJs can find, replay, and prune past session recordings without filling their disk.
**Depends on**: Phase 14 (CDJ Whisper v5 — UI primitives shipping)
**Requirements**: REC-07, REC-08
**Success Criteria** (what must be TRUE):
  1. User opens vibemix → Settings → Recordings → sees a chronologically-ordered list of past sessions with date, duration, and disk size; can click a row to reveal in Finder/Explorer.
  2. User can replay `voice.wav` (AI side) inline OR open `input.wav` (combined music + mic) in their default audio app from the same row.
  3. User can delete a session — confirm modal → row vanishes → directory removed from disk. _(NOTE: shipped as optimistic-remove + 4s undo toast per impeccable Wave 5.A 2026-05-14 critique — confirm-modal pattern superseded.)_
  4. Retention policy (default 7d, configurable in Settings) auto-prunes recordings older than the limit on sidecar startup AND every 6h; events.jsonl logs `retention_pruned: count=N, bytes=M`.
**Plans**: 4 plans (retroactive closure — surface partially shipped before plan-phase)
- [ ] 15-01-PLAN.md — Audit shipped surface against ROADMAP success criteria + lock criteria as new automated tests (Wave 1)
- [ ] 15-02-PLAN.md — Add periodic 6h retention sweep + events.jsonl retention_pruned logging (Wave 2; gap closure for criterion 4)
- [ ] 15-03-PLAN.md — Add reveal-in-Finder + open-input.wav-externally Tauri commands + UI buttons (Wave 2; gap closure for criteria 1+2)
- [ ] 15-04-PLAN.md — Kaan ear-test checkpoint, four-criterion sign-off, EAR-TEST log (Wave 3; phase-closure gate)
**Pitfall prevention**: None Critical (cheap, no upstream dependencies — knock it out first).
**UI hint**: yes

### Phase 16: Hallucination Verification Gate (Kaan's DJ Ear)
**Goal**: vibemix's reactions feel "real DJ friend in your ear" across 3-5 real DJ sessions — never hallucinating, never breaking flow, never AI slop.
**Depends on**: Phase 15 (something to record from)
**Concurrent with**: Phases 17, 18, 19, 20 — as each ships features, Phase 16 sessions consume them and feed tuning back. **Calendar-blocking**: schedule ear-test windows ahead of P22/P24 dependencies on its output.
**Requirements**: VERIFY-07, VERIFY-08, VERIFY-09, VERIFY-10
**Success Criteria** (what must be TRUE):
  1. Kaan completes ≥3 real DJ sessions (≥45 min each) with v2.0 features active; each session reviewed within 24h with structured pass/fail per detector class.
  2. `scripts/tune_detectors.py` CSV audit surface emits per-fire ground-truth annotation, fed back into P17 thresholds.
  3. Across 3 sessions: zero `linter_silence_streak > 2` events (Pitfall 2 ground-truth assertion).
  4. Kaan's qualitative sign-off — "this feels like a DJ friend, not AI commentary" — recorded in `.planning/phases/16-.../EAR-TEST-LOG.md` as the release gate.
  5. **Stretch (Pitfall 40 mitigation):** Francesco + 5-tester beta pool runs the same gate on 2+ sessions each before public ship.
**Plans**: TBD
**Pitfall prevention**: P2 (linter silence streak ground-truth), P10 (predictive misfire rate ear-gate), P40 (sample-size-of-1 stretch with Francesco + 5 testers).

### Phase 17: Hard Tek Detectors v1 + GenreRouter + MusicState Extension
**Goal**: Six cross-genre event detectors fire on the bar that defines the moment — closes Kaan's "feels surface-level" critique.
**Depends on**: Phase 6 (`MusicState`, EventDetector v4 baseline — shipped)
**Concurrent with**: Phase 18 (parallel bundle — both feed P19/P20 downstream)
**Requirements**: SENSE-11, SENSE-12, SENSE-13, SENSE-14, SENSE-15, SENSE-16
**Success Criteria** (what must be TRUE):
  1. `MusicState` carries `buildup_score`, `predicted_drop_in_sec`, `beat_phase`, `active_genre` — Phase 3 golden-equivalence tests stay green (backward-compat defaults).
  2. Six detectors fire with documented thresholds on curated reference tracks: `KICK_SWAP`, `SUB_LAYER_ARRIVAL`, `BREAKDOWN_KICK_KILL`, `REENTRY_KICK_LAND`, `KICK_DENSITY_SHIFT`, `PHRASE_BOUNDARY`.
  3. `PHRASE_BOUNDARY` locks downbeat phase within ±1 bar via band-limited (40-120Hz) autocorrelation; self-corrects on `BREAKDOWN_KICK_KILL`.
  4. `GenreRouter` atomically swaps detector-dict on `MusicState.active_genre` change without restarting session.
  5. `scripts/tune_detectors.py` reference-WAV tuning harness emits per-fire CSV consumable by Kaan ear-audit (Phase 16 input).
**Plans**: 6 plans across 6 waves (sequential — Wave 2/3/4 detector plans share `__init__.py` + `constants.py`, so they serialize)
- [x] 17-01-PLAN.md — MusicState +4 fields + state_refresh_loop writes (Wave 1; SENSE-13)
- [x] 17-02-PLAN.md — Kick-side detectors: KICK_SWAP / SUB_LAYER_ARRIVAL / KICK_DENSITY_SHIFT (Wave 2; SENSE-12)
- [x] 17-03-PLAN.md — Breakdown/re-entry pair: BREAKDOWN_KICK_KILL + REENTRY_KICK_LAND (Wave 3; SENSE-12)
- [x] 17-04-PLAN.md — PHRASE_BOUNDARY + 40-120Hz band-limited autocorr DSP module (Wave 4; SENSE-12, SENSE-14)
- [x] 17-05-PLAN.md — GenreRouter + per-genre dispatch under `vibemix/events/genres/` + EventDetector wiring (Wave 5; SENSE-11, SENSE-15)
- [x] 17-06-PLAN.md — `scripts/tune_detectors.py` reference-WAV harness + Hard Tek anchor track Kaan-action surface (Wave 6; SENSE-16)
**Pitfall prevention**: Per-genre cooldown tuning matches `G-followup-1` (`MIN_EVENT_GAP_PER_TYPE`); 6 baseline detectors only — Hard Tek-overlay `DISTORTION_CLIMB` + `ACID_LINE_ENTRY` deferred to v2.1 per cross-doc reconciliation.

### Phase 18: Evidence Registry + Citation Grammar in Prompts (v1.0 prompt-only)
**Goal**: Every Gemini reaction in v2.0 emits `[ev:.../@t]`-style citations grounded in real MusicState events — corpus seeding for Phase 20 enforcement.
**Depends on**: Phase 17 (detectors emit typed events) — or shipped IN PARALLEL with shared schema fixes.
**Concurrent with**: Phase 17 (parallel bundle)
**Requirements**: GROUND-01, GROUND-02, GROUND-03
**Success Criteria** (what must be TRUE):
  1. `EvidenceRegistry` is a SIBLING write-target to `MusicState` — `state_refresh_loop` and `EventDetector._fire` write synchronously every tick; no separate writer coroutine.
  2. Citation grammar EBNF locked: `[ev:<TYPE>@<t>]`, `[aud:<key>@<t>]`, `[midi:<event>@<t>]`, `[track:<id>]`, `[screen:<key>]`, `[mix:<derived>]`, `[tend:<profile-fact>]` + multi-citation form.
  3. Citation grammar baked into Gemini system instruction in `AICoach.build_prompt`; v1.0 = prompt-only seeding, NO enforcement yet — Gemini learns the shape in prod.
  4. `events.jsonl` records `citation_count_per_response` per AI turn; Phase 16 ear-test consumes the rolling average as Phase 20 readiness signal.
**Plans**: 4 plans across 4 waves
- [x] 18-01-PLAN.md — EvidenceRegistry skeleton + citation grammar regex (Wave 1; GROUND-01 + GROUND-02)
- [x] 18-02-PLAN.md — Wire registry into state_refresh_loop + EventDetector._fire as SIBLING write-targets (Wave 2; GROUND-01)
- [x] 18-03-PLAN.md — Citation grammar EBNF baked into Gemini system instruction + DJCoHostAgent threads snapshot (Wave 3; GROUND-02 + GROUND-03)
- [x] 18-04-PLAN.md — citation_count events.jsonl telemetry + rolling 50-turn average for Phase 16 readiness (Wave 4; GROUND-02)
**Pitfall prevention**: P12 (registry race) — single synchronous writer; ships v1.0 without enforcement so Gemini text-channel drift doesn't sustain false-strips before Phase 20's telemetry guard exists.

### Phase 19: Latency Stack v1 — Ack Bank + Cached Content + Cancel-and-Refire
**Goal**: Sub-300ms perceived first reaction + sub-2s actual voice-to-voice via prompt diet + Gemini context caching + 40-OPUS ack bank + cancel-and-refire — all without budget blowout.
**Depends on**: Phase 4 (LiveKit cascade), Phase 17 (priority-aware EventDetector)
**Requirements**: LATENCY-01, LATENCY-02, LATENCY-03, LATENCY-04, LATENCY-05, LATENCY-06, LATENCY-07, LATENCY-08, LATENCY-09, LATENCY-10, LATENCY-11, LATENCY-12, LATENCY-13
**Success Criteria** (what must be TRUE):
  1. Ack bank (40 OPUS, 5 event-class buckets) fires within 100ms of `EventDetector.detect()` return when `rolling_ttft_avg_ms > 800`; rotation deque (maxlen=10) per event class prevents same-sample-within-30s collisions on synthetic 60-fire burst.
  2. Gemini context caching active (`cached_content` via `extra_kwargs`); telemetry shows `prompt_cached_tokens > 0` sustained; cache lifecycle manager refreshes every 4 min (TTL 5 min minimum); system instruction padded above 1024 tokens with deterministic context.
  3. Prompt diet trims audio Part 18s→6s on non-PHASE events; screen Part skipped on MIX_MOVE/HEARTBEAT — observed TTFT win ≥500ms.
  4. `SpeechHandle.interrupt(force=True)` wrapper preempts in-flight generation on priority-bumped events (DROP=10 > MIX_MOVE=5); HARD cap `CANCEL_COOLDOWN_S = 8.0` + SOFT cap 30/session telemetry auto-disable.
  5. Synthetic burst-event harness (20 events in 30s) emits ≤3 `interrupted=True` outcomes; min-ack-to-response gap = 400ms enforced.
**Plans**: 4 plans
  - [x] 19-01-PLAN.md — Cancel-and-refire chokepoint + Event.priority field (LATENCY-10/11/12/13)
  - [x] 19-02-PLAN.md — Prompt diet — diet=True path + 6s audio window + screen skip (LATENCY-09)
  - [x] 19-03-PLAN.md — Gemini context caching — 1024-token floor + 4min refresh + invalidate hook (LATENCY-06/07/08)
  - [x] 19-04-PLAN.md — 40-OPUS ack bank — loader + per-bucket rotation + should_fire gate + placeholder generator (LATENCY-01/02/03/04/05)
**Pitfall prevention**: P1 (cancel-budget blowout — 8s cooldown cap + 30/session soft cap shipped WITH cancel-fire impl), P8 (ack rotation collision — deque + per-event-class buckets shipped WITH ack bank impl), P10 (predictive misfire rate — predictive firing OFF-by-default in v2.0 per project memory, telemetry guard pre-wired for v2.1 turn-on), P11 (1024-token floor — system instruction padding asserted on cache creation).

### Phase 20: Citation Linter ENFORCEMENT (Live Mode)
**Goal**: Anti-slop contract goes live — every spoken Gemini reaction is citation-validated against EvidenceRegistry; un-cited responses strip to ack-bank fallback.
**Depends on**: Phase 18 (EvidenceRegistry + grammar in prompts), Phase 19 (ack bank for fallback)
**Requirements**: GROUND-04, GROUND-05, GROUND-06, GROUND-07, GROUND-08
**Success Criteria** (what must be TRUE):
  1. `CitationLinter` (stdlib `re` only, no third-party dep) validates response-level against EvidenceRegistry; failing responses strip entirely and trigger ack-bank fallback via `PROMPT-09` integration.
  2. Telemetry guard: `stripped_rate_15s > 0.4` triggers next-response bypass with `[unverified]` log marker — verified by synthetic stripped-heavy session test; per-session `slop_ratio` metric surfaced via `ipc.session.citation` IPC message.
  3. Per-mode tolerance bands: ±1.0s live, ±2.0s debrief (Phase 25 reserves debrief slot).
  4. Prompt-side mitigation appended to live system instruction — "If you cannot cite, say 'I'm listening' — never reply with empty text" — Gemini fails toward graceful unsourced-but-honest line, not stripped void.
  5. Replay of recorded Kaan session through linter: `stripped_rate < 0.15` overall (Phase 16 ground-truth assertion).
**Plans**: TBD
**Pitfall prevention**: P2 (linter silence streak — telemetry guard + bypass + prompt mitigation all shipped Wave 1, NOT v2.x follow-up), P12 (registry race — async lock on read path matches Phase 18 sibling-writer contract), P18 (timestamp tolerance — ±1.0s live, ±2.0s debrief).

### Phase 21: Sign + Notarize + GitHub Release Matrix
**Goal**: vibemix v2.0 binary becomes downloadable from GitHub releases as a signed + notarized DMG (mac arm64 + intel) and SignPath-signed MSI (win x86_64 + arm64), with auto-update via Tauri updater.
**Depends on**: Phase 11 (PyInstaller --onedir sidecar shipped, AIza leak gate passing), Phase 14 (CDJ Whisper v5 UI complete). **CRITICAL PATH GATE — binary shippable at phase close.**
**Requirements**: DIST-09, DIST-10, DIST-11, DIST-12, DIST-13, DIST-14
**Success Criteria** (what must be TRUE):
  1. Signed + notarized DMG: `spctl --assess --type install vibemix.dmg` exits 0 on fresh non-dev macOS; `xcrun stapler validate` passes; first-launch shows NO Gatekeeper warning on a never-seen Mac.
  2. SignPath OSS MSI: Windows Defender SmartScreen does not hard-block on first launch on a fresh non-dev Windows 11 VM (reputation may still warn, but no hard block); SignPath application filed Day-1, approved by phase entry.
  3. GitHub Release page tagged `v2.0.0` includes all 4 binaries (macos-14 arm64 + macos-14 intel + windows-latest x86_64 + windows-latest arm64) with hand-written changelog; AIza scan runs across all new bundle paths and reports 0 matches.
  4. Tauri Updater `latest.json` ed25519-signed; `@tauri-apps/cli signer verify` exits 0 on synthetic manifest in CI; secret-name audit confirms `TAURI_UPDATER_KEY_PASSWORD` vs `TAURI_UPDATER_PRIVATE_KEY_PASSWORD` are aligned across release.yml + tauri.conf.json5.
  5. Updater manifest POST to `api.altidus.world/vibemix/updates/upload` succeeds end-to-end on a synthetic v2.0.0 → v2.0.1 update cycle on a fresh VM.
**Plans**: TBD
**Pitfall prevention**: P5 (Apple Issuer ID — Day-1 Kaan-action-required surface; Issuer ID `3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b` already supplied 2026-05-14; **Apple Developer Program Agreement update outstanding — Francesco-action-required** flagged in plan), P6 (SignPath OSS — application FILED Day-1 of phase, ~1-week SLA so block phase entry until approved), P7 (updater secret-name mismatch — explicit audit gate in plan), P17 (stapler missing — `xcrun stapler validate` in release gate), P31 (Day-0 rehearsal on fresh VM — overlaps with Phase 26).

### Phase 22: Mascot Anticipation Layer + Beat-Coupled Hip-Bob
**Goal**: Mascot leans forward 400-1200ms BEFORE Gemini voice arrives — masks perceived latency, sells AI as predictive not reactive — Beat B of viral demo.
**Depends on**: Phase 13 (mascot single-layer renderer), Phase 17 (`MusicState.beat_phase` + `active_genre`), Phase 19 (cancel-and-refire signal for prep-fadeout)
**Concurrent with**: Phase 23 (parallel bundle)
**Wave 0 (1-day Gemini text-channel ordering spike)**: Verify whether Gemini text channel arrives BEFORE TTS audio chunks via `livekit-plugins-google`. If verified, ships path for v2.1 inline emote-tag vocab. If NOT verified, fall back to event-detector-driven anticipation only (no inline tags).
**Requirements**: MASCOT-10, MASCOT-11, MASCOT-12, MASCOT-13, MASCOT-14, MASCOT-15, MASCOT-16, MASCOT-17, MASCOT-18, MASCOT-19
**Success Criteria** (what must be TRUE):
  1. 4-layer additive simplified subset (mood + anticipation + speak/react) wired via `AnimationUtils.makeClipAdditive`; full effect layer deferred to v2.1.
  2. Anticipation fires T+50ms from `EventDetector.detect()` — visible BEFORE Gemini round-trip on synthetic test; 5 new `prep_*` GLB clips authored with idle-zero lower-body delta.
  3. 2.5s anticipation timeout crossfades prep → `prep_settle` on Gemini misfire (NOT snap-back-to-idle — Pitfall 9 prevention); cancel-aware crossfade fires when `SpeechHandle.interrupt(force=True)` fires; linter-strip-aware crossfade fires when total-strip + ack-only fallback.
  4. Procedural hip-bob: `Hips` bone Y offset weighted by RMS, locked to `MusicState.bpm + beat_phase`; phase-locked >150 BPM, amplitude-driven <130 BPM; re-syncs on every downbeat detection.
  5. Three.js renderer p99 frame budget ≤22ms verified via vitest perf test on 60-event burst; GLB clip total budget ≤15MB asserted in CI gate.
**Plans**: TBD
**Pitfall prevention**: P9 (anticipation misfire — 2.5s timeout + cancel-aware + linter-strip-aware crossfades ALL shipped Wave 1, NOT v2.x polish), P19 (Three.js crossfade discontinuity — p99 ≤22ms perf budget), P20 (BPM phase drift — re-sync on every downbeat), P21 (emote tag text-vs-audio order — Wave 0 1-day spike BEFORE phase commits to inline-tag design), P23 (GLB clip size — ≤15MB CI gate).
**UI hint**: yes

### Phase 23: 10-SKU MIDI Controller Library + MidiMapLoader
**Goal**: vibemix understands EQ/fader/jog/cue events on the 10 most-popular bedroom-DJ controllers — universal grounding spine across every DJ app.
**Depends on**: Phase 9 (FLX4 verified + 9 JSONs shipped on Mixxx-XML basis)
**Concurrent with**: Phase 22 (parallel bundle)
**Requirements**: MIDI-15, MIDI-16, MIDI-17, MIDI-18, MIDI-19
**Success Criteria** (what must be TRUE):
  1. `MidiMapLoader` class replaces hardcoded `_CC_MAP`/`_NOTE_MAP` dicts; loads from `vibemix/midi/library/<sku>.json` — refactor passes Phase 9 FLX4 byte-equivalent golden replay.
  2. DDJ-FLX4 Sync note disambiguation resolved via 5-min mido sniff with Kaan present: chooses `0x60` (cohost_v4) vs `0x58` (Mixxx canonical) on the live hardware; both candidates documented in JSON with `verified=true`.
  3. Verified sniff data captured for DDJ-400, FLX6, FLX10, SX3, XDJ-RX3, Hercules Inpulse 300/500, Numark Party Mix Live, Numark Mixstream Pro+ — JSONs flagged `verified` vs `inferred` honestly.
  4. `scripts/sniff_controller.py` community contribution tooling captures CC + note + value-range for PR submissions; documented in `CONTRIBUTING.md` (P21 references this).
  5. Generic-MIDI fallback "observes, classifies conservatively, never invents" — logs activity in events.jsonl, never auto-assigns role inference past 5 min observation.
**Plans**: TBD
**Pitfall prevention**: P24 (9 untested SKU mappings — community PR sniff path + telemetry distinguishes verified-vs-inferred), P25 (DDJ-FLX4 Sync note disagreement — mido sniff resolution Day-1).

### Phase 24: djay Pro Mac Overlay Highlight
**Goal**: Amber ring fires on the exact djay Pro UI element the AI just cited — Beat A of viral demo ("AI points at the knob").
**Depends on**: Phase 11 (Tauri shell, capability allowlist), Phase 21 (signed bundle for AX inheritance test). **Mac-only in v2.0.**
**Wave 0 (1-day AX-from-Rust-parent feasibility spike on code-signed bundle)**: Verify kyleawayan/djay-pro-bridge pattern works on installed signed app (Pitfall 3 prevention) — not just `tauri dev`. If spike fails, phase blocks and degrades to percentage-of-window-rect coord_map only (still ships, accuracy degrades).
**Requirements**: OVERLAY-01, OVERLAY-02, OVERLAY-03, OVERLAY-04, OVERLAY-05, OVERLAY-06, OVERLAY-07, OVERLAY-08, OVERLAY-09
**Success Criteria** (what must be TRUE):
  1. AX bridge in Tauri Rust parent (`tauri/src-tauri/src/ax_bridge.rs`) — sidecar requests rect via `ipc.overlay.ax_position`; AX NEVER called from Python (codebase grep gate fails CI if `Quartz.CGWindowListCopyWindowInfo` or `AXUIElement` appears in `src/vibemix/runtime/highlight/`).
  2. Second Tauri `WebviewWindow` (label="overlay") with transparent + always_on_top + `set_ignore_cursor_events(true)` + decorations=false; window tracker @10Hz follows djay Pro window bounds (move/resize/fullscreen-Spaces detection).
  3. 12 hand-mapped pointable elements (mid/high/low EQ × 2 decks, gain, filter, fader, jog, play, cue, sync, tempo slider, hot cues) for djay Pro v5; element JSON shipped in `tauri/ui/src/overlay/elements.json`.
  4. Canvas 2D ring renderer (amber `--ring-active` token, fade-in 200ms, hold 800ms, fade-out 300ms); 8s cooldown per element + at-most-one-ring-per-3s utterance budget.
  5. Fullscreen-Spaces toast (Pitfall 4 mitigation) — when djay enters fullscreen, surface "Highlights work best in windowed djay — full-screen Spaces hide overlays (macOS limitation)" inline notice; dual-monitor coord-space all-Quartz no-NSScreen (Pitfall 13 mitigation).
**Plans**: TBD
**Pitfall prevention**: P3 (AX-from-sidecar — Rust grep gate + Day-1 AX-from-Rust-parent feasibility spike on signed bundle), P4 (fullscreen Spaces vanish — windowed-only toast + documentation), P13 (multi-monitor Y-flip — dual-monitor smoke test).
**UI hint**: yes

### Phase 25: Pyrekordbox XML One-Shot Import + DEBRIEF Architectural Slot
**Goal**: vibemix reads the user's Rekordbox collection.xml ONCE and grounds track citations in real BPM/key/cue data; DEBRIEF sidecar `--debrief` flag + IPC reservations ship as the v2.1 docking point (no UI surface in v2.0).
**Depends on**: Phase 5 (proxy quota for embed calls)
**Wave 0 (`pyrekordbox==0.4.4` SQLCipher dep tree check)**: Verify `pip install pyrekordbox==0.4.4` does NOT hard-require `sqlcipher3-wheels` at import; if it does, use `--no-deps` install path. SQLCipher path stays explicitly UNUSED.
**Requirements**: LIBRARY-01, LIBRARY-02, LIBRARY-03, LIBRARY-04, LIBRARY-05, LIBRARY-06, LIBRARY-07, LIBRARY-08, DEBRIEF-01, DEBRIEF-02
**Success Criteria** (what must be TRUE):
  1. User drag-drops or file-picks `collection.xml` in Settings → Library; `RekordboxLibrary` class parses TEMPO + POSITION_MARK nested elements (Rekordbox 5/6/7 schemas); ~5k tracks completes in <30s.
  2. SQLite cache at `$APPDATA/vibemix/library/rekordbox.db` with 3 tables (tracks, cues, beat_grid); SQLCipher path explicitly NEVER touched.
  3. 4-tier fuzzy lookup confidence ladder: exact → BPM-disambiguated → partial+artist → partial-only; artist OR BPM required for ≥0.7 confidence (Pitfall 16 mitigation); confidence-aware grounding renders "I think this is X" when <0.5; full `[track:<id>]` citation when ≥0.7.
  4. 30-day staleness nudge + lookup-fail counter (Pitfall 15) — UI surfaces "Looks like you've added new tracks — re-import to keep me grounded" after 30d OR after 10 lookup misses.
  5. DEBRIEF architectural slot: sidecar `--debrief <session_dir>` flag spawns separate child process on WS bus port 8766 (avoids 8765 collision); IPC schema reservations for `ipc.debrief.start`, `ipc.debrief.status`, `ipc.debrief.result` (3 messages, hidden in v2.0, surfaced in v2.1).
**Plans**: TBD
**Pitfall prevention**: P15 (Pyrekordbox staleness — 30-day nudge + lookup-fail counter), P16 (track title fuzzy collision — artist OR BPM required for ≥0.7 confidence), library intelligence v1 (sqlite-vec / embed pipeline) explicitly DEFERRED to v2.1 per project memory.
**UI hint**: yes

### Phase 26: README + Branding + Day-Zero Ops + Viral Demo Film + Channel Posts
**Goal**: vibemix v2.0 launches with a public-ready repo front door, fresh-VM-rehearsed day-zero ops, and the 30s viral demo + 4-channel post arsenal warming Bravoh's public launch wave.
**Depends on**: Phases 17-25 (everything that ships in the demo) and Phase 21 (signed binary)
**Requirements**: GH-19, GH-20, GH-21, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, OPS-06, OPS-07, OPS-08, VIRAL-01, VIRAL-02, VIRAL-03, VIRAL-04, VIRAL-05, VIRAL-06, VIRAL-07, VIRAL-08, VIRAL-09, VIRAL-10
**Success Criteria** (what must be TRUE):
  1. README full rewrite — value-prop paragraph above-the-fold + 30s demo GIF embedded + 12-question FAQ pre-seeded (anti-slop / anti-API-key / why-Gemini / Rekordbox-v2-roadmap) + 8-controller logo grid + badges row + install one-liner; hero PNG + architecture SVG already shipped (Phase 19 absorbed) — NEW asset = 30s demo GIF; CONTRIBUTING.md controller-mapping path references `scripts/sniff_controller.py`.
  2. Fresh-VM rehearsals recorded: clean macOS 14+ install (no dev cruft, no pre-installed BlackHole, no TCC pre-granted — Pitfall 31 mitigation) + clean Windows 11 install (AV/Defender SmartScreen reputation check); both as screencast artifacts.
  3. Day-Zero ops surface: Discord server (roles + channels — Pitfall 34); GitHub issue templates + auto-labeler (Pitfall 35); `api.altidus.world/healthz` curl gate Day-0 (Pitfall 32); Bravoh proxy load test (100 RPS for 5 min, p99 <500ms — Pitfall 30/39); adaptive cap + dashboard for proxy budget; 15+ pre-seeded friend/dev stars before public launch.
  4. 30s viral demo film recorded with 3 signature beats: Beat A (T+8s — amber overlay ring on mid EQ deck A synchronized with Gemini voice line citing the move); Beat B (T+14s — mascot leans forward 200ms BEFORE Gemini audio); Beat C (T+22-25s — 3 seconds of deliberate silence — anti-slop made visual); single take or curated multi-take, djay Pro 5 windowed mode, CDJ Whisper color, Kaan + DDJ-FLX4 + HD25 headphones.
  5. 4-channel post arsenal published: Twitter thread (Beat A hero) + IG Reels IT+EN (Beat B hero) + Reddit r/Beatmatch + r/DJs (Beat C hero, OSS angle) + HN Show HN (Beat A hero, engineering breakdown); pre-seeded FAQ per channel; GitHub stars ticker outro frame.
**Plans**: TBD
**Pitfall prevention**: P30 (Bravoh proxy viral RPM exhaustion — Pro key overflow + load test), P31 (Day-Zero rehearsal on fresh VM — screencast artifact), P32 (api.altidus.world undeployed — healthz curl gate), P33 (hero asset missing — demo film + GIF + OG image in repo at tag), P34 (Discord absent — Discord URL in README footer Day-0), P35 (GitHub Action triage gaps — issue templates + auto-labeler), P39 (free-tier budget breach — adaptive cap + Pro overflow + dashboard), P41 (Bravoh launch overlap slip — weekly slip review baked into milestone close gate).
**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 15. Recording Browser + Retention Enforcement | 0/4 | Planning | - |
| 16. Hallucination Verification Gate (Kaan's DJ Ear) | 0/0 | Not started | - |
| 17. Hard Tek Detectors v1 + GenreRouter | 6/6 | Complete   | 2026-05-14 |
| 18. Evidence Registry + Citation Grammar | 4/4 | Complete   | 2026-05-14 |
| 19. Latency Stack v1 | 3/4 | In Progress|  |
| 20. Citation Linter ENFORCEMENT | 0/0 | Not started | - |
| 21. Sign + Notarize + Release Matrix | 0/0 | Not started | - |
| 22. Mascot Anticipation + Hip-Bob | 0/0 | Not started | - |
| 23. 10-SKU MIDI Library + MidiMapLoader | 0/0 | Not started | - |
| 24. djay Pro Mac Overlay Highlight | 0/0 | Not started | - |
| 25. Pyrekordbox XML + DEBRIEF slot | 0/0 | Not started | - |
| 26. README + Day-Zero Ops + Viral Demo | 0/0 | Not started | - |

---

## Coverage

**v2.0 REQ-IDs:** 94 / 94 mapped ✓
**Orphans:** 0
**Duplicates:** 0
**Categories covered:** SENSE-11..16 (P17), GROUND-01..08 (P18 + P20), LATENCY-01..13 (P19), MASCOT-10..19 (P22), OVERLAY-01..09 (P24), LIBRARY-01..08 (P25), MIDI-15..19 (P23), DEBRIEF-01..02 (P25), REC-07..08 (P15), DIST-09..14 (P21), GH-19..21 (P26), OPS-01..08 (P26), VIRAL-01..10 (P26), VERIFY-07..10 (P16)

---

## Notes

### Cross-Document Reconciliations
- **Debrief timing** (PROJECT.md = v2.0 table-stakes vs FEATURES.md/SUMMARY.md cut to v2.1): **ship architectural slot in P25** (DEBRIEF-01 + DEBRIEF-02 — sidecar `--debrief` flag + port 8766 + 3 IPC schema reservations). Full UI feature lands in v2.1.
- **Event detector count** (PROJECT.md = 6 baseline vs G-followup-1 = 8 with 2 Hard Tek overlay): **6 baseline in P17 v2.0** (SENSE-12); 2 Hard Tek overlay (`DISTORTION_CLIMB`, `ACID_LINE_ENTRY`) deferred to v2.1 — already in REQUIREMENTS.md v2.1+ Deferred section.

### Wave 0 Day-1 Spikes Reserved In Plan Files
- **P22 Wave 0**: 1-day Gemini text-channel ordering spike (does text arrive before audio chunks via livekit-plugins-google?) — gates inline emote-tag vocab direction.
- **P24 Wave 0**: 1-day AX-from-Rust-parent feasibility spike on code-signed bundle (Pitfall 3 prevention) — verifies kyleawayan/djay-pro-bridge pattern works on installed signed app, not just dev.
- **P25 Wave 0**: `pyrekordbox==0.4.4` SQLCipher dep tree check — does it pull `sqlcipher3-wheels` on plain install? `--no-deps` needed?

### Critical Pitfalls Mapped Into Phase Plans
| Pitfall | Phase | Wave |
|--------|-------|------|
| P1 cancel-budget blowout | P19 | Same Wave as cancel-fire impl (NOT v2.x follow-up) |
| P2 silence-streak | P20 | Telemetry guard + prompt-side "I'm listening" mitigation shipped Wave 1 |
| P3 AX-from-sidecar | P24 | Day-1 spike + Rust grep gate |
| P4 fullscreen Spaces | P24 | Windowed-only toast + README docs |
| P5 Apple Issuer ID | P21 | Kaan-action surface (Issuer ID supplied; **Apple Developer Program Agreement update outstanding — Francesco-action-required**) |
| P6 SignPath OSS app filing | P21 | Day-1 file (~1-week SLA) |
| P7 Updater secret-name mismatch | P21 | Explicit audit gate |
| P8 ack rotation collision | P19 | Rotation deque + per-event-class buckets shipped WITH ack bank |
| P9 mascot anticipation misfire | P22 | 2.5s timeout + cancel-aware + linter-strip-aware crossfades |

### Parallel Bundle Ordering
- **P17 || P18** (parallel): both feed P19/P20 downstream; P17 = detectors emit events, P18 = grammar + registry seed prompts. Single-engineer interleaving possible.
- **P22 || P23** (parallel): mascot work (UI-heavy) parallel with MIDI sniff work (hardware-bench-heavy); ships any-order.

### Phase 16 Calendar-Blocking Note
Phase 16 starts AFTER P15 (so there's something to record from) but runs ALONGSIDE P17/P18/P19/P20 (as those phases ship features, P16 sessions consume them). Its tuning signal gates P22 mascot anticipation tuning + P19 cancel-cooldown calibration + P20 linter telemetry threshold (`stripped_rate > 0.4`) + P17 detector thresholds. Schedule Kaan's ear-test session windows AHEAD of phases that depend on its output.

### Deferred-Block Decisions (per memory `feedback_autonomous_no_grey_area_pause`)
- **Apple Developer Program Agreement update**: Francesco-action-required; flagged as Kaan-action-required surface in P21 plan rather than blocking roadmap creation.
- **SignPath OSS application status**: assumed STILL outstanding from v0.1.0 Phase 1 carry-forward; P21 plan re-files Day-1 if not confirmed approved.
- **Predictive drop firing default**: OFF-by-default in v2.0 per project memory `feedback_no_scope_creep_clean_utility`; telemetry guard pre-wired for v2.1 turn-on after Phase 16 ear-test baseline.

---

*Roadmap generated 2026-05-14 by `gsd-roadmapper` (Opus, fine granularity). Source-of-truth artifacts: `.planning/PROJECT.md` (v2.0 milestone), `.planning/REQUIREMENTS.md` (94 v2.0 REQ-IDs), `.planning/research/SUMMARY.md` (12-phase decomposition), `.planning/research/FEATURES.md` (7-category catalog + dependency graph), `.planning/research/ARCHITECTURE.md` (IPC schema delta + build-order graph), `.planning/research/PITFALLS.md` (41 pitfalls + pitfall-to-phase mapping), `.planning/research/STACK.md` (5 new deps + license + install impact).*
