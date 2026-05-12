//! Phase 13 Plan 02 — mascot overlay window builder + persistence.
//!
//! Builds the second Tauri window (`label = "mascot"`) per 13-CONTEXT
//! Area 2 + Open Q 1:
//!
//!   * `transparent(true)` — no opaque background; the Three.js scene
//!     in Plan 13-04 will render against an alpha-channel canvas.
//!   * `always_on_top(true)` — mascot floats over the user's DJ app.
//!   * `decorations(false)` — no titlebar / close box; lifecycle is
//!     tray-owned (closing main window does NOT quit; only tray Quit does).
//!   * `resizable(true)` — within min 200x280 / max 600x800 bounds.
//!   * `visible_on_all_workspaces(true)` — Superwhisper-style cross-Space
//!     persistence on macOS (NSWindowCollectionBehaviorCanJoinAllSpaces)
//!     and Windows virtual desktops (WS_EX_TOOLWINDOW + virtual-desktop
//!     pinning where supported).
//!   * `skip_taskbar(true)` — mascot is NOT an Alt-Tab target.
//!
//! Defaults if first launch (no saved geometry): 300x400 at top-right
//! offset (primary-monitor width minus 320, y = 80).
//!
//! Geometry persistence: a `WindowEvent::Moved` / `Resized` handler
//! writes `MascotWindowState` back to the store, debounced 200ms so a
//! pixel-drag doesn't thrash store.save().

use std::sync::Arc;
use std::time::Duration;

use tauri::{AppHandle, Manager, PhysicalPosition, PhysicalSize, WebviewUrl, WebviewWindowBuilder};
use tokio::sync::Mutex;

use crate::config;

pub const MASCOT_WINDOW_LABEL: &str = "mascot";

// Default geometry. Locked by 13-CONTEXT Area 2.
const DEFAULT_WIDTH: u32 = 300;
const DEFAULT_HEIGHT: u32 = 400;
const DEFAULT_TOP_OFFSET: i32 = 80;
const DEFAULT_RIGHT_INSET: i32 = 320; // monitor_width - DEFAULT_RIGHT_INSET = default_x
const MIN_WIDTH: f64 = 200.0;
const MIN_HEIGHT: f64 = 280.0;
const MAX_WIDTH: f64 = 600.0;
const MAX_HEIGHT: f64 = 800.0;

// Geometry-persist debounce. 200ms is well above 60Hz drag-event cadence
// without feeling laggy on the final save after the user releases.
const DEBOUNCE_MS: u64 = 200;

/// Build the mascot overlay window. Reads the saved `MascotWindowState`
/// from `config.json`; if `visible == false`, returns `Ok(None)` without
/// building (the user explicitly hid the mascot — only tray-left-click
/// can wake it).
///
/// On macOS the `visible_on_all_workspaces(true)` builder flag already
/// sets `NSWindowCollectionBehaviorCanJoinAllSpaces` via the tao backend
/// in tauri-runtime-wry 2.11. If that ever regresses, the manual ObjC
/// override goes here (documented in 13-CONTEXT Area 2).
pub fn create_mascot_window(
    app: &AppHandle,
) -> tauri::Result<Option<tauri::WebviewWindow>> {
    let state = config::load_mascot_state(app).map_err(|e| {
        // Surface store-load failure as an io error so callers can match
        // on `tauri::Error::Io` without dragging in anyhow as a direct dep.
        tauri::Error::Io(std::io::Error::other(e))
    })?;

    if !state.visible {
        // User chose to hide the mascot last session; honour that until
        // they left-click the tray to bring it back.
        return Ok(None);
    }

    // Resolve initial geometry. If saved width/height are missing, use
    // 300x400. For x/y, fall back to a top-right offset using the
    // primary monitor's width.
    let width = state.width.unwrap_or(DEFAULT_WIDTH);
    let height = state.height.unwrap_or(DEFAULT_HEIGHT);
    let (default_x, default_y) = default_top_right(app, width);
    let x = state.x.unwrap_or(default_x);
    let y = state.y.unwrap_or(default_y);

    let window = WebviewWindowBuilder::new(
        app,
        MASCOT_WINDOW_LABEL,
        WebviewUrl::App("mascot.html".into()),
    )
    .title("vibemix mascot")
    .transparent(true)
    .always_on_top(true)
    .decorations(false)
    .resizable(true)
    .skip_taskbar(true)
    .visible_on_all_workspaces(true)
    .inner_size(f64::from(width), f64::from(height))
    .position(f64::from(x), f64::from(y))
    .min_inner_size(MIN_WIDTH, MIN_HEIGHT)
    .max_inner_size(MAX_WIDTH, MAX_HEIGHT)
    .visible(true)
    .build()?;

    // Apply click-through on build if persisted.
    if state.click_through {
        window.set_ignore_cursor_events(true)?;
    }

    install_geometry_listener(app.clone(), window.clone());

    Ok(Some(window))
}

