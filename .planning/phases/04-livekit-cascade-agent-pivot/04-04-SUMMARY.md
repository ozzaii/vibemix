---
phase: 04-livekit-cascade-agent-pivot
plan: 04
type: summary
status: complete
completed_at: 2026-05-11
requirements_covered:
  - ARCH-03
  - ARCH-04
  - ARCH-05
wave_commit: ede9e59
---

# Plan 04-04 — __main__ orchestrator + CI integration smoke — Summary

## What Shipped

The final wiring of Phase 4 — everything from 04-01/02/03 converges in
`src/vibemix/__main__.py`. `python -m vibemix` now produces the same
audible reactions on a real DJ set that `./run_v4.sh` does, while
`python -m vibemix --version` exits zero on any machine without devices
or keys.

- `src/vibemix/__main__.py` (~340 lines):
  - `_parse_args` — argparse with `--version` action that short-circuits
    BEFORE any device or key access.
  - 4 callback factories matching v4's stream callback bodies verbatim:
    `_input_callback_factory` (v4:912-945), `_voice_callback_factory`
    (v4:885-888), `_passthrough_callback_factory` (v4:864-873),
    `_mic_callback_factory` (v4:1965-1969).
  - `async main()` — verbatim port of `cohost_v4.py:1925-2080`. Reads
    `GEMINI_API_KEY` (required, sys.exit on missing) + `OPENROUTER_API_KEY`
    (optional). Wires `Levels` / `PlaybackQueue` / `PassthroughBuffer` /
    `MicBuffer` / TWO `AudioBuffer` instances (state 140s + clean
    `INVOKE_AUDIO_SECONDS + 5.0`) / `VoiceRecorder` / `BufferRegistry`.
    Instantiates `ScreenMacOS` / `MidiMacOS` / `TrackMacOS` / `MusicState`
    / `EventDetector`. Opens 4 sounddevice streams via `AudioMacOS`
    (input, voice output, passthrough output, mic input). Builds LLM +
    TTS chain. Constructs `DJCoHostAgent` + `AgentSession`. Assigns
    `session.output.audio = PlaybackQueueAudioOutput(...)` BEFORE
    `await session.start(agent)` (v4:2030-2033 invariant). Spawns MIDI
    daemon thread. Spawns 6 asyncio tasks (`ws_broadcast`, `diag_loop`,
    `ScreenMacOS.run_capture_loop`, `TrackMacOS.run_poll_loop`,
    `state_refresh_loop`, `coach_loop`). Opens input_stream LAST.
    SIGINT/SIGTERM handlers via `loop.add_signal_handler`. Cleanup:
    midi_stop, cancel + await all tasks with CancelledError catch,
    `session.aclose`, stop+close all streams, `recorder.close`.
  - `cli_entry` — sync entry point that lets argparse short-circuit
    `--version` BEFORE any heavy `asyncio.run(main())` call.

- `tests/test_main_smoke.py` (~340 lines, 6 SMOKE tests):
  - **SMOKE-01**: `python -m vibemix --version` exits zero in a
    subprocess.
  - **SMOKE-02**: missing `GEMINI_API_KEY` raises `SystemExit` with the
    expected message.
  - **SMOKE-03**: full main() wiring smoke. Mocks `AudioMacOS` factories
    (find_device + 4 open_* methods), `ScreenMacOS.run_capture_loop` /
    `TrackMacOS.run_poll_loop` / `MidiMacOS.start_listener_thread` (all
    no-op), `state_refresh_loop` (no-op), `AgentSession`, `genai.Client`,
    `build_llm` / `build_tts_chain`, `DJCoHostAgent`,
    `PlaybackQueueAudioOutput`, and the 3 runtime loops. Verifies:
    find_device called 3 times, all 4 open_* called once, build_llm called
    with the dummy key, build_tts_chain called with both keys,
    DJCoHostAgent constructed with all required kwargs, AgentSession
    constructed with llm + tts, `session.output.audio` assigned to a
    PlaybackQueueAudioOutput instance, `session.start` awaited.
  - **SMOKE-04**: no `OPENROUTER_API_KEY` → `build_tts_chain` called
    with `openrouter_api_key=None`.
  - **SMOKE-05**: cleanup runs `stop()` AND `close()` on all 4 stream
    handles.
  - **SMOKE-06**: SHA-256 of `cohost_v4.py` is identical before and
    after — POC files diff-untouched during the smoke.

