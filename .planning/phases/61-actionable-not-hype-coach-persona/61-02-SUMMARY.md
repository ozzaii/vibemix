---
phase: 61-actionable-not-hype-coach-persona
plan: 02
subsystem: coach-persona
tags: [coach, anti-slop, prompt-matrix, dj-verbs, harmonic, GREEN]
requires:
  - "61-01 RED-spec coach-cell contract asserts (test_prompt_61_coach_*)"
  - "Phase 60 harmonic arms (KEY_CLASH / TRANSITION coach.py:284 verb register)"
  - "Phase 10 prompt matrix (_CELLS / _VALID_MODES / build_system_instruction)"
provides:
  - "Sharpened COACH_BEGINNER/INTERMEDIATE/PRO cells (observed→impact→prescribe + DJ-verb vocabulary)"
  - "COACH_INTERMEDIATE positive-callout balance rule + same-line prescribe-clause"
  - "COACH_BEGINNER impact clause + gentle DJ-verb register + grounded-only harmonic path"
  - "All 12 test_prompt_61_coach_* asserts GREEN across 3 coach skills"
affects:
  - "src/vibemix/prompts/matrix.py"
  - "tests/prompts/test_matrix.py"
tech-stack:
  added: []
  patterns:
    - "RED→GREEN: 61-01 fenced the contract, 61-02 turns it green by sharpening prose"
    - "Cell-prose verb-align TO state/coach.py harmonic arm (one prescriptive register)"
    - "Coach ANCHOR_PHRASES updated in-lockstep with cell anchor lines (byte-pinned); HYPE frozen"
key-files:
  created:
    - ".planning/phases/61-actionable-not-hype-coach-persona/61-02-SUMMARY.md"
  modified:
    - "src/vibemix/prompts/matrix.py — sharpened 3 COACH_* constant bodies"
    - "tests/prompts/test_matrix.py — beginner-coach ANCHOR_PHRASES lockstep update (Phase-61 comment)"
    - ".planning/phases/61-actionable-not-hype-coach-persona/61-VALIDATION.md — Per-Task Map + wave_0_complete: true"
decisions:
  - "Surfaced the FULL canonical DJ-verb set (kill/swap/cut/filter/wait/tighten/ride) as an explicit DJ-VERB REGISTER line in each cell body — anchors alone could not supply all 7 word-tokens, and aligning the register to coach.py:284 makes a harmonic turn read like a mix-move turn."
  - "COACH_INTERMEDIATE anchors were NOT reworded (all 4 already prescriptive) → no intermediate ANCHOR_PHRASES change needed; only the cell prose grew (balance + same-line + verbs)."
  - "COACH_PRO already carried 'name it AND say the fix in the SAME line' + PROPS arm → only the verb-register prose line was added; PRO arms left intact."
metrics:
  duration: "~12 min"
  completed: "2026-05-21"
  tasks: 2
  files-modified: 3
---

# Phase 61 Plan 02: Actionable-Not-Hype Coach Persona Summary

Sharpened the three COACH cell constants in `prompts/matrix.py` so the actionable-not-hype
contract that 61-01 fenced (RED) turns GREEN, without touching a single hype golden. The
coach voice is now a real prescriptive DJ mentor — observed→impact→prescribe on the same
line, the canonical DJ-verb vocabulary, a positive-callout balance rule, and a gentle
grounded-only harmonic path for beginners — while the Phase-54-validated hype voice stays
frozen behind its byte-identity goldens.

## What Was Built

### Task 1 — COACH_PRO + COACH_INTERMEDIATE — `9163d40`
The two cells needing the least change, done first to establish the fence before the headline beginner rewrite.
- **COACH_PRO**: added a single `DJ-VERB REGISTER` prose line surfacing the canonical set
  (`kill, swap, cut, filter, wait, tighten, ride` + pull/push/bring in) and noting a harmonic
  clash uses the SAME register as a mix move (verb-aligned to `state/coach.py:284`). Arms
  (DESERVED-CRITIQUE+FIX / NUDGE-FORWARD / PROPS, READ-THE-MOMENT, DELIVERY) left untouched.
- **COACH_INTERMEDIATE**: three sharpenings —
  (1) `OBSERVED → IMPACT → PRESCRIBE` same-line clause (name the fault AND the move in one breath);
  (2) `POSITIVE-CALLOUT BALANCE` rule mirroring PRO's PROPS arm (closes the over-correction-to-cold
  Pitfall 3 / COACH-04 guard); (3) the `DJ-VERB REGISTER` line. CONCRETE FEEDBACK + HONEST + LATENCY
  + LENGTH + LANGUAGE + EVIDENCE PACKET structure preserved. The four existing anchors were already
  prescriptive and kept verbatim → no `ANCHOR_PHRASES` change for intermediate.

