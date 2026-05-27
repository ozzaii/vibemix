# LEARN-FROM-AIRA → vibemix: Mobile Chat Interface + No-Hang Robustness + Per-User Scoping

Source repo (read-only): `/Users/ozai/projects/agentanalytics/`
Scope: extract (1) the mobile/chat interface pattern, (2) the agent no-hang mechanisms, (3) per-user scoping — as concrete templates for vibemix's per-user playlist agent.

> **Headline reality check.** AIRA does **not** run on Telegram, and its agent loop is **not** in this repo. AIRA's brain is **Hermes** (`openai-codex`/`gpt-5.5`, deepseek fallback) running as a Docker container on the AA server. The chat surface AIRA actually uses is **WhatsApp** via a Node **Baileys** bridge (`gateway/platforms/whatsapp.py` + `whatsapp-bridge/bridge.js`) — that bridge source lives **only on the server**, not locally. Hermes *does* support Telegram natively (it appears in the platform allow-list `("whatsapp","telegram","discord","signal",...)` — see patches 02/03), so "Telegram instead of WhatsApp" is a config swap on Hermes' side, not new code.
>
> What you can learn locally is the **architecture**, not a copy-paste Telegram bot. The valuable, reusable pieces that ARE in the local repo: the **MCP tool dispatch layer** (`backend/routes/mcp/`), the **phone→user→scoped-JWT** per-user model (`scope_helper.py` + `issue_mcp_token.py`), the **no-hang patches** (`aira-deploy/patches/`), and the **idempotency cache**. vibemix's brain is Gemini, so the LLM transport differs — but the harness shape (chat-platform → message router → agent → scoped tools → reply, with bounded loops + timeouts) is directly portable.

---

## 1. AIRA MOBILE / CHAT INTERFACE — the pattern

### How a message flows (AIRA today)
```
User phone (WhatsApp app)
  → Baileys bridge.js (Node, long-lived WebSocket to WhatsApp; on server)
  → Hermes gateway platform adapter (whatsapp.py) — inbound event {chat_id, text, attachments}
  → Hermes agent loop (codex brain; bounded — see §2)
        ↳ calls MCP tools over HTTP to the Flask backend  /mcp/call_tool
            (Bearer JWT; scoped per-user — see §3)
  → agent produces reply text
  → outbound boundary sanitizer (aira_strip_leaks) strips model/tool/iteration leaks
  → adapter.send(chat_id, reply)  → bridge.js  → user phone
```

