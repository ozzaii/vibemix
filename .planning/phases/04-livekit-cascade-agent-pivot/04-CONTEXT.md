# Phase 4: LiveKit Cascade Agent Pivot - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning
**Canonical POC baseline:** `cohost_v4.py` (live and runnable via `run_v4.sh`)

<domain>
## Phase Boundary

Wire DJCoHostAgent + AgentSession cascade + OpenRouter-primary TTS chain + coach_loop + ws_broadcast + diag_loop + main() into the new `src/vibemix/` package. After Phase 4, `python -m vibemix` (or `uv run python -m vibemix`) is a working replacement for `run_v4.sh` — producing the same audible reactions on a real DJ set without the user touching cohost_v4.py.

**In scope:**
- `src/vibemix/agent/dj_cohost.py` — `DJCoHostAgent(Agent)` with `llm_node` override (v4:1441-1593 verbatim). Built around `vibemix.state` outputs (AICoach.build_prompt + MusicState snapshots) and `vibemix.audio` ring buffers (`clean_audio_buf.snapshot_wav(INVOKE_AUDIO_SECONDS)`).
- `src/vibemix/agent/playback_sink.py` — `PlaybackQueueAudioOutput(voice_io.AudioOutput)` bridging LiveKit TTS frames → `vibemix.audio.PlaybackQueue` (v4:1596-1640 verbatim).
- `src/vibemix/agent/tts_chain.py` — Builds the FallbackAdapter TTS chain: OpenRouter primary (with monkey-patch for `google/gemini-3.1-flash-tts-preview` AudioChunkedStream path) → Gemini native TTS (gemini-3.1-flash-tts-preview) → Gemini fallback TTS (gemini-2.5-flash-preview-tts). Reads `OPENROUTER_API_KEY` from env; gracefully degrades when missing.
- `src/vibemix/agent/llm_factory.py` — `build_llm()` returning `google_plugin.LLM("gemini-3-flash-preview", thinking_level="minimal", temperature=1.0, max_output_tokens=220)` configured exactly as v4:1983-1989.
- `src/vibemix/agent/persona.py` — `SYSTEM_INSTRUCTION` constant (v4:150-213 verbatim — the full persona prompt with anti-hallucination rules). Phase 10's prompt template matrix layers ON TOP of this; Phase 4 ships the persona text as a single module-level string.
- `src/vibemix/runtime/coach.py` — `coach_loop(session, agent, state, levels, event_detector, recorder, manual_trigger, trigger_state, stop_event)` async (v4:1754-1852 verbatim). Mic gating (KAAN_SPOKE detection), in-flight guard, manual trigger handling, session.generate_reply invocation.
- `src/vibemix/runtime/diag.py` — `diag_loop(levels, state, stop_event)` terminal meter (v4:1859-1869 verbatim).
- `src/vibemix/runtime/ws_bus.py` — `ws_broadcast(levels, state, manual_trigger, stop_event)` mascot WebSocket bus @ 30fps (v4:1872-1918 verbatim). Listens for `{"action":"trigger"}` to set `manual_trigger`.
- `src/vibemix/__main__.py` — async `main()` orchestrator (v4:1925-2080 verbatim, refactored to use `src/vibemix/` imports). Entry point for `python -m vibemix`.
- Integration test: smoke run that opens session, fires a synthetic MANUAL event, asserts audio frames arrive in PlaybackQueue (mocked TTS) — runs in CI without real BlackHole.
- Optional manual smoke test under `macos_audio` marker for live DJ session with real BlackHole + DDJ-FLX4.

**Out of scope:**
- FastAPI proxy + install-UUID JWT (the production path that keeps Gemini key off client) — Phase 5. Phase 4 reads `GEMINI_API_KEY` directly from `.env` for dev-loop compatibility with v4. **This is the same security posture as v4** — Phase 5 replaces both v4 and Phase 4 with the proxy path.
- Prompt template matrix (Beginner/Intermediate/Pro × Hype/Coach) — Phase 10. Phase 4 ships ONE persona text.
- Tauri shell + PyInstaller --onedir bundling — Phase 11.
- Tauri Settings UI (voice picker, mode toggle, output device picker) — Phase 12.
- Mascot SVG render (`Avery`) — Phase 13. Phase 4's `ws_broadcast` provides the data feed; current `mascot.html` (POC file, untouched) consumes it during dev.
- Hallucination verification gate (30-session replay suite) — Phase 16.

