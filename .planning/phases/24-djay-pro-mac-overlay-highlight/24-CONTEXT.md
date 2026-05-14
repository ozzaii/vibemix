# Phase 24: djay Pro Mac Overlay Highlight - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — auto-accepted recommended decisions)

<domain>
## Phase Boundary

Amber ring fires on the exact djay Pro UI element the AI just cited — Beat A of viral demo ("AI points at the knob"). Second Tauri `WebviewWindow` (transparent, always-on-top, click-through) tracks djay Pro window bounds @10Hz. AX (macOS Accessibility) bridge in Tauri Rust parent — sidecar requests rect via `ipc.overlay.ax_position`. **Mac-only in v2.0.**

**Critical scope boundary:** Wave 0 day-1 AX-from-Rust-parent feasibility spike on code-signed bundle (Pitfall 3 prevention) — verifies kyleawayan/djay-pro-bridge pattern works on installed signed app, NOT just `tauri dev`. Per STATE: AX from Rust parent NEVER from Python sidecar (Tauri #8329) — codebase grep gate fails CI if `Quartz.CGWindowListCopyWindowInfo` or `AXUIElement` appears in `src/vibemix/runtime/highlight/`. If Wave 0 spike fails, phase blocks and degrades to percentage-of-window-rect coord_map only (still ships, accuracy degrades).

</domain>

<decisions>
## Implementation Decisions

### Architecture Constraint (LOCKED — per STATE + Pitfall 3)
- AX bridge lives ONLY in Tauri Rust parent: `tauri/src-tauri/src/ax_bridge.rs`.
- Python sidecar requests rects via IPC: `ipc.overlay.ax_position`.
- AX NEVER called from Python (Tauri #8329 — sidecar permissions can't inherit AX from parent).
- CI grep gate in `.github/workflows/lint.yml`: fails build if `Quartz.CGWindowListCopyWindowInfo` OR `AXUIElement` appears anywhere under `src/vibemix/runtime/highlight/`.

### Wave 0 AX Spike (LOCKED — per STATE + Pitfall 3)
- 1-day spike, Day-1 of phase: verify kyleawayan/djay-pro-bridge AX pattern works on a CODE-SIGNED installed bundle (NOT `tauri dev`).
- Spike artifact: `.planning/phases/24-.../WAVE-0-AX-SPIKE.md` with verdict.
- Spike PASS: phase ships AX-driven precise positioning.
- Spike FAIL: phase ships percentage-of-window-rect coord_map fallback (still functional, accuracy degrades from "knob-precise" to "EQ-region-approximate").
- Spike FAIL is NOT a phase block per `feedback_autonomous_no_grey_area_pause` — degraded ship is acceptable.

### Overlay Window (LOCKED — per success criteria)
- Second Tauri `WebviewWindow` (label="overlay"):
  - `transparent: true`
  - `always_on_top: true`
  - `decorations: false`
  - `set_ignore_cursor_events(true)` (click-through)
- Window tracker @10Hz follows djay Pro window bounds (move/resize/fullscreen-Spaces detection).
- Bounds polling via Quartz `CGWindowListCopyWindowInfo` from Rust parent (NOT sidecar).

### Pointable Elements (LOCKED — per success criteria)
- 12 hand-mapped djay Pro v5 elements:
  - Mid EQ × 2 decks
  - High EQ × 2 decks (NOTE: roadmap text lists "mid/high/low EQ × 2 decks" + 6 others = 12 total)
  - Low EQ × 2 decks
  - Gain
  - Filter
  - Fader
  - Jog
  - Play, Cue, Sync, Tempo slider, Hot cues
- Element JSON shipped at `tauri/ui/src/overlay/elements.json`.
- v2.0 = djay Pro v5 only; other DJ apps (Rekordbox DJ, Serato, Traktor, Mixxx) deferred to v2.1+.

### Ring Renderer (LOCKED — per success criteria + Pitfall 13)
- Canvas 2D ring renderer in overlay WebviewWindow.
- Amber `--ring-active` token per CDJ Whisper v5 palette (`project_visual_direction_cdj_whisper`).
- Animation: fade-in 200ms → hold 800ms → fade-out 300ms.
- 8s cooldown per element (avoids ring-spam on rapid same-element citations).
- At-most-one-ring-per-3s utterance budget (avoids visual chaos when AI fires multi-citation lines).

### Edge-Case Mitigations (LOCKED — per Pitfall 4 + Pitfall 13)
- **Fullscreen-Spaces toast (Pitfall 4)**: when djay enters fullscreen, surface inline notice "Highlights work best in windowed djay — full-screen Spaces hide overlays (macOS limitation)". One-time-per-session, dismissible.
- **Multi-monitor coord-space (Pitfall 13)**: ALL Quartz coord, NO NSScreen mixing. Dual-monitor smoke test gate in CI.
- README docs (Phase 26) include "windowed djay recommended" for overlay use.

### POC Port-From (LOCKED — per CLAUDE.md POC rule)
- Window-finding logic in `cohost_v4.py` (Quartz `CGWindowListCopyWindowInfo` djay window crop) — port pattern to Rust, NOT to Python sidecar.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tauri/src-tauri/src/sidecar.rs` — Phase 11 sidecar pattern; overlay window join here.
- `tauri/src-tauri/tauri.conf.json5` — capability allowlist; second WebviewWindow + AX entitlement added.
- `tauri/ui/src/overlay/` — NEW dir for overlay React entry point.
- Phase 18 EvidenceRegistry — citation source includes `[screen:<key>]` element ID, fed to overlay.
- `cohost_v4.py` Quartz window-find pattern — port-from REFERENCE (rewrite in Rust).

### Established Patterns
- 3-process architecture: Tauri Rust shell + Python sidecar + FastAPI proxy. v2.0 adds ZERO new processes — overlay = SAME Tauri parent, second WebviewWindow only (per STATE).
- IPC over WebSocket `127.0.0.1:8765` — extend with `ipc.overlay.*` namespace.
- Hand-written `@dataclass(frozen=True, slots=True)` + jsonschema Draft-07 (no pydantic).
- macOS TCC entitlement chain — bundle ID `world.bravoh.vibemix` LOCKED.

### Integration Points
- `[screen:<element_id>]` citation in Gemini response → linter validates → overlay fires ring.
- Phase 20 `CitationLinter` consumer side emits `ipc.overlay.cite` with element_id + lifetime.
- AX bridge `ax_position(bundle_id, element_role) -> Rect` — Rust parent function exposed via IPC.
- Window tracker @10Hz in Rust parent → broadcasts bounds via `ipc.overlay.window_bounds`.

</code_context>

<specifics>
## Specific Ideas

- Wave 0 (Day-1, 1 day): AX-from-Rust-parent on code-signed bundle spike → WAVE-0-AX-SPIKE.md verdict.
- Wave 1: second WebviewWindow scaffold (transparent + always-on-top + click-through + window tracker @10Hz).
- Wave 2: AX bridge in Rust + `ipc.overlay.ax_position` IPC + CI grep gate (Pitfall 3 fully closed).
- Wave 3: 12-element JSON map + Canvas 2D ring renderer + animation timings + cooldowns.
- Wave 4: fullscreen-Spaces toast (Pitfall 4) + multi-monitor coord-space all-Quartz (Pitfall 13).

</specifics>

<deferred>
## Deferred Ideas

- Windows overlay support (v2.x — Mac-only in v2.0 per STATE).
- Other DJ apps (Rekordbox DJ, Serato, Traktor, Mixxx) — v2.1+ (djay Pro v5 only in v2.0).
- AX-element auto-discovery (v2.x — 12 hand-mapped in v2.0).
- Color-coded rings per citation type (v2.x — single amber in v2.0).
- Multi-element ring chains (e.g., "fader → mid EQ" sequence) — v2.x.
- User-customizable ring style/color (v2.x).
</deferred>

---

*Phase: 24-djay-pro-mac-overlay-highlight*
*Context gathered: 2026-05-14 (smart discuss, fully autonomous)*
