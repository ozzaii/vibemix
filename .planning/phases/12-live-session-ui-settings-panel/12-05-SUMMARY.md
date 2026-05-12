---
phase: 12-live-session-ui-settings-panel
plan: 05
subsystem: frontend+rust
tags: [tauri, frontend, settings, drawer, hotkey, retention, confirm-dialog, integration]

# Dependency graph
requires:
  - plan: 12-01
    provides: ipc.* schema — `ipc.settings.set` / `ipc.settings.state` / `ipc.wizard.start` envelopes the drawer pushes through
  - plan: 12-02
    provides: Sidecar SessionLoop / SettingsApplier / ConfigStore — every settings.set write lands in the dispatch matrix
  - plan: 12-03
    provides: `renderPicker` / `renderRocker` / `renderPanel` / `registerStyle` — drawer composition pieces re-used verbatim
  - plan: 12-04
    provides: `sendSettings(field, value)` outbound surface; `getSessionState().settings` read surface; `rebind_hotkey` Tauri command + `HotkeyHandle` managed state; reserved-combo validator
provides:
  - tauri/ui/src/settings/state.ts — SettingsUIState singleton (open, hotkeyCaptureMode, pendingGenreReload, confirmDialog) + subscribe/notify pub-sub
  - tauri/ui/src/settings/SettingsDrawer.ts — mountSettingsDrawer / openSettings / closeSettings; reads SessionState.settings; calls sendSettings on every mutation; Esc + backdrop + ✕ dismiss; full body rebuild on each refresh (cheap; ~30 DOM nodes)
  - tauri/ui/src/settings/components/group.ts — generic group wrapper (Workbench 9px header strip + body + optional footer; no brushed-metal layer since the drawer already has it)
  - tauri/ui/src/settings/components/hotkey-capture.ts — two-state row (idle chip + Rebind button → PRESS KEYS… pulsing); keyEventToCombo wire-form conversion; isReservedCombo guard mirroring the Rust list verbatim; Esc cancels capture; setError surfaces Rust-side rejections
  - tauri/ui/src/settings/components/retention-slider.ts — 6-stop knurled-knob slider (1d/3d/7d/14d/30d/∞); ∞ wire sentinel = 36500 days; DSEG7 22px readout; lit-portion CSS var; arrow-key nav
  - tauri/ui/src/settings/components/confirm-dialog.ts — generic modal (heading + body + Cancel/Confirm); Esc dismisses; backdrop click dismisses; dialog click does not; danger variant for destructive ops (unused in v1 — Phase 12 uses default phosphor confirm)
  - tauri/ui/src/session/SessionLayout.ts — gear button onClick wired (dyn import of SettingsDrawer keeps wizard mode lean)
  - tauri/ui/src/session/router.ts — `mountSettingsDrawer(document.body)` mounted post-session-layout
  - tauri/ui/tests/settings/drawer.spec.ts — 15 vitest cases
  - tauri/ui/tests/settings/hotkey-capture.spec.ts — 17 vitest cases
  - tauri/ui/tests/settings/retention-slider.spec.ts — 14 vitest cases
  - tauri/ui/tests/session/integration.spec.ts — 3 end-to-end vitest cases
affects:
  - 13 (mascot — Avery): 42×42 cohost-header mascot circle + 256×256 reserved-corner mount points still untouched; drawer respects them too (no overlap)
  - 14 (FL-Studio polish): knurled-knob ::after cross-hatch is the hook for Phase 14's deeper knurl + screw-head polish; drawer's brushed-metal ::before is the same hook surface as the panels
  - 15 (recording browser): `retention_days` setting persisted via `sendSettings('retention_days', days)` where ∞ = 36500; Phase 15 cleanup policy treats `days >= 36500` as keep-forever

