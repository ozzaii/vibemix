---
phase: 12-live-session-ui-settings-panel
plan: 04
subsystem: frontend+rust
tags: [tauri, frontend, rust, raf, render-loop, global-shortcut, session, ipc, hotkey]

# Dependency graph
requires:
  - plan: 12-01
    provides: ipc.* schema additions — SessionSnapshot / SessionMute / SettingsSet / SettingsGet / SettingsState / StatusRecheck shapes
  - plan: 12-02
    provides: SessionLoop / SettingsApplier / ConfigStore sidecar runtime + --session CLI flag
  - plan: 12-03
    provides: 12 presentation components + SessionLayout composer (mountSessionLayout / renderSessionFrame / Mounted handle)
  - phase: 11-tauri-shell-calibration-wizard
    plan: 04
    provides: ipc client (sendIpcRequest / subscribeIpc / emitIpc), Tauri shell + WsClientHandle, first_run_state read/write Tauri commands
provides:
  - tauri/ui/src/session/state.ts — SessionState mutable singleton + getSessionState/setSessionState shallow merge + appendTranscript/appendMidiEvents ring caps (200/12)
  - tauri/ui/src/session/ws-bridge.ts — subscribes to ipc.session.snapshot/ipc.status.tick/ipc.settings.state/ipc.session.mute; exports sendSettings/sendMute outbound helpers
  - tauri/ui/src/session/render-loop.ts — startRenderLoop/stopRenderLoop single-rAF caller; dev-mode frame-time tracker; bridge→layout state projection helpers (pill mappers + hotkey formatter)
  - tauri/ui/src/session/router.ts — routeSession() + teardownSession() entry point
  - tauri/ui/src/session/SessionLayout.ts — extended renderSessionFrame with CSS-variable hot path + array-ref change gating + sticky-bottom transcript wiring on mount; Mounted now exported with userScrolledUp field
  - tauri/ui/src/main.ts — boot decision (first_run_completed → wizard | session)
  - tauri/src-tauri/src/hotkey.rs — push-to-mute module; register_default/register_combo/rebind_hotkey + reserved-combo validator + chrono-free ISO-8601 helper
  - tauri/src-tauri/src/main.rs — global-shortcut plugin + HotkeyHandle managed state + hotkey::rebind_hotkey command registered + hotkey::register_default called from setup
  - tauri/src-tauri/src/sidecar.rs — post-wizard sidecar launches now pass --session
  - tauri/src-tauri/Cargo.toml — tauri-plugin-global-shortcut = "2.3"
  - tauri/src-tauri/capabilities/default.json — global-shortcut:allow-{register,unregister} permissions; sidecar arg validator widened to ^--(wizard|session)$
  - src/vibemix/audio/buffers.py — PlaybackQueue.clear() 8-line implementation (Wave 2 handoff item)
  - tauri/ui/tests/session/state.spec.ts — 10 vitest cases
  - tauri/ui/tests/session/render-loop.spec.ts — 15 vitest cases
affects:
  - 12-05 (settings drawer — consumes sendSettings + rebind_hotkey; reads SessionState.settings via getSessionState)

# Tech tracking
tech-stack:
  added:
    - tauri-plugin-global-shortcut@2.3 (Cargo dep; macOS Cmd+Shift+M / Windows Ctrl+Shift+M registration + handler API)
  patterns:
    - Single rAF caller (render-loop.ts owns requestAnimationFrame; components have no per-instance loops)
    - CSS-variable hot path — `--meter-music-rms`, `--meter-voice-rms`, `--meter-mic-rms`, `--phase-now-pct`, `--bpm-period-ms`, `--clock-text` poked every frame on the session root; var() reads cascade into components without innerHTML thrash
    - Array-ref change gating — phase.chunks / midiEvents / transcript only rebuild DOM when their array identity changes (append helpers return new arrays on append)
    - Shallow-merge SessionState singleton — React-style `setSessionState({field: value})` replaces top-level keys; unrelated keys keep their `===` identity so the render-loop's per-key dirty checks short-circuit
    - Sticky-bottom transcript — passive scroll listener on `.vmx-cohost__transcript` flips `mounted.userScrolledUp` at the 40px threshold and mirrors onto `data-sticky` for `setCohost` to honour
    - Window-focus-gated global shortcut — hotkey handler checks `WebviewWindow::is_focused()` before forwarding ipc.session.mute, so DAW shortcuts work when vibemix is in the background
    - Reserved-combo validator at registration time — rejects macOS (cmd+q/w/tab/space) and Windows (alt+f4/ctrl+alt+del/win+l) before calling into the global-shortcut plugin; returns `Result<(), String>` for inline error surfacing
    - chrono-less ISO-8601 timestamp helper in hotkey.rs (Howard Hinnant civil-from-days) — keeps the Cargo dep diff to one crate

