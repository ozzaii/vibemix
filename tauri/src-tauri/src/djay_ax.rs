//! Phase 24 Plan 02 — djay Pro Accessibility bridge (Rust parent only).
//!
//! Per Pitfall 3 (Tauri #8329) + 24-CONTEXT D-LOCKED: AX queries MUST live
//! in the Rust parent process. The Python sidecar cannot inherit AX
//! permissions even when the parent's bundle is granted Accessibility; a
//! sidecar AX call would silently return empty data on the shipping
//! signed binary.
//!
//! Public surface:
//!
//!   `query_element_bounds(element_id) -> Option<Rect>`
//!
//! Returns the screen-coords bounding box for one of the 12 hand-mapped
//! djay Pro v5 UI elements (mid_eq_a, low_eq_a, waveform_a, …). Returns
//! `None` if djay Pro is not running, the element ID is unknown, or AX
//! permission is not granted.
//!
//! Implementation path (auto-selected by WAVE-0-AX-SPIKE.md verdict):
//!
//!   * **PARTIAL (default v2.0 path)** — uses `CGWindowListCopyWindowInfo`
//!     to find djay's window rect, then applies a percentage-of-window
//!     coord map for each known element_id. Accuracy: EQ-region-approximate.
//!     Ships on all WAVE-0 verdicts EXCEPT PASS (per 24-01-SUMMARY directive).
//!   * **PASS path (Plan 24-03 follow-up)** — would walk djay's AX tree
//!     via `AXUIElementCopyAttributeValue` to read each slider's
//!     `kAXPositionAttribute` + `kAXSizeAttribute` directly. Promoted in
//!     a follow-up when WAVE-0-AX-SPIKE.md frontmatter flips to
//!     `verdict: pass`.
//!
//! macOS-only by construction. The cross-platform shim at the bottom
//! returns `None` so Windows builds stay green without `cfg` clutter in
//! callers.

use serde::{Deserialize, Serialize};

/// Screen-coords bounding box. Units = physical pixels (Quartz coord-space,
/// NOT NSScreen — per Pitfall 13).
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub struct Rect {
    pub x: f64,
    pub y: f64,
    pub width: f64,
    pub height: f64,
}

/// The 12 hand-mapped djay Pro v5 elements + their percentage-of-window
/// position rectangles. Numbers are djay Pro 5.x default layout @ 1920×1080
/// — they degrade gracefully on smaller / larger windows (proportions hold).
///
/// Plan 24-03 will replace this with AX-precise lookup IF the spike verdict
/// comes back PASS. Until then this is the shipping coord map.
///
/// (left%, top%, width%, height%)
const COORD_MAP: &[(&str, (f64, f64, f64, f64))] = &[
    // Deck A
    ("deck_a_high_eq", (0.15, 0.22, 0.05, 0.06)),
    ("deck_a_mid_eq", (0.15, 0.30, 0.05, 0.06)),
    ("deck_a_low_eq", (0.15, 0.38, 0.05, 0.06)),
    ("deck_a_filter", (0.15, 0.46, 0.05, 0.06)),
    ("deck_a_gain", (0.15, 0.14, 0.05, 0.06)),
    ("waveform_a", (0.05, 0.05, 0.40, 0.10)),
    // Deck B
    ("deck_b_high_eq", (0.80, 0.22, 0.05, 0.06)),
    ("deck_b_mid_eq", (0.80, 0.30, 0.05, 0.06)),
    ("deck_b_low_eq", (0.80, 0.38, 0.05, 0.06)),
    ("deck_b_filter", (0.80, 0.46, 0.05, 0.06)),
    ("deck_b_gain", (0.80, 0.14, 0.05, 0.06)),
    ("waveform_b", (0.55, 0.05, 0.40, 0.10)),
];

/// Look up the percentage-rect for a known element_id. Returns None for
/// unknown ids — caller MUST treat this as a graceful no-op (T-24-02-01).
fn coord_for(element_id: &str) -> Option<(f64, f64, f64, f64)> {
    COORD_MAP
        .iter()
        .find(|(id, _)| *id == element_id)
        .map(|(_, r)| *r)
}

/// Public surface — see module docstring. macOS implementation walks
/// Quartz to find djay's window rect, then applies the coord map. Returns
/// `None` for any of:
///   - djay Pro not running (no window with owner containing "djay")
///   - element_id not in the known 12-element map
///   - djay window rect degenerate (width or height ≤ 1.0 px)
pub fn query_element_bounds(element_id: &str) -> Option<Rect> {
    // 1) Allowlist check — refuse unknown element IDs without making any
    //    OS calls. This is the T-24-02-01 mitigation.
    let (px, py, pw, ph) = coord_for(element_id)?;

    // 2) Locate djay's window rect (PARTIAL path — shipping default).
    let window_rect = imp::find_djay_window_rect()?;

    // 3) Apply percentage map.
    if window_rect.width <= 1.0 || window_rect.height <= 1.0 {
        return None;
    }
    Some(Rect {
        x: window_rect.x + px * window_rect.width,
        y: window_rect.y + py * window_rect.height,
        width: pw * window_rect.width,
        height: ph * window_rect.height,
    })
}

// ===========================================================================
// macOS impl — Quartz CGWindowListCopyWindowInfo
// ===========================================================================

