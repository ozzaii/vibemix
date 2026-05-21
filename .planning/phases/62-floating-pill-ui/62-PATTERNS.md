# Phase 62: Floating Pill UI - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 11 (6 new, 5 modified)
**Analogs found:** 11 / 11 (every new/modified file has a strong in-tree analog — this is the ~90%-reuse phase RESEARCH described)

> **How to read this file (planner):** every executor task for Phase 62 is a CLONE task,
> not an invent task. Each section below names the exact analog file + line range to copy,
> the precise delta to apply, and the anti-patterns that fail CI. The single genuinely-new
> code is (a) the macOS focus-non-steal `#[cfg]` block and (b) the display-change re-clamp
> hook — both flagged inline. **One load-bearing wire-shape gap is documented in "No Analog
> Found": Phase-59 `deck_state` is NOT on either WS frame today** — the planner must decide
> deck-chip sourcing before the executor builds the chips.

---

## File Classification

| New/Modified File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|---------|------|-----------|----------------|---------------|
| `tauri/src-tauri/src/pill_window.rs` | NEW | window-builder (Rust) | event-driven (WindowEvent) | `tauri/src-tauri/src/mascot_window.rs` | exact (clone-minus-one-block) |
| `tauri/src-tauri/src/config.rs` | MOD | config/persistence (Rust) | CRUD (store get/set) | self — `KEY_MASCOT_WINDOW` + `MascotWindowState` block | exact (same file, mirror pattern) |
| `tauri/src-tauri/src/main.rs` | MOD | bootstrap/wiring (Rust) | request-response (setup) | self — `mod mascot_window;` + `create_mascot_window` setup branch | exact (same file, mirror pattern) |
| `tauri/src-tauri/capabilities/default.json` | MOD | config (capability ACL) | n/a | self — `"windows"` array + `core:window:allow-start-dragging` | exact (one-line add) |
| `tauri/ui/pill.html` | NEW | HTML entry (overlay) | n/a | `tauri/ui/mascot.html` | exact (transparent-overlay invariant) |
| `tauri/ui/src/pill/index.ts` | NEW | boot/controller (TS) | event-driven (WS frames + rAF) | `tauri/ui/src/mascot/index.ts` (drag + handleMessage + bus wiring) | exact |
| `tauri/ui/src/pill/ws-client.ts` (reuse) | reuse | service (WS client) | streaming (WS) | `tauri/ui/src/mascot/ws-client.ts` `connectMascotBus` | exact (import, do NOT re-implement) |
| `tauri/ui/src/pill/state-machine.ts` | NEW | pure state machine (TS) | transform (frame→state) | `tauri/ui/src/mascot/state-machine.ts` (purity discipline) | role-match (much simpler — 4 states) |
| `tauri/ui/src/pill/waveform.ts` | NEW | component (TS) | transform (rms→bars) | `tauri/ui/src/session/components/meter.ts` `renderMeter`/`setMeterLevels` | role-match (reuse tokens, restyle geometry) |
| `tauri/ui/src/pill/deck-chips.ts` | NEW | component (TS) | transform (deck→chip) | `tauri/ui/src/session/components/citation-strip.ts` (chip-strip skeleton) | role-match (NB: wire-source gap — see below) |
| citation strip (reuse) | reuse | component (TS) | transform | `tauri/ui/src/session/components/citation-strip.ts` `renderCitationStrip` | exact (import verbatim) |
| `tauri/ui/src/pill/*.test.ts` | NEW | test (vitest/jsdom) | n/a | `meter.test.ts` / `citation-strip.test.ts` / mascot `state-machine.test.ts` | role-match |

---

## Pattern Assignments

### `tauri/src-tauri/src/pill_window.rs` (window-builder, event-driven) — NEW

**Analog:** `tauri/src-tauri/src/mascot_window.rs` (263 lines — clone ~90% verbatim).

**Clone-with-subtraction recipe — three deltas only:**
1. Label `"pill"` (not `"mascot"`).
2. **DROP** the `set_ignore_cursor_events(true)` block (lines 120-123) — the pill is interactive.
3. **ADD** a `#[cfg(target_os="macos")]` focus-non-steal block after `.build()?` (genuinely new — see Leg A).

