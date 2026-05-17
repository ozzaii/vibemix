# Phase 41: Gemini SKU Upgrade + Latency Stack v2 - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous — gsd-autonomous fully)

<domain>
## Phase Boundary

Adopt 2026 Gemini deltas across the stack to bring end-to-end latency from 5-10s → 3-5s and perceived latency to 0-2s (with Phase 40's lookahead offsetting the LLM hop). Three orthogonal concerns:

1. **ModelRouter seam** — kill every hardcoded `gemini-3-flash` literal across `src/vibemix/`. One config-driven router maps `path: SKU + tier` (live coach = Standard 3-Flash; debrief = Flex 3.1-Pro; library auto-tag = Flex 3-Flash; embedding = Flex Embedding-2). CI grep gate enforces zero literals after this phase.
2. **Caching cleanup** — Gemini's 2026 implicit caching default-on for static system prompts makes most of `GeminiContextCache`'s explicit cache-create machinery redundant. Strip the static-prefix path; keep explicit cache ONLY for per-session evidence registry (which is dynamic). Raise explicit cache TTL to 60min; refresh-on-evidence-mutation only.
3. **Latency primitives** — three additive wins:
   - LLM→TTS streaming pipe-through: consume `generateContentStream` SSE, kick off TTS on first sentence (200-400ms perceived savings).
   - Migrate live TTS path to Gemini 3.1 Flash TTS (200+ audio tags, 300-500ms first chunk).
   - `thinking_level=MINIMAL` enforced on live coach path (rejects runtime override; avoids 7s+ TTFT regression).
4. **Embedding 2 GA + MRL 768-dim** — migrate Phase 28's library index to 768-dim Matryoshka-truncated Embedding 2 vectors; index 4× smaller on disk; bit-identical top-K parity test must pass (no regression in citation quality).
5. **Flex tier for batch paths** — library re-index, debrief generation, eval-corpus replay route through Gemini Flex API (50% cost cut). Live coach stays Standard (latency-critical).
6. **3.1 Flash Live spike** — 1-2 day spike against real DJ clip with Proactive Audio enabled. Verdict goes in `spikes/gemini-3-1-flash-live-music.md`. Hard go/no-go on whether v3.x toggles to Live Native Audio.

Out of scope: rewriting the cascade architecture; changing Gemini SDK; deprecating OpenRouter fallback; any non-Gemini provider.

</domain>

<decisions>
## Implementation Decisions

### ModelRouter Seam
- Single `src/vibemix/llm/model_router.py` module owns the `path → (SKU, tier)` mapping. Config in `src/vibemix/llm/model_router.yaml` (or equivalent JSON5 sibling — pick whichever matches existing config conventions).
- Path keys: `live_coach`, `debrief`, `library_auto_tag`, `embedding`. Each maps to `{model: "...", tier: "standard"|"flex"}`.
- Default config (2026-05-16 SKU lineup):
  - `live_coach`: `gemini-3-flash` standard
  - `debrief`: `gemini-3-pro` flex (was 3-flash; bump to Pro for debrief depth; cost amortized via Flex)
  - `library_auto_tag`: `gemini-3-flash` flex
  - `embedding`: `gemini-embedding-002` flex
- Every Gemini SDK invocation site in `src/vibemix/` consumes the router. CI grep gate (`scripts/release/check_no_hardcoded_model.sh`) blocks PRs that introduce literal `gemini-3-flash` / `gemini-3-pro` / `gemini-embedding-001` strings outside the router config + tests.

### Caching Cleanup
- Static-prefix implicit caching: remove `GeminiContextCache.create_static_cache()` + all callers; trust Gemini's 2026 implicit cache. Static-prefix code path deleted, not deprecated.
- Per-session evidence-registry explicit cache: keep as v2.1 architecture; raise TTL `4min → 60min`. Refresh ONLY on `EvidenceRegistry.mutate()` (not on a wall clock). Delete the 4-min refresh background task + its tests.
- Migration safety: existing `cache_id` references in `GeminiContextCache` must keep functioning during the transition turn — feature-flag the v2.1 → v3.0 cache shape (`CACHE_SHAPE: v2_1 | v3_0`, default `v3_0`, fall back via env var for one-week soak).

### LLM→TTS Streaming Pipe-Through
- Refactor `run_one_turn` in `src/vibemix/agent/dj_cohost.py` (or wherever the cascade lives in current main) to:
  - Open `generateContentStream` SSE instead of `generateContent`.
  - Buffer tokens until first sentence boundary (regex `[.!?]\s` or `\n\n`).
  - Kick off TTS request with first sentence; continue feeding tokens; queue subsequent sentence-chunks to TTS in order.
- TTS path also streams (Gemini 3.1 Flash TTS supports streaming response); first audio chunk plays as soon as it arrives.
- Measure perceived-latency savings via existing `TTFTMeter` + new `LLMToTTSDeltaMeter`. Log to `events.jsonl`. CI gate asserts measured savings 200-400ms on a synthetic-session replay.

### Gemini 3.1 Flash TTS Migration
- Default live coach TTS = `gemini-3-1-flash-tts`. OpenRouter Achird OPUS fallback preserved (existing chain — do NOT remove the fallback IP; it's still the second-place choice when Gemini quota trips).
- Expose expressive-tag DSL in coach prompt template: `[whisper]`, `[laugh]`, `[fast]`, `[slow]`, `[excited]`, `[chill]`. New tag set documented in `docs/prompts/tts-tags.md`. Persona overlays can opt-in per-mood.
- `tests/llm/test_tts_3_1.py` — VCR-cassette-based unit tests: rendering with each tag produces a valid audio chunk (response shape valid, mime correct).

### Embedding 2 GA + MRL 768-dim
- Migrate `src/vibemix/library/embeddings.py` (or wherever Phase 28's index lives) from `gemini-embedding-001` → `gemini-embedding-002`.
- MRL truncation: store 768-dim slice of the full vector (Embedding 2 outputs 2048-dim; 768 is the sweet spot for cosine-similarity recall per Embedding 2 docs).
- Disk impact: existing index ~80MB → ~20MB; commit the new shape + a migration script (`scripts/library/migrate_embeddings_2.py`) that re-embeds the existing corpus on first launch with new SKU.
- Parity gate: `tests/library/test_embeddings_parity.py` — for a 100-track corpus, top-10 retrieval results MUST be bit-identical between v1 (2048-dim full) and v2 (768-dim truncated) at the cited-relevance threshold. If parity fails, raise the truncation length to 1024 and re-test.

### Flex Tier Wiring
- Router's `tier: "flex"` translates to Gemini SDK's `priority_tier="flex"` parameter (or `mode="flex"` — whichever the 2026 SDK uses).
- Three call sites must default to Flex: library auto-tag indexer (Phase 28), debrief generator (Phase 29), eval-corpus replay (Phase 27 replay_harness). Live coach explicitly opt-out — Flex SLA (60min P99) is not OK for live.
- CI cost gate: nightly batch run total Gemini spend < €50/mo (existing v2.1 €/mo CI gate stays). Flex 50% cut should bring it well under.

### Thinking-Level Enforcement
- `LiveCoachClient.send_request()` rejects `thinking_level` override at runtime — only accepts `"MINIMAL"` (or `thinking=False`, whichever the 2026 SDK uses). Caller passes a different value → raise `LiveCoachConfigError`.
- Rationale: thinking adds 7s+ TTFT regression on live path; debrief/library can override (their own router paths).

### 3.1 Flash Live Spike
- Time-boxed 1-2 day investigation. Output: `spikes/gemini-3-1-flash-live-music.md` with verdict structure:
  - Latency on real DJ clip vs cascade (TTFT, total turn time)
  - Anti-hallucination behavior (does it stay grounded? does Proactive Audio mode hallucinate beats?)
  - Cost per minute
  - Recommendation: `defer-to-v3.x` toggle vs `sealed-no`
- Spike does NOT ship Live as default; it's pure investigation. The current cascade pattern stays default until v3.x (post-v3.0) regardless of spike outcome.

### Claude's Discretion
- Exact module file names within `src/vibemix/llm/` (subject to existing conventions).
- Whether the router config is YAML / JSON5 / Python — pick whichever current `src/vibemix/` already uses (no new file format).
- Migration script's UX (CLI prompt vs auto-run vs lazy-on-first-query).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/llm/` already has provider abstractions; ModelRouter slots in alongside existing `live_coach_client.py` / `tts_client.py` (or whatever the current names are post-v2.1).
- `GeminiContextCache` (Phase 23+) already has explicit cache-create + refresh logic — caching cleanup deletes the static path, keeps the dynamic path.
- `TTFTMeter` (Phase 22 or 27) already wraps Gemini calls with timing; reuse the wrapper for `LLMToTTSDeltaMeter`.
- `scripts/eval/replay_harness.py` (Phase 27) drives the eval corpus; can drive the latency-savings CI gate.
- Phase 28 library index is the migration target for Embedding 2.
- `gsd-autonomous fully` autonomy mode applies — `spikes/` output is engineering scaffolding; the actual 1-2 day spike investigation may be a Kaan-action discharge if real-DJ-clip time isn't autonomously available. Document the spike framework + a placeholder verdict scaffold.

### Established Patterns
- All Gemini SDK calls go through a single client class (don't fan out raw SDK calls).
- Tests use VCR cassettes for Gemini interactions (no real spend in CI).
- Config files live in `src/vibemix/<module>/<module>.yaml` colocated with the module.
- CI gates live in `scripts/release/check_*.sh` and run from `.github/workflows/release.yml`.
- `events.jsonl` is the session-level structured log surface; latency meters write here.

### Integration Points
- ModelRouter wires into every existing Gemini call site: `live_coach_client.py`, `tts_client.py`, `library/auto_tag.py`, `library/embeddings.py`, `agent/dj_cohost.py` (cascade orchestrator), `agent/debrief.py`.
- `GeminiContextCache` consumers: `dj_cohost.py` (per-turn cache check) + `evidence_registry.py` (mutation refresh trigger).
- Embedding migration entry point: `library/__init__.py` or `library/embeddings.py` `register_library()` slot.
- CI grep gate: `.github/workflows/release.yml` → new `model-literal-check` job.

</code_context>

<specifics>
## Specific Ideas

- Embedding 2 MRL truncation is well-documented in Google's 2025-Q4 Embedding 2 blog post — 768-dim retains >97% recall vs 2048-dim full on text retrieval; vibemix's audio+text mixed corpus may differ, hence the parity test.
- Gemini 3.1 Flash TTS audio-tag DSL is in the 2026-Q1 release notes — vibemix's persona prompts already gesture at these tags via prose ("you whisper conspiratorially") so the structural DSL replaces inline prose hints cleanly.
- "harikaydı" Phase 40 baseline regression must hold after this phase — the latency stack changes the timing but NOT the grounding signals (mic + lookahead Parts unchanged).

</specifics>

<deferred>
## Deferred Ideas

- **Live Native Audio default** — spike outcome may green-light a v3.x toggle, but default cascade unchanged for v3.0.
- **Embedding caching at the SDK layer** — Embedding 2 supports per-doc caching; defer until measured cache-hit-rate justifies the wiring complexity.
- **Multi-region failover** — Gemini 2026 has region-specific endpoints; defer until first real outage forces the hand.
- **Streaming TTS chunked playback at sub-sentence granularity** — phoneme-level streaming is technically possible but adds complexity; sentence-boundary chunking is sufficient for the 200-400ms savings target.

</deferred>
