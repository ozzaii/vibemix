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

use crate::config;

const MAX_RESTARTS: u32 = 3;

/// Environment keys the watchdog relays from the Tauri parent process to the
/// spawned sidecar, IF present and non-empty (RELEASE-AUTH). SECURITY: this is
/// an env *relay* — no key is ever embedded in the binary. The bundled
/// distribution answer is the Bravoh proxy (VIBEMIX_LLM_MODE=proxy), which
/// needs no key; this relay only helps the local/dev "BYO key" path so a key
/// exported in the launching environment reaches the child.
pub(crate) const FORWARDED_ENV_KEYS: [&str; 2] = ["GEMINI_API_KEY", "OPENROUTER_API_KEY"];

/// Target triple of the bundled sidecar. Matches the per-triple directory
/// name produced by scripts/build_sidecar.py.
///
/// Plan 27-06 / REC-09 carry-forward: on macOS the ship now includes BOTH
/// arm64 + x86_64 PyInstaller bundles under bundle.resources. We pick the
/// matching triple at runtime via std::env::consts::ARCH so Apple Silicon
/// users never see the Rosetta prompt on first launch (Pitfall P69).
#[cfg(target_os = "macos")]
fn sidecar_triple() -> &'static str {
    match std::env::consts::ARCH {
        "aarch64" => "aarch64-apple-darwin",
        "x86_64" => "x86_64-apple-darwin",
        // Defensive fallback: unknown arch can't run a bundled binary. Pick
        // the arm64 default so Apple Silicon (the dominant install base)
        // still gets a valid path; the resolver will fail loudly with a
        // clear error if the binary isn't present.
        _ => "aarch64-apple-darwin",
    }
}

