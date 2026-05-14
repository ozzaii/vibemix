---
phase: 17-hard-tek-detectors-v1-genrerouter-musicstate-extension
plan: 03
subsystem: state
tags: [detectors, kick-side, sense-12, hard-tek, paired-detector, breakdown, reentry]
requirements: [SENSE-12]
dependency-graph:
  requires:
    - vibemix.state.music_state.MusicState (Phase 6 baseline + Plan 17-01 fields:
      beat_phase, bpm_confidence)
    - vibemix.state.event.Event (Phase 3)
    - vibemix.audio.constants (Plan 17-03 Task 1 — KICK_KILL_SUB_FLOOR,
      KICK_KILL_SUB_DROP_MIN, KICK_REENTRY_SUB_FLOOR, KICK_REENTRY_BAR_TOLERANCE,
      KICK_REENTRY_MAX_AGE_S, MIN_EVENT_GAP_PER_TYPE extended with
      BREAKDOWN_KICK_KILL + REENTRY_KICK_LAND cooldowns)
    - vibemix.state.detectors.breakdown_kick_kill.BreakdownKickKillDetector
      (Plan 17-03 Task 1 — reentry detector takes a kill instance as
      constructor dep)
  provides:
    - vibemix.state.detectors.BreakdownKickKillDetector
    - vibemix.state.detectors.ReentryKickLandDetector
    - 2 new Event types: "BREAKDOWN_KICK_KILL", "REENTRY_KICK_LAND"
    - Public pair-contract attribute: BreakdownKickKillDetector.last_kill_at
      (read by ReentryKickLandDetector — DI, no globals)
  affects:
    - Plan 17-04 (PhraseBoundaryDetector — sixth and final Wave 2 detector;
      shares the same `.detect(state, audio_buf, now)` signature)
    - Plan 17-05 (GenreRouter — registers all six Wave 2 detectors per active
      genre; responsible for wiring exactly ONE ReentryKickLandDetector per
      kill instance per active genre)
    - Plan 17-06 (tuning harness — replays reference WAVs through these
      paired detectors to validate KICK_KILL_SUB_FLOOR / drop_min /
      KICK_REENTRY_SUB_FLOOR thresholds against breakdown anchors)
    - Phase 18 (Evidence Registry — Citation Grammar will tag
      BREAKDOWN_KICK_KILL / REENTRY_KICK_LAND events with their `extra`
      payloads; the kill→reentry pair is the canonical structural-arc citation)
tech-stack:
  added: []
  patterns:
    - Paired detector via constructor dependency injection (no globals,
      no shared module state — Plan 05 GenreRouter wires exactly one pair
      per active genre)
    - Public `last_kill_at` attribute as the single-source-of-truth pair
      contract (no callbacks, no event bus, no observer pattern — just an
      attribute the sibling reads on every tick)
    - Per-pair consumption tracking via `last_consumed_kill_at` so each
      kill triggers at most one reentry (idempotency under repeated ticks)
    - bpm_confidence guard BEFORE downbeat alignment (T-17-03-02 mitigation)
      preserves Phase 13's "no fabricated lock" anti-hallucination contract
    - Wrap-around downbeat distance via `min(beat_phase, 1 - beat_phase)`
      (the downbeat is the wrap-around point at 1.0 ≡ 0.0, not just 0.0)
    - Pure read-only consumers of MusicState (Phase 3 single-writer
      invariant preserved — `grep -c "_lock"` on both modules returns 0)
key-files:
  created:
    - src/vibemix/state/detectors/breakdown_kick_kill.py
    - src/vibemix/state/detectors/reentry_kick_land.py
    - tests/state/detectors/test_breakdown_kick_kill.py
    - tests/state/detectors/test_reentry_kick_land.py
  modified:
    - src/vibemix/audio/constants.py (5 thresholds + 2 cooldown entries)
    - src/vibemix/state/detectors/__init__.py (re-exports both new classes)
    - tests/audio/test_constants.py (shape assertion: 2 new MIN_EVENT_GAP_PER_TYPE keys)
