# Phase 95: Course 2 — Transitions (L2.01–L2.14) — Context

**Gathered:** 2026-05-28
**Status:** Ready for planning
**Mode:** Smart discuss (auto-accepted per `/gsd-autonomous fully`)

<domain>
## Phase Boundary

P95 ships **Course 2 — Transitions**: 14 hand-authored lesson scripts covering beatmatching (ear + sync side-by-side), 5 canonical transitions in canonical pedagogical order, hot cues + memory cues, Camelot wheel harmonic mixing, phrase matching, train wreck diagnosis, and the Course 2 Recital that unlocks Course 3.

**The 14 lessons (CURR-2.01..2.14):**

| # | Lesson | Skill taught |
|---|--------|--------------|
| 1 | L2.01 | Beatmatching by ear (±0.5% BPM, sync-OFF) |
| 2 | L2.02 | Beatmatching with sync (side-by-side per modern consensus) |
| 3 | L2.03 | Long Blend (32-bar fade w/ crossfader; AI count-in -8 bars) |
| 4 | L2.04 | EQ Swap |
| 5 | L2.05 | Bassline/Kick Swap (kill outgoing low + raise incoming low on beat-1) |
| 6 | L2.06 | Filter Fade |
| 7 | L2.07 | Echo-Out (bail-out for beginners) |
| 8 | L2.08 | Drop Swap |
| 9 | L2.09 | Loop Transition |
| 10 | L2.10 | Hot Cues & Memory Cues (enter on cue 2 = breakdown) |
| 11 | L2.11 | Camelot Wheel (uses existing `harmonics.py` Camelot table) |
| 12 | L2.12 | Phrase Matching (align deck B phrase with deck A phrase) |
| 13 | L2.13 | Diagnosing a Train Wreck (identify off-phrase / off-key / off-BPM) |
| 14 | L2.14 | Course 2 Recital (5-track 10-min mix, ≥3 transition types, unlocks Course 3) |

**REQ-IDs:** CURR-2.01..2.14.

**Out of scope:**
- Course 3 lessons → P96
- Tutor lens proactive (Course 3) → P96
- Onboarding mode picker → P97

</domain>

<decisions>
## Implementation Decisions

### Lesson script format (REUSE P94 pattern)

- **Path:** `src/vibemix/learn/transcripts/course_2_transitions/01_beatmatching_ear.json` through `14_course_2_recital.json`
- **Shape:** same as P94 (`tutor_speak[]` + `expected_action` + `hints[]` + `system_instruction_addendum`)
- **TONE-02 hand-authored:** ALL `tutor_speak.text` lines verbatim JSON
- **TONE-03 slop discipline:** all lines pass the 35-token blocklist from P94. Same lowercase / period-terminated discipline. No "Let's go." exception in P95 (that was L1.01 only).

### Curriculum extension

- **Extend CURRICULUM dict** (already shipped P92/P94): add 14 entries (L2.01..2.14) with `course_id="course_2_transitions"`.
- **Add COURSE_FRAMES["course_2_transitions"]** — describes course context.

### Exemplar wiring (REUSE P93 ExemplarFinder)

- Several transitions need 2 tracks Camelot-matched + BPM ±6%. Lesson scripts cite `[exemplar:<track_id>]` via P93's mirror.
- `harmonics.py` Camelot table (existing) supplies the harmonic-neighbor logic.
- For L2.10 Hot Cues: if user has rekordbox-imported cues, use them; otherwise fallback "set your own cue in vibemix" UI (minimal — just a "press to mark cue" interaction; full UI optional v9.x).

### Course 2 Recital (L2.14 — REUSE P94 RecitalRuntime)

- Same RecitalRuntime from P94 (extend if needed). Sample 5 transitions from L2.03..2.09 pool. Each performed live; AI grades against transition protocol; ≥3 transition types required to pass.
- Outcome: `course_3_unlocked: true` persisted to learn-progress.json on pass.

### Reuse P94 infrastructure

- `LessonRuntime` observer pattern (P94-03) handles per-lesson lifecycle — no runtime changes needed.
- `check_no_tutor_slop.py` (P94-02) already gates `transcripts/**` recursively → P95 fixtures inherit the check automatically.
- `ExemplarLessonController` (P94-03) — extend if Course 2 lessons need different exemplar cycling patterns. Otherwise reuse as-is.

### Claude's Discretion

- Lesson script copy within tone discipline.
- Transition protocol grading specifics (what counts as "correct" for L2.14 grading).
- L2.10 minimal cue-marking UI vs hands-off "user imports rekordbox cues" path.

</decisions>

<code_context>
## Existing Code Insights

### Reusable assets (shipped P91-P94)
- `src/vibemix/learn/curriculum.py` — extend with 14 L2.x entries + course_2_transitions frame
- `src/vibemix/learn/exemplar_lesson.py::ExemplarLessonController` (P94) — reuse
- `src/vibemix/learn/recital.py::RecitalRuntime` (P94) — reuse; extend for course_3_unlocked persistence
- `src/vibemix/audio/harmonics.py` — existing Camelot table
- `scripts/launch/check_no_tutor_slop.py` (P94) — already CI-gated against `transcripts/**`

### Concurrent-session discipline
- 14 NEW JSON fixtures + 1 curriculum.py extension (shared) + 1 recital.py extension (shared)
- Named-path commits only

</code_context>

<deferred>
## Deferred Ideas

- Course 3 lessons + tutor lens proactive → P96
- Onboarding mode picker → P97
- §LEARN-CURR-KEY-NORMALIZATION (CURRICULUM key vs schema regex) → P95+ engineering follow-up; surfacing here for visibility
- Per-genre transition branches → v9.x

</deferred>
