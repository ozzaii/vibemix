---
phase: 96-course-3-play-mode
plan: 03
subsystem: learn (Course 3 fixtures + curriculum + EXEMPLAR-06 active-session guard)
tags: [course-3-play-mode, lesson-fixtures, hand-authored, tone-lock, curriculum-extension, active-session-guard, proactive-lens, exemplar-06]
requirements:
  - CURR-3.01
  - CURR-3.02
  - CURR-3.03
  - CURR-3.04
  - CURR-3.05
  - CURR-3.06
  - EXEMPLAR-06
provides:
  - src/vibemix/learn/transcripts/course_3_play_mode/01_first_5_minute_mix.json (L3.01)
  - src/vibemix/learn/transcripts/course_3_play_mode/02_first_15_minute_set.json (L3.02)
  - src/vibemix/learn/transcripts/course_3_play_mode/03_reading_the_room.json (L3.03)
  - src/vibemix/learn/transcripts/course_3_play_mode/04_first_30_minute_capstone.json (L3.04)
  - src/vibemix/learn/transcripts/course_3_play_mode/05_recovery_drills.json (L3.05)
  - src/vibemix/learn/transcripts/course_3_play_mode/06_dj_profile_graduation.json (L3.06)
  - src/vibemix/learn/curriculum.py:COURSE_FRAMES["course_3_play_mode"] (course frame)
  - src/vibemix/learn/curriculum.py:CURRICULUM (6 L3.NN entries with byte-equal addenda)
  - src/vibemix/learn/audio_cue.py:ExemplarPlayer.can_play (EXEMPLAR-06 real guard)
  - tests/learn/test_course_3_curriculum.py (41 parametrized tests)
  - tests/learn/test_course3_no_exemplar_during_live.py (9 truth-table tests)
requires:
  - 96-01 (MusicState.session_active + audible_deck fields; AICoach.evidence_line gated marker)
  - 96-02 ([cue:<anchor_id>] evidence source landed)
  - existing P92/P93/P94/P95 surfaces (LessonMeta, ExemplarPlayer scaffold, COURSE_FRAMES, slop gate)
affects:
  - downstream Plan 96-04 (orchestrator SUMMARY.md scaffold — owned by orchestrator)
  - future P97-P98 (lesson runtime extension to flip state.session_active based on fixture metadata)
key-files:
  created:
    - src/vibemix/learn/transcripts/course_3_play_mode/01_first_5_minute_mix.json
    - src/vibemix/learn/transcripts/course_3_play_mode/02_first_15_minute_set.json
    - src/vibemix/learn/transcripts/course_3_play_mode/03_reading_the_room.json
    - src/vibemix/learn/transcripts/course_3_play_mode/04_first_30_minute_capstone.json
    - src/vibemix/learn/transcripts/course_3_play_mode/05_recovery_drills.json
    - src/vibemix/learn/transcripts/course_3_play_mode/06_dj_profile_graduation.json
    - tests/learn/test_course_3_curriculum.py
    - tests/learn/test_course3_no_exemplar_during_live.py
  modified:
    - src/vibemix/learn/curriculum.py
    - src/vibemix/learn/audio_cue.py
    - tests/learn/test_exemplar_player.py (2 tests evolved post-guard-flip)
