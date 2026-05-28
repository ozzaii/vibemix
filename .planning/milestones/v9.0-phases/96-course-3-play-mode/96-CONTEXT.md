# Phase 96: Course 3 — Play Mode (L3.01–L3.06) + tutor lens proactive — Context

**Gathered:** 2026-05-28
**Status:** Ready for planning
**Mode:** Smart discuss (auto-accepted per `/gsd-autonomous fully`)

<domain>
## Phase Boundary

P96 ships **Course 3 — Play Mode** (6 lessons) AND the **proactive tutor lens** that lets vibemix coach the user mid-set with grounded count-ins (e.g. "breakdown in 16 beats — get ready to bring in track 2"). The proactive narration is GROUNDED on `[cue:<anchor_id>]` evidence — the NEW conditional 5th citation source via 4-site mirror (same pattern as `[exemplar:]` from P93). Cardinal invariant #3 BINDING.

**4 cardinal-invariant pins THIS PHASE:**
- Invariant #1: tutor narration writes go through existing `state/coach.py::AICoach.build_prompt` — NO new state writers in `learn/`. AST gate stays green.
- Invariant #2: `[cue:<anchor_id>]` citation source landed via atomic 4-site mirror.
- **Invariant #3 BINDING (THIS PHASE'S KEY PIN):** trust-the-audio rule. Proactive count-ins ONLY when `bpm_confidence ≥ 0.8` AND `phrase_position_confidence ≥ 0.7` AND `MusicState.next_phrase_at is not None`. Otherwise downgrade to retrospective ("that was a breakdown — see how the bass dropped out"). Pinned by `test_no_speculative_phrase.py` (AST gate; lands BEFORE any Gemini wiring).
- Invariant #4: no new ws ports (debrief surface already on 8766 from v2.1).

**The 6 lessons (CURR-3.01..3.06) + CURR-3.07 invariant pin:**

| # | Lesson ID | Title | What user does |
|---|-----------|-------|----------------|
| 1 | L3.01 | First 5-Minute Mix | freely choose tracks; AI suggests 1 grounded move per minute |
| 2 | L3.02 | First 15-Minute Set | uses v8.2 Build-a-Set engine; AI live-coaches each transition |
| 3 | L3.03 | Reading The Room | AI walks user through reading energy curve mid-set + adjusting next-track |
| 4 | L3.04 | First 30-Minute Set Capstone | proactive co-pilot full 30-min; session recorded; debrief auto-opens |
| 5 | L3.05 | Recovery Drills | AI synthetically introduces train-wrecks; user bails out (echo-out / filter / cut) within 4 bars |
| 6 | L3.06 | DJ Profile Graduation | user reviews v8.1 long-term profile + lesson completion summary in v2.1 debrief |

**CURR-3.07** = the test infrastructure pin (test_no_speculative_phrase + test_course3_uses_existing_coach + runtime evidence_line gate).

**REQ-IDs:** EXEMPLAR-06, CURR-3.01..3.07.

**Out of scope:**
- Onboarding mode picker → P97
- rc1 regression smoke + milestone audit → P98

</domain>

<decisions>
## Implementation Decisions

### Order of operations (LOCKED per SUMMARY §11)

1. **FIRST**: `tests/learn/test_no_speculative_phrase.py` AST gate lands — `learn/` package MUST have ZERO imports of `numpy.fft` / `scipy.signal` / phrase-guessing primitives. Static grep test.
2. **THEN**: `tests/learn/test_course3_uses_existing_coach.py` lands — every tutor-narration prompt builder MUST call `state/coach.py::AICoach.build_prompt(...)`. AST grep test.
3. **THEN**: runtime gate at `src/vibemix/state/coach.py::evidence_line` — if `bpm_confidence < 0.8` OR `phrase_position_confidence < 0.7` OR `MusicState.next_phrase_at is None` → disable count-in language → downgrade to retrospective narration. This is the BPM/phrase-confidence guard.
4. **THEN**: `[cue:<anchor_id>]` evidence source via atomic 4-site mirror (same pattern as `[exemplar:]` in P93):
   - `state/evidence_registry.py:111` — add `"cue"` to `EVIDENCE_SOURCES`
   - `state/evidence_registry.py:137` — add `|cue` to `_SOURCE_ALT` regex
   - `prompts/matrix.py` — add `[cue:<anchor_id>]` form to `CITATION_GRAMMAR_BLOCK`
   - `agent/dj_cohost.py::_build_citation_strip` — add `"cue"` to strip set
