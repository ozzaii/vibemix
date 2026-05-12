# Phase 12: Live Session UI + Settings Panel - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning
**Mode:** Smart discuss — autonomous; recommendations auto-accepted per `/gsd-autonomous fully`.

<domain>
## Phase Boundary

Phase 12 lifts the Phase 11 Tauri shell from "wizard complete" into the **live in-session UI** plus a **Settings panel** that wires mid-session changes (voice / mode / genre / output / retention / push-to-mute hotkey) through to the running Python sidecar.

Owns:
- Live session view in `tauri/ui/src/session/` — meters, phase tape, AI transcript scroll, drop countdown, MIDI event ribbon. Renders at 30 fps off the existing WS bus on `127.0.0.1:8765`.
- Settings panel in `tauri/ui/src/settings/` — voice / mode / genre / output picker, recording retention slider, push-to-mute hotkey capture, "Re-run calibration" button (wires Phase 11's `ipc.wizard.start`).
- New `ipc.session.*` and `ipc.settings.*` message families on the same WS bus + JSON Schema entries in `tauri/ui/src/ipc/messages.schema.json` (extends Phase 11 schema; CI gate stays the same).
- Settings persistence — extends the Phase 11 `config.json` with `voice`, `mode`, `genre`, `output_id`, `retention_days`, `push_to_mute_hotkey` fields.
- Live status badge bar (LiveKit / Gemini / MIDI / screen) — visual surface for the `ipc.status.tick` schema Phase 11 already defined.
- Push-to-mute system-wide hotkey via `tauri-plugin-global-shortcut`; on activation Tauri sends `ipc.session.mute` which drains `PlaybackQueue` on the Python side.
- Python sidecar surface: a thin handler module `src/vibemix/runtime/ipc_handlers.py` (extends Phase 11's wizard handlers) that routes `ipc.session.*` and `ipc.settings.*` to the running `vibemix.runtime.session_manager` for hot-reload of settings.

Does NOT own:
- Reactive mascot integration (Phase 13 — Phase 12 reserves the same 256×256 corner already wired in Phase 11).
- FL-Studio-tier visual polish loop (Phase 14).
- Recording browser / playback UI (Phase 15 — Phase 12 only exposes the retention setting, not the file browser).
- Signed/notarized installer (Phase 18).
- Auto-update wiring (Phase 18).
- New IPC transport (still WS bus; no IPC redesign).
- Mid-session genre profile creation (Phase 10 owns the profile matrix; Phase 12 only triggers reload by `genre` key).

</domain>

<decisions>
## Implementation Decisions

### Area 1: Live Session UI Architecture & Performance

- **Render loop:** Single `requestAnimationFrame` loop in `tauri/ui/src/session/render-loop.ts` consumes the latest WS message snapshot (last-write-wins ring buffer; 30 fps target). No per-component rAF. CSS `transform` + `opacity` only for hot elements (meter bars, phase tape head, countdown digits) — no layout thrash. Document confirmed in `frontend-enforcement` motion budget.
- **State pipeline:** Pure-function components from Phase 11 stay pure — each session component is `function MeterBar(state): HTMLElement` taking the current `SessionState` snapshot. A central `tauri/ui/src/session/state.ts` holds the active `SessionState`, updated by the WS client. Components diff by reference; rerender via small targeted DOM mutations (no virtual DOM, no React).
- **Performance budget:** 30 fps hard floor on Retina + 1080p externals. CSS variables (already in `tokens.css`) drive meter heights via `--meter-rms-music` etc. — JS only touches the variable, browser repaints the bar. Validated with `requestAnimationFrame` frame-timing logged to dev console in DEBUG mode.
- **Transcript scroll:** Capped 200-line ring; auto-scrolls to bottom unless user scrolled up (sticky-to-top behaviour). Each new AI line slides in 200ms ease-out. Old lines fade `--ink` → `--ink-dim` over the last 20 entries.
- **Drop countdown:** DSEG7 48px hero numeric. Surfaces only when `MusicState.phase == "BUILDUP"` AND `events.detector` predicts a drop within 16 bars — pulses 1× per beat (BPM-synced via WS tick).
- **MIDI event ribbon:** Horizontal scrolling chip strip below transcript, last 12 seconds of controller events (lifts Phase 11 controller silhouette glyphs + a one-line label per event). Auto-fades old chips `--phosphor` → `--ink-engraved` over 12s.

### Area 2: Settings Panel UX & Persistence

- **Surface form:** Right-side slide-over drawer triggered by a gear-glyph button in the titlebar (Workbench glyph, never an emoji). Drawer width 400px, height = full window minus titlebar. Slides in/out 250ms ease-in-out. NOT a modal; live session keeps rendering in the background at reduced opacity (0.75). Closing returns to live UI.
- **Mid-session change behaviour:**
  - **Voice / mode / hotkey** → hot-apply (next TTS turn picks up new voice; `mode` swap re-arms event detector with new template; hotkey re-binds immediately).
  - **Genre** → hot-apply with a 250ms "RELOADING PROFILE…" Workbench overlay on the panel (re-loads `genre_profile_*.json` via `ipc.settings.set_genre`).
  - **Output device** → hot-apply (Phase 2/7 audio core already supports `restart_output_stream`; Settings just calls `ipc.settings.set_output_device`).
  - **Retention** → persists immediately to `config.json` (Phase 15 reads on next boot; doesn't disturb running session).
  - **Push-to-mute hotkey** → re-binds the global shortcut immediately, persists to config.json.
- **"Restart required" surface:** None of the v1 settings require restart. The "restart to apply" badge component is still implemented (per success criterion 2) so Phase 15+ phases can use it; it shows on hover over any setting tagged `restart_required: true` in the schema. v1 ships with zero such settings.
- **Voice options:** Read from `vibemix.tts.voice_registry.list_voices()` (Phase 4 cascade has voice IDs hardcoded; Phase 12 surfaces them as a dropdown — `kore` / `puck` / `charon` / `fenrir` / `aoede` / `leda` / `orus` / `zephyr`). Currently selected voice marked with `--phosphor` + AUTO-style badge.
- **Mode rocker:** 2-state rocker switch (Hype / Coach) lifting the mock's `.rocker` component from `mocks/vibemix-app-ui.html` lines 642-700. Lit position = `--phosphor`. Click = animated flip 200ms.
- **Genre dropdown:** Same dropdown component pattern as Phase 11 device picker. Options pulled from `vibemix.prompts.genre_profiles.list_profiles()` (returns `['house', 'tech-house', 'techno', 'dnb', 'trance', 'hip-hop', 'edm-generic']` per Phase 6/10).
- **Recording retention:** Slider 1d / 3d / 7d / 14d / 30d / never (6 stops). Default = 7d. DSEG7 numeric readout above slider shows current selection in `--phosphor`.

### Area 3: Push-to-Mute Hotkey

- **Default hotkey:** `Cmd+Shift+M` (macOS) / `Ctrl+Shift+M` (Windows). Both ship hard-coded as defaults; user can rebind via the capture component.
- **Capture component:** "PRESS NEW HOTKEY" Workbench 11px row in Settings. On focus, swallows all key events until a non-modifier+modifier combo is captured. Stores as `{mods: ['cmd','shift'], key: 'M'}`. Validates against OS reserved combos (rejects `Cmd+Q`, `Cmd+W`, `Cmd+Tab`, etc.).
- **Implementation:** `tauri-plugin-global-shortcut` registered at Tauri startup. On trigger, Tauri sends `ipc.session.mute` (`payload: { toggle: true }`) to Python sidecar. Python drains `PlaybackQueue` immediately (`queue.clear()` + sets `mic_open_for_seconds=0` so mic re-gate happens cleanly), sets `session.muted = true`. Second keypress sends same message; Python flips `session.muted = false`. Recording (input.wav + voice.wav) continues regardless of mute state.
- **Visual feedback:** When muted, a `--rec`-tinted overlay banner appears above the transcript: `● MUTED — press {hotkey} to resume`. AI transcript pauses incoming-line animations until unmuted.

### Area 4: Status Badge Bar (UX-11 surface)

- **Position:** Bottom status bar (already in Phase 11 layout). Phase 12 fills it with the 4 live badges driven by `ipc.status.tick` (10Hz heartbeat from sidecar — `vibemix.runtime.state_refresh_loop` writes the tick).
- **Visual:** 4 LED dots (8px each) + 9px Workbench UPPERCASE 0.22em label per badge. States: `ok` → `--ok` LED + ink label; `connecting` → `--phosphor` LED slow-pulse (1.4s) + dim label; `down` → `--rec` LED + `--rec` label.
- **MIDI badge:** Special case — instead of binary, shows controller count (e.g. `● MIDI · 1`). If hot-unplug detected via watcher (2s threshold per Phase 11 spec), flips to `--rec` `● MIDI · 0` within ≤2s (matches success criterion 4).
- **Click affordance:** Click on any badge in `down` state opens a tooltip with last error message + `[ Recheck ]` button (sends `ipc.status.recheck` to sidecar). Tooltip uses `--rec` border + brushed-charcoal background, 200ms fade-in.

### Area 5: WS Message Schema & Hot-Reload Contract

- **New message families:**
  - `ipc.session.snapshot` — 30Hz from sidecar — `{music: Levels, voice: Levels, mic: Levels, phase: str, bpm: float, drop_pred: int|null, transcript_delta: [{role, text, ts}], midi_events: [{control, value, ts}], track: {title, artist, deck} | null}`
  - `ipc.session.mute` — bidirectional — `{toggle: bool}` from Tauri; sidecar acks with new state in next `ipc.session.snapshot`.
  - `ipc.settings.set_voice` / `set_mode` / `set_genre` / `set_output_device` / `set_retention` / `set_hotkey` — Tauri → sidecar. Each ack'd in next `ipc.status.tick` with new effective settings.
  - `ipc.settings.get` — Tauri → sidecar. One-shot snapshot of full settings.
- **Schema location:** Extends `tauri/ui/src/ipc/messages.schema.json` (Phase 11 file). Same CI gate (`scripts/check_ipc_schema.py`) validates Python dataclasses + TS types stay in sync.
- **Hot-reload contract:** Settings handler module reads current `SessionManager` instance, applies the change (mutate config + call appropriate `restart_*` / `reload_*` method), writes new config to disk via `vibemix.config.persistence`, returns ack.

### Claude's Discretion

- Exact rAF + Frame-Timing API instrumentation for the 30 fps validation.
- Whether transcript auto-scroll uses `scrollIntoView({behavior: 'smooth'})` vs CSS-only sticky bottom.
- Gear glyph SVG path (drawn inline in `tauri/ui/src/session/icons/gear.svg.ts`).
- Exact 6-stop retention slider visual (knurled-knob slider vs segment-LED ticks — pick whichever maps more cleanly to mock vocabulary).
- File-split granularity inside `tauri/ui/src/session/` and `tauri/ui/src/settings/` — break into `components/`, `state.ts`, `render-loop.ts`, `ws-bridge.ts` per Phase 11 wizard pattern.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tauri/ui/src/tokens.css` — token source-of-truth, lifted from `mocks/vibemix-app-ui.html`. Phase 12 adds ZERO new tokens unless they exist in the mock.
- `tauri/ui/src/ipc/messages.schema.json` + `messages.ts` + `client.ts` + `validator.ts` — Phase 11 WS bridge. Phase 12 extends with new message types only.
- `tauri/ui/src/wizard/*` — pure-function component pattern + `registerStyle()` singleton CSS injection. Phase 12 replicates the pattern under `tauri/ui/src/session/` and `tauri/ui/src/settings/`.
- `tauri/ui/src/main.ts` — router entry. Phase 12 adds `route.session()` + `route.settings()` and wires the post-wizard transition.
- `tauri/ui/src/crash-banner.ts` — reusable for session-time crashes.
- `src/vibemix/runtime/ws_bus.py` — WS server already accepts arbitrary `ipc.*` message families; Phase 12 just registers new handlers.
- `src/vibemix/runtime/state.py` — `MusicState` already holds `phase`, `bpm`, `mic` levels, `controller_state`. Phase 12 reads it to build the `ipc.session.snapshot` payload.
- `src/vibemix/runtime/audio.py` — `PlaybackQueue.clear()` already exists (Phase 2). Phase 12 mute handler calls it.
- `src/vibemix/tts/cascade.py` — voice IDs hardcoded as a list — easy to surface to Settings.
- `src/vibemix/prompts/matrix.py` + `src/vibemix/prompts/genre_profiles/*.json` — Phase 6/10 profile matrix; Phase 12 just calls `reload_profile(name)`.
- `mocks/vibemix-app-ui.html` — visual reference for every component (meters lines 758-823, rocker 642-700, transcript 956-1024, drop chip 871-910, MIDI ribbon ~1042-1098, status bar 1112-1135).

### Established Patterns
- Pure-function components (`function ComponentName(state): HTMLElement`) returning HTMLElement — no JSX, no React, no virtual DOM.
- Component-scoped CSS via `registerStyle()` singleton injecting `<style data-component="name">` once per page load.
- IPC validated through `validator.ts` against JSON Schema (Ajv) — every inbound + outbound message goes through validation.
- WS reconnect with exponential backoff already in `client.ts` (Phase 11).
- `tokens.css` is the single visual source of truth — components reference `var(--phosphor)` etc., NEVER hardcoded hex.

### Integration Points
- Wizard exit (Phase 11 smoke test) → `route.session()` swap; tears down wizard DOM, mounts live session DOM.
- WS bus already broadcasts `levels` updates (Phase 4); Phase 12 SessionState consumes those + new `ipc.session.snapshot` messages.
- Tauri menu / titlebar — Phase 11 owns titlebar; Phase 12 adds the gear-glyph button at titlebar right edge.
- `config.json` extension is additive — Phase 11 config keys remain readable; new keys default to sane values on first read.

</code_context>

<specifics>
## Specific Ideas

- **Visual fidelity to `mocks/vibemix-app-ui.html`**: Phase 12 IS the live session UI from the mock. Treat that file as the executable design spec. The meter bars, phase tape, transcript pane, drop chip, MIDI ribbon, status bar — all lift visually 1:1. Window is 1240×~860 (mock dimensions). NOT a "phase 12 reinterpretation" — port the mock.
- **30 fps is the floor, not the ceiling**: A 60 fps render is ideal but 30 fps is the success criterion. Use CSS `transform`/`opacity` for hot-path animations to free up the main thread.
- **One single accent color**: `--phosphor` amber. NO blue "info" tones, NO yellow "warning" tones except the existing `--rec`/`--ok` status dots. The Settings drawer is `--panel-lift` gradient, the active setting row is `--phosphor-soft` tinted background, lit elements glow `--phosphor`. That's it.
- **Mute is mid-utterance**: Drain `PlaybackQueue` instantly. AI voice cuts mid-word — that's correct behaviour. Recording continues uninterrupted (success criterion 3).
- **Settings drawer over modal**: Modals break flow. A drawer keeps the live session visible at 0.75 opacity behind it — DJ can still see what's happening while they tweak.
- **Status badge hot-unplug**: USB pull → MIDI badge red within 2s. The 2s watcher already exists (Phase 11). Phase 12 just renders the state.
- **Push-to-mute is the only system-wide hotkey** in v1. No "next track", no "skip event", no "trigger reaction". One hotkey = one job.
- **Mascot reserved corner stays empty**: Phase 13 owns it. Phase 12 renders the same 1px dashed outline + "AVERY · arriving phase 13" label as Phase 11.

</specifics>

<deferred>
## Deferred Ideas

- **Recording browser / playback UI** — UX-15 / Phase 15.
- **Mascot reactive integration** — MASCOT-01..03 / Phase 13.
- **Multi-hotkey support** (event skip, manual trigger) — post-v1.
- **Light theme** — explicitly out per Phase 11 dark-only decision.
- **Custom voice synthesis / voice cloning** — out of scope, Gemini TTS only.
- **Mid-session profile editor** (genre creator UI) — post-v1; Phase 10 covers profile authoring out-of-band.
- **Telemetry dashboard / event log viewer** — Phase 16 verification harness has its own surface.
- **Multi-monitor support / detached panels** — post-v1.
- **Settings export / import** — post-v1.
- **Linux** — explicitly out per PROJECT.md.

</deferred>
</content>
</invoke>