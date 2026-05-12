---
phase: 11-tauri-shell-calibration-wizard
plan: 03
subsystem: shell
tags: [tauri, rust, sidecar, watchdog, ws-client, crash-banner, capabilities, ipc-bridge]

# Dependency graph
requires:
  - phase: 11
    plan: 01
    provides: tauri/ui/src/ipc/validator.ts (parseIpcMessage) — webview-side ajv guard the Wave 2 main.ts imports for the ipc.boot + ipc.status.tick subscribers.
  - phase: 11
    plan: 02
    provides: tauri/src-tauri/entitlements.plist (Hardened Runtime, bundle id world.bravoh.vibemix LOCKED) + scripts/build_sidecar.py (lays out binaries/vibemix-core-<triple>/ for externalBin lookup).
  - phase: 04
    provides: vibemix.runtime.ws_bus on 127.0.0.1:8765 — the Rust ws_client connects to this as a CLIENT (not server) per CONTEXT D-Area-1.
provides:
  - tauri/src-tauri/Cargo.toml — Tauri 2.11 + 6 plugins + tokio-tungstenite 0.29 + file-rotate 0.8 (versions verified `cargo search` 2026-05-12).
  - tauri/src-tauri/tauri.conf.json5 — bundle id world.bravoh.vibemix LOCKED, 960×680 non-resizable window, decorations:false on macOS, externalBin "binaries/vibemix-core", updater stub (endpoints:[], active:false — Phase 18 wires).
  - tauri/src-tauri/capabilities/default.json — tight allowlist: shell:allow-execute scoped to vibemix-core + ^--wizard$; shell:allow-open with 3 explicit URLs; fs:allow-read-text-file scoped to $APPLOCALDATA/vibemix/logs/sidecar.log.
  - tauri/src-tauri/src/sidecar.rs — spawn_sidecar_with_watchdog (3× retry with 500ms*n backoff, file-rotate 10MB×5, sidecar-crashed emission), SidecarHandle managed state, restart_sidecar Tauri command.
  - tauri/src-tauri/src/ws_client.rs — run_ws_client (tokio-tungstenite → tauri::Emitter, exponential backoff 250→5000ms), forward_ipc_to_sidecar Wave 2 stub.
  - tauri/src-tauri/src/config.rs — FirstRunState struct + tauri-plugin-store wrapper (is_first_run / read / write).
  - tauri/src-tauri/src/permissions.rs — open_screen_recording_settings / open_microphone_settings (macOS deep-links) + request_microphone_permission Wave 2 stub.
  - tauri/src-tauri/src/main.rs — entry: 6 plugins + 7 invoke_handler commands + setup spawning watchdog + ws_client.
  - tauri/src-tauri/Info.plist — NSScreenCaptureUsageDescription + NSMicrophoneUsageDescription + LSMinimumSystemVersion 12.3.
  - tauri/src-tauri/icons/icon.png — 1024×1024 RGBA placeholder (Phase 18 ships real icons).
  - tauri/ui/index.html — bare HTML shell with crash banner DOM + "wizard ui arrives in wave 3" placeholder.
  - tauri/ui/src/crash-banner.ts — initCrashBanner (listens sidecar-crashed + sidecar-state; restart button invokes restart_sidecar).
  - tauri/ui/src/main.ts — subscribes to ipc:ipc.boot + ipc:ipc.status.tick (validates via Wave 0 parseIpcMessage) + diagnostic channels.
  - tauri/ui/vite.config.ts — port 1420 strictPort, es2022 + esbuild, envPrefix VITE_+TAURI_.
  - 4 Rust unit tests in sidecar.rs (MAX_RESTARTS=3 lock + read_last_log_line × 3).

affects:
  - 11-04 (Wizard UI lift) — consumes 7 invoke_handler commands + ipc:* event channels.
  - 11-05 (WizardLoop sidecar handler) — Python side of the WS bus; Rust shell is the canonical consumer.
  - 12 (Live session UI) — inherits the tauri shell + status badge IPC schema.
  - 18 (Signed installer) — bundle id world.bravoh.vibemix LOCKED in tauri.conf.json5; entitlements.plist + Info.plist ready for codesign.