</domain>

<decisions>
## Implementation Decisions

### TTS Chain (locked)
- **Primary:** OpenRouter via `livekit-plugins-openai` with `model="google/gemini-3.1-flash-tts-preview"`, `voice="Achird"`, `base_url="https://openrouter.ai/api/v1"`, `response_format="pcm"`, `instructions="Casual studio friend, brief, natural — no theatrics, no announcer voice."`. Reads `OPENROUTER_API_KEY` from env.
- **Critical monkey-patch (v4:62-66):** Before any `openai_plugin.TTS` import or instantiation, run `_openai_tts_mod.AUDIO_STREAM_MODELS.add("google/gemini-3.1-flash-tts-preview")`. Without it, LiveKit's OpenAI plugin uses SSE for this model — but OpenRouter returns raw PCM. Patch forces the `AudioChunkedStream` path used by `tts-1`. Apply this BEFORE `from livekit.plugins import openai as openai_plugin` (module-load order matters).
- **Secondary fallback (Gemini native):** `gemini_native_tts.TTS(model="gemini-3.1-flash-tts-preview", voice_name="Achird", api_key=GEMINI_API_KEY, instructions=...)`.
- **Tertiary fallback (Gemini older):** `gemini_native_tts.TTS(model="gemini-2.5-flash-preview-tts", voice_name="Achird", ...)`.
- **Adapter:** `agents_tts.FallbackAdapter(tts=[primary, secondary, tertiary], max_retry_per_tts=1)` (v4:2017 verbatim).
- **Graceful degradation:** When `OPENROUTER_API_KEY` missing, primary is omitted and chain starts at Gemini native (with a clear log line).

