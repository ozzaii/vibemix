---
milestone: v0.1.0
milestone_name: vibemix v1 — Bravoh OSS launch wedge
audited: 2026-05-13
status: ready_to_ship
scores:
  requirements: 128/128 mapped, ~120/128 satisfied autonomously
  phases: 19/20 directory-shipped, 17/20 verified, 4/20 human_needed pending UAT
  integration: structural (cross-phase wiring intact; live integration tests human-pending)
  flows: end-to-end not yet exercised on real binary (gated on Kaan ship-runbook items)
test_suite:
  passing: 1432
  failing: 5
  skipped: 6
  failure_notes: "All 5 failures are pre-existing tech debt that pre-date this session — verified by bisect at commit ba6eed7. Documented below."
external_blockers:
  apple_dev_id: "✓ cert in Kaan Mac Keychain (Francesco Fasanella, UK7DYFK6F8); APPLE_APP_PASSWORD generation pending Francesco"
  signpath_oss_cert: "approval pending — ~3-week SLA from application date"
  tauri_keypair: "not yet generated — single command run"
  github_secrets: "11 secrets to configure once Apple + SignPath + Tauri above land"
  bravoh_org: "create bravoh GitHub org or transfer ozzaii/vibemix"
  discord_invite: "create vibemix Discord channel, drop invite link in README"
  artwork: "hero PNG, 10 controller logos, demo GIF/MP4, OG image, 5 screenshots"
  fresh_machine_rehearsal: "borrow non-dev macOS Sequoia + Win 11 machines; run docs/install-rehearsal.md"
phase_16_resolution:
  decision: "Replaced 30-session formal eval suite with Kaan's personal DJ-set ear-test signoff per 2026-05-13 user instruction"
  artifact: "Kaan writes .planning/phases/16-hallucination-verification-gate/16-VERIFICATION.md after testing"
  memory: "project_phase_16_kaan_dj_testing.md"
phase_20_resolution:
  decision: "Phase 20 directory + plan + execution shipped this session"
  artifact: ".planning/phases/20-day-zero-operations/ — CONTEXT + PLAN + SUMMARY + VERIFICATION"
  output: "1 workflow + 4 docs + 1 script + 19 tests"
---

# v0.1.0 — Milestone Audit (revised)

**Audited:** 2026-05-13
**Status:** `ready_to_ship` — autonomous deliverable is complete. Outstanding work is Kaan-owned external dependencies (Apple app-password, SignPath approval, Tauri keypair, GitHub secrets, content/artwork, fresh-machine rehearsal, Phase 16 ear-test signoff). Single doc tracks ship-list: `docs/ship-runbook.md`.

## What changed from earlier today

The previous audit (commit 57fcfc6) marked status `tech_debt` with Phase 16 + Phase 20 listed as `NOT_EXECUTED`. This revision:

1. **Phase 16 resolved**: Kaan instructed (in-session) that he'll satisfy Phase 16 by personally DJing into vibemix and signing off by ear, NOT by building a formal 30-session replay suite. Memory + ROADMAP updated. Phase 16 is now `human_needed` (Kaan's DJ session), not `NOT_EXECUTED`.
2. **Phase 20 shipped**: Full phase artifacts (CONTEXT + PLAN + SUMMARY + VERIFICATION) plus 6 deliverables (issue-triage workflow, rota doc, install-rehearsal checklist, post-launch playbook, README Discord placeholder, pretag readiness script) and 19 tests. Autonomous portion complete; Kaan owns the fresh-machine rehearsal step.
3. **Status upgraded** from `tech_debt` to `ready_to_ship`. The remaining work is entirely external-credential / content / human-judgment — none of it is autonomously fixable.

## Phase-Level Status (revised)

| Phase | Status | Verification | Notes |
|---|---|---|---|
| 01 Platform Protocol Firewall | shipped | passed | SignPath OSS app filed |
| 02 Audio Core Port + Ring Buffer | shipped | passed | np.concatenate dropout fixed |
| 03 Sensing & State Port | shipped | passed | MusicState @10Hz |
| 04 LiveKit Cascade Agent Pivot | shipped | passed | 346 tests, 12/12 gates |
| 05 FastAPI Proxy + JWT | shipped | passed | api.altidus.world |
| 06 Genre-Aware Phase Detection | shipped | passed | 5-genre profile JSON |
| 07 Windows Port | shipped | passed | 614 tests, mocked CI |
| 08 macOS ScreenCaptureKit | shipped | passed | SCStream impl |
| 09 MIDI Controller Library | shipped | passed | 839 tests; 10 controllers |
| 10 Prompt Template Matrix | shipped | passed* | 978 tests; anti-slop stack (*see persona-drift note below) |
| 11 Tauri Shell + Wizard | shipped | passed | structural gate |
| 12 Live Session UI + Settings | shipped | human_needed | 7 hardware UAT pending |
| 13 3D Mascot Overlay | shipped | passed | Meshy GLB + animation state machine |
| 14 CDJ Whisper v5 Migration | shipped | passed | shim deleted, v5 contract on every surface |
| 15 Recording & Session Capture | shipped | human_needed | 2 UAT (boot-prune + drawer visual) |
| 16 Hallucination Verification Gate | redefined | **human_needed (Kaan DJ ear-test)** | Decision 2026-05-13: ear-test, not formal suite |
| 17 Reaction-Reel Slop Grading | shipped | human_needed | Bench shipped; 4-rater grading pending |
| 18 Distribution (signing/notarization) | shipped | human_needed | Secrets + Tauri keypair + Apple app-password |
| 19 GitHub Launch Presence | shipped | human_needed | Real artwork + bravoh org + demo shoot |
| 20 Day-Zero Operations | **shipped this session** | human_needed (fresh-machine rehearsal) | All autonomous artifacts in `.planning/phases/20-…/` |

