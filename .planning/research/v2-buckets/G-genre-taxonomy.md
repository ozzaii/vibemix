# Bucket G — Genre-Aware Event Taxonomy Research

> **Source feedback:** Kaan, live hard tech session (~2026-05-11): _"feels surface-level — same generic reactions, doesn't catch the actual moments that matter in this genre"._
>
> **Diagnosis:** v4's `EventDetector` (`TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT / KAAN_SPOKE / MANUAL`) is **genre-blind**. The same RMS-curve `classify_phase()`, the same band-share `LAYER_ARRIVAL`, the same "significant MIDI move" filter fires for hard tek, French house, and liquid DnB. A hard-tek-fluent friend would react to **kick-swap, sub-layer drop, distortion-climb, 16-bar phrase tension** — none of which are detected. So Gemini gets the same generic packet for every genre and produces the same generic prose.
>
> **Lever:** Per-genre detector primitives plug into v4's existing event pipeline. The `EventDetector` becomes a router; the actual detectors are pluggable per active genre profile. This is the single biggest grounding lever between v1.0 and v2 — it's the difference between "AI cohost" and "this person actually knows my genre".

---

## TL;DR

1. **v1.0 deep-genre pick = Hard Tek / Acidcore Techno (140–180 BPM, distorted kicks).** Kaan's personal practice is the reference set, and the DSP recipes (kick density, distortion-floor, sub-layer onset, 16-bar phrase) are tractable from the audio Gemini already gets. v1.1 expansion order = **Techno (peak-time) → Tech House → Drum & Bass (liquid) → Trance → UKG → Hip-hop/Trap → Disco/Nu-disco**, in that order. Rationale below.
2. **The single biggest detector win is `KICK_SWAP` for hard tek** — every hard-tek listener knows the exact moment the kick character changes (sub-loaded clean → distorted/clipped layered), and v4 fires `LAYER_ARRIVAL` on band-share but **never on kick-character change** because the detector reads bands, not kick spectrum. Closing this single hallucination class flips one entire genre from "AI slop" to "this thing has ears".
3. **Genre auto-detection = Gemini Embedding 2 nearest-neighbor over a hand-curated genre-anchor library** (8 genres × 4–6 anchor clips × ~30s = ~200 anchors total, embed once, cache locally as JSON). At session start (and on `TRACK_CHANGE`) embed a 15–30s rolling audio slice, cosine to the anchor library, pick top-1 if margin > 0.05, else fall back to "generic". **No CLAP, no MERT, no MIR model bundling.** This is the only Gemini-compatible path and fits the one-click constraint.
4. **Phrase awareness ships in v1.0 too** — but cheap: estimate downbeat by autocorrelation of energy curve at the BPM tactus, then assume 4-bar / 16-bar / 32-bar quantization. Don't ship a CRNN beat tracker (BeatNet/madmom) — they're 50–200MB models, blow the one-click budget, and we don't need bar-accurate timing, only bar-position-aware events ("drop landed bar 17 of phrase" vs "drop landed bar 3"). Tolerance ±1 bar is fine.
5. **Architecturally:** keep the v4 `Event` envelope. Per-genre detectors live in `vibemix/events/genres/<genre>.py` and are activated by `GenreRouter` based on the auto-classifier. `EventDetector.detect()` calls the active set + the cross-genre base set. The `AICoach.task_for_event()` switches per `(genre, event_type)` pair — same event type, different reaction vocabulary. **No restart, no session-reopen** — the LiveKit session stays; only the detector roster and prompt template change.

---

## Per-genre event catalogs