#[cfg(target_os = "windows")]
fn sidecar_triple() -> &'static str {
    "x86_64-pc-windows-msvc"
}

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

    let mut wizard_mode = wizard_mode;
    let mut restart_count: u32 = 0;
    loop {
        // First attempt fires immediately; retries sleep so the OS releases
        // 127.0.0.1:8765 cleanly before the next spawn.
        if restart_count > 0 {
            tokio::time::sleep(Duration::from_millis(500 * restart_count as u64)).await;
        }

        // Decide source-vs-bundled BEFORE touching resource_dir(). The
        // landmine (RESEARCH §2): resolve_sidecar_path() calls resource_dir(),
        // which errors / points at a non-existent bundle under `cargo tauri
        // dev`. So we only resolve the bundled path on the Bundled arm —
        // the DevSource arm never calls resource_dir().
        //
        // 2026-05-18 — `--session` routes to a Phase 12 W2 structural stub
        // that never wires Gemini/LiveKit. Per __main__.py docstring the
        // real cohost lives in the flag-less `main()` branch (verbatim port
        // of cohost_v4.py:1925-2080). Drop the flag for post-wizard launches
        // until session_loop owns the snapshot path (v3.2 scope).
        // Wizard launches keep `--wizard` (Phase 11 wave 4 behaviour).
        let invocation = {
            // Lazily resolve the bundled path; the resolver only consumes it
            // on the Bundled arm, so under the dev flag this closure short-
            // circuits and resource_dir() is never called.
            let bundled = if std::env::var("VIBEMIX_DEV_SIDECAR").as_deref() == Ok("1") {
                None
            } else {
                Some(
                    resolve_sidecar_path(&app)
                        .map_err(|e| format!("sidecar lookup failed: {e}"))?,
                )
            };
            resolve_sidecar_invocation(
                bundled,
                wizard_mode,
                &repo_root_from_manifest(),
                &|k: &str| std::env::var(k).ok(),
            )
        };

        let cmd = match invocation {
            SidecarInvocation::Bundled(bin) => {
                // Release path. Two correctness fixes for the "co-host never
                // speaks" release blocker (RELEASE-AUTH):
                //
                // 1. CWD — a Finder/Dock-launched .app runs with cwd "/", so
                //    the bundled binary's load_dotenv() never finds a .env.
                //    We pin cwd to the resource dir (next to the bundled
                //    binary's _internal/ tree), giving the Python-side robust
                //    loader a deterministic place to look for a shipped/.app-
                //    adjacent .env. (The Python loader also probes
                //    app_data_dir()/.env — the supported per-user key drop.)
                //
                // 2. API keys — forward GEMINI_API_KEY / OPENROUTER_API_KEY
                //    from the Tauri parent env to the child WHEN PRESENT.
                //    SECURITY (CLAUDE.md): no key is embedded here — we only
                //    relay a key that already exists in the environment (e.g.
                //    `GEMINI_API_KEY=… open vibemix.app`, or a launchd plist).
                //    The real distribution answer is the Bravoh proxy
                //    (VIBEMIX_LLM_MODE=proxy), which needs no key at all.
                let mut c = app.shell().command(&bin);
                if let Some(parent) = bin.parent() {
                    c = c.current_dir(parent);
                }
                for key in FORWARDED_ENV_KEYS {
                    if let Ok(val) = std::env::var(key) {
                        if !val.is_empty() {
                            c = c.env(key, val);
                        }
                    }
                }
                if wizard_mode {
                    c = c.args(["--wizard"]);
                }
                c
            }
            SidecarInvocation::DevSource { program, args, cwd } => {
                // Dev path — run repo source so `cargo tauri dev` reflects
                // src/vibemix/ HEAD. cwd = repo root, so the Python-side
                // load_dotenv() finds the repo .env. args already include
                // --wizard when set. We ALSO forward GEMINI_API_KEY /
                // OPENROUTER_API_KEY if they happen to be in the dev shell's
                // env, so a key exported in the terminal wins even if the
                // repo .env is absent (no key embedded — env relay only).
                let mut c = app.shell()
                    .command(&program)
                    .args(&args)
                    .current_dir(&cwd);
                for key in FORWARDED_ENV_KEYS {
                    if let Ok(val) = std::env::var(key) {
                        if !val.is_empty() {
                            c = c.env(key, val);
                        }
                    }
                }
                c
            }
        };

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
            // Post-wizard handoff: if we were running the wizard pass and it
            // wrote `first_run_completed: true` before exiting, the next
            // sidecar incarnation must run in `--session` mode so the main
            // UI gets its ipc.session.* handlers. Without this re-spawn the
            // shell sits on "loading vibemix…" forever after the wizard,
            // then the WS goes unreachable and the crash banner fires.
            if wizard_mode && !config::is_first_run(&app) {
                wizard_mode = false;
                restart_count = 0;
                app.emit(
                    "sidecar-state",
                    serde_json::json!({
                        "state": "restarting",
                        "reason": "wizard-handoff",
                    }),
                )
                .ok();
                continue;
            }
            app.emit("sidecar-state", serde_json::json!({ "state": "stopped" }))
                .ok();
            return Ok(());
        }

        // Exit codes 2 + 3 + 4 are sidecar "fatal — do not retry" sentinels.
        // 2 = port 8765 already bound (another vibemix is running)
        // 3 = required audio device missing (BlackHole not installed)
        // 4 = GEMINI_API_KEY not set (mode=direct) — the co-host can't
        //     authenticate and would never speak. Retrying just loops on the
        //     same missing key, so surface a distinct banner the webview can
        //     route to a "set your API key" recovery surface (RELEASE-AUTH).
        // Retrying just races the same fault forever — emit a distinct
        // banner with `reason` set so the webview can route to the
        // matching recovery surface.
        if exit_code == 2 || exit_code == 3 || exit_code == 4 {
            let reason = match exit_code {
                2 => "port-in-use",
                3 => "audio-device-missing",
                _ => "api-key-missing",
            };
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

/// How the watchdog should launch the sidecar this iteration.
///
/// `Bundled` is the shipped/release path: run the PyInstaller `vibemix-core`
/// binary resolved via `resource_dir()`. `DevSource` is the env-gated dev
/// path (BRINGUP-04): run the repo Python entrypoint (`python -m vibemix`)
/// so `cargo tauri dev` reflects `src/vibemix/` HEAD edits without a
/// PyInstaller rebuild. The two arms feed the SAME watchdog supervision
/// (stdout/stderr drain, exit-code sentinels, wizard handoff) — only the
/// command construction differs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum SidecarInvocation {
    /// Run the bundled PyInstaller binary at this path.
    Bundled(PathBuf),
    /// Run a Python interpreter from repo source.
    DevSource {
        program: String,
        args: Vec<String>,
        cwd: PathBuf,
    },
}

