---
phase: 78-perceive-deeper-generalized-ear
plan: 04
subsystem: state
tags: [perceive, genre-reconcile, single-writer, confidence-band, anti-slop, off-loop-dispatch]

# Dependency graph
requires:
  - phase: 78-01
    provides: PERCEIVE-03 genre-feed + reconcile xfail-strict scaffolds (RED spec)
  - phase: 78-03
    provides: GenrePrototypeLookup holder (get_latest/classify_playing/clear) + PROTO_FLOOR centered-cosine scale
provides:
  - "vibemix.state.genre.genre_reconcile: normalize_embedding_confidence (centered-cosine→>=0.5 render band) + reconcile_genre (embedding-wins-when-confident else DSP fallback)"
  - "refresh._tick_once genre_source kwarg: off-loop-holder read + reconciled single-writer detected_genre/genre_confidence write + TRACK_CHANGE off-loop classify dispatch"
  - "PERCEIVE-03 CLOSED — embedding genre actually drives the prompt; phase 78 complete"
affects: [perceive, refresh, coach, genre]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Affine confidence-band rescale anchoring two confidence scales onto one render gate (the flagged-risk fix)"
    - "Event-driven high-trust signal commits immediately + resyncs hysteresis (vs per-tick noisy DSP through the 3-tick dwell)"
    - "Off-loop TRACK_CHANGE dispatch via daemon thread + clear()-first generation token (mirrors Grounding); single writer READS the holder"

key-files:
  created:
    - src/vibemix/state/genre/genre_reconcile.py
    - tests/state/test_genre_reconcile.py
  modified:
    - src/vibemix/state/refresh.py
    - tests/state/test_refresh_perceive.py

key-decisions:
  - "Affine anchor PROTO_FLOOR(0.25)→0.5, 1.0→1.0: a centered cosine exactly at the floor sits on the render boundary; clearing the floor clears the >=0.5 gate, sub-floor is suppressed. Pins THE flagged risk (RESEARCH Pitfall 4 / A3)."
  - "Test scaffold uses kwarg name `genre_source` (not the plan-body's `genre_lookup`) — the xfail-strict scaffold is authoritative, so the kwarg is `genre_source`."
  - "Confident embedding (TRACK_CHANGE-dispatched once-per-track, 86.5%-validated) commits IMMEDIATELY and resyncs GenreHysteresis to it — re-debouncing a non-flickering high-trust signal through the 3-tick dwell would wrongly suppress a correct genre for the first 3 ticks of every track. The noisy per-tick DSP path stays dwell-debounced."
  - "reconcile_genre returns the embedding label ONLY when it cleared the floor; the agree-case (emb_label == raw_genre) falls to the DSP-through-hysteresis path so DSP keeps owning a genre it already scored."

requirements-completed: [PERCEIVE-03]

# Metrics
duration: ~25min
completed: 2026-05-26
---

# Phase 78 Plan 04: PERCEIVE-03 Genre-Feed + Reconcile Wiring Summary

