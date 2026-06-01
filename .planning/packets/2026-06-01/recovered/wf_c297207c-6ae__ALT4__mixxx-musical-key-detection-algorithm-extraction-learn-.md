# MIXXX MUSICAL KEY DETECTION — Algorithm Extraction (learn-from-spec, GPL never vendored)

## (1) THE ALGORITHM (clean-room numpy reimplementation spec)

Mixxx's default key detector is the **Queen Mary (qm-dsp) key detector**, plugin id `"qm-keydetector:2"`. It is a classic **constant-Q chromagram + key-profile correlation** pipeline. Two layers: the Mixxx wrapper (fully present, read below) and the qm-dsp DSP core (`GetKeyMode` — a build-time submodule, NOT in this checkout; its config + signal flow are fully determined by the wrapper).

### A. Signal flow (the framing layer — fully visible in this checkout)

**A1. Downmix to mono + per-window framing** (`DownmixAndOverlapHelper`, `buffering_utils.cpp:37-82`):
- Stereo → mono by simple average: `mono[i] = (L[i] + R[i]) * 0.5` (`buffering_utils.cpp:51-53`). Mixxx comments "stereo doesn't help" — for key, summing channels is fine.
- A sliding window of `windowSize` frames steps forward by `stepSize` frames. `windowSize`/`stepSize` come from `GetKeyMode::getBlockSize()`/`getHopSize()` (`analyzerqueenmarykey.cpp:56-57`).
- **First window is centre-padded**: write cursor starts at `windowSize/2` (`buffering_utils.cpp:16`) so the very first emitted window has its centre on sample 0 (makes the first result valid). Reimplement: prepend `windowSize/2` zeros.
- On each full window the callback runs, then the buffer slides left by `stepSize` (`buffering_utils.cpp:75-78`).
- **Tail flush** (`finalize`, `buffering_utils.cpp:26-34`): append at least `windowSize/2 - 1` zeros so the last real samples get a full window.

**A2. Per-window key classification** (`analyzerqueenmarykey.cpp:59-76`): each window → `GetKeyMode::process(window)` → an integer key code 1..24 (validated against the `ChromaticKey` enum). This is the per-frame key estimate.

**A3. Run-length segmentation, NOT per-window storage** (`analyzerqueenmarykey.cpp:68-74`): only store a `(key, frame_position)` pair **when the key changes** from the previous window (`if (key != m_prevKey)`). The output is a `KeyChangeList` — a compressed timeline of key-change boundaries. `frame_position` is the running input-frame count at that window.

### B. The qm-dsp DSP core (`GetKeyMode` — the math, from the Mixxx-supplied config)

The Mixxx `Config` struct (`analyzerqueenmarykey.cpp:34-55`) pins every parameter:

```
sampleRate         = track sample rate (e.g. 44100)
tuningFrequency    = 440 Hz (kTuningFrequencyHertz, line 17)
hpcpAverage        = 10
medianAverage      = 10
frameOverlapFactor = 1     # 1 = no chroma overlap (fast, skips input); 8 = full overlap
decimationFactor   = 8
```

> Note a Mixxx quirk worth copying intentionally: the local `Config` struct is **declared but never passed** — line 54 constructs `GetKeyMode::Config config(sampleRate, kTuningFrequencyHertz)` directly, so qm-dsp's own defaults for hpcpAverage/medianAverage/decimation apply. The struct documents the intended values; treat them as the qm-dsp defaults to replicate.

The qm-dsp `GetKeyMode` algorithm (Noland & Sandler, "Signal Processing Parameters for Tonality Estimation" — the published method behind these files):

1. **Decimate** the mono window by `decimationFactor = 8` (so 44100 → ~5512 Hz working rate). Cheap anti-alias + decimate. This is why analysis is fast: the chromagram runs at 1/8 the rate. (`Decimator.cpp` in qm-dsp.)
2. **Constant-Q transform** over a frequency range spanning a few octaves of the bass/mid register, with **36 bins per octave** (3 bins per semitone) referenced to `tuningFrequency = 440 Hz`. The CQ uses log-spaced geometric centre frequencies `f_k = f_min · 2^(k/36)` with constant Q = `1/(2^(1/36) − 1)`. (`ConstantQ.cpp`.)
3. **HPCP / Chromagram**: fold the 36-bin-per-octave CQ magnitude across all octaves into a **single 36-element chroma vector**, then peak-pick / reduce to 12 pitch classes. `hpcpAverage = 10` temporally smooths the chroma over ~10 hop-frames (a moving average). The 3-bins-per-semitone resolution lets it find the true tuning peak and tolerate ±tuning drift. (`Chromagram.cpp`.)
4. **Key-profile correlation (the decision)**: build a **24-row key map** (12 major + 12 minor profiles). qm-dsp uses a tone-profile (Krumhansl-style weighted templates) tiled by all 12 rotations for each mode. Correlate the smoothed chroma against all 24 rotated profiles; the **argmax correlation = the key for that window**. `medianAverage = 10` median-filters the per-frame key decision over ~10 frames to suppress single-frame flicker before emitting.
5. Output integer 1..24 mapped to `ChromaticKey` (1..12 = C..B major, 13..24 = C..B minor — the Mixxx enum order, see `s_traditionalKeyNames`, `keyutils.cpp:45-70`).

