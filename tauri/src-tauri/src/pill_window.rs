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
//!   3. **ADD** a `#[cfg(target_os="macos")]` focus-non-steal block after
//!      `.build()` (the one genuinely-new native code in the phase) + a
//!      display-change re-clamp arm in the geometry listener (Leg D).
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
//! pill into the visible work area when the monitor topology changes.

use serde::{Deserialize, Serialize};
use tauri::AppHandle;

pub const PILL_WINDOW_LABEL: &str = "pill";

// Collapsed dimensions. UI-SPEC §Pill Dimensions LOCKED 280×44. Pinning
// these in a test makes any future change a deliberate test edit.
const PILL_COLLAPSED_W: f64 = 280.0;
const PILL_COLLAPSED_H: f64 = 44.0;

// Geometry-persist debounce. 200ms is well above 60Hz drag-event cadence
// without feeling laggy on the final save after the user releases. Kept
// VERBATIM from the mascot.
const DEBOUNCE_MS: u64 = 200;

/// Persisted pill window geometry. Mirrors the mascot's window-state shape
/// but pill-scoped (its own `pill_window` store key). All fields optional →
/// a legacy/missing config decodes to "no saved geometry" and the builder
/// falls back to `default_top_right`.
// Wired into the save/load path in Task 2; declared here so the module shape
// is stable across the two commits.
#[allow(dead_code)]
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

/// Build the pill overlay window.
///
/// Task 1 (this commit) ships a no-op STUB returning `Ok(None)` so the
/// module compiles standalone and `cargo test pill_window::tests` can pin
/// the constants + clamp math. Task 2 replaces this body with the real
/// cloned builder + macOS focus-non-steal interop + geometry listener.
pub fn create_pill_window(
    _app: &AppHandle,
) -> tauri::Result<Option<tauri::WebviewWindow>> {
    // STUB — Task 2 fleshes the builder. Returning Ok(None) keeps the
    // call-site (main.rs setup branch, plan 62-02) non-fatal.
    Ok(None)
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
        let area = WorkArea { x: 0.0, y: 0.0, w: 1440.0, h: 900.0 };

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
        let area2 = WorkArea { x: 1440.0, y: 0.0, w: 1440.0, h: 900.0 };
        let (x, y) = clamp_to_work_area(1000, 50, 280, 44, area2);
        assert_eq!((x, y), (1440, 50)); // x pulled up to the monitor origin

        // A window WIDER than the work area pins to the area origin (clipped
        // right, not shoved off the left).
        let narrow = WorkArea { x: 0.0, y: 0.0, w: 200.0, h: 900.0 };
        let (x, _) = clamp_to_work_area(50, 80, 280, 44, narrow);
        assert_eq!(x, 0);
    }
}
