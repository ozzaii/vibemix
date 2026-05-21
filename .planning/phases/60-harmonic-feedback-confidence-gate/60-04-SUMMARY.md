---
phase: 60-harmonic-feedback-confidence-gate
plan: 04
subsystem: coach
tags: [harmonic, camelot, citation-linter, prompt-fragment, anti-slop, gemini]

# Dependency graph
requires:
  - phase: 60-02
    provides: "EventDetector KEY_CLASH/TRANSITION_OPPORTUNITY branches + Event.extra (a_side/a_camelot/b_side/b_camelot/semitones/clash) + default-off harmonic flag"
  - phase: 60-01
    provides: "is_clash()/compatible() deterministic verdict + semitone_distance() helper"
  - phase: 59
    provides: "existence-only CitationLinter key source + EvidenceRegistry single-writer key: observations"
provides:
  - "Real cited KEY_CLASH coach fragment (HARMONIC-01): system-decided verdict, cite-both-keys, forbids key/interval math"
  - "Real retrospective TRANSITION_OPPORTUNITY coach fragment (HARMONIC-04): past-tense only, silent when ungrounded"
  - "Matrix [ev:<TYPE>] grammar reconciled to include the two harmonic types (Open Q1 resolution)"
affects: [61-persona-voice, harmonic-feedback]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Narrate-only cited fragment: the code decides the verdict (is_clash), the LLM only narrates + cites; key math is forbidden in-prompt and stripped by the existence-only linter"
    - "Retrospective transition note: past-tense framing for any feedback whose live-imperative form would arrive 5-10s late through LLM+TTS latency"

key-files:
  created:
    - tests/state/test_coach_harmonic.py
  modified:
    - src/vibemix/state/coach.py
    - src/vibemix/prompts/matrix.py

key-decisions:
  - "The LLM narrates the system verdict — never computes intervals or invents a key. The fragment hands a pre-decided clash + pre-computed semitone count from Event.extra."
  - "Open Q1 resolved: KEY_CLASH + TRANSITION_OPPORTUNITY added to the matrix [ev:<TYPE>] grammar list for consistency (_fire writes [ev:<TYPE>], so the model may validly cite them). Goldens re-checked, byte-stable."
  - "Neither type added to ACK_ELIGIBLE_EVENTS — they are substantive full-payload events (diet path raises for them)."
  - "TRANSITION fragment carries no phrase-alignment / bass-swap specifics — vibemix has no per-deck phrase grid or dual-deck low-band, so those are not groundable; the fragment stays silent on them."

patterns-established:
  - "Pattern: cited narrate-only fragment — verdict from code, narration + citation from LLM, anti-slop enforced structurally by CitationLinter"
  - "Pattern: retrospective past-tense feedback for latency-bound events"

requirements-completed: [HARMONIC-01, HARMONIC-04]

# Metrics
duration: 6min
completed: 2026-05-21
---

# Phase 60 Plan 04: Cited Narrate-Only Harmonic Coach Fragments Summary

**Replaced the two Phase-59 stub coach arms with real cited harmonic fragments — KEY_CLASH hands the LLM a system-decided verdict + both decks' keys to cite + a hard "do NOT compute intervals" rule; TRANSITION_OPPORTUNITY is a strictly past-tense retrospective blend note — and reconciled the matrix [ev:<TYPE>] grammar.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-21T15:59:15Z
- **Completed:** 2026-05-21T16:05:05Z
- **Tasks:** 2 (TDD RED → GREEN)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- KEY_CLASH coach arm (HARMONIC-01): states "HARMONIC CLASH confirmed by the system (you do NOT decide this)", names both decks + keys + the pre-computed semitone count, instructs CITE BOTH keys exactly as `[key:A:8A]` / `[key:B:3A]`, FORBIDS inventing a key or computing intervals, guards `semitones=None` (cross-letter → "clashing" without a number), ends with the single-space silence escape.
- TRANSITION_OPPORTUNITY coach arm (HARMONIC-04): retrospective/past-tense ("You just blended deck A into deck B — harmonically the keys sat fine / clashing"), no present-tense imperatives, cites both keys, single-space silence escape.
- Matrix grammar reconciled: KEY_CLASH + TRANSITION_OPPORTUNITY added to the "Event types currently tracked" `[ev:<TYPE>]` list (Open Q1).
- Proved the structural anti-slop guarantee: a fabricated `[key:B:12B]` the registry never observed is stripped by the existence-only CitationLinter (whole-turn strip).

## Task Commits

1. **Task 1: Coach harmonic test (cited narration + retrospective + uncited-strip)** - `15ac737` (test) — RED
2. **Task 2: Replace stub arms with cited fragments + reconcile matrix grammar** - `b77b1d6` (feat) — GREEN

_TDD: RED test commit precedes the GREEN implementation commit._

## Files Created/Modified
- `tests/state/test_coach_harmonic.py` - 9 tests: cited-narration shape, no-key-math, None-semitone guard, uncited-strip, retrospective/no-imperatives, cite-both-keys, not-ack-eligible
- `src/vibemix/state/coach.py` - replaced the two Phase-59 stub `task_for_event` arms (KEY_CLASH + TRANSITION_OPPORTUNITY) with real cited fragments
- `src/vibemix/prompts/matrix.py` - added KEY_CLASH + TRANSITION_OPPORTUNITY to the `[ev:<TYPE>]` grammar list

## Decisions Made
- Open Q1 resolved in favour of adding both types to the matrix grammar list (low risk; `_fire` writes `[ev:<TYPE>]` so a citation would validate). Goldens re-checked after — byte-stable.
- Used `ev.extra.get(...)` with sane defaults in both arms (robust to a malformed/partial extra) rather than direct subscript, while still consuming the exact Plan-02 keys.

## Deviations from Plan
None - plan executed exactly as written. Surgical: only the two stub arms (coach.py) + the one matrix grammar line were touched; no other arm, no ACK_ELIGIBLE_EVENTS change, no golden re-baseline.

## Issues Encountered
- A bare `python3` invocation resolved to the Homebrew 3.14 interpreter (different `google-genai`, missing `ServiceTier`), producing 64 collection ImportErrors unrelated to this change. Re-ran the suite inside the project `.venv` (3.12) per CLAUDE.md — collection clean.

## Verification
- `tests/state/test_coach_harmonic.py` — 9 passed.
- `tests/state/test_coach_prompt_grounding.py` + `test_coach_prompt_diet.py` + `tests/agent/test_coach_prompt_grounding.py` — green, no golden churn.
- Full suite (`.venv`, PYTHONPATH=src): **7 failed, 4066 passed, 26 skipped**. The 7 failures are the documented pre-existing branch failures (repo/release/readme-matrix/anti-slop-wiring/main-smoke) — none touch coach.py, matrix.py, or the harmonic paths. Count held at 7; no new failures.
- `grep` confirms `a_camelot` / "do NOT decide this" / "single space" in coach.py and both types in matrix.py.

## Next Phase Readiness
- HARMONIC-01 (narrate-only) + HARMONIC-04 (retrospective) coach surface complete and gated default-off (Plan 60-02 flag). Phase 61 owns the persona voice and may sharpen the DJ-verb phrasing — the grounded facts are locked here.

## Self-Check: PASSED
- All 3 source/test files + SUMMARY.md present on disk.
- Both task commits (15ac737 RED, b77b1d6 GREEN) found in git log.

---
*Phase: 60-harmonic-feedback-confidence-gate*
*Completed: 2026-05-21*
