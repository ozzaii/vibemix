# MIXXX CUE LOGIC — ALGORITHM EXTRACTION (learn-from-spec, GPL never vendored)

## (1) THE ALGORITHM (clean-room reimplementable in numpy)

Two distinct mechanisms. The auto-detection that vibemix actually wants lives in `analyzersilence.cpp`, NOT `cuecontrol.cpp`. `cuecontrol.cpp` is the live state machine that consumes already-placed cues and does quantize-to-beat.

### A. AUTO INTRO/OUTRO DETECTION — the -60 dB "first-sound / last-sound" rule (analyzersilence.cpp)

This is the heuristic. It is brutally simple and that is the point — it is NOT structural drop/breakdown detection, it is purely **where does audible sound begin and end**.

**Core constant:** `kSilenceThreshold = 0.001` linear amplitude == -60 dB (`fabs(sample) >= 0.001`). A sample is "sound" if its absolute float value (sample range ±1.0) is ≥ 0.001; otherwise silence. There is NO smoothing, NO RMS window, NO hysteresis, NO adjacent-block requirement — it is a raw per-sample `abs() >= threshold` test (`analyzersilence.cpp:11,27-31`).

**Streaming state machine** (`processSamples`, lines 86-105):
- State: `signalStart = -1`, `signalEnd = -1`, `framesProcessed = 0`.
- Per chunk of interleaved samples:
  - If `signalStart < 0` (not yet found): scan FORWARD for the first sample with `abs >= threshold`; if found, `signalStart = framesProcessed + firstSoundSampleIndex / channelCount` (convert sample index → frame index by dividing by channel count).
  - Once `signalStart >= 0`: scan that same chunk BACKWARD (reverse iterator) for the last sample with `abs >= threshold`; if found, `signalEnd = framesProcessed + lastSoundSampleIndex / channelCount + 1`. (The +1 makes end exclusive/length-correct.) `signalEnd` is overwritten every chunk that contains sound, so after the whole file it equals the last sounding frame.
  - `framesProcessed += chunkFrames`.
- Finalize (`storeResults`, lines 110-119): if no sound ever found, `signalStart = 0` and `signalEnd = framesProcessed` (whole track). `firstSoundPosition = signalStart`, `lastSoundPosition = signalEnd`, both in FRAMES.

**What it produces (3 cues):**
- `N60dBSound` cue: a span cue from `firstSoundPosition` to `lastSoundPosition` (the audible region). This is the cached "first/last sound" record (`analyzersilence.cpp:121-135`).
- **Intro cue** = a cue whose START is `firstSoundPosition`, END left invalid/open (`setupMainAndIntroCue`, lines 142-171). Intro START = first audible sample. Intro END is NOT auto-detected — left for the user.
- **Outro cue** = a cue whose START is invalid/open, END is `lastSoundPosition` (`setupOutroCue`, lines 174-183). Outro END = last audible sample. Outro START is NOT auto-detected.
- **Main cue** (the cue point the deck seeks to on load): if the track has no valid main cue, OR is a pre-2.3 track with main cue at default 0.0 and no intro yet, set main cue = `firstSoundPosition` (lines 146-162). Optional config `SetIntroStartAtMainCue` makes intro start follow an existing main cue instead.

**Re-analysis guard** (`shouldAnalyze`, lines 15-24): skip if all three of {Intro, Outro, N60dBSound} exist and N60dBSound has non-zero length. The fixed `kSilenceThreshold` doubles as a change-detector — re-running on identical samples yields identical frames, so a mismatch flags a file/decoder change (`verifyFirstSound`, lines 74-84).

**Key honesty caveat for vibemix grounding:** Mixxx's "intro/outro" are only the silence boundaries of the file, NOT musical structure. Intro END and Outro START (the parts a DJ actually mixes on) are left for the human. So this complements CUE-DETR rather than replacing it: CUE-DETR finds structural mix points (build/breakdown/drop); the silence rule finds the hard track edges (first/last sound) deterministically and cheaply. Use the silence rule to bound CUE-DETR (no cue before first-sound or after last-sound) and to ground "the track has actually started / ended."

