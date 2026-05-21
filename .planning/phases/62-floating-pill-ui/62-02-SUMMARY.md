---
phase: 62-floating-pill-ui
plan: 02
subsystem: config
tags: [tauri, rust, serde, primary_surface, pill, mascot, config-store]

# Dependency graph
requires:
  - phase: 62-01
    provides: "pill_window::create_pill_window (+ transient #![allow(dead_code)]) + PILL_WINDOW_LABEL"
  - phase: 13-02
    provides: "MascotWindowState serde + legacy-decode pattern + create_mascot_window setup branch (the clone source)"
provides:
  - "config::PrimarySurface tri-state enum (default Pill | Mascot | None), lowercase serde rename"
  - "config::load_primary_surface (absent key -> Pill) + config::save_primary_surface (forward-compat)"
  - "main.rs setup() surface-selection branch: pill (default) | mascot (opt-in) | none, all non-fatal"
affects: [62-04 (pill.html the pill window points at), pill Settings flip (future), tray (targets live overlay)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Closed serde tri-state enum with #[default] variant + lowercase rename mirroring MascotWindowState"
    - "Surface selection at startup via match on load_primary_surface().unwrap_or_default() — tampered/missing config falls back to safe default"

key-files:
  created: []
  modified:
    - "tauri/src-tauri/src/config.rs"
    - "tauri/src-tauri/src/main.rs"
    - "tauri/src-tauri/src/pill_window.rs"

key-decisions:
  - "primary_surface default = Pill (Kaan-approved partial reversal of full-screen-mascot for the in-set surface)"
  - "No #[tauri::command] Settings-flip wrappers added — surface choice applies at session start in v1; save_primary_surface kept as a forward-compat helper (scoped #[allow(dead_code)])"
  - "mascot DEMOTED not deleted — PrimarySurface::Mascot still calls create_mascot_window; mascot-audit fence path-scoped and untouched"

patterns-established:
  - "Tri-state surface config: closed enum + default-on-absent + .unwrap_or_default() at the call site so a hand-edited config can never select an out-of-band surface or crash setup (T-62-04)"
  - "Non-fatal overlay-build discipline cloned across all three branches: log but never bail setup (T-62-05)"

requirements-completed: [PILL-02]

# Metrics
duration: 4min
completed: 2026-05-22
---

# Phase 62 Plan 02: primary_surface Tri-State + Surface Selection Summary

**Added the `primary_surface` tri-state config (`pill` default | `mascot` opt-in | `none`) to `config.rs` and wired `main.rs` setup() to create the pill, the mascot, or neither at session start — making the floating pill the primary in-set surface while keeping the mascot buildable on demand and the mascot-audit fence green.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-21T21:39:53Z
- **Completed:** 2026-05-22
- **Tasks:** 3 completed (Task 1 TDD: RED + GREEN; Task 2 wiring; Task 3 fence guard)
- **Files modified:** 3 (config.rs, main.rs, pill_window.rs) + deferred-items.md (notes)

## Accomplishments
- `PrimarySurface { #[default] Pill, Mascot, None }` closed enum with lowercase serde rename ("pill"/"mascot"/"none") + `KEY_PRIMARY_SURFACE = "primary_surface"` alongside the existing `mascot_window` key, exactly mirroring the `MascotWindowState` pattern in the same file.
- `load_primary_surface` (absent key → `Pill` default) + `save_primary_surface` (forward-compat for a future Settings flip), cloning the `load_mascot_state`/`save_mascot_state` shapes.
- `main.rs` setup() now branches on `config::load_primary_surface(&app_handle).unwrap_or_default()`: `Pill` → `pill_window::create_pill_window`, `Mascot` → `mascot_window::create_mascot_window` (existing path preserved), `None` → log no surface. Every branch logs but never bails setup (non-fatal discipline cloned from the mascot, T-62-05).
- Removed the transient `#![allow(dead_code)]` from `pill_window.rs` (62-01 added it; `create_pill_window` is now reachable through the setup branch — module is fully dead-code-free).
- mascot demoted via the config branch, NOT deleted; mascot-audit fence path-scoped and untouched; `mascot.html` byte-stable.

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): failing PrimarySurface serde + legacy-default tests** - `b9bbabb` (test)
2. **Task 1 (GREEN): PrimarySurface enum + load/save helpers** - `a1f71b8` (feat)
3. **Task 2: main.rs surface-selection branch + clear pill_window dead-code allow** - `d197533` (feat)

Task 3 (mascot-audit fence guard) is a verification task with no code change — verified by inspection + grep + the `test_ci_grep_gates.py` pytest mirror; its only artifact is the deferred-items.md note, committed with the plan metadata.

**Plan metadata:** committed with SUMMARY.md + STATE.md + ROADMAP.md.

_TDD note: Task 1 followed RED (`b9bbabb`, compile-fails — `PrimarySurface` undeclared) → GREEN (`a1f71b8`, all 5 config tests pass). No refactor commit needed (code mirrored the established pattern cleanly)._