/// Decide the sidecar invocation from environment + the bundled path.
///
/// Pure + side-effect-free: the environment is injected as a closure so unit
/// tests pass a fake map and never touch the process env. This is the single
/// landmine-safe decision point for the dev-vs-release split (RESEARCH §2,
/// Opt C A-first):
///
///   * `VIBEMIX_DEV_SIDECAR == "1"` → `DevSource`. The interpreter defaults to
///     `uv` (project venv auto-resolved → `uv run python -m vibemix`); set
///     `VIBEMIX_DEV_PYTHON=/path/to/python3` to override (→ `python3 -m
///     vibemix`). The repo root (cwd) comes from `VIBEMIX_DEV_REPO` when set,
///     else the deterministic `CARGO_MANIFEST_DIR`'s parent's parent
///     (`tauri/src-tauri` → `tauri` → repo root). When the override env is
///     absent we still need a deterministic cwd, so `manifest_parent` is
///     passed in by the caller.
///   * flag absent → `Bundled(bundled)`. IDENTICAL to today's behavior. The
///     bundled path is only ever resolved (via `resource_dir()`) for this
///     arm, so the DevSource path NEVER calls `resource_dir()` (the landmine:
///     `resource_dir()` errors / points at a non-existent bundle under
///     `cargo tauri dev`).
///
/// `--wizard` is folded in HERE (appended last) so both arms share one
/// wizard-arg decision and the call site stays a thin match.
pub(crate) fn resolve_sidecar_invocation(
    bundled: Option<PathBuf>,
    wizard_mode: bool,
    manifest_parent: &std::path::Path,
    env: &impl Fn(&str) -> Option<String>,
) -> SidecarInvocation {
    if env("VIBEMIX_DEV_SIDECAR").as_deref() == Some("1") {
        let program = env("VIBEMIX_DEV_PYTHON").unwrap_or_else(|| "uv".to_string());
        let mut args: Vec<String> = if program == "uv" {
            vec![
                "run".to_string(),
                "python".to_string(),
                "-m".to_string(),
                "vibemix".to_string(),
            ]
        } else {
            vec!["-m".to_string(), "vibemix".to_string()]
        };
        if wizard_mode {
            args.push("--wizard".to_string());
        }
        let cwd = env("VIBEMIX_DEV_REPO")
            .map(PathBuf::from)
            .unwrap_or_else(|| manifest_parent.to_path_buf());
        SidecarInvocation::DevSource { program, args, cwd }
    } else {
        SidecarInvocation::Bundled(
            bundled.expect("bundled sidecar path required when VIBEMIX_DEV_SIDECAR != 1"),
        )
    }
}

