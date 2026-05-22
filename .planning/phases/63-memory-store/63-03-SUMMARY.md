---
phase: 63-memory-store
plan: 03
subsystem: database
tags: [memory.db, retention, delete-cascade, path-traversal, orphan-reconcile, sqlite-vec, storage-spine, STORE-03]

# Dependency graph
requires:
  - phase: 63-02
    provides: "MemoryStore facade (add_record / query_topk / minimal delete_session) + SqliteVecMemoryStore vec0 backend + numpy fallback + moments table; lazy app_data_dir invariant"
  - phase: 15 (recordings)
    provides: "recordings_index.py — SESSION_DIR_RE + two-layer is_relative_to path-traversal gate + run_retention_sweep ∞-sentinel/best-effort pattern (mirrored, not imported)"
provides:
  - "Hardened MemoryStore.delete_session — path-traversal-defended (separator/../null floor + is_relative_to containment) atomic cascade (single commit covers vec + moments delete on the shared sqlite-vec connection)"
  - "MemoryStore.reconcile_orphans — boot backstop dropping vec records with no moments row (transactional, best-effort)"
  - "MemoryStore.run_retention_sweep + src/vibemix/memory/retention.py::run_memory_retention_sweep — oldest-session-first WHOLE-session eviction under count/age budget (never partial), routed through delete_session"
  - "RetentionSweepResult(deleted, deleted_sessions) NamedTuple"
affects: [64-session-ingest, 65-memory-retrieval-seam, 66-visible-copilot-move]

# Tech tracking
tech-stack:
  added: []  # zero net-new deps — pure stdlib (re, time) + the existing store
  patterns:
    - "Mirror-not-import the recordings_index path-traversal + retention idioms (importing recordings_index risks pulling the live path; copy the shape into memory/)"
    - "Atomic cascade via shared sqlite-vec connection: moments-row delete staged, backend.delete commits both as one transaction; numpy path stays reconcilable by vector-after-metadata ordering"
    - "Whole-session eviction never empties the store — the last surviving session is always retained even when it overshoots the raw count cap"
    - "Lazy retention import inside MemoryStore.run_retention_sweep keeps retention off the import vibemix.memory.store hot path"

key-files:
  created:
    - "src/vibemix/memory/retention.py — run_memory_retention_sweep + RetentionSweepResult (oldest-session-first whole-session eviction)"
  modified:
    - "src/vibemix/memory/store.py — _validate_session_id + SESSION_DIR_RE; hardened atomic delete_session; reconcile_orphans; run_retention_sweep seam"

key-decisions:
  - "Path-traversal gate fires in add_record AND delete_session (the RED test triggers via add_record with a crafted session_id) — not only delete_session as the plan text emphasized"
  - "run_retention_sweep shipped as BOTH a MemoryStore method (the RED test's call surface, defaults caps to None) and the module-level run_memory_retention_sweep in retention.py (production defaults ~10k/180d for boot wiring)"
  - "RetentionSweepResult.deleted is the pruned-MOMENT count (the field the RED test reads), plus deleted_sessions list — adapts the recordings RetentionSweepResult shape to whole-session eviction"
  - "Whole-session granularity never evicts the final surviving session (cap=2 over 3-record sessions retains the newest whole session) — a retention sweep must never empty the store"

patterns-established:
  - "Memory delete/retention mirror the recordings_index gate + sweep idioms by COPY (the chokepoint rule is about cosine_topk; the FS-safety + sweep shapes are storage and may be copied)"
  - "reconcile_orphans is one-way (drops danglers vec→no-moments; never drops moments→missing-vector) to avoid the more destructive error direction"

requirements-completed: [STORE-03]

# Metrics
duration: 18min
completed: 2026-05-22
---

# Phase 63 Plan 03: Memory Store Hardening Summary

**STORE-03 hardening: a path-traversal-defended, atomic `delete_session` cascade (vectors + `moments` in one transaction, no orphans), a boot `reconcile_orphans` backstop, and `run_memory_retention_sweep` — oldest-session-first WHOLE-session eviction under a per-install count/age budget routed exclusively through `delete_session`. All 19 `tests/memory/` GREEN; the no-live-path import gate stays CLEAN; zero net-new deps.**

## Performance

- **Duration:** ~18 min
- **Completed:** 2026-05-22
- **Tasks:** 2 (both TDD GREEN — the RED contract was authored in 63-01)
- **Files modified:** 2 (1 created, 1 hardened)

