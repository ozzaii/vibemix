# THE MIXXX GOLDMINE MAP
**Date: 2026-05-31** · What 20 years of GPL DJ DSP unlocks for vibemix, learn-from-spec.

> **GPL LEARN-FROM-SPEC DISCLAIMER.** Mixxx is GPL-2.0. Every item below is a clean-room **reimplementation from the algorithm** (the math, thresholds, state machine, signal flow) described in our own words — we **never copy, paste, or vendor Mixxx source**. Mixxx `file:line` citations are *method references* (where to read the technique), never code to lift. This is the same line vibemix already crossed cleanly in `state/transition_clock.py` and `learn/beatmatch_judge.py` ("ported clean-room, no GPL") — the standing ports are the proof the line is safe.

---

## 1. THE HEADLINE UNLOCKS

The single recurring theme across all six algorithms: **vibemix is one missing module away from grading real DJ mixing with zero external software.** The judges (`grade_beatmatch`), the deck (`MiniDeck`), the credit gate (`skill_recognizer`'s `BEATMATCH_GRADED` branch), the clock (`transition_clock`), and the curve (`xfade`) are ALL built, tested, and citation-gated — they have **no live producer wiring them together.** The top unlocks all converge on building that producer. This is Kaan's "OUR OWN MINI DJ / PRACTICE PLAYER" idea, and it scored at the top.

| # | Unlock | Learns from (Mixxx) | vibemix integration | u/f/m/w | Verdict | Smallest proof |
|---|--------|--------------------|--------------------|---------|---------|----------------|
| **H1** | **Practice-Deck Loop** — the producer that wires owned-deck → grade → cited `BEATMATCH_GRADED` → Mastered. Turns 3 orphan engines into the first *measured-mastery* competency. Closes **g14**. | `enginebuffer.cpp` per-block pipeline; `cuecontrol.cpp:1554` cue state machine | NEW `learn/practice_loop.py` driving `MiniDeck.render_block` (`miniplayer.py:130`) → `grade_beatmatch` (`beatmatch_judge.py:83`) → `grade_to_event_extra:145` + EvidenceRegistry citation → `skill_recognizer.recognize` (the `BEATMATCH_GRADED` branch is **live and waiting**) | 5/5/5/4 | **BUILD_NOW** | Drive deck to a known locked state, one tick, assert `BEATMATCH_GRADED(verdict="locked")` fires + citation registered + `recognize()` returns `["beatmatching"]`. Extend `test_judge_credits_beatmatch.py`. |
| **H2** | **`BeatGrid.from_anlz()`** — instant exact grid for Rekordbox users (the majority audience). Carries a TRUE downbeat (`beat_in_bar==1`) Mixxx's own analyzer admits it *can't* derive. | `beatutils.cpp:310` (Mixxx's "anchor is a temporary fix, not the real downbeat") | classmethod on `BeatGrid` (`grid.py:24`) reading `AnlzBeatGrid` (`library/anlz_ingest.py:44`): `BeatGrid(anchor_frame=times_s[0]*sr, bpm=bpms[0], sr)` | 4/5/4/3 | **BUILD_NOW** | Parse one real `.EXT`, build grid, assert `beat_distance` at a known downbeat ≈ 0.0. ~15 lines. |
| **H3** | **`grade_cue_placement` / Cue-Drop Judge** — the cueing twin of beatmatch. Scores cue placement-vs-beat and (with H1) drop-landing phase. The missing half of "Mastered cueing." | `cuecontrol.cpp:2358` `getTrackAt` (`<0.5` engine-sample tolerance), `:2373` quantize | NEW grader reusing `_phase_error` (`beatmatch_judge.py:37`) + `BeatGrid.closest_beat` (`grid.py:53`); placement = `|cue − closest_beat(cue)|` | 5/5/5/4 | **BUILD_NOW** | Cue snapped to beat scores ~1.0; 23 ms-off scores lower + emits "nudge left" sign. Placement-half needs NO deck — ships today. |
| **H4** | **Nudge Coach** — port `calcSyncAdjustment` as the *corrective controller*. Converts "you're 0.08 beat behind" into "nudge +0.7%". Three-band coach vocabulary (locked/drifting/trainwreck). | `bpmcontrol.cpp:572` (0.01 lock / 0.2 trainwreck / 0.7 gain / ±0.02 slew / ±0.05 cap) | extend `beatmatch_judge.py` with `sync_adjustment(error)`; feed `coach_loop` (`runtime/coach.py`) + practice-deck auto-sync | 4/5/4/4 | **BUILD_NOW** | Unit-test bands: err=0.005→≈1.0, err=0.05→`1+(-0.05·0.7)` clamped, err=0.3→trainwreck cap. ~30 lines numpy. |
| **H5** | **Silence floor + tag-conflict** — reuse vibemix's existing -60 dB helper to clamp every CUE-DETR anchor to `[first_sound, last_sound]`, emit confidence-1.0 intro/outro, flag impossible cues. Zero model cost. | `analyzersilence.cpp:11/27` (`abs ≥ 0.001`), `:74` `verifyFirstSound` | **REUSE** existing `audio/cues.py` (`track_cues_from_audio`, scar-20); clamp in `cue_engine.build_cue_anchors:76`; flag in `cue_agreement.py` | 3/5/4/2 | **BUILD_NOW** | 4 s silent lead-in → no auto-cue resolves before first_sound; intro anchor lands at it, confidence 1.0. |
| **H6** | **"The Blend Grade"** — transition-timing grader vs the ideal AutoDJ plan. Scores start-timing / blend-length / completion against `calculate_transition`. The g14 *transition* Mastered unlock. | `autodjprocessor.cpp:1363` (`min(intro,outro)`), `:1251` planner | NEW grader importing `state.transition_clock.calculate_transition` (already ported, `:192`) + `audio.xfade`; returns `BeatmatchGrade`-shaped verdict | 5/4/5/5 | **STRONG** | Grade a hand-crafted "early/short" fader trajectory vs a known plan; assert 3 sub-scores + abstain on unknown cues. |
| **H7** | **"Show Me The Fix" / snap-to-phase** — practice-deck demo button: snap deck B to nearest in-phase position so the learner *hears* locked, then retries. Kernel of a future automix engine. | `bpmcontrol.cpp:756` `getNearestPositionInPhase`, `:1134` `getPhaseOffset` | NEW `phase_align(grid_a, grid_b, pos_b)` in `audio/grid.py`; the cross-SR transpose collapses to 1.0 (we own both decks at one rate) | 4/4/4/5 | **STRONG** | `phase_align` returns `pos_b'` with `grid_b.beat_distance(pos_b') == grid_a.beat_distance(pos_a)` within tolerance; picks nearest. |
| **H8** | **`detect_key`** — torch-free audio→key producer for tag-less libraries. Decimate-8 → 36-bin/oct CQ chroma → 24-profile correlate → duration-weighted histogram argmax → ONE global key + confidence margin. | `analyzerqueenmarykey.cpp:34-76`, `keyutils.cpp:631` (histogram argmax) — **core DSP is qm-dsp, NOT in tree** | NEW producer in `library/` (sibling to `cue_detr.py`); emit classical spelling → existing `to_camelot()` (`harmonics.py:83`) does the rest, zero consumer changes | 5/3/4/4 | **STRONG (spike core first)** | numpy chroma + Krumhansl 24-profile argmax on 20 known-key tracks; need ~60%+ exact, must beat "always C". |

**Why H1 leads:** it is the only move that converts *shipped, test-enforced dead code* into a user-visible feature. `grade_beatmatch` has zero runtime callers (codegraph + `test_live_reality_pins.py:59` pin it as orphaned); the recognizer's credit branch is wired and waiting. One block-loop module lights the whole chain.

---

## 2. THE OWN-PLAYER VISION (Kaan's big idea, synthesized)

**What it is:** a vibemix-native 2-deck practice instrument — built on the existing `MiniDeck` (`audio/miniplayer.py:99`) — that the learning engine **fully observes**, so it can grade real beatmatching, cueing, harmonic, and transition mixing **with no Mixxx/Rekordbox/Serato open.** The student loads two of their own tracks, mixes on the DDJ-FLX4 (already MIDI-mapped) or on-screen, and every gesture is a *measured* fact, not an inference. This is the deepest expression of the vibemix moat: **we own the playhead and the grid**, so grading is sample-exact and structurally un-hallucinatable.

**Which Mixxx algorithms it needs, and their status in vibemix today:**

| Capability | Mixxx algorithm | vibemix status |
|---|---|---|
| Owned 2-deck playback + xfader | `enginebufferscalelinear.cpp` (linear interp) | **DONE** — `MiniDeck._do_scale_block` + equal-power xfader |
| Beatgrid from audio/metadata | `beatutils.cpp` Stage D + qm-dsp onset | **GAP** — `BeatGrid` type exists; **no producer** (H2 metadata path = trivial; H1-StageD = the math; audio onset = spike) |
| Static phase comparison (the grade) | `bpmcontrol.cpp:479` `shortestPercentageChange` + `synccontrol.cpp:290` octave fold | **DONE** — `grade_beatmatch`/`_phase_error`/`_octave_fold_multiplier`, all clean-room ported |
| Corrective controller (the coaching) | `bpmcontrol.cpp:572` `calcSyncAdjustment` | **GAP** — H4, ~30 lines |
| Beat-quantized cue + transport | `cuecontrol.cpp:1554` `cueCDJ`, `:2373` quantize, seek state machine | **GAP** — H3/Cue-Deck; needs `MiniDeck.seek()` (cursors are private, no write path today) |
| Keylock (tempo-without-pitch) | `enginebufferscalerubberband.cpp` (external GPL RubberBand) | **GAP** — SPIKE; WSOLA from paper (not in Mixxx tree) |
| Transition planner + curve | `autodjprocessor.cpp:1251` + `enginexfader.cpp:66` | **DONE** — `transition_clock.py` + `xfade.py`, faithful clean-room ports |
| Real-time auto-mix driver | `autodjprocessor.cpp:~860-882` (the ramp law) | **GAP** — "Ghost Line"; `step_progress` exists but isn't applied to a crossfader |

**What it unlocks for the LEARNING ENGINE:** the Earned skill-tree's "Mastered" rung — which requires a *cited live demonstration*, not just a lesson — becomes reachable for **beatmatching** (H1), **cueing** (H3), **harmonic mixing** (already credit-wired via the Vibe Judge; H8+grader enriches it with a *measured* owned-deck verdict), and **transition timing** (H6). Each is gated by Invariant #2 (citation) and Invariant #3 (abstain on weak evidence), so a wrong grade can't credit slop.

**Honest build order + effort:**
1. **`MiniDeck.seek()` + accessors** (~half day) — additive write-path to the private cursors; render_block untouched. *Prerequisite for cue/transport.*
2. **H2 `BeatGrid.from_anlz()`** (~half day) — unblocks g14 for Rekordbox users immediately.
3. **H1 practice_loop + H4 nudge** (~2-3 days) — the keystone + its coaching gradient. Ships with a minimal scripted/on-screen rate writer.
4. **H3 cue-deck + cue judge** (~2-3 days) — `cueCDJ` subset + `grade_cue_placement`. Note: TrackAt tolerance is `<0.5` **engine samples ≈ 0.25 source frame** — port the unit or ship a 2× bug.
5. **H7 snap-to-phase + H6 blend grade** (~2-3 days) — share the `getPhaseOffset` port; contrastive learning + transition mastery.
6. **Click-free rendering** (~1 hour bolt-on) — direction-flip + seek micro-crossfade via existing `xfade.py`, once seek/reverse exist.
7. **Keylock WSOLA** (SPIKE, multi-day, gamble) — the dual-scaler GATE is free and guarantees fallback to linear; the stretcher itself is invent-from-paper DSP that can warble on hardtechno. Defer; needs Kaan ear-verdict.
8. **Audio beatgrid detection (H1 Stage B/C)** (SPIKE, multi-week) — the no-metadata fallback. The onset DF is numpy-easy; the beat *tracker* (qm-dsp `TempoTrackV2`, not in tree) is the real cost.

**Total honest effort:** the *grounded core* (steps 1-5) is ~2 weeks of focused work because the hard math is already ported — it's wiring + small clean-room functions. The *audio-quality* and *no-metadata* tails (steps 7-8) are genuine multi-week DSP bets, correctly deferred behind spikes.

---

## 3. PER-ALGORITHM REIMPLEMENTATION BRIEFS

### 3.1 beatgrid-analyzer — **SPLIT: BUILD_NOW (metadata + Stage D math) / SPIKE (audio detection)**
**Spec:** Mixxx framing is 1024-sample window / 512-hop (~12 ms) @ 44.1k, DF_COMPLEXSD onset → qm-dsp tempo+DP beat track → then the **fully-readable** `beatutils.cpp` grid fitter: `retrieveConstRegions` (greedy two-pointer, `kMaxSecsPhaseError=0.025`, `kMaxSecsPhaseErrorSum=0.1`, `kMinRegionBeatCount=16`) → `makeConstBpm` (longest-region wins) → `roundBpmWithinRange` (integer → half<85 → 2/3>127 → 1/12 ladder) → `adjustPhase` (average in-tolerance offsets, **guard divide-by-zero**). Output: `(sampleRate, anchorFrame, bpm)` — exactly `BeatGrid.__init__`.
**Torch-free:** YES. Stage D is pure numpy/scalar (~430 readable lines). Onset DF is numpy `rfft`. The beat *tracker* is the hard part — and it's **NOT in Mixxx** (external qm-dsp); reimplement from the complex-spectral-difference + DP literature, or ship an ONNX beat tracker (the MIT **Beat-This** model fits the `cue_detr.py` ONNX pattern).
**Gap filled:** g14's missing `BeatGrid` *producer*. The consumer (`grade_beatmatch`) and credit gate are wired; the source is the only hole.
**Mixxx ref:** `track/beatutils.cpp:51-137, 140-322, 337-382, 403-429`; `analyzer/plugins/analyzerqueenmarybeats.cpp:21-110`. **vibemix:** `audio/grid.py:24`, NEW `audio/beatgrid_detect.py`.
**Call:** Ship `BeatGrid.from_anlz()` (H2) + the Stage-D+rounding+adjustPhase math bundle now (validate on synthetic jittered metronomes). Spike the audio onset/tracker separately.

### 3.2 sync-engine — **DONE (static half) / BUILD_NOW (corrective controller)**
**Spec:** beat-distance `∈[0,1)` modular phase, signed error `(target−cur+0.5)%1−0.5`; `calcSyncAdjustment` banded corrector (0.01 lock / 0.2 trainwreck / 0.7 gain / ±0.02 slew / ±0.05 cap); √2 octave fold; leader/follower fan-out (same single-writer discipline as Invariant #1).
**Torch-free:** YES, and the static-comparison half is **already a faithful tested port** (`_phase_error`, `_octave_fold_multiplier`).
**Gap filled:** the *corrective* controller (H4 nudge coach) and the live producer (H1). Octave fold also unblocks `next_suggestion` rejecting 174↔87 pairings (currently a real bug — BPM filter at `next_suggestion.py:163` has no fold).
**Mixxx ref:** `engine/controls/bpmcontrol.cpp:479/514/572/650/756/1134`; `engine/sync/synccontrol.cpp:290`. **vibemix:** `learn/beatmatch_judge.py:37/83`, `library/next_suggestion.py`, `state/transition_clock.py`.
**Call:** BUILD_NOW the controller; STRONG for snap-to-phase (H7) and octave-aware mixability; SPIKE the predictive live countdown (needs two live grids — abstain otherwise).

### 3.3 cue-hotcue-intro-outro — **BUILD_NOW (silence floor reuse + cue judge) / STRONG (cue deck)**
**Spec:** `analyzersilence.cpp` = raw per-sample `abs ≥ 0.001` (-60 dB), no smoothing → first/last audible frame → intro(start=firstSound)/outro(end=lastSound)/main cue. `cuecontrol.cpp` quantize = `findClosestBeat` (never mutates the stored cue — same single-writer rule), `getTrackAt` 3-state (`<0.5` engine samples ≈ **0.25 source frame**), `cueCDJ` button state machine.
**Torch-free:** YES, trivially. **CORRECTION:** the -60 dB helper already EXISTS in vibemix (`audio/cues.py track_cues_from_audio`) — reuse, don't re-derive.
**Gap filled:** deterministic confidence floor for CUE-DETR (clamp anchors, suppress drops-in-silence); ground-truth leg for `cue_agreement`; quantize-to-beat + TrackAt for the practice deck.
**Mixxx ref:** `analyzer/analyzersilence.cpp:11/27/74`; `engine/controls/cuecontrol.cpp:1554/2358/2373/2398`. **vibemix:** `audio/cues.py`, `library/cue_engine.py:76`, `cue_agreement.py`, NEW `audio/cue_deck.py` (or extend `miniplayer.py`).
**Call:** BUILD_NOW H5 (silence clamp + impossible-cue flag, shared helper) and `grade_cue_placement` (H3, no deck needed). STRONG for the Cue-Deck. **CUE_HIT live event is practice-deck-ONLY** — firing it on the BlackHole master-audio path (no cue position in evidence) is the #1 ungrounded-slop release blocker.

### 3.4 autodj-transition — **DONE (planner/curve) / BUILD_NOW (fade_now + ramp driver) / STRONG (blend grade)**
**Spec:** 2-deck state machine off the fromDeck's normalized play-position; `calculateTransition` freezes a plan (`fadeBegin/fadeEnd/toStart`) in `ADJ_IDLE`; 5 TransitionModes; the live ramp law (`transitionStep = progress − prev`, `if step>0`, `adjustment = (target−cur)/(1−prevProgress)·step` — driven by **track-position delta, not wall-clock**); `fadeNow` = the plan evaluated at "now" (double-clamped `min(intro,outro)`, `fromRemaining`, `toRemaining/2` — **no 0.1s floor**, the gate is `kMinimumTrackDurationSec=0.2` eligibility).
**Torch-free:** YES — scalar float, no DSP. **Already ported** as `transition_clock.py` + `xfade.py`.
**Gap filled:** the real-time crossfader-ramp driver ("Ghost Line" — makes MiniDeck genuinely auto-mix), `fade_now`, and the transition-timing grader (H6).
**Mixxx ref:** `library/autodj/autodjprocessor.cpp:203/1251/1363/~860-882`; `enginexfader.cpp:66-77`. **vibemix:** `state/transition_clock.py:192`, `audio/miniplayer.py` (add `drive_automix`), `runtime/automix_demo.py:73`, `runtime/coach.py`.
**Call:** BUILD_NOW the ramp driver + `fade_now` (pure arithmetic). STRONG the Blend Grade (H6) + live Outro Coach (gated, abstain-on-no-cue). SPIKE the narrated "Show Your Receipt" — it puts the co-host's mouth on output; grounding-review every line.

### 3.5 enginebuffer-timestretch — **STRONG (transport) / BUILD_NOW (keystone loop) / SPIKE (keylock)**
**Spec:** per-block pipeline (read SR → drain sync → seek → `calculateSpeed` collapse → dual-scaler select → scale → advance fractional cursor → run controls). Dual-scaler GATE (force linear if `|speed|>1.9`, `<0.1`, scratching, or pitch within 1 cent `kLinearScalerElipsis`). `calculateSpeed` precedence; `SEEK_PHASE` = snap to nearest beat; `cueCDJ` transport; direction-flip + seek micro-crossfades.
**Torch-free:** linear scaler/xfader/transport/seek/cue/rate-collapse = pure numpy (first three already ported). **Keylock is the catch:** the WSOLA core is **external SoundTouch (NOT in Mixxx tree)** — reimplement from the 1993 Verhelst-Roelands WSOLA paper, not Mixxx. The dual-scaler GATE is copy-the-logic clean and guarantees graceful fallback.
**Gap filled:** the keystone practice loop (same as H1), beat-quantized transport, honest rate mapping for FLX4 gestures, click-free scrub/back-cue.
**Mixxx ref:** `engine/enginebuffer.cpp:947-1007/1355-1431/1044-1169/480-505`; `enginebufferscalerubberband.cpp:33-95`; `ratecontrol.cpp:400-516/294`; `cuecontrol.cpp:1554-1619`. **vibemix:** `audio/miniplayer.py:130`, `audio/grid.py:53`, `learn/beatmatch_judge.py`, NEW `audio/wsola.py`/`audio/rate_control.py`/`learn/practice_runtime.py`.
**Call:** BUILD_NOW the loop (the milestone-mover) + transport. STRONG `calculate_speed` (port ONLY slider+temp+jog+reverse+scratch, **drop** sync/vinyl branches). SPIKE WSOLA — prove it holds clean over ±8% on 3 genres incl. hardtechno before scheduling; Kaan ear-verdict gates it.

### 3.6 key-detection — **STRONG (spike DSP core first) / BUILD_NOW (confidence margin + tagged harmonic grader)**
**Spec:** decimate-8 → 36-bin/oct constant-Q chroma (440Hz ref) → hpcp smooth ≈10 → 24-profile (Krumhansl-style) correlate-argmax per window → median-filter ≈10 → run-length segment → **duration-weighted histogram argmax** = ONE global key. The `KeyChangeList` timeline is real intermediate state. **Mixxx ships NO confidence** (discards the histogram margin) — reclaiming it as `key_confidence` is a vibemix ORIGINAL and the honest-unknown gate (Invariant #3).
**Torch-free:** YES (numpy CQ kernel + 24×12 profile matrix), no model download. **CATCH:** the core math (`GetKeyMode`) is qm-dsp, NOT in the tree — reimplement from Krumhansl-Schmuckler/qm-dsp papers, which raises accuracy risk: a confidently-wrong detector poisons every harmonic suggestion.
**Gap filled:** source-key for tag-less libraries (the entire Camelot stack dies on untagged audio today); a measured owned-deck harmonic grade; tag-vs-audio conflict flag.
**Mixxx ref:** `analyzer/plugins/analyzerqueenmarykey.cpp:34-76`; `track/keyutils.cpp:631-660/315-356`; `buffering_utils.cpp:37-82`. **vibemix:** `state/harmonics.py:83/278`, `state/event_detector.py:407`, NEW `library/detect_key.py`, `library/audio_decode.py:45`.
**Call:** SPIKE the DSP core on 20 known-key tracks FIRST (de-risks the whole cluster). If it clears ~60% exact: ship `detect_key` + confidence margin together (never one without the other). BUILD_NOW the tagged-track harmonic grader (no `detect_key` needed). **CUT** the "Source-Key Mastery" competency as framed — `harmonic_mixing`→Mastered is **already wired** via the Vibe Judge (`skill_recognizer.py:96-98`). SPIKE the timeline warning + tag-conflict (both invert slop risk onto the live wire; gate behind calibrated confidence).

---

## 4. GPL SAFETY LEDGER

**Every item is reimplement-from-spec. Nothing is copied.** The standing clean-room ports (`transition_clock.py`, `xfade.py`, `beatmatch_judge.py`) are the precedent that this is safe.

**Tempting-but-forbidden to copy (describe the math, never paste the C++):**
- `beatutils.cpp` grid fitter (D1-D5) — fully readable, ~430 lines, *exactly* what we want. Read it for the algorithm; type your own numpy. The `adjustPhase` divide-by-`offsetAdjustCount` has no zero-guard in Mixxx (it relies on a DEBUG_ASSERT) — **add the guard** in the clean-room version or NaN poisons every grade.
- `calcSyncAdjustment` banded corrector, `cueCDJ` state machine, `calculateTransition` modes, `calculateGlobalKey` histogram — all short numeric algorithms (math, not authored expression). Clean-room from the described thresholds.

**The pieces that are NOT even in the Mixxx checkout (so there's nothing to accidentally copy — reimplement from published papers):**
- **Beat onset DF + tempo/beat tracker** → external **qm-dsp** (GPL). Alternative: complex-spectral-difference DF from the QM-DSP literature, or the **MIT-licensed Beat-This ONNX** beat tracker (fits the `cue_detr.py` ONNX pattern, stays torch-free).
- **Time-stretch / keylock** → external **RubberBand (GPL/commercial dual)** + **SoundTouch (LGPL)**. Alternative: our own **WSOLA from the 1993 Verhelst-Roelands paper** (pure numpy, gated to the ±6-10% band by Mixxx's dual-scaler logic) or numpy phase-vocoder. Do NOT vendor RubberBand.
- **Key-detection core (`GetKeyMode`)** → external **qm-dsp** (GPL). Alternative: **Krumhansl-Schmuckler** key-profile correlation over a numpy constant-Q chroma — the published method, never qm-dsp source. The readable Mixxx wrapper constants (`analyzerqueenmarykey.cpp:34-52`) + open-key ring (`keyutils.cpp:315-356`) are a *cross-check* of vibemix's existing Camelot table, not code to lift.

**Torch posture:** NONE of the BUILD_NOW items need torch/transformers/librosa. The only ML touchpoints are the *optional* ONNX beat tracker (spike) — consistent with the existing CUE-DETR ONNX path. Everything else is numpy + the existing PyAV/FFmpeg decode.

---

## 5. FULL IDEA TABLE

| Algorithm | Idea | u | f | m | w | total | Verdict |
|---|---|---|---|---|---|---|---|
| beatgrid | `detect_beatgrid` full audio→grid producer | 5 | 2 | 5 | 4 | 16 | SPIKE (split: Stage D now, B/C separately) |
| beatgrid | `BeatGrid.from_anlz()` metadata shortcut | 4 | 5 | 4 | 3 | 16 | **BUILD_NOW** |
| beatgrid | Grid-confidence gate (Mixxx implicit SM) | 3 | 5 | 5 | 2 | 15 | STRONG (ship with B/C) |
| beatgrid | EDM-aware BPM rounding ladder | 2 | 5 | 3 | 2 | 12 | STRONG (inside Stage D) |
| beatgrid | Live const-region BPM-stability check | 3 | 3 | 4 | 3 | 13 | SPIKE |
| beatgrid | `adjustPhase` anchor refine (guard /0) | 3 | 5 | 4 | 2 | 14 | STRONG (inside Stage D) |
| sync | Practice Deck Loop (the producer) | 5 | 5 | 5 | 4 | 19 | **BUILD_NOW** |
| sync | Nudge Coach (`calcSyncAdjustment`) | 4 | 5 | 4 | 4 | 17 | **BUILD_NOW** |
| sync | "Show Me The Fix" snap-to-phase | 4 | 4 | 4 | 5 | 17 | STRONG |
| sync | Octave-aware mixability (next_suggestion) | 3 | 5 | 3 | 3 | 14 | STRONG |
| sync | "Call It Before It Lands" live countdown | 4 | 3 | 4 | 5 | 16 | SPIKE (needs 2 live grids; abstain) |
| sync | Variable-tempo grid bridge (marker bisect) | 4 | 4 | 4 | 3 | 15 | STRONG (sequence later) |
| cue | The Practice Deck (`cue_deck.py`) | 5 | 4 | 5 | 4 | 18 | STRONG (keystone instrument) |
| cue | Cue-Drop Judge (`grade_cue_placement`) | 5 | 5 | 5 | 4 | 19 | **BUILD_NOW** (placement half today) |
| cue | Silence-bounded confidence floor (REUSE) | 3 | 5 | 4 | 2 | 14 | **BUILD_NOW** |
| cue | CUE_HIT live event | 4 | 3 | 5 | 4 | 16 | STRONG (practice-deck ONLY) |
| cue | Cue-agreement ground-truth leg | 3 | 5 | 4 | 3 | 15 | **BUILD_NOW** |
| cue | Quantize-coach nudge hint | 2 | 5 | 3 | 3 | 13 | SPIKE (fold into coach, not a module) |
| autodj | "Ghost Line" real-time auto-mix driver | 5 | 5 | 5 | 4 | 19 | **BUILD_NOW** |
| autodj | "The Blend Grade" transition-timing grader | 5 | 4 | 5 | 5 | 19 | STRONG |
| autodj | "Fade Now" live-from-here primitive | 4 | 5 | 4 | 3 | 16 | **BUILD_NOW** |
| autodj | "Show Your Receipt" narrated cited tape | 3 | 3 | 4 | 5 | 15 | SPIKE (grounding-review every line) |
| autodj | "Outro Coach" live transition tap | 4 | 3 | 5 | 4 | 16 | STRONG (live, gated, last) |
| enginebuffer | `practice_runtime.py` keystone loop | 5 | 4 | 5 | 4 | 18 | **BUILD_NOW** |
| enginebuffer | Beat-quantized cue/SEEK_PHASE transport | 4 | 5 | 4 | 3 | 16 | STRONG (needs `MiniDeck.seek()`) |
| enginebuffer | `calculate_speed()` FLX4 rate collapse | 3 | 4 | 3 | 2 | 12 | STRONG (after loop) |
| enginebuffer | Keylock WSOLA tempo-without-pitch | 4 | 2 | 3 | 4 | 13 | SPIKE (not in Mixxx; Kaan ear) |
| enginebuffer | Click-free direction-flip/seek crossfade | 2 | 5 | 2 | 2 | 11 | BUILD_NOW-but-LAST (1h bolt-on) |
| key | `detect_key` audio→key producer | 5 | 3 | 4 | 4 | 16 | STRONG (spike core first) |
| key | Per-segment key timeline warning | 4 | 3 | 5 | 5 | 17 | SPIKE (gated on segment accuracy) |
| key | `grade_harmonic_blend` (tagged) | 4 | 5 | 5 | 4 | 18 | **BUILD_NOW** |
| key | "Source-Key Mastery" competency | 2 | 4 | 3 | 3 | 12 | **CUT** (already wired via Vibe Judge) |
| key | Tag-vs-audio key-conflict flag | 3 | 3 | 4 | 4 | 14 | SPIKE (downstream of detect_key+conf) |
| key | Confidence from histogram margin | 4 | 5 | 5 | 3 | 17 | **BUILD_NOW** (ship inside detect_key) |

**THE ONE THAT MATTERS:** the Practice-Deck Loop (sync H1 / enginebuffer keystone, total 18-19). Three orphaned subsystems — `MiniDeck`, `grade_beatmatch`, the recognizer's `BEATMATCH_GRADED` branch — are built, tested, and citation-gated with no driver. One block-loop module turns them into the first *measured-mastery* competency in the Earned tree and closes g14. Everything else in the top tier (`from_anlz`, nudge coach, cue judge, ghost-line driver, silence floor) is its scaffolding or near-free reuse of code already in the tree. Build the closed mastery loop first.
