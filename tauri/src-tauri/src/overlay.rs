//! Phase 24 Plan 02 — overlay-highlight Tauri command.
//!
//! When the Python sidecar emits `ipc.session.overlay-highlight` with an
//! element_id from the 12-element djay Pro v5 map, the frontend invokes
//! `show_overlay_highlight` here. This module:
//!
//!   1. Asks `djay_ax::query_element_bounds(element_id)` for the
//!      screen-coords rect (PARTIAL fallback today; AX-precise once
//!      WAVE-0-AX-SPIKE.md verdict flips to PASS).
//!   2. If `None` (djay closed, AX denied, unknown id) → graceful Ok(())
//!      no-op. The user sees nothing — preferable to a misplaced ring.
//!   3. Otherwise opens a transparent + always-on-top + click-through
//!      `WebviewWindow` sized to the rect + small visual padding. The
//!      window loads `overlay.html` which renders the amber ring CSS
//!      keyframe animation.
//!   4. Spawns a Tokio task that sleeps `duration_ms` ms then closes the
//!      window. No-overlap-per-element is enforced by giving each window
//!      a stable label per element_id — a second invocation on the same
//!      element while the first is still up returns Ok(()) without
//!      double-opening.
//!
//! Click-through is `set_ignore_cursor_events(true)` on the built window
//! — the ring layer is read-only (T-24-02-02 mitigation).

use std::time::Duration;

use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};

use crate::djay_ax;

/// Pixels of padding around the element rect — gives the ring some
/// visual breathing room without occluding adjacent controls.
const OVERLAY_PAD_PX: f64 = 12.0;

/// Tauri command — frontend-callable. Idempotent per element_id: a second
/// invocation while the first overlay is still up returns Ok(()) and
/// the existing animation runs out.
#[tauri::command]
pub async fn show_overlay_highlight(
    app: AppHandle,
    element_id: String,
    color: String,
    duration_ms: u32,
) -> Result<(), String> {
    // 1) Ask djay_ax for the bounds. None → graceful no-op.
    let rect = match djay_ax::query_element_bounds(&element_id) {
        Some(r) => r,
        None => return Ok(()),
    };

    // 2) Per-element label. Stable so a second call collapses to no-op
    //    rather than stacking windows.
    let label = format!("overlay-{element_id}");
    if app.get_webview_window(&label).is_some() {
        // Already firing — let the existing animation run.
        return Ok(());
    }

    // 3) Build the overlay window. URL query params pass color +
    //    duration_ms to the CSS-rendering frontend.
    let url = format!(
        "overlay.html?color={}&duration_ms={}",
        urlencode(&color),
        duration_ms
    );
    let outer_x = rect.x - OVERLAY_PAD_PX;
    let outer_y = rect.y - OVERLAY_PAD_PX;
    let outer_w = rect.width + 2.0 * OVERLAY_PAD_PX;
    let outer_h = rect.height + 2.0 * OVERLAY_PAD_PX;

    let window = WebviewWindowBuilder::new(&app, &label, WebviewUrl::App(url.into()))
        .title("vibemix overlay")
        .transparent(true)
        .always_on_top(true)
        .decorations(false)
        .resizable(false)
        .skip_taskbar(true)
        .visible_on_all_workspaces(true)
        .inner_size(outer_w, outer_h)
        .position(outer_x, outer_y)
        .visible(true)
        .build()
        .map_err(|e| format!("overlay window build failed: {e}"))?;

    // Click-through (T-24-02-02). MUST be called AFTER build so the OS
    // window handle exists. set_ignore_cursor_events makes the layer
    // read-only — mouse events pass through to djay below.
    if let Err(e) = window.set_ignore_cursor_events(true) {
        // Don't fail the whole command for click-through — the ring still
        // renders, the user just can't click through it. Best-effort.
        eprintln!("[overlay] set_ignore_cursor_events failed: {e}");
    }

    // 4) Schedule the auto-close. The async task captures the AppHandle
    //    so it can resolve the window by label and close it; if the
    //    window was already manually closed, get_webview_window returns
    //    None and we no-op.
    let app_close = app.clone();
    let label_close = label.clone();
    let close_after = Duration::from_millis(u64::from(duration_ms));
    tauri::async_runtime::spawn(async move {
        tokio::time::sleep(close_after).await;
        if let Some(w) = app_close.get_webview_window(&label_close) {
            let _ = w.close();
        }
    });

    Ok(())
}

/// Minimal URL-encoding for the two known fields. Avoids pulling in a
/// crate dependency for two values that are short ASCII tokens. Replaces
/// every non-alphanumeric-non-dash character with `_` so the resulting
/// URL is unambiguous. The frontend re-parses these by simple key=value
/// split — no urldecode round-trip needed.
fn urlencode(s: &str) -> String {
    s.chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '-' || c == '_' {
                c
            } else {
                '_'
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn urlencode_passes_safe_chars() {
        assert_eq!(urlencode("amber"), "amber");
        assert_eq!(urlencode("a_b-c"), "a_b-c");
    }

    #[test]
    fn urlencode_sanitises_unsafe() {
        assert_eq!(urlencode("rgb(255,0,0)"), "rgb_255_0_0_");
        assert_eq!(urlencode("amber/red"), "amber_red");
    }

    #[test]
    fn overlay_pad_is_reasonable() {
        // Small enough not to occlude adjacent controls; large enough
        // for the ring to be visible around tight EQ knob hitboxes.
        assert!((4.0..=32.0).contains(&OVERLAY_PAD_PX));
    }
}