**Builder pattern to clone** (`mascot_window.rs` lines 101-128) — change the flagged lines:
```rust
pub const PILL_WINDOW_LABEL: &str = "pill";   // was MASCOT_WINDOW_LABEL = "mascot"

let window = WebviewWindowBuilder::new(app, PILL_WINDOW_LABEL, WebviewUrl::App("pill.html".into()))
    .title("vibemix")
    .transparent(true)
    .always_on_top(true)
    .decorations(false)
    .resizable(false)               // DELTA: pill is fixed-size (expand = CSS height, not window resize)
    .skip_taskbar(true)
    .visible_on_all_workspaces(true)
    .focused(false)                 // DELTA: request non-activating (see Leg A caveat)
    .inner_size(280.0, 44.0)        // DELTA: UI-SPEC collapsed 280×44 (was 300×400)
    .position(f64::from(x), f64::from(y))
    .visible(true)
    .build()?;
// DELTA: DO NOT clone mascot_window.rs lines 120-123 (set_ignore_cursor_events) — pill is interactive.

#[cfg(target_os = "macos")]
apply_nonactivating(&window);       // NEW — see "Shared Patterns / Leg A"

install_geometry_listener(app.clone(), window.clone());  // clone verbatim, lines 166-218
```

**Geometry-persist + 200ms debounce — clone VERBATIM** (`mascot_window.rs` lines 158-218,
plus helpers `window_position`/`window_size` lines 220-232). Only swap `MASCOT_WINDOW_LABEL`→
`PILL_WINDOW_LABEL` and `load_mascot_state`/`save_mascot_state`→ the pill's equivalent (or reuse
mascot's geometry struct keyed under a `pill_window` store key — planner decides; the debounce
machinery is identical). `DEBOUNCE_MS = 200` (line 47) — keep.

**Off-screen-fallback clone** (`mascot_window.rs` lines 81-99 + `primary_logical_size` lines 135-143
+ `default_top_right` lines 150-156) — clone verbatim. This solves the physical/logical Retina-doubling
bug; re-deriving it reintroduces the off-screen-on-2x-display regression.

**Display-change re-clamp (NEW behavior, beyond a straight clone — Leg D):** in
`install_geometry_listener`, also match `WindowEvent::ScaleFactorChanged` (or hook
`current_monitor()` on a topology change) and `set_position` back inside
`current_monitor().work_area()` if off-screen. This is the one new event hook.

**Label↔capability test — clone** (`mascot_window.rs` lines 258-262):
```rust
#[test]
fn label_constant_matches_capability_allowlist() {
    assert_eq!(PILL_WINDOW_LABEL, "pill");   // capabilities/default.json "windows" must include "pill"
}
```
Also clone `defaults_pin_context_decisions` (lines 238-247) with the UI-SPEC 280×44 numbers and
`debounce_is_not_zero_or_thrashy` (lines 249-256) verbatim.

**Third-window precedent (additional reference):** `tauri/src-tauri/src/debrief_window.rs` already
shows a runtime-created `WebviewWindowBuilder` with `pub const DEBRIEF_WINDOW_LABEL` (line 33) +
`WebviewUrl::App` (line 158) — confirms the "third overlay window" path is well-trodden.

---

### `tauri/src-tauri/src/config.rs` (config/persistence, CRUD) — MODIFIED

**Analog:** self — the `KEY_MASCOT_WINDOW` + `MascotWindowState` block (same file).

**Add a tri-state enum keyed under a new top-level store key.** Mirror the three mascot helpers:
`load_mascot_state` (lines 138-148) / `save_mascot_state` (lines 153-164) / the serde-roundtrip +
legacy-decode tests (lines 259-292).

**Key constant pattern** (mirror line 41):
```rust
const KEY_PRIMARY_SURFACE: &str = "primary_surface";
```

**Tri-state enum with default = pill** (mirror `MascotWindowState` + its `impl Default`, lines 77-98):
```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum PrimarySurface {
    #[default]
    Pill,    // default — Kaan-approved partial reversal (CONTEXT Area 2)
    Mascot,  // opt-in / secondary — mascot-audit fence stays green
    None,
}
```

