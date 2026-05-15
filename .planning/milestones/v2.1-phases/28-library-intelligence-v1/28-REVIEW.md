---
phase: 28-library-intelligence-v1
reviewed: 2026-05-15T12:22:19Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - src/vibemix/__main__.py
  - src/vibemix/library/__init__.py
  - src/vibemix/library/_cosine.py
  - src/vibemix/library/budget.py
  - src/vibemix/library/embed.py
  - src/vibemix/library/grounding.py
  - src/vibemix/library/importer.py
  - src/vibemix/library/index_numpy.py
  - src/vibemix/library/index_sqlite_vec.py
  - src/vibemix/library/search.py
  - src/vibemix/library/similar.py
  - src/vibemix/library/staleness.py
  - src/vibemix/library/store.py
  - src/vibemix/ui_bus/__init__.py
  - src/vibemix/ui_bus/messages.py
  - src/vibemix/ui_bus/schemas/library.py
  - tauri/ui/src/settings/SettingsDrawer.ts
  - tauri/ui/src/settings/components/library-panel.ts
  - tauri/ui/src/settings/components/staleness-banner.ts
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 28: Code Review Report

**Reviewed:** 2026-05-15T12:22:19Z
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

Phase 28 (Library Intelligence v1) ships a 9-plan library subsystem: shared cosine math, dual storage backends with Mac/Win parity gate, drag-drop XML import with cancel, vibe-search, event-gated grounding, USER-ASKED similar, 30-day staleness nudge, cost projection + €50 CI gate, and 10 IPC schemas with TS codegen. All 91 library tests + 148 cross-module tests pass.

Code quality is strong: shared cosine path enforces P55 parity contracts via assertion gates, both stores use parameterized SQL throughout, secrets are routed through the proxy client (no AIza-leak in the library tree), the anti-feature `similar_to` rule (LIBRARY-14) is documented and physically enforced (USER-ASKED-only entry points), the cost gate (P56) carries €2.30 headroom with regression tests locking Option B grounding.

Three Warnings: (1) Tauri drag-drop dedupe `Set<number>` grows unboundedly across long-lived sessions; (2) `LibraryImporter._was_cache_hit` reaches into `_embedder._cache` private attribute (encapsulation break); (3) `staleness.save_snooze_state` reads-then-writes JSON without a lock — if another process snoozes concurrently the loser's update wins. Four Info items cover minor quality ticks (unused-keep import in import path, staleness banner unsub timing, `index_numpy.add_batch` sequential fsync, comment about `_decide` precedence).

No blockers. Phase ships green.

## Warnings

### WR-01: Drag-drop `seenEventIds` Set grows unbounded

