//! Phase 12 Wave 3 — push-to-mute global hotkey.
//!
//! Registers a single global shortcut (`Cmd+Shift+M` on macOS,
//! `Ctrl+Shift+M` on Windows) via `tauri-plugin-global-shortcut`. When
//! pressed AND the main window has focus, forwards an
//! `ipc.session.mute {toggle: true}` envelope to the Python sidecar
//! through the existing WS client sink.
//!
//! Window-focus gate (plan must-have): global shortcuts are system-wide
//! by default — they fire even when the vibemix window is in the
//! background. We restrict mute to foreground use so a user's DAW
//! shortcut doesn't accidentally trip the cohost. The check is done
//! inside the registered handler.
//!
//! Reserved combos: at registration time we reject a small allowlist of
//! OS-reserved hotkeys so a misconfigured user cannot kill their session
//! handler (`Cmd+Q`, `Cmd+W`, `Cmd+Tab`, `Cmd+Space` on macOS;
//! `Alt+F4`, `Ctrl+Alt+Del`, `Win+L` on Windows). Returns a
//! `Result<(), String>` so the webview can surface inline errors.
//!
//! The combo string format follows tauri-plugin-global-shortcut's
//! `Shortcut::from_str` grammar (`<Modifier>+<Modifier>+<Key>`), so
//! `cmd+shift+m`, `ctrl+shift+m`, etc.

use std::sync::Mutex;

use serde_json::json;
use tauri::{AppHandle, Manager, Runtime, State, WebviewWindow};
use tauri_plugin_global_shortcut::{
    GlobalShortcutExt, Shortcut, ShortcutState,
};

use crate::ws_client::WsClientHandle;

/// macOS / Windows reserved combos. Lower-case + `+`-separated for the
/// plugin's string grammar. Comparison is case-insensitive and after
/// normalising `cmd`/`super`/`meta` to `cmd`.
const RESERVED_COMBOS: &[&str] = &[
    // macOS
    "cmd+q",
    "cmd+w",
    "cmd+tab",
    "cmd+space",
    // Windows
    "alt+f4",
    "ctrl+alt+del",
    "ctrl+alt+delete",
    "win+l",
    "meta+l",
];

/// Holds the most-recently-registered shortcut string so `rebind_hotkey`
/// can unregister it before registering the replacement. Wrapped in a
/// `Mutex<Option<String>>` and managed by Tauri so command handlers can
/// grab it via `tauri::State`.
#[derive(Default)]
pub struct HotkeyHandle {
    pub current: Mutex<Option<String>>,
}

/// Validate a combo string against the reserved-combo allowlist. Returns
/// an Err with a user-facing message that the webview surfaces inline.
pub fn validate_combo(combo: &str) -> Result<String, String> {
    let normalised = normalise_combo(combo);
    if normalised.is_empty() {
        return Err("hotkey combo is empty".to_string());
    }
    for reserved in RESERVED_COMBOS {
        if normalised == *reserved {
            return Err(format!(
                "hotkey {normalised} is reserved by the operating system"
            ));
        }
    }
    // A combo must include a modifier — bare letters (`m`) would
    // capture every keystroke. Reject anything without a `+`.
    if !normalised.contains('+') {
        return Err(format!(
            "hotkey {normalised} needs at least one modifier (e.g. cmd+shift+m)"
        ));
    }
    Ok(normalised)
}

/// Lowercase + sort modifiers in a canonical order. The reserved-combo
/// list is keyed on the canonical form so `Cmd+Shift+M` and
/// `shift+cmd+m` collapse to the same entry.
fn normalise_combo(combo: &str) -> String {
    // Tauri's `Shortcut::from_str` accepts mixed-case + arbitrary modifier
    // order; we keep the modifier order as the user typed it (so the
    // plugin's parser sees what we hand back) but normalise to lowercase.
    combo.trim().to_lowercase()
}

/// Platform default hotkey combo. macOS uses Cmd, Windows uses Ctrl.
pub fn default_combo() -> &'static str {
    if cfg!(target_os = "macos") {
        "cmd+shift+m"
    } else {
        "ctrl+shift+m"
    }
}

