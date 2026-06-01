# MIXXX LOOP + BEATJUMP PERFORMANCE — ALGORITHM EXTRACTION (Round 2)

GPL hygiene: all working copies of Mixxx source were read read-only from `/tmp/mixxx-src`; no Mixxx code was vendored, and the transient scratch copies were deleted (verified gone). What follows is the *algorithm in my own words* for clean-room numpy reimplementation, with file:line method references only.

## (1) THE ALGORITHM — reimplementable from spec

### 1a. The beat-size lattice (the spine of everything)
Mixxx defines ONE static array of loop/jump sizes, in beats, shared by beatloop, beatloop-roll, beatjump, and loop-move:

```
s_dBeatSizes = [0.03125, 0.0625, 0.125, 0.25, 0.5, 1, 2, 4, 8, 16, 32, 64]
```
(`loopingcontrol.cpp:27`). That is 1/32 … 64 beats, powers of two. `minBeatSize = 0.03125`, `maxBeatSize = 64`. For each size value the engine instantiates one `BeatLoopingControl`, one `BeatJumpControl`, and one `LoopMoveControl` (`loopingcontrol.cpp:155,205,219`), i.e. the controller surface is a fixed power-of-two grid.

Halve/double are pure lattice walks: `slotLoopHalve` / `slotLoopDouble` just multiply the *beatloop_size* control by 0.5 / 2.0 (`loopingcontrol.cpp:348,356`). Beatjump-size halve/double do the same on *beatjump_size* (`:1799,1805`). Sizes are clamped into `[min,max]` on any size-change request, and notably NOT clamped on the in-flight halve/double "so one does not fall out of a measure" (`:1694,1791`).

### 1b. Beat-quantized loop in/out — `slotBeatLoop(beats, keepSetPoint, enable, anchor)` (`loopingcontrol.cpp:1499`)
This is the core "make me a 4-beat loop right here" routine. Signal flow:

1. Clamp `beats` into `[minBeatSize, maxBeatSize]`; negative beats → clear the active beatloop and bail (`:1517-1525`).
2. Choose an **anchor** — Start (size grows the END) or End (size grows the START backwards) (`:1536`).
3. Compute the loop **start** position:
   - If `keepSetPoint` (resize an existing loop): reuse the existing start/end (`:1548-1561`).
   - Else (fresh loop): if **reverse** playback, first shift the cursor back by `beats` so the loop's END lands at the playhead (`:1569-1572`). Then, **if quantize is on AND the track has true beats**, snap the start via `findQuantizedBeatloopStart`; otherwise use the raw current position (`:1574-1591`).
4. Compute the loop **end** = `findNBeatsFromPosition(start, +beats)` (or, for End-anchor, start = `findNBeatsFromPosition(end, -beats)`) (`:1594-1602`).
5. Validity gate: reject if start/end invalid, start ≥ end, or end past track-end while looping (`:1604-1623`). On track-end overflow it *shrinks* `beatloop_size` rather than growing it.
6. `omitResize` guard: when loading a track or after a non-quantized manual loop, don't resize the existing loop until `beatloop_size` actually matches it (`:1629-1632`) — anti-jump.
7. Decide a **seek mode** (the audible behavior): if the start moved or the loop is freshly enabled vs the endpoints are nearly identical → `MovedOut` (do not yank the playhead forward); else `Changed` (force playhead inside) (`:1648-1675`). This is the "don't make the music jump unless you have to" rule.
8. Commit `LoopInfo{start, end, seekMode}`, push the two engine-sample COs, optionally enable looping, refresh the per-size BeatLoopingControl LEDs (`:1677-1685`).

