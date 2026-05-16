# B — Gemini Capabilities for vibemix v3

**Researched:** 2026-05-16
**Mode:** Ecosystem (Gemini-only, scoped to vibemix v3 architecture decisions)
**Overall confidence:** HIGH on shipped surfaces, MEDIUM on Live API for live-music context (no Google docs target it), LOW on a few pricing/cap figures where third-party trackers disagree with primary blog posts.

---

## TL;DR — Top 5 capabilities that change v3 options

1. **Gemini 3.1 Pro (GA 2026-02-19) + 3.1 Flash (still preview) + 3.2 Flash leak (2026-05-05)** widen the routing menu. v3 can keep 3 Flash as the default trigger brain and reserve 3.1 Pro for the post-session debrief / library indexing where reasoning > latency. (HIGH)
2. **Gemini 3.1 Flash Live Preview (2026-03-26)** lands at **~250-500ms first-audio** and **960ms full round-trip**, with ComplexFuncBench Audio at 90.8%, Affective Dialog, Proactive Audio, and improved instruction-following (90% adherence, up from 84%). Worth a *narrow re-test* on live music — but the v2.1 Native-Audio grounding finding from Kaan's March test still stands until proven otherwise. (HIGH on numbers, MEDIUM on music-context relevance — Google docs never target music input.)
3. **Implicit caching is now default-on for Gemini 2.5+ models** with a 1024-token floor for Flash, no storage fee, 90% read discount. vibemix's `GeminiContextCache` (P60) can shed the explicit-create/refresh machinery for the *static* prompt prefix and keep explicit cache only for the per-session evidence registry. (HIGH)
4. **Flex (50% off, 1-15 min latency) and Priority (75-100% premium, ms-s latency) inference tiers (2026-04-01)** create a real cost lever: route library-indexing / debrief into Flex, route live coach calls into Standard or Priority. Cuts the €50/mo end-user budget meaningfully if library embedding traffic is the dominant cost. (HIGH)
5. **Gemini Embedding 2 went GA 2026-04-22** with **MRL truncation (3072 / 1536 / 768)**, batch-API 50% discount, and multimodal-RAG-grade adoption (Nuuly 60→87% Match@20, Harvey +3% Recall@20). v3 library intelligence (P28) gets a cheaper index and a free-of-charge dimensional knob. (HIGH on capability, LOW on audio cap — see §3 for the 80/120/180s contradiction.)

---

## 1. Gemini API surface deltas — March → May 2026

