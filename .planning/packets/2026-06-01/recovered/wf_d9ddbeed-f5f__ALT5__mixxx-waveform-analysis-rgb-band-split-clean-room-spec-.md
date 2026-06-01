# MIXXX WAVEFORM ANALYSIS + RGB BAND-SPLIT — clean-room spec for vibemix

## (1) THE ALGORITHM (numpy-reimplementable, clean-room)

Mixxx's colored waveform is a **two-stage pipeline**: an *analysis* stage that filters the decoded audio into 3 frequency bands and downsamples each to a per-pixel envelope (this is the part you want), and a *render* stage that maps the 3 band envelopes to an RGB color per screen column (the receipt-UI part). Both are dead simple once you have the band split.

### Stage A — Band-split + downsample (analyzerwaveform.cpp)

**Signal flow.** Decoded stereo float audio `[-1,1]` → 3 parallel IIR band filters (low / band / high) → per-sample `abs()` → max-pool over a fixed *stride* of input samples → quantize to `uint8` → store one `WaveformData{low,mid,high,all}` per stride, per channel (L,R interleaved). A second, coarser "summary" track is produced in the same pass by *averaging* strides.

**The 3 filters (the crux).** Three Bessel filters, 4th-order, applied to the SAME full-rate input independently. Crossover corners are constants (analyzerwaveform.cpp:18-20):
- `kLowMidFreqHz = 600.0`
- `kMidHighFreqHz = 4000.0`
- **low** = `Bessel4 low-pass @ 600 Hz` (4th order)
- **mid** = `Bessel4 band-pass @ [600, 4000] Hz` (implemented as order-8 = LP·HP cascade)
- **high** = `Bessel4 high-pass @ 4000 Hz` (4th order)

So three bands: **< 600 Hz (bass), 600–4000 Hz (mids/vocals), > 4000 Hz (hats/air).** Note: Mixxx commented out the older Butterworth-8 variant and chose **Bessel** specifically — Bessel has maximally-flat *group delay* (linear phase), so the three band envelopes stay time-aligned, which is what makes the colors line up with the actual transient. That matters for "the bass came in" grounding — a phase-smeared filter would misplace the onset.

