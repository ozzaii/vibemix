---
gsd_state_version: 1.0
milestone: v11.0
milestone_name: Earned
status: verifying
last_updated: "2026-05-28T23:36:52.491Z"
last_activity: 2026-05-28
progress:
  total_phases: 11
  completed_phases: 2
  total_plans: 4
  completed_plans: 4
  percent: 18
---

# vibemix — State

## Project Reference

**Core value:** The AI reacts to your set in a way that feels alive and grounded — never hallucinating, never sounding like AI slop. "Real DJ friend in your ear."
**v11.0 "Earned":** Turn the v9.0 Lesson One module into a DJ skill-tree where ~6 real DJ competencies each level up through a two-stage, evidence-grounded mastery bar — lessons fill a skill to "Competent", and only a real, **cited** live demonstration in an actual set unlocks "Mastered". Nothing is given; every notch is earned. A small, contained gamification layer that adds the felt reward of progression **without growing the product surface**.

## Current Position

Phase: 103 (Live Mastered Grounding) — COMPLETE
Plan: 2 of 2 (103-01 + 103-02 SHIPPED)
Status: Phase complete — ready for verification (`/gsd:verify-work`)
Last activity: 2026-05-29
Progress: [██████████] 100%

## Milestone Reference

See: `.planning/PROJECT.md` § "Current Milestone: v11.0 Earned" (goal · target features · locked constraints)
See: `.planning/ROADMAP.md` § "v11.0 Earned" (3 phases · phase details · success criteria · KAAN-ACTION queue)
See: `.planning/REQUIREMENTS.md` (16 v11.0 REQ-IDs across SKILL / COMP / MAST / DATA / SURF · traceability 16/16)

## Phase Spine