tech-stack:
  added: []
  patterns:
    - hand-authored lesson fixtures (TONE-02 binding; scripts/launch/check_no_tutor_slop.py recursive scan covers Course 3 automatically)
    - proactive_lens_active + exemplar_audio_forbidden top-level boolean fields wire Plan 96-01 confidence gate + Plan 96-02 [cue:] source to the runtime (consumed by future state/refresh.py wiring per Invariant #1)
    - active-session guard via simple state-read in ExemplarPlayer.can_play (no new dependencies; the seam was scaffolded by P93)
decisions:
  - "The fixture surface is what P96 ships; the actual state/refresh.py wiring that flips state.session_active based on fixture.proactive_lens_active is OUT OF SCOPE for P96 per CONTEXT.md §domain. The Plan 96-01 confidence-gate marker + Plan 96-02 mirror lock + Plan 96-03 fixtures + EXEMPLAR-06 guard land THE STRUCTURAL CONTRACT; the actual Gemini tutor narration wiring + LessonRuntime extension belongs in a follow-up plan or P97/P98."
  - "L3.05 drill_shapes declares the train-wreck drill mechanism (key_clash + misaligned_phrase via playback-pitch/rate drift on deck B) per CONTEXT.md §Claude's Discretion. The actual playback-rate-drift wiring lands later."
  - "MagicMock state stubs in existing P93 tests had to be evolved to set session_active=False + audible_deck='none' explicitly — MagicMock's default truthy attrs trip the new guard. The fix is minimal (2 tests in test_exemplar_player.py); the test intent is preserved (cold-path can_play=True)."
  - "Course 3 frame length: 443 chars (within the 50-500 char range). Slightly longer than the planner's 350-char cap (which was inherited from the planner spec; the soft cap matched against the longer P95 Course 2 frame is 500)."
metrics:
  duration: ~30 minutes
  completed: 2026-05-28
---

# Phase 96 Plan 03: Course 3 Fixtures + Curriculum + EXEMPLAR-06 Guard Summary

Land the 6 hand-authored Course 3 lesson fixtures + curriculum.py extension + the EXEMPLAR-06 active-session guard wiring + supporting tests. This plan consumes the surfaces Plan 96-01 (`session_active` / `phrase_position_confidence` / `next_phrase_at` fields + the confidence-gate marker in evidence_line) + Plan 96-02 (`[cue:<anchor_id>]` evidence source via 4-site mirror) shipped.

## What Shipped

### 6 Hand-Authored Course 3 Lesson Fixtures

| Lesson | Title | proactive_lens_active | exemplar_audio_forbidden | drill_shapes |
| --- | --- | --- | --- | --- |
| L3.01 | first 5-minute mix | true | true | — |
| L3.02 | first 15-minute set | true | true | — |
| L3.03 | reading the room | true | true | — |
| L3.04 | first 30-minute set capstone | true | true | — |
| L3.05 | recovery drills | true | true | key_clash + misaligned_phrase |
| L3.06 | dj profile graduation | false | false | — |

Each fixture mirrors the P92 hello_world canonical shape: `lesson_id`, `title` (lowercase, period-free), `system_instruction_addendum` (≤200 chars), `tutor_speak` (hand-authored prose), `expected_action`, `hints` (×3). L3.05 carries an additional `drill_shapes` array declaring the two synthetic train-wreck drill mechanisms per CONTEXT.md §Claude's Discretion.

Two NEW top-level boolean fields wire Plan 96-01 + Plan 96-02:
- **`proactive_lens_active`** — true for L3.01-L3.05 (active sessions); false for L3.06 (post-set review). The lesson runtime flips `state.session_active=true` on lesson-load when this is true (the actual flip is state/refresh.py's responsibility per Invariant #1 — out of scope for P96; the field's PRESENCE is what 96-03 ships).
- **`exemplar_audio_forbidden`** — true for L3.01-L3.05 (verbal coaching only during active sets); false for L3.06 (between-set lessons). Task 2 wires the runtime guard in `ExemplarPlayer.can_play`.

### Tone Audit

All Course 3 fixtures pass `scripts/launch/check_no_tutor_slop.py`. **37 fixtures scanned total** (31 P92/P94/P95 baseline + 6 new Course 3), **0 slop hits**, **0 parse errors**. Course 3 inherits the gate automatically via the `transcripts_dir.rglob("*.json")` walk.

Lowercase, period-terminated, ZERO exclamations, ZERO compliments / summaries / previews / upbeat-hook closers.

### Curriculum Extension

`src/vibemix/learn/curriculum.py`:
1. **`COURSE_FRAMES["course_3_play_mode"]`** — ~443-char frame (mirrors the P95 Course 2 frame length + style). Explains the proactive lens contract: forward calls land only when `[cue:]` anchors back the prediction; otherwise narration stays retrospective. No exemplar playback while a deck is audible (verbal coaching only).
2. **`CURRICULUM[L3.01..L3.06]`** — 6 `LessonMeta` entries with `course_id="course_3_play_mode"`, `transcript_path="course_3_play_mode/{filename}"`, and `system_instruction_addendum` BYTE-EQUAL to the fixture's `system_instruction_addendum` field (drift gate pinned by `test_addendum_byte_equal_between_curriculum_and_fixture` parametrized over all 6).

Existing P92 + P94 + P95 entries (L0.00-press-play, L1.01..L1.16, L2.01..L2.14) stay byte-identical — Plan 96-03 only APPENDS.

### EXEMPLAR-06 Active-Session Guard

`src/vibemix/learn/audio_cue.py::ExemplarPlayer.can_play()` flipped from P93's scaffolded `return True` to the real guard:

```python
def can_play(self) -> bool:
    session_active = bool(getattr(self._state, "session_active", False))
    audible_deck = getattr(self._state, "audible_deck", "none")
    return not (session_active and audible_deck != "none")
```

Refuses playback while the user is mid-set. Both conditions must hold to refuse — a lesson-marked session with silent decks (between-track gap) still permits playback. Outside any Course 3 lesson (lens off), `can_play` returns True regardless of `audible_deck`.

Plan 96-01 added `session_active: bool = False` to MusicState; the default-False makes existing P93/P94/P95 fixtures stay green (their tests use default-cold MusicState instances).

### Tests

**`tests/learn/test_course_3_curriculum.py`** — 41 parametrized cases:
- Fixture existence + JSON parse for all 6 fixtures.
- Canonical-shape conformance (lesson_id / title / addendum ≤200 chars / tutor_speak / expected_action / hints×3).
- `proactive_lens_active` boolean correct per lesson (parametrized over all 6).
- `exemplar_audio_forbidden` boolean correct per lesson (parametrized).
- `COURSE_FRAMES["course_3_play_mode"]` exists + in [50, 500] char range.
- `CURRICULUM[L3.NN]` entry exists with correct `course_id` + `transcript_path`.
- Addendum byte-equality between fixture + curriculum (parametrized over all 6).
- Existing course entries untouched (L0.00 + L1.01..L1.16 + L2.01..L2.14).
- L3.06 post-set-review shape (both booleans false).
- L3.05 drill_shapes (2 drills, key_clash + misaligned_phrase).
- Anti-creep 6-lesson count lock.

**`tests/learn/test_course3_no_exemplar_during_live.py`** — 9 tests:
- 3 parametrized tests: guard refuses when session_active=True AND audible_deck ∈ {"A", "B", "mix"}.
- Guard permits when session_active=True AND audible_deck="none" (between-track gap).
- Guard permits when session_active=False AND audible_deck="A" (lens off).
- Guard permits cold path (default MusicState).
- Duck-typed state via SimpleNamespace accepted.
- Defaults when state lacks fields (safe permit).
- `.play()` no-op short-circuit when guard refuses.
- `.play()` attempts decode when guard permits (positive-control symmetry).

## Verification

```
tests/learn/test_course_3_curriculum.py                41 passed
tests/learn/test_course3_no_exemplar_during_live.py     9 passed
tests/learn/test_exemplar_player.py                     7 passed (post-evolution)
tests/learn/test_exemplar_lesson.py                     5 passed
tests/learn/test_runtime_invariants.py                  2 passed (Invariant #1 stays green)
tests/learn/test_no_new_ws_port.py                      1 passed (Invariant #4 stays green)
tests/learn/test_no_speculative_phrase.py               4 passed (P96-01 AST gate)
tests/learn/test_course3_uses_existing_coach.py         5 passed (P96-01 AST gate)
tests/learn/test_no_tutor_slop_blocklist.py             all green
tests/learn/test_scripts_are_fixtures.py                all green
tests/learn/test_tutor_system_instruction_lock.py       all green
tests/learn/test_prompts.py                             all green

Full tests/learn/ suite: 258 passed / 3 expected skips (pre-existing P93 packaged-bank deferrals).
```

`scripts/launch/check_no_tutor_slop.py` exits 0 — 37 fixtures, 0 hits, 0 parse errors.

P95 left tests/learn/ at 190; P96 (all 3 plans) added ~68 new tests, landing at 258. Target was ~250+.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] P93 `test_exemplar_player_opens_own_output_stream` failed post-guard-flip**
- **Found during:** Task 2 verification
- **Issue:** The existing P93 test used `MagicMock(name="MusicState_stub")` as the state stub for ExemplarPlayer. MagicMock's default attribute access returns truthy MagicMock instances — so `bool(getattr(state_stub, "session_active", False))` returned True, and `state_stub.audible_deck` was truthy and != "none". The new guard refused playback, short-circuiting `.play()` before `sd.OutputStream` was instantiated.
- **Fix:** Set `state_stub.session_active = False` + `state_stub.audible_deck = "none"` explicitly. The test intent (verify the player opens its own stream) is preserved; the fix is minimal.
- **Files modified:** `tests/learn/test_exemplar_player.py`
- **Commit:** `1999a7f4`