**Load helper — clone `load_mascot_state` exactly** (lines 138-148), swapping the key + type:
```rust
pub fn load_primary_surface(app: &AppHandle) -> Result<PrimarySurface, String> {
    use tauri_plugin_store::StoreExt;
    let store = app.store(STORE_PATH).map_err(|e| format!("store init failed: {e}"))?;
    match store.get(KEY_PRIMARY_SURFACE) {
        Some(value) => serde_json::from_value(value.clone()).map_err(|e| format!("decode failed: {e}")),
        None => Ok(PrimarySurface::default()),   // legacy/missing → Pill (CONTEXT Area 2)
    }
}
```
Add `save_primary_surface` mirroring `save_mascot_state` (lines 153-164) and, if the Settings UI flips
it, the `#[tauri::command]` wrappers mirroring `read/write_mascot_window_state` (lines 179-190).

**Legacy-decode test — clone `mascot_window_state_decodes_legacy_missing_fields_as_defaults`** (lines
280-292) as the canonical "missing key → Pill" guard:
```rust
#[test]
fn primary_surface_decodes_legacy_missing_as_pill() {
    // No primary_surface key in a pre-Phase-62 config.json → default Pill.
    let s = PrimarySurface::default();
    assert_eq!(s, PrimarySurface::Pill);
}
#[test]
fn primary_surface_roundtrips_via_serde_json() {   // mirror lines 259-277
    for v in [PrimarySurface::Pill, PrimarySurface::Mascot, PrimarySurface::None] {
        let j = serde_json::to_value(v).unwrap();
        assert_eq!(serde_json::from_value::<PrimarySurface>(j).unwrap(), v);
    }
}
```

> **Forward-compat note (config.rs lines 43-54 + 280-289):** `tauri-plugin-store` + serde ignore
> unknown keys, and the sidecar's `_PHASE12_FIELDS` allowlist preserves unknown top-level keys on
> round-trip — so adding `primary_surface` does NOT disturb the existing `mascot_window` /
> `first_run_state` keys. No migration needed.

---

### `tauri/src-tauri/src/main.rs` (bootstrap/wiring, request-response) — MODIFIED

**Analog:** self — `mod mascot_window;` (line 24) + the `create_mascot_window` setup branch (lines 151-161).

**Module declaration** (mirror line 24, alphabetical-ish ordering):
```rust
mod pill_window;
```

**Setup branch — mirror the mascot create-on-startup block** (lines 151-161), but read
`config::load_primary_surface` first and branch:
```rust
// Phase 62 — choose the in-set surface from primary_surface (default Pill).
match config::load_primary_surface(&app_handle).unwrap_or_default() {
    config::PrimarySurface::Pill => {
        match pill_window::create_pill_window(&app_handle) {
            Ok(Some(_)) => tracing::info!("pill overlay window built"),
            Ok(None)    => tracing::info!("pill overlay hidden (user preference)"),
            Err(e)      => tracing::error!("pill window build failed: {e}"),  // non-fatal — mirror mascot
        }
    }
    config::PrimarySurface::Mascot => {
        let _ = mascot_window::create_mascot_window(&app_handle);   // existing path (lines 151-161)
    }
    config::PrimarySurface::None => tracing::info!("no in-set surface (primary_surface=none)"),
}
```
> **Non-fatal-on-failure discipline (main.rs lines 148-161):** the existing mascot branch logs but
> does NOT bail setup — "the main session UI must still come up even if the [overlay] fails to build".
> Clone that exactly for the pill.

**Command registration (only if Settings flips the surface):** add the pill's `#[tauri::command]`
entries to the `generate_handler![...]` macro (lines 74-95) alongside the four `config::*mascot*`
commands (lines 79-82).

---

### `tauri/src-tauri/capabilities/default.json` (config/capability ACL) — MODIFIED

**Analog:** self — the `"windows"` array (line 5) + `core:window:allow-start-dragging` (line 9, ALREADY granted).

**One-line delta** (closes the v0.1.0-rc1 drag-capability debt):
```jsonc
"windows": ["main", "mascot", "overlay-*", "debrief", "pill"]   // was [..., "debrief"]
```
`core:window:allow-start-dragging` is **already in `permissions`** (line 9) — adding the `"pill"` label
to the `"windows"` scope is what makes the existing drag permission apply to the pill window. No new
permission identifier needed for drag. Update the long `description` string (line 4) to mention the pill
window (the `capabilities-lint.yml` workflow checks this file).

