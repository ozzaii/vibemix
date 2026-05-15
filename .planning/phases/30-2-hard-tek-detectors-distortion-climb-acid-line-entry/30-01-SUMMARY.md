---
plan: 30-01
phase: 30-2-hard-tek-detectors-distortion-climb-acid-line-entry
status: complete
wave: 1
requirements: [SENSE-17]
commits:
  - 2ff8907 # feat(30-01): DISTORTION_CLIMB detector (SENSE-17)
tasks_completed: 1/1
tests_added: 6
tests_passing: 6/6
regression_check: pytest tests/state/detectors/test_distortion_climb.py → 6/6; full Phase-30 suite → 45/45
---

# Plan 30-01 Summary — DISTORTION_CLIMB detector

## What was built

`DistortionClimbDetector` — Hard Tek-only spectral-flatness rise + harmonic-distortion proxy + sustained kick density. 6s cooldown. Wired into `build_hard_tek_chain` so it ONLY runs on Hard Tek sessions (chain composition is the genre gate — no per-detector active_genre check needed).

### DSP primitives added (`src/vibemix/state/detectors/_dsp.py`)

- **`band_spectral_flatness(samples, sr, low_hz=200, high_hz=2000)`** — Wiener entropy over Hanning-windowed rfft restricted to `[low_hz, high_hz]`. Uses log-sum trick `exp(mean(log(mag + 1e-12))) / (mean(mag) + 1e-12)` for numerical stability. Returns 0.0 on silence.
- **`harmonic_distortion_proxy(samples, sr, fundamental_hz=60)`** — odd-vs-even harmonic energy ratio at kick fundamental using FFT bin-window integration around each harmonic. Distinguishes saturated/clipped kicks from clean fundamentals.

### Detector (`src/vibemix/state/detectors/distortion_climb.py`)

Fires on combined gate:
1. Spectral flatness in 200–2000Hz rises by ≥ `DISTORTION_FLATNESS_DELTA_MIN` vs baseline window.
2. Harmonic-distortion proxy ≥ `DISTORTION_HARMONIC_RATIO_MIN`.
3. Sustained kick density (≥ `DISTORTION_KICK_DENSITY_MIN` for ≥ `DISTORTION_KICK_DENSITY_SUSTAIN_S`).

Citation payload: `{chain_position: 1-indexed, distortion_db: floor -60}`.

### Constants locked (`src/vibemix/audio/constants.py`)

- `DISTORTION_FLATNESS_DELTA_MIN`
- `DISTORTION_HARMONIC_RATIO_MIN`
- `DISTORTION_KICK_DENSITY_MIN`
- `DISTORTION_KICK_DENSITY_SUSTAIN_S`
- `MIN_EVENT_GAP_PER_TYPE["DISTORTION_CLIMB"] = 6.0`

### Wiring

- `EVENT_PRIORITY["DISTORTION_CLIMB"] = 5` (par with `MIX_MOVE`)
- Exported via `src/vibemix/state/detectors/__init__.py`
- Added to `build_hard_tek_chain()` in `src/vibemix/events/genres/hard_tek.py`

## Test surface

| File | Tests | Coverage |
|------|-------|----------|
| test_distortion_climb.py | 6 | Fires on synthetic clipped-60Hz-square + noise; silence-gate; None audio_buf guard; cooldown blocks repeat; density gate enforced; chain_position increments across fires |

**Total: 6 tests, 6 pass.**

## Self-Check: PASSED

- [x] Detector class lands at expected path with `Event` payload spec.
- [x] Two new DSP primitives unit-testable in isolation.
- [x] `MIN_EVENT_GAP_PER_TYPE` extended without breaking Phase 17 entries.
- [x] Wired into `build_hard_tek_chain` only — techno + house chains do NOT see it.
- [x] 6/6 detector tests pass; no regressions in DSP primitive tests.

## What this unblocks

- Plan 30-04 references `DISTORTION_FLATNESS_DELTA_MIN` in `_DETECTOR_THRESHOLDS` for tuning.
- Plan 30-03 race test relies on Hard Tek chain being stable (already locked here).