**File:** `tauri/ui/src/settings/components/library-panel.ts:68`
**Issue:** `seenEventIds` is a `Set<number>` that accumulates every drop event.id seen for the lifetime of the panel handle. The dedupe is correct for back-to-back duplicate fires (Tauri Issue #14134), but in a long-lived session a user who imports many libraries (or who drags many times during exploration) will leak ids forever — not catastrophic, but visible if Settings drawer stays mounted across many drops over a multi-week session. `dispose()` clears the set, but the panel may stay mounted for the entire process lifetime in v1.

**Fix:**
Bound the set to the most recent 64 ids (LRU-ish via FIFO Set semantics):
```typescript
const seenEventIds = new Set<number>();
const SEEN_CAP = 64;
function rememberId(id: number): boolean {
  if (seenEventIds.has(id)) return false;
  seenEventIds.add(id);
  if (seenEventIds.size > SEEN_CAP) {
    // Set iteration is insertion-order — drop the oldest id.
    const oldest = seenEventIds.values().next().value;
    if (oldest !== undefined) seenEventIds.delete(oldest);
  }
  return true;
}
// Replace:
//   if (seenEventIds.has(eventId)) return;
//   seenEventIds.add(eventId);
// with:
//   if (!rememberId(eventId)) return;
```

### WR-02: `LibraryImporter._was_cache_hit` reaches into `_embedder._cache` private

**File:** `src/vibemix/library/importer.py:62`
**Issue:** Importer reads `self._embedder._cache.execute(...)` directly. This couples Importer to LibraryEmbedder's private SQLite handle. If LibraryEmbedder ever switches storage (e.g., adds an in-memory write-through layer per Plan 28.x optimisation), Importer silently breaks. Also bypasses any future cache observability hooks (e.g., per-key lifetime tracking) added inside the embedder.

**Fix:**
Add a public probe on LibraryEmbedder:
```python
# In src/vibemix/library/embed.py, add to LibraryEmbedder:
def has_cached_embedding(self, track: TrackEntry) -> bool:
    """Return True iff a content-hash cache hit would occur for this track."""
    key = self._track_hash(track)
    return self._cache_get(key) is not None
```
Then in importer.py, replace the private reach-through:
```python
was_hit = self._embedder.has_cached_embedding(track)
```
This also lets us drop `_was_cache_hit` and the per-call `_track_hash` re-computation.

### WR-03: `staleness.save_snooze_state` lost-update race on concurrent writers

**File:** `src/vibemix/library/staleness.py:73-102`
**Issue:** Read-modify-write of `state.json` is non-atomic at the data level (the file write is atomic via `os.replace`, but the read+merge+write triple is not). If two sidecar instances run simultaneously (rare but possible — user double-launches the app while the first is still booting) and both apply snooze concurrently, the second writer reads a snapshot that pre-dates the first's commit and overwrites it. Likely harmless for staleness specifically (latest snooze wins is acceptable), but the comment claims "preserves existing keys" — in the race, an unrelated key written by the other process can be lost.

**Fix:**
Either (a) document the single-process assumption explicitly (cheap), or (b) add an advisory file lock around the read+write:
```python
import fcntl  # POSIX; on Windows use msvcrt or skip the lock

def save_snooze_state(snoozed_until_ts: float, state_path: Path | None = None) -> None:
    sp = Path(state_path) if state_path else DEFAULT_STATE_FILE_PATH
    sp.parent.mkdir(parents=True, exist_ok=True)
    lock_path = sp.with_suffix(sp.suffix + ".lock")
    with lock_path.open("w") as lock_f:
        try:
            fcntl.flock(lock_f, fcntl.LOCK_EX)
        except (OSError, AttributeError):
            pass  # Windows or filesystem without flock — degrade gracefully
        # ... existing read + merge + atomic write ...
```
(a) is acceptable for v1 since vibemix is a single-instance desktop app — recommend adding a single-process assumption note in the docstring.

## Info

### IN-01: `_init_cache_schema` called twice for caller-provided `cache_db`

**File:** `src/vibemix/library/embed.py:170-172`
**Issue:** When the caller passes a pre-opened `cache_db`, `LibraryEmbedder.__init__` runs `_init_cache_schema(cache_db)` even though many test paths and `search.py`'s `_open_query_cache` already create the schema. CREATE TABLE IF NOT EXISTS is idempotent so this is a no-op, just slightly noisy. Acceptable as defense-in-depth.

**Fix:** Document as deliberate (defense-in-depth) in the constructor docstring, or skip the init when caller-provided. Either is fine.

### IN-02: Staleness banner subscription unsub timing

**File:** `tauri/ui/src/settings/components/staleness-banner.ts:72-80`
**Issue:** `unsub` is assigned via `.then()` after `subscribeIpc` resolves. If `dispose()` is called before the promise resolves (rapid mount/unmount in tests), the subscription leaks because `unsub` is still `null` at the time `dispose()` runs. Library-panel.ts has the same pattern (line 95-123) but with the same risk-tolerance.

**Fix:**
Track the in-flight promise and await it in dispose:
```typescript
let unsubPromise = subscribeIpc<LibraryStalenessNudge>(...);
// dispose:
async dispose() {
  try { (await unsubPromise)(); } catch {}
}
```
Low priority — disposal during boot-time mount is unlikely in production.

### IN-03: `NumpyStore.add_batch` does two sequential `os.replace` — non-atomic pair

**File:** `src/vibemix/library/index_numpy.py:88-89`
**Issue:** `os.replace(tmp_vec, vectors_path)` and `os.replace(tmp_ids, ids_path)` are two separate atomic ops. A crash between them leaves the pair desynced. The `_load` method's row-mismatch check catches this on next start, but the user loses the in-flight batch. Mac/Win parity test verifies the steady-state, not crash recovery.

**Fix:**
Either (a) accept the constraint and document it in the module docstring (current approach mostly assumes this — the docstring says "Row alignment between the two files is the integrity contract"), or (b) write a single combined sidecar JSON that contains both ids and a base64 vectors blob (loses streaming, gains atomicity), or (c) write a checksum file last and verify on load. (a) is fine for v1 — the failure mode is "lose last batch on power-loss," not "corrupt all data."

### IN-04: `_decide` evaluates `>= 0.7` then `>= 0.6` — comment would help

**File:** `src/vibemix/library/grounding.py:73-78`
**Issue:** `_decide` reads cleanly but the threshold semantics ("cited" requires ≥0.7, "uncertain" requires ≥0.6 AND <0.7, else "below_threshold") are implicit in the if-elif fall-through. A future maintainer adding a fourth band might miss the asymmetric semantics.

**Fix:** Add inline ranges to the docstring, e.g.:
```python
def _decide(cosine: float) -> str:
    """Map cosine similarity to a decision band.

    cosine >= 0.7        → "cited"
    0.6 <= cosine < 0.7  → "uncertain"
    cosine < 0.6         → "below_threshold"
    """
```

---

_Reviewed: 2026-05-15T12:22:19Z_
_Reviewer: Claude (gsd-code-reviewer, inline orchestrator)_
_Depth: standard_
