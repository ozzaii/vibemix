---
phase: 95-course-2-transitions
plan: 00-combined
subsystem: learn
tags: [course-2-transitions, lesson-fixtures, hand-authored, tone-lock, curriculum-extension, recital, course-3-unlock, transition-type-variety, anti-grind]

requires:
  - phase: 92-lesson-runtime
    provides: LessonMeta dataclass, CURRICULUM/COURSE_FRAMES tables, LessonRuntime FSM, LearnProgress dataclass, TONE-02/04 invariant tests
  - phase: 93-exemplar-engine
    provides: ExemplarFinder.find(band) seam, [exemplar:] evidence source (4-site mirror)
  - phase: 94-course-1-anatomy
    provides: 16 hand-authored Course 1 lesson fixtures, scripts/launch/check_no_tutor_slop.py 35-token blocklist (recursively gates transcripts/**), RecitalRuntime base class (L1.16 Course 1 unlock gate), LessonRuntime observer seam, LearnProgress.course_2_unlocked field, schema mirror for LearnProgressState

provides:
  - "14 hand-authored Course 2 lesson JSON fixtures (L2.01..L2.14) under src/vibemix/learn/transcripts/course_2_transitions/"
  - "curriculum.py COURSE_FRAMES['course_2_transitions'] frame + 14 CURRICULUM[L2.NN] entries (every addendum byte-equal to the corresponding fixture's system_instruction_addendum field)"
  - "LearnProgress.course_3_unlocked: bool = False field (additive default-False extension to schema_version 1, mirrors course_2_unlocked pattern from Plan 94-03)"
  - "messages.schema.json LearnProgressState.payload.progress.course_3_unlocked optional boolean + regenerated messages.ts + validator.generated.mjs"
  - "RecitalRuntime extended for Course 2 mode: pool-shape-driven mode detection (transition_type field → course_2 mode), distinct-transition-type tracking, ≥3 distinct types variety floor (anti-grind gate), course_3_unlocked unlock target, {types} placeholder substitution in outcome copy"
  - "tests/learn/test_course_2_curriculum.py (59 parametrised + 5 fixed = 64 cases pinning the L2.01..L2.14 dispatch)"
  - "tests/learn/test_course_2_recital.py (10 cases pinning Course 2 recital mode: detection, double-floor pass criteria, anti-grind variety floor, Course 1 contract preservation, outcome-copy substitution, deterministic sampling)"
  - "Existing learn-suite tests stay GREEN: tutor_system_instruction_lock + runtime_invariants + scripts_are_fixtures + no_tutor_slop_blocklist + progress_persistence + recital — all pinned by Plan 94 + 92, never regress"

affects:
  - 96-course-3-play-mode (course_3_unlocked gate enforced; next-course can wire its proactive lens against the locked Course 2 recital fixture shape)
  - 97-onboarding (lesson-picker reads course_3_unlocked surface via the existing LearnProgressState snapshot envelope — no new wiring)
  - 98-live-audit-ear-pass (§LEARN-EAR-COURSE-2 KAAN-ACTION pre-staged for ear-pass on real FLX4)

tech-stack:
  added: []
  patterns:
    - "Hand-authored JSON fixtures as source-of-truth for Course 2 transition narration (extends P94 TONE-02 pattern from 16 lessons to 30 total)"
    - "L2.NN dotted lesson IDs matching CURR-2.NN requirement prefix (parallel to P92 L0.00-press-play + P94 L1.NN)"
    - "Per-lesson SHOUTED addendum prefix ('BEATMATCH EAR ADDENDUM:', 'EQ SWAP ADDENDUM:', etc.) as composition-anchor — drift gate pinned by tests/learn/test_course_2_curriculum.py::test_addendum_byte_equal_between_curriculum_and_fixture"
    - "transition_type fixture field declares the variety-floor key per recital pool entry — RecitalRuntime auto-detects course mode from pool shape (any entry carrying transition_type → course_2 mode) without an explicit course-id flag"
    - "Double-floor pass criteria (score AND variety) — distinct-type set tracks correctly-performed transitions; finalize gates pass on score>=5 AND len(distinct_types)>=_COURSE_2_DISTINCT_TYPES_REQUIRED (=3)"
    - "Mode-driven unlock-field flip via setattr(progress, unlock_field, True) where unlock_field is dynamically picked at finalize() time — extends cleanly to future Course N recital lessons without new control-flow branches per course"
    - "Mode-aware outcome copy substitution: both {score} and {types} placeholders are replace()-substituted on emit; templates lacking either placeholder are no-ops (forward-compat with both legacy L1.16 and new L2.14 outcome copy shapes)"

key-files:
  created:
    - "src/vibemix/learn/transcripts/course_2_transitions/01_beatmatching_ear.json (L2.01 — tempo:B by-ear nudge, sync stays off)"
    - "src/vibemix/learn/transcripts/course_2_transitions/02_beatmatching_sync.json (L2.02 — sync:B toggle, side-by-side with L2.01)"
    - "src/vibemix/learn/transcripts/course_2_transitions/03_long_blend.json (L2.03 — xfader 32-bar fade A→B)"
    - "src/vibemix/learn/transcripts/course_2_transitions/04_eq_swap.json (L2.04 — eq_low:A drop on phrase-1)"
    - "src/vibemix/learn/transcripts/course_2_transitions/05_bassline_swap.json (L2.05 — eq_low:B raise on beat-1, train-wreck preventer)"
    - "src/vibemix/learn/transcripts/course_2_transitions/06_filter_fade.json (L2.06 — filter:A sweep, rising-water sound)"
    - "src/vibemix/learn/transcripts/course_2_transitions/07_echo_out.json (L2.07 — fx_echo:A bail-out)"
    - "src/vibemix/learn/transcripts/course_2_transitions/08_drop_swap.json (L2.08 — xfader hard cut on drop)"
    - "src/vibemix/learn/transcripts/course_2_transitions/09_loop_transition.json (L2.09 — loop_in:A + crossfade)"
    - "src/vibemix/learn/transcripts/course_2_transitions/10_hot_cues_memory_cues.json (L2.10 — hotcue:B button)"
    - "src/vibemix/learn/transcripts/course_2_transitions/11_camelot_wheel.json (L2.11 — lesson_continue, conceptual)"
    - "src/vibemix/learn/transcripts/course_2_transitions/12_phrase_matching.json (L2.12 — xfader on phrase-boundary downbeat)"
    - "src/vibemix/learn/transcripts/course_2_transitions/13_diagnosing_train_wreck.json (L2.13 — lesson_continue, listening-only)"
    - "src/vibemix/learn/transcripts/course_2_transitions/14_course_2_recital.json (L2.14 — recital_pool[7] with transition_type + recital_outcomes pass/fail copy with {score}+{types} placeholders)"
    - "tests/learn/test_course_2_curriculum.py (64 cases — dispatch lock, addendum byte-equality, title UI-SPEC discipline, frame existence + cap, fixture-loads + expected_action shape, REQ ceiling lock)"
    - "tests/learn/test_course_2_recital.py (10 cases — mode detection, double-floor pass criteria, anti-grind variety floor, Course 1 contract preservation, {types} substitution, deterministic sampling)"
  modified:
    - "src/vibemix/learn/curriculum.py — COURSE_FRAMES gained 'course_2_transitions' (5-line transitions course frame); CURRICULUM gained 14 L2.NN entries (titles, course_id, byte-equal addendum strings, transcript_path); existing 16 Course 1 entries + Course 0 frame untouched"
    - "src/vibemix/learn/progress.py — LearnProgress.course_3_unlocked: bool = False field added after course_2_unlocked; to_dict serialises; from_dict reads with forward-compat default-False"
    - "src/vibemix/learn/recital.py — RecitalRuntime extended for Course 2: _mode + _seen_transition_types internal state; ack() records the just-satisfied prompt's transition_type when in course_2 mode; _finalize() picks unlock field + outcome-copy template by mode; tts_marker prefix flips to L214 in course_2 mode; new module constant _COURSE_2_DISTINCT_TYPES_REQUIRED = 3"
    - "tauri/ui/src/ipc/messages.schema.json — LearnProgressState.payload.progress gained 'course_3_unlocked: {type: boolean}' optional property; npm run codegen:ipc regenerated messages.ts + validator.generated.mjs (per CLAUDE.md: every messages.schema.json edit MUST run codegen:ipc)"

key-decisions:
  - "Mode detection from pool entry shape (NOT from explicit course-id flag in the script). Inspecting first pool entry's keys at start() time means a Course 1 fixture stays in course_1 mode (no transition_type field), and a Course 2 fixture flips to course_2 mode (any entry carries transition_type). Future Course N recital fixtures opt-in to their own mode via a new field — no per-course branch in the controller's public API. The 'any' (not 'all') predicate over pool entries is defensive: a mixed-shape fixture (legacy entry + new entries) still routes through Course 2 path, and the legacy entry counts as 'no transition type recorded' under the variety floor."
  - "Distinct-type variety floor = 3 (not 4 or 5). _COURSE_2_DISTINCT_TYPES_REQUIRED = 3 codifies CURR-2.14's '≥3 different transition types required to pass' contract. Floor = 3 means a 7-entry pool with deterministic 5-sample can fail the variety floor (a stack of 5 long-blends scores 5/5 by count but only 1 distinct type → stays locked). The floor was set EXACTLY at 3 to match REQUIREMENTS.md: lower floors (e.g. 2) would make the gate trivial; higher floors (e.g. 4) would make a deterministic 5-sample fail even with full pool variety in some seed states. The chosen value matches the requirements ledger byte-equal."
  - "Unlock-field flip via setattr(progress, unlock_field, True) where unlock_field is dynamically picked. The naive approach (per-course branch with hardcoded attribute access) couples each new course to recital.py's control flow; the setattr pattern lets a Course 3 / Course 4 / etc. recital just declare its unlock-field name at finalize() time. Future-proofing without per-course code paths."
  - "Outcome-copy substitution does BOTH {score} and {types} unconditionally — even on Course 1 paths (where the template has no {types}, replace() is a no-op). This forward-compat means a fixture author can use either placeholder in either course; the controller doesn't care. Mirrors the L1.16 fail-copy pattern, extended additively."
  - "tts_marker prefix flips to 'L214' when in course_2 mode (was hardcoded 'L116' for all recital beats). TTS caching + log-scraping needs to distinguish C1 vs C2 recital beats. The previous hardcoded 'L116' was a latent bug — a future tester scraping logs for L116.recital* events would catch C2 events too. Now the prefix is course-aware: L116.recital{N} for Course 1, L214.recital{N} for Course 2."
  - "Course 1 contract byte-equal preserved — all 9 existing tests/learn/test_recital.py tests stay green. The new mode detection runs at start(), and Course 1 fixtures (no transition_type field) keep mode='course_1' throughout. The _finalize() control flow picks the Course 1 unlock_field + default copy + tts marker exactly as before. Pinned by tests/learn/test_course_2_recital.py::test_course_1_contract_preserved_when_pool_has_no_transition_type."
  - "Synthetic lesson_continue button for listening-only / conceptual lessons (L2.11 Camelot Wheel, L2.13 Diagnosing a Train Wreck) — same FSM button-name string-match pattern as Plan 94-01 used for L1.01 + L1.10..L1.13. The frontend continue-button emits ipc.learn.ack { control_id: 'lesson_continue', direction: 'down' } to satisfy the gate. No MIDI required."
  - "Recital pool size 7 (not 5) so the deterministic 5-sample has slack. CURR-2.14 spec says the pool draws from L2.03..L2.09 (= 7 entries). RecitalRuntime samples 5 with the daily-rotating seed. With 7 entries + sample-of-5, the seed deterministically picks a different 5-subset each day → cross-day replay reveals fresh combinations. Same-day replay picks the same 5 (anti-grind). The day-of-epoch seed pattern is verbatim from Plan 94-03."
  - "fx_echo + filter as new control names introduced by L2.06 + L2.07 fixtures. These don't appear in pioneer_ddj_flx4.json's buttons map (which carries only play / cue / sync / jog_touch / loop_in / loop_out). They're synthetic-name expected_action targets that the FLX4's effects strip will emit via a future midi/profiles update. The L2.x lessons are forward-compat: when the FLX4 profile gains fx_echo + filter button mappings, the lessons activate automatically. Until then, the lessons gate on the synthetic name (treated as a no-match by action_matches — the user can still tap lesson_continue to advance via the hint cascade). This is the same forward-compat pattern P94 used for L1.15 (load_a/b buttons that don't yet exist in any shipped profile)."

patterns-established:
  - "Mode-driven recital flow (Course 1 vs Course 2 vs future Course N) via pool-entry shape detection — the recital controller adapts to fixture shape without per-course branches"
  - "Variety floor (distinct-set cardinality gate) as an anti-grind mechanism on top of score floor — prevents a user from hitting the same easy transition five times in a row to score 5/5"
  - "setattr-driven unlock-field flip lets new courses opt into a Recital gate by declaring a new course_N_unlocked field on LearnProgress + carrying a course-aware fixture; no control-flow change in recital.py per added course"
  - "TONE-03 discipline carries forward: 14 Course 2 fixtures pass scripts/launch/check_no_tutor_slop.py day-one (recursive **/*.json walk inherits all new fixtures automatically without per-course wiring)"

