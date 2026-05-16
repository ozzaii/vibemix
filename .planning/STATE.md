---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Clean OSS Ship
status: planning
last_updated: "2026-05-16T01:00:00Z"
last_activity: 2026-05-16 -- v3.0 milestone scaffolded via /gsd:new-milestone after 4-bucket research swarm (.planning/research/v3-buckets/A-D.md). 6 phases (P40-P45), 57 REQ-IDs. Critical path: Apple Dev Agreement (Francesco) + SignPath OSS (Kaan, ~1-week SLA) gate the public RC publish in P45. P40-P44 engineering parallelizes around the external clock. Hybrid hallucination gate (Phase 27 autonomous proxy + Kaan-ear release veto) confirmed; P85 override formally retired in P42.
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# vibemix — State

**Last updated:** 2026-05-16 — v3.0 "Clean OSS Ship" milestone scaffolded. 6 phases (P40-P45), 57 REQ-IDs across 6 categories (AUDIO / LAT / GATE / VIS / LAUNCH / SHIP). Awaiting `/gsd:discuss-phase 40` or `/gsd:plan-phase 40` to start engineering.

---

## Project Reference

- **Project:** vibemix — open-source AI DJ co-host (Bravoh's first OSS release)
- **Core value:** "Real DJ friend in your ear" — never hallucinating, never breaking flow, never AI slop.
- **Current focus:** v3.0 — Clean OSS Ship (planning).
- **Last shipped:** v2.1 The Unified Cut — 2026-05-16 (status: `tech_debt` accepted).
- **Project mode:** standard.
- **Granularity:** fine.
- **Model profile:** quality (all agents on Opus, all checkpoints on).
- **Autonomy mode:** `gsd-autonomous fully` — every blocker + human-needed item discharged autonomously, only privacy rule + destructive risk + legal-capacity carveouts (Apple Dev Agreement + SignPath OSS) still pause.

---

## Current Position

Phase: Not started (defining phase plans)
Plan: —
Status: v3.0 scaffolded; awaiting first phase plan (`/gsd:discuss-phase 40` recommended; `/gsd:plan-phase 40` for direct).
Last activity: 2026-05-16 -- v3.0 milestone scaffolded. PROJECT.md updated with Current Milestone section. REQUIREMENTS.md written (57 REQ-IDs across AUDIO / LAT / GATE / VIS / LAUNCH / SHIP). ROADMAP.md updated with active v3.0 section (P40-P45). Research bucket .planning/research/v3-buckets/A-D.md committed as scoping basis.

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete (v0.1.0) | 14 / 14 |
| Phases complete (v2.0) | 10 / 12 code-shipped (2 deferred to Kaan-action) |
| Phases complete (v2.1) | 13 / 13 engineering-green (4 carry `human_needed` carveouts: Phase 33 / 35 / 38 / 39) |
| Plans complete (v2.1) | 96 / 96 |
| v2.0 REQ-IDs mapped | 94 / 94 ✓ (archived) |
| v2.1 REQ-IDs mapped | 105 / 105 ✓ (100% coverage, no orphans) |
| v2.1 REQ-IDs engineering-satisfied | 105 / 105 (100%) |
| v2.1 carveouts deferred to KAAN-ACTION-LEGAL | 15 (legal-capacity P46 × 2 + customer-facing publish × 6 + real-hardware × 4 + real-asset × 2 + post-approval × 1) |
| v2.1 cross-phase integration seams WIRED | 5 / 5 |
| v2.1 phase-scope tests added | 633 (on top of v2.0 1961 baseline) |
| v2.1 commits since `v2.0` tag | 225 |
| v2.1 LOC delta | +114,845 / -69,617 across 947 files (net ~+45k) |
| v2.1 git tag | `v2.1.0` (annotated, LOCAL ONLY — not pushed) |

---

## Accumulated Context

### Decisions Locked (v2.1 — shipped)

- **Phase numbering CONTINUED** from v2.0 — v2.1 closed at Phase 39. v2.2 starts at Phase 40 (no `--reset-phase-numbers`).
- **13-phase decomposition P27–P39** with build-order: parallel cluster A (27+28+29+30+34) → sequential B (31→32→35) → external-gated (38→33→36) → ship prep (37→39). Executed as planned.
- **`gsd-autonomous fully` mode** applied at milestone close — every Kaan-action item discharged autonomously EXCEPT two legal-capacity carveouts (DIST-09 + DIST-11). P46 hard rule + CI Bash + PowerShell audit grep enforces.
- **Phase 16 ear-test memory override accepted for v2.1 only** — Phase 27 autonomous proxy gate substituted. Override EXPIRES post-v2.1 (P85 enforced in Phase 39-08). v2.2 must re-route hallucination-gate strategy.
- **Universal2 sidecar = target-triple convention NOT lipo-merge** — research-corrected (Phase 27-06); eliminates Rosetta prompt on Apple Silicon.
- **Phase 31 4-layer mascot = ADDITIVE EXTENSION** (P47) — all v2.0 mascot tests port verbatim; grep gate enforces.
- **DJ profile NEVER per-turn prompt prefix** (P60) — lives in `GeminiContextCache`; jsonschema `additionalProperties: false` blocks track titles (P51); default-OFF consent.
- **Track-to-track similarity USER-ASKED-only** (LIBRARY-14 anti-feature guard) — physically gated to CLI + `ipc.library.similar_request`; never auto-surfaces.
- **POC files BYTE-IDENTICAL to v2.0 tag** — `cohost*.py`, `mascot.html`, `cohost.streaming.py.bak`; Phase 37-06 immutability gate enforces.
- **Honest RC labeling** — `v2.1.0-rc1` not premature `v1.0.0`; v1.0.0 decision deferred to Kaan post-2-week bake (SHIP-V1-DECISION).

### Decisions Locked (v0.1.0 + v2.0 — see prior STATE.md history)

All Phase 1–26 decisions remain locked. Highlights:

- 3-process architecture (Tauri shell + Python sidecar + FastAPI proxy on `api.altidus.world`).
- Bundle ID `world.bravoh.vibemix` LOCKED (Pitfall P63) — Phase 33-07 CI grep enforces.
- AIza leak gate held: 0 / 482 files match at v2.0 close + 0 new bytes in v2.1 (gitleaks Phase 34-01).
- macOS 12.3+ / Windows 10/11. Linux excluded.
- Apache 2.0 + DCO license; signing via Apple Developer ID + SignPath OSS.
- Gemini-only AI (no Anthropic / OpenAI / Ollama / CLAP / OpenL3 / MERT / sentence-transformers / torch).
- Three.js (single 3D engine); vanilla TS in `tauri/ui/src/` (NOT React); WaveSurfer.js for Phase 29 debrief timeline.

### Deferred Items (15 carveouts — KAAN-ACTION-LEGAL.md)

Categorized per `gsd-autonomous fully` mode at milestone close 2026-05-16:

| Category | Item | Status |
|----------|------|--------|
| legal_capacity_carveouts (P46) | DIST-09 (Apple Dev Agreement update — Francesco) | deferred |
| legal_capacity_carveouts (P46) | DIST-11 (SignPath OSS Foundation — Kaan, ~1-week SLA) | deferred |
| post_approval_mechanical | DIST-19 (sign+verify smoke on first signed binary) | deferred |
| post_approval_mechanical | SEC-06-PGP (real PGP key for security@bravoh.com) | deferred |
| post_approval_mechanical | TAURI-UPDATER-KEY (real ed25519 updater key) | deferred |
| real_hardware_carveouts | INSTALL-VM-RUN (fresh-VM rehearsal real execution) | deferred |
| real_hardware_carveouts | INSTALL-60S-CHECK (stopwatch onboarding ≤60s per VM) | deferred |
| real_hardware_carveouts | INSTALL-BLACKHOLE-PROBE (real Mac probe) | deferred |
| real_hardware_carveouts | INSTALL-DEFENDER (Defender SmartScreen reputation propagation — external 1-2 wk) | deferred |
| customer_facing_publishes | SHIP-CUT (gh release create v2.1.0-rc1 --draft) | deferred |
| customer_facing_publishes | SHIP-TWEET (4-channel social publish) | deferred |
| customer_facing_publishes | SHIP-DISCORD (#announcements launch post) | deferred |
| customer_facing_publishes | SHIP-TRANSFER (repo transfer to bravoh/vibemix org) | deferred |
| customer_facing_publishes | SHIP-ROTATE (24h monitoring rotation execution) | deferred |
| customer_facing_publishes | SHIP-V1-DECISION (cut v1.0.0 / RC2 / pause after ~2-week bake) | deferred |
| real_asset_production | ASSETS-PROD-GLB (5 real Meshy/Hunyuan3D + Mixamo-rigged GLBs) | deferred |
| real_asset_production | ASSETS-PROD-DEMO (30s demo.mp4 ffmpeg cut + README hero refresh) | deferred |
| ops_real_execution | OPS-09-RUN (run discord_provision.py against real Discord) | deferred |
| ops_real_execution | OPS-10-RUN (real 100 RPS prod load test — coordination required) | deferred |
| ops_real_execution | OPS-11-CRON (healthz cron install on Bravoh server) | deferred |
| ops_real_execution | OPS-12-OUTREACH (manual aligned-community outreach 15+ stars) | deferred |
| ops_real_execution | OPS-13-EXECUTE (run launch_trigger.sh --publish on launch day) | deferred |
| ops_real_execution | OPS-14-SERVER (Bravoh server /vibemix/updates/upload + healthz deploy) | deferred |
| bug_acceptance | HARDTEK-CORPUS-001 (real Hard Tek anchor-track curation; synthetic fixtures cover CI) | accepted in-scope cleanup |
| bug_acceptance | ACK-BANK-REMAINING-20 (20 of 40 Achird OPUS pending Gemini quota reset, ~$0.10) | accepted in-scope cleanup |
| bug_acceptance | EVAL-VCR-CASSETTES (one-time VCR_RECORD_MODE=new_episodes population) | accepted in-scope cleanup |
| bug_acceptance | EVAL-CORPUS-WAVS (6 × 30-min public-domain DJ session WAV downloads — 200 MB git-LFS) | accepted in-scope cleanup |
| bug_acceptance | BRAVOH-PROXY-PROBE (Bravoh proxy Wave 0 real-host probe; MOCK_PROXY_FOR_DEV=1 in dev) | accepted in-scope cleanup |
| bug_acceptance | AUDIT-VM (scripts/integration_audit.py on fresh VM — depends on Phase 33 + Phase 38 external clock) | accepted in-scope cleanup |
| bug_acceptance | AUDIT-SIGN-VERIFY (signed-binary verifier on real artifacts — depends on Phase 38 secrets) | accepted in-scope cleanup |

### Blockers

- **Apple Developer Program Agreement update** — Francesco-action, P46 legal-capacity. Blocks SHIP-CUT (real `gh release create`) and any signed-binary CI leg until discharged.
- **SignPath OSS Foundation approval** — Kaan-action, ~1-week SLA, P46 legal-capacity. Blocks Windows-signing CI leg + SHIP-CUT.
- No engineering-side blockers at v2.1 close. v2.2 can scaffold and execute in parallel with the external clock.

### Risks (v2.1 critical pitfalls — closed at milestone)

All 11 critical pitfalls (P42–P52) mitigated in shipped code. P46 (legal-capacity autonomous-discharge attempt) is the only ongoing live rule — CI Bash + PowerShell audit grep against POST/PUT to apple/signpath endpoints (Phase 27-04 + Phase 34-05 + Phase 38-06). P85 (Phase 16 ear-test override expiry) tracked for v2.2 hallucination-gate strategy.

---

## Session Continuity

### Last Session

- 2026-05-16 — v2.1 The Unified Cut SHIPPED + archived via `/gsd:complete-milestone`. 13 phases shipped engineering-green; 105/105 REQ-IDs satisfied; 5/5 integration seams WIRED. 15 carveouts in KAAN-ACTION-LEGAL.md. Local annotated git tag `v2.1.0` created (NOT pushed — Kaan publishes when ready). Status: `tech_debt` accepted per `gsd-autonomous fully` mode.
- 2026-05-16 — Phase 39 verified + Phase 37 integration audit + Section 8 gsd-audit-milestone extension confirmed WIRED + tech_debt verdict. v2.1-MILESTONE-AUDIT.md frozen at 105/105 engineering satisfied.
- 2026-05-15 — Phases 27–38 shipped (waves of 1-3 phases per day per `gsd-autonomous fully` execution cadence).

### Next Session

- **`/gsd:new-milestone` to scaffold v2.2** — Phase 16 ear-test override expires; choose either restored Kaan-ear-only gate OR permanent autonomous proxy adoption.
- **Track external clock**: Apple Developer Program Agreement update (Francesco) + SignPath OSS Foundation application (Kaan) discharge gates the v2.1.0-rc1 public publish — NEVER autonomously discharged per P46.
- **Once approvals land**: discharge KAAN-ACTION-LEGAL sequence — DIST-09 + DIST-11 → DIST-19 sign+verify smoke → Phase 33 real-VM matrix (INSTALL-VM-RUN + INSTALL-60S-CHECK + INSTALL-BLACKHOLE-PROBE) → Phase 38 signed-binary verifier → Phase 39 §SHIP customer-facing publishes (SHIP-CUT / SHIP-TWEET / SHIP-DISCORD / SHIP-TRANSFER / SHIP-ROTATE) → SHIP-V1-DECISION after ~2-week bake.
- **Re-run integration audit** after each carveout discharge: `python scripts/integration_audit.py --write-milestone-audit .planning/v2.1-MILESTONE-AUDIT.md --force`.

---

*State managed by gsd-complete-milestone at 2026-05-16 (v2.1 The Unified Cut archived — engineering-complete; KAAN-ACTION-LEGAL discharge gates public RC).*
