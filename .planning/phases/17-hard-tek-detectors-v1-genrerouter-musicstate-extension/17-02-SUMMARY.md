---
phase: 17-hard-tek-detectors-v1-genrerouter-musicstate-extension
plan: 02
subsystem: state
tags: [detectors, kick-side, sense-12, sense-15, hard-tek]
requirements: [SENSE-12]
dependency-graph:
  requires:
    - vibemix.state.music_state.MusicState (Phase 6 baseline + Plan 17-01 fields)
    - vibemix.state.event.Event (Phase 3)
    - vibemix.audio.constants (Plan 17-02 Task 1 — KICK_SWAP_CENTROID_DELTA_HZ,
      SUB_JUMP_THRESHOLD, KICK_DENSITY_SHIFT_DELTA, MIN_EVENT_GAP_PER_TYPE
      extended with KICK_SWAP/SUB_LAYER_ARRIVAL/KICK_DENSITY_SHIFT cooldowns)
    - vibemix.state.detectors._dsp.kick_band_centroid (Plan 17-02 Task 1)
    - vibemix.audio.buffers.AudioBuffer (Phase 3 — only KickSwapDetector reads it)
  provides:
    - vibemix.state.detectors.KickSwapDetector
    - vibemix.state.detectors.SubLayerArrivalDetector
    - vibemix.state.detectors.KickDensityShiftDetector
    - 3 new Event types: "KICK_SWAP", "SUB_LAYER_ARRIVAL", "KICK_DENSITY_SHIFT"
  affects:
    - Plan 17-03 (Wave 2 second-half — BreakdownKickKill / ReentryKickLand /
      PhraseBoundary detectors share the same `.detect(state, audio_buf, now)`
      signature)
    - Plan 17-05 (GenreRouter — registers all six Wave 2 detectors, swaps
      atomically per `state.active_genre`)
    - Plan 17-06 (tuning harness — replays reference WAVs through these
      detectors to validate KICK_SWAP_CENTROID_DELTA_HZ etc. against Hard Tek
      anchor tracks)
    - Phase 18 (Evidence Registry — Citation Grammar will tag KICK_SWAP /
      SUB_LAYER_ARRIVAL / KICK_DENSITY_SHIFT events with their `extra` payloads)
