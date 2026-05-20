# vibemix — Roadmap

**Project:** vibemix — AI DJ Co-Host
**Last shipped:** v3.1 Distribution-Ready Pass — 2026-05-18 (status: `tech_debt` accepted — 7 Kaan-action carveouts ride the v3.0 external clock per `gsd-autonomous fully` mode)
**Current milestone:** v3.2 "Plug In And Play" — Real-Hardware Bring-Up → Public Ship (planning)

---

## Milestones

- ✅ **v0.1.0 MVP Foundation** — Phases 1–14 (shipped 2026-05-13) — see `.planning/milestones/v0.1.0/`
- ✅ **v2.0 Research-Driven Ship** — Phases 15–26 (shipped 2026-05-14, tech_debt accepted) — see `.planning/milestones/v2.0-ROADMAP.md`
- ✅ **v2.1 The Unified Cut** — Phases 27–39 (shipped 2026-05-16, tech_debt accepted) — see `.planning/milestones/v2.1-ROADMAP.md`
- ✅ **v3.0 Clean OSS Ship** — Phases 40–45 (shipped 2026-05-17, tech_debt accepted) — see `.planning/milestones/v3.0-ROADMAP.md`
- ✅ **v3.1 Distribution-Ready Pass** — Phases 46–50 (shipped 2026-05-18, tech_debt accepted) — see `.planning/milestones/v3.1-ROADMAP.md`
- 🔨 **v3.2 Plug In And Play** — Phases 51–54 (planning) — active below

---

## Overview

v3.1 left vibemix engineering-complete: a built Tauri app + Python sidecar, one-click installer chain, dependency-audited lockfile, full mascot scaffold, and an e2e harness — all green in CI, none of it yet driven on real hardware in a real DJ session. v3.2 closes that gap. For the first time the actual app runs on Kaan's MacBook with real audio through BlackHole and a real DDJ-FLX4 over USB. The journey: **boot it and make it stable** (Phase 51) → **make both modes feel like a real DJ friend on real audio and at peak performance** (Phase 52) → **final visual pass + close the carryover bugs + tighten first-run** (Phase 53) → **get every engineering gate green on real artifacts and document the one-button ship sequence** (Phase 54). The signed public binary itself is gated on external signatures (Apple Dev Agreement via Francesco; SignPath OSS cert) — those stay KAAN-ACTION; engineering makes the release one-button-after-signatures.

This is bring-up + live validation + polish + ship of an **already-built** app. No new AI providers, no new detectors, no scope creep.

## Phases

**Phase Numbering:** Continues from v3.1 (closed at Phase 50). v3.2 starts at **Phase 51**. Integer phases (51, 52, …) = planned milestone work; decimal phases (e.g. 52.1) = urgent insertions if needed.

- [ ] **Phase 51: Real-Hardware Bring-Up** - Boot the app + sidecar on Kaan's Mac, reach a stable live "listening" session, fix every runtime break read from Tauri console + sidecar logs across a full-set run.
- [ ] **Phase 52: Live-Session Validation + Latency/Performance Tuning** - Both modes produce grounded, in-bar, non-slop reactions on real audio across ≥2 genres; citation strip + mascot track real events; TTFT/dropouts/60fps tuned to budget on real HW.
- [ ] **Phase 53: Sexify Finish** - Final Tier-1 visual pass (zero HIGH findings), close v0.1.0-rc1 carryover bugs, tighten fresh-account first-run.
- [ ] **Phase 54: Ship Readiness** - All engineering release gates green on real artifacts, §E2E-50A-WALK discharged by driving the real app, one-button SHIP-CUT sequence documented + pre-verified with external-clock items surfaced as KAAN-ACTION.

## Phase Details

### Phase 51: Real-Hardware Bring-Up
**Goal**: The built app actually runs — boots to a live listening session on Kaan's MacBook, ingests real BlackHole audio and the real DDJ-FLX4, and survives a full-set run with every console/log error triaged and fixed.
**Depends on**: Nothing (first phase — everything downstream needs a running app)
**Requirements**: BRINGUP-01, BRINGUP-02, BRINGUP-03, BRINGUP-04, BRINGUP-05
**Success Criteria** (what must be TRUE):
  1. Launching the app on the real Mac reaches a live "listening" session with no boot crash, and the Tauri console + sidecar logs are clean of unhandled exceptions at startup.
  2. Real master output routed through BlackHole reaches the co-host at 48 kHz and live audio levels register on-screen in real time.
  3. The DDJ-FLX4 is ingested live during a session when plugged in, and the app degrades gracefully (no crash, clear state) when it is unplugged.
  4. Every runtime error observed in the Tauri console + sidecar logs during a real run is triaged and fixed — a full-set run completes with zero unhandled exceptions.
  5. A ≥30-minute continuous real session runs with no dropout, hang, or unbounded memory growth (RSS stays bounded across the run).