Format per detector:
- **Name** — short detector ID
- **What it catches** — the musical moment
- **DSP recipe** — exact signal + threshold (use v4's `snapshot_features` as the building block where possible)
- **Latency window** — how much audio it needs
- **Cooldown** — per-detector min gap
- **Grounding payoff** — what hallucination class it closes

### Hard Tek / Acidcore Techno (v1.0 deep genre)

BPM **140–185** (Kaan's set hits 170+), kicks are the entire identity. Practitioner consensus across the [EDMProd hard techno guide](https://www.edmprod.com/what-is-hard-techno/), [Toolroom Academy on techno kicks](https://toolroomacademy.com/features/how-to-make-techno-perfecting-your-kick/), [Melodigging hard-industrial primer](https://www.melodigging.com/genre/hard-industrial-techno) and [Gearspace distortion threads](https://gearspace.com/board/electronic-music-instruments-and-electronic-music-production/1307705-how-get-very-heavy-distortion-layers-techno.html): **layered kick (transient click + saturated midbody + sub-rumble tail) is the load-bearing element**. Sub-genre boundary (free-tek, mentalcore, frenchcore) is mostly kick-character + tempo, not melody.

| Primitive | What it catches | DSP recipe | Window | Cooldown | Payoff |
|---|---|---|---|---|---|
| **KICK_DENSITY_SHIFT** | 4-on-floor → driving 8-on-floor, or breakbeat insert | onset count in `band=40–120Hz`, win=2s. Trigger if `onsets_per_sec` jumps >30% vs 8s baseline | 2s | 8s | "AI says he 'dropped the beat' when actually he layered a 16th-note pattern under the same kick" |
| **KICK_SWAP** | clean sub kick → distorted/clipped industrial kick (or reverse) | spectral centroid + crest-factor of `band=40–250Hz` shifted by >0.3σ from last 8s baseline, **while BPM stable** | 4s | 12s | The #1 missed moment per Kaan's feedback. v4 fires `LAYER_ARRIVAL` on highs, never on kick character |
| **SUB_LAYER_ARRIVAL** | sub bass tail / 808-style rumble joined under the kick | `band_energy(20–60Hz)` jumps >50% AND `sub_share` rises >0.15 in 2s | 2s | 15s | Closes "AI calls it a drop when it's just sub coming in under existing kick" |
| **DISTORTION_CLIMB** | producer-driven saturation ramp (kick or master) | `spectral_flatness(band=100Hz–8kHz)` rises monotonically for >3s + `crest_factor` falls — pumping vs square-edged | 4s | 20s | Closes the "intensity build" hallucination. v4's RMS-curve `BUILD` phase misses this because RMS stays flat while harmonic density rises |
| **HAT_STUTTER_ONSET** | 1/16 or 1/32 closed-hat pattern arrival (raw hat, no pre-existing loop) | onset count `band=6–14kHz`, win=1s. Trigger if onsets_per_sec > 2× BPM/60 (faster than 16ths) for ≥2s after <2× baseline | 2s | 10s | Catches the rolling tension lift before the next kick swap |
| **ACID_LINE_ENTRY** | 303 / TB-style line arrives or modulates resonance | spectral centroid sweep in `band=300–2000Hz` >2 semitones in <4s while harmonic peaks remain narrow (Q-detection: top-3 spec peaks within 80Hz at base frame) | 4s | 18s | Acidcore-specific. Closes the "AI says synth lead" when it's actually a 303 resonance sweep |
| **PHRASE_TENSION** | bar 13–16 of a 16-bar phrase (mute-out approach) | downbeat-locked counter (see Phrase Awareness section). Fire when `phrase_position ∈ {13,14,15}` AND `band_energy(20–100Hz)` falling >0.1σ/bar | 8s | per-phrase (one fire per phrase max) | "AI calls a drop seconds before the actual drop" or "AI misses the breakdown approach" |
| **BREAKDOWN_KICK_KILL** | the moment the kick stops cold (filtered out or muted) for the phrase reset | `band_energy(20–120Hz)` falls >70% in <500ms while `mid_share + high_share > 0.6` | 1s | 12s | Hard-tek listeners _live_ for this moment. v4 catches it only as `PHASE: build→drop` mislabeled |
| **REENTRY_KICK_LAND** | post-breakdown kick lands on the downbeat | sub/low_share recovery >0.4 within 500ms of detected downbeat after `BREAKDOWN_KICK_KILL` | 1s | post-pair only | Catches the climactic moment, lets the AI react with timing precision ("nailed the bar 1 reentry" vs "kicked back in late") |
| **NOISE_FLOOR_RISE** | atmospheric noise/reverb-tail layer enters under the loop | `band_energy(8–16kHz)` rises >50% with low onset density (`onsets_per_sec(high) < 1`) — sustained noise, not hats | 4s | 25s | Closes the "AI hears nothing changing" failure during ambient-build sections |

**Detector primitives needed (DSP shared across hard-tek primitives):**
1. `band_energy(lo, hi, win)` — already in v4 `snapshot_features`. Extend to take arbitrary band ranges, not just the 5 fixed bands.
2. `spectral_flatness(band, win)` — Wiener entropy of FFT magnitude in band. Cheap: 1 extra `np.log + np.mean` per band per tick.
3. `crest_factor(band, win)` — `peak / rms` of band-filtered signal. Trivial.
4. `spectral_centroid(band, win)` — already implicit in band ratios; expose as scalar in Hz for sweep detection.
5. `onsets_per_sec(band, win)` — v4 has full-spectrum version; band-limit it (BP filter via FFT mask, then envelope + thresholded diff).
6. `downbeat_phase(bpm, win=8s)` — see Phrase Awareness section.

### Techno (peak-time, driving, minimal)

BPM **128–140**. Less kick-distortion, more groove + arrangement. Track-anchored not phrase-anchored. Per [universeoftracks Techno structure guide](https://universeoftracks.com/the-ultimate-guide-to-techno-track-structure/), peak-time builds are 16–32 bar tools with single-element introduction.

| Primitive | DSP recipe | Window | Cooldown |
|---|---|---|---|
| **STAB_ENTRY** | rare percussive stab (clap layer, woodblock, FX hit) | high-band transient + spectral centroid >3kHz, isolated (not part of hat pattern) | 2s | 14s |
| **GROOVE_LOCK** | bassline + hat + kick all stable for >32s (no element changes) | low-variance flag across all band shares for 32s window | 32s | 60s |
| **SECONDARY_PERCUSSION_LAYER** | shaker / conga / ride-pattern arrives under main 4/4 | mid-high onset density rise without kick-pattern change | 4s | 18s |
| **PHRASE_RELEASE** | 32-bar phrase tension release | phrase-position-aware drop in mid_share | 8s | per-phrase |
| **FILTER_OPEN** | low-pass filter sweep on outgoing/loop | mid+high share rising monotonically while low_share flat for 4–8s | 6s | 20s |

### Tech House / Deep House / French House

BPM **120–128**. Filter sweeps are the **identifying gesture** ([NITELIFE filtered disco loop article](https://nitelifeaudio.com/classic-techniques-the-filtered-disco-loop/), [Mixgraph tech house mixing guide](https://www.mixgraph.io/mixing-guide/tech-house)). Sidechain pumping is the texture. Loops > arrangement.

| Primitive | DSP recipe | Window | Cooldown |
|---|---|---|---|
| **LOWPASS_SWEEP** | smooth high-cut filter close | high+mid_share dropping monotonically >0.2 over 4–8s while low_share stable | 6s | 16s |
| **HIGHPASS_SWEEP** | low-cut filter sweep | sub+low_share dropping monotonically while highs stable | 6s | 16s |
| **VOCAL_CHOP_ENTRY** | sampled vocal chop / disco-cut enters | mid_share spike + harmonic peak in 200–2000Hz with rhythmic gating | 4s | 18s |
| **SIDECHAIN_PUMP_ARRIVAL** | sidechain compression character changes (depth or speed) | low_share amplitude-modulated at kick rate, depth >0.3 | 4s | 25s |
| **CONGA_PERCUSSION_LAYER** | live-feel percussion arrives (conga, bongo, cowbell) | mid-high band onsets at non-4/4 positions, off-beat density >2× on-beat | 4s | 20s |
| **PIANO_STAB** | classic house piano chord stab | broad mid-band transient with harmonic peaks at musical intervals, ~150–600Hz | 2s | 14s |

### Drum & Bass (liquid / neuro)

BPM **172–180**, half-time at 86–90 perceived. Reese bass + amen-break-derived snare patterns are the genre signature ([Neurofunk wiki](https://electronicmusic.fandom.com/wiki/Neurofunk), [BassGorilla reese guide](https://bassgorilla.com/what-is-reese-how-make-one/)). Drops are the centerpiece.

| Primitive | DSP recipe | Window | Cooldown |
|---|---|---|---|
| **DROP_FROM_BREAKDOWN** | 16/32-bar breakdown ending into bass drop | `band_energy(60–250Hz)` jumps >0.5σ within 250ms after sustained-low period of 8+s | 1s | 30s |
| **REESE_BASS_ENTRY** | detuned/modulated bass arrival | low_share rise + `spectral_flatness(60–500Hz)` jump >0.3 (sawtooth detune = wide spectral spread) | 2s | 25s |
| **HALF_TIME_SWITCH** | full-time DnB drum → half-time pattern | snare onset density drops 50% while kick density holds (snare moves from beat 2&4 to beat 3 only) | 4s | 30s |
| **AMEN_BREAK_LAYER** | classic chopped-break drum sample | broadband transient cluster, irregular onsets at 16th-note positions, spectral signature of vinyl-sampled break (rolloff curve match) | 4s | 25s |
| **NEURO_BASS_MOD** | reese modulating pitch / formant | low_share constant but `spectral_centroid(60–500Hz)` swept >50Hz in <2s | 2s | 18s |
| **VOCAL_ATMOS_LAYER** | liquid-specific vocal pad arrival | high_share rise + sustained harmonic peaks in 800–4000Hz with low onset density | 4s | 25s |

### Trance (uplifting, psy, progressive)

BPM **132–145** (prog), **140–150** (uplifting), **140–150** (psy). Long-form arrangement — 32-bar breakdowns and 16-bar builds are doctrine ([Myloops trance structure](https://www.myloops.net/trance-song-structure-breakdown-basics), [How To Make Electronic Music on trance structure](https://howtomakeelectronicmusic.com/trance-song-structure-and-how-does-uplifting-trance-song-progress/)). The breakdown _is_ the genre.

| Primitive | DSP recipe | Window | Cooldown |
|---|---|---|---|
| **BREAKDOWN_ENTRY** | kick drops out, melody/pad sustain begins | `band_energy(20–120Hz)` falls >60% sustained 4+s while mid/high persist | 4s | 60s |
| **SUPERSAW_LEAD_ENTRY** | classic detuned supersaw lead arrives | `spectral_flatness(500–4000Hz)` jumps >0.4 + dominant centroid 1–3kHz | 2s | 30s |
| **BUILD_RISER** | white-noise/synth sweep rises toward drop | broadband high-energy ramp + filter open over 4–16s | 8s | per-build |
| **DROP_AFTER_BREAKDOWN** | end-of-breakdown bass+kick reentry | low_share recovery >0.4 + onset density jump | 1s | 60s |
| **ARP_LAYER** | gated arpeggio enters | mid-band rhythmic onset density at 8th/16th rate, melodic pitch movement | 4s | 25s |
| **PSYTRANCE_ROLLING_BASS** | psy-specific 16th-note rolling bass | low-band onset density >8/sec sustained, narrow spectral peak | 4s | 30s |

### UK Garage / 2-step / bassline

BPM **128–138**. **Swung 16ths + skippy 2-step kick/snare** is the identity ([Studio Brootle UK garage breakdown](https://www.studiobrootle.com/uk-garage-drum-pattern-with-presets-and-bassline/), [Wikipedia 2-step](https://en.wikipedia.org/wiki/2-step_garage)). Kick is NOT 4-on-floor — that's the whole point.

| Primitive | DSP recipe | Window | Cooldown |
|---|---|---|---|
| **SHUFFLE_GROOVE_DETECTED** | 2-step skippy pattern (not 4/4) | kick onsets land on beats 1, 2.5, 4 (not every beat); micro-timing offset of hats > 30ms swing | 4s | 60s (set-level) |
| **BASSLINE_GENRE_SWITCH** | switch from sub-bass to bassline-house style wobble | low_share modulation at 4–8Hz LFO rate (wobble) | 4s | 25s |
| **VOCAL_CHOP_ENTRY** | sliced R&B vocal arrives | mid_share spike with rhythmic envelope tied to grid | 4s | 18s |
| **SNARE_DROP** | crisp snare-on-3 character change (new snare layer) | mid-high band transient at beat 3 with spectral centroid >2kHz | 2s | 15s |
| **DUB_DELAY_THROW** | classic dub-style delay throw on vocal | echo signature — periodic copy in `mid_share` with 1/8 or 3/16 spacing | 4s | 18s |

### Hip-hop / Trap

BPM **130–170** (trap perceived 65–85). **808 sub + hi-hat rolls** are the entire DSP fingerprint ([Wikipedia trap music](https://en.wikipedia.org/wiki/Trap_music), [Top Music Arts on 808s](https://topmusicarts.com/blogs/news/808s-and-trap-production)).

| Primitive | DSP recipe | Window | Cooldown |
|---|---|---|---|
| **808_SLIDE** | 808 pitch slide between notes | `spectral_centroid(20–120Hz)` slewing >2 semitones in <500ms | 1s | 8s |
| **HAT_ROLL_TRIPLET** | 16th or 32nd hat roll | `band_energy(6–14kHz)` onset density >2× baseline for >1s, regular spacing | 1s | 6s |
| **SNARE_ROLL_BUILD** | snare roll into beat drop | mid-high band onset density ramp over 2–4s | 4s | 12s |
| **808_DROP** | 808 enters after intro/break | `band_energy(20–80Hz)` jump >0.5σ + sustained long decay >300ms | 2s | 30s |
| **VOCAL_AD_LIB_ENTRY** | ad-lib vocal stab | short mid-band transient with vocal formant signature | 2s | 8s |
| **BEAT_SWITCH** | full beat reconfigures (Drake/Travis-style mid-track flip) | simultaneous changes in all of: kick pattern, snare position, melody | 4s | 60s |

### Disco / Nu-disco

BPM **115–125**. **Live-feel instrumentation, velocity-varied groove, classic verse-chorus structure** distinguish from house ([Wikipedia nu-disco](https://en.wikipedia.org/wiki/Nu-disco), [Attack Magazine nu-disco breakdown](https://www.attackmagazine.com/technique/beat-dissected/nu-disco-live-groove/)).

| Primitive | DSP recipe | Window | Cooldown |
|---|---|---|---|
| **STRING_SECTION_ENTRY** | disco strings arrive | high-band sustained harmonics, narrow spectral peaks at musical pitches in 400–4000Hz, slow attack | 4s | 25s |
| **GUITAR_LICK** | funk guitar (chicken-scratch or single-note riff) | mid-band onset density on offbeats + spectral centroid 1–3kHz | 2s | 14s |
| **COWBELL_PERCUSSION** | cowbell/woodblock layer | narrow spectral peak ~800Hz–1.5kHz, rhythmic onsets | 2s | 20s |
| **CHORUS_HOOK** | verse → chorus transition (live-song structure) | broadband energy lift + vocal arrival (mid 200–2000Hz harmonic peaks) | 8s | per-section |
| **BREAKDOWN_PERCUSSION_SOLO** | "drum break" section (most percussion exposed) | mid+high band onset density holds while low_share falls >0.4 | 4s | 60s |
| **PIANO_STAB** | classic disco piano | broadband mid-attack with harmonic peaks at musical intervals | 2s | 14s |

---

## Phrase awareness — feasibility + recommended approach

**The problem with v4 today:** events fire by spectral diff at the moment the diff exceeds threshold. The AI gets no positional context. "Drop at bar 17 of 32-bar phrase" ≠ "Drop at bar 5" — the first is on-grid musical move, the second is a phrase-break gesture. v4 reports both as `PHASE: build → drop`.

**Three approaches considered:**

1. **BeatNet / madmom CRNN** — state-of-the-art real-time beat + downbeat per [BeatNet ISMIR 2021](https://github.com/mjhydri/BeatNet). **Rejected for v1.0**: ~50–80MB model bundle, PyTorch dependency, blows the one-click install budget. Reconsider for v2 if Apple Silicon CoreML port becomes available.

2. **librosa beat_track + dynamic tempo** — `librosa.beat.beat_track` is reasonable but offline-oriented and at 130-180 BPM with hard-distorted kicks, accuracy degrades (per [librosa dynamic tempo example](http://librosa.org/doc/0.11.0/auto_examples/plot_dynamic_beat.html)). librosa is already an indirect dep; could be enabled but still ~30MB extra.

3. **RECOMMENDED — autocorrelation downbeat phase lock from v4's existing energy curve.** v4 already computes `estimate_bpm` via autocorrelation. Extend with: (a) compute beat phase by finding peak autocorrelation lag matching `60/bpm` seconds, (b) maintain a rolling beat-index counter `beats_seen`, (c) assume 4-beat bars (every dance genre except a few UKG variants), (d) maintain a 16-bar phrase counter, resetting on major energy resets (>40% RMS drop). **Cost:** +1–2ms per 100ms state tick. **Accuracy:** ±1 beat over 30s observed in practitioner reports for similar autocorrelation approaches; ±1 bar at the phrase level is what we need. **Loss of accuracy:** acceptable — Gemini reasons in seconds, not in samples.

**Add to `MusicState`:**
```python
@dataclass
class MusicState:
    # ... existing fields ...
    beat_index: int = 0          # beats since last hard energy reset
    bar_index: int = 0           # beat_index // 4
    phrase_position: int = 0     # bar_index % 16  (or 32 for trance)
    phrase_length: int = 16      # genre-dependent (16 for techno/house, 32 for trance)
```

**Phrase-position-aware event firing:** rather than firing `LAYER_ARRIVAL` immediately, queue it and confirm on the next downbeat. Fires "on the 1" land more musically; off-grid arrivals are flagged as `MIX_MOVE` (Kaan moved a fader between bars). This is also a hallucination-grounding move — the AI can say "layered on the 1" with confidence.

**Cost-benefit:** ~+5ms per detector tick (downbeat lock + bar count update + phrase quantize). **Worth it** — phrase-position is the single most generic-prose-breaking signal across all 8 genres.

---

## Genre auto-detection — the Gemini Embedding 2 nearest-neighbor approach

**Constraint:** Gemini-only stack (per `feedback_no_clap_use_gemini_embedding`). No CLAP, no MERT, no on-device classifier model bundling.

**Approach:** [Gemini Embedding 2](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2/) is natively multimodal — text, image, audio, video, docs in one space — and supports audio inputs natively without transcription. Cosine-similarity nearest-neighbor against a hand-curated genre-anchor library.

**The anchor library (one-time setup, shipped in the binary):**
- 8 genres × 4–6 anchor clips per genre = ~40 clips total
- Each clip 25–30s (well under the 180s audio cap)
- Curated from royalty-free or properly-licensed reference tracks per genre
- Sub-genres encoded as separate anchors (e.g. hard-tek-frenchcore, hard-tek-mentalcore, acidcore both anchor to same primary detector roster)
- Each anchor embedded **once** with Gemini Embedding 2, vectors cached as JSON (~3KB per vector × 40 = ~120KB on disk)
- **No re-embedding** at runtime — Kaan never re-builds the anchor library

**Runtime classification:**
1. At session start, wait for ≥20s of audible audio (`_music_truly_playing` already gates this).
2. Sample a 25s slice from the `AudioBuffer` (downsampled to 16kHz mono — same path v4 already uses for the inline audio Part).
3. Encode WAV → send to Gemini Embedding 2 (~1 API call, ~200ms latency).
4. Cosine-similarity against the cached 40 anchors. Top-1 wins if `(top1_cosine - top2_cosine) > 0.05`. Else mark as `genre=ambiguous`, use generic detector roster.
5. Repeat on every `TRACK_CHANGE` event with confidence ≥ 0.6 — track changes are the natural re-classification moment.
6. Cache `genre_classifier_state` in `MusicState`: `(active_genre: str, confidence: float, last_classified_at: float, anchor_distances: dict)`.

**Latency budget:** ~200ms one-shot at session start (acceptable — happens before first event). ~200ms on each track change (acceptable — runs in parallel with the in-flight gating). Free during steady-state.

**Cost:** ~$0.0001 per classification at Gemini Embedding 2 pricing. ~10 classifications per 1h DJ set = ~$0.001/hour. Negligible vs the ~$0.50/hour Flash + TTS budget.

**Fallback:** if `GEMINI_API_KEY` rate-limited or Gemini Embedding 2 unreachable → fall back to **user-declared genre** in session setup (a one-click dropdown in the future UI; v1.0 ships hard-tek as default + a hidden config override).

**Why this beats user-declaration alone:** users mix genres mid-set ("I'm starting deep, going hard around 30min"). Auto-classify catches the shift; user-declared can't.

---

## Per-genre reaction vocabulary

The detection is half. The other half is **what Gemini says**. v4's prompt has hard-tek-specific scene tags baked into `SYSTEM_INSTRUCTION` (lines 196: "Kaan plays Hard Tek… Hard Tek (raw distorted kicks, 170+ BPM, French/Belgian free-party) or Acidcore Techno"). This is genre-locked, so the prompt itself needs to be **per-genre**.

Lift the v4 `SYSTEM_INSTRUCTION` into a per-genre template. Replace the SCENE TAGS + WHAT TO COACH sections per genre.

| Genre | Sample reaction vocabulary | Critique vocabulary | "Mistake" categories |
|---|---|---|---|
| **Hard tek** | "kick swap landed clean", "sub-rumble layer locked in", "the distortion floor lifted that loop", "16-bar tension ran 4 bars too long" | kick collision, sub stacking, distortion floor, layer count, phrase tension | distorted kicks colliding, sub-layer redundancy, 4-bar over-stretching, no kick swap for 64 bars |
| **Techno (peak)** | "groove locked", "stab cut through", "filter open released the room", "phrase tension built right" | stab placement, filter sweep depth, percussion layer arrival, groove drift | stab over-used, filter sweep too fast, percussion layer fighting hat pattern |
| **Tech house** | "filter close held the tension", "low cut on the incoming cleaned the blend", "piano stab placed clean", "the swing fell out" | filter timing, sidechain depth, swing feel, percussion overlap | filter sweep clashing with incoming, sidechain inconsistent between decks, piano stabs colliding |
| **Liquid DnB** | "reese pulled clean through the drop", "half-time switch caught the listener", "vocal pad lifted the breakdown" | reese tone, drop timing, break choice, vocal placement | reese clashing key, half-time switch too early, vocal layer fighting the lead |
| **Trance** | "breakdown felt 4 bars too short", "the build released right on the 1", "supersaw lead carried the drop" | breakdown duration, build pacing, supersaw character, drop release timing | build released early/late, breakdown over-stretched, supersaw too thin |
| **UKG** | "shuffle held through the blend", "vocal chop placed on the &", "skippy kick swap landed" | swing depth, chop placement, snare-on-3 timing | shuffle drift between tracks, chop colliding with bass, snare-on-3 weak |
| **Trap** | "808 slide caught the bar", "hat roll built right", "beat switch reset the room" | 808 character, hat roll pacing, beat switch timing | 808 muddy, hat roll trailing into next bar, beat switch too predictable |
| **Disco** | "strings carried the chorus", "guitar lick punched in clean", "breakdown stripped to perc held it" | string tone, guitar placement, breakdown duration, percussion exposure | strings clashing key, guitar lick over-loud, breakdown too long |

**Template plumbing:** each genre file (`vibemix/prompts/genres/<genre>.py`) exposes `SCENE_TAGS`, `MISTAKE_CATEGORIES`, `REACTION_VOCAB`. `AICoach.build_prompt(ev, genre)` composes the per-event task with the right per-genre vocabulary. Keep v4's hard-coded hard-tek prompt as the hard-tek genre file — no rewrite, just relocation.

---

## Cross-genre detector composition architecture

**Three layers** of detectors, composed at runtime:

### Layer 1 — Cross-genre baseline (always on)

These fire regardless of genre. They're the v4 set, lightly cleaned:
- `KAAN_SPOKE` (mic gate)
- `MANUAL` (controller trigger)
- `TRACK_CHANGE` (audible-deck + nowplaying-cli cross-ref)
- `HEARTBEAT` (no-event fallback)
- `MIX_MOVE` (significant MIDI moves)
- `GENRE_SHIFT` (the new one — auto-classifier flips genres mid-set)

### Layer 2 — Active-genre detectors (one set live at a time)

Loaded from `vibemix/events/genres/<genre>.py`. Each module exposes `DETECTORS: list[Detector]`, where `Detector` is a dataclass:
```python
@dataclass
class Detector:
    name: str                          # e.g. "KICK_SWAP"
    detect_fn: Callable[[MusicState, AudioBuffer, float], Event | None]
    cooldown_sec: float
    min_audio_window_sec: float        # how much audio it needs in the buffer
    phrase_aware: bool = False         # if True, gated to bar boundary
```

The `EventDetector.detect()` becomes:
```python
def detect(self, state, *, kaan_just_spoke, manual):
    # ... bypass for KAAN_SPOKE / MANUAL ...
    if not self._music_truly_playing(state, now):
        return None
    # Layer 1 — baseline
    for det in BASELINE_DETECTORS:
        if ev := det.detect_fn(state, audio_buf, now):
            if self._cooldown_ok(det.name, now):
                return ev
    # Layer 2 — active genre
    for det in GENRE_ROUTER.active_detectors():
        if ev := det.detect_fn(state, audio_buf, now):
            if self._cooldown_ok(det.name, now):
                return ev
    return None
```

### Layer 3 — Sub-genre overlays (optional, additive)

Mostly for hard tek (acidcore overlay adds `ACID_LINE_ENTRY`). Sub-genres tag onto active genre, not replace it.

### Genre switch handling

When the auto-classifier flips genres mid-set:
1. `EventDetector` emits `GENRE_SHIFT` event with old + new genre in `extra`.
2. AICoach uses the NEW genre's reaction vocabulary starting from the next event.
3. Active detector roster swaps atomically (lock around `GENRE_ROUTER.active_detectors`).
4. **No session restart** — the LiveKit RealtimeModel stays open. Only the detector dict swaps.

This composition matches v4's "single source of truth" architecture (`MusicState` writer is unchanged) — the routing layer is purely above it.

---

## v1.0 deep genre pick + expansion roadmap

**v1.0 deep genre = Hard Tek / Acidcore Techno.**

Reasons in order:
1. **Kaan's personal practice** — the entire grounded-tuning advantage requires real DJ sets to tune against. Kaan plays hard tek live. Every other genre needs surrogate reference data.
2. **High distinctiveness** — hard tek has clear DSP signatures (distortion floor, kick swap, sub-layer arrival) that other genres don't share. Easier wins per detector.
3. **Underserved by competitor tools** — Mixmag and DJTechTools reviews of existing DJ AI tools (e.g. Algoriddim Neural Mix, Pioneer's CDJ AI assist) all skew commercial/peak-time. Going hard-tek-deep is a wedge.
4. **Hard tek subculture overlaps with vibemix's target audience** — hard tek / techno listeners overlap heavily with the bedroom-DJ + producer Twitter/IG audience we want to convert into Bravoh waitlist. GitHub-star demographic skew.

**v1.1 expansion order:**
1. **Techno (peak-time, driving, minimal)** — shares 80% of hard-tek detectors. Fastest port.
2. **Tech house / French house** — Kaan's secondary practice (French Touch reference in v4 constants). Filter-sweep + sidechain detectors are easy DSP wins.
3. **Drum & Bass (liquid first, then neuro)** — distinct detector set but well-documented production conventions. Half-time switch is a single-detector grounding moment.
4. **Trance (uplifting + progressive)** — phrase-awareness pays off most here. Long breakdowns are a phrase-position-aware event masterclass.
5. **UKG / 2-step** — swing detection is a one-of-a-kind detector that doesn't generalize backward. Plays well with v2's broader "groove fingerprint" work.
6. **Hip-hop / Trap** — sub-bass + hat-roll detectors. BPM perception ambiguity (130 vs 65) needs careful handling. Less DJ-mixing focus, more vibes/track-anchor focus.
7. **Disco / Nu-disco** — most "live-feel" detectors. Hardest to port cleanly because velocity-variation detection is unreliable.

**Each expansion = 1 weekend of work** if v1.0 architecture is right (per-genre file plug-in, detector composition layer working). v1.1 ships Techno + Tech House within ~2 weeks of v1.0. Trance/DnB/UKG/Trap/Disco roll out one per minor release.

---

## Reference dataset sources

We need 5–10 reference DJ sets per genre for detector threshold tuning + LLM eval of per-genre reaction quality.

**Tier 1 — direct, legal:**
- **Kaan's own session recordings** — gold for hard tek. v4 already writes `input.wav` per session under `recordings/`. Build a hidden `_test_set/` directory of 8–10 30-min slices.
- **Boiler Room official YouTube uploads** — accessible per IP; for non-commercial detector tuning under fair-use research framing, audio extracts are reasonable. Set lists are published per artist.
- **Resident Advisor podcasts (RA.xxx series)** — free, well-documented per genre, published with track lists. ~5000+ episodes covering every genre we ship.

**Tier 2 — annotated/partially-curated:**
- **1001Tracklists** — community-annotated set transitions with timestamps. The transition timestamps are the gold for `TRACK_CHANGE` detector eval. Free read access; use for ground-truth labeling of detection accuracy.
- **Mixcloud** — searchable per genre tag, embeddable streams. Less reliable than RA for genre purity.

**Tier 3 — synthetic / paid:**
- **Sample packs** ([Splice, Loopmasters](https://www.loopmasters.com)) — produce reference 30s clips per genre/sub-genre. For the genre-anchor library (40 clips) this is the clean source — properly licensed, isolated genre signatures.
- **Custom DJ recordings via Francesco's DJ network** — Kaan's co-founder has direct outreach. v1.1+ pre-launch, ship 5 ref sets per non-hard-tek genre from real DJs willing to license a slice for the project.

**Reference-set composition target:**
- Per genre: 8 sets, 30 minutes each, with timestamped track changes and ≥3 hand-labeled events per set (KICK_SWAP / LAYER_ARRIVAL / DROP / BREAKDOWN_ENTRY / etc.).
- Total: 64 sets × 30min = ~32 hours of audio + ~1000 hand-labeled events. Built incrementally — start with 8 hard-tek sets for v1.0.

**Eval methodology (Phase 16-aware):** Kaan's DJ ear is the v1.0 detector eval per `project_phase_16_kaan_dj_testing`. He listens to his own sessions, scrubs to events the AI fired, judges by feel. Don't pre-build the 30-session replay harness — let Kaan's ear be the gate. Formalize to LLM-judge calibration in v2 only if v1 ear-testing reveals systematic gaps.

---

## Tractability matrix

| Detector | DSP cost (per tick) | Audio window | Grounding payoff | Confidence |
|---|---|---|---|---|
| `KICK_DENSITY_SHIFT` | ~2ms (band-FFT + envelope) | 2s | High — closes "AI says new beat" hallucination | High |
| `KICK_SWAP` | ~3ms (spectral centroid + crest factor) | 4s | **Critical** — Kaan's #1 missed moment | High |
| `SUB_LAYER_ARRIVAL` | ~1ms (band energy diff) | 2s | High — drop hallucination class | High |
| `DISTORTION_CLIMB` | ~3ms (spectral flatness) | 4s | High — closes "intensity build" hallucination | Medium (genre-anchor tuning needed) |
| `HAT_STUTTER_ONSET` | ~2ms (high-band onset density) | 2s | Medium | High |
| `ACID_LINE_ENTRY` | ~5ms (Q-detection on top-3 spec peaks) | 4s | Medium (acidcore only) | Medium |
| `PHRASE_TENSION` | ~5ms (incl downbeat lock cost) | 8s | **High** — phrase-position grounding | Medium (depends on downbeat accuracy) |
| `BREAKDOWN_KICK_KILL` | ~1ms (low-band energy diff) | 1s | High | High |
| `REENTRY_KICK_LAND` | ~1ms (paired event with above) | 1s | High — timing-precision moment | Medium |
| `LOWPASS_SWEEP` (tech house) | ~2ms | 6s | High for tech-house genre | High |
| `REESE_BASS_ENTRY` (DnB) | ~3ms | 2s | High for DnB | High |
| `HALF_TIME_SWITCH` (DnB) | ~4ms (snare-position tracking) | 4s | High for DnB | Medium (needs snare detector) |
| `BREAKDOWN_ENTRY` (trance) | ~2ms | 4s | **Critical** for trance | High |
| `SUPERSAW_LEAD_ENTRY` (trance) | ~4ms (spectral flatness in mid-band) | 2s | High for trance | Medium |
| `SHUFFLE_GROOVE_DETECTED` (UKG) | ~8ms (micro-timing analysis) | 4s | Genre-classifier feature | Low (needs careful tuning) |
| `808_SLIDE` (trap) | ~2ms (low-band centroid slew) | 1s | Critical for trap | High |
| `STRING_SECTION_ENTRY` (disco) | ~5ms (harmonic peak narrowness) | 4s | High for disco | Medium |
| `Genre auto-classification` (Gemini Embedding 2) | 200ms API once per track | 25s | **Critical** — routes everything else | High |
| `Phrase awareness (downbeat lock)` | ~5ms per tick | 8s | **Critical** — improves all phrase-aware events | Medium (±1 bar accuracy) |

**Total per-tick DSP cost for hard-tek active set:** ~25ms per 100ms tick. Well under the 50ms budget. Comfortable headroom for v2 additions.

---

## Risk + watchouts

1. **BPM autocorrelation fails on hard-tek distortion floor.** v4's `estimate_bpm` autocorrelates the energy envelope. Heavily distorted/saturated kicks have less envelope contrast (the saturation flattens dynamics). Mitigation: band-limit the envelope to 40–120Hz before autocorrelating; reject BPM if autocorr peak height < 0.15 of zero-lag.
2. **Genre auto-classifier can flap.** If Kaan plays a hard-tek track with an ambient breakdown, the breakdown's 25s slice may classify as trance. Mitigation: require 2 consecutive classifications agree before flipping `active_genre`; raise the margin threshold (0.05 → 0.08) for re-classifications mid-set vs initial.
3. **Phrase counter drift over time.** Autocorrelation downbeat lock will drift over a 30-min set. Mitigation: hard-reset phrase counter on every detected `BREAKDOWN_KICK_KILL` (it's the natural phrase boundary in every genre). Cheap and self-correcting.
4. **Per-genre detector roster explosion.** Each new genre adds ~8 detectors × 8 genres = 64 detectors. Most will share primitives. Strict primitive library (`band_energy`, `spectral_flatness`, `crest_factor`, `onsets_per_sec(band)`) prevents one-off DSP per detector. **Code-review rule: no detector creates a new primitive without writing the primitive into the shared library first.**
5. **Gemini Embedding 2 is preview-status as of 2026-03.** API + pricing may change before vibemix v1 launch. Mitigation: cache classifier results aggressively (one classification per track-change is plenty); have a static-default fallback to hard-tek if API is missing/quota-busted.
6. **Anchor library bias.** If anchors are chosen by Kaan alone, the classifier will be biased toward Kaan's interpretation of each genre. Mitigation: for v1.1+ genres, source 2–3 anchors from external practitioners (Francesco's network, RA podcasts) per genre.
7. **Sub-genre proliferation can dilute the v1.0 promise.** Don't ship 5 hard-tek sub-genres at v1.0 — ship one detector roster ("hard tek") and let the acidcore overlay be the only sub-genre. Defer "tribecore vs frenchcore vs mentalcore" to v2.
8. **Phrase awareness wrong on transitional tracks.** During a 32-bar blend of two hard-tek tracks, the dominant track has phrase-position 17 but the incoming track has phrase-position 1. Mitigation: phrase awareness uses the **audible-deck** track only; during a blend the dominant deck is tracked by MIDI volumes (`audible_deck` is already in `MusicState`).

---

## Open questions for Kaan

1. **Anchor library curation:** is Kaan OK contributing 4–6 anchor clips (30s each) for hard tek + acidcore, and using public RA/Boiler Room sets for the other 6 genres? Or does Francesco's network provide better anchors for the non-hard-tek list?
2. **Sub-genre granularity at v1.0:** ship "Hard Tek" as one mode, or split into "Hard Tek" + "Acidcore" toggles? My recommendation is one mode with the acid detectors as an overlay that auto-activates on acid-line detection. Confirm?
3. **User-declared override:** should v1.0 ship a hidden `~/.vibemix/genre_override.yaml` config for "force genre = X"? Useful for early testers but also a leak for "vibemix knows my genre" being the magic moment. Recommendation: ship it hidden, surface in v1.1 UI.
4. **Phrase length per genre:** 16-bar for techno/house is doctrine. 32-bar for trance is doctrine. For hard tek — is the practitioner consensus 16 or is mentalcore/frenchcore more often 8-bar phrased? Need Kaan's ear here.
5. **Gemini Embedding 2 pricing + quota risk:** if 2026-mid pricing shifts to make per-track classification expensive, are we comfortable with a per-session-once classification + manual override fallback? Or do we hard-cache the active genre per session?

---

## Research sources

- [EDMProd — What is Hard Techno?](https://www.edmprod.com/what-is-hard-techno/)
- [Toolroom Academy — Perfecting Your Techno Kick](https://toolroomacademy.com/features/how-to-make-techno-perfecting-your-kick/)
- [Melodigging — Hard Industrial Techno](https://www.melodigging.com/genre/hard-industrial-techno)
- [Gearspace — Heavy distortion layers in techno](https://gearspace.com/board/electronic-music-instruments-and-electronic-music-production/1307705-how-get-very-heavy-distortion-layers-techno.html)
- [BassGorilla — Reese Bass](https://bassgorilla.com/what-is-a-reese-bass/)
- [Future Audio Workshop — Reese Bass Explained](https://futureaudioworkshop.com/the-reese-bass-explained/)
- [Neurofunk Wiki](https://electronicmusic.fandom.com/wiki/Neurofunk)
- [Noise Masters — Reese Bass for DnB](https://noisemasters.eu/blogs/dnb-guides/how-to-make-reese-basses-for-drum-and-bass-a-step-by-step-guide)
- [NITELIFE Audio — Filtered Disco Loop](https://nitelifeaudio.com/classic-techniques-the-filtered-disco-loop/)
- [Mixgraph — Tech House Mixing](https://www.mixgraph.io/mixing-guide/tech-house)
- [Myloops — Trance Song Structure](https://www.myloops.net/trance-song-structure-breakdown-basics)
- [How To Make Electronic Music — Trance Structure](https://howtomakeelectronicmusic.com/trance-song-structure-and-how-does-uplifting-trance-song-progress/)
- [Universe of Tracks — Techno Structure](https://universeoftracks.com/the-ultimate-guide-to-techno-track-structure/)
- [Mixed In Key — Dance Music Arrangement](https://mixedinkey.com/captain-plugins/wiki/how-to-arrange-a-dance-music-track/)
- [Studio Brootle — UK Garage Drums](https://www.studiobrootle.com/uk-garage-drum-pattern-with-presets-and-bassline/)
- [Wikipedia — 2-step garage](https://en.wikipedia.org/wiki/2-step_garage)
- [Wikipedia — UK garage](https://en.wikipedia.org/wiki/UK_garage)
- [Attack Magazine — UK Garage breakdown](https://www.attackmagazine.com/technique/beat-dissected/uk-garage/)
- [Native Instruments — UK Garage primer](https://blog.native-instruments.com/uk-garage-music/)
- [Wikipedia — Trap music](https://en.wikipedia.org/wiki/Trap_music)
- [Top Music Arts — 808s and Trap](https://topmusicarts.com/blogs/news/808s-and-trap-production)
- [Wikipedia — Nu-disco](https://en.wikipedia.org/wiki/Nu-disco)
- [Attack Magazine — Nu-Disco Live Groove](https://www.attackmagazine.com/technique/beat-dissected/nu-disco-live-groove/)
- [Tracklister — Nu-Disco guide](https://tracklist.live/discover/guide/nu-disco)
- [BeatNet — Real-time beat tracking (ISMIR 2021)](https://github.com/mjhydri/BeatNet)
- [Madmom documentation](https://madmom.readthedocs.io/en/v0.16/modules/features/onsets.html)
- [Essentia — Onset Detection](https://essentia.upf.edu/reference/streaming_OnsetDetection.html)
- [librosa — Dynamic beat tracking](http://librosa.org/doc/0.11.0/auto_examples/plot_dynamic_beat.html)
- [Gemini Embedding 2 announcement](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2/)
- [Gemini Embedding 2 — Google DeepMind page](https://deepmind.google/models/gemini/embedding/)
- [Google Developers — Building with Gemini Embedding 2](https://developers.googleblog.com/en/building-with-gemini-embedding-2/)
- vibemix internal: `cohost_v4.py` lines 134–143 (event cooldowns), 1167–1330 (EventDetector), 341–446 (snapshot_features + estimate_bpm) — the architecture this proposal plugs into.
- vibemix memory: `project_v4_canonical_baseline`, `feedback_no_clap_use_gemini_embedding`, `project_anti_slop_grounded_gemini_thesis`, `project_phase_16_kaan_dj_testing`, `project_one_click_install_hard_req`.
