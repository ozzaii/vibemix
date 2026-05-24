# vibemix — Roadmap

**Project:** vibemix — AI DJ Co-Host
**Last shipped:** v7.0 "Open House" — 2026-05-24 (tech_debt accepted; KAAN-ACTION §V7-LIVE / §V7-PROXY / §V7-LANDING / §ASSETS-DEMO-CUT / §SHIP-V4 ride forward on Kaan's clock)
**Current milestone:** none active — v8.0 "Proof & Polish" SHIPPED 2026-05-25 (tech_debt accepted); run `/gsd:new-milestone` for the next cycle
**Open alongside:** v4.0 "SHIP" — engineering-complete (8/8), publish gated on the external Apple Dev + SignPath signature clock (NOT archived) — **v7.0's OSS-04 discharges §SHIP-V4 for real; v4.0 closes alongside when the real cut fires**

---

## Milestones

- ✅ **v0.1.0 MVP Foundation** — Phases 1–14 (shipped 2026-05-13) — see `.planning/milestones/v0.1.0/`
- ✅ **v2.0 Research-Driven Ship** — Phases 15–26 (shipped 2026-05-14, tech_debt accepted) — see `.planning/milestones/v2.0-ROADMAP.md`
- ✅ **v2.1 The Unified Cut** — Phases 27–39 (shipped 2026-05-16, tech_debt accepted) — see `.planning/milestones/v2.1-ROADMAP.md`
- ✅ **v3.0 Clean OSS Ship** — Phases 40–45 (shipped 2026-05-17, tech_debt accepted) — see `.planning/milestones/v3.0-ROADMAP.md`
- ✅ **v3.1 Distribution-Ready Pass** — Phases 46–50 (shipped 2026-05-18, tech_debt accepted) — see `.planning/milestones/v3.1-ROADMAP.md`
- 🟡 **v4.0 SHIP** — Phases 51–58 (engineering-complete 8/8, publish on signature clock — NOT archived; closes alongside v7.0 OSS-04) — see `.planning/milestones/v4.0-ROADMAP.md`
- ✅ **v5.0 The Useful Cut** — Phases 59–62 (shipped 2026-05-22, tech_debt accepted) — see `.planning/milestones/v5.0-ROADMAP.md`
- ✅ **v6.0 The Memory Turn** — Phases 63–66 (shipped 2026-05-23, tech_debt accepted) — see `.planning/milestones/v6.0-ROADMAP.md`
- ✅ **v7.0 Open House** — Phases 67–70 (shipped 2026-05-24, tech_debt accepted) — see `.planning/milestones/v7.0-ROADMAP.md`
- ✅ **v8.0 Proof & Polish** — Phases 71–76 (shipped 2026-05-25, tech_debt accepted) — *this file, below* · audit `.planning/v8.0-MILESTONE-AUDIT.md`

---

# v8.0 "Proof & Polish" — SHIPPED 2026-05-25 (tech_debt accepted)

**Goal:** Take the system from "engineering-sound on paper" to **proven, easy, and live on GitHub** — everything logged · simulated · reported · tested · fixed · re-tested · verified · GitHub-done, plus real **ease of use** and a **whole-design level-up loop**. The deep audit (`.planning/ALL-MILESTONES-DEEP-AUDIT.md`) already finds the system **sound** (4256 tests green at branch HEAD, 4 cardinal invariants hold); v8.0 *proves and polishes* — it does not rescue.

**Anti-creep acid test:** *"Does this make an existing capability genuinely logged / simulated / reported / tested / fixed / verified / pushed — or easier to use / better-looking — WITHOUT a new product capability, AI/embedding provider, managed framework, ws port, or IPC envelope?"* If not, defer. Gemini-only holds; the four cardinal invariants hold by zero-touch on the reaction path.

**Dependency spine:** P71 (land in-flight branch work) → P72 (log everything + simulate hardware) → P73 (report + full-grid test + fix loop + verify + close audit findings) → P74 (ease of use) ‖ P75 (design level-up) [both depend on P71-landed UI, run after P73 green] → P76 (GitHub done: push backlog, CI green; signed-release + social stay KAAN-ACTION).

| # | Phase | Goal | REQ-IDs |
|---|-------|------|---------|
| 71 | Land & Verify | Finish + verify + commit the uncommitted live-tuning + observability branch work; green its new Py/TS/Rust tests | LOG-01, LOG-03 |
| 72 | Logged & Simulated | Unified structured logging end-to-end; simulation/replay harness for hardware-gated paths (BlackHole/FLX4/device-select) | LOG-02, LOG-04, SIM-01..03 |
| 73 | Reported · Tested · Fixed · Verified | Reports (test/coverage/session); full marker-grid run + fix loop to green; close deep-audit findings #1–#4; verify | RPT-01..03, TEST-01..05 |
| 74 | Ease of Use | First-run/onboarding friction, device-select UX, settings clarity, actionable failure states | UX-01..04 |
| 75 | Design Level-Up Loop | Whole-design CDJ-Whisper glow-up (impeccable + frontend-enforcement) across all surfaces; review→fix→re-review to zero HIGH | DESIGN-01..04 |
| 76 | GitHub Done | Push the ~528-commit backlog + branch; origin/main current; CI green on full matrix; repo presence finalized | GH-01..03 (GH-04 = KAAN-ACTION) |

### Phase 71 — Land & Verify
**Goal:** The in-flight `live-tuning-or-brain` work (device_select, the debug-log surface, tray-mood, audio/sidecar/session changes) is finished, verified, and committed in clean atomic commits.
**Success criteria:** (1) `device_select.py` + new audio backend changes land with `test_device_select` + `test_audio_macos` additions green; (2) debug-log surface (`debug_log.rs` + `debug-log.ts` + `debug-log-ws.ts` + `debug-log.spec`) wired one-socket-safe and green; (3) `tray-mood` + `test_proxy_fallback` land green; (4) default `pytest -q` stays 0-red (≥4256 passed); (5) TS + Rust suites run for the changed files.

### Phase 72 — Logged & Simulated
**Goal:** Everything important is logged through one structured surface, and the hardware-gated paths are simulatable headlessly.
**Success criteria:** (1) reaction turns log evidence packet + citation-gate decision (LOG-02); (2) a log-level switch gates verbosity without changing default UX (LOG-04); (3) a sim harness replays a session end-to-end with no hardware + no live Gemini (SIM-01); (4) synthetic BlackHole/FLX4/device fixtures verify the §V7-LIVE paths in CI (SIM-02); (5) the sim emits a deterministic artifact (SIM-03).

### Phase 73 — Reported · Tested · Fixed · Verified
**Goal:** The whole suite is run, reported, every red driven green, and the result verified; the deep-audit housekeeping is closed.
**Success criteria:** (1) saved test+coverage report artifact (RPT-01); (2) sim-session report (RPT-02); (3) full default suite 0-red + opt-in marker grid exercised (TEST-01/02); (4) TS+Rust green (TEST-03); (5) audit findings #1–#4 closed (TEST-04); (6) fix→re-test loop ends green + committed, no new skip/xfail graveyards (TEST-05); (7) v8.0 verification report ties each REQ to evidence (RPT-03).

### Phase 74 — Ease of Use
**Goal:** A stranger's path from install to first reaction is effortless and forgiving.
**Success criteria:** (1) guided first-run with clear empty/loading/permission states (UX-01); (2) self-explanatory device selection + routing, no BlackHole guesswork (UX-02); (3) clear, reversible mode/level/settings controls (UX-03); (4) every failure mode (no audio/key/proxy/MIDI) gives actionable guidance (UX-04).

### Phase 75 — Design Level-Up Loop
**Goal:** Every surface is leveled up to the CDJ-Whisper bar through an auditor-driven loop, no AI slop.
**Success criteria:** (1) session UI + pill zero HIGH findings (DESIGN-01); (2) mascot overlay + debrief + wizard + settings pass the bar (DESIGN-02); (3) review→fix→re-review loop run to zero HIGH (DESIGN-03); (4) consistent design tokens across surfaces (DESIGN-04).

### Phase 76 — GitHub Done
**Goal:** GitHub reflects the verified reality; the only thing left is Kaan's signature-gated public publish.
**Success criteria:** (1) ~528-commit backlog + branch pushed; origin/main current (GH-01); (2) CI green on full matrix for the pushed state (GH-02); (3) repo presence finalized, no stale claims (GH-03); (4) §SHIP-V4 signed-release + social documented as the sole KAAN-ACTION carveout, NOT auto-fired (GH-04).

---

# v7.0 "Open House" — SHIPPED 2026-05-24 (tech_debt accepted)

<details>
<summary>✅ v7.0 Open House (Phases 67–70) — SHIPPED 2026-05-24 (tech_debt accepted)</summary>

4 phases shipped engineering-green under `gsd-autonomous fully` mode. 20 plans, 37 tasks, 19/19 v7.0 REQ-IDs satisfied (engineering-side), 6/6 cross-phase wirings sound, UI-review PASS 23/24 on the landing. A **WIRING + DISCHARGE + POLISH milestone with ZERO new product capability** — zero net-new dependencies, zero new ws ports, zero new IPC envelopes. The four cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) held by zero-touch (only Phase 69 touched `src/vibemix/agent/` for the client-side proxy fallback).

