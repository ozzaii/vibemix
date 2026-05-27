# Agent Web Search Tools — Deep Research & Comparison

> **Date:** 2026-05-26
> **Goal:** Give the Viber agent live web search / web research as a *grounded* tool.
> **Architecture target:** Codex (ChatGPT-sub) + an MCP STDIO server is the primary agent
> backend; Gemini built-in Google Search grounding is the fallback path. The agent borrows
> the "Hermes architecture" idea — it pulls Hermes's **MCP/plug translation layer + agent
> brain pattern** (NOT Hermes itself) so a new tool can be added without rebuilding the engine.
> **Scope guard:** This is a *grounded research tool*, not an open agentic browser. Every result
> must obey vibemix Invariant #2 (citation grounding) and #3 (trust the audio) — web facts are
> citable evidence, never invented; un-citeable claims strip to fallback.

---

## 0. TL;DR Recommendation

- **Primary engine: Tavily** (`/search` + `/extract`). RAG-native, returns LLM-ready chunked
  content + per-result `score` + optional `answer`, generous free tier (1,000 credits/mo, no
  card), trivial bearer-token auth, predictable per-credit cost. It is purpose-built to be
  wrapped as a single MCP tool with bounded output. This is the `web_search` engine.
- **Secondary / semantic engine: Exa** (`/search` with `contents`). Neural/semantic search +
  query-dependent **highlights** (extracted relevant passages, not full pages) → fits 4-5× more
  sources per token budget. Best when the query is conceptual ("tracks that sound like X /
  artists in the Y scene") rather than keyword. Use for `find_web` / similarity-flavored lookups.
- **`fetch_url` engine: Tavily Extract** (or Exa `/contents`) — clean markdown of a specific URL.
- **Codex path:** Codex CLI already ships a **first-party web search tool** (`web_search`,
  cached by default, `web_search = "live"` for fresh). For most "just look it up" needs this is
  free with the ChatGPT sub and needs *zero* extra infra. The custom MCP `web_search`/`fetch_url`
  tools exist for (a) deterministic grounding/caps, (b) provider control, (c) parity with the
  Gemini fallback path. Expose them via the **existing `library/mcp_server.py` STDIO server** —
  no new server.
- **Gemini fallback path:** Use **Gemini's built-in Google Search grounding** (`google_search`
  tool on `generateContent`). It returns synthesized text + `groundingMetadata` with inline
  `url_citation` annotations — citations come for free, perfectly matching Invariant #2. This is
  the fallback because Bravoh is Gemini-only and the agent already has a Gemini backend.
