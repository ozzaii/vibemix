---
phase: 78-perceive-deeper-generalized-ear
plan: 02
subsystem: state
tags: [perceive, deltas, calibrated-confidence, trajectory, single-writer, byte-identity, anti-slop]

# Dependency graph
requires:
  - phase: 78-01
    provides: PERCEIVE-01/02 xfail-strict render + single-writer scaffolds + cold-path byte-identity pin
provides:
  - "MusicState.prev_perceive (prior-tick scalar snapshot) + trajectory_narrative (bounded multi-scale narrative) — additive falsy-default fields"
  - "deltas.py — pure render_delta (abstain-below-floor) + calibrate_confidence bucket map (no state write, no API)"
  - "refresh._tick_once single-writer capture of prev_perceive (last in lock) + _compose_trajectory"
  - "coach.evidence_line gated Δ[...] + trajectory[...] render branches (cold path byte-identical)"
affects: [78-03-genre-prototypes, 78-04-genre-feed-reconcile, coach, refresh, agent-prompt, lens]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure render helper returning None to abstain (anti-slop): cold prior / zero baseline / sub-floor relative move all omit, never a 0% line"
    - "Deterministic bucket calibration (strong/clear/slight) over a logistic — human-legible in a prompt + trivially test-pinnable"
    - "Single-writer prior-snapshot captured as the LAST write inside the lock so the NEXT tick diffs against a consistent prior"
    - "Bounded narrative recomputed each tick from already-bounded fields (no new buffers, no accumulation)"

key-files:
  created:
    - src/vibemix/state/deltas.py
  modified:
    - src/vibemix/state/music_state.py
    - src/vibemix/state/refresh.py
    - src/vibemix/state/coach.py
    - tests/state/test_coach_perceive.py
    - tests/state/test_refresh_perceive.py

key-decisions:
  - "Calibration is a deterministic 3-bucket map (strong>=0.40 / clear>=0.18 / slight) not a logistic — the consumer is a TEXT PROMPT, so a human-legible bucket grounds Gemini better and is auditable."
  - "Δ-line is rendered ALONGSIDE the raw hearing[...] scalars (not instead) per the CONTEXT contract — raw scalars retained; Δ[...] appended only when prev exists AND a scalar clears the 10% floor."
  - "Δ covers sub (kick density) / rms / onset_density — the three scalars whose movement reads as a real perceptual change; bpm/band-balance deltas omitted to avoid noise."
  - "Trajectory energy-arc label ('building'/'settled') is only asserted when a phrase chain or a move anchors it — a bare 'settled' on a cold state would break byte-identity."
  - "Trajectory NOT added to _evidence_line_compact (diet/ack path) — like the decks[...] block it is substantive full-payload."
  - "DELTA_FLOOR=0.10 (10% relative) — tight enough to surface a kick-density swell, loose enough to suppress bar-to-bar 'rose 2%' jitter."

requirements-completed: [PERCEIVE-01, PERCEIVE-02]

# Metrics
duration: ~10min
completed: 2026-05-26
---

# Phase 78 Plan 02: PERCEIVE-01 Deltas + Calibrated Confidence & PERCEIVE-02 Multi-Scale Trajectory Summary

**The EAR now speaks in CHANGE: two additive single-writer MusicState fields (`prev_perceive`, `trajectory_narrative`) + a pure `deltas.py` feed gated `Δ[kick density rose 18% (clear)]` and `trajectory[build→drop→groove; building; last move: bass-swap 20s ago]` into the prompt — abstaining below floor (anti-slop) and byte-identical to the v8.0 baseline on the cold path.**

