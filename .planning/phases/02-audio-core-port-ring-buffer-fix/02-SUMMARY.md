---
phase: 02-audio-core-port-ring-buffer-fix
plan: rollup
type: summary
status: complete
completed_at: 2026-05-11
requirements_covered:
  - ARCH-07
  - AUDIO-01
  - AUDIO-06
  - AUDIO-07
  - AUDIO-08
  - AUDIO-09
wave_commits:
  - bb63774  # wave 1 — audio package skeleton + constants + Levels + errors
  - 59fdb62  # wave 2 — pre-allocated ring buffers (np.concatenate fix at v4:300 + v4:462)
  - 54e6432  # wave 3 — features.py DSP math + VoiceRecorder
  - 62413e9  # wave 4 — AudioMacOS impl + sample-rate sanity guard
---

# Phase 2 — Audio Core Port + Ring Buffer Fix — Summary

**Completed:** 2026-05-11
**Plan:** 02-audio-core-port-ring-buffer-fix / 5 plans across 5 waves (4 feat + 1 docs gate)
**Verdict:** All 8 acceptance gates PASS. Phase 2 is shipped.

## What Phase 2 Delivered

Pre-allocated ring buffers replace the v4 `np.concatenate`-per-callback regression at `cohost_v4.py:300` and `cohost_v4.py:462` (PITFALLS.md P5) — at 100Hz callback rate × 4.5MB ring, v4 was allocating ~900MB/s of throwaway ndarrays on the audio thread; the fix is structural (the ring never reallocates after construction). The concrete macOS audio backend (`AudioMacOS`) satisfies the Phase 1 `AudioBackend` Protocol with a non-negotiable sample-rate sanity guard (pre-open + post-open) that catches the BlackHole 44100/48000 trap Kaan hit live on 2026-05-11. `VoiceRecorder` writes 0o700 sessions (Kaan's voice = privacy-sensitive). The 14 LOAD-BEARING v4-tuned constants (French Touch / Daft Punk / Digitalism profile, 125-128 BPM) are now importable at `vibemix.audio.constants` — Phase 3 EventDetector + Phase 6 genre-aware override have a stable surface.

## Requirements Coverage

| Req | Description | How Phase 2 satisfied it |
|-----|-------------|--------------------------|
| ARCH-07 | Pre-allocated audio ring buffer (no `np.concatenate` in sounddevice callback) | `src/vibemix/audio/buffers.py` — all 4 buffer classes use pre-allocated `np.ndarray` (or `bytearray`) + write-pointer + `threading.Lock`. `tracemalloc` tests (RING-02, MicBuffer-equivalent) assert < 1KB allocated in `buffers.py` over 100 sustained 480-frame pushes. `grep -rE "np\.concatenate" src/vibemix/audio/` returns only docstring mentions. |
| AUDIO-01 | macOS audio capture via sounddevice (BlackHole auto-detect) | `AudioMacOS.find_device(name_substring, kind)` + `open_capture` — substring match + max_input_channels filter. Defaults `"BlackHole 2ch"` per `constants.MUSIC_GAIN_TO_GEMINI` consumer pattern. |
| AUDIO-06 | Master-output-only listening (no cue input) | `AudioMacOS.open_capture` opens against the user-selected input device only; no separate cue ingestion path. |
| AUDIO-07 | Mic gating during AI talk (port from POC) | `MicBuffer._current_gain` verbatim port of v4:449-457 — reads `levels.voice`, mutes when AI active, holds 350ms after AI silence. Tests RING-06 + RING-07 pin the behavior. |
| AUDIO-08 | TTS playback at 24kHz to user-selected output | `AudioMacOS.open_voice_output` — `sd.RawOutputStream(samplerate=24000, channels=1, dtype="int16")`. `PlaybackQueue` feeds the output callback. |
| AUDIO-09 | Voice-aware mic resumption + buffer flush after AI finishes | `_current_gain` falls back to `base_gain` once `time.time() - last_ai_active > 350ms` (MIC_HOLD_AFTER_AI_MS) AND levels.voice < AI_TALK_THRESHOLD. `PlaybackQueue.pull` on empty calls `levels.decay_voice` (×0.7) so voice drops to 0 within a few callbacks. |
| AUDIO-04 | Sample-rate sanity tone test | **Re-mapped:** Phase 2 ships sample-rate sanity *guard* (pre-open + post-open) which catches the misconfig at startup with an actionable error. A full 1kHz round-trip tone test is Phase 7's responsibility (REQUIREMENTS.md row says "Phase 7"). Phase 2's `assert_device_sample_rate` is the static-config guard; the round-trip is the live-signal guard. |
| AUDIO-02, AUDIO-03, AUDIO-05 | Windows + cross-platform + speakers picker | Deferred to Phase 7 (Windows port) — REQUIREMENTS.md explicitly maps these to Phase 7. |

## Files

**Created (18):**
- `src/vibemix/audio/__init__.py` — package re-exports
- `src/vibemix/audio/constants.py` — 14 LOAD-BEARING v4-tuned constants
- `src/vibemix/audio/errors.py` — `SampleRateMismatchError`
- `src/vibemix/audio/levels.py` — `Levels` (EMA RMS for music/voice/mic)
- `src/vibemix/audio/buffers.py` — `AudioBuffer`, `MicBuffer`, `PassthroughBuffer`, `PlaybackQueue` (all pre-allocated rings)
- `src/vibemix/audio/registry.py` — `BufferRegistry` frozen dataclass
- `src/vibemix/audio/features.py` — `snapshot_features`, `snapshot_wav`, `energy_curve`, `long_arc_curve`, `estimate_bpm`
- `src/vibemix/audio/recorder.py` — `VoiceRecorder` (0o700 sessions + configurable root)
- `src/vibemix/platform/_audio_macos.py` — `AudioMacOS` + `assert_device_sample_rate` + `_SoundDeviceStreamHandle`
- `tests/audio/__init__.py`, `tests/audio/conftest.py` — `int16_sine` helper
- `tests/audio/test_constants.py`, `test_levels.py`, `test_buffers.py`, `test_features.py`, `test_recorder.py`
- `tests/test_audio_macos.py`, `tests/test_audio_macos_live.py`

**Modified (3):**
- `src/vibemix/platform/__init__.py` — re-exports `AudioMacOS`, `assert_device_sample_rate`
- `pyproject.toml` — `pytest-mock>=3.15.1` dev dep + `macos_audio` pytest marker
- `tests/test_platform.py` — firewall AST scan now skips underscore-prefixed concrete impls (planned amendment per Plan 04 critical constraint #5)
- `uv.lock` — pytest-mock + transitive deps

**POC files touched:** 0. `cohost.py`, `cohost_v2.py`, `cohost_lk.py`, `cohost_v3.py`, `cohost_v4.py`, `cohost.streaming.py.bak`, `run*.sh`, `mascot.html`, `sprite-*.png`, `generate_bat.py`, `_test_*.py`, `test_voice.py`, `fillers/` untouched.

## Architectural Decisions Locked

| Decision | Rationale |
|----------|-----------|
| Pre-allocated `np.ndarray` + write-pointer + `threading.Lock` for AudioBuffer + MicBuffer | RESEARCH.md Q1: rolled our own (~30 LOC per class); `dvg-ringbuffer` / `numpy-ringbuffer` rejected as wrong-shape or stale. Zero-alloc on push. |
| `bytearray` for PassthroughBuffer + PlaybackQueue | PATTERNS.md §4-5: pure-byte pipelines (no math, no resample, no dtype). The `np.concatenate` bug doesn't exist there; lifted verbatim with drop-half (v4:487-492). |
| Pull policy: zero-pad inline everywhere | PATTERNS.md §7: drops v4 PassthroughBuffer-vs-PlaybackQueue inconsistency (v4 returned `b""` from one but zero-padded the other). Caller never branches on length. |
| 14 LOAD-BEARING constants in `vibemix.audio.constants` (module-level, NOT class-attrs) | 02-PATTERNS.md lifted `MUSIC_PRESENCE_MIN_SECONDS` + `BPM_VALID_MIN/MAX` OUT of EventDetector class-attrs so Phase 3 can import without dragging EventDetector along. |
| Two-layer sample-rate guard (pre-open + post-open) | RESEARCH.md Q2 empirically verified: `sd.query_devices(idx)['default_samplerate']` reflects Audio MIDI Setup state (pre-open); `Stream.samplerate` catches hardware drift on Multi-Output Devices (post-open). `sd.check_input_settings` is unreliable — DO NOT use. |
| `SampleRateMismatchError` typed exception (NOT generic Exception) | RESEARCH.md Security V7 + Plan 04 critical constraint #6. Phase 7 Windows port reuses the same exception type. Phase 11 calibration wizard catches it. |
| `VoiceRecorder` root configurable + session dir mode=0o700 | Fixes v4:773 `Path(__file__).parent` anti-pattern; RESEARCH.md Security V8 + ~/CLAUDE.md privacy posture (Kaan's voice = sensitive). |
| `features.py` separate from `buffers.py` (DSP free functions vs storage classes) | RESEARCH.md A1: free functions `(buf: AudioBuffer, ...)` are unit-testable without standing up the whole audio package. |
| `BufferRegistry` as `@dataclass(frozen=True)` | RESEARCH.md A3: cleaner than NamedTuple for type hints; immutable so the four buffer references can't be swapped after AudioMacOS construction. |
| `AudioMacOS` satisfies Protocol structurally (no inheritance) | Phase 1's `@runtime_checkable` makes `isinstance(x, AudioBackend)` work without an explicit base — clean composition. |
| Drop `_HAS_VISION` / `_HAS_WS` / `_HAS_QUARTZ` feature flags | PATTERNS.md §AntiPatterns-2: failed import = phase fails fast with a clear error. The platform firewall makes feature detection unnecessary. |

## Deviations from Plan

1. **Phase 1 firewall AST scan amended** (Rule 3 auto-fix): the original `tests/test_platform.py::test_no_os_leaks` AST-scanned EVERY `.py` under `platform/` including `_audio_macos.py`. Now skips underscore-prefixed concrete impls. Plan 04 explicitly anticipated this as a possible amendment ("if `tests/test_platform.py` flags `_audio_macos.py`, the test is over-broad"). The typing-only-module guarantee remains pinned via test RATE-11 in `tests/test_audio_macos.py`.

2. **`PassthroughBuffer.pull` zero-pads on underflow** (PATTERNS.md §7), diverging from v4:494-500's `b""` return. Documented in class docstring + RING-09 test pins the new behavior.

3. **`open_mic_capture` is AudioMacOS-only (not in Phase 1 Protocol)**. Phase 1's `AudioBackend` Protocol has 4 methods (find_device + 3 stream openers). Phase 2 ships a 5th (`open_mic_capture`) as a macOS-only extension fixing PATTERNS.md §AntiPatterns-5 (every other stream had a factory; mic didn't in v4). Phase 3 can amend Phase 1 if cross-platform mic surface is needed.

4. **`AudioBackend` not imported in `_audio_macos.py`** — ruff F401 flagged as unused. Structural Protocol check works without `AudioMacOS` declaring `AudioBackend` as a base or importing it. Test RATE-07 pins the isinstance contract.

## Dependent Phases Unlocked

| Phase | Depends on Phase 2 for | Imports |
|-------|------------------------|---------|
| 3 | Sensing & State Port | `from vibemix.audio import AudioBuffer, snapshot_features, energy_curve, long_arc_curve, estimate_bpm, Levels, BufferRegistry, MIN_EVENT_GAP_PER_TYPE, SILENT_RMS, LOW_RMS, PEAK_RMS, ...` |
| 4 | LiveKit Cascade Agent Pivot | `from vibemix.audio import PlaybackQueue, MicBuffer, VoiceRecorder, snapshot_wav, INVOKE_AUDIO_SECONDS` |
| 6 | Genre-Aware Phase Detection | `from vibemix.audio import constants` (override SILENT_RMS / LOW_RMS / PEAK_RMS per profile) |
| 7 | Windows Port | Reuses `BufferRegistry`, `VoiceRecorder`, all 4 buffer classes, and `features.py` verbatim — they're platform-agnostic. Writes `_audio_windows.py` against the same `AudioBackend` Protocol. Reuses `SampleRateMismatchError`. |
| 11 | Tauri / Calibration Wizard | Catches `SampleRateMismatchError` from `assert_device_sample_rate`, walks the user through Audio MIDI Setup. Phase 11 may also add programmatic BlackHole 48kHz config via CoreAudio API. |
| 15 | Recording & Session Capture | Wraps `VoiceRecorder` with retention policy + browser UI. The 0o700 perms + configurable root are already in place. |

## Open Items Carried Forward

1. **AUDIO-02 / AUDIO-03 / AUDIO-05** — Windows + cross-platform auto-detect + headphones/speakers picker → Phase 7
2. **AUDIO-04** — Full 1kHz round-trip tone test → Phase 7 (Phase 2 ships the static-config guard; the round-trip is the live-signal guard)
3. **BlackHole programmatic 48kHz config** via CoreAudio `AudioObjectSetPropertyData` → Phase 11 (calibration wizard)
4. **Genre-aware threshold override** → Phase 6 (Phase 2 ships v4-tuned defaults as the baseline)
5. **Recording retention policy + browser UI** → Phase 15
6. **Phase 1 Protocol amendment for `open_mic_capture`** → Phase 3 (if cross-platform mic surface needed) or Phase 7 (when Windows mic capture lands)
7. **v4 cohost.streaming.py.bak cleanup** → orthogonal; CONCERNS.md flagged it; not Phase 2's responsibility

## Verification Snapshot

| # | Check | Command | Result |
|---|-------|---------|--------|
| 1 | Zero `np.concatenate` in push paths | `grep -rE "np\.concatenate" src/vibemix/audio/` returns only docstring mentions | ✓ |
| 2 | tracemalloc zero-alloc test (AudioBuffer + MicBuffer) | `uv run pytest tests/audio/test_buffers.py::test_audio_buffer_push_zero_alloc_tracemalloc tests/audio/test_buffers.py::test_mic_buffer_push_zero_alloc_tracemalloc -v` | ✓ (2 passed) |
| 3 | 14 constants match v4 exactly | `uv run pytest tests/audio/test_constants.py -v` | ✓ (6 passed) |
| 4 | `AudioMacOS` satisfies `AudioBackend` isinstance | `python -c "isinstance(AudioMacOS(reg, rec), AudioBackend)"` → `True` | ✓ |
| 5 | `SampleRateMismatchError` on mismatch with actionable message | `uv run pytest tests/test_audio_macos.py::test_assert_device_sample_rate_raises_on_mismatch -v` | ✓ |
| 6 | All Phase 1 tests still pass | `uv run pytest tests/test_platform.py tests/test_package.py tests/test_license.py tests/test_signpath_checklist.py -x -q` | ✓ (10 passed) |
| 7 | ≥4 atomic `feat(02)` commits | `git log --oneline \| grep -cE "^[a-f0-9]+ feat\(02\)"` | ✓ (4) |
| 8 | POC files diff-untouched | `git diff --name-only HEAD~10..HEAD -- 'cohost*.py' ...` | ✓ (empty) |
| 9 | ruff check + format clean | `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/` | ✓ |
| 10 | Full suite (no live) green | `uv run pytest -x -q --ignore=tests/test_audio_macos_live.py` | ✓ (78 passed) |
| 11 | Live smoke discoverable under macos_audio marker | `uv run pytest -m macos_audio --collect-only` | ✓ (2 collected) |

## Commit History (Phase 2)

```
62413e9 feat(02): wave 4 — AudioMacOS impl + sample-rate sanity guard (pre/post-open)
54e6432 feat(02): wave 3 — features.py (DSP math) + VoiceRecorder (0o700 sessions + configurable root)
59fdb62 feat(02): wave 2 — pre-allocated ring buffers (fixes np.concatenate at v4:300 + v4:462)
bb63774 feat(02): wave 1 — audio package skeleton + constants + Levels + errors
e9f390a plan(02): audio core port + ring buffer fix — 5 plans across 5 waves
d19c0a1 docs(02): research — audio core port
da17a94 docs(02): pattern map — audio primitives (v4 baseline)
2916003 docs(02): smart discuss context — audio core port + ring buffer fix (v4 baseline)
```

(Final `docs(02): phase 2 complete` commit lands after Task 5.3 Kaan-approval + ROADMAP/STATE advance.)

## Self-Check

- File `src/vibemix/audio/buffers.py`: FOUND
- File `src/vibemix/audio/features.py`: FOUND
- File `src/vibemix/audio/recorder.py`: FOUND
- File `src/vibemix/audio/registry.py`: FOUND
- File `src/vibemix/audio/levels.py`: FOUND
- File `src/vibemix/audio/constants.py`: FOUND
- File `src/vibemix/audio/errors.py`: FOUND
- File `src/vibemix/audio/__init__.py`: FOUND
- File `src/vibemix/platform/_audio_macos.py`: FOUND
- File `tests/audio/test_buffers.py`: FOUND
- File `tests/audio/test_constants.py`: FOUND
- File `tests/audio/test_features.py`: FOUND
- File `tests/audio/test_levels.py`: FOUND
- File `tests/audio/test_recorder.py`: FOUND
- File `tests/test_audio_macos.py`: FOUND
- File `tests/test_audio_macos_live.py`: FOUND
- Commit `bb63774`: FOUND
- Commit `59fdb62`: FOUND
- Commit `54e6432`: FOUND
- Commit `62413e9`: FOUND

**Self-Check: PASSED**