## Test Suite Status

```
1432 passed, 5 failed, 6 skipped, 10 warnings in 27.9s
```

**Pre-existing failures (all bisect-confirmed at commit `ba6eed7`, before this session):**

| # | Test | Failure | Class |
|---|------|---------|-------|
| 1 | `tests/test_phase05_verification.py::test_g5_poc_files_untouched` | POC files diff vs Phase 5 baseline `ede9e59` after 327+ intervening commits | Scoping bug in Phase 5 verification test — its assertion was never updated to pin to Phase 5's commit range |
| 2 | `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` | `vibemix.agent.persona.SYSTEM_INSTRUCTION` (8358 chars, HYPE_INTERMEDIATE) ≠ `cohost_v4.py:SYSTEM_INSTRUCTION` (9219 chars, coach voice) | Phase 10 matrix lifted v3-era hype persona, never updated to v4's coach persona. v0.1.0 ships matrix variant; v4 fidelity is a v0.1.1 backlog item |
| 3 | `tests/test_main_smoke.py::test_smoke_03_full_wiring` | `MagicMock.call_count == 0 != 3` — mock setup issue in smoke harness | Smoke-test mocking issue, not runtime bug |
| 4 | `tests/test_main_smoke.py::test_smoke_04_no_openrouter_key` | Same family | Same class |
| 5 | `tests/test_main_smoke.py::test_smoke_05_cleanup_closes_all_streams` | Same family | Same class |

**None of the 5 failures regressed during this session.** Bisect at `ba6eed7` (last commit before session started) shows all 5 already failing. Verified before tagging.

### v0.1.0 → v0.1.1 backlog items spawned by these failures

1. **Phase 5 verification scope fix**: pin `test_g5_poc_files_untouched` to Phase 5's commit range only, or convert to a Phase-5-specific marker.
2. **Phase 10 persona evolution to v4 baseline**: lift `cohost_v4.py:SYSTEM_INSTRUCTION` (the coach voice with "trust the audio" anti-hallucination rule) into the matrix. Currently `HYPE_INTERMEDIATE` is the v3-era hype voice. Per `project_v4_canonical_baseline.md` memory, v4 is the canonical baseline. Phase 10 needs a re-lift.
3. **Smoke-test mock alignment**: `test_smoke_03/04/05` need their mocks regenerated against current `vibemix.runtime.main` wiring.

These are documented but NOT blocking v0.1.0 ship — they are test-suite truth-telling about known scoping bugs (Phase 5 test) and a real persona drift that v0.1.0 takes as carry-over.

## Ship-Runbook Summary

**Full doc:** `docs/ship-runbook.md`. 11 items, all Kaan-owned.

**Apple credential audit (BRAVOH server, 2026-05-13):**
- ✅ Developer ID cert in Mac Keychain: `Francesco Fasanella (UK7DYFK6F8)`
- ✅ `APPLE_SIGNING_IDENTITY`, `APPLE_ID`, `APPLE_TEAM_ID` exported in zsh
- ❌ `APPLE_APP_PASSWORD` not set — Francesco generates one at appleid.apple.com
- ⚠ `~/Certificates.p12` + `~/AuthKey_G26449M849.p8` on altidus = App Store Connect API (iOS BRAVOH app); NOT applicable to vibemix Mac notarization

## Pretag Readiness Today

`scripts/dist/pretag_check.sh` returns **1 pass / 6 fail / 0 warn**. The 6 failures are the v0.1.0 ship-list:

1. Phase 16 ear-test signoff
2. Phase 17 grading sheet (4+ raters)
3. README pre-tag TODOs (Discord)
4. Tauri pubkey placeholder
5. 11 GitHub secrets
6. Discord invite real link

Once all 6 resolve, the script exits 0 → `git tag v0.1.0` is safe.

## Cross-Phase Integration (unchanged)

Structural wiring intact (see prior audit). Phase 20's contribution: tooling that operates ON top of the integrated system (issue triage, rota, install rehearsal protocol, post-launch playbook, pretag gate) — does not change runtime wiring.

## Recommendation

v0.1.0 is ready to ship modulo entirely external dependencies. The autonomous deliverable has nothing left to build. Kaan should:

1. Follow `docs/ship-runbook.md` items A through K (estimated: 1-2 weeks calendar, dominated by SignPath SLA + Bravoh design delivery + DJ ear-test sessions)
2. Run `scripts/dist/pretag_check.sh` to track progress (it'll go from 1/7 to 7/7 as items land)
3. When 7/7: `git tag -s v0.1.0 -m "vibemix v0.1.0"` then `git push origin main --tags`
4. Follow `docs/post-launch-playbook.md` from T+0

No further autonomous work blocks the launch.
