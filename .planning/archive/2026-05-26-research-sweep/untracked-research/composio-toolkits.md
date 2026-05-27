# Composio Toolkits — Research for the Viber Agent (Codex + MCP)

> Research doc, 2026-05-26. Goal: give the Viber curator agent MANY more tool capabilities, sourced via Composio (Bravoh already uses Composio). Implementation-oriented; concrete SDK/MCP snippets + a "How it plugs into vibemix's Codex+MCP agent" section at the end.
>
> TL;DR: Composio is a **managed (cloud-only, closed-source) tool-and-auth layer** that exposes 1000+ SaaS toolkits to agents either as (a) framework-native function schemas via Python/TS SDK, or (b) a hosted **MCP server** (HTTP *or* local STDIO via `npx @composio/mcp`). Our Codex agent reaches it the same way it reaches our own MCP STDIO server today — drop a second entry in `~/.codex/config.toml [mcp_servers]`. Free tier = **20k tool calls/mo, no card**. Biggest risks: **no self-host / closed tools**, **MCP token bloat** (load the whole toolkit and you burn ~tens of K tokens before the convo starts), and **lock-in on the auth layer**. Recommended pattern for us: **Tool Router / scoped single-toolkit MCP** (not "load everything"), keep our own grounded library MCP as the source of truth, treat Composio as a *parallel* tool source for web/YouTube/scrape/social.

---

## 1. What Composio IS + architecture

Composio (composio.dev, ComposioHQ) is an **integration + auth platform for AI agents**: it lets an agent "execute actions across 1000+ apps" without the agent (or you) writing per-API glue or handling OAuth/token lifecycle. Marketed as model- and framework-agnostic (Claude, Gemini, OpenAI, LangChain, CrewAI, Vercel AI, OpenAI Agents SDK, Mastra, AutoGen, **Codex CLI**, Claude Code, Cursor…). SOC2 + ISO 27001:2022 certified.

Catalog scale (homepage, May 2026): **~985 toolkits / 20,000+ tools**.

**Architecture pieces:**

- **Toolkit** = a collection of related tools for one service (e.g. `gmail`, `youtube`, `firecrawl`, `spotify`).
- **Tool** = one executable action, named `{TOOLKIT}_{ACTION}` (e.g. `GMAIL_SEND_EMAIL`, `GITHUB_CREATE_ISSUE`, `COMPOSIO_SEARCH_*`).
- **Auth config** (`ac_…`) = reusable per-toolkit credential template (managed OAuth app, or your own client_id/secret, or API key/Bearer/Basic). Create once in dashboard or programmatically; reuse across all users.
- **Connected account** (`ca_…`) = a specific user's authorized link to a toolkit, keyed by your `user_id`.
- **Managed sandboxes**: tools run in remote ephemeral sandboxes; large responses land on a remote filesystem; multi-step workflows can be composed as code; sessions keep state (sandbox + progress).
- **Tool Router** = runtime tool discovery — instead of statically wiring N tools into the prompt, the agent calls `COMPOSIO_SEARCH_TOOLS` to find the right tool at runtime, then `COMPOSIO_MULTI_EXECUTE_TOOL` to run discovered tools in parallel. This is their answer to MCP token bloat.
- **MCP server (hosted)** = Composio wraps any toolkit selection as an MCP endpoint (`https://backend.composio.dev/v3/mcp/<id>` or `https://connect.composio.dev/mcp`). Also a **local STDIO** shim via `npx @composio/mcp`.

Two distinct deployment modes that matter for us — **Native Tools (SDK)** vs **MCP** — covered in §3.

---

## 2. TOOLKITS catalog — categories + the DJ-relevant ones

**23 categories**, incl: Developer Tools & DevOps · Collaboration & Communication · AI & Machine Learning · Document & File Management · Productivity & Project Mgmt · CRM/Analytics/Data · Design & Creative · Marketing & Social Media · E-commerce/Finance/Accounting · HR & Recruiting.

**Directly relevant to a DJ / music-curation agent (Viber):**