### C. From per-window timeline to ONE global key (THE segmentation→single-key step — fully present)

`KeyUtils::calculateGlobalKey` (`keyutils.cpp:631-660`) — a **duration-weighted histogram vote**, NOT a mode/mean:
- If only one key change, return it (`keyutils.cpp:633-635`).
- Otherwise build `key_histogram[key] += (next_change_frame − this_change_frame)` for each segment; the last segment runs to `totalFrames` (`keyutils.cpp:641-647`). So each key accumulates the **total number of frames it was the active key**.
- **Global key = argmax of total duration** (`keyutils.cpp:649-658`). The key the track spent the most time in wins. Ties: first-seen wins (strict `>`).

This is the clean-room target for the single-key emit: run-length segment the per-window estimates, sum segment durations per key, pick the longest.

### D. Wrapper config / gates (`analyzerkey.cpp`)
- **Fast-analysis mode**: only the first `kFastAnalysisSecondsToAnalyze = 60` seconds (`constants.h:18`, `analyzerkey.cpp:87-91`) — for our purposes, 60s of the most representative section is plenty and cheap.
- Block feed size `kAnalysisFramesPerChunk = 4096` frames/chunk (`constants.h:13`) — just I/O chunking, independent of the FFT window.
- Tuning offset (`keyfactory.cpp:66-84`): RapidEvolution-style "`A#m +50`" cents offsets are parsed and folded into the key + a stored `tuning_frequency_hz`. Not needed for detection, only tag-import.

### Reimplementation summary (numpy)
```
decimate(mono, 8) → STFT/CQ (36 bins/oct, ref 440Hz) → fold to 12-PC chroma
  → moving-avg smooth (hpcpAverage≈10 frames)
  → correlate vs 24 key profiles → argmax per frame
  → median-filter (medianAverage≈10) → run-length segment
  → duration-weighted histogram argmax → ONE global key (1..24)
```

## (2) MIXXX FILE:LINE REFERENCES (method, not code to lift)

- `src/analyzer/plugins/analyzerqueenmarykey.cpp:34-57` — full config (440Hz tuning, hpcpAverage/medianAverage=10, decimation=8, overlap=1) + `getBlockSize`/`getHopSize`.
- `src/analyzer/plugins/analyzerqueenmarykey.cpp:59-76` — per-window `GetKeyMode::process` → run-length `(key, frame)` change list.
- `src/analyzer/plugins/buffering_utils.cpp:37-82` — mono downmix (`*0.5`), overlap windowing, centre-pad first window (`:16`), tail flush (`:26-34`).
- `src/analyzer/analyzerkey.cpp:48-124` (init), `:159-209` (processSamples), `:215-231` (storeResults) — orchestration + fast-analysis 60s gate.
- `src/analyzer/constants.h:11-18` — `kAnalysisFramesPerChunk=4096`, `kFastAnalysisSecondsToAnalyze=60`.
- `src/track/keyutils.cpp:631-660` — `calculateGlobalKey` duration-weighted histogram argmax (the single-key emit).
- `src/track/keyutils.cpp:314-356` — `keyToOpenKeyNumber` (the Mixxx key→OpenKey ring, which is Camelot rotated).
- `src/track/keyfactory.cpp:124-162` — `makePreferredKeys` (assembles the result + tuning).
- DSP core is `lib/qm-dsp/dsp/{chromagram/Chromagram.cpp, chromagram/ConstantQ.cpp, keydetection/GetKeyMode.cpp, rateconversion/Decimator.cpp}` per `CMakeLists.txt:4591-4599` — **a build-time submodule, NOT vendored in /tmp/mixxx-src** (no `lib/` dir; confirmed). The math above is the published qm-dsp method that those files implement, fully parameterized by the Mixxx config.

## (3) TORCH-FREE FEASIBILITY (numpy / onnxruntime path)

