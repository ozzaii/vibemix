# MAP — APP-DRIVING capability (can an unattended agent launch + drive + observe the app?)

Scope: the `launch → drive → observe` loop the autonomous QA harness depends on.
Read-only map. Every claim carries file:line. Verified LIVE against the app that
was running on `127.0.0.1:8765` at map time (a packaged `vibemix.app`).

TL;DR verdict: **the OBSERVE + DRIVE half is REAL and LIVE-VERIFIED today.** The
recorded-set FEED is REAL (`VIBEMIX_REPLAY_SESSION`) but real-time only (no
fast-forward) and feeds a *downmixed mono* stream, not the multichannel deck-split.
The LAUNCH half is the weak link: there is **no deterministic, race-free, agent-owned
one-command launcher**, and the dev-boot failure we hit today ("VIBEMIX-CORE STOPPED")
is a real, reproducible timeout race. **Screenshots are not a built capability.**

---

## 1. What the vibemix-dev MCP exposes — and is it reliable?

Server: `src/vibemix/runtime/dev_mcp_server.py` (935 lines, FastMCP STDIO, client-only).
Registered LIVE in `~/.claude.json` under project `dj-set-ai` → `mcpServers.vibemix-dev`:

```json
{ "type":"stdio",
  "command":"/Users/ozai/projects/dj-set-ai/.venv/bin/python",
  "args":["-m","vibemix.runtime.dev_mcp_server","--repo-root","/Users/ozai/projects/dj-set-ai"],
  "env":{} }
```

So the MCP IS wired into this project's Claude config (an agent in this repo can call it).
It is NOT in any in-repo `.mcp.json` (none exists) — the registration lives only in the
user's `~/.claude.json`. A *fresh* Codex/Claude worktree would NOT inherit it.