/// Returns (x, y) for the default top-right placement on the current
/// primary monitor. Falls back to a conservative 1280-wide assumption if
/// monitor enumeration fails (rare; only on macOS without an attached
/// display, which is impossible for an interactive DJ session anyway).
fn default_top_right(app: &AppHandle, _width: u32) -> (i32, i32) {
    // We need a Webview to call `primary_monitor()`; in setup() the main
    // window is available. If it isn't (edge case), use a 1280×800
    // fallback that won't spawn off-screen on any reasonable display.
    let monitor_width = app
        .get_webview_window("main")
        .and_then(|w| w.primary_monitor().ok().flatten())
        .map(|m| m.size().width as i32)
        .unwrap_or(1280);
    let x = (monitor_width - DEFAULT_RIGHT_INSET).max(0);
    (x, DEFAULT_TOP_OFFSET)
}

/// Listen for `WindowEvent::Moved` and `WindowEvent::Resized` on the
/// mascot window and persist a debounced snapshot of geometry. Without
/// debounce, a single drag could fire ~60 store.save()s per second.
///
/// Implementation: every event bumps a shared "scheduled-at" instant
/// and spawns a single Tokio task that sleeps DEBOUNCE_MS then writes.
/// If a newer event lands during the sleep, the older task no-ops by
/// comparing the scheduled-at it captured against the current latest.
fn install_geometry_listener(app: AppHandle, window: tauri::WebviewWindow) {
    let scheduled: Arc<Mutex<Option<std::time::Instant>>> = Arc::new(Mutex::new(None));

    window.on_window_event(move |event| {
        use tauri::WindowEvent;

        // We only care about geometry-changing events. Close and other
        // events are handled by the lifecycle override in tray.rs.
        if !matches!(event, WindowEvent::Moved(_) | WindowEvent::Resized(_)) {
            return;
        }

        let app = app.clone();
        let scheduled = scheduled.clone();

        // Capture geometry NOW (so the closure runs on the OS event
        // thread; debounced save runs on Tokio).
        let Ok(pos) = (|| -> tauri::Result<PhysicalPosition<i32>> {
            window_position(&app)
        })() else {
            return;
        };
        let Ok(size) = (|| -> tauri::Result<PhysicalSize<u32>> { window_size(&app) })() else {
            return;
        };

        let my_schedule = std::time::Instant::now();
        let scheduled_clone = scheduled.clone();

        tauri::async_runtime::spawn(async move {
            {
                let mut g = scheduled_clone.lock().await;
                *g = Some(my_schedule);
            }
            tokio::time::sleep(Duration::from_millis(DEBOUNCE_MS)).await;
            // Compare-and-skip: if a newer event scheduled after us,
            // it owns the save.
            {
                let g = scheduled_clone.lock().await;
                if *g != Some(my_schedule) {
                    return;
                }
            }
            // Read current persisted state to preserve visible/click_through.
            let mut cur = config::load_mascot_state(&app).unwrap_or_default();
            cur.x = Some(pos.x);
            cur.y = Some(pos.y);
            cur.width = Some(size.width);
            cur.height = Some(size.height);
            let _ = config::save_mascot_state(&app, &cur);
        });
    });
}

fn window_position(app: &AppHandle) -> tauri::Result<PhysicalPosition<i32>> {
    let w = app
        .get_webview_window(MASCOT_WINDOW_LABEL)
        .ok_or_else(|| tauri::Error::WebviewNotFound)?;
    w.outer_position()
}

fn window_size(app: &AppHandle) -> tauri::Result<PhysicalSize<u32>> {
    let w = app
        .get_webview_window(MASCOT_WINDOW_LABEL)
        .ok_or_else(|| tauri::Error::WebviewNotFound)?;
    w.inner_size()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_pin_context_decisions() {
        // 13-CONTEXT Area 2: 300x400 default, min 200x280, max 600x800.
        assert_eq!(DEFAULT_WIDTH, 300);
        assert_eq!(DEFAULT_HEIGHT, 400);
        assert_eq!(MIN_WIDTH, 200.0);
        assert_eq!(MIN_HEIGHT, 280.0);
        assert_eq!(MAX_WIDTH, 600.0);
        assert_eq!(MAX_HEIGHT, 800.0);
    }

    #[test]
    fn debounce_is_not_zero_or_thrashy() {
        // 200ms keeps drag-fire below 5 store.save()s/sec in the worst
        // case (user releases, save fires; repeated drags coalesce).
        // < 50ms would still thrash; > 500ms would feel laggy on the
        // final save.
        assert!((50..=500).contains(&(DEBOUNCE_MS as u64)));
    }

    #[test]
    fn label_constant_matches_capability_allowlist() {
        // capabilities/default.json "windows": ["main", "mascot"].
        assert_eq!(MASCOT_WINDOW_LABEL, "mascot");
    }
}