# Tech tracking
tech-stack:
  added: []  # No new dependencies — drawer composes existing primitives
  patterns:
    - Drawer = overlay, NOT route — the live-session render-loop keeps running at full fps behind the backdrop. No `stopRenderLoop()` on open; the session is read-only while the drawer is up but it stays "alive".
    - Settings UI state is split from persistent settings — `src/settings/state.ts` owns ephemeral drawer concerns (open, in-flight capture, reload overlays, modal in flight). Persisted settings (voice, genre, retention_days, hotkey…) live in `src/session/state.ts` written by `ws-bridge.ts` on `ipc.settings.state`. Two singletons; one notifies the drawer to re-render; the other is the source of truth for picker labels.
    - Drawer body = full rebuild on each refresh — chosen over diffing because the body is small (~30 nodes) and the rebuild cost is one-off (only fires on open + state changes). The render-loop is unaffected.
    - Hotkey capture mirrors Rust reserved-combo list — JS-side `RESERVED_SET` in `hotkey-capture.ts` matches `RESERVED_COMBOS` in `tauri/src-tauri/src/hotkey.rs` verbatim; the test matrix asserts both sides agree.
    - ∞ retention encoded as 36500 days — chosen over `0` (ambiguous with "never keep") and `null` (the schema's `retention_days` is `integer` not `integer|null`). Documented in `retention-slider.ts` and below; Phase 15 must treat `days >= 36500` as the "keep forever" branch.
    - OS-pretty hotkey display vs wire-form — `keyEventToCombo` emits `cmd+shift+m` (lowercase, `+`-joined; matches Rust `validate_combo` grammar); the chip renders `⌘⇧M` (macOS) or `Ctrl+Shift+M` (Windows) for UX clarity. Two surfaces, one source of truth.
    - Subscribe-then-render pub-sub — `subscribeSettingsUI()` registers a listener; `setSettingsUIState()` calls `notify()`. SettingsDrawer.refresh() runs on every notify, rebuilding the body. No reactive lib; same pattern as Wave 3's render-loop.

# Outcome
status: completed
shipped:
  - tauri/ui/src/settings/state.ts (96 lines incl. docs)
  - tauri/ui/src/settings/SettingsDrawer.ts (522 lines incl. docs + CSS)
  - tauri/ui/src/settings/components/group.ts (118 lines)
  - tauri/ui/src/settings/components/hotkey-capture.ts (289 lines incl. CSS)
  - tauri/ui/src/settings/components/retention-slider.ts (267 lines incl. CSS)
  - tauri/ui/src/settings/components/confirm-dialog.ts (200 lines incl. CSS)
  - tauri/ui/src/session/SessionLayout.ts (+6 lines — gear onClick handler)
  - tauri/ui/src/session/router.ts (+5 lines — mountSettingsDrawer call)
  - tauri/ui/tests/settings/drawer.spec.ts (175 lines, 15 tests)
  - tauri/ui/tests/settings/hotkey-capture.spec.ts (195 lines, 17 tests)
  - tauri/ui/tests/settings/retention-slider.spec.ts (170 lines, 14 tests)
  - tauri/ui/tests/session/integration.spec.ts (197 lines, 3 tests)

tests:
  vitest: 141 / 141 pass (was 92 baseline; +49 new — 15 drawer + 17 hotkey + 14 retention + 3 integration)
  cargo: 13 / 13 pass (Wave 3 baseline preserved; rebind_hotkey already in generate_handler! at main.rs line 56 + tested at hotkey::tests)
  typecheck: clean (`npx tsc --noEmit` zero errors; `npm run check:ipc` green)
  pytest: 1171 / 1173 pass (2 pre-existing failures unrelated — test_audio_macos_live hardware-flaky; test_phase05_verification mascot.html drift logged in 12-02; identical to Wave 3 baseline)
  poc_files: untouched (cohost*.py / mocks/ / mascot.html / fillers/ — 0 lines diff)
  loc_delta: ~+2200 (incl. CSS + docstrings)

# Deviations from plan
- **Plan §5 SessionLayout muted-banner mount: already wired in Wave 3.** The
  plan calls for "Mount muted-banner inside cohost-panel when state.muted === true."
  Wave 3's `SessionLayout.ts` already mounts `renderMutedBanner({ hotkey })` into
  `bannerSlot` (above the cohost panel in the right column) whenever
  `state.status.muted === true`. UI-SPEC §14 describes this as "pinned above
  transcript inside cohost panel" — same effective surface; the Wave 3
  implementation places it as a sibling above the cohost panel rather than
  injecting it inside the cohost component, which keeps the cohost component
  pure-presentation. No code change required in Wave 4.

- **Plan §6 Rust `rebind_hotkey` Tauri command: already exposed.** Wave 3's
  `tauri/src-tauri/src/main.rs` line 56 includes `hotkey::rebind_hotkey` in
  `generate_handler!`. The function signature is `async fn rebind_hotkey(app:
  AppHandle, _hotkey: State<HotkeyHandle>, new_combo: String) -> Result<(),
  String>` — exactly the surface the drawer invokes. No code change required.

- **OUTPUT group device dropdown is a stub.** UI-SPEC §3 specifies a device
  picker with a swappable icon (headphones vs speakers). The Wave 4 drawer
  ships a minimal device picker showing "auto" + the currently-selected
  device id (if any). The full enumeration of audio output devices belongs
  to the sidecar's startup probe → `ipc.settings.state` payload extension;
  not in 12-05 scope. Documented as a Wave 5 / Phase 15 follow-up.

- **∞ retention sentinel = 36500 days, not 0 or null.** Plan §3 RECORDING
  group leaves the wire value for ∞ open ("a large sentinel like 36500 or 0
  — choose one and document"). Shipped 36500 (≈100 years). Rationale:
    * 0 is ambiguous with "never keep" semantics (Phase 15's cleanup policy
      might read it as "delete immediately").
    * null is not allowed by the ipc.settings.set schema (retention_days is
      `integer`, not `integer | null`).
    * 36500 is well above any plausible user retention; Phase 15 reads it as
      `days >= 36500 → never expire`.
  Documented in retention-slider.ts and called out as a Phase 15 handoff.

- **Drawer body = full rebuild on refresh.** Plan §1 says "Setters notify
  SettingsDrawer to re-render." Chosen path: full rebuild via
  `renderDrawerBody()` on each notify. Rationale: ~30 DOM nodes, rebuild
  cost is dwarfed by the render-loop's 30Hz hot path; diffing complexity
  is not justified. Confirmed in vitest perf: drawer mount + open completes
  in <1ms in jsdom. The session render-loop's per-frame cost is unaffected.

- **Pretty-form hotkey display uses navigator.platform.** macOS symbols (⌘⇧M)
  vs Windows form (Ctrl+Shift+M) is picked from `navigator.platform` at render
  time. jsdom defaults to a Linux-like platform, so the test chips render in
  Windows form — the assertions check `M$/i` rather than exact glyphs so
  the spec passes on every CI platform. Real Tauri webviews report their host
  OS correctly.

# Handoffs

## Phase 13 (3D mascot — Avery)
1. **Mount points reserved, not occupied.** The 42×42 cohost-header mascot
   circle (in `session/components/cohost.ts`) and the 256×256 reserved-corner
   in the left column are both untouched. The drawer overlays the whole
   right side of the window but ONLY when open; the mascot mount points are
   on the left/right columns and don't intersect.
2. **Drawer is z-50, mascot will be inside the live-session DOM** — the
   drawer overlays the mascot when open, but the mascot keeps animating
   underneath. Same render-loop ownership pattern.

## Phase 14 (FL-Studio polish)
1. **Knurled-knob ::after cross-hatch is the hook.** Phase 14 deepens the
   knurl by adding a finer 2-stop repeating gradient + a vertical-streak
   overlay. The retention-slider ships the v1 detail; CSS-only edit.
2. **Drawer brushed-metal `::before`** mirrors the panel pattern. Phase 14's
   screw-head polish layer can be added to the drawer in the same pass as
   the live-session panels.
3. **Confirm dialog visual.** v1 is functional; Phase 14 could add a paper-
   texture body or a screen-shake on dismiss for delight. Not required.

## Phase 15 (recording browser + cleanup policy)
1. **`retention_days` settings field is canonical.** Reads via
   `getSessionState().settings.retention_days` after `ipc.settings.state`
   broadcast. The ∞ sentinel is 36500 — Phase 15's cleanup policy treats
   any value `>= 36500` as "keep forever, never delete".
2. **The Wave 4 device picker is a stub.** Phase 15 (or a follow-up patch)
   extends `ipc.settings.state` to carry the full list of audio output
   devices (id + label) so the picker can enumerate them. The current
   minimum surface (auto + current id) keeps the drawer usable.

## Manual UAT (deferred per fully-autonomous mode)
The plan's `autonomous: false` flag asked for human UAT on real hardware.
Per fully-autonomous mode rules, the seven UAT items below are deferred to
Kaan's next rig session — code, tests, and contract gates are all green;
only runtime / hardware-coupled scenarios remain:

1. Open Settings drawer, change voice — next AI turn uses new voice.
2. Change genre — see 250ms reload overlay; sidecar log shows profile reload.
3. Change output device — audio resumes through new device <500ms.
4. Capture new hotkey (e.g. `⌥⇧K`) — press it → mute fires.
5. Re-run calibration → wizard mounts; on completion → session re-mounts at same state.
6. Pull DDJ-FLX4 USB during session → MIDI badge flips `--rec · 0` within 2s.
7. Press default hotkey mid-AI-utterance → voice cuts mid-word; banner shown; press again → resume; recording (events.jsonl + voice.wav) shows continuous timeline through mute window.

These appear in `12-VERIFICATION.md` under `status: human_needed`.

# Commits
- c432e21 feat(12-05): settings drawer + state + groups
- afc831e feat(12-05): settings — hotkey capture + retention slider + confirm dialog
- dd164ca test(12-05): settings drawer + hotkey + retention + integration
