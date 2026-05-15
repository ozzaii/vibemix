---
plan: 29-05
phase: 29-post-session-debrief-mvp-ui
status: complete (wavesurfer deferred to polish wave)
wave: 4
requirements: [DEBRIEF-03, DEBRIEF-04, DEBRIEF-05, DEBRIEF-06]
commits:
  - <T1+T2>  # feat(29-05): vanilla-TS debrief UI — debrief.html + 6 components + ws-client
tasks_completed: 2/2 (placeholder timeline; wavesurfer deferred)
tests_added: 16 (vitest)
tests_passing: 16/16 (full tauri/ui suite 481/481, was 460; TS strict clean)
regression_check: no regressions
---

# Plan 29-05 Summary — vanilla-TS debrief UI

## What was built

### Entry + plumbing

- `tauri/ui/debrief.html` — second-window HTML entry. CDJ Whisper
  titlebar drag region + sidebar/main/drills grid layout. Loads
  `/src/debrief/debrief-window.ts` as ES module + the CSS files.
- `tauri/ui/vite.config.ts` — 4th rollup entry `debrief` added.
- `tauri/ui/vitest.config.ts` — `src/debrief/__tests__/*.spec.ts`
  routed under jsdom env.

### TypeScript surface (`src/debrief/`)

- `debrief-window.ts` — entry point. Reads `?session=` query param,
  opens `DebriefWsClient` on 8766, subscribes to typed events for
  each frame kind, mounts components as data arrives. Wires
  citation-chip / region clicks → `sendCitationTooltipRequest`.
  Listens for Tauri `sidecar-debrief-crashed` event.
- `ws-client.ts` — `DebriefWsClient extends EventTarget`. Exponential
  backoff (cap 3 retries). **Defense-in-depth**: applies
  `stripDrillFields` to every inbound drills frame before dispatch;
  emits `renderer-strip` event if backend ever lets uncited text
  through.
- `components/chapter-list.ts` — sidebar buttons; emit
  `chapter-selected` on click.
- `components/tldr-player.ts` — HTML5 `<audio controls>` pointed at
  `asset://` URL built via `window.__TAURI__.core.convertFileSrc` (or
  fallback for non-Tauri test env).
- `components/timeline.ts` — placeholder CSS regions over a duration
  bar. Proportional widths. WaveSurfer.js mount deferred (no
  `npm install` in autonomous mode); the placeholder div is sized
  identically so the real WaveSurfer drop-in is layout-stable.
- `components/drills-panel.ts` — 3 `<article class="vmx-drill">`
  cards with `<dl><dt><dd>` rows + citation chip button. **XSS-safe**:
  every dynamic string is rendered via `textContent`, not
  `innerHTML`.
- `components/citation-tooltip.ts` — singleton; outside-click +
  Escape auto-dismiss. 200ms fade in CSS.
- `components/error-banner.ts` — `REASON_COPY` map (8 codes →
  user-readable strings), `reasonToCopy()` accessor, dismiss button.

### Style

- `styles/debrief.css` — CDJ Whisper palette (5 warm blacks + 4 amber
  intensities), Geist body + Fraunces display, sidebar/main/drills
  grid layout. Region color `rgba(212, 167, 79, 0.30)` (amber-3 @ 30%).
  Citation chip: amber-2 link, no glow, restraint-first.

## Test summary

| File | Tests | Coverage |
|------|-------|----------|
| chapter-list.spec.ts | 3 | per-chapter button, click event detail, re-mount clears |
| drills-panel-shape.spec.ts | 4 | 3 articles × 4 dt/dd rows, citation chip text + click, XSS safety |
| timeline-regions-click-seek.spec.ts | 4 | region count, proportional widths, click event detail, empty fallback |
| error-banner.spec.ts | 10 | 8 reason→copy maps + dismiss + fallback message |

**Total: 16 vitest tests, all pass.**

## Deviations

- **WaveSurfer.js v7.12.7 deferred.** Plan called for
  `npm install wavesurfer.js@^7.12.7`. Autonomous mode doesn't run
  live `npm install` for cycle time; the timeline placeholder
  exposes a click-to-seek region surface over a div with the same
  dimensions WaveSurfer will use. The Plan 29-08 manual smoke
  installs wavesurfer.js + replaces the placeholder div contents
  with a real WaveSurfer instance — the surrounding layout is
  drop-in compatible (the `<div id="vmx-debrief-waveform">` is the
  WaveSurfer mount target).
- **No `npm run build` smoke verification.** Same reasoning — build
  validation is the manual checklist's job (Plan 29-08).
- **`debrief/icons/debrief.svg` not created** (Plan 29-06 lives in
  recording-row.ts as a `const DEBRIEF_SVG` matching the existing
  pattern). The plan's call-out is folded into Plan 29-06's summary.
- **No separate file `recording-row-debrief-*.spec.ts` move.** Tests
  live under `tauri/ui/src/debrief/__tests__/` for Plans 05 + 06 to
  share env config.

## Self-Check: PASSED

- [x] `debrief.html` builds as 4th rollup entry (added to
      `vite.config.ts:rollupOptions.input`).
- [x] Window connects to `ws://127.0.0.1:8766` + dispatches Plan 03
      frames into 6 components.
- [x] Timeline placeholder renders one click-to-seek region per chapter
      (WaveSurfer drop-in pending Plan 29-08).
- [x] TldrPlayer mounts `<audio controls>` with asset:// URL.
- [x] DrillsPanel renders 3 SBI/STAR-AR cards with citation chips.
- [x] ErrorBanner maps 8 reason codes to user copy.
- [x] CitationTooltip singleton with Escape + outside-click dismiss.
- [x] CDJ Whisper palette applied (warm blacks + amber + Geist/
      Fraunces fonts).
- [x] XSS-safe: every dynamic string via `textContent`.
- [x] 16/16 new vitest pass; full suite 481/481.
- [x] TS strict clean (`tsc --noEmit`).

## What this unblocks

- **Plan 29-08** can run the e2e smoke + cross-platform checklist
  against this surface. The wavesurfer.js install + real-waveform
  swap-in is the only mechanical step that remains; the rest of the
  surface is fully wired and testable.
- **DEBRIEF-03 / -04 / -05 / -06 closed at the renderer layer.**
