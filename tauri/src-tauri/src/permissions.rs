//! Phase 11 Wave 2 — OS permission deep-link commands.
//!
//! macOS: opens the Settings app at the relevant Privacy & Security pane via
//! the `x-apple.systempreferences:` URL scheme. Windows: no-op (Windows
//! surfaces the mic permission via standard runtime permission grant on
//! first capture; no deep-link needed).
//!
//! The mic-permission trigger is a Wave 2 stub (Ok); Wave 4 wires it to
//! forward an `ipc.permission.check` to the sidecar so the AVCaptureDevice
//! request actually fires.

use tauri::AppHandle;
use tauri_plugin_shell::ShellExt;

const URL_PRIVACY_SCREEN_CAPTURE: &str =
    "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture";
const URL_PRIVACY_MICROPHONE: &str =
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone";

/// Opens System Settings → Privacy & Security → Screen Recording.
/// macOS only. On Windows: returns Ok immediately (no equivalent deep-link;
/// screen capture permission is handled by the screen-capture API at request
/// time).
#[tauri::command]
pub async fn open_screen_recording_settings(app: AppHandle) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        app.shell()
            .open(URL_PRIVACY_SCREEN_CAPTURE, None)
            .map_err(|e| format!("open failed: {e}"))?;
        Ok(())
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
        app.shell()
            .open(URL_PRIVACY_MICROPHONE, None)
            .map_err(|e| format!("open failed: {e}"))?;
        Ok(())
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
