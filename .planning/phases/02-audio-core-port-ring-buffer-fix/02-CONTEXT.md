# Phase 2: Audio Core Port + Ring Buffer Fix - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning
**Canonical POC baseline:** `cohost_v4.py` (NOT v3 — v4 supersedes after Kaan's live tuning session 2026-05-11)

<domain>
## Phase Boundary

Port the audio I/O + level/buffer primitives from `cohost_v4.py` into the `src/vibemix/` package, killing the `np.concatenate`-per-callback regression (PITFALLS.md P5) by introducing pre-allocated ring buffers. macOS audio I/O works end-to-end via `src/vibemix/platform/_audio_macos.py` (concrete impl of the Phase 1 `AudioBackend` Protocol).

**In scope:**
- `src/vibemix/audio/` package with `Levels`, `AudioBuffer` (16kHz mono int16 ring), `MicBuffer` (48kHz mono float32 ring), `PassthroughBuffer` (48kHz stereo float32 ring), `PlaybackQueue` (24kHz mono int16 ring). All four buffers use pre-allocated `np.ndarray` + write-pointer + `threading.Lock`.
- `src/vibemix/platform/_audio_macos.py` — concrete `AudioBackend` impl using `sounddevice`. Provides `start_capture()`, `start_passthrough()`, `start_playback()`, `find_device()`.
- The 8 tuning constants (`SILENT_RMS`, `LOW_RMS`, `PEAK_RMS`, `AUDIBLE_DEBOUNCE_SEC`, `SILENCE_DEBOUNCE_SEC`, `EVENT_GLOBAL_MIN_GAP`, `HEARTBEAT_SEC`, `MUSIC_PRESENCE_MIN_SECONDS`) and `MIN_EVENT_GAP_PER_TYPE` dict lifted verbatim from v4 (these are LOAD-BEARING — tuned against real DJ sessions).
- Sample-rate sanity check at startup — fail loud if BlackHole reports 44100Hz when code expects 48000Hz (Kaan's 2026-05-11 session bug).
- `VoiceRecorder` wired against the buffers (input.wav + voice.wav per session — Phase 15 wraps this into a full recording browser; Phase 2 just wires the writer).
- Unit tests for ring buffer wrap, snapshot APIs, level smoothing, sample-rate sanity check.

**Out of scope:**
- `MusicState` / `EventDetector` / `AICoach` — Phase 3.
- LiveKit `AgentSession` wiring (`PlaybackQueueAudioOutput`, `start_input_to_session`) — Phase 4.
- OpenRouter TTS chain + monkey-patch — Phase 4 (lives in `main()` of v4, not in primitives).
- Windows audio (`_audio_windows.py` via PyAudioWPatch) — Phase 7.
- MIDI / screen / track-info — separate Protocols, separate phases.
- BlackHole driver auto-install / programmatic 48kHz config — Phase 11 (calibration wizard). Phase 2 only detects mismatch and emits a clear error.
- Recording UI / browser — Phase 15. Phase 2 just writes the WAVs.

</domain>

<decisions>
## Implementation Decisions

### Ring Buffer Implementation (locked from session 2026-05-11)
- **Data structure:** Pre-allocated `np.ndarray(ring_size, dtype=int16 OR float32)` + write-pointer with modular indexing. Zero alloc per callback. Snapshot copies via numpy slice (`np.concatenate` of two slices around the wrap point).
- **Thread safety:** `threading.Lock` (v4 / POC pattern). Audio callback grabs lock for O(1) write only. Snapshot calls grab lock briefly, copy out, release.
- **Ring sizes (verbatim from v4):**
  - `AudioBuffer`: 140s @ 16kHz int16 = 2,240,000 samples × 2 bytes = 4.5MB ring
  - `MicBuffer`: 200ms @ 48kHz float32 = 9,600 samples × 4 bytes = 38KB ring
  - `PassthroughBuffer`: ~50ms @ 48kHz stereo float32 (for djay→speakers passthrough)
  - `PlaybackQueue`: ~5s @ 24kHz int16 (AI voice output)
- **Snapshot API on AudioBuffer:** `snapshot_features(seconds: float = 7.0) -> dict` returning `{"pcm": np.ndarray, "rms": float, "bpm_est": float, "band_energies": dict}`. Same shape as v4 (`cohost_v4.py:289` class anchor).

### Tuning Constants (LOAD-BEARING — lift verbatim from cohost_v4.py)
- `SILENT_RMS = 0.012` (cohost_v4.py:127)
- `LOW_RMS = 0.040` (cohost_v4.py:128)
- `PEAK_RMS = 0.110` (cohost_v4.py:129)
- `AUDIBLE_DEBOUNCE_SEC = 0.6` (cohost_v4.py:130)
- `SILENCE_DEBOUNCE_SEC = 1.2` (cohost_v4.py:131)
- `EVENT_GLOBAL_MIN_GAP = 7.0` (cohost_v4.py:132 — OpenRouter budget assumption)
- `HEARTBEAT_SEC = 45.0` (cohost_v4.py:133)
- `MIN_EVENT_GAP_PER_TYPE` dict (cohost_v4.py:134-141 — TRACK_CHANGE 5.0, PHASE 10.0, LAYER_ARRIVAL 10.0, MIX_MOVE 14.0, HEARTBEAT 45.0, MIC 3.0, MANUAL 1.5)
- `MUSIC_PRESENCE_MIN_SECONDS = 4.0` (cohost_v4.py:1176)
- `BPM_VALID_MIN = 100.0` (cohost_v4.py:1179)
- `BPM_VALID_MAX = 175.0` (assumed from BPM_VALID_MIN context — verify in v4)

**Where these live in vibemix:** `src/vibemix/audio/constants.py` (single file, importable by Phase 3 EventDetector + Phase 6 genre-aware re-tuning). NOT module-level globals in audio_macos.py — these are domain constants, not platform-specific.

### Sample-Rate Sanity Check (Kaan's 2026-05-11 bug)
- On `start_capture()`, after opening the sounddevice input stream, query the actual sample rate the device reports.
- If `device_actual_sample_rate != requested_sample_rate` → **fail loudly** with a clear actionable error message:
  ```
  ERROR: BlackHole 2ch is configured at {actual}Hz but vibemix expects 48000Hz.
  Fix: Open Audio MIDI Setup → BlackHole 2ch → Format → 48,000 Hz (2 ch, 32-bit float).
  Also enable Drift Correction on BlackHole if you use a Multi-Output Device.
  ```
- This is the **macOS implementation** detail. Phase 7 (Windows) adds the equivalent for WASAPI. Phase 11 (calibration wizard) hooks into this error and walks the user through the fix on first launch.

### AudioBackend Protocol Implementation
- `_audio_macos.AudioMacOS` class implements `AudioBackend` Protocol from Phase 1.
- Constructor signature is at Claude's Discretion — recommend `AudioMacOS(buffers: BufferRegistry, levels: Levels)` where `BufferRegistry` is a value-object grouping the four buffers (avoids 4-positional-args constructor).
- All sounddevice callbacks defined as inner closures inside the factory functions (`start_capture`, etc.) — POC pattern. Keeps closure state private to the stream lifetime.
- Graceful fallback: if `MicBuffer` push fails (`OverflowError` etc.) it's non-fatal; mic is best-effort.

### File Layout
```
src/vibemix/
├── audio/
│   ├── __init__.py            # re-exports Levels, AudioBuffer, MicBuffer, PassthroughBuffer, PlaybackQueue, BufferRegistry
│   ├── constants.py           # 11 tuning constants + MIN_EVENT_GAP_PER_TYPE — lifted verbatim from cohost_v4.py
│   ├── buffers.py             # AudioBuffer, MicBuffer, PassthroughBuffer, PlaybackQueue (pre-allocated rings)
│   ├── levels.py              # Levels class (EMA RMS smoothing)
│   ├── features.py            # snapshot_features() helper — FFT, RMS, BPM autocorr (lifted from v4 AudioBuffer.snapshot_features)
│   └── recorder.py            # VoiceRecorder — input.wav + voice.wav writers + events.jsonl logger
├── platform/
│   └── _audio_macos.py        # AudioMacOS concrete impl of AudioBackend Protocol — sounddevice wrapper
└── ...
```

### Claude's Discretion
- Internal organization of `features.py` (BPM autocorr math, FFT band split, etc.) — port v4's math verbatim, no algorithmic changes; clean up where v4 has experimental scratch comments.
- Whether `BufferRegistry` is a `@dataclass` or a plain `NamedTuple` — both work, pick whichever produces cleaner imports.
- Exact test mocking strategy for `sounddevice` — recommend `unittest.mock.patch` on `sounddevice.RawInputStream` / `RawOutputStream`. No actual audio device required for CI.
- Whether to keep the `_HAS_*` global feature-flag pattern from v4 — strong preference NO. The platform firewall makes feature detection unnecessary (failed import = phase fails to start; let it crash with a clear error).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 1 `AudioBackend` Protocol at `src/vibemix/platform/audio.py` — the interface Phase 2 implements. Method signatures derived from 21 POC call sites (per PATTERNS.md from Phase 1).
- POC variants at repo root — `cohost_v4.py` (CANONICAL), `cohost_v3.py`, `cohost_v2.py`, `cohost_lk.py`, `cohost.py`. All untouched.
- v4 line anchors verified 2026-05-11:
  - `class Levels` @ cohost_v4.py:255
  - `class AudioBuffer` @ cohost_v4.py:289 (with `np.concatenate` bug @ line 300 — THIS is what Phase 2 fixes)
  - `class MicBuffer` @ cohost_v4.py:439 (with `np.concatenate` bug @ line 462 — fix this too)
  - `class PassthroughBuffer` @ cohost_v4.py:480
  - `class PlaybackQueue` @ cohost_v4.py:503
  - `class VoiceRecorder` @ cohost_v4.py:769
  - `class PlaybackQueueAudioOutput` @ cohost_v4.py:1528 (LiveKit-specific — Phase 4 territory)
- `.planning/codebase/CONCERNS.md` has the full P5 description (concat bug at ~100Hz allocation rate, ~4.5MB copy per push).

### Established Patterns (carry forward from v4)
- `from __future__ import annotations` at top (PEP 604 union syntax)
- Module-level constants in `UPPER_SNAKE_CASE`
- `snake_case` files; `PascalCase` classes; private modules `_underscore_prefix`
- Type hints on public function signatures
- Custom exceptions inherit from `Exception` with `PascalCase` + `Exception` suffix (e.g., `SessionDead` in v4)
- Inline callback closures defined inside stream-factory functions
- `threading.Lock` for cross-thread buffer protection

### Integration Points
- **Phase 3 (Sensing & State Port)** imports `from vibemix.audio import AudioBuffer, Levels, snapshot_features` to drive `MusicState`.
- **Phase 4 (LiveKit Cascade)** imports `from vibemix.audio import PlaybackQueue, MicBuffer` and connects them to `AgentSession`'s `PlaybackQueueAudioOutput` + audio push pipeline.
- **Phase 6 (Genre-Aware Phase Detection)** imports `constants.py` and per-genre profiles override `SILENT_RMS` / `LOW_RMS` / `PEAK_RMS` dynamically.
- **Phase 7 (Windows Port)** writes `_audio_windows.py` against the same `AudioBackend` Protocol; reuses the buffer classes verbatim (they're platform-agnostic).
- **Phase 11 (Tauri / Calibration Wizard)** catches the sample-rate-mismatch error and walks the user through Audio MIDI Setup.
- **Phase 15 (Recording & Session Capture)** wraps `VoiceRecorder` with retention policy + browser UI.

</code_context>

<specifics>
## Specific Ideas

- **Sample-rate sanity check** is non-negotiable — Kaan hit the BlackHole 44100/48000 bug live on 2026-05-11 and lost ~30 min debugging. Phase 2 makes this impossible to ship.
- **The `np.concatenate` bug** is at exactly these two lines: `cohost_v4.py:300` (`AudioBuffer.push`) and `cohost_v4.py:462` (`MicBuffer.push`). Pre-allocated ring fixes both. Verify post-fix with a benchmark test (~100 push calls in tight loop allocates 0 new ndarrays — use `tracemalloc`).
- **VoiceRecorder** writes to `recordings/<YYYYMMDD-HHMMSS>/` with `input.wav` (16kHz mono int16) + `voice.wav` (24kHz mono int16) + `events.jsonl` (JSONL timeline) — already in v4's design; just port the dir creation + writer logic.
- **macOS-only this phase.** `_audio_windows.py` is Phase 7. Phase 2's AudioBackend impl can be `AudioMacOS`; Phase 7 adds `AudioWindows`. Cross-platform `find_input_device()` helper logic goes in `platform/__init__.py` selector if needed.

</specifics>

<deferred>
## Deferred Ideas

- **MIDI deck detection fix** (Pioneer FLX4 play-state not reaching MusicState) — Phase 9 (MIDI Controller Library) work.
- **OpenRouter TTS monkey-patch** (`_openai_tts_mod.AUDIO_STREAM_MODELS.add(...)`) — Phase 4 (LiveKit Cascade Agent Pivot). Phase 2 is pure I/O, doesn't touch TTS.
- **Programmatic BlackHole 48kHz config** via CoreAudio API — Phase 11 (calibration wizard). Phase 2 only detects mismatch.
- **Genre-aware threshold override** — Phase 6. Phase 2 ships the v4-tuned defaults in `constants.py` so Phase 6 has a baseline to refine.
- **Recording retention policy + browser UI** — Phase 15.
- **`cohost.streaming.py.bak` cleanup** — orthogonal; CONCERNS.md flags it; not Phase 2's responsibility.

</deferred>
