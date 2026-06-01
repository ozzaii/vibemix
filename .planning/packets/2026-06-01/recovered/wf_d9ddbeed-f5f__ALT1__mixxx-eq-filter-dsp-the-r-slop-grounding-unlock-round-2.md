# MIXXX EQ/FILTER DSP — THE R-SLOP GROUNDING UNLOCK (Round 2)

## (1) THE ALGORITHM IN MY OWN WORDS (clean-room numpy spec)

### 1A. The core engine: a transposed-Direct-Form-II-ish biquad, ramped between coefficient sets

Every Mixxx EQ band, isolator stage, and filter is a cascade of 2nd-order IIR sections (biquads). Mixxx does NOT hand-derive the famous RBJ coefficients in its own code — it calls the external **fidlib** library (`fid_design_coef`) with a *spec string* + center frequency + Q + dB gain, and fidlib returns the 5 coefficients. For a clean-room reimplementation you compute those coefficients yourself with the standard Audio-EQ-Cookbook (RBJ) formulas; the spec strings tell you exactly which cookbook filter each band is.

The per-sample recurrence Mixxx actually runs (a direct-form-2-transposed variant, see `enginefilteriir.h:325-365`) for one 2nd-order section is, in normalized form (a0 folded into the b/a):

```
# coef layout from fidlib: coef[0]=gain (b0_normalized), coef[1]=a1, coef[2]=a2,
# and the numerator (b1,b2) is IMPLICIT in the per-PASS code, not stored.
iir = x * coef[0] - coef[1]*buf[0] - coef[2]*buf[1]    # recursive (poles)
y   = iir + FIR_of(buf, PASS)                            # feed-forward (zeros), shape set by PASS
buf[1] = buf[0]; buf[0] = iir
```
The genius detail: the **numerator (zeros) is hardcoded per filter-TYPE** rather than stored as coefficients. Look at the templated `processSample` specializations:
- **LP** (`IIR_LP`, line 326): `fir = tmp + 2*buf0 + iir` → numerator `(1, 2, 1)` → the classic lowpass zero pair at Nyquist.
- **HP** (`IIR_HP`, line 354): `fir = tmp - 2*buf0 + iir` → numerator `(1, -2, 1)` → highpass zeros at DC.
- **BP** (`IIR_BP`, line 340): `fir = -tmp + iir` → bandpass.
- **Peaking/Shelf (size-5 `IIR_BP`, line 549):** here the numerator IS stored — `fir = coef[2]*tmp + coef[4]*buf0 + coef[5]*iir`, i.e. full general biquad `b = (coef[5], coef[4], coef[2])`, `a = (1, coef[1], coef[3])`. This is the one used for all the EQ bands.

**For numpy:** you do not need to replicate the per-PASS micro-optimization. Just compute standard `(b0,b1,b2,a0,a1,a2)` and run `scipy.signal.lfilter(b, a, x)` — or, to stay scipy-free, the trivial loop `y[n] = b0*x[n]+b1*x[n-1]+b2*x[n-2]-a1*y[n-1]-a2*y[n-2]`. But for grounding you don't even run the filter on audio in real-time — see §3, you only need the **magnitude response** `|H(e^jω)|`, evaluated with `numpy.polynomial`/`freqz`-style, to predict the per-band gain delta.

**Ramping (anti-click):** on any coefficient change Mixxx keeps the OLD coefficient set and crossfades old-filter-output → new-filter-output linearly over half a buffer (`enginefilteriir.h:240-290`). Irrelevant to grounding — but it's why Mixxx's measured delta lags the move by ~one buffer; your grounding window must allow a settling delay.

### 1B. The 3-band crossover frequencies (THE split — "kill the lows" math)

This is the most important extraction for vibemix. The default DJ mixing EQ is **BiquadFullKillEQ** (`org.mixxx.effects.biquadfullkilleq`). It is NOT a Linkwitz-Riley crossover split into 3 bands; it is a **parallel bank of bell/shelf filters layered on the dry signal** PLUS a separate Bessel isolator path. Constants (`biquadfullkilleqeffect.cpp:10-19`, corner defaults from `lvmixeqbase.h:16-17`):

