---
phase: 64-session-ingest
plan: 03
subsystem: runtime
tags: [ingest-wiring, run_in_executor, off-hot-path, one-way-import, best-effort, never-raise, boot-sweep, session-close, no-live-path]

# Dependency graph
requires:
  - phase: 64-session-ingest (plan 02)
    provides: vibemix.memory.ingest.ingest_session / run_ingest_sweep / IngestResult — the off-hot-path ingest surface this plan enqueues
  - phase: 15 (recordings/retention)
    provides: SessionLoop.run_boot_sweeps (:685) + on_session_close (:709) + _fire_one_retention_sweep dispatch idiom (the seams + the run_in_executor pattern mirrored here)
provides:
  - SessionLoop._fire_ingest — the off-loop ingest dispatch helper (boot sweep + single-session close), best-effort/never-raise, recordings_root-None-guarded
  - SessionLoop._active_session_dir — derives the just-finished session dir from active_recorder.session_dir (recorder.py:211)
  - SessionLoop._build_ingest_embedder — lazy best-effort LibraryEmbedder build (proxy or direct genai client; None on no-key/no-proxy → skip)
  - the WIRED INGEST capability — session-close + boot ingest run off the hot path, completing INGEST-02
affects: [65-memory-retrieval, copilot]

# Tech tracking
tech-stack:
  added: []  # ZERO net-new deps — stdlib + shipped in-repo modules only (genai/LibraryEmbedder already ship)
  patterns:
    - "ALL heavy work (memory.ingest import + lazy embedder/store build + ingest call) runs inside a single run_in_executor(None, _worker) — the seam coroutine returns to the loop immediately; nothing heavy touches the reaction loop"
    - "Boot ingest fired as asyncio.create_task (ref-kept) NOT awaited — never gates IPC readiness or starves the periodic retention loop (Pitfall 5)"
    - "Gate-safe one-way arrow: runtime imports memory.ingest function-locally (inside the worker); ingest.py never imports the runtime live path — no-live-path dormancy gate stays CLEAN"
    - "Best-effort / never-raise: the whole worker is try/except + log; a failing ingest can never crash session close or boot (T-64-09)"
    - "Lazy embedder build mirrors __main__: proxy client when VIBEMIX_LLM_MODE=proxy else direct genai.Client from GEMINI_API_KEY; missing key/proxy → None → skip without raising"

# Key files
key-files:
  created:
    - tests/memory/test_ingest_wiring.py
  modified:
    - src/vibemix/runtime/session_loop.py

# Decisions
decisions:
  - "Boot ingest is fire-and-forget (asyncio.create_task), NOT awaited in run_boot_sweeps — awaiting it ran the genai import + embedder build synchronously before the periodic loop started, starving the retention-sweep timing tests; the background task keeps boot/IPC readiness un-gated (Pitfall 5)"
  - "ALL heavy work (incl. the genai import and embedder construction) moved INSIDE the run_in_executor worker, not just the ingest call — the original inline embedder build before run_in_executor blocked the loop thread; the single-worker shape keeps the seam non-blocking"
  - "Close-path session dir = active_recorder.session_dir (recorder.py:211); when no live recorder is attached the close path falls back to the boot-style run_ingest_sweep (the marker makes it a near no-op — idempotent + safe)"
  - "Function-local import inside the worker keeps the exact string 'from vibemix.memory.ingest import ingest_session, run_ingest_sweep' in session_loop.py (acceptance grep) AND honors monkeypatch (the import binds the current module attribute at worker-call time)"

# Metrics
metrics:
  tasks: 2
  files_created: 1
  files_modified: 1
  duration_minutes: ~35
  completed: 2026-05-22
---

# Phase 64 Plan 03: Session-Ingest Runtime Wiring Summary

**One-liner:** Wired the Phase-64 ingest into `SessionLoop` at the two off-hot-path seams — `on_session_close` enqueues a single-session `ingest_session` for the just-finished session (`active_recorder.session_dir`) and `run_boot_sweeps` enqueues `run_ingest_sweep` over the recordings tree — both dispatched through a single `loop.run_in_executor(None, _worker)` that builds the store + lazy `LibraryEmbedder` and calls the ingest entirely off the reaction loop, best-effort and never-raising, with the runtime→`memory.ingest` arrow function-local so the no-live-path dormancy gate stays GREEN. Completes INGEST-02.

## What Was Built

- **`src/vibemix/runtime/session_loop.py`** (modified):
  - **`_fire_ingest(self, trigger, *, session_dir=None)`** — the off-loop dispatch helper, mirroring `_fire_one_retention_sweep`'s shape. Early-returns when `recordings_root is None`. Defines a synchronous `_worker()` that (1) function-locally imports `ingest_session` / `run_ingest_sweep` + `MemoryStore`, (2) builds the embedder lazily (skip if None), (3) constructs `MemoryStore(db_path=None)`, (4) calls `ingest_session(session_dir, store, embedder)` for `close` or `run_ingest_sweep(recordings_root, store, embedder)` otherwise — all wrapped in `try/except + log.exception`. The seam then `await loop.run_in_executor(None, _worker)`, itself wrapped in try/except so the dispatch can never raise.
  - **`_active_session_dir(self)`** — best-effort `Path(active_recorder.session_dir)`; None when no live recorder (close then falls back to the boot-style sweep).
  - **`_build_ingest_embedder(self)`** — lazy, best-effort `LibraryEmbedder` build. Proxy client (`build_proxy_genai_client`) when `VIBEMIX_LLM_MODE=proxy` + `VIBEMIX_PROXY_JWT` present; else direct `genai.Client(api_key=GEMINI_API_KEY)`. Returns None (logged) on missing key/proxy so a no-credential boot/close degrades gracefully.
  - **`run_boot_sweeps`** — after the retention sweep, fires `self._boot_ingest_task = asyncio.create_task(self._fire_ingest("boot"))` (NOT awaited — fire-and-forget so the heavy build never gates IPC readiness or the periodic loop).
  - **`on_session_close`** — after the retention sweep, derives `session_dir = self._active_session_dir()` and `await self._fire_ingest("close", session_dir=session_dir)`.

