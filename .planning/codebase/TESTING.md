# Testing Patterns

**Analysis Date:** 2026-05-11

## Test Framework

**Runner:**
- None. No pytest, unittest, or any test framework is installed or configured.
- The `.venv` (Python 3.14) contains no `pytest`, `unittest2`, `nose`, or similar packages.
- No `pytest.ini`, `pyproject.toml`, `setup.cfg`, or `tox.ini` exist.

**Assertion Library:**
- None. No assertions in any test file.

**Run Commands:**
```bash
# No automated test runner. Files are run directly:
source .venv/bin/activate
set -a && source .env && set +a    # load env vars
python3 test_voice.py              # smoke test: Gemini Live API + audio output
python3 _test_tts.py               # smoke test: TTS endpoint
python3 _test_multimodal.py        # smoke test: Gemini multimodal audio reasoning
```

## Test File Classification

This project has **no automated tests**. The three "test" files are **manual integration smoke tests** that require:
- A live `GEMINI_API_KEY` environment variable
- Physical audio hardware (speakers, BlackHole 2ch virtual device)
- Network access to Google Gemini APIs
- Pre-recorded audio files in `recordings/` (for `_test_multimodal.py`)

They cannot be run in CI and produce no pass/fail output — only print statements and side effects (audio playback, file writes).

**File Roles:**

| File | Type | Purpose |
|------|------|---------|
| `test_voice.py` | Manual smoke test | Verify Gemini Live API → 24kHz PCM → speaker playback works end-to-end |
| `_test_tts.py` | Manual smoke test | Verify TTS endpoint returns valid PCM; writes `/tmp/test_tts.wav` |
| `_test_multimodal.py` | Manual smoke test | Verify Gemini multimodal can reason about a real audio chunk from `recordings/` |

**Leading underscore convention:** `_test_*.py` files are distinguished from `test_voice.py` by the underscore prefix, suggesting the author treats `_test_*` as "even more informal / helper scripts" vs the non-prefixed file as the primary smoke test. Neither category is automated.

## Test File Structure

`test_voice.py` (`/Users/ozai/projects/dj-set-ai/test_voice.py`):
```python
"""Smoke test docstring describing what passing means."""
async def main():
    # direct API call
    # collect response
    # play audio
    # print result

asyncio.run(main())  # no if __name__ == "__main__" guard
```

`_test_tts.py` (`/Users/ozai/projects/dj-set-ai/_test_tts.py`):
```python
"""Usage line in docstring showing how to run it."""
# module-level execution (not in a function)
api_key = os.environ.get("GEMINI_API_KEY") or sys.exit("GEMINI_API_KEY missing")
resp = client.models.generate_content(...)
# print info
# write output file
```

`_test_multimodal.py` (`/Users/ozai/projects/dj-set-ai/_test_multimodal.py`):
```python
"""Usage line in docstring."""
# hardcoded path to local recordings directory
rec_dir = Path("/Users/ozai/projects/dj-set-ai/recordings/20260510-132307")
# module-level execution
resp = client.models.generate_content(...)
print(resp.text)
```

## Mocking

**Framework:** None.

**What's mocked:** Nothing. All tests call real external APIs with real credentials.

**What's NOT mocked:** Gemini API, audio hardware, filesystem.

## Fixtures and Factories

**Test Data:**
- Hardcoded string literal in `_test_tts.py`: `TEXT = "yo this drop is sick bro"`
- Real recorded audio from `recordings/20260510-132307/input.wav` in `_test_multimodal.py`
- No factories, no fixture files, no synthetic data generation

**Location:** `recordings/` directory holds session recordings (`voice.wav`, `input.wav`, `events.jsonl`). These are created by the main application, not purpose-built test fixtures.

## Coverage

**Requirements:** None enforced.

**Coverage tooling:** Not installed — no `coverage.py`, `pytest-cov`, or similar in the venv.

## Test Types

**Unit Tests:** None. No isolated function or class tests exist.

**Integration Tests:** None automated. The three smoke test files test full API integration paths manually.

**E2E Tests:** Not applicable — the application is a real-time audio system requiring physical hardware and live API access.

## CI/CD

**No CI configuration detected.** No `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `Makefile`, or any CI config file exists in the repository.

## What IS Tested (Manually)

The smoke tests cover these three integration paths:

1. **Gemini Live API + audio output** (`test_voice.py`):
   - `client.aio.live.connect()` with `gemini-3.1-flash-live-preview`
   - `session.send_client_content()` → stream `response.data` (PCM)
   - `sd.play()` + `sd.wait()` on MacBook Pro Speakers

2. **TTS endpoint** (`_test_tts.py`):
   - `client.models.generate_content()` with `gemini-3.1-flash-tts-preview`
   - PCM extraction from `resp.candidates[0].content.parts[0].inline_data.data`
   - Output saved to `/tmp/test_tts.wav` (24kHz mono int16)

3. **Multimodal audio reasoning** (`_test_multimodal.py`):
   - `client.models.generate_content()` with `gemini-3-flash-preview`
   - Raw 16kHz PCM sent as `audio/pcm;rate=16000` blob
   - Response text printed for manual inspection

## What Is NOT Tested

Everything in the main application files is untested by automated means:

- `Levels`, `AudioBuffer`, `MicBuffer`, `PassthroughBuffer`, `PlaybackQueue`, `ScreenBuffer`, `TurnHistory`, `VoiceRecorder` — all buffer classes in `cohost.py`
- `AudioBuffer.snapshot_features()` — the numpy-based spectral analysis pipeline
- `AudioBuffer.estimate_bpm()` — autocorrelation BPM estimation in `cohost_v2.py`
- `classify_phase()` — energy curve → phase label logic in `cohost_v2.py`
- `derive_audible_deck()` / `derive_audible_track()` — deck inference logic in `cohost_v2.py`
- `ControllerState.handle_msg()` — MIDI message parsing in `cohost_lk.py` and `cohost_v2.py`
- `EventDetector.detect()` — the event detection pipeline in `cohost_v2.py`
- `AICoach.build_prompt()` — the prompt construction logic in `cohost_v2.py`
- All trigger heuristics in `trigger_loop` in `cohost.py`

The `AudioBuffer.snapshot_features()` method (pure numpy, no I/O) is the most testable function in the codebase and has zero test coverage.

## Adding Tests (If This Changes)

**Recommended framework:** `pytest` with `pytest-asyncio` for async tests.

**Install:**
```bash
source .venv/bin/activate
pip install pytest pytest-asyncio
```

**Where to put tests:**
- Co-locate with source or create `tests/` directory at project root
- Name files `test_*.py` (without leading underscore) for pytest discovery

**Highest-value tests to add (no external dependencies required):**
1. `AudioBuffer.snapshot_features()` — pure numpy, fully deterministic
2. `classify_phase()` — pure function on a list of floats
3. `ControllerState.handle_msg()` — pure state machine, mockable MIDI input
4. `derive_audible_deck()` — pure function on dicts
5. Thread safety of `AudioBuffer.push()` / `snapshot_features()` under concurrent access

---

*Testing analysis: 2026-05-11*