```
kStartupLoFreq  = 246   Hz   # low/mid crossover corner (user-adjustable "Lo" shelf split)
kStartupHiFreq  = 2484  Hz   # mid/high crossover corner ("Hi" shelf split)
kStartupMidFreq = 1100  Hz   # nominal mid bell center
kMinimumFrequency = 10  Hz
kMaximumFrequency = sampleRate/2  (22050 @ 44.1k)
```

Each band's **bell/shelf center** is the *log-geometric midpoint* of its sub-range (`getCenterFrequency`, line 21-27):
```python
def center(low, high):                 # geometric mean in log space
    return 10 ** ((log10(high) + log10(low)) / 2)   # == sqrt(low*high)
# low  band center = center(10,   246)   ≈ 49.6 Hz
# mid  band center = center(246,  2484)  ≈ 781 Hz
# high band center = center(2484, 22050) ≈ 7400 Hz
```

The two **kill/cut filters that actually remove a band** are:
- **lowKill = LowShelving biquad** centered at `lowCenter*2` (≈99 Hz), `Q=0.4` (`kQLowKillShelve`).
- **highKill = HighShelving biquad** centered at `highCenter/2` (≈3700 Hz), `Q=0.4`.
- **midKill = Peaking biquad** centered at `midCenter` (≈781 Hz), `Q=0.9` (`kQKill`).

Boost filters are Peaking bells at the band center, `Q=0.3` (`kQBoost`, very wide/gentle).

### 1C. What "kill the lows" does to the spectrum, MATHEMATICALLY

When you turn the LOW knob to full-kill (the kill button, or knob below the bessel-start threshold), TWO things stack:

**(i) The biquad low-shelf cut.** Gain in dB is set by `knobValueToBiquadGainDb` (line 29-39):
```python
kKillGain      = -23 dB         # full biquad kill depth (BiquadFullKill)
kBesselStartRatio = 0.25        # knob position where the bessel isolator takes over
def knob_to_biquad_db(value, kill):       # value in [0,1], 0.5=neutral... actually 1.0=unity
    if kill: return -23.0
    if value > 0.25:  return 20*log10(value)        # ratio2db: gentle boost/cut region
    # below 0.25 it ramps the biquad from ratio2db(0.25)≈-12dB down toward -23dB
    startDB = 20*log10(0.25)                          # ≈ -12.04 dB
    value = 1 - (value/0.25)
    return (-23 - startDB)*value + startDB
```
So a low **shelf** is applied: below ≈99 Hz (the shelf corner), magnitude is pulled down by up to −23 dB with a Q=0.4 (broad, ~0.4-octave transition) shelf shape. The shelf transfer function (RBJ low-shelf) gives `|H|→10^(gain/20)` well below corner, `|H|→1` well above corner.

**(ii) The Bessel-4 isolator subtraction.** Separately, `knobValueToBesselRatio` drops the low band's bessel-mix gain from 1.0 toward **0.0** as the knob goes below 0.25 (line 41-46). The isolator (`lvmixeqbase.h:71-187`) reconstructs the signal as three delay-compensated bands and remixes them:
```python
fLow  = dLow  - dMid     # band gains derived by SUBTRACTING adjacent low-pass outputs
fMid  = dMid  - dHigh
fHigh = dHigh
out = lowpass_at_246(x)*fLow + delay(lowpass_at_2484(x))*fMid + delay(x)*fHigh
```
This is a **Bessel low-pass band-split with constant group delay** (Bessel chosen precisely because its passband group delay is flat, so the bands can be delay-aligned and summed without phase tearing — `enginefilterbessel4.cpp:23-65` even hardcodes a delay-ratio table to integer-quantize the group delay). With `fLow=0`, the sub-246-Hz energy is *completely removed* — a true full kill, not just −23 dB.

**Net spectrum of "kill the lows":** energy below ~100–250 Hz collapses to (−23 dB shelf) × (isolator removal) → effectively silence in the bass band; everything above the 246 Hz low/mid corner is untouched. **That is the ground-truth signature you measure: the sub+low band ratio in `band_features.py` should crater while mid+high ratios rise to absorb the normalization.**

