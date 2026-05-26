---
phase: 89-dj-library-ingest
plan: 02
subsystem: library
tags: [rekordbox, collection-xml, camelot, beatgrid, metadata, pyrekordbox, harmonics]

# Dependency graph
requires:
  - phase: 25-library
    provides: "RekordboxLibrary collection.xml loader + pickle cache + SQLCipher-dormant posture"
  - phase: state-harmonics
    provides: "to_camelot(raw) deterministic Tonality->Camelot table (total, honest-None)"
provides:
  - "Enriched TrackEntry: genre/label/rating/play_count/comments/camelot/beatgrid (additive, default-coerced)"
  - "TempoNode dataclass + TEMPO beatgrid parse (variable-grid aware; () when absent)"
  - "Cue Type fidelity (cue/fadein/fadeout/load/loop) instead of a flat default"
  - "Camelot computed at parse via harmonics.to_camelot; raw classical key preserved"
  - "SCHEMA_VERSION 1->2 cache invalidation for the widened TrackEntry shape"
affects: [89-03-cue-anchor-mapping, technics-filter, curator-grounding, co-host-grounding]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Parse-time Camelot normalization via the deterministic harmonics table (LLM never computes keys)"
    - "Defensive duck-typed pyrekordbox attribute reads via _safe_get + total int/float coercers (never raise on garbage)"
    - "Typed-empty coercion on absence (Invariant #3: missing stays missing, never fabricated)"
    - "SCHEMA_VERSION bump as the clean cache-shape-migration gate"

key-files:
  created: []
  modified:
    - "src/vibemix/library/rekordbox.py"
    - "tests/library/test_rekordbox.py"
    - "tests/library/fixtures/synthetic_collection.xml"

key-decisions:
  - "Camelot is computed at parse via harmonics.to_camelot and stored alongside the untouched raw key — a false-confident key never surfaces (None on odd/empty)."
  - "Rating byte ladder {0,51,102,153,204,255} maps to 0..5 stars with a .get(0) fallback; already-0..5 values pass through; odd values clamp to 0 (never raise)."
  - "Cue Type accepts both pyrekordbox's already-resolved label string and a raw int (schema drift) — int-coerced and mapped, unknown -> 'cue'."
  - "SCHEMA_VERSION bumped 1->2 so a stale v1 library.pkl misses cleanly via the existing version guard rather than unpickling a short blob."
  - "SQLCipher db6 path stays dormant — only docstring mentions of the grep gate exist; zero real import/call."

patterns-established:
  - "Enrichment-by-addition: every new TrackEntry field has a typed-empty default so spine consumers are unaffected."
  - "TEMPO beatgrid read defensively off track.tempos; absent accessor degrades to () instead of raising."

requirements-completed: []

# Metrics
duration: ~8min
completed: 2026-05-26
---

# Phase 89 Plan 02: Rekordbox Metadata-Richness Refinement Summary

**`rekordbox.py` now lifts the curated metadata the `collection.xml` export already exposed — genre/label/rating/play_count/comments — plus a Camelot-at-parse code, a variable-grid TEMPO beatgrid, and real cue Type labels, all additive and honestly empty on absence.**

## Performance

- **Duration:** ~8 min (verification + Task 2 commit; Task 1 RED pre-committed)
- **Completed:** 2026-05-26
- **Tasks:** 2/2 (Task 1 RED was committed at `41d6afd` in a prior session; Task 2 implementation verified + committed this session)
- **Files modified:** 3 (2 committed this session)

