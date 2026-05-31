# drive-vibemix — observe surfaces, log paths, frame grammar

Every path, port, env var, and tag below is verified against the real code (file
cited inline). Do not invent paths; if a surface is missing here, read the code.

## 1. The one socket — `ws://127.0.0.1:8765`

`WS_HOST = "127.0.0.1"`, `WS_PORT = 8765` — `src/vibemix/audio/constants.py:49-50`.
The live co-host serves this with `ws_broadcast` (`src/vibemix/runtime/ws_bus.py`).
**Invariant #4: one socket, never two listeners.** You connect as a CLIENT
(`ws_probe.py` does `websockets.connect`). Do NOT start a second `websockets.serve`
on 8765 — it collides with the running co-host. The debrief window uses `8766`,
not 8765.

The startup line the co-host prints when the bus is up (`ws_bus.py:857`):

```
-> mascot bus on ws://127.0.0.1:8765 (send {action: trigger} for manual fire)
```

### Inbound frames the bus accepts (`ws_bus.py` `handler()`)

| frame | effect | validated? |
|-------|--------|-----------|
| `{"action": "trigger"}` | sets `manual_trigger` → co-host fires a reaction next tick | no — always safe |
| `{"action": "next_suggestion.choose", "candidate_id":…, "track_id":…}` | pill alt-pick | no |
| `{"action": "next_suggestion.feedback", "feedback":…}` | pill thumbs | no |
| `{"type": "ipc.settings.set"/"ipc.settings.get"/"ipc.profile.*"/"ipc.recordings.*", …}` | routed to `SessionLoop` handlers via `IpcRouterBus.dispatch` | reply only |

The live `ws_broadcast` path does NOT schema-validate inbound `ipc.*` frames — it
only checks `msg["type"]` is a string with a registered handler (`ws_bus.py:844`,
`IpcRouterBus.dispatch` at `:716`). For a no-friction nudge, prefer
`{"action":"trigger"}`. The full `ipc.settings.get` envelope needs `{type, ts,
payload:{}}` (`tauri/ui/src/ipc/messages.schema.json`, `additionalProperties:false`).
Use `ws_probe.py --ipc ... --payload-json ...` for typed IPC probes; it fills an
ISO `date-time` `ts` so the same frame is valid when it crosses a schema-checked
path.

### Outbound frames the bus broadcasts to every client

1. **Flat mascot frame** — NO `type` field, ~30Hz. Built in `ws_broadcast`
   (`ws_bus.py:924`). Keys: `music`/`voice`/`mic` meters, `audible`, `deck`,
   `phase`, `bpm`, `mood`, `bpm_confidence`, `active_genre`, `detected_genre`,
   `emotion`, `reaction_intent`, `deck_state`, `deck_mixer`, `next_suggestion`,
   `live_evidence`, `course3_lens`, and the `*_context` strings. **Honest-null:**
   an unresolved deck carries `camelot: null` / `key: null` — never a fabricated
   key (the bus is a dumb wire).
2. **`ipc.session.snapshot`** — ~15Hz (`SNAPSHOT_EVERY_N=2`, `ws_bus.py:101`).
   `payload` carries `meters`, `bpm`, `track {title,artist,deck}`, `cohost_status`
   (`TALKING`/`LISTENING`/`IDLE`), `grounded` (= `state.audible`), `midi_events`,
   and **`transcript_delta`** = the AI lines spoken since the last snapshot
   (`_build_session_snapshot`, `ws_bus.py:569`). This is where you SEE what the
   co-host said.
3. **`ipc.status.tick`** — ~1Hz (`STATUS_EVERY_N=30`, `ws_bus.py:119`). Badges:
   `livekit`/`gemini` (always `ok` — there is no honest down-signal here),
   `midi` (real connected-controller count), `screen` (`ok`/`denied`/`unavailable`).
4. **`ipc.learn.*`** — controller-detected + midi-position envelopes when the
   Learn module is wired (`ws_bus.py:1084`).

## 2. Log + trace files on disk (macOS — verified present)

vibemix has a deliberate two-root split (`config.rs:134-145`, "config split-brain").

### Frontend UI log (what the webview did)

`~/Library/Application Support/world.bravoh.vibemix/vibemix/logs/ui.log`

