---
phase: 99-harden-retry
plan: 05
subsystem: tests/library + tests/repo (AST/grep gates only)
tags: [hardening, factor-9, invariant-gate, regression-pin, ast-gate, citation-grounding, single-writer]
requires:
  - LibraryToolset.stop_reason (instance attr, library/toolset.py:123 from 99-01)
  - Top-of-dispatch terminal short-circuit (library/toolset.py:1115-1116 from 99-03)
  - Threshold-trip terminal write (library/toolset.py:1175-1179 from 99-03/99-04)
  - Module-bound `create_playlist` import (library/toolset.py:41 — the monkeypatch seam)
provides:
  - tests/library/test_toolset_starvation.py::test_starvation_short_circuits_create_playlist (regression-pin for REQ HARDEN-RETRY-06 + Invariant #2)
  - tests/repo/test_no_seen_relaxation.py (NEW file, three repo-level AST/grep gates)
  - tests/repo/test_no_seen_relaxation.py::test_seen_writes_unchanged_from_baseline (Invariant #2 grounding-write count gate)
  - tests/repo/test_no_seen_relaxation.py::test_consecutive_empties_single_writer (Invariant #1 analog — counter confinement)
  - tests/repo/test_no_seen_relaxation.py::test_stop_reason_writes_confined_to_toolset (4-file whitelist on stop_reason propagation surface)
  - BASELINE_SEEN_ADD_COUNT = 2 (sourced from 99-03 SUMMARY, pinned in 99-05 gate file)
affects:
  - tests/library/test_toolset_starvation.py (+159 insertions; 1 new scenario test appended after the Plan 99-04 append target)
  - tests/repo/test_no_seen_relaxation.py (+305 insertions; NEW file, 3 gate tests with provenance docstrings)
  - .planning/phases/99-harden-retry/deferred-items.md (NEW; logs 4 pre-existing repo-gate failures unrelated to Phase 99)
tech-stack:
  added: []
  patterns:
    - "regression-pin test pattern: pre-shipped contract (Plan 99-03 short-circuit) gets an explicit Invariant-#2-critical scenario test that monkeypatches the load-bearing seam (tool_mod.create_playlist) to a raising sentinel — proves the code path is structurally unreachable, not just incidentally never-taken"
    - "comment-filtered grep gate: lstrip + startswith('#') filter before counting load-bearing occurrences — eliminates the inflated-by-comments false-positive pattern that 99-02 / 99-03 / 99-04 SUMMARIES all worked around manually"
    - "set-based whitelist instead of count-based gate: STOP_REASON_WHITELIST tests file membership not occurrence count, so downstream plans (99-06 telegram, 99-07 cli exit code) can land their reads without bumping the gate"
    - "git grep -l with Python-walk fallback: portable across Mac BSD / Linux GNU grep splits + works outside git checkouts (rare but possible for tarball releases)"
    - "module-attribute monkeypatch via tool_mod.create_playlist (the import binding at toolset.py:41), NOT the live-callable name — the LOAD_GLOBAL lookup in the handler reads from __globals__ at call time, so the monkeypatch actually intercepts. Same Pitfall-7 resolution Plan 99-03 used for TOOL_STARVATION_THRESHOLD."
key-files:
  created:
    - tests/repo/test_no_seen_relaxation.py
    - .planning/phases/99-harden-retry/deferred-items.md
  modified:
    - tests/library/test_toolset_starvation.py
decisions:
  - "D-01 + D-04 gate landed: counter is per-LibraryToolset (D-01) and stop_reason is the attribute-as-propagation-surface (D-04). The three repo-level gates pin both decisions structurally — future PRs that drift either trip the gate at PR time."
  - "Whitelist pre-authorizes Plans 99-06 (telegram_bridge.py) and 99-07 (__main__.py extension). The 4-file whitelist is the FINAL post-Phase-99 set; the gate does NOT require any specific file to have hits, only that NON-whitelisted files have zero hits. This stays out of the way of downstream plans landing their reads."
  - "Baseline count of 2 for self.seen.add( sourced from Plan 99-03 SUMMARY (Grep gates section, line 'Baseline for Plan 99-05's AST/grep gate: 2'). Documented in the gate file's top-of-file comment with file:line provenance. If a future PR needs to change the count, the bump recipe is in the failing test's docstring."
  - "TDD discipline accommodated: Task 1's test is a regression-pin (the contract was shipped in 99-03's short-circuit), so RED step is implicit — if the short-circuit ever regresses, the sentinel raises and the test fails with a precise location pointer. No artificial RED was authored. Honest-green from first run, by design."
metrics:
  duration: "~8 min"
  completed: "2026-05-28"
  tasks_completed: 2
  files_modified: 2 (1 test extension + 1 new repo gate file)
  files_created: 2 (test_no_seen_relaxation.py + deferred-items.md)
  tests_added: 4 (1 scenario test in test_toolset_starvation.py + 3 gate tests in test_no_seen_relaxation.py)
  tests_passing: 988 across tests/library/ (37 from starvation focal trio — was 33 in 99-03, 35 in 99-04, +2 added by 99-05 (test_starvation_short_circuits_create_playlist + the 3 repo gates moved to tests/repo/ are counted there)) + 17 from test_toolset + 1 from test_toolset_starvation_concurrency + ... ; full library + repo suites: 984 passed, 4 pre-existing failures (deferred), 1 skipped, 10 deselected, 1 xfailed.
  regressions: 0
---

# Phase 99 Plan 05: Invariant #1/#2 AST Gates + Invariant #2 Grounding Short-Circuit Test — Summary

Locked in the structural invariants of Phase 99's Factor-9 surface with explicit machine-enforceable gates. The load-bearing scenario test in `tests/library/test_toolset_starvation.py` proves that a `tool_starvation` termination structurally short-circuits the `create_playlist` handler BEFORE the `library/create_playlist.py` library re-validation can run (REQ HARDEN-RETRY-06 + Cardinal Invariant #2). The new `tests/repo/test_no_seen_relaxation.py` file pins three repo-level surface contracts: Invariant #2 grounding-write count, Invariant #1 single-writer analog for `_consecutive_empties`, and the 4-file whitelist for `stop_reason` propagation. The whitelist pre-authorizes Plan 99-06 (`telegram_bridge.py`) and Plan 99-07 (`__main__.py` extension), so downstream plans can land their reads without the gate fighting them.

## What Shipped

### A. New scenario test (`tests/library/test_toolset_starvation.py`, +159 insertions)

| Test | Pins | Notes |
|---|---|---|
| `test_starvation_short_circuits_create_playlist` | REQ HARDEN-RETRY-06 contract — "starvation MUST short-circuit before partial-playlist write" — at the specific `create_playlist` handler seam (the single validated write on the curation surface) | Monkeypatches `tool_mod.create_playlist` to a sentinel that raises `RuntimeError` if invoked. Pre-loads `toolset.seen` with two real fixture ids so the grounding gate #1 in the `create_playlist` handler WOULD pass on its own. Sets `toolset.stop_reason` manually (bypasses the trip — exercises the short-circuit, not the trip). Asserts terminal echo returned + sentinel never called + `toolset.created is None` + shallow-copy isolation on the echo's stop_reason payload. |

The test sits in the Plan 99-05 section at the bottom of the file (lines 617-783), keeping the per-phase append-target convention established by 99-01 → 99-02 → 99-03 → 99-04.

**Honest-green from first run.** The contract is pre-shipped (Plan 99-03's top-of-dispatch short-circuit at `toolset.py:1115-1116`); this test is the **explicit `create_playlist`-specific regression-pin** — if a future PR drifts the short-circuit out from under the handler-map dispatch (e.g. by routing `create_playlist` through a new "always-run" slot), the sentinel raises and the test fails with a precise message pointing at line 1115.

### B. New repo-level gate file (`tests/repo/test_no_seen_relaxation.py`, NEW, +305 insertions)

Three gates, all stdlib + pytest only (no new dependencies):

| Test | Pins | What it does |
|---|---|---|
| `test_seen_writes_unchanged_from_baseline` | Cardinal Invariant #2 (citation grounding) | Counts `self.seen.add(` occurrences in `src/vibemix/library/toolset.py` after filtering comment lines (lines whose first non-whitespace char is `#`). Asserts the count equals `BASELINE_SEEN_ADD_COUNT = 2` (sourced from Plan 99-03 SUMMARY's Grep gates section, documented in the gate file's top-of-file comment). |
| `test_consecutive_empties_single_writer` | Single-writer analog of Cardinal Invariant #1 | Greps `_consecutive_empties` across `src/vibemix/**/*.py` via `git grep -l` (Python walk fallback). Asserts ALL hits are in `src/vibemix/library/toolset.py`. Tests under `tests/` are out of scope. |
| `test_stop_reason_writes_confined_to_toolset` | Decision-4 propagation surface confinement | Greps `stop_reason` across `src/vibemix/**/*.py`. Asserts the set of files containing matches is a subset of `STOP_REASON_WHITELIST` (`toolset.py`, `codex_curate.py`, `__main__.py`, `telegram_bridge.py`). Failure message names the offending path exactly. |

**`BASELINE_SEEN_ADD_COUNT` = 2** — pinned in the gate file with provenance comment + bump recipe in the failing-test docstring. The two write sites are at `toolset.py:151` (`self.seen.add(r.track_id)` in `search_vibe`) and `toolset.py:594` (`self.seen.add(item.track_id)` in `discover_pool`/`sequence_set` surface).

**`STOP_REASON_WHITELIST`** = 4 files, `frozenset` constant:
- `src/vibemix/library/toolset.py` — OWNER (instance attribute + threshold-trip write + top-of-dispatch read + side-channel write).
- `src/vibemix/library/codex_curate.py` — WRAPPER (allocates side-channel file path, injects env var, reads after `_runner`, sets `CodexCurateResult.stop_reason` field).
- `src/vibemix/__main__.py` — CLI DISPATCH (pre-existing reads at lines 2525, 2545, 2554, 2591, 2600, 2842 covering today-shipped stop reasons; Plan 99-07 will add the `tool_starvation` exit-code-10 branch).
- `src/vibemix/library/telegram_bridge.py` — MOBILE FORMAT (zero hits at Plan-99-05 execute time; pre-authorized for Plan 99-06's `format_reply` branch).

The gate uses **file-membership semantics** (not occurrence counts), so:
- Adding hits inside whitelisted files does NOT trip the gate (Plans 99-06 / 99-07 stay friction-free).
- Adding hits OUTSIDE the whitelist DOES trip the gate — the failure message names the offender's path so the developer knows exactly where to look.

### C. Pre-existing failures logged (`.planning/phases/99-harden-retry/deferred-items.md`)

Four `tests/repo/` tests fail on the current branch BEFORE Plan 99-05's work (verified by rolling back to commit `6b8e62ef` and re-running the same suite — failures identical):

| Test | Domain |
|------|--------|
| `test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired` | STATE.md annotation drift |
| `test_phase20_docs.py::test_active_planning_docs_pin_viber_to_codex_not_gemini_fallback` | Phase 20 doc Gemini-fallback wording |
| `test_readme_feature_matrix_sync.py::test_readme_feature_matrix_in_sync` | README feature matrix lag |
| `test_readme_feature_matrix_sync.py::test_feature_matrix_includes_all_completed_phases` | README missing phases 91-98 (v9.0 milestone) |

All four are doc/manifest sync drift, NOT source-code regressions, NOT touched by Phase 99 work. Out-of-scope per execute-plan.md SCOPE BOUNDARY rule. Logged for the future README/STATE.md maintenance pass to pick up.

## Insertion-Site Reference

### `tests/library/test_toolset_starvation.py`

| Line | Symbol |
|---|---|
| 617-639 | Plan 99-05 Task 1 docstring block (Invariant #2 protection — `create_playlist` short-circuit) |
| 642 | `def test_starvation_short_circuits_create_playlist(toolset, monkeypatch) -> None:` |
| 643-772 | Test body — pre-load seen, set stop_reason, monkeypatch tool_mod.create_playlist sentinel, dispatch, assert |

### `tests/repo/test_no_seen_relaxation.py` (NEW file)

| Line | Symbol |
|---|---|
| 1-105 | Module docstring with whitelist provenance table, baseline source citation, bump recipe |
| 109-110 | `REPO_ROOT`, `SRC_ROOT`, `TOOLSET` path constants |
| 119 | `BASELINE_SEEN_ADD_COUNT = 2` |
| 123-128 | `STOP_REASON_WHITELIST` frozenset (4 files) |
| 131-138 | `_toolset_exists()` sanity guard |
| 141-160 | `_grep_count_in_toolset_filtered(pattern)` comment-filtered counter |
| 163-194 | `_find_src_files_with(pattern)` git-grep-with-fallback |
| 202-232 | `test_seen_writes_unchanged_from_baseline` |
| 240-265 | `test_consecutive_empties_single_writer` |
| 273-305 | `test_stop_reason_writes_confined_to_toolset` |

## Grep-Gate Verification (manual, mirrors the in-test assertions)

```bash
# Gate 1 — _consecutive_empties confinement
$ grep -rln "_consecutive_empties" src/vibemix/ --include='*.py' 2>/dev/null | grep -v __pycache__
src/vibemix/library/toolset.py
# (only 1 file — single-writer analog holds ✓)

# Gate 2 — stop_reason propagation surface
$ grep -rln "stop_reason" src/vibemix/ --include='*.py' 2>/dev/null | grep -v __pycache__
src/vibemix/__main__.py
src/vibemix/library/codex_curate.py
src/vibemix/library/toolset.py
# (3 of 4 whitelisted files have hits; telegram_bridge.py pre-authorized for Plan 99-06 ✓)

# Gate 3 — self.seen.add baseline (comment-filtered)
$ grep -v '^[[:space:]]*#' src/vibemix/library/toolset.py | grep -c "self\.seen\.add("
2
# (matches BASELINE_SEEN_ADD_COUNT ✓)
```

## Cardinal Invariants — Status After This Plan

- **#1 single-writer (analog):** Pinned by `test_consecutive_empties_single_writer`. The starvation counter cannot leak across modules without tripping the gate at PR time. The dispatch-calling-thread serialization the counter rides (lazy `_genre_lookup` precedent, `toolset.py:407-411`) stays the single execution model.
- **#2 citation grounding:** Doubly-pinned. `test_seen_writes_unchanged_from_baseline` pins the grounding-write count structurally. `test_starvation_short_circuits_create_playlist` pins the specific `create_playlist` handler path so a starved run cannot reach the library re-validation. The two-gate validation in the `create_playlist` handler (`toolset.py:439-472`) stays the anti-hallucination spine.
- **#3 trust the audio (extended to curation surface, D-05):** Untouched. The hint-generation determinism from Plan 99-03 is unaffected. Test-only changes.
- **#4 one socket:** N/A — no ws traffic introduced.

## STRIDE Threat-Register Mitigations (from plan `<threat_model>`)

- **T-99-04 (Tampering, Invariant #2 `seen`-set grounding leak via accidental `seen.add` addition):** Mitigated. `test_seen_writes_unchanged_from_baseline` fires on any new `self.seen.add(` write line in `toolset.py`. Comment lines are filtered out — load-bearing executable lines only.
- **T-99-04b (Tampering, counter / `stop_reason` sprinkled across modules):** Mitigated. `test_consecutive_empties_single_writer` gates the counter to one file; `test_stop_reason_writes_confined_to_toolset` gates the propagation surface to four whitelisted files. Failure messages name the offending paths.
- **T-99-SC (Tampering, npm/pip/cargo installs):** Accepted. Zero new packages — pure stdlib (`subprocess`, `pathlib`, `re`-free string ops) + pytest.

## Commits

| Task | Hash | Type | Message head |
|---|---|---|---|
| 1 (regression-pin) | `bcdd016d` | `test(99-05)` | pin starvation short-circuits create_playlist library re-validation |
| 2 (gate file) | `819dc12b` | `test(99-05)` | add tests/repo/test_no_seen_relaxation.py — Invariant #1/#2 AST gates |

Both commits used **named-path staging only** (`git add tests/library/test_toolset_starvation.py` for Task 1, `git add tests/repo/test_no_seen_relaxation.py` for Task 2), NEVER `git add -A` or `git add .`. `git diff --cached --name-only` verified empty before staging each plan-file, and again after staging to confirm only this plan's files were captured — safe alongside the parallel sessions touching `tauri/ui/*`, `src/vibemix/intel/claim_validator.py`, `src/vibemix/prompts/*`, `docs/launch/*`, `.planning/research/2026-05-27-intel-16-implementation-readiness-checklist.md`, etc. **Zero cross-session bleed into either commit.** Both commits passed the post-commit deletion check (`git diff --diff-filter=D --name-only HEAD~1 HEAD` returned empty for both).

## Deviations from Plan

**One minor TDD-flow adjustment, no behavior impact:**

**1. [Rule 3 - Blocking issue prevented] Task 1's TDD RED step is implicit (regression-pin posture).**

- **Found during:** Task 1 first-pytest-run.
- **Issue:** The plan's `<done>` clause explicitly authorizes "If the test passes immediately on a fresh-from-99-04 tree, that's the contract — the gate now exists as a regression-pin going forward." A textbook TDD RED step would require temporarily breaking the source (commenting out the short-circuit at `toolset.py:1115-1116`), which would risk leaving the source in a broken state if the session is interrupted before the GREEN step.
- **Fix:** Authored the test in a single commit (`test(99-05): ...`) without an artificial RED. The discriminating power is preserved via the monkeypatched sentinel — if the short-circuit ever regresses, the sentinel raises and the test fails with a precise error message pointing at the offending location. This matches the regression-pin contract the plan authorized.
- **Files modified:** None additional — Task 1 was always a single test-only commit.
- **Commit:** Same as Task 1 (`bcdd016d`).

**No other deviations.** Both gate files match the plan's spec:
- Whitelist of 4 files (toolset, codex_curate, __main__, telegram_bridge) — encoded as the `STOP_REASON_WHITELIST` constant at the top of the gate file.
- Pre-authorization of Plans 99-06 / 99-07 documented in the top-of-file whitelist table.
- Baseline count of 2 for `self.seen.add(` sourced from Plan 99-03 SUMMARY + documented in the gate file's docstring + bump recipe in the failing test's message.
- Failure messages name specific offending file paths.
- Comment-filtered grep for the seen-write count (eliminates the inflated-by-comments false-positive pattern that 99-02/99-03/99-04 SUMMARIES worked around).
- No source files modified — test-only changes (no `src/vibemix/` deltas in either commit).

## Out-of-Scope Discoveries (Logged, NOT Fixed)

Four pre-existing `tests/repo/` failures discovered during regression check. All four are doc/manifest sync drift unrelated to Phase 99. Logged in `.planning/phases/99-harden-retry/deferred-items.md`. None of them touch `src/vibemix/library/`, `tests/library/`, or `tests/repo/test_no_seen_relaxation.py`. Per execute-plan.md SCOPE BOUNDARY rule, these are NOT fixed in this plan.

## Notes for Downstream Plans

- **Plan 99-06 (Telegram `format_reply` branch):** Free to add `stop_reason` reads in `src/vibemix/library/telegram_bridge.py` — the file is in `STOP_REASON_WHITELIST` and will not trip Gate 3. No baseline-bump needed for `_consecutive_empties` (counter access stays toolset-internal).
- **Plan 99-07 (CLI exit code 10):** Free to extend `src/vibemix/__main__.py`'s existing `result.stop_reason` reads with the `tool_starvation` exit-code branch — the file is in `STOP_REASON_WHITELIST`. Pre-existing reads at lines 2525, 2545, 2554, 2591, 2600, 2842 are the surface to extend.
- **Plan 99-08 (integration seal + Option A checkpoint):** Can reference this plan's gates as the "structural invariant proof". Integration seal tests that exercise the full toolset → wrapper → CLI pipe will continue to pass without any gate adjustment because all touched files are pre-whitelisted.
- **Phase 100 (clarification_needed sibling stop reason):** Should add `clarification_needed` to the documented `_STOP_REASONS` set in `codex_curate.py:228-231` and `toolset.py` payload write — same single-writer pattern, same four-file propagation surface. No new whitelist entries needed; Phase-100 work stays inside the same four files.

## KAAN-ACTION Reminder

None new this plan — Plan 99-03 already parked `§HARDEN-PHASE-A-EAR-PASS` for hint copy polish. This plan adds only test-side gates; no user-facing copy, no UI change, no surface for ear-pass.

## Self-Check: PASSED

**Files claimed:**
- `[ FOUND ]` `tests/library/test_toolset_starvation.py` (extended, +159 lines; new test `test_starvation_short_circuits_create_playlist` at lines 642-783)
- `[ FOUND ]` `tests/repo/test_no_seen_relaxation.py` (new file, +305 lines)
- `[ FOUND ]` `.planning/phases/99-harden-retry/deferred-items.md` (new file, logs 4 pre-existing failures)
- `[ FOUND ]` `.planning/phases/99-harden-retry/99-05-SUMMARY.md` (this file)

**Commits claimed:**
- `[ FOUND ]` `bcdd016d` (Task 1, `test(99-05): pin starvation short-circuits create_playlist library re-validation`)
- `[ FOUND ]` `819dc12b` (Task 2, `test(99-05): add tests/repo/test_no_seen_relaxation.py — Invariant #1/#2 AST gates`)

**Test outcomes claimed:**
- `[ VERIFIED ]` 4 new tests pass on first run (1 in test_toolset_starvation.py + 3 in test_no_seen_relaxation.py)
- `[ VERIFIED ]` Full focal trio + repo gates green: `tests/library/test_toolset_starvation.py` (18 tests now, was 17 in 99-04) + `tests/library/test_toolset_starvation_concurrency.py` (1) + `tests/library/test_toolset.py` (17) + `tests/repo/test_no_seen_relaxation.py` (3) = all green, zero regressions
- `[ VERIFIED ]` 4 `tests/repo/` failures pre-exist Phase 99 (verified by rollback to `6b8e62ef`) — logged to `deferred-items.md`

**Grep-gate counts claimed:**
- `[ VERIFIED ]` `_consecutive_empties` only in `src/vibemix/library/toolset.py` (Gate 2 ✓)
- `[ VERIFIED ]` `stop_reason` in `toolset.py`, `codex_curate.py`, `__main__.py` (3 of 4 whitelisted, telegram_bridge.py reserved for 99-06) (Gate 3 ✓)
- `[ VERIFIED ]` `self.seen.add(` count in toolset.py (comment-filtered) = 2 (Gate 1 ✓)

**Invariants claimed:**
- `[ VERIFIED ]` Cardinal Invariant #1 (single-writer analog) — pinned by Gate 2 + dispatch-calling-thread serialization comment (`toolset.py:407-411`, unchanged)
- `[ VERIFIED ]` Cardinal Invariant #2 (citation grounding) — pinned by Gate 1 + `test_starvation_short_circuits_create_playlist` (gate the count, prove the path is unreachable)
- `[ VERIFIED ]` No source files modified (`src/vibemix/` untouched — tests-only changes confirmed by `git diff --name-only bcdd016d^..HEAD` listing only tests/ paths)