- **Skip for v1:** Composio search toolkit (great breadth, but it's an HTTP-MCP aggregator that
  adds a vendor + auth-broker dependency you don't need for one tool), Brave (free tier killed
  Feb 2026 — metered-only now), SerpAPI (expensive, slow P99 ~5s, credits expire), Perplexity
  Sonar (it's an *answer LLM*, not a retrieval tool — wrong layer; you already have a brain).

---

## 1. Provider Comparison Table

| Provider | What it is | Output shape | Citations | Free tier | Paid cost | Auth | Latency | MCP fit |
|---|---|---|---|---|---|---|---|---|
| **Tavily** (`/search`,`/extract`) | RAG-native search+extract for agents | Structured JSON: `results[]` each with `url`,`title`,`content` (LLM-chunked snippet), `score` (0-1 relevance), optional `raw_content`; top-level optional `answer` string | Yes — every result carries source `url`+`title`; `answer` is grounded in those results | **1,000 credits/mo, no card** | $0.008/credit PAYG; **basic search=1 cr, advanced=2 cr**; extract = 1 cr / 5 URLs (basic), 2 cr / 5 (advanced). Researcher $30/mo, Startup $100/mo | Bearer API key (`tvly-…`) | Sub-second typical (advanced higher); not officially published | **Best.** One endpoint → one MCP tool; output already capped & scored |
| **Exa** (`/search`+`contents`, `/contents`) | Neural/semantic ("embeddings-first") search + crawler | JSON `results[]` with `url`,`title`, and on-request `text` (markdown main-content), `highlights` (query-relevant excerpts), `summary` (abstractive, via Gemini Flash); `statuses[]` for contents | Yes — per-result URL; highlights are traceable passages | **1,000 credits/mo** | **$7/1k req** search-with-contents (≤10 results, text+highlights bundled since Mar 2026); deep $12/1k; deep-reasoning $15/1k; Instant <150ms | Bearer API key | **Instant <150ms**; standard search ~few hundred ms | **Strong.** Highlights = token-cheap grounding; ideal semantic 2nd engine |
| **Composio search** | Aggregator toolkit (22 tools: web=Exa under the hood, news, scholar, finance, maps, shopping…) over MCP/API | "Structured, LLM-friendly schemas"; per-tool shape varies | Per-tool (URLs present) | "Free tier available" (undisclosed credits) | Undisclosed / metered | **Managed** (Composio brokers OAuth/keys; "No Auth" for you) | Adds aggregator hop | **HTTP-MCP only** (STDIO not offered). Adds a vendor + remote endpoint. Overkill for 1 tool |
| **Brave Search** | Independent SERP index + LLM-context endpoint | Standard SERP JSON; structured extraction via LLM Context API | Source URLs in SERP | **Killed for new users Feb 2026** — now $5/mo credits (~1k q). Legacy free users grandfathered | **$5 / 1k req**; up to $30/1k for premium tiers | API subscription token | **<600ms total**, overhead <130ms p90 | OK as raw SERP behind a custom tool, but no RAG-shaping; you'd post-process |
| **SerpAPI** | Scrapes Google/Bing → structured SERP JSON | Rich structured SERP JSON (many engines/verticals) | Source URLs | **Only 66 searches** (tiny) | **$10-25 / 1k**; credits **expire monthly** (no rollover → 30-50% effective inflation) | API key | **avg ~5.4s, high variance** (own bench: 0.73s, but field reports slow) | Poor for live agent: slow tail, costly, raw SERP needs shaping |
| **Perplexity Sonar API** | Search-grounded **answer LLM** (retrieval + generation in one) | LLM answer text + `citations[]` (5-10 URLs, Sonar Pro adds titles/snippets/dates) | **Yes, built-in** in response metadata, no extra fee | Limited credits | Sonar $1/M tok; Pro $3in/$15out per M tok; per-req $5-14/1k high-context; Deep Research adds search+reasoning token fees | Bearer API key | Answer-LLM latency (multi-second) | **Wrong layer.** It's a competing brain, not a retrieval tool. Would nest an LLM inside your agent |
| **Gemini Google Search grounding** | `google_search` tool on `generateContent` | Synthesized answer text + **`groundingMetadata`** with `groundingChunks` + `url_citation` annotations (`start_index`/`end_index`→source URL) | **Yes, inline, structured** — purpose-built for citation UIs | **Gemini 3: 5,000 grounded prompts/mo free**; 2.5: 1,500 RPD free (shared) | **Gemini 3: $14 / 1k queries** (billed per *search query the model issues*, can be >1/prompt); 2.5: $35/1k (per prompt) | Existing `GEMINI_API_KEY` / proxy JWT | Adds a generation round-trip | **Fallback path.** Not an MCP tool — it's a model-side tool. Zero new infra; reuses model_router |

---

## 2. Which fits where — Codex+MCP vs Gemini-grounding

### Codex + MCP STDIO (PRIMARY agent backend)

Facts that shape the choice:
- **Codex CLI ships a built-in `web_search` tool**, on by default in **cached** mode (results from
  an OpenAI-maintained pre-indexed snapshot), `web_search = "live"` for live fetch, `"disabled"`
  to turn off. Live mode can be scoped with `allowed_domains` (prompt-injection defense). For
  ad-hoc "look something up" this is *free with the ChatGPT sub and needs no extra service*.
- **Codex MCP supports STDIO** (`codex mcp add <name> -- <cmd>`, or `[mcp_servers.<name>]` in
  `~/.codex/config.toml` / project `.codex/config.toml`). Tool exposure is allowlist-first:
  `enabled_tools` / `disabled_tools`, `default_tools_approval_mode` (`auto`/`prompt`/`approve`),
  per-tool `tools.<tool>.approval_mode`, and `tool_timeout_sec`.
- vibemix **already has `library/mcp_server.py`** — the STDIO server that exposes the grounded
  toolset to Codex (`--backend codex` path). Adding `web_search`/`fetch_url` there is the natural
  seam: **no new server, no new transport.**

**Decision for the Codex path:**
1. Keep Codex's **built-in `web_search` (cached)** enabled for cheap general lookups — costs
   nothing extra, no infra.
2. Add a **custom `web_search` MCP tool backed by Tavily** when you need: deterministic result
   caps, relevance `score`, a typed contract the *Gemini fallback can mirror exactly*, and
   provider control independent of OpenAI's snapshot. This is the parity tool across backends.
3. Add **`fetch_url` (Tavily Extract / Exa contents)** so the agent can read a specific page on
   demand without an open browser.

Why STDIO over HTTP here: it's a **local single-user desktop app** (vibemix runs on Kaan's Mac,
sidecar of the Tauri shell). STDIO is faster locally (HTTP/SSE adds 30-200ms/call) and you skip
auth/hosting. The MCP security guidance is the warning to respect: *STDIO is a transport, not a
security control* — the tool itself must be least-privilege (no free-form "run anything" dispatch;
fixed search/fetch signatures only).

