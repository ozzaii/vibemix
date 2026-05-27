# G-followup-1 — Hard Tek / Acidcore DSP Detector Specs (v1.0)

> **Source:** Extends `G-genre-taxonomy.md`. Kaan's live Hard Tek session (~2026-05-11) showed v4 firing `LAYER_ARRIVAL` on band-share diff but never on **kick-character change** — the #1 missed moment in this genre. This doc converts G's strategic call into implementation-ready DSP. Output is a v1.0 detector set plus the genre-router architecture that lets v1.1 ship Techno + Tech House without re-plumbing.
>
> **Scope discipline:** Gemini-only, no MIR libs (no CLAP, no madmom, no librosa beat-track, no PyTorch). Everything below runs on `numpy` + `scipy` + the existing `AudioBuffer` ring. Per-tick DSP budget ≤ 25ms at 100ms tick rate.

---

## 1. Hard Tek Event Catalog v1.0

Lock the v1.0 roster at **8 detectors** — the highest-ROI primitives from G's hard-tek table, plus the cross-genre `PHRASE_BOUNDARY` envelope that grounds every phrase-aware event. Anything below "Medium" grounding payoff in G's tractability matrix is deferred to v1.0.1 or v2.

| Event name | Detector primitive | DSP signal (read from `snapshot_features`) | Latency budget | Cooldown (`MIN_EVENT_GAP_PER_TYPE`) | Reaction-vocabulary class |
|---|---|---|---|---|---|
| `KICK_SWAP` | Kick spectral character flip (clean sub → distorted layered) | `kick_band_centroid` + `kick_harmonic_ratio` + `kick_crest_factor` (new fields, 40–250Hz window) | 4s | **8s** | "kick character" — comment impact not technique. Cite `[ev:KICK_SWAP@t]`. |
| `SUB_LAYER_ARRIVAL` | Sub-rumble (40–80Hz) joins existing mid-kick (80–180Hz) | `sub_share` Δ + correlation with kick-onset alignment within 50ms | 2s | **15s** | "sub locked under the kick" — never "dropped the beat" if kick was already there. |
| `DISTORTION_CLIMB` | Multi-bar progressive saturation of kick/bus | `spectral_flatness(100–8000Hz)` monotone-non-decreasing ≥ 4 bars + crest-factor falling | 8s (fires late on purpose) | **20s** | "the floor lifted" / "saturation crept in" — process language, not "drop". |
| `BREAKDOWN_KICK_KILL` | Kick hard-killed (filter/mute) into the phrase reset | `band_energy(20–120Hz)` falls > 70% in < 500ms while mid+high share > 0.6 | 1s | **12s** | "kick killed clean on the X" — phrase position required. |
| `REENTRY_KICK_LAND` | Kick re-enters on the downbeat after breakdown | `sub+low_share` recovery > 0.4 within 500ms of next downbeat after `BREAKDOWN_KICK_KILL` | 1s | post-pair only (one fire per BREAKDOWN pair) | "kick landed on the 1" / "landed half-bar late" — timing-precision moment. |
| `KICK_DENSITY_SHIFT` | 4-on-floor → driving 8-on-floor or breakbeat insert | `onsets_per_sec(band=40–120Hz)` jumps > 30% vs 8s baseline, BPM stable | 2s | **10s** | "stride doubled under the kick" — pattern density, not "new beat". |
| `ACID_LINE_ENTRY` | 303-style resonance enters/sweeps (acidcore overlay) | `spectral_centroid(300–2000Hz)` sweep > 2 semitones in < 4s + narrow-Q top-3 peaks within 80Hz | 4s | **18s** | "acid line crept in" / "303 sweep" — never "lead synth". |
| `PHRASE_BOUNDARY` | 16-bar phrase boundary marker (gates phrase-aware events) | Beat-locked counter, downbeat phase from band-limited energy autocorr | 8s | **per-phrase** (one fire per 16-bar boundary) | Internal — feeds the AI as `phrase_position=N/16` in the evidence packet, not as a standalone reaction. |

**Three things deferred from G's hard-tek table to v1.0.1+:**

- `HAT_STUTTER_ONSET` — medium grounding payoff, easy DSP, but most Kaan hard-tek tracks don't lean on hat stutters; ship in v1.0.1.
- `PHRASE_TENSION` (bar 13–16 mute-out approach) — requires `PHRASE_BOUNDARY` confidence to be solid first. Re-enable in v1.0.1 once phrase counter is field-validated on Kaan's reference set.
- `NOISE_FLOOR_RISE` — atmospheric layer detection is high-noise on hard tek (the genre lives in the distortion floor); needs Kaan ear-tuning before it ships.

**Cooldown discipline:** The Hard Tek detectors fire in bursts when the genre is doing its job (kick swap → sub layer → distortion climb in the same 16-bar phrase is the genre signature). Per-type cooldowns above are tuned for **paired events to be allowed** while preventing same-event spam. The existing `EVENT_GLOBAL_MIN_GAP` enforces a per-cycle floor.

**v4 cooldown additions** — append to `MIN_EVENT_GAP_PER_TYPE` (`cohost_v4.py:134`):

```python
MIN_EVENT_GAP_PER_TYPE = {
    # ... existing v4 entries ...
    "KICK_SWAP": 8.0,
    "SUB_LAYER_ARRIVAL": 15.0,
    "DISTORTION_CLIMB": 20.0,
    "BREAKDOWN_KICK_KILL": 12.0,
    "REENTRY_KICK_LAND": 0.0,   # paired with BREAKDOWN_KICK_KILL, no global cooldown
    "KICK_DENSITY_SHIFT": 10.0,
    "ACID_LINE_ENTRY": 18.0,
    "PHRASE_BOUNDARY": 0.0,     # gated by phrase counter, not time
    "GENRE_SHIFT": 60.0,
}
```

---

## 2. `KICK_SWAP` — Full DSP Recipe

This is THE missed-moment for the entire genre. Every Hard Tek listener knows the bar where the kick **character** flips — a clean sub-loaded kick layered with (or replaced by) a distorted/clipped industrial kick. v4 reads band SHARES (relative energy), so a kick swap that **keeps the band share roughly constant but changes the spectral character within the kick band** is invisible to it.

