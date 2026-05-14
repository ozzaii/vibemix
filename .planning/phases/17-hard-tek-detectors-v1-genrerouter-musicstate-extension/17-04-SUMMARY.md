---
phase: 17-hard-tek-detectors-v1-genrerouter-musicstate-extension
plan: 04
subsystem: state
tags: [detectors, structural, sense-14, phrase-boundary, autocorrelation, paired-detector]
requirements: [SENSE-12, SENSE-14]
dependency-graph:
  requires:
    - vibemix.state.music_state.MusicState (Phase 6 baseline + Plan 17-01 fields:
      beat_phase, bpm_confidence, energy_curve)
    - vibemix.state.event.Event (Phase 3)
    - vibemix.state.detectors.breakdown_kick_kill.BreakdownKickKillDetector
      (Plan 17-03 — phrase detector takes a kill instance as OPTIONAL ctor dep
      for self-correction; None is a valid argument)
    - vibemix.audio.constants (Plan 17-04 Task 1 — PHRASE_BOUNDARY_BAR_TOLERANCE,
      PHRASE_BOUNDARY_MIN_BARS_BETWEEN_FIRES, PHRASE_BOUNDARY_MIN_LOCK_CONFIDENCE,
      PHRASE_AUTOCORR_LOW_HZ, PHRASE_AUTOCORR_HIGH_HZ, BPM_CONFIDENCE_MIN_FOR_DOWNBEAT,
      MIN_EVENT_GAP_PER_TYPE extended with PHRASE_BOUNDARY)
    - scipy.signal.fftconvolve (project dep — CLAUDE.md tech stack `scipy==1.17.1`)
  provides:
    - vibemix.state.detectors.PhraseBoundaryDetector (sixth Wave-2 detector)
    - vibemix.state.detectors._phrase_dsp module exposing 3 pure functions:
      band_limited_autocorr, lock_downbeat_phase, estimate_phrase_length_bars
    - 1 new Event type: "PHRASE_BOUNDARY"
    - Module-level BPM_CONFIDENCE_MIN_FOR_DOWNBEAT constant (lifted from
      reentry_kick_land.py private constant; both detectors now share it)
  affects:
    - Plan 17-05 (GenreRouter — registers all six Wave-2 detectors per active
      genre; responsible for wiring exactly ONE PhraseBoundaryDetector per
      kill instance per active genre, with `kill_detector=None` allowed for
      genres where breakdowns aren't structural)
    - Plan 17-06 (tuning harness — `tune_detectors.py` will import the 3 pure
      DSP functions directly to validate against reference WAV anchors
      WITHOUT instantiating the detector class)
    - Phase 18 (Evidence Registry — Citation Grammar will tag PHRASE_BOUNDARY
      events with their `extra` payloads; the phrase boundary IS the canonical
      structural-arc marker for "the build to the next blend point")
tech-stack:
  added: []
  patterns:
    - Pure-function DSP module sibling to `_dsp.py` per SENSE-15 `_impl/`
      shared-primitives convention (kick-side primitives in `_dsp.py`,
      phrase-side in `_phrase_dsp.py`)
    - FFT band-pass before autocorrelation (vocals / leads / hi-hats zeroed
      before correlation — the kick band is the ONLY honest signal for
      phrase structure)
    - 1% in-band-vs-full-RMS gate prevents normalizing numerical noise to
      1.0 at lag-0 on out-of-band-only inputs (anti-hallucination per
      T-17-04-01)
    - mean+2σ "convincing" floor for phrase-length self-similarity (1σ was
      too lenient — random uniform curves occasionally produce 1σ excursions
      at one of the candidate lags by chance)
    - Optional dependency injection (`kill_detector: BreakdownKickKillDetector
      | None`) — Plan 05 GenreRouter passes None for genres where kick-kill
      self-correction isn't relevant (disco / pop)
    - Float-drift epsilon (`int(beats / 4.0 + 1e-6)`) — without it, a 16-bar
      interval computed from 1000.0 → 1029.538... yields 63.99999999999977
      beats → bar_index=15 silently instead of 16 (1 ulp drift drops the
      boundary tick)
    - Pure read-only consumers of MusicState (Phase 3 single-writer
      invariant preserved — `grep -c "_lock"` on phrase_boundary.py +
      _phrase_dsp.py returns 0)
key-files:
  created:
    - src/vibemix/state/detectors/_phrase_dsp.py
    - src/vibemix/state/detectors/phrase_boundary.py
    - tests/state/detectors/test_phrase_dsp.py
    - tests/state/detectors/test_phrase_boundary.py
  modified:
    - src/vibemix/audio/constants.py (5 thresholds + 1 cooldown entry +
      lifted BPM_CONFIDENCE_MIN_FOR_DOWNBEAT to module level + alias
      PHRASE_BOUNDARY_MIN_LOCK_CONFIDENCE)
    - src/vibemix/state/detectors/reentry_kick_land.py (consumes lifted
      BPM_CONFIDENCE_MIN_FOR_DOWNBEAT module-level constant; private name
      `_BPM_CONFIDENCE_MIN_FOR_DOWNBEAT` kept as backward-compat alias)
    - src/vibemix/state/detectors/__init__.py (re-exports PhraseBoundaryDetector;
      module docstring updated to document the optional-kill-detector pair contract)
    - tests/audio/test_constants.py (shape assertion: PHRASE_BOUNDARY key + value pin)
decisions:
  - "PhraseBoundaryDetector takes BreakdownKickKillDetector as an OPTIONAL constructor argument (`kill_detector: BreakdownKickKillDetector | None = None`). Same DI idiom as ReentryKickLandDetector but the kill dep is REQUIRED there (re-entry without a kill is meaningless), here it is OPTIONAL (Plan 05 GenreRouter MAY pass None for genres where breakdowns aren't structural — disco / pop)."
  - "BPM_CONFIDENCE_MIN_FOR_DOWNBEAT lifted from `reentry_kick_land.py` private constant to module-level `vibemix.audio.constants` constant. Both detectors now share it. Plan 17-03 SUMMARY explicitly noted this lift as a Plan 17-04 candidate when phrase_boundary picked the same threshold. Private name kept as backward-compat alias: `_BPM_CONFIDENCE_MIN_FOR_DOWNBEAT = BPM_CONFIDENCE_MIN_FOR_DOWNBEAT`."
  - "Self-correction on BREAKDOWN_KICK_KILL is the SAME idiom as ReentryKickLand reads `kill_detector.last_kill_at`. PhraseBoundary additionally tracks `last_observed_kill_at` (idempotency: each kill resets the anchor at most once) and clears `last_fire_bar_index` on the reset (post-kill fires must not be blocked by the pre-kill counter — the kill is a structural restart)."
  - "Two independent anti-hallucination gates per T-17-04-01: (1) state.bpm_confidence < 0.5 short-circuits before seeding OR boundary check; (2) lock_downbeat_phase's internal confidence must clear 0.5 to seed a new lock. Either gate failing returns None — never silently anchor a fake lock."
  - "Out-of-band noise rejection in band_limited_autocorr: when residual in-band RMS is < 1% of full-input RMS, return empty array. Without this guard, autocorrelating numerical residual would normalize to 1.0 at lag-0 and produce spurious peaks. Mirrors `kick_band_centroid`'s leakage gate in `_dsp.py`."
  - "estimate_phrase_length_bars uses mean+2σ (not 1σ) for the convincing-peak threshold. Random uniform curves occasionally produce 1σ excursions at one of the candidate lags by chance, which would silently mis-classify a non-periodic track as having an 8/32-bar phrase. 2σ floor pushes false-positive rate well under 5%."
  - "Cooldown pick: PHRASE_BOUNDARY = 24.0s. Phrases land ~12-15s apart at typical BPM × 16 bars; 24s prevents same-phrase double-fire while still allowing every-other-phrase reactivity. The bar-count gate (PHRASE_BOUNDARY_MIN_BARS_BETWEEN_FIRES = 8) is the meaningful unit; the wall-clock 24s is a redundant guard."
  - "Float-drift epsilon (1e-6) added to bar_index calculation. The natural arithmetic `int(beats_since_lock / 4.0)` was returning 15 instead of 16 for a 16-bar interval at 130 BPM because beats_since_lock = 63.99999999999977 (1 ulp shy of 64). Rule 1 bug fix — discovered during GREEN phase, fixed before commit."
  - "Added 8 tests for _phrase_dsp.py (plan spec listed 7). The 8th test (`test_lock_downbeat_phase_invalid_bpm_returns_zero_zero`) is a Rule 2 addition: the anti-hallucination contract for invalid BPM is critical (T-17-04-01 mitigation) and deserves explicit coverage rather than being an implicit consequence of `test_lock_downbeat_phase_returns_phase_in_zero_to_one`."
  - "Added 10 tests for PhraseBoundaryDetector (plan spec listed 9). The 10th test (`test_phrase_boundary_detector_is_re_exported_from_subpackage`) is a Rule 2 addition: re-export sentinel parity with all five sibling detector suites (kick_swap / sub_layer_arrival / kick_density_shift / breakdown_kick_kill / reentry_kick_land — every one carries a re-export test)."
  - "Test 3 (out-of-band noise rejection in test_phrase_dsp.py) updated mid-GREEN to reflect the empty-array contract: kick → real autocorr; out-of-band noise → empty / negligible. Original test assumed the function would always return a non-empty array; the 1% RMS-leakage gate makes the empty branch the correct anti-hallucination behavior."
metrics:
  duration_minutes: 8
  completed: 2026-05-14
  tasks_total: 2
  tasks_complete: 2
  files_changed: 7
  tests_added: 18
  tests_passing_in_detector_suite: 66
  tests_passing_in_state_plus_audio: 414
---

# Phase 17 Plan 04: Phrase Boundary + Band-Limited Autocorr Primitives Summary

`PhraseBoundaryDetector` shipped — the SIXTH and final Wave-2 cross-genre
detector. Fires on the downbeat that closes an 8 / 16 / 32-bar phrase, the
structural unit DJs use to plan blends. Locks the downbeat phase via 40-120Hz
band-limited autocorrelation (the kick band is the only honest signal for
phrase structure — vocals / leads / hi-hats are FFT-zeroed before correlation).
Self-corrects when `BREAKDOWN_KICK_KILL` fires by resetting its phrase counter:
the breakdown IS where the next phrase starts. With Plan 17-02 and 17-03
shipped earlier today, the AI now has the FULL grammar of dance-music
structure (groove → kick swap / sub layer / density shift → phrase end →
breakdown → re-entry). 18 new behavior tests pass; 414/414 state+audio
regression green; Phase 3 single-writer invariant preserved (zero MusicState
writes from any of the six detectors).

## What Shipped

### Detector class signature (for Plan 17-05 GenreRouter registration)

```python
class PhraseBoundaryDetector:
    def __init__(self, kill_detector: BreakdownKickKillDetector | None = None) -> None: ...
    def detect(self, state: MusicState, audio_buf: AudioBuffer, now: float) -> Event | None: ...
    # Public state for tests/observability:
    kill_detector: BreakdownKickKillDetector | None
    last_event_at: float
    locked_bpm: float            # the BPM at which we last locked
    lock_anchor_t: float         # session-time of the last lock OR kill self-correct
    phrase_length_bars: int      # 8 / 16 / 32 — re-estimated on every re-lock
    last_observed_kill_at: float # tracks kill_detector.last_kill_at for new-kill detection
    last_fire_bar_index: int     # for the min-bars-between-fires gate
```

Returns `Event(type, state, extra=dict)` on fire:

| Detector                  | Event type           | `extra` keys                                                              |
| ------------------------- | -------------------- | ------------------------------------------------------------------------- |
| PhraseBoundaryDetector    | `"PHRASE_BOUNDARY"`  | `phrase_length_bars` (int 8/16/32), `bar_index_in_phrase` (int), `beat_phase` (3dp), `bpm` (1dp) |

### DSP module — `_phrase_dsp.py` (3 pure functions for Plan 06 harness)

```python
def band_limited_autocorr(samples, sample_rate, *, low_hz=40.0, high_hz=120.0, max_lag_seconds=4.0) -> np.ndarray: ...
def lock_downbeat_phase(samples, bpm, sample_rate) -> tuple[float, float]: ...
def estimate_phrase_length_bars(energy_curve, bpm, *, hop_seconds=1.0) -> int: ...
```

- `band_limited_autocorr`: FFT band-pass into [low_hz, high_hz], then
  `scipy.signal.fftconvolve`-based autocorrelation normalized by lag-0.
  Returns empty array when residual in-band RMS is < 1% of full-input RMS
  (anti-hallucination — never normalize numerical noise to 1.0 at lag-0).

- `lock_downbeat_phase`: Band-limited variant of
  `vibemix.audio.features.compute_downbeat_phase`. Same anti-hallucination
  contract: invalid BPM (≤0, NaN, Inf, >220) → `(0.0, 0.0)`. STRICTER than
  the mascot-grade sibling: "few peaks" returns `(0.0, 0.0)` instead of
  preserving a `prior_phase` (phrase locking has no prior_phase concept).

- `estimate_phrase_length_bars`: Self-similarity over the energy curve at
  hop_seconds resolution; returns one of `{8, 16, 32}`. Default-16 fallback
  per T-17-04-02 accept disposition. mean+2σ "convincing" floor (not 1σ)
  prevents random curves from silently latching onto a noise hump.

### New thresholds (Task 1 — `vibemix.audio.constants`)

| Constant                                | Value | Rationale                                                                                                  |
| --------------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------- |
| `PHRASE_BOUNDARY_BAR_TOLERANCE`         | `0.20`| ±20% of one bar — matches `KICK_REENTRY_BAR_TOLERANCE` for "near a downbeat" semantics consistency           |
| `PHRASE_BOUNDARY_MIN_BARS_BETWEEN_FIRES`| `8`   | Bar count is the meaningful unit; ≈12-15s at 130-170 BPM. Wall-clock cooldown is a redundant floor          |
| `PHRASE_AUTOCORR_LOW_HZ`                | `40.0`| Per SENSE-14 — same lower edge as `kick_band_centroid` in `_dsp.py`                                         |
| `PHRASE_AUTOCORR_HIGH_HZ`               | `120.0`| Per SENSE-14 — wider than just the sub-band so pitched-up Hard Tek kicks (100-120Hz) still register         |
| `BPM_CONFIDENCE_MIN_FOR_DOWNBEAT`       | `0.5` | LIFTED from `reentry_kick_land.py` private constant — both detectors now share. Slightly looser than Phase 13's mascot-render gate (0.6) since structural detection is more time-critical |
| `PHRASE_BOUNDARY_MIN_LOCK_CONFIDENCE`   | `0.5` | Alias of `BPM_CONFIDENCE_MIN_FOR_DOWNBEAT` for callers that want the semantic name                          |

### New cooldown (Task 1 — `MIN_EVENT_GAP_PER_TYPE` extension)

| Event type         | Cooldown (sec) | Picked relative to                                                                                              |
| ------------------ | -------------- | --------------------------------------------------------------------------------------------------------------- |
| `PHRASE_BOUNDARY`  | `24.0`         | Phrases land ~12-15s apart at typical BPM × 16 bars; 24s prevents same-phrase double-fire while still allowing every-other-phrase reactivity. The bar-count gate (8) is the meaningful unit |

## The Self-Correction Contract (BREAKDOWN_KICK_KILL → phrase counter reset)

Same DI idiom as `ReentryKickLandDetector`, with two key differences:

1. **Optional dep:** `kill_detector: BreakdownKickKillDetector | None = None`.
   Plan 05's GenreRouter MAY pass None for genres where kick-kill self-
   correction isn't relevant (e.g. disco / pop / soul where breakdowns
   aren't structural). `ReentryKickLand` makes the kill REQUIRED (re-entry
   without a kill is meaningless); `PhraseBoundary` makes it OPTIONAL
   (phrase boundaries exist with or without breakdowns).