- [x] Phase 67: All Tests Pass (5/5 plans) — 2026-05-23 (TEST-01..04; default `pytest -q` 0-red, 21-job `full-test-matrix.yml` CI, static skip/flake gates, 10× flake-hunt baseline)
- [x] Phase 68: All Devices Ready (5/5 plans) — 2026-05-23 (DEV-01..05; 10 profile contracts + synthetic-MIDI smokes, catalog reconciled to single `profiles/` source, hot-plug + audio-backend matrices, contributor recipe)
- [x] Phase 69: OSS Fully Integrated (5/5 plans) — 2026-05-24 (OSS-01..05; 4 OSS docs + presence test, client-side proxy fallback "Co-host unavailable this session", BYO-key doc, Homebrew+Scoop scaffolds, §SHIP-V4 publish pre-staged)
- [x] Phase 70: GitHub Sexified, Generated, Tested (5/5 plans) — 2026-05-24 (GH-01..05; asset reproducibility pipeline + auto-gen og-card, CDJ-Whisper Pages landing, demo poster, one-stop `test_github_presence.py`)

**KAAN-ACTION (live-confirm / external-clock, rides forward):** §V7-LIVE-01..11 (live hardware + first-CI-green + BYO walk) + §V7-PROXY (Bravoh server-side hardening) + §V7-LANDING (Pages-live + Kaan-felt aesthetic sign-off + real waitlist URL) + §ASSETS-DEMO-CUT (real 30-sec demo film, Francesco capture) + **§SHIP-V4 (HARD external clock — OSS-04 real `cut_release.sh v0.1.0-rc1` publish, gated on Apple Dev + SignPath; v4.0 "SHIP" closes alongside when it fires)**. All in `KAAN-ACTION-LEGAL.md`.