### 1D. The simpler 3-band EQ (ThreeBandBiquadEQ) and the Filter knob

- **ThreeBandBiquadEQ** (`threebandbiquadeqeffect.cpp`): tuned to mimic an Allen&Heath **Xone:23**. Different constants worth noting: `kStartupLoFreq=50`, `kStartupHiFreq=12000`, `kBoostGain=12 dB`, `kKillGain=-26 dB`. Knob→dB is *linear in knob units* here (line 32-44): `db = (value-1)*12` for boost, `db = (value-1)*26` for cut. No bessel isolator — kills are pure −26 dB bells/shelves (low=peaking Q0.9, high=high-shelf Q0.4).
- **FilterEffect** (the single LP/HP "Filter" knob on every deck): a serial `EngineFilterBiquad1Low → EngineFilterBiquad1High` pair, corner range `13 Hz … 22050 Hz`, default Q `0.707` (Butterworth), with empirical Q-clamping near overlap (`filtereffect.cpp:118-130`). Turning the knob right past center sweeps an LPF cutoff down (kills highs progressively); left sweeps an HPF cutoff up (kills lows). This is the "filter sweep" move — its signature is a *moving* corner, measurable as a monotonic band-ratio shift over consecutive frames.

### 1E. Q→bandwidth conversion (so you can predict transition width)

Mixxx passes Q directly to fidlib's `PkBq`/`LsBq`/`HsBq` which use the cookbook `alpha = sin(w0)/(2Q)`. For numpy, the RBJ cookbook (clean-room, public math) for a **low shelf** with `A=10^(gain_db/40)`, `w0=2π·fc/fs`, `alpha=sin(w0)/2·sqrt((A+1/A)(1/Q-1)+2)`:
```
b0 =    A*((A+1) - (A-1)*cos(w0) + 2*sqrt(A)*alpha)
b1 =  2*A*((A-1) - (A+1)*cos(w0))
b2 =    A*((A+1) - (A-1)*cos(w0) - 2*sqrt(A)*alpha)
a0 =       (A+1) + (A-1)*cos(w0) + 2*sqrt(A)*alpha
a1 =   -2*((A-1) + (A+1)*cos(w0))
a2 =       (A+1) + (A-1)*cos(w0) - 2*sqrt(A)*alpha
```
(Peaking and high-shelf are the sibling cookbook forms.) You then get the magnitude at any frequency via `H(e^jω) = (b0+b1·z⁻¹+b2·z⁻²)/(a0+a1·z⁻¹+a2·z⁻²)`, `z=e^jω`. **Integrating `|H|²` over each of the four `band_features._BANDS` windows gives the predicted per-band gain — exactly comparable to measured band ratios.**

---

## (2) MIXXX FILE:LINE METHOD REFERENCES (GPL — never vendored)

