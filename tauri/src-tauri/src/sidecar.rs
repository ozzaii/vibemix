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

/// Target triple of the bundled sidecar. Matches the per-triple directory
/// name produced by scripts/build_sidecar.py. Hard-coded for the macOS build
/// — Windows ships under its own triple via a parallel cfg block.
#[cfg(target_os = "macos")]
const SIDECAR_TRIPLE: &str = "aarch64-apple-darwin";
#[cfg(target_os = "windows")]
const SIDECAR_TRIPLE: &str = "x86_64-pc-windows-msvc";

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

        let sidecar_bin = resolve_sidecar_path(&app)
            .map_err(|e| format!("sidecar lookup failed: {e}"))?;
        let mut cmd = app.shell().command(&sidecar_bin);
        // Phase 12 Wave 3 — post-wizard launches spawn the sidecar with
        // `--session` so SessionLoop registers its ipc.session.* handlers.
        // Wizard launches keep `--wizard` (Phase 11 wave 4 behaviour).
        if wizard_mode {
            cmd = cmd.args(["--wizard"]);
        } else {
            cmd = cmd.args(["--session"]);
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

        // Exit codes 2 + 3 are sidecar "fatal — do not retry" sentinels.
        // 2 = port 8765 already bound (another vibemix is running)
        // 3 = required audio device missing (BlackHole not installed)
        // Retrying just races the same fault forever — emit a distinct
        // banner with `reason` set so the webview can route to the
        // matching recovery surface.
        if exit_code == 2 || exit_code == 3 {
            let reason = if exit_code == 2 { "port-in-use" } else { "audio-device-missing" };
            let last_line = read_last_log_line(&log_path).unwrap_or_default();
            app.emit(
                "sidecar-crashed",
                serde_json::json!({
                    "restart_count": 0,
                    "last_error": last_line,
                    "reason": reason,
                }),
            )
            .ok();
            return Err(format!(
                "sidecar refused to start (reason={reason}, exit={exit_code})"
            ));
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

/// Resolve the bundled sidecar binary path inside the .app/.exe.
///
/// Tauri's `bundle.resources` puts each pattern's match under
/// Contents/Resources/<relative-path> (macOS) or resources/<relative-path>
/// (Windows), preserving the directory structure. The sidecar's
/// PyInstaller --onedir tree is therefore at:
///     Contents/Resources/binaries/vibemix-core-<triple>/
/// with the inner binary at:
///     vibemix-core-<triple>/vibemix-core-<triple>[.exe]
/// next to its _internal/ tree (which the PyInstaller bootloader needs).
fn resolve_sidecar_path(app: &AppHandle) -> Result<PathBuf, String> {
    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|e| format!("resource_dir() failed: {e}"))?;
    let exe_suffix = if cfg!(target_os = "windows") { ".exe" } else { "" };
    let bin_name = format!("vibemix-core-{SIDECAR_TRIPLE}{exe_suffix}");
    let path = resource_dir
        .join("binaries")
        .join(format!("vibemix-core-{SIDECAR_TRIPLE}"))
        .join(&bin_name);
    if !path.exists() {
        return Err(format!(
            "bundled sidecar binary missing at {}",
            path.display()
        ));
    }
    Ok(path)
}

/// Read the most-informative line from the tail of the rotated log.
///
/// Used as the `last_error` payload on `sidecar-crashed`. We prefer the
/// *last `[FATAL]` line* over the literal last non-empty line because
/// the Python sidecar can emit benign post-FATAL chatter (atexit
/// handlers, asyncio cleanup, retry banners) that would otherwise
/// clobber the actual cause of death in the crash banner. Falls back to
/// the last non-empty line when no `[FATAL]` marker is present (e.g.,
/// the sidecar died from an uncaught exception with a regular
/// traceback tail).
pub(crate) fn read_last_log_line(p: &std::path::Path) -> Option<String> {
    use std::io::{BufRead, BufReader};
    let f = std::fs::File::open(p).ok()?;
    let lines: Vec<String> = BufReader::new(f)
        .lines()
        .map_while(Result::ok)
        .filter(|l| !l.trim().is_empty())
        .collect();
    lines
        .iter()
        .rev()
        .find(|l| l.contains("[FATAL]"))
        .or_else(|| lines.last())
        .cloned()
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

    #[test]
    fn read_last_log_line_prefers_fatal_over_post_fatal_chatter() {
        // Real-world pattern: Python sidecar logs [FATAL] then atexit /
        // asyncio cleanup spew. The crash banner needs the FATAL line,
        // not the meaningless tail.
        let mut f = NamedTempFile::new().unwrap();
        writeln!(f, "-> wizard boot").unwrap();
        writeln!(f, "[FATAL] ws_bus port bind failed on 127.0.0.1:8765").unwrap();
        writeln!(f, "[FATAL] another vibemix process is already running; quit it before relaunching.").unwrap();
        writeln!(f, "asyncio cleanup task <Task pending name='Task-3'>").unwrap();
        writeln!(f, "  done").unwrap();
        f.flush().unwrap();

        let last = read_last_log_line(f.path()).expect("should find a FATAL line");
        // The last [FATAL] (not the literal last line) wins.
        assert!(last.contains("another vibemix process is already running"));
        assert!(last.starts_with("[FATAL]"));
    }

    #[test]
    fn read_last_log_line_falls_back_to_tail_when_no_fatal() {
        // No [FATAL] marker — the helper still returns the last line.
        let mut f = NamedTempFile::new().unwrap();
        writeln!(f, "Traceback (most recent call last):").unwrap();
        writeln!(f, "  File \"x.py\", line 1").unwrap();
        writeln!(f, "RuntimeError: boom").unwrap();
        f.flush().unwrap();

        let last = read_last_log_line(f.path()).expect("should find tail");
        assert_eq!(last, "RuntimeError: boom");
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
