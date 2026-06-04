# MAP — Recorded-Set Replay into the Capture Pipeline (THE KEYSTONE)

**Date:** 2026-06-04 · **Agent:** read-only mapping · **Branch:** ux-redesign-impeccable
**Question:** Can we feed a recorded DJ set so the state loop + event_detector + Sven react AS IF LIVE, with NO human DJing?

---

## TL;DR VERDICT

**The replay path EXISTS and is REAL — this is much further along than the mission brief assumed.**
A complete, env-gated, in-process file-feed replay backend is **built, wired into `__main__.py`,
tested, and has already produced a real grounded run today (2026-06-04 11:09).** A 1-line WAV +
`VIBEMIX_REPLAY_SESSION=<dir>` makes the real app hear a recording through the normal sounddevice
callback → ring buffer → state loop → event_detector → Sven path, with NO physical audio hardware,
NO BlackHole loopback, NO human at the decks.

**The keystone for the autonomous QA loop is NOT blocked by "is there a feed path" — that's solved.**
The remaining gaps are (a) **no 3-hour recorded set exists on disk** (longest real capture = ~117s),
(b) **replay is strictly REAL-TIME** (a 3h set takes 3h of wall clock — the realtime runner does not
time-warp), and (c) the **fast offline harness** (`replay_harness.py`) drives the primitives directly
but does NOT exercise the real Sven LLM/voice/ws path. So: the wire is hot; what's missing is a
**3h source WAV** and a decision on **realtime-vs-warped** for overnight throughput.

---

## THE TWO REPLAY PATHS (both real, different purposes)

### Path A — REALTIME, full-app, sounddevice-shaped feed (the keystone for QA tonight)

`src/vibemix/platform/_audio_replay.py` (498 lines, landed `3c41254b`..`b8f13fc9`) +
`scripts/eval/replay_live_runner.py` (429 lines).

This launches the **real** `python -m vibemix` and substitutes ONLY the input-capture stream:

- `replay_session_from_env()` reads `VIBEMIX_REPLAY_SESSION` (`_audio_replay.py:30-35`). Hard env gate.
- `maybe_wrap_replay_audio_backend()` / `_midi_` / `_track_` wrap the real macOS backends ONLY when
  that env is set (`_audio_replay.py:38-62`). No env → returns the real backend untouched. **Zero
  prod-path risk.**
- **Wired into the live boot path** — verified in `src/vibemix/__main__.py`:
  - `audio_backend = maybe_wrap_replay_audio_backend(AudioMacOS(registry, recorder))` — `__main__.py:1457`
  - prints `-> replay capture: <session_dir>` — `__main__.py:1458-1459`
  - `midi_macos = maybe_wrap_replay_midi_backend(MidiMacOS())` — `__main__.py:1373`, log `-> replay MIDI tape:` `:1375`
  - `track_macos = maybe_wrap_replay_track_backend(TrackMacOS())` — `__main__.py:1392`, log `-> replay nowplaying:` `:1394`
- `ReplayAudioBackend.find_device("input")` returns a sentinel index `-911` (`_audio_replay.py:68,79-82`)
  so it bypasses the BlackHole-missing FATAL exit (`__main__.py:1466-1480`). Output/passthrough/voice
  streams **delegate to the real macOS backend** (only `find_device` for `input` + `open_capture` are
  overridden — `_audio_replay.py:76-118`), which is correct: the runner mutes voice anyway.
- **THE FEED ITSELF** — `ReplayCaptureStream._run()` (`_audio_replay.py:166-186`): reads `input.wav`,
  resamples to the requested rate, then loops in `block_size` chunks calling
  **`self._callback(block, frames, {}, None)`** — the *exact sounddevice callback signature*
  `(indata, frames, time_info, status)` (see `platform/audio.py:19-20`). After each block it
  `time.sleep(block.shape[0] / sample_rate)` → **strictly real-time pacing on a daemon thread.**
- MIDI replay (`ReplayMidiBackend._run_tape`, `:230-244`) replays `midi.jsonl` at recorded timestamps
  through `controller_state.handle_msg` — so faders/EQ moves fire grounded `[midi:...]` citations.
- Now-playing replay (`ReplayTrackInfo`, `:281-344`) plays `nowplaying.jsonl` at recorded ts → track
  identity / TRACK_CHANGE events fire.