Pulled from the [Gemini API changelog](https://ai.google.dev/gemini-api/docs/changelog) and primary blog posts.

| Date | Surface | Net effect for vibemix |
|------|---------|------------------------|
| 2026-02-19 | **Gemini 3.1 Pro GA** — 1M ctx, ARC-AGI-2 77.1%, `thinking_level=MEDIUM` parameter, multimodal function-call responses | New default for *non-live* paths: corpus replay scoring, library auto-tagging, debrief drafting. Live path stays on 3 Flash. ([blog.google](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-pro/)) |
| 2026-03-10 | `gemini-embedding-2-preview` released | Replaces text-only embedding everywhere in v3. ([marktechpost](https://www.marktechpost.com/2026/03/11/google-ai-introduces-gemini-embedding-2-a-multimodal-embedding-model-that-lets-your-bring-text-images-video-audio-and-docs-into-the-embedding-space/)) |
| 2026-03-18 | **Built-in tools + function calling in one call** | Lets the v3 live coach combine `googleSearch` grounding (for "what genre is this track?") with a user-defined `flag_hallucination()` callback in a single round-trip. Removes one of the prompt-diet workarounds. ([changelog](https://ai.google.dev/gemini-api/docs/changelog)) |
| 2026-03-25 | `lyria-3-clip-preview` + `lyria-3-pro-preview` (music gen, 48kHz stereo, text+image conditioning) | Out of scope for v3 — kept for awareness only. |
| 2026-03-26 | **`gemini-3.1-flash-live-preview`** — see §2 | Candidate for a *narrow* re-test (see §2 + §7). |
| 2026-04-01 | **Flex + Priority inference tiers** | Cost knob — see TL;DR. ([blog.google](https://blog.google/innovation-and-ai/technology/developers-tools/introducing-flex-and-priority-inference/)) |
| 2026-04-15 | **Gemini 3.1 Flash TTS Preview** — 200+ audio tags, expressive control, 300-500ms first-chunk | Direct drop-in for v3's current Gemini TTS streaming path. ([blog.google](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-flash-tts/)) |
| 2026-04-22 | **`gemini-embedding-2` GA** | P28 library index can move from preview to GA without a code change. ([changelog](https://ai.google.dev/gemini-api/docs/changelog)) |
| 2026-05-05 | File Search + `gemini-embedding-2` multimodal File Search ; **`gemini-3.2-flash` leaked in iOS app / AI Studio metadata** ($0.25/$2.00 in/out) | I/O 2026 (May 19-20) is the likely reveal window — v3 should keep the model ID configurable, not hard-wire `gemini-3-flash`. ([buildfastwithai](https://www.buildfastwithai.com/blogs/gemini-3-2-flash-release-2026)) |
| 2026-05-07 | `gemini-3.1-flash-lite` GA | Too weak for the v3 coach (cohost.py confirms Flash-tier is the floor for evidence-grounded reactions) but viable for the per-frame screen-OCR side-channel if one materialises. |

**Implications:** v3 needs a `ModelRouter` configuration layer — not a hardcoded `gemini-3-flash`. Different paths (live coach, debrief, library auto-tag, embedding) all map to different SKUs and different inference tiers.

---

## 2. Gemini Live Native Audio — May 2026 status

**Verdict: WARRANTS a narrow re-test (not a default switch).** v2.1 Kaan-found grounding finding is still credible until disproven on the new model.

**What's new since Kaan's March 2026 test:**
- `gemini-3.1-flash-live-preview` released 2026-03-26 — 90.8% on ComplexFuncBench Audio (vs 71.5% on the 2.5-era version). ([marktechpost](https://www.marktechpost.com/2026/03/26/google-releases-gemini-3-1-flash-live-a-real-time-multimodal-voice-model-for-low-latency-audio-video-and-tool-use-for-ai-agents/))
- **Affective Dialog** + **Proactive Audio** features. Proactive Audio specifically *suppresses non-directed input* — could mitigate the "AI reacts to the bass like it's a voice" failure mode Kaan saw. ([cloud.google.com](https://cloud.google.com/blog/topics/developers-practitioners/how-to-use-gemini-live-api-native-audio-in-vertex-ai))
- Instruction adherence 84% → 90%.
- ~960ms round-trip in production. ([automatio.ai](https://automatio.ai/models/gemini-3-1-flash-live))
- Sequential function calling only (no NON_BLOCKING — that's 2.5-only). VAD configurable via `realtimeInputConfig.automaticActivityDetection` with low/medium/high sensitivity. ([ai.google.dev/gemini-api/docs/live-api/capabilities](https://ai.google.dev/gemini-api/docs/live-api/capabilities))

**What still bites for live music:**
- **Audio-only sessions are capped at 15 minutes; audio+video at 2 minutes.** A DJ set is 60-120 min. v3 would need a session-resume / chunked-session orchestrator to use Live API for the live coach. The cascade path has no such cap.
- **VAD is built for *speech* on a *speech* background.** Google's own best-practices doc warns "background typing/clicking causes interruptions" — Kaan's 124-BPM kick will look like continuous speech to the default VAD. Tunable to `low`, but undocumented on music. ([ai.google.dev/gemini-api/docs/live-guide](https://ai.google.dev/gemini-api/docs/live-guide))
- **No published music-context benchmark.** Every Live API metric Google publishes is conversational ASR / function-calling on speech.
- **Pricing:** $0.75/M in, $4.50/M out (audio output), $0.018/min audio out — meaningfully more expensive than 3 Flash cascade ($0.50/M in, $3/M out, audio in $1/M ≈ 25 tokens/sec). ([cloudprice.net](https://cloudprice.net/models/google-gemini-3-1-flash-live-preview))

**Recommendation for v3:** keep the LiveKit pipeline + Gemini 3 Flash cascade as default. Add a 1-2 day spike in v3 to re-test 3.1 Flash Live *with Proactive Audio enabled* on a 5-minute genre-representative DJ clip per Kaan's ear. If it grounds, file a v3.x toggle — not a default flip.

**Architecture change if adopted later:** session-resume manager (the 15-min cap is non-negotiable) + replace the `EventDetector → generate_reply()` trigger pattern with VAD-driven turns. Effort: phase-level (~Phase-equivalent of v2.1's P19 Latency Stack).

---

## 3. Gemini Embedding 2 — new use cases

GA on 2026-04-22 via Gemini API + Vertex AI. Three details that change v3 options:

**a) Matryoshka Representation Learning.** Default 3072 dim, recommended fallbacks 1536 / 768. The same embedding is *truncatable client-side*; no re-call required. ([developers.googleblog](https://developers.googleblog.com/building-with-gemini-embedding-2/)) For vibemix's sqlite-vec / numpy index (P28), 768 cuts disk + RAM 4× with negligible Recall@20 hit. **Drop-in**, no architecture change.

**b) Audio cap — primary sources disagree.** Three numbers in circulation:
- 80s per request — tokencost.app price page.
- 120s per request — primary Google blog (verified via WebFetch 2026-05-16).
- 180s per request — internal memory `[[project-gemini-embedding-2]]` (3 days old, sourced from preview-era docs).

  **Confidence: MEDIUM.** Treat the canonical limit as **120 s** until vibemix integration tests an empirical-max script; the project memory should be updated post-test. Implication: for "what's playing now" grounding, a 120 s window comfortably covers a phrase (~32 bars at 124 BPM = 62 s).

**c) Per-modality token rate is steep for audio.** Tokencost reports $6.50/M audio tokens for Embedding 2 ([tokencost.app](https://tokencost.app/blog/gemini-embedding-2-pricing)). At 25 tokens/sec, embedding one 120s track = 3000 tokens = ~$0.0195. A 1000-track library = ~$19.50, one-time. Acceptable for the €50/mo end-user budget; library indexing batched via Flex (50% off) brings it to ~$10.

**New v3 use cases unlocked by GA + multimodal-RAG production patterns** (cite: Nuuly, Harvey, Supermemory — case studies in the [developers blog](https://developers.googleblog.com/building-with-gemini-embedding-2/)):
- **"Sounds like this" library search from a live phrase** — embed a 30s window of the current track, top-K against the user's pre-indexed library, surface 3 harmonically-compatible candidates to the coach. New v3 feature, phase-level effort.
- **Cross-modal "vibe matches my mood" search** — embed the screen capture + recent mic transcript jointly, retrieve tracks. Stretch.
- **Session-moment retrieval for debrief** — embed each event window + audio, search "show me my best transitions" semantically. Drop-in extension of P29.

---

## 4. Prompt caching patterns — 2026

Three patterns are now stable; v3 should adopt all three:

**a) Implicit cache, default-on.**
- All Gemini 2.5+ models — automatic prefix detection.
- Floor: **1024 tokens** for Flash, 2048 for Pro. ([developers.googleblog](https://developers.googleblog.com/gemini-2-5-models-now-support-implicit-caching/))
- 90% read discount, **no storage fee**, no API surface to manage.
- **Action for v3:** strip the explicit cache-create call from `GeminiContextCache` (P60) for the *static* system prompt + persona block — implicit handles it for free. Keep explicit cache only for the per-session evidence registry that needs TTL control.

**b) Explicit cache for per-session evidence.**
- Storage: $1/M tokens/hour (Flash), $4.50 (Pro). 90% read discount on Gemini 2.5+. ([ai.google.dev/gemini-api/docs/caching](https://ai.google.dev/gemini-api/docs/caching))
- TTL default 60 min, no upper bound, updatable.
- **Action for v3:** the v2.1 P60 4-min refresh strategy is now *too aggressive* — implicit handles ≤4-min reuse for free. Raise explicit TTL to 60 min and only refresh on evidence-registry mutations. Cost delta: estimate -30% on session-prompt input tokens vs v2.1.

**c) Batch API for non-live (Flex).**
- 50% off standard for embedding + content calls.
- Library indexing, debrief generation, eval-corpus replay → Batch.

**Cost-optimization math for v3 (back-of-envelope, single user, 2-hr session, 30 coach turns):**

| Path | v2.1 cost | v3-with-implicit + Flex | Delta |
|------|-----------|-------------------------|-------|
| Live coach (3 Flash, 30 turns × ~3K prompt tokens, ~150 out) | ~$0.054 | ~$0.018 (implicit 90% on prefix) | **-67%** |
| TTS (Flash TTS, 30 × ~5s out) | ~$0.045 | ~$0.045 (no caching applies) | 0 |
| Embedding (live-window "what's playing", 30 × 5s windows × 25t/s) | ~$0.024 | ~$0.012 (Flex) | **-50%** |
| Debrief (3.1 Pro, 1 × 50K in, 5K out) | ~$0.16 | ~$0.08 (Flex) | **-50%** |
| **Total / 2-hr session** | **~$0.28** | **~$0.16** | **-43%** |

(Estimates only. Confidence MEDIUM — assumes a single mid-load user; €50/mo budget covers ~300 such sessions at v3 rates vs ~180 at v2.1 rates.)

---

## 5. AI music understanding SOTA (consumer-deployable only)

vibemix is Gemini-only, so this section is bounded by "what can run *alongside* Gemini in the v3 binary without breaking the one-click install" — i.e., pure-Python, no PyTorch model files >50 MB, no Java, no Node sidecar.

| Capability | SOTA May 2026 | Consumer-deployable in vibemix v3? | Notes |
|------------|----------------|-------------------------------------|-------|
| **Real-time beat tracking** | [**Beat This!** (ISMIR 2024, Foscarin/Schlüter/Widmer)](https://arxiv.org/abs/2407.21658) — transformer, no DBN post-processing, beats SoTA F1 across genres; PyTorch Lightning checkpoints. [C++ port](https://github.com/mosynthkey/beat_this_cpp) + [Rust crate](https://crates.io/crates/beat-this) exist. | **MAYBE** via Rust crate → single Tauri sidecar. **NOT** via PyTorch checkpoint (violates one-click install constraint). | Realtime mode is real-time, not zero-latency — needs ~4s lookback. v3 effort: phase-level — wire Rust binary as sidecar, IPC over Unix socket. |
| Real-time beat tracking (alternative) | [BeatNet (ISMIR 2021)](https://github.com/mjhydri/BeatNet) — CRNN + particle filter, streaming mode supported | **NO** — PyTorch + librosa dep tree breaks one-click install. | Reference for v3-eval ground-truth only. |
| Real-time beat tracking (alternative) | [Zero-latency beat tracker (TISMIR 2024)](https://transactions.ismir.net/articles/10.5334/tismir.189) | Research-only — no shipped artifact. | Not viable. |
| **Phrase/section boundary** | [Barwise Section Boundary Detection (ISMIR 2025, Eldeeb/Malandro)](https://arxiv.org/html/2509.16566v1) — MobileNetV3-pretrained CNN on piano-roll patches, 32 bars @ 4/4. | **NO** — needs MIDI/symbolic input, not raw audio. Useful only post-stems. | v3 keeps the heuristic `PHRASE_BOUNDARY` detector from v2.0/v2.1. |
| **Genre / style classification** | No clear SoTA shift in 2026 worth porting; Gemini 3 Flash itself does this well from audio. | **YES via Gemini** — feed 7-30 s audio, ask for genre. ([Gemini Audio](https://deepmind.google/models/gemini-audio/) confirms genre/mood/instrument tagging.) | Already used in cohost.py — keep. |
| **Harmonic compatibility / key detection** | Camelot-wheel-based commercial software (Mixed In Key, Serato, Rekordbox) — no breakthrough open algorithm in 2026. | **Pre-compute offline** via Gemini-embedding-2 nearest-neighbor or via Rekordbox XML import (already v2.0 P25). | Don't ship a key-detector. Import the user's existing one. |
| **Onset detection / phase change** | librosa + numpy already in vibemix POCs. Sufficient. | YES — already shipped. | No change. |

**Net SOTA implication for v3:** Beat This! via Rust sidecar is the single highest-leverage outside-Gemini addition — gives the trigger layer a non-Gemini beat-grid for the first time, closes the "AI reacts off-beat" hallucination class. Phase-level effort. Defer to v3.x if one-click-install bar slips.

---

## 6. Latency tricks — keeping Gemini round-trip <800 ms for live music

**Hard numbers from May 2026:**
- Gemini 3 Flash TTFT (text): consistently <500 ms reported on standard streaming; 7.69s on artificialanalysis.ai with reasoning enabled. ([artificialanalysis.ai](https://artificialanalysis.ai/models/gemini-3-flash-reasoning))
- Gemini 3.1 Flash TTS: **300-500 ms first chunk**. ([almcorp](https://almcorp.com/blog/gemini-3-1-flash-tts/))
- Gemini 3.1 Flash Live full round-trip: ~960 ms reported. ([automatio.ai](https://automatio.ai/models/gemini-3-1-flash-live))

**Sub-800 ms budget for v3 (cascade path):**
```
Event detect →  prompt build → Gemini 3 Flash gen → TTS first chunk
  ~50 ms     +   ~30 ms       +  300-500 ms (TTFT)+  300-500 ms (TTS)
                                                  ≈ 700-1100 ms total
```
Headroom is *tight*. Tricks that move the needle:

1. **Streaming the LLM into the TTS** (instead of awaiting full text). [Firebase docs](https://firebase.google.com/docs/ai-logic/stream-responses) + [TechWithTy/gemini-stream](https://github.com/TechWithTy/gemini-stream) confirm SSE token streaming on `generateContentStream`. v3 should pipe the *first sentence* into TTS once it lands, not wait for the full reply. Saves ~200-400 ms perceived latency. **Drop-in.**
2. **`thinking_level=MINIMAL`** on Gemini 3.1 Pro / `thinking=False` on 3 Flash for the live coach. Default reasoning on 3 Flash adds seconds of TTFT. ([artificialanalysis.ai](https://artificialanalysis.ai/models/gemini-3-flash-reasoning) confirms TTFT collapses without reasoning.) **Drop-in.**
3. **Anticipatory prompts (v4_tr lookahead).** Already in POC — see [[project-v4-tr-lookahead]]. 3s file-based forward window via `nowplaying-cli` + `mdfind` + `ffmpeg`. Phase-level port to v3 binary.
4. **Implicit caching of the static prefix** (see §4). Cache hit reportedly cuts prefill latency 20-40% on top of the cost saving (Google blog implies, no published number).
5. **Geographic routing.** `asia-southeast1` from EU / `us-central1` from US optimal. Bravoh proxy already routes to `eu-west` for low-latency; document in v3.
6. **40-OPUS AckBank fallback** (v2.0 P19). Already shipped — keeps `<200 ms` perceived response for the first 1-2 words even when the real reply is in-flight. Keep. Tune the bank to v3 voice palette.
7. **Priority inference tier** (§1) for live coach. ms-to-s latency at 75-100% premium — only worth it if Standard ever exceeds 800 ms p95 for vibemix's account. Monitor first, opt in only if needed.

**HARD constraint:** the 7.69 s "reasoning enabled" TTFT means **never enable thinking_level on the live path**. Enforce in v3 via a `LiveCoachClient` that hardcodes the parameter and rejects override.

---

## 7. v3 architecture implications

| # | Capability | Today (May 2026)? | v3 architecture change | Cost delta | Effort |
|---|------------|-------------------|------------------------|------------|--------|
| 1 | Gemini 3.1 Pro for non-live paths | GA | Add `ModelRouter` — route debrief / corpus eval / library auto-tag to 3.1 Pro; live coach stays on 3 Flash | Higher per-call but vastly fewer calls vs live | **Drop-in** |
| 2 | Gemini 3.1 Flash Live re-test | Preview | None until spike validates grounding on music; then session-resume manager for 15-min cap | $0.75 / $4.50 vs $0.50/$3 cascade — *more* expensive | **Spike (1-2d)** → phase-level if accepted |
| 3 | Embedding 2 GA + MRL truncation | GA | Move P28 from preview → GA; truncate to 768 dim in sqlite-vec | -75% index disk; embedding price stable | **Drop-in** |
| 4 | Multimodal RAG (audio+screen+text in one embedding) | GA | New v3 feature: "sounds-like" library search from live window | +$0.0195 per 120 s window embedded | **Phase-level** |
| 5 | Built-in tools + function calling in one call | GA (2026-03-18) | Coach can combine `googleSearch` grounding + user-defined `flag_hallucination` callback in one round-trip | Neutral (1 round-trip vs 2) | **Drop-in** |
| 6 | Implicit caching default-on | GA | Strip the explicit-create call from `GeminiContextCache` for the *static* prompt; keep explicit cache only for the per-session evidence registry | -30% input tokens estimated | **Drop-in** |
| 7 | Flex tier for batch paths | GA (2026-04-01) | Route library-indexing + debrief + eval-corpus replay → Flex | -50% on those paths | **Drop-in** |
| 8 | Priority tier for live coach | GA | Add tier flag in `LiveCoachClient`; opt in only if Standard p95 >800 ms | +75-100% if enabled | **Drop-in** |
| 9 | Gemini 3.1 Flash TTS (200+ tags, 300-500 ms first chunk) | Preview | Replace current TTS model ID; add expressive-tag DSL in coach prompts | Same or lower per minute | **Drop-in** |
| 10 | LLM → TTS streaming pipe-through | Available now | Refactor `run_one_turn` to consume `generateContentStream` SSE and pipe first sentence into TTS without awaiting completion | Neutral | **Drop-in** |
| 11 | `thinking_level` discipline on live | Available now | Enforce `thinking=False` / `MINIMAL` in `LiveCoachClient`; reject override | Neutral (avoids regression) | **Drop-in** |
| 12 | Beat This! via Rust sidecar | Research SoTA → C++/Rust ports exist | Non-Gemini beat-grid sidecar; trigger layer consumes beat events | Zero API cost; +bundle size | **Phase-level** (one-click-install risk — gate behind a green/yellow check) |
| 13 | 3.2 Flash readiness | Leak (likely I/O 2026, May 19-20) | Config-driven model ID; no hardcoded `gemini-3-flash` anywhere | TBD — leak says $0.25/$2.00 vs 3 Flash $0.50/$3 (=cheaper) | **Drop-in** (just don't hardcode) |
| 14 | Mic as literal audio Part | Already validated in POC ([[feedback-mic-audio-as-multimodal-part]]) | Two-audio-part `contents` array (mix + mic) in every coach invocation | +1 audio Part per call (~25 tokens/sec × mic ring) | **Drop-in** to v3 port |
| 15 | Proactive Audio (Live API only) | Preview | Only relevant if §2 spike validates Live API for music | Live API premium | **Phase-level** if adopted |

**Net v3 architecture shape:** the cascade path Kaan picked stays — but every layer of it has a more efficient SKU available. v3 = same architecture, sharper SKUs, leaner cache layer, model-router seam.

---

## Sources

Primary / authoritative (HIGH):
- [Gemini API Changelog](https://ai.google.dev/gemini-api/docs/changelog) — 2026-05-16
- [Gemini Live API capabilities guide](https://ai.google.dev/gemini-api/docs/live-api/capabilities) — 2026-05-16
- [Gemini Live API best practices](https://ai.google.dev/gemini-api/docs/live-guide) — 2026-05-16
- [Gemini API Caching docs](https://ai.google.dev/gemini-api/docs/caching) — 2026-05-16
- [Gemini 3.1 Pro launch — blog.google](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-pro/) — 2026-02-19
- [Gemini 3.1 Flash TTS launch — blog.google](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-flash-tts/) — 2026-04-15
- [Gemini Embedding 2 launch — blog.google](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-embedding-2/) — 2026-03-10
- [Building with Gemini Embedding 2 — developers.googleblog](https://developers.googleblog.com/building-with-gemini-embedding-2/) — 2026-04-22
- [Gemini 2.5 implicit caching — developers.googleblog](https://developers.googleblog.com/gemini-2-5-models-now-support-implicit-caching/)
- [Flex + Priority inference — blog.google](https://blog.google/innovation-and-ai/technology/developers-tools/introducing-flex-and-priority-inference/) — 2026-04-01
- [Gemini Audio — DeepMind](https://deepmind.google/models/gemini-audio/) — 2026
- [Gemini 3.1 Flash Audio model card — DeepMind](https://deepmind.google/models/model-cards/gemini-3-1-flash-audio/) — 2026
- [Vertex AI Live API Native Audio — cloud.google.com](https://cloud.google.com/blog/topics/developers-practitioners/how-to-use-gemini-live-api-native-audio-in-vertex-ai) — 2026

Secondary (MEDIUM — confirmed via primary where possible):
- [Gemini 3.1 Flash Live — MarkTechPost](https://www.marktechpost.com/2026/03/26/google-releases-gemini-3-1-flash-live-a-real-time-multimodal-voice-model-for-low-latency-audio-video-and-tool-use-for-ai-agents/) — 2026-03-26
- [Gemini 3.1 Flash Live pricing — automatio.ai](https://automatio.ai/models/gemini-3-1-flash-live) — 2026
- [Gemini 3.1 Flash Live pricing — cloudprice.net](https://cloudprice.net/models/google-gemini-3-1-flash-live-preview) — 2026
- [Gemini 3 Flash performance — artificialanalysis.ai](https://artificialanalysis.ai/models/gemini-3-flash-reasoning) — 2026
- [Gemini 3.1 Flash TTS deep dive — almcorp](https://almcorp.com/blog/gemini-3-1-flash-tts/) — 2026
- [Gemini 3.2 Flash leak analysis — buildfastwithai](https://www.buildfastwithai.com/blogs/gemini-3-2-flash-release-2026) — 2026-05
- [Gemini Embedding 2 pricing — tokencost.app](https://tokencost.app/blog/gemini-embedding-2-pricing) — 2026 *(audio cap of 80s here conflicts with primary blog's 120s — flagged §3)*
- [Gemini API context caching guide — gemilab](https://gemilab.net/en/articles/gemini-api/gemini-api-context-caching-cost-optimization) — 2026
- [Streaming responses — firebase.google.com](https://firebase.google.com/docs/ai-logic/stream-responses) — 2026

Research SOTA (HIGH on paper, contextual on deployability):
- [Beat This! arXiv:2407.21658](https://arxiv.org/abs/2407.21658) — ISMIR 2024, Foscarin/Schlüter/Widmer
- [Beat This! GitHub — CPJKU/beat_this](https://github.com/CPJKU/beat_this)
- [Beat This! C++ port](https://github.com/mosynthkey/beat_this_cpp)
- [Beat This! Rust crate](https://crates.io/crates/beat-this)
- [BeatNet — mjhydri/BeatNet](https://github.com/mjhydri/BeatNet) — ISMIR 2021
- [Zero-latency beat tracker — TISMIR 2024](https://transactions.ismir.net/articles/10.5334/tismir.189)
- [Barwise Section Boundary Detection — arXiv:2509.16566](https://arxiv.org/html/2509.16566v1) — ISMIR 2025
- [Brian McFee — Regularity in music structure analysis, ISMIR 2025](https://brianmcfee.net/papers/ismir2025_regularity.pdf)

Cross-references inside this repo:
- `.planning/PROJECT.md` — v2.1 closed, v3 not yet scaffolded
- `[[feedback-no-clap-use-gemini-embedding]]` — Embedding 2 is the only embedding model
- `[[project-gemini-embedding-2]]` — claims 180 s audio cap; this doc flags as MEDIUM, primary blog says 120 s
- `[[feedback-mic-audio-as-multimodal-part]]` — cascade-friendly mic delivery, ports to v3 verbatim
- `[[project-v4-tr-lookahead]]` — 3s anticipatory window, lifts into v3 latency stack
- `[[project-anti-slop-grounded-gemini-thesis]]` — every recommendation here ranked by "what hallucination class does it close"
