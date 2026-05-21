---
phase: 59-full-deck-awareness-grounding
plan: 02
subsystem: anti-slop
tags: [citation, evidence-source, linter, harmonics, camelot, grounding, anti-slop]

# Dependency graph
requires:
  - phase: 59-01 (deck-state + harmonics foundation)
    provides: DeckTrack.camelot via harmonics.to_camelot — the <camelot> a key: atom cites
  - phase: 18 (EvidenceRegistry grammar)
    provides: EVIDENCE_SOURCES / _SOURCE_ALT / parse_citations / EVIDENCE_CITATION_RE
  - phase: 20 (CitationLinter)
    provides: existence-only validation branch + _TIME_KEYED_SOURCES split
provides:
  - "Dedicated `key:` evidence source (8th member of EVIDENCE_SOURCES), body `<deck>:<camelot>`"
  - "Existence-only linter validation for key: (mirrors track:) — fabricated harmonic atoms stripped"
  - "CITATION_GRAMMAR_BLOCK teaches the LLM it can cite [key:A:8A] (touchpoint #4)"
  - "_build_citation_strip yields a key chip with a REGISTRY-derived timestamp (touchpoint #5)"
  - "All 5 schema-mirror touchpoints carry 'key' in lock-step"
affects: [phase-60-harmonic-feedback-confidence-gate, phase-61-coach-persona]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Existence-only evidence source (no @t) — mirror track:, stay OUT of _TIME_KEYED_SOURCES"
    - "Uncitable-by-construction: dedicated <deck>:<camelot> body so a hallucinated clash strips the turn"
    - "Source-aware chip-verb derivation; chip timestamp always sourced from the registry, never the body"

key-files:
  created: []
  modified:
    - src/vibemix/state/evidence_registry.py
    - src/vibemix/coach/citation_linter.py
    - src/vibemix/prompts/matrix.py
    - src/vibemix/agent/dj_cohost.py
    - tests/state/test_evidence_registry.py
    - tests/coach/test_citation_linter.py
    - tests/prompts/test_matrix.py
    - tests/agent/test_citation_strip_emit.py

key-decisions:
  - "Dedicated `key:` source over `mix:` reuse (CONTEXT-locked): the <deck>:<camelot> body makes a fabricated 12B clash uncitable-by-construction; mix: reuse would let a bare deck_A_key=... presence pass."
  - "key: is EXISTENCE-ONLY (mirrors track:) — added to EVIDENCE_SOURCES + _SOURCE_ALT only; deliberately NOT in _TIME_KEYED_SOURCES; ZERO _validate_atom logic change (existing existence-only branch handles it by exact-body presence)."
  - "key chip verb is a fixed letters-only 'key' label — camelot codes carry digits which would violate the locked verb-format pin; the deck:camelot detail rides in event_id for the deep-link."

patterns-established:
  - "Schema-mirror lock-step: any new evidence source moves all 5 touchpoints together (frozenset, regex, EBNF docstring, CITATION_GRAMMAR_BLOCK, citation-strip whitelist)."
  - "Anti-hallucination chip contract preserved: timestamp_s sourced from the registry observation, NEVER parsed from the citation body."

requirements-completed: [DECK-03]

# Metrics
duration: 9min
completed: 2026-05-21
---

# Phase 59 Plan 02: Citable `key:` Harmonic Evidence Source Summary

**Added a dedicated existence-only `key:` evidence source (body `<deck>:<camelot>`, e.g. `[key:A:8A]`) across all 5 schema-mirror touchpoints so the existing CitationLinter strips any fabricated harmonic clash — the un-cited-harmonic-feedback retrofit (Risk 2) lands BEFORE any Phase 60 harmonic prompt text.**

## Performance

- **Duration:** ~9 min
- **Started:** 2026-05-21T13:00:56Z
- **Completed:** 2026-05-21T13:09:43Z
- **Tasks:** 2 (Task 1 TDD: RED → GREEN)
- **Files modified:** 8 (4 source + 4 test)

