---
phase: 17-reaction-reel-slop-grading-gate
plan: 01
subsystem: governance-docs
tags:
  - phase-17
  - rubric
  - capture-protocol
  - iteration-loop
  - docs
  - verify-02
requirements_satisfied:
  - VERIFY-02
dependency_graph:
  requires: []
  provides:
    - "17-RUBRIC.md — anchored 1-5 scale + 10-field grade schema + pass thresholds + tie-breaker"
    - "17-CAPTURE-PROTOCOL.md — 5 × 6-min segment matrix + capture pre-flight + recordings output shape"
    - "17-ITERATION-LOOP.md — gate-fail trigger + 3-cycle Phase 10 re-entry + Hype-man-only escalation"
  affects:
    - "Plan 17-02 (scripts/reaction_reel/grade.py) — consumes 10-field schema verbatim"
    - "Plan 17-03 (scripts/reaction_reel/analyze.py) — consumes pass thresholds + tie-breaker verbatim"
    - "Phase 10 (prompt-template matrix) — iteration loop targets matrix.py if gate fails"
tech_stack:
  added: []
  patterns:
    - "Source-of-truth docs reference source-code paths (src/vibemix/prompts/negative_dict.py, src/vibemix/prompts/matrix.py) by path instead of copying contents — drift-resistant when downstream phases evolve"
    - "Locked schema lives in rubric Markdown table; Plan 17-02/17-03 will grep this table for contract enforcement"
key_files:
  created:
    - ".planning/phases/17-reaction-reel-slop-grading-gate/17-RUBRIC.md"
    - ".planning/phases/17-reaction-reel-slop-grading-gate/17-CAPTURE-PROTOCOL.md"
    - ".planning/phases/17-reaction-reel-slop-grading-gate/17-ITERATION-LOOP.md"
  modified: []
decisions:
  - "Field schema (10 fields) is the rubric document, not the tooling — tooling MUST grep the rubric for field names"
  - "Anti-slop dictionary referenced by path (src/vibemix/prompts/negative_dict.py), never duplicated in the rubric — drift-resistant"
  - "Capture protocol's 5 × 6-min matrix pins skill distribution (Beginner ×1 / Intermediate ×2 / Pro ×2) — covers all 3 axes inside 30 min"
  - "Iteration loop preserves 2 of 4 raters (Francesco + dj2) across cycles for final blind re-grade — 'blindness invariant'"
  - "3 failed cycles → Hype-man-only scope-cut is Kaan's call, not automated"
metrics:
  duration_minutes: ~5
  completed_date: "2026-05-13"
  tasks_completed: 2
  files_created: 3
  files_modified: 0
  source_code_changes: 0
  test_additions: 0
---

# Phase 17 Plan 01: Governance Docs (Rubric / Capture Protocol / Iteration Loop) Summary

**One-liner:** Locked the three human-facing governance docs for the slop grading gate — anchored 1-5 rubric with 10-field schema, 5 × 6-min reel capture matrix covering all axes, and 3-cycle Phase 10 re-entry loop with Hype-man-only escape hatch.

## What Shipped

Three Markdown documents under `.planning/phases/17-reaction-reel-slop-grading-gate/`:

1. **17-RUBRIC.md** (125 lines) — Source-of-truth for VERIFY-02 grading. Anchored 1-5 scale with concrete persona-fit examples per score, locked 10-field grade-record schema as a table (reaction_id / score / rater / grounded / timely / unique / personality_fit / slop_flag / comment / would_clip), 6 `slop_flag` enum values explained, pass thresholds verbatim (avg ≥ 4.0 AND zero 1-2), tie-breaker at avg ∈ [3.95, 4.05] + >25% threes → Kaan decides. References `src/vibemix/prompts/negative_dict.py` for the slop dictionary (no duplication).

2. **17-CAPTURE-PROTOCOL.md** (70 lines) — Instruction set for Kaan recording the 30-min reel. The 5 × 6-min segment matrix (techno / house / drum & bass / disco / pop), each split 3 + 3 min Hype-man/Coach at a chosen skill level. Skill distribution: 1× Beginner / 2× Intermediate / 2× Pro across the five segments — covers all three Phase 17 axes (5 genres × 2 modes × 3 skill levels) inside 30 minutes. 6-step pre-flight checklist (boot vibemix → curate playlist → start QuickTime screen+audio → start vibemix session → run reel → normal close). Output shape (`recordings/<YYYYMMDD-HHMMSS>/` per Phase 15-02: session.json + events.jsonl + voice.wav + input.wav). ≥40 reactions expected; <25 → re-record; >80 → Phase 10 calibration pass.

3. **17-ITERATION-LOOP.md** (69 lines) — Gate-fail recovery protocol. Trigger condition is `verdict: FAIL` from `analyze.py` (avg < 4.0 OR any 1-2). 3-cycle budget; each cycle = 4 steps (identify worst cells from `report.md` → surgical edit to Phase 10's `src/vibemix/prompts/matrix.py` → re-record 10-min focused reel → re-grade with Kaan + dj1 only, preserving Francesco + dj2 for the final blind re-grade so the blindness invariant survives). After 3 failed cycles: default escalation is Hype-man-only scope-cut (Kaan's decision). Each cycle's `report.md` gets archived as `17-CYCLE-<N>-REPORT.md` for post-hoc audit.

