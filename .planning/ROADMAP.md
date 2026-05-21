# vibemix — Roadmap

**Project:** vibemix — AI DJ Co-Host
**Last shipped:** v3.1 Distribution-Ready Pass — 2026-05-18 (status: `tech_debt` accepted — 7 Kaan-action carveouts ride the v3.0 external clock per `gsd-autonomous fully` mode)
**Current milestone:** v4.0 "SHIP" — Real-Hardware Bring-Up → Public Ship (planning)

---

## Milestones

- ✅ **v0.1.0 MVP Foundation** — Phases 1–14 (shipped 2026-05-13) — see `.planning/milestones/v0.1.0/`
- ✅ **v2.0 Research-Driven Ship** — Phases 15–26 (shipped 2026-05-14, tech_debt accepted) — see `.planning/milestones/v2.0-ROADMAP.md`
- ✅ **v2.1 The Unified Cut** — Phases 27–39 (shipped 2026-05-16, tech_debt accepted) — see `.planning/milestones/v2.1-ROADMAP.md`
- ✅ **v3.0 Clean OSS Ship** — Phases 40–45 (shipped 2026-05-17, tech_debt accepted) — see `.planning/milestones/v3.0-ROADMAP.md`
- ✅ **v3.1 Distribution-Ready Pass** — Phases 46–50 (shipped 2026-05-18, tech_debt accepted) — see `.planning/milestones/v3.1-ROADMAP.md`
- 🔨 **v4.0 SHIP** — Phases 51–58 (planning) — active below

---

## Overview

v3.1 left vibemix engineering-complete: a built Tauri app + Python sidecar, one-click installer chain, dependency-audited lockfile, full mascot scaffold, and an e2e harness — all green in CI, none of it yet driven on real hardware in a real DJ session. v4.0 closes that gap. For the first time the actual app runs on Kaan's MacBook with real audio through BlackHole and a real DDJ-FLX4 over USB.

The journey, finer-grained than the prior 4-phase cut so each real-hardware seam is its own validated checkpoint: **boot it and make it stable** (Phase 51) → **prove the audio path live and ground the features it derives** (Phase 52) → **prove the controller path live with clean fallback** (Phase 53) → **make hype mode actually fire grounded in-bar reactions on real audio** (Phase 54) → **make feedback mode coach grounded with clean citations** (Phase 55) → **hit peak performance + make the mascot react live** (Phase 56) → **final visual pass + close carryover bugs + tighten first-run** (Phase 57) → **get every engineering gate green on real artifacts and document the one-button ship** (Phase 58).

Bring-up is split into THREE input seams — boot/stability, audio, controller — because real hardware already surfaced distinct breaks in each (clean startup vs the 48 kHz capture path vs MIDI ingest), and each must be independently green before the modes that consume them can be validated. The two interaction modes get their own phases because hype and feedback have different failure shapes (hype: the AI voice currently does not fire on a detected drop; feedback: citation integrity), and each is its own Kaan-ear pass.

The signed public binary itself is gated on external signatures (Apple Dev Agreement via Francesco; SignPath OSS cert) — those stay KAAN-ACTION; engineering makes the release one-button-after-signatures. No phase depends on signatures landing.

This is bring-up + live validation + polish + ship of an **already-built** app. No new AI providers, no new detectors, no scope creep.

## Phases

**Phase Numbering:** Continues from v3.1 (closed at Phase 50). v4.0 starts at **Phase 51** and runs through **Phase 58**. Integer phases (51, 52, …) = planned milestone work; decimal phases (e.g. 54.1) = urgent insertions if needed.

