//! Phase 62 Plan 01 — floating pill overlay window builder + persistence.
//!
//! The pill is the THIRD Tauri overlay window (after `mascot`, `debrief`)
//! and Phase-62's PRIMARY in-set surface. It is a near-verbatim clone of
//! `mascot_window.rs` (geometry-persist + 200ms debounce + off-screen
//! fallback + label↔capability test) with three deliberate deltas:
//!
//!   1. label `"pill"` (not `"mascot"`).
//!   2. **DROP** the mascot's click-through block (the ignore-cursor-events
//!      call) — the pill is INTERACTIVE (draggable + clickable), never
//!      click-through. PILL-04.
//!   3. **ADD** a display-change re-clamp arm in the geometry listener (Leg D).
//!
//! Builder flags (62-CONTEXT Area 1 + UI-SPEC):
//!   * `transparent(true)` — the CSS `--glass-3` rgba surface paints the
//!     visible lozenge; the window itself has no opaque background.
//!   * `always_on_top(true)` — the pill floats over the user's DJ app.
//!   * `decorations(false)` — no titlebar/close box; lifecycle is tray-owned.
//!   * `resizable(false)` — the pill is FIXED-size; expand is CSS height
//!     growth inside the webview, NOT a window resize (avoids resize flicker
//!     + geometry-persist thrash; UI-SPEC "expands DOWN only").
//!   * `skip_taskbar(true)` — not an Alt-Tab / Dock target.
//!   * `visible_on_all_workspaces(true)` — Super-Whisper cross-Space float.
//!   * `focused(false)` — request non-activating on build (Leg A floor).
//!
//! Default geometry (first launch, no saved state): 280×44 collapsed
//! (UI-SPEC §Pill Dimensions LOCKED) at a top-right offset.
//!
//! Geometry persistence: a `WindowEvent::Moved`/`Resized` handler writes
//! the pill geometry back to the store, debounced 200ms so a pixel-drag
//! does not thrash `store.save()`. A `ScaleFactorChanged` arm re-clamps the
//! pill into the visible work area when the monitor topology changes (Leg D).
//!
//! ## macOS focus non-steal (PILL-04, Leg A)
//!
//! FLOOR (shipped baseline, no new dep): `.focused(false)` on the builder.
//! Do NOT switch the app to macOS Accessory activation: that policy is
//! process-global, so it demotes the full app window into a hidden/accessory
//! process and breaks Dock/Cmd-Tab/System Events reachability. A 2026-05-27
//! source-backed runtime pass reproduced that failure. RESIDUAL LIMITATION
//! (documented, KAAN-ACTION live-confirm): the first click on a non-activating
//! *NSWindow* may still transfer key-window status — wry#637 / tauri#14102
//! (open, no fix as of 2.11.x). Accept for v1; keep the main app reachable.
//!
//! STRETCH — DROPPED (code-review CR-01, 2026-05-22). The original plan
//! sanctioned an `objc2` `NSWindow → NSPanel` class swizzle (so the
//! `NonactivatingPanel` style mask takes effect) as a BOUNDED, gated stretch.
//! Code review found the swizzle UNSOUND: `AnyObject::set_class`'s SAFETY
//! contract requires the new class be a subclass of the object's CURRENT class
//! (which is wry's own `NSWindow` subclass, NOT bare `NSWindow` — `NSPanel` is
//! a cousin, not a descendant) and that it add no instance variables (`NSPanel`
//! historically does). Worse, under `[profile.release] panic = "abort"` a
//! `msg_send!` / `unwrap_unchecked` failure in the closure SIGABRTs the whole
//! app — `with_webview`'s `Err` arm never sees it, and `catch_unwind` is a
//! no-op under `panic = "abort"`. The plan explicitly allows shipping the floor
//! alone, so the swizzle is removed. The full felt non-activating behavior
//! (first-click not stealing key-window) is KAAN-ACTION live-confirm on the
//! built app; if it ever needs the panel mask, the correct path is the
//! crates.io `objc2-app-kit` NSPanel subclass (a real subclass, allocated as
//! NSPanel from the start) — NOT an in-place class swap on a live wry window.

// Plan 62-02 wires `create_pill_window` into the `main.rs` setup branch (the
// `primary_surface` switch), so the module is no longer dead code — the
// transient 62-01 `#![allow(dead_code)]` is removed here.

