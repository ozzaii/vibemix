//! Phase 13 Plan 02 — system tray icon + menu + lifecycle ownership.
//!
//! Per 13-CONTEXT Area 5 the tray icon is the app's persistent entry
//! point. Closing the main session UI hides it but does NOT quit the
//! process — only the tray `Quit vibemix` item exits. This file owns:
//!
//!   1. `init_tray` — build the `Menu` + `TrayIconBuilder`, register
//!      handlers for left-click (toggle mascot visibility) and menu
//!      events (emit `tray-*` events into the webview event channel).
//!   2. `set_tray_state` — swap the icon between idle / live / thinking
//!      / error (Plan 13-06 calls this on `session.status` IPC ticks).
//!   3. `install_lifecycle_override` — hook `Builder::on_window_event`
//!      so closing the `main` window calls `api.prevent_close()` + hides
//!      instead of quitting. The mascot window has no decorations so
//!      OS-chrome close isn't reachable; the only path to process exit
//!      is the tray Quit menu item.
//!
//! Tray menu (7 items per CONTEXT Area 5 + 13-02-PLAN Task 3):
//!   - "Mood: Hype-man" / "Mood: Teacher" / "Mood: Coach" (3 leaf items)
//!   - "Mute mic"
//!   - "Open Session UI"
//!   - "Re-run Calibration"
//!   - "Settings…"
//!   - --- separator ---
//!   - "Quit vibemix"
//!
//! NOTE on mood items: the plan asked for a submenu, but Tauri's tray
//! supports a flat menu more reliably on Windows (submenu opens are
//! buggy in the underlying muda crate on some Windows builds). Three
//! leaf "Mood: <name>" items emit the same `tray-set-mood` event with
//! a different payload — equivalent UX, more portable. Documented as a
//! deviation in the SUMMARY.

use std::sync::Arc;