| Need | Toolkit(s) | Notes |
|------|-----------|-------|
| **Web search (no 3rd-party key)** | **`composio` / Composio Search** | Built-in unified web search (travel, e-commerce, news, financial, images, etc.) — *no external API key needed*. Counts as a **premium** tool call (3x rate, see §4). |
| Web search (BYO) | `tavily`, `exa`, `brave_search` (Brave Search API), `serpapi`, `parallel_ai` | Agent/RAG-grade search APIs; you supply the provider key via an auth config. Exa = semantic/embedding search — interesting for "find tracks like X discourse". |
| **Browser / scraping** | **`firecrawl`** | Crawl a site, get crawl status, cancel job, list active jobs, extract structured data, **`FIRECRAWL_SEARCH`** (search + scrape top results). Best fit for "scrape a label's release page / a Beatport chart / an event lineup". |
| Browser automation | Browserbase / browser-use type toolkits exist in the AI/ML + dev categories | For full headless-browser flows if Firecrawl extraction isn't enough. |
| **YouTube** | **`youtube`** | Search/discover videos, channel + video metadata. Strong fit: resolve a track to its YT, pull set/track IDs, enrich library, find live-set references. |
| **Spotify** | **`spotify`** | Rich: get currently-playing, get/create/modify playlists, add to playlist, add to playback queue, get artist/album/track info, follow artists/playlists, check follows. Direct fit for **export a Viber set to a Spotify playlist** + audio-feature enrichment. |
| **Reddit** | `reddit` | Search across subreddits (posts/comments/topics), create text/link posts w/ flair. Use for r/DJs, r/hardtechno crowd-sourced track IDs / discovery. |
| Social / posting | `twitter` (X), `linkedin`, `discord`, `slack` | Announce sets, share playlists, community posting. |
| **File / docs / RAG** | `google_drive`, `google_docs`, `google_sheets`, `notion`, `airtable`, `supabase`, S3 (`COMPOSIO_DOWNLOAD_S3_FILE`) | Persist setlists, notes, crate planning. Notion/Sheets = natural "set planner" surface. |
| Email / calendar | `gmail`, `outlook`, `google_calendar`, `calendly` | "Email me the setlist", "block prep time before the gig". |
| Code execution | `codeinterpreter` (Python sandbox) | Premium tool; could run DSP/analysis snippets in-sandbox (we already have local DSP — low priority). |

For Viber specifically the high-value cluster is: **Composio Search + Firecrawl + YouTube + Spotify + (Reddit/Twitter)**. Everything else is optional polish.

Full live catalog: https://composio.dev/toolkits — per-toolkit tool lists at `https://docs.composio.dev/toolkits/<name>` (e.g. `/spotify`, `/youtube`, `/firecrawl`, `/reddit`).

---

## 3. HOW to wire Composio into an agent

Two integration surfaces. Pick per use-case; you can mix.

### 3a. Native Tools (Python/TS SDK) — fine-grained, you control context

You ask the SDK for tool *schemas* formatted for your framework/provider, inject only the ones you want, and the SDK executes the calls. Best when you care about token budget and want logging/retry/approval hooks.

```python
# pip install composio composio_openai   (provider packages: composio_openai, composio_gemini, composio_langchain, …)
from composio import Composio
from composio_openai import OpenAIProvider

composio = Composio(api_key="ck_…", provider=OpenAIProvider())
session = composio.create(user_id="user_123")
tools = session.tools()          # provider-formatted tool schemas → feed to the LLM

# …LLM returns a tool call; execute it directly:
result = composio.tools.execute(
    "YOUTUBE_SEARCH",
    {"query": "amelie lens boiler room tracklist"},
    user_id="user_123",
)
```

```typescript
import { Composio } from '@composio/core';
import { OpenAIProvider } from '@composio/openai';
const composio = new Composio({ apiKey: process.env.COMPOSIO_API_KEY, provider: new OpenAIProvider() });
const session = await composio.create("user_123");
const tools = await session.tools();
const res = await composio.tools.execute("YOUTUBE_SEARCH", { userId: "user_123", arguments: { query: "…" } });
```

### 3b. MCP server — framework-agnostic, just a URL + headers (or a STDIO command)

Composio hosts your toolkit selection as an MCP endpoint; any MCP client (Claude, OpenAI Responses, **Codex**, Cursor, Claude Code) connects with a URL + header. **Trade-off**: the client typically loads *all* exposed tools → token cost (their own docs cite **~55K tokens before the conversation starts with 5 servers**). Use Tool Router or scope tightly.

**Create + scope a server (SDK):**
```python
server = composio.mcp.create(
    name="viber-tools",
    toolkits=[{"toolkit": "youtube", "auth_config": "ac_xyz"},
              {"toolkit": "firecrawl", "auth_config": "ac_abc"}],
    allowed_tools=["YOUTUBE_SEARCH", "FIRECRAWL_SEARCH", "FIRECRAWL_EXTRACT"],  # scope = fewer tokens
)
# per-user URL:
inst = composio.mcp.generate(user_id="user-123", mcp_config_id=server.id)
print(inst["url"])   # https://backend.composio.dev/v3/mcp/<server_id>?user_id=user-123
```

**Hosted HTTP transport — pass to any MCP client:**
```python
mcp_server_url = "https://backend.composio.dev/v3/mcp/<server_id>?user_id=user-123"
mcp_headers   = {"x-api-key": "ck_…"}      # or x-consumer-api-key on connect.composio.dev
```

