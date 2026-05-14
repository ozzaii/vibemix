---
phase: 15-recording-browser-retention-enforcement
plan: 03
subsystem: recording-browser
tags: [tauri, shell-out, path-traversal, capability-allowlist, ui-action-cluster]
requires:
  - tauri/src-tauri/Cargo.toml (tauri-plugin-shell 2.3 — already shipped Phase 11)
  - tauri/src-tauri/tauri.conf.json5 (assetProtocol scope from Plan 15-02 — pattern mirrored)
  - src/vibemix/runtime/config_store.py:_app_data_dir (Python-side recordings root resolver — mirrored exactly in Rust)
  - tauri/ui/src/settings/components/recording-row.ts (renderRecordingRow component shipped Plan 15-04)
  - tauri/ui/src/ipc/client.ts (sendIpcRequest / emitIpc invoke patterns from Phase 11 Wave 4)
provides:
  - tauri/src-tauri/src/recordings.rs (NEW — reveal_in_os + open_input_wav commands + validate_under_root gate + 5 unit tests)
  - tauri/ui/src/ipc/client.ts (revealInOS + openInputWav typed wrappers)
  - tauri/ui/src/settings/components/recording-row.ts (4-button action cluster — replay · reveal · open-external · delete)
  - tauri/ui/src/settings/components/recording-row.spec.ts (Tests 15-18 lock the new buttons + a11y contract)
  - capabilities/default.json shell:allow-open scope extension (defense in depth on top of Rust-side validate_under_root)
affects:
  - Phase 15 ROADMAP success criteria #1 + #2 (reveal-in-Finder + open-input.wav-in-default-app) move from PARTIAL → SHIPPED
  - Phase 15 Plan 04 polish wave: action cluster slot reservation closed; Plan 04 may now platform-detect aria-label copy ("Finder" vs "Explorer") if desired
  - tauri/src-tauri/src/main.rs invoke_handler grew from 12 → 14 commands
  - capability description grew to enumerate the 14 commands + the new path-scope entries
tech-stack:
  added: []
  patterns:
    - tauri-plugin-shell `app.shell().open(...)` (deprecated; acceptable for Phase 15; Phase 21 may migrate to tauri-plugin-opener)
    - std::process::Command direct shell-out for `open -R` + `explorer /select,` (matches macOS "select-in-Finder" semantic)
    - canonicalize-prefix path-traversal gate (canonicalize follows symlinks → escape attempts resolve outside root → rejected)
    - Tauri 2.x snake_case Rust → camelCase JS argument key normalization (sessionDir vs session_dir)
key-files:
  created:
    - tauri/src-tauri/src/recordings.rs (260 lines incl. 5 unit tests)
    - .planning/phases/15-recording-browser-retention-enforcement/15-03-SUMMARY.md
  modified:
    - tauri/src-tauri/src/main.rs (+3 lines: mod decl + 2 handler entries)
    - tauri/src-tauri/capabilities/default.json (+2 path scope entries; description updated)
    - tauri/ui/src/ipc/client.ts (+45 lines: 2 wrapper exports)
    - tauri/ui/src/settings/components/recording-row.ts (+95 lines: SVGs, CSS, 2 buttons, hover-selector extension, header-doc rewrite)
    - tauri/ui/src/settings/components/recording-row.spec.ts (+105 lines: 4 new test cases + mocks)
