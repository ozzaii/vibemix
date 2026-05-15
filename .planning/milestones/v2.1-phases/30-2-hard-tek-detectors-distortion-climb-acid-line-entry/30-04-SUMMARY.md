---
plan: 30-04
phase: 30-2-hard-tek-detectors-distortion-climb-acid-line-entry
status: complete
wave: 2
requirements: [SENSE-20]
commits:
  - beb7fe4 # feat(30-04): tune_detectors Hard Tek extension + corpus README (SENSE-20)
tasks_completed: 1/1
tests_added: 3 (+ harness regression already in tests/scripts)
tests_passing: 12/12 in tests/scripts/test_tune_detectors.py (3 new + 9 existing)
regression_check: full Phase-30 suite → 45/45
kaan_action: HARDTEK-CORPUS-001 surfaced in KAAN-ACTION-LEGAL.md (non-blocking)
---

# Plan 30-04 Summary — tune_detectors Hard Tek extension + corpus README

## What was built

`scripts/tune_detectors.py` now recognises the two new overlay event types. Acquisition policy + per-track sidecar shape for the Hard Tek reference corpus is documented. Curation pass surfaces as a Kaan-action (non-blocking — synthetic fixtures already cover both detectors in CI).

### `scripts/tune_detectors.py`

- `_DETECTOR_THRESHOLDS` extended with:
  - `"DISTORTION_CLIMB": DISTORTION_FLATNESS_DELTA_MIN`
  - `"ACID_LINE_ENTRY":  ACID_SWEEP_SLOPE_MIN_OCT_PER_S`
- Per-fire CSV rows now carry a meaningful threshold column for both overlays.
- Module docstring + CLI epilog mention the new corpus location.
- Hard Tek invocation: existing `--genre-override=hard_tek` flag forces the router into the `hard_tek` chain — no new CLI surface needed.

### `eval/corpus/hard_tek/README.md` (new)

- Acquisition policy: archive.org / CCMixter / FMA, **CC-BY only — no DRM**.
- Per-track sidecar JSON template: `expected_fires` list with `(event_type, t_start, t_end)` tuples.
- Curated 5-track template (anchor list pending Kaan curation).
- Tuning-run invocation snippet using `--genre-override=hard_tek`.

### `.planning/KAAN-ACTION-LEGAL.md`

- New entry `HARDTEK-CORPUS-001`: surfaces curation pass as non-blocking Kaan-action. Synthetic fixtures cover both detectors in CI; real-track F1 scoring waits on acquisition.

## Test surface

| File | Tests | Coverage |
|------|-------|----------|
| test_tune_detectors.py (3 new) | 3 | `_DETECTOR_THRESHOLDS` includes both Phase 30 overlays; harness help epilog mentions Phase 30 corpus path; `eval/corpus/hard_tek/README.md` exists |

Existing 9 harness tests still pass (synth-kick WAV, BPM matching, breakdown section, EventDetector wiring, breakdown WAV fires KICK_KILL → KICK_REENTRY).

**Total: 3 new + 9 regression = 12/12 in `tests/scripts/test_tune_detectors.py`.**

## Self-Check: PASSED

- [x] `_DETECTOR_THRESHOLDS` exposes both new event types.
- [x] Corpus README documents source/licence/sidecar shape.
- [x] Kaan-action surfaced — explicit non-blocker.
- [x] CI tuning pipeline unaffected by real-track absence.

## What this unblocks

- Once Kaan curates the anchor track set, threshold tuning loop produces real-track F1 scores for the new overlays.
- Phase 31+ tuning workflow already wired for any new genre overlays via the same `_DETECTOR_THRESHOLDS` extension pattern.