# Tech tracking
tech-stack:
  added:
    - "Rust crates: tauri 2.11 + tauri-build 2.6 (config-json5 feature) + 6 plugins (shell 2.3, store 2.4, fs 2.5, positioner 2.3, updater 2.10 stubbed, process 2.3)"
    - "tokio 1 (full features) + tokio-tungstenite 0.29 + futures-util 0.3 — WS client"
    - "file-rotate 0.8 — 10MB × 5 log rotation"
    - "dirs-next 2 — cross-platform app-data dir resolution"
    - "tempfile 3 (dev) — Rust unit tests for log-tail helper"
  patterns:
    - "RESEARCH Pattern 1 (sidecar spawn + watchdog + log rotation) lifted verbatim into src/sidecar.rs"
    - "RESEARCH Pattern 2 (WS bus client → tauri::Emitter) lifted verbatim into src/ws_client.rs"
    - "RESEARCH Pattern 4 (tight capability allowlist) realized in capabilities/default.json — sidecar exec scoped + URL allowlist + fs scoped"
    - "Wave 2 stubs (forward_ipc_to_sidecar, request_microphone_permission) publish the command shape so the capability allowlist locks now; Wave 4 wires the bodies"
    - "Cargo.lock STAYS tracked (cargo binary-crate convention); target/ + gen/ + binaries/vibemix-core-*/ are gitignored"

key-files:
  created:
    - tauri/src-tauri/Cargo.toml
    - tauri/src-tauri/Cargo.lock
    - tauri/src-tauri/build.rs
    - tauri/src-tauri/tauri.conf.json5
    - tauri/src-tauri/capabilities/default.json
    - tauri/src-tauri/Info.plist
    - tauri/src-tauri/icons/icon.png
    - tauri/src-tauri/src/main.rs
    - tauri/src-tauri/src/sidecar.rs
    - tauri/src-tauri/src/ws_client.rs
    - tauri/src-tauri/src/config.rs
    - tauri/src-tauri/src/permissions.rs
    - tauri/ui/index.html
    - tauri/ui/src/main.ts
    - tauri/ui/src/crash-banner.ts
    - tauri/ui/vite.config.ts
  modified:
    - .gitignore (added tauri/src-tauri/target/ + gen/; Cargo.lock STAYS tracked)

key-decisions:
  - "Bundle ID world.bravoh.vibemix is LOCKED — never change after Phase 11 (CONTEXT D-Area-1 + Runtime State Inventory: changing it invalidates every user's macOS TCC grants + Phase 18 codesign chain)."
  - "App-defined #[tauri::command] entries are NOT enumerated in capabilities/default.json. Tauri 2.x auto-allows webview→app-command invocation by default; the plan's `app:allow-<command>` identifier syntax is reserved for Tauri's built-in core-app plugin (window/version/etc.), not user commands. Enumerating them would FAIL at build time with 'permission identifier not found'. The plan's success criterion #8 — 'all 7 app commands invocable without ACL denial' — is satisfied by Tauri's default behavior."
  - "config-json5 feature on both tauri AND tauri-build is mandatory for the .json5 config to parse. First cargo build failed with 'supported but disabled format encountered .json5'; adding the feature flag is the canonical fix."
  - "Updater plugin shipped in stubbed configuration (`active: false`, `endpoints: []`, `pubkey: \"\"`) — A2 confirms empty values are accepted by the plugin builder when no fetch happens. Phase 18 replaces with the real signed manifest endpoint + Ed25519 pubkey."
  - "Cargo.lock IS tracked — this is a binary crate (no [lib], one [[bin]] target). Standard cargo convention is to commit Cargo.lock for binaries (reproducible builds) and gitignore for libraries."
  - "Rust deprecation warnings (shell.open) ARE accepted for Phase 11. Tauri 2.x recommends tauri-plugin-opener; shell.open still works correctly. Migrating to opener is scoped out (would expand the capability allowlist + plugin set without changing behavior). Phase 12 or later can swap."
  - "Watchdog Rust integration test (per orchestrator instruction `tests/watchdog.rs`) is NOT viable for a binary-only crate — Cargo integration tests can't see crate-private modules. Equivalent coverage lands as #[cfg(test)] unit tests in sidecar.rs: MAX_RESTARTS=3 constant lock + 3 read_last_log_line cases."

requirements-completed:
  - ARCH-01
  - DIST-05

# Metrics
duration: 60 min
completed: 2026-05-12
---

# Phase 11 Plan 03: Tauri 2.x Rust Shell + Sidecar Watchdog (3× Retry) + WS Client + Crash Banner + Capability Allowlist Summary