### Gemini built-in Google Search grounding (FALLBACK path)

- Not an MCP tool — it's a **model-side tool** (`tools=[{google_search:{}}]` on `generateContent`).
  When the agent is on the Gemini backend, you don't wire an MCP web tool at all; you flip the
  `google_search` tool on and read `groundingMetadata`.
- This is the **best citation story of any option**: inline `url_citation` annotations map text
  spans to source URLs — a 1:1 match for vibemix's `EvidenceRegistry` citation grounding gate.
- It's the fallback because Bravoh is Gemini-only, the agent already holds a Gemini backend, and
  it costs nothing in new infrastructure. Cost is the watch-item ($14/1k *search queries* on
  Gemini 3, and the model may issue several per prompt) — but the free 5,000 grounded
  prompts/month easily covers a single-user desktop tool.

### Net: two-lane design

| Lane | Engine | When |
|---|---|---|
| Codex agent, general | Codex built-in `web_search` (cached → live) | Cheap, no infra, "just look it up" |
| Codex agent, grounded/parity | **Tavily** `web_search` + `fetch_url` MCP tools (Exa for semantic) | Deterministic caps, scores, cross-backend parity, provider control |
| Gemini agent (fallback) | **Gemini `google_search` grounding** | No MCP tool; model-side tool + `groundingMetadata` |

The custom MCP tool and the Gemini grounding path expose the **same logical contract** (query →
capped list of `{title, url, snippet}`), so the agent prompt and grounding logic don't fork.

---

## 3. The "Hermes architecture" pattern for tools

The pattern vibemix is borrowing (and which Composio literally documents for "Hermes"): **add a
tool through an MCP/plug translation layer, never by editing the agent engine.**

> Composio's own Hermes integration says it plainly: it adds the search toolkit *"through a Model
> Context Protocol (MCP) translation layer rather than requiring agent engine modifications…
> agents dynamically load tools based on the task at hand, all through a single MCP endpoint…
> Composio avoids modifying Hermes's core engine."* The agent brain handles orchestration; the
> MCP layer supplies tools on demand over a standard protocol.

Mapped onto vibemix:

```
┌─────────────────────────────────────────────────────────────┐
│  AGENT BRAIN (Codex via codex exec  |  Gemini fn-calling)     │  ← unchanged
│  decides WHICH tool, WHEN, with WHAT args                     │
└───────────────┬───────────────────────────────────────────────┘
                │  MCP STDIO (JSON-RPC 2.0)  ← the translation layer
┌───────────────▼───────────────────────────────────────────────┐
│  library/mcp_server.py  (the "plug" surface)                   │
│  existing grounded tools: search_vibe, find_similar, …         │
│  + NEW: web_search, fetch_url   ← drop-in, engine untouched     │
└───────────────┬───────────────────────────────────────────────┘
                │  provider adapter (one file, swappable)
        ┌───────▼────────┐   ┌──────────────┐
        │ Tavily client  │   │ Exa client   │   ← provider behind the tool
        └────────────────┘   └──────────────┘
```

Why this is the right shape:
- **Engine-agnostic.** `toolset.py` is already the *shared grounded tool core* across the Gemini
  and Codex backends (per CLAUDE.md). A new tool registered once is callable from both — exactly
  the Hermes "add without rebuild" property.
- **Provider is a leaf.** Swapping Tavily↔Exa↔Brave is editing one adapter file behind a stable
  tool signature. The brain never knows.
- **Grounding stays at the seam.** The MCP tool is where you enforce vibemix's invariants, so the
  brain *cannot* route around them.

### Agent-tool best practices to bake into the tool (general, then vibemix-specific)

1. **Bounded results.** Hard-cap `max_results` (default 5, ceiling 10) and per-result content
   length (e.g. 1,200 chars). Unbounded output blows the context budget and degrades grounding —
   Exa highlights / Tavily chunked `content` exist precisely to keep this small.
