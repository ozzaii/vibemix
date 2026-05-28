---
phase: 99-harden-retry
plan: 02
subsystem: library/toolset
tags: [dispatch-hook, hardening, factor-9, retry, telemetry-only, additive]
requires:
  - TOOL_STARVATION_THRESHOLD (module constant, library/toolset.py:73 from 99-01)
  - LibraryToolset._consecutive_empties (instance attr, library/toolset.py:120 from 99-01)
  - LibraryToolset.stop_reason (instance attr, library/toolset.py:121 from 99-01)
provides:
  - LibraryToolset._is_empty_or_error (private method, library/toolset.py:998)
  - dispatch-site counter increment/reset (library/toolset.py:1059-1062)
affects:
  - src/vibemix/library/toolset.py (additive — +38 insertions, -3 deletions; the 3 deletions are the `return fut.result(...)` refactor into capture-then-return)
  - tests/library/test_toolset_starvation.py (extended — +185 insertions: 5 new behavior tests)
  - tests/library/test_toolset_starvation_concurrency.py (NEW — 131 lines, 1 acid test)
tech-stack:
  added: []
  patterns:
    - "predicate-helper-as-private-method (parallel to _resolve_genre, _genre_lookup lazy-init)"
    - "dispatch-calling-thread counter writes AFTER fut.result() (mirrors the lazy-init guarantee at toolset.py:407-411)"
key-files:
  created:
    - tests/library/test_toolset_starvation_concurrency.py
  modified:
    - src/vibemix/library/toolset.py
    - tests/library/test_toolset_starvation.py
decisions:
  - "Counter increments on (a) empty search_vibe AND (b) any handler error (D-02)"
  - "Counter writes confined to dispatch-calling thread AFTER fut.result() (Pitfall 1)"
  - "_is_empty_or_error helper centralizes detection — single source of truth reused by Plan 99-03"
metrics:
  duration: "~25 min"
  completed: "2026-05-28"
  tasks_completed: 2
  files_modified: 3
  tests_added: 6
  tests_passing: 617 (full tests/library/ suite; up from 611 in 99-01)
  regressions: 0
---

# Phase 99 Plan 02: Wire Counter Increment/Reset in dispatch() Summary

Made the Plan-99-01 starvation counter LIVE: every `LibraryToolset.dispatch()` call now updates `self._consecutive_empties` on the dispatch-calling thread immediately after the handler returns, increments on empty `search_vibe` or any handler-error response, and resets on any successful non-empty/non-error tool return. The hook is telemetry-only — no threshold trip, no `stop_reason` write, no side-channel file — keeping the surface byte-equivalent to pre-plan behavior while wiring the single-writer site that Plans 99-03 / 99-05 will lock down.

## What Shipped

**Source change (`src/vibemix/library/toolset.py`):**

