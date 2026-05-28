---
phase: 96-course-3-play-mode
plan: 02
subsystem: state + prompts + agent (4-site atomic mirror for [cue:] evidence source)
tags: [cue-evidence-source, 4-site-mirror, atomic-landing, schema-mirror-lock, evidence-sources-11, invariant-2-bind]
requirements:
  - CURR-3.07
provides:
  - src/vibemix/state/evidence_registry.py:EVIDENCE_SOURCES (now 11 entries; "cue" added)
  - src/vibemix/state/evidence_registry.py:_SOURCE_ALT (regex alternation; +|cue)
  - src/vibemix/state/evidence_registry.py:EBNF docstring (cue-body grammar line)
  - src/vibemix/prompts/matrix.py:CITATION_GRAMMAR_BLOCK ([cue:<anchor_id>] form documented)
  - src/vibemix/agent/dj_cohost.py:_build_citation_strip (cue allow-list + verb branch)
  - tests/learn/test_cue_citation_schema_mirror.py (8 mirror-lock tests)
requires:
  - 96-01 (CURR-3.07 already in REQUIREMENTS.md; AST gates + runtime confidence gate)
  - existing P93 [exemplar:] mirror (defense-in-depth precedent)
affects:
  - downstream Plan 96-03 (proactive lens emits [cue:<anchor_id>] cites; the linter will validate them)
  - existing P93 exemplar mirror test (site 4 regex generalized; still pins exemplar)
