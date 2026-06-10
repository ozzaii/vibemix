//! Phase 29 Plan 29-04 — DEBRIEF second-window + sidecar lifecycle.
//!
//! Composition of three already-shipped patterns:
//!
//!   * `mascot_window` — second `WebviewWindow` with custom label.
//!   * `sidecar` — `Arc<Mutex<Option<CommandChild>>>` handle pattern
//!     for spawning + killing a child process.
//!   * `recordings::validate_under_root` — path-traversal defense.
//!
//! Public surface: one `#[tauri::command]` `open_debrief_window` that:
//!
//!   1. Validates ``session_dir`` is under the recordings root (defense
//!      against ``../etc/passwd``).
//!   2. Focuses an existing ``debrief`` window if one is open (idempotent;
//!      max one debrief sidecar at a time).
//!   3. Spawns the sidecar with ``--debrief <validated_session_dir>``.
//!   4. Builds a 1280×720 WebviewWindow with label ``debrief`` pointing
//!      at ``debrief.html?session=<encoded path>``.
//!   5. Installs a close-handler that kills the sidecar child.
//!   6. Spawns a crash watcher that emits ``sidecar-debrief-crashed``
//!      when the child exits early.

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use serde::{Deserialize, Serialize};
use tauri::window::Color;
use tauri::{AppHandle, Emitter, Manager, WebviewUrl, WebviewWindowBuilder, WindowEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

use crate::recordings;
use crate::sidecar::{
    resolve_sidecar_invocation_for_command, SidecarInvocation, FORWARDED_ENV_KEYS,
};

pub const DEBRIEF_WINDOW_LABEL: &str = "debrief";

/// Phase 44-03 / LAUNCH-02 — optional deep-link payload that scrolls the
/// debrief timeline to a specific evidence event on window open. When
/// present, we forward the payload to the webview via the URL query
/// string (`&deepLinkEventId=...&deepLinkTimestampS=...`) so the JS
/// `debrief-window.ts` boot can dispatch a `vmx-debrief-deeplink`
/// custom event after the timeline mounts.
///
/// Forwarding via URL keeps the contract stateless — no extra IPC plumbing,
/// no Tauri state to lifecycle-manage; the URL is the deep-link channel.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DebriefDeepLink {
    /// Stable citation atom in source-prefixed form (e.g. `"ev:KICK_SWAP@45.2"`).
    /// The debrief timeline uses this as the region lookup key.
    /// Wire field name (from JS / event payload): `eventId`.
    pub event_id: String,
    /// Session-relative timestamp in seconds. Float so sub-second
    /// precision survives the wire (the click-target chip displays
    /// `mm:ss`, but the highlight scroll is precise).
    /// Wire field name (from JS / event payload): `timestampS`.
    pub timestamp_s: f64,
}

const DEFAULT_WIDTH: f64 = 1280.0;
const DEFAULT_HEIGHT: f64 = 720.0;
const MIN_WIDTH: f64 = 960.0;
const MIN_HEIGHT: f64 = 540.0;

/// Shared handle to the debrief sidecar's CommandChild — separate from
/// the main `SidecarHandle` so the lifecycles don't interfere.
pub struct DebriefSidecarHandle {
    pub child: Arc<Mutex<Option<CommandChild>>>,
}

impl Default for DebriefSidecarHandle {
    fn default() -> Self {
        DebriefSidecarHandle {
            child: Arc::new(Mutex::new(None)),
        }
    }
}

fn resolve_debrief_session(root: &Path, session_dir: &str) -> Result<PathBuf, String> {
    let trimmed = session_dir.trim();
    let candidate: PathBuf = if trimmed.is_empty() {
        latest_recording_dir(root)?
    } else if PathBuf::from(trimmed).is_absolute() {
        PathBuf::from(trimmed)
    } else {
        root.join(trimmed)
    };
    recordings::validate_under_root(&candidate, root)
        .map_err(|e| format!("invalid session dir: {e}"))
}

fn latest_recording_dir(root: &Path) -> Result<PathBuf, String> {
    let entries = fs::read_dir(root).map_err(|e| format!("recordings read: {e}"))?;
    let mut latest: Option<(String, PathBuf)> = None;
    for entry in entries {
        let entry = entry.map_err(|e| format!("recordings entry: {e}"))?;
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }
        let Some(name) = path.file_name().and_then(|n| n.to_str()) else {
            continue;
        };
        if !is_session_dir_name(name) {
            continue;
        }
        if latest
            .as_ref()
            .map(|(current, _)| name > current.as_str())
            .unwrap_or(true)
        {
            latest = Some((name.to_string(), path));
        }
    }
    latest
        .map(|(_, path)| path)
        .ok_or_else(|| "no recordings available".to_string())
}

