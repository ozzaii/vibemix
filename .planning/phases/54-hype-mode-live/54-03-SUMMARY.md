---
phase: 54-hype-mode-live
plan: 03
title: "Anti-slop spine — empty evidence -> no hallucinated hype line + grounded HYPE persona (LIVE-01)"
status: complete
req_ids: [LIVE-01]
commits: 2
---

# 54-03 SUMMARY — Anti-slop spine for hype mode (LIVE-01)

## What was built

The anti-slop spine pinned as a regression: every hype reaction must trace to a
real Event + real evidence, and empty/weak evidence yields SILENCE, not a
hallucinated hype line. vibemix's central product principle + the CLAUDE.md
hallucination-grounding hard gate.

### Two gates, REAL primitives (`tests/state/test_hype_anti_slop.py`)

**FLOOR (REAL `EventDetector`)** — no fire from nothing:
- silent state (audible=False, bpm=0) -> `None`
- out-of-range-BPM (bpm=300) -> `None` (even after the presence window)
- within the music-presence window (detect at +1s, before 4s elapse) -> `None`

**SPINE (REAL `EvidenceRegistry` + `CitationLinter`, no network, no live LLM)**:
- unbacked `[ev:DROP@45.2]` against an EMPTY snapshot -> `valid=False`,
  `reason='invalid_atoms'` (strip -> no voice)
- after `reg.write('ev','DROP',45.2)`, the same text -> `valid=True`
  (grounded within +-1.0s live tolerance -> emits)
- a 0.2s-off citation still resolves within tolerance -> `valid=True`
- a citation-free hype line -> `valid=False`, `reason='no_citations'`
- a `test_spine_uses_real_primitives_not_mocks` guard documents the no-mock
  contract (cold registry is genuinely `{}`; a real write yields
  `{"ev": {"DROP": (1.0,)}}`).

### Grounded HYPE persona (`tests/agent/test_hype_prompt_grounding.py`)

- `build_system_instruction(skill, 'hype')` returns three distinct, non-empty
  HYPE_* cells (beginner / intermediate / pro); the intermediate cell carries
  the v4 substring `friend in his studio`.
- `AICoach.build_prompt(Event('PHASE', grounded_state))` embeds the grounded
  evidence_line (`hearing[rms=`, `bpm=130`) + `event=PHASE` + the PHASE task
  tail — the reaction is built FROM real state, not a generic template.
- The load-bearing **no-`phase=`** anti-hallucination invariant holds on both
  `build_prompt` and `evidence_line`.

## No source behavior changed

Both files are tests only. The strip-on-unbacked-citation behavior is PINNED,
not altered. `git diff --name-only` shows ONLY the two new test files.

## Verification (real)

- `pytest -q tests/state/test_hype_anti_slop.py tests/agent/test_hype_prompt_grounding.py`
  -> **13 passed** (8 anti-slop + 5 persona-grounding).

## Commits

1. `bd8d25d` test(54-03): pin anti-slop floor (detector) + spine (linter strips unbacked, passes grounded) (LIVE-01)
2. `74319be` test(54-03): pin grounded HYPE persona + no-phase= invariant (LIVE-01)