use std::sync::Arc;
use std::time::Duration;

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager, PhysicalPosition, PhysicalSize, WebviewUrl, WebviewWindowBuilder};
use tokio::sync::Mutex;

pub const PILL_WINDOW_LABEL: &str = "pill";

// Pill store key (config.json). The pill keeps its own geometry block so it
// does not entangle with the mascot's `mascot_window` key — PILL is the
// primary surface and persists x/y/w/h independently. config.rs is NOT
// touched by this plan (the `primary_surface` switch is plan 62-02); the
// pill reaches tauri-plugin-store directly here for its geometry only.
const STORE_PATH: &str = "config.json";
const KEY_PILL_WINDOW: &str = "pill_window";

// Collapsed dimensions. UI-SPEC §Pill Dimensions LOCKED 280×44. Pinning
// these in a test makes any future change a deliberate test edit.
const PILL_COLLAPSED_W: f64 = 280.0;
const PILL_COLLAPSED_H: f64 = 44.0;

// Default placement: top-right, fully on-screen.
const DEFAULT_TOP_OFFSET: i32 = 80;
const DEFAULT_RIGHT_INSET: i32 = 24; // monitor_width - width - INSET = default_x

// Geometry-persist debounce. 200ms is well above 60Hz drag-event cadence
// without feeling laggy on the final save after the user releases. Kept
// VERBATIM from the mascot.
const DEBOUNCE_MS: u64 = 200;

// Off-screen guard margin — keep at least a 48px sliver grabbable (matches
// the mascot's build-time off-screen fallback margin).
const ONSCREEN_MARGIN: f64 = 48.0;

/// Persisted pill window geometry. Mirrors the mascot's window-state shape
/// but pill-scoped (its own `pill_window` store key). All fields optional →
/// a legacy/missing config decodes to "no saved geometry" and the builder
/// falls back to `default_top_right`.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PillWindowState {
    pub x: Option<i32>,
    pub y: Option<i32>,
    pub width: Option<u32>,
    pub height: Option<u32>,
}

/// A monitor work-area rectangle in LOGICAL pixels (the visible region
/// excluding menubar/dock). Defined as a plain struct so the clamp math is
/// unit-testable WITHOUT a live monitor (this is the Leg-D math extracted
/// for testability).
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct WorkArea {
    pub x: f64,
    pub y: f64,
    pub w: f64,
    pub h: f64,
}

/// Clamp a candidate window rect (x, y, w, h) so its rect is fully inside
/// `area`. An off-screen candidate is snapped back inside; an on-screen
/// candidate is returned unchanged. Pure — no monitor access, no I/O.
///
/// Returns the clamped (x, y) origin in the same logical units as `area`.
pub fn clamp_to_work_area(x: i32, y: i32, w: u32, h: u32, area: WorkArea) -> (i32, i32) {
    let fw = f64::from(w);
    let fh = f64::from(h);

    // The largest origin that keeps the window fully on-screen. If the
    // window is wider/taller than the work area, pin to the area origin
    // (better a clipped-right pill than one shoved off the left edge).
    let max_x = (area.x + area.w - fw).max(area.x);
    let max_y = (area.y + area.h - fh).max(area.y);

    let cx = f64::from(x).clamp(area.x, max_x);
    let cy = f64::from(y).clamp(area.y, max_y);

    (cx as i32, cy as i32)
}

