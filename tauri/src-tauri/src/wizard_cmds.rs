//! wizard_cmds.rs — Phase 49 Tauri commands for the install wizard surface.
//!
//! Exposes:
//!   - `run_companion_fetch(dry_run: bool) -> String`
//!     Spawns `installer/companion/fetch_drivers.{sh,ps1}` per platform.
//!     Streams stdout JSON lines to the webview via the existing
//!     `audio.probe.*` event family (Phase 49 extended with an additive
//!     `auto_install_attempted` payload field — zero new event types).
//!
//!   - `run_audio_config(action: String) -> AudioConfigResult`
//!     Invokes `installer/companion/audio_config.py` with the supplied
//!     `--<action>` flag (`probe-48k`, `configure-routing`, `probe-only`,
//!     `remove-routing`). Returns the JSON payload as a strongly-typed
//!     struct.
//!
//!   - `open_audio_settings(platform: String)`
//!     Opens Audio MIDI Setup (Mac) / Sound settings (Win) via the OS
//!     shell. Plan 49-03 wizard step-48k-probe.ts hooks the manual link
//!     here.
//!
//! Capability scope: `shell:allow-execute` extended in
//! `capabilities/default.json` to include the three companion script
//! paths (Plan 49-04 Task 5). Zero new permission identifier.
//!
//! Step-0 worktree-sync invariant (per `feedback_worktree_must_sync_main_first`)
//! applies if executing in a worktree.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

#[derive(Debug, Serialize, Deserialize)]
pub struct AudioConfigResult {
    pub ok: bool,
    #[serde(default)]
    pub measured_khz: f64,
    #[serde(default)]
    pub expected_khz: f64,
    #[serde(default)]
    pub reason: Option<String>,
    #[serde(default)]
    pub installed: Option<bool>,
    #[serde(default)]
    pub driver: Option<String>,
    #[serde(default)]
    pub action: Option<String>,
    #[serde(default)]
    pub platform: Option<String>,
}

fn companion_dir(app: &AppHandle) -> Result<PathBuf, String> {
    // In dev: project root / installer / companion.
    // In production: app resource dir / installer / companion.
    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|e| format!("resource_dir: {e}"))?;
    let candidate = resource_dir.join("installer").join("companion");
    if candidate.exists() {
        return Ok(candidate);
    }
    // Dev fallback — walk up from CARGO_MANIFEST_DIR if env present.
    if let Some(dir) = option_env!("CARGO_MANIFEST_DIR") {
        let dev_path = PathBuf::from(dir)
            .join("..")
            .join("..")
            .join("installer")
            .join("companion");
        if dev_path.exists() {
            return Ok(dev_path);
        }
    }
    Err(format!("installer/companion not found at {}", candidate.display()))
}

/// Spawn the platform-appropriate companion fetch script.
///
/// Streams progress events on the `companion.fetch.progress` topic
/// (Plan 49-03 step-driver-fetch.ts subscribes). Returns the final
/// stdout JSON line as a String.
#[tauri::command]
pub async fn run_companion_fetch(
    app: AppHandle,
    dry_run: bool,
) -> Result<String, String> {
    let companion = companion_dir(&app)?;
    let (program, args, script_path): (&str, Vec<String>, PathBuf) = if cfg!(target_os = "macos") {
        let script = companion.join("fetch_drivers.sh");
        let mut args = vec![script.display().to_string()];
        if dry_run {
            args.push("--dry-run".to_string());
        } else {
            args.push("--auto".to_string());
        }
        ("bash", args, script)
    } else if cfg!(target_os = "windows") {
        let script = companion.join("fetch_drivers.ps1");
        let mut args = vec![
            "-NoProfile".to_string(),
            "-ExecutionPolicy".to_string(),
            "Bypass".to_string(),
            "-File".to_string(),
            script.display().to_string(),
        ];
        if dry_run {
            args.push("-DryRun".to_string());
        } else {
            args.push("-Auto".to_string());
        }
        ("powershell.exe", args, script)
    } else {
        return Err("unsupported platform".to_string());
    };

    if !script_path.exists() {
        return Err(format!("companion script missing at {}", script_path.display()));
    }

    let shell = app.shell();
    let (mut rx, _child) = shell
        .command(program)
        .args(args)
        .spawn()
        .map_err(|e| format!("spawn failed: {e}"))?;

    let mut final_line = String::new();
    while let Some(event) = rx.recv().await {
        match event {
            CommandEvent::Stdout(bytes) => {
                let line = String::from_utf8_lossy(&bytes).to_string();
                // Emit each line for the wizard to consume.
                let payload: serde_json::Value =
                    serde_json::from_str(&line).unwrap_or_else(|_| serde_json::json!({ "raw": line.clone() }));
                let _ = app.emit("companion.fetch.progress", payload);
                final_line = line;
            }
            CommandEvent::Stderr(bytes) => {
                let _ = app.emit(
                    "companion.fetch.stderr",
                    String::from_utf8_lossy(&bytes).to_string(),
                );
            }
            CommandEvent::Terminated(payload) => {
                if let Some(code) = payload.code {
                    if code != 0 {
                        return Err(format!("companion fetch exited {code}"));
                    }
                }
                break;
            }
            _ => {}
        }
    }
    Ok(final_line)
}

/// Invoke audio_config.py with a single action flag.
#[tauri::command]
pub async fn run_audio_config(
    app: AppHandle,
    action: String,
) -> Result<AudioConfigResult, String> {
    let companion = companion_dir(&app)?;
    let script = companion.join("audio_config.py");
    if !script.exists() {
        return Err(format!("audio_config.py missing at {}", script.display()));
    }
    let flag = format!("--{action}");
    let shell = app.shell();
    let output = shell
        .command("python3")
        .args([script.display().to_string(), flag])
        .output()
        .await
        .map_err(|e| format!("spawn: {e}"))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("audio_config exited non-zero: {stderr}"));
    }
    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    // Parse the last line as JSON (probe outputs single-line JSON).
    let last_line = stdout.lines().last().unwrap_or("{}");
    serde_json::from_str::<AudioConfigResult>(last_line)
        .map_err(|e| format!("audio_config json parse: {e}; raw={stdout}"))
}

/// Open the OS-native audio settings panel.
#[tauri::command]
pub async fn open_audio_settings(
    app: AppHandle,
    platform: String,
) -> Result<(), String> {
    let shell = app.shell();
    match platform.as_str() {
        "darwin" => {
            shell
                .command("open")
                .args(["-a", "Audio MIDI Setup"])
                .spawn()
                .map_err(|e| format!("open Audio MIDI Setup: {e}"))?;
            Ok(())
        }
        "win32" => {
            shell
                .command("control.exe")
                .args(["mmsys.cpl,,0"])
                .spawn()
                .map_err(|e| format!("open mmsys.cpl: {e}"))?;
            Ok(())
        }
        _ => Err(format!("unsupported platform: {platform}")),
    }
}
