//! Phase 11 Wave 2 — OS permission deep-link commands.
//!
//! macOS: opens the Settings app at the relevant Privacy & Security pane via
//! the `x-apple.systempreferences:` URL scheme. We invoke `/usr/bin/open`
//! directly (`Command::new("open")`) instead of going through
//! `tauri_plugin_shell::Shell::open` because the latter is deprecated and
//! has had silent-failure regressions on macOS Sequoia.
//!
//! Windows: no-op (Windows surfaces the mic permission via standard runtime
//! permission grant on first capture; no deep-link needed).
//!
//! The mic-permission trigger is a Wave 2 stub (Ok); Wave 4 wires it to
//! forward an `ipc.permission.check` to the sidecar so the AVCaptureDevice
//! request actually fires.

use tauri::AppHandle;

#[cfg(target_os = "macos")]
const URL_PRIVACY_SCREEN_CAPTURE: &str =
    "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture";
#[cfg(target_os = "macos")]
const URL_PRIVACY_MICROPHONE: &str =
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone";

/// macOS-only helper: shell out to `/usr/bin/open URL` and surface spawn
/// errors as String for the frontend.
#[cfg(target_os = "macos")]
fn open_url(url: &str) -> Result<(), String> {
    std::process::Command::new("open")
        .arg(url)
        .spawn()
        .map(|_| ())
        .map_err(|e| format!("open spawn failed: {e}"))
}

/// Opens System Settings → Privacy & Security → Screen Recording.
/// macOS only. On Windows: returns Ok immediately (no equivalent deep-link;
/// screen capture permission is handled by the screen-capture API at request
/// time).
#[tauri::command]
pub async fn open_screen_recording_settings(app: AppHandle) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        let _ = app;
        open_url(URL_PRIVACY_SCREEN_CAPTURE)
    }
    #[cfg(target_os = "windows")]
    {
        let _ = app;
        Ok(())
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = app;
        Err("unsupported platform".into())
    }
}

/// Opens System Settings → Privacy & Security → Microphone.
#[tauri::command]
pub async fn open_microphone_settings(app: AppHandle) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        let _ = app;
        open_url(URL_PRIVACY_MICROPHONE)
    }
    #[cfg(target_os = "windows")]
    {
        let _ = app;
        Ok(())
    }
    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        let _ = app;
        Err("unsupported platform".into())
    }
}

/// Trigger the AVCaptureDevice mic-permission prompt via the sidecar.
///
/// Wave 2 stub returning Ok so the capability allowlist locks now. Wave 4
/// will forward an `ipc.permission.check` envelope to the sidecar over the
/// WS bus; the sidecar then calls AVCaptureDevice.requestAccess (macOS) or
/// Windows.Devices.Enumeration (Windows) which raises the OS prompt.
#[tauri::command]
pub async fn request_microphone_permission(_app: AppHandle) -> Result<(), String> {
    Ok(())
}
