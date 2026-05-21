---
phase: 59-full-deck-awareness-grounding
plan: 03
subsystem: state
tags: [events, cooldowns, event-priority, read-only, repo-scrub, deck-state, sqlcipher-dormancy, tokenize]

# Dependency graph
requires:
  - phase: 59-full-deck-awareness-grounding (Plan 59-01)
    provides: harmonics.to_camelot, DeckTrack/DeckState model, additive MusicState.deck_state field
  - phase: 59-full-deck-awareness-grounding (Plan 59-02)
    provides: dedicated existence-only `key:` evidence source + linter rule (DECK-03)
provides:
  - "KEY_CLASH (priority 7) + TRANSITION_OPPORTUNITY (priority 5) registered in EVENT_PRIORITY — plumbing only, no firing"
  - "KEY_CLASH (28.0s) + TRANSITION_OPPORTUNITY (20.0s) cooldowns in MIN_EVENT_GAP_PER_TYPE"
  - "DECK-05 read-only repo guarantee: test_deck_readonly + positive control + deck-path SQLCipher dormancy"
affects: [60-harmonic-feedback-confidence-gate, 59-04 deck poller]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Event-type plumbing-before-firing: register priority + cooldown in 59 so Phase 60's detector branches plug into a non-zero-priority slot (closes the EVENT_PRIORITY.get(type,0) silent-0 gap)"
    - "tokenize-based comment+docstring stripping for repo grep-gates so grep-gate documentation prose cannot self-invalidate the gate"
    - "Two-tier read-only scan: SQLCipher class banned repo-wide; DJ-DB write patterns banned in the deck path only (vibemix's own sqlite-vec store legitimately writes)"
    - "Positive-control test guards the static gate from vacuously passing (proves the detector catches a synthetic write path)"

key-files:
  created:
    - .planning/phases/59-full-deck-awareness-grounding/59-03-SUMMARY.md
  modified:
    - src/vibemix/state/event.py
    - src/vibemix/audio/constants.py
    - tests/state/test_event_priority.py
    - tests/audio/test_constants.py
    - tests/repo/test_repo_scrub.py

key-decisions:
  - "KEY_CLASH=7 (tie with TRACK_CHANGE), TRANSITION_OPPORTUNITY=5 (tie with MIX_MOVE) — per RESEARCH event-plumbing section; cooldowns 28.0/20.0 are A5 plumbing values, Phase 60 tunes by ear"
  - "DECK-05 static scan uses tokenize (strips COMMENT + STRING tokens) rather than literal `grep -v '^#'` because the existing grep-gate docs live in DOCSTRINGS, not #-comments — tokenize is the robust generalization of the plan's intent"
  - "`.commit()`/write-mode patterns scoped to the deck path only — vibemix's own sqlite-vec embedding cache (library/embed.py, index_sqlite_vec.py, search.py) legitimately commits; DECK-05 is the narrower guarantee about the USER's DJ collection (master.db landmine, Risk 4)"

patterns-established:
  - "Plumbing-only event registration: types + priorities + cooldowns land a phase before the firing logic"
  - "Self-validating repo gate: a positive-control companion test prevents a stripper bug from making the gate vacuously pass"

requirements-completed: [DECK-04, DECK-05]

# Metrics
duration: 18min
completed: 2026-05-21
---

# Phase 59 Plan 03: Event-Type Plumbing + DECK-05 Read-Only Guarantee Summary

**Registered KEY_CLASH (pri 7 / 28s) + TRANSITION_OPPORTUNITY (pri 5 / 20s) event types as plumbing-only, and landed the DECK-05 strictly-read-only repo test (tokenize-stripped two-tier scan + SQLCipher dormancy) that fails if any future commit writes a DJ-software DB.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-05-21T13:10Z
- **Completed:** 2026-05-21
- **Tasks:** 2
- **Files modified:** 5 (2 src + 3 test)

## Accomplishments

- Closed the latent priority-engine plumbing gap: an unregistered `KEY_CLASH`/`TRANSITION_OPPORTUNITY` would have silently ranked at priority 0 (below HEARTBEAT) the moment Phase 60 emits one — both now carry documented priorities (7 / 5) and cooldowns (28.0s / 28.0s wait — 20.0s for TRANSITION_OPPORTUNITY) honoring the per-entry one-line-why convention.
- Landed DECK-05 as a regression-pinned repo test that statically scans executable source (comments + docstrings stripped via `tokenize`) for any DJ-DB write-mode / SQLCipher-live-DB pattern, and a subprocess-dormancy sibling that confirms importing the deck path loads no `*sqlcipher*` module.
- Added a positive-control test that proves the detector actually catches a synthetic `from pyrekordbox.db6 import Rekordbox6Database` + `db.commit()` write path while ignoring the same strings inside a docstring — so the gate can never pass vacuously.
- No firing/detection logic added (Phase 60 scope held — `event_detector.py` carries zero references to either new type).

## Task Commits

Each task was committed atomically:

1. **Task 1: Register KEY_CLASH + TRANSITION_OPPORTUNITY (plumbing only)** - `8040be7` (feat)
2. **Task 2: DECK-05 read-only repo guarantee (TDD test-only)** - `aa51499` (test)

**Plan metadata:** see final docs commit.