## Files Created/Modified
- `tauri/src-tauri/src/config.rs` - Added `KEY_PRIMARY_SURFACE`, the `PrimarySurface` tri-state enum (default `Pill`), `load_primary_surface`/`save_primary_surface` helpers, and the two cargo tests (`primary_surface_decodes_legacy_missing_as_pill`, `primary_surface_roundtrips_via_serde_json`).
- `tauri/src-tauri/src/main.rs` - Replaced the unconditional `create_mascot_window` setup block with a `match config::load_primary_surface(...).unwrap_or_default()` surface-selection branch (pill default | mascot | none), all non-fatal. Generalised the "Must run AFTER create_*_window" tray-ordering comment.
- `tauri/src-tauri/src/pill_window.rs` - Removed the transient 62-01 `#![allow(dead_code)]` now that `create_pill_window` is wired into the setup branch.

## Decisions Made
- **Default `Pill`.** The Kaan-approved partial reversal of the shipped full-screen-mascot direction for the in-set surface (62-CONTEXT Area 2). Encoded as `#[default]` on the `Pill` variant.
- **No Settings-flip command in v1.** The plan defers the Settings toggle; surface choice applies at session start. `save_primary_surface` is kept as a forward-compat helper carrying a scoped `#[allow(dead_code)]` (rather than a module-wide allow or an out-of-scope `#[tauri::command]` wrapper) so the build stays warning-free without adding unscoped surface area.
- **mascot demoted, not deleted.** `PrimarySurface::Mascot` still calls `create_mascot_window`; the mascot code path is fully intact (T-62-06).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] save_primary_surface dead-code warning broke the warning-free build goal**
- **Found during:** Task 2 (after removing the module-wide allow from pill_window.rs)
- **Issue:** The plan instructs adding `save_primary_surface` (mirroring `save_mascot_state`) but explicitly defers the Settings-flip command, leaving the helper with no v1 caller → a `dead_code` warning. The mascot's equivalent is reachable via its command wrappers; the pill's is not.
- **Fix:** Added a targeted `#[allow(dead_code)]` on `save_primary_surface` only (with a documenting comment), instead of a module-wide allow or out-of-scope command wrappers. Keeps the crate warning-free while honoring the plan's "no Settings flip in v1" scope.
- **Files modified:** tauri/src-tauri/src/config.rs
- **Commit:** `d197533`

### Plan-vs-reality reconciliations (no deviation, noted for the record)
- **`mod pill_window;` already a single full declaration.** The plan's Task 2 anticipated reconciling a "minimal" 62-01 declaration to a single full one. In reality 62-01 already shipped a single full `mod pill_window;` (main.rs line 27), so no reconciliation was needed — the `== 1` acceptance criterion was already satisfied.
- **Capability snapshot already in sync.** This plan touched NO capability files (diff = 3 Rust src files), and `SNAPSHOT.json` was already regenerated for `"pill"` in `5fe1f6a` before this plan. `pytest -k capability_snapshot` is 7/7 green; no regeneration needed for 62-02. (The stale 62-03 deferred-items note predicting 62-02 would need to regenerate it is now resolved/updated.)

## Verification Results
- `cargo test config::tests` — 5/5 pass (incl. `primary_surface_decodes_legacy_missing_as_pill` + `primary_surface_roundtrips_via_serde_json`).
- `cargo build` — succeeds, **zero warnings** (whole crate compiles with the new setup branch + reconciled module).
- `cargo test` (full crate) — **61/61 pass, 0 failed** (no regressions; baseline was 59 + new pill tests).
- `grep -c create_mascot_window main.rs` = 1 (mascot path preserved); `grep -c load_primary_surface main.rs` = 1; `^mod pill_window` = 1.
- mascot-audit fence: `tests/mascot/test_ci_grep_gates.py` 7/7 green; full mascot pytest mirror 75/75 green; `git diff --name-only` for the plan = only the 3 Rust src files (zero mascot-path files); `mascot.html` byte-stable.

## Threat Model Coverage
- **T-62-04 (Tampering — config value):** mitigated. Closed serde enum + `load_primary_surface` absent-key default + `main.rs` `.unwrap_or_default()` on decode error → a tampered/corrupt `primary_surface` value can never crash setup or select an out-of-band surface.
- **T-62-05 (DoS — overlay-build failure):** mitigated. All three branches log but never bail setup; the main session UI comes up even if the chosen overlay fails to build.
- **T-62-06 (Repudiation/regression — mascot silently deleted):** mitigated. `create_mascot_window` still reachable via `primary_surface=mascot`; mascot-audit fence + Task 3 guard prove the path is preserved and `mascot.html` is byte-stable.
- **T-62-SC (package installs):** N/A — this plan added no package (Rust config + setup wiring only; reused shipped `tauri-plugin-store` + serde).

## Known Stubs
None. `save_primary_surface` is a forward-compat helper (no v1 caller, deliberately deferred Settings flip), not a UI-facing stub; it has a real, correct body and a documenting comment. No hardcoded empty values flowing to UI, no placeholder text introduced.

## Self-Check: PASSED
