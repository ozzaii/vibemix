# Phase 2: Audio Core Port — POC Pattern Map (v4 canonical)

**Date:** 2026-05-11
**Mapper:** gsd-pattern-mapper
**Canonical baseline:** `cohost_v4.py` (NOT v3 — superseded 2026-05-11 after Kaan's live tuning session)
**Phase 1 contract:** `src/vibemix/platform/audio.py` (`AudioBackend`, `AudioStream`, `AudioCallback`, `Kind`)
**Bug under repair:** PITFALLS.md P5 — `np.concatenate`-per-callback at v4:300 (`AudioBuffer.push`) + v4:462 (`MicBuffer.push`)

---

## How to Read This File

Each primitive section below pins:
1. **v4 anchor** — exact line range in `cohost_v4.py`
2. **Verbatim signature** — the `__init__` + public-method shape, lifted from v4
3. **Threading model** — who writes (audio thread / asyncio / MIDI thread), who reads
4. **Buffer ownership** — allocation site, snapshot copy semantics
5. **Conversion paths** — dtype + sample-rate handoffs
6. **Public API consumers** — which downstream component (Phase 3+) will import this primitive
7. **Diff from v3** — what changed between v3 (Phase 1 pattern map's baseline) and v4

Treat the code excerpts as **load-bearing shape**, not load-bearing prose. The planner refines names, docstrings, and the ring-buffer rewrite during plan generation.

---

## Per-Primitive Map

### 1. `Levels` (cohost_v4.py:255–286)

**v4 signature:**
```python
class Levels:
    def __init__(self):
        self.music = 0.0
        self.voice = 0.0
        self.mic = 0.0
        self._lock = threading.Lock()

    def update_music(self, mono_int16: np.ndarray): ...
    def update_voice(self, pcm_int16: bytes): ...
    def update_mic(self, samples_float: np.ndarray): ...
    def decay_voice(self): ...
    def snapshot(self) -> dict: ...  # {"music": float, "voice": float, "mic": float}
```

**EMA smoothing coefficients (verbatim from v4:265, 273, 278, 282):**
- `music`: `self.music = self.music * 0.6 + rms * 0.4` (faster — music level shifts mid-mix)
- `voice`: `self.voice = self.voice * 0.5 + rms * 0.5` (50/50 — needs to drop fast so mic-gate releases promptly)
- `mic`: `self.mic = self.mic * 0.5 + rms * 0.5`
- `decay_voice`: `self.voice *= 0.7` (called from `PlaybackQueue.pull()` when buffer empty — ensures voice level decays even with no fresh AI audio)

**Threading model:**
- **Writers:** audio thread (`update_music` from input callback at v4:939, `update_voice` from `PlaybackQueue.push` at v4:512, `update_mic` from `MicBuffer.push` at v4:460)
- **Readers:** asyncio event loop (`state_refresh_loop`, `coach_loop`, `diag_loop`, `ws_broadcast`)
- **Sync:** single `threading.Lock` guards all three floats — held only for the EMA arithmetic, not the RMS compute (which runs lock-free on caller's stack)

**Buffer ownership:**
- Caller owns the input ndarray/bytes — `Levels` never retains a reference
- `snapshot()` returns a fresh dict (not a view) — safe to read concurrent with updates

**Conversion paths:**
- `update_music`: `int16 ndarray` → `float32` → RMS / 32768.0 (normalize to 0..1)
- `update_voice`: `bytes` → `int16` via `np.frombuffer` → `float32` → RMS / 32768.0
- `update_mic`: `float32` already (no normalize — samples come from sounddevice float32 stream which is already in -1..1)

**Public API consumers:**
- `MicBuffer._current_gain()` reads `levels.voice` for AI-talk gate (v4:450)
- `state_refresh_loop` reads `levels.snapshot()` for `MusicState.update_levels`
- `coach_loop` reads `levels.mic` for KAAN_SPOKE detection
- `ws_broadcast` reads `levels.snapshot()` @30fps for mascot
- `diag_loop` reads `levels.snapshot()` for terminal diagnostics

**Diff from v3:** Zero. Class is byte-identical between v3:235–266 and v4:255–286. Lift as-is.

---

### 2. `AudioBuffer` (cohost_v4.py:289–436)

**v4 signature:**
```python
class AudioBuffer:
    """Rolling 16kHz int16 mono PCM ring. Source of truth for audio features."""

    def __init__(self, seconds: float = 30.0, sr: int = INPUT_SR_TARGET): ...
    def push(self, pcm_int16: np.ndarray): ...                  # <-- THE BUG (v4:300)
    def snapshot_wav(self, seconds: float,
                     normalize_peak_dbfs: float | None = -3.0) -> bytes: ...
    def snapshot_features(self, seconds: float = 5.0) -> dict: ...
    def energy_curve(self, seconds: float = 12.0, hop: float = 1.0) -> list: ...
    def long_arc_curve(self, seconds: float = 120.0, hop: float = 10.0) -> list: ...
    def estimate_bpm(self, seconds: float = 6.0) -> float: ...
```

**THE BUG (v4:298–302):**
```python
def push(self, pcm_int16: np.ndarray):
    with self._lock:
        self._buf = np.concatenate([self._buf, pcm_int16])   # alloc per call
        if len(self._buf) > self._max_samples:
            self._buf = self._buf[-self._max_samples:]       # alloc again
```
At 100Hz callback rate × 4.5MB ring (140s × 16kHz × int16), this allocates ~900MB/s of throwaway ndarrays. **Phase 2 replaces this with pre-allocated `np.zeros(max_samples, dtype=int16)` + write-pointer with modular indexing.** Snapshot reads concatenate two slices around the wrap point (one allocation per snapshot, not per push).

**Instantiation sites (v4:1880–1881):**
```python
audio_buf = AudioBuffer(seconds=140.0, sr=INPUT_SR_TARGET)              # 140s × 16kHz int16 = 4.5MB
clean_audio_buf = AudioBuffer(seconds=INVOKE_AUDIO_SECONDS + 5.0,       # 23s × 16kHz int16 = 740KB
                              sr=INPUT_SR_TARGET)
```
**v4 dual-buffer model:** `audio_buf` gets gain-boosted state samples (`state48 = music48 * MUSIC_GAIN_TO_GEMINI`) for BPM/RMS feature math; `clean_audio_buf` gets natural-level samples for the LLM Part snapshot (avoids 8x clipping). Both go through the same push path → both need the ring fix.

**`snapshot_features(seconds=5.0)` return contract (v4:371–379):**
```python
{
    "silent": bool,           # rms < SILENT_RMS
    "rms": float,             # rounded to 4 decimals
    "onsets_per_sec": float,
    "sub_share": float,       # 20–100 Hz / total
    "low_share": float,       # 100–300 Hz / total
    "mid_share": float,       # 300–4000 Hz / total
    "high_share": float,      # 4000–8000 Hz / total
}
```
Or, if `arr.size < self._sr // 4`: `{"silent": True, "rms": 0.0}` (early-out guard at v4:336).

**FFT pipeline (v4:352–369):**
- `spec_win = 1 << 14` (16384 samples = ~1.02s @ 16kHz)
- Hann window → `np.fft.rfft` → magnitude
- Five band-energy slices via `band_energy(lo, hi)` closure
- Total energy + `1e-9` denom guard

**BPM autocorr (v4:410–436):**
- 6s window → 100Hz envelope frames → mean-subtract → `np.correlate` full → take positive lags 30–60 (corresponds to ~100–200 BPM)
- Returns `60.0 * 100.0 / best_lag` rounded to 1 decimal
- Returns `0.0` on insufficient data

**Threading model:**
- **Writer:** audio thread only (`push` called from sounddevice input callback at v4:930, 935)
- **Readers:** asyncio (`state_refresh_loop` calls `snapshot_features`, `energy_curve`, `long_arc_curve`, `estimate_bpm`; `coach_loop` / `DJCoHostAgent.llm_node` call `snapshot_wav`)
- **Sync:** `threading.Lock` — held for the copy-out portion of reads only (compute then runs on the caller's stack with the snapshot)

**Buffer ownership:**
- `push(pcm_int16)`: caller owns input array; v4 currently copies via `np.concatenate` (the bug)
- `snapshot_wav` / `snapshot_features` / `energy_curve`: return fresh objects (bytes / dict / list) — caller owns the copy

**Conversion paths:**
- `push`: pre-converted `int16` from caller (input callback does `np.clip(... * 32767).astype(np.int16)`)
- `snapshot_features` math: `int16 → float32 / 32768.0` to get -1..1 then RMS / FFT
- `snapshot_wav`: optional peak-dBFS normalize, then wraps PCM in WAV header via `wave.open(BytesIO, "wb")`

**Public API consumers:**
- Phase 3 `state_refresh_loop` — `snapshot_features`, `energy_curve`, `long_arc_curve`, `estimate_bpm` (all four)
- Phase 4 LiveKit `DJCoHostAgent.llm_node` — `snapshot_wav(INVOKE_AUDIO_SECONDS)` for the inline audio Part
- Phase 6 genre-aware re-tuning may add a `set_thresholds()` mutator — out of scope for Phase 2

**Diff from v3:**
- Class is byte-identical except `snapshot_wav` docstring rewording (v3:285–290 → v4:305–308): v3 says "Gemini rejects raw audio/pcm — must be WAV-wrapped", v4 says "Gemini downsamples inline audio to 16kHz mono internally so this is the canonical format. Peak-normalize to a consistent loudness regardless of djay master level." Pure docs.
- `MUSIC_GAIN_TO_GEMINI` changed from 8.0 (v3) to 1.0 (v4) — affects the ndarray contents handed to `push`, not the class itself.

---

### 3. `MicBuffer` (cohost_v4.py:439–477)

**v4 signature:**
```python
class MicBuffer:
    MAX_FRAMES = 48000 * 200 // 1000      # 9,600 samples = 200ms @ 48kHz

    def __init__(self, gain: float, levels: Levels): ...
    def _current_gain(self) -> float: ...   # auto-mute during AI talk + hold window
    def push(self, samples: np.ndarray): ...    # <-- BUG (v4:462)
    def pull(self, n_samples: int) -> np.ndarray: ...
```

**THE BUG (v4:459–464):**
```python
def push(self, samples: np.ndarray):
    self._levels.update_mic(samples * self._current_gain())
    with self._lock:
        self._buf = np.concatenate([self._buf, samples])     # alloc per call
        if len(self._buf) > self.MAX_FRAMES:
            self._buf = self._buf[-self.MAX_FRAMES:]         # alloc again
```
Same `np.concatenate` regression as `AudioBuffer`. Ring is much smaller (38KB at float32) so the absolute waste is lower, but the per-callback alloc cost still dominates a real-time thread. Same fix: pre-allocated float32 ring + write-pointer.

**`_current_gain()` auto-mute logic (v4:449–457):**
```python
def _current_gain(self) -> float:
    ai = self._levels.voice
    now = time.time()
    if ai > AI_TALK_THRESHOLD:               # AI is talking RIGHT NOW
        self._last_ai_active = now
        return MIC_GAIN_AT_AI_TALK            # = 0.0
    if now - self._last_ai_active < MIC_HOLD_AFTER_AI_MS / 1000:
        return MIC_GAIN_AT_AI_TALK            # still in 350ms hold window
    return self.base_gain
```
This is **the feedback-suppression IP** — `levels.voice` reads from `Levels` (which `PlaybackQueue.push` writes), so the mic is gain-zeroed the instant any AI audio enters the playback queue, then held mute for 350ms after AI silence to catch tails. Phase 2 lifts verbatim.

**Threading model:**
- **Writer:** audio thread — mic stream callback at v4:1897–1901 (`mic.push(mono.astype(np.float32))`)
- **Reader:** audio thread — main input callback at v4:918 (`mic.pull(len(music48))` to align cadence). LiveKit `start_input_to_session` discards pulled samples (Phase 4 may resurrect for mic-into-AgentSession push)
- **Sync:** `threading.Lock` — wraps both push (write) and pull (drain) operations

**Buffer ownership:**
- `push`: caller owns the input samples; v4 concatenates a copy
- `pull(n)`: returns a fresh `np.ndarray` of size `n` — left-aligned with zero-pad when buffer underflows (v4:469–474)

**Conversion paths:**
- Native float32 throughout — no dtype conversion. mic stream opens at 48kHz mono float32 (v4:1903–1906), `MicBuffer` keeps it at 48kHz float32, mic levels are float32 RMS (not divided by 32768 unlike `update_music`).

**Public API consumers:**
- Phase 4 LiveKit AgentSession — `pull()` to feed mic into `session.push_audio` (currently discarded in v4 — see v4:918 comment "keep cadence aligned, discard samples")
- Phase 3 `state_refresh_loop` reads `levels.mic` (which `MicBuffer.push` writes via `_levels.update_mic` at v4:460) for KAAN_SPOKE detection

**Diff from v3:** Byte-identical (v3:421–459 ↔ v4:439–477). Lift as-is.

---

### 4. `PassthroughBuffer` (cohost_v4.py:480–500)

**v4 signature:**
```python
class PassthroughBuffer:
    MAX_BYTES = 48000 * 2 * 4 // 2      # 192,000 bytes = 500ms @ 48kHz stereo float32

    def __init__(self): ...
    def push(self, b: bytes): ...
    def pull(self, n_bytes: int) -> bytes: ...
```

**Storage:** `bytearray` (NOT ndarray) — push uses `extend`, pull uses slice + `del`. This is the only buffer that uses `bytearray` because passthrough is end-to-end raw bytes (no math, no resample, no dtype conversion — just copy bytes from input callback to output callback).

**Drop-half-on-overflow logic (v4:487–492):**
```python
def push(self, b: bytes):
    with self._lock:
        self._buf.extend(b)
        if len(self._buf) > self.MAX_BYTES:
            drop = len(self._buf) - self.MAX_BYTES // 2
            del self._buf[:drop]
```
Drops back to 50% capacity (not just trim-to-max) — gives ~250ms headroom before next overflow.

**Underflow returns `b""` (v4:495–497), not zero-pad** — caller checks `if not raw or len(raw) < n_bytes: outdata.fill(0)` at v4:863. Different from `PlaybackQueue.pull` which zero-pads internally.

**Disable-at-gain-0 behavior (v4:909–912):**
```python
if PASSTHROUGH_GAIN != 1.0:
    passthrough.push((indata * PASSTHROUGH_GAIN).astype(np.float32).tobytes())
else:
    passthrough.push(indata.tobytes())
```
With `PASSTHROUGH_GAIN = 0.0` (v4 default at line 112), all pushed bytes are zeroed at the input — the output stream still drains the ring, just plays silence. This is intentional: keeps the stream alive (no callback starvation diagnostics) while the user listens to djay directly through djay's own output.

**Threading model:**
- **Writer:** audio thread (input callback at v4:910/912)
- **Reader:** audio thread (passthrough output callback at v4:862)
- **Sync:** `threading.Lock`

**Buffer ownership:** caller owns bytes; v4 copies via `extend`. Phase 2 ring-buffer rewrite *may* keep `bytearray` here OR convert to a fixed-size `bytes` ring with write-pointer — call planner's discretion. The CONTEXT specifies "~50ms" but v4 actually uses 500ms (`MAX_BYTES = 192000`) — Phase 2 plan should reconcile (CONTEXT may be wrong; v4 is the source of truth).

**Conversion paths:** none — pure bytes copy.

**Public API consumers:**
- Phase 2's own `AudioMacOS.start_passthrough()` — drains in output callback

**Diff from v3:** Byte-identical (v3:462–482 ↔ v4:480–500).

---

### 5. `PlaybackQueue` (cohost_v4.py:503–523)

**v4 signature:**
```python
class PlaybackQueue:
    def __init__(self, levels: Levels): ...
    def push(self, pcm: bytes): ...
    def pull(self, n_bytes: int) -> bytes: ...
```

**Storage:** `bytearray` — same pattern as `PassthroughBuffer` but **no max cap** (unbounded growth allowed because AI talks in short bursts, never sustained).

**Levels integration (v4:509–518):**
```python
def push(self, pcm: bytes):
    with self._lock:
        self._buffer.extend(pcm)
    self._levels.update_voice(pcm)         # update AI voice RMS on push

def pull(self, n_bytes: int) -> bytes:
    with self._lock:
        if not self._buffer:
            self._levels.decay_voice()      # decay when empty
            return b"\x00" * n_bytes
        chunk = bytes(self._buffer[:n_bytes])
        del self._buffer[:n_bytes]
        if len(chunk) < n_bytes:
            chunk += b"\x00" * (n_bytes - len(chunk))
        return chunk
```
**Key behaviors:**
- `push` updates `levels.voice` immediately (LATEST push, not aggregated) → mic-gate engages within one callback of AI audio arriving
- Empty `pull` calls `levels.decay_voice()` (multiplies by 0.7) → ensures voice level falls to 0 within a few callbacks once AI stops talking, even with no fresh push
- Underflow zero-pads inline (unlike `PassthroughBuffer.pull` which returns `b""`)

**Threading model:**
- **Writers:** asyncio + LiveKit threads — `PlaybackQueueAudioOutput.capture_frame` at v4:1528+ (Phase 4 territory)
- **Reader:** audio thread (voice output callback at v4:881–882)
- **Sync:** `threading.Lock`

**Buffer ownership:** caller owns bytes; v4 copies via `extend`.

**Conversion paths:** none — 24kHz int16 mono bytes throughout. Stream consumer expects raw int16 (`sd.RawOutputStream` at v4:884–887, `dtype="int16"`, `channels=1`, `samplerate=OUTPUT_SR=24000`).

**Public API consumers:**
- Phase 4 LiveKit `PlaybackQueueAudioOutput.capture_frame` — `playback.push(frame_bytes)`
- Phase 2's own `AudioMacOS.start_playback()` — drains in output callback

**Diff from v3:** Byte-identical (v3:485–505 ↔ v4:503–523).

---

### 6. `VoiceRecorder` (cohost_v4.py:769–848)

**v4 signature:**
```python
class VoiceRecorder:
    def __init__(self): ...                          # creates recordings/YYYYMMDD-HHMMSS/
    def push_voice(self, pcm_bytes: bytes): ...     # → voice.wav  (24kHz mono int16)
    def push_input(self, pcm_bytes: bytes): ...     # → input.wav  (16kHz mono int16)
    def log_event(self, kind: str, **fields): ...  # → events.jsonl
    def close(self): ...
    # Private:
    def _write_event_locked(self, rec: dict): ...
```

**Session directory layout (v4:770–801):**
```
recordings/
└── 20260511-143027/        # YYYYMMDD-HHMMSS, parsed via datetime.now().strftime
    ├── voice.wav            # 24kHz mono int16  (AI replies)
    ├── input.wav            # 16kHz mono int16  (BlackHole-captured music + mic mix)
    └── events.jsonl         # JSONL timeline, timestamped from session start
```
**Recording root:** `Path(__file__).parent / "recordings"` — v4 hardcodes relative-to-script. Phase 2 should move to a configurable path (e.g. project root via `Path.cwd()` or env var) so the package install doesn't pollute the site-packages dir.

**Initial event written at construction (v4:792–799):**
```python
self._write_event_locked({
    "t": 0.0,
    "kind": "session_start",
    "wall_clock_iso": wall_start.isoformat(timespec="milliseconds"),
    "wall_clock_unix": round(wall_start.timestamp(), 3),
    "session_dir": str(self.session_dir.name),
})
```
**JSONL event shape:** every event has `t` (seconds from session start, rounded to 3 decimals) + `kind` + arbitrary `**fields`. Written line-by-line with `json.dump` + `\n` + `flush`.

**WAV writer model (v4:778–786):**
- `wave.open(path, "wb")` for both files, kept open for the session lifetime
- `setnchannels(1)`, `setsampwidth(2)`, `setframerate(OUTPUT_SR=24000)` for voice
- `setnchannels(1)`, `setsampwidth(2)`, `setframerate(INPUT_SR_TARGET=16000)` for input
- `writeframes(pcm_bytes)` called per push — internal buffering by the `wave` module

**Threading model:**
- **Writers:** audio thread (`push_input` from input callback at v4:931, `push_voice` indirectly via `PlaybackQueue` consumer); asyncio (`log_event` from `coach_loop`, `EventDetector`, error handlers)
- **Sync:** single `threading.Lock` guards all three writers (WAVs + JSONL)
- **Error policy:** every writer wraps in `try/except Exception: pass` — recording is best-effort, never blocks the live pipeline

**Buffer ownership:** caller owns bytes; `wave.writeframes` internally copies.

**Conversion paths:** none — pre-converted int16 bytes at the expected rate for each WAV.

**Public API consumers:**
- Phase 2 audio I/O — `push_input` from input callback
- Phase 4 LiveKit `PlaybackQueueAudioOutput` — `push_voice` from AI audio frame bridge
- Phase 3 `EventDetector` / `coach_loop` — `log_event` for trigger + AI reply events
- Phase 15 (Recording UI) — wraps the directory layout with retention policy

**Diff from v3:** Byte-identical (v3:749–828 ↔ v4:769–848). Lift as-is.

---

## Tuning Constants Map

All constants below are **load-bearing** (Daft Punk / French Touch / Digitalism profile, 125–128 BPM, tuned against real DJ sessions on 2026-05-11). Lift to `src/vibemix/audio/constants.py` verbatim.

| Constant | v4 line | v4 value | v3 value | Domain | Phase consumer |
|----------|---------|----------|----------|--------|----------------|
| `INVOKE_AUDIO_SECONDS` | 100 | `18.0` | `10.0` | audio snapshot length to LLM | Phase 4 (LLM cascade) — sizes `clean_audio_buf` |
| `INPUT_SR_NATIVE` | 106 | `48000` | `48000` | I/O | Phase 2 (`AudioMacOS`) — input/passthrough stream rate |
| `INPUT_SR_TARGET` | 107 | `16000` | `16000` | I/O | Phase 2 — `AudioBuffer` default rate |
| `OUTPUT_SR` | 108 | `24000` | `24000` | I/O | Phase 2 — voice output stream + `voice.wav` |
| `INPUT_CHUNK_FRAMES` | 109 | `480` | `480` | I/O | Phase 2 — input stream blocksize (= 10ms @ 48kHz) |
| `OUTPUT_BLOCKSIZE` | 110 | `256` | `256` | I/O | Phase 2 — passthrough output blocksize |
| `VOICE_BLOCKSIZE` | 111 | `1024` | `1024` | I/O | Phase 2 — voice output blocksize |
| `PASSTHROUGH_GAIN` | 112 | `0.0` | `0.0` | gain | Phase 2 — `start_input_to_session` callback |
| `MUSIC_GAIN_TO_GEMINI` | 113 | **`1.0`** | `8.0` | gain | Phase 2 — input callback before resample (v4 dropped 8x because Daft Punk masters are loudness-war compressed already) |
| `MIC_GAIN` | 116 | `1.0` | `1.0` | gain | Phase 2 — `MicBuffer.base_gain` |
| `MIC_TALK_THRESHOLD` | 117 | `0.09` | `0.09` | gating | Phase 3 — KAAN_SPOKE detector |
| `MIC_GAIN_AT_AI_TALK` | 118 | `0.0` | `0.0` | gating | Phase 2 — `MicBuffer._current_gain` |
| `MIC_HOLD_AFTER_AI_MS` | 119 | `350` | `350` | gating | Phase 2 — `MicBuffer._current_gain` hold window |
| `AI_TALK_THRESHOLD` | 120 | `0.02` | `0.02` | gating | Phase 2 — `MicBuffer._current_gain` activation |
| `SILENT_RMS` | 127 | **`0.012`** | `0.008` | engine | Phase 2 / 3 — silence threshold (v4 raised for FT loudness profile) |
| `LOW_RMS` | 128 | **`0.040`** | `0.025` | engine | Phase 3 — `classify_phase` low band |
| `PEAK_RMS` | 129 | **`0.110`** | `0.055` | engine | Phase 3 — `classify_phase` peak band |
| `AUDIBLE_DEBOUNCE_SEC` | 130 | `0.6` | `0.6` | engine | Phase 3 — audible→True debounce |
| `SILENCE_DEBOUNCE_SEC` | 131 | `1.2` | `1.2` | engine | Phase 3 — audible→False debounce |
| `EVENT_GLOBAL_MIN_GAP` | 132 | **`7.0`** | `3.0` | engine | Phase 3 — global cooldown (v4 lengthened for OpenRouter budget) |
| `HEARTBEAT_SEC` | 133 | **`45.0`** | `25.0` | engine | Phase 3 — heartbeat event cadence (v4 lengthened) |
| `MIN_EVENT_GAP_PER_TYPE` | 134–142 | dict (see below) | dict (different values) | engine | Phase 3 — per-event-type cooldowns |
| `TRACK_CHANGE_MIN_CONFIDENCE` | 143 | `0.5` | (absent) | engine | Phase 3 — phantom nowplaying-cli filter (v4 new) |
| `MUSIC_PRESENCE_MIN_SECONDS` | **1176** (nested in `EventDetector` class) | `4.0` | `4.0` | engine | Phase 3 — sustained-audible gate before auto-events |
| `BPM_VALID_MIN` | **1179** (nested) | `100.0` | `100.0` | engine | Phase 3 — autocorr-noise reject |
| `BPM_VALID_MAX` | **1180** (nested) | `180.0` | `180.0` | engine | Phase 3 — autocorr-noise reject |

**`MIN_EVENT_GAP_PER_TYPE` dict (v4:134–142, verbatim):**
```python
MIN_EVENT_GAP_PER_TYPE = {
    "TRACK_CHANGE": 5.0,
    "PHASE": 10.0,
    "LAYER_ARRIVAL": 10.0,
    "MIX_MOVE": 14.0,
    "HEARTBEAT": HEARTBEAT_SEC,   # 45.0
    "MIC": 3.0,
    "MANUAL": 1.5,
}
```

**Note on `BPM_VALID_MAX`:** CONTEXT.md asks Phase 2 to "find the line" for `BPM_VALID_MAX` — it lives at **cohost_v4.py:1180** *inside* `EventDetector` (alongside `BPM_VALID_MIN` at 1179 and `MUSIC_PRESENCE_MIN_SECONDS` at 1176). These three are class-attributes, not module-level constants. Phase 2 should lift them OUT to `constants.py` so Phase 3 can import without dragging `EventDetector` along — that's a refactor improvement, not a port.

**Important — `INVOKE_AUDIO_SECONDS` is NOT in Phase 2's scope.** It's the audio-snapshot length the LLM consumes (Phase 4). However, it sizes `clean_audio_buf` (`AudioBuffer(seconds=INVOKE_AUDIO_SECONDS + 5.0)` at v4:1881), so Phase 2 should expose `INVOKE_AUDIO_SECONDS` in `constants.py` as well — both phases consume it.

---

## sounddevice Call Sites Map

All four streams Phase 2 implements via `AudioMacOS`. The `find_device` helper is a fifth required method.

| Stream / helper | v4 lines | Stream class | Sample rate | Channels | Dtype | Blocksize | Latency | Notes |
|-----------------|----------|--------------|-------------|----------|-------|-----------|---------|-------|
| `find_device(name, kind)` | 239–248 | (helper) | n/a | n/a | n/a | n/a | n/a | Linear scan of `sd.query_devices()`, case-insensitive substring; `RuntimeError` on miss. **No sample-rate validation** — that's the Phase 2 addition. |
| `start_input_to_session` | 893–947 | `sd.InputStream` | `INPUT_SR_NATIVE=48000` | 2 | `"float32"` | `INPUT_CHUNK_FRAMES=480` | `"low"` | Master capture from BlackHole. Callback @v4:906 resamples to 16kHz via `scipy.signal.resample_poly(_, 16000, 48000)`, writes to `audio_buf` (gain-boosted state) + `clean_audio_buf` (natural) + `passthrough` + `recorder`. Mic is pulled-and-discarded for cadence alignment (v4:918). |
| `start_passthrough_stream` | 855–875 | `sd.OutputStream` | `INPUT_SR_NATIVE=48000` | 2 | `"float32"` | `OUTPUT_BLOCKSIZE=256` | `"low"` | djay → speakers stereo passthrough. Drains `PassthroughBuffer.pull(n_bytes)`. Falls back to `outdata.fill(0)` on underflow. |
| `start_playback_stream` | 878–890 | `sd.RawOutputStream` | `OUTPUT_SR=24000` | 1 | `"int16"` | `VOICE_BLOCKSIZE=1024` | `"low"` | AI voice → headphones. Drains `PlaybackQueue.pull(frames * 2)` (×2 for int16 bytes). Note `RawOutputStream` (vs `OutputStream` for passthrough). |
| Mic stream (inline in `main`) | 1895–1908 | `sd.InputStream` | `INPUT_SR_NATIVE=48000` | 1 | `"float32"` | `INPUT_CHUNK_FRAMES=480` | `"low"` | MacBook mic capture. Wrapped in try/except — non-fatal fallback to `mic_stream = None` if device not found. Callback at v4:1897 mono-converts then `mic.push(mono.astype(np.float32))`. **This stream should move into a factory function in Phase 2** (currently inline in `main` — anti-pattern). |

**Sample-rate sanity check addition (Phase 2 only — not in v4):**
After opening the input stream, query the actual rate sounddevice negotiated. If `stream.samplerate != INPUT_SR_NATIVE`, raise a typed error with the actionable message from CONTEXT.md. v4 silently accepts whatever sounddevice gives — that's the bug Kaan hit on 2026-05-11.

**Stream lifecycle (v4 pattern):**
- All four factories `start()` immediately before returning
- No `stop()` / `close()` call sites in `main` — relies on process exit + sounddevice cleanup
- Phase 2 `AudioStream` Protocol (Phase 1 defined `start()` / `stop()` / `close()` / `latency_ms` property) — Phase 2 wires these explicitly so the test suite can mount/dismount streams without leaking

---

## Wiring in `main()` — How v4 Glues It Together (v4:1857–1947)

For reference when the planner writes the `_audio_macos.py` factory + the new `vibemix.audio.__init__` re-exports:

```python
# Device lookup (v4:1862-1863)
input_idx = find_device(INPUT_DEVICE, "input")           # "BlackHole 2ch"
output_idx = find_device(OUTPUT_DEVICE, "output")        # "External Headphones"

# Buffer allocation (v4:1875-1881)
levels = Levels()
playback = PlaybackQueue(levels)
passthrough = PassthroughBuffer()
mic = MicBuffer(gain=MIC_GAIN, levels=levels)
audio_buf = AudioBuffer(seconds=140.0, sr=INPUT_SR_TARGET)
clean_audio_buf = AudioBuffer(seconds=INVOKE_AUDIO_SECONDS + 5.0, sr=INPUT_SR_TARGET)
recorder = VoiceRecorder()

# Stream startup (v4:1891-1892 + 1895-1907)
voice_stream = start_playback_stream(output_idx, playback)
pass_stream = start_passthrough_stream(output_idx, passthrough)
try:
    mic_idx = find_device(MIC_DEVICE, "input")
    mic_stream = sd.InputStream(device=mic_idx, ..., callback=mic_callback)
    mic_stream.start()
except Exception:
    mic_stream = None       # graceful fallback
# (start_input_to_session is called later, after AgentSession init)
```

**This wiring is what Phase 2's `AudioMacOS` class encapsulates.** The CONTEXT.md recommendation of `AudioMacOS(buffers: BufferRegistry, levels: Levels)` matches this — six buffer/levels objects pass through; the class internalizes the stream-startup choreography behind `AudioBackend` Protocol methods.

---

## File-Map Recommendation for Phase 2

```
src/vibemix/
├── audio/
│   ├── __init__.py           # re-exports Levels, AudioBuffer, MicBuffer,
│   │                         # PassthroughBuffer, PlaybackQueue, VoiceRecorder,
│   │                         # BufferRegistry, snapshot_features (the helper)
│   ├── constants.py          # All ~24 tuning constants verbatim from v4
│   │                         # (incl. MUSIC_PRESENCE_MIN_SECONDS, BPM_VALID_MIN/MAX
│   │                         # lifted OUT of EventDetector)
│   ├── buffers.py            # AudioBuffer, MicBuffer, PassthroughBuffer, PlaybackQueue
│   │                         # — all four with pre-allocated rings + write-pointer
│   ├── levels.py             # Levels (verbatim from v4:255-286)
│   ├── features.py           # snapshot_features() + estimate_bpm() + energy_curve()
│   │                         # + long_arc_curve() lifted from AudioBuffer methods
│   │                         # — keeps buffers.py focused on storage, not DSP
│   ├── recorder.py           # VoiceRecorder (verbatim from v4:769-848, with
│   │                         # recordings root made configurable)
│   └── registry.py           # BufferRegistry dataclass — bundle for AudioMacOS ctor
└── platform/
    └── _audio_macos.py       # AudioMacOS — concrete AudioBackend impl
                              # — wraps sd.InputStream / sd.OutputStream / sd.RawOutputStream
                              # — implements sample-rate sanity check
                              # — defines callbacks as inner closures (v4 pattern)
                              # — implements find_device with typed DeviceNotFoundError
```

**Two notable splits from the CONTEXT-suggested layout:**
1. **`features.py` separate from `buffers.py`** — v4 has the DSP methods (`snapshot_features`, `estimate_bpm`, `energy_curve`, `long_arc_curve`) glued to `AudioBuffer`. Keeping them there is fine, but moving them into free functions in `features.py` that take a `(pcm: np.ndarray, sr: int)` makes them unit-testable without standing up a buffer. **Planner's discretion** — both designs are defensible.
2. **`registry.py` for `BufferRegistry`** — CONTEXT mentions `BufferRegistry` but doesn't say where. Co-locating it with the buffer module makes the import path symmetric (`from vibemix.audio import BufferRegistry, Levels, ...`).

---

## Anti-Patterns to NOT Carry Forward

Spotted in v4 source — the firewall + ring-buffer rewrite eliminates each:

1. **`np.concatenate` per push** (v4:300 + v4:462) — **THE bug Phase 2 fixes.** Replace with pre-allocated `np.ndarray` + write-pointer + modular indexing. Verify with `tracemalloc`: 100 push calls in a tight loop should allocate 0 new ndarrays.

2. **Module-level `_HAS_VISION` / `_HAS_WS` / `_HAS_QUARTZ` feature flags** (v4:70–91) — Phase 1's `AudioBackend.is_available()` model makes these obsolete. If the macOS audio backend can't import `sounddevice`, the import fails loud — no `_HAS_AUDIO` flag silently disabling capture.

3. **Hardcoded device-name strings at module top** (`INPUT_DEVICE = "BlackHole 2ch"` at v4:101, `OUTPUT_DEVICE = "External Headphones"` at v4:102, `MIC_DEVICE = "MacBook Pro Microphone"` at v4:103) — Phase 2 keeps the defaults in `constants.py` but routes them through `AudioBackend.find_device(name_substring, kind)` so the calibration wizard (Phase 11) can override at runtime without monkey-patching module globals.

4. **Hardcoded recordings path relative to `__file__`** (`Path(__file__).parent / "recordings"` at v4:771) — package install would write WAVs into site-packages. Phase 2 makes the root configurable (constructor arg defaulting to `Path.cwd() / "recordings"` or an env-var-driven path).

5. **Inline mic stream in `main()`** (v4:1895–1908) — every other stream has a factory function (`start_input_to_session`, `start_passthrough_stream`, `start_playback_stream`). Mic doesn't. Phase 2 wraps it as `AudioMacOS.start_mic_capture()` so the surface is symmetric.

6. **No sample-rate validation** (the bug Kaan hit live on 2026-05-11) — `sd.InputStream(samplerate=48000)` silently accepts whatever device rate is actually configured. Phase 2 queries `stream.samplerate` post-`start()` and raises typed error on mismatch.

7. **`pull` returns `b""` on underflow vs zero-pads inline** — `PassthroughBuffer.pull` returns empty bytes (caller zero-fills), `PlaybackQueue.pull` zero-pads inline. Inconsistency; not strictly wrong, but Phase 2 should pick one policy and document it. Recommend: zero-pad inline everywhere (caller never has to branch on length).

8. **Mic samples discarded after `pull(len(music48))` in input callback** (v4:918, comment "keep cadence aligned, discard samples") — the cadence trick works but is fragile. Phase 4 will properly feed mic into `AgentSession.push_audio`; Phase 2 just needs to make sure the API allows it cleanly (don't bake the discard into the abstraction).

---

## Diff Highlights: v4 vs. v3

For the planner — what shifted between Phase 1's pattern map (v3-anchored) and Phase 2's (v4-anchored):

### Buffer classes (Levels, AudioBuffer, MicBuffer, PassthroughBuffer, PlaybackQueue, VoiceRecorder)
**Byte-identical between v3 and v4.** Only difference: `AudioBuffer.snapshot_wav` docstring reworded (v3 mentions "Gemini rejects raw audio/pcm" — that constraint relaxed; v4 reframes as "canonical 16kHz mono format + loudness normalization"). No code change.

### Tuning constants — **the meaningful diff**
v4 retuned the entire engine profile for Daft Punk / French Touch / Digitalism (125–128 BPM, loudness-war-compressed masters) on 2026-05-11. The 8 constants below are NOT optional carry-overs — they're the load-bearing tuning Kaan validated live:

| Constant | v3 | v4 | Why v4 changed |
|----------|-----|-----|---------------|
| `MUSIC_GAIN_TO_GEMINI` | 8.0 | 1.0 | French Touch masters are already loudness-compressed; 8x was needed for sparse free-tek, clips on FT |
| `SILENT_RMS` | 0.008 | 0.012 | Higher floor — FT room tone reads louder than free-tek silence |
| `LOW_RMS` | 0.025 | 0.040 | FT mid-energy sections sit higher than free-tek breakdowns |
| `PEAK_RMS` | 0.055 | 0.110 | FT drops are full-mix wall-of-sound; ~2x peak vs free-tek |
| `EVENT_GLOBAL_MIN_GAP` | 3.0 | 7.0 | OpenRouter budget allows real talk cadence (vs v3's bare-bones token allotment) |
| `HEARTBEAT_SEC` | 25.0 | 45.0 | v4 cohost talks less often, leans on real events more |
| `INVOKE_AUDIO_SECONDS` | 10.0 | 18.0 | Needed to cover full build-up + drop within one snapshot |
| `TRACK_CHANGE_MIN_CONFIDENCE` | (absent) | 0.5 | New gate to filter phantom nowplaying-cli stale-title fires |

`MIN_EVENT_GAP_PER_TYPE` dict structure unchanged but per-key values diverged across phase-type entries — Phase 2 lifts v4's dict verbatim.

### LLM / TTS architecture (out of scope for Phase 2 but useful context)
v3 used `google_plugin.LLM(gemini-3-flash-preview)` directly in LiveKit `AgentSession`; v4 wraps it with a custom `DJCoHostAgent` that overrides `llm_node` to inject the `clean_audio_buf.snapshot_wav` as an inline `Part` (true multimodal audio input to the LLM). v4 also pivoted TTS from Gemini-native to OpenRouter primary + Gemini-native fallback chain (v4:1923–1946), gated by `_openai_tts_mod.AUDIO_STREAM_MODELS.add(...)` monkey-patch at v4:66. **All of this is Phase 4 territory** — flagged here only so the planner doesn't mistake `clean_audio_buf` for a Phase 2 invention. It's a v4 wiring detail that Phase 2 *enables* (by porting `AudioBuffer`) but doesn't *implement*.

---

## Coverage Summary

| Primitive | v4 anchor | LOC | Has `np.concatenate` bug? | Diff from v3 | Status |
|-----------|-----------|-----|---------------------------|--------------|--------|
| `Levels` | 255–286 | 32 | No | Identical | Ready to port |
| `AudioBuffer` | 289–436 | 148 | **YES (v4:300)** | Docstring-only | Ready to port w/ ring-buffer rewrite |
| `MicBuffer` | 439–477 | 39 | **YES (v4:462)** | Identical | Ready to port w/ ring-buffer rewrite |
| `PassthroughBuffer` | 480–500 | 21 | No (uses `bytearray` + drop-half) | Identical | Ready to port |
| `PlaybackQueue` | 503–523 | 21 | No | Identical | Ready to port |
| `VoiceRecorder` | 769–848 | 80 | No | Identical | Ready to port w/ configurable root |
| `find_device` | 239–248 | 10 | No | Identical | Ready to port w/ sample-rate check |
| `start_input_to_session` | 893–947 | 55 | No | v3:873–927 (renamed in v4) | Ready to port as `AudioMacOS.start_capture()` |
| `start_passthrough_stream` | 855–875 | 21 | No | Identical | Ready to port as `AudioMacOS.start_passthrough()` |
| `start_playback_stream` | 878–890 | 13 | No | Identical | Ready to port as `AudioMacOS.start_playback()` |
| Mic inline stream | 1895–1908 | 14 | No | Identical | Ready to port — wrap as `AudioMacOS.start_mic_capture()` factory |
| Tuning constants (24 names) | 100–143 + 1176–1180 | n/a | n/a | **8 retuned for FT profile** | Ready to lift to `constants.py` |

**Files with no analog in v4 (must be designed fresh in Phase 2):**
- `BufferRegistry` value-object — purely a packaging convenience, no v4 analog (planner discretion: dataclass vs NamedTuple)
- Sample-rate sanity-check error path — new typed exception (recommend `AudioSampleRateMismatch(Exception)` with actionable message)
- Pre-allocated ring + write-pointer machinery — net-new internal data structure replacing `np.concatenate` regression; v4 has zero analog

---

*Pattern mapping: 2026-05-11. Canonical baseline: cohost_v4.py.*