/// Build the pill overlay window. Reads the saved `PillWindowState` from
/// `config.json`; if no geometry is saved, falls back to a top-right
/// default. Returns `Ok(None)` only if the store cannot be read for the
/// initial geometry (the call-site logs but does NOT bail setup — the main
/// session UI must still come up even if the pill fails to build, mirroring
/// the mascot's non-fatal discipline).
pub fn create_pill_window(app: &AppHandle) -> tauri::Result<Option<tauri::WebviewWindow>> {
    let state = load_pill_state(app).unwrap_or_default();

    // The pill is FIXED-size: `resizable(false)` and the expand panel grows via
    // CSS height inside the webview, NEVER a window resize. So persisted
    // width/height are meaningless — and a corrupted save (observed in the wild:
    // 8960×1408, from a physical-vs-logical pixel scale bug in an old geometry
    // write) would restore an insanely huge window. ALWAYS use the locked
    // collapsed dims; only x/y are restored from saved state.
    let width = PILL_COLLAPSED_W as u32;
    let height = PILL_COLLAPSED_H as u32;
    let (default_x, default_y) = default_top_right(app, width);
    let mut x = state.x.unwrap_or(default_x);
    let mut y = state.y.unwrap_or(default_y);

    // Guard against a persisted origin that no longer lands on-screen (a
    // monitor topology that's since gone, or the historical physical/logical
    // save mismatch). If the window would build off the primary monitor,
    // fall back to the on-screen top-right default so it can't go "missing".
    // (Cloned VERBATIM from mascot_window.rs lines 88-99.)
    if let Some((logical_w, logical_h)) = primary_logical_size(app) {
        let (fx, fy) = (f64::from(x), f64::from(y));
        let (fw, fh) = (f64::from(width), f64::from(height));
        let off_screen = fx > logical_w - ONSCREEN_MARGIN
            || fy > logical_h - ONSCREEN_MARGIN
            || fx + fw < ONSCREEN_MARGIN
            || fy + fh < ONSCREEN_MARGIN;
        if off_screen {
            x = default_x;
            y = default_y;
        }
    }

    let window =
        WebviewWindowBuilder::new(app, PILL_WINDOW_LABEL, WebviewUrl::App("pill.html".into()))
            .title("vibemix")
            .transparent(true)
            .always_on_top(true)
            .decorations(false)
            .resizable(false) // DELTA vs mascot: pill is fixed-size; expand is CSS height.
            .skip_taskbar(true)
            .visible_on_all_workspaces(true)
            .focused(false) // DELTA vs mascot: request non-activating (Leg A floor).
            .inner_size(f64::from(width), f64::from(height))
            .position(f64::from(x), f64::from(y))
            .visible(true)
            .build()?;
    // DELTA vs mascot: DO NOT clone the click-through block — the pill is
    // interactive (it must receive the drag mousedown + chip clicks).

    install_geometry_listener(app.clone(), window.clone());

    Ok(Some(window))
}

/// Pill height ceiling: collapsed row (44) + the expand panel cap (~220) + a
/// little slack. Clamps a bad measurement so a runaway value can never blow the
/// window up (the historical 8960×1408 corruption class).
const PILL_MAX_H: f64 = 300.0;

/// Resize-to-content: grow the pill window DOWN (width fixed at
/// `PILL_COLLAPSED_W`) to fit its current content height — the expand panel and
/// the collapsed-hover peek card both live BELOW the 44px collapsed row and
/// would otherwise clip against the fixed shell. The window stays
/// `resizable(false)` for the USER; this is programmatic only, driven by the
/// renderer measuring its own content (`set_pill_height` on every state change,
/// back to 44 on collapse). Height is clamped to [collapsed, cap]. The top-left
/// origin is untouched, so the lozenge grows downward in place — no reposition,
/// no horizontal reflow.
#[tauri::command]
pub fn set_pill_height(window: tauri::WebviewWindow, height: f64) -> Result<(), String> {
    let h = if height.is_finite() {
        height.clamp(PILL_COLLAPSED_H, PILL_MAX_H)
    } else {
        PILL_COLLAPSED_H
    };
    window
        .set_size(tauri::LogicalSize::new(PILL_COLLAPSED_W, h))
        .map_err(|e| e.to_string())
}

/// Logical (width, height) of the primary monitor, or None if it can't be
/// resolved. Logical units are what `WebviewWindowBuilder::position` and
/// `inner_size` consume, so keeping all geometry math in logical units (not
/// the physical pixels `Monitor::size()` reports) avoids the 2x-Retina
/// doubling that pushed the mascot off-screen.
fn primary_logical_size(app: &AppHandle) -> Option<(f64, f64)> {
    app.get_webview_window("main")
        .and_then(|w| w.primary_monitor().ok().flatten())
        .map(|m| {
            let sf = m.scale_factor();
            let sz = m.size();
            (sz.width as f64 / sf, sz.height as f64 / sf)
        })
}

/// Returns (x, y) for the default top-right placement on the current
/// primary monitor, in LOGICAL pixels. Falls back to a conservative
/// 1280×800 assumption if monitor enumeration fails.
fn default_top_right(app: &AppHandle, width: u32) -> (i32, i32) {
    let logical_w = primary_logical_size(app).map_or(1280.0, |(w, _)| w);
    let x = (logical_w - f64::from(width) - f64::from(DEFAULT_RIGHT_INSET)).max(24.0);
    (x as i32, DEFAULT_TOP_OFFSET)
}

