# vibemix — Roadmap

**Project:** vibemix — AI DJ Co-Host
**Current milestone:** **v3.0 — Clean OSS Ship** (active, scaffolded 2026-05-16)
**Last shipped:** v2.1 The Unified Cut — 2026-05-16 (status: `tech_debt` accepted — KAAN-ACTION-LEGAL pending RC publish)

---

## Milestones

- ✅ **v0.1.0 MVP Foundation** — Phases 1–14 (shipped 2026-05-13) — see `.planning/milestones/v0.1.0/`
- ✅ **v2.0 Research-Driven Ship** — Phases 15–26 (shipped 2026-05-14, tech_debt accepted) — see `.planning/milestones/v2.0-ROADMAP.md`
- ✅ **v2.1 The Unified Cut** — Phases 27–39 (shipped 2026-05-16, tech_debt accepted) — see `.planning/milestones/v2.1-ROADMAP.md`
- 🚧 **v3.0 Clean OSS Ship** — Phases 40–45 (planning, 2026-05-16) — see below

---

## v3.0 Clean OSS Ship — Active

**Goal:** Ship vibemix as a clean, useful, value-bringing open-source product — 500-1000+ GitHub stars in 30 days, warm the Bravoh waitlist, anti-slop credibility lock.

**Research basis:** 4-bucket parallel swarm — `.planning/research/v3-buckets/{A-external-world, B-gemini-capabilities, C-internal-state, D-gate-and-visual}.md`.

**Critical path:** Apple Dev Agreement (Francesco) + SignPath OSS (Kaan, ~1-week SLA) gate the public RC publish in P45. P40-P44 parallelize around the external clock.

### Phase 40: Anti-Slop Audio Port

**Goal:** Close the biggest engineering anti-slop gap — Gemini now hears Kaan's voice (mic as 2nd Part) and gets a 3s structural preview (source-file lookahead as 3rd Part); event cooldowns re-tuned to v4 chat-tested intuition. Pre-stage independent KAAN-ACTION items (PGP, Tauri updater key, BlackHole fresh-Mac probe).

**Requirements:** AUDIO-01..07

**Success criteria:**

1. KAAN_SPOKE events trigger a 3-Part Gemini request when local file available — Part 1: BlackHole 7s, Part 2: mic 12s, Part 3: source-file lookahead 3s. Prompt explicitly labels Parts.
2. Streaming-track sessions (no local file) gracefully degrade to 2-Part (live mix + mic) with zero ffmpeg errors logged.
3. Event cooldowns (PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT / TRACK_CHANGE) measured in `replay_harness.py` match v4 chat-tested values within ±1s.
4. PGP key published to `keys.openpgp.org`; Tauri ed25519 updater key rotated to production; BlackHole probe fresh-Mac walk passes.
5. v4 "harikaydı" baseline regression — ear-test pass on ≥1 real Kaan DJ session (Coach + Hype modes).

### Phase 41: Gemini SKU Upgrade + Latency Stack v2

**Goal:** Adopt 2026 Gemini deltas — ModelRouter seam, implicit caching, LLM→TTS pipe-through, 3.1 Flash TTS, Embedding 2 GA, Flex tier for batch paths. Target: end-to-end latency 5-10s → 3-5s; perceived latency 0-2s with P40 lookahead offset.

**Requirements:** LAT-01..09

**Success criteria:**

1. `ModelRouter` config-driven — zero hardcoded `gemini-3-flash` (CI grep gate); per-path SKU + tier wired (live coach Standard 3-Flash, debrief Flex 3.1-Pro, library auto-tag Flex 3-Flash, embedding Flex Embedding-2).
2. TTFT p95 < 500ms on live coach (tracked via existing `TTFTMeter`).
3. LLM first sentence streams to TTS with measured 200-400ms perceived savings (TTFT→first-TTS-chunk delta logged).
4. Embedding 2 GA + MRL 768-dim — P28 index 4× smaller on disk; bit-identical top-K parity test passes.
5. Flex tier billing visible on next batch run (library re-index, eval-corpus replay); €/mo CI gate stays under €50.
6. 3.1 Flash Live spike verdict written (`spikes/gemini-3-1-flash-live-music.md`) — go/no-go on optional v3.x toggle.

### Phase 42: Hallucination Gate v3 — Hybrid

**Goal:** Adopt hybrid gate — Phase 27 autonomous proxy fast-lane (PR + nightly canary) + Kaan-ear release-cut veto. P85 override formally retired; corpus + thresholds calibrated against real audio; ear-test capture wired into debrief.

**Requirements:** GATE-01..09

**Success criteria:**