### B. QUANTIZE-TO-BEAT (cuecontrol.cpp — applies when placing or recalling any cue)

Two functions, both gated by a `quantize` flag:

- **`getQuantizedCurrentPosition`** (lines 2373-2396): when setting a cue at the live playhead. If quantize off → return raw current frame. If on → return `m_pClosestBeat` (the nearest beat, precomputed by the beat engine), but only if that beat is valid AND ≤ track end (an interpolated beat past the end is unreachable, so fall back to raw position).
- **`quantizeCuePoint`** (lines 2398-2438): when loading a stored cue. Clamp position to `[0, trackEnd]`. If quantize off OR no beatgrid → return as-is. Else `quantizedPosition = beats->findClosestBeat(position)`; accept it only if valid AND ≤ trackEnd, else return the unquantized position. Math is plain "nearest beat" = `argmin |beatPos - position|` over the grid.

Stored cue positions are NEVER mutated — quantization is applied only to the control-object value that the engine/UI reads (the comment at lines 657-660 is explicit: raw cue list stays unquantized so toggling quantize doesn't corrupt the saved cue). **This is the same single-writer / don't-mutate-the-source-of-truth discipline vibemix already enforces (Invariant #1).**

### C. CUE STATE MACHINE (the "drop on this cue" behavior — cuecontrol.cpp)

A `TrackAt` 3-state classifier drives all cue-button behavior (`getTrackAt`, lines 2358-2371):
- `End` if `currentPos >= trackEndPosition`.
- `Cue` if `fabs(currentPos - mainCuePos) < 0.5` frames (i.e. within half a frame = sitting exactly on the cue).
- `ElseWhere` otherwise.

The Pioneer/CDJ cue button (`cueCDJ`, lines 1554-1619) — the canonical DJ behavior — is a state machine on (`freely_playing`, `trackAt`, `previewing`):
- Pressed while **freely playing** (playing AND not scratching) OR at End → stop + seek to cue.
- Pressed while paused **at Cue** → start playing (this is the "preview"/hold-to-play).
- Pressed while paused **ElseWhere** → SET a new cue at current (quantized) position; if quantize on, also seek to the new cue.
- Released while previewing → stop + seek back to cue (the "drop back to cue on release" feel).

Hotcue activation (`hotcueActivate`, lines 1218-1274): pressing an existing hotcue while playing → goto; while paused → preview-play from the hotcue; pressing an empty hotcue → set it at current quantized position. There are Denon and CUP (`cueDenon`/`cuePlay`) variants with different latch semantics, switched by `cueDefault` (lines 1707-1723) on a `CueMode` enum.

**For vibemix the load-bearing pieces are:** the `TrackAt::Cue` test (`|pos - cuePos| < 0.5 frame`) = "the deck is sitting on its cue", and the "drop on this cue" = seek-to-cue-then-play gesture. Those are exactly the events the co-host should be able to ground ("you dropped on the cue", "you're parked on the intro cue").

---

## (2) MIXXX FILE:LINE REFERENCES (method, not code to lift — GPL)

- **Auto intro/outro/silence detection (THE algorithm):** `/tmp/mixxx-src/src/analyzer/analyzersilence.cpp`
  - `kSilenceThreshold = 0.001` (-60 dB) — `:11`
  - per-sample sound test `fabs(elem) >= kSilenceThreshold` — `:26-31`
  - streaming first/last-sound scan — `processSamples` `:86-105`; `findFirstSoundInChunk` `:62-64`; `findLastSoundInChunk` (reverse iterator, -1 fixup) `:66-71`
  - finalize → N60dBSound + Intro + Outro + Main cues — `storeResults` `:110-139`
  - intro = firstSound..open, main-cue fallback — `setupMainAndIntroCue` `:142-171`
  - outro = open..lastSound — `setupOutroCue` `:174-183`
  - re-analysis guard / change-detector — `shouldAnalyze` `:15-24`, `verifyFirstSound` `:74-84`
  - header / state fields — `/tmp/mixxx-src/src/analyzer/analyzersilence.h:37-58`
- **Quantize-to-beat:** `/tmp/mixxx-src/src/engine/controls/cuecontrol.cpp`
  - `getQuantizedCurrentPosition` (set-time, closest-beat-or-raw) — `:2373-2396`
  - `quantizeCuePoint` (load-time, `findClosestBeat`, clamp to trackEnd) — `:2398-2438`
  - don't-quantize-the-stored-cue rationale — `:657-660`, `:855-856`
- **Cue state machine / "drop on cue":** `cuecontrol.cpp`
  - `getTrackAt` (End / Cue `<0.5 frame` / ElseWhere) — `:2358-2371`
  - Pioneer CDJ button — `cueCDJ` `:1554-1619`; Denon `cueDenon` `:1621-1659`; CUP `cuePlay` `:1661-1705`; dispatch `cueDefault` `:1707-1723`
  - hotcue set/goto/activate/preview — `hotcueSet` `:942-1083`, `hotcueGoto` `:1085-1093`, `hotcueActivate` `:1218-1274`, `hotcueActivatePreview` `:1276-1307`
  - hotcue auto-set at quantized current position — `hotcueSet` → `getQuantizedCurrentPosition` `:990`
  - load cues + sync main cue (twice-stored legacy) — `loadCuesFromTrack` `:715-857`
  - seek-on-load priority (IntroStart default) — `trackLoaded` `:574-697`, `getSeekOnLoadPreference` `:2448-2450`
  - intro/outro manual set with ordering validation (intro<introEnd<outroStart<outroEnd) — `introStartSet` `:1751-1808`, `introEndSet` `:1851-1908`, `outroStartSet` `:1954-2011`, `outroEndSet` `:2057-2114`

---

## (3) TORCH-FREE FEASIBILITY

**Trivially feasible — pure numpy, zero new deps.** The whole silence algorithm is `abs() >= 0.001` over a decoded mono float array. vibemix already decodes via PyAV/FFmpeg (the `cue_detect.py::decode_to_mono` / `ANALYSIS_SR` path) and already does numpy DSP. A clean-room implementation is ~15 lines:

```
# vibemix's own code, NOT Mixxx's — re-derived from the -60 dB spec:
sound = np.abs(mono) >= 0.001            # CONST re-derived: db2ratio(-60) = 0.001
idx = np.flatnonzero(sound)
first_s = idx[0] / sr if idx.size else 0.0
last_s  = (idx[-1] + 1) / sr if idx.size else len(mono) / sr
```
Streaming vs whole-array is an implementation choice — vibemix can do the whole-array version (it already loads tracks for CLAP embedding, so the decode is free / cacheable). Quantize-to-beat is `beats[np.argmin(np.abs(beats - pos))]` — also pure numpy, and vibemix already has a `BeatGrid` (`audio/grid.py`, consumed by `beatmatch_judge`). `TrackAt` classification and the cue-button state machine are integer/float comparisons — no math libraries. **No torch, no transformers, no librosa, no scipy needed.** Note the `±1.0` sample-range assumption: vibemix must normalize decoded PCM to float ±1.0 before applying the 0.001 threshold (or scale the threshold to the actual sample dtype).

---

## (4) VIBEMIX GAP MAPPING + NEAREST INTEGRATION POINT (codegraph-verified)

**Gap 1 — bound/ground structural cues with hard track edges (PRIMARY).** vibemix already has the rich structural producer: `CUE-DETR` (`src/vibemix/library/cue_detr.py:1`, `detect_cue_positions:287`, torch-free ONNX, candidates → refined → labeled intro/build/breakdown/drop/outro) feeding `CueAnchor` (`src/vibemix/library/cue_types.py:42`) through `cue_engine.detect_cues_auto` (`cue_engine.py:156`) and `build_cue_anchors` (`cue_engine.py:76`), with a dep-free fallback `cue_detect.detect_cues` (`cue_detect.py:599`). What it lacks is Mixxx's cheap deterministic FIRST-SOUND / LAST-SOUND boundary. **Integration point: add a `first_sound_s`/`last_sound_s` helper as a new function in `src/vibemix/library/cue_detect.py`** (it already owns `decode_to_mono` + `ANALYSIS_SR` and is the dep-free heuristic tier), then have `cue_engine.build_cue_anchors` / `detect_cues_auto` clamp every CUE-DETR/heuristic anchor to `[first_sound_s, last_sound_s]` and emit a deterministic `intro` anchor at `first_sound_s` + `outro` anchor ending at `last_sound_s` when the model is silent there. This raises the floor: even with no model present, vibemix gets a correct, fast, confidence-1.0 intro-start and outro-end. The silence span also gives an honest confidence prior for `CueAnchor.confidence` (a "drop" the model places inside the silent tail is wrong by construction → suppress).

**Gap 2 — `cue_agreement` gets a deterministic reference leg.** `cue_agreement` (`cue_agreement.py:116`) compares DJ-placed vs auto anchors. The first-sound/last-sound boundaries are a ground-truth check Mixxx itself uses as a change-detector (`verifyFirstSound`) — vibemix can flag any DJ/auto intro placed before first-sound or outro after last-sound as definitely wrong, sharpening agreement scoring with zero model cost.

**Gap 3 — quantize-to-beat for the practice deck / beatmatch grading.** `grade_beatmatch` (`src/vibemix/learn/beatmatch_judge.py:83`) already ports Mixxx *sync* math (it cites `bpmcontrol.cpp`/`synccontrol.cpp` scars) and takes a `BeatGrid` + `DeckState` from `MiniDeck` (`src/vibemix/audio/miniplayer.py:99`, confirmed: `render_block:130`, `state:137` → `DeckState`). The MISSING piece for the "own mini DJ player / practice deck" idea is cue placement + quantize-to-beat + the `TrackAt`/cue-button state machine so the practice deck can grade real cue/hot-cue use, not just beatmatch. **Integration point: a new `src/vibemix/audio/cue_deck.py` (or extend `miniplayer.py`)** implementing `getQuantizedCurrentPosition` (snap to nearest `BeatGrid` beat) and the `TrackAt` 3-state classifier (`End` / within-0.5-frame `Cue` / `ElseWhere`) over `DeckState.frame_cursor` + `BeatGrid`. Because the practice deck OWNS the playhead and grid (same moat `beatmatch_judge` exploits), it can grade "did the student drop ON the beat-quantized cue" exactly. Note vibemix already has `audio/cues.py` and `state/transition_clock.py` referencing cue concepts — check those before adding a module.

**Gap 4 — live grounding for "drop on this cue" reactions.** The `TrackAt::Cue` test (`|pos - cuePos| < 0.5 frame`) and the CDJ seek-then-play gesture are exactly groundable live events. Wired through `state/event_detector.py` (which already emits typed events with cooldowns) and `state/evidence_registry.py` (`src/vibemix/state/evidence_registry.py`, the Invariant-#2 citation backing), a "you dropped on the intro cue" reaction becomes citation-grounded instead of slop — the cue position + the playhead-within-0.5-frame fact are both real, registry-resolvable evidence. **Integration point: `src/vibemix/state/event_detector.py` (emit a `CUE_HIT`/`DROP_ON_CUE` event) backed by an `EvidenceRegistry` entry**, consumed by the live `coach_loop` (`src/vibemix/runtime/coach.py`).

**Net:** the silence rule is a tiny, deterministic, torch-free FLOOR that hardens the existing CUE-DETR stack (Gaps 1-2, library side); the quantize-to-beat + `TrackAt` state machine is the missing cue layer for the owns-the-deck practice player that lets the learning engine grade real cueing the way `beatmatch_judge` already grades beatmatching (Gaps 3-4, runtime/learn side). All four are clean-room numpy reimplementations from the -60 dB / nearest-beat / 0.5-frame specs above — never copy Mixxx GPL source.