2. **Counter reset semantics:** When the detector observes a fresh kill
   (`kill_detector.last_kill_at > self.last_observed_kill_at`), it:
   - sets `lock_anchor_t = kill_at` (the new phrase starts at the kill)
   - sets `last_observed_kill_at = kill_at` (idempotency — each kill
     resets the anchor at most once)
   - **clears `last_fire_bar_index = -999`** (post-kill fires must not be
     blocked by the pre-kill counter — the kill is a structural restart)
   - returns None (next-tick is the start of the new phrase, not a boundary)

Test 4 (`test_phrase_boundary_self_corrects_on_breakdown_kick_kill`) pins
this contract: pre-kill bar_index=12 (no fire) → kill at +2s → 16 bars
after kill fires PHRASE_BOUNDARY (bar_index_in_phrase=16, counted from kill).

### Why optional vs. required differs from ReentryKickLand

`ReentryKickLand` cannot fire without a `last_kill_at > 0.0` — its entire
contract IS the pair. `PhraseBoundary` fires on phrase structure regardless
of whether breakdowns are present; the kill detector only adjusts WHERE the
phrase counter resets to. A genre router that wants "phrase boundaries but
no breakdown self-correction" should pass `None`. The detector must (and
does) handle `None` cleanly — Test 9 covers this.

