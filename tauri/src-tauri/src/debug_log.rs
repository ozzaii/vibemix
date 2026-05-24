//! Frontend observability sink (headless-operator support).
//!
//! The webview's `tauri/ui/src/debug-log.ts` mirrors every tagged log line
//! (`[vmx:click]` / `[vmx:ipc>]` / `[vmx:ipc<]` / `[vmx:ws]` / `[vmx:state]` /
//! `[vmx:error]`) to BOTH the DevTools console AND, via this command, to a
//! tailable file on disk so a headless operator (or an autonomous agent) can
//! `Read`/`tail` the UI's behaviour without a live DevTools session.
//!
//! Sink path: `<app-local-data>/vibemix/logs/ui.log`
//!   - macOS:   `~/Library/Application Support/vibemix/logs/ui.log`
//!   - Windows: `%LOCALAPPDATA%\vibemix\logs\ui.log`
//! (Mirrors the sidecar.log resolution in main.rs `setup`.)
//!
//! Each line is prefixed with a UTC RFC-3339 timestamp and appended (the file
//! grows for the session; rotation is out of scope — `sidecar.log` is the
//! rotating one, ui.log is the cheap dev/debug tail). The append is best-effort
//! and never returns a hard error that would surface as a webview reject loop:
//! a disk failure is logged via `tracing` and swallowed, so a logging call can
//! never break a UI interaction.

use std::fs::{self, OpenOptions};
use std::io::Write;

use tauri::{AppHandle, Manager, Runtime};

/// Append one UI log line (timestamped) to `<app-local-data>/vibemix/logs/ui.log`.
///
/// Webview-callable (`invoke("debug_log", { line })`). Creates the logs dir on
/// demand. Returns `Ok(())` even on a write failure — the failure is recorded
/// via `tracing::warn!` so it's discoverable in the sidecar log, but the
/// command never rejects (the console copy in the webview stands regardless).
#[tauri::command]
pub fn debug_log<R: Runtime>(app: AppHandle<R>, line: String) -> Result<(), String> {
    // Resolve the same app-local-data root used for sidecar.log. Fall back to
    // the OS temp dir if resolution fails (should be impossible on mac/win).
    let log_path = match app.path().app_local_data_dir() {
        Ok(dir) => {
            let logs_dir = dir.join("vibemix").join("logs");
            if let Err(e) = fs::create_dir_all(&logs_dir) {
                tracing::warn!("debug_log: create logs dir failed: {e}");
                return Ok(());
            }
            logs_dir.join("ui.log")
        }
        Err(_) => std::env::temp_dir().join("vibemix-ui.log"),
    };

    // Timestamp via the wall clock as RFC-3339-ish UTC. We avoid pulling a new
    // crate dep: format seconds-since-epoch is enough for a tail-and-correlate
    // workflow, but a human-readable instant is friendlier — use SystemTime.
    let ts = humantime_now();

    let mut f = match OpenOptions::new().create(true).append(true).open(&log_path) {
        Ok(f) => f,
        Err(e) => {
            tracing::warn!("debug_log: open {log_path:?} failed: {e}");
            return Ok(());
        }
    };
    if let Err(e) = writeln!(f, "{ts} {line}") {
        tracing::warn!("debug_log: write failed: {e}");
    }
    Ok(())
}

/// Best-effort human-ish UTC timestamp without adding a dep. Falls back to an
/// epoch-seconds string if the clock is before the epoch (impossible in
/// practice). Format: `2026-05-24T12:34:56Z`-style is overkill without `chrono`,
/// so we emit `t=<epoch_secs>.<millis>` which is monotone + greppable and lets
/// the operator correlate with the sidecar log's own stamps.
fn humantime_now() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(d) => format!("t={}.{:03}", d.as_secs(), d.subsec_millis()),
        Err(_) => "t=0.000".to_string(),
    }
}