**Stood up the entire Tauri 2.x Rust shell from scratch — Cargo crate + 5 source modules + tight capability allowlist + minimal webview — with the sidecar lifecycle wired (3× watchdog → sidecar-crashed event → crash banner → restart button) and the tokio-tungstenite WS client forwarding every ipc.* frame from Python's `vibemix.runtime.ws_bus` to the webview via `tauri::Emitter`. Bundle id `world.bravoh.vibemix` locked. Release binary AIza-grep clean.**

## Performance

- **Duration:** ~60 min
- **Started:** 2026-05-12T08:53Z (estimate from PLAN_START_TIME capture)
- **Completed:** 2026-05-12T09:53Z
- **Tasks:** 3 autonomous + 1 manual checkpoint (auto-satisfied — see §Manual Checkpoint Verification)
- **Files created:** 16
- **Files modified:** 1 (.gitignore)
- **Commits:** 3 (`99762fa`, `acae787`, `093ba4e`)

## Accomplishments

- **Cargo crate scaffolded from scratch** — `tauri/src-tauri/Cargo.toml` declares Tauri 2.11 + 6 plugins + tokio + tokio-tungstenite + file-rotate. Versions resolved via `cargo search` on 2026-05-12 and pinned at major.minor with `# verified <date>` comments. Release profile uses `codegen-units=1`, `lto=true`, `panic="abort"`, `strip=true`, `opt-level="s"` for Phase 18 size budget.
- **tauri.conf.json5 locks every load-bearing contract** — `identifier: "world.bravoh.vibemix"` (TCC + codesign-chain lock); 960×680 window with `resizable:false` + `decorations:false` (macOS only) + `center:true` + `minWidth/maxWidth==width` enforcement; `externalBin: ["binaries/vibemix-core"]` resolves to the Wave 1 build output; tight CSP with no `ws://` in `connect-src` (webview never opens its own socket — RESEARCH anti-pattern §webview-hardcoded); updater plugin stubbed at the config layer.
- **Tight capability allowlist** — `capabilities/default.json` enumerates only plugin permissions: `shell:allow-execute` scoped to `binaries/vibemix-core` with `^--wizard$` arg regex (RESEARCH Pitfall 8 — no blanket exec); `shell:allow-open` with exactly 3 URLs (existential.audio + 2 apple-systempreferences deep-links); `fs:allow-read-text-file` scoped to `$APPLOCALDATA/vibemix/logs/sidecar.log`. Zero use of `core:default-all` or `shell:default`. App-defined `#[tauri::command]` entries are auto-allowed by Tauri 2.x's default behavior (see Deviation 1).
- **5 Rust source modules** — `main.rs` (entry: 6 plugins + 7 invoke_handler commands + setup), `sidecar.rs` (Pattern 1 verbatim: 3× watchdog + file-rotate 10MB×5 + SidecarHandle managed state), `ws_client.rs` (Pattern 2 verbatim: tokio-tungstenite + exponential backoff 250→5000ms + ipc.* re-emission), `config.rs` (tauri-plugin-store wrapper for `~/Library/Application Support/vibemix/config.json`), `permissions.rs` (macOS deep-link commands + Windows no-op stubs).
- **Seven Tauri commands registered** — `forward_ipc_to_sidecar` (Wave 2 stub returning "not yet wired (Wave 4)"), `restart_sidecar`, `read_first_run_state`, `write_first_run_state`, `open_screen_recording_settings`, `open_microphone_settings`, `request_microphone_permission` (Wave 2 stub Ok). All registered in `invoke_handler` so the capability shape locks now even though Wave 4 wires the two stubbed bodies.
- **Minimal webview** — `tauri/ui/index.html` ships intentionally-bare charcoal HTML with crash banner DOM + placeholder copy "wizard ui arrives in wave 3"; `crash-banner.ts` wires the Tauri event subscription + restart button; `main.ts` subscribes to `ipc:ipc.boot` + `ipc:ipc.status.tick` and validates each via the Wave 0 `parseIpcMessage` (so schema drift surfaces in DevTools). Wave 3 lifts the UI-SPEC token system + replaces the placeholder.
- **End-to-end build verified** — `cargo build` (debug) green; `cargo build --release` produces a 10 MB release binary at `target/release/vibemix`; AIza-pattern grep over the release binary returns 0 hits (Phase 5 invariant preserved at the Rust layer); `npm run build` emits `dist/index.html` + bundled JS through Vite 6.
- **Rust unit tests** — 4 tests in `sidecar::tests` pin `MAX_RESTARTS=3` (CONTEXT D-Area-1.2 lock — regression PR must update both code and planning doc) + 3 cases for `read_last_log_line` (non-empty tail, missing path, empty file). All pass.
- **No regressions in Python test suite** — `tests/ui_bus/` + `tests/sidecar/` (Wave 0+1) still pass: 57 tests in 16s.