fn is_session_dir_name(name: &str) -> bool {
    let bytes = name.as_bytes();
    bytes.len() == 15
        && bytes[8] == b'-'
        && bytes
            .iter()
            .enumerate()
            .all(|(idx, b)| idx == 8 || b.is_ascii_digit())
}

/// Open the debrief window for `session_dir`.
///
/// `session_dir` may be either an absolute path under the recordings
/// root OR a bare session-id basename (e.g. `"20260515-112139"`). Both
/// forms canonicalize and validate via `recordings::validate_under_root`.
///
/// `deep_link` (Phase 44-03 / LAUNCH-02) is optional — when present,
/// the debrief webview scrolls its timeline to `deep_link.timestamp_s`
/// and dispatches a `vmx-debrief-deeplink` event so the timeline
/// component highlights the corresponding region. The payload is
/// forwarded via the webview URL query string so no extra IPC channel
/// is needed (the URL is the deep-link channel).
#[tauri::command]
pub async fn open_debrief_window(
    app: AppHandle,
    session_dir: String,
    deep_link: Option<DebriefDeepLink>,
) -> Result<(), String> {
    // 1. Validate the path BEFORE doing any work.
    let root = recordings::resolve_recordings_root()?;
    let safe = resolve_debrief_session(&root, &session_dir)?;
    let safe_str = safe.to_string_lossy().to_string();

    // 2. Focus-existing — at most one debrief window at a time. When the
    // window is already open AND a deep_link is requested, emit the
    // payload as a one-shot event so the in-window listener can scroll
    // even without a fresh mount (matches the focus-existing intent).
    if let Some(existing) = app.get_webview_window(DEBRIEF_WINDOW_LABEL) {
        let _ = existing.set_focus();
        if let Some(dl) = deep_link {
            let _ = app.emit("vmx-debrief-deeplink", dl);
        }
        return Ok(());
    }

    // 3. Spawn the same resolved vibemix command as the main/library paths,
    // then append --debrief <validated_path>.
    let sidecar_cmd = build_debrief_sidecar_command(&app, &safe_str)?;
    let (mut rx, child) = sidecar_cmd
        .spawn()
        .map_err(|e| format!("sidecar spawn: {e}"))?;

    // Store the child handle.
    if let Some(state) = app.try_state::<DebriefSidecarHandle>() {
        if let Ok(mut guard) = state.child.lock() {
            *guard = Some(child);
        }
    }

    // 4. Build the WebviewWindow.
    let session_label = safe
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| "session".to_string());
    // Minimal URL-encoder: replaces the characters we actually expect in a
    // session-dir path (spaces, +, %, ?, =) so the renderer's URLSearchParams
    // round-trip works. The full path was already canonicalized + validated.
    let url_encoded = percent_encode_path(&safe_str);
    // Phase 44-03 / LAUNCH-02 — append deep-link parameters when present.
    // The webview reads these off URLSearchParams at boot and dispatches
    // the `vmx-debrief-deeplink` event after the timeline mounts.
    let url = match &deep_link {
        Some(dl) => format!(
            "debrief.html?session={url_encoded}&deepLinkEventId={ev}&deepLinkTimestampS={ts}",
            ev = percent_encode_path(&dl.event_id),
            ts = dl.timestamp_s,
        ),
        None => format!("debrief.html?session={url_encoded}"),
    };
    let window = WebviewWindowBuilder::new(&app, DEBRIEF_WINDOW_LABEL, WebviewUrl::App(url.into()))
        .title(format!("Debrief · {session_label}"))
        .inner_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        .min_inner_size(MIN_WIDTH, MIN_HEIGHT)
        .resizable(true)
        .decorations(true)
        // Paint the warm void (--void-0) from the first frame — without it the
        // webview opens platform-white before the stylesheet lands (a white
        // flash on a dark app).
        .background_color(Color(0x1A, 0x16, 0x18, 0xFF))
        .build()
        .map_err(|e| format!("window build: {e}"))?;

    // 5. Close-handler → kill the sidecar child.
    let app_for_close = app.clone();
    window.on_window_event(move |event| {
        if let WindowEvent::CloseRequested { .. } = event {
            kill_debrief_child(&app_for_close);
        }
    });

    // 6. Spawn the crash watcher — listens for CommandEvent::Terminated
    //    from the spawn's rx stream. On early exit, emit the event AND
    //    close the window.
    let app_for_watch = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Terminated(payload) => {
                    let exit_code = payload.code;
                    let payload_json = serde_json::json!({
                        "exit_code": exit_code,
                        "reason": match exit_code {
                            Some(0) => "clean",
                            _ => "crashed",
                        },
                    });
                    let _ = app_for_watch.emit("sidecar-debrief-crashed", payload_json);
                    if let Some(w) = app_for_watch.get_webview_window(DEBRIEF_WINDOW_LABEL) {
                        let _ = w.close();
                    }
                    // Clear our state so a subsequent open_debrief_window
                    // can spawn a fresh sidecar without leaving the old
                    // CommandChild lingering.
                    if let Some(state) = app_for_watch.try_state::<DebriefSidecarHandle>() {
                        if let Ok(mut guard) = state.child.lock() {
                            *guard = None;
                        }
                    }
                    break;
                }
                CommandEvent::Stdout(line) => {
                    // The sidecar prefixes all stdout lines with [debrief]
                    // already — forward to the parent log surface as-is.
                    let s = String::from_utf8_lossy(&line).to_string();
                    tracing::info!("[debrief sidecar] {}", s.trim_end());
                }
                CommandEvent::Stderr(line) => {
                    let s = String::from_utf8_lossy(&line).to_string();
                    tracing::warn!("[debrief sidecar] {}", s.trim_end());
                }
                _ => {}
            }
        }
    });

    Ok(())
}

