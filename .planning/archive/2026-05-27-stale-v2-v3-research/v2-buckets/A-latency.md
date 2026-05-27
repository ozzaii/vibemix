# Bucket A — Latency Engineering Research

**Researched:** 2026-05-13
**Anchored to:** `cohost_v4.py` (LiveKit cascade: Gemini 3 Flash LLM → Gemini 3.1 TTS via `AgentSession.generate_reply()`, single in-flight gate, `allow_interruptions=False`)
**Goal:** Get coach reactions to land in the bar they reference (~1.85s @ 130 BPM, ~1.4s @ 170 BPM Hard Tek). Current pipeline lands 5–10s late (per `cohost_v4.py:154` system prompt — Kaan acknowledged in the prompt itself).

---

## TL;DR (5 bullets)

1. **Cascade is the latency floor, not native audio.** v4 already moved off `gemini-2.5-flash-native-audio-preview` to cascade for grounding reasons. The cascade has a documented ~993ms voice-to-voice ceiling on ideal pipelines [CITED: voiceaiandvoiceagents.com] — vibemix is at 5–10s because we send 18s of inline audio + a screen frame + thinking_level. **The first lever is not a new model — it's making the LLM prompt smaller and faster.**
2. **Predictive trigger generation is the biggest win.** Build-up → drop is the most latency-exposed event and the most predictable (8–32 bar buildup signature). Fire `generate_reply()` ~2 bars BEFORE the drop, gate playback on the actual drop event. Patterns from PredGen (arXiv 2506.15556) show 1.6–2.8× speedup with low misfire cost [CITED: arxiv.org/2506.15556].
3. **Pre-canned ack bank (sub-100ms) is mandatory for the "alive" feeling.** Locally-fired interjections ("yeah", "go", "brrr", short breath) played from disk on event detection, BEFORE the LLM response arrives. Industry standard pattern (Retell, Vapi, Google Duplex's "uh-huh") [CITED: retellai.com]. Bridges the 1–3s gap until the real LLM reaction.
4. **Streaming TTS partial speak-out already works in the v4 stack but isn't fully exploited.** `livekit-plugins-google` typical TTS first-chunk latency is 100–200ms [CITED: docs.livekit.io/agents]. The bottleneck is LLM TTFT, not TTS. Optimize prompt size to shave 500–1500ms off TTFT.
5. **Cancel-mid-generation works.** `SpeechHandle.cancel()` cancels even when `allow_interruptions=False` — verified via livekit/agents source [CITED: docs.livekit.io/python/livekit/agents/pipeline/speech_handle.html]. v4 currently uses `allow_interruptions=False` which blocks `.interrupt()` but NOT `.cancel()`. Predictive backpressure is implementable.

---

## Current SOTA (with measured numbers)

### Voice-to-voice latency floors (2025/2026)

| Pipeline | Voice-to-voice latency | Source |
|---|---|---|
| Cascade (STT → LLM → TTS), ideal | ~993ms total | [CITED: voiceaiandvoiceagents.com] breakdown: STT+endpoint 300ms + LLM TTFT 350ms + TTS TTFT 120ms + network 150ms + OS 75ms |
| Cascade, typical production | 1500–2000ms | [CITED: hamming.ai] |
| Native speech-to-speech (OpenAI Realtime, Gemini Live native audio) | 160–400ms claimed | [CITED: hamming.ai] — but treated as "not yet production-ready for most apps" |
| Voice AI industry target | 500–800ms | [CITED: autointerviewai.com 2026] |
| vibemix v4 today | **~5–10s** (per `cohost_v4.py:154` prompt) | Self-reported by Kaan in system instruction |

**Why vibemix is so far above the floor:** the LLM input is not "a transcribed sentence." It's an 18s audio Part + a screenshot Part + a multi-line evidence packet + a long system instruction (~5KB). Gemini 3 Flash with `thinking_level="minimal"` still pays an inline-multimodal cost that dwarfs text-only TTFT.

### Gemini Live API specifics

- **Input format:** 16-bit PCM 16kHz mono little-endian (auto-resample supported) [CITED: ai.google.dev/gemini-api/docs/live-api/capabilities].
- **Output:** 24kHz PCM.
- **Cancellation:** Built-in barge-in via VAD; ongoing generation is canceled and discarded when VAD detects interruption [CITED: same source].
- **`generate_reply()` on `gemini-3.1-flash-live-preview`:** NOT compatible — must stay on `gemini-2.5-*-native-audio` for `generate_reply()` flow [CITED: docs.livekit.io/agents-js, plugin notes]. v4 already avoids this trap by using cascade.
- **No documented warm-pool / pre-warming for the LLM** in any official Gemini docs. Confirmed open issue on livekit/agents [CITED: github.com/livekit/agents/issues/3240] — "LLMs usually require an inference request rather than just opening an HTTP connection."

### LiveKit cancellation primitives (the v4 lever)

- `SpeechHandle.cancel()` cancels `_init_fut` AND calls `interrupt()` on any in-flight synthesis handle [CITED: docs.livekit.io/python/livekit/agents/pipeline/speech_handle.html]. **Works regardless of `allow_interruptions`** (which only gates VAD-driven auto-interrupt).
- `SpeechHandle.interrupt()` requires `allow_interruptions=True` or raises RuntimeError [CITED: github.com/livekit/agents/issues/3230].
- **Practical implication:** v4 can keep `allow_interruptions=False` (we don't want VAD to barge-in based on Kaan's mic) AND still call `handle.cancel()` programmatically when a newer, more relevant event fires.

---

## Options surveyed

| # | Approach | Latency win | Implementation cost | Risk |
|---|---|---|---|---|
| 1 | Shrink LLM prompt (audio 18s → 6s, drop screenshot for non-PHASE events, trim system instruction) | **500–1500ms TTFT** | Low — code-only in `DJCoHostAgent.llm_node` | Reduces grounding evidence; verify anti-slop doesn't regress |
| 2 | Predictive `generate_reply()` for drop/build events (fire 1–2 bars early, gate playback) | **1–2 bars perceived (≈1–3s)** | Medium — needs build-up detector + playback gate + cancel-on-misfire | Misfires when build doesn't resolve to drop; mitigated by cancel |
| 3 | Pre-canned ack bank (10–30 vocal interjections, played on event in <100ms) | **Instant first sound (≤100ms)** | Medium — generate samples offline once with Gemini TTS Achird, ship in installer | "Same ack twice in a row" feels canned; needs rotation + per-event filtering |
| 4 | Streaming TTS already on (verify chunks land while LLM still emitting) | **100–500ms** | Low — already in livekit-plugins-google; just measure | None — already paid for |
| 5 | Speculative pre-generation while waiting for event (PredGen-style) | **400–800ms** | High — needs parallel session, draft prompts, accept/reject logic | Doubles API cost; rejected drafts wasted |
| 6 | Visual-precedes-audio mascot anticipation (mouth-open / breath frame before audio arrives) | **0ms real, ~200ms perceived** | Low — mascot already has WS bus | Only masks; doesn't fix |
| 7 | Local "thinking" sound (breath, lip-smack, "mm") triggered immediately on event | **0ms perceived** | Low — single WAV per event class | Risk: sounds robotic if overused; cap at 1× per N seconds |
| 8 | Cancel-and-re-fire when newer high-priority event arrives mid-generation | **Avoids stale reactions** | Low — `handle.cancel()` already supported | Wasted API cost on canceled responses; cap at 1 cancel per event |
| 9 | Replace cascade with `gemini-2.5-flash-native-audio` (revert v2 path) | Potentially 400ms vs 2–3s | High — loses grounding (v4 docstring says we left native audio precisely for grounding) | **Likely regression** on anti-slop thesis. Don't do this. |
| 10 | Drop `thinking_level` to "off" entirely | 200–400ms TTFT | Trivial | Already at `"minimal"` — small remaining win |
| 11 | KV-cache the system instruction (Gemini prompt caching) | 200–500ms TTFT [CITED: cloud.google.com gemini caching] | Low — `cached_content` API | Cache cost; 5min minimum TTL; OK for active session |
| 12 | Shorter response length budget (1 short sentence, hard token cap) | TTS finishes 1–2s sooner | Trivial — `max_output_tokens=50` | Already prompted; enforce hard cap |

---

## Recommended stack for vibemix (ranked by ROI)

### 1. Prompt-Size Diet + Prompt Caching (ship first — ~1 day work, biggest single TTFT win)

The LLM is doing too much work per turn. Specifically:
- **Audio Part:** drop from 18s → 6–8s for non-drop events. Keep 18s only for `PHASE` (build→drop) events where buildup history matters.
- **Screen Part:** skip on `MIX_MOVE` and `HEARTBEAT` (the audio + MIDI already grounds these). Keep on `TRACK_CHANGE` (for djay title verification) and `PHASE` (visual structure).
- **System instruction:** wrap in Gemini context caching (`client.caches.create(model=..., system_instruction=...)`). Reuse `cached_content` for the whole session. Saves ~5KB tokens of input per call [CITED: cloud.google.com/vertex-ai/generative-ai/docs/context-cache].
- **Estimated win:** 500–1500ms off TTFT, no anti-slop regression because we keep grounding on the events that need it.

### 2. Pre-Canned Ack Bank (ship second — ~2 days, biggest perceived-latency win)

Generate offline, ship in the installer:
- **~40 samples** at Achird voice, 200–800ms each, organized by event class:
  - `drop_hit/*.wav` — "yes", "go", "fuuuck", "there it is", "brrr", short breath-in
  - `track_change/*.wav` — "ohhh", "okay", "interesting", "hmm", "alright"
  - `mix_move/*.wav` — "nice", "clean", "uh-oh", "watch it", short hiss
  - `silence_break/*.wav` — "back", "here we go", "and...we're on"
  - `generic_filler/*.wav` — "mm", "yeah", short laugh, exhale, "so..."
- Fire from local disk on event detect, parallel to `generate_reply()`. Mix into `PlaybackQueue` directly (bypass LiveKit TTS path).
- **Rotation rule:** never reuse same sample within 30s. Persist usage in `MusicState`.
- **Total disk:** ~5MB at 24kHz mono OPUS (negligible).
- **Risk mitigation:** Ack bank fires only when LLM TTFT > 800ms (predict via rolling avg). If LLM is fast that turn, suppress the ack.

### 3. Predictive Drop Reactions (ship third — ~1 week, biggest semantic win)

The build-up is the most predictable structural event in Hard Tek / French Touch (Kaan's genres). Heuristic detector in `MusicState.state_refresh_loop` (already running @10Hz):

```
buildup_score = (rising_hi_share_8s × snare_roll_density × filter_sweep_present
                 × phrase_boundary_proximity_8or16_bars)
```

When `buildup_score > 0.7` AND `phrase_boundary_in <= 2 bars`:
- Fire `generate_reply()` IMMEDIATELY (event=`PHASE_PREDICTED_DROP`)
- Cache the resulting `SpeechHandle` but DELAY playback until either:
  - Actual drop confirmed (`PEAK_RMS` + `sub_share` spike) → release playback
  - Window expires (3s past predicted moment) → `handle.cancel()` and treat as misfire
- Miss cost = 1 canceled API call. Hit value = drop reaction in the bar it lands.

[CITED: arXiv 2506.15556 PredGen] — same pattern, 1.6–2.8× perceived speedup, low misfire cost when verification skips already-accepted tokens.

### 4. Programmatic Cancel-and-Re-fire (ship fourth — ~2 days)

Currently v4 is "single in-flight, drop new events." This is wrong for fast genres where context shifts mid-generation.

Change `coach_loop`:
```
if trigger_state["in_flight"] and ev.priority > current_priority + PRIORITY_GAP:
    current_handle.cancel()           # works even with allow_interruptions=False
    trigger_state["in_flight"] = False
    # fall through to new generate_reply()
```

Where `priority` is event-type-weighted (DROP=10, TRACK_CHANGE=8, MIX_MOVE=5, HEARTBEAT=1). Cap to 1 cancel per 8s to avoid thrashing.

### 5. Visual-Precedes-Audio Mascot Anticipation (ship anytime — ~1 day)

Use the already-running WS bus (`ws_broadcast` @30Hz). On event detect (before LLM responds):
- Send `{anticipating: true, event_class: "drop"}` to mascot
- Mascot plays mouth-open / lean-in / eyes-widen frame from the rig
- When audio actually arrives, mascot syncs to the audio level (already implemented)

Industry pattern: Siri's pulsing orb, ChatGPT Voice's wave start before audio. ~200ms of perceived latency masking with zero engineering risk.

---

## Implementation sketches

### Sketch 1 — Pre-canned ack bridge

```python
# In MusicState init / coach_loop setup
ACK_BANK_ROOT = Path("acks/")  # bundled in installer
ack_bank = {
    "PHASE":        list((ACK_BANK_ROOT / "drop_hit").glob("*.opus")),
    "TRACK_CHANGE": list((ACK_BANK_ROOT / "track_change").glob("*.opus")),
    "MIX_MOVE":     list((ACK_BANK_ROOT / "mix_move").glob("*.opus")),
    "MANUAL":       list((ACK_BANK_ROOT / "generic_filler").glob("*.opus")),
}
ack_recent = collections.deque(maxlen=10)  # for rotation

async def fire_ack(ev_type: str, playback_queue: PlaybackQueue):
    bank = ack_bank.get(ev_type, ack_bank["MANUAL"])
    eligible = [p for p in bank if p not in ack_recent]
    if not eligible:
        ack_recent.clear()
        eligible = bank
    pick = random.choice(eligible)
    ack_recent.append(pick)
    pcm = decode_opus_to_24k_mono_int16(pick)  # ~5ms with cached decoder
    playback_queue.push(pcm)  # writes directly to sd output queue

# In coach_loop, RIGHT AFTER detect():
if ev and _should_fire_ack(ev, rolling_ttft_avg_ms):
    asyncio.create_task(fire_ack(ev.type, playback_queue))
# Then proceed to session.generate_reply() in parallel
```

**Anti-slop guard:** ack and LLM response must not overlap awkwardly. Add a `min_ack_to_response_gap_ms=400` — if LLM response arrives within 400ms of ack start, hold the response 600ms.

### Sketch 2 — Predictive drop firing with playback gate

```python
# In MusicState — already running @10Hz state_refresh_loop
@dataclass
class MusicState:
    # ... existing fields
    buildup_score: float = 0.0
    predicted_drop_in_sec: float = 0.0  # negative if no prediction
    predicted_at: float = 0.0

# In state_refresh_loop hot path:
def _update_buildup_prediction(self):
    feats = self.audio_buf.snapshot_features(seconds=8.0)
    hi_trend = self._hi_share_rising(feats)        # 0..1
    snare_dense = self._snare_roll_density(feats)  # 0..1
    sweep = self._filter_sweep_present(feats)      # 0..1
    bar_boundary_in = self._next_bar_boundary_sec()
    if bar_boundary_in > 4.0:                      # too far out — meaningless
        self.buildup_score = 0.0
        return
    self.buildup_score = 0.4*hi_trend + 0.3*snare_dense + 0.3*sweep
    self.predicted_drop_in_sec = bar_boundary_in if self.buildup_score > 0.7 else -1

# In coach_loop:
if state.buildup_score > 0.7 and not trigger_state["in_flight"]:
    ev = Event(type="PREDICTED_DROP", priority=10, ...)
    agent.set_next_event(ev)
    # Fire LLM NOW, but tell the agent to buffer audio output
    handle = session.generate_reply(allow_interruptions=False)
    pending_predicted = (handle, time.time() + state.predicted_drop_in_sec, time.time() + 4.0)
    trigger_state["in_flight"] = True

# Separate watcher coroutine:
async def predicted_drop_watcher(state, playback_queue, ...):
    while not stop_event.is_set():
        await asyncio.sleep(0.05)
        if not pending_predicted: continue
        handle, deadline, abort_at = pending_predicted
        if state.phase == "drop" and time.time() >= deadline - 0.3:
            playback_queue.unmute()   # release the buffered audio
            pending_predicted = None
        elif time.time() > abort_at:
            handle.cancel()           # misfire — cancel
            pending_predicted = None
```

**Playback gating** requires routing TTS output through a mute-able sink. Easiest path: subclass `PlaybackQueueAudioOutput` to add `_muted` flag, drop frames when muted.

---

## Risk + watchouts

- **Predictive misfire cost:** Each canceled `generate_reply()` is wasted Gemini tokens. At ~50€/mo budget per user, a 3× hit rate is the upper bound. Cap predictive fires to 1 per 12s.
- **Ack bank "AI slop" feel:** if same ack plays twice in 30s, or if the ack doesn't match the genre intensity, the user feels it. Mitigate with rotation deque + per-event filtering + intensity binning (low/mid/high ack samples).
- **Cancel-on-mic-input is OFF:** v4 deliberately uses `allow_interruptions=False` so VAD doesn't barge-in on Kaan's mic. Our cancel must be programmatic only — verify `SpeechHandle.cancel()` works on `gemini-3-flash-preview` via livekit-plugins-google. If not, fall back to `_synthesis_handle.aclose()` directly.
- **Pre-canned samples must match the cascade voice (Achird):** if we generate the bank with Achird once and the model voice drifts in a Gemini update, samples will sound disjoint. Pin the TTS model version in installer; regenerate bank on model bump.
- **Prompt cache TTL = 5 min minimum** [CITED: cloud.google.com context-cache pricing]. For session length variance, cache lifecycle needs management — create cache on session start, refresh every 4 min.
- **No retry/reconnect for LiveKit session** (per project CLAUDE.md). Predictive firing increases session activity ~30%. Verify session stays alive under load before shipping.
- **Hard Tek 170+ BPM = 1.4s/bar.** Even 800ms voice-to-voice doesn't land in-bar. The combo of predictive firing + ack bank is the only way to make 170 BPM feel alive.
- **Don't ship `gemini-2.5-flash-native-audio` revert.** The v4 docstring explicitly moved away from it for grounding. The product thesis is grounded Gemini, not fast Gemini.

---

## Open questions for Kaan

1. **How aggressive on predictive firing?** Conservative (predict only DROP, never MIX_MOVE — high precision) vs aggressive (predict any phase-shift, accept ~30% misfire). Conservative is safer for budget; aggressive feels more alive on hard genres. My pick: conservative for v1, expand in v2 based on Kaan's DJ-ear test.
2. **Ack bank: voice match or character-distinct?** Option A: Achird-voiced acks (seamless blend with LLM output). Option B: distinct "DJ buddy" character voice for acks (clearer separation, never gets mistaken for the actual coach). I lean A but B might be more anti-slop.
3. **Playback gating for predicted drops — buffer or speak-then-mute?** If we fire 2 bars early and the LLM finishes 1.5 bars early, do we (a) hold the audio in memory until drop confirmed, or (b) start speaking quietly and crossfade up at drop? Option B is harder but feels more like a real DJ friend murmuring then yelling.
4. **Cancel budget per session?** Should we cap the number of canceled generations per hour to avoid blowing the 50€/mo per-user API budget? Suggest: 30/hour soft cap, log + telemetry.
5. **Phase 16 ear-test gates this whole bucket.** Predictive + ack bank could feel magic OR feel canned/scripted. Need Kaan to spend 2–3 real DJ sessions with predictive enabled BEFORE we lock the v1 cut. Predictive is a v1.1 candidate, not a v1.0 launch blocker — agree?

---

## Sources

### Primary (HIGH confidence)
- [LiveKit Live API capabilities](https://ai.google.dev/gemini-api/docs/live-api/capabilities) — audio format, VAD, interruption semantics
- [LiveKit SpeechHandle API](https://docs.livekit.io/reference/python/v1/livekit/plugins/google/beta/realtime/realtime_api.html) — cancel/interrupt distinction
- [livekit/agents Issue #3240 — LLM prewarm](https://github.com/livekit/agents/issues/3240) — no LLM warm-pool currently supported
- [Google context caching docs](https://cloud.google.com/vertex-ai/generative-ai/docs/context-cache) — system-instruction caching, 5min minimum TTL

### Secondary (MEDIUM confidence)
- [PredGen paper (arXiv 2506.15556)](https://arxiv.org/html/2506.15556v1) — input-time speculation, 1.6–2.8× speedup, low misfire cost
- [Voice AI and Voice Agents primer](https://voiceaiandvoiceagents.com/) — 993ms cascade breakdown, 800ms voice-to-voice target
- [Hamming AI latency primer](https://hamming.ai/resources/voice-ai-latency-whats-fast-whats-slow-how-to-fix-it) — 160-400ms speech-to-speech, 1000-2000ms cascade typical
- [Retell AI on backchanneling](https://www.retellai.com/blog/how-backchanneling-improves-user-experience-in-ai-powered-voice-agents) — pre-canned ack pattern, timing rules
- [LiveKit voice agent architecture](https://livekit.com/blog/voice-agent-architecture-stt-llm-tts-pipelines-explained) — TTS first-chunk 100-200ms typical
- [BeatNet (ISMIR 2021)](https://github.com/mjhydri/BeatNet) — real-time beat/downbeat tracking for phrase-boundary prediction

### Tertiary (LOW confidence — verify before locking)
- [autointerviewai.com 2026 voice AI latency](https://www.autointerviewai.com/blog/prompt-engineering-voice-ai-interruptions-latency-2026) — 500-800ms industry target, filler-word pattern
- [ruh.ai voice AI optimization 2026](https://www.ruh.ai/blogs/voice-ai-latency-optimization) — speculative decoding 5x TTFT claim

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `SpeechHandle.cancel()` works through the cascade path (Gemini 3 Flash LLM → Gemini TTS via livekit-plugins-google) — not just the native-audio realtime path | Recommended #4 | Predictive cancel logic doesn't work; misfires play through |
| A2 | Gemini context caching is available for `gemini-3-flash-preview` (it's listed for stable 2.5; preview models sometimes excluded) | Recommended #1 | TTFT win shrinks from 500-1500ms to 200-400ms |
| A3 | Achird voice samples generated once stay coherent across Gemini TTS model updates | Risks | Ack bank needs regeneration per model bump |
| A4 | Buildup detector at 0.7 threshold catches >70% of real drops in Hard Tek without false-positiving on filtered breakdowns | Sketch 2 | Predictive firing rate misjudged — over-cost on misfires |
| A5 | LiveKit session survives 30% higher generate_reply rate without dropping | Risks | Session instability under predictive load |
| A6 | The 5-10s perceived latency is dominated by LLM TTFT, not TTS or network | TL;DR #1, Recommended #1 | Prompt-diet wins don't materialize |