- **P102 — Skill-Tree Engine + Data Model + Competent Stage** (SKILL-01/02/03, COMP-01/02, DATA-01/02/03). Pure-logic `learn/skill_tree.py` (sole writer) + ~6-skill→lesson manifest + quality-weighted Competent fill gated on recital honest-score + `skills` block on `learn-progress.json` with v1→v2 back-fill + corrupt-recovery + reset. Standalone-verifiable WITHOUT UI. Lands Invariant #1 AST gate + Invariant #4 no-new-port gate.
- **P103 — Live "Mastered" Grounding** (MAST-01/02/03/04). Locked-until-Competent; thin recognizer maps EXISTING `EvidenceRegistry` event types → skill credit ONLY on a resolvable citation (un-cited/fabricated → zero credit; Invariants #2/#3 pinned); N grounded demos flip to Mastered with persisted count + `first_mastered_at`. NO new detectors. Engine-level verifiable on synthetic event streams.
- **P104 — Skill-Tree Surface + Earned Celebration** (SURF-01/02/03/04). UI phase. Skill-tree panel + quiet Competent cue + single rare grounded "Mastered" vocal (tone-gated, ear-pass parked) + v9.0 accessibility. Exact surface + celebration = Kaan design decision-gate during the phase. Rides `learn.*` on :8765; `messages.schema.json` edit → `npm run codegen:ipc`.

## Accumulated Context

**Locked constraints (encoded in every phase — anti-creep):** ZERO new AI provider / ws port / IPC envelope family / heavy dep / lesson content / live event detector. NO streaks / leaderboards / social / cohort (→ Bravoh). Single-user local only. NEVER write to `profile.json` (5-field `additionalProperties:false` privacy contract). All 4 cardinal invariants hold by ADDITIVE design. Honest green (engine offline-unit-testable; live-app gate for P104 per `feedback_verify_live_app_not_just_tests`).

**Island:** `src/vibemix/learn/` (+ `learn-progress.json` schema + `learn.*` IPC). Disjoint from concurrent One Mind (`src/vibemix/**` minus learn), LiveKit-upgrade (`__main__.py`/`agent/`), frontend-wiring (`tauri/ui/*`). P104 coordinates `tauri/ui` disjointness. Per `feedback_concurrent_sessions_one_tree`: surgical commits, never `git add -A`.

**Builds on v9.0:** `learn/progress.py::LearnProgress` (`SCHEMA_VERSION 1 → 2` here) · `learn/recital.py::RecitalRuntime` honest-score gate · `learn/curriculum.py::CURRICULUM` (36 lessons) · live `state/evidence_registry.py` + `state/event_detector.py` taxonomy (unchanged).

**Mode:** `gsd-autonomous fully` · all-opus · default-YES on grey-area. Human-only blockers ride to KAAN-ACTION; only privacy hard rule + destructive risk pause.

## KAAN-ACTION Queue (v11.0 — parked, never faked)

**BLOCKING (before public ship):**

- 🔴 `§EARNED-MASTERED-VOCAL-EAR` (P104) — ear-pass on the rare grounded "Mastered" unlock vocal (real friend vs gamification slop).
- 🔴 `§EARNED-LIVE-MASTERED-VERIFY` (P103) — real-FLX4 live verify: a cited event advances Mastered; an un-cited moment does not.

**NON-BLOCKING:**

- 🟡 `§EARNED-SURFACE-DESIGN-GATE` (P104) — exact panel layout + celebration treatment is Kaan's design decision during P104.
- 🟡 `§EARNED-MASTERY-THRESHOLD-TUNE` (P103) — per-skill `N` (grounded-demo count) ships with a default; Kaan tunes after live verify.

## Deferred Items (carried from v10.0 — ride Kaan's clock, never block)

| Category | Item | Status |
|----------|------|--------|
| verification_gap | v10.0 §HARDEN-PHASE-A-EAR-PASS (`tool_starvation` tone) | human_needed |
| verification_gap | v10.0 §HARDEN-PHASE-A-ENV-PROPAGATION-VERIFY | human_needed |
| verification_gap | v10.0 §HARDEN-PHASE-B-CLARIFICATION-TONE | human_needed |
| verification_gap | v10.0 §HARDEN-PHASE-C-DOC-READTHROUGH | human_needed |
| ear_pass | v9.0 §LEARN-EAR-COURSE-1/2/3 + §LEARN-LEGAL-DISCLAIMER | human_needed |

## Audit Trail (retired overrides)

- **Phase 16 ear-test memory override — RETIRED** as of Plan 42-05 (2026-05-16). The v2.1 P85 autonomous-only override is formally retired and replaced by the v3.0 hybrid hallucination gate (`scripts/release/check_gate.sh` + `check_ear_test.sh`) wired into `cut_release.sh` at Gate 2b. Cross-reference: `.planning/decisions/P85-OVERRIDE-RETIRED.md`. (v8.1 BENCH-03 re-invokes the Phase-16 "Kaan's ear is final judge" rule for the bench — consistent with the hybrid gate: auto-eval is the fast-lane rank, Kaan's ear is the veto.)

## Open Alongside (Other Workstreams)

- **v4.0 SHIP** — engineering-complete 8/8 since 2026-05-21; publish gated on Apple Dev + SignPath signature clock. Not archived.
- **v0.1.0-rc1 ship work** — bundle/launchd fixes in flight; KAAN-ACTION ear-pass + signed-release decision parked. See `.planning/handoffs/2026-05-27-session-end.md`.
- **LiveKit-upgrade handoff** — `src/vibemix/__main__.py:1353` `turn_handling` + livekit-agents 1.5.8→1.5.14. Separate session, NOT yet committed. See memory `project_streaming_pipe_speedfix_livekit_upgrade_handoff`.
- **Frontend wiring handoff** — `tauri/ui/*` rocker visual-sync, status-tick, pill hover-peek. Separate session. See memory `project_frontend_wiring_handoff`.

## Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260529-ifq | Onboarding skill-level wizard step (beginner/intermediate/pro) + config.json clobber fix | 2026-05-29 | f74635fd | [260529-ifq-onboarding-skill-level-wizard-step](./quick/260529-ifq-onboarding-skill-level-wizard-step/) |
| 260529-m4m | Converge config.json store path (Rust→sidecar `vibemix/` dir) + reload-harden all 5 writers | 2026-05-29 | 7780322c | [260529-m4m-converge-config-store-path](./quick/260529-m4m-converge-config-store-path/) |

## Session Continuity

**102-01 SHIPPED (2026-05-29):** DATA-01/02/03. `learn/progress.py` `SCHEMA_VERSION 1→2` with a forward-compatible 6-skill `skills` live-portion block; explicit `_migrate_v1_to_v2` upgrader (preserves lesson history, never wipes v1); idempotent v2 reload (Phase-103 live data not clobbered, keyed on `schema_version==1`); corrupt-recovery seeds an empty v2 block; IPC reset clears the in-memory skills ledger. Only the live-portion (`live_proof_count`/`mastered`/`first_mastered_at`) is stored — `learn_fill`/`competent` are DERIVED by the Wave-2 engine (zero dual-write drift). `__main__.py`/`profile.json` untouched. Commits `ad9fd4de`→`43a54aad`→`32e5fbfc`. `tests/learn` 461 passed. Shared-tree note: concurrent One Mind learn-island edits to `progress.py`/`ipc_handlers.py`/`test_progress_persistence.py` were absorbed (git commits whole files; all on-island + green).

**102-02 SHIPPED (2026-05-29):** SKILL-01/02/03, COMP-01/02. Pure-logic `learn/skill_tree.py` (279 lines): 6-skill `SKILL_MANIFEST`→real CURRICULUM lesson ids + recital gate (import-time drift assertion), `SkillSpec`/`SkillProgress` dataclasses, `SkillTree.compute(progress)` single-arg pure engine. Quality-weighted fill (first-try 1.0 > with-strikes 0.6 > floor 0.0; `COMPETENT_THRESHOLD 0.6`), monotonic on reload (Pitfall 4b). **COMP-02 headline: Competent AND-gates `course_N_unlocked` — 100% click-through with the gate False stays `locked`** (`test_full_clickthrough_without_recital_not_competent` is a real assertion). 3 invariant pins green (#1 no MusicState write, #4 no new ws port, privacy no profile.json leak — `PROFILE_SCHEMA` still exactly 5 fields). Live-portion read read-only from `progress.skills`; learn-portion derived every call (zero dual-write drift). Commits `ad771709`→`22861a65`→`b8af7f58`. `tests/learn` 479 passed / 1 skipped. Shared-tree: 3 NEW files, surgical `--files` commits, no absorption.

**Phase 102 COMPLETE — verified.** Both plans (102-01 data model, 102-02 engine) shipped; 8/8 phase REQ-IDs (DATA-01/02/03 + SKILL-01/02/03 + COMP-01/02) done.

**103-01 SHIPPED (2026-05-29):** MAST-01, MAST-04. Added the deferred-from-102 live-portion WRITER to `learn/skill_tree.py` (additive only): `SkillSpec.mastered_threshold` (uniform default 3, per-skill tunable — future `§EARNED-MASTERY-THRESHOLD-TUNE` is a manifest edit), `_threshold_for(skill_id)` helper, and `record_live_demo(progress, skill_id, *, now) -> LearnProgress`. Pure transform over `progress.skills[skill_id]`: MAST-01 derived-Competent gate (`SkillTree.compute(...).competent` — NO-OP + zero write when not Competent / unknown id, no buffered backfill), increment with the same `int(... or 0)` + try/except never-raises guard `compute` uses, flip `mastered=True` + stamp `first_mastered_at=now` ONCE on the not-mastered→mastered transition (idempotent, monotonic). `now` injected (no clock); persistence is the caller's job. Five new tests (flip-at-N, idempotent-stamp, locked-no-op, save→load `stage="mastered"`, garbage-degrade). All 4 cardinal invariants hold by additive design (purity / no MusicState / no port — `test_skill_tree_invariants.py` green). Commits `b8c968c5` (test RED) → `db0e27f2` (feat GREEN). `tests/learn` 496 passed / 1 skipped. Surgical `--files` commits, learn-island only.

**103-02 SHIPPED (2026-05-29):** MAST-02, MAST-03. New pure-logic `learn/skill_recognizer.py` — the citation-gated reverse event→skill map (the anti-slop spine). `EVENT_SKILL_MAP` (single source) over REAL `state/event_detector.py` literals: `LAYER_ARRIVAL→transitions`, `PHASE`/`PHRASE_BOUNDARY→phrasing_performance`; `MIX_MOVE` resolves by move-substring (`_low:`/`_mid:`/`_hi:`/`killed`→`eq_mixing`, `_play→`/`xfader`→`deck_control`; one MIX_MOVE can credit BOTH — not a double-count). `recognize(event, *, citation_check, progress, now, _seen=None) -> list[str]`: MAST-03 spine — credit ONLY when the INJECTED `citation_check("ev", event.type, t)` predicate (live wraps `EvidenceRegistry.has`; tests inject True/False) resolves true; un-cited/fabricated → ZERO credit. Dedup by `(type, round(t,1))` transient batch set; credit delegated to `record_live_demo` (owns MAST-01 Competent gate + MAST-04 flip). **Finding #1 (anti-slop):** `beatmatching` + `harmonic_mixing` are HONEST-UNCREDITABLE in v11.0 — NO map entry / NO MIX_MOVE resolution, capped at Competent, NO proxy-slop (pinned by `test_unsignalled_skills_never_auto_master` with both made Competent first). TYPE_CHECKING-only `state/` imports — engine stays offline + island-clean. Headline `test_uncited_event_grants_zero_mastery_credit` (same event, cited=credits / uncited=zero — non-vacuous). New static gate `test_skill_recognizer_no_runtime_state_import` (TYPE_CHECKING-aware) + integration-flavored real-`EvidenceRegistry` seam test. Commits `3ad307ba` (test RED) → `5b6993e6` (feat GREEN) → `8deee4e9` (test invariant+seam). `tests/learn` 509 passed / 1 skipped. 2 NEW files + 1 additive test extension; surgical `--files`, learn-island only.

**Phase 103 COMPLETE.** Both plans (103-01 record_live_demo writer, 103-02 skill_recognizer) shipped; 4/4 phase REQ-IDs (MAST-01/02/03/04) done. The live-firing call-site (`runtime/coach.py`/`__main__.py`) stays a deferred KAAN-ACTION (`§EARNED-LIVE-MASTERED-VERIFY`) — non-learn island, untouched.

Next step: `/gsd:verify-work` on Phase 103, then Phase 104 (Skill-Tree Surface + Earned Celebration — the UI phase, `tauri/ui` coordination). Read `.planning/ROADMAP.md` § Phase 104 + the locked constraints above.
