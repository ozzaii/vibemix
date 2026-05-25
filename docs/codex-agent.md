# Viber Agent — Codex backend

The Viber agent turns a natural-language theme into a playlist drawn from
**your own** library. It has two interchangeable reasoning backends behind one
grounded tool surface:

- **`gemini`** (default) — built-in Gemini function-calling. Works out of the
  box with your `GEMINI_API_KEY`.
- **`codex`** — your flat-rate ChatGPT subscription drives the reasoning via
  the native [Codex](https://developers.openai.com/codex) CLI (`codex exec`,
  `provider: openai-codex` — the same pattern Hermes uses for AIRA). vibemix
  exposes its tools to Codex over a local MCP server; Codex plans, vibemix's
  tools do the work.

Both backends share the **same grounded tools** (`search_vibe` /
`get_track_features` / `create_playlist`) and the **same anti-hallucination
gate**: the agent can only put a track in a playlist if a prior `search_vibe`
returned it, and every id is re-validated against the live library before the
playlist is written. The backend choice never weakens grounding.

## Why Codex

- **Flat-rate.** Codex is included in ChatGPT Plus ($20) / Pro ($200) — metered
  as agent messages per 5-hour window, **not** per token. Your own login, your
  own plan. (API-key auth exists too but is per-token billed — not what we
  want here.)
- **No shared secret.** BYO-Codex means there is no embedded key to leak — it
  sidesteps the API-key-protection problem entirely. The co-host brain stays on
  the Bravoh-proxied Gemini key; only this optional curation agent uses Codex.
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

If Codex is missing or not logged in, `library curate --backend codex` fails
with an actionable message (the same UX as a missing API key) — it never
crashes or silently degrades.

## Usage

```bash
# Codex reasons; vibemix's tools search your library, the app writes the playlist.
VIBEMIX_CODEX_ALLOW_SHELL=1 \
  uv run python -m vibemix library curate "warm-up hypnotic 122-126" --backend codex

# Default Gemini backend (no Codex, no bypass needed):
uv run python -m vibemix library curate "peak-time rolling techno"
```

### ⚠️ The `VIBEMIX_CODEX_ALLOW_SHELL` opt-in (upstream bug)

Codex has an **open regression** ([openai/codex#16685](https://github.com/openai/codex/issues/16685),
[#24135](https://github.com/openai/codex/issues/24135)): in non-interactive
`codex exec`, **every MCP tool call is auto-cancelled** ("user cancelled MCP tool
call") unless `--dangerously-bypass-approvals-and-sandbox` is set —
`default_tools_approval_mode = "auto"` does NOT take effect in exec mode. That
bypass also drops codex's shell sandbox.

So the Codex backend needs you to opt in with `VIBEMIX_CODEX_ALLOW_SHELL=1`,
which consciously accepts that codex runs with shell access for that invocation.
Without it, `--backend codex` returns an honest `codex_mcp_blocked` error
pointing here. **The default Gemini backend works with none of this** — it's the
recommended path until codex fixes the regression.

Division of labour: **Codex SELECTS** (search + reason + order) and **vibemix
WRITES** (the wrapper persists the validated M3U/JSON — the single grounded
write — so a file always lands even if the model doesn't call the persist tool).

Output is a neutral **M3U + JSON** playlist in `~/.cache/vibemix/playlists/`
(not a Rekordbox-XML write-back — that path is unsafe for the master DB).

## How it wires together

```
codex exec  ──(STDIO MCP)──>  python -m vibemix.library.mcp_server
   │                                   │
   │  plans the set, calls tools       ├─ search_vibe        (the only discovery path)
   │                                   ├─ get_track_features (deterministic key/BPM)
   └──< final {name, track_ids} >──    └─ create_playlist    (seen-set gate + library re-validate)
                │
                └─ vibemix re-validates track_ids against the library (grounding boundary)
```

- The MCP server (`src/vibemix/library/mcp_server.py`) wraps the shared
  `LibraryToolset` — the exact same grounding code the Gemini agent uses.
- The wrapper (`src/vibemix/library/codex_curate.py`) owns only the guards
  Codex's harness does not: not-installed / not-logged-in detection, an outer
  spawn timeout, empty-output degrade, and result-boundary grounding
  re-validation.

## Mobile surface (Telegram)

Curate from your phone: run `library telegram` and the same Viber agent answers
a long-poll Telegram bot.

```bash
export VIBEMIX_TELEGRAM_TOKEN=...            # from @BotFather
export VIBEMIX_TELEGRAM_ALLOWED_CHATS=123456 # your numeric chat id(s) — the auth
uv run python -m vibemix library telegram
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

See the full decision record in
`.planning/research/viber-direction-2026-05-25/codex-agent-design.md`.
