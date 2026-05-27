// SPDX-License-Identifier: Apache-2.0
//! Phase 91 RENDER-07 — Learn window second WebviewWindow.
//!
//! Trimmed mirror of `debrief_window.rs` per research §Pattern 7. The
//! Learn window is a passive frontend surface that connects to the
//! EXISTING main sidecar's ws:8765 (Invariant #4 — one-socket — preserved).
//!
//! What this module DROPS from the debrief precedent (§Pattern 7 diff):
//!
//!   * No sidecar spawn — Learn shares the main `vibemix` Python process.
//!     There is no `--learn` flag, no second `CommandChild`, no
//!     `LearnSidecarHandle` State.
//!   * No `session_dir` query-param validation (Learn takes no path input;
//!     the URL is the hardcoded literal `learn.html`).
//!   * No `DebriefDeepLink` deep-link payload (Learn opens at lesson 0;
//!     navigation lives inside the webview).
//!   * No `WindowEvent::CloseRequested` handler killing a child (no child).
//!   * No `CommandEvent::Terminated` crash watcher (no spawn → no crash
//!     surface to emit on).
//!
//! What this module KEEPS verbatim:
//!
//!   * `WebviewWindowBuilder` shape + dimensions (1280×720 default,
//!     960×540 min — matches the SVG `viewBox="0 0 1280 720"` design grid
//!     per UI-SPEC §Design System).
//!   * Focus-existing pattern — at most one Learn window at a time
//!     (T-91-04-03 mitigation).
//!   * Lowercase + no-space label (`tauri-runtime-wry` restriction).
//!   * `#[tauri::command] pub async fn ...` annotation — capability
//!     allowlist (Plan 91-01 `capabilities/default.json`) gates invocation.

use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};

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
/// Shares the main vibemix sidecar — no Python process is spawned by
/// this command. The webview connects to the existing ws:8765 (Invariant
/// #4) once it mounts.
///
/// The `learn.html` URL is a hardcoded literal — no user input flows
/// through the path so T-91-04-02 (path-traversal via WebviewUrl) is
/// mitigated by construction (contrast: `debrief_window.rs` accepts a
/// `session_dir` query param and runs `recordings::validate_under_root`).
#[tauri::command]
pub async fn open_learn_window(app: AppHandle) -> Result<(), String> {
    // Focus existing window if already open — keeps the window count
    // bounded at 1 (T-91-04-03).
    if let Some(existing) = app.get_webview_window(LEARN_WINDOW_LABEL) {
        let _ = existing.set_focus();
        return Ok(());
    }

    let _window = WebviewWindowBuilder::new(
        &app,
        LEARN_WINDOW_LABEL,
        WebviewUrl::App("learn.html".into()),
    )
    .title("Learn — vibemix")
    .inner_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)
    .min_inner_size(MIN_WIDTH, MIN_HEIGHT)
    .resizable(true)
    .decorations(true)
    .build()
    .map_err(|e| format!("window build: {e}"))?;

    Ok(())
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
}