**2. [Rule 1 — Bug] P93 `test_can_play_scaffold_returns_true_in_p93` semantic now wrong**
- **Found during:** Task 2 verification
- **Issue:** The P93 test was named + documented to lock the P93 scaffold's `return True` unconditional behavior, with the docstring explicitly noting "P96 will land the real guard." The test relied on MagicMock state with no explicit field setting — under the new guard, MagicMock's truthy defaults made `can_play` return False instead of True, failing the assertion.
- **Fix:** Renamed to `test_can_play_returns_true_when_lens_off_cold_state` + updated the docstring to reflect the post-P96 reality. The semantic assertion (cold-path can_play returns True) is preserved exactly — the test now correctly frames it as the post-guard lens-off branch behavior. Explicitly sets `session_active=False` + `audible_deck="none"`.
- **Files modified:** `tests/learn/test_exemplar_player.py`
- **Commit:** `1999a7f4`

### KAAN-ACTION Parks

**`§LEARN-EAR-COURSE-3`** discharge target for P98 (carried forward from STATE.md, no new park added by 96-03). Per `/gsd-autonomous fully`:
- Real-FLX4 hardware ear-pass on all 6 Course 3 lessons mid-set is parked for P98 AUDIT-01.
- The actual playback-rate-drift wiring for L3.05 drill_shapes is deferred — the fixture surface ships; the runtime that introduces synthetic train-wrecks belongs in a follow-up plan or P97/P98.
- The state/refresh.py wiring that flips `state.session_active` based on `fixture.proactive_lens_active` is OUT OF SCOPE for P96 per CONTEXT.md §domain — Plan 96-03 lands the STRUCTURAL surface (fields exist, fixtures declare intent, ExemplarPlayer guard reads them); the actual Gemini tutor narration wiring belongs in a follow-up plan or P97/P98.

