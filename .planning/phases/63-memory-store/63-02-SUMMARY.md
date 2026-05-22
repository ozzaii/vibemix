---
phase: 63-memory-store
plan: 02
subsystem: database
tags: [sqlite-vec, numpy, cosine-topk, memory.db, gemini-embedding, vec0, storage-spine]

# Dependency graph
requires:
  - phase: 63-01
    provides: "RED-first tests/memory/ contract (add_record / query_topk(*, exclude_session) / delete_session / Record fields / MemoryStore(db_path, prefer_sqlite_vec))"
  - phase: 28 (library)
    provides: "SqliteVecStore, open_store probe, NumpyStore, _cosine.cosine_topk, LibraryEmbedder — the reuse primitives cloned/imported here"
provides:
  - "src/vibemix/memory/ package: storage spine for the v6.0 memory layer"
  - "SqliteVecMemoryStore — vec0 backend over memory.db (vec_memory table + moments sibling on one connection)"
  - "MemoryStore facade — add_record / query_topk(*, exclude_session=None) / delete_session, ranking solely via imported cosine_topk"
  - "open_memory_store() — sqlite-vec probe + numpy fallback, pointed at app_data_dir()/memory.db"
  - "Record dataclass — raw-in/raw-out moment carrier (record_id, session_id, ts, kind, signature, score)"
affects: [64-session-ingest, 65-memory-retrieval-seam, 66-visible-copilot-move]

# Tech tracking
tech-stack:
  added: []  # zero net-new deps — sqlite-vec>=0.1.9 already declared; numpy/google-genai already present
  patterns:
    - "Compose-not-subclass: MemoryStore owns the moments connection; backend is composed, never subclassed"
    - "Single ranking chokepoint: query_topk ranks ONLY through imported cosine_topk (P55 Mac/Win bit-identity)"
    - "Lazy app_data_dir import: defers vibemix.runtime.__init__ so importing the store leaks no live-path module"

key-files:
  created:
    - "src/vibemix/memory/index_sqlite_vec_memory.py — SqliteVecMemoryStore (vec0 + moments)"
    - "src/vibemix/memory/store.py — MemoryStore facade + open_memory_store + Record"
    - "src/vibemix/memory/__init__.py — barrel (MemoryStore, open_memory_store, Record)"
  modified: []

key-decisions:
  - "MEMORY_DB_PATH resolved lazily via _memory_db_path() (not a module-level constant) — importing app_data_dir at module level triggers vibemix.runtime.__init__, which eagerly loads the entire live reaction path (coach loop, ws_bus, state.refresh) and would break the no-live-path invariant"
  - "moments table reuses the sqlite-vec backend's single self.db connection (atomic vec0 + metadata writes); numpy path opens a sibling memory_moments.db since .npy sidecars hold no table"
  - "add_record is vector-first then moments-row then commit — a crash leaves at worst a reconcilable orphan vector, never a metadata row pointing at a missing vector"
  - "exclude_session=None seam shipped AND implemented now (not just accepted-and-unused) — correct filtering before ranking; Phase 65 wires its use"

patterns-established:
  - "memory/ is a sibling of library/ that imports (never forks) the cosine_topk chokepoint, the open_store probe shape, NumpyStore, and LibraryEmbedder"
  - "Storage spine boundary: memory/ imports no live-reaction-path surface and makes no generation-model call (only embed_content via LibraryEmbedder)"

requirements-completed: [STORE-01, STORE-02, STORE-04]

# Metrics
duration: 32min
completed: 2026-05-22
---

# Phase 63 Plan 02: Memory Store Core Summary

**MemoryStore storage spine — a per-install memory.db (sqlite-vec vec0 primary, numpy fallback) with a moments metadata sibling, ranking solely through the imported cosine_topk chokepoint, raw-in/raw-out records, zero net-new deps, and no live-path import.**

## Performance

- **Duration:** ~32 min
- **Started:** 2026-05-22T06:45Z
- **Completed:** 2026-05-22T07:17Z
- **Tasks:** 2
- **Files modified:** 3 (all created)

## Accomplishments
- `SqliteVecMemoryStore` — a near-verbatim clone of `library/index_sqlite_vec.py::SqliteVecStore` with `vec_library`→`vec_memory` renamed in all SQL and a `moments` sibling table + `idx_moments_session` index created on the same connection; the float32 + (768,) dimension-drift guard and `ORDER BY record_id ASC` parity ordering preserved verbatim; no native vec0 KNN.
- `MemoryStore` facade composing the vec0/numpy backend + owning the `moments` connection: `add_record` (vector-first, atomic), `query_topk(query, k=8, *, exclude_session=None)` (ranking only via imported `cosine_topk`), `delete_session` (minimal correct cascade; path-traversal guard + retention land in 63-03).
- `open_memory_store()` — a clone of `library/store.py::open_store` probe-and-fall-through pointed at `app_data_dir()/memory.db`, with numpy sidecar paths derived from `db_path.parent` for tmp_path test isolation.
- Wave-1 contract turned GREEN: `test_add_query_roundtrip`, `test_numpy_fallback`, `test_delete_cascade`, the parity suite (`test_store_parity.py` — sqlite-vec ↔ numpy bit-identical, tie-break, float32 round-trip), `test_no_live_path_import.py` (now CLEAN), `test_no_extraction.py`, and `tests/repo/test_model_literal_gate.py`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Clone vec0 backend as SqliteVecMemoryStore** — `610c374` (feat)
2. **Task 2: MemoryStore facade + open_memory_store + barrel** — `d36d924` (feat)

