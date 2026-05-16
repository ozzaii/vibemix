# Requirements: vibemix v3.0 — Clean OSS Ship

**Defined:** 2026-05-16
**Core Value:** "Real DJ friend in your ear" — never hallucinating, never breaking flow, never AI slop.

**Goal:** Ship vibemix as a clean, useful, value-bringing open-source product — 500-1000+ GitHub stars in 30 days, warm the Bravoh waitlist, anti-slop credibility lock.

**Research basis:** 4-bucket parallel research swarm 2026-05-16 — `.planning/research/v3-buckets/{A-external-world, B-gemini-capabilities, C-internal-state, D-gate-and-visual}.md`.

---

## v3.0 Requirements

### Anti-Slop Audio Path (AUDIO)

- [x] **AUDIO-01**: Mic audio sent as separate 2nd Gemini multimodal Part — `mic_audio_buf` (12s ring) attached when KAAN_SPOKE event fires (per `cohost_v4.py:1791-1813` pattern; closes shipped `dj_cohost.py:332-340` gap where mic was labeled but absent) — **Plan 40-01 GREEN** (2026-05-16). 13 new tests pinning 1/2/3-Part contract + Pitfall 1 zero-fill + ring shape; 99 existing DJCoHostAgent tests regression-clean. Part 2 attach at `src/vibemix/agent/dj_cohost.py:417`. Three new constants in `src/vibemix/audio/constants.py` (MIC_AUDIO_PART_SECONDS / _RECENCY_S / _PRESENCE_RMS). `mic_part_attached` / `mic_part_skipped` recorder events for diagnostics.
- [x] **AUDIO-02**: 3s file-based source-track lookahead pipeline — `nowplaying-cli` + `mdfind` + `ffmpeg` extracts next 3s from track file on disk, attached as 3rd Gemini Part (per `cohost_v4_tr.py:624-779` `LookaheadProvider`); graceful skip on streaming-only tracks — **Plan 40-02 GREEN** (provider) + **Plan 40-03 GREEN** (wire-in). `LookaheadProvider` in `src/vibemix/audio/lookahead.py` with 8 hermetic tests; per-session lifecycle; 3rd Part attaches at `dj_cohost.py:417+` after the mic Part 2 line; graceful skip with `(None, meta)` contract pinned.
- [x] **AUDIO-03**: Event cooldowns re-tuned to v4 chat-tested values — `MIN_EVENT_GAP_PER_TYPE`: PHASE 18→10s, LAYER_ARRIVAL 16→10s, MIX_MOVE 20→14s, HEARTBEAT 70→45s, TRACK_CHANGE 6→5s
- [x] **AUDIO-04**: Prompt template documents the 3-Part contract — Part 1 = live BlackHole mix (audience perspective, all mix moves applied), Part 2 = mic (when present), Part 3 = source-file lookahead labeled `NOT YET HEARD BY AUDIENCE` — **Plan 40-03 GREEN**. `build_parts_description` builder in `src/vibemix/prompts/matrix.py` dispatches 4-way (1-Part baseline / 2-Part mic-only / 2-Part lookahead-only / 3-Part), explicit anti-prediction guard ("never react to P3 as if the audience has heard it"), 6 unit tests.
- [~] **AUDIO-05**: PGP key for `security@bravoh.com` generated + published to `keys.openpgp.org`; SECURITY.md points at real key (SEC-06-PGP discharge — pre-stage, no external clock) — Plan 40-05 engineering pre-stage GREEN (slot file + SECURITY.md retarget + runbook + dual-mode gate test); Kaan-discharge runbook in `KAAN-ACTION-LEGAL.md §AUDIO-05`
- [~] **AUDIO-06**: Tauri ed25519 updater key rotated to production value; pubkey committed in `tauri.conf.json5`; private key in GH secret `TAURI_PRIVATE_KEY` (TAURI-UPDATER-KEY discharge — pre-stage, no external clock) — Plan 40-05 engineering pre-stage GREEN (rotation comment + runbook + dual-mode gate test); Kaan-discharge runbook in `KAAN-ACTION-LEGAL.md §AUDIO-06`
- [~] **AUDIO-07**: BlackHole probe fresh-Mac smoke pass — Kaan creates fresh macOS user account, runs install wizard end-to-end, confirms BlackHole CTA fires (INSTALL-BLACKHOLE-PROBE discharge — pre-stage, no external clock) — **Plan 40-06 engineering pre-stage GREEN**: `probe_blackhole` emits `audio.probe.{detected,missing,cta_fired}` structured events + Pitfall 5 retry; 12 new tests. Kaan-discharge runbook in `KAAN-ACTION-LEGAL.md §AUDIO-07` (fresh-Mac walk).

