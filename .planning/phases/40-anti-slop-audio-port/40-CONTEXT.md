# Phase 40: Anti-Slop Audio Port - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous — gsd-autonomous fully)

<domain>
## Phase Boundary

Close the biggest engineering anti-slop gap by porting two tested-in-real-DJ-sessions audio paths from POC reference files (`cohost_v4.py` + `cohost_v4_tr.py`) into the shipped `src/vibemix/` codebase:

1. **Mic as 2nd Gemini multimodal Part** — `KAAN_SPOKE` event currently signals presence only; Gemini receives no actual mic audio. v4 attaches a `mic_audio_buf` (12s ring) as a literal second `Part` in the multimodal contents.
2. **3s file-based lookahead as 3rd Gemini Part** — `cohost_v4_tr.py`'s `LookaheadProvider` extracts 3s of audio from the source file on disk (via `nowplaying-cli` + `mdfind` + `ffmpeg`) and attaches it as a third Part labeled `NOT YET HEARD BY AUDIENCE`. Gracefully degrades on streaming-only tracks (no local file).
3. **Event cooldown re-tune** — `MIN_EVENT_GAP_PER_TYPE` matched to v4 chat-tested intuition (real session 2026-05-11 baseline).
4. **Pre-stage KAAN-ACTION pre-stage items** — items without external clock that we can discharge engineering-side now: PGP key publish (SEC-06-PGP), Tauri ed25519 updater key rotate (TAURI-UPDATER-KEY), BlackHole fresh-Mac probe instrumentation (INSTALL-BLACKHOLE-PROBE).

Out of scope for Phase 40: rewriting `LiveCoachClient` architecture; redesigning event taxonomy; changing the cascade (LLM → TTS) shape. Constants and ring-buffer shapes are direct ports from v4 with the documented anti-pattern fix (pre-allocated ring vs `np.concatenate`).

</domain>

<decisions>
## Implementation Decisions

### Audio Plumbing (Mic + Lookahead Parts)
- **Mic ring buffer** = standalone `MicAudioRing(window_seconds=12.0, sample_rate=16000)` in `src/vibemix/audio/mic_ring.py`; pre-allocated `np.zeros(window_seconds*sample_rate, dtype=np.int16)` with circular write head (not `np.concatenate`).
- **Mic ring source** = same `sounddevice` mic input stream that already feeds `Levels.update_mic()`; tap added in `audio/streams.py::mic_callback`. Single buffer instance owned by `LiveCoachClient`.
- **Attach point** = `LiveCoachClient.build_contents()` (mirrors `cohost_v4.py:1791-1813`). When KAAN_SPOKE fires, append second `Part` with `inline_data={mime_type: "audio/pcm", data: <16kHz mono int16 wav-bytes>}`.
- **Lookahead provider** = port `cohost_v4_tr.py:624-779` verbatim into `src/vibemix/audio/lookahead.py`. Three-step pipeline: `nowplaying-cli get duration elapsedTime title artist` → `mdfind kMDItemFSName == "<title>*"` (track file path) → `ffmpeg -ss <elapsed+3> -t 3 -ac 1 -ar 16000 -f s16le -` → 3s int16 PCM bytes.
- **Graceful degrade** = no local file (streaming Spotify/SoundCloud, no `mdfind` match) → log INFO once per track + skip 3rd Part. Zero ffmpeg-error stderr noise (`subprocess.run(stderr=subprocess.DEVNULL)` on the happy path).
- **3-Part vs 2-Part contract** = always Part 1 = BlackHole 7s (existing). Mic appended only when KAAN_SPOKE-recent (within 4s) AND mic ring has signal (≥ MIC_PRESENCE_RMS). Lookahead appended only when file path resolved.
- **Prompt template** = updated in `prompts/coach.py` to explicitly enumerate Parts ("You receive three audio Parts: P1 = live BlackHole mix you and audience hear, P2 = my voice if I spoke, P3 = source file 3s ahead — audience has NOT heard P3 yet"). Coach-mode and Hype-mode share the labeling; persona overlay stays separate.

### Event Cooldowns
- **Values** = match v4 chat-tested baseline literally:
  - PHASE: 18 → 10s
  - LAYER_ARRIVAL: 16 → 10s
  - MIX_MOVE: 20 → 14s
  - HEARTBEAT: 70 → 45s
  - TRACK_CHANGE: 6 → 5s
- **Implementation** = single constants dict `EVENT_COOLDOWNS_SECONDS` in `src/vibemix/events/cooldowns.py`. `EventDetector._cooldown_ok()` reads from this dict (no scattered constants).
- **Replay harness validation** = `scripts/eval/replay_harness.py` already replays sessions through `EventDetector`. Add `--print-cooldowns` mode that emits measured inter-event gaps per type; CI gate requires measured within ±1s of locked values.