- [x] **Phase 51: Real-Hardware Bring-Up** - Boot the app + sidecar on Kaan's Mac, reach a stable live "listening" session with clean startup logs, and survive a ≥30-min full-set run with zero unhandled exceptions or unbounded memory. ✅ 2026-05-21 — boot green, ws_bus empty-frame + stale-sidecar dev loop closed, soak harness shipped; review CLEAN; real ≥30-min live soak = KAAN-ACTION.
- [x] **Phase 52: Audio Path + Feature Grounding** - BlackHole 48 kHz capture is live end-to-end and every feature derived from it (levels, BPM, bands) is grounded — out-of-range values like the live BPM=200 read on a ~129 BPM track never reach the bus or UI. ✅ 2026-05-21 — BPM never exceeds 180 on harmonic-leak trace; psytrance profile + grounded DSP genre auto-detector (confidence-gated, `unknown` fallback, hysteresis) + genre on bus; review CLEAN; multi-genre live drive = KAAN-ACTION.
- [x] **Phase 53: Controller Live + Graceful Fallback** - DDJ-FLX4 MIDI is ingested live during a real session and the app degrades cleanly when the controller is unplugged. ✅ 2026-05-21 — closed the real gap: `start_port_watcher` now wired into the live session (was never spawned); `mark_disconnected` clears stale moves; single-state hot-plug callback (no rebuild divergence); review CLEAN; physical FLX4 plug/unplug drive = KAAN-ACTION.
- [x] **Phase 54: Hype Mode Live** - On real audio, hype (party) mode actually fires grounded, in-bar, non-slop reactions — the AI voice lands on real events (drops/builds) across ≥2 genres, cooldowns/latency tuned live so nothing comes late. ✅ 2026-05-21 — trace-replay regression pins the real captured trace's drop/build events fire through the REAL EventDetector (52/52 events→reactions, 0 suppressions) + a synthetic genre-2 build→drop, never on silence; `IN_BAR_TOLERANCE_S` named one-line knob + cooldown-respect pinned (no v4 value changed) + `--print-cooldowns` over the real trace; anti-slop spine pinned with REAL EvidenceRegistry+CitationLinter (empty evidence→no fire, unbacked citation→strip, grounded→emit) + grounded HYPE persona (no `phase=`); thin HYPE·LIVE indicator + reaction-cadence pulse (token-only, 20/80). Full suite 3768 passed; review CLEAN. Live ≥2-genre ear-pass + cooldown-tuning drive = KAAN-ACTION.
- [x] **Phase 55: Feedback Mode Live + Citation Integrity** - On real audio, feedback (coach) mode produces grounded, in-bar, non-slop coaching across ≥2 genres, and the EvidenceRegistry citation strip reflects real session events with zero orphaned or hallucinated citations. ✅ 2026-05-21 — LIVE-04 made airtight provable engineering: zero-orphan replay + hallucination-strip on a real non-empty registry + live/debrief consistency (REAL CitationLinter+EvidenceRegistry, no mocks); two telemetry stubs closed with REAL signals (cumulative stripped/total `slop_ratio` + actual stripped text from `StrippedRateTracker`, the `1/(1+mean)` placeholder gone). LIVE-02 coach grounding pinned across ≥2 genres (REAL EventDetector fixture + synthetic genre-2; empty evidence→no fire). Full suite 3821 passed; review 0 critical (WR-01 live/debrief test now drives the real `drills._citation_resolves` + IN-01 unified tolerance — both fixed). Live ≥2-genre coach ear-pass + live citation-strip drive = KAAN-ACTION (`55-HUMAN-UAT`).
- [ ] **Phase 56: Performance + Live Mascot** - TTFT within budget on real HW, no audio dropouts under live load, mascot + UI hold 60fps, and the Neon Rebel mascot reacts correctly to live audio/MIDI events in-session across its **many modes** (idle/groove/build/drop/breakdown/speaking), driven by the rich bus signals — not the loudness ramp it uses today.
- [ ] **Phase 57: Sexify Finish** - Final Tier-1 visual pass (zero HIGH findings), close v0.1.0-rc1 carryover bugs, tighten fresh-account first-run.
- [ ] **Phase 58: Ship Readiness** - All engineering release gates green on real artifacts, §E2E-50A-WALK discharged by driving the real app, one-button SHIP-CUT sequence documented + pre-verified with external-clock items surfaced as KAAN-ACTION.