tech-stack:
  added: []
  patterns:
    - One detector class per file (SENSE-15 dispatch architecture sibling to
      `_impl/` shared primitives)
    - `.detect(state, audio_buf, now) -> Event | None` uniform API across the
      kick-side detector trio
    - Silence-gate-first ordering (anti-phantom-baseline-seed; "trust the
      audio" rule from v4)
    - Slow-drift hygiene (rotate baseline on no-fire so multi-minute drifts
      can't accumulate into spurious fires)
    - Pure read-only consumers of MusicState (Phase 3 single-writer invariant
      preserved — `grep -c "_lock" src/vibemix/state/detectors/*.py` returns
      zero hits in code paths; the one match in `__init__.py` is a docstring
      comment about the invariant itself)
key-files:
  created:
    - src/vibemix/state/detectors/kick_swap.py
    - src/vibemix/state/detectors/sub_layer_arrival.py
    - src/vibemix/state/detectors/kick_density_shift.py
    - tests/state/detectors/test_kick_swap.py
    - tests/state/detectors/test_sub_layer_arrival.py
    - tests/state/detectors/test_kick_density_shift.py
  modified:
    - src/vibemix/state/detectors/__init__.py
decisions:
  - "Silence gate runs BEFORE baseline seeding in all three detectors (anti-phantom-seed during breakdowns)"
  - "KickSwapDetector rotates baseline ON cooldown (so the post-cooldown tick has a fresh anchor); SubLayerArrival and KickDensityShift do NOT rotate on cooldown (keep pre-fire baseline so persistent shifts re-fire after cooldown clears)"
  - "SubLayerArrivalDetector reads state.bands['sub'] directly — does NOT re-derive from raw samples. Re-deriving would duplicate the snapshot_features call state_refresh_loop just made and risk numerical disagreement with the rest of the system"
  - "BPM-stability tolerance for SubLayerArrival is hardcoded to 4.0 BPM (anti-double-fire with TRACK_CHANGE per T-17-02-02 — dance-music tempo nudges stay <= 4 BPM, track changes almost always exceed 4)"
  - "KickDensityShiftDetector delta is SIGNED in the extra dict so the AI prompt can describe direction (kick doubled vs kick halved); abs is only used for the threshold check"
  - "audio_buf parameter is ACCEPTED by SubLayerArrivalDetector + KickDensityShiftDetector for API symmetry with KickSwapDetector even though it's unused (explicit `del audio_buf` line + comment); Plan 05 GenreRouter then routes all three through one uniform call signature"
  - "8th re-export test added to test_kick_density_shift.py (plan only specified 7 — added for parity with the kick_swap + sub_layer_arrival test files which both have a re-export sentinel)"
metrics:
  duration_minutes: 9
  completed: 2026-05-14
  tasks_total: 3
  tasks_complete: 3
  files_changed: 7
  tests_added: 22
  tests_passing_in_detector_suite: 28
  tests_passing_in_state_plus_audio: 376
---

# Phase 17 Plan 02: Kick-Side Cross-Genre Detectors v1 Summary

Three new Phase 17 SENSE-12 detector classes shipped — `KickSwapDetector`,
`SubLayerArrivalDetector`, `KickDensityShiftDetector` — each in its own file
under `src/vibemix/state/detectors/` with a uniform
`.detect(state, audio_buf, now) -> Event | None` API. They close the half of
Kaan's "feels surface-level" critique that v4's existing `LAYER_ARRIVAL`
detector misses: kick-character changes, sub-bass arrivals, and kick-pattern
regime shifts. 22 new behavior tests pass; 376/376 state+audio regression
green; Phase 3 single-writer invariant preserved (zero MusicState writes from
any detector code path).

## What Shipped

### Detector class signatures (for Plan 05 GenreRouter registration)

```python
class KickSwapDetector:
    def __init__(self) -> None: ...
    def detect(self, state: MusicState, audio_buf: AudioBuffer, now: float) -> Event | None: ...
    # Public state for tests/observability:
    last_event_at: float
    last_centroid_hz: float | None
    last_centroid_at: float

class SubLayerArrivalDetector:
    def __init__(self) -> None: ...
    def detect(self, state: MusicState, audio_buf: AudioBuffer | None, now: float) -> Event | None: ...
    last_event_at: float
    baseline_sub: float | None
    baseline_bpm: float
    baseline_at: float

class KickDensityShiftDetector:
    def __init__(self) -> None: ...
    def detect(self, state: MusicState, audio_buf: AudioBuffer | None, now: float) -> Event | None: ...
    last_event_at: float
    baseline_density: float | None
    baseline_at: float
```

All three return `Event(type, state, extra=dict)` objects on fire:

| Detector | Event type | `extra` keys |
|----------|-----------|--------------|
| KickSwapDetector | `"KICK_SWAP"` | `prev_centroid_hz`, `new_centroid_hz`, `delta_hz` (all floats) |
| SubLayerArrivalDetector | `"SUB_LAYER_ARRIVAL"` | `prev_sub`, `new_sub`, `sub_jump` (rounded to 2 decimals) |
| KickDensityShiftDetector | `"KICK_DENSITY_SHIFT"` | `prev_density`, `new_density`, `delta` (signed, rounded to 2 decimals) |

### New thresholds (Task 1 — `vibemix.audio.constants`)

| Constant | Value | Rationale |
|---------|-------|-----------|
| `KICK_SWAP_CENTROID_DELTA_HZ` | `12.0` | Smallest robustly-perceptible "different kick" delta in the 40-120Hz band; Plan 06 tuning harness will validate against Hard Tek anchors |
| `SUB_JUMP_THRESHOLD` | `0.10` | Same magnitude as v4 LAYER_ARRIVAL `high_jump` threshold (kept symmetrical so the bass-side detector behaves like its mid/high analog) |
| `KICK_DENSITY_SHIFT_DELTA` | `1.5` | Onsets/sec; smallest robust shift between half-time (~1.0/sec), 4-on-floor techno (~2.5/sec), and hard-tek 4-on-floor (~5.0/sec) |

### New cooldowns (Task 1 — `MIN_EVENT_GAP_PER_TYPE` extension)

| Event type | Cooldown (sec) | Picked relative to |
|-----------|----------------|---------------------|
| `KICK_SWAP` | `14.0` | Slightly faster than `LAYER_ARRIVAL` (16) — kick-character changes are the main "moment" worth catching |
| `SUB_LAYER_ARRIVAL` | `16.0` | Mirrors `LAYER_ARRIVAL` (its bass-side analog) |
| `KICK_DENSITY_SHIFT` | `18.0` | Mirrors `PHASE` — it's a structural shift, not a layer arrival |

## Anti-double-fire contract with TRACK_CHANGE

Both `KICK_SWAP` and `SUB_LAYER_ARRIVAL` are designed to NOT fire on cross-track
moments — those belong to `TRACK_CHANGE` (which has a 6s cooldown, a track-id
confidence gate, and runs first in the `EventDetector` chain).

Two layered defenses keep the contract:

1. **Cooldown coexistence** (Task 1 cooldown table): when `TRACK_CHANGE` fires
   first, its 6s cooldown window already absorbs the centroid/sub jump that the
   new track brings in — but `KICK_SWAP` (14s) and `SUB_LAYER_ARRIVAL` (16s)
   have their own LONGER cooldowns that further suppress refire.

2. **BPM-stability gate** (SubLayerArrivalDetector only): if
   `|current_bpm - baseline_bpm| > 4.0`, the detector rotates its baseline and
   returns `None`. Dance-music tempo nudges stay within ±4 BPM; track changes
   almost always exceed it. This is the explicit T-17-02-02 mitigation.

`KickSwapDetector` does NOT have an analogous BPM gate by design — the
cooldown + the `TRACK_CHANGE` priority ordering is sufficient (a
within-track kick character change is not a tempo event, so a tempo gate
would over-suppress legitimate fires).

`KickDensityShiftDetector` falls under threat T-17-02-03 (silent-window
phantoms). It layers a `state.phase == "silent"` check on top of the
LOW_RMS gate so Phase 6's authoritative silence classification can suppress
phantom density events when RMS briefly spikes during ambient noise.

## Behavior tables

### KickSwapDetector (7 tests)

| Test | What it pins down |
|------|-------------------|
| `test_kick_swap_fires_on_centroid_shift` | 60Hz → 100Hz kick across 4.5s seeds + fires; `extra.delta_hz >= 12.0` |
| `test_kick_swap_no_fire_on_small_shift` | 60Hz → 65Hz (Δ=5) returns None |
| `test_kick_swap_no_fire_on_silent_audio` | RMS below LOW_RMS rejects BEFORE baseline seeding (`d.last_centroid_hz is None`) |
| `test_kick_swap_cooldown_blocks_repeat_fire` | Within-14s second shift returns None; baseline rotates so post-cooldown tick has a fresh anchor |
| `test_kick_swap_first_call_seeds_baseline_no_fire` | First call ever seeds + returns None; second call (>=4s later) with shifted centroid fires |
| `test_kick_swap_extra_dict_keys_and_types` | `extra` keys are exactly `{prev_centroid_hz, new_centroid_hz, delta_hz}`, all floats, delta non-negative (absolute) |
| `test_kick_swap_detector_is_re_exported_from_subpackage` | `from vibemix.state.detectors import KickSwapDetector` resolves |

### SubLayerArrivalDetector (7 tests)

| Test | What it pins down |
|------|-------------------|
| `test_sub_layer_arrival_fires_on_sub_jump_with_stable_bpm` | sub 0.20→0.35, bpm stable, `extra == {prev_sub: 0.20, new_sub: 0.35, sub_jump: 0.15}` |
| `test_sub_layer_arrival_no_fire_on_bpm_change` | sub jumps but BPM 130→145 → None (TRACK_CHANGE owns it; T-17-02-02 mitigation) |
| `test_sub_layer_arrival_no_fire_on_small_jump` | Δ=0.05 returns None |
| `test_sub_layer_arrival_silence_gate` | Below-LOW_RMS rejects BEFORE baseline seeding (`d.baseline_sub is None`) |
| `test_sub_layer_arrival_cooldown_16s` | Within-16s fire blocked even on bigger jump |
| `test_sub_layer_arrival_uses_state_bands_not_audio_buf` | `audio_buf=None` works — detector reads `state.bands["sub"]` only |
| `test_sub_layer_arrival_detector_is_re_exported_from_subpackage` | Re-export resolves |

### KickDensityShiftDetector (8 tests)

| Test | What it pins down |
|------|-------------------|
| `test_kick_density_shift_fires_on_jump_up` | 1.0→3.0 fires; `extra == {prev: 1.0, new: 3.0, delta: 2.0}` |
| `test_kick_density_shift_fires_on_jump_down` | 5.0→2.0 fires; signed `delta: -3.0` (direction preserved) |
| `test_kick_density_shift_no_fire_on_small_change` | 2.0→2.5 (Δ=0.5) returns None |
| `test_kick_density_shift_silence_gate_low_rms` | Below-LOW_RMS rejects + leaves baseline unset |
| `test_kick_density_shift_cooldown_18s` | Within-18s fire blocked |
| `test_kick_density_shift_baseline_rotation` | Slow-drift hygiene: ≥8s elapsed + no fire still rotates baseline |
| `test_kick_density_shift_no_fire_during_phase_silent` | `state.phase == "silent"` gates BEFORE density check (Phase 6 authoritative) |
| `test_kick_density_shift_detector_is_re_exported_from_subpackage` | Re-export resolves |

## Verification (plan §verification)

```text
$ pytest tests/state/detectors/ -x -q                  → 28 passed in 0.02s
$ pytest tests/state/ tests/audio/ -x -q               → 376 passed in 0.20s
$ python -c "from vibemix.state.detectors import \
    KickSwapDetector, SubLayerArrivalDetector, KickDensityShiftDetector; print('ok')"
                                                       → ok
$ grep -c "_lock" src/vibemix/state/detectors/*.py
    src/vibemix/state/detectors/__init__.py:1          ← docstring only, no code
    src/vibemix/state/detectors/_dsp.py:0
    src/vibemix/state/detectors/kick_density_shift.py:0
    src/vibemix/state/detectors/sub_layer_arrival.py:0
    src/vibemix/state/detectors/kick_swap.py:0
```

The single `_lock` match in `__init__.py` is a docstring sentence asserting the
Phase 3 single-writer invariant ("only `state_refresh_loop._tick_once` writes
inside `state._lock`") — not an actual lock acquisition. Verification rule
satisfied in spirit and in code.

## Resume-from-Task-1 context (for posterity)

This plan landed across two execution sessions. The first session (commit
`559d329`, 2026-05-14 04:07 UTC+3) shipped Task 1 only:

- `src/vibemix/state/detectors/__init__.py` (subpackage shell, empty `__all__`)
- `src/vibemix/state/detectors/_dsp.py` (`kick_band_centroid` + `sub_share`)
- `src/vibemix/audio/constants.py` extension (3 thresholds + 3 cooldown entries)
- `tests/state/detectors/__init__.py`, `tests/state/detectors/conftest.py`
  (the `_state(...)` and `_audio_sine(...)` fixtures)
- `tests/state/detectors/test_dsp_primitives.py` (6 tests)

Task 2 RED tests (`test_kick_swap.py`, `test_sub_layer_arrival.py`, 14 tests
total) were written between sessions but stayed UNTRACKED on disk. The second
session (this SUMMARY's session) staged them alongside the Task 2
implementations and committed them in commit `3420ff3`. Task 3 followed full
RED-then-GREEN: tests committed in `9fc279b`, impl in `c8cfaed`.

If a future executor needs to re-run only the post-Task-1 work, the canonical
diff range is:

```text
git log --oneline 559d329..HEAD
  3420ff3 feat(17-02): KickSwapDetector + SubLayerArrivalDetector — turn RED tests green
  9fc279b test(17-02): RED tests for KickDensityShiftDetector
  c8cfaed feat(17-02): KickDensityShiftDetector + tests — close Plan 17-02
```

## Deviations from Plan

Plan executed substantively as written. Two minor additions, both within the
plan's spirit:

1. **`test_kick_density_shift_detector_is_re_exported_from_subpackage`** — plan
   spec listed 7 tests for Task 3; added an 8th re-export sentinel for parity
   with `test_kick_swap.py` (also has a re-export test) and
   `test_sub_layer_arrival.py` (also has one). This is a Rule 2 addition (missing
   critical functionality — without it, a regression that breaks the
   `__init__.py` re-export would not be caught at the test-suite layer).

2. **Re-export ordering in `__init__.py`** — listed alphabetically
   (`KickDensityShiftDetector`, `KickSwapDetector`, `SubLayerArrivalDetector`)
   in `__all__` rather than wave-shipping order. Pure aesthetic; matches the
   stdlib convention. No behavioral impact.

No `mocker.patch('time.time')` was needed for Task 3: `KickDensityShiftDetector`
takes `now` as a parameter (matching the other two Phase 17 detectors), so
tests pass the timestamp directly without monkey-patching the system clock.

## Self-Check

- Files created (verified on disk):
  - `src/vibemix/state/detectors/kick_swap.py` — FOUND
  - `src/vibemix/state/detectors/sub_layer_arrival.py` — FOUND
  - `src/vibemix/state/detectors/kick_density_shift.py` — FOUND
  - `tests/state/detectors/test_kick_swap.py` — FOUND
  - `tests/state/detectors/test_sub_layer_arrival.py` — FOUND
  - `tests/state/detectors/test_kick_density_shift.py` — FOUND
- Commits (verified in `git log`):
  - `3420ff3` — FOUND
  - `9fc279b` — FOUND
  - `c8cfaed` — FOUND
- Test counts (verified by re-running pytest):
  - `tests/state/detectors/` — 28 passed
  - `tests/state/ tests/audio/` — 376 passed

## Self-Check: PASSED
