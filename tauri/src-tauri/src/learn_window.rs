// SPDX-License-Identifier: Apache-2.0
//! Phase 91 RENDER-07 — Learn window second WebviewWindow.
//!
//! Trimmed mirror of `debrief_window.rs` per research §Pattern 7. The
//! Learn window is a passive frontend surface that connects to the
//! EXISTING main vibemix process's ws:8765 — Invariant #4 (one-socket)
//! is preserved.
//!
//! What this module DROPS from the debrief precedent (§Pattern 7 diff):
//!
//!   * No second Python process is launched — Learn shares the main
//!     vibemix process. The Learn webview connects to the existing
//!     ws:8765 once it mounts.
//!   * No filesystem path input — Learn accepts only a validated lesson id
//!     referral, never an arbitrary URL/path.
//!   * No sidecar launch or second socket — a lesson referral only changes
//!     the Learn webview URL/event payload.
//!   * No close-event handler terminating a child process (there is no
//!     child).
//!   * No crash watcher (no spawn → no crash surface to emit on).
//!
//! What this module KEEPS verbatim:
//!
//!   * `WebviewWindowBuilder` shape + dimensions (1280×720 default,
//!     960×540 min — matches the SVG `viewBox="0 0 1280 720"` design grid
//!     per UI-SPEC §Design System).
//!   * Focus-existing pattern — at most one Learn window at a time
//!     (T-91-04-03 mitigation).
//!   * Lowercase + no-space label (`tauri-runtime-wry` restriction).
//!   * `tauri::command` annotation on `open_learn_window` — the
//!     capability allowlist (Plan 91-01 `capabilities/default.json`)
//!     gates webview invocation.

use tauri::window::Color;
use tauri::{AppHandle, Emitter, Manager, WebviewUrl, WebviewWindowBuilder};

/// Tauri window label for the Learn surface. Lowercase + no whitespace
/// per the `tauri-runtime-wry` restrictions; pinned by the unit test
/// `learn_window_label_const_is_lowercase_no_spaces` below and by the
/// vitest static-grep gate
/// `tauri/ui/tests/learn/test_learn_window_label.spec.ts`.
pub const LEARN_WINDOW_LABEL: &str = "learn";

/// Default window size — matches the SVG `viewBox="0 0 1280 720"` 1:1
/// so the controller schematic renders without a transform on first open.
const DEFAULT_WIDTH: f64 = 1280.0;
const DEFAULT_HEIGHT: f64 = 720.0;

/// Minimum window size — below this the SVG letterbox margins collapse
/// past the WCAG 2.5.5 touch-target floor (UI-SPEC §Design System).
const MIN_WIDTH: f64 = 960.0;
const MIN_HEIGHT: f64 = 540.0;

/// Open the Learn window. Focus-existing pattern: at most one Learn
/// window at a time (T-91-04-03 — resource-exhaustion mitigation).
///
/// Shares the main vibemix process — no Python child is launched by this
/// command. The webview connects to the existing ws:8765 (Invariant #4)
/// once it mounts.
///
/// The `learn.html` URL is a hardcoded literal — no user input flows
/// through the path so T-91-04-02 (path-traversal via WebviewUrl) is
/// mitigated by construction.
#[tauri::command]
pub async fn open_learn_window(app: AppHandle) -> Result<(), String> {
    open_learn_route(app, None).await
}

/// Open Learn and route the first paint to an authored lesson id.
///
/// This is intentionally separate from ``open_learn_window`` so existing mode
/// switches keep their no-argument contract. The renderer still validates the
/// id against its generated curriculum metadata before starting the lesson.
#[tauri::command]
pub async fn open_learn_lesson_window(app: AppHandle, lesson_id: String) -> Result<(), String> {
    let safe_lesson_id = validate_lesson_id(&lesson_id)?;
    open_learn_route(app, Some(safe_lesson_id)).await
}

async fn open_learn_route(app: AppHandle, lesson_id: Option<String>) -> Result<(), String> {
    // Focus existing window if already open — keeps the window count
    // bounded at 1 (T-91-04-03).
    if let Some(existing) = app.get_webview_window(LEARN_WINDOW_LABEL) {
        let _ = existing.set_focus();
        if let Some(id) = lesson_id {
            let _ = app.emit("vmx-learn-referral", serde_json::json!({ "lessonId": id }));
        }
        return Ok(());
    }

    let _window = WebviewWindowBuilder::new(
        &app,
        LEARN_WINDOW_LABEL,
        learn_webview_url(lesson_id.as_deref()),
    )
    .title("Learn · vibemix")
    .inner_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)
    .min_inner_size(MIN_WIDTH, MIN_HEIGHT)
    .resizable(true)
    .decorations(true)
    // Warm void (--void-0) from the first frame — no platform-white flash.
    .background_color(Color(0x1A, 0x16, 0x18, 0xFF))
    .build()
    .map_err(|e| format!("window build: {e}"))?;

    Ok(())
}

fn learn_webview_url(lesson_id: Option<&str>) -> WebviewUrl {
    match lesson_id {
        Some(id) => WebviewUrl::App(format!("learn.html?lessonId={id}").into()),
        None => WebviewUrl::App("learn.html".into()),
    }
}

fn validate_lesson_id(raw: &str) -> Result<String, String> {
    let lesson_id = raw.trim();
    if lesson_id.is_empty() || lesson_id.len() > 64 {
        return Err("invalid lesson id".into());
    }
    if !lesson_id
        .chars()
        .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '-' | '_'))
    {
        return Err("invalid lesson id".into());
    }
    Ok(lesson_id.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Pins the label invariant against accidental rename (e.g. to
    /// `"Learn"` — which the Tauri runtime rejects). Mirrors the
    /// `debrief_window_label_const_is_lowercase_no_spaces` precedent.
    /// Also acts as the Rust-side companion to the vitest static-grep
    /// gate `tauri/ui/tests/learn/test_learn_window_label.spec.ts`.
    #[test]
    fn learn_window_label_const_is_lowercase_no_spaces() {
        assert_eq!(LEARN_WINDOW_LABEL, "learn");
        assert!(LEARN_WINDOW_LABEL.chars().all(|c| c.is_lowercase()));
        assert!(!LEARN_WINDOW_LABEL.contains(' '));
    }

    /// Pins the named-constant dimensions against drift. The SVG
    /// `viewBox="0 0 1280 720"` design grid (UI-SPEC §Design System)
    /// requires the default to be exactly 1280×720 so the controller
    /// schematic mounts at 1:1 without a transform on first open. The
    /// 960×540 minimum is the WCAG 2.5.5 touch-target floor.
    #[test]
    fn learn_window_default_dimensions() {
        assert_eq!(DEFAULT_WIDTH, 1280.0);
        assert_eq!(DEFAULT_HEIGHT, 720.0);
        assert_eq!(MIN_WIDTH, 960.0);
        assert_eq!(MIN_HEIGHT, 540.0);
    }

    #[test]
    fn learn_lesson_url_carries_sanitized_lesson_id() {
        match learn_webview_url(Some("L2.01")) {
            WebviewUrl::App(path) => {
                assert_eq!(path.to_string_lossy(), "learn.html?lessonId=L2.01")
            }
            _ => panic!("expected app webview url"),
        }
    }

    #[test]
    fn learn_lesson_id_validation_rejects_query_smuggling() {
        assert_eq!(validate_lesson_id(" L2.01 ").unwrap(), "L2.01");
        assert!(validate_lesson_id("L2.01&x=1").is_err());
        assert!(validate_lesson_id("../learn.html").is_err());
        assert!(validate_lesson_id("").is_err());
    }
}