## Phase Details

### Phase 51: Real-Hardware Bring-Up
**Goal**: The built app actually runs — boots to a live listening session on Kaan's MacBook, starts up clean, and survives a full-set run with every console/log error triaged and fixed. This is the foundation: nothing downstream can be observed until the app boots and stays up on real hardware.
**Depends on**: Nothing (first phase — everything downstream needs a running app)
**Requirements**: BRINGUP-01, BRINGUP-04, BRINGUP-05
**Success Criteria** (what must be TRUE):
  1. Launching the app on the real Mac reaches a live "listening" session with no boot crash.
  2. The Tauri console + sidecar logs are clean at startup — no unhandled exceptions, and the ws_bus no longer emits intermittent empty `{}` frames between real frames.
  3. Every runtime error observed in the Tauri console + sidecar logs during a real run is triaged and fixed — a full-set run completes with zero unhandled exceptions.
  4. A ≥30-minute continuous real session runs with no dropout, hang, or unbounded memory growth (RSS stays bounded across the run).
**Plans**: TBD
**Known issues to fold in**: ws_bus emits intermittent empty `{}` frames between real frames (bring-up cleanliness — close here).

### Phase 52: Audio Path + Feature Grounding
**Goal**: The live audio path is proven on real hardware — master output reaches the co-host through BlackHole at 48 kHz with levels registering in real time — AND every feature derived from that audio is grounded so the AI (and the UI) never sees a value that did not happen. The live BPM=200 read on a ~129 BPM track is the canonical bug to close: out-of-range values must never reach the bus/UI.
**Depends on**: Phase 51 (needs a stable, running session to route audio into)
**Requirements**: BRINGUP-02, GENRE-01, GENRE-02
**Success Criteria** (what must be TRUE):
  1. Real master output routed through BlackHole reaches the co-host at 48 kHz and live audio levels register on-screen in real time (capture path confirmed live).
  2. Derived BPM tracks the real track tempo — a ~129 BPM track reads ~129, never 200; out-of-range BPM (outside BPM_VALID_MAX) is rejected at the source and never reaches the bus or UI. *(The median-ring stabilizer already landed in `fd25337`; this phase confirms the gate + adds a real-trace regression — it does NOT re-implement it.)*
  3. The other audio-derived features (RMS levels, frequency bands, onset density) stay within valid ranges across a full-set run — no NaN, no out-of-range spikes leaking to the UI.
  4. With a track routed in, the on-screen level meters move in time with the music (visible, grounded feedback that capture is live and correct).
  5. **Genre is auto-detected from the live audio** (Kaan directive): a `psytrance` profile exists, and a grounded DSP detector (BPM band + band-signature + crest-factor) picks the active profile from real features — confidence-gated with `unknown` fallback + hysteresis, env override wins when set. Psytrance no longer misclassifies.
  6. **Detected genre + confidence are on the bus/UI** — surfaced as `unknown` when unsure, never a hallucinated label.
**Plans**: TBD
**UI hint**: yes — genre + confidence join the live snapshot the UI/mascot read

### Phase 53: Controller Live + Graceful Fallback
**Goal**: The DDJ-FLX4 MIDI path is proven on real hardware — controller moves are ingested live during a real session — and the app degrades cleanly to a clear, no-crash state when the controller is unplugged mid-session or absent at boot.
**Depends on**: Phase 51 (running app to ingest into); independent of Phase 52
**Requirements**: BRINGUP-03
**Success Criteria** (what must be TRUE):
  1. The DDJ-FLX4 is ingested live during a session when plugged in — real fader/knob/jog moves register in `ControllerState` and surface to the bus.
  2. Unplugging the controller mid-session degrades gracefully — no crash, no unhandled exception, the app stays in a clear, defined state and keeps running.
  3. Booting with the controller absent runs a full session on audio alone with no MIDI-related errors in the logs (verified graceful fallback).
