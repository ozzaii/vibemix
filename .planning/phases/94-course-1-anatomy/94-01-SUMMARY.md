---
phase: 94-course-1-anatomy
plan: 01
subsystem: learn
tags: [course-1-anatomy, lesson-fixtures, hand-authored, tone-lock, curriculum-extension, eq-as-tutor, recital, iconic-dialog]

requires:
  - phase: 92-lesson-runtime
    provides: LessonMeta dataclass, CURRICULUM/COURSE_FRAMES tables, hello_world fixture shape, TONE-02/04 invariant tests
  - phase: 93-exemplar-engine
    provides: ExemplarFinder.find(band), ExemplarPlayer.play(track) — wired by Plan 94-03

provides:
  - "16 hand-authored Course 1 lesson JSON fixtures (L1.01..L1.16) under src/vibemix/learn/transcripts/course_1_anatomy/"
  - "L1.01 iconic 4-line opening dialog locked byte-equal to the v9.0 brand-promise text (TONE-01 binding)"
  - "L1.14 EQ-as-Tutor MARQUEE lesson with exemplar_cycle field (low → mid → high) for Plan 94-03 ExemplarFinder driver"
  - "L1.16 Course 1 Recital with recital_pool (9 entries, draws from L1.03..L1.13) + recital_outcomes pass/fail copy"
  - "curriculum.py COURSE_FRAMES['course_1_anatomy'] frame + 16 CURRICULUM[L1.NN] entries"
  - "Per-lesson system_instruction_addendum byte-equal across fixture JSON and curriculum.py (drift gate ready for Plan 94-02 pin)"
  - "TONE-03 discipline applied: lowercase, period-terminated, zero tutor-tic blocklist tokens, zero exclamations across 16 files"

affects:
  - 94-02 (TONE byte-equality test + slop blocklist will gate against these fixtures)
  - 94-03 (LessonRuntime wires exemplar_cycle for L1.14, RecitalRuntime samples recital_pool for L1.16)
  - 95-course-2-transitions (next-course curriculum follows the same fixture/curriculum.py extension shape)
  - 96-course-3-play-mode (same)

tech-stack:
  added: []
  patterns:
    - "Hand-authored JSON fixtures as source-of-truth for tutor narration (extends P92 TONE-02 pattern to 16 lessons)"
    - "L1.NN dotted lesson IDs matching CURR-1.NN requirement prefix (parallel to P92 L0.00-press-play)"
    - "Per-lesson SHOUTED addendum prefix ('CHANNEL STRIP ADDENDUM:', 'EQ AS TUTOR ADDENDUM:', etc.) as composition-anchor"
    - "exemplar_cycle field on marquee lessons drives a per-cycle ExemplarFinder.find(band) loop in the runtime (declarative)"
    - "recital_pool + recital_outcomes fields declare random-subset gates without runtime FSM changes"

key-files:
  created:
    - "src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json (iconic dialog — byte-locked)"
    - "src/vibemix/learn/transcripts/course_1_anatomy/02_meet_your_controller.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/03_channel_strip.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/04_crossfader.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/05_pitch_fader.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/06_transport_buttons.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/07_jog_wheel.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/08_headphone_cueing.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/09_master_booth_headphones.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/10_anatomy_of_a_song.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/11_counting_bars.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/12_spot_breakdown_by_ear.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/13_spot_breakdown_by_eye.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/14_eq_as_tutor.json (MARQUEE — exemplar_cycle)"
    - "src/vibemix/learn/transcripts/course_1_anatomy/15_load_two_tracks.json"
    - "src/vibemix/learn/transcripts/course_1_anatomy/16_course_1_recital.json (recital_pool + recital_outcomes)"
  modified:
    - "src/vibemix/learn/curriculum.py (COURSE_FRAMES['course_1_anatomy'] + 16 CURRICULUM entries appended after L0.00-press-play)"