decisions:
  - "ReentryKickLandDetector takes the BreakdownKickKillDetector instance as a constructor argument — explicit pair, no globals, no shared module state. Plan 17-05 GenreRouter wires exactly one re-entry per active genre with the matching kill instance."
  - "BreakdownKickKillDetector.last_kill_at is PUBLIC by design — it IS the pair contract. Read by ReentryKickLandDetector on every tick; updated only inside detect() on a successful fire."
  - "Each kill pairs with at most ONE re-entry via last_consumed_kill_at consumption tracking. Subsequent ticks pointing at the same kill timestamp return None until the kill detector advances last_kill_at."
  - "T-17-03-02 mitigation: state.bpm_confidence < 0.5 short-circuits BEFORE the downbeat-alignment gate. Without this, Phase 13's anti-hallucination contract (invalid BPM → beat_phase forced to 0.0) would naively pass the gate (0.0 IS the downbeat) and false-fire on every no-BPM-lock frame."
  - "Wrap-around downbeat distance: min(beat_phase, 1.0 - beat_phase). beat_phase = 0.95 is 0.05 from the next downbeat at 1.0 ≡ 0.0 — the bar wraps."
  - "BreakdownKickKillDetector mirrors KickDensityShiftDetector's two-layer silence gate (RMS floor + Phase 6 silent-phase classification). The phase-silent gate is the second silence guard so a transient ambient spike during silence cannot seed a phantom kill baseline."
  - "Cooldown picks: BREAKDOWN_KICK_KILL = 20s (mirrors MIX_MOVE — structural moment, not a fast tap); REENTRY_KICK_LAND = 12s (shorter than the kill cooldown because the kill→reentry pair is bounded by KICK_REENTRY_MAX_AGE_S = 30s; a longer cooldown would push re-entry past the natural pair window and silently swallow the moment)."
  - "Added 12 tests for ReentryKickLandDetector (plan spec listed 9). The 3 additions are Rule 2 (missing critical coverage): bpm_confidence guard test, DI-contract assertion test, and re-export sentinel test (parity with the kick_swap / sub_layer_arrival / kick_density_shift / breakdown_kick_kill suites which all carry a re-export test)."
  - "Added 8 tests for BreakdownKickKillDetector (plan spec listed 7) — same Rule 2 reasoning: re-export sentinel parity with the four sibling detector suites."
  - "tests/audio/test_constants.py shape assertion was updated to accept the 2 new MIN_EVENT_GAP_PER_TYPE keys (Rule 3 — direct consequence of the constants extension, not a scope expansion)."
metrics:
  duration_minutes: 6
  completed: 2026-05-14
  tasks_total: 2
  tasks_complete: 2
  files_changed: 7
  tests_added: 20
  tests_passing_in_detector_suite: 48
  tests_passing_in_state_plus_audio: 396
---

# Phase 17 Plan 03: Paired Breakdown / Re-entry Detectors Summary

Two new Phase 17 SENSE-12 detector classes shipped — `BreakdownKickKillDetector`
and `ReentryKickLandDetector` — each in its own file under
`src/vibemix/state/detectors/`. They're paired via constructor dependency
injection: the re-entry detector reads the kill detector's public
`last_kill_at` attribute. Together they capture the WHOLE structural arc
(kick gone → silence/filter → kick comes back near a downbeat) instead of
firing two unrelated noisy events. Closes the half of Kaan's "feels
surface-level" critique where v4 missed breakdowns and re-entries — the most
structurally important "moments" a DJ ear catches. 20 new behavior tests
pass; 396/396 state+audio regression green; Phase 3 single-writer invariant
preserved (zero MusicState writes from either detector code path).

## What Shipped

### Detector class signatures (for Plan 17-05 GenreRouter registration)

```python
class BreakdownKickKillDetector:
    def __init__(self) -> None: ...
    def detect(self, state: MusicState, audio_buf: AudioBuffer | None, now: float) -> Event | None: ...
    # Public state for tests/observability + the pair contract:
    last_event_at: float
    last_kill_at: float          # ← PAIR CONTRACT (read by ReentryKickLandDetector)
    baseline_sub: float | None
    baseline_at: float

class ReentryKickLandDetector:
    def __init__(self, kill_detector: BreakdownKickKillDetector) -> None: ...
    def detect(self, state: MusicState, audio_buf: AudioBuffer | None, now: float) -> Event | None: ...
    kill_detector: BreakdownKickKillDetector  # ← DI'd pair instance
    last_event_at: float
    last_consumed_kill_at: float  # ← idempotency: each kill pairs with one reentry
```

Both return `Event(type, state, extra=dict)` objects on fire:

| Detector                    | Event type             | `extra` keys                                                 |
| --------------------------- | ---------------------- | ------------------------------------------------------------ |
| BreakdownKickKillDetector   | `"BREAKDOWN_KICK_KILL"`| `prev_sub`, `new_sub`, `sub_drop` (rounded to 2dp), `rms` (rounded to 3dp) |
| ReentryKickLandDetector     | `"REENTRY_KICK_LAND"`  | `kill_age_s` (rounded to 1dp), `sub_at_reentry` (2dp), `beat_phase` (3dp) |

### New thresholds (Task 1 — `vibemix.audio.constants`)

| Constant                       | Value | Rationale                                                                                                        |
| ------------------------------ | ----- | ---------------------------------------------------------------------------------------------------------------- |
| `KICK_KILL_SUB_FLOOR`          | `0.10`| Half of LAYER_ARRIVAL high_jump magnitude — kick removal is a smaller fraction-shift than a layer arrival         |
| `KICK_KILL_SUB_DROP_MIN`       | `0.15`| Anti-noise gate — without this a quiet section already at sub=0.08 baseline could spuriously fire on first read   |
| `KICK_REENTRY_SUB_FLOOR`       | `0.18`| Hysteresis above the kill floor (0.10) to avoid rapid re-fire on jitter near the kill threshold                   |
| `KICK_REENTRY_BAR_TOLERANCE`   | `0.20`| ±20% of one bar — looser than ±1 beat (0.25); Hard Tek's distorted onsets blur precise downbeat detection         |
| `KICK_REENTRY_MAX_AGE_S`       | `30.0`| Beyond 30s the breakdown effectively "ended on its own" — no specific re-entry moment worth calling out anymore   |

### New cooldowns (Task 1 — `MIN_EVENT_GAP_PER_TYPE` extension)

| Event type             | Cooldown (sec) | Picked relative to                                                                                              |
| ---------------------- | -------------- | --------------------------------------------------------------------------------------------------------------- |
| `BREAKDOWN_KICK_KILL`  | `20.0`         | Mirrors `MIX_MOVE` — structural moment, not a fast tap                                                          |
| `REENTRY_KICK_LAND`    | `12.0`         | Shorter than the kill cooldown — kill→reentry pair is bounded by `KICK_REENTRY_MAX_AGE_S = 30s`; a longer cooldown would push re-entry past the natural pair window |

## The Paired-Detector Contract

The two detectors are designed to fire as a STRUCTURAL ARC, not two
unrelated events. The contract:

1. **Construction:** `ReentryKickLandDetector(kill_detector)` — the re-entry
   detector takes the kill detector instance as its sole constructor argument.
   No globals, no module state, no event bus, no observer pattern.

2. **Pair attribute:** `BreakdownKickKillDetector.last_kill_at: float` — public
   by design. Stamped to `now` on every successful kill fire (alongside the
   private `last_event_at`). Initial value `0.0` is the sentinel for "no
   kill yet".

3. **Watch window:** ReentryKickLandDetector ignores any kill older than
   `KICK_REENTRY_MAX_AGE_S = 30.0`. After 30s the breakdown effectively ended
   on its own — there's no specific "kick came back" moment to call out.

4. **Consumption:** Each kill pairs with at most ONE re-entry. After a
   successful re-entry fire, ReentryKickLandDetector stamps
   `last_consumed_kill_at = kill_at`. Subsequent ticks pointing at the same
   `kill_at` return `None` until the kill detector advances `last_kill_at`
   (i.e. a fresh kill arrives).

5. **GenreRouter responsibility (Plan 17-05):** wire exactly ONE
   `ReentryKickLandDetector` per active genre, paired with the matching
   `BreakdownKickKillDetector`. Multiple reentry instances watching the
   same kill detector would all fire on the same kill — caught by Plan 17-05's
   integration tests per threat T-17-03-03 (accepted disposition).

### Pair-contract smoke test (plan §verification step 3)

```text
$ python -c "from vibemix.state.detectors import \
    BreakdownKickKillDetector, ReentryKickLandDetector; \
    k=BreakdownKickKillDetector(); r=ReentryKickLandDetector(k); \
    print(r.kill_detector is k)"
                                                       → True
```

## Threat T-17-03-02 Mitigation: bpm_confidence Guard

The plan's threat register flagged a critical interaction with Phase 13's
anti-hallucination contract:

- Phase 13's contract: when BPM lock is weak (`bpm_confidence < 0.6`),
  `downbeat_phase` is FORCED to `0.0` ("no fabricated lock"). Phase 17's
  `beat_phase` mirrors `downbeat_phase`.