### Latency Stack v2 (LAT)

- [x] **LAT-01**: `ModelRouter` config-driven seam — zero hardcoded `gemini-3-flash` anywhere in `src/vibemix/`; CI grep gate enforced; per-path SKU mapping (live coach / debrief / library auto-tag / embedding) — **Plan 41-01 GREEN**. `src/vibemix/llm/model_router.py` + `_router_config.py`; 9 literals migrated; grep gate in `scripts/release/check_no_hardcoded_model.sh` + `.github/workflows/model-literal-check.yml`.
- [x] **LAT-02**: Implicit caching default-on for static system prompt — strip explicit cache-create from `GeminiContextCache` for static prefix; keep explicit cache only for per-session evidence registry — **Plan 41-02 GREEN**. `padded_body()` retained (Pitfall 5 — pad invariant matters for implicit caching too); wall-clock `refresh_loop` deleted.
- [x] **LAT-03**: Explicit cache TTL raised to 60min; refresh-on-EvidenceRegistry-mutation only; remove v2.1 4-min refresh machinery — **Plan 41-02 GREEN**. `GEMINI_CACHE_TTL_S` 300s → 3600s; `EvidenceRegistry.on_mutation` with 5s debounce + 30s min-interval guard; `cache_hit` telemetry to `events.jsonl`.
- [x] **LAT-04**: LLM→TTS streaming pipe-through — `run_one_turn` refactored to consume `generateContentStream` SSE and pipe first sentence into TTS without awaiting full LLM completion (target: 200-400ms perceived savings) — **Plan 41-04 GREEN**. `_streaming_pipe.py` with bracket-depth-aware sentence boundary (Pitfall 1); `LLMToTTSDeltaMeter` per-turn; dual-phase gate with cancel-with-silence-pad on speculation mismatch.
- [x] **LAT-05**: Migration to Gemini 3.1 Flash TTS — 200+ audio tags, 300-500ms first chunk; expressive-tag DSL exposed in coach prompts (e.g. `[whisper]`, `[laugh]`, `[fast]`) — **Plan 41-04 GREEN**. `TTS_TAGS` tuple + 6-tag DSL in `src/vibemix/prompts/matrix.py`; OpenRouter Achird OPUS fallback chain preserved; public docs at `docs/prompts/tts-tags.md`.
- [x] **LAT-06**: Gemini Embedding 2 GA migration + MRL 768-dim truncation in `sqlite-vec` / numpy index — Phase 28 library index 4× smaller on disk; bit-identical top-K parity test preserved — **Plan 41-05 GREEN** (audit + parity + GA probe + migration script). Embedding 2 + 768-dim already shipped in v2.1; LAT-06 surfaces the audit + auto-bump probe for the `gemini-embedding-2` → `gemini-embedding-002` rename.
- [x] **LAT-07**: Flex inference tier routing for library indexing, debrief generation, eval-corpus replay (50% cost cut on batch paths); live coach stays Standard — **Plan 41-01 GREEN**. ServiceTier.FLEX wired for debrief / library_auto_tag / embedding paths; ServiceTier.STANDARD for live_coach + live_coach_tts.
- [x] **LAT-08**: `thinking_level=MINIMAL` (or `thinking=False`) enforced on live path — `LiveCoachClient` rejects override at runtime (avoids 7s+ TTFT regression) — **Plan 41-03 GREEN**. `validate_live_config` in `src/vibemix/llm/thinking_gate.py`; wired at 3 call sites (`llm_factory.py:32`, `llm_factory.py:60`, `dj_cohost.py:294`); 18 tests; FLEX-on-live Pitfall 3 defense in same validator.
- [x] **LAT-09**: 1-2 day Gemini 3.1 Flash Live spike with Proactive Audio enabled on real DJ clip — verdict written to `spikes/gemini-3-1-flash-live-music.md`; defer-to-v3.x toggle if it grounds, sealed-no if it doesn't

