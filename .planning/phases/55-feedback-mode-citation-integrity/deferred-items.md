# Phase 55 — Deferred Items (out-of-scope discoveries)

Discoveries logged during execution that are NOT in scope for the current plan.
Do NOT fix here — surface for a future plan / Kaan-action.

## From Plan 55-02 (LIVE-04 citation regressions)

- **Pre-existing full-suite failure (out of scope):**
  `tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file`
  fails because `eval/corpus/sessions/hard_tek_01/` contains only `genre.txt` +
  `source.txt` (no `events.jsonl`). This session dir is an uncommitted/untracked
  corpus skeleton in the worktree checkout (created 2026-05-21 08:32), NOT touched
  by Plan 55-02's diff (which adds only two `tests/coach/` files). The eval
  diversity gate (EVAL-03, commit 11d556d) requires every session dir to carry an
  `events.jsonl`; this corpus session was sourced but never populated. Belongs to
  the eval-corpus sourcing workflow, not the citation-integrity phase. Resolve by
  either populating `hard_tek_01/events.jsonl` or removing the incomplete session
  dir.
