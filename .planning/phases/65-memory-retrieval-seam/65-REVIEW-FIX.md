---
phase: 65-memory-retrieval-seam
fixed_at: 2026-05-22T00:00:00Z
review_path: .planning/phases/65-memory-retrieval-seam/65-REVIEW.md
iteration: 3
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 65: Code Review Fix Report — Iteration 3

**Fixed at:** 2026-05-22
**Source review:** `.planning/phases/65-memory-retrieval-seam/65-REVIEW.md`
**Iteration:** 3

**Summary:**
- Findings in scope: 4 (1 BLOCKER + 3 Warnings — all critical+warning tier)
- Fixed: 4
- Skipped: 0
- Pre-existing unrelated failure (`tests/coach/test_main_anti_slop_wiring.py::test_wire13_anti_slop_disabled_path_passes_none_kwargs`) was NOT introduced by these fixes; it is a regex check against `__main__.py` unrelated to the recall flow.

This iteration patches a regression in iter-1's CR-01 fix plus three edge cases the iter-2 re-review surfaced. The v5.0 cold-memory byte-pin (`test_evidence_line_audible_no_recall_byte_identical_v5_baseline`), the headline poisoning gate (`test_fabricated_recall_strips_turn`), and the CR-04 race-discard test (`test_clear_during_inflight_on_event_discards_stale_latch`) all stay GREEN. A new cross-turn regression test (`test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall`) is GREEN and pins the BLOCKER's invariant.

## Fixed Issues

### BLOCKER: `clear_source("recall")` gated inside empty-survivor branch

**Files modified:** `src/vibemix/agent/dj_cohost.py`, `tests/agent/test_dj_cohost_linter.py`
**Commit:** `e6307db`
**Applied fix:** The iter-1 CR-01 fix placed `self._registry.clear_source("recall")` inside `if recall_moments and self._registry is not None:`. That conditional skipped the clear whenever the current turn's recall pull returned empty — but prior-turn registrations stayed in the registry. Turn N registers `{A, B}`, turn N+1 has `recall_moments == []`, the clear is skipped, `snapshot["recall"]` still carries `{A, B}`, and Gemini can fabricate `[recall:A]` past the linter's existence-only branch. This is the cross-turn poisoning leak iter-2's re-review caught.

Moved the `clear_source("recall")` call to fire UNCONDITIONALLY at the top of the recall-enabled path (still guarded by `self._registry is not None`). Every turn now rescopes its own registrations: `snapshot["recall"]` is exactly the ids in the current prompt's recall block (or `{}` when there are none). A fabricated id matching a prior-turn registration is now unregistered-by-construction and the whole turn strips.

Added the cross-turn regression test `test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall` to `tests/agent/test_dj_cohost_linter.py`. The test wires a stub `MemoryRecall` whose `get_latest()` returns `[A, B]` on turn N and `[]` on turn N+1, drives both turns, and asserts that a fabricated `[recall:<A.record_id>]` on turn N+1 strips the whole turn AND that `snapshot["recall"]` is empty on turn N+1.

### WR-01: registry-less recall edge — recall block injected without validation

**Files modified:** `src/vibemix/agent/dj_cohost.py`
**Commit:** `6c4a64c`
**Applied fix:** When `_recall_enabled=True` but `_registry=None` (a construction path used by some test fixtures; production wiring threads both), survivors flowed into `evidence_line(..., recall_moments=…)` and the `[recall:<id>]` tokens landed in the prompt — but with no registry, the linter can never validate any of them. Every recall-bearing turn would strip on the existence-only check.

Added a narrow guard right after the `get_latest()` block: if `self._registry is None`, set `recall_moments = []`. This drops the recall block entirely on the registry-less path so the live LLM is never asked to ground against a state that can never validate. Lower blast radius than a hard assertion (which would break smoke tests that wire a service without a registry); the cold/feature-off path stays byte-identical.

### WR-02: `CancelledError` in `_run` task missed by `except Exception`

**Files modified:** `src/vibemix/agent/dj_cohost.py`
**Commit:** `2cfd1f6`
**Applied fix:** `prev.cancel()` in `_maybe_dispatch_recall` raises `asyncio.CancelledError` inside the prior `_run()` task. In Python 3.8+ `CancelledError` is NOT a subclass of `Exception` — the existing `except Exception` could not see it. More critically, a clear-on-cancel would be WRONG: the cancel was triggered by `set_next_event` overwriting the dispatch with a NEW event whose own `on_event` will (a) bump `_inflight_gen` (invalidating the still-running executor write from THIS task) and (b) latch its own fresh survivors. A `clear()` on the cancelling task would torpedo the new dispatch's latch.

Added an explicit `except asyncio.CancelledError: raise` BEFORE the timeout / generic exception handlers. The cancel now propagates to the task scheduler normally — WITHOUT calling `recall.clear()` — and the new dispatch lands its survivors cleanly. The deadline-miss and other-exception paths still call `recall.clear()` with the default `bump_generation=True` (CR-04 invariant preserved).

### WR-03: reactive `clear()` in `get_latest()`-exception path bumps `_inflight_gen`

**Files modified:** `src/vibemix/agent/dj_cohost.py`, `src/vibemix/memory/retrieval.py`
**Commit:** `169bdcb`
**Applied fix:** The iter-1 WR-01 fix added a defense-in-depth `self._recall.clear()` on the `get_latest()`-exception path to prevent stale-latch bleed. But `MemoryRecall.clear()` always bumped `_inflight_gen` (the CR-04 race-discard token), which could silently invalidate a healthy concurrent `on_event` dispatch building survivors for a future turn.

Added a `bump_generation: bool = True` parameter to `MemoryRecall.clear()`. The deadline-miss / dispatch-exception paths in `_run` keep the default (`True`) — those ARE the writes we want to invalidate, so the CR-04 race-discard test `test_clear_during_inflight_on_event_discards_stale_latch` stays GREEN. The reactive `get_latest()`-exception path in `llm_node` now passes `bump_generation=False` so it drops the stale latched value without torpedoing concurrent dispatches.

---

_Fixed: 2026-05-22_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 3_