**The runner** (`replay_live_runner.py`):
- `discover_sessions()` walks a corpus dir for any subdir containing `input.wav` (`:78-93`).
- Launches `python -m vibemix` with `VIBEMIX_REPLAY_SESSION`, isolated `HOME`, per-instance
  `VIBEMIX_WS_PORT`/`VIBEMIX_DEBRIEF_PORT`, `VIBEMIX_TTS_ENGINE=off`, `VIBEMIX_DEV_SIDECAR=1`
  (`:115-139`). Supports `--jobs N` for parallel instances (`:405-417`).
- Default `--duration 20.0` s then `SIGINT` (`:141-149`). **This is the realtime knob.**
- Harvests proof: parses stdout for `music=`, `audible=1`, the `-> replay capture:` line, `ws://...`,
  `AI voice output muted`; reads the produced `events.jsonl` for event count, `llm_invoke` count,
  `citation_count` (cited vs zero-non-ack), `slop_suppressed`, `llm_to_tts_delta_ms` max latency
  (`:202-337`). Emits `live-replay-findings.json` with per-scenario `flags` + `verdict`
  (`:192-269`, schema `vibemix_live_replay_findings_v1`).
- Flags already cover the anti-slop/grounded/on-time axes the QA loop needs: `mute`, `citation_zero`,
  `slop_suppressed`, `late` (>6000ms), `no_music_meter`, `no_audible_meter`, `no_recorded_input`,
  `replay_capture_not_selected` (`:205-234`).

**PROOF IT ALREADY RAN:** `.planning/eval-runs/current-source-live-capture-blackhole-20260604-110953/ws_capture_summary.json`
— `n_snapshots=46`, `bpm=171.4`, `cohost_status=LISTENING`, `grounded=true`, real `music_rms`
0.012–0.036, `voice=muted`, `gemini=ok`, `livekit=ok`. So the real app, fed a recording, **heard
real music and held a grounded LISTENING state.** (Caveat: that summary shows `transcript_delta=[]`
— LISTENING with no Sven utterance in the captured window; see Gap 4.)

Tests: `tests/eval/test_replay_live_runner.py`, `tests/runtime/test_replay_audio_backend.py`.

### Path B — OFFLINE deterministic, primitives-only, fast (the eval/scoring twin)

`scripts/eval/replay_harness.py` (53k) + `src/vibemix/audio/buffers.py::AudioBuffer.fill_from_wav`.

- `fill_from_wav(path)` (`buffers.py:120-174`) **bulk-loads** a WAV into the ring under the same lock
  as `push`, downmixing stereo→mono and resampling to 16kHz. **Explicitly NOT the sounddevice path** —
  docstring: "offline replay only; not called from the sounddevice callback" (`:121`), enforced by a
  Phase-37 AUDIT-07 grep guard so `__main__.py` can never call it (`:131-136`).
- `replay_harness.py` (header `:1-33`) walks `--corpus` (default `eval/corpus/sessions`), loads each
  `input.wav` via `fill_from_wav`, drives **the REAL primitives** (EvidenceRegistry + EventDetector +
  CitationLinter — not mocks) at a **1Hz manual tick** across the session duration, runs judges
  (`--judges noop|gemini-3-flash`), and scores against ship thresholds (`DEFAULT_THRESHOLDS` `:55-61`:
  f1_min 0.80, substance_min 0.65, cited_cosine_min 0.4, bypass_max 0.15). **Offline-only invariant:
  MUST NOT open a sounddevice stream (`:30-32`).** Fast (no realtime pacing), but does NOT exercise
  the real `dj_cohost` LLM session, the ws bus, TTS, or `__main__`'s wiring.

**Use both:** Path B for fast, deterministic, scored grounding regression across a fixture corpus;
Path A for the "real app, as-if-live, no human" full-stack proof tonight.

---

## THE CAPTURE INPUT CONTRACT (verified)

The state loop is **decoupled from the OS** behind the `AudioBackend` protocol (`platform/audio.py`):

1. **OS audio thread** (or the replay daemon thread) calls `callback(indata, frames, time_info, status)`
   — the sounddevice shape (`audio.py:19-20`). Real path: `_audio_macos.py::open_capture` (`:675-724`)
   opens `sd.InputStream(dtype="float32", ...)`; if the device runs at a non-analysis rate it wraps the
   callback with a resampler (`:699-711`). Replay path: `ReplayCaptureStream` calls the identical
   callback from a Python thread (`_audio_replay.py:185`).
2. The callback pushes int16 PCM into the **lock-protected `AudioBuffer` ring** (`buffers.py:32-46`,
   16kHz `INPUT_SR_TARGET=16000`, `constants.py:38`, all writes under `self._lock`). Cross-thread
   state shared via `threading.Lock`, never an async queue (per CLAUDE.md threading model).
