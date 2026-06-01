# THE MIXXX GOLDMINE MAP — ROUND 2 (DSP / PERFORMANCE / UX)

**Date:** 2026-05-31 · **Purpose:** Mine Mixxx's DSP/performance/UX layer for clean-room algorithms that turn vibemix's #1 live slop bug (R-SLOP) from an ungrounded causal claim into a measured one, plus net-new learning/debrief capabilities.
**LICENSE:** Every algorithm below is LEARNED-FROM-SPEC and reimplemented clean-room in vibemix's own numpy/Python. Mixxx (GPL-2.0) is cited `file:line` as a METHOD REFERENCE only — no source vendored. Where the real DSP lives in a permissive external lib (libebur128 MIT, fidlib public-domain) or in a public standard (ITU-R BS.1770, Audio-EQ-Cookbook), the standard is the source, not Mixxx.

**Round 1 (NOT re-covered):** beatgrid, sync-engine, cue, autodj, enginebuffer, key-detection.

---

## 1. THE HEADLINE UNLOCKS

Ranked by `unlock + feasibility + moat + wow`. The R-SLOP grounding fixes lead — they attack the named release blocker.

### #1 — Loop/Beatjump = the R-SLOP-IMMUNE move class `[BUILD_NOW]`
- **Unlocks:** The *cleanest* R-SLOP kill in the whole round. A loop or beatjump is the rare move whose musical effect is **deterministically computable with zero spectral inference** — boundaries are MIDI-timestamped and beatgrid-exact by construction. Today `apply_live_claim_guard` strips every fader/EQ causal claim to the ack-bank (`rule=dsp_delta_not_causal_proof`); a loop's effect ("held a 1-bar loop for 4 bars, then +8 into the phrase") is provable from MIDI timing + beatgrid alone, the two highest-trust evidence sources.
- **Mixxx ref:** `engine/controls/loopingcontrol.cpp:1416` `findBeatloopSizeForLoop` (frames→beat-size reverse map), `:27` `s_dBeatSizes[]` lattice, `track/beats.cpp:504` `findNBeatsFromPosition`.
- **vibemix point:** NEW `state/loop_geometry.py` (verified ABSENT) → emit a fused `A_loop:4-beat` label from `midi/state.py:225 _record_move` (today emits two bare buttons, `:398-400`); new `rule=loop_boundary_beatgrid_exact` atom in `deck_context.py:1769 move_evidence_atoms` / `:2005 render_move_effect_context`; PASS branch in `apply_live_claim_guard:2239`.
- **Scores:** unlock 5 · feasibility 4 · moat 5 · wow 4 → **BUILD_NOW** (gate through `vibemix-grounding-review` — touches Invariant #2/#3).
- **Smallest proof:** unit test on a synthetic 120-BPM beatgrid: in/out 4 beats apart → returns 4.0; 3.5 beats apart → returns −1 (no false match). Then a guard test: geometry claim about a cited loop PASSES; same sentence + an appended audio-quality verdict ("the loop built tension") STRIPS.

### #2 — "Spectral Receipt": EQ-move band-delta grounds the kill claim `[BUILD_NOW]`
- **Unlocks:** THE BIG ONE for EQ/filter. Compute the *expected* per-band gain of a known move (clean-room RBJ biquad `|H(f)|²` integrated over `band_features._BANDS`) and confirm it against the *measured* `sub+low` ratio delta. The claim grounds only when measured moves in the predicted direction past `DELTA_FLOOR=0.10` (verified); on a breakdown / no-bass section it REFUTES → `LIVE_MOVE_EFFECT_HELD_*` instead of asserting a phantom effect.
- **Mixxx ref:** `effects/backends/builtin/biquadfullkilleqeffect.cpp:14-39` (Q 0.3/0.9/0.4, `kKillGain=-23`, log-geometric center, corners 246/2484), `engine/filters/enginefilteriir.h:240-288` (½-buffer ramp = settling lag), `enginefilterbessel4.cpp:23-46` (group-delay table).
- **vibemix point:** NEW `intel/eq_move_model.py` (ABSENT) `predicted_band_gains(move, fs)`; call site beside `_has_unsupported_mixer_low_kill_claim:2412` inside `apply_live_claim_guard:2239`; consumes existing `render_audio_delta_items:1729` + `band_energy_ratios` (`audio/band_features.py:30`).
- **Scores:** unlock 5 · feasibility 4 · moat 5 · wow 4 → **BUILD_NOW** (ship WITH the settling-lag window, below — they are inseparable).
- **Smallest proof:** `predicted_band_gains({'_low:kill'}, fs=16000)` → sub/low ≤ −15 dB, mid/high ≈ 0; two-frame fixture (bass present → killed) GROUNDS, no-bass fixture REFUTES.

### #3 — Crossing Detector: deliberate-engagement classifier grounds the fader claim `[BUILD_NOW]`
- **Unlocks:** Soft-takeover's `willIgnore` truth table, repurposed as a CLASSIFIER (vibemix never writes back, so it uses the math, not the suppression). Per CC event, classify the move `catching_up` / `crossed` / `engaged`. The classic ungrounded "you brought the faders up" with a non-empty-but-ineffective wiggle gets stripped; a deliberate grab corroborated by audio-delta grounds.
- **Mixxx ref:** `controllers/softtakeover.cpp:15-64` (`willIgnore` truth table + the `~50ms kSubsequentValueOverrideTime` fast-whip gate — **port BOTH halves**), `softtakeover.h:20` (threshold ≈ `3/128` in normalized control units).
- **vibemix point:** new `takeover_phase` field on `MidiEvent` in `midi/state.py:276-297` (`_compute_magnitude`); per-binding `(prev,time)` accumulator on the existing `ControllerState.deck[deck][field]`; consumed by `apply_live_claim_guard:2239`.
- **Scores:** unlock 5 · feasibility 5 · moat 5 · wow 4 → **BUILD_NOW**.
- **CRITICAL REFRAME (the single biggest correction across the round):** vibemix is a PASSIVE listener — it has NO read of the DJ software's internal fader value (Mixxx owns `control.getParameter()`; vibemix does not). So "crossed the LIVE audio value" is **not computable**. Reframe as "deliberate grab vs jitter on the controller's OWN timeline, corroborated by audio-delta." The crossing math is still the right tool; selling the un-computable version ships a confident-but-blind claim — the exact slop class we kill.
- **Smallest proof:** golden test reproducing Mixxx's 5-row truth table; one guard test where `moves=["A_low: flat→cut"]` but `takeover_phase=catching_up` strips a claim that today (with a real audio_delta) would pass.

### #4 — Short-term LUFS receipt: K-weighted "energy up" grounds (and disambiguates fader vs build) `[BUILD_NOW]`
- **Unlocks:** The literal number behind "you brought the energy up" is today raw linear-RMS EMA (`levels.py:39 update_music`, verified) — it rises identically whether the DJ pushed a fader (level) or the music genuinely built (content). A short-term (3 s sliding, no gating) K-weighted LUFS gives a SIGNED, citable delta: "short-term LUFS +3.1 LU over 4 s." K-weighting is the disambiguator — a broadband fader push moves RMS and LUFS together; a real build moves LUFS via band-weighted spectral shift a flat fader can't fake.
- **Mixxx ref:** `analyzer/analyzerebur128.cpp:12` (`kReplayGain2ReferenceLUFS=-18`), `:37` `EBUR128_MODE_I`, `:83-85` gain. **CAVEAT:** Mixxx does NOT implement the K-filter — it calls libebur128 (MIT). Reimplement from ITU-R BS.1770 (public), conformance-test against the −3.01 LUFS reference tone (997 Hz / −20 dBFS).
- **vibemix point:** NEW `audio/lufs.py` (ABSENT); state-refresh loop reads it beside `Levels.snapshot()` (single-writer, Invariant #1); attach `master_lufs_delta` as a citable atom into `apply_live_claim_guard`'s audio-delta path.
- **Scores:** unlock 5 · feasibility 4 · moat 5 · wow 4 → **BUILD_NOW**.
- **Smallest proof:** `ShortTermLoudness` passes the −3.01 LUFS conformance tone at 44.1k AND 48k; guard test grounds a +3 LU window, strips a flat 0 LU window.

### #5 — Grounded Move-Effect Resolver: wire the EXISTING `xfade.py` into the guard `[BUILD_NOW]`
- **Unlocks:** Upgrades the crossfader R-SLOP path from CORRELATION ("did the audio change near a move") to CAUSATION ("did it change in the DIRECTION the curve law predicts"). Given a known move (`xfader 64→112`) off the `deck_mixer` snapshot, compute the expected orientation-gain Δ in dB; license the claim only when predicted-sign ∧ measured-sign agree.
- **CRITICAL CORRECTION:** the keystone is NOT a new `state/mixer_physics.py` (the packet proposed it; it would DUPLICATE). `audio/xfade.py` **already exists** (verified: Apache-2.0, clean-room of `enginexfader.cpp:11-84`, both additive + constpwr branches, unit-power normalize). It is imported by 30+ modules (learn/midi/state/runtime) but NOT by the live R-SLOP guard. The real work: WIRE `xfade.py` into `live_claim_policy`, plus port the two MISSING laws — dB-taper fader (`controlbehavior.cpp:170-231`, ~12 lines) and pregain/headroom clamp (`enginepregain.cpp:14-147`, ~12 lines).
- **Mixxx ref:** `engine/enginexfader.cpp:11-84`, `control/controlbehavior.cpp:170-231`, `engine/enginepregain.cpp:14-162` (`kMaxTotalGainBySpeed=0.9` ≈ −1 dB headroom), `engine/enginemixer.h:82-176`.
- **vibemix point:** `deck_context.py:2126 live_claim_policy` / `:2176 _supports_grounded_transition_verdict` (already does measured per-deck audio-window delta — add the expected-Δ-sign check); replaces the crude `_xfader_factor:3254` 0-127 bucket.
- **Scores:** unlock 5 · feasibility 4 · moat 5 · wow 4 → **BUILD_NOW**.
- **Smallest proof:** known move `xfader 64→112` constpwr + measured `deck_audio_delta` with WRONG sign → NOT `supported_verdict`; right sign + matching magnitude → may.

### #6 — Per-move MIDI receipt in debrief / Earned ledger `[STRONG]`
- **Unlocks:** Makes grounding VISIBLE (the product thesis — "show its receipt"). A consumer of #1–#5: persist the classified, magnitude-graded, takeover-tagged moves onto the `ai_message` deck-mixer snapshot, render a post-session move-receipt with a "grounded vs stripped" column. Feeds new Earned competencies (Clean EQ Swap, Pitch Rider).
- **vibemix point:** extend the deck-mixer snapshot on `ai_message` rows; debrief window (8766); `skill_recognizer` live call-site in `coach_loop`.
- **Scores:** unlock 4 · feasibility 4 · moat 5 · wow 5 → **STRONG** (build AFTER #1/#3 are honest — a badge built on un-groundable "crossed the live value" semantics = a *graded* hallucination, a worse slop class).
- **Smallest proof:** persist `takeover_phase`+magnitude onto one snapshot, render one move row with a grounded/stripped flag derived from whether the citation resolved.

### #7 — Energy-arc receipt: colored-waveform debrief timeline `[STRONG]`
- **Unlocks:** A whole-set per-band colored energy ribbon + shareable receipt. Highest shareability in the round (the screenshot people post). Detail track = peak-pooled, overview = mean-of-peaks; RGB barycentric blend (bass→red, mid→green, air→blue) with brightness normalized OUT of hue into bar height.
- **Mixxx ref:** `analyzer/analyzerwaveform.cpp:18-20` (corners 600/4000), `:236-262` (peak-pool max-of-|x|), `waveform/renderers/waveformrendererrgb.cpp:159-182` (barycentric blend + normalize-by-max).
- **vibemix point:** NEW `band_energy_timeline(samples, sr, hop_s)` in `audio/band_features.py` (slides the existing windowed rFFT — no new dep) → `debrief/`.
- **Scores:** unlock 4 · feasibility 4 · moat 3 · wow 5 → **STRONG**.
- **Smallest proof:** timeline over a 30 s clip → (r,g,b,height) frames; throwaway HTML canvas; eyeball a breakdown reads blue-green, a drop reads red. **Adopt Mixxx's peak-pool + RGB INSIGHTS, not its 600/4000 corners — keep vibemix's existing band edges for codebase consistency.**

### #8 — RGB-synced mascot/pill: the overlay breathes the spectrum `[BUILD_NOW]`
- **Unlocks:** Near-free live win. The mascot/pill tints to the current spectral hue (breakdown cools blue, drop flares red), glow from the brightness channel. Non-verbal, always-honest, runs at idle (Invariant #5: idle is fine, it just reflects audio — can physically never show red in a bass-free passage).
- **vibemix point:** stream the already-instantaneous `band_energy_ratios` → RGB blend over `runtime/ws_bus` → `mascot.html` / pill (`runtime/suggestion.py`). No new audio path.
- **Scores:** unlock 3 · feasibility 5 · moat 3 · wow 4 → **BUILD_NOW** (cheap visible companion once #7's RGB helper exists; EMA the hue so it doesn't strobe).
- **Smallest proof:** feed live ratios → ws `{r,g,b}` → mascot tints; obvious breakdown cools the orb, no red in the bass-free section.

---

## 2. THE R-SLOP KILL (dedicated)

R-SLOP = the co-host claiming an EQ/fader move had an effect it cannot ground. The current guard is **more built than the packets first assumed** (verified): `live_claim_policy:2126` / `_supports_grounded_transition_verdict:2176` already cross-check measured per-deck audio-window deltas, two-active-lane gating, and trusted-source gating; `_has_unsupported_mixer_low_kill_claim:2412` reads the MIDI **knob tier**, not the audio. What's missing is the **expected-effect predictor** that turns correlation into causation. Five independent grounding axes, in order of grounding strength:

| Axis | What it computes | Grounding strength | Live or offline |
|---|---|---|---|
| **Loop/beatjump geometry** (#1) | Move effect from MIDI timestamp + beatgrid | **Strongest** — deterministic, zero inference | LIVE (boundaries sample-exact) |
| **EQ biquad band-delta** (#2) | Predicted per-band gain (`∫|H|²`) ∩ measured `sub+low` ratio | Strong — predicted ∩ measured, signed | LIVE (window-settled) |
| **Short-term LUFS** (#4) | K-weighted signed LU delta; disambiguates fader-level vs musical-content | Strong — perceptual, K-weighted | LIVE (3 s sliding) |
| **Crossfader curve** (#5) | Expected orientation-gain Δ dB from `xfade_gains` ∩ measured deck-lane delta | Medium-strong — predicted ∩ measured | LIVE |
| **Controller engagement** (#3) | Deliberate-grab vs jitter on controller timeline | Corroborating only | LIVE |

**The honest line on each:**
- **Computable live:** loop geometry (exact); EQ band-delta and LUFS delta (with a settling-lag window, below); crossfader expected-Δ sign; controller engagement classification.
- **NOT computable live (do not ship):** "crossed the DJ software's internal fader value" (#3) and "tempo nailed to within a cent" (14-bit, §4) — vibemix cannot read the host's control state and cannot resolve sub-BPM pitch from audio. Reframe #3 to the controller's own timeline; CUT the 14-bit precision claim.
- **Causation guard rail (applies to #2/#4/#5):** a band/LU delta correlated-in-time with a move is NOT proof the move CAUSED it (a natural breakdown can coincide). Keep the existing `dsp_delta_not_causal_proof` humility: the predicted∩measured agreement UPGRADES the gate from "knob tier says so" to "knob tier AND audio confirms direction"; it does NOT license a bare causal verdict. Frame as "the lows are gone now" (state), not "your kill removed the lows" (causation), unless move identity + timing + signed delta all align tightly.

**The settling-lag window (ship WITH #2, inseparable):** Mixxx ramps old↔new coefficients over ½ buffer (`enginefilteriir.h:240-288`, `cross_inc=4.0/bufferSize`) and the Bessel isolator adds quantized group delay (`enginefilterbessel4.cpp:33-46`, deeper corner = longer settle). So a TRUE kill's measured delta lags the move by ≥1 buffer. A naive single-frame compare REFUTES real kills — a NEW false-negative slop class. Compare over a short POST-move window via the existing `deck_audio_window_context:571`, with a `settle_hint(move)` so sub kills get a longer window than a high-shelf cut.

**Per-lane, not master-sum (applies to #2/#4/#5):** the live master is two decks summed (plus always-on passthrough); a kill on deck A is partly masked by deck B in the same band, and BlackHole bleed can fake per-lane energy. Predict on the lane, measure on the lane (`band_energy_ratios` already supports per-lane), and gate on the existing `source_trusted` flag — never assert off the master sum.

---

## 3. PER-ALGORITHM REIMPLEMENTATION BRIEFS

### A. eq-filter-biquad-dsp
- **Spec:** RBJ-cookbook biquads (Mixxx delegates derivation to fidlib, public-domain — reimplement the public cookbook). FullKill EQ corners 246/2484 Hz, log-geometric band centers, kill = low/high SHELVING at Q=0.4 + mid PEAKING at Q=0.9 (**per-band biquad TYPE dispatch — not one uniform shape**), `kKillGain=-23 dB`; true full-kill stacks a Bessel-4 isolator (`fLow=dLow-dMid`). Filter knob = serial LP→HP Butterworth Q=0.707. For grounding you don't run the filter on audio — you only need `|H(e^jω)|²` integrated over the four bands (a dot product against a precomputed magnitude grid, microseconds).
- **Torch-free:** YES — ~15 lines RBJ math per type + `np.exp`/complex division. No scipy/fidlib.
- **vibemix gap:** `intel/eq_move_model.py` ABSENT; guard validates MIDI tier, never the predicted spectral delta.
- **Mixxx ref:** `enginefilteriir.h:96-145,325-365,549-560`, `enginefilterbiquad1.cpp:12-89` (spec strings = exact cookbook filters), `biquadfullkilleqeffect.cpp:10-46,124-146`, `lvmixeqbase.h:16-17,71-187`, `filtereffect.cpp:9-64`.
- **Call:** **BUILD_NOW** (#2, with the settling window).

### B. waveform-rgb-bandsplit
- **Spec:** Two-stage. Analysis = 3 Bessel-4 IIR bands (600/4000 Hz, Bessel for flat group delay → time-aligned envelopes), `abs()`, **max-pool over stride** (peak envelope, NOT RMS), quantize uint8; detail @ 441 visual-samples/s, overview = mean-of-peaks. Render = barycentric RGB blend, hue normalized by max(r,g,b), brightness → bar height via `eqGain`.
- **Torch-free:** YES — vibemix's `band_features.py` rFFT band-sum is the cheaper route; slide it for a timeline. Do NOT port Mixxx's Bessel4 IIR coefficients (the one real GPL-derivation temptation) — use rFFT or a zero-phase numpy filter.
- **vibemix gap:** `band_energy_ratios` is instantaneous + RMS-like (no timeline, no peak-pool).
- **Mixxx ref:** `analyzer/analyzerwaveform.cpp:18-20,175-188,236-305`, `waveform/renderers/waveformrendererrgb.cpp:102-211`, `waveformsignalcolors.cpp:33-49`.
- **Call:** energy-arc **STRONG** (#7), RGB orb **BUILD_NOW** (#8), peak-pool onset fix **STRONG**.

### C. loudness-ebur128-replaygain
- **Spec:** K-weighting (2 cascaded biquads: ~1681 Hz high-shelf + ~38 Hz RLB high-pass) → 400 ms mean-square (75% overlap) → channel-weighted sum `−0.691 + 10log10(ΣG·z)` → two-stage gating (absolute −70 LUFS, relative −10 LU). ReplayGain-2 gain = `−18 − LUFS`. Live path = short-term (3 s, no gating) — easy mode. Headroom clamp `≤0.9` (−1 dB), 1.0 s smooth-fade, ramping apply.
- **Torch-free:** YES — biquad IIR + block mean-square + log + gates, ~60 lines. Source from BS.1770 (public), NOT Mixxx (which wraps MIT libebur128). Conformance-test the −3.01 LUFS tone.
- **vibemix gap:** live loudness = raw RMS EMA (`levels.py:39`, gain-confounded); offline = P80-RMS crest-fudge (`energy.py:321`, verified — a hand-rolled K-weighting approximation ripe for swap).
- **Mixxx ref:** `analyzer/analyzerebur128.cpp:12,37,83-85`, `enginepregain.cpp:16,96,118-119`.
- **Call:** short-term LUFS receipt **BUILD_NOW** (#4); offline integrated LUFS auto-gain **STRONG**; "Loudness Control" Earned node **STRONG** (LRA uses a DIFFERENT EBU Tech 3342 gating than the integrated 3341 gate — don't undercount it; a wrong dynamic-range score on a mastery gate is trust-breaking).

### D. loop-beatjump-performance
- **Spec:** `s_dBeatSizes` power-of-two lattice (1/32…64 beats); `findBeatloopSizeForLoop` reverse-maps frames→beat-size; `findQuantizedBeatloopStart` two-regime snap (nearest-whole-beat ≥1; sub-beat-slot <1); `slotBeatJump` = inside-loop→move else grid-exact seek; loop-roll = slip-mode stack (`m_activeLoopRolls`, unwind-to-top catch-up).
- **Torch-free:** YES — pure scalar beatgrid arithmetic, zero DSP, zero new deps (vibemix has the beatgrid from rekordbox ANLZ).
- **vibemix gap:** captures `loop_in`/`loop_out` as two bare buttons (`midi/state.py:398-400`), no beat-size, no significance (`event_detector.py:35` tuple lacks loop), no skill (6-skill manifest, verified). FLX4 profile has only loop_in/out notes 16/17 — no beatloop/roll/jump pads.
- **Mixxx ref:** `loopingcontrol.cpp:27,296,1290-1347,1416,1457,1499,1763,1823`, `beats.cpp:504`.
- **Call:** loop receipt **BUILD_NOW** (#1); R-SLOP-immune rule **STRONG** (#1's grounding); loop_performance skill / roll detector / snap coach / debrief lane **SPIKE**.
- **Two verified traps:** the `_record_move` 400 ms same-label dedup (`midi/state.py:226`) collapses a rapid roll-stack — route rolls through the no-dedup `_record_event` path; a 7th skill overlaps `phrasing_performance`'s C3 territory (carve, don't greenfield).

### E. controller-mapping-engine
- **Spec:** raw MIDI → 16-bit lookup key `(status<<8)|control` → multimap fan-out → MidiOption flag cascade (`computeValue`); Rot64 relative-encoder (`±1→/16` fine step, de-bias dead-step) vs vibemix's crude ±1.0; soft-takeover `willIgnore` truth table + 50 ms whip gate; 14-bit MSB/LSB pairing (`/128.0` quirk lands center on 64); XML mapping schema (option-name→flag table).
- **Torch-free:** YES — integer bit-twiddling + scalar floats, stdlib only.
- **vibemix gap:** `_compute_magnitude` flattens relative ticks to ±1.0 (`state.py:294`); no soft-takeover; no 14-bit; 11 profiles vs Mixxx's hundreds.
- **Mixxx ref:** `controllers/softtakeover.cpp:15-88`, `controllers/midi/midicontroller.cpp:390-595`, `midimessage.h:107-134`, `legacymidicontrollermappingfilehandler.cpp:76-105`.
- **Call:** crossing classifier **BUILD_NOW** (#3, reframed to passive-listener); Rot64/Diff decode **BUILD_NOW** (~15 lines, FLX4 golden path untouched); scratch alpha-beta integrator **SPIKE** (a different GPL surface, not yet sourced); XML transcoder **SPIKE** (scripted mappings carry GPL `.js` — only the non-scripted XML slice is cleanly harvestable; per-file license check, never bulk-vendor); 14-bit pairing **SPIKE→CUT** (un-groundable precision for a passive listener — increases slop surface).

### F. mixer-crossfader-curve
- **Spec:** 3-law crossfader (`getXfadeGains`): additive (`1-|x|^transform`, hot +6 dB center) vs constant-power (`pow(0.5,1/transform)` calibration → complete pair → unit-power normalize `g1²+g2²=1`) vs reverse; channel gain = pregain × dB-taper volume (`-20..0`) × orientation gain (L/C/R, center bypasses xfader); PFL/head-mix/split routing.
- **Torch-free:** YES — scalar `pow/log10/sqrt` + per-block ramped multiply.
- **vibemix gap:** `xfade.py` EXISTS (Apache, both curves) but is NOT wired into the live guard; the dB-taper fader law and pregain/headroom law are NOT yet ported; MiniDeck uses fixed cos/sin (`miniplayer.py:69`), no per-deck volume.
- **Mixxx ref:** `engine/enginexfader.cpp:11-84`, `control/controlbehavior.cpp:170-249`, `engine/enginepregain.cpp:14-162`, `engine/enginemixer.h:82-176`, `:387-435` (PFL).
- **Call:** wire `xfade.py` into guard + port 2 laws **BUILD_NOW** (#5); True-Curve Practice Mixer **STRONG**; Transition Anatomy debrief card **STRONG**; Gesture Discriminator / Curve-Literacy Earned / PFL detector **SPIKE** (gated on inputs the v1 hardware catalog doesn't supply — controller curve-mode lives in the DJ software, invisible; FLX4 `cue_a/b` are HOT-CUES not PFL toggles, verified).

---

## 4. GPL SAFETY LEDGER

- **Reimplement-from-spec only.** All math above is re-derived in vibemix's own code. Mixxx is cited `file:line` as method reference, never copied.
- **The standard is the source, not Mixxx, where one exists:** RBJ Audio-EQ-Cookbook (public), ITU-R BS.1770 / EBU R128 / Tech 3341/3342 (public), barycentric color blend (a formula). For loudness, source the standard even though Mixxx's actual DSP is MIT (libebur128) — avoids any same-shape-as-a-specific-impl argument.
- **Permissive libs Mixxx pulls (NOT GPL traps for our needs):** fidlib (public-domain, Jim Peters — biquad design), libebur128 (MIT — K-weighting), libreplaygain (RG 1.0, legacy path).
- **Tempting-but-FORBIDDEN copies — flagged:**
  - Mixxx's **Bessel4 IIR coefficients** (`enginefilterbessel4.cpp`) — do NOT port. Use rFFT band-sum or a zero-phase numpy filter (what `band_features.py` already does).
  - The **scratch alpha-beta integrator** (Mixxx engine/JS layer) — a separate GPL surface; SPIKE only, not yet sourced.
  - **Community Mixxx mappings** — the `.xml` is config data (per-file license check OK), but the paired `.js` scripts are GPL code and many controllers are useless without them. Harvest only the non-scripted XML slice; never bulk-vendor.
  - The waveform **draw loop** (`waveformrendererrgb.cpp`) — reimplement the blend formula, never paste the loop.
- **Existing precedent in-repo:** `audio/xfade.py` is already a correct Apache-2.0 clean-room of `enginexfader.cpp` ("facts re-derived, no source copied") — the model to follow for every new module.
- **Runtime deps:** zero new third-party deps across the entire round (numpy + existing rFFT). No PyInstaller spec edit. No torch / transformers / librosa. mutagen-style GPL-runtime-dep question does NOT arise here.

---

## 5. FULL IDEA TABLE

| Algorithm | Idea | unlock | feas | moat | wow | total | verdict |
|---|---|---|---|---|---|---|---|
| loop-beatjump | Loop/beatjump R-SLOP-immune rule (`loop_boundary_beatgrid_exact`) | 5 | 4 | 5 | 4 | 18 | **BUILD_NOW** |
| eq-biquad | Spectral Receipt — predicted band-delta grounds kill claim | 5 | 4 | 5 | 4 | 18 | **BUILD_NOW** |
| controller-map | Crossing Detector (passive-listener engagement classifier) | 5 | 5 | 5 | 4 | 19 | **BUILD_NOW** |
| loudness-lufs | Short-term LUFS "energy up" receipt + fader/build disambig | 5 | 4 | 5 | 4 | 18 | **BUILD_NOW** |
| mixer-xfader | Move-Effect Resolver — wire existing `xfade.py` + 2 laws into guard | 5 | 4 | 5 | 4 | 18 | **BUILD_NOW** |
| eq-biquad | Settling-lag verdict window (ships WITH Spectral Receipt) | 4 | 5 | 5 | 2 | 16 | **BUILD_NOW** |
| loop-beatjump | Loop Receipt (`findBeatloopSizeForLoop` → "4-bar loop") | 4 | 5 | 5 | 3 | 17 | **BUILD_NOW** |
| controller-map | Rot64/Diff velocity-aware encoder decode | 4 | 5 | 4 | 3 | 16 | **BUILD_NOW** |
| waveform-rgb | RGB-synced mascot/pill (live spectral hue) | 3 | 5 | 3 | 4 | 15 | **BUILD_NOW** |
| controller-map / all | Per-move MIDI receipt in debrief / Earned ledger | 4 | 4 | 5 | 5 | 18 | **STRONG** |
| waveform-rgb | Energy-arc colored-waveform debrief receipt | 4 | 4 | 3 | 5 | 16 | **STRONG** |
| waveform-rgb | Transient-true onset (peak-pool fixes LAYER/breakdown) | 4 | 4 | 4 | 3 | 15 | **STRONG** |
| loudness-lufs | True loudness-match auto-gain on next-suggestion pill | 4 | 4 | 4 | 3 | 15 | **STRONG** |
| loudness-lufs | Perceptual `lufs_curve` in MusicState + debrief arc | 3 | 4 | 3 | 3 | 13 | **STRONG** |
| loudness-lufs | "Loudness Control" Earned node (headroom + LRA) | 4 | 3 | 5 | 4 | 16 | **STRONG** |
| mixer-xfader | True-Curve Practice Mixer in MiniDeck | 3 | 5 | 3 | 3 | 14 | **STRONG** |
| mixer-xfader | Transition Anatomy debrief card (predicted curve vs measured) | 4 | 3 | 4 | 4 | 15 | **STRONG** |
| eq-biquad | "EQ Surgeon" Earned competency (spectral-demo mastery) | 4 | 3 | 5 | 5 | 17 | **STRONG** |
| eq-biquad | Debrief "Frequency Move Map" heat-strip | 3 | 4 | 4 | 4 | 15 | **STRONG** |
| eq-biquad | Master-only filter-sweep grounding (no controller) | 5 | 3 | 5 | 5 | 18 | **STRONG (spike detector)** |
| waveform-rgb | MIX_CLASH mud detector (two decks same band) | 4 | 3 | 4 | 4 | 15 | **STRONG (per-deck-routed only)** |
| loop-beatjump | `loop_performance` 7th Earned skill | 3 | 4 | 4 | 2 | 13 | **SPIKE (after rule lands)** |
| loop-beatjump | Roll-the-Drop detector (slip-stack live event) | 4 | 3 | 4 | 5 | 16 | **SPIKE (FLX4-only first)** |
| loop-beatjump | Beat-Slice Snap Coach (sub-beat offset) | 3 | 4 | 4 | 3 | 14 | **SPIKE** |
| loop-beatjump | Loop-Arc debrief lane | 3 | 4 | 4 | 3 | 14 | **SPIKE (last)** |
| controller-map | Mixxx-XML → vibemix-JSON catalog transcoder | 4 | 3 | 2 | 3 | 12 | **SPIKE (GPL/coverage gated)** |
| controller-map | Scratch alpha-beta jog integrator | 4 | 2 | 4 | 3 | 13 | **SPIKE (un-sourced GPL surface)** |
| mixer-xfader | Mixer Gesture Discriminator (cut/blend/ride) | 3 | 2 | 3 | 3 | 11 | **SPIKE (MIDI-source split only)** |
| mixer-xfader | Gain-Staging + Curve-Literacy Earned nodes | 3 | 3 | 4 | 3 | 13 | **SPIKE (gain-staging half only)** |
| mixer-xfader | PFL / headphone-cue detector | 4 | 2 | 4 | 3 | 13 | **SPIKE (trainer-side + suppression seam)** |
| eq-biquad | "Boost-then-clip" overcook warning | 3 | 3 | 4 | 3 | 13 | **SPIKE (precision-gated)** |
| controller-map | 14-bit high-res fader pairing | 2 | 4 | 2 | 2 | 10 | **SPIKE→CUT (un-groundable precision)** |
| loudness-lufs | Fader-vs-music LU attribution ("you" vs "the track") | 4 | 2 | 4 | 5 | 15 | **SPIKE (no fader dB law in profiles; ship boolean not fraction or CUT)** |

---

## BUILD ORDER (cross-algorithm, dependency-true)

1. **One PR — the R-SLOP grounding core (all BUILD_NOW, mostly one new module each):** `intel/eq_move_model.py` + settling window (#2), `audio/lufs.py` short-term meter (#4), wire `audio/xfade.py` + port dB-taper/pregain into `live_claim_policy` (#5), `state/loop_geometry.py` + the beatgrid-exact rule (#1), and the crossing-classifier reframed to the controller's own timeline (#3) + Rot64/Diff decode. Every atom enters through `apply_live_claim_guard` as evidence under the existing `dsp_delta_not_causal_proof` humility — gate the whole PR through `vibemix-grounding-review`.
2. **Cheap visible win, same session:** RGB orb (#8) — proves the live band signal end-to-end.
3. **Receipts (consume #1–#5):** per-move MIDI receipt (#6), energy-arc ribbon (#7), Transition Anatomy card.
4. **SPIKEs gated on a precision bar or a missing input:** master-only filter-sweep, MIX_CLASH, roll detector (FLX4-only, via `_record_event`), Earned competencies, LU attribution (boolean only), XML transcoder, overcook warning.

**Single biggest correction to the inbound packets:** vibemix is a **passive listener** with no read of the DJ software's internal control values. Every framing that assumes vibemix can compare a controller position against the host's "live value" (#3 "crossed the live value", 14-bit "to within a cent") is un-computable and must be reframed against what vibemix actually observes — the controller's own last position + the measured per-deck band-energy/LUFS delta. The crossing/curve/biquad math is the right tool; sell the un-computable version and you ship a confident-but-blind claim, the exact slop class this round exists to kill.