_TDD note: the RED contract was authored in Plan 63-01 (commits `dde3c0f`/`5635390`); this plan is the GREEN phase that makes the Wave-1 subset pass._

## Files Created/Modified
- `src/vibemix/memory/index_sqlite_vec_memory.py` — vec0 backend over memory.db: `vec_memory` virtual table + `moments` sibling table on one connection; storage-only (no KNN), dimension-drift guard intact.
- `src/vibemix/memory/store.py` — `MemoryStore` facade, `open_memory_store()` probe, `Record` dataclass; `cosine_topk` the sole ranking path; embedding seam via reused `LibraryEmbedder`.
- `src/vibemix/memory/__init__.py` — barrel re-exporting `MemoryStore`, `open_memory_store`, `Record`.

## Decisions Made
- **Lazy `app_data_dir` import (load-bearing).** A module-level `from vibemix.runtime.config_store import app_data_dir` triggers `vibemix.runtime.__init__`, which eagerly imports `coach`, `ws_bus`, `session_loop`, `state.refresh` — the entire live reaction path. That leaked into `sys.modules` and failed `test_no_live_path_import.py::test_importing_memory_loads_no_coach_loop`. Fixed by deferring the import into a function-local `_memory_db_path()` and using `db_path=None` sentinels that resolve lazily. The library subsystem never hit this because it uses `~/.cache` defaults and never imports `config_store`.
- **moments connection sharing:** sqlite-vec path reuses the backend's `self.db` (single-writer, atomic); numpy path opens a sibling `memory_moments.db`.
- **Followed the plan's reuse map exactly otherwise** — `cosine_topk` imported verbatim, `NumpyStore` reused as-is, `open_store` probe cloned, no hardcoded model literal.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Lazy `app_data_dir` import to preserve the no-live-path invariant**
- **Found during:** Task 2 (MemoryStore facade)
- **Issue:** The plan's interface block specified `from vibemix.runtime.config_store import app_data_dir` at module level and `MEMORY_DB_PATH = app_data_dir() / "memory.db"` as a module constant. Importing `vibemix.runtime.config_store` runs `vibemix.runtime.__init__`, which eagerly imports the live reaction path (`coach`, `ws_bus`, `session_loop`, `state.refresh`). This leaked those modules into `sys.modules` on `import vibemix.memory.store`, failing `test_no_live_path_import.py` (the no-live-path import-boundary gate, T-63-01).
- **Fix:** Moved the `app_data_dir` import to a function-local lazy import inside `_memory_db_path()`; changed `MEMORY_DB_PATH` constant to a sentinel-default (`db_path=None`) pattern resolved lazily in `open_memory_store` / `MemoryStore.__init__`. The durable `app_data_dir()/memory.db` semantics are preserved; only the import timing changed.
- **Files modified:** `src/vibemix/memory/store.py`
- **Verification:** `test_importing_memory_loads_no_coach_loop` now prints `CLEAN`; the full Wave-1 subset is GREEN (20 passed).
- **Committed in:** `d36d924` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The auto-fix was necessary to satisfy a Plan-01 invariant (no-live-path import). It changed import timing only, not behavior or the public surface. No scope creep.

## Issues Encountered
- During baseline-confirmation of the 4 pre-existing repo-gate failures (README feature-matrix sync, gate-42 STATE annotation, cut-release tag-regex — all unrelated to `memory/` and failing at the parent commit), an exploratory `git stash pop` accidentally applied an unrelated old worktree-session stash, creating add/add merge conflicts in mascot `.glb` binaries. Recovered cleanly with `git reset --hard HEAD` (both `memory/` commits intact; the stash entry remains preserved in the stash list, nothing lost). No memory/ files were affected.

## Wave-2 Deferral (correctly still RED)
Per plan scope, these stay RED until Plan 63-03 (Wave 2):
- `tests/memory/test_store.py::test_session_id_path_traversal` (6 params) — the session_id path-traversal guard (regex shape + `is_relative_to`, mirroring `recordings_index`) lands in 63-03.
- `tests/memory/test_retention.py` (3 tests) — `run_retention_sweep(max_moments=)` / whole-session eviction lands in 63-03.

Test split confirmed: **10 GREEN / 9 RED** in `tests/memory/`, exactly matching the planned Wave-1 boundary.

## Pre-existing Baseline (NOT introduced by this plan)
4 `tests/repo/` failures fail identically at the parent commit (`b45b419`), unrelated to `memory/`: `test_readme_feature_matrix_sync` (×2), `test_gate_42_hybrid_in_force::test_state_md_phase_16_line_is_annotated_retired`, `test_cut_release_invokes_bravoh_server::test_tag_regex_unchanged_in_this_plan`. No new failures introduced.

## User Setup Required
None - no external service configuration required. (The P63 sqlite-vec clean-VM/sign item remains on the v4.0 external-clock surface per STATE.md — unchanged by this plan; it concerns the binary `.dylib`/`.dll` already in shipping builds, not this data-file code.)

## Next Phase Readiness
- Storage spine ready for Plan 63-03 (Wave 2): `delete_session` is the documented extension point for the path-traversal guard + retention sweep + orphan reconciliation; `add_record` is the natural place for the session_id validation gate.
- Plan 64 (Session Ingest) can write to `MemoryStore.add_record` once 63-03 lands the validation guard.
- `query_topk`'s `exclude_session` seam is shipped and implemented — Phase 65 needs no signature change.

## Self-Check: PASSED
- All 3 created source files + SUMMARY.md present on disk.
- Both task commits (`610c374`, `d36d924`) present in git history.

---
*Phase: 63-memory-store*
*Completed: 2026-05-22*