## Tasks Executed

| Task | Name                                                              | Commit  | Files                                              |
|------|-------------------------------------------------------------------|---------|----------------------------------------------------|
| 1    | Write 17-RUBRIC.md with anchored scores and locked field schema    | 65c1a04 | 17-RUBRIC.md                                       |
| 2    | Write 17-CAPTURE-PROTOCOL.md and 17-ITERATION-LOOP.md              | 491bf0f | 17-CAPTURE-PROTOCOL.md, 17-ITERATION-LOOP.md       |

## Acceptance Criteria

All Task 1 + Task 2 acceptance criteria pass:

- **17-RUBRIC.md:** 5 score-anchor headings, 10 schema field tokens, 6 slop_flag enums, `≥ 4.0` threshold marker (4 occurrences), zero 1-2 phrasing (3 occurrences), Kaan tie-breaker reference, `src/vibemix/prompts/negative_dict.py` path reference, no python codeblock duplicating NEGATIVE_PHRASES.
- **17-CAPTURE-PROTOCOL.md:** 5 segment rows in matrix table, all 5 genres present (techno / house / drum & bass / disco / pop), both modes (Hype-man / Coach), all 3 skill levels (Beginner / Intermediate / Pro), recordings/<session>/ + events.jsonl + voice.wav references.
- **17-ITERATION-LOOP.md:** gate-fail trigger states `< 4.0` AND `1 or 2`, 3-cycle budget mentioned 4×, Hype-man-only escalation mentioned 2×, `matrix.py` reference, Phase 10 referenced 6×, `analyze.py` referenced 4×, `report.md` referenced 3×.

## Overall Verification

- All three documents exist at the expected paths.
- Zero source code modified (`git diff --name-only HEAD~2 HEAD` shows only `.planning/` paths).
- Zero tests added (no `tests/` entries in the diff).
- POC files untouched (no `cohost*.py`, `mascot.html`, `mocks/` in the diff).
- Locked schema in RUBRIC matches what Plans 17-02 / 17-03 will implement (field names, enum values, thresholds).

## Deviations from Plan

None — plan executed exactly as written.

The plan was a clean documentation-only spec. No bugs surfaced, no missing critical functionality to auto-add, no blocking issues, no architectural questions. The only execution wrinkle was a worktree-vs-main-repo path resolution issue (the initial Write tool call resolved against the main repo because the absolute path from the executor prompt pointed there); cleaned up by removing the stray file from the main repo and re-staging the work inside the worktree before committing. No content lost, no scope change.

## Decisions Made

- **Field schema is the rubric document, not the tooling.** Plans 17-02 / 17-03 grep this rubric's Markdown table for field-name contract enforcement. Drift is caught in CI rather than discovered at grading time.
- **Anti-slop dictionary referenced by path, never duplicated.** `src/vibemix/prompts/negative_dict.py` is the canonical source. If Phase 10 evolves the dictionary, the rubric stays accurate without edits. This is the most important drift-resistance lever in the spec.
- **Capture protocol pins skill distribution.** 1× Beginner / 2× Intermediate / 2× Pro is the canonical layout — not a suggestion. Without pinning, Kaan would likely capture 5× Intermediate and the gate would over-test the middle of the persona surface.
- **Iteration loop preserves 2 of 4 raters across cycles.** Francesco + dj2 do not see focused-cycle reels. Their blindness on the final 30-min re-grade is the gate's honesty guarantee. Burning all four raters on intermediate cycles would make the final pass-verdict suspect.
- **3-failed-cycle escalation is Hype-man-only scope-cut, by default.** The alternative paths (push launch date, drop a skill level, re-evaluate the rubric) are listed but require Kaan's explicit override. Default-to-scope-cut keeps the loop bounded.

## Known Stubs

None.

## Threat Flags

None new. The plan's `<threat_model>` flagged T-17-01-01 (Tampering on schema field names) which is mitigated by Plan 17-02/17-03's CI greps — that mitigation lands in those plans, not this one. T-17-01-02 (rater-identity disclosure) was an `accept` disposition and the rubric uses only the four canonical rater handles. T-17-01-03 (iteration-loop budget repudiation) is mitigated by 17-ITERATION-LOOP.md §4 (per-cycle report archival under `17-CYCLE-<N>-REPORT.md`).

## Self-Check: PASSED

- FOUND: `.planning/phases/17-reaction-reel-slop-grading-gate/17-RUBRIC.md`
- FOUND: `.planning/phases/17-reaction-reel-slop-grading-gate/17-CAPTURE-PROTOCOL.md`
- FOUND: `.planning/phases/17-reaction-reel-slop-grading-gate/17-ITERATION-LOOP.md`
- FOUND: `.planning/phases/17-reaction-reel-slop-grading-gate/17-01-SUMMARY.md`
- FOUND commit: `65c1a04` (Task 1 — 17-RUBRIC.md)
- FOUND commit: `491bf0f` (Task 2 — 17-CAPTURE-PROTOCOL.md + 17-ITERATION-LOOP.md)
