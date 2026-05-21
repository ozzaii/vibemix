---
phase: 60-harmonic-feedback-confidence-gate
plan: 01
subsystem: state
tags: [harmonics, camelot, anti-slop, deterministic-predicate, circle-of-fifths]

# Dependency graph
requires:
  - phase: 59-full-deck-awareness-grounding
    provides: to_camelot normalizer + _CAMELOT_RE recognizer + DECK_CITE_MIN_CONF cite-floor + KEY_CLASH/TRANSITION_OPPORTUNITY event registration
provides:
  - "is_clash(a,b) — deterministic NARROW Camelot clash predicate (same-letter hours {5,6,7} = 1-semitone/tritone)"
  - "compatible(a,b) — SAFE-relationship predicate (same/fifth/+2/relative/±1-diagonal)"
  - "semitone_distance(a,b) — same-letter hour→semitone interval so the coach narrates without LLM key math"
  - "_parse / _hour_distance helpers + _CLASH_HOURS/_SAFE_HOURS/_HOUR_TO_SEMITONES tables"
affects: [event_detector harmonic branches, coach task_for_event KEY_CLASH/TRANSITION_OPPORTUNITY arms, kaan-ear veto harness]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deterministic table-driven predicate the LLM only narrates (anti-slop core, HARMONIC-01)"
    - "Honest-None/never-raise contract mirrored from to_camelot"
    - "Conservative-by-default NARROW clash band — under-flag over over-flag"

key-files:
  created: []
  modified:
    - src/vibemix/state/harmonics.py
    - tests/state/test_harmonics.py

key-decisions:
  - "is_clash is NARROW: only same-letter hours {5,6,7} fire; cross-letter + drift hours {3,4} stay silent (the deliberate 'neither' zone)"
  - "_parse normalizes via to_camelot FIRST so musical/open-key forms resolve before the _CAMELOT_RE split — reuses the shipped recognizer, no second parser"
  - "semitone_distance returns None for cross-letter pairs (no single same-letter ring) rather than guessing — keeps the honest-unknown discipline"
  - "8A↔6A is hour-distance 2 (SAFE -2 energy move), labeled as such — NOT a misleading 'hour-4' drift comment"

patterns-established:
  - "Pattern: pure deterministic Camelot verdict in harmonics.py; the LLM narrates the verdict, never computes intervals"
  - "Pattern: compatible() and is_clash() are NOT complements — a deliberate silent middle band (hours 3/4, most cross-letter)"

requirements-completed: [HARMONIC-01]

# Metrics
duration: ~14min
completed: 2026-05-21
---

# Phase 60 Plan 01: Deterministic Camelot Clash Predicate Summary

**Pure table-driven `is_clash`/`compatible`/`semitone_distance` on top of `to_camelot` — the anti-slop core where the LLM narrates a Camelot clash the code already proved, never computing intervals (HARMONIC-01).**

## Performance

- **Duration:** ~14 min
- **Tasks:** 2 (TDD RED → GREEN)
- **Files modified:** 2

## Accomplishments
- `is_clash(a, b)` — NARROW deterministic clash predicate: only same-letter hour-distances {5,6,7} (the 1-semitone / tritone dissonance band) fire; cross-letter and the hours-3/4 drift zone stay silent.
- `compatible(a, b)` — SAFE-relationship predicate: same key / adjacent perfect fifth / +2 energy (`_SAFE_HOURS={0,1,2}`), relative major/minor (same number, swapped letter), and the exact ±1 cross-letter diagonal.
- `semitone_distance(a, b)` — same-letter hour→semitone interval via the verified `_HOUR_TO_SEMITONES` table (cross-letter / None → None) so the coach can say "1 semitone apart" without the LLM doing key math.
- `_parse` / `_hour_distance` helpers + `_CLASH_HOURS` / `_SAFE_HOURS` lookup tables, all pure and never-raising, mirroring `to_camelot`'s honest-None contract.
- 41 new table-oracle test cases covering CLASH / SAFE / DRIFT bands, honest-None never-raises, compatible mirror, and the semitone anchors — full unit-table coverage of every relationship class.

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1: table-oracle test (RED)** — `35b21e8` (test) — failing tests; ImportError because the predicate did not exist yet.
2. **Task 2: is_clash/compatible/semitone_distance (GREEN)** — `3083aac` (feat) — implementation turns every RED assertion green.