This is the BUNDLE-ID root (`world.bravoh.vibemix`) because `debug_log.rs` uses
`app.path().app_local_data_dir()` (which on macOS returns the bundle-id dir) then
joins `vibemix/logs/ui.log` (`tauri/src-tauri/src/debug_log.rs`). `sidecar.log`
(rotating Python sidecar log) sits next to it.

Line shape (`debug-log.ts` `formatLine` + Rust timestamp prefix):

```
t=<epoch>.<ms> [vmx:click] mood-rocker → set HYPE {"value":"hype-man"}
```

Tag grammar (`debug-log.ts:14-15`, `debug_log.rs:4-5`):

| tag | meaning |
|-----|---------|
| `[vmx:click]` | a UI control was clicked (the optimistic local flip) |
| `[vmx:ipc>]` | request the webview SENT to the sidecar |
| `[vmx:ipc<]` | reply the webview RECEIVED from the sidecar |
| `[vmx:ws]` | ws bus lifecycle / frame note |
| `[vmx:state]` | local state transition |
| `[vmx:error]` | a swallowed/handled error |

**Read it, don't theorize.** A dead button shows as `[vmx:click]` with NO matching
`[vmx:ipc>]`/`[vmx:ipc<]` pair → the handler never fired or the round-trip never
came back. A `[vmx:error]` line names the throw.

### Python engine recordings + trace (what the brain did)

`~/Library/Application Support/vibemix/recordings/<YYYYMMDD-HHMMSS>/`
(NO bundle-id; `app_data_dir()` → `_resolve_recordings_root()`,
`config_store.py:119-126` + `__main__.py:314-327`).

Per session dir:

| file | content |
|------|---------|
| `events.jsonl` | structured per-session events (always written) |
| `trace.jsonl` | categorized trace (`VIBEMIX_TRACE` default ON; off with `VIBEMIX_TRACE=0`) — `__main__.py:851` |
| `voice.wav` / `last_gemini_audio.wav` / `input.wav` | captured audio |
| `session.json` | session meta |

`events.jsonl` line kinds (verified from a real session):

| `kind` | what it proves |
|--------|----------------|
| `event` (+`type`: `HEARTBEAT`/`TRACK_CHANGE`/`PHASE`/`LAYER_ARRIVAL`/`MIX_MOVE`…) | a real detected event fired (Invariant #3 — trust the audio) |
| `llm_invoke` (+`event`,`track`,`phase`,`prompt`,`cache_state`) | the brain was actually called, and ON WHAT evidence |
| `citation_count` (+`count`,`response_id`) | **THE anti-slop signal (Invariant #2)** — `count: 0` = the reaction had no resolvable citation and was stripped to the ack-bank fallback |
| `mic_part_skipped` / `lookahead_part_attached` | which audio Parts went to the model |

## 3. Grounded vs slop — what "it works" actually means

A change that "works in the app" means a REAL event produced a reaction that cites
REAL evidence — not that a log line appeared.

- **Grounded reaction:** a `kind:event` line, then a `llm_invoke` on that same
  event/track/phase, then `citation_count` with `count >= 1`, then the spoken text
  shows up in the next `ipc.session.snapshot`'s `transcript_delta`. The text refers
  to what is actually playing.
- **Slop / hallucination:** `citation_count: 0` repeatedly (un-cited → ack-bank),
  OR transcript text naming a track/move that no `event`/`llm_invoke` line supports,
  OR a reaction with no preceding detected event. That FAILS the release gate.
- **Idle ≠ fault (Invariant #5):** at idle, `grounded:false` and `cohost_status:IDLE`
  are EXPECTED (no music to ground to). Do not read that as "AI unreachable".

## 4. Why dev-source, not the bundled app

The Tauri shell normally spawns a FROZEN bundled Python sidecar that lags edited
`src/` — so `cargo tauri dev` gives FALSE NEGATIVES on backend changes (a fixed
bug still looks broken; the stale livekit circular-import even fails to boot).
`VIBEMIX_DEV_SIDECAR=1` flips the sidecar resolver (`sidecar.rs:537`) to run repo
source via `uv run python -m vibemix` (override interpreter with
`VIBEMIX_DEV_PYTHON`, repo root with `VIBEMIX_DEV_REPO`). Verify backend wiring on
CURRENT source, never the bundle.
