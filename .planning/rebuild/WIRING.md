# vibemix UI Rebuild — WIRING CONTRACT

> Authoritative UI↔backend wiring inventory for the "The Deck Speaks" full-app
> rebuild. Every surface element below MUST stay connected to the data source /
> IPC channel named here. The 2026-05-25 dead-controls regression happened
> because rebuilt controls were not wired to their IPC handlers — this doc is
> the firewall against repeating it. Grounded in source (tauri/ui/src/) as of
> 2026-05-28. Design target: `mocks/vibemix-rebuild-session.html`.

## 0. Transport topology

| Bus | URL | Who consumes | Frames |
|-----|-----|--------------|--------|
| Primary ws_broadcast | `ws://127.0.0.1:8765` | session (via Rust ws_client → Tauri event bridge), mascot (direct WS), pill (direct WS) | snapshot, status.tick, settings.state, session.mute, recordings.usage, cohost-reaction, mascot.mood_change |
| Debrief sidecar | `ws://127.0.0.1:8766` | debrief window only (`DebriefWsClient`) | session-loaded, chapter-list, drills, tldr-audio, citation-tooltip, error |

**Outbound IPC route:** webview → `emitIpc(type, payload)` / `sendIpcRequest(type, payload, replyType, timeoutMs)` (`src/ipc/client.ts`) → Tauri `invoke("forward_ipc_to_sidecar", { message })` → Rust `ws_client.tx.send` → Python loop. Replies arrive back over the same bus and are delivered via `@tauri-apps/api/event` `listen("ipc:<type>")`.

**IPC contract source of truth:** `src/ipc/messages.schema.json` → codegen (`npm run codegen:ipc`) emits `messages.ts` (types) + `validator.generated.mjs` (ajv, PRE-COMPILED). **Editing the schema REQUIRES re-running codegen** or the validator rejects new fields (see [[feedback_schema_edit_needs_codegen_ipc]]).

## 1. Session (the heart) — main window, bus :8765

**Mount:** `src/session/router.ts::routeSession()` (called from `main.ts` after wizard teardown). Bridge: `src/session/ws-bridge.ts::initSessionBridge()`. State: `src/session/state.ts` (`getSessionState`/`setSessionState`, append rings). Paint: `src/session/render-loop.ts` (rAF projects state → SessionLayout props).

### INBOUND (subscribe → state)
| Channel | Rate | → writes |
|---------|------|----------|
| `ipc.session.snapshot` | 30Hz | meters{music,voice,mic:{rms,peak}}, phase[], phase_now_pct, bpm, drop_pred_bars, track{title,artist,deck,key}, cohost_status, latency_ms, grounded; appends transcript_delta[], midi_events[] |
| `ipc.status.tick` | 1Hz | livekit("ok"\|"connecting"\|"down"), gemini("ok"\|"down"), midi(n\|null), screen("ok"\|"denied") |
| `ipc.settings.state` | on change | voice, mode, skill, genre, output_device_id, output_profile, retention_days, push_to_mute_hotkey, mood, click_through, lighter_blur, muted, `session.mode` |
| `ipc.session.mute` | ack | muted |
| `ipc.recordings.usage` | on change | sessions, bytes_total |
| `ipc.session.cohost-reaction` | event | text, event_id, citation_strip[]{event_id,verb,timestamp_s} — appended to reactions ring (cap 200), paired to transcript by `ts` |

