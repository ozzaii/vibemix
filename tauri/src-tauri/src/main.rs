//! vibemix — Tauri 2.x shell entry point (Phase 11 Wave 2).
//!
//! Responsibilities:
//!   1. Register plugins: shell, store, fs, positioner, updater (stubbed), process.
//!   2. Register the seven `#[tauri::command]` entries the webview is allowed to
//!      invoke (capability allowlist in `capabilities/default.json` enumerates
//!      them so they're locked at Wave 2; Wave 4 wires the two stubbed bodies).
//!   3. In `.setup(...)`:
//!        - Resolve the rotating-log path under `$APPLOCALDATA/vibemix/logs/`.
//!        - Read first-run state to decide wizard mode (`--wizard` flag).
//!        - Spawn the sidecar supervisor + WS bus client as async tasks.
//!   4. Run the event loop.
//!
//! No business logic lives here. The shell is intentionally thin — Pattern
//! 1, Pattern 2 + the five modules carry the work.

// Prevent additional console window on Windows in release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod config;
mod hotkey;
mod permissions;
mod sidecar;
mod ws_client;

use std::fs;

use tauri::Manager;

use crate::hotkey::HotkeyHandle;
use crate::sidecar::SidecarHandle;
use crate::ws_client::WsClientHandle;

fn main() {
    tauri::Builder::default()
        // Plugins — every one is gated by the capability allowlist.
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_positioner::init())
        .plugin(tauri_plugin_process::init())
        // Updater plugin is stubbed at the config layer (endpoints: [], pubkey: "").
        // Phase 18 ships real signed manifests.
        .plugin(tauri_plugin_updater::Builder::new().build())
        // Phase 12 Wave 3 — push-to-mute global shortcut.
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        // Eight webview-callable commands (capability allowlist mirrors).
        .invoke_handler(tauri::generate_handler![
            ws_client::forward_ipc_to_sidecar,
            sidecar::restart_sidecar,
            config::read_first_run_state,
            config::write_first_run_state,
            permissions::open_screen_recording_settings,
            permissions::open_microphone_settings,
            permissions::request_microphone_permission,
            hotkey::rebind_hotkey,
        ])
        .manage(SidecarHandle::default())
        .manage(WsClientHandle::default())
        .manage(HotkeyHandle::default())
        .setup(|app| {
            let app_handle = app.handle().clone();

            // Resolve rotating-log path. Falls back to a temp path if app-local
            // dir resolution fails (should be impossible on macOS/Windows).
            let log_path = match app.path().app_local_data_dir() {
                Ok(dir) => {
                    let logs_dir = dir.join("vibemix").join("logs");
                    let _ = fs::create_dir_all(&logs_dir);
                    logs_dir.join("sidecar.log")
                }
                Err(_) => std::env::temp_dir().join("vibemix-sidecar.log"),
            };

            let wizard_mode = config::is_first_run(&app_handle);

            // Sidecar supervisor.
            let sidecar_app = app_handle.clone();
            let sidecar_log = log_path.clone();
            tauri::async_runtime::spawn(async move {
                let _ = sidecar::spawn_sidecar_with_watchdog(
                    sidecar_app,
                    wizard_mode,
                    sidecar_log,
                )
                .await;
            });

            // WS bus client.
            let ws_app = app_handle.clone();
            tauri::async_runtime::spawn(async move {
                ws_client::run_ws_client(ws_app).await;
            });

            // Phase 12 Wave 3 — register the default push-to-mute hotkey.
            // Fires on platform default (Cmd+Shift+M / Ctrl+Shift+M).
            hotkey::register_default(&app_handle);

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