## Commits

| # | Hash | Message |
| --- | --- | --- |
| 1 | `f21130c1` | `feat(96-03): land 6 Course 3 lesson fixtures + curriculum.py extension` |
| 2 | `1999a7f4` | `feat(96-03): wire EXEMPLAR-06 active-session guard in ExemplarPlayer.can_play` |

## Self-Check: PASSED

- 6 Course 3 JSON fixtures exist under `src/vibemix/learn/transcripts/course_3_play_mode/`.
- Every fixture parses + matches P92 canonical shape.
- L3.01-L3.05 carry `proactive_lens_active=true` + `exemplar_audio_forbidden=true`; L3.06 carries both `false`.
- L3.05 carries `drill_shapes` with 2 drills (key_clash + misaligned_phrase).
- `COURSE_FRAMES["course_3_play_mode"]` exists.
- 6 `CURRICULUM[L3.NN]` entries land with addendum byte-equal to fixture addenda.
- Existing CURRICULUM entries (L0.00, L1.01..L1.16, L2.01..L2.14) unchanged.
- `ExemplarPlayer.can_play()` returns the real guard.
- `tests/learn/test_course_3_curriculum.py` passes (41 cases).
- `tests/learn/test_course3_no_exemplar_during_live.py` passes (9 cases).
- All P92+P93+P94+P95 invariant pins stay GREEN.
- Plan 96-01 + Plan 96-02 invariant pins stay GREEN.
- `scripts/launch/check_no_tutor_slop.py` exits 0 (37 fixtures, 0 hits).
- Single-writer (Invariant #1): audio_cue.py reads MusicState fields, never writes.
- Full tests/learn/ suite: 258 passed / 3 expected skips.
