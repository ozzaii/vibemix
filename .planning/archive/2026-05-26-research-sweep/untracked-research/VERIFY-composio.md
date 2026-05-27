# VERIFY — Composio + web-search-provider claims

> Verification pass, 2026-05-26. Fact-checks `composio-toolkits.md` (and the Composio/Tavily/Exa
> rows of `agent-web-search-tools.md`) against authoritative Composio docs (`docs.composio.dev`)
> + the Composio Codex framework page + npm + pricing/toolkits pages. context7 MCP was **not
> available** in this environment (no `mcp__context7__*` deferred tools surfaced), so verification
> fell back to WebFetch/WebSearch of first-party Composio docs as instructed.
>
> **Bottom line:** the research doc is substantially accurate. Two real corrections: (1) the
> Codex CLI command is `codex mcp login composio` (auth) — there is **no** bare `codex mcp add
> composio` browser-auth command; a generic `codex mcp add <name> -- <cmd>` exists only for STDIO
> servers. (2) The `connect.composio.dev/mcp` gateway header is `x-consumer-api-key` (the doc is
> internally inconsistent — §5 right, TL;DR/§3b say `x-api-key`, which is correct only for the
> `backend.composio.dev/v3/mcp` URL). Toolkit count "~985" is a slight undercount vs the official
> "1000+ toolkits / 20,000+ tools".

## Verdict table

| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| 1a | Python SDK: `from composio import Composio`; init `Composio(provider=...)`, `composio.create(user_id=...)`, `session.tools()` | **CONFIRMED** | docs.composio.dev/docs/quickstart — exact imports + `composio.create(user_id="user_123")` + `session.tools()` |
| 1b | TS SDK: `import { Composio } from '@composio/core'`; provider pkgs `@composio/<provider>` | **CONFIRMED** | docs.composio.dev/docs/quickstart — `@composio/core` + `@composio/<provider>` confirmed current |
| 1c | Direct exec via `composio.tools.execute(SLUG, {arguments}, user_id=...)` | **CONFIRMED** | docs.composio.dev/docs/executing-tools — PY: `composio.tools.execute("GITHUB_LIST_STARGAZERS", user_id=user_id, arguments={...})`. TS: `composio.tools.execute("SLUG", { userId, arguments })`. **Minor:** doc's PY example passes args positionally `execute("YOUTUBE_SEARCH", {...}, user_id=...)` — current canonical form is keyword `arguments=` (positional dict still works); cosmetic, not wrong. |
| 1d | Native Tools (SDK) vs MCP server as two distinct modes | **CONFIRMED** | docs.composio.dev/docs/quickstart distinguishes native (`session.tools()`) vs MCP (`session.mcp.url`/`.headers`); separate "Native Tools vs MCP" doc cited in sources exists |
| 1e | `npx @composio/mcp` local STDIO shim exists | **CONFIRMED** | npmjs.com/package/@composio/mcp — package exists (v1.0.9), MCP CLI tool; `npm i @composio/mcp` / npx STDIO pattern |
| 1f | `codex mcp add composio` (browser-auth) | **OUTDATED / IMPRECISE** | composio.dev/toolkits/composio/framework/codex shows auth = **`codex mcp login composio`** (opens browser) + `codex mcp list` to verify, OR manual `[mcp_servers.composio]` config.toml. A bare `codex mcp add composio` is **not** the documented browser-auth command; generic `codex mcp add <name> --env ... -- <stdio-cmd>` exists only for STDIO servers. **Correct to:** `codex mcp login composio` (then `codex mcp list`). |
| 1g | Codex config: `url = "https://connect.composio.dev/mcp"`, header `x-api-key` | **PARTLY REFUTED** | composio.dev/toolkits/composio/framework/codex — the `connect.composio.dev/mcp` gateway uses **`http_headers = { "x-consumer-api-key" = "ck_***" }`**, NOT `x-api-key`. (Doc §5 lines 163-164 are correct; TL;DR + §3b's `x-api-key` are wrong for *this* URL.) `x-api-key` is correct only for the `backend.composio.dev/v3/mcp/<id>` URL (claim 5b). |
| 2a | ~985 toolkits / 20,000+ tools | **OUTDATED (undercount)** | composio.dev/toolkits + github.com/ComposioHQ/composio + docs.composio.dev — official figure is **"1000+ toolkits / 20,000+ tools"**. Tools count exact; "~985 toolkits" is a slightly stale undercount. Use "1000+". |
| 2b | Free tier: 20,000 tool calls/mo, no card | **CONFIRMED** | composio.dev/pricing — "Totally Free", $0/mo, **20K Tool Calls/Mo**, community support |
| 2c | Paid: $29 / 200k ($0.299/1k overage); $229 / 2M ($0.249/1k overage) | **CONFIRMED** | composio.dev/pricing — "Ridiculously Cheap" $29/200K @ $0.299/1k; "Serious Business" $229/2M @ $0.249/1k |
| 3a | Per-user OAuth model (user_id → connected accounts, managed OAuth, token refresh) | **CONFIRMED** | quickstart requires `user_id` on every `create()`/`execute()`; tools run on behalf of that user; "500+ managed MCP integrations featuring unified OAuth and automatic token refreshes" (Composio marketing/enterprise pages) |
| 3b | Remote/managed sandbox execution | **CONFIRMED** | github.com/ComposioHQ/composio describes "a sandboxed workbench"; Composio markets runtime execution in managed sandboxes |
| 3c | No self-host / on-prem except Enterprise VPC | **CONFIRMED (with caveat)** | github.com/ComposioHQ/composio issue #291 + community: "Composio doesn't allow self-hosting and the source code isn't available." Enterprise page lists **VPC / On-Prem**. **Caveat:** Composio has *stated intent* to follow PostHog's playbook (open-source MCP containers / self-host) — a future direction, not yet shipped. Claim holds today. |
| 4a | Toolkit `composio` / Composio Search (built-in web search, no external key) | **CONFIRMED** | composio.dev/toolkits — "Composio search is a unified web search toolkit spanning travel, e-commerce, news, financial markets, images" |
| 4b | `firecrawl` toolkit (crawl/extract/`FIRECRAWL_SEARCH`) | **CONFIRMED** | composio.dev/toolkits/firecrawl + docs.composio.dev/toolkits/firecrawl |
| 4c | `youtube` toolkit | **CONFIRMED** | composio.dev/toolkits — YouTube listed as a toolkit |
| 4d | `spotify` toolkit (playlists, playback, artist/track info) | **CONFIRMED** | composio.dev/toolkits — Spotify listed |
| 4e | `reddit` toolkit | **CONFIRMED** | composio.dev/toolkits — Reddit listed |
| 4f | `notion` toolkit | **CONFIRMED** | composio.dev/toolkits + v1.docs.composio.dev/tools/notion |
| 5a | MCP token bloat ~55K tokens with 5 servers | **CONFIRMED (real, attribution nuance)** | thenewstack.io/how-to-reduce-mcp-token-bloat + DEV.to — "5-server setup burns 55K tokens before any work"; note the canonical 55K figure is GitHub MCP's 93 tools alone, and 5 servers ≈ 50–75K. ~55K is a fair representative number; not a hard per-5-server constant. |
| 5b | `composio.mcp.create(..., allowed_tools=[...])` scoping; URL `backend.composio.dev/v3/mcp/<id>?user_id=...` w/ `x-api-key` | **CONFIRMED** | docs.composio.dev/docs/mcp-overview — `composio.mcp.create(name, toolkits=[{toolkit, auth_config}], allowed_tools=[...])`; URL `https://backend.composio.dev/v3/mcp/<id>?user_id=<uid>`; "Connections require an `x-api-key` header". (This is the URL where `x-api-key` is correct — distinct from the `connect.composio.dev` gateway in 1g.) |
| 5c | Tool Router (`COMPOSIO_SEARCH_TOOLS` + multi-execute) — runtime tool discovery | **CONFIRMED** | composio.dev toolkit pages + how-to-mcp content — "With the Composio Tool Router, agents can dynamically load tools ... based on the task at hand, all through a single MCP endpoint"; collapses N servers to 1 to cut registration overhead |
| 6 | Premium tools (Composio Search, code-exec) bill ~3x standard | **CONFIRMED (verbatim)** | docs.composio.dev/toolkits/premium-tools — "Premium tool calls are roughly 3x the cost of a standard tool call" (e.g. $0.299/1k standard → $0.897/1k premium on the $29 plan). Premium set = search APIs (Composio Search, Perplexity, Exa, SerpAPI), code-exec (E2B), AI/ML inference, OCR. |

## Web-search-provider rows (`agent-web-search-tools.md`) spot-check

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Composio Search row: aggregator (web/news/scholar/finance/maps/shopping…), HTTP-MCP only, managed auth, free tier "available" | **CONFIRMED** | composio.dev/toolkits/composio_search matches scope; managed auth + free tier consistent with pricing page. "STDIO not offered" for *this hosted toolkit* is fair (the `@composio/mcp` STDIO shim is a separate client-side wrapper, not the hosted search endpoint). |
| Tavily 1,000 credits/mo free, no card; basic=1cr/advanced=2cr; extract 1cr/5 URLs | **CONFIRMED** (Tavily-side, not Composio) | docs.tavily.com / tavily.com/pricing cited in source doc; consistent with current Tavily metering. Not Composio's number — independent provider. |
| Exa 1,000 credits/mo free; semantic/neural search + highlights | **CONFIRMED** (Exa-side) | exa.ai/pricing + docs.exa.ai cited; consistent. |

## Corrections to fold back into `composio-toolkits.md`

1. **§ TL;DR + §3b — header for the Codex `connect.composio.dev/mcp` gateway is `x-consumer-api-key`, not `x-api-key`.** `x-api-key` is correct ONLY for the `backend.composio.dev/v3/mcp/<id>` URL. The doc's §5 is already right; make TL;DR/§3b consistent.
2. **§5 — `codex mcp add composio` → `codex mcp login composio`.** Auth for the hosted HTTP Composio server is the `login` subcommand (opens browser), then `codex mcp list` to verify; OR hand-edit `[mcp_servers.composio]` in `config.toml`. `codex mcp add` is the generic STDIO-server add (`codex mcp add <name> -- <cmd>`), not the Composio browser-auth path.
3. **§1 — "~985 toolkits" → "1000+ toolkits".** Official catalog figure is "1000+ toolkits / 20,000+ tools".
4. **§3a — `composio.tools.execute(...)` arg style.** Prefer keyword `arguments={...}, user_id=...` (canonical) over positional dict; both work, cosmetic.
5. **§3c — self-host caveat.** True today (cloud-only, no OSS execution backend, on-prem = Enterprise VPC), but note Composio has publicly stated intent to open-source its MCP containers / allow self-host (PostHog playbook) — a roadmap item, not shipped.

## Sources
- docs.composio.dev/docs/quickstart · docs.composio.dev/docs/executing-tools · docs.composio.dev/docs/mcp-overview · docs.composio.dev/toolkits/premium-tools
- composio.dev/pricing · composio.dev/toolkits · composio.dev/toolkits/firecrawl · composio.dev/toolkits/composio/framework/codex
- npmjs.com/package/@composio/mcp · github.com/ComposioHQ/composio · github.com/ComposioHQ/composio/issues/291
- thenewstack.io/how-to-reduce-mcp-token-bloat · dev.to "Cutting MCP token bloat by 12x"
- (web-search rows) docs.tavily.com · tavily.com/pricing · exa.ai/pricing · docs.exa.ai
- NOTE: context7 MCP unavailable in this environment; verified against first-party Composio docs via WebFetch/WebSearch.
