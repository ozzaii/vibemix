//! Phase 11 Wave 2 — first-run state persistence.
//!
//! Wraps `tauri-plugin-store` so the wizard can read/write
//! `~/Library/Application Support/vibemix/config.json` (macOS) or
//! `%APPDATA%\vibemix\config.json` (Windows). Schema mirrors CONTEXT
//! Area 3 — every field is `Option<...>` so the on-disk shape can evolve
//! without breaking the loader.
//!
//! Wave 4 wires the actual write paths; Wave 2 just publishes the
//! commands so the capability allowlist locks now.

use serde::{Deserialize, Serialize};
use tauri::AppHandle;

const STORE_PATH: &str = "config.json";
const KEY_FIRST_RUN_STATE: &str = "first_run_state";

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct FirstRunState {
    pub first_run_completed: bool,
    pub calibrated_at: Option<String>,
    pub output_device_id: Option<String>,
    pub controller_profile: Option<String>,
    pub target_dj_app_hint: Option<String>,
    pub target_window_id: Option<String>,
    pub blackhole_install_seen: bool,
}

/// Returns true when no `first_run_state` is recorded or when its
/// `first_run_completed` field is `false`. The Tauri `setup` block calls
/// this synchronously to decide whether to pass `--wizard` to the sidecar.
pub fn is_first_run(app: &AppHandle) -> bool {
    match load_state(app) {
        Ok(state) => !state.first_run_completed,
        Err(_) => true,
    }
}

fn load_state(app: &AppHandle) -> Result<FirstRunState, String> {
    use tauri_plugin_store::StoreExt;
    let store = app
        .store(STORE_PATH)
        .map_err(|e| format!("store init failed: {e}"))?;
    match store.get(KEY_FIRST_RUN_STATE) {
        Some(value) => serde_json::from_value(value.clone())
            .map_err(|e| format!("decode failed: {e}")),
        None => Ok(FirstRunState::default()),
    }
}

fn save_state(app: &AppHandle, state: &FirstRunState) -> Result<(), String> {
    use tauri_plugin_store::StoreExt;
    let store = app
        .store(STORE_PATH)
        .map_err(|e| format!("store init failed: {e}"))?;
    let value = serde_json::to_value(state).map_err(|e| format!("encode failed: {e}"))?;
    store.set(KEY_FIRST_RUN_STATE, value);
    // Force flush so a crash mid-wizard doesn't lose calibration state.
    store
        .save()
        .map_err(|e| format!("store save failed: {e}"))?;
    Ok(())
}

#[tauri::command]
pub async fn read_first_run_state(app: AppHandle) -> Result<FirstRunState, String> {
    load_state(&app)
}

#[tauri::command]
pub async fn write_first_run_state(
    app: AppHandle,
    state: FirstRunState,
) -> Result<(), String> {
    save_state(&app, &state)
}
