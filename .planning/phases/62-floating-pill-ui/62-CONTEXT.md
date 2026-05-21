# Phase 62: Floating Pill UI - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Smart-discuss (autonomous, `gsd-autonomous fully` — grey areas auto-resolved with recommended answers grounded in ROADMAP success criteria + research SUMMARY + locked project memory; overnight run, no interactive pause)

<domain>
## Phase Boundary

Deliver a small, transparent, always-on-top, draggable **Super-Whisper-style pill** as the
**primary** live in-set surface for vibemix. Clone the existing `mascot_window.rs` →
`pill_window.rs`, make it the default surface via a tri-state `primary_surface` config,
have it consume the EXISTING `ws://127.0.0.1:8765` frames (no new port, no Python delivery
change), and show idle/listening/speaking/expand-on-event states with the real TTS waveform
+ citation strip + deck-context chips. The Three.js mascot demotes to opt-in/secondary —
**kept, not retired** (`mascot-audit` CI fence stays green). The load-bearing risk is the
drag-on-unfocused-window + focus-steal + transparency-parity behavior, which must be resolved
on the BUILT app; the felt confirmation of that behavior is the only KAAN-ACTION carve-out.

This is the last v5.0 phase and parallelizes with the 59–61 spine (its deck-chip polish
soft-depends on Phase 59, which is COMPLETE — so deck chips can land in this phase).
</domain>

<decisions>
## Implementation Decisions

### Area 1 — Window mechanics + drag/focus/transparency spike (PILL-01, PILL-04)
- **Clone, don't fork-in-place:** new `tauri/src-tauri/src/pill_window.rs` modeled on
  `mascot_window.rs` — reuse its geometry-persist + 200ms debounce + "label constant matches
  capability allowlist" pattern. Keep the mascot file intact.
