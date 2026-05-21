---
phase: 60-harmonic-feedback-confidence-gate
plan: 02
subsystem: state
tags: [event-detector, harmonics, camelot, key-clash, conservatism, anti-slop, default-off-flag]

# Dependency graph
requires:
  - phase: 60-01
    provides: "deterministic Camelot is_clash/compatible/semitone_distance in harmonics.py"
  - phase: 59
    provides: "MusicState.deck_state (per-deck camelot + confidence + source), DECK_CITE_MIN_CONF=0.6, registered KEY_CLASH (28s) + TRANSITION_OPPORTUNITY (20s) event types/cooldowns, DeckPoller._vision_enabled default-off precedent"
provides:
  - "_melodic_overlap_gate(state) — suppression precondition composed from shipped MusicState signals (no new detector stack)"
  - "KEY_CLASH branch in EventDetector.detect() — fires only on is_clash()==True with cross-deck + cite-floor suppression"
  - "TRANSITION_OPPORTUNITY branch — retrospective, groundable-only (both decks cited + structural blend move)"
  - "harmonic_clash_enabled default-off flag (Kaan-ear ship gate) + kwarg, mirroring DeckPoller._vision_enabled"
affects: [60-03 (Kaan-ear veto corpus flips the flag), 60-04 (coach cited fragments narrate the KEY_CLASH/TRANSITION_OPPORTUNITY extra)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Default-off ship-gate flag (kwarg + attribute) mirroring DeckPoller._vision_enabled — a behavior stays completely quiet until a Kaan-ear veto flips it"
    - "Pure read-gate composed from shipped MusicState fields (no new audio computation) as a detector precondition"
    - "Layered conservatism in a detector branch: flag -> melodic-overlap gate -> cross-deck cite-floor -> deterministic verdict -> cooldown"

key-files:
  created:
    - tests/state/test_event_detector_harmonic.py
  modified:
    - src/vibemix/state/event_detector.py

key-decisions:
  - "TONAL_SHARE_FLOOR=0.20 module constant gates percussive/atonal overlaps (mid+high band share floor); start conservative, raise only on Kaan-ear false-fires"
  - "TRANSITION_OPPORTUNITY scoped near-zero this phase: fires only on both-decks-cited + a recent structural xfader/EQ move (reusing MIX_MOVE significance keys); phrase-grid/dual-deck-low-band notes stay silent (not groundable)"
  - "Import DECK_CITE_MIN_CONF from deck_poller (no import cycle — deck_poller does not import event_detector)"
  - "Both new event types kept OUT of ACK_ELIGIBLE_EVENTS (unchanged) — they are substantive full-payload, not diet-path acks"

patterns-established:
  - "Default-off harmonic_clash_enabled flag = the runtime conservatism killswitch; no clash reaches the audience until Plan 60-03 veto passes"
  - "_melodic_overlap_gate runs BEFORE any clash branch; clash is structurally impossible unless the gate AND flag both pass"

requirements-completed: [HARMONIC-02, HARMONIC-03]

# Metrics
duration: ~20min
completed: 2026-05-21
---

# Phase 60 Plan 02: Harmonic Detector Branches + Default-Off Gate Summary

**Wired `_melodic_overlap_gate` + the KEY_CLASH and TRANSITION_OPPORTUNITY branches into `EventDetector.detect()` behind a default-off `harmonic_clash_enabled` flag — a clash is structurally impossible to reach the audience unless the melodic-overlap gate passes, both decks clear the 0.6 cite floor, `is_clash()` returns True, AND the Kaan-ear ship gate flips the flag.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2 (TDD RED → GREEN)
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- `_melodic_overlap_gate(state)` — a pure read-gate over shipped MusicState fields (audible_deck=="mix", rms ≥ LOW_RMS, non-breakdown/silent/low phase, not vocal_active, mid+high tonal share ≥ TONAL_SHARE_FLOOR). No new detector stack, no new audio computation.
- `KEY_CLASH` branch placed AFTER MIX_MOVE / BEFORE the genre chain — layered conservatism: default-off flag → gate → cross-deck both-resolved + confidence ≥ DECK_CITE_MIN_CONF (0.6) → deterministic `is_clash()` verdict → inherited 28s cooldown. Emits the cited extra (a_side/a_camelot/b_side/b_camelot/semitones).
- `TRANSITION_OPPORTUNITY` branch — retrospective, groundable-only: fires only when both decks are cited AND a recent structural xfader/EQ blend move is present; silent otherwise (honest near-zero this phase per Open Q2 §5).
- `harmonic_clash_enabled` default-off flag + kwarg, mirroring `DeckPoller._vision_enabled` — the Kaan-ear ship gate.

## Task Commits

1. **Task 1: Harmonic detector test (RED)** - `2a868fe` (test)
2. **Task 2: gate + branches + default-off flag (GREEN)** - `c870ab4` (feat)

_TDD plan: test commit (RED) precedes the implementation commit (GREEN)._

## Files Created/Modified
- `tests/state/test_event_detector_harmonic.py` - 13 tests: default-off, every gate suppression path (single-deck, breakdown/silent/low, percussive/acapella, sub-LOW_RMS), cross-deck cite-floor (sub-floor/missing/unresolved deck), safe-pair vs clash verdict, inherited 28s cooldown, TRANSITION_OPPORTUNITY silence paths.
- `src/vibemix/state/event_detector.py` - imports (is_clash/semitone_distance/DECK_CITE_MIN_CONF), TONAL_SHARE_FLOOR constant, `harmonic_clash_enabled` flag + kwarg in `__init__`, `_melodic_overlap_gate` helper, KEY_CLASH + TRANSITION_OPPORTUNITY branches between MIX_MOVE and the genre chain.

## Decisions Made
- `TONAL_SHARE_FLOOR=0.20` (mid+high band share) suppresses drum-only/atonal overlaps; conservative starting value documented for Kaan-ear tuning.
- TRANSITION_OPPORTUNITY deliberately scoped near-zero (groundable retrospective structural blend only) — silence over a guess, on-thesis.
- Imported `DECK_CITE_MIN_CONF` from `deck_poller` after confirming no import cycle.

## Deviations from Plan
None - plan executed exactly as written. (The test prime helper was adjusted during the GREEN step to sync `last_phase`/`last_audible_track` so the earlier-priority PHASE branch doesn't pre-empt the harmonic branches under test — a test-harness detail, not a contract change.)

## Issues Encountered
- The full suite must run in the project `.venv` (Python 3.12). The system `python3` is 3.14 and lacks `livekit` / has an incompatible `google.genai` — running there produced 64 collection errors. Re-ran under `.venv`: **7 failed, 4046 passed, 26 skipped** — exactly the documented 7-failure branch baseline (release/readme/coach-wiring infra; none in event_detector/harmonics). No new failures introduced.

## Verification
- `tests/state/test_event_detector_harmonic.py` — 13/13 green.
- Full suite (`.venv`): 7 pre-existing failures unchanged, 0 new.
- `ACK_ELIGIBLE_EVENTS` unchanged (`{HEARTBEAT, MIX_MOVE, LAYER_ARRIVAL, KAAN_SPOKE}`) — neither new type added.
- Flag default False, gate + `is_clash()` verdict call present in `event_detector.py`.

## Next Phase Readiness
- Detector branches live but quiet by default. Plan 60-03 (Kaan-ear veto corpus) flips `harmonic_clash_enabled`. Plan 60-04 replaces the stub coach arms with cited fragments that narrate the KEY_CLASH/TRANSITION_OPPORTUNITY `extra`.

## Self-Check: PASSED

- `tests/state/test_event_detector_harmonic.py` — FOUND
- `60-02-SUMMARY.md` — FOUND
- Commit `2a868fe` (RED) — FOUND
- Commit `c870ab4` (GREEN) — FOUND

---
*Phase: 60-harmonic-feedback-confidence-gate*
*Completed: 2026-05-21*