| Symbol | Location | Decision | Purpose |
|---|---|---|---|
| `LibraryToolset._is_empty_or_error(self, name, result)` | line **998** (immediately above `dispatch()`, private-helper convention) | D-02 | Single source of truth for empty/error detection. True on any `{"error": ...}` dict OR empty `search_vibe` `{"results": []}`. Re-used by Plan 99-03 from the same call site. |
| Counter update block in `dispatch()` | lines **1058-1062** (AFTER `fut.result()`'s try/except resolves `result`; BEFORE the unchanged `return result`) | D-02 + Pitfall 1 | `+= 1` when `_is_empty_or_error` returns True; `= 0` on success. Writes confined to dispatch-calling thread (the `ThreadPoolExecutor` worker has been joined via `fut.result()` / the `with` block exit before this point). |
| `dispatch()` body refactor | lines 1037-1043 | Pitfall 1 | The 3 prior `return fut.result(...)` / `return {"error": ...}` lines became 3 `result = ...` assignments to capture the handler outcome BEFORE the counter hook runs. `return result` (line 1064) is the new single exit. |

**Test changes:**

`tests/library/test_toolset_starvation.py` (extended from 99-01's 98 lines → 283 lines):

| Test | Pins |
|---|---|
| `test_empty_search_increments` | D-02(a): empty `search_vibe` increments counter by 1; `stop_reason` stays None. |
| `test_handler_error_increments` | D-02(b): `get_track_features` with unknown `track_id` returns `{"error": ...}` → counter = 1; `stop_reason` stays None. |
| `test_counter_resets_on_success` | "consecutive" semantics: empty (→1) then non-empty (→0). |
| `test_counter_resets_after_partial_failures` | Mixed sequence: empty (→1) → error (→2) → success (→0). |
| `test_counter_monotonic_no_terminal_below_threshold` | With `monkeypatch.setattr(tool_mod, "TOOL_STARVATION_THRESHOLD", 4)`, 3 empties → counter = 3, `stop_reason` is None, every dispatch return is byte-equivalent to handler output (no short-circuit). |

`tests/library/test_toolset_starvation_concurrency.py` (NEW, 131 lines):

| Test | Pins |
|---|---|
| `test_monotonic_under_parallel_dispatch` | 9 worker threads, `threading.Barrier(9)` simultaneous release, each calls `dispatch("search_vibe", ...)` with empty results. Final counter == 9 exactly. Zero lost updates, zero double increments. Acid test for RESEARCH.md §Q7 / Pitfall 1. **Determinism verified: 5/5 consecutive green.** |

## Verification Gates (per plan `<verification>` block)

**Test gates:**
- `pytest -q tests/library/test_toolset_starvation.py tests/library/test_toolset_starvation_concurrency.py` → 9/9 green (3 99-01 scaffolding + 5 behavior + 1 acid).
- `pytest -q tests/library/test_toolset.py` → 17/17 green (zero regression on canonical fixture; the dispatch refactor preserved every error-path return shape).
- `pytest -q tests/library/` → **617 passed, 1 skipped (pre-existing, no transformers), 1 xfailed (pre-existing budget gate)**. Up from 611 in 99-01 by the 6 new tests this plan added. Zero regressions.
- Wider sanity: `pytest -q tests/ --ignore=tests/e2e -k "dispatch or toolset or curate or codex_curate or mcp"` → 139 passed, 5651 deselected, 8 pre-existing deprecation warnings — zero regressions. (`tests/e2e/macbook/` collection-errors on missing `jinja2` is pre-existing and unrelated to this plan; documented as out-of-scope.)

**Acid-test determinism (per `<output>` block):**

```
run 1: 1 passed in 0.06s
run 2: 1 passed in 0.05s
run 3: 1 passed in 0.06s
run 4: 1 passed in 0.06s
run 5: 1 passed in 0.05s
```

5/5 deterministic. `threading.Barrier` timing is stable.

**Grep gates (single-writer analog precondition for Cardinal Invariant #1):**
- `grep -c "self\._consecutive_empties" src/vibemix/library/toolset.py` → **3** (helper-read at line 1059 + `+= 1` at line 1060 + `= 0` at line 1062). Matches plan spec exactly.
- `grep -c "self\.stop_reason" src/vibemix/library/toolset.py` → **1** (the `__init__` assignment from 99-01 at line 121). Plan 99-03 has NOT been jumped — no threshold trip, no payload write.
- Anti-pattern grep (Pitfall 1): `grep -B2 "_consecutive_empties += 1\|_consecutive_empties = 0" src/vibemix/library/toolset.py` returns only context lines from `dispatch()` (the comment block at lines 1051-1057 + the `if self._is_empty_or_error(name, result):` line). Zero occurrences inside any handler body.

## `return result` Byte-Equivalence

Plan `<output>` requires confirmation that the `return result` line is unchanged in position (i.e. the surface contract is byte-equivalent). **Confirmed:**

- Pre-plan (99-01): `dispatch()` body ended at line 1029 with `return fut.result(timeout=...)` inside the try block, with two `return {"error": ...}` lines in the `except` branches.
- Post-plan (99-02): `dispatch()` body now ends at line 1064 with a single `return result` after the counter hook block. The function still:
  - Returns `{"error": "unknown tool ..."}` for unknown handler names (unchanged dict shape).
  - Returns the handler's literal return value on success (unchanged dict shape — counter is observable ONLY via the `_consecutive_empties` attribute, never folded into the return dict).
  - Returns `{"error": "tool '<name>' timed out"}` on TimeoutError (unchanged dict shape).
  - Returns `{"error": "tool '<name>' crashed: <ExcType>"}` on any other handler exception (unchanged dict shape).

The 3-line `return fut.result(...) → result = fut.result(...)` refactor (one `return` per branch → one `result = ...` per branch + one `return result` at end) is a structurally equivalent code transformation. The 17/17 canonical `tests/library/test_toolset.py` regression check pins this — including `test_dispatch_errors_never_raise` which exercises all four error-return paths.

## Insertion-Site Line Numbers (for Plan 99-03 to reference)

After this plan, the file layout for the dispatch region is:

| Line | Symbol |
|---|---|
| 998 | `def _is_empty_or_error(self, name, result) -> bool:` (NEW in 99-02) |
| 1016 | `def dispatch(self, name, args) -> dict:` |
| 1018-1036 | handler-map dict + lookup |
| 1038-1043 | ThreadPoolExecutor → `result = fut.result(...)` capture block |
| 1051-1057 | Phase 99 hook comment block |
| 1058 | `# ─── PHASE 99 HOOK (Plan 99-02 — counter telemetry, no terminal) ───` |
| 1059 | `if self._is_empty_or_error(name, result):` |
| 1060 | `    self._consecutive_empties += 1` ← Plan 99-03 inserts threshold-trip + `stop_reason` write block AFTER this line and BEFORE the `else:` at 1061. |
| 1061-1062 | `else: self._consecutive_empties = 0` |
| 1064 | `return result` (unchanged exit) |

Plan 99-03's threshold trip will live inside the `if` branch, immediately after the `+= 1`. The `_is_empty_or_error` predicate is the single source of truth; Plan 99-03 reuses it (no re-detection logic), and Plan 99-04 (side-channel file write) lives inside the same `if` branch alongside the `stop_reason` payload write.

## Commits

| Task | Hash | Type | Message |
|---|---|---|---|
| 1 (RED) | `e7b9f5b3` | `test(99-02)` | add failing tests for dispatch counter wiring + concurrency acid |
| 2 (GREEN) | `569acd1f` | `feat(99-02)` | wire counter increment + reset in dispatch() with _is_empty_or_error |

Both commits use named-path staging (never `git add -A`). Pre-commit `git diff --cached --name-only` verified empty before staging this plan's files, and again after staging to confirm only this plan's files were captured — safe alongside the parallel sessions touching `tauri/ui/*`, `src/vibemix/intel/claim_validator.py`, `src/vibemix/prompts/*`, `docs/launch/*`, etc. Zero cross-session bleed into either commit. Both commits passed the post-commit deletion check (no files removed).

## Cardinal Invariants — Status After This Plan

- **#1 single-writer (analog):** Holds. The dispatch-site counter update is the SOLE write site for `_consecutive_empties` outside `__init__`. The acid test pins thread-safety: 9 parallel `dispatch()` calls land exactly 9 increments. RESEARCH.md §Q7's claim is now empirically verified by `test_monotonic_under_parallel_dispatch`. Plan 99-05 will tighten this into an AST gate.
- **#2 citation grounding:** Untouched. `self.seen` semantics are byte-equivalent. Counter is additive telemetry on the dispatch path — the `create_playlist` two-gate validation is structurally unaffected. The 17 canonical `tests/library/test_toolset.py` tests stay green, including `test_search_populates_seen_set`, `test_create_rejects_invented_id`, `test_create_persists_grounded_playlist`.
- **#3 trust the audio:** N/A (live co-host untouched).
- **#4 one socket:** N/A (no ws traffic introduced).

## Deviations from Plan

**One minor textual deviation (no behavior impact):**

**1. [Rule 1 - Bug] Initial counter-update comment block contained the literal substring `self.stop_reason`, breaking the plan's `grep -c "self\.stop_reason" src/vibemix/library/toolset.py == 1` gate (returned 2).**
- **Found during:** Task 2 verification.
- **Issue:** The forward-reference comment ("Plan 99-03 will extend this block with the threshold trip + ``self.stop_reason`` payload write.") contained `self.stop_reason` as a literal substring, inflating the textual grep count from 1 to 2 even though the semantic gate (no executable assignment outside `__init__`) held.
- **Fix:** Rephrased the comment to "the ``stop_reason`` payload write" — preserving the semantic intent while keeping the textual count at 1. The plan author's intent (no executable references to `self.stop_reason` outside `__init__`) is preserved; the AST gate Plan 99-05 will install would catch the same thing more robustly.
- **Files modified:** `src/vibemix/library/toolset.py` (one comment-line rewrite within Task 2 GREEN's diff).
- **Commit:** included in `569acd1f` (Task 2 GREEN).

**No other deviations.** Wiring executed exactly as the plan specifies:
- `_is_empty_or_error` placed immediately above `dispatch()` (private-helper adjacency per the plan's `<action>` block).
- Counter update block placed AFTER `fut.result()` returns and BEFORE `return result`.
- The `dispatch()` body refactor (capture-then-return) is the minimum structural change required to give the counter hook a captured `result` to inspect — necessary because the pre-plan code returned directly from inside the try/except branches.
- No threshold check, no `stop_reason` write, no side-channel file (Plans 99-03 and 99-04 land those).
- No handler bodies touched. No `agent/`, `__main__.py`, `intel/`, `mcp_server.py`, `codex_curate.py`, or `tauri/ui/` touched.

## Out-of-Scope Discoveries (Logged, NOT Fixed)

- `tests/e2e/macbook/conftest.py` collection error on missing `jinja2` — pre-existing env issue; the e2e tests are marker-skipped in default runs but conftest collection runs first. Unrelated to this plan's surface. (Documented; no action.)

## What's Left for Future Plans (per Phase 99 scope)

- **Plan 99-03**: Threshold-trip terminal action — inside the `if self._is_empty_or_error(...)` branch, write `self.stop_reason = self._build_starvation_payload(...)` when `self._consecutive_empties >= TOOL_STARVATION_THRESHOLD`. Uses the three-case deterministic hint generator (D-05). Insertion point: between lines 1060 (`+= 1`) and 1061 (`else:`) in this plan's file layout.
- **Plan 99-04**: Cross-process side-channel — `self._write_side_channel(self.stop_reason)` immediately after the payload assignment Plan 99-03 will add. Reads `VIBEMIX_STOP_REASON_FILE` env var; best-effort write.
- **Plan 99-05**: AST/grep gate — `tests/repo/test_no_seen_relaxation.py` plus tight single-writer assertion on `_consecutive_empties` (one assignment in `__init__`, one read + one `+= 1` + one `= 0` in `dispatch()`, one read in `_is_empty_or_error`).
- **Plan 99-06**: Telegram bridge `format_reply` branch.
- **Plan 99-07**: CLI exit-code dispatch (exit 10 for `tool_starvation`).
- **Plan 99-08**: Env-propagation cross-process verification checkpoint.

## Self-Check: PASSED

**Files claimed:**
- `[ FOUND ]` `src/vibemix/library/toolset.py` (modified, +38 insertions, -3 deletions)
- `[ FOUND ]` `tests/library/test_toolset_starvation.py` (extended, +185 lines)
- `[ FOUND ]` `tests/library/test_toolset_starvation_concurrency.py` (created, 131 lines)

**Commits claimed:**
- `[ FOUND ]` `e7b9f5b3` (Task 1 RED, `test(99-02)`)
- `[ FOUND ]` `569acd1f` (Task 2 GREEN, `feat(99-02)`)

**Symbol locations claimed:**
- `[ FOUND ]` `_is_empty_or_error` at `src/vibemix/library/toolset.py:998`
- `[ FOUND ]` counter `+= 1` at `src/vibemix/library/toolset.py:1060`
- `[ FOUND ]` counter `= 0` at `src/vibemix/library/toolset.py:1062`
- `[ FOUND ]` `return result` at `src/vibemix/library/toolset.py:1064`

**Test count claimed:**
- `[ VERIFIED ]` `tests/library/` = 617 passed, 1 skipped, 1 xfailed (full suite; up from 611 in 99-01).
- `[ VERIFIED ]` `tests/library/test_toolset_starvation.py` = 8 passed (3 99-01 + 5 99-02).
- `[ VERIFIED ]` `tests/library/test_toolset_starvation_concurrency.py` = 1 passed (acid test).
- `[ VERIFIED ]` `tests/library/test_toolset.py` = 17 passed (no regression on canonical fixture).
- `[ VERIFIED ]` Acid test x5 consecutive runs = 5/5 deterministic green.
