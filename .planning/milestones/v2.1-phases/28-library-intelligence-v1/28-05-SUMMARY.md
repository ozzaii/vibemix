---
phase: 28-library-intelligence-v1
plan: 05
subsystem: library
tags: [similar, user-asked, anti-feature-guard, LIBRARY-14]

requires:
  - phase: 28-01
    provides: LibraryEmbedder.embed_track
  - phase: 28-02
    provides: LibraryStore.search

provides:
  - similar_to() with seed-self-exclusion
  - SimilarResult dataclass
  - 'vibemix library similar' CLI subcommand
  - Anti-feature guards: docstring + structural import check

affects: []

tech-stack:
  added: []
  patterns:
    - "Anti-feature guard via docstring contract + structural import test"
    - "Seed self-exclusion (k+1 search, drop seed)"

key-files:
  created:
    - src/vibemix/library/similar.py
    - tests/library/test_similar.py
    - tests/scripts/test_cli_library_similar.py
  modified:
    - src/vibemix/library/__init__.py
    - src/vibemix/__main__.py (similar subcommand description with USER-ASKED warning)

key-decisions:
  - "USER-ASKED-only contract enforced at 3 levels: docstring (loud), CLI help description, structural test that bans agent-loop imports of similar."
  - "Seed track excluded from results (k+1 search, drop seed)."
  - "Defensive: skip tracks in store but missing from library."

patterns-established:
  - "Pattern: anti-feature modules carry USER-ASKED in docstring + are structurally banned from agent-loop imports via test_no_background_caller_imports_similar."
---

# Plan 28-05 — USER-ASKED Similar-Track

Status: complete. 10/10 tests pass.

## What landed

### `src/vibemix/library/similar.py`
- `similar_to()` returns top-K results sorted by similarity DESC.
- Seed track auto-excluded (k+1 search, drop seed at top).
- Empty library / unknown seed → `[]` without embed call.
- Module docstring carries the USER-ASKED contract.

### CLI: `vibemix library similar <track_id>`
- Help description includes the USER-ASKED warning so the contract surfaces at every CLI invocation.

## Anti-feature enforcement

3 layers:
1. **Module docstring**: "ANTI-FEATURE GUARD ... NEVER autosurfaces ... USER-ASKED ONLY".
2. **CLI help description**: "vibemix never autosurfaces ... anti-feature guard per CONTEXT LIBRARY-14".
3. **Structural test**: `test_no_background_caller_imports_similar` scans `dj_cohost.py`, `coach.py`, `session_loop.py` for `import vibemix.library.similar` — fails if any background-loop module imports it.

## Test posture

- `pytest tests/library/test_similar.py`: 7 pass in 0.5s
- `pytest tests/scripts/test_cli_library_similar.py`: 3 pass in 6s

## Deviations

- None.