## Anti-Hallucination Stack (T-17-04-01 mitigation)

Two **independent** confidence gates, both at threshold 0.5:

1. **State-level gate:** `state.bpm_confidence < BPM_CONFIDENCE_MIN_FOR_DOWNBEAT`
   short-circuits BEFORE any seeding or boundary check. Phase 13 forces
   `beat_phase = 0.0` when BPM lock is weak — without this gate, that
   fabricated 0.0 would naively pass the alignment check (0.0 IS the
   downbeat) and false-fire on every "no BPM lock" frame.

2. **Lock-level gate:** `lock_downbeat_phase` requires its OWN internal
   confidence ≥ 0.5 to seed a new lock. The internal confidence is the
   prominence (peak-vs-mean) of the comb-correlation, capped by peak count.

Either gate failing returns None — the detector never anchors a fake lock.
Test 5 (`test_phrase_boundary_no_fire_on_low_bpm_confidence`) verifies the
state-level gate AND that the detector did NOT seed (`d.lock_anchor_t == 0.0`)
on a low-confidence first call.

## Threshold Lift: BPM_CONFIDENCE_MIN_FOR_DOWNBEAT

Plan 17-03 SUMMARY explicitly flagged this as a Plan 17-04 candidate:

> The threshold lives as a private module constant
> (`_BPM_CONFIDENCE_MIN_FOR_DOWNBEAT = 0.5`) inside `reentry_kick_land.py`
> — not promoted to `audio/constants.py` because no other detector consumes
> it (yet). Plan 17-04's `PhraseBoundaryDetector` will face the same hazard;
> if it picks the same threshold, lift to constants then.

