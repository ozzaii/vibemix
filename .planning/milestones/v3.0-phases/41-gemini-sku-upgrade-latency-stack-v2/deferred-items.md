# Phase 41 — Deferred Items

Items discovered during Phase 41 execution that are out-of-scope for the
plans creating them but worth tracking for follow-up.

## Plan 41-02 — Smoke-03/04/05/06 environmental failures

**Discovered during:** Plan 41-02 execution, regression sweep.

**Symptom:**
- `tests/test_main_smoke.py::test_smoke_03_full_wiring` →
  `AssertionError: assert 0 == 3` on `find_device.call_count`
- `tests/test_main_smoke.py::test_smoke_04_no_openrouter_key`
- `tests/test_main_smoke.py::test_smoke_05_cleanup_closes_all_streams`
- `tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke`
  → `FileNotFoundError: 'cohost_v4.py'`

**Root cause:** Worktree environment lacks the untracked POC reference
file `cohost_v4.py` (per project memory: v3/v4 POC files are reference
material, untracked). The smoke-03 test driver fails very early when this
file is absent, and the find_device mocks never get called.

**Verification this is pre-existing, not a Plan 41-02 regression:** Both
smoke-03 and smoke-06 fail identically on the parent commit `206389e`
(before any Plan 41-02 surgery). Smoke-01 and smoke-02 (the two
GSD-relevant smoke tests for the `--version` short-circuit and the missing
`GEMINI_API_KEY` error) pass on Plan 41-02's HEAD.

**Action:** Defer. The fix is to either (a) check `cohost_v4.py` into a
test fixtures directory or (b) skip smoke-03/04/05/06 when the POC file
is absent. Neither belongs in Plan 41-02's scope.