**Plans** (2 plans, 2 waves):
  - **Wave 1** — 53-01: Controller state hardening + FLX4 decode proof + canonical-binding pin (mark_disconnected clears stale rings; profiles/ vs controllers/ dual-map resolved; FLX4 synthetic-stream decode; unknown-controller graceful path).
  - **Wave 2** *(blocked on Wave 1 completion)* — 53-02: Wire hot-plug watcher into the live session + disconnect/reconnect proof (single-state callback, no rebuild divergence; `__main__` watcher spawn + cleanup; disconnect→reconnect + watcher-callback integration; macos_audio live-drive recipe).
  - **Cross-cutting constraints:** profiles/ is canonical for live binding/decode (controllers/+MidiMapLoader unwired — do not switch/delete); mark_disconnected must clear moves+events rings; real FLX4 plug/move/unplug/replug drive = KAAN-ACTION.

### Phase 54: Hype Mode Live
**Goal**: On real audio, hype (party) mode feels like a real DJ friend in the ear — and, critically, the AI voice **actually fires** on real events. Real hardware surfaced a hard bug: a detected drop produced no voice in a 32s window. Hype mode is not validated until grounded, in-bar reactions reliably land on real drops/builds across ≥2 genres, with cooldowns and latency tuned live so nothing comes late.
**Depends on**: Phase 52 (grounded audio features are what hype reactions react to)
**Requirements**: LIVE-01, LIVE-03
**Success Criteria** (what must be TRUE):
  1. On real audio, when a drop/build is detected the AI voice fires — no more dead windows where a clear event passes with no reaction (the 32s-silent-on-drop bug is closed).
  2. Hype-mode reactions are grounded, in-time, and non-slop across ≥2 genres — no scripted, late, or hallucinated lines (Kaan-ear pass + autonomous proxy clean).
  3. Event cooldowns and reaction latency are tuned live so reactions land in-bar rather than after the moment passes.
  4. Across a full hype-mode set, the cadence feels alive (reactions present at the right density) — not silent stretches, not chatter.
**Plans**: TBD
**UI hint**: yes

### Phase 55: Feedback Mode Live + Citation Integrity
**Goal**: On real audio, feedback (coach) mode coaches like a real DJ mentor — grounded, in-bar, non-slop across ≥2 genres — and every claim it makes is backed by a real event. The EvidenceRegistry citation strip is the visible proof: it must reflect real session events live with zero orphaned or hallucinated citations.
**Depends on**: Phase 52 (grounded audio features back the coaching); benefits from Phase 54 (latency/cooldown tuning carries over)
**Requirements**: LIVE-02, LIVE-04
**Success Criteria** (what must be TRUE):
  1. On real audio, feedback (coach) mode produces grounded, in-time, non-slop coaching across ≥2 genres — observations tie to things that actually happened in the set (Kaan-ear pass + autonomous proxy clean).
  2. The EvidenceRegistry citation strip reflects real session events live — every citation maps to a real event, zero orphaned or hallucinated citations across a full-set run.
  3. Clicking a live citation deep-links to the real event it cites (citation → debrief region highlight works on real session data, not fixtures).
**Plans**: TBD
**UI hint**: yes

