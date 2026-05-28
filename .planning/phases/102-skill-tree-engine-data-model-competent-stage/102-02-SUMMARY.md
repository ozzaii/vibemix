---
phase: 102-skill-tree-engine-data-model-competent-stage
plan: 02
subsystem: learn-engine
tags: [skill-tree, competent-gate, anti-slop, pure-logic, invariant-pins, fill-math, tdd]

# Dependency graph
requires:
  - phase: 102-01-skill-tree-data-model
    provides: "LearnProgress schema v2 + `skills` live-portion block (live_proof_count/mastered/first_mastered_at) the engine reads read-only"
  - phase: 94-95-recital-unlock-flags
    provides: "course_2_unlocked / course_3_unlocked honest-score gate flags the Competent AND-gate reads"
  - phase: 96-curriculum
    provides: "CURRICULUM (37 lesson ids) the SKILL_MANIFEST maps onto + asserts against at import"
provides:
  - "SKILL_MANIFEST: 6 REQ-locked DJ skills → real CURRICULUM lesson ids + recital gate"
  - "SkillSpec (frozen) + SkillProgress dataclasses"
  - "SkillTree.compute(progress) — pure single-arg engine deriving quality-weighted fill + Competent stage"
  - "Fill-math constants (WEIGHT_FIRST_TRY 1.0 / WEIGHT_WITH_STRIKES 0.6 / WEIGHT_FLOOR 0.0 / COMPETENT_THRESHOLD 0.6)"
  - "HEADLINE anti-slop pin: 100% click-through without recital stays locked"
  - "3 invariant pins (#1 no MusicState write, #4 no new ws port, privacy no profile.json leak)"
