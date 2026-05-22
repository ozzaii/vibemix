---
phase: 64-session-ingest
reviewed: 2026-05-22T00:00:00Z
depth: deep
files_reviewed: 2
files_reviewed_list:
  - src/vibemix/memory/ingest.py
  - src/vibemix/runtime/session_loop.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 64: Code Review Report

**Reviewed:** 2026-05-22
**Depth:** deep (cross-file: ingest ↔ MemoryStore ↔ embed cache ↔ runtime async wiring)
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the Phase-64 session-ingest module (`src/vibemix/memory/ingest.py`, NEW) and its
runtime wiring (`src/vibemix/runtime/session_loop.py`, MODIFIED). The headline async-correctness
risk flagged in the brief is **clean**: all heavy work (the `memory.ingest` import, the lazy
embedder/`genai` client build, and the FS+embed ingest) runs inside a single
`loop.run_in_executor(None, _worker)` so it never touches the reaction loop, never holds
`state._lock`, never reads `MusicState`; the boot ingest is fired as a ref-kept
`asyncio.create_task` (not awaited inline) so it does not gate IPC readiness; the worker is
try/except-wrapped so a failure cannot crash boot/shutdown. The no-extraction,
no-live-path-import, idempotency (marker + signature-keyed embed cache + A4 moments-count
reconciliation), `citation_strip`-skip, path-traversal, SQL-parameterization, and
one-way-import invariants all hold by direct verification against the cloned sources
(`embed.py`, `store.py`, both vector backends).

Three real defects remain, all in the runtime wiring. None is a security hole or data-loss
risk, so no Critical. The two resource-hygiene findings (un-closed `MemoryStore`, orphaned
boot-ingest task) are genuine leaks worth fixing before ship; the duplicate `except` is dead
code. Four Info items round out quality.

## Warnings

### WR-01: `MemoryStore` constructed in the ingest worker is never closed (sqlite connection / backend leak)

**File:** `src/vibemix/runtime/session_loop.py:898`
**Issue:** `_worker()` does `store = MemoryStore(db_path=None)` and runs the ingest, but never
calls `store.close()`. `MemoryStore.close()` (store.py:459) closes the moments connection (numpy
path) and `self._backend.close()` (the sqlite-vec/numpy backend handle) on every path. Each
session-close trigger and each boot sweep allocates a fresh `MemoryStore` → opens a fresh sqlite
connection to `memory.db` (and, on the numpy fallback, the sibling `memory_moments.db`) that is
never released. Over a long-running app with many session-close events these accumulate as leaked
sqlite handles / file descriptors on the executor threads. The store's own docstring treats it as
a closable resource (`store.close()` is part of the documented API).
**Fix:**
```python
def _worker() -> None:
    try:
        from vibemix.memory.ingest import ingest_session, run_ingest_sweep
        from vibemix.memory.store import MemoryStore

        embedder = self._build_ingest_embedder()
        if embedder is None:
            return
        store = MemoryStore(db_path=None)
        try:
            if trigger == "close" and session_dir is not None:
                result = ingest_session(session_dir, store, embedder)
                log.info(...)
            else:
                ingested = run_ingest_sweep(recordings_root, store, embedder)
                log.info(...)
        finally:
            store.close()
    except Exception:
        log.exception("memory ingest (%s) failed", trigger)
```

### WR-02: Boot-ingest task is orphaned — never declared, never cancelled/awaited at teardown

**File:** `src/vibemix/runtime/session_loop.py:719` (created), `:1309-1320` (teardown omits it)
**Issue:** `run_boot_sweeps` assigns `self._boot_ingest_task = asyncio.create_task(self._fire_ingest("boot"))`,
but (a) `_boot_ingest_task` is not initialized in `__init__` alongside the other task fields
(`_snapshot_task`, `_retention_task`, `_parent_watch_task` at lines 209-211), and (b) `run()`'s
`finally` block only cancels/awaits those three tasks — `_boot_ingest_task` is not in the tuple.
On a fast boot→shutdown the boot ingest is left running on the executor; the `bus.stop()` and
event-loop teardown can race it, producing a "Task was destroyed but it is pending" warning and
an executor thread still mid-embed after the loop closes. The ref-keep prevents mid-flight GC
(good) but nothing ever joins or cancels it.
**Fix:** Declare `self._boot_ingest_task: asyncio.Task | None = None` in `__init__`, and add it
to the teardown tuple:
```python
for task in (
    self._snapshot_task,
    self._retention_task,
    self._parent_watch_task,
    self._boot_ingest_task,
):
    if task is not None:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
```
(The underlying `run_in_executor` future cannot be cancelled mid-run, but cancelling the wrapping
task + awaiting it bounds the teardown and silences the pending-task warning.)

