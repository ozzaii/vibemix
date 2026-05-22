---
phase: 65-memory-retrieval-seam
plan: 01
subsystem: testing
tags: [pytest, tdd-red, citation-linter, anti-slop, memory-retrieval, schema-mirror]

# Dependency graph
requires:
  - phase: 64-session-ingest
    provides: vibemix.memory.ingest + MemoryStore.query_topk(exclude_session=) read seam + Record carrier
  - phase: 59-deck-harmonic
    provides: EVIDENCE_SOURCES / _SOURCE_ALT schema-mirror + key-source existence-only linter precedent
provides:
  - "RED-first Wave-0 test scaffold pinning the entire Phase 65 retrieval-seam contract"
  - "tests/memory/test_retrieval.py — 5 RED unit tests for the not-yet-built MemoryRecall service"
  - "tests/agent/test_dj_cohost_linter.py::test_fabricated_recall_strips_turn — THE HEADLINE poisoning gate"
  - "tests/coach/test_citation_linter.py::test_recall_existence_only_valid — registered recall passes"
  - "tests/state/test_coach.py — 2 RED recall-block tests; silent golden preserved byte-identical"
  - "Lockstep source/grammar count tests updated 8->9 (the anti-half-edit poisoning guard)"
affects: [65-02-evidence-vocabulary, 65-03-memory-recall-service, 65-04-coach-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RED-first Wave-0 scaffold: every NEW test + every UPDATED lockstep count-test authored before any impl"
    - "Synthetic-cosine seeding: _aligned(query, target_cos) crafts vectors above/below the 0.7 floor with no live API"
    - "Poisoning test rides a VALID [ev:] alongside the fabricated [recall:] so only the unregistered recall can strip the turn"

key-files:
  created:
    - tests/memory/test_retrieval.py
  modified:
    - tests/coach/test_citation_linter.py
    - tests/state/test_coach.py
    - tests/agent/test_dj_cohost_linter.py
    - tests/state/test_evidence_registry.py
    - tests/prompts/test_matrix.py

key-decisions:
  - "Headline poisoning test asserts whole-turn strip via invalid_atoms (id named in missing), riding a valid [ev:] so it is RED today for the right reason — the poisoning hole made visible — not a same-now-as-later smoke test"
  - "test_retrieval.py uses a module-level import RED (ModuleNotFoundError) mirroring the shipped test_ingest.py Wave-0 shape — the canonical not-yet-built signal in this repo"
  - "Did NOT mark RECALL-01..04 requirements complete — RED-first plan; impl lands in 65-02/03/04"

patterns-established:
  - "Schema-mirror lockstep tests go RED in pairs (sites 1+2) so a half-edit cannot silently open the poisoning hole"
  - "evidence_line recall block gated identically to decks[…]/registry_snapshot (falsy gate -> byte-identical when empty)"

requirements-completed: []  # RED-first — RECALL-01..04 are PINNED here, COMPLETED in 65-02/03/04

# Metrics
duration: 18min
completed: 2026-05-22
---

# Phase 65 Plan 01: Memory Retrieval Seam — Wave-0 RED Scaffold Summary

**RED-first test scaffold pinning the milestone's anti-slop release gate: a fabricated `[recall:<unregistered>]` must strip the whole turn (headline RED), plus the MemoryRecall service contract, the recall-block coach golden, and the 8->9 schema-mirror lockstep tests — all authored before any implementation lands.**

## Performance

- **Duration:** ~18 min
- **Completed:** 2026-05-22
- **Tasks:** 2
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments
- **THE HEADLINE poisoning RED** — `test_fabricated_recall_strips_turn`: a fabricated `[recall:20260520-2200:999]` riding alongside a genuinely valid `[ev:KICK_SWAP@45.2]` must strip the WHOLE turn. RED today because recall is unparsed, so the fabricated callback rides through un-stripped — the exact poisoning the milestone exists to kill, made visible. Goes green at 65-02 via `invalid_atoms` with the fabricated id in `missing`.
- **MemoryRecall unit contract** — 5 RED tests (`tests/memory/test_retrieval.py`): heartbeat-never-retrieves (+ zero embed), below-floor injects nothing, current-session excluded, deadline-miss clear() injects nothing, embed-called-once. Synthetic-cosine seeding (`_aligned`) lands records above/below the 0.7 floor with no live API.
- **Recall-block coach goldens** — `test_evidence_line_recall_block_present` (PAST-TENSE "FROM A PAST SESSION (not happening now):" fence + both `[recall:<id>]` tokens, subordinate ordering) + `test_evidence_line_recall_empty_no_block` (`[]` == no-kwarg byte-identical). The `:47` silent-state golden left UNTOUCHED and confirmed green at baseline.
- **Registered-recall linter pass** — `test_recall_existence_only_valid`: a registered `[recall:<id>]` validates via the existence-only branch (RED until 65-02).
- **Lockstep 8->9** — `test_evidence_11_sources_constant_locked_GROUND02` (+`recall`) and `test_o_citation_grammar_block...` (+`[recall:`). RED until 65-02 lands sites 1+2 together — the anti-half-edit poisoning guard.

## Task Commits

1. **Task 1: MemoryRecall RED unit tests + extended linter test** — `8882104` (test)
2. **Task 2: RED coach goldens + headline poisoning RED + lockstep 8->9** — `f225ec6` (test)

## Files Created/Modified
- `tests/memory/test_retrieval.py` (created) — 5 RED MemoryRecall unit tests; mirrors test_ingest.py fixtures (`_SpyEmbedder`, synthetic L2-normalized vectors, `MemoryStore(prefer_sqlite_vec=False)`)
- `tests/coach/test_citation_linter.py` — `test_recall_existence_only_valid` (registered recall passes the existence-only branch)
- `tests/state/test_coach.py` — 2 recall-block tests; silent golden preserved
- `tests/agent/test_dj_cohost_linter.py` — `test_fabricated_recall_strips_turn` (headline poisoning gate)
- `tests/state/test_evidence_registry.py` — sources-count lockstep 8->9 (+`recall`)
- `tests/prompts/test_matrix.py` — grammar-forms lockstep 8->9 (+`[recall:`)

## Decisions Made
- **Strengthened the headline poisoning test beyond a smoke test.** Initial draft (empty registry, recall-only reaction) passed today because the turn strips on `no_citations` regardless. Reworked so the reaction carries a VALID `[ev:KICK_SWAP@45.2]` alongside the fabricated `[recall:]` — now the only thing that can strip the turn is the linter recognizing the unregistered recall atom. RED today (recall unparsed -> turn EMITS), green at 65-02. This makes it RED for the right reason and a genuine guard against the half-edit poisoning hole.
- **No-extraction / no-live-path static gates need no edit** — `tests/memory/test_no_extraction.py` and `test_no_live_path_import.py` already `rglob("memory/*.py")` (VERIFIED), so they auto-cover the future `retrieval.py` the moment 65-03 lands it. Documented in the test module docstring; no edit made.
- **Did NOT mark RECALL-01..04 complete** — RED-first plan; the requirements are PINNED here and discharged in 65-02/03/04.

## Deviations from Plan

None - plan executed exactly as written. (The poisoning-test strengthening is within the plan's explicit instruction to "make it genuinely assert whole-turn strip on an UNREGISTERED recall id, not just a smoke test.")

## Issues Encountered
- The targeted suite run is `Interrupted` by the `test_retrieval.py` module-level import RED (ModuleNotFoundError) unless `--continue-on-collection-errors` is passed. This is the expected Wave-0 signal (identical to how `test_ingest.py` was RED in Phase 64 Wave-0), not a defect. Downstream verify runs should pass that flag or `--ignore tests/memory/test_retrieval.py` until 65-03 lands the module.

## Baseline Verification
Full suite (`pytest -q --continue-on-collection-errors`): **14 failed + 1 error, 4122 passed, 26 skipped.**
- **6 failed + 1 error = this plan's intentional RED set** (test_retrieval module error; test_fabricated_recall_strips_turn; test_recall_existence_only_valid; test_evidence_line_recall_block_present; test_evidence_line_recall_empty_no_block; test_evidence_11_sources_constant_locked_GROUND02; test_o_citation_grammar_block...).
- **8 failed = the known `live-tuning-or-brain` WIP baseline** (untouched files: test_main_anti_slop_wiring, repo/test_cut_release_invokes_bravoh_server, repo/test_gate_42_hybrid_in_force, repo/test_readme_feature_matrix_sync ×2, scripts/test_cut_release_preflight ×2, test_main_smoke::test_smoke_08).
- **Zero NEW collateral failures.** The `:47` silent-state cold golden is green.

## Threat Surface
No new threat surface introduced (test-only plan). The headline poisoning guard (T-65-01) and the schema-mirror half-edit guard (T-65-02) are now AUTHORED as RED tests per the plan's `<threat_model>` — they discharge structurally in 65-02 + 65-04.

## Next Phase Readiness
- **65-02** (evidence vocabulary): turn `test_evidence_11_sources_constant...`, `test_o_citation_grammar_block...`, `test_recall_existence_only_valid`, and `test_fabricated_recall_strips_turn` green by adding `recall` to EVIDENCE_SOURCES + `_SOURCE_ALT` (sites 1+2 together) + the `[recall:` grammar form (site 3). MUST land sites 1+2 together — a half-edit leaves the poisoning RED un-greened.
- **65-03** (MemoryRecall service): create `src/vibemix/memory/retrieval.py` to turn the 5 `test_retrieval.py` tests green (mirrors `library/grounding.py::Grounding`).
- **65-04** (coach wiring): add `recall_moments` kwarg + the gated PAST-TENSE block to `evidence_line` to turn the 2 coach tests green; wire registration so the fabricated-recall strip is fully end-to-end.

## Self-Check: PASSED

All 7 files present on disk; both task commits (`8882104`, `f225ec6`) present in git history.

---
*Phase: 65-memory-retrieval-seam*
*Completed: 2026-05-22*