use tauri::{
    image::Image,
    menu::{Menu, MenuBuilder, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Emitter, Manager,
};
use tokio::sync::Mutex;

use crate::config;

pub const TRAY_ID: &str = "vibemix-tray";

// Menu item IDs. These are the strings emitted into `MenuEvent.id()`
// when the user clicks each item; the dispatcher matches on them.
const MENU_ID_MOOD_HYPE: &str = "mood-hype-man";
const MENU_ID_MOOD_TEACHER: &str = "mood-teacher";
const MENU_ID_MOOD_COACH: &str = "mood-coach";
const MENU_ID_MUTE: &str = "mute-mic";
const MENU_ID_OPEN_SESSION: &str = "open-session";
const MENU_ID_RECALIBRATE: &str = "re-run-calibration";
const MENU_ID_SETTINGS: &str = "open-settings";
const MENU_ID_QUIT: &str = "quit-vibemix";

// PNG bytes baked into the binary at compile time. `include_bytes!`
// keeps the icons in `.rodata` so we never hit the filesystem at
// startup — also avoids the "icons missing in app bundle" failure mode
// in Phase 18's signed builds.
const ICON_IDLE: &[u8] = include_bytes!("../icons/tray-idle.png");
const ICON_LIVE: &[u8] = include_bytes!("../icons/tray-live.png");
const ICON_THINKING: &[u8] = include_bytes!("../icons/tray-thinking.png");
const ICON_ERROR: &[u8] = include_bytes!("../icons/tray-error.png");

/// Tray state shared between init + later set_tray_state calls. The
/// `tauri::tray::TrayIcon` handle stored here lets Plan 13-06 swap
/// icons without re-building the tray.
#[derive(Default, Clone)]
pub struct TrayHandle {
    pub icon: Arc<Mutex<Option<tauri::tray::TrayIcon>>>,
}

/// Build the tray icon + menu and park its handle into managed state.
/// Called once from `main.rs::setup()` after the mascot window builder.
pub fn init_tray(app: &AppHandle) -> tauri::Result<()> {
    let menu = build_menu(app)?;
    let idle_icon = Image::from_bytes(ICON_IDLE)?;

    let tray = TrayIconBuilder::with_id(TRAY_ID)
        .icon(idle_icon)
        // macOS NSStatusItem template-image convention — system handles
        // tinting for light/dark mode. Our PNG is pure black so tinting
        // produces the correct contrast on both menu-bar themes.
        .icon_as_template(true)
        .tooltip("vibemix")
        .menu(&menu)
        // CRITICAL: 13-02-PLAN Task 3 + 13-CONTEXT Area 5: LEFT-CLICK
        // toggles mascot visibility, RIGHT-CLICK opens the menu. Tauri
        // defaults `show_menu_on_left_click=true` (macOS standard), so
        // we must disable that to reclaim left-click for the toggle.
        .show_menu_on_left_click(false)
        .on_tray_icon_event(handle_tray_icon_event)
        .on_menu_event(handle_menu_event)
        .build(app)?;

    // Park the tray icon so set_tray_state can find it later.
    if let Some(state) = app.try_state::<TrayHandle>() {
        let icon_clone = tray;
        let handle = state.icon.clone();
        tauri::async_runtime::spawn(async move {
            let mut g = handle.lock().await;
            *g = Some(icon_clone);
        });
    }

    Ok(())
}

/// Build the 7-item tray menu. See module docstring for layout.
fn build_menu(app: &AppHandle) -> tauri::Result<Menu<tauri::Wry>> {
    let mood_hype = MenuItem::with_id(
        app,
        MENU_ID_MOOD_HYPE,
        "Mood: Hype-man",
        true,
        None::<&str>,
    )?;
    let mood_teacher = MenuItem::with_id(
        app,
        MENU_ID_MOOD_TEACHER,
        "Mood: Teacher",
        true,
        None::<&str>,
    )?;
    let mood_coach = MenuItem::with_id(
        app,
        MENU_ID_MOOD_COACH,
        "Mood: Coach",
        true,
        None::<&str>,
    )?;
    // Cmd+Shift+M is the existing Phase 12 push-to-mute hotkey; we
    // surface the same accelerator so users discover it via the menu.
    let mute = MenuItem::with_id(
        app,
        MENU_ID_MUTE,
        "Mute mic",
        true,
        Some("CmdOrCtrl+Shift+M"),
    )?;
    let open_session = MenuItem::with_id(
        app,
        MENU_ID_OPEN_SESSION,
        "Open Session UI",
        true,
        None::<&str>,
    )?;
    let recalibrate = MenuItem::with_id(
        app,
        MENU_ID_RECALIBRATE,
        "Re-run Calibration",
        true,
        None::<&str>,
    )?;
    let settings = MenuItem::with_id(
        app,
        MENU_ID_SETTINGS,
        "Settings…",
        true,
        None::<&str>,
    )?;
    let separator = PredefinedMenuItem::separator(app)?;
    // Cmd+Q is the OS-standard quit accelerator — the lifecycle override
    // makes sure ONLY this item kills the process (closing the main
    // window via the OS chrome hides it instead).
    let quit = MenuItem::with_id(
        app,
        MENU_ID_QUIT,
        "Quit vibemix",
        true,
        Some("CmdOrCtrl+Q"),
    )?;

    MenuBuilder::new(app)
        .item(&mood_hype)
        .item(&mood_teacher)
        .item(&mood_coach)
        .item(&mute)
        .item(&open_session)
        .item(&recalibrate)
        .item(&settings)
        .item(&separator)
        .item(&quit)
        .build()
}

/// LEFT-CLICK on the tray toggles mascot visibility. RIGHT-CLICK is
/// handled by the OS opening the menu (`show_menu_on_left_click(false)`
/// keeps the default right-click behaviour intact).
fn handle_tray_icon_event(_tray: &tauri::tray::TrayIcon, event: TrayIconEvent) {
    let TrayIconEvent::Click {
        button: MouseButton::Left,
        button_state: MouseButtonState::Up,
        ..
    } = event
    else {
        return;
    };

    let app = _tray.app_handle().clone();
    tauri::async_runtime::spawn(async move {
        let state = match config::load_mascot_state(&app) {
            Ok(s) => s,
            Err(e) => {
                tracing::warn!("tray left-click: load_mascot_state failed: {e}");
                return;
            }
        };
        let next_visible = !state.visible;
        // Reuse the canonical setter so the persisted state + live window
        // both update atomically (set_mascot_visible handles both).
        if let Err(e) = config::set_mascot_visible(app.clone(), next_visible).await {
            tracing::warn!("tray left-click: set_mascot_visible failed: {e}");
        }
    });
}

/// Dispatch menu clicks. Each item either emits a `tray-*` event the
/// webview listens for (mood / mute / recalibrate / settings) or calls
/// an app-side action directly (open session / quit).
fn handle_menu_event(app: &AppHandle, event: tauri::menu::MenuEvent) {
    match event.id().as_ref() {
        MENU_ID_MOOD_HYPE => {
            let _ = app.emit("tray-set-mood", "hype-man");
        }
        MENU_ID_MOOD_TEACHER => {
            let _ = app.emit("tray-set-mood", "teacher");
        }
        MENU_ID_MOOD_COACH => {
            let _ = app.emit("tray-set-mood", "coach");
        }
        MENU_ID_MUTE => {
            // Webview owns the actual mute toggle (Phase 12 push-to-mute
            // path) — tray just kicks the same event the global shortcut
            // already fires through.
            let _ = app.emit("tray-mute-toggle", ());
        }
        MENU_ID_OPEN_SESSION => {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }
        MENU_ID_RECALIBRATE => {
            // Phase 12 Settings drawer owns the confirm-dialog flow —
            // emit the event and let the webview route it.
            let _ = app.emit("tray-recalibrate", ());
        }
        MENU_ID_SETTINGS => {
            // Same channel as the gear button in the session UI.
            let _ = app.emit("tray-open-settings", ());
        }
        MENU_ID_QUIT => {
            // The ONE legitimate exit path. Lifecycle override below
            // makes sure window close events don't reach this code path.
            app.exit(0);
        }
        other => {
            tracing::debug!("unrecognised tray menu id: {other}");
        }
    }
}

/// Hook into the global window event stream and prevent the `main`
/// window's close from killing the process — hide it instead. Mascot
/// has no decorations so its close path is unreachable from the OS.
///
/// Wired from `main.rs` via `.on_window_event(tray::on_window_event)`.
pub fn on_window_event(window: &tauri::Window, event: &tauri::WindowEvent) {
    if let tauri::WindowEvent::CloseRequested { api, .. } = event {
        if window.label() == "main" {
            api.prevent_close();
            let _ = window.hide();
        }
    }
}

/// Swap the tray icon. Plan 13-06 calls this on `session.status` IPC
/// events ("idle" / "live" / "thinking" / "error"). Unknown states are
/// silently ignored — caller mistakes shouldn't blow up the tray.
#[allow(dead_code)]
pub async fn set_tray_state(app: &AppHandle, state: &str) {
    let bytes = match state {
        "idle" => ICON_IDLE,
        "live" => ICON_LIVE,
        "thinking" => ICON_THINKING,
        "error" => ICON_ERROR,
        other => {
            tracing::debug!("set_tray_state: unknown state '{other}', ignoring");
            return;
        }
    };
    let image = match Image::from_bytes(bytes) {
        Ok(i) => i,
        Err(e) => {
            tracing::warn!("set_tray_state: image decode failed: {e}");
            return;
        }
    };

    let Some(handle) = app.try_state::<TrayHandle>() else {
        return;
    };
    let g = handle.icon.lock().await;
    if let Some(tray) = g.as_ref() {
        if let Err(e) = tray.set_icon(Some(image)) {
            tracing::warn!("set_tray_state: set_icon failed: {e}");
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn icon_bytes_are_valid_png_signatures() {
        // PNG magic: 89 50 4E 47 0D 0A 1A 0A
        const PNG: [u8; 8] = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
        for (name, bytes) in [
            ("idle", ICON_IDLE),
            ("live", ICON_LIVE),
            ("thinking", ICON_THINKING),
            ("error", ICON_ERROR),
        ] {
            assert!(bytes.len() >= 8, "{name} icon too small ({} bytes)", bytes.len());
            assert_eq!(
                &bytes[..8],
                &PNG,
                "{name} icon is not a valid PNG (missing magic header)"
            );
        }
    }

    #[test]
    fn menu_ids_are_unique_and_stable() {
        // Stability matters: handle_menu_event matches on these strings;
        // a rename anywhere without updating both sides would silently
        // turn a menu item into a no-op.
        let ids = [
            MENU_ID_MOOD_HYPE,
            MENU_ID_MOOD_TEACHER,
            MENU_ID_MOOD_COACH,
            MENU_ID_MUTE,
            MENU_ID_OPEN_SESSION,
            MENU_ID_RECALIBRATE,
            MENU_ID_SETTINGS,
            MENU_ID_QUIT,
        ];
        let unique: std::collections::HashSet<_> = ids.iter().collect();
        assert_eq!(
            unique.len(),
            ids.len(),
            "duplicate menu ids detected: {ids:?}"
        );
    }

    #[test]
    fn tray_id_matches_lookup_constant() {
        // If set_tray_state ever needs to look up the tray by id instead
        // of the parked handle, it must use this constant. Pinning here
        // catches an accidental rename.
        assert_eq!(TRAY_ID, "vibemix-tray");
    }
}
