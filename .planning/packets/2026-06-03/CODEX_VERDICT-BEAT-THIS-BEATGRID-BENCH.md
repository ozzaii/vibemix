# CODEX VERDICT - BEAT-THIS-BEATGRID-BENCH

Item: BEAT-THIS offline beatgrid bench
Packet: `.planning/packets/2026-06-03/CODEX_READY-BEAT-THIS-BEATGRID-BENCH.md`
Code SHA: `2ac6a313 feat(eval): add beatgrid comparison bench`
Date: 2026-06-03

## What Landed

- Added `scripts/eval/beatgrid_compare.py`, a dev-tooling-only JSON bench that compares:
  - A: live post-guard BPM (`estimate_bpm` -> `_stabilize_bpm` -> optional `validate_bpm`)
  - B: raw `estimate_bpm`
  - C: external `beat-this` CLI output parsed from `beat-this <file> --json=<tmp>.json`
- Added `tests/bench/test_beatgrid_compare.py` with torch-free stub coverage for:
  - octave-error detection (`65` vs `130`, double, 3:2, 3:4)
  - `beatgrid_compare_v1` report shape and ok threshold pass
  - new beat-this octave-failure rejection
  - CLI JSON-file parsing shape
- Encoded the corrected torch-free contract in the report, including the third lazy-only site:
  `src/vibemix/library/clap_engine.py:329 import torchaudio`.

## By-Eye Artifact

Automated bench logic proof:

```text
uv run pytest -q tests/bench/test_beatgrid_compare.py
....                                                                     [100%]
4 passed in 0.04s

uv run ruff check scripts/eval/beatgrid_compare.py tests/bench/test_beatgrid_compare.py
All checks passed!
```

Real-corpus readiness proof:

```text
uv run python scripts/eval/beatgrid_compare.py --manifest tests/bench/data/bpm_truth_manifest.json
beatgrid manifest not found: tests/bench/data/bpm_truth_manifest.json (needs Kaan/Rekordbox truth BPMs)
```

The bench refuses to fabricate a result without truth BPMs. That is the correct current state.

## Honest Gate

The harness is landed; the actual beat-this adoption verdict is still blocked on:

- `tests/bench/data/bpm_truth_manifest.json` with real Rekordbox/Kaan truth BPMs.
- The isolated `beat-this` CLI installed outside product deps.
- Kaan ear-checking 2-3 rows and making the adopt/discard call against the packet accept bar.

No product runtime, Tauri command, `pyproject.toml`, `uv.lock`, `src/vibemix/**`, or shipped Rust beat-this integration was touched.
