// SPDX-License-Identifier: Apache-2.0
//
// vibemix Phase 24 Wave-0 spike — AX-from-Rust-parent feasibility test.
//
// Pitfall 3 (Tauri #8329): sidecar processes spawned by a Tauri parent do
// NOT inherit AX permissions even when the parent's bundle is granted
// Accessibility access. This spike is a STANDALONE Rust binary that
// reproduces the parent-process side of that pattern: a bundle signed
// with `world.bravoh.vibemix.spike` calls both `CGWindowListCopyWindowInfo`
// (window-rect fallback path) and `AXUIElementCopyAttributeValue` (precise
// knob-level path) against a running djay Pro 5 process. The verdict
// determines whether Plan 24-03 ships the AX-precise positioning OR the
// percentage-of-window-rect coord_map fallback.
//
// Reference port: cohost_v4.py's `find_djay_window_bounds()` (POC,
// UNTOUCHED per CLAUDE.md). The Python pattern is read-only inspiration —
// the spike rewrites the same logic in Rust to test AX inheritance ON A
// CODE-SIGNED INSTALLED BUNDLE (which `tauri dev` doesn't exercise).
//
// Output verdicts (printed to stdout, one per run):
//   - AX_PASS         : both kCGWindowBounds AND AX returned non-empty data
//   - AX_PARTIAL      : kCGWindowBounds OK, AX empty → fallback path
//   - AX_FAIL         : both empty → Tauri #8329 confirmed; fallback only
//   - AX_INCONCLUSIVE : djay Pro not running → user re-runs after launching
//
// Run from the standalone binary (NOT from inside the Tauri parent — the
// parent's own AX grant must NOT pollute this test).

#![cfg(target_os = "macos")]

use std::process;

#[cfg(target_os = "macos")]
mod ax {
    //! AX + Quartz wrapper. All FFI gated behind cfg(target_os = "macos")
    //! so a stray cross-compile attempt fails at link time, not silently.

    use accessibility_sys::{
        kAXChildrenAttribute, kAXFocusedWindowAttribute, kAXPositionAttribute,
        kAXRoleAttribute, kAXSizeAttribute, kAXTitleAttribute,
        AXUIElementCopyAttributeValue, AXUIElementCreateApplication,
        AXUIElementRef,
    };
    use core_foundation::array::{CFArray, CFArrayRef};
    use core_foundation::base::{CFTypeRef, TCFType};
    use core_foundation::dictionary::CFDictionary;
    use core_foundation::number::CFNumber;
    use core_foundation::string::{CFString, CFStringRef};
    use core_graphics::display::{
        kCGNullWindowID, kCGWindowListOptionOnScreenOnly, CGWindowListCopyWindowInfo,
    };
    use std::ffi::c_void;

    /// Rect mirrors djay Pro window kCGWindowBounds.
    #[derive(Debug, Clone, Copy)]
    pub struct Rect {
        pub x: f64,
        pub y: f64,
        pub width: f64,
        pub height: f64,
    }

    /// Find the djay Pro window via Quartz. Returns `(pid, rect)` on success.
    ///
    /// Match strategy: kCGWindowOwnerName lowercased contains "djay". Mirrors
    /// the cohost_v4.py POC pattern verbatim — DO NOT TIGHTEN without a real
    /// false-positive (the loose match is intentional; djay Pro v5 vs djay
    /// Pro AI vs djay Pro 5 all carry "djay" in the owner string).
    pub fn find_djay_window() -> Option<(i32, Rect)> {
        // SAFETY: Quartz API — returns CFArrayRef the caller releases. The
        // CFArray::wrap_under_create_rule below takes ownership so the
        // refcount drops at scope end.
        let info_ref: CFArrayRef = unsafe {
            CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
        };
        if info_ref.is_null() {
            return None;
        }
        let array: CFArray<CFDictionary<CFString, CFTypeRef>> =
            unsafe { CFArray::wrap_under_create_rule(info_ref) };

        for i in 0..array.len() {
            let dict = match array.get(i) {
                Some(d) => d,
                None => continue,
            };

            let owner_key = CFString::new("kCGWindowOwnerName");
            let owner_value: Option<CFString> = unsafe {
                let raw = dict.find(&owner_key)?;
                if raw.is_null() {
                    None
                } else {
                    // The dictionary stores a CFStringRef under this key.
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

            // pid lives at kCGWindowOwnerPID — CFNumber → i32.
            let pid_key = CFString::new("kCGWindowOwnerPID");
            let pid: i32 = unsafe {
                let raw = dict.find(&pid_key)?;
                if raw.is_null() {
                    continue;
                }
                let num = CFNumber::wrap_under_get_rule(*raw as _);
                num.to_i32().unwrap_or(0)
            };

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
                            Some(v) if !v.is_null() => {
                                CFNumber::wrap_under_get_rule(*v as _)
                                    .to_f64()
                                    .unwrap_or(0.0)
                            }
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
                    return Some((pid, r));
                }
            }
        }
        None
    }