## Accomplishments
- **Task 1 — hardened `delete_session` + `reconcile_orphans`:** added `SESSION_DIR_RE` + `_validate_session_id` (a separator/`..`/NUL floor for any session_id plus an `is_relative_to(root.resolve())` containment check that refuses the root itself — mirroring `recordings_index.py:388-401`). Wired the gate into BOTH `add_record` and `delete_session` (the RED path-traversal test triggers through `add_record`). Made the cascade atomic: the `moments`-row delete is staged on the moments connection, then `backend.delete()` commits — on the sqlite-vec path the two share `self.db`, so a SINGLE transaction covers both deletes (no orphaned vectors); on the numpy fallback the vector-after-metadata ordering keeps any crash window reconcilable. Added `reconcile_orphans()` — loads all vec record_ids, drops those with no `moments` row in one transaction, best-effort (never raises on a single bad entry), intended for boot.
- **Task 2 — `run_memory_retention_sweep`:** new `src/vibemix/memory/retention.py` with a `RetentionSweepResult(deleted, deleted_sessions)` NamedTuple and `run_memory_retention_sweep(store, *, max_moments=~10k, max_age_days=~180, now=None)`. Groups `moments` by `session_id` (min/max ts + count), evicts WHOLE sessions OLDEST-FIRST: first any session staler than `max_age_days`, then while total moments exceed `max_moments` the oldest remaining session — never the last surviving one. Both-caps-`None` is an ∞-sentinel no-op short-circuit. Best-effort per session (a single `delete_session` failure logs and continues). Every eviction routes through `store.delete_session` (no partial-session delete, no second ranking path). A thin `MemoryStore.run_retention_sweep` method (caps default to `None`) is the RED test's call surface and delegates lazily.

## Task Commits

1. **Task 1: harden delete_session (path-traversal gate + atomic cascade) + reconcile_orphans** — `18a5c1f` (feat)
2. **Task 2: add run_memory_retention_sweep (oldest-session-first, whole-session eviction)** — `eb5b5b5` (feat)

_TDD note: the RED contract was authored in 63-01 (`dde3c0f`/`5635390`); 63-02 turned the Wave-1 subset GREEN; this plan (Wave 2 GREEN) flips the remaining 9 RED → GREEN._

## Test Results
- `tests/memory/` — **19/19 GREEN** (was 10/19 at the 63-02 tip): the 9 previously-RED (`test_session_id_path_traversal` ×6, `test_retention` ×3) now pass; the 10 already-green stay green (roundtrip, numpy_fallback, delete_cascade, parity ×4, no_live_path static + subprocess, no_extraction + positive control).
- `tests/repo/test_model_literal_gate.py` — green (no model literal introduced).
- `pytest -m parity` — 8 passed (Mac/Win bit-identity intact).
- `grep -rn "import" src/vibemix/memory/ | grep -E "agent|prompts|state.coach|ws_bus|MusicState"` — only a docstring line, NO live-path import; the subprocess dormancy gate prints CLEAN.