### Hallucination Gate v3 — Hybrid (GATE)

- [ ] **GATE-01**: 40/40 Achird OPUS files in ack-bank (close ACK-BANK-REMAINING-20 — ~$0.10 Gemini TTS quota when free-tier resets)
- [ ] **GATE-02**: VCR cassettes populated via one-time `VCR_RECORD_MODE=new_episodes` run (close EVAL-VCR-CASSETTES; CI no longer spends real Gemini cost on first PR)
- [ ] **GATE-03**: 6 × 30-min public-domain DJ session WAVs in `git-LFS` corpus (close EVAL-CORPUS-WAVS — 200 MB)
- [ ] **GATE-04**: Locked thresholds (F1≥0.80, substance≥0.65, cited-cosine≥0.40, bypass≤0.15, per-genre F1≥0.70) calibrated against real corpus on first canary run; recalibrate + re-sign if measured F1 outside ±0.10 locked range
- [x] **GATE-05**: Ear-test protocol codified — 30min minimum per session, ≥2 genres, structured "what felt slop?" capture template in `eval/ear-test-logs/`; ear-pass requires ≥2 sessions ≥2 genres within 14d window
- [x] **GATE-06**: `scripts/release/check_gate.sh` cut-criteria implemented — reads last 7 nightly scorecards + signed ear-test log; SHIP-CUT gate-2 blocks unless both green
- [x] **GATE-07**: Debrief window exposes ear-test capture surface — "rate this session for release-gate" toggle writes `eval/ear-test-logs/<session>.json` with structured "felt slop / felt scripted / felt late / felt generic" payload
- [x] **GATE-08**: P85 override-expiry Decision Log entry committed — autonomous-only override formally terminated; `cut_release.sh` reminder lines removed; `test_phase_16_override_expiry.py` retired / refactored to enforce hybrid regime
- [x] **GATE-09**: `eval/README.md` public-facing — documents hybrid regime, threshold values, judge architecture; redacts ear-test log content while documenting protocol (Plan 42-06: 163-line scannable README + 21 tests pinning threshold-mirror + privacy contract)

### Visual Ship Lock (VIS)