3. **`state_refresh_loop`** (the single writer, Invariant #1) reads the ring — `refresh.py:1600`,
   takes `audio_buf` (`:929,1602`) and computes `snapshot_features(audio_buf, 4.0)` `:1002`,
   `energy_curve` `:1017`, `estimate_bpm(audio_buf, 6.0)` `:1048`, `long_arc_curve` `:1546`. It writes
   `MusicState`; `event_detector.py` emits typed events with cooldowns; `coach.py` builds grounded
   prompts; Sven (dj_cohost) reacts.

**Bottom line:** replay injects at layer 1 (the callback). Everything from the ring buffer downstream
— state, events, evidence, citations, Sven — runs **exactly as live**, because it is the live code.
The replay backend is the only substituted component, and only its `input` capture.

`input.wav` format contract (what the recorder writes, what replay reads):
- `VoiceRecorder` writes `<session>/input.wav` = **16kHz mono int16** (`recorder.py:177,250-253`),
  co-located with `voice.wav`, `events.jsonl`, `session.json`, `evidence_registry.json`.
- Replay reader (`_read_wav_float32`, `_audio_replay.py:358-408`) accepts 8/16/32-bit, any channel
  count, any sample rate — resamples + channel-maps to the requested capture rate. So a real-world
  44.1k stereo set WAV works without preprocessing.

**Round-trip exists:** a live/dev session's recorder output dir IS a valid replay session dir
(same `input.wav` + `midi.jsonl` + `nowplaying.jsonl` layout). Record once → replay forever.

---

## REAL vs ASPIRATIONAL — line by line

| Claim | Verdict | Evidence |
|---|---|---|
| In-process file feed into the capture callback exists | **REAL** | `_audio_replay.py:166-186`, `:101-118` |
| Wired into the real `__main__` boot path (not just a script) | **REAL** | `__main__.py:1373,1392,1457-1459` |
| Feed uses the exact sounddevice callback contract | **REAL** | `_audio_replay.py:185` vs `audio.py:19-20` |
| MIDI + now-playing also replayed (grounded `[midi:]`/track events fire) | **REAL** | `_audio_replay.py:230-344` |
| State loop + event_detector + grounding run as-if-live | **REAL** | path is unmodified; `refresh.py:1600-1679` reads the same ring |
| Has produced a real grounded run with no human | **REAL** | `current-source-live-capture-blackhole-20260604-110953/ws_capture_summary.json` (grounded=true, bpm=171.4, 46 snapshots) |
| Tests cover it | **REAL** | `tests/eval/test_replay_live_runner.py`, `tests/runtime/test_replay_audio_backend.py` |
| Findings JSON scores anti-slop/grounded/on-time/mute | **REAL** | `replay_live_runner.py:202-269` |
| Fast deterministic offline scoring harness exists | **REAL** | `replay_harness.py:1-61`, `buffers.py:120-174` |
| A 3-hour recorded DJ set exists to replay | **ASPIRATIONAL** | longest real `input.wav` on disk ≈ **117s**; most <30s (measured under `~/Library/Application Support/vibemix/recordings/`) |
| Replay can compress 3h into minutes (time-warp) | **ASPIRATIONAL / ABSENT** | `_audio_replay.py:186` `time.sleep(frames/sr)` = strict realtime; `replay_live_runner.py:141` sleeps `--duration` then SIGINTs. No warp knob. |
| Replay drives Sven's real LLM + captures utterances in the realtime path | **PARTIAL** | the realtime app DOES run the real `dj_cohost`/Gemini (`gemini=ok`), but the one captured run shows LISTENING with empty `transcript_delta` (20s window too short / speak-gate). Needs a longer feed + utterance capture to prove. |
| Screenshots / UX-legibility capture in the loop | **ABSENT for this piece** | runner captures stdout/stderr/events/ws, not screenshots. (Tauri/playwright is a separate map piece.) |

---

## WHAT MUST BE BUILT / WIRED (smallest viable, in priority order)

The feeder is **built**. The work is supplying a long source and tuning throughput. Concrete items:

1. **[DATA — keystone gap] Produce a 3h replay session dir.** No 3h `input.wav` exists.
   - Smallest viable: render a Rekordbox export (or any ~3h DJ mix WAV/MP3) to a single WAV and drop it
     as `<corpus>/3h_set_01/input.wav`. Format is forgiving — `_read_wav_float32` (`_audio_replay.py:358-408`)
     resamples any rate/channels, so no manual 16k-mono conversion needed. **No code required to feed it.**
   - Optional richness: also write `midi.jsonl` / `nowplaying.jsonl` (track-change timestamps) so
     TRACK_CHANGE + `[midi:]` citations fire; without them, replay still grounds on audio (PHASE/PHRASE/
     LAYER) but won't name tracks. A tiny generator that turns a Rekordbox set's track list +
     start-times into `nowplaying.jsonl` would materially improve coverage (NEW small module:
     `scripts/eval/rekordbox_set_to_session.py`).
   - Decision for Kaan: a *real captured* set (record the rig once into the recorder, gives authentic
     audio+MIDI+nowplaying) vs a *synthesized* set (a concatenated mix WAV; audio-only grounding).

2. **[THROUGHPUT] Decide realtime vs time-warp for overnight.** A 3h realtime replay = 3h wall clock
   per pass. For 2-3 autonomous lanes overnight that may be acceptable (run once, judge once), but if
   you want many passes, you need EITHER:
   - **(a) Use the fast offline `replay_harness.py`** for bulk grounding/scoring (it's already
     non-realtime, deterministic, scored) — but it does NOT exercise the real Sven LLM/voice/ws.
   - **(b) Add a time-warp knob to the realtime feed** (smallest code change): replace the
     `time.sleep(frames/sr)` in `ReplayCaptureStream._run` (`_audio_replay.py:186`) with
     `time.sleep((frames/sr) / speed)` behind a `VIBEMIX_REPLAY_SPEED` env. **WARNING/CAVEAT:** the
     state-refresh loop's window/hop constants (`snapshot_features 4s`, `energy_curve 12s`,
     `estimate_bpm 6s`, `long_arc 120s` in `refresh.py:1002-1546`) and `event_detector` cooldowns are
     wall-clock; warping audio faster than ~1x will desync detection windows and likely BREAK
     grounding fidelity. So time-warp is NOT free — it needs its own validation pass before trusting
     judged output. **Recommend: run realtime for the authoritative judged pass; use Path B for fast
     regression.** Flag this as a Kaan/Codex decision, do not silently warp.