| Tool | Impl | What it does | REAL? |
|------|------|--------------|-------|
| `ws_observe(seconds, type_filter?)` | `tool_ws_observe_async` / `_ws_collect` `dev_mcp_server.py:226,634` | Client-attach to :8765, collect inbound frames for N s. `type_filter` = `all` / `mascot` / substring of `type`. | **REAL — LIVE-VERIFIED:** 116 frames in 3 s from the running app (76 mascot, 38 `ipc.session.snapshot`, 2 `ipc.status.tick`). |
| `ws_trigger(action, payload?)` | `tool_ws_trigger_async` / `_ws_send_one` `:294,641` | Send ONE inbound frame. `trigger` → `manual_trigger`; `ipc.*` → typed `{type,ts,payload}` via IpcRouterBus; bare actions → `{action,...}`. | **REAL — LIVE-VERIFIED:** `{"action":"trigger"}` accepted, immediate mascot reply returned. |
| `tail_events(lines, session?)` | `tool_tail_events` `:515` | Parse recent `events.jsonl` (event / llm_invoke / citation_count) from newest-or-named session under the PLAIN root. | REAL (read-only file tail; fail-soft when no session). |
| `tail_ui_log(lines)` | `tool_tail_ui_log` `:497` | Last N lines of bundle-id `ui.log` (`[vmx:click]/[vmx:ipc>]/[vmx:ipc<]/[vmx:error]`). | REAL — but only exists once the GUI has run (engine-only never writes it, `:504`). |
| `which_handler(type_or_control)` | `tool_which_handler` `:557` | Resolve ipc type → TS sender + Py handler, WIRED/DEAD/ORPHANED, by reusing the ipc-wiring scanner. | REAL — but **needs `--repo-root`**; degrades to actionable error if the skill scanner is absent `:147,565`. |
| `learn_probe(...)` | `tool_learn_probe_async` / `_ws_learn_probe` `:660,385` | Start a Learn lesson + send one `ipc.learn.ack`, return all `ipc.learn.*` frames + a parsed summary. | REAL design, **NOT live-verified here** (would need an active Learn window). Defaults reproduce the FLX4 L1.03 knob failure class. |
| `sidecar_status()` | `tool_sidecar_status_async` `:695` | ws reachable? dev-source mode? GEMINI_API_KEY present (presence only, never value)? | **REAL — LIVE-VERIFIED:** `ws_reachable:true`, `gemini_key_present:true (.env)`. **Caveat:** `dev_sidecar` reflects the MCP child's OWN env, NOT the app's (env doesn't cross — `:731-733`), so it can't actually tell you whether the *running app* is dev-source or bundled. |

Reliability assessment:
- **Tooling itself is reliable** — 24/24 unit tests pass (`tests/runtime/test_dev_mcp_server.py`, all against fakes on ephemeral ports). Every tool is fail-soft (returns `{"error":...}`, never raises — the no-hang contract, `:15`).
- **Flakiness risk is environmental, not code:** all ws tools depend on something already listening on :8765. If nothing is running, every tool returns an actionable "cannot reach" error (`:273-281`) — honest, not a hang.
- **A genuine correctness caveat:** `ws_trigger`/`ws_observe` open a **new short-lived connection per call** (`websockets.connect` inside each helper, `:248,311,447`). They do NOT hold a persistent client. So "trigger then observe" is two separate connects — a fast broadcast emitted between the two calls can be missed. For the QA loop you must `ws_observe` with a long window and trigger *from a second concurrent task*, or accept that immediate replies (captured in the 0.5 s drain at `:317`) are the only guaranteed trigger feedback.

---

## 2. The deterministic one-command launch path TODAY — and its gap

There is **no single command** that an unattended agent can run to get a clean
launched-and-driveable app. The drive-vibemix skill (`.claude/skills/drive-vibemix/SKILL.md`)
documents TWO launch modes, both with manual caveats:

- **Engine only:** `uv run python -m vibemix` (SKILL.md:43-46). Binds :8765, no GUI.
  Fastest, proves backend + ws bus. **This is the closest thing to a one-command path**
  for an audio/brain QA loop that does NOT need the webview.
- **Full app:** `cd tauri && VIBEMIX_DEV_SIDECAR=1 cargo tauri dev` (SKILL.md:52). Needs a
  display, needs the Rust supervisor, and is where today's boot failure lives (§3).

Resolver: `VIBEMIX_DEV_SIDECAR=1` → `DevSource` arm → `uv run python -m vibemix`
(`sidecar.rs:678`, `resolve_sidecar_invocation` `:656-657`). Unset → `Bundled` (the
FROZEN PyInstaller binary that lags `src/` — the false-negative trap the skill warns about).

**Hard launch blockers an agent will hit (all real, observed):**
1. **Invariant #4 / port contention.** Only ONE co-host may own :8765. At map time a
   packaged `vibemix.app` was already holding it (PID 50326, `/Applications/vibemix.app`).
   A second launch returns the **fatal exit-2 sentinel** → `sidecar-crashed reason=port-in-use`,
   no retry (`sidecar.rs:582-601`). The agent must `lsof -ti :8765` and kill first
   (SKILL.md:55-58) — there is no auto-free.
2. **No display = no GUI mode.** `cargo tauri dev` needs a windowing surface; there is
   **no headless/offscreen launch path** anywhere in `tauri/` (grep: 0 hits for
   headless/xvfb/offscreen in non-dist source). For an overnight unattended run the
   engine-only path is the only display-free option.
3. **MCP env doesn't cross.** The MCP child can't read the launching shell's env
   (`dev_mcp_server.py:30-33,876`), so the harness must pass roots/keys as ARGS and
   launch the app in a separate process it controls — the MCP cannot launch the app
   (by design: "never launching the app", `:8`).

---

## 3. ROOT CAUSE — "VIBEMIX-CORE STOPPED" on dev boot (the uv-first-run race)

This is a real, reproducible timeout race between two independent clocks. There is
**no boot health-handshake** — the Rust shell infers "alive" purely from "did :8765
start answering in time", and that window is shorter than a cold `uv` sync.

The timeout that fires the banner:
- `tauri/src-tauri/src/ws_client.rs:39` — `const UNREACHABLE_AFTER: u32 = 12;`
- Backoff `BACKOFF_START_MS=250 → BACKOFF_CAP_MS=5000` (`ws_client.rs:33-34`), doubling.
- The loop connects, fails (sidecar not bound yet), sleeps backoff, doubles, repeats.
  After 12 consecutive failures it latches `ws-state="unreachable"` (`ws_client.rs:127-129`).
- **Computed cumulative time to the latch ≈ 42.75 s** (250+500+1000+2000+4000+5000×7).
  (The code comment says "~30s" at `ws_client.rs:35` — that comment is stale; the real
  number is ~43 s. Either way it is well short of an ~80 s cold uv sync.)
- The webview turns that latch into the banner: `crash-banner.ts:104-106` maps
  `ws-state=="unreachable"` → `reasonMessage("ws-unreachable")` →
  **"vibemix-core stopped responding. The Restart button below will relaunch it."**
  (`crash-banner.ts:57-58`). That is the "VIBEMIX-CORE STOPPED" surface.

Why uv blows past it: the `DevSource` arm runs `uv run python -m vibemix`
(`sidecar.rs:469-531`). On first run in a worktree, `uv` does a full dep-sync
(resolve + build/download wheels) BEFORE Python even starts — so :8765 isn't bound
until ~80 s+, long after the 12-failure latch at ~43 s. The sidecar eventually binds
and the ws client *does* reconnect (it keeps trying — `ws_client.rs:124-125`), so the
banner self-clears on the next `connected` (`crash-banner.ts:108-110`) — but to a human
or an agent watching the first 60 s, it looks dead/stopped. The supervisor itself does
NOT kill the slow sidecar (it only restarts on a non-zero EXIT, `sidecar.rs:603-624`,
MAX_RESTARTS=3) — so this is purely a *false* "stopped" signal, not a real crash.

Important: the Rust supervisor has **no spawn/health TIMEOUT of its own**. It waits on
the child forever (`spawn_blocking(child.wait())` / the plugin event loop,
`sidecar.rs:459-467,510-531`). The only "timeout" in the whole boot path is the
ws_client unreachable latch. So the fix is entirely in two places: pre-warm uv, and/or
relax the latch during boot.

### Fix options (cheapest → most robust)
1. **Pre-sync deps before launch (cheapest, do this tonight).** Run `uv sync` (or
   `uv run python -c "pass"`) ONCE in the worktree before `cargo tauri dev`, so the
   first `uv run python -m vibemix` starts Python immediately. This removes the race
   without touching code. The harness launcher should always do a warm `uv sync`
   pre-step. (Belt-and-suspenders: also pre-warm the bundled-vs-dev path you'll use.)
2. **Bump the boot-grace latch (small code change).** Raise `UNREACHABLE_AFTER`
   (`ws_client.rs:39`) or add a one-time longer initial grace so first-boot tolerates
   ~90 s before latching "unreachable". Cheap, but masks genuinely-dead sidecars longer.
3. **Real boot health handshake (most robust, more work).** Have the sidecar emit a
   "bound + ready" event the Rust supervisor waits on with an explicit, generous boot
   timeout (separate from the steady-state reconnect latch), so "starting" and
   "stopped" are distinct states. This is the correct long-term fix and would make
   `sidecar_status()`/the banner truthful during boot.

Recommendation for tonight: **option 1 (pre-sync) in the harness launcher**, plus
option 2 as a 1-line safety bump. Option 3 is a follow-up build.

---

## 4. The recorded-set FEED — REAL, with two sharp caveats

This is the keystone the whole QA mission rests on, and it EXISTS:
`src/vibemix/platform/_audio_replay.py` — env-gated replay capture backend, wired into
`__main__.py`:
- `VIBEMIX_REPLAY_SESSION=<session-dir>` activates it (`_audio_replay.py:30-35`).
- Three wrappers swap the **input capture stream** (not output): audio
  (`maybe_wrap_replay_audio_backend`), MIDI (`...midi...`), nowplaying track
  (`...track...`) — all called in `__main__.py:1373,1392,1457`.
- It reads a recorded session dir's `input.wav` + `midi.jsonl` + `nowplaying.jsonl` and
  replays them through the *same* sounddevice-shaped callback the live CoreAudio stream
  would call (`_audio_replay.py:101-118,166-186`), so the normal buffers, deck splitter,
  event detector, state refresh, and reaction loop run unchanged. MIDI is timed off a
  monotonic tape (`:230-244`); nowplaying is a time-scripted player (`:304-331`).
- A recorded session is produced by `audio/recorder.py` (per-session `input.wav` +
  jsonl, `recorder.py:175-181,250-253`).

**Caveat A — real-time only, NO fast-forward.** The capture stream sleeps
`block.shape[0] / sample_rate` per block (`_audio_replay.py:186`). A 3-hour recording
replays in **exactly 3 hours** of wall-clock. There is zero acceleration knob
(verified: no speed/rate/2x path). Acceptable for an overnight run, but it means one
3h pass = 3h, and you cannot iterate quickly.

**Caveat B — replayed audio is DOWNMIXED MONO 16 kHz, not the multichannel deck-split.**
`recorder.py` writes `input.wav` as 1-channel, 16 kHz (`recorder.py:251-253`,
`INPUT_SR_TARGET=16000`, `constants.py:38`) — i.e. the post-resample mono Gemini-feed,
NOT the live 48 kHz / 4-channel deck-pair capture (the live snapshot at map time showed
`input_channels=16 opened_channels=4 ... deck_pairs=A:0,1+B:2,3`). So a replayed session
exercises the **mono reaction brain on real audio** (good — that IS Sven's #1 path), but
it does **not** reproduce per-deck audio separation / stem grounding from a recording.
Any QA judgment about deck-attributed citations on replay must account for this — the
deck audio context on replay falls back to "global mix", not true stems.

---

## 5. Screenshots / UX-legibility capture — MISSING as a built capability

The QA mission requires "capture screenshots" and judge "UX-legible". There is **no
in-app screenshot command**: zero `screenshot`/`screencapture`/webview-capture commands
in `tauri/src-tauri/src/` (only a `record_50a_walk.sh` that shells `screencapture` for a
human walk, `scripts/e2e/record_50a_walk.sh:51`). To screenshot the running GUI an
unattended agent must use OS-level computer-use / `screencapture`, which needs a display
and a real window — incompatible with the engine-only headless path. **The UX/visual
half of the judge has no headless data source today.** The text-legible surface that IS
available headlessly is `ipc.session.snapshot` (transcript, grounded flag, cohost_status)
+ `ui.log` + `events.jsonl` — enough to judge anti-slop/grounded/on-time, NOT enough to
judge "you open Learn and can't tell what to do" (that is a visual/layout claim).

---

## 6. REAL vs ASPIRATIONAL — verdict table

| Capability | Verdict | Evidence |
|---|---|---|
| Observe live frames (transcript, grounded, status, meters) | **REAL, live-verified** | `dev_mcp_server.py:226`; 116 frames/3s observed |
| Drive a manual reaction / typed IPC over the wire | **REAL, live-verified** | `dev_mcp_server.py:294,641`; trigger accepted live |
| Read brain decisions/citations headlessly | **REAL** | `tail_events` `:515`; events.jsonl `recorder.py:175` |
| Read frontend round-trip (dead-button detection) | **REAL** (needs prior GUI run) | `tail_ui_log` `:497-504` |
| Resolve IPC wiring static (WIRED/DEAD) | **REAL** (needs `--repo-root`) | `which_handler` `:557` |
| Learn-surface QA hand | **REAL design, unverified here** | `learn_probe` `:660` |
| Feed a recorded set into the real pipeline | **REAL, but real-time + mono only** | `_audio_replay.py:1-186`; wired `__main__.py:1373,1392,1457` |
| Deterministic race-free one-command launch | **ASPIRATIONAL** | no such command; uv race §3 |
| Headless GUI launch | **MISSING** | no headless path in `tauri/` |
| Headless screenshots / visual capture | **MISSING** | no in-app capture; only `record_50a_walk.sh` (human) |
| Truthful boot/health state ("starting" vs "stopped") | **MISSING (broken signal)** | `ws_client.rs:39,127`; stale "~30s" comment vs ~43s real |
| Auto-free :8765 on launch | **MISSING** | exit-2 fatal, manual kill required `sidecar.rs:582` |

---

## 7. What must be BUILT / WIRED for unattended launch→drive→observe (where)

Ordered by leverage for tonight's loop:

1. **A harness launcher script (new, e.g. `scripts/qa/launch_replay.sh`)** that an agent
   can run with ONE command and trust:
   - pre-step: `uv sync` (warm deps — kills the §3 race) ;
   - free :8765 if held (`lsof -ti :8765 | xargs kill`) — there is no auto-free today ;
   - export `VIBEMIX_REPLAY_SESSION=<recorded 3h set>` + `GEMINI_API_KEY` + `VIBEMIX_LOCAL_TTS` ;
   - launch ENGINE-ONLY (`uv run python -m vibemix`) in the background, headless ;
   - poll `sidecar_status()` until `ws_reachable:true` (generous ~120 s budget) before
     declaring ready. This is the missing deterministic entrypoint.
2. **Record (or locate) a real 3-hour session dir** in the replay format
   (`input.wav` 16k mono + `midi.jsonl` + `nowplaying.jsonl`). Without a recorded set,
   the replay backend has nothing to feed. (Recorder format: `recorder.py:175-181`.)
3. **Fix the boot-health signal (`ws_client.rs:39` + a boot-grace)** so a slow first
   boot isn't a false "STOPPED" — at minimum bump `UNREACHABLE_AFTER`/add initial grace;
   ideally a real ready-handshake (§3 option 3). Also fix the stale "~30s" comment.
4. **Add a headless visual-capture path** for the UX-legibility judge: either a Tauri
   `capture_webview_png` command (new, `tauri/src-tauri/src/`) the agent can invoke, or
   document an OS-level `screencapture` step gated to GUI runs. Until then, the UX judge
   runs on text surfaces only and the "can't tell what to do in Learn" claim stays human.
5. **Wire the vibemix-dev MCP into the repo (`.mcp.json`)** so a fresh Codex worktree
   inherits it (today only `~/.claude.json` has it — worktrees won't). Pass `--repo-root`.
6. **(Nice-to-have) optional replay acceleration knob** in `_audio_replay.py:186`
   (e.g. `VIBEMIX_REPLAY_SPEED`) so iteration isn't locked to 3h/pass. Note: faster than
   real-time will desync the event-detector cooldowns/heartbeat timing, so a clean
   accelerated run needs care — real-time is the safe default for tonight.
