<!--
SPDX-License-Identifier: Apache-2.0
Phase 43 / VIS-09 — Audio capture plan for Francesco's hero-demo shoot day.
-->

# vibemix hero demo — Audio capture plan

**Phase 43 / VIS-09.** 3 separate tracks recorded simultaneously, synced via clapboard, alongside vibemix's own `session.wav` as the canonical reference mix.

## The 3 capture tracks

### Track 1 — Gemini voice

- **Source:** vibemix's `playback_queue` → speaker bus.
- **Capture:** line-out from the headphone amp, OR USB recording from vibemix audio output. Avoid re-recording with a mic in the room (introduces room tone and double-mics the audio).
- **Format:** 48kHz 24-bit WAV mono.
- **Filename:** `take_NN_gemini.wav`
- **Why isolated:** the final cut may need the Gemini line at variable level vs ambient/mascot reactions — a clean isolated track gives the colourist full headroom.

### Track 2 — Ambient (room)

- **Source:** room mic (boom or shotgun), positioned off-axis from speakers.
- **Purpose:** room tone + crowd-feel atmosphere. Adds depth to the cut even though no real crowd is present.
- **Format:** 48kHz 24-bit WAV stereo.
- **Filename:** `take_NN_ambient.wav`
- **Mic note:** off-axis from the speaker monitors prevents the Gemini voice bleeding back into ambient at high level. A cardioid pattern aimed at the booth surface works.

### Track 3 — Headphone return (DJ's cue)

- **Source:** DJ headphone monitor, split via Y-cable or audio-interface insert send.
- **Purpose:** shows what the DJ is hearing in cue (often the next track in queue). Used in the final cut for the "DJ in flow" feel — never the primary audio bed.
- **Format:** 48kHz 24-bit WAV stereo.
- **Filename:** `take_NN_headphones.wav`

## Sync — clapboard at every take

- **Clapboard at the head of every take** (visual + audio clap; single slate, both visible and audible across all cameras and all 3 audio tracks).
- All 4 sources (3 audio tracks + vibemix `session.wav`) align via the clapboard transient in post.
- If a digital slate (Tentacle Sync etc.) is on hand, use it; clapboard remains the fallback canonical sync.

## vibemix `session.wav` — canonical reference mix

vibemix records its own canonical mix to:

```
macOS:   ~/Library/Application Support/vibemix/recordings/<session-id>/session.wav
Windows: %APPDATA%\vibemix\recordings\<session-id>\session.wav
```

Format: 48kHz 24-bit (matches the 3 capture tracks → bit-identical alignment after clapboard offset).

**Always copy `session.wav` into the take folder before tearing down the booth.** It is the only audio source guaranteed to include the literal vibemix reactions in their literal mix as the AI heard them. Losing it = losing the canonical reference.

## AV spec (CONTEXT §VIS-09 minimums)

| Spec | Minimum | Recommended |
|------|---------|-------------|
| Video resolution | 1080p (1920×1080) | 4K (3840×2160) downsampled in post |
| Frame rate | 60fps | 60fps (don't go higher; matches mascot animation rate) |
| Audio sample rate | 48kHz | 48kHz (matches vibemix's session.wav — bit-identical alignment) |
| Audio bit depth | 24-bit | 24-bit |
| Codec | ProRes 422 or H.264 high | ProRes 422 |

## Take workflow

1. **Reset vibemix demo-mode:** `vibemix --demo-mode reset` (resets the 30-event deterministic sequence to step 0 — every take starts from the same musical position).
2. **Slate the take** (clapboard, visible and audible on all 3 audio tracks + all cameras).
3. **Roll all recorders:** 3 audio tracks + cameras + vibemix's own `session.wav` capture (auto-starts when demo-mode starts).
4. **Trigger demo-mode start in vibemix:** `vibemix --demo-mode start` — the deterministic 30-event sequence plays out across 6:00. See [`DEMO-MODE-CONFIG.md`](./DEMO-MODE-CONFIG.md).
5. **Capture cuts 1, 4, 7 (real-world)** during the 6-minute demo-mode playback. Mascot cuts (4 and 7) are screen capture; cut 1 (DJ hands on FLX4) is a separate camera setup but rolls in parallel.
6. **End take.** Stop all recorders. Verify the clapboard transient is present at the head of all 4 audio sources.
7. **Copy `session.wav`** from the vibemix recordings dir into the take folder before the next take.
8. **Repeat per planned take count.** Reset between takes (step 1).

## Post — alignment recipe

In Resolve / Premiere / Logic:

1. Drop all 4 audio sources onto separate tracks.
2. Find the clapboard transient on each.
3. Slip-align to match the transient peaks.
4. Lock the group; from here forward all 4 tracks scrub in sync.
5. Use vibemix's `session.wav` as the reference mix for level reference; mix the 3 capture tracks against it.

## Cross-references

- Shot list (8 cuts + per-cut timing): [`SHOT-LIST.md`](./SHOT-LIST.md)
- Demo-mode deterministic sequence + reset CLI: [`DEMO-MODE-CONFIG.md`](./DEMO-MODE-CONFIG.md)
- Demo-mode sequencer source (the 30 events): `src/vibemix/runtime/demo_mode.py`
- Francesco discharge runbook: [`KAAN-ACTION-LEGAL.md §VIS-09`](../../KAAN-ACTION-LEGAL.md)
