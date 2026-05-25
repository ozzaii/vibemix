---
phase: 77-wire-connect-the-islands
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - src/vibemix/__main__.py
  - src/vibemix/agent/dj_cohost.py
  - src/vibemix/library/agent.py
  - src/vibemix/library/codex_curate.py
  - src/vibemix/library/mcp_server.py
  - src/vibemix/prompts/matrix.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 77: Code Review Report

**Reviewed:** 2026-05-26
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 77 wired four additive seams: WIRE-01 (grounding `[track:<id>]` injection via a 4-point off-loop dispatch in `dj_cohost.py`), WIRE-04 (`build_curator_instruction` matrix seam consumed lazily by both curator backends), WIRE-05 (gated boot/close memory ingest on the live `main()` path), and WIRE-06 (`load_dotenv(override=True)`).

Most of the wiring is sound and the additive-gating discipline holds: WIRE-06 logs no secret value; no hardcoded model literals were introduced; the lazy-import seam keeps `vibemix.prompts` off the memory storage spine's import boundary; the `[track:<id>]` injection is correctly guarded (`is_cited and track_id`) so only a genuinely cited, library-registered id can be injected (invariant #2 holds — the linter needs no change); the off-loop dispatch reads the clean-audio buffer under the buffer's own `threading.Lock`, so it does not race the audio callback or alias buffers; grounding is consulted strictly read-only and never writes `MusicState` (invariant #1 holds); and `_fire_ingest` calls only `ingest_session`/`run_ingest_sweep` (never retention), so no double-prune, with the close-path `await` correctly inside `async def main()`'s `finally` and gated on `recall_enabled`.

The one serious defect is a stale-citation race in the WIRE-01 dispatch: the seam copies the recall dispatch's structure but the underlying `Grounding` service lacks the generation-token guard that the recall service has — so a timed-out grounding lookup's late executor write can resurrect a stale `[track:<id>]` after `clear()` ran, which is exactly the anti-hallucination class invariant #3 exists to prevent.

## Critical Issues

### CR-01: Stale grounding citation can survive a deadline miss and inject a wrong `[track:<id>]` (invariant #3)

**File:** `src/vibemix/agent/dj_cohost.py:967-992` (with `src/vibemix/library/grounding.py:188-220`)

**Issue:** `_maybe_dispatch_grounding._run()` wraps `loop.run_in_executor(None, grounding.on_event, …)` in `asyncio.wait_for(timeout=_DEADLINE_S)`. On timeout it calls `grounding.clear()`. But `asyncio.wait_for` timing out does **not** stop the executor thread — `grounding.on_event` keeps running and, on completion, does `with self._lock: self._latest = citation` (`grounding.py:206-208`). Because `Grounding` has **no generation token** (`grep` for `_inflight_gen`/`generation`/`token` in `grounding.py` returns nothing — and `clear()` at `grounding.py:216-220` merely nulls `_latest`), the late write happens *after* `clear()` and resurrects a citation that the dispatch already deemed "too late". That stale citation — from a *previous* track's lookup — can then be pulled by a subsequent turn's `llm_node` (`dj_cohost.py:1339-1341`) and injected as `[track:<id>]` for the wrong track. That is a grounded-but-wrong attribution: precisely the hallucination class invariant #3 ("trust the audio — react to real detected events, never invents them") is meant to close.

The recall seam this code claims to "mirror" solved this exact bug (its own CR-04): `MemoryRecall.clear(bump_generation=True)` bumps `_inflight_gen` so the in-flight executor's `_latest = survivors` write fails its token check and is discarded (see `retrieval.py:195-218` and the recall `_run` comment at `dj_cohost.py:1091-1097`). WIRE-01 copied the dispatch wrapper but not the underlying race-discard guard.

**Fix:** Give `Grounding` the same generation-token discipline as `MemoryRecall`, so a clear() invalidates any in-flight write:

```python
# library/grounding.py
class Grounding:
    def __init__(self, embedder, store):
        self._embedder = embedder
        self._store = store
        self._lock = threading.Lock()
        self._latest: Citation | None = None
        self._inflight_gen: int = 0

    def on_event(self, event_type, audio_bytes, *, event_id=None, mime_type="audio/wav"):
        with self._lock:
            my_gen = self._inflight_gen          # snapshot the generation
        citation = identify_playing(
            self._embedder, self._store, audio_bytes,
            event_type=event_type, event_id=event_id, mime_type=mime_type,
        )
        if citation is not None and citation.is_cited:
            with self._lock:
                if my_gen == self._inflight_gen:  # token still valid → not cleared mid-flight
                    self._latest = citation
        return citation

    def clear(self) -> None:
        with self._lock:
            self._inflight_gen += 1               # invalidate any in-flight write
            self._latest = None
```

This makes the deadline-miss `grounding.clear()` at `dj_cohost.py:987`/`991` actually discard the late write, matching the recall contract. Alternatively, latch the citation in the agent task itself (assign `self._latest` only from inside `_run()` after `wait_for` returns successfully) so a timed-out lookup never reaches the latch.

## Warnings

### WR-01: Orphaned `_grounding_task` is never cancelled at shutdown (resource leak)

**File:** `src/vibemix/agent/dj_cohost.py:1000` (and `__main__.py` finally block, ~1356-1438)

**Issue:** `self._grounding_task = asyncio.create_task(_run())` is created per track-aware event but is never cancelled on session shutdown — `grep` shows no `_grounding_task.cancel()` (nor `_recall_task.cancel()`) in any `finally`/`aclose`/shutdown path. A track-aware event firing just before SIGINT leaves the task (and its in-flight executor embed) running with no cooperative cancellation. This mirrors the pre-existing recall task, but WIRE-01 adds a second leaking task. On a clean process exit the executor thread is a daemon and the loop tears down, so this is bounded — but it is still an unclosed background embed + a `Task was destroyed but it is pending` warning risk.

**Fix:** Cancel both task refs in `main()`'s finally (or in an agent `aclose`/shutdown hook), best-effort:

```python
for _t in (getattr(agent, "_grounding_task", None), getattr(agent, "_recall_task", None)):
    if _t is not None and not _t.done():
        _t.cancel()
```

### WR-02: Boot-path ingest task is fire-and-forget with no retained reference (GC-cancellation risk)

**File:** `src/vibemix/__main__.py:1290` (the WIRE-05 boot dispatch — `asyncio.create_task(_session_ipc._fire_ingest("boot"))`)

**Issue:** The return value of `asyncio.create_task(...)` is discarded. Per the CPython docs, the event loop holds only a *weak* reference to a task, so a fire-and-forget task whose reference is dropped can be garbage-collected mid-flight before it completes, silently cancelling the boot ingest. In practice `_fire_ingest` immediately `await`s `loop.run_in_executor`, and the executor future keeps the coroutine's frame alive, so the window is narrow — but the pattern is fragile and the boot ingest could be dropped under GC pressure, leaving `memory.db` un-seeded even with `VIBEMIX_RECALL_ENABLED=1`. (The close path correctly `await`s, so only the boot path is exposed.)

**Fix:** Retain the task on a long-lived name so the loop keeps a strong ref until completion:

```python
if recall_enabled and _session_ipc is not None:
    _boot_ingest_task = asyncio.create_task(_session_ipc._fire_ingest("boot"))
    # keep a reference (e.g. append to a module/main-scope set) until done
```

### WR-03: Turn-end `grounding.clear()` is not inside the `llm_node` `finally`, so a mid-stream exception leaves the latch set

**File:** `src/vibemix/agent/dj_cohost.py:2295-2299` (relative to the `try`/`finally` at 1145/1268)

**Issue:** The turn-end `self._grounding.clear()` (and the sibling `self._recall.clear()` at 2283-2287) live at the function-body tail of `llm_node`, *after* the `finally` at line 1268 (which only clears `_pending_event`). If any uncaught exception is raised in the streaming/lint/emit phase between ~1300 and ~2299, the turn-end grounding clear is skipped and a `[track:<id>]` latch persists into the next turn. The injection guard (`is_cited and track_id`) keeps it from being malformed, but combined with CR-01 this widens the stale-citation window. The next track-aware event's `on_event` does overwrite `_latest`, which mitigates (a HEARTBEAT-only follow-up turn is the exposed case). This matches the pre-existing recall structure, so it is a parity warning, not a regression — but the new grounding clear inherits the same gap.

**Fix:** Move the recall + grounding turn-end clears into a `finally` that wraps the stream/emit body (or add a second `try/finally` around lines ~1300-2299), so the latch is always cleared regardless of how the turn exits.

## Info

### IN-01: `__getattr__` return-type annotation differs between the two curator modules

**File:** `src/vibemix/library/agent.py:434` (`-> str`) vs `src/vibemix/library/codex_curate.py:98` (`-> Any`)

**Issue:** Both modules add a PEP 562 `__getattr__` for the lazily-built system-instruction constants. `agent.py` annotates `-> str` and `codex_curate.py` annotates `-> Any`. Both return strings; the inconsistency is cosmetic but invites confusion about whether non-string attributes are expected. `Any` is correctly imported in both files.

**Fix:** Annotate `codex_curate.__getattr__` as `-> str` for parity (it only ever returns the `_SYSTEM_PROMPT` string), or document why `Any` is used.

### IN-02: `_CURATOR_LENS_TO_MOOD` exposes a `"critique"` lens that no caller passes; docstring/charter say `{tutor, hype, critique}` but the charter elsewhere uses `coach`

**File:** `src/vibemix/prompts/matrix.py:834-837`

**Issue:** `_CURATOR_LENS_TO_MOOD` maps `{"tutor": "teacher", "hype": "hype-man", "critique": "coach"}`. Both curator backends only ever call `build_curator_instruction("tutor")`, so `hype`/`critique` are dead entries for now. The charter naming (per CLAUDE.md / matrix docstring) describes lenses as `{hype, coach, tutor}`, but the dict uses `critique` (not `coach`) as the third key. There is no bug today (the only live call is `"tutor"`), but a future caller passing `"coach"` (the charter word) would hit the `ValueError` guard at 636-640 instead of resolving. This is a naming-drift trap.

**Fix:** Either accept both `"coach"` and `"critique"` as aliases for the `coach` persona, or align the key with the charter vocabulary so the public lens name matches what the rest of the codebase calls it.

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