### WR-03: Duplicate unreachable `except Exception:` clause in `_fire_ingest` dispatch

**File:** `src/vibemix/runtime/session_loop.py:922-925`
**Issue:** The dispatch try block has two identical `except Exception:` handlers stacked:
```python
try:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _worker)
except Exception:
    log.exception("memory ingest (%s) dispatch failed", trigger)
except Exception:                                   # <- dead code, unreachable
    log.exception("memory ingest (%s) failed", trigger)
```
The second `except Exception:` (lines 924-925) is statically unreachable — Python evaluates
handlers top-down and the first identical clause always matches first. It parses, but it is dead
code that misleads a maintainer into thinking two distinct failure modes are handled. (The
"...failed" wording also duplicates the worker's own internal `log.exception("memory ingest (%s)
failed", trigger)` at :917, compounding the confusion.)
**Fix:** Delete lines 924-925 (the second `except` block).

## Info

### IN-01: `said:` field embeds the inline citation tokens verbatim alongside the spoken text

**File:** `src/vibemix/memory/ingest.py:130-134`
**Issue:** `build_coach_line_signature` extracts citation tokens into the `cite=` field but
`_EMOTION_TAG_RE.sub("", reaction_text)` only strips a leading `[emotion]` tag — the inline
`[ev:drop]`/`[track:...]` citation brackets remain inside `said:`. So a reaction's citations
appear twice in the signature (once sorted in `cite=`, once inline in `said:`). This is
deterministic (cache-stable) and not a bug, but it slightly muddies the embedded text and the
human-readable signature, and means the embedded vector partly encodes machine tokens rather than
pure spoken language. Defensible as-is given `text=full_text` is what the recorder logs
(dj_cohost.py:1056); flag for the planner only if Phase-65 retrieval quality wants a clean spoken
line.
**Fix:** Optionally strip `EVIDENCE_CITATION_RE` matches from `said:` too:
`said = EVIDENCE_CITATION_RE.sub("", _EMOTION_TAG_RE.sub("", reaction_text)).strip()` — but this
would be a `SIG_TEMPLATE_VERSION` bump (re-embeds all signatures), so only do it deliberately.

### IN-02: `citation_bypass` (heard-but-unverified) lines are silently not ingested

**File:** `src/vibemix/memory/ingest.py:402-405` (cross-ref `src/vibemix/agent/dj_cohost.py:1087`)
**Issue:** The ingest path embeds only `kind=="ai_text"`. The `citation_bypass` path
(dj_cohost.py:1087-1094) logs `kind="citation_bypass"` for lines the DJ *did* hear (the one-shot
unverified bypass). These are skipped by ingest. This is arguably correct (don't memorize an
unverified utterance), and matches the confabulation-guard intent, but it is an undocumented
asymmetry: a line the user heard never reaches memory. Worth a one-line comment so a future
maintainer doesn't "fix" it by adding `citation_bypass` to the embed set.
**Fix:** Add `citation_bypass` to the skip comment at ingest.py:403-404 to document it is an
intentional skip, not an oversight.

### IN-03: Embed-cache read does not validate vector shape (stale-dim row would only fail at write)

**File:** `src/vibemix/memory/ingest.py:256-263`
**Issue:** `_cache_get` returns `np.frombuffer(row[0], dtype=np.float32).copy()` with no shape
assertion. If a cached row predates an `EMBEDDING_DIM` change, it returns a wrong-shaped vector;
the failure surfaces only downstream at `store.add_record → add_batch`'s shape assert, which the
worker's try/except then swallows — leaving that session perpetually un-ingested with only a
logged exception. The cache key includes `SIG_TEMPLATE_VERSION` + `model_id` (which rotates on the
GA-rename dim bump), so in practice a dim change rotates the key and this is unreachable — this
mirrors `embed.py`'s own `_cache_get` (no shape check there either), so it is a faithful clone.
Info-only.
**Fix:** Optional defensive guard mirroring `_cache_put`'s assert:
`if vec.shape != (EMBEDDING_DIM,): return None` so a malformed/stale row is treated as a miss and
re-embedded rather than poisoning the write path.

### IN-04: `model_id` falls back to empty string for a stand-in embedder without `_model`

**File:** `src/vibemix/memory/ingest.py:385`
**Issue:** `model_id = getattr(embedder, "_model", "") or ""` namespaces a `_model`-less embedder
to `""`. This is documented and deliberate (a test stand-in still caches stably under the empty
component). It is safe with the real `LibraryEmbedder` (which always sets `self._model`,
embed.py:301/308). The only latent risk: if two *different* real embedders ever both lacked
`_model`, their caches would collide under `""` — not possible with the current single embedder
class, so Info-only.
**Fix:** None required; the fallback is correct for the shipped embedder. Keep the docstring note.

---

_Reviewed: 2026-05-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