affects: [103-live-mastered-grounding, 104-skill-tree-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Derived learn-portion / stored live-portion split — fill+competent recomputed every compute(), live-portion read read-only from progress.skills"
    - "Import-time manifest↔curriculum drift assertion (lazy import, mirrors progress.dots_for_course)"
    - "Monotonic-fill semantics (Pitfall 4b): once completed=True a lesson's weight is fixed by stored strikes_used; fewer-strikes replay only raises fill"
    - "Substantive invariant pins (actual import/write regex) over naive substring counts — comment-filtered, over-broad-grep-safe"

key-files:
  created:
    - src/vibemix/learn/skill_tree.py
    - tests/learn/test_skill_tree.py
    - tests/learn/test_skill_tree_invariants.py
  modified: []

key-decisions:
  - "Competent = (learn_fill >= COMPETENT_THRESHOLD) AND getattr(progress, gate) — the recital is AND-ed in so a 100% click-through can NEVER reach Competent regardless of threshold (COMP-02 product spine)"
  - "Weights chosen first-try 1.0 > with-strikes 0.6 > floor 0.0 (Claude's discretion per CONTEXT GA2); the load-bearing invariant is the strict ORDERING, pinned by test, not the literal numbers"
  - "Monotonicity via Pitfall-4(b): recompute deterministically from stored lesson rows; a completion never reverts and fewer strikes only raise fill"
  - "phrasing_performance gated on course_3_unlocked (Open-Q#1) — C3 play-mode has no recital/completion flag, so the honest C2-recital pass that EARNS play-mode entry is the gate"
  - "Invariant pins assert the SUBSTANTIVE requirement (real import/field-write/port-bind), not naive substring counts — the engine's docstrings legitimately name MusicState/profile.json to explain what it does NOT do (CLAUDE.md 'explain why')"

patterns-established:
  - "Pattern: SkillTree.compute is the sole DERIVER of skill state; learn-portion never serialized (zero dual-write drift with the 102-01 stored live-portion)"
  - "Pattern: stage precedence mastered > competent > locked (live-proof overlay outranks the derived learn-portion)"

requirements-completed: [SKILL-01, SKILL-02, SKILL-03, COMP-01, COMP-02]

# Metrics
duration: 4min
completed: 2026-05-29
---

# Phase 102 Plan 02: Skill-Tree Engine + Competent Stage Summary

**The pure-logic skill-tree engine `skill_tree.py`: a 6-skill `SKILL_MANIFEST` mapped onto real curriculum lesson ids, a quality-weighted Competent fill that orders first-try > with-strikes > click-through, and a `SkillTree.compute` that AND-gates Competent behind the recital honest-score — so a 100% lesson click-through can never cross into Competent (the "nothing is given; every notch is earned" anti-slop spine, executable), plus the 3 invariant pins.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-05-28T22:34:34Z
- **Completed:** 2026-05-29
- **Tasks:** 2 (Task 1 = TDD: RED → GREEN; Task 2 = invariant pins)
- **Files created:** 3 (0 modified — fully additive, surgical commits)

## Accomplishments
- **SKILL-01:** `SkillTree.compute(progress)` returns exactly the 6 REQ-locked skills, each resolving a `stage ∈ {locked, competent, mastered}` from a `LearnProgress`.
- **SKILL-02:** `compute` is pure — single-arg, deterministic (twice on the same input → equal results), zero input mutation, no I/O, no clock, no `MusicState`. Pinned by `test_compute_is_pure_no_side_effects` + the Invariant-#1 static gate.
- **SKILL-03:** readable `SKILL_MANIFEST` (6 `SkillSpec`s) + an import-time `assert lesson_id in CURRICULUM` drift gate for every referenced id; re-pinned by `test_manifest_lesson_ids_exist_in_curriculum`. All 24 referenced ids verified present in the 37-lesson CURRICULUM.
- **COMP-01:** quality-weighted fill ∈ [0,1]; all-first-try (1.0) > all-with-strikes (0.6) > all-click-through (0.0); partial completion is fractional; **monotonic on reload** (Pitfall 4b — a fewer-strikes replay only raises fill, a completion never reverts).
- **COMP-02 (HEADLINE):** `test_full_clickthrough_without_recital_not_competent` is a real assertion — fill = 1.0 + `course_2_unlocked = False` → `.competent is False` AND `.stage == "locked"`. The recital is AND-ed into Competent (`learn_fill >= COMPETENT_THRESHOLD and gate_passed`), so a click-through can never be promoted regardless of threshold.
- **3 invariant pins** all green: `#1` no MusicState import/write, `#4` no `websockets.serve`/`WS_PORT`/`8765`/`8766`, privacy = no profile-surface import + `PROFILE_SCHEMA` still exactly its 5 fields with `additionalProperties:false` and no `skills`/`live_proof_count`/`mastered` leak.
- **Mastered overlay** wired read-only: when the stored live-portion (`progress.skills[...]["mastered"]`) is True, `stage == "mastered"` (live-proof outranks competent/locked) — the forward seam Phase 103 writes into.

## Task Commits

1. **Task 1 (TDD RED): failing skill-tree engine suite** — `ad771709` (test)
2. **Task 1 (TDD GREEN): skill_tree.py engine** — `22861a65` (feat)
3. **Task 2: 3 invariant pins** — `b8af7f58` (test)

_No REFACTOR commit — the GREEN implementation was already clean (directive prose, no fenced code, conventions followed)._

## Files Created
- `src/vibemix/learn/skill_tree.py` (279 lines) — `WEIGHT_*` + `COMPETENT_THRESHOLD` constants with a fill-math rationale docstring; `@dataclass(frozen=True) SkillSpec(lesson_ids, gate)`; the 6-skill `SKILL_MANIFEST`; import-time `_assert_manifest_matches_curriculum()` (lazy CURRICULUM import); `@dataclass SkillProgress`; `_weight_for(row)` quality-weight helper; `class SkillTree` with the pure `compute(progress) -> dict[str, SkillProgress]`. I/O-free, clock-free, MusicState-free.
- `tests/learn/test_skill_tree.py` — 13 tests: 6-skills/stage, purity, manifest drift, 6-skill set, gate-attrs, fill ordering, partial-fractional, monotonic-on-reload, **headline click-through**, threshold-AND-recital matrix, phrasing_performance C3 gate, mastered overlay, live-portion defaults.
- `tests/learn/test_skill_tree_invariants.py` — 3 line-oriented `re` pins mirroring `test_runtime_invariants.py` (comment-filtered): `test_skill_tree_never_mutates_musicstate` (#1), `test_no_new_ws_port` (#4), `test_skills_never_in_profile_json` (privacy — import-absence + live `PROFILE_SCHEMA` contract assertions).

## Decisions Made
- **Recital AND-gate is the decisive lock (COMP-02).** Competent = `fill >= threshold AND course_N_unlocked`. The threshold is the secondary "you did the lessons" floor; the earned recital is the gate that makes 100% click-through impossible to promote.
- **Weights are Claude's discretion (CONTEXT GA2); the ORDERING is the contract.** `1.0 / 0.6 / 0.0` with `COMPETENT_THRESHOLD = 0.6` chosen so a single with-strikes skill (harmonic_mixing, 1 lesson) still clears the floor while a click-through (0.0) never does. The fill-math tests pin the strict ordering, not the literal numbers.
- **Monotonicity via stored-row recompute (Pitfall 4b).** Fill is recomputed deterministically from the persisted lesson rows; a completion never reverts to incomplete and a fewer-strikes replay only raises fill.
- **phrasing_performance → course_3_unlocked (Open-Q#1).** C3 play-mode has no recital and no completion flag, so the honest C2-recital pass that earns play-mode entry is the gate.

## Deviations from Plan

### Observations (no auto-fix rule triggered)

**1. [Acceptance-criteria literal vs. intent] Task 2 AC `grep -c "music_state\|MusicState" == 0` / `grep -c profile == 0` flag docstring prose**
- **Found during:** Task 2 verification.
- **Issue:** The Task 2 acceptance grep `grep -c "music_state\|MusicState" src/vibemix/learn/skill_tree.py returns 0` (and the analogous profile substring) returns 2/1 — because `skill_tree.py`'s module docstring legitimately uses the words "MusicState" and "profile.json" to explain what the engine does NOT do (a CLAUDE.md "explain why" convention; the privacy/purity invariants are the most important design property of the module). The naive substring count cannot distinguish prose from a real import/write. This is the identical over-broad-grep pattern documented in `102-01-SUMMARY.md` deviation #1.
- **Resolution:** Kept the explanatory docstrings. Wrote the invariant pins to assert the SUBSTANTIVE requirement instead — an actual `import`/`from` of `vibemix.state.music_state`, an actual `MusicState.<field> =` field write, an actual `websockets.serve(`/`WS_PORT`/port-literal, an actual `vibemix.profile` import / `PROFILE_SCHEMA` reference — with comment-line filtering (mirroring `test_runtime_invariants.py`'s `FORBIDDEN_WRITES` idiom, which the plan's `<read_first>` explicitly told me to mirror). The plan's own Task-2 `<action>` forbids "bare `== 0` gates on unfiltered files per CLAUDE grep-gate hygiene", so the substantive-check approach is the plan-sanctioned path; the literal AC line is the over-broad artifact.
- **Verification:** All 3 flagged lines (skill_tree.py:21, :217, :24) are docstring prose, zero are imports/writes. `test_skill_tree_never_mutates_musicstate` + `test_skills_never_in_profile_json` green; the engine has no `music_state`/`profile` import and no MusicState field write.

---

**Total deviations:** 0 code auto-fixes; 1 documented observation (over-broad acceptance grep, identical to 102-01 deviation #1).
**Impact on plan:** None on scope or correctness. The substantive intent (no MusicState, no port, no profile leak) is enforced more precisely than the literal AC grep would.

## Issues Encountered
- None. The TDD cycle ran clean: RED failed on the absent module (`ModuleNotFoundError`), GREEN passed 13/13 on first implementation, the 3 pins passed 3/3 on first write.
- Bare `python3` (3.14) cannot import the `learn` package (pulls `sqlite_vec` via `__init__`); all verification ran under `source .venv/bin/activate && PYTHONPATH=src python3` (3.12) as the contract requires.

## Known Stubs
None. The engine is complete pure logic; the live-portion (`live_proof_count`/`mastered`/`first_mastered_at`) is read with safe defaults and is the documented forward seam Phase 103 fills — not a stub.

## Next Phase Readiness
- **Phase 103 (live mastered + grounding) unblocked.** `SkillProgress` already surfaces `mastered`/`live_proof_count`/`first_mastered_at` and the stage precedence is `mastered > competent > locked`. Phase 103 adds `record_live_demo` to write `progress.skills`; `compute` already reads the overlay with zero second migration.
- **Phase 104 (skill-tree UI) unblocked.** `SkillTree().compute(progress)` returns the per-skill display dict; the UI recomputes display state on every progress reload (no dual-write drift).
- All 4 cardinal invariants held by additive design: #1 (no MusicState write), #4 (no new port), privacy (no profile.json leak) are now test-pinned for the learn-engine surface; the engine is a pure reader of `LearnProgress`.
- No blockers. No `profile.json` surface touched.

---
*Phase: 102-skill-tree-engine-data-model-competent-stage*
*Completed: 2026-05-29*

## Self-Check: PASSED

- FOUND: `src/vibemix/learn/skill_tree.py` (created)
- FOUND: `tests/learn/test_skill_tree.py` (created)
- FOUND: `tests/learn/test_skill_tree_invariants.py` (created)
- FOUND commit `ad771709` (test RED), `22861a65` (feat GREEN), `b8af7f58` (test pins)
- `tests/learn/test_skill_tree.py tests/learn/test_skill_tree_invariants.py`: 16 passed
- `tests/learn` full suite: 479 passed, 1 skipped (opt-in live-jog) — nothing red cross-tree