decisions:
  - resolve_recordings_root mirrors src/vibemix/runtime/config_store.py:_app_data_dir EXACTLY (NOT app.path().app_data_dir() which would append the bundle identifier `world.bravoh.vibemix` and miss the Python-side path)
  - Action cluster grew 64px → 128px (4 icons × 24 + 3 gaps × 8 = 120 + 8 breathing) per impeccable Wave 5.A discipline (Plan 15-03 Step 2 spec)
  - Reveal aria-label fixed to "in Finder" (macOS-biased) — acceptable for v0.1.0-rc1 launch target; Plan 15-04 polish wave may platform-detect
  - All 3 info buttons (replay/reveal/open-external) share the silk-65→amber hover ink-flip via combined selector, NOT three separate hover rules — single source of truth for hover discipline
  - Linux explicitly returns Err("unsupported platform") — fail-loud per CLAUDE.md §Constraints, never silently accept on unsupported OS
  - Test file lives at tauri/src-tauri/src/recordings.rs as `mod tests` (Rust convention) NOT tests/sidecar/test_reveal_in_os_command.rs (which is the Python tests dir; Cargo wouldn't pick it up)
metrics:
  duration_minutes: ~25
  completed: 2026-05-14T03:14Z
  tasks_completed: 2
  files_created: 1
  files_modified: 5
  cargo_unit_tests_added: 5
  vitest_cases_added: 4
---

# Phase 15 Plan 03: Reveal-in-OS + Open-Input.wav Tauri Commands — Summary

Closed Phase 15 ROADMAP success criteria #1 (reveal a session row in Finder/Explorer) and #2 (open `input.wav` in the OS default audio app) by shipping two `#[tauri::command]` Rust shell-outs gated by a canonicalize-prefix path-traversal check, two typed TS wrappers, and a 4-button row action cluster (was 2). The Python sidecar continues to never shell out — all OS interaction lives on the Tauri Rust parent per CONTEXT.md `<specifics>`.

---

## 1. Commands Shipped

### `reveal_in_os(session_dir: String) -> Result<(), String>`

Path: `tauri/src-tauri/src/recordings.rs:108`.

```rust
#[tauri::command]
pub async fn reveal_in_os(_app: AppHandle, session_dir: String) -> Result<(), String>
```

- macOS: `Command::new("open").args(["-R", safe_str]).status()` — Finder opens with the dir pre-selected.
- Windows: `Command::new("explorer").arg(format!("/select,{safe_str}")).status()` — explorer with the dir pre-selected; `/select` + path glued (separating breaks selection).
- Linux: `Err("unsupported platform")` (fail-loud per CLAUDE.md §Constraints).

### `open_input_wav(session_dir: String) -> Result<(), String>`

Path: `tauri/src-tauri/src/recordings.rs:165`.

```rust
#[tauri::command]
pub async fn open_input_wav(app: AppHandle, session_dir: String) -> Result<(), String>
```

- Joins `<recordings_root>/<session_dir>/input.wav`, validates, then calls `app.shell().open(safe.to_string_lossy().to_string(), None)` which delegates to LaunchServices (macOS) / ShellExecute (Windows) — opens whatever the OS associates with `.wav` (Music.app, Audacity, VLC, etc.).

Both commands are registered in `main.rs::tauri::generate_handler![…]` (handler grew from 12 → 14 entries).

---

## 2. Capability Scope

`tauri/src-tauri/capabilities/default.json` — `shell:allow-open` extended:

```json
{
  "identifier": "shell:allow-open",
  "allow": [
    { "url": "https://existential.audio/blackhole" },
    { "url": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture" },
    { "url": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone" },
    { "path": "$APPDATA/vibemix/recordings/**/*" },
    { "path": "$APPLOCALDATA/vibemix/recordings/**/*" }
  ]
}
```

Pattern mirrors the assetProtocol scope shipped in `tauri.conf.json5` Plan 15-02 (both `$APPDATA` and `$APPLOCALDATA` listed for cross-platform safety: macOS both resolve to `~/Library/Application Support`; Windows splits roaming vs local).

The capability is defense-in-depth — the **primary** security gate is `validate_under_root` in `recordings.rs`. The capability allowlist only filters which paths `tauri-plugin-shell` will accept on the `open_input_wav` shell-out path. `reveal_in_os` does NOT touch tauri-plugin-shell (it uses `std::process::Command` directly), so its security depends entirely on the Rust-side gate.

The `description` field in `capabilities/default.json` was updated to enumerate all 14 commands and explain the new path-scope entries.

---

## 3. Path-Validation Gate

```text
fn validate_under_root(candidate: &Path, root: &Path) -> Result<PathBuf, String>
    canon_root  = root.canonicalize()?
    canon_target = candidate.canonicalize()?    // follows symlinks
    if !canon_target.starts_with(canon_root):  return Err("path_traversal_rejected")
    if  canon_target == canon_root:            return Err("path_traversal_rejected")
    return Ok(canon_target)
```

5 unit tests pin every branch (`tauri/src-tauri/src/recordings.rs::tests`):

| # | Test | Defends | Result |
|---|------|---------|--------|
| 1 | `validates_path_under_root_returns_canonical_path` | Happy-path success | PASS |
| 2 | `rejects_traversal_via_dotdot` | `../etc` candidate → resolves outside root → Err | PASS |
| 3 | `rejects_root_itself` | `session_dir = ""` would target root → Err | PASS |
| 4 | `rejects_symlink_escape` | Symlink inside root pointing OUTSIDE → canonicalize follows → Err | PASS |
| 5 | `missing_candidate_returns_target_canon_error` | Bogus session_dir → Err("target canon: …") not panic | PASS |

`cargo test --bin vibemix recordings::` → **5/5 PASS** (full suite: 33/33 PASS, no regressions).

---

## 4. Amber-Reserved Spots Expansion (Accepted Scope Change)

UI-SPEC §"Color" originally enumerated 8 amber-reserved spots. Plan 15-03 Task 2 added **two more elements** that ink-flip silk-65 → amber on hover:

| # | Spot | Added by |
|---|------|----------|
| 9 | reveal-button hover ink-flip + drop-shadow halo | Plan 15-03 Task 2 |
| 10 | open-external-button hover ink-flip + drop-shadow halo | Plan 15-03 Task 2 |

**Scope-change rationale:** The two new info-buttons (reveal + open-external) live in the same action-cluster row as the existing replay button. Restricting amber to ONLY replay would have broken the "info buttons share one hover discipline" rule and forced separate hover rules for visually-equivalent affordances. Sharing the single combined CSS selector (`replay,reveal,open-external`) is cleaner and the amber-hover ink-flip is the established info-affordance pattern.

The `recording-row.ts` header docblock now declares the expansion (5 → 7 amber accents in this component) and points at this SUMMARY for the SPEC-level rationale.

---

## 5. Tauri 2.x `app.shell().open()` Deprecation Note

`tauri-plugin-shell` 2.3.5 marks `Shell::open()` as deprecated in favor of `tauri-plugin-opener`. The compiler emits the deprecation warning at:

- `tauri/src-tauri/src/permissions.rs:29` (`open_screen_recording_settings` — pre-existing)
- `tauri/src-tauri/src/permissions.rs:51` (`open_microphone_settings` — pre-existing)
- `tauri/src-tauri/src/recordings.rs:172` (`open_input_wav` — new in this plan)

Acceptable for Phase 15 closure per the inline note in `Cargo.toml:30`. **Phase 21 binary-shippable gate may migrate** all three call sites to `tauri-plugin-opener` in a single sweep (no behavioural delta — the migration is mechanical).

---

## 6. UI / Action Cluster

Layout shift: `flex 0 0 64px` → `flex 0 0 128px` for `.vmx-rec-row__actions`.

Calculation: 4 icons × 24px + 3 gaps × 8px = 120px + 8px breathing room.

Order left → right: `replay` · `reveal` · `open-external` · `delete`.

Two new inline SVGs added (per UI-SPEC §"Icon library: inline SVG paths" — no icon library import):
- `REVEAL_SVG`: folder outline with a small arrow exiting at the bottom-right.
- `EXTERNAL_SVG`: square outline with an arrow exiting from the top-right corner.

aria-labels:
- `reveal session 2026-05-13 21:04 in Finder` (macOS-biased — Plan 15-04 polish may platform-detect)
- `open input.wav for session 2026-05-13 21:04 in default app`

Click handlers stop propagation (don't toggle row), invoke the wrapper, route errors to `console.error`. The row keyboard handler is unchanged — Enter/Space on the row body still toggles expand; Enter/Space on a button uses default browser focus behavior.

---

## 7. Verification Results

| Check | Result |
|-------|--------|
| `cargo test --bin vibemix recordings::` | 5/5 PASS |
| `cargo test --bin vibemix` (full) | 33/33 PASS (28 pre-existing + 5 new) |
| `cargo build --bin vibemix` | Clean (3 deprecation warnings on Shell::open() — acceptable) |
| `cd tauri/ui && npm run check:ipc` | Clean (codegen + tsc --noEmit both green) |
| `cd tauri/ui && npm run test -- --run src/settings/components/recording-row.spec.ts` | 22/22 PASS (18 pre-existing + 4 new) |
| `cd tauri/ui && npm run test -- --run src/settings/` | 33/33 PASS (no regressions) |
| `grep -rn 'reveal_in_os\|open_input_wav' tauri/src-tauri/src/ tauri/ui/src/ \| wc -l` | 11 (success criterion threshold ≥4) |
| `grep -rn 'revealInOS\|openInputWav' tauri/ui/src/ \| wc -l` | 22 (success criterion threshold ≥3) |

---

## 8. Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test-file location: `tests/sidecar/*.rs` does not match Cargo's test discovery.**
- **Found during:** Task 1 setup
- **Issue:** Plan Step 4 cited `tests/sidecar/test_reveal_in_os_command.rs` as the test home. That directory is the Python sidecar tests dir (contains `__init__.py`, `test_build_sidecar_rename.py`); Cargo cannot pick up Rust integration tests from outside the crate root. The plan's own Step 4 explicitly allows the fallback ("place under `tauri/src-tauri/src/` as `mod tests` inside lib.rs (per Rust convention) — verify the existing pattern in lib.rs first").
- **Fix:** Placed the unit tests inside `recordings.rs` as `#[cfg(test)] mod tests` — matches the existing pattern in `sidecar.rs::tests` and `tray.rs::tests`. Cargo discovers them automatically via `cargo test --bin vibemix`.
- **Files modified:** `tauri/src-tauri/src/recordings.rs` (the test module is in the same file)
- **Commit:** `8ac4c5e`

**2. [Rule 1 - Bug] `app.path().app_data_dir()` would have resolved to a different directory than the Python sidecar writes to.**
- **Found during:** Task 1 implementation
- **Issue:** The plan's Step 1 reference code used `app.path().app_data_dir()` to resolve the recordings root. On macOS Tauri 2.x, that returns `~/Library/Application Support/<bundle_identifier>/` = `~/Library/Application Support/world.bravoh.vibemix/`. But the Python sidecar's `src/vibemix/runtime/config_store.py:_app_data_dir` writes to the LITERAL `~/Library/Application Support/vibemix/` (no bundle ID — the actual on-disk location verified `ls ~/Library/Application Support/` shows `vibemix/`, not `world.bravoh.vibemix/`). So `validate_under_root` would have failed at `target.canonicalize()` for every reveal call (target dir does not exist).
- **Fix:** Wrote `app_data_dir_matching_sidecar()` in `recordings.rs` that mirrors `_app_data_dir` exactly (`$HOME/Library/Application Support/vibemix` on macOS; `$APPDATA/vibemix` on Windows; XDG fallback on Linux/CI). The Python and Rust sides now resolve to the SAME on-disk path.
- **Files modified:** `tauri/src-tauri/src/recordings.rs` (`resolve_recordings_root` + helper)
- **Commit:** `8ac4c5e`

**3. [Rule 3 - Blocking] Worktree had no `tauri/ui/node_modules`, `tauri/ui/dist`, or `tauri/src-tauri/binaries` symlinks.**
- **Found during:** Task 1 verification run
- **Issue:** Worktree mode in Claude Code does not duplicate npm installs, vite-build artifacts, or the PyInstaller sidecar binary. `cargo build` failed at `frontendDist "../ui/dist" doesn't exist` and `binaries/vibemix-core-aarch64-apple-darwin doesn't exist`. `npm run check:ipc` failed at `tsc not found`.
- **Fix:** Symlinked all three from the main repo into the worktree (gitignored — symlinks themselves are not tracked):
  - `tauri/ui/node_modules → /Users/ozai/projects/dj-set-ai/tauri/ui/node_modules`
  - `tauri/ui/dist → /Users/ozai/projects/dj-set-ai/tauri/ui/dist`
  - `tauri/src-tauri/binaries → /Users/ozai/projects/dj-set-ai/tauri/src-tauri/binaries`
- **Files modified:** none in tree (symlinks are gitignored via `node_modules` rule + the dist/binaries dirs are excluded by the existing patterns in the repo).
- **Commit:** none (infrastructure fix, not a code change).

### Authentication Gates

None — pure local development; no external service authentication required.

---

## Self-Check: PASSED

**Files (verified on disk):**
- FOUND: `tauri/src-tauri/src/recordings.rs`
- FOUND: `tauri/src-tauri/src/main.rs` (modified — `mod recordings;` + 2 handler entries)
- FOUND: `tauri/src-tauri/capabilities/default.json` (modified — 2 new path scope entries + description rewrite)
- FOUND: `tauri/ui/src/ipc/client.ts` (modified — 2 new exported wrappers)
- FOUND: `tauri/ui/src/settings/components/recording-row.ts` (modified — 2 new SVGs, 2 new buttons, CSS for 128px cluster)
- FOUND: `tauri/ui/src/settings/components/recording-row.spec.ts` (modified — 4 new test cases)
- FOUND: `.planning/phases/15-recording-browser-retention-enforcement/15-03-SUMMARY.md`

**Commits (verified in `git log --oneline`):**
- FOUND: `8ac4c5e` — feat(15-03): add reveal_in_os + open_input_wav Tauri commands with path-traversal guard
- FOUND: `288f434` — feat(15-03): add revealInOS + openInputWav TS wrappers + 4-button row action cluster

**Test runs (final, clean execution):**
- `cargo test --bin vibemix`: 33/33 PASS
- `cd tauri/ui && npm run test -- --run src/settings/`: 33/33 PASS
- `cd tauri/ui && npm run check:ipc`: clean