## Performance
- **Duration:** ~10 min
- **Completed:** 2026-05-26
- **Tasks:** 2
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments
- **PERCEIVE-01 deltas + calibrated confidence:** new pure `deltas.py` — `render_delta(label, cur, prev, *, floor, fmt)` returns Δ-phrasing (`"kick density rose 18% (clear)"`) above the 10% relative floor, and `None` (abstain) on a cold prior, a zero baseline, OR a sub-floor move. `calibrate_confidence` is a deterministic monotone bucket map (strong/clear/slight). No state write, no library, no API.
- **PERCEIVE-02 multi-scale trajectory:** `refresh._compose_trajectory` joins three scales — phrase chain (last-3 `phase_history`), energy-arc (`buildup_score` → building/settled), newest `recent_moves` + age — into ONE bounded string, recomputed each tick from already-bounded fields (no new buffers, no accumulation).
- **Single-writer captures (invariant #1):** `state.trajectory_narrative` composed after the phase_history/recent_moves/long_arc writes; `state.prev_perceive` captured as the LAST write before lock release so the NEXT tick diffs against a consistent prior. Both live inside the existing `with state._lock:` batch — grep-confirmed no assignment outside `_tick_once`.
- **Gated render (anti-slop + byte-identity):** `coach.evidence_line` appends a `Δ[...]` branch (only when `prev_perceive` non-empty and a scalar clears the floor) and a `trajectory[...]` branch (only when non-empty). Both `if <field>:`-guarded; raw `hearing[...]` scalars retained; diet/compact path untouched.
- **Scaffolds flipped:** all 5 PERCEIVE-01/02 xfail-strict scaffolds from Plan 01 (`test_delta_rendered`, `test_delta_abstains_below_floor`, `test_trajectory_rendered_when_warm`, `test_prev_snapshot_written_in_lock`, `test_trajectory_composed_bounded`) flipped to real green. The 4 PERCEIVE-03 scaffolds stay xfail (Plans 03/04).

## Task Commits
1. **Task 1: Additive fields + pure delta/calibration helpers** - `24e8dcb` (feat)
2. **Task 2: Single-writer capture + trajectory compose + gated render** - `826c6a4` (feat)

**Plan metadata:** _(this docs commit)_

## Files Created/Modified
- `src/vibemix/state/deltas.py` (created) — pure `render_delta` + `calibrate_confidence`, `DELTA_FLOOR=0.10`, abstain semantics.
- `src/vibemix/state/music_state.py` — `prev_perceive: dict = {}` + `trajectory_narrative: str = ""` additive falsy-default fields with the SINGLE-WRITER comment block.
- `src/vibemix/state/refresh.py` — `_compose_trajectory` helper + single-writer compose/capture inside `_tick_once`'s lock batch.
- `src/vibemix/state/coach.py` — `from vibemix.state.deltas import ...` + gated `Δ[...]` and `trajectory[...]` render branches.
- `tests/state/test_coach_perceive.py` — added 4 focused `render_delta`/`calibrate_confidence` unit tests; un-xfailed 3 PERCEIVE-01/02 render scaffolds.
- `tests/state/test_refresh_perceive.py` — un-xfailed the 2 PERCEIVE-01/02 single-writer/trajectory scaffolds.

## Decisions Made
- Bucket calibration over logistic — prompt consumer reads `(clear)` better than a probability; auditable.
- Δ-line alongside raw scalars (not replacing) per CONTEXT; floor 10%; covers sub/rms/onset only.
- Energy-arc label only when anchored by a phrase/move (cold-path byte-identity).
- Trajectory off the diet path (substantive full-payload, mirrors decks[...]).

## Deviations from Plan
None - plan executed exactly as written. The two judgment calls the plan delegated (which scalars get a Δ-line; trajectory phrasing/order) were resolved per the interface anchors and the recent_moves/phase_history render precedents, not as deviations.

## Issues Encountered
None.

## Self-Check: PASSED
- `src/vibemix/state/deltas.py` — FOUND
- `src/vibemix/state/music_state.py` (prev_perceive + trajectory_narrative) — FOUND
- `src/vibemix/state/refresh.py` (_compose_trajectory + single-writer captures) — FOUND
- `src/vibemix/state/coach.py` (Δ[ + trajectory[ render) — FOUND
- commit `24e8dcb` — FOUND
- commit `826c6a4` — FOUND
- `tests/state/test_coach_perceive.py tests/state/test_refresh_perceive.py tests/state/test_coach.py`: **72 passed, 2 xfailed** (the 2 remaining are PERCEIVE-03, correct).
- Single-writer grep gate: `grep ... src/vibemix | grep -v refresh.py` returns EMPTY (PASS).
- Full suite: **4465 passed / 26 skipped / 5 xfailed (1 pre-existing budget + 4 PERCEIVE-03) / 4 xpassed (pre-existing live-hardware) / 13 warnings** (240s). Honest green — no `genai.Client`, no `GEMINI_API_KEY`.

## Threat Surface
Per the plan's `<threat_model>`, all three `mitigate` dispositions are implemented:
- T-78-02-01 (consistency): both writes inside `with state._lock:`; grep gate empty.
- T-78-02-02 (anti-slop truth): `render_delta` abstains below floor — pinned by `test_delta_abstains_below_floor`.
- T-78-02-03 (cold drift): every new branch `if <falsy>:`-gated; cold byte-identity green (`test_cold_path_byte_identical` + `test_coach.py` goldens). No new threat surface introduced.

## Next Phase Readiness
- Plan 03 creates `vibemix/library/genre_prototypes.py` → flips the 2 prototype xfails.
- Plan 04 adds the `genre_source` holder kwarg + reconciliation to `_tick_once` → flips the 2 genre-feed/reconcile xfails.
- The cold-path byte-identity pin stands guard; the Δ + trajectory render edges are now live for the lens (P79) to interpret.

---
*Phase: 78-perceive-deeper-generalized-ear*
*Completed: 2026-05-26*
