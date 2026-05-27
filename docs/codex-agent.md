# Viber Agent — Codex Backend

The Viber agent turns a natural-language theme, set brief, or chat message into
grounded action over **your own** library. The product backend is **local
Codex**: your flat-rate ChatGPT subscription drives the reasoning via the native
[Codex](https://developers.openai.com/codex) CLI (`codex exec`,
`provider: openai-codex` — the same pattern Hermes uses for AIRA). vibemix
exposes its tools to Codex over a local MCP server; Codex plans, vibemix's tools
do the work.

Codex runs against the **grounded tool core**. The core tools are
`search_vibe`, `discover_pool`, `get_track_features`, `sequence_set`,
`create_playlist`, and `export_set`; expanded capabilities add energy,
quote/moment, web, DJ-knowledge, and cue-export helpers. They all use
the **same anti-hallucination gate**: a track can only be written or exported if
a prior discovery tool returned it, and every id is re-validated against the
live library before the output is written.

## Why Codex

- **Flat-rate.** Codex is included in ChatGPT Plus ($20) / Pro ($200) — metered
  as agent messages per 5-hour window, **not** per token. Your own login, your
  own plan. (API-key auth exists too but is per-token billed — not what we
  want here.)
- **No shared secret.** BYO-Codex means there is no embedded key to leak — it
  sidesteps the API-key-protection problem entirely. The live co-host brain
  stays on the Bravoh-proxied Gemini key; Library/Viber uses Codex.
- **The harness is Codex's job.** The agentic loop, per-tool timeouts, and
  sandboxing are all enforced by Codex. vibemix just exposes tools and adds an
  outer wall-clock kill.

## One-time setup

1. **Install Codex:**
   ```bash
   npm i -g @openai/codex     # or: brew install codex
   ```
2. **Log in with your ChatGPT plan:**
   ```bash
   codex login
   ```
   Auth lands in `~/.codex/auth.json` (your own subscription). vibemix never
   touches your global `~/.codex/config.toml` — the MCP-server wiring is
   injected per-invocation via `-c` overrides.

If Codex is missing or not logged in, `library curate`, `library build-set`,
and `library chat` return an actionable setup result. The desktop Library UI
renders those as Viber setup cards; it never crashes or silently falls back to
fake data.

Finder/Dock-launched macOS apps do not inherit shell startup PATH. vibemix
therefore searches common Codex and Node locations before launching
`codex exec`; set `VIBEMIX_CODEX_BIN` or `VIBEMIX_NODE_BIN` when a machine uses
a custom install path.

## Usage

```bash
# Codex reasons; vibemix's tools search your library, the app writes the playlist.
VIBEMIX_CODEX_ALLOW_SHELL=1 \
  uv run python -m vibemix library curate "warm-up hypnotic 122-126" --backend codex

# Default is Codex during the local test phase:
VIBEMIX_CODEX_ALLOW_SHELL=1 \
  uv run python -m vibemix library curate "peak-time rolling techno"

# One conversational Viber turn (stateless; the UI supplies --history):
VIBEMIX_CODEX_ALLOW_SHELL=1 \
  uv run python -m vibemix library chat "find a darker bridge from this" --backend codex --json

# Build and export a Rekordbox-importable XML set:
VIBEMIX_CODEX_ALLOW_SHELL=1 \
  uv run python -m vibemix library build-set "warehouse opener, melodic into rolling" \
    --curve peak_time --export rekordbox --backend codex --json
```

### ⚠️ The `VIBEMIX_CODEX_ALLOW_SHELL` opt-in (upstream bug)

Codex has an **open regression** ([openai/codex#16685](https://github.com/openai/codex/issues/16685),
[#24135](https://github.com/openai/codex/issues/24135)): in non-interactive
`codex exec`, **every MCP tool call is auto-cancelled** ("user cancelled MCP tool
call") unless `--dangerously-bypass-approvals-and-sandbox` is set —
`default_tools_approval_mode = "auto"` does NOT take effect in exec mode. That
bypass also drops codex's shell sandbox.

For direct CLI use, the Codex backend needs you to opt in with
`VIBEMIX_CODEX_ALLOW_SHELL=1`, which consciously accepts that Codex runs with
shell access for that invocation. The desktop app is already a trusted local
context, so the Rust Library bridge sets this env only for `--backend codex`
chat/curate/build-set commands. Without it, `--backend codex` returns an honest
`codex_mcp_blocked` error pointing here.

Division of labour: **Codex SELECTS/REASONS** (search, order, explain, decide
which tools to call) and **vibemix VALIDATES/WRITES** (seen-set gate +
library re-validation at the boundary). Curate persists a neutral **M3U + JSON**
playlist in `~/.cache/vibemix/playlists/`. Build-set can additionally write a
Rekordbox-importable **collection XML** via `export_set`; this is a portable
import artifact, not a direct master DB mutation.

## How it wires together

```
codex exec  ──(STDIO MCP)──>  python -m vibemix.library.mcp_server
   │                                   │
   │  plans the set, calls tools       ├─ search_vibe / discover_pool (grounded discovery)
   │                                   ├─ get_track_features / energy (deterministic facts)
   │                                   ├─ sequence_set / export_set   (validated set prep)
   └──< final JSON reply/set >──       └─ create_playlist / export_set (seen-set gate + re-validate)
                │
                └─ vibemix re-validates track_ids before playlist/export artifacts land
```

- The MCP server (`src/vibemix/library/mcp_server.py`) wraps the shared
  `LibraryToolset` grounding code.
- The wrapper (`src/vibemix/library/codex_curate.py`) owns only the guards
  Codex's harness does not: not-installed / not-logged-in detection, an outer
  spawn timeout, empty-output degrade, and result-boundary grounding
  re-validation.

## Mobile surface (Telegram)

Curate from your phone: run `library telegram` with the optional `telegram`
extra and the same Viber agent answers a long-poll Telegram bot.

```bash
export VIBEMIX_TELEGRAM_TOKEN=...            # from @BotFather
export VIBEMIX_TELEGRAM_ALLOWED_CHATS=123456 # your numeric chat id(s) — the auth
export VIBEMIX_CODEX_ALLOW_SHELL=1           # required for direct CLI Codex MCP runs
uv run --extra telegram python -m vibemix library telegram
```

- **Auth = a chat_id allow-list** (fail-closed: an empty list authorizes
  nobody). No public URL — long-poll, so it runs alongside the desktop app with
  nothing exposed. To find your chat id, message the bot and check the rejection
  log, or use a `@userinfobot`.
- **Privacy:** outbound messages are path-scrubbed — a result lists tracks by
  `artist - title`, never your local filesystem paths. The M3U/JSON still lands
  in `~/.cache/vibemix/playlists/` on your machine.
- **Grounding holds:** the bot only ever relays REAL library tracks (the agent's
  seen-set + library re-validation), never invented ones.
- Each request runs under a wall-clock timeout in an executor, so a slow
  curation can never wedge the poll loop (no-hang).

## Distribution note

Phase 1 is **BYO-Codex** (each user's own login): €0 to us, ToS-clean, no
shared key to protect. A we-host model (one shared subscription behind a
Bravoh proxy) is possible later but re-introduces the key-protection and
shared-rate-limit problems, so it is explicitly out of scope for now.

Current implementation notes live in this file and
`.planning/research/CODEX-full-product-sweep-map.md`. The original
pre-implementation Codex decision record is archived under
`.planning/archive/2026-05-27-stale-viber-direction-research/codex-agent-design.md`.