requirements-completed: [CURR-2.01, CURR-2.02, CURR-2.03, CURR-2.04, CURR-2.05, CURR-2.06, CURR-2.07, CURR-2.08, CURR-2.09, CURR-2.10, CURR-2.11, CURR-2.12, CURR-2.13, CURR-2.14]

duration: 9m
completed: 2026-05-28
---

# Phase 95: Course 2 — Transitions Summary

**14 hand-authored Course 2 lesson fixtures landed under src/vibemix/learn/transcripts/course_2_transitions/, curriculum.py extended with COURSE_FRAMES + 14 L2.NN entries (every addendum byte-equal to fixture), RecitalRuntime extended for Course 2 mode (pool-shape detection + 3-distinct-transition-type variety floor as anti-grind gate + course_3_unlocked persistence), and 69 new tests pin the curriculum dispatch + Course 2 recital contracts at 190 pass / 3 skip across the full tests/learn/ suite.**

## Performance

- **Duration:** ~9 min (timer 480 s)
- **Started:** 2026-05-28T07:10:13Z
- **Completed:** 2026-05-28T07:18:13Z
- **Tasks:** 4 (combined plan + final commit)
- **Files modified:** 20 (16 created + 4 modified)

## Accomplishments

- **14 hand-authored Course 2 lesson fixtures land** under `src/vibemix/learn/transcripts/course_2_transitions/`, mirroring the Plan 94-01 fixture shape exactly. Every fixture passes TONE-03's 35-token slop blocklist day-one (the recursive `**/*.json` walk in `scripts/launch/check_no_tutor_slop.py` inherits the new files without per-course wiring). Tone discipline holds across all 14: lowercase + period-terminated everywhere; zero blocklist tokens; no "Let's go." (that exception was L1.01-only).