> **Anti-pattern (capabilities/default.json line 4):** do NOT add `app:allow-<command>` entries for
> the pill's `#[tauri::command]`s — Tauri 2.x auto-allows webview→app-command invocation; that
> namespace is reserved for the core-app plugin and enumerating user commands fails the build with
> "permission identifier not found".

---

### `tauri/ui/pill.html` (HTML entry, overlay) — NEW

**Analog:** `tauri/ui/mascot.html` (95 lines) — clone the transparent-overlay invariant head.

**MANDATORY invariant — clone VERBATIM** (`mascot.html` lines 1-2, 55, 66-78, 84). Without it,
`tokens.css` paints a global dark vignette + film-grain over the desktop (RESEARCH Pitfall 4):
```html
<html lang="en" style="background: transparent; margin: 0; padding: 0;">
  <head>
    <link rel="stylesheet" href="/src/tokens.css" />
    <style>
      html, body {
        margin: 0; padding: 0;
        background: transparent !important;       /* survive tokens.css v5 vignette */
        background-image: none !important;
        overflow: hidden; width: 100vw; height: 100vh;
      }
      body::before { display: none !important; }   /* kill the film-grain SVG over the desktop */
    </style>
  </head>
  <body style="background: transparent; margin: 0; padding: 0; overflow: hidden;">
    <!-- pill DOM here; top 28px = drag strip -->
    <script type="module" src="/src/pill/index.ts"></script>
  </body>
</html>
```
> The pill's visible surface is painted by **CSS `--glass-3` = `rgba(2,3,6,0.88)`** (UI-SPEC §Color),
> NOT OS vibrancy — guarantees mac+win parity + dodges the DMG white-box regression (#13415).
> `backdrop-filter: var(--blur-glass)` is a progressive enhancement layered ON TOP, never the sole
> opacity source.
> **Anti-pattern:** never reference `mascot.html` from a pill test — `mascot-audit`'s
> `mascot-tauri-only-grep` gate fails (`.github/workflows/mascot-audit.yml` line 75).
> `overlay.html` + `debrief.html` are additional in-tree examples of the same invariant.

---

### `tauri/ui/src/pill/index.ts` (boot/controller, event-driven) — NEW

**Analog:** `tauri/ui/src/mascot/index.ts` — clone the drag handler + bus wiring + reader/writer
`handleMessage` discipline; throw away the Three.js renderer/rAF-crossfade parts.

**Drag handler — clone VERBATIM** (`mascot/index.ts` lines 144-163), but scope the listener to the
**top 28px drag strip** (UI-SPEC) and tag chips `[data-no-drag]`:
```ts
const mod = await import("@tauri-apps/api/window");
const tauriWin = mod.getCurrentWindow();
dragStrip.addEventListener("mousedown", (ev) => {       // DELTA: dragStrip, not document
  const me = ev as MouseEvent;
  if (me.button !== 0) return;                          // left-click only
  if ((me.target as HTMLElement | null)?.closest("[data-no-drag]")) return;  // chips exempt
  tauriWin.startDragging().catch((e) => console.warn("startDragging() rejected:", e));
});
```
> This is exactly the CONTEXT-prescribed mechanism and it is ALREADY PROVEN here (mascot ships it).
> `data-tauri-drag-region` is kept as progressive enhancement only — unreliable alone on
> non-activating windows (RESEARCH Leg B / tauri#11605).

**Bus subscription — REUSE `connectMascotBus`, do NOT re-implement** (`mascot/index.ts` lines 51, 291-293):
```ts
import { connectMascotBus } from "../mascot/ws-client.js";   // import the shipped client verbatim
const bus = connectMascotBus("ws://127.0.0.1:8765");
bus.addMessageListener(handleFrame);
bus.addStatusListener((s) => { /* CONTEXT: no error UI on the pill — silence is the honest empty state */ });
```
(Or copy `ws-client.ts` to `tauri/ui/src/pill/ws-client.ts` if the planner wants the pill fully
decoupled from `src/mascot/**` — either is fine; importing keeps DRY and the file is already
contract-tested. **If imported, note the pill PR may path-trigger `mascot-audit` since it touches
`tauri/ui/src/mascot/**` indirectly — copying into `pill/` avoids that.** Planner's call.)

**Reader/writer `handleMessage` discipline — clone the pattern** (`mascot/index.ts` lines 183-251):
snapshots are READERS (update a current-view ref, no transition), `cohost-reaction` is the WRITER
(drives `expand-on-event`). See "Shared Patterns / Frame fan-out" for the exact pill version.

> **WIRE NUANCE — clone the mascot's flat-float read** (`mascot/index.ts` lines 205-217, "LIVE-05a"):
> on the **direct live WS frame** the pill reads, `voice`/`music` arrive as **flat top-level floats**
> (`levels.snapshot()` broadcasts top-level numbers — VERIFIED `ws_bus.py` lines 266-267). On the
> **rich `ipc.session.snapshot`** frame they're nested `meters.voice.rms` (VERIFIED `ws_bus.py`
> lines 113-116). Read defensively: `msg.voice ?? msg.meters?.voice?.rms ?? prev`.

---

### `tauri/ui/src/pill/state-machine.ts` (pure state machine, transform) — NEW

**Analog:** `tauri/ui/src/mascot/state-machine.ts` — clone the **purity discipline header** (lines 1-26),
not the transition tables (the pill's are far simpler: 4 states).

**Purity contract to honor** (mascot `state-machine.ts` lines 1-13): no wall-clock reads (take
`now: number` as a param), no timers (express the 6s expand-collapse as a `collapseAt` data field the
rAF loop fires), no heavy imports — so the vitest cases are deterministic without clock mocking.

**State derivation (verified enum):** `cohost_status ∈ {IDLE, LISTENING, TALKING}` (VERIFIED
`ws_bus.py` lines 119-125 + `messages.schema.json`):
```ts
type CohostStatus = "IDLE" | "LISTENING" | "TALKING";
function baseState(s: CohostStatus): "idle" | "listening" | "speaking" {
  return s === "TALKING" ? "speaking" : s === "LISTENING" ? "listening" : "idle";
}
// expand-on-event: a cohost-reaction sets state="expand" + collapseAt = now + 6000;
// rAF loop reverts to baseState(currentStatus) once now >= collapseAt (no setTimeout — data-driven).
```

---

### `tauri/ui/src/pill/waveform.ts` (component, transform) — NEW

**Analog:** `tauri/ui/src/session/components/meter.ts` — reuse the token-driven LED fill + the
zero-DOM-churn `data-lit` update pattern; restyle the geometry (vertical 16-seg strip → horizontal
12-16 bars per UI-SPEC).

**Reusable verbatim:** the amber-zone gradient tokens (`meter.ts` lines 113-118 — `--amber`/`--amber-78`
warm fill) + the **single-attribute-write update path** (`setMeterLevels`, lines 230-254): JS sets one
`data-lit-count`/`data-lit` attribute, the browser repaints — no per-frame DOM construction.

**Wire the real signal — NOT a fake animation** (CONTEXT Area 3, UI-SPEC §States):
```ts
// voice.rms IS Levels.update_voice AI-speech RMS already on the bus (VERIFIED ws_bus.py 111,115).
import { renderMeter, setMeterLevels } from "../session/components/meter.js";  // or fork geometry, reuse tokens
// per snapshot frame during `speaking`:
setMeterLevels(wf, { rms: view.voiceRms, peak: view.voicePeak ?? null });
```
> The UI-SPEC describes **horizontal** 12-16 bars; `meter.ts` is a **vertical** 16-segment strip.
> Reuse the CSS tokens + the `data-lit-count` update pattern (meter.ts lines 230-240) + the amber
> gradient (lines 113-118); the bar **orientation/count** is the pill-specific styling delta.
> **Anti-pattern:** do NOT hand-roll a canvas/SVG waveform — it risks breaking the 20/80 rule +
> the frontend-enforcement audit; the LED ladder is token-tested.

---

### `tauri/ui/src/pill/deck-chips.ts` (component, transform) — NEW

**Analog (skeleton):** `tauri/ui/src/session/components/citation-strip.ts` — clone the chip-strip
DOM-build + token discipline + `null`-on-empty pattern; the **data source differs** (see gap below).

**Reusable from `citation-strip.ts`:** the `vmx-citation-strip` flex layout (lines 56-68), the mono
tabular-nums chip styling (lines 69-96), the resting-glow-OFF / hover-glow discipline (lines 84-103),
and the **return-`null`-when-empty** contract (line 147) so the caller does `if (strip) panel.append(strip)`.

**Chip text — honest-unknown, never fabricate** (UI-SPEC §Deck-context chips):
```ts
function deckChipText(d: { deck: string; camelot: string | null; bpm: number | null }) {
  const key = d.camelot ?? "unknown";        // NEVER fabricate a key (anti-slop, Phase 59 contract)
  const bpm = d.bpm != null ? Math.round(d.bpm) : "unknown";
  return `${d.deck.toLowerCase()} · ${key.toLowerCase()} · ${bpm}`;   // "a · 8a · 128"
}
// no deck resolves → single "decks · unknown" chip in --silk-40. Key glyph amber ONLY when resolved.
```
> Key amber when resolved, `--silk-40` when `unknown`. The chip key MUST come from registry-observed
> `key:` evidence (Phase-59 citable source) — never invented.
>
> **⚠️ WIRE-SOURCE GAP — see "No Analog Found" below.** Phase-59 per-deck `deck_state` (with
> `camelot`/`key`/`bpm`) is NOT on either WS frame today. The planner must resolve sourcing before
> this file is built.

---

### `tauri/ui/src/pill/*.test.ts` (test, vitest/jsdom) — NEW

**Analogs:** `meter.test.ts`, `citation-strip.test.ts`, mascot `state-machine.test.ts`.

- **State-machine purity/derivation:** clone mascot `state-machine.test.ts` (deterministic `now`-param
  cases). Cover `IDLE/LISTENING/TALKING → idle/listening/speaking` + `cohost-reaction → expand` +
  `collapseAt` revert.
- **Token/CSS contract:** clone the `_CSS_FOR_TEST` grep pattern (`meter.ts` line 263 +
  `citation-strip.ts` line 119) — assert no hex / non-black rgba, amber tokens present (frontend-enforcement).
- **Clamp math:** unit-test the off-screen-fallback + work-area clamp (the Rust math has Rust tests;
  any TS-side clamp helper gets a vitest case).
- Routed by the `src/session/components/*.test.ts` + mascot test globs in `vitest.config.ts`; pill
  tests live under `tauri/ui/src/pill/` (NOT `src/mascot/`) — keeps `mascot-audit` from path-triggering.

---

## Shared Patterns

### Frame fan-out (snapshots = readers, events = writers)
**Source:** `tauri/ui/src/mascot/index.ts` `handleMessage` (lines 183-251) + the LIVE-05a flat-float
read (lines 205-217).
**Apply to:** `tauri/ui/src/pill/index.ts` + `state-machine.ts`.
```ts
function handleFrame(msg: any) {
  // READER: snapshot frames update the current view, no transition.
  if (msg?.type === "snapshot" || msg?.cohost_status != null) {
    view.cohostStatus = msg.cohost_status ?? view.cohostStatus;          // IDLE|LISTENING|TALKING
    view.voiceRms = msg.voice ?? msg.meters?.voice?.rms ?? view.voiceRms; // flat OR nested (LIVE-05a)
    view.track = msg.track ?? view.track;                                // {title, deck}
    view.bpm = typeof msg.bpm === "number" ? msg.bpm : view.bpm;
    return;
  }
  // WRITER: cohost-reaction drives expand-on-event.
  if (msg?.type === "cohost-reaction" || msg?.type === "ipc.session.cohost-reaction") {
    expandWith(msg.text, msg.citation_strip ?? []);   // text verbatim + chips → 6s expand, then collapse
  }
}
```

### Direct-WS bus client (reconnect/backoff)
**Source:** `tauri/ui/src/mascot/ws-client.ts` `connectMascotBus` (whole file, 175 lines) — 1→2→4→8s
backoff (lines 35-36, 77-88), reset-on-open (line 108), silent-drop of non-JSON / malformed frames
(lines 116, 120-127, anti-slop), `addMessageListener`/`addStatusListener`/`close` surface (lines 150-174).
**Apply to:** the pill (import or copy). Self-healing + lifecycle-independent of the main window —
exactly what the PRIMARY surface needs.
**Do NOT** build a new socket client.

### Citation strip — reuse VERBATIM
**Source:** `tauri/ui/src/session/components/citation-strip.ts` `renderCitationStrip` (lines 144-174)
+ `formatMmSs` (lines 128-137).
**Apply to:** the pill's expand panel.
```ts
import { renderCitationStrip } from "../session/components/citation-strip.js";
const strip = renderCitationStrip({ chips: reaction.citation_strip, onChipClick: (c) => {/* v1 no-op */} });
if (strip) expandPanel.append(strip);   // returns null when empty — no hanging div
```
Wire fields are field-identical: `event_id` / `verb` / `timestamp_s` (VERIFIED Python
`CitationChipPayload` `cohost_reaction.py` lines 52-54 == TS `CitationChip` `citation-strip.ts` lines 37-47).
**Do NOT** re-implement a chip component.

### macOS focus-non-steal (Leg A — the one genuinely-new Rust code)
**Source:** none in-tree — `mascot_window.rs` line 56 documents the intended ObjC-override slot
("the manual ObjC override goes here") but never needed it. This is the phase's only net-new native code.
**Apply to:** `pill_window.rs`, `#[cfg(target_os="macos")]` only.
- **Floor (recommended baseline, no new dep):** `.focused(false)` on the builder (already in the
  builder snippet above) + `app.set_activation_policy(tauri::ActivationPolicy::Accessory)` so vibemix
  reads as a background/accessory app. **Documented limitation:** first click on a non-activating
  `NSWindow` may still transfer key-window status (wry#637, tauri#14102 open) → KAAN-ACTION live-confirm.
- **Stretch (true non-activating, bounded spike):** in a `with_webview` closure get `ns_window()`
  (cast to `objc2_app_kit::NSWindow`), swizzle the class to `NSPanel`, then set
  `styleMask |= NonactivatingPanel`. **CAVEAT (HIGH-confidence, RESEARCH Leg A):**
  `NSWindowStyleMaskNonactivatingPanel` is a **silent no-op on a plain `NSWindow`** — it only changes
  behavior on an `NSPanel` subclass. Setting it without the class swizzle compiles, runs, and does
  nothing. Mark as a time-boxed spike with the Floor as the honest fallback (`gsd-autonomous fully`:
  defer, don't pause).
- **Verification (KAAN-ACTION):** focus a text field in the DJ app, click the pill, type — keystrokes
  must still land in the DJ app. Cannot be unit-tested.

### Transparency parity (Leg C)
**Source:** `mascot.html` lines 66-78 (the `!important` transparent invariant) + `tauri.conf.json5`
`macOSPrivateApi: true` (line 97, already set).
**Apply to:** `pill.html` (clone the invariant) + the pill's `--glass-3` rgba surface.
Window flags `transparent(true)` + `decorations(false)` (in the builder snippet). The visible surface
is the CSS rgba fill, never OS vibrancy. **DMG white-box (#13415, open, no upstream fix)** is only
confirmable on the built `.dmg` → KAAN-ACTION.

---

## No Analog Found

| File / Concern | Role | Data Flow | Reason / planner action |
|----------------|------|-----------|--------------------------|
| **Deck-state on the WS wire** (feeds `deck-chips.ts`) | wire field | transform | **LOAD-BEARING GAP (VERIFIED):** Phase-59 `MusicState.deck_state` (per-deck `DeckTrack` with `camelot`/`key`/`bpm`/`confidence`, `deck_state.py` lines 25-58) exists in-process but is **NOT serialized onto EITHER WS frame today.** The mascot frame carries only flat `deck = audible_deck` (single string, `ws_bus.py` line 269); the `ipc.session.snapshot` carries only `track{title, deck}` + flat `bpm` (`ws_bus.py` lines 130-139, `session_loop.py` `_build_snapshot`). Neither has per-deck `camelot`/`key`. **Planner must pick one:** (a) add a `deck_state` field to the EXISTING snapshot on the EXISTING socket — additive, no new port (the safe reading of CONTEXT's "no Python delivery change" = "no new port / no new socket / no transport rework"; an additive field on the existing frame is the same delivery path), confirm with Kaan if needed; OR (b) scope v1 deck chips to only what's already on the wire (`track{title, deck}` + `bpm`, key always `unknown`) and defer the key glyph. RESEARCH open question A4 flagged exactly this. |
| `apply_nonactivating()` macOS interop | native interop | n/a | No in-tree analog (Leg A above). `mascot_window.rs` line 56 reserves the slot but never implemented it. Net-new; bounded spike with Floor fallback. |
| display-change re-clamp hook | event handler | event-driven | Partial: `mascot_window.rs` has the off-screen fallback at BUILD time (lines 81-99) but no runtime topology-change listener. The pill adds one `WindowEvent` match arm — small new piece on top of the cloned listener (RESEARCH Leg D). |

---

## Metadata

**Analog search scope:** `tauri/src-tauri/src/`, `tauri/src-tauri/capabilities/`, `tauri/ui/`,
`tauri/ui/src/mascot/`, `tauri/ui/src/session/components/`, `src/vibemix/runtime/`,
`src/vibemix/state/`, `src/vibemix/ui_bus/`, `.github/workflows/`.
**Files scanned (read in full or targeted):** `mascot_window.rs`, `config.rs`, `main.rs`,
`capabilities/default.json`, `mascot.html`, `mascot/index.ts`, `mascot/ws-client.ts`,
`mascot/state-machine.ts` (head), `citation-strip.ts`, `meter.ts`, `debrief_window.rs` (head),
`ws_bus.py`, `session_loop.py` (`_build_snapshot`), `deck_state.py`, `cohost_reaction.py`,
`mascot-audit.yml`.
**Wire shapes VERIFIED against source:** flat `voice`/`music`/`deck` on the 30Hz mascot frame
(`ws_bus.py` 266-269); nested `meters.voice.rms` + `cohost_status` + `track` on `ipc.session.snapshot`
(`ws_bus.py` 113-178); `cohost_status` enum derivation (`ws_bus.py` 119-125); citation chip fields
(`cohost_reaction.py` 52-54); deck_state ABSENT from both frames (grep, `session_loop.py` /
`ws_bus.py` builders).
**Pattern extraction date:** 2026-05-22

---

## PATTERN MAPPING COMPLETE

**Phase:** 62 - Floating Pill UI
**Files classified:** 11 (6 new, 5 modified/reuse)
**Analogs found:** 11 / 11

### Coverage
- Files with exact analog: 7 (`pill_window.rs`, `config.rs`, `main.rs`, `default.json`, `pill.html`, `pill/index.ts`, citation-strip + ws-client reuse)
- Files with role-match analog: 4 (`state-machine.ts`, `waveform.ts`, `deck-chips.ts`, pill tests)
- Files with no analog: 0 files entirely new; 3 CONCERNS net-new (deck-state-on-wire gap, macOS focus-non-steal interop, display-change re-clamp)

### Key Patterns Identified
- **Clone-with-subtraction:** `pill_window.rs` = `mascot_window.rs` minus `set_ignore_cursor_events`, plus a macOS `#[cfg]` block — geometry-persist/200ms-debounce/off-screen-fallback/label↔capability test all cloned verbatim.
- **Snapshots = readers, events = writers:** the mascot's `handleMessage` discipline is the pill's state-machine contract; `cohost-reaction` is the only WRITER (drives expand).
- **One socket, two frame shapes:** the pill reads the direct WS bus (`connectMascotBus`); `voice` is flat on the live frame, nested under `meters.voice.rms` on the bridged snapshot — read defensively.
- **Reuse-don't-invent UI:** `renderCitationStrip` verbatim, `meter.ts` tokens + `data-lit` update path for the waveform, `mascot.html` transparent-overlay invariant for `pill.html`.
- **`primary_surface` tri-state:** mirrors the `MascotWindowState` serde + legacy-decode pattern in the same `config.rs`; default Pill; mascot stays buildable (mascot-audit green, fence path-scoped to `tauri/ui/src/mascot/**`).

### Load-bearing flag for the planner
**Phase-59 `deck_state` is NOT on any WS frame today.** Deck chips need either an additive snapshot
field (same socket, same delivery path — the safe reading of "no Python delivery change") or a v1
scope-down to `track{title,deck}` + `bpm` with key always `unknown`. Resolve before building
`deck-chips.ts`.

### File Created
`/Users/ozai/projects/dj-set-ai/.planning/phases/62-floating-pill-ui/62-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Every executor task is a clone task with the exact analog file + line range
named. Planner can reference these analog patterns directly in PLAN.md action sections.