### OUTBOUND (action → IPC)
| UI action | Call | Channel |
|-----------|------|---------|
| change any setting | `sendSettings(field,value)` (ws-bridge) | `ipc.settings.set {field,value}` — allowlist: voice, mode, genre, output_device_id, output_profile, retention_days, push_to_mute_hotkey, mood, click_through, lighter_blur, skill |
| mute toggle | `sendMute(toggle)` | `ipc.session.mute {toggle}` |
| boot perf-pref read | `sendIpcRequest("ipc.settings.get",{},"ipc.settings.state",2000)` | — |
| re-run calibration | `emitIpc("ipc.wizard.start",{})` | — |
| rebind hotkey | `invoke("rebind_hotkey",{newCombo})` | Tauri |
| restart co-host | `invoke("restart_sidecar")` | Tauri |
| mode picker: learn | local `setSessionState({mode:"learn"})` + `invoke("open_learn_window")` + `emitIpc("ipc.session.set_mode",{mode:"learn"})` | Tauri + `ipc.session.set_mode` |
| mode picker: build | local `setSessionState({mode:"build"})` + `invoke("open_library_window")` + `emitIpc("ipc.session.set_mode",{mode:"build"})` | Tauri + `ipc.session.set_mode` |
| mode picker: debrief | local `setSessionState({mode:"debrief"})` + `invoke("open_debrief_window",{sessionDir:""})` + `emitIpc("ipc.session.set_mode",{mode:"debrief"})` | Tauri + `ipc.session.set_mode` |

### "The Deck Speaks" element → source (the rebuild MUST wire these)
| Mock element | Backend source |
|--------------|----------------|
| `.now` hero line + `.ghost` recession | `transcript_delta[]` / `reactions` ring (newest = `.now`, prior = ghosts), keyed by `ts` |
| `.receipt` (`.rule` draw + `.cite` ignite) | `ipc.session.cohost-reaction.citation_strip[]` — verb + timestamp_s; chip click → `invoke("open_debrief_window",{session_dir,deep_link:{eventId,timestampS}})` |
| `.now` dims / silent state | `grounded=false` + no fresh reaction = listening; reaction present = live |
| `.foot bpm` | `snapshot.bpm` |
| `.foot key` (8A) | `snapshot.track.key` (null → hide) |
| `.meter .fill`/`.peak` (live level) | `snapshot.meters.music.{rms,peak}` — apply smoothing 0.16 attack / 0.04 peak-decay / 86% ceiling; hard-stop in silent/fault |
| `.persona` (hype/teach/coach, tap-to-cycle) | read `settings.mood`; tap → `ipc.settings.set{field:"mood"}` |
| `.controls` mute | `sendMute` |
| `.actions` Vibe Engine | `invoke("open_library_window")` |
| `.mode` picker | local optimistic state + `ipc.session.set_mode`; learn/build/debrief also open their owning window |
| status `audio·screen·midi` (silk-dim; red on drop) | `status.tick` {midi,screen} + audio health; `data-mode="fault"` lights the dropped input |
| `data-mode` (live\|silent\|fault) | live=grounded+reaction; silent=grounded, quiet; fault=input down (status.tick livekit/screen down or audio lost) |

## 2. Wizard — main window, bus :8765 (request/response, no persistent subs except status)
- **OUT:** `ipc.permission.check`→`ipc.permission.state`; `ipc.calibration.list_devices`→`device_list`; `ipc.calibration.probe_audio`→`audio_result`; `ipc.calibration.user_heard_tone`; `ipc.calibration.list_windows`→`window_list`; `ipc.calibration.start_midi_listen`→`midi_event`*/`midi_timeout`; `ipc.calibration.smoke_test`→`smoke_test_started`/`smoke_test_done` (30s); `ipc.profile.set_consent`→`consent_state`; `emitIpc("ipc.wizard.done",{output_device_id,controller_profile,target_window_id})`.
- **Tauri:** `read_first_run_state`, `write_first_run_state`, `request_microphone_permission`, `open_microphone_settings`, `open_screen_recording_settings`.
- **IN (persistent):** `ipc.status.tick` → LED badges.

