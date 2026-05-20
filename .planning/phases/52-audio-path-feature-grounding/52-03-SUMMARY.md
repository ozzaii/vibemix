# 52-03 SUMMARY — Grounded DSP genre auto-detector + tick wiring (GENRE-01)

**Requirements:** GENRE-01
**Status:** complete

## What shipped

A continuous, grounded DSP genre auto-detector that picks the active
`GenreProfile` from the features ALREADY computed each tick — no env-pin lock,
no new heavy deps, zero per-tick API cost. This is the fix for psytrance running
under techno's wrong band-signature + phase thresholds.

New module `src/vibemix/state/genre/genre_autodetect.py`, two additive
MusicState fields, single-writer tick wiring, the env-override flag plumbing,
and a 20-test anti-slop suite.

## Scoring axes + weights + gate constants

Per profile, three axes in [0, 1], combined as a weighted mean:

| axis | weight | rule |
|---|---|---|
| BPM | 0.4 | 1.0 inside `bpm_range`; linear falloff over `_BPM_TOLERANCE`=12 BPM; `bpm<=0` → 0 |
| bands | 0.4 | per-band MIDPOINT proximity `max(0, 1-|obs-mid|/_BAND_TOLERANCE)`, `_BAND_TOLERANCE`=0.08, averaged over sub/low/mid/high |
| crest | 0.2 | 1.0 inside `expected_crest_factor`; falloff over 3.0; `crest<=0` → neutral 0.5 |

**Why midpoint proximity for bands (the load-bearing decision):** psytrance's
band ranges are a SUBSET of techno's, so a pure "within-range" membership test
scores both 1.0 on a psy vector — the exact misclassification bug. Midpoint
distance separates them: at psytrance's midpoint the psy/techno confidence lead
is **0.106 > GENRE_TIE_MARGIN (0.08)**, so each profile scores itself.

**Gate constants:**
- `GENRE_CONFIDENCE_MIN = 0.55` — below it → `unknown`.
- `GENRE_TIE_MARGIN = 0.08` — best minus runner-up below it → `unknown`.

## How anti-slop is enforced

- **`unknown` fallback** below the confidence gate OR within the tie margin —
  never a false-confident guess. PROVEN: a high-band-dominant out-of-library
  vector (bpm 100, 0.50 high) scores 0.54 < gate → `unknown`; a clone-tie point
  → `unknown`.
- **No BPM lock → `unknown` outright** (`bpm<=0` short-circuit), mirroring
  `_classify_active_genre`'s anti-hallucination rule — no genre without a tempo.
- **Hysteresis** (`GenreHysteresis` + `apply_genre_hysteresis`): 3-tick dwell
  before a switch commits; oscillation resets the counter; `unknown` commits
  immediately (when confidence drops we stop claiming the old genre at once,
  mirroring `silent` in the phase `HysteresisState`).
- **Env override wins**: `__main__` sets `set_auto_enabled(VIBEMIX_GENRE_PROFILE
  not explicitly present)`. A DEFAULTED 'techno' does NOT count as a pin. When
  env-pinned, `_tick_once` still SCORES (honesty fields surfaced) but does NOT
  call `set_active_profile`.

## Single-writer wiring + env-pinned flag plumbing

`_tick_once` gained a lazy-defaulting `genre_hysteresis` kwarg (mirrors the
crest/vocal/phase loop-local lazy-defaults). Inside the existing
`with state._lock:` batch it scores from `bpm_cache` + band shares +
`smoothed_crest` over a once-cached profile library (`_cached_profiles()` — the
JSONs don't change at runtime), applies hysteresis, writes `state.detected_genre`
+ `state.genre_confidence`, and (when `is_auto_enabled()` and the committed genre
is real and differs from the active profile) calls `set_active_profile`.
`state_refresh_loop` creates one `GenreHysteresis` per session and threads it.

## No heavy deps + active_genre untouched

- `genre_autodetect.py` imports only `dataclasses.dataclass` + `GenreProfile`
  (numpy not even needed — pure arithmetic). No CLAP/MERT/OpenL3/torch.
- `_classify_active_genre` and the `state.active_genre = ...` write are
  **AST-verified IDENTICAL** to the pre-phase baseline (`e73893c`).
  `_stabilize_bpm` is also AST-verified identical.

## Genre-detector sanity (real assertions)

- `score_genre(144, {sub:0.40,low:0.27,mid:0.14,high:0.10}, 5.5)` → `psytrance`
  (NOT techno), conf ≥ 0.55.
- `score_genre(100, {sub:0.10,low:0.15,mid:0.25,high:0.50}, 2.0)` → `unknown`,
  conf < 0.55 (genuinely out-of-library).

## Verification (observed)

- `pytest -q tests/state/test_genre_autodetect.py` → **20 passed**.
- `pytest -q tests/state/test_refresh.py` → **43 passed** (40 existing + 3 new).
- `pytest -q tests/state/test_music_state.py` → **11 passed**.
- `pytest -q tests/state/ tests/agent/test_llm_factory.py` → **543 passed, 1 skipped** (pre-existing skip).
- `__main__` imports cleanly.

## Commits (5 atomic)

- `abaf13e` test(52-03): RED genre auto-detector scorer + hysteresis (GENRE-01).
- `b146427` feat(52-03): grounded DSP genre scorer + hysteresis, unknown fallback (GENRE-01).
- `a64a109` feat(52-03): MusicState detected_genre/genre_confidence + genre detector exports (GENRE-01).
- `9613360` feat(52-03): wire genre auto-detector into _tick_once single-writer batch (GENRE-01).
- `934b9cc` feat(52-03): env override wins over auto-detect via explicit auto-enabled flag (GENRE-01).