Key properties to copy:
- **The bridge is a thin, persistent transport.** It owns the connection to the messaging platform (WhatsApp WebSocket / Telegram long-poll or webhook) and does nothing but marshal `{chat_id, text, media}` in and `reply` out. All intelligence is behind it.
- **`chat_id` is the routing key, and it's stable per device.** AIRA uses the WhatsApp **LID** (`95421925965878@lid`) as the durable id — phone-number changes don't invalidate it (gotcha #44). For Telegram the equivalent is the numeric `chat_id` from the update.
- **Inbound id is NOT the agent session id.** A landmine AIRA hit (gotcha #44 Layer 2): the hook passed Hermes' internal `session_id` (`20260506_171214_a0b7af4e`) where the bridge expected a platform JID → bridge crashed `Cannot destructure 'user' of jidDecode(...)`. **Lesson: keep a clean map `{platform_chat_id ↔ internal_user/session}`; never let one leak into the other's slot.**
- **Outbound sanitizer is mandatory.** Everything the agent says passes through `_aira_sanitizer.aira_strip_leaks` (single source of truth — patch 07 deduped a stale inline copy that silently bypassed it). It strips model identity, tool names, "iteration 12/60", patch markers. For vibemix this is your **anti-slop boundary**: strip any "as an AI", tool-call chatter, or internal event names before the DJ sees it.

### Telegram crash-alert (the ONE Telegram thing that IS local)
`backend/config/agentanalytics-telegram-alert.service` — a systemd `OnFailure=` oneshot that fires a Telegram Bot API `sendMessage` when the backend crashes:
```
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
     -d chat_id=${TELEGRAM_CHAT_ID} -d parse_mode=HTML -d text=...
```
This is **one-way push**, not an interactive agent — but it's a complete, dependency-free template for the Telegram Bot API call (token in env, `chat_id` target, `sendMessage` endpoint). It proves the minimal outbound half.

### Minimal vibemix port (Gemini-first, Telegram, no server bridge needed)
vibemix is a **local desktop app**, so you don't need AIRA's container/Baileys infra. The simplest robust shape:

1. **Transport: python-telegram-bot long-poll** (not webhook — webhook needs a public URL; long-poll works from a laptop behind NAT). One `getUpdates` loop. Bot token in `.env` (`TELEGRAM_BOT_TOKEN`), same as the alert service.
2. **Auth / per-user: an allow-list of `chat_id`s.** For a single-owner tool, hard-pin the owner's `chat_id` (mirror `TELEGRAM_CHAT_ID`). Reject everything else — this is your entire auth model for v1 (don't build JWT scoping until vibemix is multi-user). AIRA's scoped-JWT (§3) is the upgrade path when you go multi-user.
3. **Router: `chat_id → user → user's library + played-set state`.** One dict/table keyed by `chat_id`. This is the playlist-agent's tenancy boundary (the vibemix analog of `scope_helper.get_scope_for_mcp_caller`).
4. **Agent: Gemini Flash with function-calling over your existing embedding tools.** "make me a 90-min peak-time set" → Gemini calls `query_library(vibe=..., bpm=..., minutes=90)` (your sqlite-vec/embedding search) → assembles → replies with the tracklist. Reuse vibemix's `library/` vibe-search + `evidence_registry` grounding so the reply cites real tracks (anti-hallucination, same bar as the live co-host).
5. **Outbound sanitizer.** Run the reply through a vibemix `strip_leaks()` before `bot.send_message` — no tool names, no "iteration", no model identity. Keep the "real DJ friend" voice.
6. **Heartbeat for long runs** (see §2) — if the embedding query takes >a few seconds, send "bir saniye, set'i kuruyorum…" so the chat never *looks* hung.

File refs to mirror:
- `backend/config/agentanalytics-telegram-alert.service` — Bot API `sendMessage` shape + env handling.
- `backend/routes/mcp/scope_helper.py` — per-user tenancy translation (copy the *shape*, not the JWT).
- `backend/routes/mcp/handlers/aa_get_calls_by_phone.py` — model handler: input schema, normalize id, scoped DuckDB query, JSON-safe return. vibemix's `query_library` tool should look exactly like this.

---

## 2. NO-HANG ROBUSTNESS CHECKLIST ("agent takılmaz")

AIRA's anti-wedge mechanisms, extracted as concrete items vibemix's agent MUST implement. Each maps to a real file/gotcha.

| # | Mechanism (AIRA) | Source | vibemix MUST do |
|---|---|---|---|
| R1 | **Bounded agent loop.** Hermes caps iterations (`iteration X/60` surfaced in patches 02/03). The loop cannot run forever. | patches 02/03 ("iteration X/60") | Gemini function-call loop **MUST** have a hard `max_tool_calls` cap (e.g. 8) + a wall-clock budget. On cap-hit, return best-effort answer, never spin. |
| R2 | **Hard per-call timeout on every outbound HTTP / tool call.** Every relay/gateway POST uses `timeout=10`. No unbounded network wait. | `echo_wa_push.py:128`, `skrib_channel_dispatcher.py:212` | Wrap every Gemini call AND every embedding/DB query in `asyncio.wait_for(..., timeout=N)` (or `httpx`/`google-genai` request timeout). Never call a blocking API with no timeout. |
| R3 | **Never-give-up reconnect with capped backoff (no permanent death).** The original Hermes bug: MCP coroutine `return`ed after 5 retries → `session=None` permanent → only a container restart recovered. Fixed: after `MAX_RECONNECT_RETRIES`, **don't return** — keep retrying at `_MAX_BACKOFF_SECONDS` cap, throttle log to every 10th attempt. | `aira-deploy/patches/mcp_never_give_up_2026_05_23.py` (markers `MCP-NEVER-GIVE-UP`, `MCP-RESET-ON-CLEAN-RECONNECT`) | If vibemix's agent depends on a long-lived connection (ws_bus, Gemini Live session), the reconnect path must **cap backoff and loop forever**, never `return`/exit the task. **Reset retry counters on a clean reconnect** so spread-out blips don't accumulate to exhaustion. |
| R4 | **Stuck-loop watchdog / auto-suspend.** `_STUCK_LOOP_THRESHOLD = 3`: a session that's active across 3 consecutive restarts gets auto-suspended (treated as wedged). | gotcha #44 Layer 3b | Add a watchdog: if the same agent turn has been "in flight" across N restarts / past a stale-age, force-clear it. (vibemix already has the `in_flight` flag + stale-age force-clear in the live loop — apply the same to the playlist agent.) |
| R5 | **Cross-provider fallback on the brain.** codex → deepseek fires on `401/402/429/5xx/timeout/empty`. A dead/ratelimited primary never wedges the turn. | CLAUDE.md AIRA "Brain" | vibemix is Gemini-only (no second provider), so the analog is: on Gemini `429/5xx/timeout/empty`, **fail gracefully to a deterministic answer** (e.g. a non-LLM library query result) rather than retrying forever or hanging. Bounded retries (R1) then bail. |
| R6 | **Idempotency cache on write/expensive actions.** 24h LRU+TTL keyed by `(tool_name, idempotency_key)`; a retried request returns the cached result instead of re-running. | `backend/routes/mcp/idempotency.py` | Key any expensive/side-effecting playlist action (e.g. "build set", "send to Rekordbox") by an idempotency key so a Telegram retry / double-tap doesn't double-run or hang re-doing work. |
| R7 | **Fail-closed, never fail-open.** Bad scope → `AND 1 = 0` (matches nothing), not empty filter (which reads as "all rows"). | `scope_helper.py:89-97` | When user/library context is missing, return "no results / can't do that," never silently fall through to global/unscoped behavior. |
| R8 | **Every handler catches broadly + returns a structured error, never raises into the loop.** Dispatch wraps `spec.handler(**args)` in try/except, logs last 500 chars of traceback, returns an MCP error envelope. A tool exception degrades to a message, it doesn't crash the agent. | `dispatch.py:321-340`, all handlers return `{ok: False, error}` | Every vibemix tool returns `{ok, ...}`/`{ok:False, error}`; the agent loop turns a tool error into a spoken/typed apology, never an unhandled exception that wedges the turn. |
| R9 | **Heartbeat / "still working" so a long run never *looks* hung.** Hermes emits a neutral "Hâlâ çalışıyorum, bir dakika." on messaging platforms during long turns (iteration counter stripped). | patches 02/03 | If a Telegram request runs long (big embedding scan), send a typing indicator + a neutral progress line. Perceived-hang is as bad as real hang for the "DJ friend" feel. |
| R10 | **Non-blocking spawn for any subprocess.** (Project lesson, not AIRA-specific but reinforced): an agent that shells out to a never-returning command (`pytest`, `npm run dev`, `ffmpeg`) wedges. | this project's own history | Any subprocess the playlist agent spawns (ffmpeg for clip prep, etc.) MUST be `run_in_executor` with a timeout OR detached/non-blocking, never a foreground blocking `wait()`. |

**Minimum bar for vibemix's playlist agent to "never takılır":** R1 (bounded loop) + R2 (per-call timeout) + R8 (handlers return errors, never raise) + R9 (heartbeat). R3/R4 apply only if it holds a long-lived connection. R6/R7 harden correctness.

---

## 3. PER-USER SCOPING — reusable bits

AIRA's per-user isolation, and what vibemix should lift for "each user's own library + played set":

- **Tenancy lives in the token, never in tool input.** The JWT's `user_id` IS the boundary; tools read `g.user_id` and MUST NOT accept a tenant id as a parameter (gotcha: `issue_mcp_token.py` docstring D-23). → **vibemix: derive the user from the `chat_id`→user map server-side; never let the chat message specify whose library to query.**
- **Two scope modes** (`scope_helper.py`): a **service token** = tenant-wide ("Müberra mode", sees all), a **per-user `mcp:agent` token** = filtered to that user's own rows (`AND agent_name = ?`). vibemix analog: owner token = full library; a future shared/guest token = scoped to that user's own library + played set.
- **Phone→user→scoped-JWT mint.** Phase 99 maps a WhatsApp phone to a user, then mints a per-user token (`issue_mcp_token --scopes mcp:agent --role agent --ttl-days 30`) so "a single agent calling via WhatsApp can never see another agent's calls." → **vibemix multi-user upgrade path: `chat_id → user → scoped token → query only that user's library/played-set`.** For v1 (single owner) this collapses to a `chat_id` allow-list.
- **Phone normalization before lookup** (`aa_get_calls_by_phone.py:_normalize_tr_phone`) — idempotent canonicalization of the routing key. vibemix analog: normalize the Telegram `chat_id` (it's already a clean int — trivial) but the *pattern* (normalize the external id once, at the edge) is the lesson.
- **Cross-channel session continuity** (`sohbet_session_resolver.py`): one stable `session_id` (UUID v4) per `user_id` across web/WA/voice; **distinct `user_id` → distinct session, never merged**; guards against oversized ids that would 422. → **vibemix: one playlist-agent session per user, keyed by user_id; the same user talking from Telegram and from the desktop app should resolve to the same session/state, and two users must never share state.**
- **Fail-closed default** (R7 above) is the security backstop for all of the above.

**Reusable for vibemix's per-user playlist agent:**
1. `chat_id → user_id` map at the transport edge (the whole per-user model for v1).
2. Pass `user_id` to every tool implicitly (from context), never from the message.
3. Scope every library/played-set query by that `user_id`, fail-closed if missing.
4. One session per user; never merge users; same user across surfaces = same session.

---

## 4. SERVER-ONLY — needs the owner (could not verify locally)

These exist only on the AA server (`ssh aa` / the `aira-tbb-next` container volume) and were **not** read (no ssh, per instructions):
- **The actual messaging bridge source** — `gateway/platforms/whatsapp.py` and `whatsapp-bridge/bridge.js` (Baileys). The local repo only has *patches* against them, not the files. The exact inbound-event shape, the Telegram adapter (if any is wired), and how `chat_id` maps to a Hermes session live there.
- **The Hermes agent loop itself** — `tools/mcp_tool.py`, `gateway/run.py` (where `iteration X/60`, `_MAX_RECONNECT_RETRIES`, `_STUCK_LOOP_THRESHOLD`, the heartbeat sender live). We see them only via the patch anchors. To read the real loop, owner must pull from the container/Hermes upstream.
- **Live config** — `/opt/data/config.yaml` (whether Telegram is actually enabled, the platform list, reasoning_effort, timeouts).
- **`bridge.js` PTT/audio routing** (gotcha #39) — relevant only if vibemix ever accepts voice notes over Telegram.

If you want the bridge's exact Telegram wiring as a literal template (rather than rebuilding with python-telegram-bot), that's the one thing that needs server access — but for a local desktop tool, **you should NOT copy the server bridge anyway**; python-telegram-bot long-poll is the right local-first choice.

---
*Generated from local repo only. No ssh, no server access, no private transcript paths touched.*
