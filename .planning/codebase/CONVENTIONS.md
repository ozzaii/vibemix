# Coding Conventions

**Analysis Date:** 2026-05-11

## Naming Patterns

**Files:**
- `snake_case.py` throughout — `cohost.py`, `cohost_v2.py`, `cohost_lk.py`, `generate_bat.py`
- Leading underscore prefix = manual smoke-test scripts not intended for automated execution: `_test_tts.py`, `_test_multimodal.py`
- No underscore prefix = lightweight integration smoke test meant to be run: `test_voice.py`
- `.bak` suffix for superseded snapshots kept for reference: `cohost.streaming.py.bak`

**Functions:**
- `snake_case` throughout — `find_device`, `start_input_stream`, `receive_audio`, `classify_phase`, `derive_audible_deck`
- Private helper methods use single leading underscore: `_current_gain`, `_is_session_dead`, `_knob_label`, `_write_event_locked`, `_cooldown_ok`, `_fire`
- Async coroutines named with `_loop` suffix for long-running background tasks: `trigger_loop`, `screen_capture_loop`, `track_poll_loop`, `diag_loop`, `ws_broadcast`
- Module-level private helpers use `_` prefix: `_HAS_VISION`, `_HAS_WS`, `_HAS_QUARTZ`
- Inner callback functions always named `callback` (defined inside stream factory functions)

**Variables:**
- `snake_case` — `input_idx`, `levels`, `audio_buf`, `trigger_state`, `stop_event`
- Module-level constants in `UPPER_SNAKE_CASE` — `INPUT_SR_NATIVE`, `OUTPUT_SR`, `MIC_GAIN`, `SILENT_RMS`
- Short temporary names for local signal processing: `rms`, `arr`, `pcm`, `spec`, `freqs`
- Loop state dicts use string keys: `state["last_trigger"]`, `trigger_state["in_flight"]`

**Types / Classes:**
- `PascalCase` for all classes — `Levels`, `AudioBuffer`, `MicBuffer`, `PassthroughBuffer`, `PlaybackQueue`, `ScreenBuffer`, `VoiceRecorder`, `TurnHistory`, `MusicState`, `EventDetector`, `AICoach`, `TrackInfo`, `ControllerState`
- Custom exceptions use `PascalCase` with `Exception` suffix: `SessionDead`
- Dataclass fields use `snake_case` matching the pattern of other vars

## Code Style

**Formatting:**
- No formatter config file present (no `.black`, `.ruff.toml`, `pyproject.toml`)
- Consistent 4-space indentation observed throughout
- 79-100 char informal line length — no enforced limit
- Blank lines between top-level defs and class methods follow PEP 8 (2 between top-level, 1 between methods)

**Linting:**
- No linting config detected (no `.flake8`, `.eslintrc`, `ruff.toml`)
- Project relies on developer discipline, not automated enforcement

## Import Organization

**Order (observed across all main files):**
1. `from __future__ import annotations` (only in `cohost_v2.py` and `cohost_lk.py`)
2. stdlib imports — `asyncio`, `io`, `json`, `os`, `signal`, `sys`, `threading`, `time`, `wave`
3. third-party imports — `numpy`, `sounddevice`, `dotenv`, `google.genai`, `scipy`, `livekit`
4. Optional imports wrapped in `try/except ImportError` blocks to allow degraded mode

**Optional import guard pattern (used consistently):**
```python
try:
    import mss
    from PIL import Image
    _HAS_VISION = True
except ImportError:
    _HAS_VISION = False
```
Used for: `mss`/`PIL` (screen vision), `websockets` (mascot bus), `Quartz` (macOS window bounds in `cohost_lk.py` and `cohost_v2.py`).

**Path Aliases:**
- None. All imports are absolute package names.

## Error Handling

**Patterns:**

1. **Bare `except Exception: pass`** — used in `VoiceRecorder` write methods (`cohost.py` lines 566–596) to ensure file writes never crash the audio hot path:
```python
with self._lock:
    try:
        self.voice_wav.writeframes(pcm_bytes)
    except Exception:
        pass
```

2. **Catch-and-log-then-reraise** — used for session-level errors that need reconnect logic:
```python
except Exception as e:
    print(f"\n[receive err] {e} — will reconnect", file=sys.stderr)
    recorder.log_event("session_error", error=str(e))
    raise SessionDead(str(e)) from e
```

3. **Custom exception as signal** — `SessionDead` (`cohost.py` line 440) signals that the WebSocket session is gone and the caller should reconnect. Not a catch-all; raised deliberately.

4. **`_is_session_dead` heuristic** — string inspection on exception messages to classify WebSocket close codes (`1000`, `1006`, `1007`, `1011`, `"closed"`, `"connectionclosed"`).

5. **`RuntimeError` for unrecoverable config errors** — device lookup failure raises `RuntimeError(f"No {kind} device matching {name_substring!r}")`.

6. **`sys.exit` for missing env vars** — smoke test scripts use `os.environ.get("GEMINI_API_KEY") or sys.exit("GEMINI_API_KEY missing")`.

7. **Broad `except Exception` in WS handler** — swallowed silently in the websocket client set handler to prevent one client disconnect from crashing the server.