- [x] **VIS-01**: Tier-1 surface audit — session window, mascot overlay, wizard surfaces (6 onboarding steps), calibration / first-run — every interactive element passes paired `gsd-ui-checker` + `gsd-ui-auditor` with zero HIGH findings (critique→execute loop until green)
- [ ] **VIS-02**: Hover-state coverage sweep — every interactive element gets `--glow-faint` outer halo on hover; pinned via visual-regression test
- [x] **VIS-03**: `session/components/meter.ts` spectrum rebuild — hardware-LED-strip aesthetic with amber peak hold, silk-12 minor grid lines (replace web-app gradient)
- [ ] **VIS-04**: 5 `prep_*.glb` placeholder replacements via Mixamo retargets (ASSETS-MESHY-A/B + ASSETS-MIXAMO-RIG + ASSETS-PREP-REPLACE); total mascot bundle stays ≤ 25MB cap; per-clip 400KB-1.2MB
- [ ] **VIS-05**: Mood→animation pool runtime validation — Hype-man / Teacher / Coach pools wired to MANIFEST clips; 30s smoke test per persona with crossfades; idle-zero contract bone-level tests pass
- [ ] **VIS-06**: Mascot overlay perf — `data-blur-perf` honored on integrated GPU; `backdrop-filter` fallback ladder tested on Intel UHD + M1 base; 60fps p99 maintained
- [x] **VIS-07**: Memory + doc drift cleanup — `project_mascot_as_vtuber_personality_surface` memory updated from "DJ bat" → "Neon Rebel"; storyboard vocabulary (`vibemix-cinematic-storyboard.html`) aligned to CDJ Whisper v5 (Saira + glass, not Workbench + DSEG7)
- [x] **VIS-08**: Hero demo storyboard v5 alignment — re-mock UI chip overlay frames in `mocks/vibemix-cinematic-storyboard.html` to match shipped CDJ Whisper v5; finalize cut script + 8-cut shot list (≤8 cuts gate)
- [ ] **VIS-09**: Pre-production package handed to Francesco — shot list, audio capture plan (Gemini voice + ambient + headphone return separate), vibemix demo-mode config (deterministic event sequence for repeatable takes), 1080p+ 60fps 48kHz spec

### Launch Positioning + Pre-stage (LAUNCH)

- [ ] **LAUNCH-01**: README rewrite — "the only AI co-host that actually listens to your set" frontloaded above the fold; one-line opinionated pitch; hero artefact (static + demo.mp4 reference); "no AI slop" hook section; "built by DJs, runs on your machine, your audio doesn't leave it without you knowing" positioning
- [ ] **LAUNCH-02**: `EvidenceRegistry` citation strip surfaced in live UI — every AI reaction shows 2-3 word evidence tag (e.g. `[kick swap @ 2:33]`); click tag → debrief window opens with waveform region highlight; closes anti-slop receipts gap from §6.2 white-space
- [ ] **LAUNCH-03**: DJ-software-logo grid in README — rekordbox, Serato, Traktor, djay Pro, VirtualDJ, Mixxx; "works alongside whatever DJ app you already use" framing
- [ ] **LAUNCH-04**: Supported-controllers grid finalized — 10 mapped controllers with logos + "calibrate any other" callout for generic-MIDI fallback
- [ ] **LAUNCH-05**: In-app Bravoh funnel CTA — debrief window optional "join Bravoh waitlist" toggle; subtle, opt-in, not gating; signed-out telemetry default-off; UTM-tracked link to `bravoh.com/waitlist`
- [ ] **LAUNCH-06**: `bravoh` GitHub org standup — resolve Bravoh Enterprise billing flag (per `signpath-application.md`), create org, members provisioned; ready to receive transfer (SHIP-TRANSFER pre-stage)
- [ ] **LAUNCH-07**: SHIP-TWEET 5-channel copy review + sign-off — Kaan + Francesco mutual approval on `scripts/dayzero/launch_copy/{twitter,instagram,linkedin,reddit,discord}.txt`; no AI-slop language, "real tool not toy" framing
- [ ] **LAUNCH-08**: Discord auto-provision dry-run — `scripts/dayzero/discord_provision.py --dry-run` complete; Bravoh Discord bot token sourced + stored in GH secret; channels + roles defined; OPS-09 ready for live execution
- [ ] **LAUNCH-09**: Outreach calendar finalized — DJ TechTools + DDJ Tips + Mixmag editorial pitches drafted; r/DJs + r/Beatmatch + r/edmproduction Show HN cross-post plan; DJ TechTools Discord T-3 soft-launch slot reserved
- [ ] **LAUNCH-10**: Launch sequence T-7 → T+30 doc — T-7 pre-seed 15-20 stars from dev network, T-3 DJ TechTools Discord soft-launch, T-0 Show HN early-morning ET + cross-post, T+24h maintainer-answers-every-comment commitment, T+72h Substack "how we built it", T+7d "week-1 numbers" transparency post, T+30 SHIP-V1-DECISION review