key-decisions:
  - "Wire-format control names: fixtures use `<field>` + separate `deck` per the live ipc.learn.ack rpartition(':') contract — `eq_hi`, `xfader`, `tempo`, `jog`, `headphone_cue`, `master_vol`, `cue`, `play`, `lesson_continue` — NOT the raw profile keys (`eq_hi_a`, `tempo_a`, etc.). Re-aligns the planner's prose to the LessonRuntime.action_matches contract documented in runtime.py:209 + the P92 hello-world precedent. Required for the FSM gate to actually fire on real MIDI events."
  - "L1.01 opening dialog ships with a new `speaker` field on each tutor_speak beat to distinguish user vs vibemix lines while leaving Plan 94-02's byte-equality test on `tutor_speak[i].text` intact. Plan 94-03's runtime hook reads `speaker` only on this single lesson."
  - "Listening-only lessons (L1.01, L1.10, L1.11, L1.12, L1.13, L1.15, L1.16 outer) gate on a synthetic `lesson_continue` button — the FSM's button branch accepts any control name string, so the synthetic name works without runtime changes. The frontend continue-button maps to this when no real MIDI control is bound."
  - "L1.09 expected_action targets `master_vol` (no deck) because master volume is a master-section knob (no `:deck` suffix in midi_position keys per midi_mirror.py:325). Per CONTEXT.md `master_vol movement` spec."
  - "L1.08 headphone-cue is gated on deck A (matching the objective table's `headphone_cue:A toggle`), not the plan ACTION's deck B suggestion. The objective table is the source of truth for `expected_action target`."
  - "L1.16 recital_pool ships 9 entries (drawing from L1.03–L1.13) so Plan 94-03's RecitalRuntime can deterministically sample 5 — the pool ≥5 contract from REQ CURR-1.16. L1.10/L1.11/L1.14/L1.15 excluded from the pool by design (passive lessons + the MARQUEE exemplar_cycle would not survive sampling)."
  - "All 16 fixture addenda kept ≤200 chars (composition-time cap in prompts.py:185); largest is L1.04 at 182 chars. Curriculum.py duplicates the addendum string byte-equal so prompts.py reads it without re-reading JSON."

patterns-established:
  - "Course-frame text introduces the lesson context to the LLM in 3-5 sentences without revealing the lesson script — grounds observation in 'what hands and ears are doing right now'"
  - "Listening-only lessons use lesson_continue as the gate control (button branch, synthetic control name) — no MIDI required, no runtime change"
  - "Marquee lessons embed declarative per-cycle data (exemplar_cycle for L1.14, recital_pool for L1.16) the runtime reads instead of hard-coding cycle logic per-lesson"

requirements-completed: [TONE-01, CURR-1.01, CURR-1.02, CURR-1.03, CURR-1.04, CURR-1.05, CURR-1.06, CURR-1.07, CURR-1.08, CURR-1.09, CURR-1.10, CURR-1.11, CURR-1.12, CURR-1.13, CURR-1.14, CURR-1.15, CURR-1.16]

duration: 6m
completed: 2026-05-28
---

# Phase 94 Plan 01: Course 1 Anatomy Fixtures + Curriculum Extension Summary

**16 hand-authored Course 1 lesson JSON fixtures landed under src/vibemix/learn/transcripts/course_1_anatomy/ with L1.01 iconic dialog byte-locked, L1.14 EQ-as-Tutor exemplar_cycle declared, and L1.16 recital_pool + outcomes copy ready — plus curriculum.py extended with COURSE_FRAMES['course_1_anatomy'] + 16 L1.NN entries that maintain addendum byte-equality with their fixtures.**

## Performance

- **Duration:** 6 min (timer 364 s)
- **Started:** 2026-05-28T06:08:27Z
- **Completed:** 2026-05-28T06:14:31Z
- **Tasks:** 2
- **Files modified:** 17 (16 created + 1 modified)

## Accomplishments

