---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Clean OSS Ship
status: Session + overlay HIGH-findings-closed; 20 --glow-faint sites; storyboard 8-cut re-mock + cut-count gate; Mixamo retarget scaffold + §VIS-04 runbook; meter LED-strip rebuild; doc drift cleaned; Francesco capture-day handoff package shipped (4 docs + demo-mode 30-event sequencer + §VIS-09 dual sign-off runbook). VIS-01, VIS-02, VIS-03, VIS-04 (scaffold), VIS-07, VIS-08, VIS-09 closed. README hero one-liner locked + "No AI slop" hook section + 3-gate CI lock shipped; LAUNCH-01 closed.
last_updated: "2026-05-16T17:45:26.978Z"
last_activity: 2026-05-16
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 35
  completed_plans: 29
  percent: 67
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

Phase: 43 — Visual Ship Lock (IN PROGRESS — Wave 3 active) + Phase 44 — Launch Positioning + Pre-stage (IN PROGRESS — Wave A active)
Plan: 43-01, 43-02, 43-03, 43-04, 43-05, 43-07, 43-08, 43-09 COMPLETE (8/9). Remaining: 43-06 (mood pool runtime + perf). Phase 44: 44-01 COMPLETE (1/7) — LAUNCH-01 closed. Remaining: 44-02 through 44-07.
Status: Session + overlay HIGH-findings-closed; 20 --glow-faint sites; storyboard 8-cut re-mock + cut-count gate; Mixamo retarget scaffold + §VIS-04 runbook; meter LED-strip rebuild; doc drift cleaned; Francesco capture-day handoff package shipped (4 docs + demo-mode 30-event sequencer + §VIS-09 dual sign-off runbook). VIS-01, VIS-02, VIS-03, VIS-04 (scaffold), VIS-07, VIS-08, VIS-09 closed. README hero one-liner locked + "No AI slop" hook section + 3-gate CI lock shipped; LAUNCH-01 closed.
Last activity: 2026-05-16

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
| Phase 40 P04 | 11 | - tasks | - files |
| Phase 41 P06 | 30min | 4 tasks | 8 files |
| Phase 42 P03 | 14 | 3 tasks | 15 files |
| Phase 42 P06 | 7min | 3 tasks | 3 files |
| Phase 43 P04 | 11m 48s | 3 tasks | 6 files |
| Phase 43 P07 | 14m 11s | 3 tasks | 7 files |
| Phase 43 P08 | 14m 57s | 2 tasks | 3 files |
| Phase 43 P05 | 14m 02s | 3 tasks | 8 files |
| Phase 44-launch-positioning-pre-stage P01 | 10min | 2 tasks | 3 files |

## Accumulated Context

### Decisions Locked (v3.0 — in progress)

