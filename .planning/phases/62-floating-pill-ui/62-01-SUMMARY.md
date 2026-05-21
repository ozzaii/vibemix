---
phase: 62-floating-pill-ui
plan: 01
subsystem: ui
tags: [tauri, rust, overlay-window, nspanel, objc2, macos, capability-acl, multi-monitor, drag]

# Dependency graph
requires:
  - phase: 13-mascot-overlay
    provides: "mascot_window.rs clone source (builder flags, 200ms-debounce geometry persist, off-screen fallback, label↔capability test) + capabilities/default.json windows-scope pattern"
provides:
  - "pill_window.rs — third Tauri overlay window builder (transparent/always_on_top/decorations(false)/resizable(false)/skip_taskbar/visible_on_all_workspaces/focused(false)), NOT click-through (interactive)"
  - "PILL_WINDOW_LABEL = \"pill\" + pure clamp_to_work_area + WorkArea (Leg-D math, unit-testable without a live monitor)"
  - "pill-scoped geometry persistence under a dedicated `pill_window` config.json store key (config.rs untouched; 200ms debounce)"
  - "display-change re-clamp (WindowEvent::ScaleFactorChanged → current_monitor work-area clamp) — the one new event hook"
  - "macOS focus-non-steal FLOOR (ActivationPolicy::Accessory + focused(false)) + bounded NSPanel STRETCH (objc2 NSWindow→NSPanel swizzle + NonactivatingPanel mask, gated → degrades to floor)"
  - "\"pill\" window label in the capability allowlist (closes the v0.1.0-rc1 drag-capability debt; existing core:window:allow-start-dragging now applies to the pill)"
affects: [62-02-primary-surface-switch, 62-04-pill-ui-surface, 62-05-deck-chips]

# Tech tracking
tech-stack:
  added: ["objc2 = \"0.6\" (macOS-only, crates.io — already transitive in Cargo.lock; graph unchanged)"]
  patterns: ["clone-with-subtraction overlay window", "Leg-D clamp math extracted to a pure fn for unit-testability", "floor+stretch native interop with never-panic degradation"]

key-files:
  created:
    - tauri/src-tauri/src/pill_window.rs
  modified:
    - tauri/src-tauri/src/main.rs
    - tauri/src-tauri/Cargo.toml
    - tauri/src-tauri/Cargo.lock
    - tauri/src-tauri/capabilities/default.json

key-decisions:
  - "Used objc2 (raw runtime: AnyObject::set_class + msg_send) for the NSPanel swizzle rather than objc2-app-kit typed bindings — both crates.io, objc2 was already in Cargo.lock so the dep graph is unchanged; the swizzle needs the raw class-set anyway. tauri-nspanel (git-only) stays rejected."
  - "Pill geometry persists under its OWN `pill_window` store key reached directly via tauri-plugin-store, NOT a config.rs helper — config.rs is plan 62-02's edit (the primary_surface switch); this plan keeps config.rs untouched."
  - "Shipped BOTH focus tiers: Accessory-policy FLOOR (guaranteed, no graph change) + the NSPanel STRETCH (compiles + gated). Runtime efficacy of the stretch is the felt KAAN-ACTION."

patterns-established:
  - "Clone-with-subtraction overlay window: pill_window.rs = mascot_window.rs minus the click-through block, plus the macOS focus #[cfg] block + the display-change re-clamp arm."
  - "Pure clamp helper (clamp_to_work_area + WorkArea struct) so multi-monitor clamp math is cargo-testable without a live monitor."
  - "Floor+stretch native interop: the no-dep baseline always applies; the bounded native stretch is gated behind with_webview and degrades silently to the floor on any failure (never panics)."

requirements-completed: [PILL-01, PILL-04]

# Metrics
duration: 6min
completed: 2026-05-22
---

# Phase 62 Plan 01: Floating Pill Window — Spike + Capability Summary

