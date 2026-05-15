# Windows VM Debrief E2E Smoke Checklist — Phase 29 Plan 08

**Tester:** Kaan
**Date:** _______________
**Platform:** Windows 11 VM (specify host + virtualization: Parallels / UTM / VMware Fusion)
**Build:** `cd tauri && cargo build` or CI artifact

## Steps (mark PASS / FAIL with brief notes)

| # | Step | Result |
|---|------|--------|
| 1 | Boot Windows 11 VM | |
| 2 | Build vibemix.exe via `cargo build` OR copy CI artifact from GitHub Releases | |
| 3 | Launch `target\debug\vibemix.exe` | |
| 4 | Navigate to Settings → Recordings | |
| 5 | Locate a session > 5 minutes with > 5 events (copy a recordings dir into `%APPDATA%/vibemix/recordings/`) | |
| 6 | Hover the row → confirm 5 buttons visible: replay · reveal · open-external · **debrief** · delete | |
| 7 | Click Open Debrief button | |
| 8 | Verify second window opens at 1280×720 with title `Debrief — <session>` | |
| 9 | Verify chapter list renders in left sidebar | |
| 10 | Verify timeline regions appear (or WaveSurfer waveform once installed) | |
| 11 | Verify TLDR audio plays — WebView2 MP3 native support per Pitfall 1 | |
| 12 | Verify 3 drill cards with citation chips | |
| 13 | Click a citation chip → tooltip appears | |
| 14 | Click a timeline region → tooltip appears | |
| 15 | Take full-window screenshot → save to `.planning/phases/29-post-session-debrief-mvp-ui/screenshots/windows-debrief-window.png` | |
| 16 | Close the debrief window | |
| 17 | Verify no orphan process in Task Manager (Details tab → `vibemix-core.exe`) | |
| 18 | Re-open same session → cache hit < 1 second | |
| 19 | Short session test: button disabled with correct tooltip | |

## Pitfall 1 verdict (MP3 plays in WebView2): __PASS / FAIL / N/A__

## Pitfall 5 verdict (WaveSurfer rendering parity vs macOS): __MATCH / DRIFT / BROKEN / DEFERRED__

## Notes / observations (Windows-specific)

_______________________________________________________________
_______________________________________________________________

## Final verdict for Windows surface: __PASS / FAIL__