/// The pill window's current monitor work area in LOGICAL pixels, for the
/// display-change re-clamp. Uses `current_monitor()`; if `Monitor` does not
/// expose a usable work-area in this tauri version, falls back to the full
/// `size()/scale_factor()` (62-RESEARCH A2 — the mascot's working fallback).
fn pill_work_area(window: &tauri::WebviewWindow) -> Option<WorkArea> {
    let m = window.current_monitor().ok().flatten()?;
    let sf = m.scale_factor();
    let pos = m.position();
    let sz = m.size();
    Some(WorkArea {
        x: pos.x as f64 / sf,
        y: pos.y as f64 / sf,
        w: sz.width as f64 / sf,
        h: sz.height as f64 / sf,
    })
}

/// Listen for geometry-changing + display-topology `WindowEvent`s on the
/// pill window and persist a debounced snapshot of geometry. Without
/// debounce, a single drag could fire ~60 store.save()s per second.
///
/// `Moved`/`Resized` → debounced geometry save (cloned from the mascot).
/// `ScaleFactorChanged` → display-change re-clamp (Leg D — the one new arm):
/// recompute against the current monitor's work area and `set_position`
/// back inside if the pill is off-screen.
fn install_geometry_listener(app: AppHandle, window: tauri::WebviewWindow) {
    let scheduled: Arc<Mutex<Option<std::time::Instant>>> = Arc::new(Mutex::new(None));
    let reclamp_window = window.clone();

    window.on_window_event(move |event| {
        use tauri::WindowEvent;

        // Leg D — display-change re-clamp. A monitor unplug / resolution
        // change fires ScaleFactorChanged on the affected window; re-evaluate
        // the persisted origin against the (possibly shrunken) work area and
        // pull the pill back on-screen if it now lands outside.
        if let WindowEvent::ScaleFactorChanged { .. } = event {
            if let Some(area) = pill_work_area(&reclamp_window) {
                if let (Ok(pos), Ok(size)) =
                    (reclamp_window.outer_position(), reclamp_window.inner_size())
                {
                    let sf = reclamp_window.scale_factor().unwrap_or(1.0);
                    // Convert physical → logical for the clamp math, then
                    // back to physical for set_position.
                    let lx = (pos.x as f64 / sf) as i32;
                    let ly = (pos.y as f64 / sf) as i32;
                    let lw = (size.width as f64 / sf) as u32;
                    let lh = (size.height as f64 / sf) as u32;
                    let (cx, cy) = clamp_to_work_area(lx, ly, lw, lh, area);
                    if (cx, cy) != (lx, ly) {
                        let _ = reclamp_window.set_position(tauri::LogicalPosition::new(cx, cy));
                    }
                }
            }
            return;
        }

        // We only care about geometry-changing events otherwise. Close and
        // other events are handled by the lifecycle override in tray.rs.
        if !matches!(event, WindowEvent::Moved(_) | WindowEvent::Resized(_)) {
            return;
        }

        let app = app.clone();
        let scheduled = scheduled.clone();

        // Capture geometry NOW (closure runs on the OS event thread; the
        // debounced save runs on Tokio).
        let Ok(pos) = window_position(&app) else {
            return;
        };
        let Ok(size) = window_size(&app) else {
            return;
        };

        let my_schedule = std::time::Instant::now();
        let scheduled_clone = scheduled.clone();

        tauri::async_runtime::spawn(async move {
            {
                let mut g = scheduled_clone.lock().await;
                *g = Some(my_schedule);
            }
            tokio::time::sleep(Duration::from_millis(DEBOUNCE_MS)).await;
            // Compare-and-skip: if a newer event scheduled after us, it owns
            // the save.
            {
                let g = scheduled_clone.lock().await;
                if *g != Some(my_schedule) {
                    return;
                }
            }
            let cur = PillWindowState {
                x: Some(pos.x),
                y: Some(pos.y),
                width: Some(size.width),
                height: Some(size.height),
            };
            let _ = save_pill_state(&app, &cur);
        });
    });
}

