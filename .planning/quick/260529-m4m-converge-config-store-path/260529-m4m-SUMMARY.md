---
phase: quick-260529-m4m
plan: 01
subsystem: tauri-rust-config
tags: [config-store, tauri-plugin-store, split-brain-fix, rust]
requires: []
provides:
  - "config::config_store_path() -> Result<PathBuf, String> (pub(crate))"
  - "recordings::app_data_dir_matching_sidecar() promoted to pub(crate)"
affects:
  - "tauri/src-tauri/src/config.rs"
  - "tauri/src-tauri/src/recordings.rs"
  - "tauri/src-tauri/src/updater.rs"
  - "tauri/src-tauri/src/pill_window.rs"
tech-stack:
  added: []
  patterns:
    - "Single shared absolute-path helper for all tauri-plugin-store config.json access"
key-files:
  created: []
  modified:
    - "tauri/src-tauri/src/config.rs"
    - "tauri/src-tauri/src/recordings.rs"
    - "tauri/src-tauri/src/updater.rs"
    - "tauri/src-tauri/src/pill_window.rs"
decisions:
  - "Reuse recordings::app_data_dir_matching_sidecar() rather than duplicate the OS-aware app-data-dir logic — one source of truth for the vibemix/ dir."
  - "updater's check_on_launch_enabled returns bool (not Result), so the helper's Err is folded into the existing default-ON behavior instead of using `?`."
metrics:
  duration: "~12 min"
  completed: "2026-05-29"
  tasks: 2
  files: 4
  commits: 3
---

# Quick 260529-m4m: Converge config.json store path Summary

Fixed the config.json split-brain: all 11 Rust `tauri-plugin-store` call sites now route through a single `config_store_path()` helper that returns the ABSOLUTE `…/vibemix/config.json` path — the same file the Python sidecar writes — instead of a relative `"config.json"` that tauri-plugin-store resolved under the bundle-id `world.bravoh.vibemix/` dir.

## What Was Built