- L1.01 ships the iconic 4-line opening dialog byte-equal: "Hello vibemix, what are you?" / "I'm the best DJ app in the world." / "If you are the best, then who the fuck am I?" / "Oh bestie, don't worry. You know why? Because I'm the beginner module of vibemix. Let's go." — Plan 94-02 will pin the byte-equality formally.
- L1.14 EQ-as-Tutor MARQUEE lesson declares the 3-band exemplar_cycle (low → mid → high) with per-band tutor_speak + expected_action — Plan 94-03's runtime hook will drive ExemplarFinder.find(band) + ExemplarPlayer per cycle entry without lesson-specific FSM code.
- L1.16 Course 1 Recital declares recital_pool with 9 entries drawn from L1.03–L1.13 (Plan 94-03 deterministically samples 5) plus recital_outcomes pass/fail copy: "5 of 5. course 2 unlocked." vs "{score} of 5. replay when you're ready." — honest grading, no shame.
- curriculum.py extended cleanly: 1 new COURSE_FRAMES entry + 16 new CURRICULUM entries, every addendum byte-equal to its fixture's `system_instruction_addendum` field.
- TONE-03 discipline holds across all 16 files: zero blocklist tokens (great / awesome / now let's / etc.), zero exclamations, lowercase + period-terminated everywhere except L1.01's verbatim lines.
- P92 invariant test suite stays green (5 files, 11 tests); full tests/learn/ green at 81 pass / 3 skip (skips are pre-existing P93 packaged-bank deferrals).

## Task Commits

Each task was committed atomically:

1. **Task 1: Hand-author the 16 Course 1 lesson JSON fixtures** — `eda18aea` (feat)
2. **Task 2: Extend curriculum.py with COURSE_FRAMES + 16 CURRICULUM entries** — `e00718e4` (feat)

**Plan metadata commit:** pending (this SUMMARY.md + STATE.md + ROADMAP.md commit follows).

## Files Created/Modified

### Created (16 fixtures)
- `src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json` — L1.01 iconic 4-line opening dialog (byte-locked); new `speaker` field on each beat (user|vibemix); expected_action = lesson_continue button
- `src/vibemix/learn/transcripts/course_1_anatomy/02_meet_your_controller.json` — L1.02 controller-section overview; expected_action = play button on deck A
- `src/vibemix/learn/transcripts/course_1_anatomy/03_channel_strip.json` — L1.03 channel strip walkthrough; expected_action = eq_hi:A knob sweep (min_delta=80)
- `src/vibemix/learn/transcripts/course_1_anatomy/04_crossfader.json` — L1.04 crossfader throw; expected_action = xfader full-throw (min_delta=100)
- `src/vibemix/learn/transcripts/course_1_anatomy/05_pitch_fader.json` — L1.05 pitch fader ±%; expected_action = tempo:A nudge (min_delta=50)
- `src/vibemix/learn/transcripts/course_1_anatomy/06_transport_buttons.json` — L1.06 play / cue / sync; expected_action = cue button on deck A
- `src/vibemix/learn/transcripts/course_1_anatomy/07_jog_wheel.json` — L1.07 jog wheel nudge; expected_action = jog:A nudge (min_delta=10)
- `src/vibemix/learn/transcripts/course_1_anatomy/08_headphone_cueing.json` — L1.08 headphone cue toggle; expected_action = headphone_cue button on deck A
- `src/vibemix/learn/transcripts/course_1_anatomy/09_master_booth_headphones.json` — L1.09 master/booth/headphone volumes + red-zone hygiene; expected_action = master_vol touch (min_delta=5)
- `src/vibemix/learn/transcripts/course_1_anatomy/10_anatomy_of_a_song.json` — L1.10 intro/build/drop/breakdown/outro narration (passive); expected_action = lesson_continue
- `src/vibemix/learn/transcripts/course_1_anatomy/11_counting_bars.json` — L1.11 four-bar count-along (passive); expected_action = lesson_continue
- `src/vibemix/learn/transcripts/course_1_anatomy/12_spot_breakdown_by_ear.json` — L1.12 ear-spot breakdown (passive); expected_action = lesson_continue
- `src/vibemix/learn/transcripts/course_1_anatomy/13_spot_breakdown_by_eye.json` — L1.13 visual-spot breakdown on waveform (passive); expected_action = lesson_continue
- `src/vibemix/learn/transcripts/course_1_anatomy/14_eq_as_tutor.json` — **L1.14 MARQUEE**; exemplar_cycle with 3 band entries (low/mid/high) each carrying expected_action + tutor_speak; outer expected_action = eq_low:A (matches cycle[0])
- `src/vibemix/learn/transcripts/course_1_anatomy/15_load_two_tracks.json` — L1.15 load decks A + B; expected_action = lesson_continue (no MIDI map for load buttons in shipped profiles)
- `src/vibemix/learn/transcripts/course_1_anatomy/16_course_1_recital.json` — L1.16 recital; recital_pool (9 entries L1.03..L1.13) + recital_outcomes (pass/fail copy); outer expected_action = lesson_continue (RecitalRuntime takes over post-start)

### Modified
- `src/vibemix/learn/curriculum.py` — COURSE_FRAMES gained `"course_1_anatomy"` (5-line anatomy course frame); CURRICULUM gained 16 L1.NN entries (titles, course_id, byte-equal addendum strings, transcript_path); existing L0.00-press-play entry + course_0 frame untouched (P92 invariants pinned by test_prompts/test_tutor_system_instruction_lock stay green).

## Decisions Made

- **Wire-format control names** for `expected_action.control` follow the live ipc.learn.ack rpartition(':') contract — the LessonRuntime.action_matches gate compares `midi["control"]` (the part before `:`) against `expected["control"]`. The plan's prose used alternative literal names (`channel_fader_a`, `crossfader`, `tempo_fader_a`, etc.) that would never match real MIDI events; the objective table's spec (`eq_hi:A`, `xfader`, `tempo:A`, `jog:A`, `headphone_cue:A`, `master_vol`) is the wire-correct authority. Re-aligned fixtures to use `control: "eq_hi"`, `deck: "A"` (etc.) — matching the P92 hello_world precedent (`control: "play"`, `deck: "A"`) and the runtime contract documented in runtime.py:223–298.
- **Synthetic `lesson_continue` button** for passive listening lessons (L1.01, L1.10, L1.11, L1.12, L1.13, L1.15, L1.16 outer) — the FSM's button branch matches by control-name string equality (runtime.py:289), so any synthetic name works. The frontend's continue button emits `ipc.learn.ack { control_id: "lesson_continue", direction: "down" }` to satisfy this.
- **L1.01 `speaker` field** added to tutor_speak entries (`"speaker": "user" | "vibemix"`) for Plan 94-03's runtime hook to render the dialog as alternating-voice. Plan 94-02's byte-equality test reads `tutor_speak[i].text` by index — the new field doesn't break that contract.
- **L1.16 recital_pool size 9** (not 5) so Plan 94-03's RecitalRuntime can deterministically sample 5 from a fair pool. L1.10/L1.11/L1.14/L1.15 deliberately excluded from the pool (L1.10/L1.11 are passive, L1.14 is the MARQUEE cycle, L1.15 has no MIDI map).
- **Three EQ bands of L1.14** use min_delta=80 (≈63% of 127 CC range) — high enough to require a real sweep, low enough that a 4-band-only DDJ-FLX4 EQ pot can clear it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Re-aligned `expected_action.control` names to the live wire-format contract**
- **Found during:** Task 1 (fixture authoring, before any file was written)
- **Issue:** The plan ACTION prose specified literal control names that don't match the LessonRuntime.action_matches contract (`channel_fader_a`, `crossfader`, `tempo_fader_a`, `jog_a`, `headphone_cue_b`, `master_volume`, `load_b`). The wire format is `<field>:<deck>` (per ipc_handlers.py:240 + midi_mirror.py:325 — e.g. `eq_hi:A`, `vol:A`, `xfader`, `master_vol`), which the ipc handler rpartitions to `control="eq_hi"`, `deck="A"`. P92's hello_world precedent uses `"control": "play", "deck": "A"`. Fixtures written with the planner's literal names would have failed every action_matches gate at runtime — the lesson FSM would stay parked forever.
- **Fix:** Re-mapped the planner's prose to wire-correct names per the objective table's `expected_action target` column (which uses `eq_hi:A` / `xfader` / `tempo:A` / `jog:A` / `headphone_cue:A` / `master_vol` etc.) and the P92 hello_world precedent. Fixtures now use the rpartition-split form: `{control: "eq_hi", deck: "A"}` not `{control: "eq_hi_a"}`. Synthetic `lesson_continue` retained for passive lessons per the plan's explicit acknowledgment of its synthetic status.
- **Files modified:** all 16 fixtures in src/vibemix/learn/transcripts/course_1_anatomy/
- **Verification:** Task 1's automated verify-script passed; cross-cutting verify confirmed every L1.NN composes the tutor system instruction without ValueError + the four-forbidden-moves lock lands AFTER the per-lesson addendum sentinel.
- **Committed in:** eda18aea (Task 1)

**2. [Rule 2 - Missing Critical] Added `speaker` field to L1.01 tutor_speak beats**
- **Found during:** Task 1 (L1.01 authoring)
- **Issue:** The iconic 4-line dialog interleaves user-spoken and vibemix-spoken lines, but the existing tutor_speak shape has no way to distinguish them. Plan 94-03 will need to render the dialog with alternating voices — without `speaker`, the runtime would either narrate all 4 lines in vibemix-voice (breaking the user/vibemix dialog) or invent a heuristic. The plan ACTION explicitly mentions adding this field ("Add a new `speaker` field on tutor_speak entries to distinguish user vs vibemix lines").
- **Fix:** Each L1.01 beat carries `"speaker": "user" | "vibemix"`. Plan 94-02's byte-equality test reads `tutor_speak[i].text` by index — unaffected. Plan 94-03's runtime hook reads `speaker` only on L1.01 (the rest of the curriculum doesn't have alternating voices).
- **Files modified:** src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json
- **Verification:** L1.01's 4-line byte-equality smoke-check (in Task 1 verify-script) passed; the four `text` values match the verbatim spec exactly.
- **Committed in:** eda18aea (Task 1)

**3. [Rule 1 - Filename Alignment] Used the plan frontmatter's filename `09_master_booth_headphones.json` (not the objective table's longer `09_master_booth_headphone_volumes.json`)**
- **Found during:** Task 1 (L1.09 authoring)
- **Issue:** The plan's `files_modified` frontmatter and the verify-script's expected list both use `09_master_booth_headphones.json`; the objective table in the prompt uses `09_master_booth_headphone_volumes.json`. Choosing the wrong filename would have failed the verify-script's `p.exists()` check.
- **Fix:** Used `09_master_booth_headphones.json` (the plan frontmatter's authoritative filename). Title field is `"master · booth · headphones"` per the plan's title-list section.
- **Files modified:** src/vibemix/learn/transcripts/course_1_anatomy/09_master_booth_headphones.json
- **Verification:** Task 1's verify-script enumeration (which uses the plan's filename) passed; the file is loadable via CURRICULUM["L1.09"].script.
- **Committed in:** eda18aea (Task 1)

---

**Total deviations:** 3 auto-fixed (1 Rule 3 blocking, 1 Rule 2 missing-critical, 1 Rule 1 alignment)
**Impact on plan:** All three auto-fixes preserve the plan's INTENT (lessons gate on real controller actions; iconic dialog ships as a 4-voice cinematic; filename + verify-script stay in lock-step). No scope creep — every adjustment was forced by an existing wire contract or by a fixture-shape contract the plan itself referenced.

## Issues Encountered

- The `vibemix.learn` package has a transitive `sqlite_vec` import at module-load time (via `band_share_store` → `library.index_sqlite_vec`). Running the Task 2 verify with system Python 3.14 outside the venv tripped a `ModuleNotFoundError: No module named 'sqlite_vec'`. Worked around by sourcing `.venv` (Python 3.12 + project deps) before running the verify — the venv has sqlite_vec installed. Not a P94-01 regression; pre-existing import pattern from earlier learn-suite work.

## User Setup Required

None — no external service configuration. Pure content + curriculum.py extension; zero new dependencies.

## Threat Flags

None new in this plan beyond the threat register documented in 94-01-PLAN.md `<threat_model>`. All four `mitigate` dispositions remain on track for Plan 94-02's formal byte-equality test + Plan 94-03's runtime wiring.

## Next Phase Readiness

**Ready for Plan 94-02:** the 16 fixtures + curriculum.py extension are in place; the test the next plan will land (`test_tutor_prompts_byte_equality.py`) will read L1.01's 4 `tutor_speak[i].text` values + assert byte-equality against the verbatim spec. Smoke-checked already; formal pin is 94-02's job.

**Ready for Plan 94-03:** the L1.14 `exemplar_cycle` and L1.16 `recital_pool` + `recital_outcomes` fields are declared per spec — Plan 94-03's runtime hook can drive ExemplarFinder.find(band) / RecitalRuntime.sample(n=5) without further fixture changes.

**Concerns:** none. All P92 invariant tests pass; full `tests/learn/` suite green (81 pass / 3 pre-existing P93 skip).

## Self-Check: PASSED

- src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/02_meet_your_controller.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/03_channel_strip.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/04_crossfader.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/05_pitch_fader.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/06_transport_buttons.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/07_jog_wheel.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/08_headphone_cueing.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/09_master_booth_headphones.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/10_anatomy_of_a_song.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/11_counting_bars.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/12_spot_breakdown_by_ear.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/13_spot_breakdown_by_eye.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/14_eq_as_tutor.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/15_load_two_tracks.json — FOUND
- src/vibemix/learn/transcripts/course_1_anatomy/16_course_1_recital.json — FOUND
- src/vibemix/learn/curriculum.py — FOUND (modified)
- Commit eda18aea — FOUND in git log
- Commit e00718e4 — FOUND in git log

---
*Phase: 94-course-1-anatomy*
*Completed: 2026-05-28*