`PhraseBoundary` does pick the same 0.5 threshold (rationale identical: re-
entry/phrase detection is more time-critical than mascot animation, but the
bar should not be so high that legitimate Hard Tek BPM locks at confidence
≈ 0.55 silently lose their structural calls). So the lift happened in this
plan: `BPM_CONFIDENCE_MIN_FOR_DOWNBEAT: float = 0.5` is now a module-level
constant in `vibemix.audio.constants`. The private name in
`reentry_kick_land.py` is preserved as a backward-compat alias
(`_BPM_CONFIDENCE_MIN_FOR_DOWNBEAT = BPM_CONFIDENCE_MIN_FOR_DOWNBEAT`) — no
risk of breaking anything that already imported the private name. The
existing 12 reentry tests still pass after the refactor.

## Float-Drift Bug Fix (Rule 1 — discovered during GREEN phase)

The natural arithmetic `int(beats_since_lock / 4.0)` was returning 15 instead
of 16 for a 16-bar interval at 130 BPM:

```text
fire_at - lock_anchor_t = 1029.5384615384615 - 1000.0 = 29.538461538461548
beats_since_lock        = 29.538461538461548 * 130.0 / 60.0 = 63.99999999999977
bar_index               = int(63.99999999999977 / 4.0) = int(15.9999...) = 15  ← BUG
```