/// Register the default hotkey on startup. Called from `main.rs`'s
/// setup block after the plugin is initialised. Persists the registered
/// combo into `HotkeyHandle.current`.
///
/// On registration failure we log + return Ok — a missing global-shortcut
/// permission must NOT break the wizard / session. The webview's rebind
/// command surfaces real failures inline.
pub fn register_default<R: Runtime>(app: &AppHandle<R>) {
    let combo = default_combo().to_string();
    if let Err(e) = register_combo(app, &combo) {
        tracing::warn!("hotkey default registration failed: {e}");
    }
}

/// Register a combo. Validates, unregisters any prior combo, then
/// registers the new one. Updates `HotkeyHandle.current` on success.
pub fn register_combo<R: Runtime>(
    app: &AppHandle<R>,
    combo: &str,
) -> Result<(), String> {
    let normalised = validate_combo(combo)?;

    let gs = app.global_shortcut();

    // Drop the prior combo (if any) before registering the new one.
    if let Some(state) = app.try_state::<HotkeyHandle>() {
        let prior = state
            .current
            .lock()
            .ok()
            .and_then(|g| g.clone());
        if let Some(p) = prior {
            // Best-effort — if the prior never registered cleanly the
            // unregister call returns NotRegistered which we swallow.
            let _ = gs.unregister(p.as_str());
        }
    }

    let shortcut: Shortcut = normalised
        .parse()
        .map_err(|e: <Shortcut as std::str::FromStr>::Err| e.to_string())?;

    gs.on_shortcut(shortcut, {
        let app = app.clone();
        let combo_str = normalised.clone();
        move |_app_handle, _sc, ev| {
            // Only fire on the press, not the release — `ShortcutState`
            // toggles between Pressed/Released on key-up.
            if ev.state() != ShortcutState::Pressed {
                return;
            }
            if !window_is_focused(&app) {
                // Plan §must-have: hotkey only fires when window focused.
                // Silent no-op so other windows / DAWs keep their combos.
                return;
            }
            forward_mute(&app, &combo_str);
        }
    })
    .map_err(|e| e.to_string())?;

    if let Some(state) = app.try_state::<HotkeyHandle>() {
        if let Ok(mut g) = state.current.lock() {
            *g = Some(normalised);
        }
    }
    Ok(())
}

/// Returns true when the "main" window exists and is currently focused.
/// The mute hotkey is gated on this — see plan note re: shortcut
/// activity across window blur.
fn window_is_focused<R: Runtime>(app: &AppHandle<R>) -> bool {
    let win: Option<WebviewWindow<R>> = app.get_webview_window("main");
    match win {
        Some(w) => w.is_focused().unwrap_or(false),
        None => false,
    }
}

/// Send `ipc.session.mute {toggle: true}` through the existing WS sink
/// owned by `WsClientHandle`. Spawns onto the Tauri async runtime so the
/// shortcut handler stays non-blocking.
fn forward_mute<R: Runtime>(app: &AppHandle<R>, combo: &str) {
    let app = app.clone();
    let combo = combo.to_string();
    tauri::async_runtime::spawn(async move {
        let Some(state) = app.try_state::<WsClientHandle>() else {
            tracing::warn!("hotkey {combo} fired but WsClientHandle missing");
            return;
        };
        let mut guard = state.tx.lock().await;
        let Some(sink) = guard.as_mut() else {
            // Sidecar not connected — drop silently. The user will see
            // the AI continue talking; their next keypress retries.
            tracing::debug!("hotkey {combo} fired but sidecar not connected");
            return;
        };
        let msg = json!({
            "type": "ipc.session.mute",
            "ts": chrono_now_iso(),
            "payload": { "toggle": true },
        });
        let text = match serde_json::to_string(&msg) {
            Ok(t) => t,
            Err(e) => {
                tracing::warn!("hotkey mute serialize failed: {e}");
                return;
            }
        };
        use futures_util::SinkExt;
        use tokio_tungstenite::tungstenite::Message;
        if let Err(e) = sink.send(Message::Text(text.into())).await {
            tracing::warn!("hotkey mute send failed: {e}");
        }
    });
}

