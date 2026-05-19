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

use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Manager, WebviewUrl, WebviewWindowBuilder, WindowEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

use crate::recordings;

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
    let candidate: PathBuf = if PathBuf::from(&session_dir).is_absolute() {
        PathBuf::from(&session_dir)
    } else {
        root.join(&session_dir)
    };
    let safe = recordings::validate_under_root(&candidate, &root)
        .map_err(|e| format!("invalid session dir: {e}"))?;
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

    // 3. Spawn the sidecar with --debrief <validated_path>.
    let sidecar_cmd = app
        .shell()
        .sidecar("vibemix-core")
        .map_err(|e| format!("sidecar resolve: {e}"))?
        .args(["--debrief", &safe_str]);
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
    let window = WebviewWindowBuilder::new(
        &app,
        DEBRIEF_WINDOW_LABEL,
        WebviewUrl::App(url.into()),
    )
    .title(format!("Debrief — {session_label}"))
    .inner_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)
    .min_inner_size(MIN_WIDTH, MIN_HEIGHT)
    .resizable(true)
    .decorations(true)
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
                    let _ = app_for_watch
                        .emit("sidecar-debrief-crashed", payload_json);
                    if let Some(w) =
                        app_for_watch.get_webview_window(DEBRIEF_WINDOW_LABEL)
                    {
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

/// Minimal percent-encoder for a filesystem path destined for a URL
/// query-string value. Covers the characters that would corrupt
/// ``URLSearchParams`` decoding: space, +, %, ?, =, #, &.
///
/// The full set of "unsafe" RFC 3986 chars is larger; this helper is
/// purpose-built for the validated session-dir path (which already
/// excludes the bulk of them via the canonicalization step).
fn percent_encode_path(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for b in s.bytes() {
        match b {
            b' ' => out.push_str("%20"),
            b'+' => out.push_str("%2B"),
            b'%' => out.push_str("%25"),
            b'?' => out.push_str("%3F"),
            b'=' => out.push_str("%3D"),
            b'#' => out.push_str("%23"),
            b'&' => out.push_str("%26"),
            _ => out.push(b as char),
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
        assert_eq!(
            percent_encode_path("a?b=c&d=e#f"),
            "a%3Fb%3Dc%26d%3De%23f"
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
}