**Plans**: TBD

### Phase 52: Live-Session Validation + Latency/Performance Tuning
**Goal**: On real audio, both hype and feedback modes feel like a real DJ friend in the ear — grounded, in-bar, non-slop across ≥2 genres — with the citation strip and mascot tracking real events and performance tuned to budget on the real machine.
**Depends on**: Phase 51 (needs a stable, running session to validate against)
**Requirements**: LIVE-01, LIVE-02, LIVE-03, LIVE-04, LIVE-05, PERF-01, PERF-02, PERF-03
**Success Criteria** (what must be TRUE):
  1. In a live session, hype (party) mode produces grounded, in-time, non-slop reactions on real audio across ≥2 genres — no scripted/late/hallucinated lines (Kaan-ear pass + autonomous proxy clean).
  2. In a live session, feedback (coach) mode produces grounded, in-time, non-slop reactions on real audio across ≥2 genres, with cooldowns and reaction latency tuned live so reactions land in-bar rather than after the moment passes.
  3. The EvidenceRegistry citation strip reflects real session events live with zero orphaned or hallucinated citations, and the Neon Rebel mascot reacts correctly to live audio/MIDI events in-session.
  4. TTFT (trigger → first audio out) measured on the real MacBook meets the live-path latency budget, and no audio glitches/dropouts occur in the playback path under real-session load.
  5. The mascot + UI hold 60fps on the integrated-GPU MacBook during a live session.
**Plans**: TBD
**UI hint**: yes

### Phase 53: Sexify Finish
**Goal**: The surfaces a real user touches are polished to peak — Tier-1 live views get a final CDJ-Whisper visual pass, the v0.1.0-rc1 carryover bugs are closed, and a fresh account reaches first-session with no friction.
**Depends on**: Phase 51 (running app to inspect); benefits from Phase 52 live observations
**Requirements**: POLISH-01, POLISH-02, POLISH-03
**Success Criteria** (what must be TRUE):
  1. Tier-1 live surfaces (session view, mascot overlay) pass a final paired ui-checker + ui-auditor visual pass with zero HIGH findings and CDJ Whisper consistency held (20/80 accent rule, textured material feel, no AI-slop typography).
  2. The three v0.1.0-rc1 carryover bugs are closed and verified on the real app: Tauri drag capability works, the mascot chrome strip is gone, and the TCC permissions list populates correctly.
  3. A fresh macOS user account walks first-run → first-session with the friction points identified and tightened (no dead-ends, no confusing steps before audio is live).
**Plans**: TBD
**UI hint**: yes

### Phase 54: Ship Readiness
**Goal**: Everything that does not require an external signature is green and proven — release gates pass on real artifacts, the §E2E-50A-WALK is discharged by driving the real app, and the exact one-button ship sequence is documented and pre-verified so the only thing left is the external signatures.
**Depends on**: Phase 52 (live validation feeds Gate 2b hallucination + Gate 6b e2e report), Phase 53 (polish complete before final artifacts)
**Requirements**: REL-01, REL-02, REL-03
**Success Criteria** (what must be TRUE):
  1. `cut_release.sh` 6-gate pre-flight + Gate 2b (hallucination) + Gate 6b (e2e report) all run green on real artifacts (not simulated fixtures).
  2. §E2E-50A-WALK is discharged by driving the real app end-to-end on the MacBook with real DJ-set audio, and the walk artifact (`docs/e2e/2026-05-walk.webm`) is recorded.
  3. The external-clock items (Apple Dev Agreement, SignPath OSS cert) are surfaced as KAAN-ACTION with the exact one-button SHIP-CUT sequence documented and pre-verified — a dry-run confirms everything-but-the-signature is ready, with no engineering step left to discover after signatures land.
**Plans**: TBD

---

## Progress — v3.2 Plug In And Play

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 51. Real-Hardware Bring-Up | 0/TBD | Not started | - |
| 52. Live-Session Validation + Latency/Performance Tuning | 0/TBD | Not started | - |
| 53. Sexify Finish | 0/TBD | Not started | - |
| 54. Ship Readiness | 0/TBD | Not started | - |

**Coverage:** 19/19 v3.2 requirements mapped ✓ (no orphans, no duplicates)

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
| v3.2 Plug In And Play | 51–54 | 🔨 Planning | - |

---

*Roadmap reopened 2026-05-20 for v3.2 "Plug In And Play" (Phases 51–54) via `/gsd:new-milestone` under `gsd-autonomous fully`. Bring-up MUST come first (Phase 51) since all downstream validation depends on a running app. Live validation + performance tuning are co-observed in the same real sessions (Phase 52). External signatures (Apple Dev + SignPath) stay KAAN-ACTION — engineering makes the release one-button-after-signatures.*