2. **Citation grounding (Invariant #2).** Every returned item MUST carry a real `url`. The tool
   returns *evidence with sources*, never a bare prose answer. Register returned URLs in the
   `EvidenceRegistry`-equivalent so any reaction/playlist note citing a web fact resolves; an
   un-citeable web claim strips to fallback. **Do not** use Perplexity-style "answer LLM" output
   here — it hides the sources behind a generated paragraph and nests a second brain.
4. **No-hang (AIRA checklist, already used by the Telegram bridge).** Wrap every provider call in
   a **wall-clock timeout** (e.g. 8s), make the tool handler **always return** (typed empty result
   on timeout/error, never raise into the agent loop), keep the agent's tool loop **bounded**
   (max tool calls/turn), and emit a heartbeat. A flaky web call must never wedge the in-flight
   gate (mirrors the co-host's single-in-flight rule).
5. **Least-privilege tool surface.** Two narrow tools (`web_search`, `fetch_url`) with fixed typed
   args — **no** "free-form fetch anything / run anything" omnibus tool (the MCP security guidance
   flags omnibus run-time-dispatch tools as the top critical finding). On the Codex side set
   `approval_mode` appropriately and, for live fetch, an `allowed_domains` posture against prompt
   injection.
6. **Privacy.** Scrub query + result text before any logging (vibemix already path-scrubs outbound
   Telegram messages). Web queries can leak set/track context — treat like outbound messages.
7. **Cache + dedupe.** 15-min content-hash cache on `(query, k)` and on fetched URLs (cheap, cuts
   credits, mirrors `embeddings.db` content-hash pattern). Codex's own cached mode is the same idea.

---

## 4. Recommended stack + concrete MCP tool design

### Stack

| Layer | Choice |
|---|---|
| Primary search engine | **Tavily** `/search` (advanced) + `/extract` |
| Semantic search engine (optional 2nd) | **Exa** `/search` with `contents.highlights` |
| Codex general lookup | Codex built-in `web_search` (cached default, `live` opt-in) |
| Gemini fallback | **Gemini `google_search`** grounding + `groundingMetadata` |
| Translation layer | **existing `library/mcp_server.py`** STDIO server (no new server) |
| Provider adapter | new leaf module, e.g. `library/web_search.py`, behind a stable signature |
| Config | `VIBEMIX_TAVILY_API_KEY` (+ optional `VIBEMIX_EXA_API_KEY`); `.env`; fail-closed if absent → tool reports "web search unavailable" actionably (same pattern as `--backend codex` absent) |

### Tool 1 — `web_search`

```jsonc
// MCP tool: web_search — grounded, bounded web retrieval
{
  "name": "web_search",
  "description": "Search the live web for facts about tracks, artists, labels, releases, scenes, gear. Returns a small set of sourced results. Every result carries a URL you MUST cite; never state a web fact without its source.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query":       { "type": "string", "description": "Search query." },
      "max_results": { "type": "integer", "default": 5, "minimum": 1, "maximum": 10 },
      "depth":       { "type": "string", "enum": ["basic","advanced"], "default": "basic" }
    },
    "required": ["query"]
  }
}
```

**Returns** (typed, capped — provider-normalized):
```jsonc
{
  "results": [
    {
      "title":   "string",
      "url":     "string",          // REQUIRED — the citation handle
      "snippet": "string (≤1200 chars, LLM-chunked content)",
      "score":   0.0                // 0-1 relevance (Tavily score; Exa→derived)
    }
  ],
  "truncated": false,               // true if provider had more than max_results
  "source":    "tavily"             // which engine answered (telemetry/grounding)
}
```

**Behavior contract:**
- Provider call wrapped in **8s wall-clock timeout**; on timeout/error return
  `{"results": [], "truncated": false, "source": "<engine>", "error": "<class>"}` — **never raise**.
- Results hard-capped at `max_results` (≤10) and each `snippet` truncated to 1,200 chars.
- Each `url` registered as evidence so downstream citations resolve (Invariant #2).
- 15-min `(query, max_results, depth)` cache.
- Mapping: Tavily `basic`→`search_depth=basic` (1 cr), `advanced`→`search_depth=advanced` (2 cr);
  request `include_answer=false` (we want sourced *results*, not a generated answer — keeps the
  brain singular and the output citeable).

### Tool 2 — `fetch_url`

```jsonc
// MCP tool: fetch_url — read ONE page as clean text (no open browser)
{
  "name": "fetch_url",
  "description": "Fetch a single web page and return its main content as clean markdown. Use only on URLs that came from web_search results or that the user supplied. Cite the URL for any fact you use from it.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "url":          { "type": "string", "format": "uri" },
      "max_chars":    { "type": "integer", "default": 4000, "minimum": 500, "maximum": 12000 }
    },
    "required": ["url"]
  }
}
```

**Returns:**
```jsonc
{
  "url":       "string",
  "title":     "string",
  "content":   "string (markdown, truncated to max_chars)",
  "truncated": false,
  "source":    "tavily-extract"     // or "exa-contents"
}
```

**Behavior contract:**
- Backed by **Tavily Extract** (1 cr / 5 URLs) or **Exa `/contents`** (`text` markdown).
- Same 8s timeout + always-return-empty-on-error rule; 15-min URL content cache.
- Content truncated to `max_chars` (default 4,000).
- **Least-privilege:** only `http(s)`; on the Codex side pair `live` web access with an
  `allowed_domains` posture for prompt-injection safety; refuse non-public/loopback hosts.

### Gemini fallback wiring (no MCP tool)

When the agent runs on the Gemini backend, do **not** register the MCP web tools. Instead pass
`tools=[{ "google_search": {} }]` to `generateContent` (model resolved via `model_router`, never a
literal), then read `candidates[].groundingMetadata` → `groundingChunks` + `url_citation`
annotations and normalize into the **same `{title,url,snippet}` shape** the MCP tool emits. This
keeps the agent prompt and grounding code identical across both backends — the only fork is *who
runs the search*.

### Build order (one tool first, prove grounding, then expand)

1. `library/web_search.py` adapter: Tavily client + timeout + cap + cache + normalize. Pure logic,
   dep-free testable (mock the HTTP) like the Telegram allow-list/leak-strip core.
2. Register `web_search` in `mcp_server.py` (Codex) **and** in `toolset.py` so the Gemini backend
   sees the same tool; add the `google_search` fallback branch.
3. Add `fetch_url` (Tavily Extract).
4. Optional: Exa adapter behind the same `web_search` signature for semantic queries (`source`
   field tells you which answered).
5. CLI smoke: `uv run python -m vibemix library curate "<theme>"` should now ground notes on
   web facts with citations; verify every web claim resolves to a registered URL.

---

## Sources

- [Tavily pricing](https://www.tavily.com/pricing) · [Tavily API credits docs](https://docs.tavily.com/documentation/api-credits) · [Tavily](https://www.tavily.com/)
- [Exa pricing](https://exa.ai/pricing) · [Exa contents retrieval](https://docs.exa.ai/reference/contents-retrieval) · [Exa search API (Morph)](https://www.morphllm.com/exa-search-api)
- [Composio search toolkit](https://composio.dev/toolkits/composio_search) · [Composio search + Hermes integration](https://composio.dev/toolkits/composio_search/framework/hermes-agent) · [Composio (GitHub)](https://github.com/composiohq/composio)
- [Brave Search API](https://brave.com/search/api/) · [Brave kills free tier (Implicator)](https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing/) · [Brave pricing docs](https://api-dashboard.search.brave.com/documentation/pricing)
- [SerpApi pricing](https://serpapi.com/pricing) · [SERP API comparison 2026 (Proxies.sx)](https://www.proxies.sx/blog/cheapest-serp-api-comparison-2026)
- [Perplexity API pricing (AI Pricing Guru)](https://www.aipricing.guru/perplexity-pricing/) · [Sonar quickstart](https://docs.perplexity.ai/docs/sonar/quickstart)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) · [Grounding with Google Search](https://ai.google.dev/gemini-api/docs/google-search)
- [Codex MCP docs](https://developers.openai.com/codex/mcp) · [Codex best practices](https://developers.openai.com/codex/learn/best-practices) · [Codex web search config (Vaughan KB)](https://codex.danielvaughan.com/2026/05/09/codex-cli-web-search-configuration-cached-live-domain-allow-lists-prompt-injection-defence/) · [Codex config reference](https://developers.openai.com/codex/config-reference)
- [MCP server security best practices 2026 (DigitalApplied)](https://www.digitalapplied.com/blog/mcp-server-security-best-practices-2026-engineering-guide)
- [Best web search APIs 2026 (Firecrawl)](https://www.firecrawl.dev/blog/best-web-search-apis)