**What is NOT caught:** `KeyboardInterrupt` — main coroutine registers a `signal.SIGINT` handler, not a try/except.

## Logging

**Framework:** `print()` to stdout/stderr only — no `logging` module anywhere.

**Patterns:**
- Startup info uses `->` prefix: `print(f"-> listening to {name} @ {sr}Hz")`
- Error output goes to `sys.stderr`: `print(f"[receive err] {e}", file=sys.stderr)`
- Error prefixes use bracketed category tags: `[input status]`, `[turn err]`, `[coach err]`, `[screen err]`, `[mic status]`
- AI transcription output uses `AI> ` prefix: `print(f"\nAI> {txt}", flush=True)`
- Trigger events use `\n` prefix to break out of overwrite line: `print(f"\n[trigger {tag}] ...")`
- Live diagnostic uses `\r` overwrite: `sys.stdout.write(f"\r[live] music=...")` with `sys.stdout.flush()`
- Structured event logging via `VoiceRecorder.log_event()` to `events.jsonl` — separate from console output

## Comments

**When to Comment:**
- Inline comments explain *why* a value or gate exists, not what the code does — especially for audio DSP constants and thresholds
- Multi-line inline comments on decisions that have been deliberately changed (e.g., AI talk gate removal at `cohost.py` lines 419–422)
- Section dividers use `# ----` or `# =====` in `cohost_v2.py` and `cohost_lk.py`

**Docstrings:**
- Module-level docstrings present in all files — describes purpose and audio/data flow with ASCII diagrams where helpful
- Class docstrings: single-line or short multi-line describing thread safety and role — present on most classes in `cohost.py`; absent or minimal on equivalent classes in `cohost_v2.py` (they carry forward without re-documenting)
- Method docstrings: used on non-trivial methods (`snapshot_features`, `run_one_turn`, `start_input_stream`) but not on simple accessors (`push`, `pull`, `snapshot`)
- Async loop functions (`trigger_loop`, `receive_audio`) have docstrings describing the trigger logic and reconnect strategy
- No Google-style, NumPy-style, or Sphinx-style formatting — plain prose only

**Style:** `"""One-liner or short paragraph."""` — no multi-section structured docstrings.

## Function Design

**Size:**
- Short utility functions: 5–15 lines (`find_device`, `_knob_label`, `_cooldown_ok`)
- Medium business logic: 20–50 lines (`run_one_turn`, `detect`, `classify_phase`, `snapshot_features`)
- Long orchestration coroutines: `trigger_loop` (cohost.py ~120 lines), `main` (cohost_v2.py ~200 lines) — not split into sub-functions
- Audio stream callbacks defined as inner closures inside factory functions (`start_input_stream`, `start_passthrough_stream`, `start_playback_stream`)

**Parameters:**
- Positional for required objects, keyword-only for tuning values: `snapshot_features(self, seconds: float = 7.0)`
- Dependency injection over globals: `Levels`, `AudioBuffer`, `PlaybackQueue` etc. are always passed explicitly
- `stop_event: asyncio.Event` passed to every long-running coroutine as cooperative shutdown signal

**Return Values:**
- Explicit `None` return for early exits in guard clauses
- Dict return for feature snapshots: `snapshot_features` returns `dict` with well-defined keys
- `bytes` / `np.ndarray` for audio data
- `bool` from `run_one_turn` to indicate success/failure

## Module Design

**Exports:** No `__all__` defined. Each file is a standalone runnable script, not a library.

**Barrel Files:** Not applicable — no package structure. All code is flat in the project root.

**Configuration:** All tuning constants defined as module-level `UPPER_SNAKE_CASE` at the top of each file. Env vars loaded at module level via `load_dotenv()`.

**Versioning pattern:** New complete-rewrite versions get new files (`cohost_v2.py`, `cohost_lk.py`) rather than in-place modification. Old versions are kept as `.bak` or just left in place.

## Type Hints

**Usage:**
- All public function signatures use type hints in `cohost.py` — `find_device(name_substring: str, kind: str) -> int`
- `cohost_v2.py` uses `from __future__ import annotations` (line 18) enabling PEP 604 union syntax (`str | None`, `bytes | None`, `dict | None`)
- Numpy arrays typed as `np.ndarray`, never as `list`
- Forward references use string literal form where needed: `levels: "Levels"` in `cohost.py`
- `cohost_lk.py` class methods mostly untyped internally; public function signatures have hints
- `@dataclass` used only in `cohost_v2.py` for `MusicState` (line 965) and `Event` (line 1119)
- No `mypy` or `pyright` config present — hints are documentation, not enforced

## Async vs Sync

**Model:**
- Main loop is `asyncio` with `asyncio.run(main())`
- Audio I/O callbacks are synchronous (sounddevice requires it) — called from separate OS audio threads
- Shared state (buffers, levels) uses `threading.Lock` for thread safety between audio threads and asyncio event loop
- Blocking operations offloaded via `loop.run_in_executor(None, fn)`: screen capture, track polling
- Long-running background tasks registered as `asyncio.create_task(...)` at startup

---

*Convention analysis: 2026-05-11*
