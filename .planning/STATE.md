---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: The Unified Cut
status: executing
last_updated: "2026-05-15T09:58:09.366Z"
last_activity: 2026-05-15 -- Phase 28 execution started
progress:
  total_phases: 13
  completed_phases: 1
  total_plans: 18
  completed_plans: 9
  percent: 50
---

# vibemix — State

**Last updated:** 2026-05-14 — v2.1 "The Unified Cut" roadmap created. 13 phases (27–39) scaffolded from `.planning/research/v2-1/SUMMARY.md`. 105 v2.1 REQ-IDs mapped 100% across phases. Phase 27 entry-ready (parallel cluster A with 28 + 29 + 30 + 34).

---

## Project Reference

- **Project:** vibemix — open-source AI DJ co-host (Bravoh's first OSS release)
- **Core value:** "Real DJ friend in your ear" — never hallucinating, never breaking flow, never AI slop.
- **Current focus:** Phase 28 — library-intelligence-v1
- **Last shipped:** v2.0 Research-Driven Ship — 2026-05-14 (status: `tech_debt` accepted).
- **Project mode:** standard.
- **Granularity:** fine.
- **Model profile:** quality (all agents on Opus, all checkpoints on).
- **Autonomy mode:** `gsd-autonomous fully` — every blocker + human-needed item discharged autonomously, only privacy rule + destructive risk + legal-capacity carveouts (Apple Dev Agreement + SignPath OSS) still pause. Phase 16 ear-test memory override accepted for v2.1 only (autonomous proxy gate via Phase 27 substitutes).

---

## Current Position

Phase: 28 (library-intelligence-v1) — EXECUTING
Plan: 1 of 9
Status: Executing Phase 28
Last activity: 2026-05-15 -- Phase 28 execution started

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete (v0.1.0) | 14 / 14 |
| Phases complete (v2.0) | 10 / 12 code-shipped (2 deferred to Kaan-action: P15-04 UAT + P16 ear-test) |
| Phases complete (v2.1) | 0 / 13 |
| Plans complete (v2.1) | 0 / 0 (planning not started) |
| v2.0 REQ-IDs mapped | 94 / 94 ✓ (archived) |
| v2.0 REQ-IDs satisfied end-to-end | 56 / 94 (60%) + 25 satisfied-at-primitive Kaan/external pending + 13 unwired-self-contained |
| v2.1 REQ-IDs mapped | 105 / 105 ✓ (100% coverage, no orphans) |
| v2.1 REQ-IDs satisfied | 0 / 105 (execution not started) |
| v2.0 tests at close | 1961 passed / 10 pre-existing fail / 7 skipped (0 v2.0 regressions) |
| Critical pitfalls (v2.1) tracked | 11 critical (P42–P52) + 41 v2.0 carry-forward + 35 high/medium (P53–P88) mapped to phases |
| Estimated wall-clock to RC | 5–7 weeks of focused engineering |

---

## Accumulated Context

### Decisions Locked (v2.1 — new this milestone)

- **Phase numbering CONTINUES** from v2.0 — v2.1 starts at Phase 27 (v2.0 closed at Phase 26). No `--reset-phase-numbers`.
- **13-phase decomposition P27–P39** with build-order: parallel cluster A (27+28+29+30+34) → sequential B (31→32→35) → external-gated (38→33→36) → ship prep (37→39).
- **`gsd-autonomous fully` mode** — every Kaan-action item discharged autonomously EXCEPT two legal-capacity carveouts (Apple Developer Program Agreement update + SignPath OSS Foundation application). Pitfall P46 encodes this — CI bash audit grep against POST/PUT to apple/signpath endpoints catches autonomous-discharge attempts.
- **Phase 16 ear-test memory override accepted for v2.1 only** — Phase 27 autonomous hallucination-proxy gate (2-judge cross-check + corpus diversity + substance metric + cited-but-irrelevant filter + F1) substitutes for Kaan-ear-only test. Override expires post-v2.1.
- **3 new runtime deps total** for v2.1: `sqlite-vec==0.1.9` (carry-forward from v2.0 — Mac only, Win numpy fallback), `wavesurfer.js ^7.10` (npm), `tauri-plugin-macos-permissions = "2.3.0"` (Rust crate). Net bundle delta <1 MB; ~10 dev/CI-only adds. Bundle stays at ~201 MB vs 350 MB hard cap.
- **Critical path = external approvals**, not engineering. Day-1 action: file SignPath OSS Foundation application + start Apple Developer Program Agreement update prep in parallel with Phase 27 execution. Engineering parallelism absorbs slack.
- **No architectural redesign in v2.1.** 3-process Tauri-shell + Python-sidecar + FastAPI-proxy model is locked. Every v2.1 feature lands via EXTEND / DOCK-TO-SLOT / NEW out-of-band — no new processes, no new buses (ports 8765 live + 8766 debrief stay).
- **Phase 31 4-layer mascot = ADDITIVE EXTENSION, not rewrite** (Pitfall P47). All v2.0 mascot tests port verbatim; priority-70 + 2.5s timeout + cancel-aware + linter-strip-aware preserved by exact test name.
- **Phase 28 closes v2.0 `register_library` final-mile orphan** (Pitfall P48) — invocation test + end-to-end live citation test + Phase 37 fresh-VM smoke required for "WIRED" verdict.
- **DJ profile NEVER per-turn prompt prefix** — lives in `GeminiContextCache` to preserve 1024-token floor (Pitfall P60). Content allowlist + jsonschema `additionalProperties: false` blocks track titles + free-form strings (Pitfall P51).
- **POC files (`cohost*.py`, `mascot.html`) UNTOUCHED across every v2.1 phase** — `test_g5_poc_files_untouched.py` extended with v2.1 modified-files allowlist (Phase 37 AUDIT-07).

### Decisions Locked (v0.1.0 + v2.0 carry-forward — see prior STATE.md history)

All Phase 1–26 decisions remain locked. Highlights:

- 3-process architecture (Tauri shell + Python sidecar + FastAPI proxy on `api.altidus.world`).
- Bundle ID `world.bravoh.vibemix` LOCKED — TCC permissions break on any change (Pitfall P63).
- AIza leak gate held: 0 / 482 files match at v2.0 close; v2.1 new bundled assets (40 Achird OPUS, Gemini Embedding 2 caches, real GLBs, mascot-pipeline outputs) re-scan and must stay 0.
- macOS 12.3+ / Windows 10/11. Linux excluded.
- Apache 2.0 + DCO license; signing via Apple Developer ID + SignPath OSS.
- Gemini-only AI (no Anthropic / OpenAI / Ollama / CLAP / OpenL3 / MERT / sentence-transformers / torch).
- Three.js (single 3D engine); vanilla TS in `tauri/ui/src/` (NOT React); WaveSurfer.js for Phase 29 timeline.

### Open To-dos

**v2.1 day-1 unblock actions:**

- **File SignPath OSS Foundation application** (Kaan-action) on day 1 — ~1-week SLA. Lives in `.planning/phases/38-signing-pipeline-real-execution/KAAN-ACTION-LEGAL.md` once Phase 38 scaffolds.
- **Start Apple Developer Program Agreement update prep** (Francesco-action) on day 1 — Issuer ID `3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b` already supplied 2026-05-14.
- **Run `/gsd-plan-phase 27`** to plan Phase 27 — foundation cluster's anchor.

**v2.1 parallel cluster A phases (planning-ready):**

- Phase 27 — Eval Harness + Carry-Forward Close-Out (no v2.1 prereqs)
- Phase 28 — Library Intelligence v1 (closes v2.0 register_library orphan; needs Phase 25 surface — shipped)
- Phase 29 — Post-Session Debrief MVP UI (docks into v2.0 DEBRIEF slot — shipped)
- Phase 30 — 2 Hard Tek Detectors (extends v2.0 GenreRouter — shipped)
- Phase 34 — Open-Source Security Pass (extends v2.0 CI scaffold — shipped)

**v2.1 sequential cluster B (gated):**

- Phase 31 needs Phase 30
- Phase 32 needs Phase 28 + Phase 30
- Phase 35 needs Phase 31

**v2.1 external-gated:**

- Phase 38 needs Apple Dev Agreement + SignPath OSS approval (external)
- Phase 33 needs Phase 38 (signed binary required for fresh-VM rehearsal)
- Phase 36 needs Phase 21 + Phase 26 scaffold (both shipped — can start in parallel with P35)

**v2.1 ship prep (sequential after all):**

- Phase 37 needs ALL v2.1 phases shipped
- Phase 39 needs Phase 37 + Phase 38 signed binary

### Blockers

- **Apple Developer Program Agreement update** — Francesco-action-required. Does NOT block Phase 27 entry, foundation cluster, or sequential cluster B; DOES block Phase 38.
- **SignPath OSS Foundation approval status** — Kaan-action-required (re-file day 1 of v2.1 if not already approved). ~1-week SLA. DOES block Phase 38.
- No engineering-side blockers for Phase 27 entry — proceed.

### Risks (v2.1 critical pitfalls — encoded in roadmap phase notes)

- **P42** (LLM-judge self-bias) → Phase 27 mitigation: 2-judge cross-check (Pro + Flash, different rubrics, both ≥ 0.80) + cited-but-empty cosine ≥ 0.4 filter + Kaan-veto bookmark.
- **P43** (replay-harness corpus overfit) → Phase 27 mitigation: ≥ 3 public-domain DJ sets, Hard Tek/techno ≤ 70%, per-detector-per-genre F1 matrix.
- **P44** (F1 too lenient) → Phase 27 mitigation: `useful_response_ratio ≥ 0.65` substance metric + per-event-class substance + bypass-rate ceiling 0.15.
- **P45** (citation linter gamed) → Phase 27 + 32 mitigation: min-8-words-around-citation + embedding-relevance check (orthogonal to F1).
- **P46** (legal-capacity autonomous-discharge attempt) → Phase 27 + 38 mitigation: `KAAN-ACTION-LEGAL.md` + CI bash audit grep against POST/PUT to apple/signpath endpoints.
- **P47** (4-layer mascot rewrite breaks priority 70) → Phase 31 mitigation: additive-only refactor, all v2.0 mascot tests port verbatim.
- **P48** (`register_library` final-mile orphan ships AGAIN) → Phase 28 + Phase 37 mitigation: invocation test + end-to-end live citation test + fresh-VM smoke.
- **P49** (GenreRouter atomic swap breaks during Hard Tek add) → Phase 30 mitigation: construct-time registration only via `MappingProxyType` + 1000-cycle stress test.
- **P50** (macOS 15 Settings reorg breaks TCC pre-grant) → Phase 33 mitigation: multi-version VM matrix (12.3 + 14 + 15) + dynamic URL fallback ladder.
- **P51** (DJ profile leaks track titles) → Phase 32 mitigation: profile content allowlist + jsonschema `additionalProperties: false` + user consent.
- **P52** (real GLBs push bundle past 350 MB cap) → Phase 31 + Phase 35 mitigation: CI gate < 350 MB + mascot sub-budget ≤ 25 MB + DRACO L7+ + KTX2/WebP.
- **41 v2.0 carry-forward pitfalls** + 35 high/medium (P53–P88) tracked in `.planning/research/v2-1/PITFALLS.md`, mapped to owning phase in roadmap.

---

## Session Continuity

### Last Session

- 2026-05-14 — v2.0 Research-Driven Ship SHIPPED + archived to `.planning/milestones/v2.0-ROADMAP.md`. Local annotated git tag `v2.0` created. 10/12 phases shipped Claude-side end-to-end + 2 deferred (P15-04 UAT, P16 ear-test). 1961 passing tests, 220 commits since `v0.1.0-rc1`. Status: `tech_debt` accepted per `gsd-autonomous fully` mode.
- 2026-05-14 — Milestone v2.1 "The Unified Cut" initiated via `/gsd-new-milestone`. PROJECT.md "Current Milestone" section appended; REQUIREMENTS.md v2.1 draft written (105 REQ-IDs across 13 phases enumerated). Research synthesis SUMMARY.md + STACK.md + FEATURES.md + ARCHITECTURE.md + PITFALLS.md anchored under `.planning/research/v2-1/`.
- 2026-05-14 — v2.1 ROADMAP scaffolded (this session). 13 phases P27–P39 derived 1:1 from research/SUMMARY.md bucket decomposition. REQUIREMENTS.md Traceability section populated (105/105 mapped, no orphans). Critical pitfalls P42–P52 encoded in phase notes; sequential / parallel build-order graph locked. Critical-path callout = external Apple+SignPath approvals (NOT engineering). Estimated wall-clock to RC: 5–7 weeks focused engineering.

### Next Session

- **Run `/gsd-plan-phase 27`** to plan Phase 27 — Eval Harness + v2.0 Carry-Forward Close-Out. Foundation cluster's anchor; no v2.1 prereqs.
- **In parallel: file SignPath OSS Foundation application + start Apple Developer Program Agreement update prep** (day-1 unblock actions for Phase 38 — external clock is critical path).
- **In parallel: `/gsd-plan-phase 28`, `29`, `30`, `34`** can ALL start once Phase 27 plan-checker passes (foundation cluster runs in parallel; assign Claude pulls accordingly).
- Phase 27 should produce: `scripts/eval/replay_harness.py` + `.github/workflows/eval.yml` + universal2 sidecar + WASAPI `IMMNotificationClient` subscription + 40 Achird OPUS recordings + DDJ-FLX4 sync sniff fixture + 5-min `register_library` patch.
- Phase 27 needs research-phase: judge prompt rubric design + corpus diversity sourcing (≥3 public-domain DJ sets license-cleared).
- Carry-forward Kaan-side outstanding (Phase 14): (a) `npm run tauri dev` visual review of all four CDJ Whisper v5 surfaces; (b) Windows transparency rehearsal — folds into Phase 33 fresh-VM matrix.

---

*State managed by gsd-roadmapper at 2026-05-14 (milestone v2.1 roadmap scaffolded — 13 phases P27–P39; Phase 27 entry-ready; foundation cluster A parallel-startable).*
