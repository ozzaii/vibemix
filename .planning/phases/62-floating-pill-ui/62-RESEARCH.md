# Phase 62: Floating Pill UI — Research

**Researched:** 2026-05-21
**Domain:** Tauri v2 always-on-top transparent overlay window (macOS NSPanel non-activating + drag-on-unfocused + transparency parity) + vanilla-TS overlay UI consuming an existing localhost WebSocket bus
**Confidence:** HIGH on codebase reuse + wire shapes; MEDIUM-HIGH on the Tauri-v2 spike (the focus-non-steal mechanism has a load-bearing platform caveat verified below); the felt behaviors are KAAN-ACTION live-confirms by design.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Area 1 — Window mechanics + drag/focus/transparency spike (PILL-01, PILL-04)**
- Clone, don't fork-in-place: new `tauri/src-tauri/src/pill_window.rs` modeled on `mascot_window.rs` — reuse geometry-persist + 200ms debounce + "label constant matches capability allowlist" pattern. Keep the mascot file intact.
- NOT click-through: the pill is interactive (draggable + clickable) → MUST NOT call `set_ignore_cursor_events(true)`.
- Focus non-steal (PILL-04): macOS → build the pill as a non-activating NSPanel (`NSWindowStyleMaskNonactivatingPanel`) + `.focused(false)` at build, so clicking the pill never activates vibemix / never pulls keyboard focus off the DJ app. Verify keystrokes still reach the DJ app after a click (live = KAAN-ACTION).
- Drag mechanism: `data-tauri-drag-region` alone is unreliable on unfocused/non-activating windows (tauri#11605/#10767) → primary mechanism is explicit JS `getCurrentWindow().startDragging()` on `mousedown` over the drag handle; `data-tauri-drag-region` kept as progressive enhancement. Winning combination resolved on the BUILT app (research-flagged spike — resolve FIRST in plan-time; felt confirm = KAAN-ACTION).
- Transparency parity: `transparent(true)` + `decorations(false)`, but the pill's visible surface uses an explicit CSS `--glass-*` rgba fallback, NOT pure OS vibrancy — guarantees mac+win parity (no opaque white box on Windows) and dodges the DMG-build transparency regression (tauri#13415). Verify on the built `.dmg` (KAAN-ACTION).
- Multi-monitor: clamp-to-visible on display change; persist x/y/w/h exactly like the mascot.
- Capability allowlist (closes v0.1.0-rc1 drag debt): add a `"pill"` capability/allowlist entry (the pill window label) covering `window:allow-start-dragging` + the IPC the pill needs, mirroring the mascot allowlist.

**Area 2 — `primary_surface` tri-state config (PILL-02)**
- New top-level config key in `config.rs`: `primary_surface ∈ { "pill" (default) | "mascot" (opt-in/secondary) | "none" }`, alongside the existing `mascot_window` state key.
- Default `"pill"` — the deliberate, Kaan-approved partial reversal of the shipped full-screen-mascot direction for the in-set surface. Mascot stays opt-in/secondary, NOT retired — `mascot-audit` CI fence must stay green.
- Surface selection takes effect on session start (config write → which window is created); no live hot-swap required for v1.
- Legacy/missing config decodes to the `"pill"` default (mirror the mascot's `decodes_legacy_missing_fields_as_defaults` pattern).

**Area 3 — Pill states, content + visual register (PILL-03)**
- Consume EXISTING frames: reuse the mascot's `ws_client` path on `ws://127.0.0.1:8765` (`ipc.session.snapshot` + `ipc.session.cohost-reaction`). NO new port, NO Python delivery change.
- States: `idle` / `listening` / `speaking` / `expand-on-event`. Expand shows reaction text + citation strip + deck-context chips, then collapses back to the compact pill.
- Real TTS waveform: driven by `Levels.update_voice` (AI-speech RMS already on the bus) during `speaking` — not a fake animation.
- Citation strip: the existing EvidenceRegistry chip strip (the same `[key:…]`/`[ev:…]` grounded chips).
- Deck-context chips: Phase 59 deck-state is COMPLETE → deck chips land here — title/key/BPM per resolved deck, honest `unknown` when unresolved.
- Visual register: CDJ-Whisper / Super-Whisper — 5 warm blacks, single amber accent at 20/80, Saira + JetBrains Mono, tactility via faint glow not faux-3D bevels (`frontend-enforcement` skill governs; baseline `mocks/vibemix-direction-final.html`). Compact pill, no AI-slop copy.

**Area 4 — Scope boundaries**
- IN: pill window + 4 states + TTS waveform + citation strip + deck chips + `primary_surface` config + `"pill"` capability allowlist + drag/focus/transparency engineering + multi-monitor clamp.
- KAAN-ACTION (felt, on the built app): drag-on-unfocused-window feel, focus non-steal, transparency parity on the `.dmg`, multi-monitor behavior. Surface, do not pause (`gsd-autonomous fully`).
- OUT (no scope creep): notch-locked pill, any new ws port, any Python delivery change, retiring/deleting the mascot, new AI providers.

### Claude's Discretion
- Exact pill dimensions, collapse/expand animation curve, drag-handle placement, the precise glass rgba stack — bounded by the CDJ-Whisper register + `frontend-enforcement` skill. (NOTE: the UI-SPEC has since LOCKED most of these: 280×44 collapsed, 280×auto-≤220 expanded, `--rad-lg`, top-28px drag strip, 200ms expand. Treat UI-SPEC values as authoritative.)
- Internal module layout of `pill_window.rs` vs shared helpers extracted from `mascot_window.rs`.

### Deferred Ideas (OUT OF SCOPE)
- Live hot-swap between pill ↔ mascot mid-session (v1 applies surface choice at session start).
- Notch-locked / menubar-docked pill variants.
- Pill-driven controls that send commands back to Python (one-way consume only for v1).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PILL-01 | A small, always-on-top, transparent, draggable Super-Whisper pill, positionable anywhere + multi-monitor safe. | Clone `mascot_window.rs` builder (transparent/on-top/decorations(false)/skip_taskbar). Drag via `getCurrentWindow().startDragging()` (already proven in `mascot/index.ts`). Multi-monitor clamp via `available_monitors()` + `Monitor::work_area()` (Tauri v2 verified) + the mascot's existing off-screen-fallback math. |
| PILL-02 | Pill = primary surface via tri-state `primary_surface` config; mascot keeps working (`mascot-audit` green). | New `KEY_PRIMARY_SURFACE` in `config.rs`, serde enum w/ `#[serde(default)]`, legacy-decode test mirroring `mascot_window_state_decodes_legacy_missing_fields_as_defaults`. Setup branch in `main.rs` chooses surface. `mascot-audit` fence path-scoped (verified) — pill dir does not trip it. |
| PILL-03 | Pill consumes existing ws:8765 frames; idle/listening/speaking/expand states + real TTS waveform (`Levels.update_voice`) + citation strip + deck chips. | Reuse `connectMascotBus()` pattern (direct WS) OR `ws-bridge.ts` (Rust→event). `cohost_status` enum {IDLE,LISTENING,TALKING} → states (verified in schema). `voice.rms` drives waveform (reuse `meter.ts` segmented-LED CSS). `renderCitationStrip()` reused verbatim. Deck chips from Phase-59 snapshot fields. |
| PILL-04 | Pill never steals keyboard focus mid-set; drag-on-unfocused resolved (spike); mac+win transparency parity; closes drag-capability debt. | **LOAD-BEARING CAVEAT (verified below): `NSWindowStyleMaskNonactivatingPanel` only takes effect on an `NSPanel`, NOT a plain `NSWindow` — which is what a Tauri `WebviewWindow` is.** See "The Load-Bearing Spike" for the two viable paths + the recommended one. Transparency parity via explicit `--glass-3` rgba (UI-SPEC §Color). `"pill"` capability entry. |
</phase_requirements>

## Summary

Phase 62 is an **integration / clone phase**, not greenfield in spirit: nearly every moving part already exists in the tree and the task is to instantiate a third overlay window (`pill`) modeled on the second (`mascot`), wire a tri-state config switch, and render four states from frames already on the bus. The drag mechanism, the direct-WS subscription, the segmented-LED waveform, the citation chip strip, the geometry-persist/debounce/off-screen-fallback, and the transparent-overlay HTML invariant are **all already shipped** — the pill reuses them. The new code is: one Rust window builder, one config key, one capabilities entry, the macOS focus-non-steal interop, the four-state TS surface, and the multi-monitor clamp-on-display-change refinement.

The single highest-risk item — and the one the ROADMAP flags "resolve FIRST" — is **focus non-steal on macOS**. Research surfaced a load-bearing platform fact that the CONTEXT decision under-specifies: **`NSWindowStyleMaskNonactivatingPanel` is a no-op on a regular `NSWindow`; it only changes behavior on an `NSPanel` subclass.** A Tauri `WebviewWindow` is created as an `NSWindow` (not an `NSPanel`). So "set the non-activating style mask via `with_webview`/`ns_window()`" — as worded in the spike — will compile, will not error, and will **silently not work**. There are two real paths to genuine non-activating behavior; the recommendation below picks the one that respects vibemix's one-click-install / dependency-discipline constraint and degrades honestly.

The other two spike legs are lower-risk: the **drag-on-unfocused-window** problem is already solved in this codebase (the mascot uses `getCurrentWindow().startDragging()` on `mousedown`, exactly the pattern CONTEXT prescribes, and the `core:window:allow-start-dragging` permission is already granted in `capabilities/default.json`), and the **transparency parity** problem is handled by the UI-SPEC's explicit-rgba decision (the pill paints its own `rgba(2,3,6,0.88)` surface, never relying on OS vibrancy). The DMG transparency regression (tauri#13415) is **open with no upstream fix** and can only be confirmed on the built `.dmg` — that is a genuine KAAN-ACTION live-confirm.

**Primary recommendation:** Clone `mascot_window.rs` → `pill_window.rs` and reuse 90% of its body verbatim (drop only the `set_ignore_cursor_events` block; keep geometry-persist + 200ms debounce + off-screen fallback + the label↔capability test). For focus-non-steal, use the **in-tree `objc2-app-kit` path** (apply `NSWindowCollectionBehavior` + set `ActivationPolicy::Accessory` app-wide-or-effectively, and apply the non-activating panel mask **after** converting the window to an `NSPanel` via class-swizzle) — **OR**, the lower-effort honest fallback: ship the pill as a plain transparent always-on-top `NSWindow` with `.focused(false)` and `set_activation_policy(Accessory)`, accept that the first click may transfer focus, and mark "true non-activating" as a follow-up. Given the dependency constraint (`tauri-nspanel` is git-only, not on crates.io), the plan should treat the full NSPanel conversion as a **bounded spike task with an honest fallback**, not a guaranteed deliverable — and surface the felt result as KAAN-ACTION. Everything else (config, capability, four states, waveform, citation strip, deck chips, multi-monitor clamp) is straightforward reuse.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Window creation / transparency / always-on-top / drag-capability | Rust backend (`pill_window.rs` + `tauri.conf.json5` + `capabilities/default.json`) | — | Window lifecycle and OS-window flags are owned by the Tauri host process; the webview only requests dragging via an IPC command the capability must allow. |
| Focus non-steal (NSPanel / activation policy) | Rust backend (macOS objc2 interop in `pill_window.rs`, `#[cfg(target_os="macos")]`) | — | Pure native-window concern; the webview cannot influence NSWindow class or activation policy. |
| `primary_surface` persistence + surface selection | Rust backend (`config.rs` key + `main.rs` setup branch) | — | Config lives in `tauri-plugin-store` (`config.json`); which window is created at startup is a host decision. |
| Frame transport (ws:8765 → UI) | Rust backend (`ws_client.rs`, already shipped) **or** webview direct-WS (`connectMascotBus`, already shipped) | Browser/webview | One-socket invariant: Python sidecar is the single writer; the pill is a pure consumer. No new transport. |
| Pill state machine + rendering (4 states) | Browser/webview (vanilla TS under `tauri/ui/src/pill/`) | — | DOM/CSS render of frames is a client concern; mirrors the mascot's reader/writer discipline (snapshots = readers, events = writers). |
| TTS waveform / citation strip / deck chips | Browser/webview (reuse `meter.ts`, `citation-strip.ts`) | — | Pure presentation of wire data already on the snapshot/reaction frames. |
| Multi-monitor clamp-to-visible | Rust backend (display-change listener + clamp math) | Browser/webview (none) | Monitor enumeration + position clamping are `WebviewWindow`/`Monitor` APIs on the host side. |

## Standard Stack

This phase adds **no new runtime npm dependency** and **at most one new Rust dependency** (`objc2-app-kit`, only if the full NSPanel path is taken). It is overwhelmingly reuse of the locked stack.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tauri` | 2.11.1 (locked in `Cargo.lock`) | Window builder, `with_webview`, monitor APIs, capability ACL | Already the app's runtime; `macos-private-api` feature already enabled (required for transparency). [VERIFIED: codebase `Cargo.toml`/`Cargo.lock`] |
| `@tauri-apps/api` | ^2.11 | `getCurrentWindow().startDragging()` + monitor JS APIs | Already a devDep; the mascot already imports `@tauri-apps/api/window` for drag. [VERIFIED: codebase `tauri/ui/package.json`] |
| `tauri-plugin-store` | 2.4 | `config.json` persistence for `primary_surface` | Already wired for `mascot_window` + `first_run_state`. [VERIFIED: codebase] |
| `three` | ^0.170 | (mascot only — pill uses NONE of it) | The pill is DOM/CSS; Three.js stays mascot-scoped. [VERIFIED: codebase] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `objc2-app-kit` | latest 0.x (verify at plan time) | Apply `NSWindow`→`NSPanel` swizzle + non-activating style mask + collection behavior + `ActivationPolicy` on macOS | ONLY if the plan takes the full non-activating-panel path. Tauri's own `with_webview`/`ns_window()` returns a pointer castable to `objc2_app_kit::NSWindow`. [CITED: docs.rs/tauri WebviewWindow.with_webview; ASSUMED for exact objc2-app-kit version] |
| `tauri-nspanel` | git `v2.1` branch, NOT on crates.io | Turn-key panel conversion (`PanelBuilder`, `get_webview_panel`) | **DISCOURAGED for vibemix** — git-only dependency conflicts with the dependency-discipline / reproducible-build constraint, and its own docs note it still requires a click-to-focus and "doesn't prevent focus stealing" in some configs. Documented here only as the ecosystem-standard reference. [VERIFIED: github.com/ahkohd/tauri-nspanel — 398★, default branch `v2.1`, last push 2026-05-06; NOT published to crates.io] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Full NSPanel non-activating conversion (objc2 swizzle) | Plain `NSWindow` + `set_activation_policy(Accessory)` + `.focused(false)` | Accessory policy keeps the app off the Dock/menubar and reduces (but does not guarantee) focus theft; first-click may still transfer focus. Far less code, no new dep, honest fallback. **Recommended as the floor; NSPanel as the bounded stretch.** |
| `tauri-nspanel` (git) | In-tree objc2-app-kit interop | In-tree keeps the dep graph crates.io-only (reproducible builds, one-click-install discipline) and matches the codebase's own stated fallback plan (`mascot_window.rs` line 56 already documents "the manual ObjC override goes here"). |
| Direct webview WS (`connectMascotBus`) | Rust→event bridge (`ws_client.rs` → `ws-bridge.ts`) | Mascot uses direct-WS so it survives main-window hide (CONTEXT.md Area 6 rationale). The pill, as the PRIMARY surface, has the same lifecycle independence need → **reuse the direct-WS pattern** (`connectMascotBus`). The Rust bridge already dashes `ipc.session.snapshot`→`ipc-session-snapshot`; the pill avoids that re-mapping by reading the raw frame directly. |

**Installation:**
```bash
# No npm install needed — the pill uses zero new runtime deps.
# IF (and only if) the plan takes the full NSPanel path, add to tauri/src-tauri/Cargo.toml:
#   objc2-app-kit = "<verify-version>"   # macOS-only target
# Verify before adding:
cargo search objc2-app-kit
```

**Version verification (run at plan time):**
```bash
cargo search objc2-app-kit          # confirm current 0.x and that it is on crates.io
# tauri 2.11.1 already locked; @tauri-apps/api ^2.11 already present.
```

## Package Legitimacy Audit

This phase adds **no npm package** and at most one Rust crate. `slopcheck` targets npm/PyPI; the one candidate Rust crate is verified directly against crates.io / the objc2 project (madsmtm), a well-known maintained binding set.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `objc2-app-kit` | crates.io | mature (objc2 ecosystem, madsmtm) | high (transitive in most macOS Rust apps) | github.com/madsmtm/objc2 | n/a (Rust; not npm/PyPI) | Approved IF full-NSPanel path taken; verify exact version with `cargo search` at plan time |
| `tauri-nspanel` | **git only (NOT crates.io)** | active (398★, push 2026-05-06) | n/a | github.com/ahkohd/tauri-nspanel | n/a | **REMOVED** from recommendation — git-only dep violates reproducible-build/one-click-install discipline. Documented as reference only. |

**Packages removed due to legitimacy/policy verdict:** `tauri-nspanel` (git-only; dependency-discipline conflict — not a slop verdict, a policy verdict).
**Packages flagged suspicious:** none.

*slopcheck was not run (no npm/PyPI packages in scope). The single Rust crate is part of the canonical objc2 binding set and is verified against crates.io directly at plan time via `cargo search`.*

## The Load-Bearing Spike — Drag + Focus-Non-Steal + Transparency Parity

> This is the section the planner should read first. Resolve these BEFORE building the UI (per ROADMAP "resolve FIRST"). Each leg is tagged with its confidence and what is plan-time vs KAAN-ACTION.

### Leg A — Focus non-steal (macOS) — **HIGHEST RISK; has a verified caveat**

**The trap (verified):** `NSWindowStyleMaskNonactivatingPanel` (objc2: `NSWindowStyleMask::NonactivatingPanel`) **only changes behavior when the window is an `NSPanel`** (or subclass). A regular `NSWindow` ignores it. A Tauri `WebviewWindow` is created as an `NSWindow`, not an `NSPanel`. Setting the mask via `with_webview`/`ns_window()` compiles and runs but is a **silent no-op** for focus behavior. [VERIFIED: Apple docs `nonactivatingPanel` "a window that is a panel or subclass thereof that does not activate the owning app"; CITED: electron#35815 "NSWindow does not support nonactivating panel styleMask"; CITED: tauri community answer in discussion #9876 — "they use NSPanels instead of regular windows"]

**Why this matters for the plan:** the CONTEXT decision text ("build the pill as a non-activating NSPanel (`NSWindowStyleMaskNonactivatingPanel`) + `.focused(false)`") describes the *intent* correctly but the *mechanism* needs a class conversion (NSWindow→NSPanel), which Tauri does not expose natively. The plan must NOT assume "set the style mask in a `with_webview` closure" is sufficient.

**Two viable paths:**

1. **Floor (recommended baseline — in-tree, no new dep, honest):**
   - Build the pill window with `.focused(false)` on the `WebviewWindowBuilder` (Tauri v2 builder flag).
   - Call `app.set_activation_policy(tauri::ActivationPolicy::Accessory)` (or set it for the pill-primary mode) so vibemix behaves like a background/accessory app (no Dock bounce, no menubar takeover) — reduces the perceived "focus stolen" feel.
   - Apply `NSWindowCollectionBehavior` (canJoinAllSpaces) via objc2 if cross-Space float is wanted (the mascot already gets this from `visible_on_all_workspaces(true)` builder flag — reuse that flag, no objc2 needed for Spaces).
   - **Known limitation to document:** the first click on a non-activating *NSWindow* may still transfer key-window status (wry#637 "First click if the window is not focused don't get propagated to the webview"; tauri#14102 "`focusable:false` seems broken on macOS", **open, no fix as of 2.8.4**). Accept this for v1; surface as KAAN-ACTION.

2. **Stretch (true non-activating — bounded spike task, objc2 in-tree):**
   - In a `#[cfg(target_os="macos")]` `with_webview` closure, get `ns_window()` (castable to `objc2_app_kit::NSWindow`).
   - Convert the underlying class to `NSPanel` (the technique `tauri-nspanel` uses — `object_setClass` / class swizzle to a panel subclass), then set `styleMask |= NonactivatingPanel`, set `setFloatingPanel(true)`, `setBecomesKeyOnlyIfNeeded(true)`, and `setLevel(NSStatusWindowLevel)` as needed.
   - This is the only path to *genuine* "click the pill, keystrokes still go to the DJ app". It is the same code `tauri-nspanel` ships — but written in-tree so the dep stays crates.io-only.
   - **Mark this as a spike task with a time box and the Floor as the documented fallback.** If it doesn't land cleanly, ship the Floor and log the stretch as a follow-up. (`gsd-autonomous fully`: defer, don't pause.)

**Verification (KAAN-ACTION, live on built app):** focus a text field in the DJ app (or a notes window), click the pill, type — keystrokes must still land in the DJ app. This cannot be unit-tested; it is the felt confirmation the spike is about.

**Confidence:** the *caveat* is HIGH (multiple corroborating sources). The *which-path-lands* is MEDIUM until tried on the built app — hence the bounded-spike framing.

### Leg B — Drag on an unfocused window — **LOW RISK; already solved in this codebase**

`data-tauri-drag-region` alone is unreliable on non-activating/unfocused windows: dragging first focuses the window and doesn't move it (you must drag twice). [VERIFIED: tauri#11605 "can't drag a `data-tauri-drag-region` element when the window is not focused"; the docs themselves recommend `window.startDragging()` for custom drag behavior]

**The working pattern is already in the tree** — `tauri/ui/src/mascot/index.ts` lines 139-163:
```ts
// Source: tauri/ui/src/mascot/index.ts (shipped, working)
const mod = await import("@tauri-apps/api/window");
const tauriWin = mod.getCurrentWindow();
document.addEventListener("mousedown", (ev) => {
  const me = ev as MouseEvent;
  if (me.button !== 0) return;                 // left-click only
  const target = me.target as HTMLElement | null;
  if (target?.closest("[data-no-drag]")) return;   // exempt chips/buttons
  // Don't preventDefault — let the webview see the click.
  tauriWin.startDragging().catch((e: unknown) =>
    console.warn("startDragging() rejected:", e),
  );
});
```
For the pill, scope the listener to the **top 28px drag strip** (UI-SPEC) rather than the whole document, and tag the citation chips / future controls `[data-no-drag]` so a chip click doesn't start a drag.

**Capability:** `core:window:allow-start-dragging` is **already granted** in `capabilities/default.json` (line 9). The pill's window label must be added to the `"windows"` array of that capability for the permission to apply to the pill window. [VERIFIED: codebase `capabilities/default.json` line 9 + the `"windows": ["main","mascot","overlay-*","debrief"]` scope on line 5]

**Confidence:** HIGH — proven pattern, permission already present.

### Leg C — Transparency parity + DMG regression — **LOW RISK in dev; the DMG check is genuine KAAN-ACTION**

- Window flags: `transparent(true)` + `decorations(false)` (mascot already does both). `macOSPrivateApi: true` is already set in `tauri.conf.json5` (required for transparency). [VERIFIED: codebase]
- **The visible surface is painted by CSS, not the OS.** Per UI-SPEC §Color, the pill uses an explicit `--glass-3` = `rgba(2,3,6,0.88)` fill (near-opaque dark glass). `backdrop-filter: var(--blur-glass)` is a *progressive enhancement layered on top*, never the sole opacity source. This guarantees mac+win parity (Windows has no NSVisualEffectView vibrancy → relying on it yields an opaque white box).
- **Mandatory HTML invariant** (reuse mascot.html / overlay.html pattern): the pill's HTML must force
  ```html
  html, body { background: transparent !important; background-image: none !important; }
  body::before { display: none !important; }   /* kill the tokens.css film-grain over the desktop */
  ```
  Without this, `tokens.css` paints a global dark vignette + film-grain that opaque-out the overlay. [VERIFIED: codebase mascot.html lines 56-82]
- **DMG regression (tauri#13415):** `.transparent(true)` windows can render **solid white after DMG bundling** even though they're transparent in `tauri dev`. The issue is **OPEN with no confirmed upstream fix** (affected 2.5.1; not resolved through 2.11.x as of research). The explicit-rgba decision *mitigates* the felt impact (the pill paints its own dark surface regardless), but full transparency of the window *chrome* around the rgba rectangle can only be confirmed on the built `.dmg`. [VERIFIED: github.com/tauri-apps/tauri#13415 — open, no fix]
  - **KAAN-ACTION:** build the `.dmg`, run it (not `tauri dev`), confirm the pill renders as a floating dark-glass lozenge over the desktop, not a white box. If white-box reproduces, the rgba surface still reads correctly but document the chrome edge.

**Confidence:** HIGH that the rgba approach is the right call; the DMG-build verdict is genuinely unknowable without the build → KAAN-ACTION.

### Leg D — Multi-monitor clamp-to-visible — **LOW RISK; APIs verified**

Tauri v2 `WebviewWindow` exposes (all verified at docs.rs/tauri/latest):
- `available_monitors() -> Result<Vec<Monitor>>`
- `current_monitor() -> Result<Option<Monitor>>`
- `primary_monitor() -> Result<Option<Monitor>>`
- `monitor_from_point(x, y) -> Result<Option<Monitor>>`
- `outer_position() -> Result<PhysicalPosition<i32>>`, `set_position(pos)`, `scale_factor()`
- `Monitor` exposes `name()`, `size()`, `position()`, `scale_factor()`, and **`work_area()`** (the visible region excluding menubar/dock — use this, not raw `size()`, for clamping). [CITED: docs.rs/tauri WebviewWindow + Monitor; ASSUMED `work_area()` field name pending plan-time confirm — the mascot currently clamps with `size()/scale_factor`, which is a usable fallback if `work_area()` differs by version]

**Reuse the mascot's existing off-screen fallback** (`mascot_window.rs` lines 88-99: if the persisted origin lands off the primary monitor's logical bounds, snap back to `default_top_right`). **Add for the pill** a `WindowEvent`-driven re-clamp when the monitor topology changes (display unplugged / resolution change) — on such an event, recompute against `current_monitor().work_area()` and `set_position` if off-screen. This is the one *new* behavior beyond a straight clone.

**Confidence:** HIGH on APIs; the display-change event hook is the small new piece.

## Architecture Patterns

### System Architecture Diagram

```
                    Python sidecar (vibemix.runtime.ws_bus)
                    SINGLE WRITER · one socket · ws://127.0.0.1:8765
                              │  (broadcasts JSON frames @ ~30Hz)
                              │   ipc.session.snapshot  {meters.voice.rms, cohost_status,
                              │                           track{title,deck}, bpm, key, deck_state}
                              │   ipc.session.cohost-reaction {text, event_id, citation_strip[]}
                              ▼
        ┌─────────────────────────────────────────────────────────┐
        │  TWO consumer paths (both already exist — pick direct-WS) │
        │                                                           │
        │  (a) Rust ws_client.rs ──emit("ipc-session-snapshot")──► main window
        │      (dots in event name; main session UI uses this)      │
        │                                                           │
        │  (b) Direct webview WS  ◄── PILL USES THIS (like mascot)  │
        │      connectMascotBus("ws://127.0.0.1:8765")              │
        │      survives main-window hide; raw frame, no re-map       │
        └───────────────────────────────┬──────────────────────────┘
                                         ▼
                       ┌──────────────────────────────────┐
                       │  pill webview  (tauri/ui/pill.html)│
                       │  transparent · always-on-top ·     │
                       │  NSPanel/Accessory · drag-handle    │
                       │                                     │
                       │  state machine (snapshots=readers,  │
                       │  events=writers — mascot discipline)│
                       │   IDLE ─► LISTENING ─► SPEAKING      │
                       │            └─ expand-on-event ─┘     │
                       │                                     │
                       │  renders:                           │
                       │   • state dot + label (silkscreen)  │
                       │   • TTS waveform  ◄ meter.ts CSS     │
                       │       driven by voice.rms           │
                       │   • citation strip ◄ citation-strip.ts (verbatim)
                       │   • deck chips ◄ deck_state (Phase 59)
                       └──────────────────┬──────────────────┘
                                          │  on mousedown over top 28px:
                                          ▼
                            getCurrentWindow().startDragging()
                            (capability core:window:allow-start-dragging,
                             window label "pill" in capabilities/default.json)

   Surface selection (startup):
     config.json primary_surface ∈ {pill(default)|mascot|none}
        └─ main.rs setup() reads it ─► creates pill_window OR mascot_window OR neither
           mascot stays buildable on demand (opt-in/secondary) — mascot-audit green
```

### Recommended Project Structure
```
tauri/
├── src-tauri/src/
│   ├── pill_window.rs        # NEW — clone of mascot_window.rs (drop set_ignore_cursor_events);
│   │                         #       + macOS focus-non-steal interop (#[cfg(target_os="macos")]);
│   │                         #       + display-change re-clamp listener
│   ├── config.rs             # EDIT — add KEY_PRIMARY_SURFACE + PrimarySurface enum + load/save + tests
│   ├── main.rs               # EDIT — `mod pill_window;`; setup() branches on primary_surface
│   └── ws_client.rs          # UNCHANGED (pill uses direct-WS like mascot)
├── src-tauri/capabilities/
│   └── default.json          # EDIT — add "pill" to "windows": [...]  (start-dragging already granted)
├── src-tauri/tauri.conf.json5# EDIT (optional) — pill is built at runtime like mascot; no static window entry needed
└── ui/
    ├── pill.html             # NEW — transparent-overlay invariant (clone mascot.html head)
    └── src/pill/             # NEW — vanilla TS, mirrors src/mascot/ discipline
        ├── index.ts          # boot: connectMascotBus + drag handler + rAF/state loop
        ├── state-machine.ts  # pure: cohost_status + reaction → {idle|listening|speaking|expand}
        ├── waveform.ts        # reuse meter.ts segmented-LED CSS for voice.rms bars
        ├── deck-chips.ts      # deck_state → "a · 8a · 128" chips, honest unknown
        └── *.test.ts         # vitest (jsdom) — state machine, frame→state map, clamp math
```
> NOTE: place pill code under `tauri/ui/src/pill/` (NOT `tauri/ui/src/mascot/`) so the `mascot-audit` CI fence (path-scoped to `tauri/ui/src/mascot/**`) does not trip on pill changes. The pill must NOT reference `mascot.html` anywhere (the `mascot-tauri-only-grep` gate fails if `mascot.html` appears in tests/e2e/scripts/ci).

### Pattern 1: Clone-with-subtraction (window builder)
**What:** `pill_window.rs` is `mascot_window.rs` with three deltas: (1) label `"pill"`, (2) DROP the `if state.click_through { set_ignore_cursor_events(true) }` block (the pill is interactive), (3) ADD `#[cfg(target_os="macos")]` focus-non-steal interop after `.build()`.
**When to use:** any time a new overlay window is needed; this is the third (`mascot`, `debrief`, now `pill`).
**Example:**
```rust
// Source: derived from tauri/src-tauri/src/mascot_window.rs (shipped)
pub const PILL_WINDOW_LABEL: &str = "pill";

let window = WebviewWindowBuilder::new(app, PILL_WINDOW_LABEL, WebviewUrl::App("pill.html".into()))
    .title("vibemix")
    .transparent(true)
    .always_on_top(true)
    .decorations(false)
    .resizable(false)              // pill is fixed-size (expand is CSS height, not window resize)
    .skip_taskbar(true)
    .visible_on_all_workspaces(true)
    .focused(false)                // request non-activating (see Leg A caveat)
    .inner_size(280.0, 44.0)       // UI-SPEC collapsed; expand grows via CSS, not window
    .position(x, y)
    .visible(true)
    .build()?;
// DO NOT call window.set_ignore_cursor_events(true) — the pill is interactive.

#[cfg(target_os = "macos")]
apply_nonactivating(&window);      // Leg A — see The Load-Bearing Spike
```

### Pattern 2: Snapshots are readers, events are writers (state machine)
**What:** `ipc.session.snapshot` frames update a *current view* (cohost_status, voice.rms, track/deck) but do NOT themselves drive a transition; `ipc.session.cohost-reaction` is the *event* that drives `expand-on-event`. Mirrors the mascot's documented discipline.
**When to use:** the pill state machine.
**Example:**
```ts
// Source: pattern from tauri/ui/src/mascot/index.ts handleMessage()
function handleFrame(msg: any) {
  if (msg?.type === "snapshot") {            // READER
    view.cohostStatus = msg.cohost_status ?? view.cohostStatus;   // IDLE|LISTENING|TALKING
    view.voiceRms = typeof msg.voice === "number" ? msg.voice : view.voiceRms;
    // ...track/deck/bpm/key
    return;                                  // no transition
  }
  if (msg?.type === "cohost-reaction" || msg?.type === "ipc.session.cohost-reaction") {
    expandWith(msg.text, msg.citation_strip ?? []);   // WRITER → expand-on-event
  }
}
// state derives purely: TALKING→speaking, LISTENING→listening, else idle; reaction→expand (6s) then back.
```
> WIRE NUANCE (verified): on the **rich Rust-bridged** `ipc.session.snapshot`, voice RMS is nested `meters.voice.rms`. On the **direct live WS frame** the mascot reads, `voice` arrives as a **flat top-level float** (mascot/index.ts lines 205-217, "LIVE-05a: music/voice arrive as FLAT floats"). Since the pill uses direct-WS, read `msg.voice` flat — but defensively also check `msg.meters?.voice?.rms` so it works against either shape.

### Pattern 3: Reuse the segmented-LED meter for the TTS waveform
**What:** the UI-SPEC says the waveform uses "the SAME visual language as the session meter — reuse, do not invent." `meter.ts` exposes `renderMeter()` + `setMeterLevels(el, {rms, peak})` with the amber-zone segmented ladder + 1.2s peak decay, all token-driven.
**When to use:** the `speaking` state waveform.
**Example:**
```ts
// Source: tauri/ui/src/session/components/meter.ts (shipped)
import { renderMeter, setMeterLevels } from "../session/components/meter.js";
const wf = renderMeter({ label: "voice" });          // reuses the LED ladder CSS
// per snapshot frame during speaking:
setMeterLevels(wf, { rms: view.voiceRms, peak: view.voicePeak ?? null });
```
> The UI-SPEC describes 12-16 *horizontal* bars; `meter.ts` is a *vertical* 16-segment strip. The amber gradient + `.m-fill` comb overlay tokens are reusable verbatim; the bar *orientation/count* is the pill-specific styling delta. Reuse the CSS tokens + the data-lit-count update pattern (single attribute write, zero DOM churn), restyle the geometry.

### Pattern 4: Citation strip — reuse verbatim
**What:** `renderCitationStrip({chips, onChipClick})` already returns the exact `[<verb> @ mm:ss]` amber chip strip from `citation_strip[]`, with resting-glow-off / hover-glow discipline and `null` on empty. Import and use as-is in the expand panel.
**Example:**
```ts
// Source: tauri/ui/src/session/components/citation-strip.ts (shipped)
import { renderCitationStrip } from "../session/components/citation-strip.js";
const strip = renderCitationStrip({
  chips: reaction.citation_strip,           // {event_id, verb, timestamp_s}[]
  onChipClick: (chip) => { /* v1: no-op or open_debrief_window deep-link */ },
});
if (strip) expandPanel.append(strip);       // returns null when empty — no hanging div
```
> The chips MUST come from registry-observed evidence (the backend already builds `citation_strip` post-linter). The pill renders them as-is — it does NOT fabricate or add framing (anti-slop).

### Anti-Patterns to Avoid
- **Setting `NSWindowStyleMaskNonactivatingPanel` on the plain NSWindow and assuming focus-non-steal works.** It is a silent no-op on a non-NSPanel window (Leg A). Either convert to NSPanel or use the Accessory-policy floor and document the limitation.
- **Relying on `data-tauri-drag-region` alone** for drag on the unfocused pill (tauri#11605). Use explicit `startDragging()` (Leg B) — `data-tauri-drag-region` is progressive-enhancement only.
- **Relying on OS vibrancy / `backdrop-filter` for the surface opacity.** On Windows that's an opaque white box; in the DMG build it can white-box on macOS too (#13415). Paint an explicit `rgba` surface (Leg C).
- **Re-implementing the meter, the citation strip, the geometry-persist, or the WS client.** All four are shipped and token/contract-tested; reuse them.
- **Putting pill code under `tauri/ui/src/mascot/`** or referencing `mascot.html` — trips the `mascot-audit` path-scoped fence / the `mascot-tauri-only-grep` gate.
- **Adding a new ws port or any Python change.** Hard one-socket invariant; the pill is consume-only (deferred: pill→Python command channel).
- **Window-resize on expand.** Expand is CSS height growth inside a fixed-or-auto webview, not `set_size` (avoids a window-resize flicker + geometry-persist thrash). UI-SPEC: "expands DOWN only, no horizontal jump."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drag on transparent/unfocused window | A custom mousemove→`set_position` drag loop | `getCurrentWindow().startDragging()` (mascot pattern) | Native OS drag is jank-free, snaps to edges, handles multi-monitor; a JS drag loop fights the compositor and lags. |
| Geometry persist + debounce + off-screen fallback | New store-write logic | Clone `mascot_window.rs` `install_geometry_listener` (200ms debounce + compare-and-skip) + the off-screen snap-back | Already solves the physical/logical Retina-doubling bug + thrash; re-deriving it reintroduces those bugs. |
| TTS waveform meter | A fresh canvas/SVG waveform | `meter.ts` `renderMeter`/`setMeterLevels` tokens | Token-tested, zero-DOM-churn update, CDJ-LED aesthetic locked; a new one risks breaking the 20/80 rule + frontend-enforcement audit. |
| Citation chips | A new chip component | `renderCitationStrip` verbatim | Contract-tested (`citation-strip.test.ts`), anti-slop glow discipline baked in, `mm:ss` formatter handles >1h sets. |
| WS reconnect/backoff | A new socket client | `connectMascotBus` (1→2→4→8s backoff) | Self-healing, drops malformed frames silently (anti-slop), already lifecycle-independent of the main window. |
| Config serde + legacy decode | A bespoke parser | `tauri-plugin-store` + `#[serde(default)]` + the mascot's legacy-decode test pattern | Forward-compat (ignores unknown keys), the `_PHASE12_FIELDS` Python allowlist already preserves unknown top-level keys on round-trip. |
| macOS non-activating panel | `tauri-nspanel` git dep | In-tree `objc2-app-kit` interop (or the Accessory floor) | Keeps the dep graph crates.io-only (reproducible build / one-click-install discipline); the codebase already plans for the in-tree ObjC override. |

**Key insight:** Phase 62 is ~90% wiring of shipped, contract-tested parts. The only genuinely *new* engineering is the macOS focus-non-steal interop (one `#[cfg]` block) and the display-change re-clamp (one event hook). Everything that *looks* like new UI is a restyle of existing token-driven components. The risk is concentrated almost entirely in Leg A.

## Common Pitfalls

### Pitfall 1: NonactivatingPanel mask silently ignored on NSWindow
**What goes wrong:** You set the style mask in a `with_webview` closure, it compiles, dev looks fine, but clicking the pill still steals keyboard focus from the DJ app.
**Why it happens:** The mask only affects `NSPanel` subclasses; a Tauri window is an `NSWindow`. (Apple docs; electron#35815; tauri discussion #9876.)
**How to avoid:** Either convert the window's class to `NSPanel` (swizzle, the `tauri-nspanel` technique) and *then* set the mask, or use the Accessory-policy floor and document the residual first-click behavior.
**Warning signs:** Focus test (KAAN-ACTION) fails: type after clicking the pill and the text lands in the pill's webview / nowhere instead of the DJ app.

### Pitfall 2: Transparent window → white box in the DMG build
**What goes wrong:** Pill is transparent in `tauri dev`, ships as a solid white rectangle in the `.dmg`.
**Why it happens:** tauri#13415 (open, no fix) strips transparency during bundling for some configs.
**How to avoid:** Paint an explicit dark `rgba` surface (already the UI-SPEC decision) so the *content* reads correctly regardless; verify the *chrome edge* transparency only on the built `.dmg`.
**Warning signs:** Only reproducible on the built artifact — never in dev. → KAAN-ACTION build-and-run check.

### Pitfall 3: `data-tauri-drag-region` "drag twice" bug
**What goes wrong:** First drag focuses the pill but doesn't move it; you have to drag again.
**Why it happens:** tauri#11605 — drag-region needs the window focused first on macOS Sonoma.
**How to avoid:** Use explicit `startDragging()` on `mousedown` (mascot pattern); keep `data-tauri-drag-region` only as a fallback.
**Warning signs:** Pill "ignores" the first grab on a non-activating window.

### Pitfall 4: `tokens.css` opaque-out of the overlay
**What goes wrong:** The pill renders a full dark vignette + film grain over the whole window rect (covering the desktop), not a compact lozenge.
**Why it happens:** `tokens.css` applies a global body background + `body::before` film-grain at `:root`; an overlay webview inherits it.
**How to avoid:** Copy the mascot.html invariant (`html,body{background:transparent!important;background-image:none!important} body::before{display:none!important}`).
**Warning signs:** The transparent window shows a rectangle of texture instead of compositing over the desktop.

### Pitfall 5: Wire-shape mismatch (nested vs flat voice RMS)
**What goes wrong:** The waveform stays flat because `msg.voice` is undefined.
**Why it happens:** Bridged snapshot nests `meters.voice.rms`; the direct live WS frame the pill reads has flat `voice`.
**How to avoid:** Read `msg.voice ?? msg.meters?.voice?.rms ?? prev`. (Mascot already documents this LIVE-05a flattening.)
**Warning signs:** Waveform animates in the bridged path but is dead on the direct-WS path (or vice versa).

### Pitfall 6: Tripping the mascot-audit fence
**What goes wrong:** A pill PR fails CI on the mascot-audit workflow.
**Why it happens:** Pill code placed under `tauri/ui/src/mascot/**` (path-triggered) or `mascot.html` referenced in a pill test (the `mascot-tauri-only-grep` gate).
**How to avoid:** Pill code lives under `tauri/ui/src/pill/`; pill HTML is `pill.html`; never grep/reference `mascot.html` from pill tests.
**Warning signs:** mascot-audit job runs on a PR that didn't touch the mascot.

## Code Examples

### Reading `cohost_status` → pill state (verified enum)
```ts
// Source: tauri/ui/src/ipc/messages.schema.json (cohost_status enum: LISTENING|TALKING|IDLE)
type CohostStatus = "IDLE" | "LISTENING" | "TALKING";
function baseState(s: CohostStatus): "idle" | "listening" | "speaking" {
  return s === "TALKING" ? "speaking" : s === "LISTENING" ? "listening" : "idle";
}
```

### Deck-context chip from snapshot (Phase 59 deck_state, honest unknown)
```ts
// Source: 62-UI-SPEC §Deck-context chips + .planning/STATE.md (Phase 59 deck_state shape)
// Render "<deck> · <key> · <bpm>" e.g. "a · 8a · 128"; key amber when resolved, --silk-40 when unknown.
function deckChipText(d: { deck: string; camelot: string | null; bpm: number | null }) {
  const key = d.camelot ?? "unknown";        // NEVER fabricate a key (anti-slop)
  const bpm = d.bpm != null ? Math.round(d.bpm) : "unknown";
  return `${d.deck.toLowerCase()} · ${key.toLowerCase()} · ${bpm}`;
}
// If no deck resolves at all → single chip "decks · unknown" in --silk-40.
```

### Capability entry for the pill window (the v0.1.0-rc1 drag-debt close)
```jsonc
// Source: tauri/src-tauri/capabilities/default.json — add "pill" to the existing windows scope.
// core:window:allow-start-dragging is ALREADY in permissions (line 9) — adding the label is what
// makes it apply to the pill window.
"windows": ["main", "mascot", "overlay-*", "debrief", "pill"]
```

## Runtime State Inventory

> Phase 62 is additive (a new window + a new config key) — not a rename/refactor/migration. This section is included only to discharge the rename-check explicitly; nearly all categories are empty.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `config.json` (`tauri-plugin-store`) gains a new top-level key `primary_surface`. No existing key is renamed. Existing `mascot_window` state is untouched. | None for existing data — new key defaults to `"pill"` when absent (legacy decode). No migration. |
| Live service config | None — no external service holds pill state. | None — verified by grep (no datadog/n8n/tailscale in this repo). |
| OS-registered state | None — the pill is a runtime-created Tauri window, not an OS-registered task/service. | None. |
| Secrets/env vars | None — the pill reads no secrets; `GEMINI_API_KEY` is sidecar-only and unchanged. | None. |
| Build artifacts | The pill adds `pill.html` + `tauri/ui/src/pill/` to the Vite build and `pill_window.rs` to the Rust crate. The `.dmg`/`.app` bundle must be rebuilt to verify transparency (#13415). | Rebuild bundle for the KAAN-ACTION DMG check. No stale-artifact cleanup needed (greenfield files). |

**Nothing found in 4 of 5 categories** — verified by inspection of `config.rs`, the absence of `pill` references in the tree, and the additive nature of the change.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `data-tauri-drag-region` for custom-chrome drag | Explicit `getCurrentWindow().startDragging()` on mousedown | Tauri v2 era (docs recommend it; #11605 confirms drag-region unreliable on unfocused windows) | The pill must use the explicit API (mascot already does). |
| Hope `focused:false` / style-mask gives non-activating | NSPanel conversion (tauri-nspanel technique) OR Accessory activation policy | `focused:false` confirmed broken on macOS (#14102, open, 2.8.4); NSPanel is the community-blessed answer (#9876) | The plan must treat true non-activating as a bounded spike, not a free builder flag. |
| OS vibrancy for translucent overlays | Explicit CSS `rgba` surface + optional `backdrop-filter` enhancement | Forced by Windows parity + DMG regression (#13415) | The UI-SPEC already locks the explicit-rgba decision. |

**Deprecated/outdated:**
- Relying on `cohost.streaming.py.bak` / POC `cohost*.py` for any wire shape — those are RETIRED (2026-05-20). Use `src/vibemix/` + the `messages.schema.json` contract as ground truth.
- The CLAUDE.md auto-generated map's "Python 3.14 / no pyproject.toml / single-file cohost" block is STALE — ignore it for this phase (reality: packaged `src/vibemix/`, Python 3.12).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `objc2-app-kit` exact version is a current 0.x on crates.io | Standard Stack / Supporting | LOW — verify with `cargo search objc2-app-kit` at plan time; it is part of the canonical objc2 set. |
| A2 | `Monitor::work_area()` exists in tauri 2.11 for clamp-to-visible | Leg D | LOW — the mascot already clamps with `size()/scale_factor` as a working fallback; if `work_area()` differs, use the existing fallback math. |
| A3 | The full NSWindow→NSPanel swizzle is achievable in-tree with objc2 within the spike time-box | Leg A (stretch path) | MEDIUM — if it doesn't land, the Accessory-policy FLOOR ships and true non-activating is a documented follow-up. (`gsd-autonomous fully`: defer, don't pause.) |
| A4 | The direct-WS live frame carries the Phase-59 deck_state fields (not only the bridged snapshot) | Pattern 2 / Deck chips | MEDIUM — confirm at plan time which frame variant carries `deck_state`/`key`; if deck fields are bridge-only, the pill can use the Rust→event bridge for the deck chips specifically (still no new port). |
| A5 | `set_activation_policy(Accessory)` does not regress the main session window / tray behavior | Leg A (floor) | MEDIUM — Accessory hides the app from the Dock; verify the tray + main window still behave (the app is already tray-centric, so Accessory likely aligns, but confirm). |

## Open Questions (RESOLVED)

1. **Which focus-non-steal path lands on the built app?**
   - What we know: NonactivatingPanel needs an NSPanel; Tauri gives an NSWindow; Accessory policy is the no-dep floor; objc2 swizzle is the true-fix stretch.
   - What's unclear: whether the in-tree swizzle works cleanly with wry's NSWindow within the spike budget.
   - **RESOLVED:** Plan 62-01 ships the Accessory-policy + `focused(false)` **floor** as the real PILL-04 mechanism, with the in-tree objc2 NSPanel swizzle as a **bounded stretch** (honest fallback to the floor if it doesn't land in budget). The *felt* focus-non-steal on the built app = KAAN-ACTION live-confirm.

2. **Does the DMG build reproduce #13415 white-box?**
   - What we know: open issue, no fix; explicit rgba mitigates the content.
   - What's unclear: chrome-edge transparency on the artifact.
   - **RESOLVED:** explicit `--glass-3` rgba (Plan 62-05) mitigates the content surface; the chrome-edge transparency on the built `.dmg` = KAAN-ACTION build-and-run (document outcome). Not a blocker.

3. **Does `deck_state` ride the direct-WS frame or only the bridged snapshot?** (A4)
   - **RESOLVED:** confirmed (PATTERNS + grep) `deck_state` rides **NEITHER** frame today — it lives only in-process in `MusicState.deck_state`. Plan 62-03 adds it additively to the existing flat ws:8765 frame (no new port → honors one-socket); 62-05's deck-chips consume it. Producer (62-03, Wave 1) lands before consumer (62-05, Wave 4).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `tauri` (Rust) | window builder, monitor APIs, capabilities | ✓ | 2.11.1 (locked) | — |
| `macos-private-api` feature | transparency | ✓ (enabled in Cargo.toml + `macOSPrivateApi:true`) | — | — |
| `@tauri-apps/api` | `startDragging`, monitor JS | ✓ | ^2.11 | — |
| `tauri-plugin-store` | `primary_surface` persist | ✓ | 2.4 | — |
| `objc2-app-kit` (Rust) | full NSPanel non-activating (stretch only) | ✗ (not yet a dep) | — | Accessory-policy floor (no new dep) |
| Xcode/macOS toolchain | building the `.dmg` for the transparency KAAN-ACTION check | ✓ (Kaan's Mac, per memory) | — | — |
| `vitest` + jsdom | unit tests (state machine, clamp math, frame map) | ✓ | ^2.1 | — |
| `cargo test` | Rust config/serde + label↔capability tests | ✓ (standard toolchain) | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `objc2-app-kit` — only needed for the stretch NSPanel path; the Accessory floor needs no new dep.

## Validation Architecture

> `workflow.nyquist_validation: true` (verified in `.planning/config.json`) → this section is REQUIRED.

### Test Framework
| Property | Value |
|----------|-------|
| Framework (UI) | Vitest ^2.1 under jsdom (`environmentMatchGlobs`) |
| Framework (Rust) | `cargo test` (built-in `#[cfg(test)]` modules, as in `mascot_window.rs` / `config.rs`) |
| Config file | `tauri/ui/vitest.config.ts` (include: `src/**/*.test.ts`, `src/**/*.spec.ts`) |
| Quick run command (UI) | `cd tauri/ui && npx vitest run --reporter=dot src/pill/` |
| Quick run command (Rust) | `cd tauri/src-tauri && cargo test pill_window:: config::tests::` |
| Full suite command | `cd tauri/ui && npm test` ; `cd tauri/src-tauri && cargo test` ; `cd <root> && uv run pytest -q` (Python unaffected but must stay green) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PILL-01 | Geometry serde round-trip + off-screen fallback math + clamp-to-work-area | unit (Rust) | `cargo test pill_window::tests` | ❌ Wave 0 (clone mascot's tests) |
| PILL-01 | Label constant matches capability allowlist (`"pill"`) | unit (Rust) | `cargo test pill_window::tests::label_constant_matches_capability_allowlist` | ❌ Wave 0 |
| PILL-02 | `PrimarySurface` enum serde round-trip + legacy/missing → `pill` default | unit (Rust) | `cargo test config::tests::primary_surface` | ❌ Wave 0 (mirror `decodes_legacy_missing_fields_as_defaults`) |
| PILL-02 | `mascot-audit` fence stays green (pill paths don't trip it) | CI (existing) | `gh pr checks` / mascot-audit workflow | ✅ exists (path-scoped) |
| PILL-03 | `cohost_status` → base state map (IDLE/LISTENING/TALKING) | unit (TS) | `npx vitest run src/pill/state-machine.test.ts` | ❌ Wave 0 |
| PILL-03 | reaction frame → expand-on-event → auto-collapse after timeout | unit (TS) | `npx vitest run src/pill/state-machine.test.ts` | ❌ Wave 0 |
| PILL-03 | voice.rms (flat OR nested) → waveform lit-count (reuse `setMeterLevels`) | unit (TS) | `npx vitest run src/pill/waveform.test.ts` | ❌ Wave 0 |
| PILL-03 | deck_state → chip text, honest `unknown` (no fabricated key) | unit (TS) | `npx vitest run src/pill/deck-chips.test.ts` | ❌ Wave 0 |
| PILL-03 | citation strip renders verbatim / null on empty | unit (TS, existing) | `npx vitest run src/session/components/citation-strip.test.ts` | ✅ exists (reuse) |
| PILL-04 | drag handler scoped to top strip; `[data-no-drag]` exempts chips | unit (TS) | `npx vitest run src/pill/index.test.ts` (DOM dispatch mousedown) | ❌ Wave 0 |
| PILL-04 | Focus non-steal (keystrokes reach DJ app after click) | **manual / KAAN-ACTION** | live on built app — no automated test | n/a (felt) |
| PILL-04 | Transparency parity on `.dmg` (no white box) | **manual / KAAN-ACTION** | build `.dmg`, run, eyeball | n/a (felt) |
| PILL-04 | Multi-monitor clamp on display change | unit (clamp math TS/Rust) + **manual** | `cargo test pill_window::tests::clamp` + live unplug | partial ❌ Wave 0 + KAAN-ACTION |

### Sampling Rate
- **Per task commit:** the task's quick-run subset (`vitest run src/pill/<file>` or `cargo test pill_window::`).
- **Per wave merge:** `npm test` (UI) + `cargo test` (Rust) + `uv run pytest -q` (Python regression guard — must stay at the known 7 pre-existing `live-tuning-or-brain` WIP failures, no new reds).
- **Phase gate:** full UI+Rust+Python suites green (modulo the documented 7 pre-existing) before `/gsd:verify-work`; then the KAAN-ACTION felt checks on the built `.dmg`.

### Wave 0 Gaps
- [ ] `tauri/src-tauri/src/pill_window.rs` `#[cfg(test)]` — defaults/debounce/label↔capability/clamp (clone mascot's three tests + add clamp test) — covers PILL-01/04
- [ ] `config.rs` `primary_surface` tests — serde round-trip + legacy-missing→`pill` — covers PILL-02
- [ ] `tauri/ui/src/pill/state-machine.test.ts` — status→state + reaction→expand→collapse — covers PILL-03
- [ ] `tauri/ui/src/pill/waveform.test.ts` — voice.rms (flat+nested) → lit-count — covers PILL-03
- [ ] `tauri/ui/src/pill/deck-chips.test.ts` — deck_state → chip text, honest unknown — covers PILL-03
- [ ] `tauri/ui/src/pill/index.test.ts` — drag handler scope + `[data-no-drag]` exemption — covers PILL-04
- [ ] No framework install needed — vitest + cargo test already present.

## Security Domain

> `security_enforcement` absent in config → treated as enabled. Scope is narrow: the pill is a localhost-only WS consumer + an always-on-top window. No network listener, no remote input, no eval.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface; localhost-only consume. |
| V3 Session Management | no | No sessions; the WS bus is unauthenticated localhost (existing invariant). |
| V4 Access Control | yes (Tauri ACL) | The `"pill"` capability grants ONLY `core:window:allow-start-dragging` + the minimal IPC the pill needs — least privilege. Do NOT widen the capability beyond drag + window state. |
| V5 Input Validation | yes | Frames are JSON from the trusted local sidecar; the pill MUST NOT `eval` or `innerHTML`-inject frame text. Reaction text and chip verbs render via `textContent` only (citation-strip.ts already does this). Malformed frames dropped silently (mascot bus discipline). |
| V6 Cryptography | no | No crypto on the pill. |

### Known Threat Patterns for {Tauri overlay + localhost WS}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Frame text injected as HTML (XSS via reaction text) | Tampering / Elevation | Render reaction/chip text with `textContent`, never `innerHTML`; no `eval`. (citation-strip.ts is the model — `btn.textContent = ...`.) |
| Over-broad window capability | Elevation | Scope the `"pill"` capability to drag + window-state IPC only; do NOT add shell/fs/process perms to the pill label. |
| New network surface | Spoofing / Info disclosure | NONE introduced — the pill opens NO new port; it consumes the existing `ws://127.0.0.1:8765` localhost bus (one-socket invariant). No remote input is accepted. |
| Always-on-top window covering critical UI | Denial (usability) | PILL-04: never cover critical deck info (top-right default placement, compact 280×44), never steal focus; bus-error condition logged, not painted (UI-SPEC error contract). |

<threat_model>
**Surface delta introduced by Phase 62:** one additional always-on-top webview window + one additional Tauri capability entry (`"pill"` label, drag + window-state IPC only). **No new listening port. No remote input. No `eval`/`innerHTML` of frame content** (text rendered via `textContent`). The pill is a strictly read-only consumer of the existing trusted-localhost sidecar bus. The only privilege it requests beyond default is window-drag (already granted app-wide via `core:window:allow-start-dragging`). Net new attack surface: effectively zero beyond "an extra window that can be dragged."
</threat_model>

## Project Constraints (from CLAUDE.md)

- **Gemini-only** — no other AI providers. (Pill adds no AI calls at all; pure consumer.)
- **Anti-slop thesis** — the pill renders grounded text verbatim, never fabricates a key/BPM (honest `unknown`), no scripted "waiting for your set…" filler (silence is the honest empty state). Copy must pass the 15-token + `deeply\s+\w+` anti-slop blocklist.
- **One-click install / deps stay green** — no git-only dependency (rules out `tauri-nspanel`); no new npm runtime dep; at most one crates.io Rust crate, only if the stretch path is taken.
- **macOS + Windows v1** — transparency parity is mandatory (explicit rgba, not OS vibrancy); focus-non-steal is macOS-specific (`#[cfg(target_os="macos")]`), Windows uses always-on-top + skip-taskbar.
- **No scope creep** — no notch-lock, no new port, no Python change, no mascot deletion, no pill→Python command channel.
- **GSD workflow** — all edits go through a GSD command; the pill is planned phase work (`/gsd-execute-phase`).
- **frontend-enforcement skill (hard rules)** — 20/80 amber discipline (amber reserved to the 4-item list in UI-SPEC §Color), textured material feel (faint glow, not faux-3D bevels), no Inter/Roboto/system-ui (Saira + JetBrains Mono), intentional motion (one orchestrated expand reveal, not scattered micro-effects), token-driven CSS only (`var(--token)`, never hex).

## Sources

### Primary (HIGH confidence)
- Codebase ground truth (all VERIFIED by direct read this session):
  - `tauri/src-tauri/src/mascot_window.rs` — clone source (builder flags, geometry-persist, 200ms debounce, off-screen fallback, label↔capability test, the documented "manual ObjC override goes here" fallback plan).
  - `tauri/src-tauri/src/config.rs` — `KEY_MASCOT_WINDOW` + serde + legacy-decode test pattern.
  - `tauri/src-tauri/src/ws_client.rs` — ws:8765 consumer + Rust→event dash-mapping.
  - `tauri/src-tauri/capabilities/default.json` — `core:window:allow-start-dragging` already granted (line 9); windows scope (line 5).
  - `tauri/ui/src/mascot/index.ts` — working `startDragging()` drag pattern + flat-voice-RMS LIVE-05a note.
  - `tauri/ui/src/mascot/ws-client.ts` — `connectMascotBus` direct-WS pattern.
  - `tauri/ui/src/session/components/meter.ts` + `citation-strip.ts` — reuse anchors.
  - `tauri/ui/src/ipc/messages.schema.json` — `cohost_status` enum {IDLE,LISTENING,TALKING}, `cohost-reaction` {text,event_id,citation_strip[]}, `track{title,deck}`, `meters.voice.rms`.
  - `tauri/ui/mascot.html` — transparent-overlay HTML invariant.
  - `tauri/src-tauri/Cargo.toml` / `Cargo.lock` — tauri 2.11.1 + macos-private-api.
  - `tauri.conf.json5` — `macOSPrivateApi:true`, bundle targets `["app","dmg"]`.
  - `.github/workflows/mascot-audit.yml` — fence path-scope (pill won't trip it).
  - `.planning/config.json` — `nyquist_validation:true`, `security_enforcement` absent (enabled).
- docs.rs/tauri (latest) — `WebviewWindow` monitor APIs (`available_monitors`, `current_monitor`, `primary_monitor`, `monitor_from_point`, `outer_position`, `set_position`), `with_webview` signature, `Monitor`.

### Secondary (MEDIUM confidence — verified against multiple sources)
- tauri#11605 — `data-tauri-drag-region` unreliable on unfocused windows → use `startDragging()`. (corroborated by Tauri docs recommending `window.startDragging()`)
- tauri#14102 — `focusable:false` broken on macOS (open, 2.8.4) — the spike-referenced issue.
- tauri#13415 — transparent windows white-box after DMG build (OPEN, no fix; affected 2.5.1, not resolved through 2.11.x in research).
- tauri#13034 / discussion #9876 — NSPanel is the community-blessed non-activating solution; "they use NSPanels instead of regular windows."
- Apple Developer docs — `nonactivatingPanel`: "a window that is a panel or subclass thereof that does not activate the owning app."
- electron#35815 — "NSWindow does not support nonactivating panel styleMask" (cross-framework corroboration of the NSWindow vs NSPanel caveat).
- github.com/ahkohd/tauri-nspanel — 398★, default branch `v2.1`, last push 2026-05-06; NOT on crates.io (git-only) — verified via `gh api` + crates.io API.

### Tertiary (LOW confidence — flagged for plan-time/live confirm)
- Exact `objc2-app-kit` version + the precise NSWindow→NSPanel swizzle incantation — confirm with `cargo search` + a spike build (A1/A3).
- `Monitor::work_area()` exact availability in 2.11 — fallback to existing `size()/scale_factor` clamp (A2).
- Which frame variant (direct-WS vs bridged) carries Phase-59 `deck_state` — confirm in `ws_bus` (A4).

## Metadata

**Confidence breakdown:**
- Codebase reuse (clone source, wire shapes, components, capability, CI fence): HIGH — direct read this session.
- Drag (Leg B) + transparency-parity-via-rgba (Leg C): HIGH — proven in-tree + locked by UI-SPEC.
- Focus non-steal (Leg A): MEDIUM-HIGH on the *caveat* (multi-source verified), MEDIUM on *which path lands* (bounded spike + honest floor).
- Multi-monitor (Leg D): HIGH on APIs, MEDIUM on the display-change hook (new piece).
- DMG transparency outcome: UNKNOWABLE without the build → KAAN-ACTION by design.

**Research date:** 2026-05-21
**Valid until:** ~2026-06-20 for the Tauri-issue status (fast-moving — re-check #13415/#14102 resolution before relying on the floor); codebase reuse facts are stable until those files change.