**A pure `state/genre/genre_reconcile.py` solves THE flagged risk — an affine rescale that maps the embedding lookup's centered-cosine confidence (≈0.25 floor) into coach.py's `>= 0.5` render band, plus an embedding-wins-when-confident reconciliation — and `refresh._tick_once` now reads the off-loop `GenrePrototypeLookup` holder inside its lock, reconciles it with the DSP `score_genre`, and writes ONE coherent `detected_genre`/`genre_confidence` (single-writer invariant #1), dispatching the lookup off-loop on TRACK_CHANGE. PERCEIVE-03 closes; phase 78 complete.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-05-26
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- **`normalize_embedding_confidence` (Task 1):** the flagged-risk fix. A deterministic monotone affine rescale anchored `PROTO_FLOOR → 0.5` and `1.0 → 1.0`, clamped to `[0,1]`. A centered cosine clearing the ~0.25 floor maps to `>= 0.5` (clears coach.py:334); a sub-floor cosine maps to `< 0.5` (suppressed → abstain holds). Pinned by `normalize_embedding_confidence(0.40) >= 0.5` and `(0.20) < 0.5`.
- **`reconcile_genre` (Task 1):** embedding wins when it is a real label AND its normalized confidence clears the render floor; else DSP fallback at its native confidence. Agree / disagree-confident-embedding / sub-floor-embedding / both-unknown all covered. Pure module — no state write, no API, no model literal.
- **`refresh._tick_once` genre_source wiring (Task 2):** the single writer READS `genre_source.get_latest()` inside the existing `with state._lock:` batch, reconciles with the DSP `(raw_genre, raw_genre_conf)`, and writes `detected_genre`/`genre_confidence` ONCE. `genre_source=None` / empty holder / sub-floor embedding → the pure DSP-through-hysteresis path → v8.0 byte-identical (cold-path goldens green).
- **Off-loop TRACK_CHANGE dispatch (Task 2):** on a real track change, `_dispatch_genre_lookup` `clear()`s the holder first (generation-token discard of a superseded in-flight lookup), then runs `classify_playing` on a daemon thread, try-guarded so a lookup failure logs and never wedges the 10Hz tick (T-78-04-04). Mirrors the Grounding off-loop dispatch; the worker NEVER writes the live state dataclass.
- **Hysteresis policy resolved:** the confident embedding genre (dispatched once-per-track, not per-tick) commits immediately and resyncs `GenreHysteresis` to it; the noisy per-tick DSP score stays 3-tick dwell-debounced. This is why a single tick with a confident holder commits the embedding label (the scaffold's contract).
- **Flipped the final 2 PERCEIVE-03 xfail scaffolds to real green** (`test_genre_fed_single_writer`, `test_genre_reconciliation`) → PERCEIVE-03 CLOSED, phase 78 complete.
- **Single-writer + no-API grep gates pass:** no `state.detected_genre =` / `state.genre_confidence =` outside `refresh.py`; no `genai.Client` / `GEMINI_API_KEY` token on the new paths.
- **Honest green:** €0, numpy-only, no Gemini client, no API key.

## Task Commits

1. **Task 1: pure genre reconcile + centered-cosine→render-band normalize** - `3f38a5c` (feat)
2. **Task 2: feed embedding genre into the single-writer refresh write** - `66dd2b1` (feat)

**Plan metadata:** _(this docs commit)_

## Files Created/Modified

- `src/vibemix/state/genre/genre_reconcile.py` — `normalize_embedding_confidence` (the flagged-risk affine rescale) + `reconcile_genre` (embedding-wins-when-confident else DSP fallback). Pure, no state write, no API.
- `tests/state/test_genre_reconcile.py` — 12 unit tests: the known-cosine→above/below-0.5 pin (the flagged risk), anchors/clamp/monotone, and the four reconcile branches.
- `src/vibemix/state/refresh.py` — `genre_source` kwarg threaded through `_tick_once` + `state_refresh_loop`; holder read + reconcile + immediate-commit/resync inside the lock; `_dispatch_genre_lookup` off-loop TRACK_CHANGE dispatch.
- `tests/state/test_refresh_perceive.py` — removed the 2 xfail markers (now real green).

## Decisions Made

- **Affine anchor `PROTO_FLOOR → 0.5`, `1.0 → 1.0`.** A centered cosine exactly at the floor sits on the render boundary; this is the simplest deterministic monotone map that reconciles the two confidence scales onto the single `>= 0.5` gate (RESEARCH Pitfall 4 / Assumption A3).
- **kwarg is `genre_source`** (the xfail-strict scaffold's contract), not the plan-body's `genre_lookup`. The scaffold is authoritative.
- **Confident embedding commits immediately + resyncs hysteresis.** See Deviations Rule 1 — the dwell exists to debounce the per-tick DSP flicker, not the once-per-track high-trust embedding signal.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Hysteresis dwell blocked the single-tick embedding commit the scaffold requires**
- **Found during:** Task 2 (running `test_genre_fed_single_writer` / `test_genre_reconciliation`).
- **Issue:** The plan said "run the COMMITTED label through `apply_genre_hysteresis`". Applied naively, a fresh `GenreHysteresis(current_label="unknown")` requires a 3-tick dwell before a NEW label commits — so a single tick supplying a confident holder (`("hardtechno", 0.82)` / `("trance", 0.90)`) committed `"unknown"`, failing the scaffold's `detected_genre == "hardtechno"` / `== "trance"` assertion.
- **Fix:** The embedding genre is dispatched ONLY on TRACK_CHANGE (once per track, not per-tick) and is a high-trust 86.5%-validated signal — it does not flicker bar-to-bar, so the per-tick dwell is the wrong debounce for it. When the embedding wins, commit it immediately and resync `GenreHysteresis` (`current_label = label`, clear pending) — mirroring how `apply_genre_hysteresis` commits `unknown` immediately. The noisy per-tick DSP path stays dwell-debounced exactly as before. This is correctness, not a scope change: re-debouncing the embedding through the dwell would wrongly suppress a correct genre for the first 3 ticks of every track.
- **Files modified:** `src/vibemix/state/refresh.py`
- **Commit:** `66dd2b1`

**2. [Rule 3 - Blocking] Scaffold kwarg name differs from plan body**
- **Found during:** Task 2 (reading the authoritative xfail-strict scaffold).
- **Issue:** The plan body referred to a `genre_lookup` kwarg; the xfail-strict scaffold (`test_refresh_perceive.py`) calls `_tick_once(..., genre_source=holder)`. A `genre_lookup` kwarg would leave the scaffold red.
- **Fix:** Named the kwarg `genre_source` (the scaffold's contract). No behavior change vs the plan's intent.
- **Files modified:** `src/vibemix/state/refresh.py`, `tests/state/test_refresh_perceive.py`
- **Commit:** `66dd2b1`

## Issues Encountered
None beyond the two auto-fixed items above.

## Known Stubs
None. The TRACK_CHANGE off-loop dispatch passes the audible track title (`tt`) to `classify_playing`; the holder abstains safely (`("unknown", 0.0)`, no live embed) for any id not in the cached library, so the live wiring is complete and fail-safe. Real live-set genre accuracy beyond the folder-proxy validation is the parked Phase-81 BENCH + Kaan's-ear item (never faked — KAAN-ACTION, not a stub).

## Self-Check: PASSED
- `src/vibemix/state/genre/genre_reconcile.py` — FOUND
- `tests/state/test_genre_reconcile.py` — FOUND
- commit `3f38a5c` — FOUND
- commit `66dd2b1` — FOUND
- Task 1: 12 passed (reconcile/normalize). Task 2: 13 passed (genre/reconcil/byte_identical/silent/audible).
- Full suite: **4481 passed / 0 failed / 1 xfailed (pre-existing budget gate) / 4 xpassed (pre-existing live-hardware) / 26 skipped** (240s) — the 2 PERCEIVE-03 genre-feed/reconcile xfails flipped to real green. Honest green, no Gemini client, no API key.
- Single-writer grep gate: PASS (no `state.detected_genre =` / `state.genre_confidence =` outside refresh.py). No-API gate on new files: PASS.

## Next Phase Readiness
- **PERCEIVE-03 CLOSED — phase 78 complete** (all 3 requirements: PERCEIVE-01/02 in Plan 02, PERCEIVE-03 mechanism in Plan 03, PERCEIVE-03 wiring here).
- Next phase per the v8.1 spine: **P79 (LENS) ‖ P80 (GROUND)** — both depend on P77 + the now-deepened P78 evidence surface.
- No blockers. Live-set genre accuracy = soft KAAN-ACTION (Phase-81 BENCH + ear-pass), rides forward.

---
*Phase: 78-perceive-deeper-generalized-ear*
*Completed: 2026-05-26*
