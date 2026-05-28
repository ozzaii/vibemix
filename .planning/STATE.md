---
gsd_state_version: 1.0
milestone: v11.0
milestone_name: Earned
status: roadmapped
last_updated: "2026-05-29T00:00:00.000Z"
last_activity: 2026-05-29
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# vibemix — State

## Project Reference

**Core value:** The AI reacts to your set in a way that feels alive and grounded — never hallucinating, never sounding like AI slop. "Real DJ friend in your ear."
**v11.0 "Earned":** Turn the v9.0 Lesson One module into a DJ skill-tree where ~6 real DJ competencies each level up through a two-stage, evidence-grounded mastery bar — lessons fill a skill to "Competent", and only a real, **cited** live demonstration in an actual set unlocks "Mastered". Nothing is given; every notch is earned. A small, contained gamification layer that adds the felt reward of progression **without growing the product surface**.

## Current Position

Phase: 102 — Skill-Tree Engine + Data Model + Competent Stage (next: `/gsd:plan-phase 102`)
Plan: —
Status: Roadmapped — 3 phases (P102–P104), 16/16 REQ-IDs mapped, 0 orphans
Last activity: 2026-05-29 — v11.0 roadmap created (P102→P103→P104 linear spine)
Progress: [----------] 0/3 phases · 0% — █ P102 (engine + Competent) → P103 (live Mastered) → P104 (surface + celebration)

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

## Open Alongside (Other Workstreams)

- **v4.0 SHIP** — engineering-complete 8/8 since 2026-05-21; publish gated on Apple Dev + SignPath signature clock. Not archived.
- **v0.1.0-rc1 ship work** — bundle/launchd fixes in flight; KAAN-ACTION ear-pass + signed-release decision parked. See `.planning/handoffs/2026-05-27-session-end.md`.
- **LiveKit-upgrade handoff** — `src/vibemix/__main__.py:1353` `turn_handling` + livekit-agents 1.5.8→1.5.14. Separate session, NOT yet committed. See memory `project_streaming_pipe_speedfix_livekit_upgrade_handoff`.
- **Frontend wiring handoff** — `tauri/ui/*` rocker visual-sync, status-tick, pill hover-peek. Separate session. See memory `project_frontend_wiring_handoff`.

## Session Continuity

Next step: `/gsd:plan-phase 102` (Skill-Tree Engine + Data Model + Competent Stage). Engine-only phase — fully offline-unit-testable, standalone-verifiable without UI. Read `.planning/ROADMAP.md` § Phase 102 + the locked constraints above before touching `src/vibemix/learn/`.