### 1c. `findQuantizedBeatloopStart(pBeats, pos, beats)` — the snap math (`loopingcontrol.cpp:1457`)
Two regimes:
- **beats ≥ 1.0**: snap to the *nearest whole beat* — pick `prevBeat` or `nextBeat` by whichever is closer to the cursor (`:1470-1477`).
- **beats < 1.0 (sub-beat / beat-slicing)**: subdivide the current beat. `beatLength = nextBeat − prevBeat`; `loopLength = beatLength * beats`. Find which sub-beat slot the cursor sits in: `prevFraction = prevBeat + floor(framesSinceLastBeat / loopLength) * loopLength`. Then snap to the nearer of `prevFraction` and `prevFraction + loopLength` using a half-slot threshold (`framesSinceLastFraction ≤ loopLength/2`) (`:1486-1496`). This is exactly "1/4 beatloop snaps to 0/25/50/75% of the beat".

### 1d. `findNBeatsFromPosition(pos, beats)` — fractional-beat arithmetic (`beats.cpp:504`)
The beatgrid walker every loop/jump op uses. It splits `beats` into integer + fractional parts (`std::modf`), advances `n` whole beats along the grid iterator, then adds `localBeatLength * fraction` (`:516-530`). Crucially the **fraction is scaled by the LOCAL beat's length**, so on a variable-BPM grid a "0.25 beat" is 0.25 of *that* beat, not a global constant. If the cursor isn't exactly on a beat it first consumes the partial beat to the next grid line (`:510-514`). For clean-room: on a constant-BPM grid this reduces to `pos + beats * (60/bpm) * sample_rate`; the variable-grid case needs the per-segment beat lengths.

### 1e. Beat jump — `slotBeatJump(beats)` (`loopingcontrol.cpp:1763`)
Dead simple and beat-locked:
- If **inside an active loop** (looping on, not adjusting in/out, playhead within [start,end]) → it's a **loop move** instead (`:1772-1776`): jumping inside a loop slides the whole loop rather than escaping it.
- Else → `seekExact(findNBeatsFromPosition(cursor, beats))` (`:1778-1782`). `seekExact` deliberately **bypasses quantize** because "a beat jump is implicitly quantized" — the jump distance is already a beat multiple off a grid-aligned cursor. Forward = `+size`, backward = `−size` (`:1811-1820`).

### 1f. Loop move — `slotLoopMove(beats)` (`loopingcontrol.cpp:1823`)
Slides start and end by `beats` along the grid. If the current loop matches `beatloop_size` it re-derives end from `findNBeatsFromPosition(newStart, beatloop_size)` (keeps it an exact beatloop); else it shifts both edges by `beats` independently (preserves a hand-set odd length) (`:1840-1844`). Refuses to move a loop past track-end (`:1850`). Seek mode = Changed while looping, else MovedOut (`:1855`).

### 1g. Loop roll — the momentary stack (`loopingcontrol.cpp:1290,1310,1725`)
This is the performance gesture: a **momentary, slip-enabled beatloop** that springs back when released. State machine:
- **Activate-roll** (`slotBeatLoopActivateRoll`, `:1290`): `storeLoopInfo()` (save whatever loop was active), force **slip mode on** (`m_pSlipEnabled->set(1)` — the track keeps advancing silently underneath), start the beatloop, set `m_bLoopRollActive`, and **push the size onto a stack** `m_activeLoopRolls` (`:1296-1302`). The stack lets a DJ mash several roll buttons and unwind in order.
- **Deactivate-roll** (`slotBeatLoopDeactivateRoll`, `:1310`): erase this size from the stack (`:1326-1333`); if the stack is now empty, disable looping, **turn slip off** (playhead snaps to where the track silently advanced to — the signature "loop-roll catch-up"), and `restoreLoopInfo()` to bring back the pre-roll loop (`:1337-1341`); else re-arm the loop at the stack's top size (`:1345`). `storeLoopInfo/restoreLoopInfo` early-return while any roll is active so the saved loop isn't clobbered mid-stack (`:1349,1367`).
- The toggle/momentary entry `slotBeatLoopRollActivate(pressed)` (`:1725`) treats `pressed>0` as press, `≤0` as release, so it maps to a controller's hold-to-roll pad.