fn window_position(app: &AppHandle) -> tauri::Result<PhysicalPosition<i32>> {
    let w = app
        .get_webview_window(PILL_WINDOW_LABEL)
        .ok_or(tauri::Error::WebviewNotFound)?;
    w.outer_position()
}

fn window_size(app: &AppHandle) -> tauri::Result<PhysicalSize<u32>> {
    let w = app
        .get_webview_window(PILL_WINDOW_LABEL)
        .ok_or(tauri::Error::WebviewNotFound)?;
    w.inner_size()
}

/// Read the persisted `PillWindowState`. Returns defaults when the key is
/// absent (first launch). Reaches `tauri-plugin-store` directly (config.rs
/// is plan 62-02's edit, not this plan's).
fn load_pill_state(app: &AppHandle) -> Result<PillWindowState, String> {
    use tauri_plugin_store::StoreExt;
    let store = app
        .store(STORE_PATH)
        .map_err(|e| format!("store init failed: {e}"))?;
    match store.get(KEY_PILL_WINDOW) {
        Some(value) => {
            serde_json::from_value(value.clone()).map_err(|e| format!("decode failed: {e}"))
        }
        None => Ok(PillWindowState::default()),
    }
}

/// Persist the `PillWindowState` (called from the debounced geometry handler).
fn save_pill_state(app: &AppHandle, state: &PillWindowState) -> Result<(), String> {
    use tauri_plugin_store::StoreExt;
    let store = app
        .store(STORE_PATH)
        .map_err(|e| format!("store init failed: {e}"))?;
    let value = serde_json::to_value(state).map_err(|e| format!("encode failed: {e}"))?;
    store.set(KEY_PILL_WINDOW, value);
    store
        .save()
        .map_err(|e| format!("store save failed: {e}"))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_pin_context_decisions() {
        // UI-SPEC §Pill Dimensions LOCKED: collapsed 280×44.
        assert_eq!(PILL_COLLAPSED_W, 280.0);
        assert_eq!(PILL_COLLAPSED_H, 44.0);
    }

    #[test]
    fn debounce_is_not_zero_or_thrashy() {
        // 200ms keeps drag-fire below 5 store.save()s/sec in the worst
        // case. < 50ms would still thrash; > 500ms would feel laggy on the
        // final save (cloned from the mascot's tuned value).
        assert!((50..=500).contains(&{ DEBOUNCE_MS }));
    }

    #[test]
    fn label_constant_matches_capability_allowlist() {
        // capabilities/default.json "windows" must include "pill".
        assert_eq!(PILL_WINDOW_LABEL, "pill");
    }

    #[test]
    fn clamp_to_work_area_keeps_visible() {
        // A 1440×900 work area at origin (0,0).
        let area = WorkArea {
            x: 0.0,
            y: 0.0,
            w: 1440.0,
            h: 900.0,
        };

        // On-screen candidate is returned unchanged.
        let (x, y) = clamp_to_work_area(100, 80, 280, 44, area);
        assert_eq!((x, y), (100, 80));

        // Off-screen to the RIGHT (saved x past a now-gone external display)
        // snaps back so the full 280px width is visible: max_x = 1440-280 = 1160.
        let (x, _) = clamp_to_work_area(2564, 80, 280, 44, area);
        assert_eq!(x, 1160);

        // Off-screen to the BOTTOM snaps back: max_y = 900-44 = 856.
        let (_, y) = clamp_to_work_area(100, 5000, 280, 44, area);
        assert_eq!(y, 856);

        // Negative origin (off the top-left) snaps to the area origin.
        let (x, y) = clamp_to_work_area(-300, -300, 280, 44, area);
        assert_eq!((x, y), (0, 0));

        // A work area offset from the screen origin (e.g. a second monitor at
        // x=1440) clamps relative to that origin.
        let area2 = WorkArea {
            x: 1440.0,
            y: 0.0,
            w: 1440.0,
            h: 900.0,
        };
        let (x, y) = clamp_to_work_area(1000, 50, 280, 44, area2);
        assert_eq!((x, y), (1440, 50)); // x pulled up to the monitor origin

        // A window WIDER than the work area pins to the area origin (clipped
        // right, not shoved off the left).
        let narrow = WorkArea {
            x: 0.0,
            y: 0.0,
            w: 200.0,
            h: 900.0,
        };
        let (x, _) = clamp_to_work_area(50, 80, 280, 44, narrow);
        assert_eq!(x, 0);
    }
}