### External Discharge + Public RC Publish (SHIP)

- [ ] **SHIP-01**: Apple Developer Program Agreement update signed by Francesco (DIST-09) — external clock blocker, P46 legal-capacity; submit Day 1 of v3.0
- [ ] **SHIP-02**: SignPath OSS Foundation application submitted Day 1 + approval received (DIST-11, Kaan, ~1-week SLA) — external clock blocker, P46 legal-capacity
- [ ] **SHIP-03**: DIST-19 — signed-binary smoke + `scripts/verify_signed.py --require-signed` on first real artifacts (cascades from SHIP-01 + SHIP-02)
- [ ] **SHIP-04**: INSTALL-VM-RUN — fresh-VM matrix via `tart` (macOS 12.3 / 14 / 15 + Win 10 / 11); signed binary install end-to-end walk; screenshots captured
- [ ] **SHIP-05**: INSTALL-60S-CHECK — `onboarding-stopwatch.ts` confirms ≤60s end-to-end onboarding on every VM
- [ ] **SHIP-06**: OPS-14-SERVER — Bravoh team deploys `POST /vibemix/updates/upload` + `GET /vibemix/updates/latest.json` + `GET /vibemix/healthz`; healthz cron `*/5 * * * *` on Bravoh server; auto-update + monitoring live
- [ ] **SHIP-07**: SHIP-CUT — `gh release create v3.0.0-rc1 --draft` after `cut_release.sh` 6-gate green (Gate-2 signed-binary check flips green from SHIP-03)
- [ ] **SHIP-08**: SHIP-TWEET — 5-channel social publish via `launch_trigger.sh --publish` on T-30 / T+0 / T+5 / T+24h cadence
- [ ] **SHIP-09**: SHIP-DISCORD — #announcements launch post + `discord_provision.py --real` execution
- [ ] **SHIP-10**: SHIP-TRANSFER — repo transfer to `bravoh/vibemix` via `gh api repos/.../transfer`
- [ ] **SHIP-11**: SHIP-ROTATE — 24h monitoring rotation execution per `docs/launch-rotation.md`
- [ ] **SHIP-12**: INSTALL-DEFENDER — Windows SmartScreen reputation propagation observed (passive, 1-2 wk post-signed release)
- [ ] **SHIP-13**: SHIP-V1-DECISION — Kaan signs off after RC1 ~2-week bake: cut `v1.0.0` / cycle `v3.0.0-rc2` / pause

---

## v3.x / Future Requirements

Deferred to post-v3.0 cycle. Tracked but not in current roadmap.

### Audience Expansion (v3.x)

- **MIXXX-01**: Mixxx OSC adapter — vibemix subscribes to UDP `:7777`, maps to existing `MusicState` schema (GPL-2 IPC-only, never link)
- **MIXXX-02**: Mixxx controller map transpiler — offline build-time XML+JS → vibemix semantic event JSON; ships under separate `vibemix-maps` GPL-2 repo; vibemix-core consumes as data
- **CONTROLLER-EXPAND**: 10 → 30+ controller library via Mixxx map corpus ingest (closes "10 controllers" promise; unlocks ~80% OSS DJ TAM)

### Pedagogy Depth (v3.x)

- **COACH-01**: Library coach drill packs — "harmonic mixing pratiği için library'nde bu 5 track Am ↔ C sırayla mix'le"
- **COACH-02**: Curriculum-mode lesson packs per user level (Beginner / Intermediate / Pro)
- **DEBRIEF-DEEP**: Post-session debrief depth — multi-session arc, weekly progress summary, energy-arc taxonomy lift (ai-remixmate inspiration, not dep)
- **SOUNDS-LIKE**: Multimodal "sounds like this" library search from live 30s phrase window (Gemini Embedding 2 multimodal RAG)