## Accomplishments
- Extended `TrackEntry` with `genre`, `label`, `rating` (0..5 stars), `play_count`, `comments`, `camelot`, `beatgrid` — all default-coerced (Invariant #3).
- Added `TempoNode` (inizio_s/bpm/metro/battito) + `_track_to_beatgrid`: variable-grid aware, `()` when no TEMPO children — never fabricated.
- Camelot normalized at parse via `harmonics.to_camelot` (deterministic table, honest-None on empty/odd key); raw classical `key` preserved untouched.
- Cue `Type` upgraded to real int->label fidelity (cue/fadein/fadeout/load/loop), handling both pyrekordbox's resolved label string and a raw int defensively.
- `SCHEMA_VERSION` bumped 1->2 so stale v1 caches invalidate cleanly under the existing unpickle version guard.

## Task Commits

1. **Task 1: Enriched fixture + RED strict-xfail tests** — `41d6afd` (test) — *pre-committed in a prior session; verified intact.*
2. **Task 2: Read high-value fields + Camelot + beatgrid + cue Type** — `5699f20` (feat) — flips the 6 Task-1 xfail tests to real-green; SCHEMA_VERSION 1->2; TrackID edge fixture `edge`->`9001`.

_TDD plan: Task 1 RED (`test`) → Task 2 GREEN (`feat`). No REFACTOR commit needed (implementation landed clean)._

## Files Created/Modified
- `src/vibemix/library/rekordbox.py` — TempoNode dataclass, enriched TrackEntry, `_track_to_beatgrid`, `_rating_to_stars`, `_coerce_int/_coerce_float`, `_resolve_cue_type`, `to_camelot` at parse, SCHEMA_VERSION=2.
- `tests/library/test_rekordbox.py` — 6 Plan-89-02 enriched-parse tests flipped from strict-xfail to green; edge fixture TrackID `edge`->`9001`.
- `tests/library/fixtures/synthetic_collection.xml` — track 1 enriched with Genre/Label/Rating/PlayCount/Comments + two TEMPO nodes (variable grid) + a Type=3 load mark (committed in Task 1).

## Verification

- `PYTHONPATH=src python3 -m pytest -q tests/library/test_rekordbox.py` → **18 passed** (offline, no network, no torch, no GEMINI_API_KEY).
- Import-clean: `rekordbox.py` imports with no `torch`/`laion_clap` in `sys.modules` (printed `IMPORT_CLEAN`). harmonics is pure (numpy-free).
- SQLCipher dormancy: `grep -rn "Rekordbox6Database\|pyrekordbox.db6" src/vibemix/library/rekordbox.py` matches only the docstring describing the gate — zero real import/call.
- Fixture is valid XML; `<TEMPO` count = 2; `Rating="204"` present.
- `grep "to_camelot"`, `grep "class TempoNode"`, `grep "SCHEMA_VERSION: int = 2"` all present in `rekordbox.py`.
- Full offline suite: **4719 passed, 27 skipped, 4 xfailed, 4 xpassed, 6 failed**. All 6 failures are outside this plan's scope fence (see Deferred Issues) — none touch `rekordbox.py` or its tests.

## Deviations from Plan

None for the plan's own surface. The Task 2 implementation was already authored in the working tree (uncommitted) at session start; this executor verified it against every acceptance criterion and committed it atomically. Task 1's RED commit (`41d6afd`) was already present and verified intact (strict-xfail markers, SCHEMA_VERSION still 1 in that commit).

## Deferred Issues (out of scope — logged to deferred-items.md)

The full-suite run surfaced 6 failures, all OUTSIDE the 89-02 scope fence and NOT caused by this plan's two files:

- `tests/library/test_sources_rekordbox.py` (4 failing) — Plan 89-01's `library/sources/` LibrarySource Protocol RED tests (committed `6aa9686`); implementation not landed yet. Expected-RED for the parallel plan.
- `tests/security/test_no_api_key_surface.py::test_no_api_key_label_text_anywhere_in_ui` (1 failing) — UI/security guard unrelated to the Python parser.

Per the executor scope boundary these were logged to `deferred-items.md` and left untouched.

## Cardinal Invariants

- **Invariant #3 (trust the audio / missing stays missing):** every new field coerces to a typed empty on absence; `camelot` is `None` on odd/empty key (never guessed); `beatgrid` is `()` with no TEMPO children.
- Single-writer / citation-grounding / one-socket invariants untouched (zero-touch — additive parser change only).

## Self-Check: PASSED
