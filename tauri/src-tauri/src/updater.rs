// SPDX-License-Identifier: Apache-2.0
//! Phase 18 Plan 18-04 — Tauri updater boot-time fire-and-forget.
//!
//! The Tauri updater plugin (`tauri-plugin-updater` 2.10) is configured live
//! in `tauri.conf.json5` (Plan 18-04 Task 1):
//!   - `endpoints: ["https://api.altidus.world/vibemix/updates/{{target}}/{{arch}}/{{current_version}}"]`
//!   - `pubkey: "<base64 minisign>"` (placeholder until Kaan generates the
//!     keypair pre-v0.1.0 — see `tauri/src-tauri/keys/README.md`)
//!
//! NOTE: tauri-plugin-updater 2.x has NO built-in prompt — the v1-era
//! `dialog` config option does not exist (unknown fields are silently
//! ignored by its Config deserializer). The consent prompt lives HERE,
//! via tauri-plugin-dialog, before any download starts.
//!
//! This module is the **boot-time dispatcher**: it reads a single bool
//! (`update_check_on_launch`, default `true`) from `tauri-plugin-store`'s
//! `config.json` (the SAME file the Python sidecar's `ConfigStore` reads —
//! both sides preserve unknown top-level keys on round-trip per
//! `src/vibemix/runtime/config_store.py` lines 14-22). When the flag is
//! `true` (default), we call `app.updater()?.check().await`, ask the user
//! over a native dialog when an update exists, and install only on
//! confirm. When `false`, we log and exit — the user keeps the version
//! they have.
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
use tauri_plugin_dialog::{DialogExt, MessageDialogButtons};
use tauri_plugin_store::StoreExt;
use tauri_plugin_updater::UpdaterExt;

use crate::config::KEY_UPDATE_CHECK_ON_LAUNCH;

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
    // This fn returns `bool` (not Result), so `?` is invalid here. Fold the
    // config_store_path() Err into the SAME default-ON behavior the store-init
    // Err arm already uses — a corrupt/unresolvable config must never silently
    // disable security updates. (Quick 260529-m4m: absolute path so this reads
    // the SAME config.json the Python sidecar writes.)
    let path = match crate::config::config_store_path() {
        Ok(p) => p,
        Err(e) => {
            tracing::debug!("updater: config path failed ({e}); defaulting check_on_launch=true");
            return true;
        }
    };
    let store = match app.store(path) {
        Ok(s) => s,
        Err(e) => {
            tracing::debug!("updater: store init failed ({e}); defaulting check_on_launch=true");
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
/// the `update_check_on_launch` opt-out (default ON). When enabled, invokes
/// the Tauri updater plugin's `.check().await` — if an update is available,
/// WE ask first via tauri-plugin-dialog ("Install now / Later") and only
/// then download → minisign-verify against the pubkey baked into the
/// running app → install (applies on the next launch).
///
/// Consent is OURS to ask: the v1-era `updater.dialog` config option does
/// not exist in tauri-plugin-updater 2.x (its Config deserializer silently
/// ignores unknown fields), so without this prompt a boot-time check would
/// download and replace the app with zero user interaction.
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
                "updater: update available (version {}); asking the user",
                update.version
            );
            let (tx, rx) = tokio::sync::oneshot::channel::<bool>();
            app.dialog()
                .message(format!(
                    "vibemix {} is ready.\nInstall now? It applies the next time the app opens.",
                    update.version
                ))
                .title("Update available")
                .buttons(MessageDialogButtons::OkCancelCustom(
                    "Install now".to_string(),
                    "Later".to_string(),
                ))
                .show(move |confirmed| {
                    let _ = tx.send(confirmed);
                });
            let confirmed = rx.await.unwrap_or(false);
            if !confirmed {
                tracing::info!("updater: user chose Later; keeping the running version");
                return;
            }
            if let Err(e) = update
                .download_and_install(|_chunk_len, _total_len| {}, || {})
                .await
            {
                tracing::warn!("updater: download_and_install failed: {e}");
            } else {
                tracing::info!("updater: installed; applies on next launch");
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