**Git tag + branch merge deferred** (consistent with v4.0 + v5.0 + v6.0): the `v7.0` tag + `live-tuning-or-brain` → main merge are Kaan's call on his clock (the OSS-04 publish + v4.0 close ride the same signature clock).

Full archive: `.planning/milestones/v7.0-ROADMAP.md` · Requirements: `.planning/milestones/v7.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v7.0-MILESTONE-AUDIT.md`

</details>

---

# v6.0 "The Memory Turn" — SHIPPED 2026-05-23 (tech_debt accepted)

<details>
<summary>✅ v6.0 The Memory Turn (Phases 63–66) — SHIPPED 2026-05-23 (tech_debt accepted)</summary>

4 phases shipped engineering-green under `gsd-autonomous fully` mode. 12 plans, 14/14 v6.0 REQ-IDs satisfied, 6/6 cross-phase integration seams WIRED, 53/53 must-haves verified, 247/247 v6.0 surface tests GREEN. A **WIRING / REUSE milestone with ZERO net-new dependencies** — built entirely on the shipped `src/vibemix/library/` primitives (sqlite-vec, cosine_topk, embed-cache, grounding pattern, EVIDENCE_SOURCES schema).

- [x] Phase 63: Memory Store (3/3 plans) — 2026-05-22 (STORE-01..04 GREEN; 19/19 tests/memory/)
- [x] Phase 64: Session Ingest (3/3 plans) — 2026-05-22 (INGEST-01..03 GREEN; one v1 moment kind = `coach_line`; `moment` cut, `audio_moment` deferred)
- [x] Phase 65: Memory Retrieval Seam — ANTI-SLOP RELEASE GATE (4/4 plans) — 2026-05-22 (RECALL-01..04 GREEN; existence-only `recall` source à la P59 `key:`, fabricated `[recall:<id>]` strips whole turn)
- [x] Phase 66: Visible Copilot Move (2/2 plans) — 2026-05-22 (COPILOT-01..03 GREEN; transition-shape + vocabulary callbacks; ships behind `VIBEMIX_RECALL_ENABLED=0` until §RECALL-EAR Kaan-ear pass)

