# Bravoh Reusable Capabilities — Audit for the Viber Agent

**Date:** 2026-05-26
**Auditor:** read-only research pass (no writes, no service touches)
**Source of truth:** remote live backend `ssh altidus:/var/www/bravoh-backend/` (deploy SHA `e455996a`, Apr 27 2026 — newer than the local `/Users/ozai/projects/bravoh` checkout which is Mar 30, and newer in app-surface than `bravoh-server-pull` which lacked `app/api/composio/`). All paths below are on the remote box unless noted.
**Lift target in vibemix:** `src/vibemix/library/{toolset.py, agent.py, mcp_server.py, codex_curate.py, telegram_bridge.py}` — the Viber agent. Bravoh's whole companion is a Gemini function-calling agent over a `BravoTool` registry; vibemix's Viber is the same shape (typed tools + grounding seen-set), so the lift is "copy the pattern, swap the domain tools".

---

## TL;DR — what's reusable, ranked by lift value

| Capability | Bravoh source | Lift difficulty | Why it matters for Viber |
|---|---|---|---|
| **YouTube → Gemini native** (zero-download, just a URL) | `services/ai/audio_session.py:787-808` | **Trivial** | Let Viber "watch/hear" a YouTube reference track the DJ names, then recommend from the library. |
| **Quote-a-moment engine** (`[[track:stem:start-end:Label]]`) | `services/ai/audio_map.py:486+`, `api/companion/ws_quote_cache.py` | **Medium** | The killer feature — Viber cites a *cue point* ("enter on the breakdown at 1:04") as a playable clip, grounded. Maps onto our `cue_types.py` / CueAnchor seam. |
| **Web search tool** (Brave + Gemini synth + citations) | `services/ai/tools/web_search.py` | **Trivial** | Drop-in `BravoTool`-shaped tool; Viber can answer "what's trending in hardtechno". |
| **Google Search grounding** (native `Tool(google_search=...)`) | `services/ai/gemini_client.py:1651-1780`, `services/ai/grounding.py` | **Trivial** | Real-time grounding with `grounding_chunks` (source URI+title) extraction. |
| **Agent/tool architecture** (`BravoTool` ABC + `ToolRegistry` + per-turn dynamic tools) | `services/ai/tool_registry.py` | **Reference** | The exact pattern to mirror for Codex+MCP Viber. Already 90% present in our `toolset.py`/`mcp_server.py`. |
| **Composio** (9 toolkits, OAuth, dynamic tool bridge) | `services/composio/client.py`, `api/composio/routes.py` | **Heavy / probably skip for v1** | OAuth + per-artist connected accounts. Overkill for a local DJ utility; lift only if Viber needs to post to socials. |
| **MCP dynamic registration** (load MCP tools per turn into the same registry) | `services/ai/agentic_engine.py:2330-2360` | **Reference** | Proves the Codex+MCP path: MCP tools get `register_dynamic()`'d into the same Gemini tool surface alongside native tools. |

---

## 1. YouTube ingestion — Gemini watches/hears YouTube from a bare URL

**This is the cheapest, highest-value lift.** Bravoh does NOT download YouTube to feed Gemini — it passes the YouTube watch URL straight into a `FileData` part. Gemini's API resolves it natively.

**The load-bearing code** — `services/ai/audio_session.py:787-808`:
```python
for vid in selected:
    fps = 0.1 if vid.mode == "music" else 1   # "music" = hear-only (cheap), "video" = watch
    parts.append(types.Part(text=f"\n[YOUTUBE VIDEO: {vid.title} ({vid.category})]"))
    part_kwargs = {
        "file_data": types.FileData(file_uri=vid.url, mime_type=vid.mime_type),
    }
    if vid.mime_type.startswith("video/"):
        part_kwargs["video_metadata"] = types.VideoMetadata(fps=fps)   # fps=0.1 → audio-focused, low token cost
    parts.append(types.Part(**part_kwargs))
```
- `vid.url` is literally `https://www.youtube.com/watch?v=<id>` — see the `YouTubeVideoRef` dataclass at `audio_session.py:79-89`.
- `mode="music"` sets `fps=0.1` so Gemini samples ~1 frame / 10s → it *listens* to the track without paying for full video frames. This is exactly what Viber wants ("hear this reference track").
- The interleaved `[text label, FileData]` pattern (`_build_media_parts`, `audio_session.py:120-127`) is how every media type is labeled for the model.