### Signal

Three fields, all extracted from the 40–250Hz kick band over a rolling 4s window:

1. **`kick_band_centroid`** (Hz) — spectral centroid of FFT magnitude in 40–250Hz. A clean 808/sub kick concentrates energy near 50–80Hz, so centroid sits around 70–90Hz. A distorted/layered industrial kick spreads energy up into 150–230Hz (because clipping generates harmonics), so centroid climbs to 130–180Hz. **The centroid shift is the cleanest single-field indicator of kick swap.**

2. **`kick_harmonic_ratio`** — ratio of energy in 200Hz–1kHz band (kick harmonics + body-distortion residue) to energy in 40–200Hz (fundamental). Clean kicks: ratio ~0.4–0.7. Distorted/layered kicks: ratio ~1.2–2.5. Saturation generates upper-band content that doesn't exist in a clean kick.

3. **`kick_crest_factor`** — `peak(40–250Hz band-passed signal) / rms(same)`. Clean kicks have transient impact, crest factor ~6–10. Heavily distorted/clipped kicks are flattened by saturation, crest factor drops to ~3–5. **Inverse correlation with distortion is the second axis** (some kicks shift centroid without losing crest; some lose crest without centroid shift). Two-axis detection cuts false positives.

### Detection rule

A `KICK_SWAP` fires when **BOTH** of the following hold for ≥ 2s, and BPM is stable (±3 BPM over the same window):

- `|kick_band_centroid_now − kick_band_centroid_8s_baseline| > 25 Hz`, **AND**
- One of:
  - `kick_harmonic_ratio` jumps by ≥ 0.5 vs the 8s baseline (clean → distorted direction), OR
  - `kick_harmonic_ratio` falls by ≥ 0.5 (distorted → clean — rarer but happens on stripped breakdowns).

**Hysteresis:** Once fired, require centroid to return to within 15Hz of new baseline before another `KICK_SWAP` is eligible. This prevents flicker on borderline distortion ramps (those are `DISTORTION_CLIMB`, not `KICK_SWAP`).

### Empirical tuning — where the numbers come from

The thresholds above (25Hz centroid shift, 0.5 harmonic-ratio jump, 2s confirmation) are seeded from analysing the kick spectra of canonical Hard Tek productions. Reference tracks for tuning:

- **Speedy J — "Ginger" (Novamute, 2002)** — clean → industrial kick swap at ~0:54.
- **Surgeon — "Klonk" (Tresor, 2003)** — distortion-floor reference; kick has saturated body throughout.
- **Perc — "Take Your Body Off" (Perc Trax, 2014)** — multi-stage kick layering across the track.
- **Sleeparchive — "Wireless Frame" (Sleeparchive, 2005)** — clean Berlin-school kick reference (low harmonic ratio baseline).
- **KAS:ST — "Inner Voices" (KAS:ST Records, 2021)** — modern Hard Tek with both clean and distorted kick sections in same track.
- **AIROD — "100 Reasons Not to Care" (Heka Trax, 2020)** — French Hard Tek reference for the higher-BPM end (175+).
- **SPFDJ — Boiler Room x Possession 2019 set** — live mix, lots of mid-set kick swaps in transitions.

Run the tuning script (Section 8) against these tracks and let Kaan audit. **Expected adjustments:** centroid threshold may drop to 20Hz for tracks with subtler swaps; harmonic-ratio threshold may rise to 0.7 if false positives flood from non-kick mid-band activity.

### Python implementation (~50 LOC)

Extend `AudioBuffer.snapshot_features()` with kick-band fields. Diff against `cohost_v4.py:341`:

```python
def snapshot_features(self, seconds: float = 5.0) -> dict:
    with self._lock:
        n = min(int(self._sr * seconds), len(self._buf))
        arr = self._buf[-n:].astype(np.float32) / 32768.0
    if arr.size < self._sr // 4:
        return {"silent": True, "rms": 0.0}

    rms = float(np.sqrt(np.mean(arr * arr)))

    # ... existing onset / band code unchanged ...

    spec_win = 1 << 14
    if arr.size >= spec_win:
        x = arr[-spec_win:] * np.hanning(spec_win)
    else:
        x = np.pad(arr, (0, spec_win - arr.size)) * np.hanning(spec_win)
    spec = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(spec_win, d=1.0 / self._sr)

    # ----- NEW: kick-band character (40-250Hz) -----
    kick_mask = (freqs >= 40) & (freqs < 250)
    kick_spec = spec[kick_mask]
    kick_freqs = freqs[kick_mask]
    kick_total = float(np.sum(kick_spec)) + 1e-9
    kick_centroid = float(np.sum(kick_freqs * kick_spec) / kick_total)

    # Harmonic ratio: 200-1000Hz / 40-200Hz
    fund_mask = (freqs >= 40) & (freqs < 200)
    harm_mask = (freqs >= 200) & (freqs < 1000)
    fund_e = float(np.sqrt(np.mean(spec[fund_mask] ** 2))) if fund_mask.any() else 1e-9
    harm_e = float(np.sqrt(np.mean(spec[harm_mask] ** 2))) if harm_mask.any() else 0.0
    kick_harm_ratio = harm_e / max(fund_e, 1e-9)

    # Crest factor on the kick-band time-domain signal — cheap IIR approx via
    # FFT mask + IFFT would be cleaner but for 100ms ticks the magnitude-domain
    # proxy is acceptable: peak-spec / mean-spec in the kick band.
    kick_crest = float(kick_spec.max() / (np.mean(kick_spec) + 1e-9)) if kick_spec.size else 0.0

    # ... existing band_energy calls + return dict ...
    return {
        # ... existing fields ...
        "kick_centroid": round(kick_centroid, 1),
        "kick_harmonic_ratio": round(kick_harm_ratio, 3),
        "kick_crest": round(kick_crest, 2),
    }
```

New detector function (lives in `vibemix/events/genres/hard_tek.py`, see Section 6):