- Naive consequence: `beat_phase = 0.0` is exactly on a downbeat, so the
  re-entry detector's downbeat-alignment gate would naively pass on every
  "no BPM lock" frame — false-firing the entire kick re-entry classification.

**Mitigation (per T-17-03-02):** `ReentryKickLandDetector.detect` short-circuits
when `state.bpm_confidence < 0.5` BEFORE the downbeat-alignment gate. The
threshold (0.5) is slightly looser than Phase 13's mascot-render gate (0.6) —
chose 0.5 because re-entry detection is more time-critical than mascot
animation (we'd rather miss a marginal-confidence re-entry than fire a
fabricated one, but the bar should not be so high that legitimate hard-tek
BPM locks at confidence ≈ 0.55 silently lose their re-entry calls).

The threshold lives as a private module constant
(`_BPM_CONFIDENCE_MIN_FOR_DOWNBEAT = 0.5`) inside
`reentry_kick_land.py` — not promoted to `audio/constants.py` because no
other detector consumes it (yet). Plan 17-04's `PhraseBoundaryDetector`
will face the same hazard; if it picks the same threshold, lift to constants
then.

Test: `test_reentry_no_fire_when_bpm_confidence_low` covers this gate.

## Behavior tables

### BreakdownKickKillDetector (8 tests)

| Test                                                          | What it pins down                                                                              |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `test_breakdown_kick_kill_fires_on_sub_collapse_with_audible_rms` | sub 0.30→0.05, rms 0.08 → fires; `extra == {prev_sub: 0.30, new_sub: 0.05, sub_drop: 0.25, rms: 0.08}` |
| `test_breakdown_kick_kill_no_fire_when_rms_also_dropped`      | sub 0.05 BUT rms 0.02 (< LOW_RMS) → silence gate rejects (silence, not kick kill)              |
| `test_breakdown_kick_kill_no_fire_on_small_sub_drop`          | sub 0.30→0.20: new value (0.20) above floor (0.10) → None                                      |
| `test_breakdown_kick_kill_cooldown`                           | Within-20s repeat fire blocked even with intervening baseline rotation                         |
| `test_breakdown_kick_kill_baseline_seeded_on_first_call`      | First call seeds baseline_sub + baseline_at, returns None                                      |
| `test_breakdown_kick_kill_exposes_last_kill_at_for_pair_detector` | After fire, `detector.last_kill_at == now` (pair contract)                                  |
| `test_breakdown_kick_kill_phase_silent_gate`                  | `state.phase == "silent"` rejects even when numbers look right (Phase 6 authoritative)         |
| `test_breakdown_kick_kill_detector_is_re_exported_from_subpackage` | `from vibemix.state.detectors import BreakdownKickKillDetector` resolves                  |

### ReentryKickLandDetector (12 tests)

| Test                                                          | What it pins down                                                                              |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `test_reentry_no_fire_without_prior_kill`                     | `kill_detector.last_kill_at == 0.0` → never fires regardless of state alignment                |
| `test_reentry_fires_on_sub_recovery_within_30s_of_kill_near_downbeat` | kill 5s ago + sub 0.25 + beat_phase 0.05 + bpm_confidence 0.8 → fires; extra carries kill_age_s, sub_at_reentry, beat_phase |
| `test_reentry_no_fire_when_kill_age_exceeds_max`              | kill 35s ago > 30s cap → None                                                                  |
| `test_reentry_no_fire_when_sub_below_reentry_floor`           | sub 0.15 < KICK_REENTRY_SUB_FLOOR (0.18) → None                                                |
| `test_reentry_no_fire_when_beat_phase_misaligned`             | beat_phase 0.50 → distance 0.50 > tolerance 0.20 → None                                        |
| `test_reentry_accepts_beat_phase_near_either_end_of_bar`      | beat_phase 0.95 → wrap-around distance 0.05 < tolerance → fires                                |
| `test_reentry_consumes_kill_after_fire`                       | After fire: same kill cannot re-trigger; new kill arriving later re-arms                       |
| `test_reentry_silence_gate`                                   | rms < LOW_RMS rejects                                                                          |
| `test_reentry_cooldown_12s`                                   | Within-12s second fire blocked even with a fresh kill                                          |
| `test_reentry_no_fire_when_bpm_confidence_low`                | T-17-03-02: bpm_confidence 0.0 short-circuits before alignment gate                            |
| `test_reentry_stores_kill_detector_reference`                 | DI contract: `r.kill_detector is k`                                                            |
| `test_reentry_kick_land_detector_is_re_exported_from_subpackage` | `from vibemix.state.detectors import ReentryKickLandDetector` resolves                       |

