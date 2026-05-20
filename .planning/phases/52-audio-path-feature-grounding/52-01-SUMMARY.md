# 52-01 SUMMARY — Audio path live + BPM/feature grounding (BRINGUP-02)

**Requirements:** BRINGUP-02
**Status:** complete

## What shipped

Three default-suite regressions that PIN the sensing-trust foundation, plus one
opt-in real-hardware recipe. **No production source was modified** — the audio
capture path, the 48 kHz guard, and the `_stabilize_bpm` median-ring stabilizer
(fd25337) already exist at HEAD; this plan drives and pins them.

### 1. 48 kHz guard pinned for the listening INPUT (`tests/audio/test_sample_rate_guard.py`)
Default-suite (mocked sounddevice, NO `macos_audio` marker). Pins the BlackHole
44.1k-vs-48k misconfig Kaan hit live 2026-05-11:
- 44100 device + expected 48000 → `SampleRateMismatchError` with actionable
  `44100` + `48` text, after a best-effort programmatic fix + Audio MIDI Setup pop.
- 48000 device → no raise, no fix attempt.
- the listening input path (`open_capture`) is guarded at `INPUT_SR_NATIVE==48000`
  via `assert_device_sample_rate(device_index, sample_rate)`.

### 2. BPM-to-bus grounding (`tests/state/test_bpm_bus_grounding.py`)
Drives the SHIPPED chain (`estimate_bpm` → `bpm_ring` → `_stabilize_bpm` →
`validate_bpm`) through `_tick_once` with the exact measured psytrance
harmonic-leak distribution (~66% @130, ~28% @194-200, scatter). `estimate_bpm`
is monkeypatched to pop raw samples; a real `bpm_ring`/`bpm_cache`/`last_bpm_at`
is threaded across 300 ticks like `state_refresh_loop` does. Asserts the
bus-facing `state.bpm` (read verbatim by ws_bus) **never exceeds
`BPM_VALID_MAX` (180)** for BOTH techno AND psytrance, and that the steady-state
median tracks the real ~130 tempo (not the 200 subdivision lock).

### 3. Feature-range grounding (`tests/state/test_feature_grounding.py`)
Replays silence → quiet sine → loud sine → frequency sweep through `_tick_once`
and asserts every audio-derived MusicState field is finite (`math.isfinite`, no
NaN/inf) and in range: `state.rms ≥ 0`, each band share in `[0,1]`,
`onset_density ≥ 0`. Silence tick → rms below `SILENT_RMS`, all bands 0; loud
tick → rms > 0, band-share sum ≤ ~1.05.

### 4. Live-tap recipe (`tests/test_audio_macos_live.py`, `macos_audio`)
Added `test_blackhole_input_is_48k_for_live_capture`: asserts the real BlackHole
input device default_samplerate == `INPUT_SR_NATIVE`. Its docstring is the
one-command live-tap recipe for Kaan's real-hardware sign-off.

## `_stabilize_bpm` (fd25337) + `estimate_bpm` NOT modified — only driven

Verified: the 4 commits touched ONLY test files (390 insertions, 0 src changes);
`git diff` shows `refresh.py` and `features.py` unchanged across the whole phase;
`_stabilize_bpm`'s body md5 is byte-identical pre/post.

## Was a real leak found through `validate_bpm`?

**No.** The replay passed as a pure regression. `_stabilize_bpm` already drops
anything outside [100,180] before the lower-median, so by the time
`validate_bpm` runs, `bpm_cache` is already in-band; psytrance's [138,150]
half/double snap cannot push an in-band value back out (e.g. 130→260/65 both
out of [138,150] → passthrough 130 ≤ 180). No source clamp was needed.

## Live-tap recipe surfaced for Kaan-action

Real multi-genre drive on Kaan's Mac is the deferred Kaan-action sign-off (per
the autonomous carveout). The recipe is in the test docstring:
play known-BPM track → BlackHole 2ch; `uv run python -m vibemix`; tap
`ws://127.0.0.1:8765`; confirm `music` moves + `bpm` in-band (never ~200) +
`detected_genre` matches or `unknown`.

## Note on `macos_audio` collection

The repo's pytest `addopts` does not auto-deselect `macos_audio`, so on Kaan's
Mac (BlackHole present) these opt-in tests run and pass (BlackHole IS at 48k
here) — a stronger outcome than skipping. CI runs only targeted e2e files, not
the full suite, so the marker has no CI impact. The new test follows the exact
convention of the 3 pre-existing `macos_audio` tests in the same file.

## Verification (observed)

- `pytest -q tests/audio/test_sample_rate_guard.py tests/state/test_bpm_bus_grounding.py tests/state/test_feature_grounding.py` → **9 passed**.
- `grep -c macos_audio tests/test_audio_macos_live.py` → 4 (≥2).

## Commits (4 atomic)

- `a8308e1` test(52-01): pin BlackHole 48kHz guard fires for the listening input (BRINGUP-02).
- `89dc422` test(52-01): regress state.bpm never exceeds BPM_VALID_MAX on harmonic-leak trace (BRINGUP-02).
- `0cae908` test(52-01): regress audio features stay finite + in-range across a synthetic set (BRINGUP-02).
- `d1753dc` test(52-01): macos_audio live-tap recipe — BlackHole input @48k for Kaan-action sign-off (BRINGUP-02).
