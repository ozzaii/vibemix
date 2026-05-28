# Phase 94: Course 1 — Anatomy (L1.01–L1.16) — Context

**Gathered:** 2026-05-28
**Status:** Ready for planning
**Mode:** Smart discuss (auto-accepted per `/gsd-autonomous fully`); decisions LOCKED in `.planning/research/SUMMARY.md` §3 + STATE.md verbatim opening dialog + ROADMAP P94.

<domain>
## Phase Boundary

P94 ships **Course 1 — Anatomy of a Deck**: 16 hand-authored lesson scripts walking a beginner through controller anatomy + counting bars + the marquee EQ-as-Tutor demo that uses P93's exemplar engine. Tone discipline lands here: byte-equality on iconic opening dialog + `check_no_tutor_slop.py` v2 blocklist + tutor system instruction lock from P92 binding.

**The 16 lessons (REQ-IDs `CURR-1.01..1.16`):**

| # | Lesson ID | Title | What user does |
|---|-----------|-------|----------------|
| 1 | L1.01 | Opening Dialog (verbatim) | reads/skips through iconic 4-line dialog |
| 2 | L1.02 | Meet Your Controller | rendered SVG appears + AI names it |
| 3 | L1.03 | Channel Strip | EQ + gain + fader tour |
| 4 | L1.04 | Crossfader | user moves crossfader to confirm |
| 5 | L1.05 | Pitch Fader | user moves pitch fader |
| 6 | L1.06 | Transport Buttons | play / cue / sync |
| 7 | L1.07 | Jog Wheel (nudge only) | user nudges jog wheel deck A |
| 8 | L1.08 | Headphone Cueing | user toggles headphone cue |
| 9 | L1.09 | Master/Booth/Headphone Volumes + red-zone hygiene | user moves master vol; warning at >-6 dBFS |
| 10 | L1.10 | Anatomy of a Song | intro / build / drop / breakdown / outro audio diagram |
| 11 | L1.11 | Counting Bars | 1-2-3-4 count-in over a known track |
| 12 | L1.12 | Spot Breakdown By Ear | listen for energy drop |
| 13 | L1.13 | Spot Breakdown By Eye (waveform) | identify breakdown visually |
| 14 | **L1.14** | **EQ-as-Tutor Demo (MARQUEE)** | uses ExemplarFinder.find(band) for each EQ band; user HEARS the band swell |
| 15 | L1.15 | Load Two Tracks | user loads decks A + B |
| 16 | L1.16 | Course 1 Recital | 5-prompt mixed gate (random subset of L1.03..1.13) |

**REQ-IDs delivered:** TONE-01, TONE-03, CURR-1.01 through CURR-1.16 (16 lessons).

**Out of scope:**
- Course 2 lessons (transitions) → P95
- Course 3 lessons (play mode + tutor lens proactive) → P96
- Onboarding mode picker on main window → P97
- Headphone wizard UI → P97

</domain>

<decisions>
## Implementation Decisions

### Lesson script format (LOCKED — extends P92 pattern)

- **Path:** `src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json` through `16_course_1_recital.json`
- **Shape per lesson:** matches P92 hello_world precedent (`tutor_speak[]` + `expected_action` + `hints[]` + `system_instruction_addendum` etc.)
- **TONE-02 hand-authored:** every `tutor_speak.text` field is verbatim JSON. NO live LLM generation of lesson script text. Test gate `tests/learn/test_scripts_are_fixtures.py` (landed P92) MUST stay green.
- **TONE-04 system instruction lock:** uses the 4-forbidden-moves lock from P92's `_FORBIDDEN_TUTOR_MOVES_LOCK`. NO change to lock; just verify Course 1 lessons honor it.

### Iconic opening dialog (LOCKED — STATE.md verbatim)

**The 4-line dialog (BYTE-EQUALITY locked):**
```
user: Hello vibemix, what are you?
vibemix: I'm the best DJ app in the world.
user: If you are the best, then who the fuck am I?
vibemix: Oh bestie, don't worry. You know why? Because I'm the beginner module of vibemix. Let's go.
```

- **Test gate:** `tests/learn/test_tutor_prompts_byte_equality.py` (NEW) — reads the L1.01 JSON fixture + asserts the 4 lines match VERBATIM. CI fails red on any drift.
- **The "Let's go." is the ONE permitted exclamation-equivalent in v9.0** (UI-SPEC noted this exception). All other tutor copy stays lowercase / period-terminated.

### `check_no_tutor_slop.py` v2 blocklist (LOCKED per SUMMARY §10 + P92 binding)