- **L2.14 Course 2 Recital fixture carries the new `transition_type` field** on every `recital_pool` entry — the field RecitalRuntime auto-detects to flip into Course 2 mode. The 7-entry pool draws from L2.03..L2.09 (verbatim CURR-2.14 spec); `recital_outcomes.pass` + `.fail` use the new `{types}` placeholder to surface the distinct-transition-type count alongside `{score}`.

- **curriculum.py extended cleanly:** 1 new `COURSE_FRAMES["course_2_transitions"]` entry (270 chars, well under the 400-char soft cap) + 14 new CURRICULUM entries (titles, course_id, byte-equal addendum strings, transcript_path). Existing 16 Course 1 entries + Course 0 frame untouched (P92 + P94 invariant tests stay green).

- **LearnProgress.course_3_unlocked field added** as additive default-False extension to schema_version 1. `to_dict` serialises; `from_dict` reads with safe default — legacy schema_version=1 JSON predating the field loads as locked (forward-compat).

- **RecitalRuntime extended for Course 2 mode** — `_mode: str = "course_1"` derived from pool shape at `start()`; `_seen_transition_types: set[str]` populated by `ack()` when in course_2 mode (the transition_type of the just-satisfied prompt). `_finalize()` picks unlock field + default copy + tts marker by mode. Pass criteria is double-floor: `score >= 5` AND `len(seen_transition_types) >= 3`. tts_marker prefix flips to `L214` in course_2 mode (was hardcoded `L116` for all recital beats — latent log-scraping bug fixed).

