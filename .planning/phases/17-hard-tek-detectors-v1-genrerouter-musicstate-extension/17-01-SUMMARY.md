---
phase: 17-hard-tek-detectors-v1-genrerouter-musicstate-extension
plan: 01
subsystem: state
tags: [musicstate, genre-router, hard-tek, sense-13, sense-15]
requirements: [SENSE-13]
dependency-graph:
  requires:
    - vibemix.state.music_state.MusicState (Phase 6 baseline)
    - vibemix.audio.constants.BPM_VALID_MIN/MAX (Phase 3)
    - vibemix.audio.energy_curve / snapshot_features (Phase 4)
    - vibemix.audio.compute_downbeat_phase (Phase 13)
  provides:
    - vibemix.state.MusicState.{buildup_score, predicted_drop_in_sec, beat_phase, active_genre}
    - vibemix.audio.constants.{GENRE_BPM_BANDS, BUILDUP_SLOPE_WINDOW_S, GENRE_CENTROID_HARD_TEK_MIN}
    - vibemix.state.refresh._classify_active_genre (private helper)
    - vibemix.state.refresh._compute_buildup_score (private helper)
  affects:
    - Phase 17 Wave 2 detector plans (KICK_SWAP, SUB_LAYER_ARRIVAL, BREAKDOWN_KICK_KILL,
      REENTRY_KICK_LAND, KICK_DENSITY_SHIFT, PHRASE_BOUNDARY) — read these fields
    - Phase 17 Wave 3 GenreRouter — atomic swap on active_genre change
    - Phase 19 ack bank — must honor predicted_drop_in_sec=None as "predictive OFF"
tech-stack:
  added: []
  patterns:
    - Single-writer state extension (Phase 3 invariant preserved)
    - Backward-compat dataclass defaults for golden-equivalence regression
    - Anti-hallucination band gates ("trust the audio" rule from v4)
key-files:
  created:
    - tests/audio/test_phase17_constants.py
  modified:
    - src/vibemix/state/music_state.py
    - src/vibemix/audio/constants.py
    - src/vibemix/state/refresh.py
    - tests/state/test_music_state.py
    - tests/state/test_refresh.py
decisions:
  - "predicted_drop_in_sec stays None by default (predictive drop firing OFF in v2.0)"
  - "hard_tek upper bound anchored to BPM_VALID_MAX (genre router shares autocorr-noise-reject ceiling)"
  - "Hard Tek band requires (mid_share + high_share) >= 0.55 (centroid floor blocks house-with-fast-tempo misclassify)"
  - "buildup_score clamps negative slopes to 0.0 (buildups are monotonic-climbs only)"
  - "beat_phase is a Phase-17-named alias of downbeat_phase (no new computation, mirror in single-writer)"
metrics:
  duration_minutes: 7
  completed: 2026-05-14
  tasks_total: 2
  tasks_complete: 2
  files_changed: 5
  tests_added: 9
  tests_passing_in_targeted_suite: 47
  tests_passing_in_state_suite: 289
  tests_passing_in_state_plus_audio: 348
---

# Phase 17 Plan 01: MusicState Extension + GenreRouter Foundation Summary

MusicState gained 4 Phase 17 fields (`buildup_score`, `predicted_drop_in_sec`,
`beat_phase`, `active_genre`) populated synchronously by the existing
single-writer `_tick_once` block; `vibemix.audio.constants` exposes the genre
band table + buildup window for Wave 2 detectors. Phase 3/6/13 golden-equivalence
holds (348 state+audio tests green); no new I/O.

## What Shipped

### MusicState (`src/vibemix/state/music_state.py`)

Four new fields appended **AFTER** `downbeat_phase` (the related rhythmic
derivation block) and **BEFORE** the controller block. All carry v4-compatible
inert defaults so Phase 3 golden-equivalence regression stays green.

| Field | Type | Default | Written by | Read by |
|-------|------|---------|------------|---------|
| `buildup_score` | `float` | `0.0` | `_tick_once` (every tick) | Wave 2 detectors |
| `predicted_drop_in_sec` | `float \| None` | `None` | **never** in v2.0 (OFF by default) | Wave 2 detectors / Phase 19 ack bank |
| `beat_phase` | `float` | `0.0` | `_tick_once` (mirrors `downbeat_phase`) | SENSE-12 Wave 2 detectors |
| `active_genre` | `str` | `"unknown"` | `_tick_once` (every tick) | GenreRouter (Wave 3) |