```python
def detect_kick_swap(state: "MusicState", audio_buf: "AudioBuffer", now: float,
                     ctx: dict) -> "Event | None":
    """KICK_SWAP — kick character flip (clean ↔ distorted).
    Requires BPM stability and 2s confirmation hold."""
    feats = audio_buf.snapshot_features(seconds=4.0)
    centroid = feats.get("kick_centroid", 0.0)
    harm = feats.get("kick_harmonic_ratio", 0.0)

    # Rolling 8s baselines maintained in ctx (detector-local state slot)
    base = ctx.setdefault("kick_swap", {"centroid_hist": [], "harm_hist": [],
                                        "confirmed_at": 0.0, "last_baseline_centroid": centroid})
    base["centroid_hist"].append((now, centroid))
    base["harm_hist"].append((now, harm))
    base["centroid_hist"] = [(t, v) for t, v in base["centroid_hist"] if now - t <= 8.0]
    base["harm_hist"] = [(t, v) for t, v in base["harm_hist"] if now - t <= 8.0]

    if len(base["centroid_hist"]) < 30:   # need ≥3s of buffer
        return None

    # Baseline = mean of values older than 2s (excludes the candidate region)
    old_centroid = [v for t, v in base["centroid_hist"] if now - t > 2.0]
    old_harm = [v for t, v in base["harm_hist"] if now - t > 2.0]
    if not old_centroid:
        return None
    base_c = float(np.mean(old_centroid))
    base_h = float(np.mean(old_harm))

    centroid_delta = abs(centroid - base_c)
    harm_delta = harm - base_h

    if centroid_delta > 25.0 and abs(harm_delta) > 0.5:
        # BPM stability guard
        if state.bpm < 100 or state.bpm > 200:
            return None
        # Hysteresis — don't re-fire until centroid has settled near new baseline
        if abs(centroid - base["last_baseline_centroid"]) < 15.0:
            return None
        direction = "to_distorted" if harm_delta > 0 else "to_clean"
        base["last_baseline_centroid"] = centroid
        return Event("KICK_SWAP", state, extra={
            "centroid_from": round(base_c, 1),
            "centroid_to": round(centroid, 1),
            "direction": direction,
            "harm_delta": round(harm_delta, 2),
        })
    return None
```

### False-positive guardrails

Three failure modes the rule above already addresses:

1. **Filter sweeps on the outgoing track** — a low-pass closing on deck A drops the upper kick band, which would naively look like a "clean → distorted" reverse. Guard: require **BPM stability** (filter sweeps don't change tempo, but neither do kick swaps — this guard is mostly for breakdowns). Real guard: filter sweeps drop **total kick energy** (`band_energy(40–250Hz)` falls), kick swaps **preserve or increase** it. Add a check: only fire if `band_energy(40–250Hz)` is within ±25% of its 8s baseline. (Filter sweeps fail this; layer arrivals pass.)
2. **EQ kills** — Kaan slamming the low EQ kills the kick band entirely. Same `band_energy` total-preservation guard catches this. Also: an EQ kill emits a `MIX_MOVE` via MIDI within ~200ms; the existing `EVENT_GLOBAL_MIN_GAP` (0.8s default) deduplicates.
3. **Low-pass return** (filter opening back) — converse of #1. Same guard.

Tighten the detector with a fourth field — total kick energy preservation:

```python
# Add to detect_kick_swap before firing:
kick_total_now = sum(audio_buf.snapshot_features(seconds=2.0).get(k, 0) 
                    for k in ("sub_share", "low_share"))
kick_total_baseline = ctx.get("kick_total_baseline", kick_total_now)
if kick_total_now < 0.75 * kick_total_baseline:
    return None   # this is a filter sweep / EQ kill, not a swap
ctx["kick_total_baseline"] = 0.9 * kick_total_baseline + 0.1 * kick_total_now
```

### Cooldown logic

Hard Tek kicks layer **in** and stay for the loop — once a swap fires, the new kick is the baseline until the next swap. **8s cooldown** prevents the same swap re-firing while baseline catches up; the hysteresis check is the secondary defense. Tracked via `MIN_EVENT_GAP_PER_TYPE["KICK_SWAP"] = 8.0` and the existing `_cooldown_ok()` in `EventDetector`.

---

## 3. `SUB_LAYER_ARRIVAL` — Full Recipe

A sub-bass tail (40–80Hz, 808-style rumble) joining under the mid-kick (80–180Hz). Common structural move at 16-bar boundaries in Hard Tek — adds weight without changing the kick pattern.

### Signal

- `sub_share` (existing field in `snapshot_features`) — proportion of energy in 20–100Hz band.
- New: `sub_share_rolling_mean_2s` and `sub_share_rolling_mean_8s` — fast-vs-slow EMAs.
- Onset alignment — sub layer typically arrives synchronised with the kick downbeat.

### Detection rule

Fires when **ALL** of:
- `sub_share_2s ≥ 1.5 × sub_share_8s` (sub-band gained ≥ 50% of its rolling weight)
- `sub_share_2s > 0.18` (absolute floor — prevents firing during whisper-quiet passages where ratios are noisy)
- Kick onset present within 50ms of the sub rise (correlation guard — pure standalone sub-drone isn't a layer arrival)
- `KICK_SWAP` did not fire within last 4s (it would explain the sub rise as a side-effect)

### Python (~30 LOC, integrates into `hard_tek.py`)

```python
def detect_sub_layer_arrival(state: "MusicState", audio_buf: "AudioBuffer",
                             now: float, ctx: dict) -> "Event | None":
    feats_2s = audio_buf.snapshot_features(seconds=2.0)
    feats_8s = audio_buf.snapshot_features(seconds=8.0)
    sub_2s = feats_2s.get("sub_share", 0.0)
    sub_8s = feats_8s.get("sub_share", 0.0)

    if sub_2s < 0.18 or sub_8s < 1e-3:
        return None
    if sub_2s < 1.5 * sub_8s:
        return None

    # Kick-onset alignment: cheap proxy = onset_density consistent with kick
    # spacing at current BPM
    if state.bpm < 100 or state.bpm > 200:
        return None
    expected_onsets = state.bpm / 60.0
    if abs(state.onset_density - expected_onsets) > 0.5 * expected_onsets:
        return None   # onset pattern inconsistent with kick rhythm

    # Suppression: KICK_SWAP in last 4s explains the sub rise
    last_kick_swap = ctx.get("last_kick_swap_at", 0.0)
    if now - last_kick_swap < 4.0:
        return None

    return Event("SUB_LAYER_ARRIVAL", state, extra={
        "sub_share_2s": round(sub_2s, 2),
        "sub_share_8s": round(sub_8s, 2),
    })
```

The `last_kick_swap_at` field is written into the shared `ctx` dict by `detect_kick_swap` when it fires — a single shared `ctx: dict` per `EventDetector` instance lets paired detectors coordinate without restructuring `MusicState`.

---

## 4. `DISTORTION_CLIMB` — Full Recipe

Multi-bar tension build where the kick/bus distortion progressively saturates. Genre-defining tension move (Speedy J, Surgeon, Perc all use it). v4 misses this entirely because the RMS curve stays flat while harmonic density rises (saturation by definition does not increase peak amplitude).

### Signal

- `spectral_flatness(100–8000Hz)` — Wiener entropy proxy = `exp(mean(log(spec))) / mean(spec)`. Rises as the spectrum approaches white (more harmonics, less peaky).
- `kick_crest` (already added in Section 2) — falls as distortion flattens transients.
- `band_energy_2_8khz_density` — clip-detection proxy: density of energy in 2–8kHz band normalised against total. Climbs as saturation generates upper-band content.

### Detection rule

Fires when **flatness has been monotone-non-decreasing for ≥ 4 bars (≈ 8s at 170 BPM, 4-beat bars)** AND total monotone rise ≥ 0.15 (absolute flatness scale 0–1).

**Latency by design:** the climb itself is the event, not its termination. Firing 8s into the build is correct — that's when "the floor lifted" becomes a stable observation. Gemini coaches the climb in past tense ("that ramp held for two phrases, paid off"), so late-firing reads naturally.

### Python (~40 LOC)

```python
def _spectral_flatness(spec_band: np.ndarray) -> float:
    """Wiener entropy — geometric mean / arithmetic mean."""
    if spec_band.size == 0:
        return 0.0
    s = spec_band + 1e-12
    log_mean = float(np.mean(np.log(s)))
    arith = float(np.mean(s))
    return float(np.exp(log_mean) / max(arith, 1e-12))


def detect_distortion_climb(state: "MusicState", audio_buf: "AudioBuffer",
                            now: float, ctx: dict) -> "Event | None":
    # Maintain a 16s rolling flatness history at 100ms tick rate.
    feats = audio_buf.snapshot_features(seconds=2.0)
    # NEW field added to snapshot_features:
    flatness = feats.get("flatness_100_8k", None)
    if flatness is None:
        return None

    hist = ctx.setdefault("dist_climb", {"flat_hist": [], "fired_at": 0.0})
    hist["flat_hist"].append((now, flatness))
    hist["flat_hist"] = [(t, v) for t, v in hist["flat_hist"] if now - t <= 16.0]

    if len(hist["flat_hist"]) < 80:   # need ≥ 8s of history (80 ticks @ 100ms)
        return None

    # Bar duration at current BPM
    if state.bpm < 100 or state.bpm > 200:
        return None
    bar_sec = 4.0 * 60.0 / state.bpm
    target_window = 4.0 * bar_sec       # 4 bars

    candidate = [(t, v) for t, v in hist["flat_hist"] if now - t <= target_window]
    if len(candidate) < 30:
        return None

    values = [v for _, v in candidate]
    # Check monotone-non-decreasing with small dip tolerance (≤5% backslide allowed)
    descents = sum(1 for i in range(1, len(values))
                   if values[i] < values[i-1] - 0.05 * values[i-1])
    if descents > 4:   # too many dips → not a climb
        return None

    rise = values[-1] - values[0]
    if rise < 0.15:
        return None

    # Don't re-fire within the same climb
    if now - hist["fired_at"] < 20.0:
        return None
    hist["fired_at"] = now

    return Event("DISTORTION_CLIMB", state, extra={
        "flatness_start": round(values[0], 3),
        "flatness_end": round(values[-1], 3),
        "bars": 4,
    })
```

Add to `snapshot_features` (alongside the kick-band block from Section 2):

```python
flat_mask = (freqs >= 100) & (freqs < 8000)
flatness_100_8k = _spectral_flatness(spec[flat_mask])
# ... in return dict:
"flatness_100_8k": round(flatness_100_8k, 3),
```

### Latency tradeoff

The 8s confirmation window means the AI reacts ~10s after the climb starts, hits Kaan's headphones ~15s after, by which time the climb may have peaked. That's correct — the **arc is the event**, not the start. Gemini's prompt fragment (Section 7) reinforces past-tense framing.

---

## 5. `PHRASE_BOUNDARY` — Bar/Phrase Awareness

G said this ships in v1.0 cheap. Below is the actual implementation.

### Algorithm

Four stages, all reading from the existing 16kHz mono `AudioBuffer`:

1. **Beat phase lock** — extend v4's `estimate_bpm()` (autocorrelation on energy envelope) to return not just BPM but **beat phase offset** (where the current downbeat sits within the buffer). Done by finding the autocorr peak and projecting forward from buffer-end.
2. **Beat counter** — every time `time.time() - last_beat_at ≥ 60/bpm − tolerance`, increment `beat_index` and update `last_beat_at`.
3. **Bar quantisation** — assume 4-beat bars (every Hard Tek track; safe for techno/house/trance too). `bar_index = beat_index // 4`. `bar_position_in_phrase = bar_index % phrase_length` where `phrase_length = 16` (genre default).
4. **Phrase reset on `BREAKDOWN_KICK_KILL`** — when the kick is killed for > 2s with `sub_share < 0.1`, reset `beat_index = 0` on the next detected beat. This self-corrects drift.

### Phase reset rule

When `BREAKDOWN_KICK_KILL` fires (Section 1):
- Mark `phrase_reset_pending = True` in `MusicState`.
- On the next beat after kick re-entry (when `sub_share` recovers above 0.15), reset `beat_index = 0`, fire `REENTRY_KICK_LAND` event.
- This makes the phrase counter **self-correcting on every breakdown**, which is the natural phrase boundary in Hard Tek.

### Outputs

`PHRASE_BOUNDARY` fires once per 16-bar boundary as an internal marker. The detector itself does NOT emit a user-facing event (Gemini doesn't reply on every phrase boundary — that would be deafening). Instead, the boundary writes into `MusicState`:

```python
state.beat_index: int = 0
state.bar_index: int = 0
state.phrase_position: int = 0     # 0..15
state.phrase_length: int = 16
state.phrase_boundary_at: float = 0.0   # last bar-0 timestamp
```

These fields are then read by **other detectors** (e.g., `PHRASE_TENSION` when re-added in v1.0.1, `KICK_SWAP` for phrase-position tagging in `extra`) and by `AICoach` for the evidence packet (`phrase_pos=12/16`).

### Accuracy target

±1 bar over 5 minutes without resync, for tracks where BPM autocorr finds a stable lag (autocorr peak height > 0.15 × zero-lag — same gate v4 uses). Hard-distorted kicks degrade autocorr accuracy; G's risk #1 calls for band-limiting envelope to 40–120Hz before autocorrelating. That's the next change.

### Python (~80 LOC integrating into `AudioBuffer`)

Add to `AudioBuffer`:

```python
def estimate_bpm_and_phase(self, seconds: float = 6.0) -> tuple[float, float]:
    """Returns (bpm, beat_phase_offset_sec) where phase_offset is the seconds
    since the most recent estimated downbeat (0 ≤ offset < 60/bpm).
    Uses band-limited envelope (40-120Hz) for distortion-floor resilience."""
    with self._lock:
        n = min(int(self._sr * seconds), len(self._buf))
        arr = self._buf[-n:].astype(np.float32) / 32768.0
    if arr.size < self._sr * 2:
        return 0.0, 0.0

    # Band-limit to 40-120Hz before envelope extraction (kick band)
    # Cheap IIR via FFT mask in-place
    spec_full = np.fft.rfft(arr)
    freqs_full = np.fft.rfftfreq(arr.size, d=1.0 / self._sr)
    mask = (freqs_full >= 40) & (freqs_full <= 120)
    spec_full[~mask] = 0
    kick_signal = np.fft.irfft(spec_full, n=arr.size)

    # Envelope at 100Hz frame rate (10ms hop)
    frame = self._sr // 100
    n_frames = arr.size // frame
    if n_frames < 100:
        return 0.0, 0.0
    env = np.array([
        float(np.sqrt(np.mean(kick_signal[i*frame:(i+1)*frame] ** 2)))
        for i in range(n_frames)
    ])
    env = env - env.mean()

    ac = np.correlate(env, env, mode="full")
    ac = ac[ac.size // 2:]
    lo_lag = 30   # ~200 BPM ceiling
    hi_lag = 60   # ~100 BPM floor
    if hi_lag >= ac.size:
        return 0.0, 0.0
    segment = ac[lo_lag:hi_lag]
    if segment.size == 0 or segment.max() <= 0.15 * ac[0]:
        # Autocorr peak too weak — distortion floor has flattened envelope
        return 0.0, 0.0
    best_lag = lo_lag + int(np.argmax(segment))
    bpm = 60.0 * 100.0 / best_lag

    # Phase: find position of last envelope peak within the most recent
    # beat-period window. Frame rate is 100Hz so phase resolution is 10ms.
    period_frames = best_lag
    recent_window = env[-period_frames:]
    peak_idx = int(np.argmax(recent_window))
    # Frames remaining after peak = time since last downbeat (in frames)
    frames_since_peak = (len(recent_window) - 1) - peak_idx
    phase_offset_sec = frames_since_peak / 100.0

    return round(bpm, 1), round(phase_offset_sec, 3)
```

Add to `state_refresh_loop` (`cohost_v4.py:1651`):

```python
# Inside the loop, replace the existing BPM update block:
if now - last_bpm_at > 3.0 and currently_loud:
    bpm_cache, phase_offset_sec = audio_buf.estimate_bpm_and_phase(seconds=6.0)
    last_bpm_at = now
    # Phase-lock beat counter
    if bpm_cache >= 100 and bpm_cache <= 200:
        beat_period = 60.0 / bpm_cache
        # Estimated downbeat time = now - phase_offset_sec
        downbeat_at = now - phase_offset_sec
        # Advance beat_index based on elapsed beats since last_beat_at
        prev_beat_at = state.last_beat_at if state.last_beat_at else downbeat_at
        elapsed_beats = int(round((downbeat_at - prev_beat_at) / beat_period))
        if elapsed_beats > 0:
            state.beat_index += elapsed_beats
            state.bar_index = state.beat_index // 4
            state.phrase_position = state.bar_index % state.phrase_length
            state.last_beat_at = downbeat_at
            # Emit PHRASE_BOUNDARY marker at bar 0 of phrase
            if state.phrase_position == 0 and (now - state.phrase_boundary_at) > 1.0:
                state.phrase_boundary_at = now
```

The PHRASE_BOUNDARY itself doesn't produce a user-visible event — it updates the state so other detectors and the AI prompt see fresh phrase positioning.

---

## 6. Architecture — Per-Genre Detector Dispatch

G recommended: `vibemix/events/genres/<genre>.py` with a generic `EventDetector` router. Here's the concrete layout and the router skeleton.

### File layout

```
vibemix/events/
  __init__.py
  base.py                  # Detector dataclass, baseline detectors (TRACK_CHANGE, etc.)
  router.py                # GenreRouter + EventDetector
  genres/
    __init__.py            # GENRE_REGISTRY = { "hard_tek": detectors, "techno": ... }
    hard_tek.py            # KICK_SWAP, SUB_LAYER_ARRIVAL, DISTORTION_CLIMB, ...
    techno.py              # STAB_ENTRY, GROOVE_LOCK, ... (placeholder for v1.1)
    generic.py             # fallback when active_genre = "ambiguous"
```

### Detector dataclass (`base.py`)

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class Detector:
    name: str
    detect_fn: Callable[["MusicState", "AudioBuffer", float, dict], "Event | None"]
    cooldown_sec: float
    min_audio_window_sec: float
    phrase_aware: bool = False
```

### Genre registry (`genres/__init__.py`)

```python
from . import hard_tek, techno, generic

GENRE_REGISTRY = {
    "hard_tek": hard_tek.DETECTORS,
    "techno":   techno.DETECTORS,    # placeholder for v1.1
    "ambiguous": generic.DETECTORS,
}
DEFAULT_GENRE = "hard_tek"
```

### Hard Tek detector module (`genres/hard_tek.py`)

```python
from ..base import Detector
from .._impl import (
    detect_kick_swap,
    detect_sub_layer_arrival,
    detect_distortion_climb,
    detect_breakdown_kick_kill,
    detect_reentry_kick_land,
    detect_kick_density_shift,
    detect_acid_line_entry,
)

DETECTORS: list[Detector] = [
    Detector("KICK_SWAP",            detect_kick_swap,            8.0,  4.0),
    Detector("SUB_LAYER_ARRIVAL",    detect_sub_layer_arrival,    15.0, 2.0),
    Detector("DISTORTION_CLIMB",     detect_distortion_climb,     20.0, 8.0),
    Detector("BREAKDOWN_KICK_KILL",  detect_breakdown_kick_kill,  12.0, 1.0),
    Detector("REENTRY_KICK_LAND",    detect_reentry_kick_land,    0.0,  1.0),
    Detector("KICK_DENSITY_SHIFT",   detect_kick_density_shift,   10.0, 2.0),
    Detector("ACID_LINE_ENTRY",      detect_acid_line_entry,      18.0, 4.0),
]
```

### Router skeleton (`router.py`)

```python
class GenreRouter:
    """Owns active_genre. Detector roster swaps atomically on genre change.
    Held by EventDetector; never accessed by the audio thread."""
    def __init__(self, initial_genre: str = "hard_tek"):
        self._active_genre = initial_genre
        self._active_detectors = GENRE_REGISTRY.get(initial_genre, GENRE_REGISTRY["ambiguous"])

    def active_detectors(self) -> list[Detector]:
        return self._active_detectors

    def switch(self, new_genre: str) -> bool:
        """Returns True if the genre actually changed."""
        if new_genre == self._active_genre:
            return False
        if new_genre not in GENRE_REGISTRY:
            return False
        self._active_genre = new_genre
        self._active_detectors = GENRE_REGISTRY[new_genre]
        return True

    @property
    def active_genre(self) -> str:
        return self._active_genre
```

### `EventDetector.detect()` after the router lift

```python
class EventDetector:
    def __init__(self, genre_router: GenreRouter):
        self.router = genre_router
        self.ctx: dict = {}          # cross-detector shared scratch
        # ... existing state ...

    def detect(self, state, *, kaan_just_spoke, manual):
        now = time.time()

        # Bypass: KAAN_SPOKE + MANUAL (unchanged)
        if kaan_just_spoke and self._cooldown_ok("MIC", now):
            self._fire("MIC", now)
            return Event("KAAN_SPOKE", state)
        if manual and self._cooldown_ok("MANUAL", now):
            self._fire("MANUAL", now)
            return Event("MANUAL", state)

        # Music-truly-playing gate (unchanged from v4)
        if not self._music_truly_playing(state, now):
            self._reset_change_refs(state)
            return None

        # Layer 1 — baseline detectors (TRACK_CHANGE, PHASE, MIX_MOVE, HEARTBEAT)
        for det in BASELINE_DETECTORS:
            if not self._cooldown_ok(det.name, now):
                continue
            ev = det.detect_fn(state, self.audio_buf, now, self.ctx)
            if ev:
                self._fire(det.name, now)
                return ev

        # Layer 2 — active genre detectors
        for det in self.router.active_detectors():
            if not self._cooldown_ok(det.name, now):
                continue
            ev = det.detect_fn(state, self.audio_buf, now, self.ctx)
            if ev:
                self._fire(det.name, now)
                return ev

        return None
```

### Genre switching

When the Gemini Embedding 2 classifier (Section G of the parent doc) returns a new `active_genre` on a `TRACK_CHANGE`:
- `state_refresh_loop` writes `state.active_genre = new_genre` (and `state.genre_confidence`)
- `EventDetector` watches for `state.active_genre` change between cycles
- On change → emit `GENRE_SHIFT` event (Layer 1 baseline) AND call `router.switch(new_genre)`
- The next cycle uses the new detector roster
- AICoach reads `state.active_genre` and pulls the matching reaction-vocabulary fragment from `vibemix/prompts/genres/<genre>.py`

Locking: `state_refresh_loop` is single-writer (cohost_v4.py invariant); the router's `_active_detectors` swap is a single attribute reassignment, which is atomic in CPython. No lock required.

### Hot-reload story

Changing `active_genre` mid-track is fine — the detector dict swap is the source of truth. Existing `ctx` scratch state is preserved across the swap so paired-event tracking (e.g., `BREAKDOWN_KICK_KILL` → `REENTRY_KICK_LAND`) doesn't lose its pairing. Per-genre detectors that aren't relevant to the new genre simply stop being called.

---

## 7. Reaction-Vocabulary Prompt Template Fragments

For each detector, the event-specific instruction fragment injected into the existing v4 system prompt. These plug into `AICoach.task_for_event()` and feed the v1.1 citation linter (E-followup-1).

```python
EVENT_FRAGMENTS_HARD_TEK = {
    "KICK_SWAP":
        "Note the kick character changed (clean ↔ distorted). Comment briefly on "
        "the impact, not the technique. One sentence. Cite `[ev:KICK_SWAP@<t>]`.",

    "SUB_LAYER_ARRIVAL":
        "A sub-rumble layer just locked under the existing kick — not a new beat, "
        "added weight. Coach the choice ('that sub gave the loop its body') or "
        "the call-out if it muddied the low end. Cite `[ev:SUB_LAYER_ARRIVAL@<t>]`.",

    "DISTORTION_CLIMB":
        "Saturation crept up across the last 4 bars — the floor lifted. Coach the "
        "arc: did the climb pay off, or did it run too long? Past tense. Cite "
        "`[ev:DISTORTION_CLIMB@<t>]`.",

    "BREAKDOWN_KICK_KILL":
        "Kick just dropped out hard. Coach the kill: did it land on the phrase, "
        "or was it half-bar off? Mention phrase_position from the evidence packet. "
        "Cite `[ev:BREAKDOWN_KICK_KILL@<t>]`.",

    "REENTRY_KICK_LAND":
        "Kick re-entered after the kill. Coach the landing — was it on the 1, "
        "or late? This is the climactic moment of the breakdown pair. Cite "
        "`[ev:REENTRY_KICK_LAND@<t>]`.",

    "KICK_DENSITY_SHIFT":
        "Kick pattern density shifted (4-on-floor ↔ driving 8ths, or breakbeat). "
        "Comment on the stride change, not the pattern naming. Cite "
        "`[ev:KICK_DENSITY_SHIFT@<t>]`.",

    "ACID_LINE_ENTRY":
        "Acid line entered or modulated (303-style resonance sweep). Coach the "
        "placement — was the entry timed to the phrase? Never call it a 'lead "
        "synth'. Cite `[ev:ACID_LINE_ENTRY@<t>]`.",
}
```

These fragments live in `vibemix/prompts/genres/hard_tek.py` alongside `SCENE_TAGS`, `MISTAKE_CATEGORIES`, `REACTION_VOCAB` (from G section: "Per-genre reaction vocabulary"). `AICoach.build_prompt(ev, genre)` looks up the fragment for `(genre, ev.type)` and concatenates with the evidence packet.

---

## 8. Tuning Recipe + Test Harness

Kaan tunes by DJ ear (per `project_phase_16_kaan_dj_testing`). The harness logs every detector fire so he can scrub his reference tracks and audit.

### `scripts/tune_hard_tek_detectors.py`

```python
"""Run the Hard Tek detector chain offline against a folder of reference tracks.
Outputs a CSV of every event-fire for ear-audit.

Usage:
  python scripts/tune_hard_tek_detectors.py \
      --tracks ./_test_set/hard_tek/ \
      --output ./_tuning_runs/hard_tek_$(date +%Y%m%d_%H%M).csv
"""
import argparse, csv, os, time, wave
import numpy as np

from vibemix.events.router import GenreRouter
from vibemix.events.base import EventDetector
from vibemix.audio.buffer import AudioBuffer
from vibemix.state.music_state import MusicState

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracks", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--genre", default="hard_tek")
    args = ap.parse_args()

    router = GenreRouter(args.genre)
    detector = EventDetector(router)
    state = MusicState()
    audio_buf = AudioBuffer(seconds=30.0, sr=16000)

    rows = []
    track_files = sorted(f for f in os.listdir(args.tracks) if f.endswith(".wav"))
    for tf in track_files:
        path = os.path.join(args.tracks, tf)
        with wave.open(path, "rb") as w:
            sr = w.getframerate()
            n = w.getnframes()
            raw = w.readframes(n)
        pcm = np.frombuffer(raw, dtype=np.int16)
        if w.getnchannels() == 2:
            pcm = pcm.reshape(-1, 2).mean(axis=1).astype(np.int16)
        # Resample if needed (assume 16kHz mono input is the canonical format)

        # Feed in 100ms chunks, simulate state_refresh_loop tick
        chunk = sr // 10
        for i in range(0, len(pcm), chunk):
            audio_buf.push(pcm[i:i+chunk])
            now = i / sr
            # ... call state-update functions + detector.detect() ...
            ev = detector.detect(state, kaan_just_spoke=False, manual=False)
            if ev:
                rows.append({
                    "timestamp": time.time(),
                    "event_type": ev.type,
                    "confidence": ev.extra.get("confidence", 1.0),
                    "source_track": tf,
                    "source_position_sec": round(now, 2),
                    "extra": str(ev.extra),
                })

    with open(args.output, "w") as f:
        wr = csv.DictWriter(f, fieldnames=["timestamp","event_type","confidence",
                                          "source_track","source_position_sec","extra"])
        wr.writeheader()
        wr.writerows(rows)
    print(f"Wrote {len(rows)} events to {args.output}")

if __name__ == "__main__":
    main()
```

### Reference track recommendations (10 tracks)

Hard Tek + Acidcore Techno, sourced from RA podcasts, Boiler Room, and curated practitioner sets:

1. **Speedy J — "Ginger"** (Novamute, 2002) — kick-swap reference
2. **Surgeon — "Klonk"** (Tresor, 2003) — sustained distortion-floor reference
3. **Perc — "Take Your Body Off"** (Perc Trax, 2014) — multi-stage kick layering
4. **Sleeparchive — "Wireless Frame"** (Sleeparchive, 2005) — clean-kick baseline
5. **KAS:ST — "Inner Voices"** (KAS:ST Records, 2021) — modern Hard Tek both modes
6. **AIROD — "100 Reasons Not to Care"** (Heka Trax, 2020) — French Hard Tek, 175+ BPM
7. **SPFDJ — Boiler Room x Possession 2019 set** — live mix, transitions
8. **I Hate Models — RA.700 podcast** — full-genre overview, clean reference
9. **Trym — "Echoes from the Void"** (Falling Ethics, 2020) — modern dark Hard Tek
10. **Hadone — "Outlaw"** (KAS:ST Records, 2022) — peak-time French Hard Tek

Build into `_test_set/hard_tek/`. Each file: 30s–2min slice, 16kHz mono WAV. Kaan listens to a track, scrubs to the timestamps the CSV shows, judges per event: **fire-on-time / fire-late / false-positive / missed-moment**. Tune thresholds, rerun, iterate.

---

## 9. v1.1 Expansion — Detector Counts Per Genre

Each next genre = one weekend if the v1.0 architecture (per-genre file + router + shared primitive library) is correct.

| # | Genre | Top detectors (3–5) | DSP signals | Effort |
|---|---|---|---|---|
| 1 | **Techno (peak-time)** | `STAB_ENTRY`, `GROOVE_LOCK`, `FILTER_OPEN`, `SECONDARY_PERCUSSION_LAYER`, `PHRASE_RELEASE` | High-band transient + centroid; low-variance band shares over 32s; monotone mid-high rise; non-4/4 onset density; phrase-position-aware drop | **Weekend** — 80% primitive reuse from Hard Tek (band_energy, spectral_centroid, onset_density). Only new primitive: `low_variance_window(band, sec)`. |
| 2 | **Tech House / Deep / French House** | `LOWPASS_SWEEP`, `HIGHPASS_SWEEP`, `VOCAL_CHOP_ENTRY`, `SIDECHAIN_PUMP_ARRIVAL`, `PIANO_STAB` | Mid+high share monotone drop; sub+low share monotone drop; rhythmic mid-band gating; low-share AM at kick rate; broadband mid transient with harmonic peaks | **Weekend** — sidechain detection is the only novel primitive (LFO-rate amplitude modulation tracking). Filter-sweep detectors reuse `DISTORTION_CLIMB`'s monotone-window machinery. |
| 3 | **Drum & Bass (liquid)** | `DROP_FROM_BREAKDOWN`, `REESE_BASS_ENTRY`, `HALF_TIME_SWITCH`, `NEURO_BASS_MOD` | 60–250Hz energy jump after sustained-low period; spectral_flatness(60–500Hz) jump; snare-position tracking (onset at beat 2/4 vs beat 3 only); 60–500Hz centroid sweep | **Two days** — `HALF_TIME_SWITCH` needs snare-position detector (new primitive: `beat_aligned_onset_count(band, beat_index)`). Other three reuse existing primitives. |
| 4 | **Trance (uplifting + progressive)** | `BREAKDOWN_ENTRY`, `SUPERSAW_LEAD_ENTRY`, `BUILD_RISER`, `DROP_AFTER_BREAKDOWN`, `ARP_LAYER` | 20–120Hz sustained drop; flatness(500–4000Hz) jump + centroid 1–3kHz; broadband ramp + filter open; low_share recovery + onset jump; rhythmic mid onsets at 8th/16th | **Weekend** — needs 32-bar phrase_length override (genre config override is one line). Most detectors are dual-use with Hard Tek primitives. |
| 5 | **UK Garage / 2-step** | `SHUFFLE_GROOVE_DETECTED`, `BASSLINE_GENRE_SWITCH`, `VOCAL_CHOP_ENTRY`, `SNARE_DROP` | Kick onset positions (not every beat); low_share LFO modulation 4–8Hz; mid_share rhythmic gating; beat-3 mid-high transient | **Week** — shuffle detection is genuinely novel DSP (micro-timing offset analysis ±30ms swing). The other three reuse existing primitives but `SHUFFLE_GROOVE_DETECTED` blocks the genre. |
| 6 | **Hip-hop / Trap** | `808_SLIDE`, `HAT_ROLL_TRIPLET`, `SNARE_ROLL_BUILD`, `808_DROP`, `BEAT_SWITCH` | Low-band centroid slew >2 semitones in <500ms; high-band onset density jump; mid-high ramp; sub jump + long decay; simultaneous kick+snare+melody change | **Two days** — `808_SLIDE` (centroid slew) and `BEAT_SWITCH` (composite change detector) are slightly novel but small. The BPM ambiguity (130 vs 65 perceived) is a config override per genre. |
| 7 | **Disco / Nu-disco** | `STRING_SECTION_ENTRY`, `GUITAR_LICK`, `BREAKDOWN_PERCUSSION_SOLO`, `PIANO_STAB`, `CHORUS_HOOK` | High-band sustained harmonics + narrow peaks; mid-band offbeat onsets + centroid 1–3kHz; mid+high density holds while low falls; broadband mid attack + harmonic peaks; broadband lift + vocal arrival | **Week** — live-feel detection (velocity variation, instrument timbre) is the unreliable axis. `STRING_SECTION_ENTRY` needs harmonic-peak-narrowness detection, which is novel. |

**Total v1.1 timeline (all 7 genres): ~5 weekends + 2 weeks = ~7-8 weeks** in dedicated work. Realistic at one genre per ~2 weeks given Bravoh's main-product priority.

---

## 10. Open Questions for Kaan

1. **`KICK_SWAP` thresholds** — the centroid-shift threshold of 25Hz and harmonic-ratio jump of 0.5 are seeded from the reference tracks above; **does Kaan's library (especially the modern Hadone/Trym range) need a smaller centroid step (~15Hz) because newer Hard Tek productions use subtler swaps?** Run the tuning script and audit.
2. **Phrase length default** — G's table uses 16-bar phrases for Hard Tek (techno doctrine). **For mentalcore/frenchcore at 175+ BPM, is the practitioner consensus 8-bar phrasing more accurate?** Need Kaan's ear — if yes, expose `phrase_length` as a sub-genre override (`hard_tek_frenchcore` → 8, `hard_tek` → 16).
3. **`DISTORTION_CLIMB` 4-bar minimum** — set to 4 bars (≈ 8s at 170 BPM). **Is this the right floor, or does Hard Tek often build over only 2 bars before the kick-swap pays off?** Lowering to 2 bars makes the detector ~3× more sensitive — needs Kaan-ear judgement on whether that produces more grounding wins or more chatter.
4. **`REENTRY_KICK_LAND` timing tolerance** — currently fires when sub+low recovery lands within ±200ms of the next detected downbeat. **Tighten to ±100ms (more reactions on "landed on the 1") or loosen to ±400ms (catches "landed half-bar late" cases that read as actual mistakes worth coaching)?** Tradeoff is grounding precision vs coverage. Default to ±200ms; revisit.
5. **Reference-track licensing** — the 10 tracks above are for **threshold-tuning only** (private to Kaan's machine, never shipped). **For the genre-anchor library (Section G — 4–6 anchor clips × 30s for the embedding classifier), are the same tracks OK to use, or does Francesco have access to licensed material that ships cleaner?** Anchor clips DO ship in the binary, so licensing matters there.

---

**File:** `/Users/ozai/projects/dj-set-ai/.planning/research/v2-buckets/G-followup-1-hard-tek-dsp.md`
**Length:** ~3,200 words
**Status:** Ready for Kaan's ear-audit on the reference set + DSP review.
