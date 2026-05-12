//! Phase 11 Wave 2 — sidecar lifecycle: spawn + watchdog + log rotation.
//!
//! Lifts RESEARCH Pattern 1 verbatim. The watchdog tries 3× to restart the
//! Python sidecar; on the 4th consecutive non-zero exit it emits
//! `sidecar-crashed` (consumed by the webview crash banner) and exits the
//! loop permanently. A clean exit (code 0) stops the loop without restart.
//!
//! Logs stream stdout/stderr from the PyInstaller bundle into a
//! `file-rotate`-managed log under `$APPLOCALDATA/vibemix/logs/sidecar.log`
//! (10 MB × 5 files per CONTEXT decision D-Area-1.4).
//!
//! The `restart_sidecar` `#[tauri::command]` is wired to the crash banner's
//! Restart button — Wave 2 publishes it as a stub command that emits a
//! state event but does not actually re-invoke `spawn_sidecar_with_watchdog`
//! (the watchdog loop has already exited at that point; respawning requires
//! a separate task channel that Wave 4 will add). The capability allowlist
//! locks at Wave 2 so we never surface "not allowed by ACL" later.

use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use file_rotate::{
    compression::Compression,
    suffix::AppendCount,
    ContentLimit, FileRotate,
};
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const MAX_RESTARTS: u32 = 3;

/// Shared handle to the most-recently-spawned sidecar child. `restart_sidecar`
/// reads this to kill the current process; the watchdog loop refreshes it on
/// every spawn. Wave 4 may extend this struct with a wake-up channel.
pub struct SidecarHandle {
    pub child: Arc<Mutex<Option<CommandChild>>>,
}

impl Default for SidecarHandle {
    fn default() -> Self {
        SidecarHandle {
            child: Arc::new(Mutex::new(None)),
        }
    }
}

/// Spawn the PyInstaller-built `vibemix-core` binary and supervise it.
///
/// Up to MAX_RESTARTS restarts. On clean exit (code 0) returns `Ok(())`.
/// On exhaustion emits `sidecar-crashed` and returns `Err(...)`.
pub async fn spawn_sidecar_with_watchdog(
    app: AppHandle,
    wizard_mode: bool,
    log_path: PathBuf,
) -> Result<(), String> {
    let log = match FileRotate::new(
        log_path.clone(),
        AppendCount::new(5),
        ContentLimit::Bytes(10 * 1024 * 1024),
        Compression::None,
        None,
    ) {
        rotate => Arc::new(Mutex::new(rotate)),
    };

    let mut restart_count: u32 = 0;
    loop {
        // First attempt fires immediately; retries sleep so the OS releases
        // 127.0.0.1:8765 cleanly before the next spawn.
        if restart_count > 0 {
            tokio::time::sleep(Duration::from_millis(500 * restart_count as u64)).await;
        }

        let mut cmd = app
            .shell()
            .sidecar("vibemix-core")
            .map_err(|e| format!("sidecar lookup failed: {e}"))?;
        if wizard_mode {
            cmd = cmd.args(["--wizard"]);
        }

        let (mut rx, child) = cmd
            .spawn()
            .map_err(|e| format!("sidecar spawn failed: {e}"))?;

        // Publish the child handle for restart_sidecar to kill it.
        if let Some(state) = app.try_state::<SidecarHandle>() {
            if let Ok(mut guard) = state.child.lock() {
                *guard = Some(child);
            }
        }

        app.emit("sidecar-state", serde_json::json!({ "state": "running" }))
            .ok();

        let log_clone = log.clone();
        let app_clone = app.clone();

        // Drain the child's stdout/stderr until it terminates.
        let exit_code: i32 = tokio::spawn(async move {
            use std::io::Write as _;
            while let Some(event) = rx.recv().await {
                match event {
                    CommandEvent::Stdout(b) | CommandEvent::Stderr(b) => {
                        if let Ok(mut g) = log_clone.lock() {
                            let _ = g.write_all(&b);
                        }
                    }
                    CommandEvent::Error(e) => {
                        app_clone.emit("sidecar-error", e).ok();
                    }
                    CommandEvent::Terminated(payload) => {
                        return payload.code.unwrap_or(-1);
                    }
                    _ => {}
                }
            }
            -1
        })
        .await
        .unwrap_or(-1);

        // Clear the published child handle — the process is gone.
        if let Some(state) = app.try_state::<SidecarHandle>() {
            if let Ok(mut guard) = state.child.lock() {
                *guard = None;
            }
        }

        if exit_code == 0 {
            app.emit("sidecar-state", serde_json::json!({ "state": "stopped" }))
                .ok();
            return Ok(());
        }

        restart_count += 1;
        if restart_count > MAX_RESTARTS {
            let last_line = read_last_log_line(&log_path).unwrap_or_default();
            app.emit(
                "sidecar-crashed",
                serde_json::json!({
                    "restart_count": restart_count - 1,
                    "last_error": last_line,
                }),
            )
            .ok();
            return Err(format!(
                "sidecar crashed after {} restarts (exit code {})",
                MAX_RESTARTS, exit_code
            ));
        }

        app.emit(
            "sidecar-state",
            serde_json::json!({ "state": "restarting", "attempt": restart_count }),
        )
        .ok();
    }
}

