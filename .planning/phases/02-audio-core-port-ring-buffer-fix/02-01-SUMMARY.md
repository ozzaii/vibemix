---
phase: 02-audio-core-port-ring-buffer-fix
plan: 01
type: summary
status: complete
completed_at: 2026-05-11
wave: 1
commit: bb63774
---

# Wave 1 — Audio Package Skeleton + Constants + Levels + Errors

**Commit:** `bb63774`

## What Wave 1 Delivered

Pure domain foundations: 14 LOAD-BEARING v4-tuned constants in `vibemix.audio.constants`, the verbatim `Levels` class (EMA RMS for music/voice/mic), the `SampleRateMismatchError` typed exception consumed by Plan 04, plus pytest-mock dev dep + `macos_audio` marker for Plan 05's opt-in BlackHole smoke. Zero OS imports — Plans 02/03/04 can `from vibemix.audio import …` freely without circular-dep or platform-coupling risk.

## Files Created

- `src/vibemix/audio/__init__.py` — public re-exports for every constant + Levels + SampleRateMismatchError
- `src/vibemix/audio/constants.py` — 14 constants verbatim from `cohost_v4.py:100-143` + `:1178-1182` (3 lifted OUT of EventDetector class-attrs per 02-PATTERNS.md)
- `src/vibemix/audio/levels.py` — verbatim port of `cohost_v4.py:255-286`
- `src/vibemix/audio/errors.py` — `SampleRateMismatchError(Exception)` with macOS Audio MIDI Setup docstring
- `tests/audio/__init__.py` — empty
- `tests/audio/conftest.py` — `int16_sine` helper (plain function, not fixture)
- `tests/audio/test_constants.py` — 6 tests covering all 14 constants
- `tests/audio/test_levels.py` — 8 tests covering EMA coefficients + empty-bytes early-return + snapshot-is-fresh-dict + sine helper

## Files Modified

- `pyproject.toml` — `pytest-mock>=3.15.1` in `[dependency-groups].dev`; `macos_audio` marker registered in `[tool.pytest.ini_options].markers`
- `uv.lock` — pytest-mock 3.15.1 + its deps resolved

## Verification

- `uv run python -c "from vibemix.audio import Levels, SILENT_RMS, ..., SampleRateMismatchError"` succeeds
- `uv run pytest tests/audio/ -x -q` — 14 new tests green
- `uv run pytest -x -q` — full suite 24 green (10 Phase 1 + 14 Wave 1)
- `uv run ruff check src/vibemix/audio tests/audio` — clean
- `uv run ruff format --check src/vibemix/audio tests/audio` — clean
- POC files untouched (`git diff --name-only HEAD~1..HEAD` excludes them)

## Decisions

- `__all__` sorted isort-style (uppercase-first) per RUF022 auto-fix
- Tests use `lv` instead of `l` to avoid E741 (ambiguous variable name)
- `MIN_EVENT_GAP_PER_TYPE` typed as `dict[str, float]` via PEP 585 inline annotation
- The 3 EventDetector class-attrs (`MUSIC_PRESENCE_MIN_SECONDS`, `BPM_VALID_MIN/MAX`) are now module-level so Phase 3 doesn't need EventDetector to import them — 02-PATTERNS.md refactor improvement

## Handoff to Wave 2

Plans 02/03/04 can now:
- `from vibemix.audio import AI_TALK_THRESHOLD, MIC_GAIN_AT_AI_TALK, MIC_HOLD_AFTER_AI_MS` for `MicBuffer._current_gain`
- `from vibemix.audio import Levels` for `MicBuffer` / `PlaybackQueue` constructor
- `from vibemix.audio.errors import SampleRateMismatchError` for `_audio_macos.assert_device_sample_rate`
