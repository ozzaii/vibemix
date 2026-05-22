---
phase: 65-memory-retrieval-seam
plan: 02
subsystem: state / prompts (citation-grounding vocabulary)
tags: [recall, evidence-source, citation-grammar, anti-slop, schema-mirror, RECALL-01]
requires:
  - "65-01 RED scaffold (lockstep 8->9 tests, headline poisoning RED, registered-recall RED)"
provides:
  - "recall registered as the 9th existence-only evidence source across schema-mirror sites 1-3"
  - "parse_citations now matches [recall:<record_id>] — fabricated recalls are parseable -> strippable"
  - "CITATION_GRAMMAR_BLOCK teaches Gemini the [recall:<record_id>] form"
affects:
  - "65-03 (MemoryRecall service — consumes the recall vocabulary)"
  - "65-04 (AICoach.evidence_line recall_moments kwarg — gated recall block)"
  - "66 (recall chip on dj_cohost citation strip — site 4, NOT this plan)"
tech-stack:
  added: []  # zero net-new deps — pure vocabulary edit (RECALL-01 is data-driven)
  patterns:
    - "existence-only evidence source (in EVIDENCE_SOURCES, out of _TIME_KEYED_SOURCES) — mirrors Phase 59 `key`"
    - "silent-poisoning-hole guard: sites 1+2 land in ONE commit"
key-files:
  created: []
  modified:
    - "src/vibemix/state/evidence_registry.py — recall in EVIDENCE_SOURCES (site 1) + _SOURCE_ALT regex (site 2) + EBNF docstring"
    - "src/vibemix/prompts/matrix.py — [recall:<record_id>] form in CITATION_GRAMMAR_BLOCK (site 3) + lock-step comment 8->9"
decisions:
  - "Sites 1+2 committed together (2016e36) — the silent-poisoning-hole pair, never split"
  - "recall kept OUT of _TIME_KEYED_SOURCES and OUT of memory/ingest.py:79 (retrieval-time, not ingest-time); asymmetry guarded by a code comment so a future maintainer does not 'fix' it"
  - "citation_linter.py byte-unchanged — recall joins the existence-only branch purely by registry membership (data-driven, zero new logic)"
requirements-completed: [RECALL-01]
metrics:
  duration: ~12min
  completed: 2026-05-22
---

# Phase 65 Plan 02: Memory Retrieval Seam — `recall` Evidence-Source Vocabulary Summary

**Added the existence-only `recall` evidence source across schema-mirror sites 1-3 (EVIDENCE_SOURCES frozenset, `_SOURCE_ALT` regex, `CITATION_GRAMMAR_BLOCK`) with ZERO new linter code — closing the silent poisoning hole so a fabricated `[recall:<id>]` is now parseable and therefore strippable by the unchanged CitationLinter existence-only branch (RECALL-01).**

## What Landed

- **Sites 1+2 (one commit, `2016e36`)** — `recall` added to `EVIDENCE_SOURCES` (8->9, existence-only) AND appended to the `_SOURCE_ALT` regex alternation in the SAME commit. This is the silent-poisoning-hole pair: had `recall` joined the frozenset without the regex, a fabricated `[recall:…]` would never be matched by `parse_citations`, never stripped, and would ride through un-validated. The EBNF docstring `source` rule and a new `recall-body` line were updated; `_INNER_ATOM` left UNCHANGED (the `recall:20260520-2200:7` body's inner colon survives as `record_id`, exactly like `key:A:8A`).
- **Site 3 (`977c014`)** — `[recall:<record_id>]  past-moment reference, e.g. [recall:20260520-2200:7]` appended to `CITATION_GRAMMAR_BLOCK`; lock-step comment bumped 8->9. Existence-only tone (a reference to a past moment, not a live action — parallels `track`/`tend`, not `ev`/`key`).
- **recall kept OUT of `_TIME_KEYED_SOURCES`** (would force `@t` parse, breaking existence-only) **and OUT of `memory/ingest.py:79`** (retrieval-time vs ingest-time asymmetry, guarded by a code comment).
- **`citation_linter.py` byte-unchanged** — `grep -n recall src/vibemix/coach/citation_linter.py` returns nothing. recall validates through the existing existence-only branch purely by registry membership.

## Tasks & Commits

1. **Task 1: recall -> EVIDENCE_SOURCES + _SOURCE_ALT + EBNF doc (sites 1+2, one commit)** — `2016e36` (feat)
2. **Task 2: [recall:<record_id>] form -> CITATION_GRAMMAR_BLOCK (site 3)** — `977c014` (feat)

## Verification Results

- `tests/state/test_evidence_registry.py -k 'sources_constant or grammar_coherence'` — **2 passed** (9 sources, recall matchable + writable)
- `tests/prompts/test_matrix.py -k citation_grammar_block` — **1 passed** (9 forms, `[recall:` present)
- `test_recall_existence_only_valid` (tests/coach/test_citation_linter.py) — **GREEN**
- `tests/agent tests/coach` full dirs — 395 passed, 1 pre-existing WIP failure (see below)
- `tests/state tests/prompts` full dirs — 911 passed, 2 known-RED (65-04 targets)
- Boundary greps: linter `recall` = none; ingest `_SOURCE_ALT` stays at 8 sources (no recall); dj_cohost (site 4) `recall` = none — all UNTOUCHED as required.

## Notable Outcome: headline poisoning test went GREEN here (earlier than 65-04)

`tests/agent/test_dj_cohost_linter.py::test_fabricated_recall_strips_turn` is **GREEN** after this plan. The plan anticipated it greening at 65-04 wiring, but the headline poisoning gate (fabricated `[recall:<unregistered>]` riding a valid `[ev:]` -> whole turn strips) only needs the **PARSE path**, which landed here: recall is now matchable via `_SOURCE_ALT`, so a fabricated unregistered id hits the existence-only branch -> missing from registry -> turn strips. 65-04's registration wiring is what makes *legitimate registered* recalls survive — not what makes fabricated ones strip. The silent poisoning hole is closed exactly as designed; this is a positive (earlier-than-planned) close of the milestone's existential anti-slop gate.

## Deviations from Plan

None — plan executed exactly as written. (The fabricated-recall test greening at 65-02 rather than 65-04 is a reframe of expectation, not a deviation: no extra edits were made; the parse path alone closes that gate.)

## Still-RED / Out-of-Scope (expected)

- `tests/memory/test_retrieval.py` — import-errors (ModuleNotFoundError `vibemix.memory.retrieval`); MemoryRecall module is **65-03**. Expected RED.
- `tests/state/test_coach.py::test_evidence_line_recall_block_present` + `::test_evidence_line_recall_empty_no_block` — `AICoach.evidence_line()` lacks the `recall_moments` kwarg; that wiring is **65-04**. Expected RED.
- `tests/coach/test_main_anti_slop_wiring.py::test_wire13_anti_slop_disabled_path_passes_none_kwargs` — pre-existing WIP failure in `src/vibemix/__main__.py` (conditional `CitationLinter()` construction). NOT touched by this plan (out of scope; part of the known WIP baseline). Logged here, not fixed.

## Self-Check: PASSED
- src/vibemix/state/evidence_registry.py — FOUND, contains recall (sites 1+2)
- src/vibemix/prompts/matrix.py — FOUND, contains `[recall:` (site 3)
- Commit 2016e36 — FOUND
- Commit 977c014 — FOUND