/// Build the debrief sidecar command from the shared dev-vs-bundled resolver.
///
/// This deliberately avoids Tauri's named sidecar API: the product ships
/// PyInstaller onedir bundles through `bundle.resources`, and sidecar.rs
/// resolves the resource path at runtime.
fn build_debrief_sidecar_command(
    app: &AppHandle,
    safe_str: &str,
) -> Result<tauri_plugin_shell::process::Command, String> {
    let invocation = resolve_sidecar_invocation_for_command(app)?;

    let mut cmd = match invocation {
        SidecarInvocation::DevSource { program, args, cwd } => {
            let args = debrief_cli_args(&args, safe_str);
            app.shell().command(&program).args(args).current_dir(&cwd)
        }
        SidecarInvocation::Bundled(bin) => {
            let mut c = app.shell().command(&bin);
            if let Some(parent) = bin.parent() {
                c = c.current_dir(parent);
            }
            c.args(["--debrief", safe_str])
        }
    };

    for key in FORWARDED_ENV_KEYS {
        if let Ok(val) = std::env::var(key) {
            if !val.is_empty() {
                cmd = cmd.env(key, val);
            }
        }
    }

    Ok(cmd)
}

fn debrief_cli_args(base_args: &[String], safe_str: &str) -> Vec<String> {
    let mut args = base_args.to_vec();
    args.push("--debrief".to_string());
    args.push(safe_str.to_string());
    args
}

/// Minimal UTF-8 percent-encoder for a filesystem path destined for a URL
/// query-string value. Covers ASCII delimiters that would corrupt
/// ``URLSearchParams`` decoding and every non-ASCII byte.
///
/// The full set of "unsafe" RFC 3986 chars is larger; this helper is
/// purpose-built for the validated session-dir path (which already
/// excludes the bulk of them via the canonicalization step).
fn percent_encode_path(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    const HEX: &[u8; 16] = b"0123456789ABCDEF";
    for b in s.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'.' | b'_' | b'~' | b'/' => {
                out.push(b as char)
            }
            // Everything else, including UTF-8 continuation bytes, becomes a
            // byte-level %XX escape. URLSearchParams decodes this back to the
            // original Unicode string; casting raw bytes to char would not.
            _ => {
                out.push('%');
                out.push(HEX[(b >> 4) as usize] as char);
                out.push(HEX[(b & 0x0F) as usize] as char);
            }
        }
    }
    out
}