## Decisions Made
- **Path-traversal gate in `add_record` too, not just `delete_session`.** The plan text emphasized `delete_session`, but `test_session_id_path_traversal` crafts the bad id and passes it to `store.add_record`. A shared `_validate_session_id` is called from both write paths so a malicious session_id is rejected the moment it could index a path/sibling-DB filename. (Rule 2 — security correctness; the gate's whole point is "before any FS op".)
- **`run_retention_sweep` as a MemoryStore method AND a module function.** The RED tests call `store.run_retention_sweep(max_moments=...)` (a method) and read `result.deleted` (an int). The plan asked for a module-level `run_memory_retention_sweep` + `RetentionSweepResult`. Reconciled by shipping both: `retention.py::run_memory_retention_sweep` holds the logic (production defaults ~10k/180d, ready for boot/session-close wiring); `MemoryStore.run_retention_sweep` is the ergonomic seam the test exercises and defaults caps to `None` (so the no-op test's `max_moments=10_000`-only call leaves the age axis disabled and prunes nothing).
- **`RetentionSweepResult.deleted` = pruned moment count.** The recordings `RetentionSweepResult(deleted_names, bytes_pruned)` shape was adapted to whole-session eviction: `deleted` (the headline pruned-MOMENT total the test reads) + `deleted_sessions` (the evicted ids). Byte accounting is N/A for an in-DB sweep.
- **Never evict the last surviving session.** With cap=2 over 3-record sessions, whole-session granularity can't reach ≤2 without emptying the store; the contract retains the single newest whole session (test `test_retention_evicts_multiple_whole_sessions_when_needed` → `deleted==6`, remaining `{s_new}`). The count loop stops at `len(survivors)-1`.
- **`reconcile_orphans` is one-way.** It drops vec-without-moments danglers (the recoverable direction given the vector-first `add_record` ordering); it never drops a moments row whose vector is missing (the more destructive error, and one the write ordering should never produce).

## Deviations from Plan

### Auto-fixed / reconciled (no scope change)

**1. [Rule 1 — Contract reconciliation] `run_retention_sweep` shipped as a method + module function**
- **Found during:** Task 2.
- **Issue:** The RED tests (`tests/memory/test_retention.py`) call `store.run_retention_sweep(max_moments=...)` and read `result.deleted`, but the plan specified only a module-level `run_memory_retention_sweep` returning `RetentionSweepResult(deleted_sessions, moments_pruned)`.
- **Fix:** Shipped the module-level `run_memory_retention_sweep` (with production caps) as the plan asked, plus a thin `MemoryStore.run_retention_sweep` seam that delegates to it, and named the result field `deleted` (the pruned-moment count) to satisfy the pinned contract.
- **Files modified:** `src/vibemix/memory/retention.py`, `src/vibemix/memory/store.py`.
- **Committed in:** `eb5b5b5` (+ the method seam in `18a5c1f`).

**2. [Rule 2 — Security] Path-traversal gate applied to `add_record` (the RED trigger), not only `delete_session`**
- **Found during:** Task 1.
- **Issue:** The plan focuses the gate on `delete_session`; the RED test triggers rejection through `add_record`.
- **Fix:** Shared `_validate_session_id` invoked from both `add_record` and `delete_session`.
- **Files modified:** `src/vibemix/memory/store.py`.
- **Committed in:** `18a5c1f`.

**Total deviations:** 2 (both contract/security reconciliations to satisfy the pinned RED tests — no behavior/surface beyond what the tests demand, no scope creep).

## Threat Register Status (from PLAN `<threat_model>`)
- **T-63-07 (path traversal via crafted session_id)** — mitigated: `_validate_session_id` (separator/`..`/NUL floor + `is_relative_to` containment + refuse-root), enforced by `test_session_id_path_traversal` ×6.
- **T-63-08 (orphaned vectors after delete)** — mitigated: atomic single-commit cascade + `reconcile_orphans` backstop, enforced by `test_delete_cascade`.
- **T-63-09 (embeddings exempt from retention/delete)** — mitigated: embeddings now subject to the same delete cascade + oldest-first retention sweep as raw artifacts.
- **T-63-10 (unbounded memory.db growth)** — mitigated: per-install count/age budget evicts oldest-session-first.
- **T-63-SC (npm/pip/cargo installs)** — accept (zero net-new deps; no install step).

## KAAN-ACTION (surface, do not block)
- **Call-site wiring (deferred — by plan scope):** wiring `recordings_index.delete → MemoryStore.delete_session` and `boot/session-close → run_memory_retention_sweep` is **deferred to the phase that owns the recordings-UI delete flow** (CONTEXT defers it to avoid importing scope into the storage spine). Phase 63 ships the store contract (`delete_session` / `reconcile_orphans` / `run_memory_retention_sweep`) + their unit tests; the call-sites land downstream. The live reaction path was NOT touched.
- **sqlite-vec clean-VM round-trip (external clock):** prove a `memory.db` write→read round-trip on a clean Mac + Windows (incl. ARM64) VM in the e2e install matrix. The `vec0.*` binary is already signed in shipping builds; `memory.db` is a data file with zero new signing surface. Rides the in-flight Apple-notarization + SignPath approvals — NOT a Phase 63 engineering blocker.

## Deferred / Out-of-Scope Discoveries (pre-existing, NOT introduced by this plan)
The full suite shows **8 failures**, all OUTSIDE `tests/memory/` and unrelated to the `memory/` package (none of the 8 failing test files reference `vibemix.memory`). They are the known WIP-baseline failures on the `live-tuning-or-brain` branch (4 were already documented as pre-existing at `b45b419` in the 63-02 SUMMARY; the rest are branch WIP):
- `tests/repo/test_readme_feature_matrix_sync.py` (×2)
- `tests/repo/test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired`
- `tests/repo/test_cut_release_invokes_bravoh_server.py::test_tag_regex_unchanged_in_this_plan`
- `tests/scripts/test_cut_release_preflight.py` (×2)
- `tests/coach/test_main_anti_slop_wiring.py::test_wire13_anti_slop_disabled_path_passes_none_kwargs`
- `tests/test_main_smoke.py::test_smoke_08_main_source_wires_cache_create_with_graceful_degradation`

Per the SCOPE BOUNDARY rule these are logged here and left untouched — they are not caused by this plan's two `memory/` files.

## Next Phase Readiness
- `MemoryStore.delete_session` is the shippable cascade hook the recordings-delete call-site will call (Phase that owns the recordings-UI delete flow).
- `run_memory_retention_sweep` is ready for boot + session-close wiring (Phase 64 ingest / runtime).
- `reconcile_orphans` is the documented boot backstop for the numpy-path vector-first ordering.
- Storage spine is feature-complete for STORE-01..04; Phase 64 (Session Ingest) can write to `MemoryStore.add_record` with the validation gate now in place.

## Self-Check: PASSED
- `src/vibemix/memory/retention.py` present on disk; `src/vibemix/memory/store.py` contains `is_relative_to`, `_validate_session_id`, `reconcile_orphans`, `run_retention_sweep`.
- Both task commits (`18a5c1f`, `eb5b5b5`) present in git history.
- 19/19 `tests/memory/` GREEN; no-live-path subprocess gate CLEAN; model-literal gate green.

---
*Phase: 63-memory-store*
*Completed: 2026-05-22*
