<!--
SPDX-License-Identifier: Apache-2.0
Phase 43 / VIS-09 — Index for the Francesco capture-day handoff package.
-->

# vibemix launch-prep — Hero demo handoff package

**Phase 43 / VIS-09** — engineering-side deliverables for Francesco's capture day. These three documents + the demo-mode sequencer are everything Francesco needs to bring the booth, the cameras, and the DJ ear; vibemix supplies the deterministic playback environment.

## Documents

| Doc | Purpose |
|-----|---------|
| [`SHOT-LIST.md`](./SHOT-LIST.md) | 8-cut sequenced shot list with per-cut timing budget + B-roll suggestions. Sourced 1-to-1 from `mocks/vibemix-cinematic-storyboard.html`. |
| [`AUDIO-CAPTURE.md`](./AUDIO-CAPTURE.md) | 3-track capture plan (Gemini-voice + ambient + headphone-return) + clapboard sync + AV spec. |
| [`DEMO-MODE-CONFIG.md`](./DEMO-MODE-CONFIG.md) | Demo-mode deterministic 30-event sequence + reset workflow + AV spec. |

## Launch orchestration

Added by **Phase 44** (LAUNCH-09 + LAUNCH-10) — the day-of synchronization
spine for the v1 ship. The Phase 43 capture-day docs above are the
upstream prerequisites; the docs below are what Kaan + Francesco actually
work from once the demo cut is locked.

| Doc | Purpose |
|-----|---------|
| [`OUTREACH-CALENDAR.md`](./OUTREACH-CALENDAR.md) | LAUNCH-09 — 3 editorial pitches (DJ TechTools / DDJ Tips / Mixmag) + 3 subreddit cross-posts (r/DJs / r/Beatmatch / r/edmproduction) + 1 DJ TechTools Discord T-3 soft-launch slot. Each entry carries a 4-state status checkbox. |
| [`LAUNCH-SEQUENCE.md`](./LAUNCH-SEQUENCE.md) | LAUNCH-10 — T-7 → T+30 timeline (T-7 pre-seed stars, T-3 Discord soft-launch, T-0 Show HN + cross-post + outreach fires, T+24h monitoring rotation, T+72h Substack draft, T+7d transparency post, T+30 SHIP-V1-DECISION review). Every row cross-links the ROADMAP phase + `KAAN-ACTION-LEGAL §LAUNCH-*` runbook it depends on. |

## Cross-references

- **Storyboard mock (the 8 `data-cut` frames):** `mocks/vibemix-cinematic-storyboard.html`
- **Visual direction baseline (CDJ Whisper locked):** `mocks/vibemix-direction-final.html`
- **Demo-mode sequencer source:** [`src/vibemix/runtime/demo_mode.py`](../../src/vibemix/runtime/demo_mode.py)
- **Demo-mode sequencer pytest pins:** [`tests/runtime/test_demo_mode_sequence.py`](../../tests/runtime/test_demo_mode_sequence.py)
- **Francesco discharge runbook:** [`KAAN-ACTION-LEGAL.md §VIS-09`](../../KAAN-ACTION-LEGAL.md)
- **Cut-count gate (≤8 cuts hard rule):** `scripts/launch/check_cut_count.py`

## Aesthetic gates (non-negotiable)

These are the load-bearing visual contracts Kaan + Francesco must hold the line on. Engineering ships the deterministic playback; aesthetic judgment closes the gate.

1. **Mascot celebrate = Pioneer-CDJ headbob, NOT a generic VTuber dance.** Cut 7 is the load-bearing aesthetic moment. Reject jazz hands, body twirl, hip pop, exaggerated weight-shift, full-arm dance. Re-take if the mascot reads "vtuber slop".
2. **CDJ Whisper palette held throughout** — 5 warm blacks + single amber accent. Any chip overlay or caption text must use `--amber-pri` from `tauri/ui/src/tokens.css`, never teal/electric-blue.
3. **AV spec held** — 1080p+ resolution, 60fps+ frame rate, 48kHz audio. Anything under fails the post-shoot ffprobe check in §VIS-09.

## Handoff status

- [x] Storyboard locked (Plan 43-08)
- [x] Shot list written (this plan, Task 2)
- [x] Audio capture plan written (this plan, Task 2)
- [x] Demo-mode config doc written (this plan, Task 2)
- [x] Demo-mode sequencer implemented + pinned (this plan, Task 1)
- [x] §VIS-09 discharge runbook in `KAAN-ACTION-LEGAL.md` (this plan, Task 3)
- [ ] Pre-production review with Francesco (post-Phase 43, tracked in §VIS-09)
- [ ] Capture day (post-Phase 43, Francesco-discharge)
- [ ] Final cut signed off (post-shoot, Kaan + Francesco)