## 3. Settings drawer: main window, overlay on session, bus :8765
- **IN:** reads `getSessionState().settings`; local UI state via `getSettingsUIState()`.
- **OUT:** all mutations → optimistic component repaint + `sendSettings`/direct `emitIpc("ipc.settings.set",{field,value})` (mood/click_through/lighter_blur/skill bypass the allowlist), then self-correct on `ipc.settings.state` echo. Recordings: `ipc.recordings.list`→`list_result`, `ipc.recordings.delete`→`delete_ack`, `invoke("reveal_in_os")`, `invoke("open_input_wav")`. Library: `ipc.library.import`→`import_progress`, `ipc.library.search`→`search_result`, `ipc.library.staleness_action`. Profile: `ipc.profile.view`/`regenerate`/`delete`/`set_consent`. Calibration: `emitIpc("ipc.wizard.start")`. Hotkey: `invoke("rebind_hotkey")`.
- **Lifecycle:** `routeSession()` and dev mock teardown MUST call `unmountSettingsDrawer()` so the drawer shell, backdrop, modal slot, document keydown listener, picker disposers, and settling timer cannot survive a route bounce. Runtime transfer anchors are pinned in `SETTINGS_RUNTIME_WIRES`; group anchors are pinned in `SETTINGS_GROUP_WIRES`.

## 4. Vibe Engine / Viber: separate library window, direct Tauri commands + events
- **Mount:** `library.html` → `src/library/index.ts::mountLibrary()`. Client gateway: `src/library/api.ts`. Mode state: `src/library/state-machine.ts`.
- **IN:** command responses from `library_search`, `library_similar`, `library_curate`, `library_build_set`, `library_chat`, `library_stats`, `library_models`; live events `library://embed-progress`, `library://embed-done`, `library://model-progress`.
- **OUT:** `library_embed_folder`, `library_models`, `library_search`, `library_similar`, `library_curate`, `library_build_set`, `library_chat`.
- **Run ownership:** every user action gets a monotonically increasing run id. Mode switches cancel the active run before changing the visible surface, and stale async completions MUST NOT render results, errors, or Viber turns into the new mode.
- **Boundary guards:** direct command responses stay strict through `normalize*` guards. Live event callbacks drop malformed frames with a warning so a bad progress payload cannot wedge the UI. Embed progress/done handlers also check the current run and mode before repainting.
- **Grounding and research:** `LibraryToolset` keeps per-run `seen` track ids from `search_vibe` and `discover_pool`; playlist/export/transition/cue tools reject invented ids. `web_search` issues per-run source URLs; `fetch_url` rejects any URL not returned by `web_search` in that same run.

## 5. Debrief: separate "debrief" window, bus :8766
- **Open:** `invoke("open_debrief_window",{session_dir,deep_link?})` → Rust spawns `vibemix-core --debrief <path>` + WebviewWindow `debrief.html?session=<path>`. Empty `session_dir`/`sessionDir` resolves to the latest timestamped recording directory under the validated recordings root, which is the live-session fallback for citation chips, "see all", and the debrief mode segment.
- **IN (`DebriefWsClient`, KIND_MAP):** session-loaded{duration_s,genre}, chapter-list{chapters[]}, drills{drills[3]}, tldr-audio{audio_relative_path,duration_s,tldr_sha256}, citation-tooltip{event_id,evidence_text,timestamp,found}, error{reason,message}. Rust events: `sidecar-debrief-crashed`, `vmx-debrief-deeplink{eventId,timestampS}`.
- **OUT:** `sendCitationTooltipRequest(event_id)` → `ipc.debrief.citation-tooltip-request`; `sendEarTestSubmit`; `invoke("read_bravoh_waitlist_opt_in")`/`write_bravoh_waitlist_opt_in`.
- **Boot URL:** query parsing lives in `src/debrief/url-state.ts`; session/deep-link decoding is validated before the window attempts playback or tooltip wiring.

