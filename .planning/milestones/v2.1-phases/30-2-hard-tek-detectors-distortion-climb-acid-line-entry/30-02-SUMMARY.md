---
plan: 30-02
phase: 30-2-hard-tek-detectors-distortion-climb-acid-line-entry
status: complete
wave: 1
requirements: [SENSE-18]
commits:
  - 1dc5399 # feat(30-02): ACID_LINE_ENTRY detector (SENSE-18)
tasks_completed: 1/1
tests_added: 6 + 9 router-chain assertions
tests_passing: 6/6 + router suite 12/12
regression_check: pytest tests/state/detectors/test_acid_line_entry.py → 6/6; full Phase-30 suite → 45/45
---

# Plan 30-02 Summary — ACID_LINE_ENTRY detector

## What was built

`AcidLineEntryDetector` — Hard Tek-only TB-303 acid-line detector firing on 200–800Hz formant-sweep + resonance-rise envelope. 8s cooldown. Wired into `build_hard_tek_chain` only (chain composition gates genre).

### DSP primitives added (`src/vibemix/state/detectors/_dsp.py`)

- **`dominant_freq_in_band(samples, sr, low_hz=200, high_hz=800)`** — frequency of max-magnitude bin in `[low_hz, high_hz]`. Out-of-band guard: if in-band energy < 1% of total → return 0.0 (anti-hallucination, won't claim acid on bass kicks). Silence → 0.0.
- **`band_resonance_q(samples, sr, low_hz=200, high_hz=800)`** — peak-to-neighbour ratio at the dominant in-band bin; proxy for TB-303 resonance Q.

### Detector (`src/vibemix/state/detectors/acid_line_entry.py`)

Fires on:
1. `dominant_freq_in_band` slope (octaves per second) ≥ `ACID_SWEEP_SLOPE_MIN_OCT_PER_S` — captures the formant sweep.
2. `band_resonance_q` rises by ≥ `ACID_RESONANCE_Q_RISE_MIN` vs baseline — the squelch/resonance signature.
3. Both gates must coincide in a sliding window.

Citation payload: `{formant_hz, resonance_q}`.

### Constants locked

- `ACID_SWEEP_SLOPE_MIN_OCT_PER_S`
- `ACID_RESONANCE_Q_RISE_MIN`
- `MIN_EVENT_GAP_PER_TYPE["ACID_LINE_ENTRY"] = 8.0`
- `EVENT_PRIORITY["ACID_LINE_ENTRY"] = 5`

### Wiring

- Exported via `src/vibemix/state/detectors/__init__.py`
- Added to `build_hard_tek_chain()` (chain now has 7 detectors total = techno baseline + DISTORTION_CLIMB + ACID_LINE_ENTRY)
- `test_hard_tek_chain_is_techno_plus_overlay_detectors`: asserts 7 detectors
- `test_techno_chain_does_not_contain_hard_tek_overlays` / `test_house_chain_does_not_contain_hard_tek_overlays`: assert overlays NOT present in other chains (chain composition is the genre gate)

### Bug fix folded in: circular-import in `genre_router.py`

`events.genres → state.detectors → state.__init__ → genre_router → events.genres` re-entry caused import-order failure when `events.genres` was the entry point. Fix: `GENRE_REGISTRY` import moved INSIDE `swap()` (lazy import). 14-line edit.

## Test surface

| File | Tests | Coverage |
|------|-------|----------|
| test_acid_line_entry.py | 6 | Fires on sweep+resonance combined; silence-gate; None audio_buf guard; flat tone (no sweep) rejected; resonance-rise gate enforced; cooldown blocks repeat |
| test_genre_router.py (extended) | +9 assertions | Hard Tek chain composition, techno/house chain exclusion of overlays, registry key alignment with `GENRE_BPM_BANDS` |

**Total: 6 new + 9 chain assertions, all pass.**

## Self-Check: PASSED

- [x] `AcidLineEntryDetector` fires on synthetic sweep+resonance fixture.
- [x] Two new DSP primitives covered (in-band silence guard prevents false positives on bass-heavy material).
- [x] Detector wired into `build_hard_tek_chain` only — confirmed by negative tests on techno/house chains.
- [x] Circular-import regression fixed; full router suite passes.
- [x] 8s cooldown enforced; chain length now 7 for `hard_tek`.

## What this unblocks

- Plan 30-04 references `ACID_SWEEP_SLOPE_MIN_OCT_PER_S` in `_DETECTOR_THRESHOLDS`.
- Plan 30-03 race test asserts the final 7-detector Hard Tek chain shape.
