# Phase 52: Audio Path + Feature Grounding - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Orchestrator-grounded — real-hardware + live-source findings injected directly (autonomous `fully`). Planning works against observed reality + the live `src/vibemix/` tree at HEAD, not guesses.

<domain>
## Phase Boundary

Prove the **live audio path** end-to-end on real hardware — master output → BlackHole 2ch @ 48 kHz → co-host, with levels registering in real time — AND make **every feature derived from that audio grounded** so neither the AI nor the UI ever sees a value that did not happen. Covers **BRINGUP-02** (audio path live + feature grounding) plus **GENRE-01/02** (the genre-detector hardening Kaan requested after psytrance misclassified).

**Out of this phase:** controller/MIDI (Phase 53), the reaction modes that *consume* these features (hype 54 / feedback 55), performance/mascot (56). This phase makes the **sensing layer** trustworthy.

**The canonical bug to close (success criterion):** out-of-range derived values must never reach the bus/UI — e.g. the live **BPM=200** read on a track that was nowhere near 200 (psytrance ~140 / the roadmap's ~129 example). The autocorr harmonic leak is the failure shape.
</domain>

<decisions>
## Implementation Decisions (Claude's discretion, autonomous `fully`)

- **BPM stabilization is ALREADY DONE — do NOT duplicate it.** The median-ring stabilizer landed in `fd25337` (`src/vibemix/state/refresh.py`: `_stabilize_bpm`, `_BPM_RING_MAXLEN=5`, ring wired into `_tick_once` at the 3 s estimate cadence). Verified live: it took the psytrance track's BPM max from 200→130, genre flicker 14→4 transitions, unknown frames 25→11. Phase 52 BUILDS ON this; it does not re-implement it. Remaining BPM work is only: confirm the out-of-range gate (`vibemix.audio.constants` filter + `validate_bpm`) plus the stabilizer together guarantee no out-of-range BPM reaches the bus, and add a regression that replays a real harmonic-leak trace and asserts the bus never sees > BPM_VALID_MAX.

- **Add a `psytrance` genre profile.** No psytrance/psy/goa profile exists today — only `disco, drum_and_bass, house, pop, techno`. Psytrance played under no/`techno` profile gets the wrong band-signature + phase thresholds. Add `src/vibemix/state/genre/profiles/psytrance.json` mirroring the locked schema (`profile.py`): bpm_range ~[138,150], heavy `sub`/`low` band signature (offbeat rolling bass), high `expected_crest_factor`, `vocal_likelihood: rare`, tuned build/breakdown/drop thresholds. Validate against the hand-written schema validator (no pydantic — Critical Constraint 6).

- **Add a grounded, DSP-based genre AUTO-DETECTOR (GENRE-01) — the core of Kaan's "genre detector da ekle".** Today the active profile is chosen by env at startup (`apply_genre_env`), never from the audio — so the system can't self-correct when the wrong genre is set. Add a continuous detector that picks the active profile from REAL audio features already computed each tick: **BPM band + band_signature match + crest_factor**, scored nearest-profile across the library. Anti-slop rules (non-negotiable, per [[project_anti_slop_grounded_gemini_thesis]]):
  - **Confidence gate + `unknown` fallback** — when no profile clears the threshold, emit `unknown`, NOT a guess. (Mirror the existing `derive_audible_track` `(unsure)`/`unknown` confidence pattern.)
  - **Hysteresis** — debounce profile switches so genre doesn't flicker bar-to-bar (mirror `HysteresisState` in `detector.py`).
  - **No new heavy deps, no CLAP/MERT/OpenL3** ([[feedback_no_clap_use_gemini_embedding]]) — pure numpy DSP on features already in the snapshot. A Gemini-based confirmation pass is a *possible later refinement*, not this phase's mechanism.
  - Env (`apply_genre_env`) stays as an explicit **override** — when the user pins a genre, auto-detection yields to it.

- **Genre is a grounded derived feature, exposed on the bus (GENRE-02).** Surface the detected genre + confidence on the snapshot/ws bus the same way phase/bpm/mood are, so the UI (and the mascot, Phase 56) can show "what's playing" honestly — `unknown` when unsure, never a hallucinated label.
</decisions>

<code_context>
## Existing Code Insights (verified live this session)

- **Audio path** (`src/vibemix/audio/`): `constants.py` — `INPUT_SR_NATIVE=48000` (BlackHole capture), `INPUT_SR_TARGET=16000` (LLM/feature rate). Resample 48k→16k via `scipy.signal.resample_poly` (`buffers.py` + `resample.py`). `errors.py` already documents the **BlackHole nominal-SR misconfig** trap: if Audio MIDI Setup has BlackHole at a non-48k rate, the stream silently succeeds and resamples wrong — a real bring-up footgun to assert against (BRINGUP-02 startup validation).
- **BPM**: `audio/features.py::estimate_bpm` (autocorr, lag 30–60 → BPM 100–200) is golden/pinned — do NOT touch. Stabilization is the ring in `refresh.py` (done). Out-of-range filtering: `validate_bpm` (profile half/double snap) + the `BPM_VALID_MIN/MAX` constants gate.
- **Genre module** (`src/vibemix/state/genre/`): `profile.py` (GenreProfile dataclass + JSON loader + `_ACTIVE_PROFILE` singleton, set by `apply_genre_env`), `detector.py` (`classify_phase_percentile` + `HysteresisState` — this is the PHASE detector, genre-profile-aware; there is **no genre auto-detector yet**), `bpm_validator.py` (half/double snap to `profile.bpm_range`), `crest_factor.py`, `vocal_detector.py`. Profiles in `profiles/*.json`.
- **State writer**: `refresh.py::state_refresh_loop` / `_tick_once` @10Hz is the single writer of `MusicState`; it already computes levels, bands, BPM (stabilized), phase. The genre detector slots in here, reading the features already on hand each tick.
- **Bus**: `runtime/ws_bus.py` broadcasts the snapshot (phase, bpm, mood, levels…). Adding `genre` + `genre_confidence` follows the existing field pattern. (Phase 51 just hardened this emitter — coordinate so the new field doesn't trip the empty-frame guard; it won't, the static keys remain.)
</code_context>

<specifics>
## Specific Ideas

- **Live-drive validation recipe** (orchestrator, no controller): play a known track into BlackHole 2ch, tap `ws://127.0.0.1:8765`, assert BPM lands in the track's real band and never exceeds BPM_VALID_MAX; assert detected genre matches the played genre (or `unknown`), never a wrong confident label.
- **Real-trace regression**: replay the captured psytrance harmonic-leak trace offline through `_tick_once`; assert the stabilized BPM stays in-band and the bus never emits >180.
- **Genre detector test**: feed synthetic feature vectors matching each profile's band_signature/bpm/crest → assert correct profile; feed an ambiguous/out-of-library vector → assert `unknown` (no false-confident pick).
</specifics>

<deferred>
## Deferred Ideas (Kaan-action — real hardware, autonomous carveout)

- The real **multi-genre live drive on Kaan's Mac** (his library, his ears) is the true grounding sign-off — does BPM/genre track reality across his actual sets? Engineering ships the detector + profiles + automated synthetic/real-trace tests + the live-tap recipe; the across-his-whole-library confirmation rides the live-drive / Kaan-ear surface (per [[project_phase_16_kaan_dj_testing]]).
- **Gemini-based genre confirmation** (multimodal audio → genre label as a periodic high-confidence cross-check of the DSP detector) is a possible v.next refinement — NOT this phase. This phase's detector is pure-DSP, grounded, zero-API-cost at 10Hz.
</deferred>