**The tool that feeds it** — `services/ai/tools/fetch_youtube.py`:
- `FetchYoutubeTool(BravoTool)`, `name="fetch_youtube"`, schema = `{videos: [{url, title}], maxItems: 3}`.
- `_extract_video_id()` handles `watch?v=`, `youtu.be/`, `/shorts/`, and bare 11-char IDs.
- `_validate_videos()` does a parallel oEmbed HEAD check (`https://www.youtube.com/oembed`) to filter dead/removed videos before queuing — cheap liveness gate.
- Returns `{"queued": N, "_youtube_videos": [...]}`; the `_youtube_videos` key is the contract consumed downstream to build the `FileData` parts.
- (Secondary: it *also* fire-and-forgets a `yt-dlp` audio extract → MinIO → Celery embed for RAG. **Skip this for Viber** — we don't need the download; the FileData path is the win.)

**Lift into Viber:** add a `fetch_youtube`-shaped tool to `toolset.py`/`mcp_server.py`. When the DJ names a YouTube reference, build a `types.Part(file_data=types.FileData(file_uri=url), video_metadata=types.VideoMetadata(fps=0.1))` and prepend it to the Gemini contents. ~30 lines, no download, no yt-dlp dependency.

---

## 2. Quote-a-moment engine — cite a clip with a caption, grounded

Bravoh's "quoting" = the model emits an inline token `[[track-key:stem:start-end:Label]]` in its prose; a resolver turns each into a playable clip object; the frontend renders a player. This is the *exact* anti-slop "show its receipt" idea, applied to audio.

**How the model is taught to quote** — `services/ai/agentic_prompts.py:186`:
```
- AUDIO QUOTING: Gemini writes [[track-key:stem:start-end:Label]] → frontend renders playable clips.
```
That single prompt line is the entire contract. The model decides *when* to quote; the resolver guarantees it resolves or gets stripped.

**The resolver** — `services/ai/audio_map.py:486+` `AudioMap.resolve_quote(raw_quote)`:
- Input: `"empty-handed:drums:14-22:The Pocket"` → Output: `{raw, track_id, title, stem, start, end, label, url, available, ...}`.
- Parses both `M:SS-M:SS` and float-seconds time ranges (regex at `audio_map.py:507`).
- Resolves `track_id` against a per-conversation map (Redis-backed), with an ISRC→pool-URL fallback. **Unresolved quotes return `available: False`** — i.e. the un-cited/un-resolvable quote is downgraded, never faked. This is structurally the same as vibemix's Invariant #2 (citation grounding → strip to ack-bank).

**Quote persistence/caching** — `api/companion/ws_quote_cache.py`:
- Redis cache `quote_res:{conversation_id}:{md5(raw)[:12]}`, 7-day TTL, so resolved clips survive WS reconnects.
- `cache_resolved_quotes()` only caches quotes where `available` is true (line ~70).
- The cached blob carries the full citation payload: `url, label, track_id, title, artist, stem, start, end, bpm, key, scale, genre, art_url`.

**For a YouTube clip-a-moment specifically** — `api/companion/ws_chat_handler.py:169`:
```python
external_url = f"https://www.youtube.com/watch?v={video_id}&t={start}"
```
i.e. a quote's start-time becomes a deep-link `&t=` into the YouTube video. That's the "cut a clip at a moment and present it" mechanic for external media.

**Lift into Viber:** This is the marquee feature. vibemix already has the cue substrate — `src/vibemix/library/cue_types.py` (CueAnchor: intro/build/breakdown/drop/outro) and per-track BPM/key. Mirror Bravoh's pattern:
1. Teach the Viber prompt one quote syntax, e.g. `[[track_id:cue_name:Label]]` or `[[track_id:start-end:Label]]`.
2. Add a `resolve_quote()` to `toolset.py` that looks up the track + cue anchor, returns `{available, file/preview path, start, end, bpm, key, label}`.
3. Strip/downgrade unresolved quotes (already our Invariant #2). For local files the "url" is a file path or a `vibemix://preview/<id>?t=<sec>` the Tauri shell can play.

---

## 3. Composio — 9 toolkits, OAuth-managed, bridged as dynamic tools

**Probably skip for Viber v1** (it's a social-platform integration layer for an artist OS; a local DJ utility doesn't need OAuth-to-Instagram). Documented for completeness / future.

**Supported toolkits** — `services/composio/client.py:36-46`:
```
Tier 1: spotify, instagram, gmail, googlecalendar
Tier 2: tiktok, twitter, notion, canva, googledrive
```
Plus `_ESSENTIAL_TOOLS` (client.py:53-66) force-includes specific slugs Composio's default subset omits (e.g. `GMAIL_SEND_EMAIL`, `INSTAGRAM_POST_IG_USER_MEDIA`).

**Wiring:**
- `ComposioService` (client.py:124) = singleton around `from composio import Composio; Composio(api_key=...)`. Every SDK call goes through a monitored thread pool with hard timeouts (`_run_sync`).
- `execute_tool(artist_id, slug, arguments)` (client.py:409) → `self._client.tools.execute(slug, arguments, user_id=str(artist_id))`. Composio wraps results as `{"data": {...}, "successful": bool}`.
- `ComposioToolBridge(BravoTool)` (client.py:~722) = **the key pattern**: wraps each Composio tool as a `BravoTool`, prefixes the name with `ext_` to avoid native collisions, truncates description to Gemini's 295-char limit, sanitizes the JSON schema. `load_for_artist()` returns the per-artist bridges; failures degrade to `[]` (never turn-killing). `required_deps=["composio"]` so a kill-switch can drop them all.
- OAuth lifecycle in `api/composio/routes.py`: `GET /status`, `POST /connect/{toolkit}` (returns redirect URL), `DELETE /disconnect/{toolkit}` (with derived-data purge cascade).
- `_composio_instagram.py` shows the alternate pattern: a Composio-backed adapter that *duck-types* a native client (`ComposioInstagramAdapter`) so existing tools work whether the user connected via Composio or native OAuth.

**Lift verdict:** the reusable nugget is the **dynamic-bridge pattern** (wrap external tool → `BravoTool` → `register_dynamic()`), not Composio itself. We already have that shape via MCP (§5).

---

## 4. Web research / grounding / citations

Two distinct mechanisms, both reusable:

**(a) Brave Search tool** — `services/ai/tools/web_search.py` (`WebSearchTool(BravoTool)`):
- `name="web_search"`, schema `{query: string}`, `timeout_seconds=30`.
- Step 1: Brave Search API (`https://api.search.brave.com/res/v1/web/search`, `count=6`, key in `settings.brave_search_api_key`), ~500ms.
- Auto-appends the current year to queries lacking it (freshness hack, line ~58).
- Step 2: extracts `citations=[{title, url}]` + snippets; optionally synthesizes a summary with Gemini Flash (`thinking_level="LOW"`, 10s timeout) that's instructed to cite `[1][2]`.
- Returns `{query, result, citations[:8]}`. Falls back to raw snippets if synthesis fails (graceful).

**(b) Native Google Search grounding** — `services/ai/gemini_client.py:1651-1780` `generate_with_search()`:
- `config = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())], temperature=1.0)`.
- Extracts from `response.candidates[0].grounding_metadata`: `web_search_queries`, `grounding_chunks` (each → `{uri, title}` from `chunk.web`), and `search_entry_point.rendered_content`.
- Returns `{text, search_queries, grounding_chunks, search_entry_point}`.
- `services/ai/grounding.py` `MarketGrounding` wraps this for domain queries (genre trends, artist insight) with a **6-hour in-process cache** (`GroundingCacheEntry`, SHA256 query-hash key, 200-entry LRU eviction). Note its prompts explicitly say "Do NOT include source citations — present as Bravo's knowledge" — Bravoh's product choice; vibemix's anti-slop stance is the opposite (cite everything), so prefer the `web_search.py` citation-keeping behavior.

**Lift into Viber:** copy `web_search.py` almost verbatim as a Viber tool (swap `BravoTool` base for our toolset's tool shape). Or, simpler, use `generate_with_search()` directly — one `types.Tool(google_search=...)` config gets you grounded answers + `grounding_chunks` citations with zero extra API keys.

---

## 5. Agent/tool architecture — the pattern to mirror for Codex+MCP Viber

Bravoh's companion is structurally identical to what Viber wants. This is the **reference blueprint**.

**`BravoTool` ABC** — `services/ai/tool_registry.py:291-432`. A tool = class attrs + one `execute()`:
```python
class BravoTool(ABC):
    name: str
    description: str
    parameters_schema: dict          # JSON Schema for params
    timeout_seconds: float = 45.0
    side_effect: bool = False        # write-tools never re-fire on WS resume
    required_deps: list[str] = []    # kill-switch filtering
    async def execute(self, params, session, artist_id) -> dict: ...
    def to_function_declaration(self) -> types.FunctionDeclaration:   # → Gemini
        return types.FunctionDeclaration(name=self.name, description=self.description, parameters=self.parameters_schema)
    def to_deferred_definition(self) -> dict:                          # → Anthropic Tool Search ("defer_loading")
        return {"name": ..., "description": ..., "input_schema": ..., "defer_loading": True}
```
Notable patterns worth stealing:
- `announce()` / `announce_data()` (line 389-400) — per-task progress events via `contextvars` (no shared mutable state across concurrent sessions). Lets a tool stream "Searching the web…" sub-steps.
- `__init_subclass__` (line 347-371) auto-wraps every subclass's `execute()` with a context-bound guard — structural enforcement over discipline.
- Per-tool error classification `_classify_error()` (line ~120): `transient | input | dependency | auth_expired | internal` with retry policy (`_RETRY_DELAYS=[1,3]`, 3 attempts).
- `to_deferred_definition()` shows Bravoh already supports **Anthropic-style Tool Search deferred loading** — directly relevant if the Codex Viber path uses tool-search.

**`ToolRegistry`** — `tool_registry.py:476+`: `register()`, `register_dynamic(tools)` (per-request, contextvar-scoped at `_dynamic_tools_ctx` so concurrent sessions don't corrupt each other's tool surface), `get_tools_for_mode()`, `get_tool_search_config()` (returns deferred defs), `execute()` dispatch with shadow/timeout handling. Singleton via `get_tool_registry()`.

**The agent loop** — `services/ai/agentic_engine.py:1999+` `generate()`:
- Bounded function-calling loop (`_max_tool_rounds`, `tool_calls_made` counter, `max_rounds_reached` guard at line 2592) — the no-hang discipline Viber already follows.
- **Three tool sources merged into one Gemini surface per turn:**
  1. native tools (always registered),
  2. **Composio** dynamic bridges: `register_dynamic(_ext_tools)` (engine line 2290/2299),
  3. **MCP** dynamic tools: `register_dynamic(_mcp_tools)` (engine line 2342).
- MCP wiring — `agentic_engine.py:2330-2360`: when the artist's Studio is online, `load_mcp_tools(artist_id)` → `_select_mcp_subset(message, all, max_tools=budget)` → `register_dynamic()`. Budget = `ITR_MAX_TOOLS_PER_ITER - native - composio` so the per-turn tool count stays bounded. **This is the direct precedent for the Codex+MCP Viber agent**: MCP tools are loaded per-turn, subset-selected by relevance to the message, and registered into the same registry the model sees — no special-casing in the loop.

**Lift verdict:** vibemix's Viber already has the bones (`toolset.py` typed tools, `mcp_server.py` STDIO dispatch with `search_vibe`/`sequence_set`/`export_set`/etc., `codex_curate.py` for the Codex backend). The gaps Bravoh fills:
- A formal tool *base class* with `to_function_declaration()` + `to_deferred_definition()` (Gemini AND Anthropic/Codex tool-search in one shape).
- Per-turn `register_dynamic()` + relevance subset-selection with a tool-count budget (lets us add YouTube/web-search/quote tools without blowing the per-call tool cap).
- `announce()` progress streaming via contextvars.
- Error classification + bounded retry on tools.

---

## Concrete lift order for Viber (recommended)

1. **`fetch_youtube` + FileData injection** (§1) — trivial, no new deps, immediate "Viber heard your reference" demo.
2. **Quote-a-moment over CueAnchors** (§2) — the differentiator; reuses our `cue_types.py`. Teach one quote token, add `resolve_quote()`, strip unresolved (Invariant #2 already enforces this).
3. **`web_search` / `generate_with_search`** (§4) — drop-in grounded answers with citations.
4. **Formalize the tool base class + per-turn dynamic registration + budget** (§5) — so 1–3 plug in cleanly alongside the existing curate tools, for both Gemini and Codex backends.
5. **Composio** (§3) — defer unless Viber needs to post to socials; the dynamic-bridge pattern is already covered by MCP.

---

## Access note
`ssh altidus` worked (read-only `cat`/`grep`/`sed`/`ls`/`find` only; no writes, no service touches). Local `/Users/ozai/projects/bravoh` exists but is Mar 30 and lacks the composio API surface; `bravoh-server-pull` is May 2 frontend but its backend predates `app/api/composio/`. **The remote backend is the authoritative source for these capabilities** — re-grep there for any deeper dive.