- **`tests/memory/test_ingest_wiring.py`** (new, 6 tests):
  - **Source-text gate** — asserts `from vibemix.memory.ingest import ingest_session, run_ingest_sweep` + `await loop.run_in_executor(None, _worker)` + the in-worker `ingest_session(...)` / `run_ingest_sweep(...)` calls are present (proof the heavy path is off-loop, not inline).
  - **Off-loop behavioural proof** — monkeypatches `ingest_mod.ingest_session` / `run_ingest_sweep` (recording `threading.get_ident()`), `store_mod.MemoryStore`, and `SessionLoop._build_ingest_embedder` to a fake; drives the close + boot seam coroutines and asserts the recorded executor-thread id != the event-loop thread id.
  - **None-guard** — `recordings_root=None` → neither seam attempts ingest.
  - **Failure-swallow** — a raising ingest stub does not propagate (both seam coroutines return normally).
  - **Close fallback** — `on_session_close` with no live recorder (session_dir None) falls back to `run_ingest_sweep`, not `ingest_session`.

## Verification

- `PYTHONPATH=src python3 -m pytest -q tests/memory` → **35 passed** (the 6 ingest tests, the 6 new wiring tests, no-extraction, no-live-path static + both subprocess dormancy gates, store + parity + retention).
- `tests/memory/test_no_live_path_import.py` → 3 passed; `grep` over `ingest.py` real imports for `session_loop|runtime.session|state.coach|ws_bus|agent|prompts` → empty (the arrow stays one-way).
- `tests/recording/test_periodic_retention_sweep.py` → 11 passed (stable across 3 runs — the fire-and-forget boot ingest no longer perturbs the periodic-loop timing).
- `tests/runtime/test_session_loop.py` → 22 passed.
- Full suite: **8 failed, 4124 passed, 26 skipped** — exactly the documented `live-tuning-or-brain` 8-WIP baseline (coach anti-slop wiring, cut_release tag-regex + preflight ×2, gate_42 STATE.md annotation, readme feature-matrix ×2, main_smoke cache wiring) — NONE related to Phase-64 ingest. No NEW failures.
- `git diff --name-only` since plan start = exactly `src/vibemix/runtime/session_loop.py` + `tests/memory/test_ingest_wiring.py`. No new dep, no model literal, no taxonomy change.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Boot ingest blocked the periodic retention loop (timing regression)**
- **Found during:** Task 2 / full-suite verification.
- **Issue:** The first implementation built the `LibraryEmbedder` (which imports `google.genai`) synchronously in `_fire_ingest` BEFORE the `run_in_executor` call, and `run_boot_sweeps` `await`ed `_fire_ingest("boot")`. The heavy synchronous genai import on the boot path delayed the periodic retention-sweep loop start past the 200ms test window — `test_periodic_sweep_fires_at_interval` / `test_periodic_sweep_respects_stop_event` saw 1 sweep instead of ≥3 (a real regression, confirmed by running the pre-work `session_loop.py` which passed).
- **Fix:** (a) Moved ALL heavy work — `memory.ingest` import, embedder + store construction, and the ingest call — INSIDE a single synchronous `_worker()` dispatched via `await loop.run_in_executor(None, _worker)`, so the seam returns to the loop immediately. (b) Changed `run_boot_sweeps` to fire the boot ingest as `asyncio.create_task(...)` (ref-kept) instead of awaiting it, so the boot path never gates IPC readiness (matches Pitfall 5: "boot sweep must not block startup").
- **Files modified:** `src/vibemix/runtime/session_loop.py`
- **Commits:** `96df78b` (off-loop worker refactor), `e024c8a` (fire-and-forget boot task)

## Threat Surface Scan

No new security-relevant surface beyond the plan's `<threat_model>`. The wiring touches only the existing session-end / boot seams, dispatches dead on-disk artifacts onto an executor thread, and adds no network endpoint, auth path, or schema change. T-64-06 (one-way arrow), T-64-08 (boot non-blocking), T-64-09 (never-raise), T-64-10 (no MusicState/lock) all mitigated as specified.

## Self-Check: PASSED

- `src/vibemix/runtime/session_loop.py` — FOUND (contains `_fire_ingest`, `run_in_executor`, the one-way import).
- `tests/memory/test_ingest_wiring.py` — FOUND (6 tests GREEN).
- Commits: `f871b17`, `d5ac253`, `96df78b`, `e024c8a` — all FOUND in `git log`.