## 6. Pill: "pill" transparent always-on-top window (280×44), bus :8765
- **IN:** `snapshot` → meters.voice.{rms,peak} (dual-path: flat `voice`/`peak` OR nested `meters.voice`), cohost_status; `cohost-reaction`/`ipc.session.cohost-reaction` → text + citation_strip. State machine `src/pill/state-machine.ts` (IDLE→LISTENING→SPEAKING→EXPAND, 5min collapse).
- **OUT:** `invoke("set_pill_height",{height})` for collapsed/peek/expanded window bounds; citation chips call `open_debrief_window` with empty-session latest fallback + deep link; next-suggestion feedback and alternate picks call `forward_ipc_to_sidecar`.
- **Bounds:** renderer-side height math clamps bad DOM measurements before `set_pill_height`; Rust still clamps the final window height. Non-finite voice RMS, peak, and citation timestamps are ignored or treated as silence before rendering.
- **Redesign rule:** `pill.shell`, `pill.wave`, `pill.expand`, `pill.reaction`, `pill.decks`, `pill.peek`, and runtime `pill.next` anchors must survive any visual transfer. Keep the state machine and geometry persistence; do not turn the pill into a static badge.

## 7. Mascot: "mascot" transparent always-on-top window, bus :8765, observe-only
- **IN:** `snapshot` (bpm, bpm_confidence, downbeat_phase, mood), `ipc.mascot.mood_change{mood,previous_mood,at}`, event frames via `event-dispatcher.ts` (HEARTBEAT/KAAN_SPOKE/DROP_UPCOMING…). State machine + Three.js renderer crossfade.
- **OUT:** none. `mood` + `lighter_blur` mirrored from settings.

## 8. REBUILD WIRING RULES (the firewall — verify each before "done")
1. **Every interactive control must trace to an OUTBOUND row above.** A button with no `emitIpc`/`sendIpcRequest`/`invoke` is a dead control. (Root cause of the 2026-05-25 regression.)
2. **Inbound subscriptions are set up at mount, before first paint** — `initSessionBridge()` equivalent must subscribe to all 6 session channels or the deck renders empty.
3. **Settings repaint optimistically at the component edge, then self-correct on echo** — the persisted source remains `ipc.settings.state`, but rocker/picker/toggle affordances must visibly land on click so the UI never feels dead. The next frame still reads back from `SessionState`.
4. **Schema edits → `npm run codegen:ipc`** (regenerates `validator.generated.mjs`); Python parity alone is insufficient.
5. **Three-state enum (live|silent|fault) is driven by real signals** — never a hardcoded/boolean stand-in. live = grounded + recent reaction; silent = grounded, no reaction; fault = `status.tick` input down or audio lost.
6. **The signature gesture re-fires per reaction** — keyed off each new `cohost-reaction`/transcript `ts`, with a forced reflow / element re-key (CSS won't replay on a present class). Constants: rise 400 / rule-draw 520@360 / cite-ignite 380@900 ms.
7. **Meter telemetry uses the smoothing envelope** (0.16 / 0.04 / 86%) on real RMS, hard-stopped in silent/fault.
8. **KNOWN-OPEN from [[project_viber_ship_handoff]]:** voice/mode/output settings don't apply live in the LiveKit path (cascade-era hooks absent); mood/skill DO. `grounding` wiring gap in `__main__`. These are backend gaps the UI rebuild can't fix but must not regress around.

## 9. Claude mock transfer contract

Claude-generated mockups are source material, not an alternate app. Transfer is allowed only through the wiring rows above:

1. Identify the owning surface and data contract before moving visuals (`SessionLayout` props, settings state, library command, debrief frame, pill frame).
2. Copy structure/classes/tokens only after mapping every interactive element to an OUTBOUND row and every dynamic label to an INBOUND row.
3. Do not add raw, unregistered IPC names. New channels start in `messages.schema.json`, then codegen, then Python/Rust handlers, then UI.
4. Keep mock-only affordances behind `?mock=1` or fixture files. Production routes must consume real WS/IPC payloads or render an honest empty/error state.
5. Pill redesign gets the same treatment: preserve bus `:8765`, consume `snapshot`/`cohost-reaction`/`next_suggestion`, and keep geometry persistence. Visual polish can change; the state machine cannot silently become a static badge.
6. Active mock iteration files may live under `mocks/iterations/`, but production transfer still lands through `src/mock-transfer/contract.ts` anchors and the surface rows above. The settings drawer source is tracked separately via `SETTINGS_MOCK_SOURCES`.