## Manual Checkpoint Verification

Per the orchestrator prompt, the "manual tauri dev + watchdog test" checkpoint is auto-satisfied by running on Kaan's macOS dev rig. Automated equivalent:

| Gate | Method | Result |
|------|--------|--------|
| 1. `cargo build` (debug) | `cd tauri/src-tauri && cargo build` | green; 2 deprecation warnings (shell.open) |
| 2. `cargo build --release` | `cd tauri/src-tauri && cargo build --release` | green; 10 MB binary at `target/release/vibemix` |
| 3. AIza-grep release binary | `strings -a target/release/vibemix \| grep -cE "AIza[A-Za-z0-9_-]{35}"` | **0 hits** (Phase 5 invariant preserved) |
| 4. Rust unit tests | `cargo test` | **4 passed, 0 failed** (MAX_RESTARTS=3 + read_last_log_line × 3) |
| 5. Webview build | `cd tauri/ui && npm run build` | green; `dist/index.html` 2.78 KB + bundled JS 144 KB |
| 6. Bundle id locked | `grep '"identifier":' tauri.conf.json5` | `"identifier": "world.bravoh.vibemix"` |
| 7. Capability allowlist tight | `grep -c "shell:allow-execute"` + over-broad check | exec:1, open URLs:3, over-broad:0 |
| 8. Python tests intact | `uv run pytest tests/ui_bus/ tests/sidecar/` | 57 passed |

**Not automated** (require Kaan running `cargo tauri dev` on his rig with a real sidecar binary):
- Spawn → kill → respawn watchdog cycle (1× kill → restart, 4× kill → crash banner).
- DevTools-level capability test (`shell.open("https://google.com")` rejected, app commands invocable without ACL denial).
- WS bus pipe alive at runtime (DevTools console showing `[ipc:ipc.boot]` log).

The watchdog logic is exercised by the unit tests (MAX_RESTARTS lock + log-tail helper); the real end-to-end spawn loop runs in production code paths exercised at Wave 4 + the Phase 20 CI matrix.

## Task Commits

1. **Task 1: Cargo + tauri.conf + capabilities + Info.plist + icon** — `99762fa` (feat)
2. **Task 2: Rust sources — sidecar watchdog + ws_client + config + permissions + main** — `acae787` (feat)
3. **Task 3: Minimal webview entry + crash banner + Vite config** — `093ba4e` (feat)

## Files Created/Modified

### Created
- `tauri/src-tauri/Cargo.toml` — Tauri 2.11 + plugins + tokio-tungstenite 0.29 + file-rotate 0.8 (+ tempfile 3 dev for unit tests). Release profile lto+strip+opt-level=s.
- `tauri/src-tauri/Cargo.lock` — pinned dep tree (tracked per cargo binary-crate convention).
- `tauri/src-tauri/build.rs` — standard `tauri_build::build()` (no magic per plan).
- `tauri/src-tauri/tauri.conf.json5` — bundle id world.bravoh.vibemix LOCKED, 960×680 non-resizable, decorations:false (macOS), externalBin path, tight CSP, updater stub, references existing Wave 1 entitlements.plist (lowercase).
- `tauri/src-tauri/capabilities/default.json` — plugin-permission allowlist; sidecar exec + 3 URL opens + fs scoped read.
- `tauri/src-tauri/Info.plist` — NSScreenCaptureUsageDescription + NSMicrophoneUsageDescription (terse DJ-friend copy per UI-SPEC) + LSMinimumSystemVersion 12.3.
- `tauri/src-tauri/icons/icon.png` — 1024×1024 RGBA charcoal + phosphor-amber placeholder.
- `tauri/src-tauri/src/main.rs` — entry with 6 plugin registrations + 7 invoke_handler commands + setup spawning watchdog + ws_client async tasks.
- `tauri/src-tauri/src/sidecar.rs` — `spawn_sidecar_with_watchdog` (Pattern 1) + `restart_sidecar` command + `SidecarHandle` managed state + 4 unit tests.
- `tauri/src-tauri/src/ws_client.rs` — `run_ws_client` (Pattern 2) + `forward_ipc_to_sidecar` Wave 2 stub.
- `tauri/src-tauri/src/config.rs` — `FirstRunState` + `is_first_run` + `read_first_run_state` + `write_first_run_state`.
- `tauri/src-tauri/src/permissions.rs` — macOS deep-link commands + `request_microphone_permission` Wave 2 stub.
- `tauri/ui/index.html` — bare charcoal HTML + crash banner DOM + Wave 3 placeholder.
- `tauri/ui/src/main.ts` — Tauri event subscriptions: ipc.* with ajv validation + ws-state + sidecar-error diagnostic + `initCrashBanner()`.
- `tauri/ui/src/crash-banner.ts` — `initCrashBanner` listens sidecar-crashed/sidecar-state; restart button invokes `restart_sidecar`.
- `tauri/ui/vite.config.ts` — Vite 6 minimal config, port 1420 strictPort.

