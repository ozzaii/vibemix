# MIXXX BEAT DETECTION + BEATGRID — reimplementable spec for vibemix

## 0. CRITICAL LICENSE/SCOPE NOTE
Mixxx's actual onset + tempo DSP is NOT in this checkout. The default beat plugin (`AnalyzerQueenMaryBeats`) is a thin ~116-line wrapper that delegates ALL the hard math to the bundled **qm-dsp** library (Queen Mary DSP, `<dsp/onsets/DetectionFunction.h>`, `<dsp/tempotracking/TempoTrackV2.h>`) — those headers are not vendored here. So this spec splits into: (a) the Mixxx-side glue I read directly with line cites, and (b) the qm-dsp onset/tempo algorithm, which I describe from the published QM-DSP method (the file:line cites for that half are the *call sites*, not the algorithm body — the algorithm body is GPL and not present; reimplement from the academic method, not from Mixxx code). The most valuable, fully-readable, fully-reimplementable part — the **constant-BPM grid fitter** (`beatutils.cpp`) — IS present in full and is the piece that directly closes the vibemix g14 gap.

---

## 1. THE ALGORITHM (signal flow, math, thresholds, state machine)

### Stage A — Configuration / framing (`analyzerqueenmarybeats.cpp:21-66`)
- Step size: `kStepSecs = 0.01161 s` → `stepSizeFrames = round(sampleRate * 0.01161)` = **512 frames @ 44.1 kHz** (~86 Hz frame rate, ~12 ms hop). This 12 ms hop is THE quantum that all downstream tolerances are derived from.
- Window size: `windowSize = nextPowerOfTwo(sampleRate / kMaximumBinSizeHz)`, `kMaximumBinSizeHz = 50` → at 44.1 kHz, `nextPow2(882) = 1024` samples. Gives ~43 Hz bin resolution.
- Input is **stereo downmixed to mono** before analysis (the `m_helper.processStereoSamples` path); for 8-ch STEM files Mixxx isolates the drum stem first (`analyzerbeats.cpp:208-228`) — not relevant to vibemix's stereo decks.
- Detection function type: `DF_COMPLEXSD` (complex-domain spectral difference) with `dbRise = 3`, adaptive whitening OFF (`analyzerqueenmarybeats.cpp:28-36`).

### Stage B — Onset detection function (qm-dsp `DetectionFunction::processTimeDomain`, body NOT in checkout)
The algorithm (published QM-DSP method, reimplementable clean-room):
1. Window each 1024-sample frame (Hamming), FFT → complex spectrum `X_k`.
2. **Complex Spectral Difference (COMPLEXSD)**: for each bin, predict the current bin from the previous two frames assuming constant magnitude and linear phase advance; the detection value is the Euclidean distance between predicted and observed complex bin, summed over bins. Concretely per frame `n`, per bin `k`: predicted phase `φ̂ = 2·φ[n-1] − φ[n-2]`, predicted complex `X̂ = |X[n-1]|·e^{jφ̂}`; `DF[n] = Σ_k |X[n,k] − X̂[n,k]|`. This rewards both energy onsets AND phase-deviation onsets (so it catches soft/tonal onsets, not just kick transients).
3. Output: one nonnegative scalar per 12 ms hop → a 1-D **detection-function envelope** `df[]` at ~86 Hz.
- Mixxx collects these into `m_detectionResults` (`analyzerqueenmarybeats.cpp:58-64`), then **trims trailing zeros** and **drops the first 2 frames** (startup noise) before tempo tracking (`:80-95`).