1 ulp drift (4×10⁻¹⁵) silently dropped the boundary tick. Fix:

```python
bar_index = int(beats_since_lock / 4.0 + 1e-6)
```

The 1e-6 epsilon is well under any real beat period (1 µs of beats at the
fastest sane BPM ≈ 1.3×10⁻⁹ seconds — many orders of magnitude smaller than
the bar-tolerance gate at ±20%). Discovered + fixed during GREEN; the
inline comment in `phrase_boundary.py` documents the rationale so a future
reader doesn't strip the "magic number" thinking it's noise.

## Behavior tables

### `_phrase_dsp.py` (8 tests in `test_phrase_dsp.py`)

| Test                                                                  | What it pins down                                                                              |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `test_band_limited_autocorr_locks_synthetic_4on4_at_130bpm`           | 16s synthetic 4-on-floor → autocorr peak at samples-per-beat (130 BPM) within ±5%               |
| `test_band_limited_autocorr_locks_at_150bpm_and_170bpm`               | Same lock at 150 + 170 BPM (Hard Tek band)                                                      |
| `test_band_limited_autocorr_rejects_high_freq_noise`                  | 1-4kHz pink noise → empty array OR peak < 30% of kick-pattern peak                              |
| `test_lock_downbeat_phase_returns_phase_in_zero_to_one`               | phase ∈ [0, 1) and confidence ∈ [0, 1] on valid synthetic kick input                            |
| `test_lock_downbeat_phase_invalid_bpm_returns_zero_zero`              | bpm ≤ 0 / NaN / > 220 → (0.0, 0.0) — anti-hallucination per T-17-04-01                          |
| `test_phrase_length_bars_estimates_8_16_32_from_self_similarity`      | Synthetic curve with clear 16-bar self-similarity peak → returns 16                             |
| `test_phrase_length_bars_returns_default_on_short_curve`              | Curve length 3 < 8-bar minimum → returns 16 (conservative default)                              |
| `test_phrase_length_bars_returns_16_on_unconvincing_self_similarity`  | Random uniform curve → returns 16 (mean+2σ floor blocks spurious 8-bar latch)                   |