## Accomplishments
- `key` is the 8th member of `EVIDENCE_SOURCES`; `parse_citations('[key:A:8A]') == [('key', 'A:8A')]` (no parser change — partition on first colon keeps the inner `A:8A` body).
- The CitationLinter STRIPS a response citing a fabricated `[key:A:12B]` (never written by the poller) and ACCEPTS a registered `[key:A:8A]` — purely by `key` being in `EVIDENCE_SOURCES` and absent from `_TIME_KEYED_SOURCES`. Zero `_validate_atom` logic change.
- The LLM is taught it can cite `[key:<deck>:<camelot>]` via `CITATION_GRAMMAR_BLOCK` (touchpoint #4).
- `_build_citation_strip` emits a `key` chip whose `timestamp_s` comes from the registry observation, not the citation body (touchpoint #5).
- The `screen_jpeg = None` vision killswitch is untouched (count-stable grep returns 1). No harmonic firing/detection logic added — that is held back for Phase 60.

## Task Commits

1. **Task 1 (RED): failing tests for citable key: source** — `416b504` (test)
2. **Task 1 (GREEN): add key: source + existence-only linter rule** — `4bb3c7e` (feat)
3. **Task 2: teach prompt + citation-strip the key: form (touchpoints 4+5)** — `c19c691` (feat)

**Plan metadata:** (final docs commit — this SUMMARY + STATE + ROADMAP + REQUIREMENTS + deferred-items)

_Task 1 followed the TDD RED→GREEN cycle; no REFACTOR commit needed (changes were minimal)._

## Files Created/Modified
- `src/vibemix/state/evidence_registry.py` — `key` added to `EVIDENCE_SOURCES` frozenset (now 8) + `_SOURCE_ALT` regex alternation + EBNF docstring (`key-body := <deck> ':' <camelot>`). `_INNER_ATOM` / `parse_citations` UNCHANGED.
- `src/vibemix/coach/citation_linter.py` — comments document that `key` joins the existence-only set by being in `EVIDENCE_SOURCES` and ABSENT from `_TIME_KEYED_SOURCES`. No `_validate_atom` body-logic change.
- `src/vibemix/prompts/matrix.py` — `CITATION_GRAMMAR_BLOCK` gains the `[key:<deck>:<camelot>]` Form line; lock-step comment updated 7→8 forms.
- `src/vibemix/agent/dj_cohost.py` — `_build_citation_strip` allow-list gains `"key"`; source-aware verb derivation (fixed `"key"` label); chip timestamp sourced from registry. Killswitch untouched.
- `tests/state/test_evidence_registry.py` — count tests updated to 8 forms; new `key:` frozenset + parse-split tests.
- `tests/coach/test_citation_linter.py` — `key` existence-only accept + fabricated-`A:12B` strip + not-time-keyed tests.
- `tests/prompts/test_matrix.py` — Test O updated to assert all 8 forms incl. `[key:<deck>:<camelot>]`.
- `tests/agent/test_citation_strip_emit.py` — `key` chip w/ registry timestamp + fabricated-key no-chip tests.

## Decisions Made
- **Dedicated `key:` source, not `mix:` reuse** (CONTEXT-locked, resolves the ARCHITECTURE↔PITFALLS divergence): the `<deck>:<camelot>` body makes a hallucinated `12B` clash uncitable-by-construction; `mix:` reuse would let a bare `deck_A_key=...` presence slip a false clash through.
- **Existence-only (mirror `track:`)** — `key` deliberately kept OUT of `_TIME_KEYED_SOURCES`; a bare `[key:A:8A]` (no `@t`) validates by presence. No `_validate_atom` change required (verified by logic trace + diff-grep showing zero logic-line edits).
- **`key` chip verb = fixed `"key"` label** — camelot codes carry digits (`8A`) which would break the locked verb-format pin (`^[a-z]+( [a-z]+){0,2}$`); the deck:camelot detail lives in `event_id` for the click→debrief deep-link.

## Deviations from Plan
None - plan executed exactly as written. The two count-locked tests (`test_evidence_07`, `test_evidence_11`) and the prompt Test O were updated to the new 8-source grammar — this is the expected lock-step schema-mirror move the plan calls for, not a deviation.

## Issues Encountered
- Bare `python3` on this machine resolves to Homebrew Python 3.14 with an incompatible `google.genai` (`ImportError: ServiceTier`). Switched to `source .venv/bin/activate` (Python 3.12) per CLAUDE.md's authoritative test command. Agent-side tests (`test_citation_strip_emit.py`) only collect under the venv.

## Threat Model Coverage
- **T-59-02-01 (Spoofing — fabricated clash):** mitigated — dedicated `key:` source + existence-only strip; a fabricated `[key:A:12B]` strips the whole turn (test-pinned).
- **T-59-02-02 (Tampering — body-driven chip timestamp):** mitigated — chip `timestamp_s` sourced from the registry, never the citation body (test-pinned).
- **T-59-02-03 (Spoofing — re-enabling screen Part):** mitigated — `screen_jpeg = None` killswitch untouched, count-stable grep returns 1.

## Full-Suite Result
`PYTHONPATH=src python3 -m pytest -q` (venv): **7 failed, 3947 passed, 26 skipped**. The 7 failures are the SAME pre-existing `live-tuning-or-brain` WIP failures documented in `deferred-items.md` from Plan 59-01 (README feature-matrix phases 55–58, cut-release tag-regex/preflight churn, `__main__.py` anti-slop + cache wiring) — unchanged count, none reference the citation/grammar surface this plan touched (grep-verified empty). No new failures; no golden flips on any citation/prompt/coach test.

## Next Phase Readiness
- DECK-03 satisfied. The citable `key:` source is the un-cited-harmonic-feedback retrofit landed BEFORE any harmonic prompt — Phase 60 (Harmonic-Feedback Confidence Gate) can now ground `KEY_CLASH` narration on `[key:A:8A]` citations the linter will validate response-level.
- No firing/detection logic added (held for Phase 60); event-type plumbing (`KEY_CLASH`/`TRANSITION_OPPORTUNITY` priorities + cooldowns) and the registry write-site wiring belong to later 59-plans / Phase 60.

## Self-Check: PASSED

- FOUND: `.planning/phases/59-full-deck-awareness-grounding/59-02-SUMMARY.md`
- FOUND commit: `416b504` (test RED)
- FOUND commit: `4bb3c7e` (feat GREEN Task 1)
- FOUND commit: `c19c691` (feat Task 2)

---
*Phase: 59-full-deck-awareness-grounding*
*Completed: 2026-05-21*