- `engine/filters/enginefilteriir.h:96-145` — `setCoefs()`: how a spec string + freq + Q + gain becomes the 5 coefficients (via fidlib `fid_design_coef`).
- `engine/filters/enginefilteriir.h:325-365` — biquad `processSample` per-PASS specializations; the implicit numerator `(1,±2,1)` for LP/HP, `-tmp` for BP.
- `engine/filters/enginefilteriir.h:549-560` — size-5 `IIR_BP` = the GENERAL biquad used for all peaking/shelf EQ bands (numerator stored in coef[2,4,5]).
- `engine/filters/enginefilteriir.h:240-290` — old↔new coefficient crossfade ramp (the ~half-buffer settling lag).
- `engine/filters/enginefilterbiquad1.cpp:12-89` — the fidlib spec strings: `"LsBq/Q/dB"` (low shelf), `"HsBq/Q/dB"` (high shelf), `"PkBq/Q/dB"` (peaking), `"LpBq/Q"`/`"HpBq/Q"`/`"BpBq/Q"`. **These strings name the exact RBJ cookbook filter to reimplement.**
- `effects/backends/builtin/biquadfullkilleqeffect.cpp:10-46` — ALL the constants: corners (246/2484/1100), Q values (boost 0.3, kill 0.9, shelf 0.4), `kKillGain=-23`, `kBesselStartRatio=0.25`, `getCenterFrequency` (geometric mean), `knobValueToBiquadGainDb`, `knobValueToBesselRatio`.
- `effects/backends/builtin/biquadfullkilleqeffect.cpp:124-146` — `setFilters`: which filter sits where (lowKill@lowCenter*2, highKill@highCenter/2, midKill@midCenter).
- `effects/backends/builtin/lvmixeqbase.h:16-17` — `kStartupLoFreq=246`, `kStartupHiFreq=2484`.
- `effects/backends/builtin/lvmixeqbase.h:71-187` — the Bessel isolator band-split: `fLow=dLow-dMid`, `fMid=dMid-dHigh`, `fHigh=dHigh`, delay-compensated 3-band remix = the TRUE full-kill path.
- `engine/filters/enginefilterbessel4.cpp:23-65` — Bessel-4 (`"LpBe4"`) corner + the integer-group-delay quantization table (`kDelayFactor1=0.336440447`, `kDelayFactor2=1.1044845`, `delayRatioTable[]`). Bessel chosen for FLAT group delay so bands sum cleanly.
- `effects/backends/builtin/threebandbiquadeqeffect.cpp:12-44` — Xone:23-tuned variant (50/1100/12000 Hz, +12/−26 dB, linear knob→dB, no isolator).
- `effects/backends/builtin/filtereffect.cpp:9-64,118-132` — the deck LP/HP Filter knob: corners 13…22050 Hz, Butterworth Q=0.707, serial Low→High biquads, Q-clamp-on-overlap.

---

## (3) TORCH-FREE FEASIBILITY — TRIVIAL, ALREADY 95% THERE