### `PhraseBoundaryDetector` (10 tests in `test_phrase_boundary.py`)

| Test                                                                  | What it pins down                                                                              |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `test_phrase_boundary_seeds_lock_on_first_call`                       | First call seeds lock_anchor_t + locked_bpm + phrase_length_bars; returns None                 |
| `test_phrase_boundary_fires_on_downbeat_at_estimated_phrase_count`    | bar_index=16 with phrase_length_bars=16 + beat_phase≈0 → fires; extra carries metadata         |
| `test_phrase_boundary_no_fire_mid_phrase`                             | bar_index=8 of 16 (mid-phrase) → returns None                                                  |
| `test_phrase_boundary_self_corrects_on_breakdown_kick_kill`           | pre-kill bar_index=12 → kill at +2s → 16 bars after kill fires (counted from kill)             |
| `test_phrase_boundary_no_fire_on_low_bpm_confidence`                  | bpm_confidence=0.3 < 0.5 → None AND does not seed (anti-hallucination)                          |
| `test_phrase_boundary_silence_gate`                                   | rms < LOW_RMS OR phase == "silent" → None                                                      |
| `test_phrase_boundary_cooldown_prevents_double_fire`                  | Within-24s repeat fire blocked even with intervening 16-bar boundary                            |
| `test_phrase_boundary_min_bars_between_fires`                         | bar count gate: 4 bars after fire (bar_index_delta=4 < 8) → None even if wall-clock cleared    |
| `test_phrase_boundary_with_no_kill_detector_works`                    | `PhraseBoundaryDetector(kill_detector=None)` fires correctly (Plan 05 disco/pop case)           |
| `test_phrase_boundary_detector_is_re_exported_from_subpackage`        | `from vibemix.state.detectors import PhraseBoundaryDetector` resolves                          |

## Verification (plan §verification)

```text
$ pytest tests/state/detectors/ -x -q                  → 66 passed in 0.41s
$ pytest tests/state/ tests/audio/ -x -q               → 414 passed in 0.58s
$ python -c "from vibemix.state.detectors import \
    KickSwapDetector, SubLayerArrivalDetector, KickDensityShiftDetector, \
    BreakdownKickKillDetector, ReentryKickLandDetector, PhraseBoundaryDetector; \
    print('all 6 importable')"
                                                       → all 6 importable
$ python -c "from vibemix.state.detectors._phrase_dsp import \
    band_limited_autocorr, lock_downbeat_phase, estimate_phrase_length_bars; \
    print('dsp exports ok')"
                                                       → dsp exports ok
```

