---
phase: 55-feedback-mode-citation-integrity
plan: 02
subsystem: coach / citation-integrity
tags: [citation-integrity, zero-orphan, hallucination-strip, debrief, linter, live-04, tests]
requires:
  - "src/vibemix/state/evidence_registry.py (EvidenceRegistry.write/register_library/has/snapshot, parse_citations)"
  - "src/vibemix/coach/citation_linter.py (CitationLinter.check + LintResult)"
  - "src/vibemix/coach/constants.py (LIVE_TOLERANCE_S=1.0, DEBRIEF_TOLERANCE_S=2.0)"
  - "tests/fixtures/hype_trace_genre1.jsonl (real session trace)"
provides:
  - "LIVE-04 zero-orphan replay regression on the real fixture (every grounded citation resolves; orphan count 0)"
  - "LIVE-04 hallucination-strip proof on a NON-empty real registry (injected ghost citation stripped, in .missing)"
  - "LIVE-04 live/debrief consistency regression (same orphan stripped both bands; grounded accepted both; live ⊆ debrief)"
affects: []
tech-stack:
  added: []
  patterns:
    - "Replay-from-real-fixture: build a REAL EvidenceRegistry from tests/fixtures/hype_trace_genre1.jsonl event lines"
    - "Duck-typed register_library via types.SimpleNamespace(tracks={...}) — no full RekordboxLibrary needed"
    - "Orphan = parsed atom that does NOT resolve via has() (time-keyed) or key-presence (existence-only)"
key-files:
  created:
    - "tests/coach/test_citation_zero_orphan_replay.py (290 lines, 7 tests)"
    - "tests/coach/test_citation_live_debrief_consistency.py (134 lines, 5 tests)"
  modified: []
decisions:
  - "No source modified — the emission-boundary grounding contract is already airtight at HEAD (55-RESEARCH Q0); this plan PINS it with replay regressions."
  - "Track ids registered in slug form (54830, 12345) not the fixture's full-title track field — the citation grammar body charset rejects whitespace, so [track:<id>] uses the spaceless form Gemini emits."
  - "The zero-orphan + hallucination-strip tests share one file (Task 1 + Task 2, two commits) since both build on the same fixture-registry helper."
metrics:
  duration: "~4 min"
  completed: "2026-05-21"
  tasks: 3
  files: 2
  tests_added: 12
---

# Phase 55 Plan 02: Zero-orphan replay + hallucination-strip + live/debrief consistency Summary

LIVE-04 made provable: 12 regressions pin that every citation a grounded reply emits against a registry built from the real session trace resolves to a real EvidenceRegistry entry (zero orphans), a deliberately-hallucinated citation is stripped on a NON-empty real registry, and the strip is consistent across live (±1.0s) and debrief (±2.0s) — one grammar, one registry, two tolerance bands. No source touched; the airtight emission contract was validated, not changed.

## What Was Built

Two test files, REAL primitives, no mocks, no network:

### `tests/coach/test_citation_zero_orphan_replay.py` (7 tests)

**Registry from the real fixture.** `_build_registry_from_fixture()` loads `tests/fixtures/hype_trace_genre1.jsonl`, filters `kind=="event"`, and writes `reg.write("ev", line["type"], float(line["t"]))` for every event line (157 lines → the real PHASE / MIX_MOVE / HEARTBEAT / LAYER_ARRIVAL / TRACK_CHANGE corpus). It registers track ids via `register_library` on a duck-typed `SimpleNamespace(tracks={...})`.

- **Task 1 (zero orphans):**
  - `test_registry_built_from_real_fixture_events` — registry `ev` keys mirror the fixture event types exactly; every registered track id is present.
  - `test_grounded_replies_are_valid_against_real_registry` — replies citing real fixture `@t` values (verbatim, 0.0s offset) + a registered track id → `valid is True`, `reason "valid"`. Includes a multi-citation reply.
  - `test_zero_orphans_across_grounded_replies` — for every parsed `(source, body)` atom, assert it resolves via `has()` (time-keyed) or key-presence (existence-only); orphan count is exactly **0**.
- **Task 2 (hallucination-strip on a NON-empty real registry):**
  - `test_hallucinated_time_keyed_citation_is_stripped` — `[ev:GHOST_EVENT@999.9]` → `valid False`, `reason "invalid_atoms"`, `("ev","GHOST_EVENT@999.9")` in `.missing`.
  - `test_hallucinated_track_citation_is_stripped` — `[track:NONEXISTENT_ID]` → `valid False`, orphan in `.missing`.
  - `test_mixed_reply_one_hallucinated_atom_strips_whole_reply` — one real + one ghost atom → **response-level binary strip**: whole reply `valid False`, ghost atom in `.missing`, real atom NOT.
  - `test_strip_holds_on_nonempty_registry_not_just_empty` — asserts `len(reg) > 0` (real evidence exists), yet the fabricated citation is still stripped. Stronger than `test_hype_anti_slop.py` which strips against an EMPTY registry.