### Stage C — Tempo + beat tracking (qm-dsp `TempoTrackV2`, body NOT in checkout)
Two calls (`analyzerqueenmarybeats.cpp:97-101`):
1. `calculateBeatPeriod(df, beatPeriod)` — windowed tempo estimation. Method: slice `df` into overlapping windows (~6 s, the `df.size()/128` sizing at `:89`), autocorrelate each window, **comb-filter the autocorrelation** against a bank of candidate beat periods (a perceptually weighted tempo prior, Gaussian-ish, centered ~120 BPM — this is why Mixxx is biased toward 120-ish and octave errors happen), pick the period maximizing the comb response → one BPM estimate per window. This yields a *piecewise* (possibly varying) tempo track.
2. `calculateBeats(df, beatPeriod, beats)` — **dynamic-programming beat phase**. Given the per-window period, find the beat sequence maximizing a score = (sum of `df` value AT each chosen beat location) − (a transition penalty for inter-beat intervals deviating from the local period). This is a Viterbi-style DP over candidate frames; it locks phase onto the strongest onsets while staying period-regular. Output: a list of beat indices in detection-frame units.
3. Convert back to audio frames (`:104-110`): `beatFrame = beatIdx * stepSizeFrames + stepSizeFrames/2` (the `+ stepSize/2` centers the beat between the two hops it was detected across).

Output of the plugin: `QVector<FramePos> beats` — a raw, slightly jittery (±12 ms) list of beat positions. **This is the input to the part fully present in the checkout.**

### Stage D — Constant-vs-variable BPM model + grid fitting (FULLY PRESENT — `beatutils.cpp`, the reimplementable gold)
Mixxx by default (`m_bPreferencesFixedTempo = true`, `analyzerbeats.cpp:37`) collapses the jittery beat list into ONE constant-tempo grid. Pipeline:

**D1. `retrieveConstRegions(coarseBeats, sr)` (`beatutils.cpp:51-137`)** — segment the beat list into maximal "constant-tempo regions". Greedy two-pointer:
- `leftIndex=0`, `rightIndex=last`. Candidate `meanBeatLength = (beats[right]−beats[left])/(right−left)`.
- Walk `i` from `left+1..right`, accumulating an *ironed* prediction `ironedBeat += meanBeatLength`; `phaseError = ironedBeat − beats[i]`.
- A region is rejected if: any beat deviates by `> kMaxSecsPhaseError = 0.025 s` (= 2× the 12 ms detector step) more than `kMaxOutliersCount = 1` time, OR the first interior beat is itself an outlier, OR the running `phaseErrorSum` exceeds `kMaxSecsPhaseErrorSum = 0.1 s` (catches slow drift = wrong tempo).
- If the whole `[left,right]` span passes AND a border-symmetry check holds (`regionBorderError = |firstLen + lastLen − 2·meanLen| < kMaxSecsPhaseError/2`, `:111-119` — prevents correction beats at both ends bending the mean), store `ConstRegion{firstBeat, meanBeatLength}`, jump `left=right`, reset `right=last`.
- Else shrink: `rightIndex--` and retry. Terminates with a final zero-length sentinel region (`:135`).

**D2. `makeConstBpm(regions, sr, *pFirstBeat)` (`beatutils.cpp:140-322`)** — pick ONE global tempo:
- Find the **longest** region (most beats = most trustworthy) → `longestRegionBeatLength` (`:164-176`).
- Compute a tolerance band on beat length: `± (kMaxSecsPhaseError·sr)/numBeats` — i.e. the more beats span the region, the tighter the BPM is pinned (error averages down) (`:185-188`).
- Then try to **extend the trusted span** by scanning earlier regions (`:193-242`) and later regions (`:245-287`) that share the same tempo AND phase: a candidate region joins only if the integer beat count across the merged span is *unambiguous* (`minNumberOfBeats == maxNumberOfBeats` under the tolerance band, `:223/:273`). This is the "find the static metronome that the whole track agrees on" step — robust to intros/outros/breakdowns where the detector floats.
- `centerBpm = 60·sr/longestRegionBeatLength`, with min/max from the band (`:302-304`).