**Local STDIO transport** (same shape as our own MCP server):
```jsonc
// e.g. Claude Desktop / generic MCP client config
{ "command": "npx", "args": ["-y", "@composio/mcp"], "env": { "COMPOSIO_API_KEY": "ck_…" } }
// or: npx @composio/mcp@latest setup  → generates a per-client config with a unique URL
```

### Auth model

- **Per-user** by design. A `user_id` groups a user's connected accounts; Composio stores/refreshes that user's tokens. Tools execute "on behalf of" that user.
- **Managed OAuth**: for popular toolkits (Gmail/GitHub/Slack/etc.) Composio ships a managed OAuth app → zero setup, works out of the box. For production scale you can swap in **your own** client_id/secret (custom auth config) for scope control + branding.
- **API-key / Bearer / Basic** toolkits (e.g. Firecrawl, Tavily) → store the key in an auth config; no user OAuth dance.
- **Connection flow** (OAuth toolkit): `connected_accounts.link(user_id, auth_config_id, callback_url)` → redirect user to `redirect_url` → callback returns `?status=success&connected_account_id=ca_…` → poll `wait_for_connection(timeout)` until `ACTIVE` → then `tools.execute(...)`. (Old `initiate()` is being phased out for `link()`.)
- **Composio's own API key** authenticates *you* to Composio (`ck_…`), separate from the per-user toolkit creds.

### Self-hosted vs cloud

**Cloud only. Composio is NOT open source and has NO self-host / on-prem (except Enterprise VPC).** Tools are closed-source — you can't inspect or modify a tool's code; if one misbehaves you rebuild it yourself outside Composio. (There *is* an open `ComposioHQ/composio` SDK repo + a `composio-fastapi` example, but the execution/integration backend is hosted.)

---

## 4. Pricing / rate limits / free tier

Usage-based, metered in **tool calls/month** (composio.dev/pricing):

| Plan | $/mo | Tool calls/mo | Overage | Support |
|------|------|---------------|---------|---------|
| Free | $0 (no card) | **20,000** | — | community |
| Hobby ("Ridiculously Cheap") | $29 | 200,000 | $0.299 / 1k | email |
| Team ("Serious Business") | $229 | 2,000,000 | $0.249 / 1k | Slack |
| Enterprise | custom | custom | custom | SLA, SOC-2, **VPC / on-prem** |

**Watch-out: premium tools** (semantic/Composio Search, code execution) bill at **~3x** the standard rate → cost less predictable at scale. Each `COMPOSIO_SEARCH`, `CODEINTERPRETER`, etc. call is a premium call.

For Viber at our volume (a curator agent fired by a user building a set, not a high-QPS pipeline) **20k free calls/mo is plenty** for initial integration; one curate session = maybe 5–30 tool calls.

---

## 5. How it plugs into vibemix's Codex + MCP STDIO agent  ← key section

**Current Viber arch (vibemix):** `library/agent.py` / `codex_curate.py` drive reasoning via Codex (`codex exec`, BYO ChatGPT-sub); `library/mcp_server.py` is a **STDIO MCP server** exposing our grounded tools (`search_vibe` / `discover_pool` / `sequence_set` / `export_set`) over the user's *local* DJ library. Grounding (seen-set + library re-validation) lives in `toolset.py`, shared with the Gemini backend. Codex finds our MCP server via `~/.codex/config.toml [mcp_servers]`.