_Note: Task 2 is a test-only regression pin (no src changes) — a single `test(...)` commit. The TDD RED→GREEN cycle ran inside Task 2: the positive control went RED (it caught a real `tokenize.untokenize` adjacency bug where `db.commit()` became `db . commit ( )`), the stripper was fixed to preserve adjacency, then the static scan caught a real scoping issue (vibemix's own sqlite-vec store) which was correctly excluded — final GREEN._

## Files Created/Modified

- `src/vibemix/state/event.py` - Added `KEY_CLASH: 7` + `TRANSITION_OPPORTUNITY: 5` to `EVENT_PRIORITY` with rationale comments (plumbing-only block).
- `src/vibemix/audio/constants.py` - Added `KEY_CLASH: 28.0` + `TRANSITION_OPPORTUNITY: 20.0` to `MIN_EVENT_GAP_PER_TYPE` honoring the one-line-why convention.
- `tests/state/test_event_priority.py` - Per-type asserts (`Event(type="KEY_CLASH").priority==7`, `...="TRANSITION_OPPORTUNITY").priority==5`) + map-constant asserts.
- `tests/audio/test_constants.py` - Added both keys to the exact-keyset assert + the two gap-value asserts.
- `tests/repo/test_repo_scrub.py` - `test_deck_readonly` (two-tier tokenize-stripped scan), `test_deck_readonly_detector_catches_a_write_pattern` (positive control), `test_deck_path_sqlcipher_dormant` (subprocess dormancy), plus the `_strip_comments_and_docstrings` / `_src_python_files` / `_is_deck_path` helpers.

## Decisions Made

- **tokenize over literal `grep -v '^#'`**: The plan asked for `grep -v '^#'` comment-stripping "so header prose cannot self-invalidate the gate." But the actual banned strings (`Rekordbox6Database`, `pyrekordbox.db6`) live in **docstrings** (`library/rekordbox.py:14-18`, `library/__init__.py:4`), not `#`-comments — a bare line grep would leave them in place and falsely trip the gate. Tokenize-based stripping (removes COMMENT + STRING tokens) is the robust generalization that honors the intent: it hides prose that *documents* the ban while still flagging a real write statement. A line-based fallback is kept for un-tokenizable files (never silently passes).
- **Two-tier scope**: `Rekordbox6Database` / `pyrekordbox.db6` are banned repo-wide (no legitimate use anywhere). `.commit()` / `executescript()` / sqlite write-mode URIs are banned in the **deck path only** — vibemix's own sqlite-vec embedding cache legitimately commits to its own DB, so a blanket `.commit(` ban would have produced false positives in `library/embed.py`, `index_sqlite_vec.py`, `search.py`. DECK-05 is specifically about the USER's DJ collection (the `master.db` landmine, Risk 4), so the deck-path scope is the correct boundary.

## Deviations from Plan

None affecting scope. Two implementation refinements made within the plan's stated intent (both documented above):

1. **[Within plan intent] tokenize-stripping instead of literal `grep -v '^#'`** — the plan's stated *goal* ("header prose cannot self-invalidate the gate") could not be met by line-based `#`-stripping because the gate documentation lives in docstrings. Tokenize is the faithful generalization.
2. **[Within plan intent] write-pattern scope narrowed to the deck path** — a repo-wide `.commit(` ban would false-positive on vibemix's own internal store; DECK-05's boundary is the user's DJ collection. The positive control + the SQLCipher-class repo-wide ban preserve the hard guarantee.

No src files were modified in Task 2 (test-only regression pin, as the plan required). No firing/detection logic added. No unrelated in-flight WIP files swept in (strict per-file staging throughout).

## Issues Encountered

- **`tokenize.untokenize` token adjacency**: The first stripper joined tokens with spaces, turning `db.commit()` into `db . commit ( )` so the `.commit(` substring no longer matched. The positive-control test caught this immediately (genuine TDD RED). Fixed by reconstructing source via `tokenize.untokenize` on the kept tokens (STRING tokens replaced with `""` to preserve positions), which preserves the original adjacency so substring patterns match real write calls.

## Verification

- `tests/state/test_event_priority.py tests/audio/test_constants.py tests/repo/test_repo_scrub.py tests/library/test_rekordbox.py` — **41 passed** (venv 3.12).
- Acceptance shell checks all exit 0: `EVENT_PRIORITY['KEY_CLASH']==7 and ['TRANSITION_OPPORTUNITY']==5`; `MIN_EVENT_GAP_PER_TYPE['KEY_CLASH']==28.0 and ['TRANSITION_OPPORTUNITY']==20.0`; `Event(type='KEY_CLASH').priority==7`.
- `grep -c KEY_CLASH\|TRANSITION_OPPORTUNITY src/vibemix/state/event_detector.py` → **0** (no firing branch; Phase 60 owns it).
- Existing `test_no_sqlcipher_module_imported_after_load` still passes (deck path adds no sqlcipher import).
- **Full suite: 7 failed, 3952 passed, 26 skipped** — the SAME 7 pre-existing `live-tuning-or-brain` WIP failures documented in `deferred-items.md` (anti-slop wiring + cut_release ×3 + README feature-matrix ×2 + main smoke), unchanged count. Passing count rose 3947 → 3952 from this plan's 5 new tests. No new failures, no golden flips. Re-confirmed in `deferred-items.md`.

## Next Phase Readiness

- DECK-04 (event-type plumbing) + DECK-05 (read-only repo test) satisfied. Phase 60's harmonic-clash detector branches now have non-zero-priority slots to plug into; the read-only pin will fail loudly if the 59-04 poller or any future commit introduces a DJ-DB write path.
- Remaining in Phase 59: 59-04 (deck poller + single-writer `_tick_once` registry-write site + `evidence_line` deck block) and 59-05 (Gemini-vision deck-badge eval). Phase 60 (harmonic firing) stays gated behind the rest of Phase 59.
- No blockers engineering-side.

## Self-Check: PASSED

- All 5 modified files present on disk (event.py, constants.py, test_event_priority.py, test_constants.py, test_repo_scrub.py) + SUMMARY.md.
- Both task commits present in git history: `8040be7` (feat — event types), `aa51499` (test — DECK-05).

---
*Phase: 59-full-deck-awareness-grounding*
*Completed: 2026-05-21*