/// Read the last non-empty line from the rotated log. Used as the
/// `last_error` payload on `sidecar-crashed`.
pub(crate) fn read_last_log_line(p: &std::path::Path) -> Option<String> {
    use std::io::{BufRead, BufReader};
    let f = std::fs::File::open(p).ok()?;
    BufReader::new(f)
        .lines()
        .filter_map(|l| l.ok())
        .filter(|l| !l.trim().is_empty())
        .last()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn max_restarts_locked_at_three() {
        // CONTEXT D-Area-1.2: 3× automatic restart attempts before banner.
        // This test pins the constant so a regression PR is forced to update
        // both the code and the planning doc.
        assert_eq!(MAX_RESTARTS, 3);
    }

    #[test]
    fn read_last_log_line_returns_non_empty_tail() {
        let mut f = NamedTempFile::new().unwrap();
        writeln!(f, "first line").unwrap();
        writeln!(f, "[error] something broke").unwrap();
        writeln!(f, "").unwrap();
        writeln!(f, "   ").unwrap();
        f.flush().unwrap();

        let last = read_last_log_line(f.path()).expect("should find a line");
        assert_eq!(last, "[error] something broke");
    }

    #[test]
    fn read_last_log_line_returns_none_for_missing_path() {
        let bogus = std::path::Path::new("/nonexistent/path/sidecar.log");
        assert!(read_last_log_line(bogus).is_none());
    }

    #[test]
    fn read_last_log_line_returns_none_for_empty_file() {
        let f = NamedTempFile::new().unwrap();
        assert!(read_last_log_line(f.path()).is_none());
    }
}

/// Webview-callable restart trigger — wired to the crash banner button.
///
/// Wave 2 stub: kills the current child if present and emits a state event.
/// Wave 4 wires the actual respawn — the watchdog has already exited by the
/// time the user sees the banner, so we need a separate channel to restart
/// the supervisor.
#[tauri::command]
pub async fn restart_sidecar(app: AppHandle) -> Result<(), String> {
    if let Some(state) = app.try_state::<SidecarHandle>() {
        if let Ok(mut guard) = state.child.lock() {
            if let Some(child) = guard.take() {
                let _ = child.kill();
            }
        }
    }
    app.emit(
        "sidecar-state",
        serde_json::json!({ "state": "restarting", "attempt": 0 }),
    )
    .ok();
    // Wave 4 wires the actual respawn path; Wave 2 just makes the capability
    // and webview-side wiring reachable end-to-end.
    Ok(())
}
