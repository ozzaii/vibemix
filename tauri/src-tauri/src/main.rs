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
mod debrief_window;
mod djay_ax;
mod hotkey;
mod mascot_window;
mod overlay;
mod permissions;
mod recordings;
mod sidecar;
mod tray;
mod updater;
mod ws_client;

use std::fs;

use tauri::{Listener, Manager};

use crate::debrief_window::DebriefSidecarHandle;
use crate::hotkey::HotkeyHandle;
use crate::sidecar::SidecarHandle;
use crate::tray::{QuitPending, TrayHandle};
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
        // Webview-callable commands (capability allowlist mirrors).
        // Phase 13 Plan 02 adds 4 mascot commands:
        //   read_mascot_window_state, write_mascot_window_state,
        //   set_mascot_visible, set_mascot_click_through
        // Phase 15 Plan 03 adds 2 recording commands:
        //   reveal_in_os, open_input_wav
        // Phase 24 Plan 02 adds 1 overlay command:
        //   show_overlay_highlight
        .invoke_handler(tauri::generate_handler![
            ws_client::forward_ipc_to_sidecar,
            sidecar::restart_sidecar,
            config::read_first_run_state,
            config::write_first_run_state,
            config::read_mascot_window_state,
            config::write_mascot_window_state,
            config::set_mascot_visible,
            config::set_mascot_click_through,
            permissions::open_screen_recording_settings,
            permissions::open_microphone_settings,
            permissions::request_microphone_permission,
            hotkey::rebind_hotkey,
            recordings::reveal_in_os,
            recordings::open_input_wav,
            overlay::show_overlay_highlight,
            debrief_window::open_debrief_window,
        ])
        .manage(SidecarHandle::default())
        .manage(DebriefSidecarHandle::default())
        .manage(WsClientHandle::default())
        .manage(HotkeyHandle::default())
        .manage(TrayHandle::default())
        .manage(QuitPending::default())
        // Phase 13 Plan 02 — lifecycle override. Closing the main session
        // window hides it instead of quitting the process; only the tray
        // `Quit vibemix` item kills the app. The mascot window has no
        // decorations so its OS-chrome close is unreachable.
        .on_window_event(tray::on_window_event)
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

            // Phase 13 Plan 02 — spawn the mascot overlay window.
            // Honours persisted visibility (visible=false → no window built;
            // tray left-click can wake it on next launch). Logs but does
            // NOT bail setup on failure — the main session UI must still
            // come up even if the mascot fails to build (e.g. an unusual
            // multi-monitor topology).
            match mascot_window::create_mascot_window(&app_handle) {
                Ok(Some(_)) => {
                    tracing::info!("mascot overlay window built");
                }
                Ok(None) => {
                    tracing::info!("mascot overlay hidden (user preference)");
                }
                Err(e) => {
                    tracing::error!("mascot window build failed: {e}");
                }
            }

            // Phase 13 Plan 02 — initialise the system tray icon + menu.
            // Must run AFTER create_mascot_window so the left-click handler
            // can target the live mascot window when toggling visibility.
            if let Err(e) = tray::init_tray(&app_handle) {
                // Tray failure is non-fatal at setup but visibility-breaking
                // for the user (no Quit, no Open Session UI from the menu
                // bar). Log loudly so it's discoverable in the rotated log.
                tracing::error!("tray init failed: {e}");
            }

            // Phase 13 Plan 06 — install tray-state listener. Subscribes to
            // ipc:ipc.session.snapshot + ipc:ipc.status.tick (forwarded by
            // ws_client.rs from the Python bus) + ipc:ipc.mascot.mood_change
            // and re-derives tray icon state with a 2 Hz throttle. Listener
            // lives for the process lifetime — no uninstall needed.
            tray::install_tray_state_listener(&app_handle);

            // Critique pass 3 (2026-05-14) — quit confirmation listener.
            // The webview's quit-guard emits `confirmed-quit` after the
            // user picks "Quit anyway" in the recording-confirm dialog (or
            // immediately if no recording is in flight). On receipt we
            // exit the process. Two-step quit (tray-quit-requested ->
            // confirmed-quit) means Cmd+Q on a live recording no longer
            // drops the take silently.
            //
            // Pass 4 (2026-05-14): also listen for `quit-cancelled` (user
            // picked Stay). Clear the QuitPending flag so the tray.rs
            // fallback timer becomes a no-op when it fires at +1.5s.
            let quit_pending_for_exit = app.state::<QuitPending>().0.clone();
            let quit_app = app_handle.clone();
            app_handle.listen("confirmed-quit", move |_event| {
                quit_pending_for_exit.store(false, std::sync::atomic::Ordering::SeqCst);
                quit_app.exit(0);
            });
            let quit_pending_for_cancel = app.state::<QuitPending>().0.clone();
            app_handle.listen("quit-cancelled", move |_event| {
                quit_pending_for_cancel.store(false, std::sync::atomic::Ordering::SeqCst);
            });

            // Phase 18 Plan 18-04 — Tauri updater boot-time fire-and-forget.
            // Gated by `update_check_on_launch` (default true); when true the
            // plugin's `dialog: true` config drives the prompt UX. Failures
            // are logged but never bail setup — the user keeps the version
            // they have if the manifest server is unreachable. This is the
            // lowest-priority boot task on purpose (runs AFTER sidecar +
            // ws_client + tray are already up).
            let updater_app = app_handle.clone();
            tauri::async_runtime::spawn(async move {
                updater::run_update_check_if_enabled(updater_app).await;
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