Everything needed is pure numpy + the cookbook formulas. Specifically:
- **Coefficient derivation:** closed-form RBJ math, ~15 lines of numpy per filter type. No fidlib, no scipy required (fidlib is GPL and unnecessary — the math is public-domain cookbook).
- **Magnitude response:** `H = polyval(b, e^{-jω}) / polyval(a, e^{-jω})` with `ω = 2π·f/fs` over a freq grid — pure `np.exp` + complex division. (Or `scipy.signal.freqz` if scipy is ever allowed, but it isn't needed.)
- **You don't have to filter audio.** For grounding you only need the *predicted per-band gain* of the claimed move, which is `∫|H|²` over each band window. That's a dot product against a precomputed magnitude grid — microseconds, no real-time DSP.
- **The measurement side already exists and is torch-free:** `audio/band_features.py::band_energy_ratios` already does the Hanning-windowed rfft (`state.detectors._dsp._windowed_spectrum`) → `{sub,low,mid,high}` ratios, with an honest-null silence floor. Its band edges (`sub 20-100, low 100-300, mid 300-4000, high 4000-8000`) line up with Mixxx's corners closely enough to map a "low kill" prediction onto `sub+low`.

No new third-party dep. No PyInstaller spec change. Fits the existing `from __future__ import annotations` + numpy-only house style.

---

## (4) THE VIBEMIX GAP + NEAREST INTEGRATION POINT (verified via codegraph + grep)

### The gap (this IS R-SLOP, precisely)
The existing low-kill guard `_has_unsupported_mixer_low_kill_claim` (`state/deck_context.py:2412-2424`) validates a "you killed the lows" claim against the **controller tier** — a MIDI-derived label (`_control_now_tier(raw, "low")` ∈ {killed, deep-cut, …}). That only works when:
1. a controller is connected (`controller_connected` gate, line 2413), AND
2. the MIDI map reports an EQ-low CC tier.

It has **zero connection to what the audio actually did.** So:
- **False-accept:** controller says "low knob at kill tier" but the track had no bass in that section (breakdown) → guard passes "you killed the lows" → SLOP (claimed effect on energy that wasn't there).
- **False-reject / can't-ground:** no controller, or master-only rig (the common case) → guard returns False (no tier evidence) → the co-host either stays mute on real EQ moves or the claim slips through ungrounded. The whole `live_signal.py` Judge even gates on `routing_enabled` being False on master-only rigs.

The deeper issue the task names: the guard checks the *move existed*, never *what the move did to the spectrum*. Mixxx's biquad math is the missing half — it lets you COMPUTE the expected spectral delta of the known move and CONFIRM it against the measured band delta.

### Nearest integration point — a new pure module + one call site
**New module:** `src/vibemix/intel/eq_move_model.py` (intel is the right home — "pure musical-intelligence primitives, import-light, no audio capture, no model clients"). Contents, clean-room from the Mixxx spec above:
```python
# rbj cookbook coeffs for low_shelf/high_shelf/peaking/lp/hp  (clean-room, public math)
# Mixxx-matched defaults: LO_MID_CORNER=246, MID_HI_CORNER=2484,
#   LOW_KILL_FC=99 (lowCenter*2), HIGH_KILL_FC=3700, KILL_GAIN_DB=-23,
#   Q_KILL=0.9, Q_SHELF=0.4, Q_BOOST=0.3
def predicted_band_gains(move: str, fs: int) -> dict[str,float]:
    """e.g. move='low_kill' -> {'sub':-23,'low':-21,'mid':-0.5,'high':0.0} (dB), from |H|^2 over bands."""
```
**Grounding seam:** `state/deck_context.py::apply_live_claim_guard` already takes `audio_delta_items` and computes `render_audio_delta_items` (line 1729-1756) which pulls `state.bands {sub,low,mid,high}` and the prior-frame delta via `render_delta`. The new check sits right next to `_has_unsupported_mixer_low_kill_claim`:

> **Upgrade the verdict from "controller tier says so" to "controller move ∧ measured spectral delta matches `predicted_band_gains`".** Concretely: if a "kill the lows" claim is present and a low-cut move is in `moves`, compute `predicted_band_gains('low_kill')`, then GROUND it only if the measured `sub+low` band-ratio delta (already available via `render_audio_delta_items` / `band_features.band_energy_ratios`) dropped in the predicted direction beyond `DELTA_FLOOR`. If the bands didn't move (breakdown / no bass present), REFUTE → fall back to `LIVE_MOVE_EFFECT_HELD_*` instead of asserting the effect.

This makes the guard work **on master-only rigs (no controller)** too: a move can be inferred purely from a measured monotonic band-ratio shift matching a known filter signature (the Filter-knob sweep case in §1D), turning Invariant #3 ("trust the audio") into a quantitative test rather than a label lookup.

**Verified existing primitives to wire into (all torch-free, all present):**
- `src/vibemix/audio/band_features.py:30` `band_energy_ratios()` — the measured per-band ratios (the ground truth).
- `src/vibemix/state/deck_context.py:1729` `render_audio_delta_items()` + `:17` `render_delta`/`DELTA_FLOOR` from `state/deltas.py` — the existing frame-to-frame band delta machinery.
- `src/vibemix/state/deck_context.py:2412` `_has_unsupported_mixer_low_kill_claim` / `:2427` `_mixer_low_summary` — the exact functions to extend (or sit beside).
- `src/vibemix/state/event_detector.py:33-37,356-378` — MIX_MOVE already fires on `'killed' / '_low: / _mid: / _hi: / _filter: / xfader'` move strings; those are the `moves` tuples handed to the guard, so the move→prediction mapping has a stable vocabulary to key off.
- `src/vibemix/state/detectors/breakdown_kick_kill.py` and `distortion_climb.py`/`kick_swap.py` already consume the same `_dsp`/`_phrase_dsp` rfft band primitives — confirming the band-energy approach is the established in-repo pattern; the EQ-move model just adds the *predictive* counterpart to those *detective* ones.

**One caveat to encode (from Mixxx):** the coefficient-ramp crossfade (`enginefilteriir.h:240-290`) and the isolator group delay (`bessel4` table) mean the measured spectral delta lags a move by ~1 audio buffer (and longer for very-low corners). The guard should compare the band delta over a short post-move window (the existing `deck_audio_window_context` 1100-char window machinery, `deck_context.py:571`), not the single frame at the instant of the move — otherwise it will REFUTE a true kill that simply hasn't settled yet.