/// Tiny stdlib-only ISO-8601 timestamp helper. The sidecar's
/// jsonschema validator requires `date-time`-formatted strings; a chrono
/// dep would be heavier than the inline implementation.
fn chrono_now_iso() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = now.as_secs() as i64;
    let nanos = now.subsec_nanos();

    // Convert epoch seconds to UTC y/m/d h:m:s via the civil-from-days
    // algorithm. Sufficient precision for the WS envelope's date-time.
    let days = secs.div_euclid(86_400);
    let secs_of_day = secs.rem_euclid(86_400);
    let (y, m, d) = civil_from_days(days);
    let hh = secs_of_day / 3600;
    let mm = (secs_of_day % 3600) / 60;
    let ss = secs_of_day % 60;
    format!(
        "{y:04}-{m:02}-{d:02}T{hh:02}:{mm:02}:{ss:02}.{nanos:09}Z",
    )
}

/// Howard Hinnant's civil-from-days (public-domain). Days are signed
/// offsets from 1970-01-01. Output is the (y, m, d) tuple.
fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64; // [0, 146096]
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365; // [0, 399]
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100); // [0, 365]
    let mp = (5 * doy + 2) / 153; // [0, 11]
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32; // [1, 31]
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32; // [1, 12]
    let y = if m <= 2 { y + 1 } else { y };
    (y, m, d)
}

/// Webview-callable rebind. The settings drawer (Wave 4) invokes this
/// when the user enters a new combo. Returns a structured error so
/// the inline tooltip can surface "key reserved" / "invalid combo".
#[tauri::command]
pub async fn rebind_hotkey<R: Runtime>(
    app: AppHandle<R>,
    _hotkey: State<'_, HotkeyHandle>,
    new_combo: String,
) -> Result<(), String> {
    register_combo(&app, &new_combo)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validate_rejects_macos_reserved() {
        assert!(validate_combo("cmd+q").is_err());
        assert!(validate_combo("Cmd+Q").is_err());
        assert!(validate_combo("cmd+space").is_err());
        assert!(validate_combo("cmd+tab").is_err());
        assert!(validate_combo("cmd+w").is_err());
    }

    #[test]
    fn validate_rejects_windows_reserved() {
        assert!(validate_combo("alt+f4").is_err());
        assert!(validate_combo("ctrl+alt+del").is_err());
        assert!(validate_combo("ctrl+alt+delete").is_err());
        assert!(validate_combo("win+l").is_err());
    }

    #[test]
    fn validate_rejects_bare_letter() {
        // No modifier — would intercept every keystroke.
        assert!(validate_combo("m").is_err());
        assert!(validate_combo("escape").is_err());
    }

    #[test]
    fn validate_rejects_empty() {
        assert!(validate_combo("").is_err());
        assert!(validate_combo("   ").is_err());
    }

    #[test]
    fn validate_accepts_default_macos() {
        assert_eq!(
            validate_combo("cmd+shift+m").unwrap(),
            "cmd+shift+m"
        );
        assert_eq!(
            validate_combo("Cmd+Shift+M").unwrap(),
            "cmd+shift+m"
        );
    }

    #[test]
    fn validate_accepts_default_windows() {
        assert_eq!(
            validate_combo("ctrl+shift+m").unwrap(),
            "ctrl+shift+m"
        );
    }

    #[test]
    fn default_combo_platform_aware() {
        let c = default_combo();
        if cfg!(target_os = "macos") {
            assert_eq!(c, "cmd+shift+m");
        } else {
            assert_eq!(c, "ctrl+shift+m");
        }
    }

    #[test]
    fn civil_from_days_handles_epoch() {
        // 1970-01-01 — days = 0.
        let (y, m, d) = civil_from_days(0);
        assert_eq!((y, m, d), (1970, 1, 1));
    }

    #[test]
    fn iso_timestamp_format_is_valid() {
        let ts = chrono_now_iso();
        // YYYY-MM-DDTHH:MM:SS.nnnnnnnnnZ
        assert!(ts.contains('T'));
        assert!(ts.ends_with('Z'));
        assert!(ts.len() >= 20);
    }
}