**Composio integrates as a SECOND MCP server in the exact same place — no architecture change.** Confirmed Codex path (Composio's own Codex docs):

```bash
codex mcp add composio          # browser-auth to your Composio account
codex mcp list                  # verify
```
produces in `~/.codex/config.toml`:
```toml
[mcp_servers.composio]
url = "https://connect.composio.dev/mcp"
http_headers = { "x-consumer-api-key" = "ck_*******" }
```
Codex (which uses HTTP/streamable MCP) talks to Composio's hosted gateway; we keep our local STDIO server alongside:
```toml
[mcp_servers.vibemix_library]    # our existing grounded server (STDIO)
command = "uv"
args = ["run", "python", "-m", "vibemix", "library", "mcp"]
```
So the Codex agent sees **both** tool namespaces in one session: `vibemix_library__*` (grounded, local, authoritative) + Composio's tools (web/YouTube/scrape/social). That's the "parallel tool source" model. We don't have to re-expose Composio tools through *our* MCP server — Codex multiplexes multiple MCP servers natively.

**Two viable wiring patterns:**

1. **Direct multiplex (simplest).** Add the `[mcp_servers.composio]` entry as above (or a scoped per-toolkit server via `composio.mcp.create(... allowed_tools=[...])` to cut token bloat). The Codex agent calls Composio tools directly. Downside: Composio tools are **ungrounded** by our seen-set/library-revalidation invariants — they can return arbitrary web data. **Mitigation:** prompt-scope which tools the agent may call, and keep `export_set` etc. flowing only through *our* validated toolset so the final playlist is still library-grounded.

2. **Wrap-and-ground (cleaner, more work).** Don't expose Composio to Codex directly. Instead call Composio from inside `toolset.py` via the **Python SDK** (`composio.tools.execute("YOUTUBE_SEARCH", …, user_id=…)`), then surface a *new grounded tool* (e.g. `enrich_track_youtube`, `discover_web`) through our existing STDIO `mcp_server.py`. This keeps Invariant #2/#3 discipline (every external result re-validated against the real library before it can enter a set) and keeps one tool surface. Recommended for anything that feeds the actual setlist; pattern 1 is fine for read-only enrichment/lookup.

**Highest-leverage first tools for Viber:** `COMPOSIO_SEARCH` (web, no key) + `YOUTUBE_SEARCH` (track→video/ID enrichment, set-reference discovery) + `FIRECRAWL_SEARCH/EXTRACT` (scrape charts/label pages/lineups) + `SPOTIFY_*` (export set to Spotify playlist; audio-feature enrichment). Reddit/Twitter = phase 2.

**Bravoh synergy:** Bravoh already uses Composio → we likely already have an org API key + auth-config patterns to reuse, and the per-user `user_id` model maps onto vibemix users cleanly.

---

## 6. Gotchas / ToS / lock-in risk

- **MCP token bloat is real.** Loading a full toolkit (or 5 servers) into an MCP client can burn tens of K tokens before the user says anything (their docs: ~55K w/ 5 servers); one comparison cites a raw-passthrough query using 373% of a 200K window vs 3.7% for intent-level tooling. **→ Always scope `allowed_tools`, or use Tool Router (`COMPOSIO_SEARCH_TOOLS` + `MULTI_EXECUTE`) so tools are discovered at runtime, not preloaded.**
- **No grounding by default.** Composio tools return live web/SaaS data — directly opposite to vibemix Invariant #3 ("trust the audio / never invent"). Any path that reaches the setlist MUST be re-validated against the real library (pattern 2 above). Treat Composio output as untrusted input.
- **Closed-source, no self-host, no tool extensibility.** Can't inspect/modify a tool; if it breaks you rebuild outside Composio. On-prem only at Enterprise (VPC). **Lock-in concentrates on the auth/connection layer** — migrating off means re-implementing OAuth/token storage for every toolkit (Nango is the commonly-cited open alternative if we ever want to self-host auth).
- **Observability is shallow.** Basic debug info; no custom log injection, no full request/response inspection, no OpenTelemetry export → production failures need guesswork.
- **Default logging can expose payloads** — request/response bodies may be logged. For our privacy posture, **never route Kaan's private/local-AI data through Composio**, and audit logging config before sending any user content.
- **Premium-call cost spikes** — search/code-exec at 3x; bound worst-case with the same SessionMeter/cost-guardrail discipline as the Gemini key (this is already a launch gate for vibemix).
- **Multi-tenant governance is thin** — fine for our single-user-per-session model; if vibemix ever needs per-user distinct access controls + audit trails, that layer is on us.
- **Codex transport is HTTP**, our existing server is STDIO — both coexist fine in `config.toml`; just don't assume Composio's hosted server runs STDIO (the `npx @composio/mcp` STDIO shim exists but the Codex-documented path is the hosted HTTP URL).

---

## Sources

- https://composio.dev/  ·  https://composio.dev/toolkits  ·  https://composio.dev/pricing
- https://docs.composio.dev/docs/mcp-overview  ·  https://docs.composio.dev/docs/mcp-quickstart  ·  https://docs.composio.dev/docs/native-tools-vs-mcp
- https://docs.composio.dev/docs/authenticating-tools  ·  https://docs.composio.dev/docs/auth-configuration/custom-auth-configs  ·  https://docs.composio.dev/docs/custom-app-vs-managed-app
- https://docs.composio.dev/docs/tools-and-toolkits  ·  https://docs.composio.dev/toolkits/premium-tools
- https://composio.dev/toolkits/composio (Composio Search / Tool Router) · https://docs.composio.dev/toolkits/firecrawl · https://docs.composio.dev/toolkits/spotify · https://docs.composio.dev/toolkits/reddit
- https://composio.dev/toolkits/firecrawl/framework/codex (Codex CLI MCP setup) · https://composio.dev/content/how-to-mcp-with-codex
- https://www.npmjs.com/package/@composio/mcp (STDIO shim)
- https://composio.dev/content/9-top-ai-search-engine-tools (Exa/Tavily/Brave/SerpApi)
- https://nango.dev/blog/composio-alternatives/ (lock-in / no-self-host critique) · https://agenticcontrolplane.com/blog/mcp-gateway-comparison · https://thenewstack.io/how-to-reduce-mcp-token-bloat/
- https://github.com/ComposioHQ/composio · https://github.com/ComposioHQ/composio-fastapi
