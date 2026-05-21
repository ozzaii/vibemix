# Phase 55 — Deferred Items (out-of-scope discoveries)

Logged per the executor SCOPE BOUNDARY rule across all three plans (55-01, 55-02,
55-03). These are NOT caused by Phase 55 work and are explicitly left unfixed.

## 1. [Out-of-scope, pre-existing] `tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file` fails

- **Found independently by:** Plan 55-01, 55-02, and 55-03 full-suite verification runs.
- **Cause:** `eval/corpus/sessions/*/events.jsonl` are git-IGNORED (`.gitignore:89 *.jsonl`)
  and never committed. They exist as local untracked placeholders in the main checkout
  (so the test passes there) but are absent from a fresh worktree/clone (worktrees
  materialize only tracked files), so the test fails. In particular
  `eval/corpus/sessions/hard_tek_01/` ships `genre.txt` + `source.txt` but no
  `events.jsonl`.
- **Pre-existing on base `15fa3fe`:** Yes — independent of Phase 55. None of the three
  plans touched any `eval/` file (55-01: two `tests/state` + `tests/agent` files;
  55-02: two `tests/coach` files; 55-03: `src/vibemix/coach/stripped_rate.py`,
  `src/vibemix/agent/dj_cohost.py`, `src/vibemix/__main__.py` + their 3 test files).
  Matches RESEARCH landmine #2 and the documented **GATE-03 carryover** (corpus
  population pending — see PROJECT.md "Active requirements" + STATE.md known tech-debt).
- **Not fixed because:** out of plan scope (unrelated file) + real-corpus population is a
  Kaan-action discharge, not engineering. Resolve by either committing real corpus
  `events.jsonl` files (Kaan corpus acquisition) or relaxing the gate to skip when the
  ignored placeholder is absent — a separate decision, not this phase's.
