---
phase: 78-perceive-deeper-generalized-ear
plan: 01
subsystem: testing
tags: [pytest, xfail-strict, nyquist, byte-identity, perceive, genre-prototypes, single-writer]

# Dependency graph
requires:
  - phase: 77-wire
    provides: wired evidence_line + grounding surface that PERCEIVE deepens
provides:
  - Wave-0 RED scaffolds for PERCEIVE-01 (deltas), PERCEIVE-02 (trajectory), PERCEIVE-03 (genre prototypes) + genre reconciliation gate
  - REAL-GREEN cold-path byte-identity pin (v8.0 baseline that implementation must preserve)
  - shared synthetic fixtures (perceive_state_pair, synthetic_corpus) in tests/state/conftest.py
affects: [78-02-deltas-trajectory, 78-03-genre-prototypes, 78-04-genre-feed-reconcile, perceive, coach, refresh, library]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "xfail(strict=True) Wave-0 RED scaffold — failing test flips to real green when its implementation plan lands; silent early-pass = HARD failure (Nyquist safety net)"
    - "Cold-path byte-identity REAL-GREEN pin — captures the v8.0 baseline as a golden the additive implementation must not break"
    - "Autouse tmp_path cache routing for all library-cache tests (T-78-01-01 dev-data-tampering mitigation)"

key-files:
  created:
    - tests/state/test_coach_perceive.py
    - tests/state/test_refresh_perceive.py
    - tests/library/test_genre_prototypes.py
  modified:
    - tests/state/conftest.py

key-decisions:
  - "Cold-path byte-identity golden copied VERBATIM from test_coach.py's absolute-bytes v5.0/v8.0 baseline — so a future maintainer who adds a trailing space / reorders a field also breaks this pin."
  - "empty_trajectory_omitted phrased as a REAL GREEN (absence assertion holds on current baseline) per the plan's 'real green pin if not referencing a new field' guidance — not xfail."
  - "test_genre_prototypes.py imports the nonexistent vibemix.library.genre_prototypes INSIDE each xfail test body (not module-level) so collection succeeds and the ModuleNotFoundError IS the xfail trigger — a module-level import would break collection of the whole file."
  - "_route_caches_to_tmp is an autouse fixture (every test) + a dedicated real-green test_real_cache_untouched pin; the proto-path monkeypatch is wrapped in try/ModuleNotFoundError (raising=False) so it no-ops until Plan 03 creates the module."
  - "Single-writer scaffolds assert a genre_source holder kwarg on _tick_once (the deck-holder copy-in idiom) — its TypeError today is the PERCEIVE-03 RED trigger; Plan 04 adds the kwarg."

patterns-established:
  - "Wave-0 RED + cold-path byte-identity: every additive-perception requirement gets a strict-xfail behavior test PLUS a real-green pin of the baseline it must preserve."
  - "Library-cache test isolation: autouse tmp_path routing of RekordboxLibrary.CACHE_PATH + centering.CENTROID_PATH/META + the new prototype sidecar, with a mtime spot-check on the real library.pkl."

requirements-completed: []  # scaffolds only — PERCEIVE-01/02/03 implemented + closed in Plans 02/03/04

# Metrics
duration: ~12min
completed: 2026-05-26
---

# Phase 78 Plan 01: PERCEIVE Wave-0 RED Scaffolds + Cold-Path Byte-Identity Pin Summary

**Three new test files install the Nyquist safety net for PERCEIVE — 9 strict-xfail behavior scaffolds (deltas / trajectory / genre-prototype build+classify / genre single-writer feed / genre reconciliation) plus a REAL-GREEN cold-path byte-identity pin that captures the v8.0 baseline implementation must preserve.**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-05-26
- **Tasks:** 2
- **Files modified:** 4 (3 created, 1 created-where-empty)

## Accomplishments
- **Cold-path byte-identity (REAL GREEN):** `test_coach_perceive.py` pins a cold audible `MusicState` (no prior snapshot, empty trajectory) byte-for-byte to the v8.0 baseline + asserts NO `trajectory[` / `Δ` / `rose` / `fell` tokens — the additive-design contract Plans 02/04 must not break.
- **PERCEIVE-01/02 render scaffolds (xfail-strict):** delta-rendered-above-floor, delta-abstains-below-floor (anti-slop), trajectory-rendered-when-warm — all RED on missing `prev_perceive` / `trajectory_narrative` fields.
- **PERCEIVE single-writer scaffolds (xfail-strict):** `prev_perceive` captured last in the lock, trajectory composed + bounded across repeated ticks, genre fed ONLY via `_tick_once` reading an off-loop holder, and the genre-reconciliation gate (confident embedding wins / sub-floor → DSP fallback).
- **PERCEIVE-03 prototype scaffolds (xfail-strict):** `build_prototypes` centered-mean-per-label + `classify` floor/tie-margin abstain — RED on the nonexistent `vibemix.library.genre_prototypes` module.
- **Shared synthetic fixtures:** `perceive_state_pair` (controllable scalar-delta MusicState pair) + `synthetic_corpus` (anisotropic 1536-dim labeled vectors) in `tests/state/conftest.py`.
- **T-78-01-01 mitigation pinned:** autouse tmp_path routing of all cache paths + a real-green untouched-cache assertion; the real `~/.cache/vibemix/library.pkl` mtime was verified unchanged across the run.

