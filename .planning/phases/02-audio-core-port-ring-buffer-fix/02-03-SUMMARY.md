---
phase: 02-audio-core-port-ring-buffer-fix
plan: 03
type: summary
status: complete
completed_at: 2026-05-11
wave: 3
commit: 54e6432
---

# Wave 3 — features.py DSP Math + VoiceRecorder

**Commit:** `54e6432`

## What Wave 3 Delivered

- **features.py** — 5 free functions ported verbatim from `cohost_v4.py:304-436` (FFT pipeline, BPM autocorr, peak-normalize, RMS, onset detection, band-share split). Refactored from v4's `AudioBuffer` methods into free functions taking `(buf: AudioBuffer, ...)` per RESEARCH.md A1 so tests can build a tiny synthetic buffer and pin the dict shape without standing up the whole audio package.
- **recorder.py** — `VoiceRecorder` verbatim port of `cohost_v4.py:771-850` with two improvements: configurable `root: Path | None` (fixes v4:773 `Path(__file__).parent` anti-pattern), session dir `mode=0o700` (RESEARCH.md Security V8 + ~/CLAUDE.md privacy posture).

## Files Created

- `src/vibemix/audio/features.py` — `snapshot_features`, `snapshot_wav`, `energy_curve`, `long_arc_curve`, `estimate_bpm`
- `src/vibemix/audio/recorder.py` — `VoiceRecorder`
- `tests/audio/test_features.py` — 12 tests covering dict shape (empty + full), silent-rms gate, RIFF header, peak-normalize no-overflow + disabled, BPM range + short-buffer 0.0, energy_curve / long_arc_curve length + too-short empty
- `tests/audio/test_recorder.py` — 8 tests covering 0o700 perms, WAV headers (input + voice), session_start JSONL line, log_event roundtrip, configurable root, empty-bytes no-op, close() idempotence

## Files Modified

- `src/vibemix/audio/__init__.py` — re-exports the 5 features + VoiceRecorder

## Verification

- `uv run pytest tests/audio/ -x -q` — 55 tests green (14 W1 + 21 W2 + 20 W3)
- `uv run pytest -x -q` — full suite 65 green
- `uv run ruff check src/vibemix/audio tests/audio` — clean
- `uv run ruff format --check src/vibemix/audio tests/audio` — clean
- Peak-normalize: full-scale `np.full(16000, 32767, int16)` → snapshot_wav with -3 dBFS → min PCM value > -32768 (RESEARCH.md Pitfall 4 invariant pinned)
- Recordings session dir verified at mode 0o700 by `stat(...).st_mode & 0o777`

## Decisions

- DSP math = pure-function port; no algorithmic changes from v4
- `snapshot_features` returns the v4 dict EXACTLY as-is — Phase 3 EventDetector consumes this shape
- `VoiceRecorder` constructor sig: `__init__(self, root: Path | None = None)` — default is `Path.cwd() / "recordings"`, callers (Plan 04 AudioMacOS or Phase 15 UI) override the root for packaged installs / custom storage paths
- Defensive `os.chmod` after both `mkdir(mode=0o700)` calls — some platforms ignore the mode arg under umask

## Handoff to Wave 4

Plan 04 can now:
- `from vibemix.audio import BufferRegistry, VoiceRecorder` for the `AudioMacOS(registry, recorder)` constructor
- Caller-side callback factories (Phase 3+) use `snapshot_features` / `snapshot_wav` / `estimate_bpm` over the captured `AudioBuffer`

## Threat Mitigation

- **T-02-03-01 (Info Disclosure — recordings world-readable)**: mode=0o700 + defensive chmod pinned by REC-01
- **T-02-03-03 (Info Disclosure — int16 peak-normalize overflow)**: FEAT-05 fails CI if clip-before-cast invariant regresses
- **T-02-03-04 (Tampering — snapshot_features dict shape drift)**: FEAT-01 + FEAT-02 pin both 2-key and 7-key shapes