/// Compute the repo root from CARGO_MANIFEST_DIR (`tauri/src-tauri`).
///
/// The dev-source cwd defaults to the repo root so `python -m vibemix`
/// resolves the project (and `uv` finds the project venv). Two `parent()`
/// hops: `tauri/src-tauri` → `tauri` → repo root.
fn repo_root_from_manifest() -> PathBuf {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest
        .parent()
        .and_then(|p| p.parent())
        .map(|p| p.to_path_buf())
        .unwrap_or(manifest)
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
    let triple = sidecar_triple();
    let bin_name = format!("vibemix-core-{triple}{exe_suffix}");
    let path = resource_dir
        .join("binaries")
        .join(format!("vibemix-core-{triple}"))
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

    // ---------------------------------------------------------------------
    // Plan 51-02 — env-gated sidecar invocation resolver (dev vs bundled).
    // ---------------------------------------------------------------------

    /// Build a fake env reader from a slice of (key, value) pairs.
    fn fake_env(pairs: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> {
        let map: std::collections::HashMap<String, String> = pairs
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();
        move |k: &str| map.get(k).cloned()
    }

    #[test]
    fn resolve_sidecar_flag_absent_returns_bundled() {
        // Release path: with VIBEMIX_DEV_SIDECAR unset the resolver returns
        // the bundled binary path verbatim (no path-shape change).
        let bundled = PathBuf::from("/app/Resources/binaries/vibemix-core-x/vibemix-core-x");
        let env = fake_env(&[]);
        let manifest_parent = std::path::Path::new("/repo");

        let inv = resolve_sidecar_invocation(
            Some(bundled.clone()),
            /* wizard */ false,
            manifest_parent,
            &env,
        );
        assert_eq!(inv, SidecarInvocation::Bundled(bundled));
    }

    #[test]
    fn resolve_sidecar_flag_set_default_uses_uv_module_vibemix() {
        // Dev path with no VIBEMIX_DEV_PYTHON → program "uv", args run the
        // project: ["run","python","-m","vibemix"].
        let env = fake_env(&[("VIBEMIX_DEV_SIDECAR", "1")]);
        let manifest_parent = std::path::Path::new("/repo");

        let inv =
            resolve_sidecar_invocation(None, false, manifest_parent, &env);
        match inv {
            SidecarInvocation::DevSource { program, args, cwd } => {
                assert_eq!(program, "uv");
                // contains "-m" then "vibemix"
                let m = args.iter().position(|a| a == "-m").expect("has -m");
                assert_eq!(args[m + 1], "vibemix");
                assert_eq!(args, vec!["run", "python", "-m", "vibemix"]);
                // cwd defaults to the manifest parent when VIBEMIX_DEV_REPO unset.
                assert_eq!(cwd, PathBuf::from("/repo"));
            }
            other => panic!("expected DevSource, got {other:?}"),
        }
    }

    #[test]
    fn resolve_sidecar_flag_set_custom_python_runs_module_directly() {
        // VIBEMIX_DEV_PYTHON override → that interpreter, args start ["-m","vibemix"].
        let env = fake_env(&[
            ("VIBEMIX_DEV_SIDECAR", "1"),
            ("VIBEMIX_DEV_PYTHON", "/path/python3"),
        ]);
        let manifest_parent = std::path::Path::new("/repo");

        let inv =
            resolve_sidecar_invocation(None, false, manifest_parent, &env);
        match inv {
            SidecarInvocation::DevSource { program, args, .. } => {
                assert_eq!(program, "/path/python3");
                assert_eq!(args[0], "-m");
                assert_eq!(args[1], "vibemix");
            }
            other => panic!("expected DevSource, got {other:?}"),
        }
    }

    #[test]
    fn resolve_sidecar_dev_repo_env_overrides_cwd() {
        // VIBEMIX_DEV_REPO sets the cwd explicitly (the run script exports it).
        let env = fake_env(&[
            ("VIBEMIX_DEV_SIDECAR", "1"),
            ("VIBEMIX_DEV_REPO", "/elsewhere/dj-set-ai"),
        ]);
        let manifest_parent = std::path::Path::new("/repo");

        let inv =
            resolve_sidecar_invocation(None, false, manifest_parent, &env);
        match inv {
            SidecarInvocation::DevSource { cwd, .. } => {
                assert_eq!(cwd, PathBuf::from("/elsewhere/dj-set-ai"));
            }
            other => panic!("expected DevSource, got {other:?}"),
        }
    }

    #[test]
    fn resolve_sidecar_wizard_arg_appended_in_both_arms() {
        let manifest_parent = std::path::Path::new("/repo");

        // Dev path with wizard → --wizard appended last.
        let dev_env = fake_env(&[("VIBEMIX_DEV_SIDECAR", "1")]);
        let dev = resolve_sidecar_invocation(None, true, manifest_parent, &dev_env);
        match dev {
            SidecarInvocation::DevSource { args, .. } => {
                assert_eq!(args.last().map(String::as_str), Some("--wizard"));
                // wizard is LAST, after -m vibemix.
                assert_eq!(args, vec!["run", "python", "-m", "vibemix", "--wizard"]);
            }
            other => panic!("expected DevSource, got {other:?}"),
        }

        // Bundled path is unaffected by the helper's wizard flag — wizard for
        // the bundled arm is appended at the call site (Task 2), so the
        // helper still returns plain Bundled(path).
        let bundled = PathBuf::from("/app/vibemix-core");
        let rel_env = fake_env(&[]);
        let rel = resolve_sidecar_invocation(
            Some(bundled.clone()),
            true,
            manifest_parent,
            &rel_env,
        );
        assert_eq!(rel, SidecarInvocation::Bundled(bundled));
    }

    #[test]
    fn forwarded_env_keys_relay_gemini_and_openrouter() {
        // RELEASE-AUTH: the watchdog relays exactly these two keys from the
        // parent env to the spawned sidecar. Pin the set so a regression that
        // drops GEMINI_API_KEY (the "co-host never speaks" cause) is forced to
        // update this test. SECURITY: relay only — never an embedded value.
        assert_eq!(FORWARDED_ENV_KEYS, ["GEMINI_API_KEY", "OPENROUTER_API_KEY"]);
    }

    #[test]
    fn fatal_exit_code_4_maps_to_api_key_missing() {
        // The no-retry sentinel for a missing API key. Mirrors the match arm
        // in spawn_sidecar_with_watchdog so the reason string + non-retry
        // behavior stay pinned together (Python __main__ sys.exit(4)).
        let reason = match 4 {
            2 => "port-in-use",
            3 => "audio-device-missing",
            _ => "api-key-missing",
        };
        assert_eq!(reason, "api-key-missing");
    }

    #[test]
    fn repo_root_from_manifest_is_two_levels_up() {
        // CARGO_MANIFEST_DIR is .../tauri/src-tauri; repo root is two hops up.
        let root = repo_root_from_manifest();
        let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        assert_eq!(root, manifest.parent().unwrap().parent().unwrap());
        // Sanity: the repo root contains pyproject.toml (the project marker).
        assert!(
            root.join("pyproject.toml").exists(),
            "repo root {root:?} should contain pyproject.toml"
        );
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