5. **ONLY THEN**: wire tutor narration to Gemini via `model_router.resolve("learn_tutor")` (the route landed P92-01).

After step 5, EVIDENCE_SOURCES count flips 10 → 11.

### Reuse existing infrastructure (LOCKED per ROADMAP)

- **`state/coach.py::AICoach`** — existing live coach from v4+. Course 3 tutor narration BUILDS PROMPTS via this; no new prompt builder in `learn/`.
- **`agent/dj_cohost.py`** — existing live-co-host. Same Gemini Flash path (`model_router.resolve("live_coach")` for live OR `resolve("learn_tutor")` for lesson — researcher decides; same model in practice).
- **CueAnchor + phrase detection** — UNCHANGED. Reads from existing `state/refresh.py` MusicState (the single writer).
- **v2.1 debrief surface (port 8766)** — already-shipped second window opens on L3.04 capstone end.
- **v8.2 Build-a-Set** — L3.02 uses existing CLI flow to pre-sequence the 15-min set.
- **v8.1 long-term DJ profile** — L3.06 surfaces this in the debrief panel.

### Active-session guard (EXEMPLAR-06 binding)

- `ExemplarPlayer` (P93 shipped) gets a check: when `MusicState.audible_deck != none` AND `state.session_active` → REFUSE to play exemplar audio.
- In Course 3 lessons (L3.01-L3.04), exemplar playback is FORBIDDEN — verbal coaching only.
- Pinned by `tests/learn/test_course3_no_exemplar_during_live.py`.
- P93 already scaffolded the `state` kwarg on ExemplarPlayer constructor — P96 wires the real check.

### Lesson script format (REUSE P94 pattern)

- **Path:** `src/vibemix/learn/transcripts/course_3_play_mode/01_first_5_minute_mix.json` through `06_dj_profile_graduation.json`
- Same JSON shape. Same tone discipline (lowercase, no slop tokens).
- NEW field: `proactive_lens_active: true` on L3.01-L3.04 (signals the runtime to enable proactive count-ins).
- NEW field: `exemplar_audio_forbidden: true` on L3.01-L3.04 (active-session guard binding).

### Claude's Discretion

- The exact `bpm_confidence` / `phrase_position_confidence` thresholds (0.8 / 0.7 from ROADMAP are sensible defaults; can tune in ear-pass).
- The exact CueAnchor → `[cue:<anchor_id>]` mapping (how a phrase boundary becomes a citable anchor_id).
- L3.05 Recovery Drills synthesis (how the system "introduces" a train wreck — probably playback-rate or pitch drift on deck B).

</decisions>

<code_context>
## Existing Code Insights

### Reusable assets (shipped P91-P95)
- `src/vibemix/state/coach.py::AICoach.build_prompt` — REUSE (no new prompt builder)
- `src/vibemix/state/coach.py::evidence_line` — ADD runtime confidence gate here
- `src/vibemix/agent/dj_cohost.py` — live coach; extend with Course-3 proactive mode flag
- `src/vibemix/state/refresh.py` — single MusicState writer (UNTOUCHED)
- `src/vibemix/state/music_state.py` — `next_phrase_at`, `bpm_confidence`, `phrase_position_confidence` fields (verify all exist)
- `src/vibemix/state/evidence_registry.py` — extend with "cue" source (sites 1+2 atomic)
- `src/vibemix/prompts/matrix.py::CITATION_GRAMMAR_BLOCK` — site 3
- `src/vibemix/learn/audio_cue.py::ExemplarPlayer` — wire active-session check (P93 shipped the `state` kwarg)
- All existing CueAnchor + phrase detection — UNCHANGED

### Concurrent-session discipline
- 6 NEW JSON fixtures + 1 curriculum.py extension (shared) + 4 SHARED-FILE edits (the 4-site mirror) + 1 coach.py runtime gate + 1 audio_cue.py active-session check
- Named-path commits only; cardinal-invariant pins are non-negotiable

</code_context>

<deferred>
## Deferred Ideas

- Onboarding mode picker → P97
- Live audit + Kaan ear-pass on Course 3 → P98
- Per-genre play-mode branches → v9.x

</deferred>