_(No REFACTOR commit — the GREEN implementation was already clean against the §Pattern 1 reference.)_

## Files Created/Modified
- `src/vibemix/state/harmonics.py` — added `_parse`, `_hour_distance`, `_CLASH_HOURS`/`_SAFE_HOURS`/`_HOUR_TO_SEMITONES`, `semitone_distance`, `compatible`, `is_clash`; updated module docstring scope note (Phase 60 functions now shipped).
- `tests/state/test_harmonics.py` — extended import; added `CLASH_PAIRS`/`SAFE_PAIRS`/`DRIFT_PAIRS` oracles + `test_clash_pairs_flag`, `test_safe_pairs_never_flag`, `test_compatible_safe_pairs`, `test_drift_pairs_not_compatible_not_clash`, `test_canonical_clash_safe_anchors`, `test_predicate_honest_none_never_raises`, `test_semitone_distance_anchors`, `test_semitone_distance_cross_letter_or_none_is_none`.

## Decisions Made
- **NARROW clash band by design** — `_CLASH_HOURS={5,6,7}` only. Hours 3/4 (drift) and all cross-letter pairs sit in the intentional silent "neither" zone, because a wrong key tag (~57-70% library accuracy) there is indistinguishable from a real drift. Under-flagging is acceptable; over-flagging trips Kaan's gate.
- **`_parse` normalizes via `to_camelot` first** — so musical (`Am`) and open-key (`1m`) forms resolve before the `_CAMELOT_RE` split. Reuses the shipped recognizer; no second parser.
- **`semitone_distance` is same-letter only** — cross-letter pairs have no single semitone ring, so they return `None` rather than a guessed interval (honest-unknown).
- **8A↔6A labeled as SAFE -2 energy (hour-distance 2)** — per the corrected RESEARCH note; deliberately NOT commented as "hour-4" drift.

## Deviations from Plan

None — plan executed exactly as written (TDD RED → GREEN, both tasks committed atomically with strict per-file staging).

## Issues Encountered
None.

## Verification
- `PYTHONPATH=src python3 -m pytest -q tests/state/test_harmonics.py` → **98 passed** (57 pre-existing `to_camelot` + 41 new predicate cases).
- `grep -c "def is_clash" src/vibemix/state/harmonics.py` → **1**; all four functions (`is_clash`, `compatible`, `semitone_distance`, `_hour_distance`) defined.
- Full suite `PYTHONPATH=src python3 -m pytest -q` → **7 failed, 4033 passed, 26 skipped**. The 7 failures are the documented pre-existing `live-tuning-or-brain` WIP failures (Phase 59 deferred-items.md) — count UNCHANGED, identical set, no new failures. Killswitch / anti-slop invariants untouched.

## User Setup Required
None — pure in-repo logic, no external service config, no new dependencies.

## Next Phase Readiness
- HARMONIC-01 deterministic half is complete and unit-table-proven. `is_clash` / `compatible` / `semitone_distance` are ready for Plan 02 to wire into `EventDetector.detect()` (the `KEY_CLASH` / `TRANSITION_OPPORTUNITY` branches + `_melodic_overlap_gate`) and Plan 04's cited coach fragments.
- The detector ships gated/quiet by default until the Kaan-ear veto corpus (Plan 03) passes — the predicate itself is the proven oracle that gate sits on.

## Self-Check: PASSED
- FOUND: 60-01-SUMMARY.md, src/vibemix/state/harmonics.py, tests/state/test_harmonics.py
- FOUND commits: 35b21e8 (test/RED), 3083aac (feat/GREEN)

---
*Phase: 60-harmonic-feedback-confidence-gate*
*Completed: 2026-05-21*
