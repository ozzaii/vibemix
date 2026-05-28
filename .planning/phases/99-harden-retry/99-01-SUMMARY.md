---
phase: 99-harden-retry
plan: 01
subsystem: library/toolset
tags: [scaffolding, hardening, factor-9, retry, additive]
requires: []
provides:
  - TOOL_STARVATION_THRESHOLD (module constant, library/toolset.py:73)
  - LibraryToolset._consecutive_empties (instance attr, library/toolset.py:120)
  - LibraryToolset.stop_reason (instance attr, library/toolset.py:121)
affects:
  - src/vibemix/library/toolset.py (additive only — 16 insertions, 0 removals)
  - tests/library/test_toolset_starvation.py (NEW — 3 tests, 98 lines)
tech-stack:
  added: []
  patterns:
    - "instance-attribute-as-terminal-result (parallel to self.created / self.exported)"
    - "module-level threshold constant (parallel to TOOL_CALL_TIMEOUT_S)"
key-files:
  created:
    - tests/library/test_toolset_starvation.py
  modified:
    - src/vibemix/library/toolset.py
decisions:
  - "Counter location locked to LibraryToolset instance attribute (D-01)"
  - "Threshold N=3 locked as module constant TOOL_STARVATION_THRESHOLD (D-03)"
  - "Stop-reason surface locked to self.stop_reason: dict | None (D-04)"
metrics:
  duration: "~12 min"
  completed: "2026-05-28"
  tasks_completed: 2
  files_modified: 2
  tests_added: 3
  tests_passing: 611 (full tests/library/ suite)
  regressions: 0
---

# Phase 99 Plan 01: Scaffolding — Tool Starvation Counter Spine Summary

Added the static spine for Phase 99's tool-starvation retry policy — a `TOOL_STARVATION_THRESHOLD = 3` module constant plus per-instance `_consecutive_empties` counter and `stop_reason` attribute on `LibraryToolset` — with zero runtime behavior change, gating future plans 99-02 / 99-03 / 99-04 / 99-05 on a verified, tested foundation.

## What Shipped

**Source change (`src/vibemix/library/toolset.py`):**

| Symbol | Location | Decision | Purpose |
|---|---|---|---|
| `TOOL_STARVATION_THRESHOLD: int = 3` | line 73 (module scope, adjacent to `TOOL_CALL_TIMEOUT_S`) | D-03 | Threshold N for consecutive-empty trip. Tunable via `monkeypatch.setattr`. |
| `self._consecutive_empties: int = 0` | line 120 (in `__init__`, immediately after `self.exported`) | D-01 | Per-run counter. Mirrors `self.seen` lifetime. |
| `self.stop_reason: dict[str, Any] | None = None` | line 121 (in `__init__`, after the counter) | D-04 | Terminal stop_reason surface. Mirrors `self.created` / `self.exported`. |

**Test change (`tests/library/test_toolset_starvation.py` — NEW):**

| Test | Pins |
|---|---|
| `test_threshold_constant_present` | `tool_mod.TOOL_STARVATION_THRESHOLD == 3` (int, exactly 3 per D-03) |
| `test_counter_initial_zero` | Fresh `LibraryToolset()._consecutive_empties == 0` |
| `test_stop_reason_initial_none` | Fresh `LibraryToolset().stop_reason is None` |

Fixture posture mirrors `tests/library/test_toolset.py:148-170` (in-memory `RekordboxLibrary` + `MagicMock()` embedder/store) — re-defined locally per pytest convention (no cross-test imports of private helpers).

## Verification Gates (per plan `<verification>` block)

**Test gates:**
- `pytest -q tests/library/test_toolset_starvation.py` → 3/3 green (Task 2 GREEN transition).
- `pytest -q tests/library/test_toolset.py` → 17/17 green (zero regression on canonical fixture).
- `pytest -q tests/library/` (full suite) → **611 passed, 1 skipped (pre-existing, no transformers), 1 xfailed (pre-existing budget gate)**, 0 regressions.