After this commit: `61_coach` verb/prescribe/balance asserts GREEN for `pro` + `intermediate`;
beginner still RED (Task 2 target); hype goldens + persona byte-identity byte-stable.

### Task 2 — COACH_BEGINNER + lockstep anchors — `f35e9bc`
The headline COACH-01 rewrite, kept gentle:
- `OBSERVED → IMPACT → PRESCRIBE (gently)` — three beats on the same line, impact as a required
  middle step.
- `DJ-VERB REGISTER (kept gentle)` — the same canonical verbs, framed softly for a beginner.
- `GENTLE HARMONIC PATH (grounded only)` — on a KEY_CLASH/transition event, deliver a soft cited
  note tied to the observed event only; cite the system's keys, NEVER invent a key (the existence-only
  CitationLinter is the hard guarantee; the prompt is the soft layer).
- Kept `ONE THING PER TURN` + `ENCOURAGING TONE` (the beginner balance rule, COACH-04) and the
  EVIDENCE PACKET / past-tense LATENCY / LENGTH / LANGUAGE sections.
- **Anchors**: replaced the vague nudges (`give the build more space` / `more space` /
  `you're rushing the blend` / `rushing the blend`) with cited-observation + DJ-verb past-tense lines
  (`the build felt rushed — try holding it 8 bars longer`, `the blend ran long and muddied the drop —
  tighten it next time`) and added a gentle harmonic anchor (`those two tracks were fighting a bit —
  try cutting one in cleaner`). Exactly 8 anchors, gentle/encouraging tone.
- **LOCKSTEP**: `ANCHOR_PHRASES[("beginner","coach")]` in `tests/prompts/test_matrix.py` updated in the
  SAME commit with a Phase-61 comment, byte-pinned against the cell anchor lines by
  `test_prompt_01_each_cell_has_eight_anchor_phrases`.

After this commit: all 12 `test_prompt_61_coach_*` asserts (4 groups × 3 skills) GREEN.

## Deviations from Plan

None — plan executed exactly as written. The only judgment call (noted as a decision): the full
canonical DJ-verb set is surfaced as an explicit `DJ-VERB REGISTER` prose line in each cell body
rather than relying on anchors, because the word-token verb check (`kill/wait/tighten/ride` were
missing across all three cells) could not be satisfied by anchor phrasing alone.

## Constraint Compliance

- `state/coach.py` **untouched** (verb-aligned the cell prose TO it, per research Assumption A2).
- CitationLinter **untouched** (T-61-04 accept: prompt is soft layer, linter is hard guarantee).
- No new mode — `_VALID_MODES == {"hype","coach"}` and `_CELLS` unchanged.
- Shared blocks (`_ANTI_SLOP_FOOTER`, `CITATION_GRAMMAR_BLOCK`, `COACH_TAG_DSL_BLOCK`,
  `COACH_CLOSING_BLOCK`) and all hype cells / shared `task_for_event` arms **untouched** (T-61-03 mitigate).
- No package installs (T-61-SC).

## Verification

- **Hype fence** (`tests/prompts/test_matrix.py tests/agent/test_persona.py
  tests/agent/test_hype_prompt_grounding.py`): all GREEN — HYPE_INTERMEDIATE byte-identity + all hype
  anchors stable; persona SYSTEM_INSTRUCTION byte-identical.
- **61_coach contract** (`-k 61_coach` + dispatch + coach grounding): 13 passed, 0 failed — all 4 groups
  GREEN across 3 coach skills.
- **Full suite**: **7 failed, 4085 passed, 26 skipped** — exactly the 7 pre-existing
  `live-tuning-or-brain` WIP failures (anti-slop-wiring, cut-release-invokes-bravoh, readme-matrix ×2,
  cut-release-preflight ×2, main-smoke — NONE touch coach.py/matrix.py). Down from the 13 before this
  plan (the 6 RED `61_coach` asserts are gone). NO new failures; hype goldens byte-stable.

## Known Stubs

None.

## Self-Check: PASSED

- src/vibemix/prompts/matrix.py — FOUND (contains `DJ-VERB REGISTER`, `POSITIVE-CALLOUT BALANCE`, `GENTLE HARMONIC PATH`)
- tests/prompts/test_matrix.py — FOUND (beginner-coach ANCHOR_PHRASES updated with Phase 61 comment)
- .planning/phases/61-actionable-not-hype-coach-persona/61-02-SUMMARY.md — FOUND
- Commit 9163d40 — FOUND
- Commit f35e9bc — FOUND