**Task 1 (commit `1148b8fa`)** — shared helper + HOME-pinned test (TDD RED→GREEN):
- `recordings.rs`: promoted `app_data_dir_matching_sidecar()` from `fn` to `pub(crate) fn` (signature-only; no body/doc change).
- `config.rs`: added `use std::path::PathBuf;` and `pub(crate) fn config_store_path() -> Result<PathBuf, String>` delegating to `crate::recordings::app_data_dir_matching_sidecar().map(|d| d.join("config.json"))`, with a doc comment explaining WHY (absolute path forces the plugin onto the sidecar's `vibemix/` dir).
- New unit test `config_store_path_resolves_under_sidecar_vibemix_dir`: pins the macOS path to `$HOME/Library/Application Support/vibemix/config.json` (gated `#[cfg(target_os = "macos")]`) and asserts (all-OS) the path ends with `vibemix/config.json`. Saves the prior `HOME`, sets a `tempfile::TempDir` HOME, computes the path, then restores HOME BEFORE any assertion can panic-unwind (Rust runs tests in parallel; `HOME` is process-global).
- RED was confirmed first: `cannot find function config_store_path in this scope` (E0425) before the helper existed. GREEN after.

**Task 2 (commit `e7006f61`)** — 11 call sites converted, 3 local consts deleted:
- `config.rs`: all 8 store sites (`load_state`, `save_state`, `load_mascot_state`, `save_mascot_state`, `load_bool_key`, `save_bool_key`, `load_primary_surface`, `save_primary_surface`) now `app.store(config_store_path()?)`. Each enclosing fn returns `Result<_, String>`, so `?` is valid. Deleted `const STORE_PATH`.
- `pill_window.rs`: both sites (`load_pill_state`, `save_pill_state`, both `Result`-returning) now `app.store(crate::config::config_store_path()?)`. Deleted `const STORE_PATH`; trimmed the now-false "config.rs is NOT touched by this plan" comment clause.
- `updater.rs`: `check_on_launch_enabled` returns `bool` (NOT Result) → used the plan's `match`-based adaptation: `let path = match crate::config::config_store_path() { Ok(p) => p, Err(e) => { tracing::debug!(...); return true; } };` then `app.store(path)`. The helper's Err folds into the SAME default-ON behavior the existing store-init Err arm uses — failure semantics unchanged. Deleted `const STORE_PATH` and its "Mirrors crate::config::STORE_PATH" doc comment. No new import added (the match does not name PathBuf).

## Verification (exact output)

Run from `tauri/src-tauri`. Note: the crate is `[[bin]]`-only (no lib target), so tests run via `--bin vibemix` (the plan's `--lib` errors with "no library targets found").

```
### cargo check ###
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.16s     (clean, no warnings)

### STORE_PATH code refs across 3 modules (expect 0) ###
0

### config:: tests ###
running 6 tests
test config::tests::config_store_path_resolves_under_sidecar_vibemix_dir ... ok
test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 110 filtered out; finished in 0.00s

### recordings:: tests ###
running 5 tests
test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 111 filtered out; finished in 0.00s

### pill_window:: tests ###
running 4 tests
test result: ok. 4 passed; 0 failed; ...

### clippy total errors (baseline 25, expect 25) ###
25
```

**RED proof (Task 1):**
```
error[E0425]: cannot find function `config_store_path` in this scope
   --> src/config.rs:469:22
```

## Clippy baseline note (important)

`cargo clippy --all-targets -- -D warnings` is RED on the WHOLE pre-change tree (25 errors in `mascot_window.rs`, `sidecar.rs`, `library_cmds.rs`, `tray.rs`, `djay_ax.rs`, `debug_log.rs`, and pre-existing doc-markdown nits — NONE introduced by this change). Per the constraint ("no NEW warnings vs baseline; pre-existing warnings in untouched code don't fail the gate"), I captured the baseline before editing and diffed after:

- **Total tree errors: 25 → 25 (unchanged).**
- **Per-target-file findings identical to baseline:**
  - `config.rs`: 1 finding — the `impl Default for MascotWindowState` nit, baseline at line `94`, now at line `95` (shifted +1 only because Task 1 added `use std::path::PathBuf;`). Same pre-existing lint, not new.
  - `recordings.rs`: lines `96/97/98` (doc-markdown nits) — byte-identical to baseline.
  - `updater.rs`: line `56` (doc-markdown nit) — byte-identical to baseline.
  - `pill_window.rs`: zero findings (unchanged).

My four files introduced **zero new clippy warnings**. The transient `dead_code` warning on `config_store_path()` that existed after Task 1 (helper defined, not yet wired) was resolved by Task 2 wiring all 11 sites — the final tree has no new warnings.

## Deviations from Plan

**1. [Rule 3 - Blocking] Test runner: `--bin vibemix` instead of `--lib`**
- **Found during:** Task 1 verify.
- **Issue:** The plan's verify command `cargo test config::tests --lib` errors with `no library targets found in package vibemix` — the crate is `[[bin]]`-only (`src/main.rs`), tests live in the bin target.
- **Fix:** Ran the tests via `cargo test --bin vibemix config::tests` (and `recordings::` separately, since `cargo test` accepts only one positional TESTNAME filter). No code change; verification-method-only adaptation.
- **Files modified:** none.

No other deviations. The four named files are the only files touched. updater's default-ON-on-error semantics preserved exactly. HOME restored after the test.

## Migration

None. The abandoned `world.bravoh.vibemix/config.json` is dropped. Next launch, Rust reads the unified `vibemix/config.json`; the old Rust-only keys are absent there → `is_first_run` → true (wizard re-shows ONCE — desired for the upcoming ear-pass); other keys → safe defaults. Pre-release, ~0 real users, re-onboarding harmless.

## Effect + adversarial-review hardening (commit `7780322c`)

This converge makes the boot-cache clobber hazard REAL: now that the Rust store and the Python sidecar share one `vibemix/config.json`, ANY Rust `store.set() + save()` that doesn't `reload()` disk→cache first serializes the stale boot snapshot and silently clobbers Python-written `skill`/`mood`/`lens`. Before convergence the two writers never collided (separate files), so this was benign; now it is load-bearing.

An adversarial review of the convergence (2 parallel agents) confirmed:
- **(a) Convergence is COMPLETE** — no leftover relative accessor re-splits the file. Every Rust config.json access routes through `config_store_path()` (absolute); the frontend uses no JS `@tauri-apps/plugin-store` API; the plugin is registered with no pre-declared relative path.
- **(b) A real CLOBBER REGRESSION** — only `save_state` had the `reload()` (from `f6240299`); the other four writers did not. **Commit `7780322c` adds the same `reload()`-before-`set()` to `save_mascot_state`, `save_bool_key`, `save_primary_surface` (config.rs) + `save_pill_state` (pill_window.rs).** `save_pill_state` was the critical one — the pill is draggable in every live session, so its debounced geometry save would clobber concurrent Settings-drawer writes without the reload.

All 5 config.json writers now reload before save → the convergence is SAFE (not a regression that trades a benign split-brain for live data loss). This also validates the earlier (`260529-ifq`) clobber-fix story, which was premised on a single shared file that only now actually exists.

## Out of Scope

Live read/write confirmation (Rust + Python sharing one file across a real wizard run) needs the GUI and is a SEPARATE ear-pass — not done here, per the plan.

## Self-Check: PASSED

- `recordings::app_data_dir_matching_sidecar` is `pub(crate)` — verified in commit.
- `config::config_store_path() -> Result<PathBuf, String>` exists, is `pub(crate)`, delegates to the recordings helper + `.join("config.json")` — verified.
- All 11 store call sites pass the absolute path (8 config + 2 pill_window + 1 updater); 3 local `const STORE_PATH` declarations gone (grep = 0 code refs) — verified.
- updater Err semantics unchanged (default-ON on any path/store failure) — verified by structure.
- New unit test pins the macOS path and restores HOME — green.
- cargo check + targeted tests green; no new clippy warnings vs baseline — verified.
- Both convergence commits exist (`1148b8fa`, `e7006f61`); the adversarial-review hardening commit `7780322c` adds `reload()` to the 4 remaining writers — each commit staged ONLY its named files (shared-tree discipline) — verified.
- Post-hardening: cargo check clean; `config::`/`pill_window::` tests green; reload count = config.rs 4 + pill_window.rs 1 = all 5 config.json writers reload; no new clippy findings on the touched files.
