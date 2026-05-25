# Codex-Powered Playlist-Curation Agent — Design Doc (vibemix)

**Date:** 2026-05-25 · **Status:** RESEARCH + DESIGN (read-only; zero repo edits)
**Decision (owner):** the per-user *playlist-curation agent* runs its REASONING on **Codex** (OpenAI's agentic coding tool, flat-rate via the owner's ChatGPT subscription), NOT Gemini. Co-host BRAIN stays Gemini; similarity engine stays local (vibemix's Gemini-embedding + sqlite-vec, not CLAP — note: brief says "local CLAP", but vibemix is Gemini-only per CLAUDE.md/MEMORY; the local similarity engine is `library/embed.py` + sqlite-vec). Only the AGENT's planning loop is Codex.
**Principle (owner):** simplest possible — "we don't build everything ourselves, we give the agent TOOLS and it figures it out." Codex itself is the bounded harness; we just expose tools.

---

## 1. AIRA → Codex mechanism (the template, with file refs)

AIRA's "codex/deepseek second brain" is **not** the OpenAI Codex CLI. It is the **Nous Hermes Agent** harness (`nousresearch/hermes-agent:v0.14`) configured to use **`provider: openai-codex`** as its model backend. The pattern is identical in shape to what vibemix wants, and is the proven template.

### How it wires together
- **Config-driven brain swap.** `aira-deploy/cutover/aira-tbb-next.config.codex-v014.yaml:1-5`:
  ```yaml
  model:
    default: gpt-5.5
    context_window: 256000
    provider: openai-codex
  ```
  The harness (Hermes) is the loop; `provider: openai-codex` points its brain at `chatgpt.com/backend-api/codex`.
- **Auth = ChatGPT-subscription OAuth, NOT an API key.** This is the cheap part.
  - Login (device flow, headless): `hermes auth add openai-codex --type oauth --no-browser` — `aira-deploy/pilot-codex/README.md:11`.
  - Token persists on the volume: `/opt/data/.hermes/auth.json` (chown uid 10000, perms 600) — CLAUDE.md:778, `aira-deploy/deploy.py:40-64` (it literally `docker cp`s `auth.json` from the pilot to reuse the OAuth).
  - The env override that selects routing: `HERMES_INFERENCE_PROVIDER=openai-codex` (config yaml header comment lines 13-22). Routing is self-contained: `base=chatgpt.com/backend-api/codex, auth=codex OAuth token store`.
- **Tools are exposed via MCP.** `aira-tbb-next.config.codex-v014.yaml:77-105`:
  ```yaml
  mcp_servers:
    agentanalytics:
      url: ${MCP_SERVER_URL}              # streamable HTTP MCP server
      headers:
        Authorization: Bearer ${MCP_SERVICE_TOKEN}
      tools:
        include: [aa_query_duckdb_readonly, aa_kb_search, ...]   # 22-tool allowlist
  ```
  The MCP server is AIRA's own backend (`MCP_SERVER_URL` → `host.docker.internal:8080/mcp` in pilot, prod backend in live). The brain (codex) accepts the tool schemas and calls them; verified at `aira-deploy/cutover/pilot-v014/eval/verdict.md:14` ("codex → `aa_query_duckdb_readonly` → prod → 2097 real rows").
- **Headless / one-shot invocation:** `hermes -z "<prompt>"` prints ONLY the final response to stdout (`pilot-codex/README.md:10`). That is the "spawn → curate → result" primitive.
- **Robustness already in the harness:** cross-provider fallback codex→deepseek fires on `401/402/429/5xx/timeout/empty` (config lines 6-25); reasoning effort clamped to `medium` (lines 26-35); a schema sanitizer flattens union/format schemas codex rejects (`patches/11-anthropic-tool-schema-sanitize.py`).

### What's transferable to vibemix
The shape — **harness + `provider: openai-codex` (OAuth) + MCP-tool allowlist + headless one-shot** — transfers directly. The ONE difference: AIRA uses the *Hermes* harness (heavy, container, persona, hooks). vibemix should use the **native OpenAI Codex CLI** (`codex exec`) instead — same auth model, far lighter, no container, perfect for a desktop OSS app. AIRA proves the auth + MCP + one-shot pattern works; vibemix just swaps the harness for the lighter native one.

---

## 2. Codex 2026 runtime facts (sourced)

- **What "Codex" is now:** an open-source agentic coding tool with a CLI (`codex`), an IDE extension, and a cloud mode. The CLI runs an agentic tool-calling loop against an OpenAI model (`gpt-5.5`-class).
- **Headless / programmatic:** `codex exec "<prompt>"` — non-interactive, processes the prompt and prints the result to stdout, progress to stderr. Built for CI/scripts. Key flags:
  - `--json` → JSONL event stream on stdout (`thread.started`, `item.completed`, `turn.completed`) for machine parsing.
  - `--output-schema <file>` + `-o <path>` → enforce a JSON Schema on the final message and write it to a file (this is how we get a clean playlist object out).
  - `--sandbox read-only|workspace-write|danger-full-access` → filesystem permission tier; default read-only, no interactive prompts in exec mode.
  - `--skip-git-repo-check`, `--ephemeral` (don't persist session), `--ignore-user-config`.
- **Tool-calling / MCP:** Codex is an MCP **client**. Configure servers in `~/.codex/config.toml` (or per-project `.codex/config.toml`), or `codex mcp add <name> -- <command>`. Two transports:
  - **STDIO** (local subprocess): `[mcp_servers.x] command=... args=[...] env_vars=[...]` with `startup_timeout_sec` (default 10) and `tool_timeout_sec` (default 60).
  - **Streamable HTTP**: `[mcp_servers.x] url=... bearer_token_env_var=... http_headers={...}`.
  - Tool filtering: `enabled_tools` (allowlist) / `disabled_tools` (denylist), `default_tools_approval_mode = auto|prompt|approve`. For headless: set approval to `auto`.
- **The "insanely cheap" — CONFIRMED flat-rate:** Codex is **included in ChatGPT Plus ($20/mo), Pro ($200/mo)**, Business, Edu, Enterprise. Usage is metered as **agent messages / cloud tasks per rolling 5-hour window** (Plus ≈ 45-225 local agent messages + 10-60 cloud tasks per window) — i.e. covered by the flat subscription, NOT per-token billed. The alternative is API-key auth (`CODEX_API_KEY` / `OPENAI_API_KEY`) which IS metered per-token (credits per Mtok). So the owner's "flat-rate vs metered Gemini API" intuition is exactly right: **`codex login` (ChatGPT sub) = flat-rate; API key = metered.**
  - ⚠️ Caveat to flag: the subscription path is **per-user account-bound** and rate-limited per window — fine for one user's own login, problematic if WE host one shared login (see §4).
- **Boundedness is built in:** the agentic loop, timeouts (`tool_timeout_sec`, `startup_timeout_sec`), sandbox tiers, and turn termination are all the Codex harness's job — we do not rebuild them (see §5).

Sources:
- https://developers.openai.com/codex/noninteractive
- https://developers.openai.com/codex/mcp
- https://developers.openai.com/codex/config-reference
- https://developers.openai.com/codex/cli/reference
- https://developers.openai.com/codex/pricing
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://chatgpt.com/codex/pricing/

---

## 3. The simplest vibemix design — MCP tool-server + Codex wiring

**Key finding: vibemix already has the agent built — as a GEMINI function-calling harness.** `src/vibemix/library/agent.py` is a "Viber Agent — Phase 1: bounded Gemini function-calling playlist curator" with EXACTLY the 3 tools the brief proposes (`search_vibe` / `get_track_features` / `create_playlist`), full grounding (seen-set), and no-hang (`MAX_TOOL_ITERATIONS=12`, per-tool + per-call timeouts). The Codex decision means **re-fronting those same 3 already-implemented tool handlers as an MCP server and pointing Codex at it** — the handlers, grounding gate, and validators are reusable as-is. This is a small, additive change, not a rewrite.

### 3a. Existing hooks (file:line where each tool maps)
- `search_vibe` → `src/vibemix/library/search.py:84` `vibe_search(embedder, store, library, query, k=10, cache_db=None) -> (list[VibeSearchResult], bool)`. Already wrapped at `agent.py:192` `_tool_search_vibe` (adds returned ids to the per-run seen-set, `agent.py:210`).
- `get_track_features` → keys via `src/vibemix/state/harmonics.py:83` `to_camelot(raw)` (deterministic — LLM never computes keys) + the `TrackEntry` BPM/title/artist from the Rekordbox library. Wrapped at `agent.py:224` `_tool_get_track_features`.
- `create_playlist` → `src/vibemix/library/create_playlist.py:53` `create_playlist(library, name, track_ids, *, out_dir=None) -> PlaylistResult`. Already validates every id via `library.lookup_by_id` and writes **M3U + JSON**, dropping unknown ids (`create_playlist.py:73-90`). Wrapped at `agent.py:243` `_tool_create_playlist` with **grounding gate #1** (every id must be in this run's seen-set, `agent.py:250-262`) before `create_playlist`'s own library re-validation (gate #2).

### 3b. The MCP server (new, tiny — ~120 lines)
Build with the official **Python MCP SDK** (`pip install "mcp[cli]"` — FastMCP). vibemix does NOT currently depend on `mcp` (grep: only doc references in `.planning/`), so this is one new dep. New file `src/vibemix/library/mcp_server.py`, STDIO transport (simplest for a desktop subprocess):

```python
# src/vibemix/library/mcp_server.py  (sketch — not committed)
from mcp.server.fastmcp import FastMCP
from vibemix.library import search, create_playlist, store, embed, importer
from vibemix.state import harmonics

mcp = FastMCP("vibemix-library")
# allocate library/embedder/store ONCE at startup (DI, mirrors main())

@mcp.tool()
def search_vibe(query: str, k: int = 10) -> list[dict]:
    matches, _ = search.vibe_search(EMBEDDER, STORE, LIBRARY, query, k=k)
    _SEEN.update(m.track_id for m in matches)        # grounding seen-set
    return [m.to_dict() for m in matches]

@mcp.tool()
def get_track_features(track_id: str) -> dict:
    t = LIBRARY.lookup_by_id(track_id)
    if t is None: return {"error": "unknown track_id"}
    return {"title": t.title, "artist": t.artist, "bpm": t.bpm,
            "camelot": harmonics.to_camelot(t.key)}   # deterministic key

@mcp.tool()
def create_playlist_tool(name: str, track_ids: list[str]) -> dict:
    invented = [t for t in track_ids if t not in _SEEN]   # gate #1
    if invented: return {"error": f"not from search_vibe: {invented}"}
    res = create_playlist.create_playlist(LIBRARY, name, track_ids)  # gate #2
    return res.to_dict()

if __name__ == "__main__":
    mcp.run()   # STDIO
```
This re-uses `agent.py`'s grounding/validation logic verbatim — both invariants (#2 citation grounding, #3 trust-the-audio) are preserved because `create_playlist` still re-validates against the live library and keys still come from `to_camelot`.

### 3c. Pointing Codex at it
Per-request config written at curate-time (so the OSS app controls it, not the user's global `~/.codex/config.toml`). Use a project-scoped `.codex/config.toml` or pass `--config`:

```toml
[mcp_servers.vibemix_library]
command = "uv"
args = ["run", "python", "-m", "vibemix.library.mcp_server"]
startup_timeout_sec = 15
tool_timeout_sec = 30
enabled_tools = ["search_vibe", "get_track_features", "create_playlist_tool"]
default_tools_approval_mode = "auto"   # headless: no prompts
```

### 3d. Per-request invocation (`vibemix library curate "<theme>"`)
A thin Python wrapper spawns Codex headless and reads back a schema-validated playlist:

```python
# sketch — new CLI subcommand wrapper
proc = subprocess.run(
    ["codex", "exec",
     "--sandbox", "read-only",          # tools do the writing, not the shell
     "--output-schema", str(SCHEMA),    # {name, track_ids[], rationale}
     "-o", str(out_json),
     "--skip-git-repo-check",
     SYSTEM_PROMPT + f"\n\nTheme: {theme}"],
    capture_output=True, timeout=120,   # OUR outer guard (see §5)
)
playlist = json.loads(out_json.read_text())
```
System prompt = the same 3 grounding rules already in `agent.py:62-68` ("only put a track in a playlist if a prior search_vibe returned it; keys/BPM come from get_track_features; call create_playlist once").

### 3e. Auth/install story (desktop OSS app)
- **Codex CLI install:** `npm i -g @openai/codex` or Homebrew (`brew install codex`) — document in `docs/`. One-time.
- **Auth:** `codex login` → browser → ChatGPT account. Token lands in `~/.codex/auth.json` (mirror of AIRA's `/opt/data/.hermes/auth.json`). This is the user's OWN flat-rate subscription.
- **MCP SDK:** add `mcp` to `pyproject.toml` (one new pure-Python dep — green on the one-click-install bar; no native build).

---

## 4. Distribution decision (flag, don't decide)

| | **BYO-Codex** (user's own login) | **We-host one subscription** |
|---|---|---|
| Cost to us | **€0** | ~$20-200/mo + overage; abuse can blow the rolling-window cap for everyone |
| Adoption barrier | User needs ChatGPT account + `codex login` (extra step; some friction) | Zero user setup — "just works" |
| ToS | Clean — each user uses their own plan as intended | **Grey/violating** — one account shared across many users is exactly what per-account rate-limits exist to stop; risk of account ban |
| Key-protection problem | **Solved** — no shared secret to leak | **Re-creates the API-key-protection problem of the year** (CLAUDE.md security constraint) — same as embedding a raw key; needs a Bravoh-side proxy + per-client rate limit |
| Abuse blast radius | Contained to the abuser's own account | One bad actor exhausts the shared window → outage for all |
| Quality control | We can't pin model/effort centrally | Central control of model + effort |

**Recommendation — BYO-Codex for Phase 1.** It is €0, ToS-clean, and *sidesteps the API-key-protection problem entirely* (the project's stated security constraint). The friction (one `codex login`) is acceptable for the curation feature being an opt-in power-user surface, not the core co-host. The co-host brain stays on the Bravoh-proxied Gemini key (existing plan); only the *optional* playlist agent asks the user to BYO-Codex. If/when adoption proves it, revisit we-host behind a Bravoh proxy with per-client rate-limit (same shape as the planned Gemini proxy) — but that is explicitly NOT Phase 1.

---

## 5. No-hang split (Codex's harness vs our wrapper)

**Codex's harness owns (do NOT rebuild):**
- The agentic loop itself — turn termination, when to stop calling tools.
- MCP tool timeouts: `tool_timeout_sec` (default 60, we set 30) and `startup_timeout_sec` (default 10, we set 15).
- Sandbox enforcement (read-only by default; tools do the writing, not shell).
- Reasoning-effort / token budget bounding (set via config, like AIRA's `reasoning_effort: medium`).
- Per-tool approval gating (`default_tools_approval_mode = auto` for headless).

**Our thin vibemix wrapper MUST still guard:**
1. **Subprocess spawn timeout** — `subprocess.run(..., timeout=120)` (outer wall-clock). Codex bounds *tool* calls but a wedged Codex process or a stuck OAuth refresh needs an outer kill. On timeout: `proc.kill()` + return a graceful "curation timed out" to the UI.
2. **Codex-not-installed / not-logged-in** — detect `FileNotFoundError` (no `codex` binary) and the auth-error exit code; surface an actionable message ("Run `codex login` to enable AI playlists"), mirroring vibemix's existing api-key-missing UI loop (P74).
3. **Empty/garbage output** — `--output-schema` enforces shape, but still defensively parse: if `out_json` is empty or missing `track_ids`, degrade to "no playlist" instead of crashing (mirrors `agent.py`'s `stop_reason` handling).
4. **MCP server process lifecycle** — Codex spawns the STDIO server as a child; our wrapper should ensure the library/embedder is allocated once and the server exits cleanly when Codex disconnects (no orphan).
5. **Grounding re-validation** — even though the MCP server gates ids, the wrapper trusts ONLY `create_playlist`'s persisted M3U/JSON (real ids) as the result — never the model's free-text track list. Invariant #2 stays enforced at the tool boundary, not the prompt.

Everything else (loop control, tool timeouts, sandboxing) is Codex's job — the wrapper is a spawn + timeout + parse + degrade shell, nothing more.

---

## Appendix — corrections / things to verify with owner
- Brief says "similarity engine is local CLAP." vibemix is **Gemini-only, no CLAP** (MEMORY: `feedback_no_clap_use_gemini_embedding`). The local similarity engine is `library/embed.py` (Gemini embedding) + sqlite-vec. Confirmed against repo, not changed.
- A prior design doc `/tmp/audit/agent-harness-design.md` (the Gemini-harness Phase-1 contract `agent.py` cites) already exists — this Codex doc supersedes the *brain* choice in it; the tool surface + grounding contract carry over unchanged.
- `mcp` is a NEW dependency (not currently in `pyproject.toml`). Needs owner OK per the no-scope-creep rule, though it's pure-Python and green on the one-click-install bar.
- Native `codex` CLI auth file path (`~/.codex/auth.json`) inferred from the AIRA Hermes analogue + OpenAI docs; verify exact path on a real `codex login` (needs owner / a machine with Codex installed).