- **Plan 40-01 — `AudioBuffer` reuse over new `MicAudioRing` class** (2026-05-16) — CONTEXT.md's `MicAudioRing` name was permitted but the PLAN `<interfaces>` + RESEARCH "Alternatives Considered" recommended verbatim `AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)` reuse to match `cohost_v4.py:2257`. Anti-DRY subclass avoided.
- **Plan 40-01 — Zero-fill at sounddevice callback boundary, not in `llm_node`** (2026-05-16) — Pitfall 1 (self-triggered KAAN_SPOKE loop) is real. Filtering in `llm_node` still lets the AI's own voice contaminate the mic ring. The callback-boundary zero-fill is load-bearing IP and keeps every downstream consumer clean. v4:2278-2296 verbatim pattern.
- **Plan 40-01 — Three-gate Part 2 decision computed once per turn** (2026-05-16) — Snapshot + RMS reused for both prompt-suffix wording and structured log line. Avoids double-work on the LLM hot path.
- **Plan 42-03 — `signed_by` enum locked to `[kaan]` at JSON Schema level** (2026-05-16) — Single-DJ regime is the v3.0 ship gate; cross-DJ sign-off requires schema bump + check_ear_test.sh update (deferred to v3.x per Plan 42 CONTEXT).
- **Plan 42-03 — 30-min minimum enforced at JSON Schema level (`duration_s >= 1800`)** (2026-05-16) — Writer is the only producer of logs, so the bash gate trusts the schema rather than re-checking; avoids contract drift between writer + gate.
- **Plan 42-03 — `schema.json` co-located with logs under `eval/ear-test-logs/`** (2026-05-16) — Writer + bash gate import paths stay trivially relative; bash gate skips `schema.json` by basename when globbing `*.json` so it does not pollute the log enumeration.
- **Plan 42-06 — Anti-slop manifesto link target = project root README.md** (2026-05-16) — CONTEXT D-GATE-09's "cross-link to the anti-slop manifesto" satisfied via existing `../README.md#what-it-does` ("A real DJ friend in your ear — no AI slop") rather than creating a new `docs/ASLOP-MANIFESTO.md`. Existing public surface satisfies the contract without doc proliferation.
- **Plan 42-06 — Privacy tests skip-cleanly (not vacuous-true) when no ear-test logs exist** (2026-05-16) — `pytest.skip` with informative message surfaces the §GATE-05 outstanding state in CI output. Contract still holds and will fire once logs land. Avoids false-positive green coverage.
- **Plan 42-06 — Threshold mirror via parametrized 2-decimal normalization** (2026-05-16) — README locked values formatted as `{value:.2f}` and asserted substring-present per key (`f1_min`, `substance_min`, `cited_cosine_min`, `bypass_max`, `per_genre_f1_min`). Catches both numeric drift AND format drift in the README table.
- **Plan 42-06 — Rubric-leak sentinel derivation at test-time** (2026-05-16) — sentinels read from `judge_pro.md` + `judge_flash.md` first-meaningful-chunk (post-YAML frontmatter, ≥40 chars). Self-updating against rubric evolution; removes Phase 27's documented hardcoded-sentinel maintenance burden.
- **Plan 43-05 — Output dir default = `tauri/ui/assets/mascot/animations/`** (2026-05-16) — CONTEXT §VIS-04 named `tauri/ui/public/mascot/` but no files exist there; existing 5 placeholders + manifest.json + `asset-loader.ts` `s.startsWith('prep_')` convention live in `assets/mascot/animations/`. Default matches reality; `--output-dir` flag still lets Kaan override.
- **Plan 43-05 — Retarget remap stays `NotImplementedError` in plan; two paths in §VIS-04** (2026-05-16) — Scaffold ships CLI + slot taxonomy + draco shell-out + size-band predicate + file-existence guard fully functional, but the load-bearing skeleton remap is intentionally not implemented. §VIS-04 runbook documents pygltflib (preferred) + blender headless (fallback) — Kaan picks at discharge time once Mixamo source clips are downloaded.
- **Plan 43-05 — Bundle-gate two-tier with placeholder-permissive exit-2** (2026-05-16) — Tier 1 delegates to existing Phase 31 25 MB cap (no duplication); Tier 2 adds prep_*.glb 400 KB-1200 KB band check. Today's placeholders (44-56 KB) intentionally fail Tier 2 with exit 2, which is the visible signal that §VIS-04 discharge is still pending. Test asserts `{0, 2}` not strict 0.
- **Plan 44-01 — README hero one-liner gate is case-sensitive + exact-count=1, anchor + blocklist gates case-insensitive** (2026-05-16) — Locked tagline "the only AI co-host that actually listens to your set" enforced verbatim (1 occurrence exact); case-sensitivity catches Francesco-reword drift, exact-count catches copy-paste duplicates. Anchor phrases (`real DJ friend in your ear`, `built by DJs`, `your audio doesn't leave`, `open source`/`open-source`, `Mac + Windows`) + AI-slop blocklist gates (15 tokens + `\bdeeply\s+\w+` regex) stay case-insensitive — anchor phrases naturally vary in sentence casing, blocklist must catch any casing. `scripts/launch/check_readme_hero_lock.py` is now the single source of truth for the blocklist; future plans (44-05 SHIP-TWEET) import `_AI_SLOP_BLOCKLIST` rather than redeclaring.
- **Plan 44-01 — "## No AI slop" H2 inserted between `<!-- vibemix:hero-end -->` and badge row** (2026-05-16) — Section is the explicit anti-slop value-prop, earns the H2 slot ahead of badges + Install. The existing inline `**A real DJ friend in your ear — no AI slop.**` paragraph below the badges remains as editorial voice — anchor phrase coverage is intentionally redundant (lock script only requires presence, not uniqueness).