Filters are pre-settled to silence before processing (`assumeSettled()`) to avoid a ramp artifact at t=0 (Mixxx issue #7776).

**Per-stride reduction (analyzerwaveform.cpp:236-305 + WaveformStride::store, .h:46-75).** The "pixel" is a stride of `m_length` input samples. `m_length = getAudioVisualRatio()` = `audioSampleRate / desiredVisualSampleRate`. The detail waveform targets `desiredVisualSampleRate = 441` visual samples/sec (analyzerwaveform.cpp:62) → at 44100 Hz, `m_length = 100` samples/stride (~2.27 ms/pixel). For each band and each channel, within a stride it keeps the **max of `abs(sample)`** (`storeIfGreater`, not an average — peak envelope, so transients survive; comment line 237 "Take max value, not average"). At stride boundary (`fmod(position, length) < 1`):

```
all_band_value  = max(|raw_sample|)   over the stride   # the unfiltered overall envelope
low_value       = max(|low_filtered|) over the stride
mid_value       = max(|mid_filtered|) over the stride
high_value      = max(|high_filtered|) over the stride
```

**Quantization (.h:49-56).** Each float `[0,1]` → `uint8`:
```
byte = min(255, 255.0 * value + 0.5)     # *255, round, clamp
```
Stored as `WaveformData.filtered.{low,mid,high,all}`, one struct per (channel). Channels are stored interleaved L,R so a "visual frame" = 2 structs.

**The summary/overview track (.h:77-118).** Computed in the SAME pass: every `m_averageLength` samples (a much bigger stride — sized so the whole track fits in `2*1920 = 3840` visual samples, analyzerwaveform.cpp:64) it emits a row whose value is the **mean of the per-stride maxes** accumulated since the last summary row (`m_averageFilteredData[band] / m_averageDivisor`), then quantized identically. So: detail = peak-pooled; overview = mean-of-peaks. This is exactly your debrief "whole-track energy arc" vs a live scrolling detail view.

**Output shape.** A `(N_strides, 2_channels)` array of `{low,mid,high,all}` uint8 — i.e. effectively `(N, 8)` uint8. That's the entire persisted waveform. It's tiny (441 Hz × track-seconds × 2ch × 4bytes).

### Stage B — RGB mapping (waveformrendererrgb.cpp)

Per screen column `x`, Mixxx pools the band envelopes again (display-time max-pool over the `WaveformData` points that fall under that pixel, lines 139-157) into `maxLow, maxMid, maxHigh` (uint8) and `maxAll`. Then (lines 159-211):

```
maxLowF  = maxLow  * lowGain      # lowGain/midGain/highGain default 1.0 (EQ-knob driven in Mixxx)
maxMidF  = maxMid  * midGain
maxHighF = maxHigh * highGain

red   = maxLowF*Cr_low + maxMidF*Cr_mid + maxHighF*Cr_high
green = maxLowF*Cg_low + maxMidF*Cg_mid + maxHighF*Cg_high
blue  = maxLowF*Cb_low + maxMidF*Cb_mid + maxHighF*Cb_high

m = max(red,green,blue)
if m > 0:  color = (red/m, green/m, blue/m)   # HUE only — normalize out brightness
```
Default band colors (waveformsignalcolors.cpp:33-49): **low = red `(1,0,0)`, mid = green `(0,1,0)`, high = blue `(0,1,...)` actually Qt::blue `(0,0,1)`**. So a pixel's hue is a barycentric blend: bass-heavy → red, vocal/mid → green, hats/air → blue, full-spectrum → white-ish. Brightness is normalized OUT of the color and instead drives the bar *height* via a separate channel:

```
allUnscaled = maxLow + maxMid + maxHigh
eqGain = (maxLowF+maxMidF+maxHighF)/allUnscaled    # = 1.0 when no EQ applied
heightFactor = allGain * halfBreadth / 255
barHeight = heightFactor * eqGain * max(maxAllLeft, maxAllRight)
```
(line 96 comment: a full-scale pink-noise reference sits at value 60/band — useful normalization fact.) The `eqGain` term is how an EQ-cut *visibly shrinks* the bar — directly relevant to your R-SLOP problem (see §4).

## (2) MIXXX FILE:LINE METHOD REFERENCES (learn-from, never vendor)

- **Crossover corners + filter choice**: `analyzer/analyzerwaveform.cpp:18-20` (600/4000 Hz), `:175-188` (`createFilters` — Bessel4 Low/Band/High + `assumeSettled`).
- **Per-stride max-pool + quantize loop**: `analyzer/analyzerwaveform.cpp:236-305`; `storeIfGreater` `:361-365`; stride store/quantize `analyzerwaveform.h:46-75`; summary mean-of-peaks `analyzerwaveform.h:77-118`.
- **Visual sample rate / stride length**: `analyzerwaveform.cpp:62` (`mainWaveformSampleRate=441`), `:64` (`summaryWaveformSamples=2*1920`); ratio via `waveform/waveform.h:96` (`getAudioVisualRatio`).
- **Band/channel layout + storage struct**: `waveform/waveform.h:15-32` (`BandIndex{AllBand,Low,Mid,High}`, `ChannelIndex{Left,Right}`, `WaveformFilteredData{low,mid,high,all uint8}`).
- **RGB mapping + hue-normalize + EQ-gain height**: `waveform/renderers/waveformrendererrgb.cpp:102-211` (band→RGB `:169-182`, eqGain/height `:163-209`).
- **Default band colors**: `waveform/renderers/waveformsignalcolors.cpp:33-49` (low=red, mid=green, high=blue).
- **Bessel coefficient derivation**: `engine/filters/enginefilterbessel4.cpp` (fid-spec strings `"LpBe4"/"BpBe4"/"HpBe4"`), `engine/filters/enginefilteriir.h:96-145` (`setCoefs` → `fid_design_coef`). Coefficients come from **fidlib** (`<fidlib.h>`) at runtime — Mixxx does NOT hardcode the biquad taps; it asks fidlib to design a Bessel from the spec string + corner + sample rate. fidlib is public-domain (Jim Peters), so a clean-room Bessel design is unencumbered.

## (3) TORCH-FREE FEASIBILITY — fully feasible, two valid routes

Everything here is numpy + scipy-free-able:

**Route 1 — IIR (faithful to Mixxx, time-aligned).** `scipy.signal.bessel(N=4, [600|4000], btype=..., fs=sr, norm='delay')` → `sosfilt` to get low/band/high. But vibemix is **scipy-free by default**, so either (a) add a narrow dependency, or (b) hardcode the SOS coefficients per supported sample rate (16k/44.1k/48k — you only need a handful since the per-lane buffer is fixed at `INPUT_SR_TARGET=16000`) and run a ~12-line Direct-Form-II biquad cascade in pure numpy. A 4th-order = 2 biquads; band-pass = 4 biquads. The biquad recurrence is trivial (`y[n]=b0 x[n]+b1 x[n-1]+b2 x[n-2]-a1 y[n-1]-a2 y[n-2]`), vectorizable per-section with `scipy.signal.lfilter`-equivalent or a short Python loop over sections (not samples). Pre-settle = run the filter on a few hundred zeros first.

**Route 2 — rFFT band-sum (what vibemix ALREADY does).** vibemix's `band_features.py::band_energy_ratios` already computes band *power* via a Hanning-windowed rFFT and summing `|X|²` over frequency masks — torch-free, librosa-free, reusing `_windowed_spectrum`. This is the *spectral* equivalent of the IIR split and is **cheaper and simpler** than IIR for an offline energy-timeline. The only thing it lacks vs Mixxx is (a) the peak-envelope (it's RMS/energy, not max), and (b) per-pixel time resolution (it's whole-window). For a debrief energy-arc and an onset-of-bass receipt, route 2 over **sliding windows** (e.g. STFT-style hop) gives you a `(T, {sub,low,mid,high})` timeline directly — no new dep. **Recommendation: extend Route 2; do not add scipy.** Mixxx's 600/4000 corners are the value-add to import, not the filter topology.

**Cost.** Trivial. An offline whole-track band-energy timeline at ~10–20 Hz frame rate over a 6-min track is a few hundred rFFTs — milliseconds. No model, no GPU.

## (4) THE VIBEMIX GAP + NEAREST INTEGRATION POINT (verified)

vibemix ALREADY has the core primitive — Mixxx confirms its design is sound and donates the band edges. Two distinct gaps:

**Gap A — the debrief energy-arc + shareable receipt (a band-energy *timeline*).**
Today `band_energy_ratios` (`src/vibemix/audio/band_features.py:30`) returns a *single instantaneous* `{sub,low,mid,high}` ratio for the live Judge — there is no time-series. The debrief (`src/vibemix/debrief/`) has a "energy arc" notion but no per-band colored timeline. **Build a `band_energy_timeline(samples, sr, hop_s)` next to `band_energy_ratios`** that slides the existing windowed-rFFT across the track and returns `(T, 4)` energies + an `all` peak per frame — this is the numpy reimplementation of Stage A using vibemix's existing DSP. Map to RGB with Mixxx's Stage-B barycentric blend (low=red/sub, mid=green, high=blue) for the shareable receipt. **Two adjustments vs the live function**: (i) keep raw per-band energy (not just the normalized ratio) so the *height* channel exists, and (ii) take a peak/max within each hop window for the `all` envelope to match Mixxx's transient-preserving max-pool — pure rFFT energy alone smooths transients and would mute "the bass dropped".
- Integration point: **`src/vibemix/audio/band_features.py`** (extend, same module, same torch-free primitive) feeding **`src/vibemix/debrief/`** (stripper/main). Reuse the existing band edges (already mirror Mixxx's split conceptually; the master features split lives at `src/vibemix/audio/features.py:71` `band_energy`).

**Gap B — THE BIG ONE: grounding the EQ/fader causal claim (R-SLOP).**
This is the highest-value use of Mixxx's spec. The R-SLOP bug = co-host says "you brought the lows up / killed the bass" when it cannot ground *what the move did to the audio*. `apply_live_claim_guard` (`src/vibemix/state/deck_context.py`) currently gates these EQ/fader claims via *regex on the claim text* + required evidence atoms (lines 106, 133-155, 1745-1750 read band ratios as evidence) — but it has **no measured before/after spectral delta** to confirm the move had an effect. Mixxx's RGB renderer hands you the exact recipe (waveformrendererrgb.cpp:163-209): a band-energy value *and* an `eqGain` that shrinks when a band is cut. **Reimplement that as a grounding check**: when a MIX_MOVE/LAYER_ARRIVAL fires on a known control (the move is known from MIDI — `midi/`/the deck mixer snapshot on the `ai_message` row), compute the master/deck band-energy *delta* across the move using `band_energy_ratios` before vs after (you already capture per-lane PCM rings in `DeckAudioCapture`, `deck_signal.py` already pulls `~1s` lane windows). The claim "killed the lows" is grounded ⇔ the measured `sub+low` band energy actually dropped by a threshold in the window after the move; if the audio shows no band change, strip the causal claim to the ack-bank (Invariant #2). This converts an ungrounded causal claim into a measured one — exactly the brief's "compute the spectral effect of a move from the audio + the known move."
- Integration point: **`src/vibemix/state/deck_context.py::apply_live_claim_guard`** (the R-SLOP gate) consuming a new `band_energy_delta(...)` helper in **`src/vibemix/audio/band_features.py`**, fed by the per-lane rings in **`src/vibemix/audio/deck_capture.py`** / the snapshot in **`src/vibemix/audio/deck_signal.py`**. The move identity comes from the deck mixer snapshot already attached to `ai_message` rows + the MIDI catalog (`midi/profiles/`).

**Net:** vibemix's `band_energy_ratios` is already the right torch-free engine and its band edges roughly match Mixxx (Mixxx uses 600/4000 two-corner; vibemix uses sub/low/mid/high at 100/300/4000/8000). The wins to import from Mixxx are: (1) the **max-pool peak envelope** (transient-preserving, vs vibemix's pure energy-sum), (2) the **timeline/downsample stride model** for the debrief arc + receipt, (3) the **`eqGain` band-shrink + RGB barycentric blend** for the shareable colored-waveform receipt, and (4) the conceptual lever that **a measured before/after band delta is what grounds an EQ causal claim** — the direct fix for R-SLOP. No new heavy dependency required; everything reuses `state/detectors/_dsp._windowed_spectrum`.