### Pre-stage KAAN-ACTION Items (no external clock)
- **PGP key (AUDIO-05 / SEC-06-PGP)** = Kaan generates ed25519 GPG key for `security@bravoh.com` locally; publishes to `keys.openpgp.org` via web; commits public key armor block to `docs/security/pgp-public-key.txt` and updates `SECURITY.md` reference. Documented in `KAAN-ACTION-LEGAL.md` as discharged.
- **Tauri ed25519 updater key (AUDIO-06 / TAURI-UPDATER-KEY)** = generate fresh ed25519 pair via `tauri signer generate`; pubkey committed in `tauri.conf.json5` under `plugins.updater.pubkey`; private key armor stored in GH secret `TAURI_PRIVATE_KEY` (Kaan adds via `gh secret set`); update release.yml to sign installer with new key.
- **BlackHole probe instrumentation (AUDIO-07 / INSTALL-BLACKHOLE-PROBE)** = the engineering surface for the fresh-Mac walk. Instrument `tauri/src-tauri/src/audio_probe.rs::probe_blackhole()` to emit structured `audio.probe.{detected,missing,cta_fired}` events to local log + telemetry sink. Kaan's actual fresh-Mac account walk-through stays a KAAN-ACTION discharge step; ensure the probe surfaces the right CTA when BlackHole is absent.

### Anti-Hallucination Hardening
- **"Trust the audio" rule preserved** = v4 prompt-side instruction `If you are uncertain about the music, do NOT say anything specific — instead describe what you hear` is carried over verbatim to the new 3-Part prompt template (memory: project_v4_canonical_baseline).
- **No new grounding signals introduced** — Phase 40 ports existing anti-slop primitives; no CLAP, no librosa-derived features, no extra detectors beyond cooldown-tuned existing ones.

### Testing Strategy
- **Unit tests** = `tests/audio/test_mic_ring.py`, `tests/audio/test_lookahead.py` (mock subprocess + filesystem), `tests/events/test_cooldowns.py`, `tests/prompts/test_coach_3part.py`.
- **Integration test** = `tests/integration/test_3part_request.py` — mocks Gemini SDK at `genai.GenerativeModel.generate_content`, asserts request payload has 3 Parts when KAAN_SPOKE + local file present, 2 Parts when KAAN_SPOKE without file, 1 Part baseline.
- **Replay harness regression** = `scripts/eval/replay_harness.py` re-run against one real Kaan DJ session (existing corpus 30-min WAV). Score must not regress vs Phase 27 baseline. New cooldown metrics printed.

### Claude's Discretion
- Module file names and exact internal API shape (subject to existing `src/vibemix/audio/` conventions).
- Whether `LookaheadProvider` is a singleton or per-session — pick whichever matches existing `LiveCoachClient` lifecycle.
- ffmpeg invocation flags as long as output is mono 16kHz int16 PCM matching the existing mic ring format.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/audio/streams.py` — `sounddevice` mic + BlackHole stream wiring; mic callback already exists, just needs the new ring tap.
- `src/vibemix/audio/ring_buffer.py` — proven pre-allocated ring pattern from v2.0; pattern reused for `MicAudioRing`.
- `src/vibemix/events/detector.py` — `EventDetector` with `_cooldown_ok()` already takes per-type gaps as parameters; only the constants need to move.
- `src/vibemix/llm/client.py` (or `live_coach.py`) — existing `build_contents()` shape supports multimodal Parts; mic + lookahead become additional items in the list.
- `scripts/eval/replay_harness.py` — already drives `EventDetector` headlessly; add cooldown report mode.

### Established Patterns
- Multimodal Gemini requests built as `list[Part]` and serialized via `genai.types.Content`.
- All audio buffers are 16kHz mono int16; resampling done at `sounddevice` callback boundary.
- Thread-safe ring buffers use a single `threading.Lock` per buffer (no async-safe queues between audio thread and event loop).
- Subprocess invocations use absolute Homebrew paths (e.g. `/opt/homebrew/bin/nowplaying-cli`).

### Integration Points
- `LiveCoachClient` is the single point that builds Gemini requests; mic + lookahead Parts attach here.
- `EventDetector._fire()` already routes to `LiveCoachClient.run_one_turn()`; no signature change.
- `tauri/src-tauri/src/audio_probe.rs` is the Rust side of the install wizard's audio probe; emits IPC events to the TS UI layer.
- `SECURITY.md` already references PGP key — replace placeholder with real fingerprint.

</code_context>

<specifics>
## Specific Ideas

- The "harikaydı" baseline ear-test session is real — v4 was chat-tested live 2026-05-11. The cooldown numbers are not theoretical; they're what felt right. Match them literally and only deviate with audit trail.
- POC `cohost_v4_tr.py` `LookaheadProvider` works end-to-end on local files. Port the implementation verbatim, only adapt to project conventions (typing, logging, error handling).
- Use `ffmpeg`'s `-ss` (input seek) for speed; not `-ss` after `-i`. The 3s grab takes <300ms on a local file.

</specifics>

<deferred>
## Deferred Ideas

- **Streaming-track lookahead via service-side hooks** — Spotify Connect / SoundCloud-Player Web APIs could give a 3s window for streamed tracks. Out of scope: requires per-service OAuth + product partnership.
- **Mic noise gate before sending to Gemini** — if Kaan is in a quiet room the mic ring is mostly silence; trivial RMS gate could prune. Defer — Gemini's tolerance is high; revisit if mic-only Part empirically degrades reactions.
- **Lookahead variable window (>3s) for slow-mix detection** — could help with very long blends. Out of scope: 3s matches v4 baseline.

</deferred>