**KAAN-ACTION (live-confirm, rides forward):** §RECALL-EAR felt-quality discharge (4 ear items) + §LIVE-EMBED real-session FLEX-tier round-trip + two doc-drifts (code correct) + STORE-03 recordings-UI call-site (out of v6.0 scope; future recordings-UI phase). All in `KAAN-ACTION-LEGAL.md §RECALL-EAR` + `66-HUMAN-UAT.md`.

**Git tag deferred** (consistent with v4.0 + v5.0): the `v6.0` tag + branch merge are Kaan's call on his clock.

Full archive: `.planning/milestones/v6.0-ROADMAP.md` · Requirements: `.planning/milestones/v6.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v6.0-MILESTONE-AUDIT.md`

</details>

---

# v5.0 "The Useful Cut" — SHIPPED 2026-05-22 (tech_debt accepted)

<details>
<summary>✅ v5.0 The Useful Cut (Phases 59–62) — SHIPPED 2026-05-22 (tech_debt accepted)</summary>

Deck-aware, actionable, unobtrusive. Full session-wide deck-state (pyrekordbox XML → Gemini-vision → numpy ladder) with a citable `key:` evidence source; a deterministic Camelot harmonic key-clash gate the LLM only narrates (ships **default-OFF** behind the Kaan-ear veto); an actionable-not-hype coach persona extending the `live-tuning-or-brain` branch (hype goldens regression-fenced); and a transparent, draggable, non-focus-stealing **floating pill** as the primary live surface (Three.js mascot kept opt-in/secondary, mascot-audit green). 4/4 phases, 17/17 requirements satisfied, 4/4 cross-phase integration seams WIRED.

- [x] Phase 59: Full Deck Awareness + Grounding (5/5 plans) — 2026-05-21
- [x] Phase 60: Harmonic-Feedback Confidence Gate (4/4 plans) — 2026-05-21 (detector default-OFF until the Kaan-ear veto flip)
- [x] Phase 61: Actionable-Not-Hype Coach Persona (2/2 plans) — 2026-05-21
- [x] Phase 62: Floating Pill UI (5/5 plans) — 2026-05-22

Full archive: `.planning/milestones/v5.0-ROADMAP.md` · Requirements: `.planning/milestones/v5.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v5.0-MILESTONE-AUDIT.md`

</details>

---

# v4.0 SHIP — OPEN (engineering-complete 8/8, publish on signature clock — NOT archived)

> **Status:** All 8 phases (51–58) are engineering-complete. The milestone is deliberately **left open and unarchived** — its public RC publish stays gated on the external signature clock (Apple Dev Agreement via Francesco + SignPath OSS cert). **v7.0's OSS-04 actually consumes this publish** (closes alongside §SHIP-V4 discharge). Do not delete or archive this section until OSS-04 fires.

<details>
<summary>🟡 v4.0 SHIP (Phases 51–58) — engineering-complete 2026-05-21, publish on signature clock</summary>