## Verification (plan §verification)

```text
$ pytest tests/state/detectors/ -x -q                  → 48 passed in 0.02s
$ pytest tests/state/ tests/audio/ -x -q               → 396 passed in 0.21s
$ python -c "from vibemix.state.detectors import \
    BreakdownKickKillDetector, ReentryKickLandDetector; \
    k=BreakdownKickKillDetector(); r=ReentryKickLandDetector(k); \
    print(r.kill_detector is k)"
                                                       → True
$ grep -c "_lock" src/vibemix/state/detectors/breakdown_kick_kill.py \
                  src/vibemix/state/detectors/reentry_kick_land.py
    src/vibemix/state/detectors/breakdown_kick_kill.py:0
    src/vibemix/state/detectors/reentry_kick_land.py:0
```

All four verification steps pass. Read-only invariant verified — neither
detector acquires `state._lock` (Phase 3 single-writer invariant preserved).

## Deviations from Plan

Plan executed substantively as written. Three minor additions, all within
the plan's spirit:

1. **Re-export sentinel tests (both files)** — plan spec listed 7 tests for
   Task 1 and 9 for Task 2. Added an 8th test to Task 1 and 11th + 12th tests
   to Task 2 covering subpackage re-exports + DI contract. Rule 2 addition
   (missing critical coverage): without it, a regression that breaks the
   `__init__.py` re-export or the constructor wiring would not be caught at
   the test-suite layer. Parity with all four sibling detector suites
   (kick_swap, sub_layer_arrival, kick_density_shift, breakdown_kick_kill —
   all carry a re-export test).

2. **`tests/audio/test_constants.py` shape assertion update** — Plan 17-02
   pinned the `MIN_EVENT_GAP_PER_TYPE` dict shape with an exact-set assertion.
   Plan 17-03 adds two new keys, so the assertion needed extending. Rule 3
   (blocking issue caused by the constants extension — not a scope
   expansion). Two new value pins added alongside (`BREAKDOWN_KICK_KILL ==
   20.0`, `REENTRY_KICK_LAND == 12.0`).

3. **`__init__.py` updated twice (once per task)** — to keep TDD discipline
   strict, Task 1's GREEN only re-exports `BreakdownKickKillDetector` (so
   the `__init__.py` doesn't error on a not-yet-existing
   `reentry_kick_land` module). Task 2's GREEN extends to re-export
   `ReentryKickLandDetector`. Pure mechanical — no behavioral impact.

The plan body's Step 7 of Task 2 lists the bpm_confidence guard implicitly
("If `state.bpm_confidence < 0.5`: return None") via the threat-model
implementation note. Implemented it explicitly with a private module constant
`_BPM_CONFIDENCE_MIN_FOR_DOWNBEAT = 0.5` inside `reentry_kick_land.py`.
Documented in the module docstring + the inline comment + a dedicated test.

## Self-Check

- Files created (verified on disk):
  - `src/vibemix/state/detectors/breakdown_kick_kill.py` — FOUND
  - `src/vibemix/state/detectors/reentry_kick_land.py` — FOUND
  - `tests/state/detectors/test_breakdown_kick_kill.py` — FOUND
  - `tests/state/detectors/test_reentry_kick_land.py` — FOUND
- Files modified (verified via git log):
  - `src/vibemix/audio/constants.py` — FOUND in `17dfe0d`
  - `src/vibemix/state/detectors/__init__.py` — FOUND in `26c1e6d` + `36439a0`
  - `tests/audio/test_constants.py` — FOUND in `26c1e6d`
- Commits (verified in `git log`):
  - `17dfe0d` — RED tests + constants — FOUND
  - `26c1e6d` — Task 1 GREEN — FOUND
  - `b451c26` — Task 2 RED tests — FOUND
  - `36439a0` — Task 2 GREEN — FOUND
- Test counts (verified by re-running pytest):
  - `tests/state/detectors/` — 48 passed (28 baseline + 8 + 12 = 48)
  - `tests/state/ tests/audio/` — 396 passed (376 baseline + 20 = 396)
- Pair contract smoke (verified):
  - `r.kill_detector is k` → True

## Self-Check: PASSED