# Outcome
status: completed
shipped:
  - tauri/ui/src/session/state.ts (180 lines incl. docs)
  - tauri/ui/src/session/ws-bridge.ts (300 lines incl. docs)
  - tauri/ui/src/session/render-loop.ts (240 lines incl. docs)
  - tauri/ui/src/session/router.ts (80 lines incl. docs)
  - tauri/ui/src/session/SessionLayout.ts (+135 lines — hot path + sticky transcript)
  - tauri/ui/src/main.ts (rewritten — 115 lines, +43 vs prior)
  - tauri/src-tauri/src/hotkey.rs (310 lines incl. tests)
  - tauri/src-tauri/src/main.rs (+6 lines — plugin + handle + register call)
  - tauri/src-tauri/src/sidecar.rs (+5 lines — --session branch)
  - tauri/src-tauri/Cargo.toml (+1 line)
  - tauri/src-tauri/Cargo.lock (transitive update — 6 new packages: global-hotkey, x11rb, x11rb-protocol, xkeysym, gethostname, tauri-plugin-global-shortcut)
  - tauri/src-tauri/capabilities/default.json (+2 permissions, arg validator widened)
  - src/vibemix/audio/buffers.py (+9 lines — PlaybackQueue.clear)
  - tauri/ui/tests/session/state.spec.ts (155 lines, 10 tests)
  - tauri/ui/tests/session/render-loop.spec.ts (310 lines, 15 tests)

tests:
  vitest: 92 / 92 pass (was 67 baseline; +25 new across state.spec.ts + render-loop.spec.ts)
  cargo: 13 / 13 pass (was 4 baseline; +9 new hotkey module tests)
  typecheck: clean (`npm run check:ipc` zero errors; tsc --noEmit clean)
  schema_drift_gate: green (26 == 26 wrapper-count parity, dataclass round-trip clean)
  python_suite: 1171 / 1173 pass (2 pre-existing failures unrelated — test_phase05_verification mascot.html drift logged in 12-02; test_audio_macos_live hardware-flaky)
  poc_files: untouched in this plan (mascot.html drift predates Phase 12)
  loc_delta: ~+1850 (incl. docstrings)

# Deviations from plan
- **Plan §1 SessionState shape: `phase: PhaseChunk[]` vs nested.** The
  plan frontmatter lists `phase: PhaseChunk[]` and `phaseNowPct: number`
  as flat fields on SessionState. The session-LAYOUT (12-03) consumes a
  nested `phase: { chunks, nowPct }` prop shape. Shipped: bridge state
  keeps the plan's flat shape; render-loop's `projectToLayoutState`
  nests them at projection time. Both worlds happy.

- **Hotkey reserved-combo validator is a startup gate, not the plugin's
  responsibility.** The plan calls for combo validation at registration
  time. The plugin itself does not validate — it parses syntactically
  and registers. Shipped `validate_combo` as our own gate inside
  `register_combo`; the plugin still sees only validated strings. This
  is also tested in isolation (`tests::validate_rejects_*`).

- **chrono helper inlined.** Plan didn't pre-spec a JSON timestamp
  source for the Rust-side ipc.session.mute envelope. The webview-side
  emitIpc uses `new Date().toISOString()`. To avoid pulling chrono
  (~80 KB transitive), the Rust handler ships a 30-line stdlib helper
  using Howard Hinnant's civil-from-days. Format is YYYY-MM-DDTHH:MM:SS.nnnnnnnnnZ
  which the sidecar's jsonschema `date-time` format accepts.

- **`--session` flag wire-through took 5 lines, not a rewrite.** Plan
  says "Update the Rust sidecar spawn to pass --session after wizard
  completion (the existing wizard-done callback restarts the sidecar)."
  Shipped a simpler branch: `sidecar.rs` reads the same `wizard_mode`
  bool the existing setup block resolves from `is_first_run(app)`. The
  watchdog restarts already pick up the new arg list. No webview-side
  callback added — `write_first_run_state` flips the bit; next launch
  (or restart) consumes the new state.