### Decisions Locked (v2.1 — shipped)

- **Phase numbering CONTINUED** from v2.0 — v2.1 closed at Phase 39. v2.2 starts at Phase 40 (no `--reset-phase-numbers`).
- **13-phase decomposition P27–P39** with build-order: parallel cluster A (27+28+29+30+34) → sequential B (31→32→35) → external-gated (38→33→36) → ship prep (37→39). Executed as planned.
- **`gsd-autonomous fully` mode** applied at milestone close — every Kaan-action item discharged autonomously EXCEPT two legal-capacity carveouts (DIST-09 + DIST-11). P46 hard rule + CI Bash + PowerShell audit grep enforces.
- **Phase 16 ear-test memory override [RETIRED post-v2.1]** — replaced by v3.0 hybrid gate (Phase 42). See .planning/decisions/P85-OVERRIDE-RETIRED.md. Phase 27 autonomous proxy = fast lane; Kaan ear-test = slow lane (release-cut Gate 2b veto).
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

- 2026-05-16 — Plan 43-08 complete: hero demo storyboard re-mocked to 8-cut 30s sequence per CONTEXT §VIS-08; UI chip overlays in cuts 2-6 inline-rendered with CDJ Whisper v5 (wizard welcome, calibration meter, session shell, AI caption pop, EvidenceRegistry chip strip); end-card carries `open-source · MIT · github.com/bravoh/vibemix` star-funnel CTA; ≤8 cut hard gate wired via `scripts/launch/check_cut_count.py` + 6-test pytest spec; 12/12 launch-prep pytests green. Commits: c1877ed (test RED) + 6e7dd06 (feat GREEN) + f53cb9f (storyboard re-mock). Closes VIS-08; unblocks Plan 43-09 (Francesco handoff package).
- 2026-05-16 — Plan 43-07 complete: mascot memory snapped to "Neon Rebel"; storyboard mock migrated from Workbench + DSEG7 to Saira + Geist Mono on the 5-warm-blacks + 1-amber CDJ Whisper palette; `scripts/launch/check_storyboard_palette.py` + 6-test pytest spec wired as drift-prevention gate. Commits: 4054536 + 2e4c1eb (test RED) + 927f79f (feat GREEN). Closes VIS-07.
- 2026-05-16 — Plan 42-04 complete: `scripts/release/check_gate.sh` (hybrid hallucination gate combining last-7 nightly proxy scorecards from `.planning/eval-runs/` AND `check_ear_test.sh`) + wired Gate 2b into `scripts/launch/cut_release.sh` + retired v2.1 P85 reminder echo lines. 22 tests added (14 bash-gate + 8 cut_release wire-in; 21 pass + 1 conditional jq-missing skip). Phase 39 regression baselines preserved (test_g5_poc_files_untouched + test_bundle_id_locked green; verify_signed.py call still in Gate 2). Closes GATE-06 (hybrid release gate plumbing); GATE-08 partially advanced (echo-line removal; Plan 42-05 owns the test-file retirement + P85-OVERRIDE-RETIRED.md decision-log). Commits: 4a77b4d + c204318.
- 2026-05-16 — Plan 42-03 complete: ear-test protocol doc + JSON Schema + Python capture writer + Phase 29 debrief toggle UI + `check_ear_test.sh` release gate + §GATE-05 Kaan-discharge runbook. 41 tests added (40 pass + 1 conditional jq-missing skip); Phase 29 105-test debrief suite still green. Closes GATE-05 (protocol) + GATE-07 (capture); unblocks Plan 42-04 `check_gate.sh` Gate-2.
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