3. **[CAPTURE] Wire Sven utterance + telemetry capture into the realtime loop.** The runner reads
   `events.jsonl` (citation counts, llm_invokes, latency) — good. But to JUDGE Sven's *prose* (the
   anti-slop / real-friend axis), the harness must collect the actual `transcript_delta` text. Two
   options: (a) subscribe a ws client to `127.0.0.1:<VIBEMIX_WS_PORT>` and record `transcript_delta`
   frames (the `ws_capture_summary.json` schema already does exactly this — reuse that capturer), or
   (b) read transcripts from the recorder/`events.jsonl`. The realtime run today captured 0 utterances
   in a 20s window — confirm utterances flow over a longer (multi-minute) feed before declaring the
   loop ready to judge prose.

4. **[ORCHESTRATION] Glue the realtime runner → a judge.** `replay_live_runner.py` produces
   structured findings but does NOT call an LLM judge on Sven's lines. Wire its output (+ captured
   transcripts from item 3) into the existing judge (`scripts/eval/judge.py` / the Sven prompt-bench
   panel from `project_sven_prompt_bench_measured`) to score grounded/real-friend/anti-slop/on-time
   automatically. This is the "JUDGE with no human ears" half of the mission.

5. **[NICE-TO-HAVE] Confirm corpus discovery + a smoke pass.** `eval/corpus/sessions/` already has
   fixture dirs (`hard_tek_01`, `house_01`, `techno_01`, ...) and `tests/eval/fixtures/` exists.
   Verify a `replay_live_runner.py --corpus eval/corpus/sessions --duration 60` smoke run is green on
   current source before the 3h pass.

---

## IS THIS A BLOCKER FOR THE AUTONOMOUS QA LOOP TONIGHT?

**NO — the audio-replay keystone (the feed mechanism) is NOT a blocker. It is built, wired, tested,
and proven on a real run today.** The remaining work is **data + glue**, not invention:
- Need a **3h source WAV** dropped as `<dir>/input.wav` (no code).
- Need to **capture Sven's transcript** (reuse the existing ws-capture) and **pipe it to a judge**.
- Need a **realtime-vs-warp decision** for overnight throughput (warp is risky; realtime is safe-but-slow).

If you supply a 3h WAV and reuse the ws-capturer + existing judge, the loop that removes Kaan can run
TONIGHT on the realtime path. The only thing that *would* make it a blocker is if "overnight = many
fast passes" is a hard requirement — then time-warp validation (item 2b) becomes load-bearing and
must be proven not to desync grounding first.
