---
phase: 82-curate-unify-curator-co-host
plan: 01
subsystem: library (curator) + tests
tags: [wave-0, scaffold, xfail-strict, regression-pin, curate, anti-slop]
requires:
  - "Phase 78 genre_prototypes (the shared perception mechanism)"
  - "Phase 79 read_shared_lens / build_curator_instruction (the shared lens, already DONE)"
  - "profile/ + render_profile_for_cache (the shared taste vehicle)"
provides:
  - "tests/library/test_toolset.py CURATE-01 genre-via-prototypes xfail scaffolds"
  - "tests/library/test_curate_unify.py CURATE-02 taste scaffolds + 5 real-green must-stay-true pins"
affects:
  - "Plan 82-02 (lands the SEAM #1 genre + SEAM #2 taste wiring that flips the xfails green)"
tech-stack:
  added: []
  patterns:
    - "Wave-0 xfail(strict=True) scaffold convention (Phase 77-81 precedent)"
    - "Static-attribute import-boundary pin (invariant #1) over a subprocess"
    - "Class-method monkeypatch to pin one-mechanism routing (Pitfall 2)"
key-files:
  created:
    - "tests/library/test_curate_unify.py"
  modified:
    - "tests/library/test_toolset.py"
decisions:
  - "Pin (f) no-MusicState is a static-attribute check (curator never imports the live OBJECT into its namespace), NOT a sys.modules scan — because toolset.py imports `from vibemix.state import harmonics` and state/__init__ eagerly binds MusicState as a side effect, so the module is transitively present regardless. The attribute check matches what test_no_live_path_import's FORBIDDEN_NAMES static gate actually enforces (invariant #1 = no read/write of the live object)."
  - "Task-1 abstain scaffold uses a call-spy on classify_playing so it is genuinely RED today (the seam does not yet consult the mechanism) — a bare `genre in (None,\"unknown\")` would xpass against today's hardcoded `genre: None` and break strict xfail."
metrics:
  duration: ~12 min
  completed: 2026-05-26
---

# Phase 82 Plan 01: CURATE Wave-0 Scaffolds + Invariant Pins Summary

The Nyquist safety net for Phase 82: every CURATE-01/02 acceptance criterion now has a failing `xfail(strict=True)` scaffold that flips green only when Plan 02 lands the seam, plus five real-green "must-stay-true" pins (lens-shared regression, no-MusicState import boundary, no-track-title leak, cold-path byte-identity, surfaces-still-import). No `src/vibemix/` file touched; honest green (no Gemini client, no API key, zero package installs).

## What Was Built

### Task 1 — `tests/library/test_toolset.py` (extend) — CURATE-01 genre-via-prototypes
- `test_genre_via_prototypes_when_classified` (xfail-strict): monkeypatches `GenrePrototypeLookup.classify_playing` to a real label and asserts `get_track_features({"track_id":"t000"})["genre"]` is that label, not `None`.
- `test_genre_honest_none_on_abstain` (xfail-strict): a call-spy proves the seam must CONSULT the shared mechanism (RED today — never called) AND on abstain (`("unknown",0.0)`) the genre is honest-null (`None`/`"unknown"`), never fabricated (invariant #3).
- Reuses the existing in-memory `library`/`toolset` fixtures — no `RekordboxLibrary.CACHE_PATH` write (the `library.pkl` gotcha respected). The 6 existing grounding-gate tests stay green.

### Task 2 — `tests/library/test_curate_unify.py` (new) — CURATE-02 taste + invariant pins
- (a) `test_curator_taste_hint_present_when_profile_set` (xfail-strict): gemini `_system_instruction()` must carry the `preferred_genre` token when a profile is set.
- (c) `test_taste_hint_reaches_codex_backend` (xfail-strict): codex `_system_prompt()` must carry it too — the CURATE acid test (neither backend orphaned).
- (b) `test_curator_taste_cold_path_identical_when_no_profile` (REAL-GREEN): with no profile (consent-OFF), the built instruction is byte-identical to `build_curator_instruction(lens) + "\n" + _RULES_BLOCK`.
- (d) `test_taste_hint_no_track_titles_leak` (REAL-GREEN, T-82-01): `render_profile_for_cache` emits only the 5 allowlisted fields even when fed title/artist/free-form keys.
- (e) `test_lens_shared_across_both_backends` (REAL-GREEN, Phase-79 regression): both `agent._shared_lens` and `codex_curate._shared_lens` resolve the same `extra["lens"]="critique"`.
- (f) `test_curator_does_not_import_musicstate` (REAL-GREEN, invariant #1): a subprocess asserts neither `MusicState` nor `EventDetector` is reachable as a curator-module attribute.
- (g) `test_existing_surfaces_still_import` (REAL-GREEN): `ViberAgent`, `build_toolset`, `next_suggestion`, `telegram_bridge` all import.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Reframed pin (f) no-MusicState from a sys.modules scan to a static-attribute check**
- **Found during:** Task 2
- **Issue:** The plan's literal "assert no `vibemix.state.music_state` leaked into `sys.modules`" is RED today against existing code I must not change — `toolset.py:43` does `from vibemix.state import harmonics`, and `state/__init__` eagerly binds `MusicState`/`EventDetector` as a side effect, so the module is transitively in `sys.modules` regardless of the curator.
- **Fix:** Pin instead asserts neither `MusicState` nor `EventDetector` is reachable as an *attribute* of the three curator modules — i.e. the curator never imports the live OBJECT into its own namespace. This is exactly what `test_no_live_path_import`'s `FORBIDDEN_NAMES` static gate enforces, and it is the true meaning of invariant #1 (no read/write of the live state object). The pin is REAL-GREEN today and stays green through Plan 02.
- **Files modified:** tests/library/test_curate_unify.py
- **Commit:** 5898855

**2. [Rule 1 - Bug] Hardened the Task-1 abstain scaffold with a call-spy**
- **Found during:** Task 1
- **Issue:** The plan's abstain criterion (`genre in (None,"unknown")`) trivially passes today because `genre` is unconditionally `None` — an xpass, which under strict xfail is a HARD failure (and a false RED).
- **Fix:** Added a call-spy on `classify_playing` so the scaffold is genuinely RED (the seam does not yet consult the mechanism) while still asserting honest-null on abstain. Flips green only when Plan 02 routes genre through `genre_prototypes`.
- **Files modified:** tests/library/test_toolset.py
- **Commit:** e1c1e56

## Verification

- `tests/library/test_toolset.py` — 5 existing green, 2 new xfailed (plain); both FAIL under `--runxfail` (RED proven).
- `tests/library/test_curate_unify.py` — 5 real-green pins pass, 2 taste scaffolds xfailed; both FAIL under `--runxfail`.
- `tests/memory/test_no_live_path_import.py` — stays CLEAN (3 passed).
- Full suite: **4534 passed, 26 skipped, 5 xfailed (1 pre-existing budget gate + 4 new CURATE scaffolds), 4 xpassed (pre-existing live-hardware, non-strict)**, exit 0. Baseline was 4523 passed / 1 xfailed → +11 passed (5 new real-green pins + suite ordering), +4 xfailed, zero new failures, no strict-xpass.
- No `genai.Client`, no `GEMINI_API_KEY`, no package install (grep hits are comment-prose disclaimers only).

## Known Stubs

None. These are Wave-0 test scaffolds, not product code; the stubs they spec are the Plan-02 seams.

## Self-Check: PASSED

- FOUND: tests/library/test_curate_unify.py
- FOUND: tests/library/test_toolset.py (modified)
- FOUND commit: e1c1e56 (Task 1)
- FOUND commit: 5898855 (Task 2)