- **NEW file:** `scripts/launch/check_no_tutor_slop.py` — extends existing `scripts/launch/check_no_ai_slop.py`. CI-gated.
- **Blocklist ≥20 tutor-tic tokens** (per SUMMARY §10):
  - "Great question!" / "Awesome!" / "Today we'll be learning..." / "You crushed it!"
  - "Let's dive in!" / "Don't worry, you'll get the hang of it"
  - + 14 more (Khanmigo/Duolingo precedent: any compliment-tic + summarize-tic + preview-tic + upbeat-hook-tic)
- **Scope:** runs against ALL `src/vibemix/learn/transcripts/**.json` (every lesson fixture) AND against runtime AI interjections (intercept hook in `prompts.py`).
- **Pinned by:** `tests/learn/test_no_tutor_slop_blocklist.py`.

### Curriculum metadata (extend P92's `curriculum.py`)

- **Extend CURRICULUM dict:** add 16 entries `L1.01..1.16` with `course_id="course_1_anatomy"` + `lesson_id` + `system_instruction_addendum` (≤200 chars per lesson) + `expected_action`.
- **Extend COURSE_FRAMES:** add `"course_1_anatomy"` frame describing the course context for the tutor system instruction.

### EQ-as-Tutor Demo (L1.14 marquee — wires P93)

- **Backend wiring:** lesson script calls `ExemplarFinder.find("low" | "mid" | "high")` from P93. ExemplarPlayer (P93) plays the picked track on user's headphone device.
- **AI claim grounded via `[exemplar:<track_id>]`** citation (P93's 4-site mirror). Invariant #2 binding.
- **Honest-null fallback:** if library empty, packaged CC-BY bank kicks in (P93's `assets/band_exemplars/`).
- **User action:** turns EQ knob on physical controller; rendered SVG mirrors; user HEARS band swell live.

### Course 1 Recital (L1.16)

- **Gate:** 5-prompt mixed gate (random subset of CURR-1.03..1.13 controls). User must perform each correctly to unlock Course 2.
- **Replayable + honest grading:** show user which prompts they got right/wrong; no shame, no "you crushed it!" — just "5/5 — Course 2 unlocked." or "3/5 — replay to advance."
- **State persisted:** `learn-progress.json` flags `course_2_unlocked: true` on first 5/5 recital.

### Claude's Discretion

- Exact lesson script copy within the tone discipline — lowercase, period-terminated, no exclamations (except "Let's go." in L1.01), no tutor-tics from the blocklist.
- Exact `system_instruction_addendum` per-lesson (≤200 chars each).
- Exact recital randomization seed strategy (deterministic per-user vs random per replay).

</decisions>

<code_context>
## Existing Code Insights

### Reusable assets (shipped P91-P93)
- `src/vibemix/learn/curriculum.py` — extend CURRICULUM + COURSE_FRAMES
- `src/vibemix/learn/runtime.py` — LessonRuntime FSM handles state transitions per lesson
- `src/vibemix/learn/prompts.py` — `build_tutor_system_instruction` composes per-lesson
- `src/vibemix/learn/transcripts/hello_world/01_press_play.json` — P92 precedent for lesson script shape
- `src/vibemix/learn/exemplar.py::ExemplarFinder` — P93 EQ-as-Tutor demo backend
- `src/vibemix/learn/audio_cue.py::ExemplarPlayer` — P93 audio play side
- `scripts/launch/check_no_ai_slop.py` — extend with tutor-slop blocklist
- All `ipc.learn.*` envelopes already wired (P92)
- UI surfaces (HUD, tutor-dock, skip button, highlight paint) already shipped in P92/P91

### Concurrent-session discipline
- 16 NEW JSON fixtures + 1 new check script + 1 new test file + curriculum.py extension (shared)
- Commit by named paths only

</code_context>

<specifics>
## Specific Ideas

- The opening dialog L1.01 is THE iconic moment — Kaan's product brand. Byte-equality lock is non-negotiable.
- L1.14 EQ-as-Tutor is the MARQUEE demo — this is the moment that proves vibemix understands music vs just MIDI. Must work end-to-end on real hardware.
- Course 1 Recital design: random 5 prompts; the user can't guess; they MUST perform. No multiple-choice escape hatch.

</specifics>

<deferred>
## Deferred Ideas

- Course 2 + 3 lessons → P95 + P96
- Onboarding mode picker + verbatim opening dialog mounted on main window → P97
- Per-genre lesson branches → v9.x (not in v9.0)
- Scratching lessons → v9.x or never
- Mobile, Linux, web catalog → never per CLAUDE.md constraints

</deferred>