- [x] Phase 51: Real-Hardware Bring-Up (3/3 plans) — 2026-05-21
- [x] Phase 52: Audio Path + Feature Grounding (4/4 plans) — 2026-05-21
- [x] Phase 53: Controller Live + Graceful Fallback (2/2 plans) — 2026-05-21
- [x] Phase 54: Hype Mode Live (4/4 plans) — 2026-05-20
- [x] Phase 55: Feedback Mode Live + Citation Integrity (3/3 plans) — 2026-05-21
- [x] Phase 56: Performance + Live Mascot (3/3 plans) — 2026-05-21
- [x] Phase 57: Sexify Finish (3/3 plans) — 2026-05-21
- [x] Phase 58: Ship Readiness (4/4 plans) — 2026-05-21 (`cut_release.sh --dry-run v0.1.0-rc1` GREEN; publish hard-guard regression-pinned)

**Critical path at close:** External clock — Apple Dev Agreement (Francesco) + SignPath OSS Foundation (Kaan, ~1-week SLA). `KAAN-ACTION-LEGAL.md §SHIP-V4` documents the one-button SHIP-CUT sequence. **v4.0 closes alongside v7.0 OSS-04.**

Full archive: `.planning/milestones/v4.0-ROADMAP.md`

</details>

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

13 phases shipped engineering-green under `gsd-autonomous fully` mode. 96 plans, 633 phase-scope tests added, 225 commits since `v2.0` tag, net ~+45k LOC. 105/105 v2.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

Full archive: `.planning/milestones/v2.1-ROADMAP.md` · Requirements: `.planning/milestones/v2.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.1-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.0 Clean OSS Ship (Phases 40–45) — SHIPPED 2026-05-17 (tech_debt accepted)</summary>

6 phases shipped engineering-green under `gsd-autonomous fully` mode. 41 plans, 250 commits since `v2.1.0` tag, net ~+61k LOC. 57/57 v3.0 REQ-IDs engineering-satisfied. All 3 integration seams + 5 flows audited.

Full archive: `.planning/milestones/v3.0-ROADMAP.md` · Requirements: `.planning/milestones/v3.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.1 Distribution-Ready Pass (Phases 46–50) — SHIPPED 2026-05-18 (tech_debt accepted)</summary>

5 phases shipped engineering-green under `gsd-autonomous fully` mode. 32 plans, 61 commits since `v3.0` tag, net ~+57.5k LOC. 44/44 v3.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

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
| v4.0 SHIP | 51–58 | 🟡 Engineering-complete (8/8) — publish on signature clock; closes alongside v7.0 OSS-04 | - |
| v5.0 The Useful Cut | 59–62 | ✅ Shipped (tech_debt) | 2026-05-22 |
| v6.0 The Memory Turn | 63–66 | ✅ Shipped (tech_debt) | 2026-05-23 |
| v7.0 Open House | 67–70 | ✅ Shipped (tech_debt) | 2026-05-24 |

---

*Roadmap extended 2026-05-23 for v7.0 "Open House" — **4 phases (67–70)** continuing numbering from v6.0 (which ran 63–66). v4.0 "SHIP" stays OPEN and unarchived above — its publish closes alongside v7.0's OSS-04 (KAAN-ACTION §SHIP-V4 discharge fires `cut_release.sh v0.1.0-rc1` for real). v7.0 derives from 19 requirements across 4 pillars (TEST · DEV · OSS · GH), one phase per pillar, sized by `.planning/REQUIREMENTS.md` Traceability — 4/5/5/5 REQ-IDs per phase, zero orphans, zero duplicates. **Hard scope rule (locked):** v7.0 is WIRING + DISCHARGE + POLISH — zero new product capability, zero new AI providers, zero new managed-memory frameworks, zero new ws ports, zero new IPC envelopes. The four cardinal invariants (single-writer / citation grounding / "trust the audio" / one socket) hold by zero-touch — no phase modifies the reaction path. The v4.0 external signature clock is unchanged. Critical path: P67 (test infrastructure, dependency-free) → P68 (controller catalog reconciliation + audio backends, lands on P67's CI matrix) → P69 (OSS surface + actual publish gated on §SHIP-V4) → P70 (GitHub front-porch + Kaan-felt landing-page sign-off). Under `gsd-autonomous fully`, OSS-04 routes to §SHIP-V4 if signatures haven't landed at execution; the other 18 REQ-IDs ship unblocked.*