**Built `pill_window.rs` as a clone-with-subtraction of `mascot_window.rs` (transparent/on-top/decoration-less/non-focus-steal, interactive — NOT click-through), with pill-scoped 200ms-debounced geometry persistence, a display-change re-clamp hook, the macOS focus-non-steal Accessory FLOOR plus a gated NSPanel STRETCH, and the `"pill"` capability-allowlist entry that closes the v0.1.0-rc1 drag-capability debt.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-21T21:21:56Z
- **Completed:** 2026-05-22 (post-midnight rollover during the run)
- **Tasks:** 4 (3 automated + 1 human-verify checkpoint auto-approved per overnight policy)
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments
- **`pill_window.rs` (the resolve-FIRST spike) shipped:** transparent, always-on-top, decoration-less, fixed-size (280×44), non-focus-stealing, multi-monitor-safe pill window builder. Interactive (no `set_ignore_cursor_events`).
- **macOS focus-non-steal, both tiers:** Accessory-policy FLOOR (no new dep, the shipped PILL-04 mechanism) + a bounded NSPanel STRETCH (objc2 `NSWindow→NSPanel` swizzle + `NonactivatingPanel` mask) that compiles and degrades silently to the floor on any failure.
- **Display-change re-clamp (Leg D):** a `WindowEvent::ScaleFactorChanged` arm pulls the pill back into the current monitor's work area on topology change — the one genuinely-new event hook on top of the cloned listener.
- **`"pill"` capability label added** to `capabilities/default.json` — the existing `core:window:allow-start-dragging` permission now scopes to the pill, closing the v0.1.0-rc1 drag-capability debt with NO new permission identifier (least privilege, threat T-62-01).
- **All automated verification green:** `cargo build` clean (no warnings), full `cargo test` 59/59 (incl. the 4 new pill tests), `tauri-nspanel` absent from Cargo.toml, `pill` present in the windows JSON array.

## Task Commits

Each task was committed atomically (per-file staged on the `live-tuning-or-brain` main working tree):

1. **Task 1: Wave-0 cargo tests + skeleton (RED/char)** — `0d4458f` (test)
   - `defaults_pin_context_decisions`, `debounce_is_not_zero_or_thrashy`, `label_constant_matches_capability_allowlist`, `clamp_to_work_area_keeps_visible` — all green; `create_pill_window` stubbed `Ok(None)`; `mod pill_window;` declared in main.rs.
2. **Task 2: Flesh builder + geometry-persist + re-clamp + macOS focus floor/stretch** — `22087b5` (feat)
   - Real `WebviewWindowBuilder`; 200ms-debounced geometry save under `pill_window` store key; Leg-D `ScaleFactorChanged` re-clamp; Accessory FLOOR + gated NSPanel STRETCH; `objc2 = "0.6"` added macOS-only.
3. **Task 3: Add `"pill"` to the capability allowlist** — `7a2772a` (feat)
   - `"windows": [..., "debrief", "pill"]`; description updated for capabilities-lint.yml; no new permission identifier; no `app:allow-` identifier added.
4. **Task 4: Spike checkpoint (felt drag + focus-non-steal on the built app)** — no commit (human-verify checkpoint). ⚡ Auto-approved per the unattended overnight `gsd-autonomous fully` policy; the felt result is RECORDED below under KAAN-ACTION (built-app FELT confirmation = the one carve-out class — not self-approvable as "done", not blocking).

**Plan metadata:** committed separately (this SUMMARY + STATE.md + ROADMAP.md).

_Task 1 is the test/characterization commit; Task 2 is the implementation (TDD test→feat sequence)._

## Files Created/Modified
- `tauri/src-tauri/src/pill_window.rs` (created) — pill overlay window builder + pure clamp math + WorkArea + pill-scoped geometry persist/debounce/off-screen-fallback + display-change re-clamp + macOS focus-non-steal floor/stretch + 4 cargo tests.
- `tauri/src-tauri/src/main.rs` (modified) — one-line `mod pill_window;` declaration (the setup-branch wiring that calls `create_pill_window` is plan 62-02).
- `tauri/src-tauri/Cargo.toml` (modified) — added macOS-only `objc2 = "0.6"` (crates.io) for the NSPanel swizzle stretch.
- `tauri/src-tauri/Cargo.lock` (modified) — `+objc2` on the vibemix crate only (objc2 0.6.4 was already resolved as a transitive tauri/wry dep — no version bump, no new crates).
- `tauri/src-tauri/capabilities/default.json` (modified) — `"pill"` added to the windows scope + description note.