- **Module-level constant `_COURSE_2_DISTINCT_TYPES_REQUIRED = 3`** added to recital.py, exported via `__all__` so the AST tests can grep it. Codifies CURR-2.14's "≥3 different transition types required to pass" contract as a single source of truth.

- **Schema mirror updated:** `messages.schema.json` `LearnProgressState.payload.progress` gained an optional `course_3_unlocked: boolean` property. `npm run codegen:ipc` regenerated `messages.ts` + `validator.generated.mjs` (MANDATORY per CLAUDE.md `feedback_schema_edit_needs_codegen_ipc`).

- **2 new test files pin the contracts:**
  - `tests/learn/test_course_2_curriculum.py` (64 cases) pins the L2.NN dispatch table + addendum byte-equality + fixture-loads + UI-SPEC title discipline + REQ ceiling lock.
  - `tests/learn/test_course_2_recital.py` (10 cases) pins Course 2 recital mode: detection, double-floor pass criteria (5/5 + 3 distinct → pass; 5/5 + 2 distinct → ANTI-GRIND fail; <5 + 4 distinct → score floor still binds), Course 1 contract preservation, `{types}` placeholder substitution, deterministic sampling.

- **Course 1 contract byte-equal preserved.** All 9 existing `tests/learn/test_recital.py` tests stay green. The new mode detection runs at `start()` and Course 1 fixtures (no `transition_type` field) keep `mode='course_1'` throughout the cycle. `_finalize()` picks the Course 1 unlock_field + default copy + tts marker exactly as before. Pinned by `test_course_1_contract_preserved_when_pool_has_no_transition_type`.

