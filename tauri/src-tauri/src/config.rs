//! Phase 11 Wave 2 — first-run state persistence (Phase 13 Plan 02 extends with mascot window state).
//!
//! Wraps `tauri-plugin-store` so the wizard can read/write
//! `~/Library/Application Support/vibemix/config.json` (macOS) or
//! `%APPDATA%\vibemix\config.json` (Windows). Schema mirrors CONTEXT
//! Area 3 — every field is `Option<...>` so the on-disk shape can evolve
//! without breaking the loader.
//!
//! Wave 4 wires the actual write paths; Wave 2 just publishes the
//! commands so the capability allowlist locks now.
//!
//! ## Phase 13 Plan 02 — Mascot window state
//!
//! A second top-level key `mascot_window` stores the overlay window's
//! geometry, visibility, and click-through bool. Position fields are
//! `Option<i32>` because first launch has no saved position —
//! `mascot_window.rs` picks a default top-right offset.
//!
//! Defaults: `visible: false` (opt-in experimental, see 2026-05-19
//! mascot-opt-in decision below) and `click_through: false`
//! (drag-positionable, NOT click-through).
//!
//! ## 2026-05-19 — Mascot opt-in (decision #3 from /impeccable critique)
//!
//! The original Phase 13 default was `visible: true` — every user got
//! the mascot overlay on first launch. The 2026-05-19 critique flipped
//! this for rc1: the mascot ships as opt-in experimental. The character
//! art is a placeholder ("DJ bat") and shipping incomplete signature
//! features in screenshots hurts the launch surface. The default is now
//! `visible: false`; users enable via Settings → Mascot → "ENABLE".
//!
//! Lazy creation: `set_mascot_visible(true)` will build the window
//! on-demand if it doesn't exist (first toggle after a hidden launch),
//! so enabling does NOT require an app restart.

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager};

const STORE_PATH: &str = "config.json";
const KEY_FIRST_RUN_STATE: &str = "first_run_state";
const KEY_MASCOT_WINDOW: &str = "mascot_window";

/// Phase 18 Plan 18-04 — bool. Default `true`. When `false`, the boot-time
/// updater check in `updater::run_update_check_if_enabled` returns early
/// without hitting the manifest endpoint. Read directly from
/// `tauri-plugin-store`'s `config.json` (no IPC schema change — the
/// sidecar's `_PHASE12_FIELDS` allowlist preserves unknown top-level keys
/// on round-trip per `src/vibemix/runtime/config_store.py` lines 14-22).
/// The Settings UI surface for flipping this is deferred to Phase 19
/// polish (one row in the existing `PerformanceGroup` or a new
/// `UpdateGroup`). When that ships, it calls `tauri-plugin-store`'s
/// built-in `set` command via the existing `store:default` capability —
/// no new app command needed.
pub const KEY_UPDATE_CHECK_ON_LAUNCH: &str = "update_check_on_launch";

const MASCOT_WINDOW_LABEL: &str = "mascot";

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

/// Persisted overlay window state. `x`/`y`/`width`/`height` are `Option`
/// so first-launch (no saved position) is distinguishable from saved
/// `0,0` — `mascot_window::create_mascot_window` substitutes a top-right
/// default offset when these are `None`.
///
/// Defaults (2026-05-19 mascot-opt-in — see module-level doc):
///   - `visible: false` (mascot hidden on first launch; opt-in via Settings)
///   - `click_through: false` (drag-positionable; click-through is opt-in via Settings)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MascotWindowState {
    pub x: Option<i32>,
    pub y: Option<i32>,
    pub width: Option<u32>,
    pub height: Option<u32>,
    pub visible: bool,
    pub click_through: bool,
}

