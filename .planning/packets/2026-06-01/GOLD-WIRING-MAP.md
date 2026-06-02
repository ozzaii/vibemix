# GOLD-WIRING-MAP — Turning the vibemix Narrator into a Coach

> The founder's decision doc. Workflow `wf_03a2590e` (8 agents, codegraph-verified). Raw: `_gold-wiring-recovery-raw-wf_03a2590e.json`. HEAD `ce909a87`. READ-ONLY — every claim file:line / codegraph-verified.
> Answers "where is the intelligence and how do we connect it?" Confirms the founder's thesis: the DJ intelligence was clean-room-built + unit-tested but **orphaned to tests/demos/the library path**, never reaching the live coach prompt. So the live brain narrates instead of coaching.

---

## 1. THE ONE-LINE TRUTH
The live brain eats **raw band ratios + a 0-127 xfader bucket + MIDI move labels**; the intelligence that would let it *coach* (move physics, spectral causality, loudness, beatmatch, transition geometry) is **built and tested but ORPHANED**. Connect in order: **(1) the EQ-move physics keystone + its spectral receipt** (the one engine that doesn't exist yet — the named R-SLOP killer), **(2) finish the already-live Vibe Judge so it speaks on a master-only rig**, **(3) wire the orphaned scorers/grader that already run elsewhere.**

## 2. WHAT THE BRAIN EATS TODAY (the crude menu)
Assembled in `dj_cohost.py::_build_attached_audio_context_clause:383` from `state/coach.py` render fns. The honest input:
- **RICH (real measured):** `hearing[rms sub low mid high bpm]` (`coach.py:371`), tick deltas `audio_delta` (`deck_context.py:1794`), `decks[A/B camelot]+blend` harmonic relation (`coach.py:418`, the ONE well-wired intelligence join), phase/arc history.
- **CRUDE (why it narrates):**
  - `mixer_context` deck EQ = **0-127 MIDI → text tiers** (`killed/cut/flat/boost`, `deck_context.py:2146/3577`) — a name of where the *knob sits*, never a measured acoustic effect.
  - `recent_moves[8s]` = **bare MIDI labels** ("killed lows on A") with zero attached audio consequence (`coach.py:512`).
  - `move_effect_context` / `audio_delta` stamped **`rule=dsp_delta_not_causal_proof`** (`deck_context.py:2098/325/338`) — the brain may *correlate* but is **forbidden to attribute**; `caused_by_move=true` is in `_DECK_AUDIO_DELTA_CONTEXT_FORBIDDEN_ATOMS` (`:330`). `apply_live_claim_guard:2313` strips any causal verdict because **no producer licenses one**.
  - `deck_audio_context: source=global_mix isolated_decks=false` — per-deck stems need the default-off 4-ch path, so it can't separate deck A's top end from B's.

**Net:** the brain gets *what the room sounds like* + *what knob moved (as a number)* but never *the physics that connects move→sound*. The single missing ingredient that gates "coach" mode is **measured move→acoustic-effect attribution.**

## 3. THE WIRING MAP (ranked by narrator→coach leverage)

**CARD 1 — EQ-Move Physics Resolver `intel/eq_move_model.py` ★ KEYSTONE**
- **STATUS: BUILD** (`grep mixer_physics|expected_move_effect src/` = NOT-FOUND; only PROPOSED in `.planning/packets/2026-06-01/recovered/wf_d9ddbeed-f5f__ALT1__mixxx-eq-filter-dsp...md`).
- **REPLACES:** the controller-tier-only guard `_has_unsupported_mixer_low_kill_claim` (`deck_context.py:2585`) — a MIDI label with zero audio connection, and `return False` (dead) on a master-only rig.
- **UNLOCKS:** *"your low-kill actually thinned the bass — sub+low cratered 18 dB"* **and refuses** it on a breakdown where the bass wasn't there. The single move that flips REFUSE→CLAIM.
- **WIRING:** pure `predicted_band_gains(move, fs) -> {sub,low,mid,high} dB` (clean-room RBJ cookbook, Mixxx corners 246/2484 Hz, kill −23 dB) → compare to measured post-move delta inside `apply_live_claim_guard` (`deck_context.py:2342`).
- **CLASS: BUILD** (~1d, pure numpy, no dep) · **LEVERAGE: HIGHEST** · **DEPS:** none new (measurement side `band_features.band_energy_ratios:30` + `render_audio_delta_items:1794` already present).

**CARD 2 — Spectral / Loudness Receipt (measurement half of the keystone)**
- **STATUS: FINISH** — band ratios + per-deck features exist (`deck_capture.py:307`) but carry **no LUFS, no centroid**. Only loudness code `library/energy.py::_loudness_dbfs:321` is library-only (not the coach loop).
- **UNLOCKS:** a citable loudness/brightness receipt the EQ verdict cites + energy-arc coaching.
- **CLASS: FINISH** (~0.5d) · **LEVERAGE: HIGH (keystone-paired)** · Card 1 consumes it.

**CARD 3 — Vibe Judge: full-rig → master-only**
- **STATUS: FINISH — already wired live.** `coach_loop` (`runtime/coach.py:405`) → `_run_live_judge:327` → `judge_voice`. The ONE gold engine reaching the live brain today — but **abstains** on master-only rigs (`deck_signal.py:37` `routing_enabled=False`; needs 2 active decks `deck_context.py:2241`).
- **UNLOCKS:** transition quality verdicts on the rig people actually run.
- **WIRING:** Card 1's spectral-causality lets a *single master* frame infer the executed mix (filter-sweep signature) instead of requiring two routed lanes. **Depends on Card 1.**
- **CLASS: FINISH** (~1d) · **LEVERAGE: HIGH.**

**CARD 4 — Transition Scorer `intel/transition_scorer.py`**
- **STATUS: WIRE (orphaned)** — runs in `library/next_suggestion`, `toolset`, `sequencer`, `move_grade`, `context_compiler` — **none in `coach.py`.** Pure + present.
- **UNLOCKS:** "9A→4A clean harmonic jump, phrases aligned" as a *live* line, not just a next-track pick.
- **CLASS: WIRE** (~0.5d) · **LEVERAGE: MEDIUM** · DEPS: trusted two-deck state (post-Card 3).

**CARD 5 — Beatmatch Grader `learn/beatmatch_judge.py::grade_beatmatch`**
- **STATUS: WIRE engine + BUILD live feed** — `grade_beatmatch:83` callers = **6, ALL tests**; `practice_loop.py` NOT-FOUND. Grader is pure; the **live per-deck beatgrid is the gap.**
- **UNLOCKS:** "you're an eighth-beat behind, nudge up" — the most-requested DJ coaching line.
- **CLASS: WIRE+BUILD** (~1.5d, grid is the cost) · **LEVERAGE: MEDIUM-HIGH.**

**CARD 6 — Transition planner `transition_clock.calculate_transition`**
- **STATUS: WIRE (orphaned to a DEMO)** — 1 caller `build_automix_reel` (`automix_demo.py:73`). `move_grade.grade_move` → only the pill (`pill/index.ts:1955`).
- **UNLOCKS:** "you've got 16 bars to bring B in."
- **CLASS: WIRE** · **LEVERAGE: LOW-MEDIUM** · DEPS: Cards 1+3.

*(Screen-vision: wired but `VIBEMIX_DECK_VISION` default-off — out of scope for the audio-coach unlock.)*

## 4. BUILD ORDER
| # | Step | Class | Effort | Promise-safe? |
|---|------|-------|--------|---------------|
| 1 | **`intel/eq_move_model.py`** — clean-room RBJ `predicted_band_gains` (Card 1) | **BUILD** | ~1d | NEW (but spec fully written) |
| 2 | Spectral/LUFS receipt in `_deck_frame_features` + `render_audio_delta_items` (Card 2) | FINISH | ~0.5d | finishing built code |
| 3 | Wire 1+2 into `apply_live_claim_guard:2342` — verdict = move ∧ predicted matches measured | FINISH | ~0.5d | finishing built code |
| 4 | Master-only Judge — single-stream mix inference (Card 3) | FINISH | ~1d | finishing live code |
| 5 | Wire `transition_scorer` into coach prompt (Card 4) | WIRE | ~0.5d | wiring existing code |
| 6 | Beatmatch live grid + `grade_beatmatch` call site (Card 5) | WIRE+BUILD | ~1.5d | mixed |

Steps 2–5 = *finishing/wiring already-built, tested code* (Francesco-promise-safe). Only Step 1 + the Step 6 beatgrid are new BUILD; Step 1's algorithm is fully specified in the ALT1 packet.

## 5. THE KEYSTONE SPEC (ready for Codex)
**New `src/vibemix/intel/eq_move_model.py`** (intel = import-light, correct home).
- **Inputs:** `move: str` (MIX_MOVE vocab from `event_detector.py`: `killed / _low: / _mid: / _hi: / _filter: / xfader`), `fs: int`.
- **Core:** clean-room RBJ cookbook coefficients (Mixxx-matched, GPL never vendored): `LO_MID_CORNER=246`, `MID_HI_CORNER=2484`, `LOW_KILL_FC=99`, `HIGH_KILL_FC=3700`, `KILL_GAIN_DB=-23`, `Q_KILL=0.9 / Q_SHELF=0.4 / Q_BOOST=0.3`. Magnitude `|H(e^jω)|` via `polyval(b,z)/polyval(a,z)` (pure numpy, no scipy). Predicted per-band gain = `∫|H|²` over each `band_features._BANDS` window.
- **Output atom:** `predicted_band_gains('low_kill', fs) -> {'sub':-23,'low':-21,'mid':-0.5,'high':0.0}` dB → citation `[move_effect: A_low_kill -> sub -18dB ✓measured -16dB]`.
- **Call site:** `state/deck_context.py::apply_live_claim_guard:2342`, beside `_has_unsupported_mixer_low_kill_claim`. Compare predicted-direction delta to **measured** `render_audio_delta_items`/`band_energy_ratios` delta **over the post-move window** (`deck_audio_window_context:571`) — NOT the instant frame (coefficient-ramp + group delay lag the move ~1 buffer). Match → license the claim; no band move → REFUTE to `LIVE_MOVE_EFFECT_HELD_REPLY`.
- **Guard upgrade:** flip `rule=deck_audio_delta_not_causal_proof` (`:325`) to a *grounded causal verdict* when prediction matches measurement — the first time the live brain may assert cause.

## 6. HONEST BOTTOM LINE
**~70% of the missing intelligence is recoverable by WIRING/FINISHING already-built, unit-tested code.** The Vibe Judge is already in `coach_loop` (just abstains); `transition_scorer`/`move_grade`/`grade_beatmatch`/`calculate_transition` all run *somewhere* (library/pill/demo/tests) and need a coach-loop call site, not invention. **~30% is genuine new BUILD**, concentrated in two places: the **`eq_move_model.py` keystone** (spec fully written) and the **live per-deck beatgrid feed**.

**THE SINGLE HIGHEST-LEVERAGE FIRST MOVE:** build `intel/eq_move_model.py` and wire it into `apply_live_claim_guard:2342`. It's the only engine that converts the live guard from REFUSE-all-causal-claims into licensed cause-and-effect ("your EQ move thinned the top end"), it works on the **master-only rig everyone actually runs**, and it unlocks the master-only Vibe Judge (Card 3). **That is the line between narrator and coach.**