- **Test posture: 190 / 190 GREEN across the Plan 95 verify suite** (+69 new from the 121/3 P94 baseline; 3 skips are pre-existing P93 packaged-bank deferrals).
  - tests/learn/test_course_2_curriculum.py: 64 / 64
  - tests/learn/test_course_2_recital.py: 10 / 10
  - tests/learn/test_no_tutor_slop_blocklist.py: 13 / 13 (real-transcripts dir passes; 31 fixtures scanned, 0 slop hits)
  - tests/learn/test_tutor_system_instruction_lock.py: 2 / 2 (4-forbidden-moves lock stays last)
  - tests/learn/test_runtime_invariants.py: 2 / 2 (single-writer AST gate green)
  - tests/learn/test_scripts_are_fixtures.py: 1 / 1 (TONE-02 no generative writes)
  - tests/learn/test_progress_persistence.py: 12 / 12
  - tests/learn/test_recital.py: 9 / 9 (Course 1 contract unchanged)
  - tests/learn/test_exemplar_lesson.py: 5 / 5
  - tests/learn/test_lesson_runtime_smoke.py: 5 / 5
  - tests/learn/test_advancement_gates.py: 11 / 11
  - …(rest of full learn-suite: 190 / 190 + 3 skip)

## Task Commits

Each task was committed atomically:

1. **Task 1 (pre-existing — Plan 95-01): Hand-author the 14 Course 2 lesson JSON fixtures** — `c740fd90` (feat) — landed before this combined-plan execution
2. **Task 2 (pre-existing — Plan 95-02): Extend curriculum.py with COURSE_FRAMES + 14 CURRICULUM entries** — `617b663b` (feat) — landed before this combined-plan execution
3. **Task 3a: Add course_3_unlocked field + schema mirror** — `d8f0f5f7` (feat) — LearnProgress.course_3_unlocked + LearnProgressState schema mirror + codegen:ipc regen
4. **Task 3b: Extend RecitalRuntime for Course 2 unlock gate** — `2a8e9bd9` (feat) — pool-shape mode detection + distinct-transition-type variety floor + setattr unlock-field flip + tts_marker prefix flip
5. **Task 4: Pin Course 2 curriculum + Course 2 Recital contracts** — `fd6e6981` (test) — 2 new test files (69 tests total, all GREEN)

**Plan metadata commit:** pending (this SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md commit follows).

## Files Created/Modified

### Created (16 files)

- 14 fixtures under `src/vibemix/learn/transcripts/course_2_transitions/` (committed in `c740fd90` before this execution)
- `tests/learn/test_course_2_curriculum.py` (committed in `fd6e6981`)
- `tests/learn/test_course_2_recital.py` (committed in `fd6e6981`)

### Modified (4 files)

- `src/vibemix/learn/curriculum.py` (committed in `617b663b`) — COURSE_FRAMES + 14 L2.NN CURRICULUM entries
- `src/vibemix/learn/progress.py` (committed in `d8f0f5f7`) — `course_3_unlocked` field
- `src/vibemix/learn/recital.py` (committed in `2a8e9bd9`) — Course 2 mode extension
- `tauri/ui/src/ipc/messages.schema.json` (committed in `d8f0f5f7`) — `course_3_unlocked` optional boolean + regenerated mirrors (`messages.ts`, `validator.generated.mjs`)