### Phase 56: Performance + Live Mascot
**Goal**: On the real machine under live-session load, the co-host hits peak performance — reactions are fast (TTFT within budget), audio never glitches, the UI and mascot hold 60fps — and the Neon Rebel mascot is a live, correct feedback surface that telegraphs back what the system saw from real audio/MIDI events.
**Depends on**: Phase 54 + Phase 55 (perf is measured against real reaction traffic from both modes); Phase 53 (mascot reacts to live MIDI)
**Requirements**: PERF-01, PERF-02, PERF-03, LIVE-05, LIVE-05a
**Success Criteria** (what must be TRUE):
  1. TTFT (trigger → first audio out) measured on the real MacBook meets the live-path latency budget.
  2. No audio glitches/dropouts occur in the playback path under real-session load across a full set.
  3. The mascot + UI hold 60fps on the integrated-GPU MacBook during a live session.
  4. The Neon Rebel mascot reacts correctly to live audio/MIDI events in-session — its state visibly tracks real drops/builds/controller moves (the visual feedback loop is grounded, not decorative).
  5. The mascot consumes the **rich bus signals** (`phase`, `mood`, `reaction_intent`, `bpm`, levels), not just the music-loudness ramp it uses today — `mascot.html` currently reads only `music`+`voice` → 3 tiers; this seam is the gap.
  6. The mascot has **many distinct modes** (Kaan directive 2026-05-21): ≥ idle/dead-air, vibing/groove, building, drop/peak, breakdown/chill, and a speaking/emoting mode while the AI talks — every mode change corresponds to a real musical/session event (anti-slop: no random or purely decorative state changes).
**Plans**: 3 plans (2 waves)
  - [x] 56-01-PLAN.md — LIVE-05/05a anti-slop guard: extend the Three.js rig SnapshotSlice with music/voice + the drop/breakdown music-confirmation defence-in-depth guard + anti-slop fixtures (wave 1)
  - [x] 56-02-PLAN.md — PERF-01 (TTFT telemetry budget + thinking-gate positive/negative pin) + PERF-02 (zero playback underruns under both-mode soak) via Python test extensions (wave 1)
  - [ ] 56-03-PLAN.md — LIVE-05/05a six-mode reachability + speaking-overrides-music proof + mood/emotion tint discipline + PERF-03 dispatch-latency mode-transition floor (wave 2, depends on 56-01)
**UI hint**: yes — mascot is a Tier-1 live surface; the many-modes work is design-led (lift `mocks/` + `frontend-enforcement` skill; the bus already carries the signals to drive it).

### Phase 57: Sexify Finish
**Goal**: The surfaces a real user touches are polished to peak — Tier-1 live views get a final CDJ-Whisper visual pass, the v0.1.0-rc1 carryover bugs are closed, and a fresh account reaches first-session with no friction.
**Depends on**: Phase 51 (running app to inspect); benefits from Phases 52–56 live observations
**Requirements**: POLISH-01, POLISH-02, POLISH-03
**Success Criteria** (what must be TRUE):
  1. Tier-1 live surfaces (session view, mascot overlay) pass a final paired ui-checker + ui-auditor visual pass with zero HIGH findings and CDJ Whisper consistency held (20/80 accent rule, textured material feel, no AI-slop typography).
  2. The three v0.1.0-rc1 carryover bugs are closed and verified on the real app: Tauri drag capability works, the mascot chrome strip is gone, and the TCC permissions list populates correctly.
  3. A fresh macOS user account walks first-run → first-session with the friction points identified and tightened (no dead-ends, no confusing steps before audio is live).
**Plans**: TBD
**UI hint**: yes — **use the `impeccable` skill for the visual polish pass** (Kaan directive 2026-05-21), not just the default ui-phase/ui-review.

### Phase 58: Ship Readiness
**Goal**: Everything that does not require an external signature is green and proven — release gates pass on real artifacts, the §E2E-50A-WALK is discharged by driving the real app, and the exact one-button ship sequence is documented and pre-verified so the only thing left is the external signatures.
**Depends on**: Phase 54 + Phase 55 (live validation feeds Gate 2b hallucination + Gate 6b e2e report), Phase 57 (polish complete before final artifacts)
**Requirements**: REL-01, REL-02, REL-03
**Success Criteria** (what must be TRUE):
  1. `cut_release.sh` 6-gate pre-flight + Gate 2b (hallucination) + Gate 6b (e2e report) all run green on real artifacts (not simulated fixtures).
  2. §E2E-50A-WALK is discharged by driving the real app end-to-end on the MacBook with real DJ-set audio, and the walk artifact (`docs/e2e/2026-05-walk.webm`) is recorded.
  3. The external-clock items (Apple Dev Agreement, SignPath OSS cert) are surfaced as KAAN-ACTION with the exact one-button SHIP-CUT sequence documented and pre-verified — a dry-run confirms everything-but-the-signature is ready, with no engineering step left to discover after signatures land.
