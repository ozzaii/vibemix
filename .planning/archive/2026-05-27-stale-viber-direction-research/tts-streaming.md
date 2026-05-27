# vibemix TTS-Streaming Path — Research (2026-05-25)

Repo: /Users/ozai/projects/dj-set-ai @ branch `live-tuning-or-brain`. READ-ONLY.
Architecture (owner clarification): **Gemini Flash cascade (brain) + streaming TTS for voice — NOT the Gemini Live API.**

---

## 1. THE REPO'S TTS PATH (mapped)

### Brain (LLM), not TTS, but it's the head of the chain
- `DJCoHostAgent.llm_node` (`src/vibemix/agent/dj_cohost.py`) hijacks LiveKit's text-only cascade and calls `google.genai` directly with the last ~6–18s of master audio attached as a multimodal Part (the LLM literally hears the music). Brain model resolves to **`gemini-3.5-flash`** (`live_coach` route, `_router_config.py:27`).
- Optional OpenRouter brain path (`or_client`, `google/gemini-3.5-flash`) escapes free-tier Gemini 503s. Default is direct genai.

### TTS engine: primary + fallback chain (DIRECT mode)
Built by `build_tts_chain(...)` → `_build_direct_chain(...)` in `src/vibemix/agent/tts_chain.py`. It returns a LiveKit `agents_tts.FallbackAdapter(max_retry_per_tts=1)` with a 3-entry chain:

1. **PRIMARY — OpenRouter, routing Gemini TTS.** `openai_plugin.TTS(model="google/gemini-3.1-flash-tts-preview", base_url="https://openrouter.ai/api/v1", response_format="pcm", voice="Achird")`. Only included if `OPENROUTER_API_KEY` is set; otherwise the chain starts at #2. This is the "OpenRouter-primary TTS fallback chain" from CLAUDE.md — it's the **LiveKit OpenAI plugin pointed at OpenRouter**, but the model being synthesized is still **Gemini TTS** (`google/gemini-3.1-flash-tts-preview`). So even the "primary" is Gemini TTS — OpenRouter is just the transport/billing surface, consistent with Gemini-only-in-product.
2. **SECONDARY — Gemini native TTS.** `livekit.plugins.google.beta.gemini_tts.TTS(model="gemini-3.1-flash-tts-preview", voice_name="Achird")` via the direct Gemini API key (`live_coach_tts` route).
3. **TERTIARY — Gemini native TTS fallback.** `model="gemini-2.5-flash-preview-tts"` (`live_coach_tts_fallback` route).

So the cascade is: **OpenRouter→Gemini-3.1-flash-tts** ⇒ **native Gemini-3.1-flash-tts** ⇒ **native Gemini-2.5-flash-preview-tts**. All three synth engines are Gemini TTS; the only non-Gemini element is the OpenRouter/OpenAI-plugin *transport* (the explicit allowed fallback seam).

### TTS engine: PROXY mode
`build_proxy_tts_chain(...)` (`agent/proxy_client.py:61`) — single-entry `FallbackAdapter` of `openai_plugin.TTS(model="google/gemini-3.1-flash-tts-preview", base_url="{proxy}/v1", api_key=<JWT>, response_format="pcm")`. No client-side Gemini-native fallback in proxy mode — the Bravoh proxy handles upstream fallback (circuit breaker) server-side. This is the shipping mode (Phase 18 installer flips default to proxy; the API key never ships in the binary — the "API-key-protection problem of the year" fix).

### The load-bearing monkey-patch
`tts_chain.py:42` adds `OPENROUTER_TTS_MODEL` to `_openai_tts_mod.AUDIO_STREAM_MODELS` at module-load. OpenRouter (and the Bravoh proxy) emit **raw PCM**, not SSE; without this patch the LiveKit OpenAI plugin picks its SSE decode path and fails. Must run BEFORE any `openai_plugin.TTS` init (v4 import-order invariant).