## Task Commits

1. **Task 1: PERCEIVE-01/02 render scaffolds + cold-path byte-identity pin** - `82a6452` (test)
2. **Task 2: PERCEIVE single-writer + prototype scaffolds + shared fixtures** - `a08a074` (test)

**Plan metadata:** _(this docs commit)_

## Files Created/Modified
- `tests/state/test_coach_perceive.py` - cold-path byte-identity REAL-GREEN pin + PERCEIVE-01/02 render xfail-strict scaffolds.
- `tests/state/test_refresh_perceive.py` - PERCEIVE single-writer / trajectory / genre-feed / reconciliation xfail-strict scaffolds.
- `tests/library/test_genre_prototypes.py` - PERCEIVE-03 build_prototypes + classify xfail-strict scaffolds; autouse tmp_path cache routing + real-cache-untouched pin.
- `tests/state/conftest.py` - was empty; now holds `perceive_state_pair` + `synthetic_corpus` shared fixtures.

## Decisions Made
- Cold-path golden copied verbatim from `test_coach.py`'s absolute-bytes baseline so any field reorder / trailing-space regression also trips this pin.
- `empty_trajectory_omitted` is a real green (absence assertion on the current baseline), not xfail.
- Nonexistent-module imports placed INSIDE xfail test bodies (not module-level) so the `ModuleNotFoundError` is the per-test xfail trigger and file collection still succeeds.
- The prototype-sidecar monkeypatch is `raising=False` inside a `try/except ModuleNotFoundError` so it no-ops until Plan 03 creates the module.
- The genre single-writer scaffolds assert a `genre_source` holder kwarg on `_tick_once` (the deck-holder copy-in idiom); its `TypeError` today is the RED trigger, Plan 04 adds it.

## Deviations from Plan
None - plan executed exactly as written. The two test-design judgment calls the plan explicitly delegated (phrase `empty_trajectory_omitted` as real-green vs xfail; resolve the genre-feed holder/reconciliation shape) were resolved per the plan's stated guidance, not as deviations.

## Issues Encountered
None. `tests/state/conftest.py` existed but was empty (1 blank line) — handled by the plan's "create or extend if present" instruction (overwrote with the shared fixtures).

## Self-Check: PASSED
- `tests/state/test_coach_perceive.py` — FOUND
- `tests/state/test_refresh_perceive.py` — FOUND
- `tests/library/test_genre_prototypes.py` — FOUND
- `tests/state/conftest.py` — FOUND
- commit `82a6452` — FOUND
- commit `a08a074` — FOUND
- Combined verification block: 64 passed, 9 xfailed (zero unexpected fail, zero xpass on the new scaffolds).
- Full suite: **4456 passed / 0 failed / 10 xfailed (1 pre-existing budget gate + 9 new) / 4 xpassed (pre-existing live-hardware) / 26 skipped** (243s). Honest green — no `genai.Client`, no `GEMINI_API_KEY`.
- Real `~/.cache/vibemix/library.pkl` mtime `1779706225` unchanged before/after (T-78-01-01 mitigation verified).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02 flips PERCEIVE-01/02: adds `MusicState.prev_perceive` + `trajectory_narrative` fields, the refresh-loop single-writer captures, and the coach.py delta/trajectory render branches → 5 of the 9 xfails flip green (the 3 coach render + 2 refresh single-writer for 01/02).
- Plan 03 creates `vibemix/library/genre_prototypes.py` (`build_prototypes` + `classify` + `PROTOTYPES_PATH`/`PROTOTYPES_META_PATH` sidecar) → flips the 2 prototype xfails.
- Plan 04 adds the `genre_source` holder kwarg + reconciliation to `_tick_once` → flips the 2 genre-feed/reconcile xfails.
- No blockers. Cold-path byte-identity pin stands guard the whole way.

---
*Phase: 78-perceive-deeper-generalized-ear*
*Completed: 2026-05-26*