**Fully feasible, no torch/transformers/librosa needed.** Every stage maps to numpy + the existing PyAV/FFmpeg decode the repo already uses:
- **Decode + decimate**: PyAV → float32 mono → `scipy`-free polyphase decimate (or FFmpeg `aresample` to ~5.5kHz; or naive `signal[::8]` after a numpy FIR low-pass). vibemix already does 48k→16k resample, so the resample muscle exists.
- **Constant-Q → chroma**: a 36-bin/oct CQ kernel is a precomputed complex matrix `K[bins, fft]`; chroma = `|K @ rfft(window)|`. Pure numpy. (No librosa — build the CQ kernel once from `f_k = f_min·2^(k/36)`, exactly the librosa-free Slaney-style approach the CLAP mel path already established in this repo.)
- **Key profiles**: 24 fixed 12-vectors (Krumhansl or Temperley templates) as a `(24,12)` numpy constant; correlation = `chroma @ profiles.T` argmax.
- **Smoothing / median / run-length / histogram**: trivial numpy (`np.convolve`, `np.median` sliding, `np.diff` for change points, `np.bincount`-style duration sum).

No model download required (unlike CLAP/CUE) — it's deterministic DSP. It would live alongside the torch-free DSP helpers, install-free in the base dep set. Accuracy caveat to set expectations: qm-dsp key detection is ~70-75% exact / ~85%+ within-a-relative on EDM; good enough as a *grounded* source-key (and it degrades to honest-unknown on low confidence, which fits Invariant #3). License: this is a **clean-room reimplementation of the published algorithm from numbers/method** — never copy qm-dsp source; GPL stays untouched.

## (4) VIBEMIX GAP MAPPED + INTEGRATION POINT (verified via codegraph)

**Gap closed: "source-key detection accuracy" + the missing key *producer*.** Today vibemix has a complete key *consumer* stack but **no audio→key detector** — keys only come from Rekordbox/file tags. Verified via codegraph:

- **Consumer that's already wired and waiting**: `src/vibemix/state/harmonics.py` — `to_camelot()` (`harmonics.py:83`) normalizes a key tag → Camelot; `is_clash`/`compatible`/`semitone_distance` (`harmonics.py:238-295`) are the deterministic Camelot-wheel verdicts the coach narrates. These take a **key string** and need a source.
- **Where the string comes from today**: `_practice_track` (`harmonic_practice.py:171`) does `camelot = getattr(row,"camelot") or to_camelot(getattr(row,"key"))` — i.e. it depends entirely on a pre-existing tag. Same pattern across `library/rekordbox.py`, `library/sequencer.py`, `library/discovery.py`, `intel/transition_scorer.py`, `runtime/coach.py`, `runtime/suggestion.py` (all surfaced by codegraph as key/camelot consumers). **None of them can run on an untagged WAV/AIFF.**

**Nearest integration point**: add a torch-free `detect_key(audio: np.ndarray, sr: int) -> str | None` (returns a classical spelling like `"Am"`, or honest `None`) as a new producer in `src/vibemix/library/` — sibling to the existing offline analyzers `library/cue_detr.py` (auto-cue) and the CLAP embed path. Wire it into the **ingest/embed-folder** flow (`library embed-folder` already decodes audio per file via PyAV) so a track with no `key` tag gets `key = detect_key(...)` → `camelot = to_camelot(key)` filled in exactly where `_practice_track`/`rekordbox._track_to_beatgrid` read it. The whole downstream (Camelot clash, transition scorer, coach `key:` citations, harmonic practice) then works on tag-less libraries with **zero changes** — they already consume `to_camelot()` output.

**Secondary fit — the beatmatch/owned-deck moat**: this is the same clean-room-from-Mixxx-DSP pattern already proven in `src/vibemix/learn/beatmatch_judge.py` (math "ported verbatim from Mixxx sync, re-derived clean-room C1 numpy-only, no GPL" — `beatmatch_judge.py:9-14`). A `detect_key` producer is the harmonic analogue: it would let an owned-deck practice loop grade *harmonic mixing* (key-clash on the overlap via `harmonics.is_clash`) the same way `grade_beatmatch` grades tempo/phase — feeding the same `BEATMATCH_GRADED`-style cited-event → `skill_recognizer` Mastered-credit machinery (`learn/skill_recognizer.py`). Note `grade_beatmatch` is currently import-orphaned in production (no live emitter — `tests/repo/test_live_reality_pins.py` pins this), so a key producer + practice loop closes both the harmonic-grading AND the beatmatch-producer gaps together.

**One reuse note**: vibemix's Camelot table (`harmonics.py:29-66`, sourced from mixedinkey/dj.studio) and Mixxx's `keyToOpenKeyNumber` ring (`keyutils.cpp:314-356`) are the same circle-of-fifths relabeling — your detector should emit the **classical spelling** (`s_traditionalKeyNames`/`s_IDv3KeyNames` order, `keyutils.cpp:45-105`) and let the existing `to_camelot()` do the Camelot conversion, so there's one canonical Camelot mapping in the codebase, not two.
