# Deferred Items — Phase 9 Wave 2

Items discovered during Wave 2 execution that are out of scope per the
deviation rules SCOPE BOUNDARY (only auto-fix issues DIRECTLY caused by
the current task's changes). Logged for follow-up; not blocking.

## Pre-existing failures (not caused by Wave 2)

### 1. `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4`

- **Failure:** `FileNotFoundError: cohost_v4.py`
- **Cause:** The Wave 2 executor worktree was created from a base that
  does not contain `cohost_v4.py` (untracked file at project root). The
  test hashes the POC v4 reference for byte-identity checks.
- **Fix:** Either commit `cohost_v4.py` (and v3 siblings) to the repo
  or skip these tests in worktree-only runs. Not a Wave 2 concern.

### 2. `tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke`

- **Failure:** `FileNotFoundError: cohost_v4.py`
- **Cause:** Same as #1 — depends on the untracked POC reference files.
- **Fix:** Same as #1.

### 3. `tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device`

- **Failure:** `RuntimeError: No output device matching 'Headphones'`
- **Cause:** Test machine lacks an output device named "Headphones".
  This is a live-audio test that runs against the host CoreAudio
  device list.
- **Fix:** Convert to opt-in (mark with `macos_audio` like
  `test_main_live.py`) or extend the device-name fallback list. Not a
  Wave 2 concern — Wave 2 touches no audio I/O code.