## Decisions Made
- **objc2 (raw) over objc2-app-kit (typed):** the plan named `objc2-app-kit` as the candidate; I used `objc2` directly because (a) the `NSWindow→NSPanel` swizzle needs the raw `AnyObject::set_class` regardless, (b) `objc2 0.6.4` was already in `Cargo.lock` as a transitive tauri/wry dep, so adding it direct leaves the resolved graph identical, and (c) it avoids pulling the larger typed AppKit binding surface. Both are crates.io; the rejected git-only NSPanel crate stays out (asserted absent: `grep -c tauri-nspanel Cargo.toml` == 0).
- **Pill geometry under its own `pill_window` store key, reached directly:** config.rs (and the `primary_surface` switch) is plan 62-02's edit. This plan keeps config.rs untouched and persists pill geometry via `tauri-plugin-store` directly, mirroring the mascot's debounce machinery verbatim.
- **Ship the floor, land the stretch as a compile-clean gated extra:** the Accessory FLOOR is the real shipped PILL-04 mechanism; the NSPanel STRETCH compiles and is gated to degrade to the floor. Whether the swizzle actually produces non-activating behavior at runtime is the felt KAAN-ACTION (cannot be unit-tested).

## Deviations from Plan

### Auto-fixed / discretionary adjustments

**1. [Discretion — dep choice] Used `objc2` rather than `objc2-app-kit` for the NSPanel stretch**
- **Found during:** Task 2
- **Issue:** The plan/research named `objc2-app-kit` as the candidate crate; the typed AppKit bindings are heavier than the swizzle needs.
- **Fix:** Added `objc2 = "0.6"` (macOS-only, crates.io) and used its raw runtime (`AnyObject::set_class`, `msg_send`, `AnyClass::get(c"NSPanel")`). The plan explicitly grants module-internal discretion and the dep policy (crates.io-only, no git `tauri-nspanel`) is honored.
- **Files modified:** `tauri/src-tauri/Cargo.toml`, `tauri/src-tauri/Cargo.lock`, `tauri/src-tauri/src/pill_window.rs`
- **Verification:** `cargo build` green; `cargo test` 59/59; `grep -c tauri-nspanel Cargo.toml` == 0; objc2 under `[target.'cfg(target_os = "macos")'.dependencies]`.
- **Committed in:** `22087b5`

**2. [Scope clarification] Geometry persisted via direct store access (config.rs not touched)**
- **Found during:** Task 2
- **Issue:** The mascot clones `config::load/save_mascot_state`; cloning into config.rs would touch a file outside this plan's `files_modified` (config.rs is 62-02's edit).
- **Fix:** Pill geometry uses a dedicated `pill_window` store key reached via `tauri-plugin-store` directly inside `pill_window.rs` (plan grants "your discretion … reuse the same geometry struct keyed under a `pill_window` store key, OR a dedicated pill helper"). Debounce/off-screen machinery kept identical to the mascot.
- **Files modified:** `tauri/src-tauri/src/pill_window.rs`
- **Verification:** `cargo build` + `cargo test` green; config.rs untouched (`git status` shows no config.rs change).
- **Committed in:** `22087b5`

---

