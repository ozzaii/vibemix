---
plan_id: 15-04
status: deferred
deferred_by: gsd-autonomous fully mode
deferred_at: 2026-05-14
deferred_to: kaan-action-required
---

# Plan 15-04 — DEFERRED (Kaan Ear-Test Checkpoint)

This plan requires Kaan to drive a real DJ session against the dev build to verify all 4 Phase 15 ROADMAP success criteria end-to-end (`15-EAR-TEST.md` signed PASS = phase closure + Phase 16 hand-off).

**Why deferred:** `autonomous: false` + fully mode rule = surface as Kaan-action, continue with unblocked work.

## What Kaan needs to do

1. Build dev: `npm run tauri dev` (or `cargo tauri dev`)
2. Run a 5-10min ad-hoc DJ session that produces ≥1 recording
3. Open Settings → Recordings → drive each criterion:
   - **C1**: chronological list shows date + duration + disk size; click row → reveals in Finder
   - **C2**: replay voice.wav inline (play button on row); open input.wav externally (new external-app icon button)
   - **C3**: delete a row → optimistic remove + 4s undo toast (NOT confirm modal — superseded by impeccable Wave 5.A)
   - **C4**: kick a periodic sweep with `VIBEMIX_RETENTION_INTERVAL_S=10` env (per Plan 02) and confirm `retention_pruned` line appears in events.jsonl

4. Single-row playback discipline (Gap E): expand 2 rows in succession → second expand should auto-collapse first. Currently expected to FAIL (Plan 01 Test G is `it.fails(...)`) — fix lives in `recording-browser.ts:362-378` `onToggle` handler. Worth fixing in this same session if Kaan has 5min.

5. Sign `15-EAR-TEST.md` PASS or FAIL with notes.

## When Kaan is ready

Run: `/gsd-autonomous --only 15` (it'll pick up the deferred plan)
or run inline: `/gsd-execute-phase 15 --wave 3`

## Status of other plans

- Plan 15-01 ✅ merged (cecf614) — 65 pytest + 32 vitest gates
- Plan 15-02 ✅ merged (4f cited above) — 6h periodic sweep + retention_pruned events
- Plan 15-03 ✅ merged — reveal_in_os + open_input_wav + 4-button row
- Plan 15-04 ⏸ deferred (this file) — Kaan ear-test