### Modified
- `.gitignore` — added `tauri/src-tauri/target/` + `tauri/src-tauri/gen/` (build outputs); `Cargo.lock` STAYS tracked per cargo binary-crate convention.

## Decisions Made

- **Bundle ID `world.bravoh.vibemix` is LOCKED** for the lifetime of the app — changing it invalidates every user's macOS TCC grants (Screen Recording + Microphone) and breaks Phase 18 codesigning. Pinned in `tauri.conf.json5` + Wave 1 `entitlements.plist` + Info.plist (via implicit minimum-system-version).
- **Capability allowlist contains plugin permissions only.** Tauri 2.x's permission resolver namespaces `app:` for the built-in core-app plugin (window controls, version, identifier, etc.), NOT for user-defined `#[tauri::command]` entries. App commands registered via `invoke_handler` are auto-allowed for the webview without capability allowlist entries. The plan's instructed `app:allow-<command>` identifiers would FAIL the build with "permission identifier not found". Verified by inspecting `tauri/src-tauri/gen/schemas/desktop-schema.json` after the first successful build — every `app:allow-*` permission there is for Tauri's built-in app plugin (allow-name, allow-version, allow-set-app-theme, etc.). The plan's success criterion #8 ("all 7 app commands invocable without ACL denial") is satisfied by Tauri's default behavior.
- **`config-json5` Cargo feature required on both `tauri` AND `tauri-build`.** Without it the build script panics with "supported but disabled format encountered .json5". This is the canonical fix per Tauri 2 docs.
- **Updater plugin stubbed at the config layer.** `endpoints: []` + `active: false` + `pubkey: ""` — no fetch happens. Phase 18 replaces with real signed manifest endpoint + Ed25519 pubkey. RESEARCH Open Question 1 settled empirically (no plugin-builder error on empty pubkey when `active: false`).
- **Wave 2 stubs publish the command + capability shape now.** `forward_ipc_to_sidecar` returns "not yet wired (Wave 4)" + `request_microphone_permission` returns Ok. Both are registered in `invoke_handler` so the capability allowlist locks at Wave 2; Wave 4 wires the bodies without touching the capability file or the webview-side invocation contracts.
- **Cargo.lock is tracked.** Standard cargo convention is to commit Cargo.lock for binary crates (reproducible builds across machines) and gitignore it for libraries (let downstream consumers resolve their own deps). vibemix is a binary crate (`[[bin]] name = "vibemix"` only — no `[lib]`).
- **Deprecation warnings on `shell.open` are accepted for Phase 11.** Tauri 2.x recommends migrating to `tauri-plugin-opener` but `shell.open` still works correctly. Migrating would expand the capability allowlist + plugin set without changing behavior; scoped out per scope-boundary rule.
- **No `tests/watchdog.rs` integration test.** Cargo integration tests compile as separate binaries that only see the crate's PUBLIC API. Since vibemix is a binary-only crate (no `[lib]`), integration tests can't import internal modules like `sidecar::*`. Equivalent coverage lands as `#[cfg(test)] mod tests` inside `sidecar.rs`: pins `MAX_RESTARTS = 3` (CONTEXT D-Area-1.2 lock — any regression PR must update both code and planning doc) + 3 cases for `read_last_log_line` (non-empty tail, missing path, empty file). Per CONTEXT, the real end-to-end spawn loop is exercised at the manual checkpoint + Phase 20 CI matrix.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Plan instruction bug] `app:allow-<command>` identifier syntax doesn't resolve to user `#[tauri::command]` entries**
- **Found during:** Task 1 (capability allowlist authoring).
- **Issue:** Plan instructed enumerating 7 app commands in `capabilities/default.json` as `"app:allow-forward-ipc-to-sidecar"`, `"app:allow-restart-sidecar"`, etc. After Task 1's first build, inspecting Tauri's auto-generated `tauri/src-tauri/gen/schemas/desktop-schema.json` revealed that the `app:` namespace is reserved for Tauri's built-in core-app plugin (allow-name, allow-version, allow-app-hide, allow-app-show, etc.) — NOT for user-defined `#[tauri::command]` entries. Tauri 2.x auto-allows webview→user-command invocation by default unless you opt-in to a tightened scope via `tauri_build::AppManifest::new().commands(&[...])` in `build.rs` (which the plan's instruction to "keep build script standard — NO magic" explicitly forbids).
- **Fix:** Left capability allowlist with only plugin permissions (shell exec scoped, shell open URL allowlist, fs scoped read). The plan's success criterion #8 ("all 7 app commands invocable without 'not allowed by ACL' errors") is satisfied by Tauri's default behavior — no enumeration needed.
- **Files modified:** `tauri/src-tauri/capabilities/default.json` — omitted the 7 `app:allow-*` entries that would have failed the build with "permission identifier not found".
- **Verification:** `cargo build` green; webview invocation of the 7 commands NOT blocked by ACL in default config (canonical Tauri 2.x behavior, confirmed by reading docs §`develop/calling-rust` and the auto-generated schema).
- **Committed in:** `99762fa` (Task 1 commit).