1. 40/40 Achird OPUS files in ack-bank; VCR cassettes populated; 6 × 30-min DJ session WAVs in git-LFS corpus.
2. Threshold-lock values calibrated against real corpus — measured F1 within ±0.10 of locked values, OR thresholds re-locked with audit trail.
3. `scripts/release/check_gate.sh` enforces "7 consecutive nightly proxy-green + signed ear-test within 14d" before SHIP-CUT gate-2 passes.
4. Ear-test capture surface in debrief window writes `eval/ear-test-logs/<session>.json` with structured "what felt slop?" payload.
5. P85 Decision Log entry committed; `cut_release.sh` reminder lines removed; `test_phase_16_override_expiry.py` retired or refactored.
6. `eval/README.md` public-facing documentation drafted (redacts ear-test log content while documenting protocol).

### Phase 43: Visual Ship Lock

**Goal:** Lock CDJ Whisper UI to FL-Studio-grade polish; replace 5 mascot stub animations with Mixamo retargets; pre-produce 30s hero demo for launch hero. Three internal waves (UI / mascot / demo prep), critique→execute loop spanning the phase.

**Requirements:** VIS-01..09

**Success criteria:**

1. Tier-1 surfaces (session, mascot overlay, wizard, calibration) pass paired `gsd-ui-checker` + `gsd-ui-auditor` with zero HIGH findings after critique→execute loop.
2. `session/components/meter.ts` spectrum rebuild ships — hardware-LED-strip aesthetic with amber peak hold.
3. 5 `prep_*.glb` placeholders replaced with real Mixamo retargets (400KB-1.2MB each); bundle stays ≤ 25MB.
4. Mood→animation pool runtime validation green — 30s smoke per persona (Hype-man / Teacher / Coach) with crossfades; idle-zero contract bone-level tests pass.
5. Hero demo storyboard re-aligned to CDJ Whisper v5; pre-production package (shot list + capture plan + demo-mode config) handed off to Francesco.
6. Memory + doc drift cleaned — `project_mascot_as_vtuber_personality_surface` updated to "Neon Rebel"; storyboard mocks aligned.

### Phase 44: Launch Positioning + Pre-stage

**Goal:** README launch-ready; EvidenceRegistry citation strip visible in live UI (anti-slop receipts on screen); Bravoh funnel CTA placed; bravoh GH org stood up; SHIP-TWEET copy locked; Discord provisioning + outreach calendar finalized. Every pre-stage item discharged that doesn't require external clock.

**Requirements:** LAUNCH-01..10

**Success criteria:**

1. README hero section frontloads "the only AI co-host that actually listens to your set"; one-line pitch above fold; static screenshot or GIF in place (demo.mp4 references resolvable post-shoot).
2. Live UI shows 2-3 word evidence tag per AI reaction (`[kick swap @ 2:33]`); click → debrief opens with waveform region highlight.
3. DJ-software grid + controllers grid render in README; alt-text + accessibility checks pass.
4. `bravoh` GitHub org exists; billing flag resolved; ready to receive transfer.
5. SHIP-TWEET copy files signed off (Kaan + Francesco mutual approval) for all 5 channels (twitter/instagram/linkedin/reddit/discord).
6. Discord provision dry-run completes without errors; outreach calendar (DJ TechTools + DDJ Tips + Mixmag + Reddit + Discord T-3 soft-launch) populated.

### Phase 45: External Discharge + Public RC Publish

**Goal:** Apple Dev Agreement + SignPath OSS approvals land → cascading discharge (DIST-19 sign+verify → INSTALL-VM matrix → INSTALL-60S → SHIP-CUT v3.0.0-rc1) → social publish + Discord + repo transfer + 24h monitoring rotation → ~2-week bake → SHIP-V1-DECISION. KAAN-ACTION-LEGAL critical path.

**Requirements:** SHIP-01..13

**Success criteria:**

1. Apple Developer Program Agreement signed by Francesco; macOS signing secrets populated in GH.
2. SignPath OSS Foundation approval received; Windows signing secrets populated in GH.
3. First signed binaries produced (DMG + MSI); `scripts/verify_signed.py --require-signed` smoke passes.
4. INSTALL-VM-RUN matrix green on macOS 12.3 / 14 / 15 + Win 10 / 11; onboarding ≤60s per VM.
5. Bravoh `POST /vibemix/updates/upload` + `GET /vibemix/updates/latest.json` + `GET /vibemix/healthz` endpoints live with `*/5 * * * *` cron.
6. `gh release create v3.0.0-rc1 --draft` executed; 5-channel social publish complete; #announcements Discord post live; repo transferred to `bravoh/vibemix`; 24h rotation executed.
7. ~2-week bake observation period — Kaan signs SHIP-V1-DECISION (cut v1.0.0 / cycle RC2 / pause).

### Sequencing

