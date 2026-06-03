# CODEX VERDICT — B16 AUDIO KEY ESTIMATOR

**Item:** B16 — offline audio key estimator for untagged/folder libraries  
**Code SHA:** `20f7a189 feat(library): estimate missing keys from audio`  
**Date:** 2026-06-03

## What Landed

- Added `vibemix.library.key_estimator`: pure-numpy FFT chroma +
  Krumhansl-Kessler major/minor template matching.
- `library embed-folder` and `library ingest` now estimate missing keys by
  default and expose `--compute-key` / `--no-key`.
- Estimated keys are marked `key_source="numpy_ks"` in `TrackEntry`.
- The next-song suggestion engine can use the library row's key when the live
  deck seed withholds it.
- The live deck poller suppresses `numpy_ks` keys from `DeckTrack`, so an
  offline estimate can score pill/Viber options without becoming citable live
  deck proof or a spoken harmonic-clash input.

## User Value

A Free/Pro user with a folder-only or partly keyless library now gets real
Camelot data feeding the pill/Viber harmonic scorer instead of permanent
`key_unknown` neutrality, while Sven still does not present estimated keys as
live deck facts.

## Proof

No-speaker decode proof:

```json
{"camelot": "8B", "confidence": 0.3232, "musical": "C", "source": "numpy_ks"}
```

This came from a generated C-major WAV decoded through the same
`estimate_key(path)` / PyAV path used by ingest. No app/TTS/audio output was
launched.

Checks:

- `uv run pytest -q tests/library/test_key_estimator.py tests/library/test_folder_ingest.py tests/library/test_ingest.py tests/state/test_deck_poller.py tests/runtime/test_suggestion.py`
  - `117 passed`
- `uv run pytest -q tests/state/test_harmonics.py tests/intel/test_transition_scorer.py tests/library/test_track_relation.py`
  - `203 passed`
- `uv run pytest -q tests/intel/test_transition_judge.py tests/audio/test_deck_signal.py`
  - `15 passed`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_citation_strip_emit.py`
  - `28 passed`
- `uv run ruff check ...` on touched files
  - passed
- `git diff --check ...` on touched files
  - passed
- CLI help for `library embed-folder` and `library ingest`
  - both show `[--compute-key | --no-key]`.

## Corrections / Boundaries

- The packet's corrected premise held: `transition_judge.py` was not touched.
  Routing-disabled / executed-mix trust gates remain intact.
- Equal C/E/G triads can be relative-major/minor ambiguous, so the estimator
  abstains below the confidence floor instead of guessing.
- Live app/pill proof on a real folder-only crate remains pending a safe
  user-approved runtime session with real playback. This loop was verified with
  generated-audio decode + library/scorer tests to avoid speaker/TTS output.