**D3. `roundBpmWithinRange(min, center, max)` (`beatutils.cpp:337-382`)** — snap to a musically-plausible BPM. Try in order, accept first snap that lands inside `(min,max)`:
1. integer BPM (`fraction=1.0`),
2. half-BPM only if `center < 85` (`fraction=2.0`),
3. 2/3-BPM only if `center > 127` (`fraction=2/3` — the classic 174↔116 dnb/halftime fold),
4. 1/3-BPM (`fraction=3.0`),
5. 1/12-BPM (`fraction=12.0`),
6. else keep raw `center`.
`trySnap(min,center,max,f) = round(center·f)/f` accepted iff `min < snap < max`.

**D4. `adjustPhase(firstBeat, bpm, sr, beats)` (`beatutils.cpp:403-429`)** — refine the grid anchor. With the rounded BPM's `beatLength`, for every detected beat compute `offset = ((beat − startOffset) mod beatLength)` folded into `[−beatLength/2, +beatLength/2]`; **average all offsets within ±0.025 s** of grid → shift `firstBeat` by that mean. This phase-locks the grid to the true downbeat cloud, rejecting outliers.

**D5. Build the grid object (`beatfactory.cpp:78-86`)**: `firstBeat = adjustPhase(makeConstBpm(...))`, anchor floored to nearest frame, then `Beats::fromConstTempo(sr, anchor, bpm)`. The stored model is **just `(sampleRate, anchorFramePos, bpm)`** — NO beat list (`beats.h:248-252`). Beat *k* = `anchor + k·(60·sr/bpm)`, extrapolated infinitely both directions.

