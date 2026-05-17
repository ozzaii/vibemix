---
phase: 41-gemini-sku-upgrade-latency-stack-v2
plan: 02
subsystem: agent.cache + state.evidence_registry + agent.dj_cohost
tags: [latency, cache, telemetry, autonomous]
status: complete
requirements: [LAT-02, LAT-03]
dependency_graph:
  requires:
    - 41-01  # ModelRouter seam — referenced by cache.py model resolution path
  provides:
    - cache.event_driven_refresh
    - cache.cache_hit_telemetry
    - cache.ttl_60min
  affects:
    - src/vibemix/agent/cache.py
    - src/vibemix/state/evidence_registry.py
    - src/vibemix/__main__.py
    - src/vibemix/agent/dj_cohost.py
tech_stack:
  added: []
  patterns:
    - "asyncio TimerHandle cancel-and-reschedule debounce"
    - "min-interval guard on debounced timer"
    - "atomic-swap chokepoint replacing wall-clock loop"
key_files:
  created:
    - tests/agent/test_cache_mutation_refresh.py
    - tests/agent/test_dj_cohost_cache_hit.py
    - .planning/phases/41-gemini-sku-upgrade-latency-stack-v2/deferred-items.md
  modified:
    - src/vibemix/agent/cache.py
    - src/vibemix/state/evidence_registry.py
    - src/vibemix/__main__.py
    - src/vibemix/agent/dj_cohost.py
    - tests/agent/test_cache.py
    - tests/test_main_smoke.py
decisions:
  - "TTL 300s → 3600s (60-min). Wall-clock refresh is gone; longer ceiling matches event-driven cadence."
  - "Debounce = 5.0s (DEFAULT_MUTATION_DEBOUNCE_S); min-refresh-interval = 30.0s (DEFAULT_MIN_REFRESH_INTERVAL_S). Pinned via test_default_constants."
  - "Pad block + padded_body() preserved — Pitfall 5 (Gemini 2026 implicit caching needs ≥1024-token prefix; lean personas fall below without the pad)."
  - "cache_hit telemetry dedupes per-turn against last_cache_hit_emitted — the SDK repeats UsageMetadata across multiple end-of-stream chunks."
  - "refresh() re-raises create failures AFTER restoring current_name to old — caller logs, cache never goes None mid-session."
metrics:
  duration: "single session"
  tasks_completed: 3
  files_modified: 6
  files_created: 3
  tests_added: 24  # 9 new in test_cache.py + 11 in test_cache_mutation_refresh.py + 4 in test_dj_cohost_cache_hit.py
  tests_deleted: 3  # the three old refresh_loop tests
  net_tests: 33  # total Plan 41-02 test coverage
---

# Phase 41 Plan 02: Caching Cleanup Summary

One-liner: GeminiContextCache wall-clock refresh_loop replaced by
EvidenceRegistry-driven debounced refresh + cache_hit telemetry, with TTL
raised 300s → 3600s and the Pitfall 5 pad invariant preserved.

## Commits

| Hash      | Task | Title |
| --------- | ---- | ----- |
| `fd68e88` | 1    | refactor(41-02): cache surgery — TTL 3600s, drop refresh_loop, add refresh() |
| `a19483c` | 2    | feat(41-02): mutation-driven cache refresh — debounce + min-interval guard |
| `6f96511` | 3    | feat(41-02): cache_hit telemetry in DJCoHostAgent.llm_node |

## Pre vs Post Cleanup Proof

### grep: `refresh_loop` in production code

**Before (parent commit `206389e`):**
```
src/vibemix/agent/cache.py:185:    async def refresh_loop(self, stop_event: asyncio.Event) -> None:
src/vibemix/__main__.py:870:        cache_refresh_task = asyncio.create_task(cache.refresh_loop(stop_event))
```

**After (HEAD `6f96511`):** only docstring references — no method definition, no invocation. The `src/vibemix/__main__.py:state_refresh_loop` references are an UNRELATED module (`vibemix.state` refresh loop, not cache refresh).

```
$ grep -n "refresh_loop" src/vibemix/agent/cache.py src/vibemix/__main__.py \
    | grep -v state_refresh_loop
src/vibemix/agent/cache.py:10:The wall-clock ``refresh_loop`` background task is GONE...
src/vibemix/agent/cache.py:33:  2. **refresh() is the atomic-swap chokepoint** (replaces refresh_loop)
```

### grep: `GEMINI_CACHE_REFRESH_S`

**Before:** constant defined at `cache.py:59`, kwarg used at `cache.py:102 + 110`.
**After:** zero matches anywhere in `src/` and `tests/`.

### grep: TTL value

```
$ grep -n "GEMINI_CACHE_TTL_S = " src/vibemix/agent/cache.py
71:GEMINI_CACHE_TTL_S = 3600.0
```

### grep: pad invariant

