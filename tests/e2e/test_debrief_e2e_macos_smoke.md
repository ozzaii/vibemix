# macOS Debrief E2E Smoke Checklist — Phase 29 Plan 08

**Tester:** Kaan
**Date:** _______________
**Platform:** macOS (specify version + chip: e.g. macOS 15.2 / M2 Pro)
**Build:** `cd tauri && npm run tauri build --debug` → run `./target/debug/vibemix`

## Steps (mark PASS / FAIL with brief notes)

| # | Step | Result |
|---|------|--------|
| 1 | Build app: `cd tauri && npm run tauri build --debug` | |
| 2 | Launch app: `./target/debug/vibemix` (or .app) | |
| 3 | Navigate to Settings → Recordings | |
| 4 | Locate a session > 5 minutes with > 5 events (e.g. `recordings/20260515-112139`) | |
| 5 | Hover the row → confirm 5 buttons visible: replay · reveal · open-external · **debrief** · delete | |
| 6 | Confirm Open Debrief icon visible (speech bubble + replay arrow) | |
| 7 | Click Open Debrief button | |
| 8 | Verify second window opens with label `debrief`, 1280×720, title `Debrief — <session>` | |
| 9 | Verify chapter list renders in left sidebar | |
| 10 | Verify timeline placeholder regions appear under "Timeline" section (or WaveSurfer waveform once installed) | |
| 11 | Verify TLDR `<audio controls>` element present + plays MP3 | |
| 12 | Verify 3 drill cards render with SBI/STAR-AR rows + citation chip | |
| 13 | Click a citation chip → tooltip appears with evidence_text + timestamp | |
| 14 | Click a timeline region → tooltip appears (same path via citation_event_id) | |
| 15 | Take full-window screenshot → save to `.planning/phases/29-post-session-debrief-mvp-ui/screenshots/macos-debrief-window.png` | |
| 16 | Close the debrief window | |
| 17 | Verify no orphan process in Activity Monitor (search `vibemix-core` → debrief sidecar should be gone) | |
| 18 | Re-open same session → verify load completes in < 1 second (cache hit) | |
| 19 | Find or create a session shorter than 5 minutes → verify Open Debrief button is **disabled** with tooltip "Session too short for debrief (need ≥ 5 minutes)" | |

## Pitfall 1 verdict (MP3 plays cross-webview): __PASS / FAIL / N/A__

## Pitfall 5 verdict (WaveSurfer rendering parity vs Windows): __MATCH / DRIFT / BROKEN / DEFERRED__

## Notes / observations

_______________________________________________________________
_______________________________________________________________

## Final verdict for macOS surface: __PASS / FAIL__