key-files:
  created:
    - tests/learn/test_cue_citation_schema_mirror.py
  modified:
    - src/vibemix/state/evidence_registry.py
    - src/vibemix/prompts/matrix.py
    - src/vibemix/agent/dj_cohost.py
    - tests/state/test_evidence_registry.py (GROUND-02 constant lock: 10 → 11)
    - tests/prompts/test_matrix.py (Test O extended to [cue: + [exemplar:)
    - tests/learn/test_exemplar_citation_schema_mirror.py (site 4 regex generalized)
tech-stack:
  added: []
  patterns:
    - atomic 4-site mirror — all sites land in ONE commit (silent-poisoning hole prevention)
    - retrieval-time-only source (joins existence-only set via being IN EVIDENCE_SOURCES + ABSENT from _TIME_KEYED_SOURCES)
    - asymmetry preserved (intentional) — memory/ingest.py extractor stays at 8 sources; cue is retrieval-time, never ingest-time
decisions:
  - "Plan 96-02 generalized the P93 exemplar mirror test's site-4 regex from a closed 6-tuple ('ev'..'exemplar') to an open-ended prefix match — accommodates the locked source order ('ev'..'exemplar') with the new 'cue' tail without requiring a regex rewrite each time a source is added."
  - "Test O in tests/prompts/test_matrix.py was extended to assert BOTH '[cue:' (P96) AND '[exemplar:' (P93). The P93 ship had landed exemplar in CITATION_GRAMMAR_BLOCK but left Test O at 9 prefixes — this fix retroactively pins both."
  - "Verb derivation for [cue:] mirrors [exemplar:]/[recall:]/[key:] — a fixed letters-only 'cue' label. Anchor-id strings could leak detector-internal values to the UI surface if used as the verb."
metrics:
  duration: ~25 minutes (~10 min of which was sibling-session conflict recovery)
  completed: 2026-05-28
---

# Phase 96 Plan 02: Atomic 4-Site Mirror for [cue:] Evidence Source Summary

Land the `[cue:<anchor_id>]` citation source via the locked 4-site atomic mirror pattern. This is the proof-of-grounding source for Course 3 proactive count-ins — when the tutor narrates "breakdown in 16 beats — get ready to bring in track 2", it must cite `[cue:<anchor_id>]` against a CueAnchor / phrase-boundary observation already in the EvidenceRegistry. A fabricated `[cue:bogus]` strips the whole turn via the existing Phase 20 linter.

## What Shipped

### Site 1 — `EVIDENCE_SOURCES` frozenset (state/evidence_registry.py)

Count flipped 10 → 11. Added `"cue"` to the frozenset + comment block explaining the new source semantics (CueAnchor / phrase-boundary reference, body = `<anchor_id>`, existence-only retrieval-time, mirrors `key`/`track`/`recall`/`exemplar` posture). Also updated the SCHEMA-MIRROR note that lists the 4 lock-step surfaces.

### Site 2 — `_SOURCE_ALT` regex alternation (state/evidence_registry.py)

Appended `|cue` tail. Updated the silent-poisoning-hole comment block to name `cue` alongside `recall`/`exemplar` (all three are the same situation: must join in the SAME commit as the frozenset). Updated the EBNF docstring with a `cue-body := <anchor_id>` line. Updated the "Matches the N single-citation forms" count comment 10 → 11.

### Site 3 — `CITATION_GRAMMAR_BLOCK` (prompts/matrix.py)

Added the `[cue:<anchor_id>]      cue/phrase anchor reference, e.g. [cue:phrase_boundary@45.2]` line immediately after `[exemplar:]` (mirrors the lock-step source order). Updated the header comment "The 10 source forms" → "The 11 source forms" with the +`cue` Phase 96 / CURR-3.07 attribution.

### Site 4 — `_build_citation_strip` allow-list (agent/dj_cohost.py)

Added `"cue"` to the 6-tuple allow-list — now 7-tuple `("ev", "mix", "midi", "key", "recall", "exemplar", "cue")`. Added an `elif source == "cue":` verb-derivation branch mirroring the `exemplar`/`recall`/`key` precedents — fixed letters-only `"cue"` label that satisfies the locked verb-format regex `^[a-z]+( [a-z]+){0,2}$`. Comment block names Phase 96 / CURR-3.07 + the silent-poisoning-hole + defense-in-depth rationale.

### Mirror-Lock Test — `tests/learn/test_cue_citation_schema_mirror.py`

8 tests covering all 4 sites + regex round-trip + registry write/read + lock-step. Exactly mirrors the P93 `test_exemplar_citation_schema_mirror.py` shape.

### Evolved Existing Tests

1. **`tests/state/test_evidence_registry.py::test_evidence_11_sources_constant_locked_GROUND02`** — assertion body evolved from 10 sources to 11. Docstring updated to name Phase 96 / CURR-3.07.
2. **`tests/prompts/test_matrix.py::test_o_citation_grammar_block_contains_eight_source_forms_and_multi_cite`** — prefix list extended from 9 entries to 11 (`[cue:` + `[exemplar:`; the P93 ship had omitted `[exemplar:` from this test even though it landed in CITATION_GRAMMAR_BLOCK).
3. **`tests/learn/test_exemplar_citation_schema_mirror.py::test_site_4_citation_strip_allow_list_includes_exemplar`** — site 4 regex generalized from closed 6-tuple match to open-ended prefix match (`("ev"...exemplar"`); accommodates P96's 7th-entry addition without rewriting the regex.

## Atomic Single-Commit Landing

All 4 mirror sites + the new mirror-lock test + the 3 evolved existing tests landed in ONE commit (`750d8cf8`). The atomicity is critical — if any site landed alone, the silent-poisoning hole would open until the next commit lands.

## Verification

```
tests/learn/test_cue_citation_schema_mirror.py        8 passed
tests/state/test_evidence_registry.py + sibling all green
tests/prompts/test_matrix.py + sibling all green
tests/agent/test_dj_cohost_linter.py all green
tests/coach/test_citation_linter.py all green
tests/learn/test_exemplar_citation_schema_mirror.py   6 passed (P93 mirror stays green)
tests/learn/test_runtime_invariants.py                2 passed (Invariant #1 stays green)
tests/learn/test_no_new_ws_port.py                    1 passed (Invariant #4 stays green)
tests/learn/test_no_speculative_phrase.py             4 passed (P96-01 AST gate stays green)
tests/learn/test_course3_uses_existing_coach.py       5 passed (P96-01 AST gate stays green)
tests/state/test_coach_course3_confidence_gate.py     9 passed (P96-01 runtime gate stays green)

Total: 188 passed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] P93 exemplar mirror test site-4 regex was closed-form**
- **Found during:** Task 1 first verify
- **Issue:** `tests/learn/test_exemplar_citation_schema_mirror.py::test_site_4_citation_strip_allow_list_includes_exemplar` had a regex hard-coded to match the EXACT 6-tuple shape `("ev", "mix", "midi", "key", "recall", "exemplar")`. When Plan 96-02 adds `"cue"` as the 7th entry, the regex no longer matches — failing the P93 lock instead of guarding it.
- **Fix:** Generalized the regex to an open-ended prefix match (`("ev"..."exemplar"`). The locked source order ("ev" → "mix" → ... → "exemplar") is still enforced; the regex now accommodates additional sources after exemplar without rewriting.
- **Files modified:** `tests/learn/test_exemplar_citation_schema_mirror.py`
- **Commit:** `750d8cf8` (atomic 4-site mirror commit)

**2. [Rule 2 — Missing Critical] Test O in tests/prompts/test_matrix.py missed `[exemplar:` prefix**
- **Found during:** Task 1 verify
- **Issue:** Test O (the CITATION_GRAMMAR_BLOCK source-prefix list lock) had only 9 entries — P93 EXEMPLAR-05 ship added `[exemplar:` to the grammar block but didn't update Test O. The miss was silent because Test R (the dynamic-iteration variant) covered it.
- **Fix:** Extended Test O's prefix list from 9 entries to 11, adding both `[cue:` (P96) and `[exemplar:` (retroactive P93 fix). Both are now pinned at the static-list lock layer.
- **Files modified:** `tests/prompts/test_matrix.py`
- **Commit:** `750d8cf8`

**3. [Rule 3 — Blocking] Sibling-session staged work conflict on shared files**
- **Found during:** Pre-commit staging
- **Issue:** Sibling session(s) had pre-staged 28 unrelated files (stop-slop integration: `src/vibemix/agent/_streaming_pipe.py`, `src/vibemix/agent/dj_cohost.py`, `src/vibemix/prompts/matrix.py`, `src/vibemix/prompts/negative_dict.py`, `tests/agent/test_dj_cohost_*.py`, `tauri/ui/*` overlay work, etc.) BEFORE this session started. A naive `git add my_files && git commit` would have committed ALL of the staged work + my Phase 96 work together in one commit — violating concurrent-session-discipline.
- **Fix:** Used `git reset --soft HEAD~1` to undo the first (bad) commit, then `git reset HEAD` to unstage everything, then re-staged ONLY my Phase 96 files (named paths only) and committed cleanly. The sibling's worktree changes are preserved (saved to `/tmp/sibling_*.patch` and re-applied to the worktree); the sibling session can re-stage them with their own `git add`.
- **Outcome:** Commit `750d8cf8` is exactly 7 files / +195/-30 lines = Phase 96 mirror work only. The sibling's worktree state is restored as unstaged. No sibling work was lost; no sibling work was committed prematurely.

### KAAN-ACTION Parks

None added in 96-02.

## Commits

| # | Hash | Message |
| --- | --- | --- |
| 1 | `750d8cf8` | `feat(96-02): add [cue:] evidence source via atomic 4-site mirror` |

(A failed first attempt at `fcb4321b` was reset-undone; the index was cleaned and the atomic commit was re-issued cleanly.)

## Self-Check: PASSED

- All 4 mirror sites carry "cue" in lock-step.
- `EVIDENCE_SOURCES` is exactly 11 entries.
- `_SOURCE_ALT` regex includes "cue".
- `CITATION_GRAMMAR_BLOCK` documents `[cue:<anchor_id>]`.
- `_build_citation_strip` allow-list contains "cue" + verb branch.
- `tests/learn/test_cue_citation_schema_mirror.py` exists with 8 passing tests.
- GROUND-02 constant lock evolves to 11 sources; passes.
- P93 [exemplar:] mirror lock STAYS GREEN (defense in depth — each source has its own dedicated lock test).
- All P92+P93+P94+P95 invariant pins stay GREEN.
- Plan 96-01 AST gates + runtime confidence gate stay GREEN.
- Commit landed atomically (single commit, all 4 sites).
- Sibling worktree state restored cleanly (no loss).