**Plans**: TBD

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 51. Real-Hardware Bring-Up | v4.0 | 3/3 | Complete | 2026-05-21 |
| 52. Audio Path + Feature Grounding | v4.0 | 4/4 | Complete | 2026-05-21 |
| 53. Controller Live + Graceful Fallback | v4.0 | 2/2 | Complete | 2026-05-21 |
| 54. Hype Mode Live | v4.0 | 4/4 | Complete    | 2026-05-20 |
| 55. Feedback Mode Live + Citation Integrity | v4.0 | 3/3 | Complete   | 2026-05-21 |
| 56. Performance + Live Mascot | v4.0 | 2/3 | In Progress|  |
| 57. Sexify Finish | v4.0 | 0/TBD | Not started | - |
| 58. Ship Readiness | v4.0 | 0/TBD | Not started | - |

**Coverage:** 19/19 v4.0 requirements mapped ✓ (no orphans, no duplicates)

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

Full archive: `.planning/milestones/v2.1-ROADMAP.md` · Requirements: `.planning/milestones/v2.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.1-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.0 Clean OSS Ship (Phases 40–45) — SHIPPED 2026-05-17 (tech_debt accepted)</summary>

6 phases shipped engineering-green under `gsd-autonomous fully` mode. 41 plans, 250 commits since `v2.1.0` tag, net ~+61k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`, `docs/`, `eval/`. 57 / 57 v3.0 REQ-IDs engineering-satisfied. All 3 integration seams + 5 flows audited.

- [x] Phase 40: Anti-Slop Audio Port (6/6 plans) — completed 2026-05-16 (AUDIO-01..04 GREEN; AUDIO-05/06/07 = KAAN-ACTION-LEGAL)
- [x] Phase 41: Gemini SKU Upgrade + Latency Stack v2 (7/7 plans) — completed 2026-05-16 (LAT-01..08 GREEN; LAT-09 spike = KAAN-ACTION-PROXY)
- [x] Phase 42: Hallucination Gate v3 — Hybrid (6/6 plans) — completed 2026-05-16 (GATE-05..09 GREEN; GATE-01/02/03/04 corpus = KAAN-ACTION-LEGAL)
- [x] Phase 43: Visual Ship Lock (9/9 plans) — completed 2026-05-16 (VIS-01..09 GREEN; VIS-04 Mixamo retargets = KAAN-ACTION-LEGAL)
- [x] Phase 44: Launch Positioning + Pre-stage (7/7 plans) — completed 2026-05-17 (LAUNCH-01..10 GREEN; LAUNCH-03/04/06/07/08 = KAAN-ACTION-LEGAL)
- [x] Phase 45: External Discharge + Public RC Publish (6/6 plans) — completed 2026-05-17 (SHIP-08/11/13 engineering GREEN; SHIP-01..13 cookbook in KAAN-ACTION-LEGAL)

**Critical path at close:** External clock — Apple Dev Agreement (Francesco, P46) + SignPath OSS Foundation (Kaan, ~1-week SLA, P46) gate the public RC publish. After approvals land, SHIP-CUT v3.0.0-rc1 is one-button via the §SHIP-01..13 discharge cookbook (45-06).

