# Phase 55 — Deferred Items (out-of-scope discoveries)

Logged per the executor SCOPE BOUNDARY rule. These are NOT caused by Plan 55-01
(coach anti-slop tests) and are explicitly left unfixed.

## 1. [Out-of-scope] `tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file` fails in a fresh worktree/clone

- **Found during:** Plan 55-01 full-suite verification run (in the parallel worktree).
- **Cause:** `eval/corpus/sessions/*/events.jsonl` are git-IGNORED (`.gitignore:89: *.jsonl`) and never committed. They exist as local untracked placeholders in the main checkout (so the test passes there) but are absent from a fresh worktree/clone (worktrees materialize only tracked files), so the test fails.
- **Pre-existing:** Yes — independent of this plan. Plan 55-01 touches no `eval/` files (diff is exactly `tests/state/test_coach_anti_slop.py` + `tests/agent/test_coach_prompt_grounding.py`). Matches RESEARCH landmine #2: "`eval/corpus/sessions/*.events.jsonl` are EMPTY placeholders pending Kaan corpus acquisition."
- **Not fixed because:** out of plan scope (unrelated file) + corpus acquisition is a Kaan-action carveout (GATE-03 in PROJECT.md Active requirements). The fix is either committing real corpus `events.jsonl` files (Kaan corpus acquisition) or relaxing the gate to skip when the ignored placeholder is absent — a separate decision, not this plan's.