```
$ grep -n "_CACHE_PAD_BLOCK" src/vibemix/agent/cache.py
17:**Pitfall 5 — pad invariant survives the cleanup.** ``_CACHE_PAD_BLOCK``
28:     proxy get the deterministic ``_CACHE_PAD_BLOCK`` appended.
88:_CACHE_PAD_BLOCK: str = "\n".join(
106:     pad invariant for any input ≥1 char ...
148:    """Return ... padded above the 1024-token Gemini cache floor ..."""
150:        return combined + "\n\n" + _CACHE_PAD_BLOCK
```

Pad block content identical to pre-cleanup (verified by
`test_pad_block_unchanged_golden` — 81 lines, header + 80 × 60-char
filler).

## Debounce + Min-Interval Values Shipped

| Constant | Value | Source |
|----------|-------|--------|
| `DEFAULT_MUTATION_DEBOUNCE_S` | **5.0** | `src/vibemix/state/evidence_registry.py:76` |
| `DEFAULT_MIN_REFRESH_INTERVAL_S` | **30.0** | `src/vibemix/state/evidence_registry.py:84` |
| `GEMINI_CACHE_TTL_S` | **3600.0** | `src/vibemix/agent/cache.py:71` |

These match the CONTEXT.md + research locked design exactly (no in-flight
tuning during implementation). The test
`test_default_constants` pins them in CI.

## Test Count Delta

**Deleted from `tests/agent/test_cache.py` (3):**
- `test_refresh_loop_atomic_swap`
- `test_refresh_loop_keeps_old_on_create_failure`
- `test_refresh_loop_stops_on_stop_event`

**Added to `tests/agent/test_cache.py` (9 net new + 6 carried over with edits):**

| Test | Type |
|------|------|
| `test_ttl_constant_is_3600` | TTL bump pin |
| `test_refresh_s_constant_removed` | cleanup pin |
| `test_token_floor_unchanged` | floor invariant |
| `test_padded_body_invariant_preserved` | Pitfall 5 |
| `test_pad_block_unchanged_golden` | byte-identical pad invariant |
| `test_init_rejects_refresh_s_kwarg` | constructor cleanup |
| `test_refresh_loop_method_removed` | cleanup pin |
| `test_refresh_method_exists_and_is_awaitable` | new API |
| `test_create_calls_caches_create_with_padded_body_and_3600s_ttl` | renamed from 300s |
| `test_refresh_atomic_swap_new_name_then_delete_old` | new replacement test |
| `test_refresh_handles_create_failure_keeps_old` | new graceful degradation test |
| `test_refresh_with_no_prior_create_creates_first_cache` | cold-start branch |
| `test_pad_block_*`, `test_create_stores_*`, `test_invalidate_*` (×3) | carried over unchanged |

**Created `tests/agent/test_cache_mutation_refresh.py` (11 tests):**

| Test | What it pins |
|------|--------------|
| `test_default_constants` | DEBOUNCE_S=5.0, MIN_INTERVAL=30.0 |
| `test_mutation_with_no_callback_is_noop` | optional wiring works |
| `test_mutation_without_running_loop_is_noop` | sync caller safe |
| `test_single_mutation_schedules_refresh_after_debounce` | debounce timing |
| `test_burst_of_mutations_only_fires_once_post_burst` | T-41-02-01 storm guard |
| `test_callback_exception_does_not_kill_registry` | Pitfall 2 isolation |
| `test_min_refresh_interval_guard_delays_when_under_window` | min-interval cap |
| `test_main_no_create_task_for_refresh_loop` | grep gate on __main__.py |
| `test_main_wires_evidence_registry_to_cache_refresh` | wiring smoke |
| `test_register_library_schedules_refresh` | bulk mutation triggers |
| `test_register_library_empty_does_not_schedule` | no-op when nothing changed |

**Created `tests/agent/test_dj_cohost_cache_hit.py` (4 tests):**

| Test | What it pins |
|------|--------------|
| `test_cache_hit_event_logged_when_usage_metadata_present` | basic emission shape |
| `test_cache_hit_event_not_logged_when_zero` | miss = no noise |
| `test_cache_hit_event_not_logged_when_metadata_absent` | early-stream tolerance |
| `test_cache_hit_event_dedupes_within_turn` | per-turn dedupe + new-value re-fire |

**Updated `tests/test_main_smoke.py` (1 assertion flipped):**
- The smoke-03 wiring assertion now asserts the inverse: `"cache.refresh_loop(" not in src` AND `"on_mutation=lambda: cache.refresh()" in src`.

**Net Plan 41-02 test footprint:** 18 (test_cache.py) + 11 (test_cache_mutation_refresh.py) + 4 (test_dj_cohost_cache_hit.py) = **33 tests, all green.**

## Plan 41-04 Coordination

The cache_hit telemetry block inside `dj_cohost.py:llm_node` is bracketed
by clearly-marked comments:

```python
# ---- Plan 41-02 telemetry — Plan 41-04 may refactor this loop further ----
# ...
# ---- end Plan 41-02 telemetry block ----
```

and the per-chunk block:

```python
# ---- Plan 41-02 cache_hit telemetry ---------------------
# ...
# ---- end Plan 41-02 cache_hit telemetry -----------------
```

When Plan 41-04 (LLM→TTS streaming pipe-through) refactors the stream
consumer to push tokens through a sentence-boundary buffer, the executor
can move/wrap the cache_hit telemetry without re-deriving the dedupe
semantics. The `last_cache_hit_emitted` variable lives outside the stream
loop, so refactoring the inner iteration shape (e.g. switching to a
`StreamProcessor` class or moving the loop into a coroutine helper)
only requires preserving the dedupe-state-across-chunks invariant.

The four cache_hit tests are self-contained (they mock
`generate_content_stream` directly, not the LiveKit cascade) — Plan 41-04
will not break them as long as the per-turn dedupe + cache_state field
propagation survive.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `register_library()` also wired into mutation refresh**
- **Found during:** Task 2.
- **Issue:** Plan referenced `EvidenceRegistry.mutate()` as the singular
  trigger — but the codebase uses `write()` for per-observation mutations
  and `register_library()` for bulk library load. Wiring only `write()`
  would have left bulk library-load mutations un-refreshed.
- **Fix:** Hooked `_schedule_refresh()` at the end of both `write()` AND
  `register_library()`. Added two regression tests (`*_schedules_refresh`
  and `*_empty_does_not_schedule`) to pin the behaviour.
- **Files modified:** `src/vibemix/state/evidence_registry.py`.
- **Commit:** `a19483c`.

**2. [Rule 3 — Blocking] no `pytest-asyncio` plugin available**
- **Found during:** Task 2 test design.
- **Issue:** Plan suggested `@pytest.mark.asyncio` for async tests. The
  project doesn't install pytest-asyncio (verified with
  `uv run python -c "import pytest_asyncio"`).
- **Fix:** Tests use the same `asyncio.run(_drive())` pattern that
  pre-existing `test_cache.py` uses. Debounce/min-interval values
  parameterized to small (0.05s / 0.10-0.40s) for sub-second test runs.
- **Files modified:** `tests/agent/test_cache_mutation_refresh.py`,
  `tests/agent/test_dj_cohost_cache_hit.py`.
- **Commit:** `a19483c`, `6f96511`.

### Deferred Issues

- **Smoke-03/04/05/06 fail in worktree environment** — `cohost_v4.py` is
  an untracked POC reference (per project memory note), absent in
  worktree base. Failures are identical on the parent commit `206389e`.
  Documented in
  `.planning/phases/41-gemini-sku-upgrade-latency-stack-v2/deferred-items.md`.
  Smoke-01 (`--version`) and smoke-02 (missing GEMINI_API_KEY) both pass.

- **`CACHE_SHAPE: v2_1 | v3_0` env var override for one-week soak**
  (CONTEXT.md decision) — Plan 41-02 did NOT add this feature flag. The
  rationale: this plan's behaviour change is additive (refresh trigger
  switches; no schema or wire-format change). The legacy refresh path is
  gone after this commit — there's nothing for v2_1 mode to fall back
  to without resurrecting the deleted code. If the soak surfaces an
  issue, the fix is to roll back at the commit level, not behind a flag.
  This was a Rule 4 grey area; defaulting to the simpler shape per
  `gsd-autonomous fully` (CONTEXT memory note: defer instead of pause).

## Threat-Model Coverage

| ID | Status | Pinned by |
|----|--------|-----------|
| T-41-02-01 (callback storm DoS) | mitigated | `test_burst_of_mutations_only_fires_once_post_burst` |
| T-41-02-02 (stale cache content) | accepted | TTL 3600s; Gemini server enforces |
| T-41-02-03 (cross-session leak) | mitigated | existing `clear()` semantics unchanged |
| T-41-02-04 (orphan cache on create failure) | mitigated | `test_refresh_handles_create_failure_keeps_old` |
| T-41-02-05 (telemetry leak) | accepted | only integer token count logged |

No new threat flags discovered during execution.

## Self-Check: PASSED

- File `src/vibemix/agent/cache.py` — VERIFIED
- File `src/vibemix/state/evidence_registry.py` — VERIFIED
- File `src/vibemix/__main__.py` — VERIFIED
- File `src/vibemix/agent/dj_cohost.py` — VERIFIED
- File `tests/agent/test_cache.py` — VERIFIED
- File `tests/agent/test_cache_mutation_refresh.py` — VERIFIED
- File `tests/agent/test_dj_cohost_cache_hit.py` — VERIFIED
- File `tests/test_main_smoke.py` — VERIFIED
- Commit `fd68e88` — VERIFIED
- Commit `a19483c` — VERIFIED
- Commit `6f96511` — VERIFIED