### 1h. Loop scale (free-stretch) — `slotLoopScale(scaleFactor)` (`loopingcontrol.cpp:296`)
Multiplies the *sample* length (not beats) by `scaleFactor`, abandoning the loop if it shrinks below `kMinimumAudibleLoopSizeFrames = 150` frames (`:19,311`) or would exceed track-end. It clears the active beatloop (the loop is no longer a clean power-of-two) and re-seeks only when shrinking under the playhead (`scaleFactor < 1.0`) (`:337`). The 150-frame floor (~3.1 ms @ 48 kHz) is the universal "audible loop" threshold reused by the loop-in/out clamps (`:761,931`).

### 1i. Detecting a loop's beat-size from raw in/out — `findBeatloopSizeForLoop` (`loopingcontrol.cpp:1416`)
Given arbitrary start/end frames, walk `s_dBeatSizes`, compute `findNBeatsFromPosition(start, size)` for each, and return the first size whose computed end lands near the actual end (`positionNear`) (`:1424-1428`). This is the reverse map: it lets vibemix label a hand-set loop ("that's a 4-bar loop") from its frame boundaries + the beatgrid. `currentLoopMatchesBeatloopSize` (`:1395`) is the boolean version against the current `beatloop_size`.

## (2) MIXXX FILE:LINE REFERENCES (method, not code-to-lift)
- `engine/controls/loopingcontrol.cpp:27` — `s_dBeatSizes[]` the power-of-two lattice
- `…:19` — `kMinimumAudibleLoopSizeFrames = 150`
- `…:296` — `slotLoopScale` (free stretch + audible-floor + reseek-on-shrink)
- `…:348 / :356` — `slotLoopHalve` / `slotLoopDouble`
- `…:1457` — `findQuantizedBeatloopStart` (nearest-beat ≥1 / sub-beat-slot <1 snap)
- `…:1499` — `slotBeatLoop` (anchor, quantize, validity, seek-mode state machine)
- `…:1416 / :1395` — `findBeatloopSizeForLoop` / `currentLoopMatchesBeatloopSize` (frames→beat-size reverse map)
- `…:1763` — `slotBeatJump` (inside-loop→move, else grid-exact seek)
- `…:1811 / :1817` — `slotBeatJumpForward` / `Backward` (±size)
- `…:1823` — `slotLoopMove`
- `…:1290 / :1310 / :1725` — beatloop-roll activate / deactivate / momentary (the slip-mode stack)
- `…:1349 / :1367` — `storeLoopInfo` / `restoreLoopInfo` (pre-roll loop preservation)
- `track/beats.cpp:504` — `findNBeatsFromPosition` (fractional-beat grid walk; fraction scaled by local beat length)
- Control keys observed: `beatlooproll_activate` (`:149`), `loop_in/loop_out/reloop_toggle/loop_exit` (`:65-98`), `beatloop_size`, `beatjump_size` COs.

## (3) TORCH-FREE FEASIBILITY — fully clear
Everything above is pure scalar arithmetic over a beatgrid array: clamps, `floor`, `modf`, nearest-neighbor selection, cumulative-sum beat positions. **No DSP, no model, no filtering.** It is numpy-trivial (or even plain Python). vibemix already has the prerequisite: a beatgrid from rekordbox ANLZ / beat-track (per the `local_deck_ingest` memory) and `state/harmonics.py`-style deterministic tables. The reverse map `findBeatloopSizeForLoop` needs only the track BPM + a loop's frame boundaries — both available from MIDI timing + the beatgrid. The `findNBeatsFromPosition` variable-grid path is the only mildly involved bit; the constant-BPM closed form (`pos + beats*(60/bpm)*sr`) covers the common case and is one line. Zero new third-party deps.

## (4) THE vibemix GAP + NEAREST INTEGRATION POINT (verified)

**The gap is real and confirmed via codegraph/grep:**

**A. Earned skill-tree has NO loop/beatjump competency.** The manifest (`src/vibemix/learn/skill_tree.py:130-164`) ships exactly 6 skills: `deck_control`, `beatmatching`, `eq_mixing`, `harmonic_mixing`, `transitions`, `phrasing_performance`. There is no `loops`/`beatjump`/`loop_roll`. The reverse map `EVENT_SKILL_MAP` (`src/vibemix/learn/skill_recognizer.py:73-77`) maps only `LAYER_ARRIVAL→transitions`, `PHASE/PHRASE_BOUNDARY→phrasing_performance`, plus the MIX_MOVE substring resolver (`_MIX_MOVE_EQ_SUBSTRINGS`/`_MIX_MOVE_DECK_SUBSTRINGS`, `:91-92`). **Loops/jumps demonstrate nothing today.**