- **NOT click-through:** the pill is interactive (draggable + clickable), so it MUST NOT call
  `set_ignore_cursor_events(true)` (the mascot's click-through line). Cursor events reach the pill.
- **Focus non-steal (PILL-04):** macOS → build the pill as a **non-activating NSPanel**
  (`NSWindowStyleMaskNonactivatingPanel`) and `.focused(false)` at build, so clicking the pill
  never activates vibemix / never pulls keyboard focus off the DJ app. Verify keystrokes still
  reach the DJ app after a click (live = KAAN-ACTION).
- **Drag mechanism:** `data-tauri-drag-region` alone is unreliable on unfocused/non-activating
  windows (tauri#11605/#10767) → primary mechanism is explicit JS
  `getCurrentWindow().startDragging()` on `mousedown` over the drag handle; `data-tauri-drag-region`
  kept as progressive-enhancement. The exact winning combination is resolved on the BUILT app
  (this is the research-flagged spike — resolve FIRST in plan-time; felt confirm = KAAN-ACTION).
- **Transparency parity:** `transparent(true)` + `decorations(false)`, but the pill's visible
  surface uses an **explicit CSS `--glass-*` rgba fallback**, NOT pure OS vibrancy — guarantees
  mac+win parity (no opaque white box on Windows) and dodges the DMG-build transparency
  regression (tauri#13415). Verify on the built `.dmg` (KAAN-ACTION).
- **Multi-monitor:** clamp-to-visible on display change; persist x/y/w/h exactly like the mascot.
- **Capability allowlist (closes v0.1.0-rc1 drag debt):** add a `"pill"` capability/allowlist
  entry (the pill window label) covering `window:allow-start-dragging` + the IPC the pill needs,
  mirroring how the mascot label is allowlisted.

### Area 2 — `primary_surface` tri-state config (PILL-02)
- New top-level config key in `config.rs`: `primary_surface ∈ { "pill" (default) | "mascot"
  (opt-in/secondary) | "none" }`, sitting alongside the existing `mascot_window` state key.
- **Default `"pill"`** — the deliberate, Kaan-approved partial reversal of the shipped
  full-screen-mascot direction for the in-set surface. Mascot stays opt-in/secondary, **NOT
  retired** — `mascot-audit` CI fence must stay green.
- Surface selection takes effect on session start (config write → which window is created); no
  live hot-swap required for v1. Honest documented behavior.
- Legacy/missing config decodes to the `"pill"` default (mirror the mascot's
  `decodes_legacy_missing_fields_as_defaults` pattern).

### Area 3 — Pill states, content + visual register (PILL-03)
- **Consume EXISTING frames:** reuse the mascot's `ws_client` path on `ws://127.0.0.1:8765`
  (`ipc.session.snapshot` + `ipc.session.cohost-reaction`). NO new port, NO Python delivery change.
- **States:** `idle` / `listening` / `speaking` / `expand-on-event`. Expand shows the reaction
  text + citation strip + deck-context chips, then collapses back to the compact pill.
- **Real TTS waveform:** driven by `Levels.update_voice` (the AI-speech RMS already on the bus)
  during `speaking` — not a fake animation.
- **Citation strip:** the existing EvidenceRegistry chip strip (the same `[key:…]`/`[ev:…]`
  grounded chips), so the pill carries the anti-slop proof surface.
- **Deck-context chips:** Phase 59 deck-state is COMPLETE, so deck chips land here — title/key/BPM
  per resolved deck, honest `unknown` when unresolved (never a false-confident guess).
- **Visual register:** CDJ-Whisper / Super-Whisper — 5 warm blacks, single amber accent at 20/80,
  Saira + JetBrains Mono, tactility via faint glow not faux-3D bevels (the `frontend-enforcement`
  skill governs this; baseline `mocks/vibemix-direction-final.html`). Compact pill, no AI-slop copy.

### Area 4 — Scope boundaries
- **IN:** pill window + 4 states + TTS waveform + citation strip + deck chips + `primary_surface`
  config + `"pill"` capability allowlist + drag/focus/transparency engineering + multi-monitor clamp.
- **KAAN-ACTION (felt, on the built app):** drag-on-unfocused-window feel, focus non-steal
  (keystrokes reach the DJ app after clicking the pill), transparency parity on the `.dmg`,
  multi-monitor behavior. Surface, do not pause (`gsd-autonomous fully`).
- **OUT (no scope creep):** notch-locked pill, any new ws port, any Python delivery change,
  retiring/deleting the mascot, new AI providers.

### Claude's Discretion
- Exact pill dimensions, collapse/expand animation curve, drag-handle placement, and the precise
  glass rgba stack — bounded by the CDJ-Whisper register + `frontend-enforcement` skill.
- Internal module layout of `pill_window.rs` vs shared helpers extracted from `mascot_window.rs`.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tauri/src-tauri/src/mascot_window.rs` — the clone source: `transparent(true)`,
  `always_on_top(true)`, `decorations(false)`, `skip_taskbar(true)`, geometry-persist with 200ms
  debounce, `default_top_right`/`primary_logical_size` placement, `install_geometry_listener`,
  and a `label_constant_matches_capability_allowlist` test. (Do NOT copy `set_ignore_cursor_events`.)
- `tauri/src-tauri/src/config.rs` — `KEY_MASCOT_WINDOW` + `read/write_mascot_window_state`
  + serde roundtrip + legacy-missing-fields-default tests. `primary_surface` slots in here.
- `tauri/src-tauri/src/ws_client.rs` — existing ws:8765 consumer; the pill reuses it.
- `tauri/src-tauri/capabilities/default.json` — single capability file; add the `"pill"` window.
- `tauri/ui/mascot.html` (Three.js rig) — the secondary surface; must keep working (`mascot-audit`).
- `mocks/vibemix-app-ui.html` + `mocks/vibemix-direction-final.html` — visual contracts.

### Established Patterns
- Second-window pattern already exists (`mascot_window`, `debrief_window`) — pill is a third.
- The mascot is ALREADY opt-in (visible default false, "2026-05-19 opt-in decision") — so
  `primary_surface="pill"` default is a clean continuation, not a fight with current behavior.
- One-socket invariant: everything on `ws://127.0.0.1:8765`; the pill consumes, never adds a port.

### Integration Points
- `main.rs` window/setup wiring (`mod mascot_window;` → add `mod pill_window;`).
- `config.rs` create-on-startup branch chooses the surface from `primary_surface`.
- `capabilities/default.json` allowlist for the new window label.
- `ws_client.rs` frame fan-out to whichever surface(s) are active.
</code_context>

<specifics>
## Specific Ideas
- "Super-Whisper pill" is the explicit reference form (compact, glassy, always-on-top, draggable).
- The drag/focus/transparency spike is THE phase risk — "the single most likely 'looks done but
  feels broken' failure" — resolve on the built app before polishing the UI.
- Mascot is demoted, NOT deleted — a deliberate, Kaan-approved partial reversal.
</specifics>

<deferred>
## Deferred Ideas
- Live hot-swap between pill ↔ mascot mid-session (v1 applies surface choice at session start).
- Notch-locked / menubar-docked pill variants (explicitly out of scope per project memory).
- Pill-driven controls that send commands back to Python (one-way consume only for v1).
</deferred>