```
P40 (Audio Port) ──┬─→ P42 (Hybrid Gate) ──┐
                   │                        │
P41 (Latency v2) ──┤                        ├─→ P44 (Launch Pre-stage) ──→ P45 (External + Publish)
                   │                        │
                   └────→ P43 (Visual) ─────┘
```

- **P40 + P41 parallel** — independent (audio path vs model layer).
- **P42 + P43 parallel after P40** — gate calibration depends on stable audio path; visual is independent of audio.
- **P44 after P43** — launch positioning needs final UI for screenshots + hero demo references.
- **P45 cascades** when Apple + SignPath approvals land — submit both Day 1 of v3.0.

---

## Phase History (Archived)

<details>
<summary>✅ v0.1.0 MVP Foundation (Phases 1–14) — SHIPPED 2026-05-13</summary>

See `.planning/milestones/v0.1.0/` for full archive.

</details>

<details>
<summary>✅ v2.0 Research-Driven Ship (Phases 15–26) — SHIPPED 2026-05-14 (tech_debt accepted)</summary>

12 phases shipped — 10 Claude-side end-to-end + 2 deferred to Kaan-action (Phase 15 Plan 04 UAT + entire Phase 16 ear-test gate). 38 plans, 1961 passing tests, 220 commits since `v0.1.0-rc1`, ~45.7k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`.

Full archive: `.planning/milestones/v2.0-ROADMAP.md` · Requirements: `.planning/milestones/v2.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v2.1 The Unified Cut (Phases 27–39) — SHIPPED 2026-05-16 (tech_debt accepted)</summary>

13 phases shipped engineering-green under `gsd-autonomous fully` mode. 96 plans, 633 phase-scope tests added, 225 commits since `v2.0` tag, net ~+45k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`, `docs/`, `eval/`. 105 / 105 v2.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

- [x] Phase 27: Eval Harness + v2.0 Carry-Forward Close-Out (9/9 plans, 140 tests) — completed 2026-05-15
- [x] Phase 28: Library Intelligence v1 (9/9 plans, 258 tests) — completed 2026-05-15
- [x] Phase 29: Post-Session Debrief MVP UI (9/9 plans) — completed 2026-05-15
- [x] Phase 30: 2 Hard Tek Detectors (4/4 plans, 45 tests) — completed 2026-05-15
- [x] Phase 31: 4-Layer Mascot Full Additive State Machine (8/8 plans, 17 mascot tests, GLB 21.67/25 MB) — completed 2026-05-15
- [x] Phase 32: Long-Term DJ Profile ~2KB JSON (6/6 plans, 67 tests, P51/P53/P60 enforced) — completed 2026-05-15
- [x] Phase 33: One-Click Install Hardening (9/9 plans, 50 tests; INSTALL-VM-RUN = KAAN-ACTION-LEGAL) — completed 2026-05-15
- [x] Phase 34: Open-Source Security Pass (10/10 plans, 63 tests) — completed 2026-05-15
- [x] Phase 35: Real GLBs + 30s Viral Demo Film (6/6 plans, 35 tests; real assets = KAAN-ACTION-LEGAL) — completed 2026-05-15
- [x] Phase 36: Day-Zero Operations Automation (6/6 plans, 36 tests; 6 real-execution items = KAAN-ACTION-LEGAL) — completed 2026-05-15
- [x] Phase 37: Cross-Phase Integration Audit Gate (6/6 plans, 42 tests; 5/5 seams WIRED) — completed 2026-05-15
- [x] Phase 38: Signing Pipeline Real Execution (6/6 plans, 58 tests; DIST-09 + DIST-11 = P46 legal-capacity carveouts) — completed 2026-05-15
- [x] Phase 39: Public RC Cut + Ship (8/8 plans, 91 tests; §SHIP × 6 + §POST-RC-CLEANUP × 3 = KAAN-ACTION-LEGAL) — completed 2026-05-16

Full archive: `.planning/milestones/v2.1-ROADMAP.md` · Requirements: `.planning/milestones/v2.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.1-MILESTONE-AUDIT.md`

</details>

---

## Progress

| Milestone | Phases | Status | Shipped |
|-----------|--------|--------|---------|
| v0.1.0 MVP Foundation | 1–14 | ✅ Shipped | 2026-05-13 |
| v2.0 Research-Driven Ship | 15–26 | ✅ Shipped (tech_debt) | 2026-05-14 |
| v2.1 The Unified Cut | 27–39 | ✅ Shipped (tech_debt) | 2026-05-16 |
| **v3.0 Clean OSS Ship** | **40–45** | **🚧 Planning** | — |

---

*Roadmap updated 2026-05-16 via `/gsd:new-milestone` — v3.0 scoped after 4-bucket research swarm. 6 phases (P40-P45), 57 REQ-IDs, critical path = external clock (Apple Dev Agreement + SignPath OSS).*
