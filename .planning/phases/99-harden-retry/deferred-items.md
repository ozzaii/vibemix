# Phase 99 HARDEN-RETRY — Deferred Items

Out-of-scope discoveries logged during phase execution. None of these block
phase completion; they are unrelated to the Factor-9 starvation surface and
will be addressed in their respective owner phases.

## Pre-existing repo-gate failures (discovered during Plan 99-05 regression check)

The following four tests fail on `pytest -q tests/repo/` against the
current `live-tuning-or-brain` branch (verified by rolling back to commit
`6b8e62ef` — pre-Plan-99-05 — and re-running the same suite; failures
identical, so they pre-date Phase 99 entirely).

| Test | Domain | Likely owner |
|------|--------|--------------|
| `tests/repo/test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired` | STATE.md annotation drift | Roadmap maintenance |
| `tests/repo/test_phase20_docs.py::test_active_planning_docs_pin_viber_to_codex_not_gemini_fallback` | Active-planning docs reference outdated Gemini-fallback wording | Phase 20 docs maintenance |
| `tests/repo/test_readme_feature_matrix_sync.py::test_readme_feature_matrix_in_sync` | README feature matrix lags shipped phases | README sync chore |
| `tests/repo/test_readme_feature_matrix_sync.py::test_feature_matrix_includes_all_completed_phases` | README missing phases 91-98 (v9.0 "Lesson One" milestone) | README sync chore |

All four are doc/manifest sync drift, not source-code regressions. Scope
boundary applies (only auto-fix issues caused by THIS task's changes) —
documented here per execute-plan.md's SCOPE BOUNDARY rule, NOT fixed.
