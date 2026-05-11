# Phase 7 — Deferred Items (out-of-scope discoveries)

Pre-existing test failures discovered during plan 07-01 execution.
None caused by Wave 1 changes; logged here per scope-boundary rule (do not fix).

## 1. `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` — `cohost_v4.py` not found

- **Failure:** `FileNotFoundError: [Errno 2] No such file or directory: 'cohost_v4.py'`
- **Cause:** `cohost_v4.py` is an untracked POC reference file (per memory `project_v4_canonical_baseline.md`). It exists in Kaan's main checkout but not in this Claude Code worktree (worktrees only see tracked files).
- **Why ignored:** Pre-existing on the worktree base commit `6e6dd9f`; not introduced by Wave 1.
- **Real fix (post-phase-7):** make the test skip gracefully when `cohost_v4.py` is absent, OR commit `cohost_v4.py` (Kaan must approve since it's currently kept untracked).

## 2. `tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke` — `cohost_v4.py` not found

- **Failure:** Same as above — reads `cohost_v4.py` to checksum it.
- **Cause:** Same as #1.
- **Why ignored:** Same as #1.

## 3. `tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device` — "No output device matching 'Headphones'"

- **Failure:** `RuntimeError: No output device matching 'Headphones'. Available output devices: ['BlackHole 16ch', 'BlackHole 2ch', 'MacBook Pro Speakers', 'rekordbox Aggregate Device', 'HEADPHONEMG', 'Aggregate Device', 'AIDJ', 'AIDJ', 'Multi-Output Device', 'AI Capture']`
- **Cause:** Environmental — Kaan's CoreAudio device list has "HEADPHONEMG", not "Headphones". The test hardcodes "Headphones" as the substring.
- **Why ignored:** Pre-existing on the worktree base commit; not introduced by Wave 1.
- **Real fix:** broaden the substring (e.g., "Headphone" with capital H) OR mark the test `@pytest.mark.macos_audio` opt-in like the BlackHole smoke tests.