impl Default for MascotWindowState {
    fn default() -> Self {
        MascotWindowState {
            x: None,
            y: None,
            width: None,
            height: None,
            visible: false,
            click_through: false,
        }
    }
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

/// Read the persisted `MascotWindowState`. Returns defaults when the key
/// is absent (first launch).
pub fn load_mascot_state(app: &AppHandle) -> Result<MascotWindowState, String> {
    use tauri_plugin_store::StoreExt;
    let store = app
        .store(STORE_PATH)
        .map_err(|e| format!("store init failed: {e}"))?;
    match store.get(KEY_MASCOT_WINDOW) {
        Some(value) => serde_json::from_value(value.clone())
            .map_err(|e| format!("decode failed: {e}")),
        None => Ok(MascotWindowState::default()),
    }
}

/// Persist the `MascotWindowState`. Called from the debounced
/// `WindowEvent::Moved`/`Resized` handler in `mascot_window.rs` AND from
/// the `set_mascot_visible` / `set_mascot_click_through` commands.
pub fn save_mascot_state(app: &AppHandle, state: &MascotWindowState) -> Result<(), String> {
    use tauri_plugin_store::StoreExt;
    let store = app
        .store(STORE_PATH)
        .map_err(|e| format!("store init failed: {e}"))?;
    let value = serde_json::to_value(state).map_err(|e| format!("encode failed: {e}"))?;
    store.set(KEY_MASCOT_WINDOW, value);
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

#[tauri::command]
pub async fn read_mascot_window_state(app: AppHandle) -> Result<MascotWindowState, String> {
    load_mascot_state(&app)
}

#[tauri::command]
pub async fn write_mascot_window_state(
    app: AppHandle,
    state: MascotWindowState,
) -> Result<(), String> {
    save_mascot_state(&app, &state)
}

/// Toggle mascot window visibility. Updates the persisted state AND
/// calls `show()`/`hide()` on the live "mascot" window if it exists.
///
/// The tray's left-click handler is the primary caller; the webview
/// Settings drawer (Plan 13-03) also invokes this.
#[tauri::command]
pub async fn set_mascot_visible(app: AppHandle, visible: bool) -> Result<(), String> {
    let mut state = load_mascot_state(&app)?;
    state.visible = visible;
    save_mascot_state(&app, &state)?;

    if let Some(window) = app.get_webview_window(MASCOT_WINDOW_LABEL) {
        if visible {
            window.show().map_err(|e| format!("show failed: {e}"))?;
        } else {
            window.hide().map_err(|e| format!("hide failed: {e}"))?;
        }
    } else if visible {
        // 2026-05-19 mascot-opt-in: lazy-create on first enable after a
        // hidden launch. `state.visible` is already saved as true above,
        // so `create_mascot_window`'s `if !state.visible { return Ok(None) }`
        // gate passes. Without this branch, the user would have to restart
        // the app to bring the mascot in after flipping the Settings toggle.
        crate::mascot_window::create_mascot_window(&app)
            .map_err(|e| format!("lazy create failed: {e}"))?;
    }
    Ok(())
}

/// Toggle ignore-cursor-events on the mascot window. When `true`, the
/// mascot becomes click-through (mouse events pass to the window
/// underneath). Drag-handle UX in Plan 13-04 owns a non-click-through
/// zone for the user to drag the mascot even when click-through is on.
#[tauri::command]
pub async fn set_mascot_click_through(
    app: AppHandle,
    enabled: bool,
) -> Result<(), String> {
    let mut state = load_mascot_state(&app)?;
    state.click_through = enabled;
    save_mascot_state(&app, &state)?;

    if let Some(window) = app.get_webview_window(MASCOT_WINDOW_LABEL) {
        window
            .set_ignore_cursor_events(enabled)
            .map_err(|e| format!("set_ignore_cursor_events failed: {e}"))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mascot_window_state_defaults_match_opt_in_decision() {
        // 2026-05-19 mascot-opt-in (decision #3 from /impeccable critique):
        // mascot is hidden on first launch — opt-in experimental until the
        // placeholder character art is replaced. Click-through stays OFF
        // (draggable when enabled).
        let s = MascotWindowState::default();
        assert!(!s.visible, "mascot must be hidden on first launch (opt-in)");
        assert!(!s.click_through, "click-through must be OFF default (draggable)");
        assert!(s.x.is_none() && s.y.is_none(), "no saved position on first launch");
        assert!(s.width.is_none() && s.height.is_none(), "no saved size on first launch");
    }

    #[test]
    fn mascot_window_state_roundtrips_via_serde_json() {
        let s = MascotWindowState {
            x: Some(1200),
            y: Some(80),
            width: Some(300),
            height: Some(400),
            visible: true,
            click_through: false,
        };
        let json = serde_json::to_value(&s).unwrap();
        let back: MascotWindowState = serde_json::from_value(json).unwrap();
        assert_eq!(back.x, Some(1200));
        assert_eq!(back.y, Some(80));
        assert_eq!(back.width, Some(300));
        assert_eq!(back.height, Some(400));
        assert!(back.visible);
        assert!(!back.click_through);
    }

    #[test]
    fn mascot_window_state_decodes_legacy_missing_fields_as_defaults() {
        // Forward-compat: a config.json written by a future build with extra
        // fields must still decode here (serde_json ignores unknown keys by
        // default). A config written without optional fields must default.
        let raw = serde_json::json!({
            "visible": true,
            "click_through": false
        });
        let s: MascotWindowState = serde_json::from_value(raw).unwrap();
        assert_eq!(s.x, None);
        assert_eq!(s.width, None);
        assert!(s.visible);
    }
}