### Variable-tempo path (non-default)
If `fixedTempo = false`, Mixxx skips D2-D4 and instead **irons each region in place** (`getBeats`, `beatutils.cpp:385-400` — within each const region it lays beats at the region's own `meanBeatLength`) and stores them as a `BeatMap` via `fromBeatPositions` (`beatfactory.cpp:90-93`). So the variable model = a piecewise-constant beat list, NOT a global BPM. The grid API (`beats.h:308-359`: `findNextBeat`/`findClosestBeat`/`findNthBeat`/`findNBeatsFromPosition`) is identical for both models — the consumer never branches.

### Confidence / re-analysis state machine (`analyzerbeats.cpp:131-197`)
There is NO explicit numeric confidence emitted. "Confidence" is implicit: (a) `<2` beats → no grid; (b) `<16` beats (`kMinRegionBeatCount`) → fall back to dumb `calculateAverageBpm = 60·N·sr/(last−first)` (`beatutils.cpp:42-43`); (c) a grid is *re-analyzed* if BPM invalid (≤0), or imported-from-other-software + user opted in, or version/subversion changed (`shouldAnalyze`). The grid carries a `version`/`subVersion` string stamping which code + settings produced it (`beatfactory.cpp:14-49`, rounding version "V4").

### Downbeat / phrase
**Mixxx does NOT detect downbeats or phrases in this analyzer.** The anchor is just "the first detected beat near the start" (`makeConstBpm:310-319` comment explicitly says *"ideally the anchor should be the first proper downbeat... this is a temporary fix"*). 4/4 bar grouping is assumed implicitly elsewhere (the `BpmScale` enum `beats.h:266-275` and bar=4 conventions), never derived from audio. **So Mixxx is a beat-only engine; downbeat/phrase is an open gap in Mixxx too** — vibemix already gets real downbeat/phrase from Rekordbox ANLZ PSSI (`anlz_ingest.py`) and that remains the better source.

---

## 2. MIXXX file:line REFERENCES (for the method)
- Framing/config constants: `/tmp/mixxx-src/src/analyzer/plugins/analyzerqueenmarybeats.cpp:21-37` (kStepSecs 0.01161, kMaximumBinSizeHz 50, DF_COMPLEXSD, dbRise 3).
- init (step/window sizing): `analyzerqueenmarybeats.cpp:49-66`.
- DF collection + trim-first-2: `analyzerqueenmarybeats.cpp:77-95`.
- Tempo+beat track call + frame conversion (+stepSize/2): `analyzerqueenmarybeats.cpp:97-110`.
- Plugin selection / fixed-tempo default / fast-analysis cap: `analyzer/analyzerbeats.cpp:32-99, 261-282`.
- Re-analyze decision (implicit confidence): `analyzer/analyzerbeats.cpp:131-197`.
- **Const-region segmentation:** `track/beatutils.cpp:51-137` (constants at `:12-17`: kMaxSecsPhaseError 0.025, kMaxSecsPhaseErrorSum 0.1, kMaxOutliersCount 1, kMinRegionBeatCount 16).
- **Global const BPM fit + region extension:** `track/beatutils.cpp:140-322`.
- **Musical BPM rounding ladder:** `track/beatutils.cpp:324-382`.
- **Grid phase-anchor refine:** `track/beatutils.cpp:403-429`.
- Variable-tempo iron-in-place: `track/beatutils.cpp:385-400`.
- Grid assembly (const vs map): `track/beatfactory.cpp:51-98`; version/subversion: `:14-49`.
- Grid model (no beat list; `fromConstTempo` / `fromBeatPositions`; find* API): `track/beats.h:248-359`, `hasConstantTempo` at `:282`.
- The DSP bodies (DetectionFunction, TempoTrackV2) are NOT vendored — only the `#include` at `analyzerqueenmarybeats.cpp:1-2`. Reimplement those from the QM-DSP / complex-spectral-difference + DP-beat-tracking literature, not from Mixxx.

---

## 3. TORCH-FREE FEASIBILITY (Python / vibemix default stack)
**Fully feasible, no torch / no transformers / no librosa.** Maps cleanly onto vibemix's existing `onnxruntime + PyAV + numpy` stack:
- **Stage D (grid fitter)** — pure numpy/Python, a direct port of the ~430 fully-readable lines in `beatutils.cpp`. No DSP, no model. This is a 1-2 day clean-room job and is the highest-value piece (it's the missing `BeatGrid` producer). Math is all scalar/array arithmetic + `fmod` + `round`.
- **Stage B (onset DF)** — `numpy.fft.rfft` over 1024-sample Hamming-windowed 512-hop frames; complex-spectral-difference is ~20 lines of numpy. No external dep beyond numpy. PyAV already decodes audio to numpy in the library path (`embed-folder`), so the front-end exists.
- **Stage C (tempo + DP beat track)** — autocorrelation comb (numpy) + a Viterbi/DP loop (plain Python or numpy). This is the only nontrivial chunk; ~150 lines. Reimplement from the published method to avoid GPL.
- Two cheaper alternatives if Stage C is too much: (i) **`madmom`** has a high-quality DBN beat tracker but pulls heavy deps (and Cython) — off-stack, reject; (ii) ship an **ONNX beat tracker** (e.g. a small TCN/Beat-This-style model exported to ONNX) and feed its beat list straight into Stage D — this fits the existing CUE-DETR ONNX pattern (`library/cue_detr.py`) exactly and keeps the torch-free runtime. **Recommended:** numpy Stage B + ONNX (or numpy autocorr) Stage C + **numpy port of Stage D** — Stage D is the part that turns ANY beat list into the clean `(anchor, bpm)` grid the Judge needs.

---

## 4. VIBEMIX GAP MAPPED + NEAREST INTEGRATION POINT (codegraph-verified)

**The exact gap (g14, the mastery hole):** `grade_beatmatch(grid_a: BeatGrid, grid_b: BeatGrid, state: DeckState)` (`src/vibemix/learn/beatmatch_judge.py:83`) already exists and is correct, and its consumer `skill_recognizer` already gates "Mastered" on a cited LOCKED grade. But there is **NO module in vibemix that produces a `BeatGrid` from raw track audio.** `BeatGrid` (`src/vibemix/audio/grid.py:24`, codegraph-confirmed) takes exactly `(anchor_frame, bpm, sample_rate)` — which is *precisely* the `(firstBeat, roundBpm, sampleRate)` triple that Mixxx Stage D (`makeConstBpm` + `adjustPhase`) computes. The two ends of g14 are wired to each other but the *source* is missing: a beat→grid producer.

**What to build:** a new module `src/vibemix/audio/beatgrid_detect.py` (sits next to `grid.py` and `miniplayer.py`) exposing e.g. `detect_beatgrid(samples: np.ndarray, sample_rate: int) -> BeatGrid`. Internally: Stage B (numpy FFT DF) → Stage C (beat list, numpy autocorr+DP or ONNX) → **Stage D ported from `beatutils.cpp`** (`retrieveConstRegions` → `makeConstBpm` → `roundBpmWithinRange` → `adjustPhase`) → `return BeatGrid(anchor_frame=firstBeat, bpm=roundBpm, sample_rate=sample_rate)`.

**Integration wiring (the live path that closes g14):**
1. `MiniDeck` (`src/vibemix/audio/miniplayer.py:99`, codegraph-confirmed) loads `src_a`/`src_b` whole-track slabs and owns the playhead → call `detect_beatgrid(src_a, sr)` and `detect_beatgrid(src_b, sr)` ONCE at load to get `grid_a`, `grid_b`.
2. A practice loop reads `deck.state()` (`miniplayer.py:137` → `DeckState`) each block and calls `grade_beatmatch(grid_a, grid_b, state)`.
3. On a non-abstain LOCKED grade, fire the `BEATMATCH_GRADED` event with `grade_to_event_extra(grade)` (`beatmatch_judge.py:145`) AND register the `("ev","BEATMATCH_GRADED",t)` citation in `EvidenceRegistry` — that is the cited live demonstration `skill_recognizer.recognize` (codegraph + grep-confirmed caller, `src/vibemix/learn/skill_recognizer.py`) needs to flip beatmatching to "Mastered" under invariant #2.

**Two important "don't" notes for the reimplementer:**
- Stage D's BPM rounding ladder is biased toward EDM (integer/half/2:3 folds). vibemix's hardtechno/dnb library is exactly the case where the 2/3 fold (`:357-364`) and 1/12 fold (`:373-378`) earn their keep — keep them; do not "simplify" to integer-only.
- For the **owned-deck Judge specifically**, you often do NOT need Stages B/C at all: when vibemix already has a real grid from Rekordbox ANLZ (`AnlzBeatGrid`, `library/anlz_ingest.py:44` — `times_s`/`bpms`/`beat_in_bar`, which uniquely ALSO carries true downbeat/phrase) you can construct `BeatGrid(anchor_frame=times_s[0]*sr, bpm=bpms[0], sample_rate=sr)` directly and skip audio detection entirely. The audio Stages B-D are the fallback for tracks with no ANLZ — and the fallback is what makes the practice deck work on arbitrary user audio without Rekordbox. Build Stage D first (cheap, exact, GPL-safe); add B/C only for the no-metadata case.

Relevant absolute paths: `/Users/ozai/projects/dj-set-ai/src/vibemix/audio/grid.py` (BeatGrid, the target type), `/Users/ozai/projects/dj-set-ai/src/vibemix/audio/miniplayer.py` (MiniDeck/DeckState, the owner), `/Users/ozai/projects/dj-set-ai/src/vibemix/learn/beatmatch_judge.py` (grade_beatmatch, the consumer), `/Users/ozai/projects/dj-set-ai/src/vibemix/learn/skill_recognizer.py` (the credit gate), `/Users/ozai/projects/dj-set-ai/src/vibemix/library/anlz_ingest.py` (AnlzBeatGrid, the metadata shortcut). New module to create: `/Users/ozai/projects/dj-set-ai/src/vibemix/audio/beatgrid_detect.py`.