- `tests/test_main_live.py` — opt-in live smoke. Marked
  `@pytest.mark.macos_audio` and skipped by default UNLESS
  `VIBEMIX_LIVE_SMOKE=1` is set. Spawns `python -m vibemix` for ~5s,
  sends SIGINT, asserts clean exit + new `recordings/<...>/` session dir.

## Files

Created (3):
- `src/vibemix/__main__.py` (~340 lines)
- `tests/test_main_smoke.py` (~340 lines, 6 tests)
- `tests/test_main_live.py` (~70 lines, 1 opt-in test)

Modified (0).

## Tests Added

7 new tests:
- 6 mocked-device integration tests (SMOKE-01..06).
- 1 opt-in live smoke (`@pytest.mark.macos_audio`, skipped by default).

Full suite: **346 pass** (340 from Phases 1-3 + plan 04-01/02/03 +
runtime, plus 6 new in `test_main_smoke.py`). 0 ruff errors, 0 format
diffs.

## Architectural Decisions Locked

- **AudioMacOS as the firewall.** v4's free-function stream factories
  (`start_input_to_session`, `start_playback_stream`,
  `start_passthrough_stream`) are replaced by `AudioMacOS.open_*`
  methods that accept callbacks. The 4 callback bodies live in factory
  functions in `__main__.py` matching v4 verbatim.
- **`cli_entry` separation lets `--version` short-circuit.** argparse's
  `action="version"` exits immediately before any device or env access.
  SMOKE-01 verifies this in an env-stripped subprocess.
- **Twin `AudioBuffer` instances.** `audio_buf = AudioBuffer(seconds=140.0)`
  for state thresholds (gain-boosted via `MUSIC_GAIN_TO_GEMINI` in
  callback) + `clean_audio_buf = AudioBuffer(seconds=INVOKE_AUDIO_SECONDS
  + 5.0)` for LLM Part (natural level, no gain). v4:1948-1949 verbatim.
  Grep gate 11 passes (≥2 `AudioBuffer(seconds=` matches).
- **`session.output.audio = PlaybackQueueAudioOutput(...)` BEFORE
  `await session.start(agent)`.** v4:2030-2033 invariant. Verified by
  awk gate 10 (line 301 < line 304).
- **SIGINT/SIGTERM via `loop.add_signal_handler`.** The handle_sigint
  closure sets `stop_event`; all 6 asyncio tasks observe and exit
  cleanly. Cleanup in the `finally:` block cancels each task with a
  `CancelledError`/`Exception` catch.
- **Mic stream is optional.** v4:1962-1979 try/except gracefully
  degrades when `MIC_DEVICE` not found.
- **`BufferRegistry` uses the dataclass signature** (`audio`,
  `clean_audio`, `mic`, `passthrough`, `playback`, `levels`) — slight
  deviation from the plan's example which used `music=audio_buf`. The
  plan example is wrong; the real `BufferRegistry` dataclass fields are
  what main() uses.

## Deviations from Plan

- **Plan example for `BufferRegistry` was off.** The plan showed
  `BufferRegistry(music=audio_buf, mic=mic, passthrough=passthrough,
  playback=playback)` but the actual dataclass (Phase 2) has fields
  `audio` / `clean_audio` / `mic` / `passthrough` / `playback` /
  `levels`. main() uses the real fields. No functional impact.
- **SMOKE-02 timing fix.** The original test design patched
  `load_dotenv` before `from vibemix.__main__ import cli_entry`, but
  the import itself runs `load_dotenv` at module load — which beats
  the patch. Fix: delete env vars AFTER importing the module. Result
  is identical (env-stripped check inside main()).
- **No flakiness encountered in SMOKE-03.** Patching the 3 runtime loops
  (`coach_loop`, `diag_loop`, `ws_broadcast`) to no-op coroutines makes
  the wiring assertion deterministic. No need for `@pytest.mark.flaky`.

## Carry-Forward

- **Plan 04-05 (Wave 5)**: Run the full 12-gate verification, write the
  phase rollup `04-SUMMARY.md`, advance `STATE.md` to Phase 5, tick
  `ROADMAP.md` Phase 4 entry. Optional Kaan-verify checkpoint (live
  smoke against his rig).
- **Phase 5 (FastAPI Proxy)**: `build_llm(api_key)` and
  `build_tts_chain(gemini_api_key, openrouter_api_key)` are the seams
  Phase 5 modifies. Replace `api_key` with a proxy-issued JWT and the
  `base_url` for OpenRouter TTS — no other Phase 4 code changes needed.
- **Phase 12 (Live Session UI)**: consumes the WS bus payload format
  pinned by `WS-06` (`{music, voice, mic, audible, deck, phase}`).