**B. The MIDI catalog cannot even SEE a loop performance.** `midi/profiles/pioneer_ddj_flx4.json` exposes only `loop_in`/`loop_out` buttons (notes 16/17, `:32-35`) — and *no* profile has `beatloop`, `beatloop_roll`, or `beatjump` kinds. `midi/state.py::_record_move` builds the move-label vocabulary (`_low:/_mid:/_hi:/_filter:/killed/_play→/xfader`) that both the EventDetector significance set (`event_detector.py:33-35`) and the skill recognizer key off — **there is no "loop"/"roll"/"jump" move label**, so no `MIX_MOVE` ever carries a loop signature.

**Nearest integration points (concrete, in dependency order):**

1. **MIDI catalog** — add `beatloop_4`, `beatloop_roll`, `beatjump_fwd/back` button kinds to `midi/profiles/*.json` (FLX4 performance pads) and teach `midi/state.py::_record_move` to emit labels like `"A_loop:4-beat (roll)"` / `"A_beatjump:+4"`. Mixxx's `s_dBeatSizes` lattice is the exact size vocabulary to label against, and `findBeatloopSizeForLoop` is the algorithm to turn a hand-set `loop_in`→`loop_out` pair (which the catalog ALREADY captures) into a "that's a 4-bar loop" label, grounded by the beatgrid.

2. **EventDetector significance set** — extend the `MIX_MOVE` significance tuple in `state/event_detector.py:33-35` (and the cooldown'd `_fire` at `:375-378`) to treat a loop/roll/jump label as significant. A roll is a high-energy gesture; it deserves a `MIX_MOVE` (or a new `LOOP_ROLL` event) with its own cooldown so the co-host can react live ("nice 1-bar roll into the drop").

3. **Earned skill-tree** — add a `loops` (or `loop_performance`) `SkillSpec` to `skill_tree.py` SKILL_MANIFEST and a `MIX_MOVE`-substring branch (or a new event key) in `skill_recognizer.py::_candidate_skills` so a **cited** live loop/beatjump demo flips it Competent→Mastered through the existing `record_live_demo` + MAST-03 citation gate. This is the requested "new learnable performance competency" and it slots into the proven anti-slop spine with no new mechanism.

4. **R-SLOP grounding (the big one)** — `state/deck_context.py::render_move_effect_context` (`:2005`) and `move_evidence_atoms` (`:1769`) feed `apply_live_claim_guard` (`:2239`), the live-claim gate. A loop/beatjump is the rare move whose effect IS deterministically computable WITHOUT spectral inference: given the beatgrid + the known loop size, the co-host can ground the *musical* claim ("you held a 1-bar loop for 4 bars, then jumped +8 into the breakdown") from the MIDI label + beatgrid alone — boundaries are sample-exact by construction, unlike an EQ twist whose audio effect is uncertain. So a loop-effect atom can carry `rule=loop_boundary_beatgrid_exact` (a *stronger* grounding than the `rule=dsp_delta_not_causal_proof` EQ atoms currently emit at `:2033`), letting `apply_live_claim_guard` PASS a loop causal claim it would strip for a fader move. That directly attacks R-SLOP: it converts an otherwise-ungrounded performance callout into a beatgrid-grounded one.

**Net:** Mixxx's loop/beatjump engine gives vibemix (a) the exact size lattice + snap math to *label* loop gestures from MIDI+beatgrid, (b) `findBeatloopSizeForLoop` to name a hand-set loop from the `loop_in`/`loop_out` it already captures, and (c) a class of move whose effect is beatgrid-exact — the cleanest possible win against the #1 slop bug, since the boundaries are deterministic, not inferred.
