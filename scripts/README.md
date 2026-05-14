# scripts/ — vibemix CI + build + tuning tooling

This directory hosts repo-side helpers (CI scripts, build helpers, one-off
generators) plus the Phase 17 detector tuning harness. Each script is
self-contained and runnable from the repo root with `.venv/bin/python`.

---

## tune_detectors.py — Phase 17 reference-WAV detector tuning harness (SENSE-16)

Drives one or more reference WAV files through the **full Phase 17 detector
pipeline** (`GenreRouter` + baseline `EventDetector` + 6 Wave-2 detectors)
and emits a per-fire CSV consumable by Kaan's Phase 16 ear-audit.

### Usage

```bash
.venv/bin/python scripts/tune_detectors.py track1.wav [track2.wav ...] --csv out.csv
```

Optional flags:

- `--csv PATH` — output CSV path. Default: `tuning_runs/<UTC-iso>.csv` under
  repo root.
- `--bpm-override FLOAT` — force `state.bpm` to this value for the run
  (default: derive via `estimate_bpm` from the audio).
- `--genre-override STR` — force `state.active_genre` to one of `house`,
  `techno`, `hard_tek`, `unknown` (default: derive via the same heuristic
  `state_refresh_loop` uses).

### CSV schema (CONTEXT D-locked, Plan 17-06)

| Column          | Type    | Meaning                                                      |
| --------------- | ------- | ------------------------------------------------------------ |
| `track`         | string  | Basename of the input WAV (e.g. `acid_loop_a.wav`)           |
| `t_seconds`     | float   | Synthetic detector-time of the fire (seconds since WAV start)|
| `bar_index`     | integer | `floor(t * bpm / 60 / 4)` — same formula PhraseBoundary uses |
| `detector_name` | string  | Event type — one of the baseline or chain detector names     |
| `score`         | string  | JSON-serialised `event.extra` payload at fire time           |
| `threshold`     | float   | Active detector threshold (best-effort representative value) |
| `fired`         | int     | Always `1` — one row per fire (NOT every-tick rows)          |

### Anchor tracks — Kaan-action

The harness needs real Hard Tek + 9 SKU reference tracks to validate
thresholds during Phase 16 ear-audit. STATE.md outstanding to-do:

> **Collect Hard Tek + 9 SKU reference tracks for P17 detector tuning
> harness. Hard Tek 7-10 anchor tracks especially — Kaan-owned.**

Suggested anchor location:

```
.planning/phases/17-hard-tek-detectors-v1-genrerouter-musicstate-extension/anchor_tracks/
```

The harness logs a clear `tune_detectors: no input WAV files` error and
exits 2 (UNIX usage-error convention) when called with no input — it does
NOT silently degrade or produce an empty CSV.

### Output directory — `tuning_runs/`

Default output path is `tuning_runs/<UTC-iso>.csv` under the repo root.
This directory is **gitignored** (per Plan 17-06 threat register
T-17-06-04 — accidental commit of large per-run CSVs). When tuning, copy
the relevant CSV to a documented path under `.planning/` if you want it
versioned alongside the threshold change it justifies.

### Recommended track length

60–300 seconds per WAV. Multi-hour input is supported but not optimised
(per T-17-06-01 — Kaan-only offline tool, no input-length enforcement).

### Format support

- WAV via stdlib `wave`: int16, int32, uint8 mono / stereo at any sample
  rate. Stereo is mixed to mono; non-16kHz is resampled via
  `scipy.signal.resample_poly`.
- Other formats (mp3, flac, m4a) are NOT supported — convert to WAV first.

---

## Other scripts

- `gen_sine.py` — generates the 1kHz / 1.5s calibration tone WAV used by
  the Phase 11 calibration wizard. Run once; commit the output.
- `build_sidecar.py` — PyInstaller wrapper that builds the Python sidecar
  binary for the Tauri shell.
- `check_ipc_schema.py` — JSON-Schema validator for `src/vibemix/ui_bus/`
  message schemas.
- `check_v5_*.sh` — Phase 14 v5 migration enforcement guards (CDJ Whisper
  v5 design-system rollout).
- `reset_first_run.py` — wipes the first-run wizard's TCC + state files for
  re-testing the wizard flow.
- `dist/` + `hooks/` + `reaction_reel/` — build-time + reaction-reel
  generation tooling (see in-tree docstrings).