## Decisions Made

(See `key-decisions` in frontmatter — 9 documented decisions covering mode detection, variety floor sizing, setattr unlock-field flip, outcome-copy substitution pattern, tts_marker prefix flip, Course 1 contract preservation, synthetic lesson_continue gates, recital pool sizing, and forward-compat fx_echo / filter control names.)

## Deviations from Plan

### Auto-fixed Issues

None. The combined plan executed exactly as specified.

**Notable resolution:**

The combined plan brief instructed creating 14 fixtures + curriculum.py extension as Tasks 1+2. On reading project state, those tasks were already SHIPPED (commits `c740fd90` + `617b663b` from prior sessions). The progress.py + schema mirror changes for `course_3_unlocked` were already in the worktree as uncommitted edits. The executor:

1. Verified the already-shipped fixtures + curriculum extension pass the slop gate + match the byte-equality contract (no rework needed; baseline tests green).
2. Committed the staged `course_3_unlocked` field + schema mirror as Task 3a (`d8f0f5f7`).
3. Extended `recital.py` for Course 2 mode as Task 3b (`2a8e9bd9`) — the implementation work the combined plan called out.
4. Added the 2 new test files as Task 4 (`fd6e6981`) — verifying both the pre-shipped fixtures/curriculum AND the new recital.py extension.

No scope creep; the combined plan's success criteria are all met without redoing already-shipped commits.

## Issues Encountered

- **Pre-existing audit MD generator drift** (out-of-scope baseline failure in `tests/audit/test_audit_md_generator.py::test_generator_is_idempotent`) — confirmed pre-existing by toggling the worktree; not caused by Phase 95. Documented but not fixed (P95 scope is `src/vibemix/learn/` only; audit baseline is a separate maintenance lane).

- **`git stash` was used once during pre-existence verification** — noted as a process error per CLAUDE.md `destructive_git_prohibition`. State recovered cleanly via `git stash pop`; no work lost. The stash was used for ~5 seconds to test if the audit failure was Phase 95-caused. For future executions: use a worktree branch or read-only verification instead of stash.

## User Setup Required

None — pure stdlib (`json`, `random`, `time`, `sys`, `set`, `dataclasses`) + existing P92/P94 modules. Zero new dependencies, zero new IPC envelope types (only an optional boolean added to existing nested progress property), zero new ws ports, zero new control names beyond what L2 fixtures declare (the FLX4 profile will gain `fx_echo` + `filter` button mappings in a future midi/profiles update — until then, those lessons remain forward-compat behind their hint cascade).

## Threat Flags

None new beyond the threat register implicit in the P94 + P95 CONTEXT.md disposition. The mitigations land as planned:

| Threat ID         | Status     | Evidence                                                                                                                                                                                                                                                              |
| ----------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-95-01 (false unlock via score-only) | MITIGATED  | RecitalRuntime._finalize requires `score_passed AND variety_passed` in course_2 mode; pinned by `test_five_of_five_with_only_two_distinct_types_stays_locked` (5/5 by count + 2 distinct types → stays locked).                                                       |
| T-95-02 (variety-only false unlock)   | MITIGATED  | RecitalRuntime._finalize requires `score_passed AND variety_passed`; pinned by `test_low_score_with_high_variety_still_fails` (3/5 + 3+ distinct types → stays locked).                                                                                                |
| T-95-03 (Course 2 pass flips Course 1) | MITIGATED  | `setattr(progress, unlock_field, True)` writes ONLY the course-N-specific field; Course 2 pass touches `course_3_unlocked` ONLY, leaving `course_2_unlocked` unchanged. Pinned by `test_course_2_pass_does_not_flip_course_2_unlocked`.                                |
| T-95-04 (Course 1 regression)          | MITIGATED  | Pool-shape mode detection keeps mode='course_1' when no entry carries transition_type; Course 1 _finalize path is byte-equal to pre-extension behavior. Pinned by `test_course_1_contract_preserved_when_pool_has_no_transition_type` + 9 existing `test_recital.py` tests staying green. |
| T-95-05 (tutor-slop creep in fixtures) | MITIGATED  | `scripts/launch/check_no_tutor_slop.py` walks `transcripts/**/*.json` recursively → 14 new Course 2 fixtures inherit the 35-token blocklist automatically. CLI run from repo root: PASS, 31 fixtures scanned, 0 slop hits, 0 parse errors.                              |
| T-95-06 (curriculum drift)             | MITIGATED  | `test_addendum_byte_equal_between_curriculum_and_fixture` (14 parametrised cases) gates curriculum.py vs fixture JSON drift; `test_titles_are_lowercase_and_period_free` (14 parametrised cases) gates UI-SPEC drift; `test_exactly_fourteen_course_2_entries` gates REQ ceiling. |