/// Idempotent kill — takes the CommandChild Out and drops the Mutex
/// guard. Second call with `guard.take()` returns None (no-op).
fn kill_debrief_child(app: &AppHandle) {
    if let Some(state) = app.try_state::<DebriefSidecarHandle>() {
        if let Ok(mut guard) = state.child.lock() {
            if let Some(child) = guard.take() {
                let _ = child.kill();
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn empty_session_dir_resolves_latest_recording_dir() {
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();
        fs::create_dir(root.join("20260513-210410")).unwrap();
        fs::create_dir(root.join("notes")).unwrap();
        fs::create_dir(root.join("20260515-112139")).unwrap();

        let resolved = resolve_debrief_session(root, "").unwrap();

        assert_eq!(
            resolved,
            root.join("20260515-112139").canonicalize().unwrap()
        );
    }

    #[test]
    fn empty_session_dir_errors_when_no_recordings_exist() {
        let tmp = TempDir::new().unwrap();

        let err = resolve_debrief_session(tmp.path(), "").unwrap_err();

        assert!(err.contains("no recordings available"));
    }

    #[test]
    fn empty_session_dir_ignores_non_timestamp_dirs() {
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();
        fs::create_dir(root.join("latest")).unwrap();
        fs::create_dir(root.join("2026-05-15")).unwrap();

        let err = resolve_debrief_session(root, "").unwrap_err();

        assert!(err.contains("no recordings available"));
    }

    #[test]
    fn explicit_session_dir_still_validates_under_root() {
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();
        fs::create_dir(root.join("20260515-112139")).unwrap();

        let resolved = resolve_debrief_session(root, "20260515-112139").unwrap();

        assert_eq!(
            resolved,
            root.join("20260515-112139").canonicalize().unwrap()
        );
    }

    #[test]
    fn percent_encode_path_handles_spaces() {
        assert_eq!(percent_encode_path("foo bar"), "foo%20bar");
    }

    #[test]
    fn percent_encode_path_handles_plus_and_percent() {
        assert_eq!(percent_encode_path("a+b%c"), "a%2Bb%25c");
    }

    #[test]
    fn percent_encode_path_handles_query_delimiters() {
        assert_eq!(percent_encode_path("a?b=c&d=e#f"), "a%3Fb%3Dc%26d%3De%23f");
    }

    #[test]
    fn percent_encode_path_handles_utf8_bytes() {
        assert_eq!(
            percent_encode_path("/Users/ozai/Müzik/çağrı.mp3"),
            "/Users/ozai/M%C3%BCzik/%C3%A7a%C4%9Fr%C4%B1.mp3"
        );
    }

    #[test]
    fn percent_encode_path_preserves_session_id_format() {
        // Real session-dir basenames are YYYYMMDD-HHMMSS, plus filesystem
        // path separators. None of these characters need encoding.
        assert_eq!(
            percent_encode_path("/Users/x/Library/recordings/20260515-112139"),
            "/Users/x/Library/recordings/20260515-112139"
        );
    }

    #[test]
    fn debrief_sidecar_handle_default_starts_empty() {
        let handle = DebriefSidecarHandle::default();
        let guard = handle.child.lock().unwrap();
        assert!(guard.is_none());
    }

    #[test]
    fn debrief_sidecar_handle_arc_is_clonable() {
        let handle = DebriefSidecarHandle::default();
        let cloned = Arc::clone(&handle.child);
        // Both Arc handles point at the same Mutex.
        assert_eq!(Arc::strong_count(&cloned), 2);
    }

    #[test]
    fn debrief_window_label_const_is_lowercase_no_spaces() {
        // Tauri window labels MUST be lowercase + no whitespace per the
        // tauri-runtime-wry restrictions.
        assert_eq!(DEBRIEF_WINDOW_LABEL, "debrief");
        assert!(DEBRIEF_WINDOW_LABEL.chars().all(|c| c.is_lowercase()));
        assert!(!DEBRIEF_WINDOW_LABEL.contains(' '));
    }

    #[test]
    fn debrief_cli_args_append_after_uv_module_invocation() {
        let base = vec![
            "run".to_string(),
            "python".to_string(),
            "-m".to_string(),
            "vibemix".to_string(),
        ];

        assert_eq!(
            debrief_cli_args(&base, "/recordings/20260515-112139"),
            vec![
                "run",
                "python",
                "-m",
                "vibemix",
                "--debrief",
                "/recordings/20260515-112139",
            ]
        );
    }

    #[test]
    fn debrief_cli_args_append_after_custom_python_invocation() {
        let base = vec!["-m".to_string(), "vibemix".to_string()];

        assert_eq!(
            debrief_cli_args(&base, "20260515-112139"),
            vec!["-m", "vibemix", "--debrief", "20260515-112139"]
        );
    }
}