Section comment block in source documents the OFF-by-default sentinel for
`predicted_drop_in_sec` and the anti-hallucination rule ("never fabricate a
genre during BPM lock-up").

### Constants (`src/vibemix/audio/constants.py`)

```python
GENRE_BPM_BANDS: dict[str, tuple[float, float]] = {
    "house":    (118.0, 128.0),
    "techno":   (128.0, 138.0),
    "hard_tek": (140.0, BPM_VALID_MAX),   # 180.0 — anchored to autocorr-noise-reject ceiling
    "unknown":  (0.0,   0.0),
}
BUILDUP_SLOPE_WINDOW_S: float = 8.0
GENRE_CENTROID_HARD_TEK_MIN: float = 0.55
```

Bands are **non-overlapping** by design — gaps (128-128, 138-140) → "unknown"
("trust the audio" — don't force-classify ambiguous tempos).

### `_classify_active_genre(bpm, feats)` helper

```text
1. bpm <= 0 OR not in BPM_VALID_MIN..BPM_VALID_MAX → "unknown"
   (anti-hallucination: no fabricated genre during BPM lock-up)
2. centroid = feats["mid_share"] + feats["high_share"]
3. For each (name, (lo, hi)) in GENRE_BPM_BANDS (skip "unknown"):
     match = lo <= bpm < hi  OR  (name == "hard_tek" AND bpm == hi)
     if match:
       if name == "hard_tek" AND centroid < GENRE_CENTROID_HARD_TEK_MIN:
         return "unknown"   # distorted-kick spectral signature gate
       return name
4. fall-through → "unknown"
```

The hard_tek **upper-equality** carve-out (`bpm == hi`) catches BPMs landing
exactly at `BPM_VALID_MAX = 180.0` — without it the autocorr ceiling would
silently fall into the fall-through branch.

### `_compute_buildup_score(curve, window_s, hop_s=1.0)` helper

```text
n = int(window_s / hop_s)            # → 8 samples for window_s=8.0, hop=1.0
tail = curve[-n:]                     # last 8s of energy_curve
slope = numpy.polyfit(0..n, tail, 1)[0]
if slope <= 1e-9:                     # epsilon floor catches polyfit float noise on flat curves
  return 0.0                          # also catches negative slopes — buildups are monotonic-climbs only
max_recent = max(0.05, max(tail))     # avoid divide-by-zero on silence
score = (slope * window_s) / max_recent
return clip(score, 0.0, 1.0)
```

**Bound contract:** `buildup_score ∈ [0.0, 1.0]`. Cost: numpy polyfit on n=8
is O(n) ≈ µs (T-17-01-03 in threat register; tick budget is 100ms,
crest+BPM autocorr already dwarf this).

### Single-writer wiring (`src/vibemix/state/refresh.py`)

Three of four new fields written inside the existing `with state._lock:` block
in `_tick_once`, immediately after `state.downbeat_phase`/`state.bpm_confidence`:

```python
state.active_genre = _classify_active_genre(bpm_cache, feats)
state.buildup_score = _compute_buildup_score(curve, BUILDUP_SLOPE_WINDOW_S)
state.beat_phase = state.downbeat_phase
# state.predicted_drop_in_sec is intentionally NOT written — stays at None
```

`feats` and `curve` are reused from the Phase 6 path above — **zero new audio I/O**.

## Predicted Drop Sentinel — Confirmation

`state.predicted_drop_in_sec` is **never written** by `_tick_once` in v2.0.
Verified by `grep -c "state\.predicted_drop_in_sec" src/vibemix/state/refresh.py`
returning `0`. The dataclass default `None` is the OFF-by-default sentinel that
downstream Phase 17 detectors and the Phase 19 ack bank MUST honor. Predictive
drop firing turn-on is v2.1 telemetry-guard work.

## Single-Writer Invariant — Confirmation

`grep -n "with state\._lock:" src/vibemix/state/refresh.py` reports:

- Line 26 — module docstring text (inert)
- Line 225 — the **single executable writer block**

Pre-task baseline (HEAD~2) had the same count (docstring already mentioned the
phrase). Phase 3 single-writer invariant preserved.

## Test Coverage

### `tests/state/test_music_state.py` (modified)

- `test_default_construction_exposes_22_fields` → `_26_fields` (extended with
  4 new field asserts).
- `test_phase_17_fields_have_backward_compat_defaults` (NEW) — explicit
  per-field asserts on all 4 new defaults PLUS every pre-Phase-17 default.
  Locks T-17-01-04 (silent default-drift would break Phase 3 / Phase 6).
- `test_phase_17_field_types_via_dataclass_fields` (NEW) — introspects
  `dataclasses.fields(MusicState)` and asserts type annotations are
  `float`, `float | None`, `float`, `str` for the new fields.

### `tests/audio/test_phase17_constants.py` (NEW)

- `test_genre_bpm_bands_constant_shape` — keys + tuple shape.
- `test_genre_bpm_bands_values_match_context_d04` — band values + hard_tek
  upper bound equals `BPM_VALID_MAX` (locks SENSE-15 contract).
- `test_buildup_slope_window_is_positive_float` — pins 8.0s.
- `test_genre_centroid_hard_tek_min_is_in_unit_range` — pins 0.55.

### `tests/state/test_refresh.py` (extended)

- `test_tick_writes_active_genre_house` — bpm=124.0 → "house".
- `test_tick_writes_active_genre_hard_tek_requires_centroid` — bpm=150.0 with
  centroid 0.40 → "unknown"; with 0.60 → "hard_tek".
- `test_tick_writes_buildup_score_from_energy_curve_slope` — climb / flat /
  fall (negative slope clamp).
- `test_tick_writes_beat_phase_mirroring_downbeat_phase` — alias mirror.
- `test_tick_keeps_predicted_drop_in_sec_none_by_default` — sentinel intact.
- `test_tick_with_invalid_bpm_yields_unknown_genre` — bpm=0.0 → "unknown".

### Regression coverage

- `pytest tests/state/test_music_state.py tests/state/test_refresh.py tests/audio/test_phase17_constants.py` — 47/47 pass.
- `pytest tests/state/` — 289/289 pass (Phase 3 / Phase 6 / Phase 13 net).
- `pytest tests/state/ tests/audio/` — 348/348 pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Epsilon-floor on `_compute_buildup_score` slope**
- **Found during:** Task 2 GREEN run.
- **Issue:** numpy `polyfit(deg=1)` returns ~1e-16 (not exact 0.0) for a
  perfectly flat curve, breaking the contract that flat curves yield
  `buildup_score == 0.0`. Test
  `test_tick_writes_buildup_score_from_energy_curve_slope` failed on the
  flat-curve assertion with `7.5e-16 == 0.0`.
- **Fix:** Tightened the slope rejection from `slope <= 0.0` to
  `slope <= 1e-9` — below this threshold the slope is numerically
  indistinguishable from "no slope" given that `energy_curve` values
  are themselves rounded by `snapshot_features`.
- **Files modified:** `src/vibemix/state/refresh.py` (`_compute_buildup_score`).
- **Commit:** `2ebc6b4`.

**2. [Note - not a deviation] Hard Tek band-edge carve-out**
- The default Python band-match `lo <= bpm < hi` would silently miss
  `bpm == BPM_VALID_MAX` (180.0). Added an `OR (name == "hard_tek" and
  bpm == hi)` clause so the autocorr ceiling boundary is captured by the
  hard_tek band rather than the fall-through "unknown". Documented in the
  helper docstring; no test currently exercises bpm=180.0 exactly because
  autocorr noise rejection rarely lands precisely on the edge — the carve-out
  is defense-in-depth.

### Architectural changes
None.

### Authentication gates
None.

## Self-Check: PASSED

- `src/vibemix/state/music_state.py` — FOUND (modified)
- `src/vibemix/audio/constants.py` — FOUND (modified)
- `src/vibemix/state/refresh.py` — FOUND (modified)
- `tests/state/test_music_state.py` — FOUND (modified)
- `tests/state/test_refresh.py` — FOUND (modified)
- `tests/audio/test_phase17_constants.py` — FOUND (created)
- Commit `a407ed5` (Task 1) — FOUND in `git log --oneline --all`
- Commit `2ebc6b4` (Task 2) — FOUND in `git log --oneline --all`

## TDD Gate Compliance

This plan executed task-level TDD (RED → GREEN per task), not plan-level.
Per-task RED→GREEN sequence:

- **Task 1 RED:** `pytest tests/audio/test_phase17_constants.py` failed with
  `ImportError: cannot import name 'BUILDUP_SLOPE_WINDOW_S'` (constants not
  yet defined).
- **Task 1 GREEN:** appended fields + constants → 15/15 tests pass.
- **Task 1 commit:** `a407ed5` (`feat(17-01): extend MusicState with 4 Phase 17 fields + genre constants`).
- **Task 2 RED:** 3 of 6 new tests failed (`active_genre`, `buildup_score`
  assertions); 3 passed coincidentally because they pin invariants the new
  code must preserve (None default, alias mirror, invalid-bpm "unknown").
- **Task 2 GREEN:** wired `_classify_active_genre` + `_compute_buildup_score`
  + the 3-line writer block → 47/47 (Task 1+2) pass; 348/348 state+audio
  regression net intact.
- **Task 2 commit:** `2ebc6b4` (`feat(17-01): populate Phase 17 fields in state_refresh_loop single-writer`).

Plan-level frontmatter is `type: execute` (not `type: tdd`), so the plan-level
test/feat/refactor gate sequence does not apply. Task-level `tdd="true"` was
honored on both tasks.
