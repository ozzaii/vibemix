// SPDX-License-Identifier: Apache-2.0
//! Phase 18 Plan 18-04 — Tauri updater boot-time fire-and-forget.
//!
//! The Tauri updater plugin (`tauri-plugin-updater` 2.10) is configured live
//! in `tauri.conf.json5` (Plan 18-04 Task 1):
//!   - `active: true`
//!   - `endpoints: ["https://api.altidus.world/vibemix/updates/{{target}}/{{arch}}/{{current_version}}"]`
//!   - `pubkey: "<base64 minisign>"` (placeholder until Kaan generates the
//!     keypair pre-v0.1.0 — see `tauri/src-tauri/keys/README.md`)
//!   - `dialog: true`
//!
//! This module is the **boot-time dispatcher**: it reads a single bool
//! (`update_check_on_launch`, default `true`) from `tauri-plugin-store`'s
//! `config.json` (the SAME file the Python sidecar's `ConfigStore` reads —
//! both sides preserve unknown top-level keys on round-trip per
//! `src/vibemix/runtime/config_store.py` lines 14-22). When the flag is
//! `true` (default), we call `app.updater()?.check().await` and let the
//! plugin's `dialog: true` config drive the prompt UX (notify → show
//! release notes → install + restart on user confirm). When `false`, we
//! log and exit — the user keeps the version they have.
//!
//! ## Why a separate module
//!
//! The `.setup` closure in `main.rs` is already crowded (sidecar
//! supervisor, ws_client, hotkey register, mascot window builder, tray
//! init, tray-state listener). The updater fire-and-forget is the
//! lowest-priority boot task and deserves its own file for the
//! `tracing::info!` and `tracing::warn!` lines that document its
//! lifecycle without bloating main.rs.
//!
//! ## Why no public command surface
//!
//! The Settings UI surface for the opt-out toggle is deferred to Phase 19
//! polish (one row in `PerformanceGroup` or a new `UpdateGroup`). The
//! future Settings drawer calls `tauri-plugin-store`'s built-in `set`
//! command directly through the existing `store:default` capability
//! permission — no new app command is needed here. This module exposes
//! only the boot-time reader.
//!
//! ## Error handling
//!
//! All failure modes (store read error, updater builder error, manifest
//! 404, signature mismatch, manifest unreachable) log at `info!`/`warn!`
//! and return without propagating. The updater MUST NEVER bail boot — if
//! the network is offline or the manifest server is down, the user keeps
//! the running version and nothing surfaces in the UI.
//!
//! ## Default-on invariant
//!
//! `check_on_launch_enabled` returns `true` on:
//!   - key absent (first launch — no prior opt-out)
//!   - store read error (defensive — a corrupt store should not silently
//!     disable security updates)
//!   - value present and non-bool (defensive — shouldn't happen, but if
//!     a future writer puts a string there, we still default ON)
//! Only an explicit `false` boolean disables the check.

use tauri::AppHandle;
use tauri_plugin_store::StoreExt;
use tauri_plugin_updater::UpdaterExt;

use crate::config::KEY_UPDATE_CHECK_ON_LAUNCH;

/// Mirrors `crate::config::STORE_PATH`. Re-declared here so this module
/// can be unit-tested + read independently. Both must reference the
/// SAME file ("config.json" under `$APPDATA/vibemix/`) — drift would
/// silently split the opt-out flag from the rest of the config.
const STORE_PATH: &str = "config.json";

/// Read the user opt-out flag from `tauri-plugin-store`'s config.json.
///
/// Returns `true` (check enabled) on any of:
///   - key absent (no opt-out recorded — default ON)
///   - store read fails (defensive default-ON: a corrupt config must
///     not silently disable security updates)
///   - value present but not a bool (defensive — defaults to ON if a
///     future writer drops a non-bool)
///
/// Returns `false` ONLY when the key is present AND the value is `false`.
pub fn check_on_launch_enabled(app: &AppHandle) -> bool {
    let store = match app.store(STORE_PATH) {
        Ok(s) => s,
        Err(e) => {
            tracing::debug!(
                "updater: store init failed ({e}); defaulting check_on_launch=true"
            );
            return true;
        }
    };
    match store.get(KEY_UPDATE_CHECK_ON_LAUNCH) {
        Some(value) => match value.as_bool() {
            Some(b) => b,
            None => {
                tracing::debug!(
                    "updater: {KEY_UPDATE_CHECK_ON_LAUNCH} present but not bool; defaulting true"
                );
                true
            }
        },
        None => true,
    }
}

/// Boot-time fire-and-forget update check.
///
/// Called from `main.rs .setup` via `tauri::async_runtime::spawn`. Honours
/// the `update_check_on_launch` opt-out (default ON). When enabled,
/// invokes the Tauri updater plugin's `.check().await` — if an update is
/// available, the plugin's `dialog: true` config drives the standard
/// "Update available: vX.Y.Z. Install now?" prompt. On user confirm:
/// download → minisign-verify against the pubkey baked into the running
/// app → install → restart.
///
/// All errors are logged but never propagated. The updater MUST NEVER
/// bail boot — manifest server unreachable, signature mismatch, network
/// offline: the user simply keeps the version they have.
pub async fn run_update_check_if_enabled(app: AppHandle) {
    if !check_on_launch_enabled(&app) {
        tracing::info!("updater: skipped (user opt-out via update_check_on_launch=false)");
        return;
    }

    let updater = match app.updater() {
        Ok(u) => u,
        Err(e) => {
            tracing::warn!("updater: builder failed ({e}); skipping update check");
            return;
        }
    };

    match updater.check().await {
        Ok(Some(update)) => {
            tracing::info!(
                "updater: update available (version {}); dispatching download_and_install",
                update.version
            );
            // The `dialog: true` plugin config means Tauri shows the standard
            // prompt + progress bar; the callbacks below are no-ops because
            // the plugin owns the UX. If we ever flip to `dialog: false` for
            // a custom drawer, these closures become the progress hooks.
            if let Err(e) = update
                .download_and_install(|_chunk_len, _total_len| {}, || {})
                .await
            {
                tracing::warn!("updater: download_and_install failed: {e}");
            }
        }
        Ok(None) => {
            tracing::info!("updater: no update available (running version is latest)");
        }
        Err(e) => {
            // Common in dev / offline / manifest server not yet deployed —
            // see docs/updater.md "Until the Bravoh proxy endpoint ships,
            // the updater will receive HTTP 404 and silently keep the
            // running version." WARN, not ERROR — this is expected.
            tracing::warn!("updater: check failed: {e}");
        }
    }
}