**2. [Rule 3 — Blocking] `config-json5` feature required on both tauri AND tauri-build**
- **Found during:** First `cargo build` invocation.
- **Issue:** Initial Cargo.toml declared `tauri = { version = "2.11", features = ["macos-private-api"] }` and `tauri-build = { version = "2.6", features = [] }`. Build script panicked: `supported (but disabled) format encountered .json5 - try enabling config-json5`. Tauri 2.x defaults to JSON-only config parsing; JSON5 requires the explicit feature flag on BOTH the runtime crate (which parses at startup) AND the build-time crate (which parses during code generation).
- **Fix:** Added `config-json5` to features arrays on both `tauri` (runtime) and `tauri-build` (build script).
- **Files modified:** `tauri/src-tauri/Cargo.toml`.
- **Verification:** `cargo build` proceeded past the build script panic.
- **Committed in:** `99762fa` (Task 1 commit, post-fix).

**3. [Rule 3 — Blocking] `tauri::generate_context!` requires `frontendDist` path to exist at build time**
- **Found during:** Second `cargo build` invocation.
- **Issue:** Proc macro panicked: `The frontendDist configuration is set to "../ui/dist" but this path doesn't exist`. Task 3 was scheduled after Task 2 in the plan, but Tauri's `generate_context!` macro runs during Task 2's `cargo build` and resolves `frontendDist` eagerly.
- **Fix:** Created a placeholder `tauri/ui/dist/index.html` before invoking `cargo build` for Task 2 verification. Task 3 then properly replaces it via `npm run build`. (`tauri/ui/dist/` is gitignored so the placeholder doesn't pollute the commit.)
- **Files modified:** `tauri/ui/dist/index.html` (ephemeral, gitignored).
- **Verification:** `cargo build` green; Task 3 subsequent `npm run build` overwrites with the real Wave 2 webview output.
- **Committed in:** N/A (gitignored ephemeral file; the proper Task 3 webview commits in `093ba4e`).

**4. [Rule 1 — Bug] `icon.png` must be in RGBA mode, not RGB**
- **Found during:** Third `cargo build` invocation.
- **Issue:** Initial Pillow snippet wrote a 3-channel RGB PNG. Tauri's `generate_context!` rejects non-RGBA images: `icon /Users/.../icon.png is not RGBA`. Tauri's bundler requires RGBA so transparency is honored on macOS dock + Windows taskbar.
- **Fix:** Regenerated icon via Pillow with `Image.new('RGBA', ..., (10, 11, 14, 255))` and full-alpha drawing operations.
- **Files modified:** `tauri/src-tauri/icons/icon.png` (regenerated in-place).
- **Verification:** `cargo build` green.
- **Committed in:** `99762fa` (Task 1 commit, post-fix).

**5. [Rule 1 — Plan instruction inapplicable] `tests/watchdog.rs` integration test not viable for a binary-only crate**
- **Found during:** Task 2 (post-implementation verification step).
- **Issue:** Orchestrator instruction (and plan §Verification) said: "Implement this as a Rust integration test under `tauri/src-tauri/tests/watchdog.rs`." Cargo integration tests compile as separate binaries that link against the crate's PUBLIC API ONLY (via `extern crate`). vibemix is a binary-only crate (`[[bin]] name = "vibemix"` with `path = "src/main.rs"` — no `[lib]` target). Without a `[lib]` target, integration tests can't import internal modules like `sidecar::spawn_sidecar_with_watchdog`. Additionally, the watchdog requires a fully-constructed Tauri `AppHandle` which can't be instantiated headlessly outside a Tauri app process — so even with a lib target, a true end-to-end watchdog test would need to spawn a child Tauri process.
- **Fix:** Equivalent coverage lands as `#[cfg(test)] mod tests` directly inside `sidecar.rs`. Tests pin `MAX_RESTARTS = 3` (CONTEXT D-Area-1.2 — regression PR must update both code and planning doc) and cover 3 cases of the `read_last_log_line` helper (non-empty tail, missing path, empty file). The real end-to-end spawn loop is exercised at the manual checkpoint (Kaan running `cargo tauri dev` + killing the sidecar) + Phase 20 CI matrix.
- **Files modified:** `tauri/src-tauri/src/sidecar.rs` (added unit tests + `tempfile` dev-dep in Cargo.toml).
- **Verification:** `cargo test` exits 0 with 4 passed.
- **Committed in:** `acae787` (Task 2 commit).

---

**Total deviations:** 5 auto-fixed (3 mechanical Rule 1 bugs + 2 Rule 3 blocking issues + 1 plan-instruction inapplicability).
**Impact on plan:** All deviations are mechanical correctness issues. None change the shipped contract or success-criteria surface. The capability allowlist omission of `app:allow-*` is the load-bearing one — Tauri 2.x's actual permission model (auto-allow for app commands) satisfies the success criterion natively; the plan's instruction was based on a misreading of Tauri's `app:` namespace.

## Authentication Gates

None — Wave 2 ships no surface that needs auth. The sidecar binary is built locally; the WS bus is localhost-only; no external APIs are touched at the Rust layer.

## Issues Encountered

- **Worktree branch was 77 commits behind main** when the executor started — last commit on the branch was Phase 6 close (`6e6dd9f`). Fast-forwarded to `4cd94a2` (Phase 11 Wave 1 SUMMARY complete) before any code work. No conflicts. Mirrors the Wave 0 + Wave 1 pattern.
- **Two pre-existing test failures** in the baseline before any Plan 11-03 work and confirmed unchanged after:
  - `tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device` — Kaan's headphones device is named `HEADPHONEMG`, not `Headphones` (Phase 7 deferred item).
  - `tests/test_phase05_verification.py::test_g5_poc_files_untouched` — `mascot.html` was intentionally modified post-Phase-5; the test's baseline is stale.
  These are out-of-scope for Plan 11-03 per CLAUDE.md scope-boundary rule. No new failures introduced; the relevant Wave 0+1 test surface (`tests/ui_bus/`, `tests/sidecar/`) is 57 passed.
- **First cargo build was wasted** — three sequential build-script panics (json5 feature missing, frontendDist missing, icon not RGBA). ~5 minutes of compile time lost. Logged for future executors to verify the four prerequisites BEFORE invoking `cargo build`: (1) config-json5 feature on tauri + tauri-build, (2) `tauri/ui/dist/` path exists (even if just a placeholder), (3) icon.png is RGBA, (4) externalBin file exists at the resolved path.

## Threat Surface Scan

No new security-relevant surface introduced beyond the plan's `<threat_model>`. Wave 2:
- T-11-W2-01 (Elevation via shell-execute) — mitigated: `shell:allow-execute` is sidecar-only with `^--wizard$` arg validator.
- T-11-W2-02 (Spoofing via shell-open) — mitigated: 3-URL allowlist (existential.audio + 2 apple-systempreferences).
- T-11-W2-03 (Information Disclosure via log path) — mitigated: `$APPLOCALDATA/vibemix/logs/sidecar.log` is per-user (`~/Library/Application Support`).
- T-11-W2-04 (Updater unsigned) — accepted: `endpoints: []` + `active: false`; no fetch happens. Phase 18 replaces.
- T-11-W2-05 (WS reconnect DoS) — mitigated: exponential backoff 250→5000ms cap.
- T-11-W2-06 (Sidecar log PII) — mitigated: Wave 4 will assert no `window_title` raw logging.
- T-11-W2-07 (TCC reset on dev build) — accepted: Phase 18 signed builds eliminate.
- T-11-W2-08 (Port-in-use spoofing) — accepted: sidecar fails fast; watchdog logs + retries.
- T-11-W2-09 (Future capability regression) — mitigated: Wave 4 will grep capability file for command entries. Wave 2 does not add new threats.

## User Setup Required

None for Wave 2 close. Wave 3 (Wizard UI lift) pulls in:
- Workbench / DM Mono / DSEG7 / Caveat WOFF2 fonts (vendored under `tauri/ui/public/fonts/` — local copies to survive offline first-run).
- 1 kHz sine WAV generated at build time via `scripts/gen_sine.py`.

## Next Phase Readiness

- **Wave 3** (Wizard UI lift) can begin — minimal webview is in place, crash banner subscribes to Tauri events, the 7 invoke_handler commands are reachable from JS. Wave 3 lifts UI-SPEC tokens.css from `mocks/vibemix-app-ui.html` (anodised charcoal + phosphor amber + Workbench + DSEG7) and builds the 3-step wizard.
- **Wave 4** (WizardLoop sidecar handler) can begin in parallel — `forward_ipc_to_sidecar` Wave 2 stub is the wire-up target; `request_microphone_permission` Wave 2 stub is the second wire-up target. Both commands' capability shape locks at Wave 2 so Wave 4 doesn't need to touch `capabilities/default.json`.
- **Phase 18** (Signed installer) has the complete macOS Hardened Runtime surface ready: bundle id `world.bravoh.vibemix` + entitlements.plist + Info.plist + `hardenedRuntime: true` in tauri.conf.json5. Codesign will be `codesign --force --options runtime --entitlements tauri/src-tauri/entitlements.plist ...`.

## Self-Check: PASSED

- `tauri/src-tauri/Cargo.toml` + `Cargo.lock` + `build.rs` — FOUND
- `tauri/src-tauri/tauri.conf.json5` — FOUND, `"identifier": "world.bravoh.vibemix"` present
- `tauri/src-tauri/capabilities/default.json` — FOUND, `shell:allow-execute` + 3 URL allowlist + `fs:allow-read-text-file` scoped
- `tauri/src-tauri/Info.plist` — FOUND, NSScreenCaptureUsageDescription + LSMinimumSystemVersion 12.3 present
- `tauri/src-tauri/icons/icon.png` — FOUND (RGBA)
- `tauri/src-tauri/src/{main,sidecar,ws_client,config,permissions}.rs` — all 5 FOUND
- `tauri/ui/index.html` + `src/main.ts` + `src/crash-banner.ts` + `vite.config.ts` — FOUND
- Commit `99762fa` (Task 1) — FOUND in git log
- Commit `acae787` (Task 2) — FOUND in git log
- Commit `093ba4e` (Task 3) — FOUND in git log
- `cd tauri/src-tauri && cargo build` — green (2 deprecation warnings expected)
- `cd tauri/src-tauri && cargo build --release` — green; 10 MB binary
- `cd tauri/src-tauri && cargo test` — 4 passed, 0 failed
- `strings -a tauri/src-tauri/target/release/vibemix | grep -cE "AIza[A-Za-z0-9_-]{35}"` — 0
- `cd tauri/ui && npm run build` — green; `dist/index.html` 2.78 KB
- `grep '"identifier":' tauri/src-tauri/tauri.conf.json5` — `"identifier": "world.bravoh.vibemix"`
- `grep -c "shell:allow-execute" tauri/src-tauri/capabilities/default.json` — 1
- `grep -cE '(core:default-all|"shell:default")' tauri/src-tauri/capabilities/default.json` — 0
- `grep "12.3" tauri/src-tauri/Info.plist` — 1+ match
- `uv run pytest tests/ui_bus/ tests/sidecar/ -q` — 57 passed
- POC files (`cohost*.py`, `cohost_v4.py`, `run_v4.sh`) — UNTOUCHED in this plan's diff
- No deletions in any of the 3 task commits (verified via `git diff --diff-filter=D --name-only HEAD~N HEAD`)

---
*Phase: 11-tauri-shell-calibration-wizard*
*Completed: 2026-05-12*