**Grep gates (single-writer analog precondition for Cardinal Invariant #1):**
- `grep -c "_consecutive_empties\|self\.stop_reason" src/vibemix/library/toolset.py` → **2** (exactly the two `__init__` assignment lines; no stray reads/writes elsewhere). 99-05 will tighten this into an AST gate.
- `grep -rn "_consecutive_empties\|TOOL_STARVATION_THRESHOLD" src/vibemix/` → hits ONLY in `src/vibemix/library/toolset.py:73,120`. No other source module references the new symbols (disjointness contract holds — `agent/`, `__main__.py`, `intel/`, `tauri/ui/` untouched).

**`dispatch()` byte-equivalence:** `git diff src/vibemix/library/toolset.py` total = **16 insertions, 0 removals**. Both edits are pure inserts (constant block at line 73, attribute block at lines 120-121). The body of `dispatch()` (toolset.py:982-1013) is unchanged — verified by reading the diff: no hunks touch the dispatch region.

## Insertion-Site Line Numbers (for Plan 99-02 to reference)

After this plan, the file layout is:
- Line **65**: existing `TOOL_CALL_TIMEOUT_S = 30.0`
- Line **73**: NEW `TOOL_STARVATION_THRESHOLD: int = 3`
- Line **111**: existing `self.exported: ExportResult | None = None`
- Line **120**: NEW `self._consecutive_empties: int = 0`
- Line **121**: NEW `self.stop_reason: dict[str, Any] | None = None`

Plan 99-02 will add the counter-increment hook inside `dispatch()` (around the existing `fut.result()` at toolset.py:1009, post-edit line number — recompute after this plan's insertions land). The hook will be the SINGLE writer of `self._consecutive_empties` outside `__init__`, satisfying the Invariant #1 analog.

## Commits

| Task | Hash | Type | Message |
|---|---|---|---|
| 1 (RED) | `aded8e8b` | `test(99-01)` | add failing scaffolding tests for tool-starvation counter |
| 2 (GREEN) | `79961b45` | `feat(99-01)` | scaffold TOOL_STARVATION_THRESHOLD + counter + stop_reason |

Both commits use named-path staging (never `git add -A`) per `feedback_concurrent_sessions_one_tree` — safe alongside the parallel LiveKit handoff in `__main__.py:1353` and the parallel frontend handoff in `tauri/ui/*`.

## Cardinal Invariants — Status After This Plan

- **#1 single-writer (analog):** Holds by construction. The only writes to `_consecutive_empties` and `stop_reason` are inside `__init__` (lines 120-121). Grep gate (count=2) is the proof; AST gate lands in 99-05.
- **#2 citation grounding:** Untouched. `self.seen` semantics are byte-equivalent. The 17 existing toolset tests (including `test_search_populates_seen_set`, `test_create_rejects_invented_id`, `test_create_persists_grounded_playlist`) stay green — the `seen`-set + `create_playlist` two-gate validation is structurally unaffected.
- **#3 trust the audio:** N/A (live co-host untouched).
- **#4 one socket:** N/A (no ws traffic introduced).

## Deviations from Plan

**None.** Pure scaffolding executed as written:
- Task 1 RED state captured exactly as the `<done>` block specifies (3 `AssertionError`s, no `pytest.skip`/`xfail` markers).
- Task 2 inserted the constant + two attributes at the planned sites (top-of-file near `TOOL_CALL_TIMEOUT_S`; immediately after `self.exported`).
- `Any` was already imported (`from typing import ..., Any, ...` at line 37) — no import edit needed.
- No `dispatch()` touch, no handler touch, no `mcp_server.py` touch, no `codex_curate.py` touch, no `__main__.py` touch, no `agent/` touch, no `intel/` touch, no `tauri/ui/` touch. Disjointness contract held.

## What's Left for Future Plans (per Phase 99 scope)

- **Plan 99-02**: Wire the dispatch-site increment hook (single writer site for `_consecutive_empties`).
- **Plan 99-03**: Threshold-trip terminal action — write `self.stop_reason` payload with deterministic hint generation (D-05 three cases).
- **Plan 99-04**: Cross-process side-channel (env-var-passed temp file) so `codex_curate.py` can read the toolset's stop_reason across the MCP STDIO subprocess boundary.
- **Plan 99-05**: AST/grep gate — `tests/repo/test_no_seen_relaxation.py` plus tight single-writer assertion on `_consecutive_empties`.
- **Plan 99-06**: Telegram bridge `format_reply` branch.
- **Plan 99-07**: CLI exit-code dispatch (exit 10 for `tool_starvation`).
- **Plan 99-08**: Env-propagation cross-process verification checkpoint.

Insertion-site line numbers above feed those plans directly.

## Self-Check: PASSED

**Files claimed:**
- `[ FOUND ]` `tests/library/test_toolset_starvation.py` (created, 98 lines)
- `[ FOUND ]` `src/vibemix/library/toolset.py` (modified, +16 lines)

**Commits claimed:**
- `[ FOUND ]` `aded8e8b` (Task 1 RED, `test(99-01)`)
- `[ FOUND ]` `79961b45` (Task 2 GREEN, `feat(99-01)`)

**Symbol locations claimed:**
- `[ FOUND ]` `TOOL_STARVATION_THRESHOLD` at `src/vibemix/library/toolset.py:73`
- `[ FOUND ]` `self._consecutive_empties` at `src/vibemix/library/toolset.py:120`
- `[ FOUND ]` `self.stop_reason` at `src/vibemix/library/toolset.py:121`

**Test count claimed:**
- `[ VERIFIED ]` `tests/library/` = 611 passed (full suite, last run after Task 2 commit)
- `[ VERIFIED ]` `tests/library/test_toolset_starvation.py` = 3 passed
- `[ VERIFIED ]` `tests/library/test_toolset.py` = 17 passed (no regression)