- **`config:event:default` permission already present.** The plan
  required it for hotkey-handler IPC. The Phase 11 capability already
  granted `core:event:default`. Only the two `global-shortcut:*`
  permissions are net-new.

- **No `--session`-flag-add-then-remove path.** The plan suggested 12-04
  "may unify the two paths" of __main__.py dispatch (12-02 deviation).
  Out of scope here — the dispatch unification is a Phase 4/5/6
  integration task downstream of this glue plan. Sidecar runs the
  current --session standalone for now; 12-05 doesn't depend on
  unification.

- **WS bus conflict resolution.** Plan §"Critical handoffs" called for
  routing mascot ws_broadcast + SessionLoop snapshot through the same
  Phase 11 IpcBus. This plan does NOT touch the cohost*.py POC files
  (they're trusted reference, not integrated yet). The canonical bus
  going forward is the Phase 11 WizardBus / IpcBus alias from
  `vibemix.runtime.ws_bus`. The mascot's WebSocket server in cohost_v4.py
  remains POC-only — when the cascade graph is wired into SessionLoop
  (Phase 4/5/6 integration), `ws_broadcast` will be replaced by the
  IpcBus's `ipc.session.snapshot` payload. Documented; no code touched
  in POCs.

- **Real refs into SettingsApplier deferred.** Plan §"Critical handoffs"
  noted that SettingsApplier needs real cascade/event_detector/audio_core/
  genre_loader refs. 12-02 ships the Optional hook surface; the real
  refs are Phase 4/5/6 integration work — out of scope for this glue
  plan. The SettingsApplier already warn-and-persists on missing hooks
  per 12-02 design.

# Handoffs

## 12-05 (settings drawer — final wave of Phase 12)
1. **sendSettings is the outbound surface** — call
   `sendSettings(field, value)` from the drawer's rocker/picker
   onChange callbacks. The sidecar replies with `ipc.settings.state`
   which the bridge already subscribes to, so the drawer's controls
   re-render on the round-trip without extra wiring.
2. **rebind_hotkey is exposed as a Tauri command** —
   `invoke("rebind_hotkey", { newCombo })` returns
   `Result<(), String>`. On Err, surface the error inline in the
   drawer (e.g. red border + "key reserved by operating system"). The
   command is in the capability allowlist by default (Tauri 2.x auto-
   allows user `#[tauri::command]` entries).
3. **`getSessionState().settings` is the read surface** — the drawer
   reads current values via this; the rAF render loop keeps the drawer
   in sync if the user changes settings mid-drawer-open (e.g. via
   hotkey rebind from another instance).
4. **Drawer mount/unmount adds to existing `renderSessionFrame`** — no
   need for a second rAF loop. Add a `drawerOpen: boolean` field on
   SessionState; renderSessionFrame mounts the drawer DOM under the
   right column when it transitions true→false. The CSS animations
   (slide-in 300ms) match the wizard's step transitions.
5. **No new IPC required** — every settings.set field is already wired
   end-to-end (12-02). The drawer is a pure-DOM addition.

## Downstream integration (Phase 4 / 5 / 6)
1. **Wire cascade refs into SettingsApplier in main().** TODO comments
   in `src/vibemix/runtime/settings.py` mark each hook site.
2. **Wire SessionLoop into main().** Replace `ws_broadcast` (the
   mascot 30Hz WS server in cohost*.py) with `SessionLoop.run` so the
   IpcBus is the single 127.0.0.1:8765 owner. Mascot mount in the
   webview should consume `ipc.session.snapshot` rather than its own
   socket.
3. **Pull through MIDI deltas correctly.** SessionLoop currently uses
   list-length-diff to detect new ControllerState moves. When real
   ControllerState is in the loop, swap to a monotonic event index
   so out-of-band trims don't replay stale moves.

# Commits
- 487c0e8 feat(12-04): SessionState singleton + tests
- 18237f6 feat(12-04): ws-bridge — ipc.session/status/settings subscribers
- 9d84b70 feat(12-04): rAF render loop + sticky transcript + tests
- 0a4a1fe feat(12-04): router.session + boot decision
- fb214b1 feat(12-04): push-to-mute global hotkey via tauri-plugin-global-shortcut
- 8890c30 feat(12-04): PlaybackQueue.clear() — drain mid-utterance on mute
