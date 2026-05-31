---
name: drive-vibemix
description: Launch vibemix in dev-source mode and DRIVE the running app to prove a change works LIVE — the perception loop (fire a control, read the logs it produced, confirm the co-host's reaction is grounded, not slop). Trigger when verifying any backend/runtime change actually works in the app (not just green tests), when Kaan asks "does this actually work / show me it working / run it / verify live", when a control or panel looks dead/unresponsive (button does nothing, panel blank, no reaction), when confirming a co-host reaction is grounded vs hallucinated, or when you edited anything under src/vibemix/ (state, agent, runtime/ws_bus, prompts, coach) and need to observe it on the real ws bus. Use BEFORE claiming a runtime fix is done — green unit tests do NOT prove the live app works (frozen sidecar + Tauri runtime hide real failures).
---

# drive-vibemix

Green tests are not a working app. vibemix has bitten this repo repeatedly: the
bundled sidecar is FROZEN and lags edited `src/`, the live `main()` path serves
the ws bus differently than the test stubs, and Tauri-runtime wiring (dead
buttons, idle-fault empty screens) never shows up in vitest/pytest. This skill is
the perception loop: **launch the real engine on current source, drive a control,
read what it actually produced, and confirm the co-host reacted to a REAL event.**

Companion skills (don't duplicate them — route):
- **vibemix-grounding-review** — judge whether a reaction-loop CHANGE is sound vs slop (static review). drive-vibemix is the LIVE counterpart: observe the actual output.
- **ipc-wiring-checker** — confirm both ends of an `ipc.*` type are wired (static). Use it first when a button looks dead; use drive-vibemix to then SEE the wire move.

## When you do NOT need this

A pure prose/doc edit, a frontend-only visual tweak (use vitest + the browser),
or a change with no runtime surface. This skill is for backend/runtime behavior
you must SEE move.

## 0 — Ground the surfaces first

Read [references/observe-and-logs.md](references/observe-and-logs.md). It has the
verified ws protocol, the exact on-disk log/trace paths, the frame grammar, and
the grounded-vs-slop definition. Everything below assumes it.

## 1 — Launch on current source (never the frozen bundle)

The Tauri shell spawns a FROZEN Python sidecar that lags your edits → false
negatives (a fixed bug still looks broken). Flip the resolver to repo source with
`VIBEMIX_DEV_SIDECAR=1` (verified: `tauri/src-tauri/src/sidecar.rs:537` → runs
`uv run python -m vibemix`).

Pick the lightest launch that exercises your change:

**A. Engine only (no GUI)** — fastest; proves backend + the ws bus. Prefer this
for state/agent/coach/event-detector/ws_bus changes.

```bash
# from repo root. Binds 127.0.0.1:8765 — make sure no other co-host is running.
uv run python -m vibemix
```

**B. Full app (GUI + engine on your source)** — when the change is end-to-end
(a control → sidecar → reaction) or visual:

```bash
cd tauri && VIBEMIX_DEV_SIDECAR=1 cargo tauri dev
```

CRITICAL — the single-socket invariant (#4): only ONE co-host may own
`127.0.0.1:8765`. If a packaged vibemix or another `python -m vibemix` is already
running, free the port first (`lsof -ti :8765`) or you get "address in use" / a
dead probe. Never start a second `websockets.serve` on 8765 — attach as a CLIENT.

Run the launch as a BACKGROUND process so you can observe while it runs.

## 2 — Attach as a client and watch the wire

The bundled probe connects as a normal client, prints frames, and can fire a
manual trigger or one schema-valid typed IPC frame. Run it with the project venv
(it needs the project's `websockets`):

```bash
# watch everything for 8s
.venv/bin/python .claude/skills/drive-vibemix/scripts/ws_probe.py --seconds 8
# watch only the co-host's spoken lines + grounded flag
.venv/bin/python .claude/skills/drive-vibemix/scripts/ws_probe.py --watch ipc.session.snapshot
# watch only the flat 30Hz mascot frame (meters / deck / next_suggestion)
.venv/bin/python .claude/skills/drive-vibemix/scripts/ws_probe.py --watch mascot --seconds 5
# fire a manual reaction (sets manual_trigger; the co-host speaks next tick)
.venv/bin/python .claude/skills/drive-vibemix/scripts/ws_probe.py --trigger --watch ipc.session.snapshot --seconds 6
# drive a typed sidecar handler with an ISO date-time ts
.venv/bin/python .claude/skills/drive-vibemix/scripts/ws_probe.py --ipc ipc.status.recheck --payload-json '{"component":"midi"}' --watch ipc.status.tick --seconds 3
```

`{"action":"trigger"}` is the always-safe inbound frame — the live path does NOT
schema-validate it; it just sets `manual_trigger`. The spoken text arrives in the
next `ipc.session.snapshot`'s `transcript_delta`.

Use `--ipc` for `ipc.*` frames; the probe builds `{type, ts, payload}` with a
schema-valid ISO `date-time` timestamp. Use `--action` only for bare action
frames such as `next_suggestion.feedback`.

To DRIVE the real app (push a settings control, click a button) use the live GUI
under `cargo tauri dev`, or send a frame the bus routes — see the inbound table in
the reference.

## 3 — Read what your action produced (don't theorize)

Two surfaces, two questions. Both verified present on disk.

**Frontend behavior — `~/Library/Application Support/world.bravoh.vibemix/vibemix/logs/ui.log`**
Did the click reach the sidecar and come back?

```bash
tail -n 40 ~/Library/Application\ Support/world.bravoh.vibemix/vibemix/logs/ui.log
```

A live control shows a `[vmx:click]` → `[vmx:ipc>]` → `[vmx:ipc<]` triple. A DEAD
button shows `[vmx:click]` with NO `[vmx:ipc<]` reply (round-trip never returned),
or a `[vmx:error]` line. This is the dead-control debugging path — read the tape,
don't guess.

**Brain behavior — the newest Python session dir**
What did the co-host actually decide, and on what evidence?

```bash
S=$(ls -dt ~/Library/Application\ Support/vibemix/recordings/*/ | head -1)
tail -n 30 "$S/events.jsonl"           # event / llm_invoke / citation_count lines
```

## 4 — The grounded-verification checklist (the release gate)

A change "works" only when a REAL event drove a reaction that cited REAL evidence.
Walk the chain in `events.jsonl` + the snapshot, in order:

- [ ] A `{"kind":"event","type":...}` line fired (HEARTBEAT/TRACK_CHANGE/PHASE/…) — the brain reacted to a detected event, not nothing (Invariant #3).
- [ ] A `{"kind":"llm_invoke",...}` line on that same `event`/`track`/`phase` — the model was actually called on that evidence.
- [ ] `{"kind":"citation_count","count": N}` with **N ≥ 1** — the reaction resolved a real citation. **`count: 0` repeatedly = slop** (un-cited → stripped to ack-bank fallback, Invariant #2). This is the anti-slop gate.
- [ ] The spoken text appears in the next `ipc.session.snapshot` `transcript_delta` AND refers to what is actually playing — not a fabricated track/move.
- [ ] At idle, `grounded:false` / `cohost_status:IDLE` is EXPECTED, not a fault (Invariant #5). Don't read silence at idle as "AI unreachable".

If text names a track or move that no `event`/`llm_invoke` line supports, or
`citation_count` is stuck at 0 while it keeps talking — that is hallucination and
the change FAILS. Route the reaction-content question to **vibemix-grounding-review**.

## 5 — Report honestly

State what you OBSERVED, with the exact log/frame lines as evidence (paste the
`citation_count`, the `transcript_delta`, the `[vmx:ipc<]` line). If the co-host
stayed mute, say so and name why from the tape (no key collected → never speaks;
`citation_count:0` → ack-bank only; port busy → never connected). Do not invent a
tidier story than the logs support. Tear down the background launch when done.
