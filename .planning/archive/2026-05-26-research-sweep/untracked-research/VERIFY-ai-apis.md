# VERIFY — AI-API Fact-Check of Research Docs

> **Verification date:** 2026-05-26
> **Verifier scope:** load-bearing AI-API claims in `youtube-ingestion-gemini.md`,
> `agent-web-search-tools.md`, plus one embedding claim in `dj-knowledge-rag-sources.md`.
> **Method:** context7 was **NOT available** in this environment (no `mcp__context7__*` tools could
> be loaded via ToolSearch). Per fallback instruction, verification used **WebFetch of official docs**
> (ai.google.dev, developers.openai.com, docs.tavily.com, exa.ai/docs) + **WebSearch** corroboration.
> Evidence column cites the authoritative doc URL + exact API reference.

## Verdict summary

**Net: the docs are accurate.** Every load-bearing API signature, class/field name, and limit checked
out against official docs. **One genuine wrong field name** in `agent-web-search-tools.md` (`url_citation`
does not exist in Gemini grounding — it's `groundingChunks`/`groundingSupports`). The doc's prose
elsewhere correctly names `groundingMetadata`/`groundingChunks`, so it's an internal inconsistency, not a
systemic hallucination. Everything else CONFIRMED.

---

## Table

| Claim | Verdict | Evidence (doc + exact API ref) |
|---|---|---|
| **YT-1** YouTube URL passed via `types.Part(file_data=types.FileData(file_uri="https://www.youtube.com/watch?v=..."))` | **CONFIRMED** | ai.google.dev/gemini-api/docs/video-understanding — docs show exactly `types.Part(file_data=types.FileData(file_uri=...))`; raw JSON `"fileData": {"fileUri": "..."}`. No `mime_type` required for YouTube URL. |
| **YT-2** `types.VideoMetadata(start_offset=..., end_offset=..., fps=...)` exists; offsets are strings like `"1250s"` | **CONFIRMED** | Same doc — example `video_metadata=types.VideoMetadata(start_offset='1250s', end_offset='1570s')`; offsets are `"<n>s"` strings. |
| **YT-3** `fps` field on `VideoMetadata`; default 1 FPS; lower for static/music | **CONFIRMED** | video-understanding.md.txt + Vertex `VideoMetadata` Python class ref — "By default 1 FPS sampled"; custom `fps` arg; "set low FPS (<1) for long … mostly static videos." Doc's "0.2–1 FPS for music" is sound guidance. |
| **YT-4** Limit: **public videos only** | **CONFIRMED** | Same doc — "You can only upload public videos." |
| **YT-5** Limit: free tier **≤ 8 hours** YouTube/day | **CONFIRMED** | Same doc — "you can't upload more than 8 hours of YouTube video per day" (free tier). |
| **YT-6** Limit: **10 videos/request** on 2.5+, 1 on older; prefer 1 | **CONFIRMED** | Same doc — "Gemini 2.5 and later models, you can upload a maximum of 10 videos." |
| **YT-7** Length: 1M-ctx ≈ 1h video at default res | **CONFIRMED** (doc says "≈2h for 2M-ctx, ≈1h for 1M-ctx" — official doc explicitly states the 1M=1h figure; the 2M=2h is consistent extrapolation) | Same doc — "1M context window can process videos up to 1 hour long" at default resolution. |
| **YT-8** Token cost **~300 tokens/sec** default, ~100/sec low res | **CONFIRMED** | Same doc — "Approximately 300 tokens per second of video" at default resolution. (Low-res ~100/sec is the documented low-media-resolution figure.) |
| **YT-9** Timestamp drift on YouTube-URL Part (5–10 min off / 30-min video, truncates ~17min); downloading+uploading bytes fixes it — issue #1359 | **CONFIRMED** | github.com/googleapis/python-genai/issues/1359 — reporter: timestamps "off by 5-10 minutes," output ends ~17min on 30-min video; transcription text accurate; "downloading the video and uploading it directly eliminates the timestamp drift." The doc's load-bearing caveat is real. |
| **WS-1** Gemini grounding enabled via `Tool(google_search=GoogleSearch())` | **CONFIRMED** | ai.google.dev/gemini-api/docs/google-search — `types.Tool(google_search=types.GoogleSearch())` passed in `GenerateContentConfig(tools=[...])`. Both forms in the doc (the `{"google_search": {}}` raw dict and the typed class) are valid. |
| **WS-2** Response has `groundingMetadata` with `groundingChunks` + `groundingSupports` | **CONFIRMED** | Same doc — `groundingMetadata` fields: `webSearchQueries`, `searchEntryPoint`, `groundingChunks` (objects with `uri`+`title`), `groundingSupports` (link text spans to chunks). |
| **WS-3** Grounding response carries a `url_citation` annotation field | **REFUTED** | Same doc — **there is NO `url_citation` field.** Citations are built manually from `groundingSupports` (segment + `groundingChunkIndices`) → `groundingChunks` (`uri`/`title`). `url_citation` is OpenAI-API terminology, not Gemini. **Correction:** the doc should say "build citations from `groundingSupports`→`groundingChunks` (`uri`,`title`)", not "inline `url_citation` annotations." (Note: the doc's §0/§1 prose elsewhere correctly uses `groundingMetadata`/`groundingChunks`; only the table cell + the `url_citation` mentions are wrong.) |
| **WS-4** Gemini 3: **5,000 grounded prompts/mo free**, then **$14 / 1k queries** (billed per search query model issues, can be >1/prompt); 2.5: per-prompt | **CONFIRMED** | google-search doc + ai.google.dev/gemini-api/docs/pricing + dev-forum thread — Gemini 3: 5,000 free grounded prompts/mo, then $14/1k queries, billed per search query the model executes; Gemini 2.5 billed per prompt. (Vertex differs: 1,500/day free, $35/1k.) |
| **WS-5** Codex CLI ships built-in `web_search`; config key `web_search` with values `disabled`/`cached`/`live`; default `cached` (OpenAI index, not live fetch) | **CONFIRMED** | developers.openai.com/codex/config-reference — top-level `web_search = "disabled" \| "cached" \| "live"`, default `"cached"` (OpenAI-maintained index, no live fetch). Live mode + `allowed_domains` confirmed. |
| **WS-6** `codex mcp add <name> -- <cmd>` adds an MCP STDIO server | **CONFIRMED** | developers.openai.com/codex/cli/reference + /codex/mcp — `codex mcp add <name> -- <COMMAND> [ARGS...]` adds STDIO (and HTTP) servers; `--env KEY=VALUE` supported. Also configurable via `[mcp_servers.<id>]` in config.toml. |
| **WS-7** `--output-schema` flag exists on `codex exec` (JSON schema on output) | **CONFIRMED** | developers.openai.com/codex/cli/reference — `--output-schema` is a real `codex exec` flag that enforces a JSON schema on output. (It is NOT a `codex mcp add` flag — the doc attributes it to exec/output, which is correct.) |
| **WS-8** Tavily auth = bearer token (`tvly-…`); results have `url`,`title`,`content`,`score`,(opt)`raw_content`; top-level optional `answer`; `search_depth` basic/advanced; `include_answer` | **CONFIRMED** | docs.tavily.com/documentation/api-reference/endpoint/search — `bearerAuth` (Authorization: Bearer <key>); result fields `title`,`url`,`content`,`score`,`raw_content`; top-level `answer` when `include_answer` set. `search_depth` enum: `basic`,`advanced` (+ newer `fast`,`ultra-fast`). |
| **WS-9** Tavily cost: basic search = 1 cr, advanced = 2 cr; free tier 1,000 credits/mo, no card | **CONFIRMED** | docs.tavily.com/documentation/api-credits — "basic, fast, ultra-fast: 1 API Credit," "advanced: 2 API Credits." Free Researcher plan = 1,000 credits/mo, no credit card, ongoing. PAYG $0.008/credit. |
| **WS-10** Exa auth = API key header; `results[]` with `url`,`title` + on-request `text`/`highlights`/`summary`; neural/semantic search | **CONFIRMED** | exa.ai/docs/reference/search — auth via `x-api-key` header (bearer also accepted); `results[]` required `title`+`url`, optional `text`/`highlights`/`summary` via `contents`; neural search supported; `type` enum incl. `instant`,`fast`,`auto`,`deep`,`deep-reasoning`. |
| **WS-11** Exa free tier ~1,000 requests/mo (doc says "1,000 credits/mo") | **CONFIRMED (with nuance)** | exa.ai/pricing — "Run up to 1,000 requests per month for free"; new accounts also get **$10 starter credits**. The doc's "1,000 credits/mo" is right in spirit; Exa frames it as **1,000 requests/mo** (+ $10 grant). Minor wording, not an error. |
| **WS-12** Skipped-providers facts (Brave free tier killed Feb 2026; SerpAPI slow/expensive; Perplexity = answer-LLM not retrieval) | **UNCERTAIN / not re-verified** | Not independently fact-checked this pass (non-load-bearing — these are "skip" rationales). Brave-tier-kill and Perplexity-is-an-answer-LLM are plausible and widely reported; treat as soft until needed. |
| **RAG-1** DJ-knowledge KB should embed with **Gemini text-embedding, NOT CLAP** (CLAP is audio-domain; text knowledge is a different modality; doesn't violate the CLAP-for-audio decision) | **CONFIRMED (reasoning sound)** | This is an architecture judgment, not a single-API claim, and it is **correct**: CLAP (`laion_clap`, 512-dim) is an audio/text-into-audio-space contrastive model tuned for audio similarity; a *text* knowledge KB (DJ how-to prose) is best served by a text embedding model. Project's own decision log scopes "CLAP is the engine" to **track/audio similarity** only (MEMORY.md), so using Gemini text-embedding for a text KB does not contradict it. Gemini text-embedding is already wired (`library/embed.py` pre-CLAP path). The mean-centering note carries over correctly. No API-signature claim to refute here. |

---

## Corrections to apply (the only real errors)

1. **`agent-web-search-tools.md` — `url_citation` is wrong (REFUTED, WS-3).** Gemini grounding does **not**
   return a `url_citation` annotation. Replace mentions (TL;DR §0, table row, §2 "inline `url_citation`
   annotations", §4 "`url_citation` annotations") with the real shape:
   > `groundingMetadata.groundingSupports[]` (each: a text `segment` with `startIndex`/`endIndex` +
   > `groundingChunkIndices`) → resolve into `groundingMetadata.groundingChunks[]` (each: `web.uri`,
   > `web.title`). Build the citation UI by mapping support spans to chunk URIs.

   The doc's central design point ("citations come for free, structured, map text spans to source URLs")
   **remains true** — it's just delivered via `groundingSupports`+`groundingChunks`, not a field literally
   named `url_citation`.

2. **Minor wording (no action required):** Exa free tier is "**1,000 requests/mo** (+ $10 starter credit)",
   not literally "1,000 credits/mo" (WS-11). Tavily *is* literally credit-metered (1,000 credits/mo). Worth
   a one-word tightening if precision matters for budgeting.

Everything else in the three docs that was checked is accurate as written.