### LLM (locked)
- `LLM_MODEL = "gemini-3-flash-preview"`
- `google_plugin.LLM(model=LLM_MODEL, api_key=GEMINI_API_KEY, temperature=1.0, thinking_config=types.ThinkingConfig(thinking_level="minimal"), max_output_tokens=220)`
- The `genai_client = genai.Client(api_key=GEMINI_API_KEY)` is used DIRECTLY by `DJCoHostAgent.llm_node` for multimodal streaming (bypassing LiveKit's text-only path).

### DJCoHostAgent (locked, lift v4:1441-1593 verbatim)
- Subclass `livekit.agents.Agent`. Constructor: `__init__(self, *, genai_client, clean_audio_buf, screen_buf, state, recorder, llm_inst, tts_inst)`.
- `instructions=SYSTEM_INSTRUCTION` passed to super(). `allow_interruptions=False`.
- `_pending_event: Event | None` — set via `set_next_event(ev)` from `coach_loop` before each `session.generate_reply()` call.
- `_ai_text_history: collections.deque(maxlen=10)` — last 10 AI replies for the anti-repetition history clause.
- `_gen_cfg = types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, thinking_config=..., temperature=1.0, max_output_tokens=220)`.
- `async def llm_node(chat_ctx, tools, model_settings) -> AsyncGenerator` overrides LiveKit's text-only path:
  1. Pop `self._pending_event`.
  2. Build text prompt via `AICoach.build_prompt(ev)` (from Phase 3 `vibemix.state`).
  3. Pull `audio_wav = clean_audio_buf.snapshot_wav(INVOKE_AUDIO_SECONDS)` (18s WAV from Phase 2 `vibemix.audio`).
  4. Build per-invocation dump folder: `recordings/<session>/invocations/<NNNN>_<HHMMSS>_<EVENT>/{audio.wav, prompt.txt, response.txt, meta.json}`. Also write `recordings/<session>/last_gemini_audio.wav` shortcut.
  5. `screen_jpeg = None` — v4 explicitly disabled screen-image attachment (line 1503: "Single-modality: audio only. Screen + MIDI metadata caused hallucination.") — port verbatim including the comment.
  6. Build `contents = [text_prompt + audio Part description + history clause, types.Part.from_bytes(audio_wav, mime_type="audio/wav")]`. Optional screen Part path is dead code in v4 — keep the conditional but the path is never taken.
  7. `recorder.log_event("llm_invoke", ...)` with audible/deck/track/phase/audio_bytes/has_screen/prompt/invoke_dir.
  8. `await genai_client.aio.models.generate_content_stream(model=LLM_MODEL, contents=contents, config=self._gen_cfg)`. Stream text chunks via `yield txt`.
  9. On completion: log `ai_text` event, append stripped text to `_ai_text_history`, write response.txt + meta.json.

### PlaybackQueueAudioOutput (locked, lift v4:1596-1640 verbatim)
- Subclass `livekit.agents.voice.io.AudioOutput`.
- Constructor: `__init__(self, playback: PlaybackQueue, recorder: VoiceRecorder, sample_rate: int = OUTPUT_SR)`.
- `super().__init__(label="dj-cohost.playback", capabilities=voice_io.AudioOutputCapabilities(pause=False), sample_rate=sample_rate)`.
- `async def capture_frame(frame: rtc.AudioFrame)`:
  - On first frame: set `_segment_started_at`, call `self.on_playback_started(created_at=now)`.
  - Push `bytes(frame.data)` → `self._playback.push(pcm)` AND `self._recorder.push_voice(pcm)`.
  - Track `_segment_duration += frame.samples_per_channel / frame.sample_rate`.
- `def flush()`: emit `on_playback_finished(playback_position=_segment_duration, interrupted=False)`. Reset segment state.
- `def clear_buffer()`: no-op (v4 runs `allow_interruptions=False`).

### coach_loop (locked, lift v4:1754-1852 verbatim)
- `await asyncio.sleep(2.0)` warmup before first cycle.
- 10Hz poll (`asyncio.sleep(0.1)`).
- **In-flight guard:** `trigger_state["in_flight"]` set True when firing; cleared in finally. Stale clear after 12s.
- **AI-talking guard:** Skip if `levels.voice > AI_TALK_THRESHOLD` or last AI voice was within 7s.
- **Mic detection (KAAN_SPOKE):**
  - When `levels.mic > MIC_TALK_THRESHOLD`: increment `mic_active_frames`, reset silence counter, update `state.last_kaan_spoke_at`.
  - When mic drops below: require `mic_active_frames >= 3` AND `mic_silence_since > 0.6s` to flip `kaan_just_spoke=True`.
- **Manual trigger:** `manual = manual_trigger.is_set()`; if set, `manual_trigger.clear()`.
- **Detect:** `ev = event_detector.detect(state, kaan_just_spoke=..., manual=...)`. If None, continue.
- **Fire:**
  - `agent.set_next_event(ev)` — hand event to llm_node.
  - `handle = session.generate_reply(allow_interruptions=False)`.
  - `await asyncio.wait_for(handle.wait_for_playout(), timeout=20.0)`.
  - Log via `recorder.log_event("event", ...)`.

### main() (locked, lift v4:1925-2080 with package-aware imports)
- Read `GEMINI_API_KEY` from env (sys.exit if missing). Read `OPENROUTER_API_KEY` (optional).
- `find_device(INPUT_DEVICE, "input")` + `find_device(OUTPUT_DEVICE, "output")` via `vibemix.platform._audio_macos`.
- Set up SIGINT/SIGTERM handlers via `loop.add_signal_handler(sig, handle_sigint)`.
- Instantiate `Levels`, `PlaybackQueue`, `PassthroughBuffer`, `MicBuffer`, `ScreenBuffer`, two `AudioBuffer` instances (one 140s for state thresholds, one (INVOKE_AUDIO_SECONDS + 5)s for LLM snapshot), `VoiceRecorder`, `TrackInfo`, `ControllerState`, `MusicState`, `EventDetector`.
- Start sounddevice streams: `start_playback_stream` (output), `start_passthrough_stream` (output), `start_input_to_session` (input, BlackHole), separate mic InputStream.
- Build LLM + TTS chain (with monkey-patch applied at module-load).
- Instantiate `DJCoHostAgent(...)`, create `AgentSession(llm=llm_inst, tts=tts_inst)`, assign `session.output.audio = PlaybackQueueAudioOutput(...)`.
- `await session.start(agent)`.
- Start MIDI listener daemon thread.
- Spawn asyncio tasks: `ws_broadcast`, `diag_loop`, `screen_capture_loop`, `track_poll_loop`, `state_refresh_loop`, `coach_loop`.
- `await stop_event.wait()`.
- Cleanup: cancel tasks, await them with CancelledError catch, `session.aclose()`, stop+close all streams, `recorder.close()`.

### File Layout
```
src/vibemix/
├── __main__.py                   # async main() — entry point for `python -m vibemix`
├── agent/
│   ├── __init__.py
│   ├── persona.py                # SYSTEM_INSTRUCTION (v4:150-213 verbatim)
│   ├── llm_factory.py            # build_llm() — google_plugin.LLM config
│   ├── tts_chain.py              # build_tts_chain() — OpenRouter + monkey-patch + Gemini fallbacks
│   ├── dj_cohost.py              # DJCoHostAgent(Agent) with llm_node override
│   └── playback_sink.py          # PlaybackQueueAudioOutput(voice_io.AudioOutput)
├── runtime/
│   ├── __init__.py
│   ├── coach.py                  # coach_loop async
│   ├── diag.py                   # diag_loop async (terminal meters)
│   └── ws_bus.py                 # ws_broadcast async (mascot WebSocket bus)
└── (Phases 1-3 packages already present)
```

### Configuration (locked)
- `LLM_MODEL = "gemini-3-flash-preview"`
- `TTS_MODEL = "gemini-3.1-flash-tts-preview"` (Gemini native fallback)
- `TTS_FALLBACK_MODEL = "gemini-2.5-flash-preview-tts"`
- `OPENROUTER_TTS_MODEL = "google/gemini-3.1-flash-tts-preview"`
- `VOICE = "Achird"`
- `INPUT_DEVICE = "BlackHole 2ch"`
- `OUTPUT_DEVICE = "AI Capture"` (v4:102 — Multi-Output Device name on Kaan's machine; Phase 11 calibration wizard will surface this as a configurable Setting; for Phase 4, port the v4 default)
- `MIC_DEVICE = "MacBook Pro Microphone"`

These live in `src/vibemix/agent/config.py` (or extend `vibemix.audio.constants` — planner discretion).

### Claude's Discretion
- Internal structure of `dj_cohost.py` — one file (verbatim port) vs split between `llm_node.py` and `agent.py`. Recommend single file matching v4 layout.
- Per-invocation dump location — keep `recordings/<session>/invocations/<NNNN>_<HHMMSS>_<EVENT>/` exactly as v4 to maintain audit-trail compatibility with cohost_v4.py debugging output.
- Async vs blocking calls to `genai_client.aio.models.generate_content_stream` — port v4's async exactly.
- Test mocking strategy for integration smoke — use `pytest-mock` to patch `google_plugin.LLM`, `gemini_native_tts.TTS`, `openai_plugin.TTS`, and assert `session.start()` + `generate_reply()` invocation chains.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (from Phases 1-3)
- **Phase 1:** All four Protocols (AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend). Phase 4's main() instantiates the macOS impls of all four.
- **Phase 2:** `vibemix.audio.AudioBuffer` (with `snapshot_wav(seconds)` ALREADY ported — verified Phase 2 SUMMARY), `Levels`, `PlaybackQueue`, `MicBuffer`, `PassthroughBuffer`, `BufferRegistry`, `VoiceRecorder`, `vibemix.audio.constants.*`. Phase 4 imports these — no re-implementation.
- **Phase 3:** `vibemix.state.MusicState`, `Event`, `EventDetector`, `AICoach`, `state_refresh_loop`. `vibemix.platform.{ScreenMacOS, MidiMacOS, TrackMacOS}` + `find_djay_window_bounds` + `screen_capture_loop` + `midi_listener_thread` + `track_poll_loop`. Phase 4 imports these — no re-implementation.

### v4 Line Anchors (verified 2026-05-11)
- `class DJCoHostAgent` @ cohost_v4.py:1441-1593
- `class PlaybackQueueAudioOutput` @ cohost_v4.py:1596-1640
- `async def coach_loop` @ cohost_v4.py:1754-1852
- `async def diag_loop` @ cohost_v4.py:1859-1869
- `async def ws_broadcast` @ cohost_v4.py:1872-1918
- `async def main` @ cohost_v4.py:1925-2080
- `SYSTEM_INSTRUCTION` @ cohost_v4.py:150-213
- OpenRouter monkey-patch @ cohost_v4.py:62-66
- TTS chain build @ cohost_v4.py:1991-2017
- LLM build @ cohost_v4.py:1983-1989

### Integration Points
- **Phase 5 (FastAPI Proxy)** swaps `genai_client = genai.Client(api_key=GEMINI_API_KEY)` for a JWT-authed proxy URL pointed at `api.altidus.world`. `tts_chain` similarly switches to proxy-routed OpenRouter. Both require minimal Phase 4 code changes — just URL + auth header.
- **Phase 6 (Genre-Aware Phase Detection)** doesn't touch Phase 4's wiring; it changes `classify_phase` in `vibemix.state.phase`.
- **Phase 10 (Prompt Template Matrix)** layers ON TOP of `persona.py`'s `SYSTEM_INSTRUCTION` — Phase 4 ships single persona; Phase 10 ships 6-cell matrix.
- **Phase 11 (Tauri Shell)** wraps `python -m vibemix` as a PyInstaller --onedir sidecar.
- **Phase 12 (Live Session UI)** consumes the WS bus from `ws_broadcast` — Phase 4's bus format is the contract.
- **Phase 13 (Mascot Avery)** consumes the same WS bus.

</code_context>

<specifics>
## Specific Ideas

- **Monkey-patch ordering** is load-bearing. Place `_openai_tts_mod.AUDIO_STREAM_MODELS.add("google/gemini-3.1-flash-tts-preview")` IMMEDIATELY after `from livekit.plugins.openai import tts as _openai_tts_mod` and BEFORE any `openai_plugin.TTS(...)` instantiation. If imports get reorganized, the patch goes stale silently.
- **OpenRouter PCM format:** `response_format="pcm"` is the magic word — without it OpenRouter returns mp3 by default and LiveKit can't decode the SSE stream.
- **Per-invocation dump folder structure** is part of the live-debugging UX Kaan uses today (`last_gemini_audio.wav` shortcut in session root). Don't reorganize this.
- **`screen_jpeg = None` in llm_node** is deliberate (v4:1503 comment). The screen image Part is dead code; keep the conditional include path but the path is never taken because of the hardcoded None. Phase 10 may revisit if screen evidence proves useful.
- **`coach_loop` 2.0s warmup** lets audio/state catch up before the first event poll.
- **`mic_active_frames >= 3` + `0.6s silence`** is the KAAN_SPOKE trigger threshold — short enough for natural conversation, long enough not to fire on coughs.
- **In-flight stale-clear at 12s** prevents a hung generation from blocking forever.

</specifics>

<deferred>
## Deferred Ideas

- FastAPI proxy + install-UUID JWT → Phase 5 (replaces direct GEMINI_API_KEY usage)
- 6-cell prompt template matrix → Phase 10
- Genre-aware phase detection → Phase 6
- Tauri shell + PyInstaller bundling → Phase 11
- Settings UI for voice / mode / output device → Phase 12
- Mascot Avery SVG render → Phase 13
- `allow_interruptions=True` and proper buffer-clear semantics → out of v1 scope (would require a barge-in design pass)
- Hallucination verification gate → Phase 16
- Recording browser UI → Phase 15
- Hot-plug MIDI re-enumeration → Phase 9

</deferred>