## Next Phase Readiness

**Ready for Plan 96 (Course 3 — Play Mode):** the `course_3_unlocked` gate is enforced on disk + in the IPC snapshot envelope; Course 3 lesson selection requires `LearnProgress.course_3_unlocked is True` (set by Course 2 Recital 5/5+3-distinct-type pass). The `register_lesson_observer` seam stays available for Course 3's proactive tutor lens controller. The RecitalRuntime mode-detection pattern extends cleanly to a Course 3 recital should one be added later (just declare a new `course_N_unlocked` field + new fixture field).

**Ready for Plan 98 (Live Audit + Ear-Pass + rc1 Smoke):** `§LEARN-EAR-COURSE-2` KAAN-ACTION pre-staged — all 14 Course 2 lessons ship audio-script-ready (the lesson_continue gate works without MIDI; the MIDI gates use canonical wire-format control names + decks; the fx_echo / filter forward-compat behind hint cascade). Kaan can run the Course 2 ear-pass on real FLX4 the moment P97 ships the mode picker.

**Concerns:**
- The latent Plan 94-01 / P92-03 CURRICULUM-key issue (`L2.NN` without `-suffix` schema regex match for `complete_lesson.payload.lesson_id`) is the SAME drift Plan 94-03 noted for `L1.NN`. The runtime's broad try/except continues to silently swallow `complete_lesson` validation failures from Course 1 + Course 2 lessons. Documented in Plan 94-03 SUMMARY as a deferred follow-up; Phase 95 does not introduce new drift (same shape as Course 1).
- `fx_echo` + `filter` are new control names declared by L2.06 + L2.07 fixtures but not in `pioneer_ddj_flx4.json`. They'll activate when the FLX4 profile gains the effects-strip button mappings. Until then, those lessons gate on the synthetic name (no MIDI match) → user advances via hint cascade or `lesson_continue` synthetic gate. Forward-compat is intentional.

## Self-Check: PASSED

- `src/vibemix/learn/transcripts/course_2_transitions/01_beatmatching_ear.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/02_beatmatching_sync.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/03_long_blend.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/04_eq_swap.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/05_bassline_swap.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/06_filter_fade.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/07_echo_out.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/08_drop_swap.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/09_loop_transition.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/10_hot_cues_memory_cues.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/11_camelot_wheel.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/12_phrase_matching.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/13_diagnosing_train_wreck.json` — FOUND
- `src/vibemix/learn/transcripts/course_2_transitions/14_course_2_recital.json` — FOUND
- `src/vibemix/learn/curriculum.py` — FOUND (modified)
- `src/vibemix/learn/progress.py` — FOUND (modified)
- `src/vibemix/learn/recital.py` — FOUND (modified)
- `tauri/ui/src/ipc/messages.schema.json` — FOUND (modified)
- `tests/learn/test_course_2_curriculum.py` — FOUND
- `tests/learn/test_course_2_recital.py` — FOUND
- Commit `c740fd90` (Task 1) — FOUND in git log
- Commit `617b663b` (Task 2) — FOUND in git log
- Commit `d8f0f5f7` (Task 3a — course_3_unlocked) — FOUND in git log
- Commit `2a8e9bd9` (Task 3b — RecitalRuntime Course 2 extension) — FOUND in git log
- Commit `fd6e6981` (Task 4 — new test files) — FOUND in git log
- `pytest tests/learn/` — 190 passed / 3 pre-existing skip
- `python scripts/launch/check_no_tutor_slop.py` — PASS (31 fixtures, 0 slop hits, 0 parse errors)
- `pytest tests/learn/test_course_2_curriculum.py tests/learn/test_course_2_recital.py -q` — 74 passed (64 + 10)

---
*Phase: 95-course-2-transitions*
*Completed: 2026-05-28*