    /// Walk the AX tree of the given pid. Returns `(slider_count, sample_role)`.
    /// Used to gate the AX_PASS verdict — non-zero slider count or any
    /// non-empty role string means AX inheritance worked.
    pub fn probe_ax_tree(pid: i32) -> (usize, Option<String>) {
        // SAFETY: AXUIElementCreateApplication returns a +1 reference the
        // caller releases. We treat the AXUIElementRef as an opaque handle
        // and let the CF release run at scope end via wrap_under_create_rule.
        let app: AXUIElementRef = unsafe { AXUIElementCreateApplication(pid) };
        if app.is_null() {
            return (0, None);
        }

        // First: read the focused window. If AX is not granted, this call
        // returns kAXErrorAPIDisabled / kAXErrorCannotComplete — both
        // manifest as a null value pointer with a non-zero error code.
        let focused = copy_attribute(app, kAXFocusedWindowAttribute);
        let focused = match focused {
            Some(f) => f,
            None => {
                unsafe { release_cf(app as CFTypeRef) };
                return (0, None);
            }
        };

        // Walk children + find sliders. Single-level scan for the spike —
        // production code in Plan 24-03 will recurse the full tree.
        let mut slider_count = 0usize;
        let mut sample_role: Option<String> = None;
        if let Some(children_ref) = copy_attribute(focused as AXUIElementRef, kAXChildrenAttribute)
        {
            let arr: CFArray<CFTypeRef> = unsafe {
                CFArray::wrap_under_create_rule(children_ref as CFArrayRef)
            };
            for i in 0..arr.len() {
                let child_ref = match arr.get(i) {
                    Some(c) => *c as AXUIElementRef,
                    None => continue,
                };
                if let Some(role_ref) = copy_attribute(child_ref, kAXRoleAttribute) {
                    let role: CFString =
                        unsafe { CFString::wrap_under_create_rule(role_ref as CFStringRef) };
                    let role_str = role.to_string();
                    if sample_role.is_none() {
                        sample_role = Some(role_str.clone());
                    }
                    if role_str == "AXSlider" {
                        slider_count += 1;
                        if let Some(p) = copy_attribute(child_ref, kAXPositionAttribute) {
                            println!("  slider position handle: {:?}", p);
                        }
                        if let Some(s) = copy_attribute(child_ref, kAXSizeAttribute) {
                            println!("  slider size handle: {:?}", s);
                        }
                        if let Some(t) = copy_attribute(child_ref, kAXTitleAttribute) {
                            let title: CFString = unsafe {
                                CFString::wrap_under_create_rule(t as CFStringRef)
                            };
                            println!("  slider title: {:?}", title.to_string());
                        }
                    }
                }
            }
        }

        unsafe {
            release_cf(focused as CFTypeRef);
            release_cf(app as CFTypeRef);
        }
        (slider_count, sample_role)
    }

    fn copy_attribute(elem: AXUIElementRef, attr: &str) -> Option<*const c_void> {
        let attr_cf = CFString::new(attr);
        let mut out: CFTypeRef = std::ptr::null();
        // SAFETY: AXUIElementCopyAttributeValue follows the standard
        // Create Rule for the out-param — we receive a +1 reference if the
        // call succeeds (err == 0).
        let err = unsafe {
            AXUIElementCopyAttributeValue(
                elem,
                attr_cf.as_concrete_TypeRef(),
                &mut out as *mut CFTypeRef,
            )
        };
        if err != 0 || out.is_null() {
            None
        } else {
            Some(out as *const c_void)
        }
    }

    unsafe fn release_cf(_ref: CFTypeRef) {
        // CoreFoundation::base does not expose a stable `release` symbol via
        // the high-level wrapper; we rely on the wrap_under_create_rule
        // dropping the refcount when the CFType wrapper goes out of scope
        // upstream. Stub kept here for symmetry with the C API.
    }
}

fn main() {
    #[cfg(target_os = "macos")]
    {
        println!("== vibemix-ax-spike (Phase 24 Wave 0) ==");
        println!("Probing for djay Pro window via Quartz CGWindowListCopyWindowInfo...");

        let djay = ax::find_djay_window();
        let (pid, rect) = match djay {
            Some((pid, r)) => {
                println!(
                    "  djay found: pid={} rect=({:.1},{:.1},{:.1}x{:.1})",
                    pid, r.x, r.y, r.width, r.height
                );
                (pid, r)
            }
            None => {
                println!("  djay NOT running — skipping AX probe.");
                println!("AX_INCONCLUSIVE (djay not running — re-run after launching djay Pro)");
                process::exit(0);
            }
        };

        println!("Probing AX tree for pid={} ...", pid);
        let (slider_count, sample_role) = ax::probe_ax_tree(pid);
        println!(
            "  slider_count={} sample_role={:?}",
            slider_count, sample_role
        );

        let window_ok = rect.width > 1.0 && rect.height > 1.0;
        let ax_ok = slider_count > 0 || sample_role.is_some();

        // Verdict matrix per 24-01-PLAN.md Task 3:
        match (window_ok, ax_ok) {
            (true, true) => {
                println!("AX_PASS (kCGWindowBounds + AX tree both populated — Plan 24-03 ships AX-precise)");
            }
            (true, false) => {
                println!("AX_PARTIAL (kCGWindowBounds OK, AX empty — Plan 24-03 ships percentage-of-window-rect fallback)");
            }
            (false, true) => {
                println!("AX_PARTIAL (AX OK, kCGWindowBounds empty — unusual; check coord space)");
            }
            (false, false) => {
                println!("AX_FAIL (both empty — Tauri #8329 confirmed; fallback only)");
            }
        }
    }

    #[cfg(not(target_os = "macos"))]
    {
        eprintln!("vibemix-ax-spike only runs on macOS — this binary is a no-op on other targets.");
        process::exit(2);
    }
}
