<!--
SPDX-License-Identifier: Apache-2.0
Phase 43 / VIS-09 — Francesco capture day handoff package
Sourced 1-to-1 from mocks/vibemix-cinematic-storyboard.html (8 data-cut frames).
-->

# vibemix hero demo — Shot list

**Phase 43 / VIS-09.** 8 cuts total. Target runtime ~30 seconds.

Sourced 1-to-1 from `mocks/vibemix-cinematic-storyboard.html` (8 `<section data-cut>` elements; cut count gate at `scripts/launch/check_cut_count.py`).

| Cut | Description | Timing | B-roll suggestions |
|-----|-------------|--------|---------------------|
| 1 | Cold open — DJ hands on FLX4 + dim room | 0:00 – 0:03 (3s) | close-up of jog wheel; faders at neutral; dim purple-amber room light; rim light on the controller chassis |
| 2 | vibemix wizard "Welcome" frame (hold 1s) | 0:03 – 0:05 (2s) | screen capture of wizard step 0; subtle amber accent glow on Continue button; cursor idle |
| 3 | Calibration screen with live audio meter rising | 0:05 – 0:09 (4s) | screen capture of LED meter climbing from safe (1-5) to warm (6-13); peak-hold lozenge floats up; hardware-LED-strip segmentation visible |
| 4 | Live session — mascot overlay subtle reaction | 0:09 – 0:14 (5s) | screen-in-screen: mascot in corner doing micro-head-turn while session UI fills frame; AI line audio softly fades in |
| 5 | AI line caption pop — "nice kick swap @ 2:33" | 0:14 – 0:17 (3s) | caption bubble fade-in over session UI; audio overlay of Gemini voice line at low EQ; mascot mood shifts to Hype-man |
| 6 | EvidenceRegistry chip strip — anti-slop receipts | 0:17 – 0:20 (3s) | chip strip render: `[kick swap @ 2:33]` `[layer drop @ 4:50]` `[bpm shift @ 6:00]`; amber accent on the active chip; one-second hold per chip |
| 7 | Mascot Hype-man celebrate animation (mid-track) | 0:20 – 0:25 (5s) | mascot full-frame; **Pioneer-CDJ headbob** (NOT generic VTuber dance per CDJ Whisper baseline); reserved energy, head-and-shoulders motion only |
| 8 | End card — vibemix logo + altidus.world/vibemix + "open-source" | 0:25 – 0:30 (5s) | wordmark in Saira amber on warm-black; URL beneath in Geist Mono; "open-source · MIT · github.com/bravoh/vibemix" CTA; 1s logo dwell before fade |

## Notes for Francesco

- **Cuts 1 + 7 are real-world capture** (DJ hands + booth). Cuts 2-6, 8 are screen capture composited or hybrid.
- **Cut 7 aesthetic gate (Pioneer-CDJ headbob, NOT VTuber dance):** if the take feels "slop" — jazz hands, body twirl, hip pop, exaggerated weight-shift, full-arm dance — re-take with a more reserved Mixamo source clip. Mascot celebrate must read like a CDJ pro at the booth, not a vtuber stream.
- **Cut 4 mascot overlay** should be SUBTLE — micro-motion only, not a celebrate. Save the energy for cut 7.
- **Cut 5 caption** is the literal demo-mode kick_swap anchor (153.0s in `DEMO_SEQUENCE`). Time the caption pop to land synced with the audio cue.
- **Cut 6 chip strip** comes from the real EvidenceRegistry render — use the in-app screen capture, not a mocked overlay.

## Audio cues to time against

The demo-mode deterministic sequence (see `DEMO-MODE-CONFIG.md`) fires at:

- **0:00** track_start (Track A) — covers cuts 1–4
- **2:33** kick_swap → mascot celebrate trigger → cut 5 caption + cut 7 animation are anchored here
- **4:50** layer_drop → mascot teacher line — happens during cut 7 mid-track moment
- **6:00** track_end — natural fade-out into cut 8

Note: the 6-minute demo runs in vibemix; the final demo film is the 30-second cut down. Francesco picks the visual highlights from the full 6-minute pass.

## Cross-references

- Storyboard mock (8 `<section data-cut>` frames): `mocks/vibemix-cinematic-storyboard.html`
- Visual baseline (CDJ Whisper locked): `mocks/vibemix-direction-final.html`
- Audio capture plan (3-track separation + clapboard sync): [`AUDIO-CAPTURE.md`](./AUDIO-CAPTURE.md)
- Demo-mode config (deterministic playback for repeatable takes): [`DEMO-MODE-CONFIG.md`](./DEMO-MODE-CONFIG.md)
- Francesco discharge runbook: [`KAAN-ACTION-LEGAL.md §VIS-09`](../../KAAN-ACTION-LEGAL.md)