Full archive: `.planning/milestones/v3.0-ROADMAP.md` · Requirements: `.planning/milestones/v3.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.1 Distribution-Ready Pass (Phases 46–50) — SHIPPED 2026-05-18 (tech_debt accepted)</summary>

5 phases shipped engineering-green under `gsd-autonomous fully` mode. 32 plans, 61 commits since `v3.0` tag, net ~+57.5k LOC across `installer/`, `tauri/`, `scripts/`, `tests/`, `docs/`, `.github/workflows/`. 44 / 44 v3.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

- [x] Phase 46: Dependency Audit + Lockfile + AUDIT.md (6/6 plans, 45 tests + 1 xfail; DEPS-01..06 + DEPS-09/10 GREEN; DEPS-07 pinact + DEPS-08 cull-blocked documented in AUDIT.md § Decisions) — completed 2026-05-18
- [x] Phase 47: Mascot Real GLB Land + Full Emotion Coverage (8/8 plans, 63 python + 177 ts tests; MASCOT-01..08 GREEN; §VIS-04 + §VIS-05 Mixamo discharge = KAAN-ACTION) — completed 2026-05-18
- [x] Phase 48: New-Dep + Integration Opportunity Scan (6/6 plans, 19 tests; OPP-01..06 GREEN; 24 candidates rated 1G/8Y/9R-constraint/6R-risk; OBS adopted docs-only) — completed 2026-05-18
- [x] Phase 49: Win + Mac One-Click Installer Chain (6/6 plans, 68 passing + 1 skip; INSTALL-01..10 GREEN; §INSTALL-COMPANION-SIGN + §INSTALL-VM-RUN + §SHIP-CONTACT-VBAUDIO = KAAN-ACTION; median 41,000 ms / 60,000 ms budget) — completed 2026-05-18
- [x] Phase 50: End-to-End MacBook + OS-Matrix Pass (6/6 plans, 16 passing + 5 CI-tolerant skips; E2E-01..10 GREEN; §E2E-50A-WALK + §INSTALL-VM-RUN downstream = KAAN-ACTION; Gate 6b wired into cut_release.sh) — completed 2026-05-18

**Critical path at close:** Same external clock as v3.0 — §INSTALL-COMPANION-SIGN (SignPath OSS Foundation cert) unblocks §INSTALL-VM-RUN (real Tart VM execution) which enables §E2E-50A-WALK full completion. §VIS-04 (28 Mixamo retargets via Adobe walk) is independent and runs in parallel. SHIP-CUT v3.1 ride-along with v3.0 publish.

Full archive: `.planning/milestones/v3.1-ROADMAP.md` · Requirements: `.planning/milestones/v3.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.1-MILESTONE-AUDIT.md`

</details>

---

## Milestone-Level Progress

| Milestone | Phases | Status | Shipped |
|-----------|--------|--------|---------|
| v0.1.0 MVP Foundation | 1–14 | ✅ Shipped | 2026-05-13 |
| v2.0 Research-Driven Ship | 15–26 | ✅ Shipped (tech_debt) | 2026-05-14 |
| v2.1 The Unified Cut | 27–39 | ✅ Shipped (tech_debt) | 2026-05-16 |
| v3.0 Clean OSS Ship | 40–45 | ✅ Shipped (tech_debt) | 2026-05-17 |
| v3.1 Distribution-Ready Pass | 46–50 | ✅ Shipped (tech_debt) | 2026-05-18 |
| v4.0 SHIP | 51–58 | 🔨 Planning | - |

---

*Roadmap re-split 2026-05-20 for v4.0 "SHIP" — **8 phases (51–58)** per Kaan's directive for finer granularity than the prior 4-phase cut. Continues numbering from v3.1 (closed at Phase 50). Bring-up is split into three input seams — boot/stability (51), audio + feature grounding (52), controller (53) — so each real-hardware path is independently green before the modes that consume it are validated. The two interaction modes get dedicated phases (hype 54, feedback 55) because they have different live failure shapes; performance + live mascot land together (56) once both modes generate real reaction traffic. Real-hardware findings folded in: ws_bus empty-frame cleanup (51), live BPM=200 grounding fix (52), AI-voice-must-actually-fire (54). External signatures (Apple Dev + SignPath) stay KAAN-ACTION — engineering makes the release one-button-after-signatures; no phase depends on signatures landing.*