### Audio → headphones path
- LiveKit `AgentSession` runs **headless (no Room)**. `session.output.audio = PlaybackQueueAudioOutput(playback, recorder, sample_rate=OUTPUT_SR)` (`__main__.py:1099-1100`).
- `PlaybackQueueAudioOutput` (`agent/playback_sink.py`) subclasses LiveKit's `voice_io.AudioOutput`. `capture_frame()` receives int16 PCM TTS frames, applies `VIBEMIX_VOICE_GAIN` (default 2.0×, hard-clipped) so the voice isn't buried under the music passthrough, then `self._playback.push(pcm)` into the Phase-2 `PlaybackQueue` ring buffer (feeds the sounddevice CoreAudio/WASAPI output stream) and `recorder.push_voice(pcm)` for the `voice.wav` audit trail.
- TTS native output is **24 kHz / 16-bit mono PCM** (Gemini TTS spec); the playback sink reads `frame.sample_rate` and falls back to `OUTPUT_SR`.

### Is TTS streamed incrementally? YES — and the top-of-file docstring is STALE.
The `dj_cohost.py` module docstring (lines 26–29, Phase 10) says chunks are "buffered until the stream completes, then yielded in one batch." **That is no longer true.** The live code (Plan 41-04 / LAT-04, `llm_node` lines ~1397–1556) does **speculative sentence-boundary streaming**:
- As the brain streams, `find_sentence_end()` (`_streaming_pipe.py`, bracket-depth-aware so citation `.`s don't mis-fire, `MIN_HEAD_LEN=20`) detects the first sentence boundary.
- The head sentence is yielded **speculatively** to TTS the instant it clears `passes_head_gate()` (silence-token + slop-prefix prefix check). Subsequent chunks then stream straight through.
- If the post-stream full gate (slop / citation-lint failure) later rejects the turn AFTER the head already went to TTS, a 500ms silence pad (`SILENCE_PAD_BYTES = 24000`) is appended to `PlaybackQueue` — the head plays, then a brief audible cut (known degrade; can't preempt frames already in the OPUS encoder).
- So the reaction is **token-streamed brain → first-sentence-to-TTS → incremental PCM to headphones**. Latency is measured by `LLMToTTSDeltaMeter` (event_fired → first_sentence_yielded, always-on) and `TTFTMeter` (event_fired → first brain chunk, telemetry).

---

## 2. CONTINUITY / DURATION LIMITS — DEFINITIVE

**The TTS path has NO long-stream/session cap analogous to the Live API's ~15-min cap.** Reasoning + evidence:

- vibemix TTS is **per-utterance**: each co-host reaction = one short spoken line (system prompt keeps lines short; `max_output_tokens=1024`). Each line is its own `generate_content`/SSE TTS request. A 90-min set = hundreds of independent short TTS calls, back-to-back, with no shared session object that can time out. There is no LiveKit Room and no persistent bidirectional audio session that could hit a duration ceiling.
- The relevant Gemini TTS limits are **per-request**, not per-session:
  - **~655 s max output audio per request** — text that would synth longer is truncated. Irrelevant here (lines are seconds long). [Google AI / community docs]
  - **8,000-byte combined text+prompt input cap per request** — also irrelevant for one-liner reactions. [community]
  - A documented bug: **Gemini 3.1 Flash TTS SSE sometimes returns exactly 20 s / 1,280,000 base64 chars and truncates** — a *single-request* defect, not a session cap, but worth noting because the primary model is `gemini-3.1-flash-tts-preview`. The 3-entry FallbackAdapter + `response_format=pcm` partially insulates against this; vibemix's sub-second lines stay well under 20 s so it should not bite in practice. [Google AI Dev Forum thread 144813]
- **Verdict:** streaming/per-utterance TTS allows unlimited back-to-back utterances over a full set. The only thing to watch is per-request truncation defects, not continuity. The Live API's 15-min cap is exactly the constraint vibemix DESIGNED AROUND by choosing cascade + per-utterance TTS (corroborated by `.planning/research/v3-buckets/B-gemini-capabilities.md:168` — Flash Live would need a "session-resume manager for 15-min cap").

Sources: https://ai.google.dev/gemini-api/docs/speech-generation · https://discuss.ai.google.dev/t/.../144813 · https://docs.cloud.google.com/text-to-speech/docs/gemini-tts

---

## 3. LATEST 2026 GEMINI TTS — models / prices / sources

| Model | Status (2026) | Use in repo | Notes |
|---|---|---|---|
| **gemini-3.1-flash-tts-preview** | Preview, current flagship Flash TTS | PRIMARY (via OpenRouter) + SECONDARY (native) | Prompt-steerable, 30 voices, 100+ languages, controllable style/pacing, up to 2 speakers, 24 kHz/16-bit mono PCM out. SSE streaming. |
| **gemini-2.5-flash-preview-tts** | Older preview | TERTIARY fallback | Cheaper. |
| **gemini-3-flash-tts-preview** | Preview | `debrief_tts` (post-session, FLEX tier) | Not on the live path. |

**Verified pricing (per 1M tokens, 2026):**
- **gemini-3.1-flash-tts**: **$1.00 input (text) / $20.00 output (audio)**. Audio billed at **~25 tokens per second of audio**. → The repo's `budget.py:164` `live_coach_tts {"input":1.00,"output":20.00}` is **CORRECT / matches real prices.**
- **gemini-2.5-flash-tts**: ~**$0.50 input / $10.00 output** per 1M (cheaper — the fallback model is genuinely the cost lane).
- For context, the brain (`gemini-3.5-flash`, `budget.py:163`) bills $1.50 in / $9.00 out with a $0.15 cached-input rate (90% cache discount); median text latency ~1.19 s, ~185 tok/s.

**Is there a newer/cheaper/faster TTS option?**
- **gemini-3.1-flash-tts-preview is already the newest Flash TTS** as of 2026; the repo is on it. No newer Flash-tier TTS surfaced in research.
- The repo's *fallback ordering is suboptimal for cost*: tertiary (`2.5-flash-tts`, half the price) only fires on double failure. That's correct for quality-first (newest model primary), but if budget pressure appears, 2.5-flash-tts is the cheaper knob — a one-line `_router_config.py` swap.
- **Gemini-TTS on Vertex / Cloud TTS** exists as an alternate surface but adds GCP plumbing — not worth it for an OSS app; OpenRouter+direct API is simpler.

Sources: https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-tts-preview · https://openrouter.ai/google/gemini-3.1-flash-tts-preview · https://www.metacto.com/blogs/... · https://costgoat.com/pricing/gemini-api · https://cloudprice.net/models/google-gemini-3-1-flash-tts · https://almcorp.com/blog/gemini-3-1-flash-tts/ · https://cloud.google.com/blog/products/ai-machine-learning/gemini-3-1-flash-tts-on-google-cloud

---

## 4. TTFT / LATENCY STORY

- **Target: `LIVE_TTFT_BUDGET_MS = 1500`** (the anti-slop "alive, not late" bar). Lives in the soak/perf harness + `.env`, referenced across `.planning/` (PROJECT.md:96, PITFALLS.md:117, FEATURES.md:67). This is event_fired → first brain token.
- Two meters wired into `llm_node`:
  - `TTFTMeter` (`runtime/ttft.py`): rolling 8-sample avg of event_fired→first-brain-chunk; cold-start sentinel 1500 ms; now telemetry-only (the pre-canned ack-bank it once fed was retired — pre-recorded English fillers fought the anti-slop thesis).
  - `LLMToTTSDeltaMeter`: always-on, measures event_fired → **first-sentence-yielded-to-TTS** (the speculative-head emit). Emits `llm_to_tts_delta_ms` to `events.jsonl`.
- **How cascade + streaming-TTS meets the bar:** brain runs `thinking_level="minimal"` + Gemini context caching (90% cached-input discount, prompt diet) for a 500–1500 ms TTFT win; the speculative head ships the *first sentence* to TTS the instant it's grammatically complete (doesn't wait for the full line); TTS streams incremental PCM. Perceived latency is further masked by the mascot moving at ~T+50 ms before any audio (`synthesis-viral-demo.md`).
- **vs Live API:** Gemini 3.1 Flash Live reportedly hits ~250–500 ms first-audio / ~960 ms full round-trip (`B-gemini-capabilities.md:12`) — *faster on paper* than the cascade's ~1500 ms budget. BUT: (a) Live has the 15-min session cap (needs a resume manager); (b) Live is *more expensive* ($0.75/$4.50 vs cascade ~$0.50/$3); (c) Kaan's March Native-Audio test found **grounding was worse** than explicit Flash+TTS — and grounding is the hard release gate. So cascade+streaming-TTS is the deliberate, quality-driven choice; Flash Live stays a deferred v3.x opt-in toggle pending a music-grounding spike (LAT-09, still open).

---

## 5. LEVEL-UP RECOMMENDATIONS (Gemini-first)

1. **Fix the stale docstring (free, do-now).** `dj_cohost.py:26-29` claims buffer-then-batch; the code does speculative streaming. The wrong comment will mislead the next person tuning latency. (Doc-only; not behavior.)

2. **Multi-sentence speculative streaming.** Today only the FIRST sentence is yielded speculatively, then the rest streams. For 2-sentence reactions, consider yielding each completed sentence as it boundaries (the `find_sentence_end(start=...)` API already supports resume) — shaves perceived latency on longer lines. Weigh against the slop/citation gate: each speculatively-yielded sentence is un-revocable once in the OPUS encoder (the silence-pad degrade). Keep the gate prefix-checked per sentence.

3. **Prosody / voice steerability.** `gemini-3.1-flash-tts` is prompt-steerable (style, pacing). The repo passes a static `_TTS_INSTRUCTIONS = "Casual studio friend, brief, natural — no theatrics"`. Highest-leverage realism win: **mood-condition the TTS instruction** (hype vs coach, energy of the moment) so the voice's energy tracks the set — vibemix already has `VIBEMIX_MOOD` + live `MusicState.mood`. Thread mood into `_TTS_INSTRUCTIONS` per-utterance. This is the single biggest "feels alive" upgrade and stays Gemini-native.

4. **Parallel TTS while brain still generating** is ALREADY done (speculative head). The remaining win is **shrinking brain TTFT**, not TTS: keep prompt-diet + context cache hot (the 1024-token cache floor padding), and keep `thinking_level=minimal`. Don't add an embedding round-trip on the hot path (PITFALLS.md:117 — blocking embed blows the 1500 ms budget).

5. **Guard the 20 s SSE truncation bug.** Primary model `gemini-3.1-flash-tts-preview` has a documented SSE 20 s/truncation defect. vibemix's sub-second lines are safe, but add a per-utterance defensive check (if a line's text would synth >~15 s, it's a prompt bug — cap it) so a runaway brain output can never trip the truncation path. Low effort, closes a latent edge.

6. **Cost knob, not urgent.** Pricing verified correct. If €/mo pressure appears, demote primary to `gemini-2.5-flash-tts` (half price: $0.50/$10) — quality-vs-cost is a one-line `_router_config.py` edit. Keep 3.1 as default for the launch (quality-first).

7. **Re-spike Gemini 3.1 Flash Live (deferred, v3.x).** 250–500 ms first-audio is tempting, but only flip if a music-grounding spike (LAT-09) proves grounding ≥ cascade. Until then, cascade+streaming-TTS is correct.