**Total deviations:** 2 discretionary (both within plan-granted discretion + dep policy). **No scope creep** — config.rs, the UI (pill.html / src/pill/**), and the 62-02 setup-branch wiring all stay out of this plan.
**Impact on plan:** none adverse; the dep graph is unchanged and all acceptance criteria pass.

## Issues Encountered
- **Module-wide dead-code warnings:** `create_pill_window` + helpers are unused until plan 62-02 wires the setup branch, producing 23 dead-code warnings. Resolved with a single module-level `#![allow(dead_code)]` (commented as transient until 62-02), keeping the build quiet. Not a bug — intentional deferral.
- **Grep-literal collisions in comments:** the acceptance greps for `set_ignore_cursor_events` (must be 0) and `tauri-nspanel` (must be 0) initially matched explanatory comment text. Reworded the comments so the greps return 0 (no functional change). The `app:allow-` token remains only in the pre-existing description string (an anti-pattern warning), NOT as a permission identifier — confirmed via JSON parse.

## KAAN-ACTION (live-confirm)

These require the BUILT app on real macOS hardware and CANNOT be unit-tested — engineering is complete; the felt results are recorded here, not blocked (per `gsd-autonomous fully`).

**Focus tier shipped:** Accessory-policy **FLOOR** is the guaranteed baseline. The NSPanel **STRETCH** compiles and is gated (objc2 `NSWindow→NSPanel` swizzle + `NonactivatingPanel` mask, with never-panic fallback to the floor) — but whether the swizzle actually yields non-activating behavior at runtime is unverified without the built app. `objc2 = "0.6"` was added (macOS-only, crates.io; no graph change).

1. **Drag-on-unfocused-window FEELS right (tauri#11605/#10767):** build + run the app (set `primary_surface = "pill"` once 62-02 lands, or temporarily force-create the pill in setup for this spike); with a DJ app focused, grab the pill's top strip and drag — it should follow the cursor smoothly on the FIRST grab, no focus flash, no "drag twice" bug. *(Note: the drag mechanism is the already-proven `getCurrentWindow().startDragging()`; the JS handler lands with the pill UI in a later 62 plan.)*
2. **Focus non-steal (PILL-04):** focus a text field in the DJ app (or Notes), CLICK the pill, then TYPE — keystrokes must land in the DJ app, not vibemix. Report which tier is in effect: **Accessory floor** (first click may transfer focus — note it) vs **NSPanel stretch** (no transfer at all). This confirms whether the swizzle worked at runtime.
3. **Transparency parity on the `.dmg` (tauri#13415, out of THIS plan's scope — 62-04 owns the rgba surface):** when the pill UI lands, build the `.dmg` (not `tauri dev`) and confirm the pill renders as a floating dark-glass lozenge over the desktop, not a white box.
4. **Multi-monitor feel:** with the pill on an external display, unplug it — the pill should re-clamp back onto the remaining visible work area (the `ScaleFactorChanged` re-clamp; the math is cargo-tested via `clamp_to_work_area_keeps_visible`, the felt unplug is live-only).

## Self-Check: PASSED
- `tauri/src-tauri/src/pill_window.rs` — FOUND
- Commit `0d4458f` (Task 1) — FOUND
- Commit `22087b5` (Task 2) — FOUND
- Commit `7a2772a` (Task 3) — FOUND
- `cargo build` green, `cargo test` 59/59, `grep -c set_ignore_cursor_events pill_window.rs` == 0, `grep -c tauri-nspanel Cargo.toml` == 0, `pill` in capabilities windows array — all verified.

## Next Phase Readiness
- **62-02** (`primary_surface` switch): can now wire `pill_window::create_pill_window` into the main.rs setup branch and add the config.rs `KEY_PRIMARY_SURFACE` enum. `create_pill_window` is `pub` and returns `Result<Option<WebviewWindow>>` (non-fatal). Removing the transient `#![allow(dead_code)]` happens naturally once the fn is called.
- **62-04/62-05** (pill UI + deck chips): the `pill.html` entry the builder references (`WebviewUrl::App("pill.html")`) does not exist yet — must land before the window renders content. The window flags + drag capability are ready.
- **Blocker/concern:** none for engineering. The felt drag + focus-non-steal results are the KAAN-ACTION carve-out (recorded above, not blocking).

---
*Phase: 62-floating-pill-ui*
*Completed: 2026-05-22*