All four verification steps pass.

## Test count delta

| Suite                        | Before Plan 17-04 | After Plan 17-04 | Delta |
| ---------------------------- | ----------------- | ---------------- | ----- |
| `tests/state/detectors/`     | 48                | 66               | +18   |
| `tests/state/ tests/audio/`  | 396               | 414              | +18   |

(+8 phrase_dsp tests + 10 phrase_boundary tests = 18 new; both suites grew by
the same 18 since the new tests live under `tests/state/detectors/` which is
a subset of `tests/state/`.)

## Deviations from Plan

Plan executed substantively as written. Five additions / adjustments, all
within the plan's spirit:

1. **Lifted `BPM_CONFIDENCE_MIN_FOR_DOWNBEAT` to module-level constant** —
   Plan 17-03 SUMMARY flagged this as a Plan 17-04 candidate; `PhraseBoundary`
   does pick the same 0.5 threshold so the lift happened. Refactored
   `reentry_kick_land.py` to consume the lifted name; private name preserved
   as backward-compat alias. (Per executor system prompt directive.)

2. **Added 8th test in `test_phrase_dsp.py`** (plan listed 7) —
   `test_lock_downbeat_phase_invalid_bpm_returns_zero_zero`. Rule 2 (missing
   critical coverage): the anti-hallucination contract for invalid BPM is
   T-17-04-01 mitigation and deserves explicit coverage rather than being
   an implicit consequence of the phase-range test.

3. **Added 10th test in `test_phrase_boundary.py`** (plan listed 9) —
   `test_phrase_boundary_detector_is_re_exported_from_subpackage`. Rule 2
   (missing critical coverage): re-export sentinel parity with all five
   sibling detector suites.

4. **Test 3 (out-of-band noise rejection) updated mid-GREEN to reflect the
   empty-array contract.** Original test assumed the function would always
   return a non-empty array; the 1% RMS-leakage anti-hallucination gate
   makes the empty branch the correct behavior. Rule 1 (the test was wrong;
   the implementation choice is correct).

5. **Float-drift epsilon (1e-6) added to bar_index calculation.** Rule 1
   bug fix discovered during GREEN — `int(beats / 4.0)` was returning 15
   instead of 16 for a 16-bar interval at 130 BPM (1 ulp drift). Fixed
   inline with documenting comment.

6. **`tests/audio/test_constants.py` shape assertion updated for
   `PHRASE_BOUNDARY` key.** Rule 3 (blocking issue caused by the constants
   extension — not a scope expansion). Value pin added (24.0).

## Threat Flags

None. The plan's threat register fully covers the surface introduced by
this plan; no new trust boundaries discovered during execution.

## Self-Check

- Files created (verified on disk):
  - `src/vibemix/state/detectors/_phrase_dsp.py` — FOUND
  - `src/vibemix/state/detectors/phrase_boundary.py` — FOUND
  - `tests/state/detectors/test_phrase_dsp.py` — FOUND
  - `tests/state/detectors/test_phrase_boundary.py` — FOUND
- Files modified (verified via git log):
  - `src/vibemix/audio/constants.py` — modified in `0ef4f67`
  - `src/vibemix/state/detectors/reentry_kick_land.py` — modified in `0ef4f67` (lifted constant import)
  - `src/vibemix/state/detectors/__init__.py` — modified in `80375f1`
  - `tests/audio/test_constants.py` — modified in `0ef4f67`
- Commits (verified in `git log`):
  - `0ef4f67` — Task 1 RED + constants — FOUND
  - `bd75bc0` — Task 1 GREEN — FOUND
  - `cae2f3f` — Task 2 RED — FOUND
  - `80375f1` — Task 2 GREEN — FOUND
- Test counts (verified by re-running pytest):
  - `tests/state/detectors/` — 66 passed (48 baseline + 18 new = 66)
  - `tests/state/ tests/audio/` — 414 passed (396 baseline + 18 new = 414)
- Smoke imports (verified):
  - all 6 detectors importable from `vibemix.state.detectors`
  - 3 DSP functions importable from `vibemix.state.detectors._phrase_dsp`

## Self-Check: PASSED
