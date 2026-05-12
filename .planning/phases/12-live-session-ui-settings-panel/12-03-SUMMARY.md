---
phase: 12-live-session-ui-settings-panel
plan: 03
subsystem: frontend
tags: [tauri, ui, typescript, vitest, jsdom, components, session, presentation]

# Dependency graph
requires:
  - phase: 11-tauri-shell-calibration-wizard
    provides: pure-function (state) => HTMLElement component pattern, registerStyle() singleton, tokens.css design system source-of-truth, vendored fonts (Workbench / DM Mono / DSEG7 / Caveat)
  - plan: 12-01
    provides: IpcSessionSnapshot / SessionMute / SettingsState / StatusRecheck schemas — typed prop shapes consumed by phase-tape / event-ribbon / cohost / status-bar
provides:
  - tauri/ui/src/session/components/_style-registry.ts — singleton CSS injector (lift of Phase 11 pattern)
  - tauri/ui/src/session/icons/{gear, headphones, speakers, screw, mascot-placeholder}.svg.ts — 5 inline SVG TS modules
  - tauri/ui/src/session/components/panel.ts — generic panel shell with brushed-metal streak overlay
  - tauri/ui/src/session/components/titlebar.ts — 56px strip: traffic-light + wordmark + 3 status pills + DSEG7 clock + settings gear
  - tauri/ui/src/session/components/rocker.ts — segmented rocker (variants: rocker + interaction)
  - tauri/ui/src/session/components/picker.ts — dropdown row (48px trigger + 240px option list)
  - tauri/ui/src/session/components/meter.ts — 16-segment vertical LED meter, data-attr driven, layout-thrash-free
  - tauri/ui/src/session/components/timecode.ts — DSEG7 hero clock + meta cells
  - tauri/ui/src/session/components/phase-tape.ts — paper-textured horizontal phase timeline (locally-scoped --paper-tape-*)
  - tauri/ui/src/session/components/drop-chip.ts — beat-pulsed countdown via --bpm-period-ms CSS var
  - tauri/ui/src/session/components/event-ribbon.ts — max-12 chip strip, age-bucketed (now/warm/cool)
  - tauri/ui/src/session/components/cohost.ts — mascot header + receipt-paper transcript + grounded/latency foot
  - tauri/ui/src/session/components/status-bar.ts — 4 LED badges + muted indicator + Caveat signature + recheck tooltip
  - tauri/ui/src/session/components/muted-banner.ts — --rec-tinted strip pinned above transcript
  - tauri/ui/src/session/SessionLayout.ts — mountSessionLayout(root) + renderSessionFrame(state) composer
  - tauri/ui/tests/session/components.spec.ts — 36 jsdom-backed vitest cases covering all 12 component contracts + cross-cutting hex grep guard
  - vitest.config.ts — environmentMatchGlobs adds jsdom for tests/**
  - tsconfig.json — include tests/** for typecheck coverage
affects:
  - 12-04 (Wave 3 — glue): SessionLayout.renderSessionFrame is the only public hot-path; ws-bridge.ts writes SessionState then calls it. onChange / onSettingsClick / onRecheck callbacks are the outgoing edges.
  - 12-05 (Wave 4 — settings drawer): rocker.ts + picker.ts + panel.ts are re-used inside the drawer; status-bar.ts tooltip is the recheck UX pattern the drawer's calibration row inherits.
  - 13 (mascot): cohost.ts ships a placeholder mascot-placeholder.svg.ts that Phase 13 (Avery) swaps without touching cohost.ts itself.

# Tech tracking
tech-stack:
  added:
    - jsdom@29.1.1 (devDependency) — first DOM-test environment in the repo; required by vitest for the new components.spec.ts under tests/session/
  patterns:
    - Data-attribute driven state changes (data-state / data-active / data-lit / data-tier / data-age / data-bars / data-tooltip-open / data-sticky / data-grounded) — every state transition is a single attribute write, browser repaints the styles. No layout thrash.
    - CSS-custom-property driven hot updates — --meter-peak-pct, --phase-now-pct, --bpm-period-ms; the rAF loop writes the variable, the browser composites without recomputing layout.
    - Two-paper-surface discipline — phase-tape + cohost transcript both scope `--paper-*` vars LOCALLY on their root element; tokens.css stays charcoal + amber only. Hex grep guard enforces this at test time.
    - Pure-function (props) => HTMLElement contract — no internal state, no setInterval, no rAF, no IPC. Hot-update helpers (`setMeterLevels`, `setTimecode`, `setPhaseTape`, `setCohost`, `setTitlebarClock`, etc.) accept the mount + new props and apply minimal mutations. Wave 3 owns the rAF loop and IPC wiring.
    - Singleton style registry — registerStyle(scope, css) injects exactly one <style data-scope="…"> per component class, no matter how many instances render. Tests rely on this contract for the cross-component hex grep guard.
    - Locally-bundled CSS animations (vmx-phase-arrow / vmx-drop-pulse / vmx-cohost-cursor / vmx-statusbar-pulse / vmx-rec-blink / vmx-muted-enter / vmx-drop-rec-flash) — sub-150ms snap or BPM-synced infinite ambient pulses per UI-SPEC §Motion Budget.

# Outcome
status: completed
shipped:
  - 5 inline SVG icon TS modules (gear, headphones, speakers, screw, mascot-placeholder)
  - 12 presentation components (style-registry + panel + titlebar + rocker + picker + meter + timecode + phase-tape + drop-chip + event-ribbon + cohost + status-bar + muted-banner)
  - SessionLayout.ts composer (mountSessionLayout + renderSessionFrame + defaultState)
  - tests/session/components.spec.ts — 36 vitest cases
  - vitest.config.ts + tsconfig.json updates to allow jsdom + tests/** coverage
  - package.json + package-lock.json — jsdom 29.1.1 devDependency

tests:
  vitest: 67 / 67 pass (was 31 baseline; +36 new cases under jsdom)
  typecheck: clean (`npx tsc --noEmit` zero errors)
  hex_grep_guard: green — every component <style> contains zero hex matches outside `--paper-*` local var declarations (verified at test time against live document.styleSheets)
  poc_files: untouched (cohost.py / cohost_v2.py / cohost_lk.py / cohost.streaming.py.bak / cohost_v3.py / cohost_v4.py / mocks/* / mascot.html — 0 lines diff)

# Deviations from plan
- **Spec path nuance:** the plan frontmatter (line 28) names the test file `tests/session/components.spec.ts`. I placed it at `tauri/ui/tests/session/components.spec.ts` — the Tauri UI workspace's tests root — and updated `tauri/ui/vitest.config.ts` + `tauri/ui/tsconfig.json` to discover and typecheck it. The alternative (`tauri/ui/src/session/components.spec.ts`) would have required less config churn but bled test-only concerns into the source tree. Net: one extra `environmentMatchGlobs` line, one extra `include` entry.
- **jsdom dependency added:** the plan didn't pre-declare this. It was the only way to satisfy the vitest cases (Phase 11 validator.spec.ts is node-only). Scope: `devDependency` only, no production bundle impact.
- **DropChip count format:** UI-SPEC §7 lists `{bars}:{eighths}` as the desired format. Until the sub-bar tracker lands in Wave 3 (12-04), the eighths placeholder is `00`. Renders as `08:00` for `bars=8`, `00:00` for `bars=0`. Phase 12-04 may extend the formatter.
- **Output panel device options empty by default:** the plan calls for an output device dropdown, but the device list is sourced from `ipc.settings.state` which Wave 3 writes. The picker mounts with an empty options array; Wave 3 populates via `renderSessionFrame`. No spec violation — the picker accepts arbitrary option lists.
- **No `?dev=session-mock` URL param handler:** the plan §Verification mentions opening `index.html?dev=session-mock`. The dev surface lives in Wave 4 (12-04) — adding it now would require IPC wiring. SessionLayout.defaultState() ships a mountable mock state; Wave 3 will surface it via a router hook.

# Handoffs
- **12-04 (Wave 3 — glue):** `mountSessionLayout(rootEl)` returns a `Mounted` handle. The rAF/WS bridge writes SessionState then calls `renderSessionFrame(mounted, state)`. Component-level callbacks (`onSettingsClick` on titlebar, `onChange` on rocker/picker, `onRecheck` on status-bar) are the only outgoing edges — wire those to `ipc.settings.set` / `ipc.status.recheck` / drawer-open dispatch.
- **12-05 (Wave 4 — settings drawer):** re-use `renderRocker`, `renderPicker`, `renderPanel` inside the drawer body. The drawer header pattern mirrors the titlebar pill style — same gear-button affordance pattern; consider lifting `renderTitlebar.__settings` styling for the drawer close button if it shares the bezel look.
- **13 (mascot — Avery):** swap `mascot-placeholder.svg.ts` for the real Avery SVG/canvas mount inside `vmx-cohost__mascot`. The 42×42 circle + inset shadows + radial-gradient background are stable mount points; Phase 13 only writes inside the circle.
- **14 (FL-Studio polish):** the brushed-metal `::before` overlay on `.vmx-panel` is the hook for adding deeper screw-head detail, edge-bevel highlights, and knurled-knob shadows. CSS-only — no DOM changes required.

# Commits
- 9087df3 feat(12-03): session components — icons + panel + titlebar
- ff07bd3 feat(12-03): session components — rocker + picker
- 6e1d3da feat(12-03): session components — meters + timecode + phase tape
- 9f95091 feat(12-03): session components — drop chip + event ribbon + cohost + status bar + muted banner
- 92e9daa feat(12-03): session components — SessionLayout composer + vitest spec
