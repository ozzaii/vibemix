# KAAN-ACTION-LEGAL — Phase 29 Cross-Platform Smoke (NON-BLOCKING)

These items require Kaan-touch — Apple + Windows physical access in
particular — and were deferred from the autonomous Phase 29 execution
per `gsd-autonomous fully` mode. Phase 29 code-completion is unblocked;
release-gate verdict (SHIP/BLOCK/REWORK) requires these items closed.

## Source: Phase 29 Plan 29-08 Task 2 — Cross-platform manual smoke

**Plan:** `.planning/phases/29-post-session-debrief-mvp-ui/29-08-PLAN.md`
**Verdict template:** `.planning/phases/29-post-session-debrief-mvp-ui/29-CROSS-PLATFORM-VERDICT.md`

### Action items

1. **MAC-SMOKE-001 — macOS E2E debrief smoke checklist**
   - Run: `cd tauri && npm run tauri build --debug && ./target/debug/vibemix`
   - Walk: `tests/e2e/test_debrief_e2e_macos_smoke.md` (19 steps)
   - Save screenshot: `.planning/phases/29-post-session-debrief-mvp-ui/screenshots/macos-debrief-window.png`
   - Fill in PASS/FAIL per step in the checklist md
   - Mark `MAC-SMOKE-001` as `done` here when complete

2. **WIN-SMOKE-001 — Windows VM E2E debrief smoke checklist**
   - Boot Windows 11 VM (Parallels / UTM / VMware)
   - Build vibemix.exe via `cargo build` OR copy CI artifact
   - Walk: `tests/e2e/test_debrief_e2e_windows_smoke.md` (19 steps)
   - Save screenshot: `.planning/phases/29-post-session-debrief-mvp-ui/screenshots/windows-debrief-window.png`
   - Fill in PASS/FAIL per step
   - Mark `WIN-SMOKE-001` as `done` here when complete

3. **VERDICT-001 — Cross-platform verdict consolidation**
   - Open `.planning/phases/29-post-session-debrief-mvp-ui/29-CROSS-PLATFORM-VERDICT.md`
   - Fill in Pitfall 1 verdict (MP3 plays both WebViews)
   - Fill in Pitfall 5 verdict (WaveSurfer parity — DEFERRED is OK
     because the placeholder timeline meets DEBRIEF-05 functionally)
   - Final release decision: SHIP / BLOCK / REWORK
   - If REWORK, enumerate gaps and create gap-closure plan via
     `/gsd-plan-phase 29 --gaps`
   - Sign + date

4. **POLISH-OPT-001 — wavesurfer.js install (OPTIONAL, polish wave)**
   - `cd tauri/ui && npm install wavesurfer.js@^7.12.7`
   - Replace `mountTimelinePlaceholder` calls in
     `src/debrief/debrief-window.ts` with a real WaveSurfer instance
     mounting `voice.wav` via `convertFileSrc`. The placeholder div
     `#vmx-debrief-waveform` is already sized so the swap-in is
     drop-in (layout-stable).
   - The placeholder regions surface meets DEBRIEF-05 functionally;
     real waveform is a visual upgrade only.

## Non-blocking note (per gsd-autonomous fully)

Autonomous execution finished Plans 29-01 through 29-07 + Plan 29-08
Task 1 (3 automated e2e pytest files, 6 tests, all pass). Plan 29-08
Task 2 (manual smoke) is the only outstanding work for the phase.
Kaan can either:

- Run the smoke now (1-2 hours estimated) → Phase 29 ships
- Run the smoke at a less load-bearing moment → Phase 29 stays in
  "ready-to-ship-pending-smoke" state; subsequent phases proceed
  without dependency on this verdict
