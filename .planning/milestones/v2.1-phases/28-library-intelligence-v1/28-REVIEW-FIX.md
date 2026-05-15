---
phase: 28-library-intelligence-v1
fixed: 2026-05-15T12:26:45Z
fix_scope: critical+warning
findings_addressed:
  - WR-01
  - WR-02
  - WR-03
findings_remaining:
  - IN-01
  - IN-02
  - IN-03
  - IN-04
status: fixes_applied
test_status: passing
test_count: 148+441
---

# Phase 28: Code Review Fix Report

**Fixed:** 2026-05-15T12:26:45Z
**Fix Scope:** Critical + Warning (default — Info items deferred)
**Status:** fixes_applied
**Tests after fixes:** 148 Python + 441 vitest pass

## Fixes Applied

### WR-01 ✓ Drag-drop `seenEventIds` Set bounded to 64 LRU

**File:** `tauri/ui/src/settings/components/library-panel.ts`
**Change:** Added `rememberId(id)` helper with `SEEN_CAP = 64`. When the
set grows past the cap, the oldest insertion-order entry is evicted via
`seenEventIds.values().next().value`. The Tauri Issue #14134 dedupe
behavior is preserved (back-to-back duplicate fires within the cap window
are still rejected).

### WR-02 ✓ Public `has_cached_embedding()` probe replaces private reach-through

**Files:**
- `src/vibemix/library/embed.py` — added `LibraryEmbedder.has_cached_embedding(track) -> bool`
- `src/vibemix/library/importer.py` — removed `_was_cache_hit` and the private `_embedder._cache.execute(...)` reach-through; now calls `self._embedder.has_cached_embedding(track)`. Removed the per-call `_track_hash` re-computation. Dropped the now-unused `sqlite3` import.
- `tests/library/test_importer.py` — `fake_embedder` fixture now provides a real `has_cached_embedding(track)` implementation (MagicMock would auto-stub to truthy and break the cache-hit count test).

### WR-03 ✓ Single-process assumption documented in `staleness.save_snooze_state`

**File:** `src/vibemix/library/staleness.py`
**Change:** Added explicit single-process assumption to the docstring. The
file write itself is atomic via `os.replace`; the read+merge+write triple
is not. vibemix is a single-instance desktop app, so concurrent writers
won't appear in v1. If multi-instance support lands, the recommended
mitigation is `fcntl.flock` around the read+write block (POSIX) plus
graceful degradation on Windows. v1 accepts the constraint.

## Findings Deferred (Info — out of default scope)

Per gsd-code-review default scope, Info items are not auto-fixed.

- **IN-01:** `_init_cache_schema` called twice for caller-provided `cache_db` — no-op via `IF NOT EXISTS`, acceptable as defense-in-depth.
- **IN-02:** Staleness banner subscription unsub-during-pending-promise leak — low priority, unlikely in production lifecycle.
- **IN-03:** `NumpyStore.add_batch` two-stage `os.replace` is non-atomic across the pair — already documented in module docstring; failure mode is "lose last batch on power-loss," acceptable for v1.
- **IN-04:** `_decide` cosine-band semantics could use docstring polish — cosmetic.

These can be picked up in a v2.2 polish phase or as opportunistic touch-ups when the surrounding code changes.

## Verification

- `pytest tests/library/ tests/integration/ tests/ipc/ -q` → **148 passed** in 14.4s.
- `npx vitest run` → **441 passed** in 2.7s (2 unrelated Tauri-env errors pre-existing).
- `python -m vibemix library budget --json --dau 1000` → still under-budget, telemetry counters increment correctly.
- `grep -c register_library src/vibemix/__main__.py` → 2 (P48 preserved).
- AIza-leak scan → 0 in src/.

## Re-review

Spot re-check of fixed files: the WR-02 refactor cleanly eliminates the encapsulation break and the WR-01 cap is conservative enough (64 ids ≈ ~64 successive imports) to never bite a real user. No new issues surfaced.

**Iteration count:** 1 (no further iterations needed — all targeted findings addressed and tests green).