### Mascot Ecosystem (v3.x stretch)

- **HATCH-01**: `/hatch` user-gen mascot pipeline — Imagen / Hunyuan3D user-uploaded image → custom 3D mascot (Codex Pets pattern)

### Streaming + OBS (v3.x backlog)

- **OBS-01**: OBS browser source mascot path — README 2-line update (mascot.html already serves on `ws://127.0.0.1:8765`)
- **OBS-02**: `obs-websocket-py` uplink — vibemix events → OBS scene switch / lower-third subtitle
- **CAPTION-NINJA**: WebSocket → HTML overlay → OBS browser source pattern for AI subtitle track

### Audio Analysis Stretch (v3.x — gated on one-click-install)

- **BEAT-THIS-RUST**: Beat This! via Rust sidecar — non-Gemini beat-grid, closes "AI reacts off-beat" hallucination class; gated on install-size budget green/yellow check

---

## Out of Scope

Explicit exclusions for v3.0. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Stem separation (Demucs/Spleeter/htdemucs/Open-Unmix) | Install bloat, compute-heavy, explicit anti-scope-creep decision 2026-05-12; see `feedback_no_scope_creep_clean_utility` |
| CLAP / LAION-CLAP / MERT / OpenL3 / MusicNN | Gemini Embedding 2 is the only embedding model; `feedback_no_clap_use_gemini_embedding` hard rule |
| Pioneer ProDJ Link path | Niche club/touring DJ audience; 80-200MB install bloat (Node/Java sidecar); Kaan 2026-05-12: "doesn't bring great realistic value as in the live DJ" |
| DAW integration (Logic / Ableton / FL Studio) | Defer entirely — "next conquest" after DJ software |
| Mobile / iPad / iOS app | Desktop-only milestone |
| Custom voice cloning | Gemini TTS prebuilt voices only |
| Linux support | Niche audience; doubles platform engineering cost |
| Multi-language UI | English-only app chrome (AI itself speaks Gemini-supported languages) |
| Mascot.html as shipped UI | Stays as dev visualization / OBS-browser-source easter egg only |
| Real-time Twitch/YouTube hook | Recording for later sharing is enough |
| User-supplied Gemini API keys | Friction kills virality; Bravoh-managed key via proxy only |
| Gemini Live Native Audio as default | v3.x toggle if LAT-09 spike validates; default cascade unchanged |
| `/hatch` user-gen mascot in v3.0 | Deferred to v3.x stretch; single character + mood variation only |
| Retiring v2.1 ack-bank | Stable shipped surface; keep — close 20/40 quota gap only |
| Replacing EvidenceRegistry | Stable anti-slop foundation; v3 surfaces it in UI, doesn't redesign |
| Re-rolling Neon Rebel mascot | Ships as-is; Hunyuan3D + AccuRIG 2 noted for v3.x refresh if wanted |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUDIO-01..07 | Phase 40 | AUDIO-01 GREEN (40-01); AUDIO-05/06 pre-stage GREEN (40-05); 4 remaining (AUDIO-02/03/04/07) |
| LAT-01..09 | Phase 41 | Pending |
| GATE-01..09 | Phase 42 | Pending |
| VIS-01..09 | Phase 43 | Pending |
| LAUNCH-01..10 | Phase 44 | Pending |
| SHIP-01..13 | Phase 45 | Pending |

**Coverage:**
- v3.0 requirements: 57 total
- Mapped to phases: 57
- Unmapped: 0 ✓

---

*Requirements defined: 2026-05-16 — v3.0 "Clean OSS Ship" scoped after 4-bucket research swarm (`.planning/research/v3-buckets/A-D.md`). Critical path: Apple Dev Agreement (Francesco, P46) + SignPath OSS Foundation (Kaan, ~1-week SLA, P46) gate the public RC publish in Phase 45. P40-P44 parallelize around the external clock.*