### `tests/coach/test_citation_live_debrief_consistency.py` (5 tests)

One grammar (`EVIDENCE_CITATION_RE`), one registry (`reg.write("ev","PHASE",120.0)`), two bands:

- `test_tolerance_constants_are_one_and_two` — pins `LIVE_TOLERANCE_S==1.0`, `DEBRIEF_TOLERANCE_S==2.0`.
- `test_orphan_stripped_in_both_live_and_debrief` — `[ev:GHOST@500.0]` stripped in BOTH modes (`valid False`, `invalid_atoms`). No band widening rescues an unregistered key.
- `test_grounded_within_live_band_accepted_in_both` — `[ev:PHASE@120.5]` (0.5s off) valid in BOTH (live ⊆ debrief — debrief never strips what live accepts).
- `test_citation_in_debrief_only_band_is_live_invalid_debrief_valid` — `[ev:PHASE@121.5]` (1.5s off) INVALID in live (±1.0s), VALID in debrief (±2.0s) — the wider band is intentional + monotone.
- `test_unknown_mode_raises_value_error` — `mode="bogus"` raises `ValueError` (fail-loud).

## Orphan Definition & How Zero-Orphan Is Proven

An ORPHAN is a citation atom emitted by the model that does NOT resolve to a real EvidenceRegistry entry within the mode tolerance. "Zero orphans" is proven by: (a) building the registry from real session data, (b) constructing grounded replies whose every atom is a real fixture event `@t` or a registered track id, (c) asserting `CitationLinter.check(...).valid is True` AND every parsed atom independently resolves via `has(...)` / key-presence — orphan count 0. The hallucination case proves the inverse: a ghost id is provably an orphan (`valid False`, in `.missing`), so the linter strips it before it reaches the ear.

## The Hallucination-Strip Proof (stronger than the hype proof)

`tests/state/test_hype_anti_slop.py::test_spine_unbacked_citation_is_stripped` strips against an EMPTY registry. This plan strips against a NON-empty real registry (the full fixture corpus) — the harder, realistic case: real evidence EXISTS, yet a fabricated citation is still stripped. A single bad atom strips the whole reply (response-level binary), and the orphan surfaces in `LintResult.missing` for telemetry.

## Live/Debrief Consistency Property

One grammar, one registry, two tolerance bands. (1) Orphans stripped in both bands — band widening cannot rescue an unregistered key. (2) Inclusion is monotone: live's accept set ⊆ debrief's on the same data — debrief never strips what live accepts. (3) The debrief-only band (1.0s < |Δt| ≤ 2.0s) is intentional, documented by the 1.5s-off case.

## Deviations from Plan

None — plan executed exactly as written. ADD-tests-only; no source modified.

### Out-of-scope discovery (logged, NOT fixed)

The full default suite has **one pre-existing failure unrelated to this plan**: `tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file` fails because `eval/corpus/sessions/hard_tek_01/` carries only `genre.txt` + `source.txt` (no `events.jsonl`) — an uncommitted/untracked eval-corpus skeleton in the worktree checkout (created 2026-05-21 08:32), NOT in this plan's diff. The diversity gate (EVAL-03, commit 11d556d) requires every session dir to carry an `events.jsonl`; this corpus session was sourced but never populated. Logged to `deferred-items.md` per the SCOPE BOUNDARY rule; belongs to the eval-corpus sourcing workflow, not citation-integrity.

## Verification

- `tests/coach/test_citation_zero_orphan_replay.py tests/coach/test_citation_live_debrief_consistency.py` → **12 passed**.
- `tests/coach/test_citation_linter.py tests/debrief/test_drill_citations_resolve.py` (untouched suites) → **25 passed** (linter + debrief resolution stay green).
- Full default suite → **3778 passed, 27 skipped, 1 failed** — the single failure is the pre-existing, out-of-scope eval-corpus gap above (no `events.jsonl` in `hard_tek_01`), not caused by this plan.
- `git diff --name-only <base> HEAD` → only the two new test files (no `src/` change, no Kaan WIP touched).

## Commits

- `9fefc05` test(55-02): zero-orphan replay — every grounded citation resolves to a real registry entry (LIVE-04)
- `df58fc9` test(55-02): hallucination-strip — injected non-existent citation stripped on a real registry (LIVE-04)
- `c4aeb0a` test(55-02): live/debrief citation consistency — one grammar, two tolerance bands (LIVE-04)

## Self-Check: PASSED

- FOUND: `tests/coach/test_citation_zero_orphan_replay.py` (290 lines)
- FOUND: `tests/coach/test_citation_live_debrief_consistency.py` (134 lines)
- FOUND: commit 9fefc05
- FOUND: commit df58fc9
- FOUND: commit c4aeb0a