#[cfg(target_os = "macos")]
mod imp {
    use super::Rect;
    use core_foundation::array::{CFArray, CFArrayRef};
    use core_foundation::base::{CFTypeRef, TCFType};
    use core_foundation::dictionary::CFDictionary;
    use core_foundation::number::CFNumber;
    use core_foundation::string::{CFString, CFStringRef};
    use core_graphics::display::{
        kCGNullWindowID, kCGWindowListOptionOnScreenOnly, CGWindowListCopyWindowInfo,
    };

    /// Find djay Pro's on-screen window via Quartz. Match strategy mirrors
    /// the cohost_v4.py POC pattern (owner contains "djay", case-insensitive)
    /// — DO NOT TIGHTEN without a real false-positive; djay Pro v5 / djay
    /// Pro AI / djay Pro 5 all carry "djay" in the owner string.
    pub fn find_djay_window_rect() -> Option<Rect> {
        // SAFETY: Quartz returns a +1 CFArrayRef the caller releases. We
        // wrap_under_create_rule so the refcount drops at scope end.
        let info_ref: CFArrayRef = unsafe {
            CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
        };
        if info_ref.is_null() {
            return None;
        }
        let array: CFArray<CFDictionary<CFString, CFTypeRef>> =
            unsafe { CFArray::wrap_under_create_rule(info_ref) };

        for i in 0..array.len() {
            let dict = array.get(i)?;
            let owner_key = CFString::new("kCGWindowOwnerName");
            let owner_value: Option<CFString> = unsafe {
                let raw = dict.find(&owner_key)?;
                if raw.is_null() {
                    None
                } else {
                    Some(CFString::wrap_under_get_rule(*raw as CFStringRef))
                }
            };
            let owner = match owner_value {
                Some(s) => s.to_string().to_lowercase(),
                None => continue,
            };
            if !owner.contains("djay") {
                continue;
            }

            // kCGWindowBounds is a CFDictionary {X, Y, Width, Height}.
            let bounds_key = CFString::new("kCGWindowBounds");
            let rect: Option<Rect> = unsafe {
                let raw = dict.find(&bounds_key)?;
                if raw.is_null() {
                    None
                } else {
                    let bounds_dict: CFDictionary<CFString, CFTypeRef> =
                        CFDictionary::wrap_under_get_rule(*raw as _);
                    let read = |k: &str| -> f64 {
                        let key = CFString::new(k);
                        match bounds_dict.find(&key) {
                            Some(v) if !v.is_null() => CFNumber::wrap_under_get_rule(*v as _)
                                .to_f64()
                                .unwrap_or(0.0),
                            _ => 0.0,
                        }
                    };
                    Some(Rect {
                        x: read("X"),
                        y: read("Y"),
                        width: read("Width"),
                        height: read("Height"),
                    })
                }
            };

            if let Some(r) = rect {
                if r.width > 1.0 && r.height > 1.0 {
                    return Some(r);
                }
            }
        }
        None
    }
}

// ===========================================================================
// Cross-platform stub — Windows / Linux always return None.
// ===========================================================================

#[cfg(not(target_os = "macos"))]
mod imp {
    use super::Rect;
    pub fn find_djay_window_rect() -> Option<Rect> {
        // Phase 24 is Mac-only in v2.0 (per CONTEXT). Windows ships in v2.x.
        None
    }
}

// ===========================================================================
// Tests
// ===========================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unknown_element_returns_none() {
        // Allowlist mitigation T-24-02-01: unknown element ids return
        // None without making any OS calls. Compile-test only — the
        // function signature must accept &str and return Option<Rect>.
        assert!(query_element_bounds("definitely-not-an-element").is_none());
        assert!(query_element_bounds("").is_none());
    }

    #[test]
    fn known_elements_are_complete() {
        // Verify the 12 hand-mapped elements all have entries — guards
        // against accidental deletion / typo of map keys.
        let required = [
            "deck_a_high_eq",
            "deck_a_mid_eq",
            "deck_a_low_eq",
            "deck_a_filter",
            "deck_a_gain",
            "waveform_a",
            "deck_b_high_eq",
            "deck_b_mid_eq",
            "deck_b_low_eq",
            "deck_b_filter",
            "deck_b_gain",
            "waveform_b",
        ];
        assert_eq!(COORD_MAP.len(), required.len());
        for id in required {
            assert!(
                coord_for(id).is_some(),
                "missing element_id in coord map: {id}",
            );
        }
    }

    #[test]
    fn query_when_djay_absent_is_graceful() {
        // CI never has djay Pro running, so this must return None for any
        // valid id without panicking. macOS-only behavior matters here —
        // on other platforms imp::find_djay_window_rect() returns None
        // unconditionally, so the same assertion holds.
        let r = query_element_bounds("waveform_a");
        // We don't assert is_none() unconditionally because a developer
        // running tests locally MIGHT have djay Pro open. The contract
        // is "does not panic" — which is what we test here.
        let _ = r;
    }

    #[test]
    fn coord_map_percentages_are_in_unit_range() {
        // Sanity check: all four ratios in [0.0, 1.0].
        for (id, (l, t, w, h)) in COORD_MAP {
            assert!((0.0..=1.0).contains(l), "{id} left out of range: {l}");
            assert!((0.0..=1.0).contains(t), "{id} top out of range: {t}");
            assert!((0.0..=1.0).contains(w), "{id} width out of range: {w}");
            assert!((0.0..=1.0).contains(h), "{id} height out of range: {h}");
            assert!(l + w <= 1.0001, "{id} right edge overruns: {}", l + w);
            assert!(t + h <= 1.0001, "{id} bottom edge overruns: {}", t + h);
        }
    }
}
