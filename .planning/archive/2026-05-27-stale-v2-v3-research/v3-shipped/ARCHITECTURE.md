# Architecture Research — v2.0 Integration

**Domain:** Subsequent-milestone integration into a 3-process Tauri + Python-sidecar + remote-FastAPI app
**Researched:** 2026-05-14
**Confidence:** HIGH on existing-architecture surface (codebase maps + Phase 11 STATE.md), MEDIUM on new-component placements (some are first-time-integrated, e.g. AX bridge), LOW on viral-demo Tauri overlay parity (cross-Space behavior open per `tauri#11488`)

---

## I. EXECUTIVE SUMMARY

v2.0 adds ~10 feature buckets to an already-shipped 3-process architecture. The integration thesis:

1. **One process boundary, four kinds of work.** Tauri shell (Rust) owns OS-permission-bound work + window/overlay geometry. Python sidecar owns audio/DSP/AI/state. Bravoh proxy owns Gemini key + rate limit. Every new feature picks ONE of those three homes; never spans (AX bridge is the canonical case — sits in Rust, NOT sidecar, per `tauri#8329`).
2. **The IPC schema is the load-bearing contract.** 19 messages → ~38 messages after v2.0. Schema parity drift gate (`scripts/check_ipc_schema.py`) blocks merge if Python dataclass count diverges from `oneOf` count diverges from TypeScript codegen.
3. **MusicState stays the single writer @10Hz.** Every new sensor (Mixxx OSC if it ships, library hit, citation-grounded event) routes through `state_refresh_loop`. The Evidence registry is a SIBLING write-target alongside MusicState, fed from the same loop tick — never a separate writer.
4. **No new process types.** Three processes today (shell + sidecar + proxy) and three at v2.0 close. New `--debrief <dir>` mode is a sidecar FLAG, not a new daemon. New `--wizard` precedent (Phase 11 Wave 4) is the pattern.
5. **The overlay is a SECOND Tauri webview window inside the existing shell, NOT a new app.** Label = "overlay", capability allowlist extended, AX call runs in Rust parent.

---

## II. EXISTING ARCHITECTURE — BASELINE (post-Phase 14)

```
                                                       ┌──────────────────────┐
                                                       │   api.altidus.world  │
                                                       │ FastAPI proxy        │
                                                       │ JWT install-UUID     │
                                                       │ slowapi 60rpm/2krpd  │
                                                       │ Routes: SSE LLM +    │
                                                       │   /audio/speech +    │
                                                       │   /register +/healthz│
                                                       └──────────▲───────────┘
                                                                  │ HTTPS
                                                                  │ (cascade only)
┌────────────────────────────────────┐    WS bus     ┌────────────┴──────────────┐
│       Tauri Rust SHELL             │  127.0.0.1:8765│      Python SIDECAR        │
│  src-tauri/src/main.rs             │◀──────────────▶│  vibemix-core-<triple>     │
│  • mascot_window.rs (label=mascot) │   ipc.* JSON   │  (PyInstaller --onedir)    │
│  • ws_client.rs                    │  19 message    │  • runtime/__main__.py     │
│  • permissions.rs (TCC plumbing)   │  family        │    --wizard | live | (new: │
│  • sidecar lifecycle (Sidecar      │                │    --debrief <dir>)        │
│    plugin)                         │                │  • runtime/ws_bus.py       │
│  • capabilities/default.json       │                │    (WizardBus + Broadcast) │
│  • updater (latest.json, ed25519)  │                │  • state.MusicState (only  │
│                                    │                │    writer @10Hz in         │
│  Windows:                          │                │    state_refresh_loop)     │
│  • mascot transparent always-top   │                │  • events.EventDetector    │
│  • wizard (Workbench fonts +       │                │  • agent.DJCoHostAgent     │
│    cdj-whisper-v5 tokens.css)      │                │    (LiveKit AgentSession,  │
│                                    │                │     google.LLM + google.   │
│                                    │                │     beta.gemini_tts.TTS)   │
└──────────┬─────────────────────────┘                │  • audio/_audio_macos.py + │
           │ Three.js + Canvas2D                       │    _audio_windows.py       │
           │ tauri/ui/src/                              │  • screen/_screen_macos.py │
           ▼                                            │    + _screen_windows.py   │
   ┌─────────────────────────┐                          │  • midi.* (10 SKUs +      │
   │  mascot WebGL (Three.js)│                          │    generic fallback)      │
   │  21 GLB clips           │                          │  • prompts.* (6-cell     │
   │  AnimationMixer         │                          │    matrix + negative-dict │
   │  flat priority router   │                          │    + scorecard)           │
   └─────────────────────────┘                          │  • recorder.VoiceRecorder │
                                                        │    (input.wav/voice.wav/  │
                                                        │     events.jsonl)         │
                                                        └────────┬──────────────────┘
                                                                 │
                                       BlackHole/WASAPI loopback │
                                       Quartz/EnumWindows screen │
                                       mido MIDI                 │
                                       nowplaying-cli/SMTC       │
                                                                 ▼
                                                          [DJ Software]
```

**Existing IPC family (19 messages, Phase 11 W0)** — covers wizard lifecycle (permission.check, list_devices, probe_audio, list_windows, start_midi_listen, smoke_test, wizard.done, wizard.start), live status (status_tick, sidecar_ready, sidecar_crashed) and the 8 W4 additions. Single source of truth: `tauri/ui/src/ipc/messages.schema.json` (Draft-07). Wrapper count (19) hard-asserted by `scripts/check_ipc_schema.py`.

**Existing invariants (non-negotiable, preserved by v2.0):**

| Invariant | Where pinned | What v2.0 must not break |
|-----------|--------------|---------------------------|
| MusicState single writer @10Hz | Phase 6 D6, `state_refresh_loop` | New sensors register OUTPUT into the same loop; never start a second writer |
| `_HAS_VISION`/`_HAS_WS`/`_HAS_QUARTZ` feature flags | Phase 2 (anti-pattern fix) | New optional sensors (sqlite-vec, fpcalc, pyrekordbox) follow the same `_HAS_*` import-guard pattern |
| No pydantic in `src/vibemix/ui_bus/` | Phase 6 D-Area-4.4 / Phase 11 W0 | New IPC wrappers use `@dataclass(frozen=True, slots=True)` + `jsonschema` |
| 19 wrappers == 19 oneOf == 19 TS exports | `scripts/check_ipc_schema.py` | Updated to `38 == 38 == 38` after v2.0 |
| AIza scan @ build time, 0 matches | Phase 11 W1 | New bundled assets (ack-bank OPUS, sqlite-vec dylib) re-scan; must stay 0 |
| Bundle ID `world.bravoh.vibemix` | Phase 11 W1 A8 | TCC permissions break on any change — locked |
| `cohost_v4.py`/POC files untouched | All phases | Reference port-from only, never edit |
| LiveKit AgentSession `session.output.audio` BEFORE `session.start` | Phase 4 v4:2030-2033 | Predictive firing + cancel-and-refire don't reorder this |
| `allow_interruptions=False` at session level | Phase 4 invariant | `interrupt(force=True)` is the programmatic backdoor; user-mic gate untouched |

---

## III. NEW IPC MESSAGES (additions to `messages.schema.json`)

v2.0 adds **19 new ipc.\* messages** → schema count moves from 19 to 38, asserted by `scripts/check_ipc_schema.py`. Drift-gate updates from `assert wrapper_count == 19` to `assert wrapper_count == 38`.

| # | Message | Direction | Payload sketch | Why a new message (can't reuse) |
|---|---------|-----------|----------------|-------------------------------|
| 1 | `ipc.session.event` | sidecar → shell | `{type: "KICK_SWAP"|"SUB_LAYER_ARRIVAL"|..., t_session: 423.1, t_wall, audible_deck: "A", citation_handles: ["ev:KICK_SWAP@..."], extras: {...}}` | Today `status_tick` carries levels only; the shell needs **typed event surfacing** for v2 UI features (overlay highlight, mascot anticipation, debrief timeline scrubbing). Status_tick is high-frequency level data, events are sparse + typed. |
| 2 | `ipc.session.citation` | sidecar → shell | `{response_id, mode: "live"|"debrief", validated: bool, valid_citations: 3, invalid_citations: 0, stripped_sentences: [{sentence, reason}], slop_ratio: 0.04}` | Carries linter telemetry for the eventual transparency-UI ("vibemix kept 47 of 52 reactions"). Decouples linter signal from event signal. |
| 3 | `ipc.session.ack_fired` | sidecar → shell | `{ack_sample: "drop_hit/yes_03.opus", t_session, in_response_to_event: "PHASE", reason: "ttft_predicted_slow"|"linter_fallback"|"normal"}` | Shell logs ack-bank fires for the dev panel + debug overlay. Distinct from voice playback because acks bypass LiveKit TTS path. |
| 4 | `ipc.session.predicted_fire` | sidecar → shell | `{handle_id, event: "PREDICTED_DROP", deadline_at_session_t, abort_at_session_t}` | New for predictive firing — shell needs visibility into "we fired early, waiting for confirmation" for debug panel + mascot anticipation gating. |
| 5 | `ipc.session.cancel_refire` | sidecar → shell | `{cancelled_handle_id, new_event: "KICK_SWAP", reason: "priority_supersede"}` | Cancel-and-refire visibility. Shell shows "preempted by higher-priority event" in debug. |
| 6 | `ipc.overlay.highlight` | shell → overlay window (intra-shell) AND sidecar → shell | `{element_id: "deck.a.mid_eq", deck: "A", hold_ms: 2500, ring_color: "amber"|"warn"|"info"}` | Shell-internal AND sidecar-originated. Sidecar fires after linter validates the `point` field of Gemini reply; shell forwards to overlay webview. Cannot reuse session.event (this is an OUTPUT command, not a SENSED event). |
| 7 | `ipc.overlay.dismiss` | shell → overlay | `{element_id, reason: "timeout"|"manual"|"window_hidden"}` | Overlay receives explicit dismiss when AX query says "djay no longer foreground" mid-hold. |
| 8 | `ipc.overlay.window_bounds` | shell-internal | `{app: "djay_pro", x, y, w, h, scale_factor, monitor_id}` | Window-tracking heartbeat from Rust parent to overlay webview @10Hz. Pure intra-shell (Tauri event bus), but specified in IPC schema for type-discoverability + test parity. |
| 9 | `ipc.overlay.ax_position` | shell → sidecar (response to query) | `{element_id, screen_rect: [x,y,w,h]|null, source: "ax"|"coord_map"|"none"}` | Sidecar requests AX position via shell (Rust parent does the AX call, sidecar can't per `tauri#8329`). Sidecar uses the rect to decide whether to issue overlay.highlight or fall back silently. |
| 10 | `ipc.library.import_start` | shell → sidecar | `{xml_path, replace_existing: bool}` | Starts pyrekordbox XML import workflow. Distinct from generic file ops because it triggers a multi-second worker task. |
| 11 | `ipc.library.import_progress` | sidecar → shell | `{job_id, tracks_parsed: N, total_estimated: M, current_track: "Boys Noize - Mvinline"}` | Progress bar for the 5-20s indexing flow. Cannot piggyback on status_tick (which is level-data 30Hz; import is event-driven). |
| 12 | `ipc.library.import_done` | sidecar → shell | `{job_id, tracks_total: 8427, duration_s: 12.4, db_path: "..."}` | Final state of import job. |
| 13 | `ipc.library.lookup` | sidecar → shell (response query, optional UX surface) | `{title, artist, confidence, track_id|null}` | Surfaces lookup result for debug + future UX ("we matched 'X' to your library track 'Y' with 87% confidence"). Tier mapping defined by F-research confidence bands (0.9/0.7/<0.7). |
| 14 | `ipc.library.embed_progress` | sidecar → shell | `{job_id, tracks_embedded: N, total: M, est_remaining_s, current_track, mode: "drop"|"breakdown"}` | Separate from import_progress — embedding is a SECOND pass after XML import (or auto-watch-detected new tracks). Different cadence (~30 embeds/min on free tier, hours-long), different UX. |
| 15 | `ipc.library.embed_done` | sidecar → shell | `{job_id, tracks_embedded, errors_count, total_cost_usd}` | Surfaces completion + cost transparency. |
| 16 | `ipc.debrief.start` | shell → sidecar | `{session_dir: "/Users/.../recordings/20260514-203400"}` | Triggers `--debrief` mode call on a sibling sidecar process (sidecar respawns with `--debrief` flag — see §V). |
| 17 | `ipc.debrief.status` | sidecar (debrief instance) → shell | `{stage: "loading"|"validating"|"calling_gemini"|"linting"|"voicing", pct: 42}` | Sidecar-debrief reports stage progress; UI shows spinner with stage label. |
| 18 | `ipc.debrief.result` | sidecar → shell | `{session_dir, debrief_md_path, debrief_json_path, voiced_wav_path, chapters_count, slop_ratio_per_chapter: [0.05, 0.12, 0.20, 0.08]}` | Final result paths + per-chapter slop ratio (transparency surface). |
| 19 | `ipc.mascot.tick` | sidecar → mascot (intra-shell forward) | `{music_rms, voice_rms, mic_rms, bpm, beat_phase, anticipation: {event_class, fires_in_ms}|null, emote_tag: "[hype]"|null}` | EXTENDS existing 30Hz status-tick → mascot bridge. Adds beat-phase + anticipation hint + emote-tag. Today the mascot listens on 8765 directly to a "snapshot" payload that pre-dates the IPC schema. v2.0 promotes it to first-class schema entry — same payload still flows over WS bus but is now wrapper-validated. |

**Net schema delta:** 19 → 38 wrappers. Update `scripts/check_ipc_schema.py` assertion. Regenerate `messages.ts`. Update `_serialize` `tuples_to_lists` for new payload shapes if any contain tuples. Lock the count in both Python `__dataclass_fields__` introspection AND TS `VibemixIPCMessages` union.

---

## IV. NEW COMPONENTS — Module/Class Map

### IV.A Sidecar Python additions (`src/vibemix/`)

```
src/vibemix/
├── events/
│   ├── base.py                  [MOD: extract Detector dataclass + BASELINE_DETECTORS]
│   ├── router.py                [NEW: GenreRouter class — owns active_genre + active_detectors swap]
│   ├── genres/
│   │   ├── __init__.py          [NEW: GENRE_REGISTRY = {"hard_tek": ..., "techno": ..., "ambiguous": ...}]
│   │   ├── hard_tek.py          [NEW: 8 detectors — KICK_SWAP, SUB_LAYER_ARRIVAL,
│   │   │                              DISTORTION_CLIMB, BREAKDOWN_KICK_KILL,
│   │   │                              REENTRY_KICK_LAND, KICK_DENSITY_SHIFT,
│   │   │                              ACID_LINE_ENTRY, PHRASE_BOUNDARY]
│   │   ├── techno.py            [NEW: placeholder for v1.1+, empty DETECTORS at v2.0]
│   │   └── generic.py           [NEW: fallback when active_genre = ambiguous]
│   └── _impl/                   [NEW: shared DSP primitives used by genre detector funcs]
│
├── grounding/                   [NEW PACKAGE — central to anti-slop thesis]
│   ├── __init__.py
│   ├── evidence.py              [NEW: Evidence dataclass, EvidenceRegistry — O(1) in-memory
│   │                                   keyed by (source, key), holds list[t_session]]
│   ├── citation_linter.py       [NEW: CitationLinter class with validate() / strip_unsourced();
│   │                                  CITATION_RX + SENTENCE_RX module constants]
│   └── prompts.py               [NEW: per-mode prompt fragments (live/debrief/library/genre)
│                                       that bake the citation grammar into system instructions]
│
├── library/                     [NEW PACKAGE — v2.0 library intelligence]
│   ├── __init__.py
│   ├── rekordbox_xml.py         [NEW: RekordboxLibrary class — XML import + SQLite store +
│   │                                  fuzzy lookup (4-tier confidence ladder)]
│   ├── embed.py                 [NEW: Bravoh service.py lifted 80% verbatim — _embed_audio_sync,
│   │                                  _l2_normalize, retry-on-SSL/429, 80s audio cap]
│   ├── store.py                 [NEW: LibraryStore abstraction over sqlite-vec; fallback to
│   │                                  numpy.float32.tobytes() blob if sqlite-vec wheel breaks]
│   ├── watcher.py               [NEW: watchdog FSEvents/ReadDirectoryChangesW; one embed worker]
│   ├── fingerprint.py           [NEW: chromaprint via bundled fpcalc; dedupe on move/copy]
│   ├── metadata.py              [NEW: mutagen ID3/Vorbis/MP4 reader; pyrekordbox optional layer]
│   └── camelot.py               [NEW: 30 LoC homegrown Camelot wheel math]
│
├── latency/                     [NEW PACKAGE — latency stack]
│   ├── __init__.py
│   ├── ack_bank.py              [NEW: AckBank class — load ~40 OPUS samples, rotation deque,
│   │                                  fire_ack() pushes decoded PCM to PlaybackQueue,
│   │                                  bypasses LiveKit TTS path]
│   ├── cache.py                 [NEW: CachedLLM subclass of google_llm.LLM that injects
│   │                                  cached_content into extra_kwargs; cache lifecycle
│   │                                  manager (create at session start, refresh @ 50min)]
│   ├── predictor.py             [NEW: BuildupPredictor + predicted_drop_watcher coroutine;
│   │                                  consumes state.buildup_score + state.predicted_drop_in_sec;
│   │                                  manages pending_predicted handle + playback gate]
│   └── interrupt.py             [NEW: thin wrapper around SpeechHandle.interrupt(force=True)
│                                       with last_cancel_ts cooldown (8s); falls back to _cancel()]
│
├── overlay/                     [NEW PACKAGE — sidecar half of overlay highlight]
│   ├── __init__.py
│   ├── elements.py              [NEW: element vocabulary parser (12 IDs); validates Gemini
│   │                                  `point` field against allowlist]
│   └── coord_map.py             [NEW: loads tauri/ui/src/overlay/elements.json
│                                       (percent-of-window-rect); falls back to AX query via shell]
│
├── debrief/                     [NEW PACKAGE — post-session debrief]
│   ├── __init__.py
│   ├── __main__.py              [NEW: invoked when sidecar started with --debrief <dir>;
│   │                                  loads events.jsonl + input.wav, fires single Gemini call,
│   │                                  applies linter sentence-level, voices TL;DR via Gemini TTS]
│   ├── pipeline.py              [NEW: DebriefPipeline class — orchestrates load/validate/
│   │                                  prompt/lint/voice stages, emits ipc.debrief.status]
│   ├── prompts.py               [NEW: SBI/STAR-AR pedagogy prompt template (per Bucket E)]
│   └── profile.py               [NEW: ~2KB long-term DJ profile JSON read/write at
│                                       $APPDATA/vibemix/dj_profile.json]
│
├── mascot/                      [NEW PACKAGE — sidecar half of mascot anticipation]
│   ├── __init__.py
│   └── anticipation.py          [NEW: maps Event.type → anticipation hint payload;
│                                       fires ipc.mascot.tick with anticipation field BEFORE
│                                       Gemini round-trip; bridges EventDetector → mascot
│                                       state machine layer 1]
│
└── runtime/
    ├── __main__.py              [MOD: add --debrief <dir> flag dispatch + arg parsing]
    └── coach_loop.py            [MOD: orchestrates ack-bank fire, predictive firing,
                                        evidence registration, citation lint, cancel-refire;
                                        replaces v4 inline coach loop with composable pipeline]
```

### IV.B Tauri shell additions (Rust + TS)

```
tauri/
├── src-tauri/src/
│   ├── main.rs                  [MOD: register new commands, spawn overlay window builder,
│   │                                  spawn debrief-sidecar lifecycle]
│   ├── mascot_window.rs         [MOD: same builder pattern, ANOTHER window for overlay]
│   ├── overlay_window.rs        [NEW: clone of mascot_window.rs with label="overlay",
│   │                                  decorations=false, set_ignore_cursor_events(true)]
│   ├── ax_bridge.rs             [NEW: pyobjc-equivalent in Rust — wraps macOS
│   │                                  AXUIElementCopyAttributeValue, queries by role+label,
│   │                                  returns screen rect (or None). Called from
│   │                                  forward_ipc_to_sidecar for ipc.overlay.ax_position.
│   │                                  MACOS ONLY — `#[cfg(target_os = "macos")]`]
│   ├── window_tracker.rs        [NEW: WindowTracker service — Quartz/EnumWindows poll @10Hz,
│   │                                  emits ipc.overlay.window_bounds events to overlay webview]
│   ├── debrief.rs               [NEW: DebriefManager spawns a sibling sidecar with --debrief
│   │                                  flag (separate child process from live-runtime),
│   │                                  forwards ipc.debrief.* over a dedicated WS bus port (8766)
│   │                                  to avoid colliding with live-runtime's 8765]
│   ├── library.rs               [NEW: forward ipc.library.* between shell UI and sidecar;
│   │                                  also dispatches FilePicker.open() for XML import drag-drop]
│   ├── updater.rs               [NEW: Tauri Updater plugin wiring — ed25519-signed latest.json
│   │                                  pulled from api.altidus.world/vibemix/updates/]
│   └── capabilities/default.json [MOD: add overlay window + 12 new app commands
│                                         (ax_query, request_overlay_highlight, dismiss_overlay,
│                                          start_debrief, list_recordings, delete_recording,
│                                          import_library_xml, open_library_path, ...)]
│
└── ui/src/
    ├── overlay/                 [NEW DIR — overlay webview app]
    │   ├── overlay.html         [NEW: lean HTML — single full-screen canvas + element-ring CSS]
    │   ├── overlay.ts           [NEW: subscribeIpc("ipc.overlay.highlight"), drives the
    │   │                              Canvas 2D ring animation; subscribes window_bounds for
    │   │                              positioning, dismisses on .dismiss]
    │   ├── elements.json        [NEW: 12 hand-mapped elements as {id, x_pct, y_pct, r_pct}
    │   │                              + AX query hints {role: "AXSlider", label: "Mid EQ Deck A"}
    │   │                              per djay Pro v5; bundled in installer]
    │   └── ring.css             [NEW: ~50 LOC — amber radial gradient pulse + fade keyframes]
    │
    ├── debrief/                 [NEW DIR — debrief UI surface]
    │   ├── DebriefView.ts       [NEW: receives ipc.debrief.result, renders 4-chapter markdown,
    │   │                              clickable timeline (jumps voiced WAV playback), per-chapter
    │   │                              slop ratio bar]
    │   └── debrief.css          [NEW: cdj-whisper-v5 chrome, glass panels, amber accents]
    │
    ├── library/                 [NEW DIR — library import UX + browser]
    │   ├── LibraryImportWizard.ts [NEW: drag-drop XML, file picker fallback, progress bar
    │   │                                wired to ipc.library.import_progress]
    │   ├── LibraryBrowser.ts    [NEW: simple table over tracks (title/artist/bpm/key/rating),
    │   │                              search + filter; not the demo wow surface, just functional]
    │   └── library.css          [NEW]
    │
    ├── mascot/
    │   ├── types.ts             [MOD: add LayerState (mood/anticipation/speak/effect),
    │   │                              extend MascotState to per-layer]
    │   ├── state-machine.ts     [MOD: refactor flat → 4-layer additive; planTransition()
    │   │                              becomes per-layer; cross-layer overlap is the design
    │   │                              point, not the bug]
    │   ├── renderer.ts          [MOD: Three.js multi-action mixer + Hips procedural bob
    │   │                              driver in tick() reading state.bpm + state.beat_phase
    │   │                              from ipc.mascot.tick]
    │   ├── asset-loader.ts      [MOD: AnimationUtils.makeClipAdditive() pass for new prep_*
    │   │                              + talk_* + react_* clips]
    │   ├── event-dispatcher.ts  [MOD: fire prep_* on event class IMMEDIATELY (T=0),
    │   │                              before Gemini round-trip; subscribe ipc.session.event]
    │   └── manifest.json        [MOD: register 8 new clips (prep_lean_listen/anticipate/
    │                                  settle/head_turn_a/b + talk_loop_energetic_v2 +
    │                                  react_celebrate_alt + dance_alt3)]
    │
    ├── settings/                [NEW DIR (or MOD existing) — settings drawer surfaces]
    │   ├── LatencyPanel.ts      [NEW: "Predictive firing" toggle, "Ack bank rotation rate"]
    │   ├── LibraryPanel.ts      [NEW: import status, last-refreshed, "Re-import" button]
    │   ├── OverlayPanel.ts      [NEW: "Show djay overlay" toggle, AX permission status check]
    │   └── PrivacyPanel.ts      [NEW: "Show slop ratio" toggle, retention policy days]
    │
    └── recording/               [NEW DIR — recording browser + retention]
        ├── RecordingBrowser.ts  [NEW: list ~/Library/.../recordings/*, click → open dir,
        │                              "Generate Debrief" button → ipc.debrief.start]
        └── RetentionPolicy.ts   [NEW: settings — keep last N days/sessions, auto-delete worker]
```

### IV.C Bundled assets (ship in installer)

| Asset | Path inside bundle | Size | Notes |
|-------|-------------------|------|-------|
| 40 OPUS ack samples | `_internal/acks/{drop_hit,track_change,mix_move,silence_break,generic_filler}/*.opus` | ~5 MB | Generated once with Achird voice; regenerate on Gemini TTS model bump |
| `elements.json` djay Pro v5 | `_internal/overlay/elements.json` | ~5 KB | Hand-mapped percentage coords + AX hints; ships in installer, refreshed per djay major version |
| sqlite-vec extension | `_internal/sqlite_vec/vec0.{dylib,dll}` | ~500 KB | Bundled via PyInstaller `binaries=` for sqlite_vec wheel mac+win |
| Chromaprint `fpcalc` binary | `_internal/fpcalc/{fpcalc,fpcalc.exe}` | ~200 KB | Bundled mac+win; same pattern as nowplaying-cli |
| ffmpeg binary | `_internal/ffmpeg/{ffmpeg,ffmpeg.exe}` | ~20 MB | For pydub MP3 transcode on Windows (mac uses afconvert fallback) |
| 8 new mascot GLB clips | `tauri/ui/public/mascot/` | ~3 MB | Author with idle-zero lower-body delta for additive blending |

**Build-time AIza scan must include these new asset trees.** `scripts/build_sidecar.py:assert_no_aiza_leak` already walks recursively — no scan-spec change needed.

---

## V. MODIFIED EXISTING COMPONENTS

| Component | File | Modification | Tests to update | Invariants preserved |
|-----------|------|--------------|-----------------|---------------------|
| `MusicState` dataclass | `src/vibemix/state/music_state.py` | +4 fields: `buildup_score: float`, `predicted_drop_in_sec: float`, `beat_phase: float` (0..1), `active_genre: str = "hard_tek"`. ALL with backward-compat defaults. | `tests/state/test_music_state.py` adds field-default checks; Phase 6 golden-equivalence tests stay green (default values match v4 behavior) | Single-writer @10Hz; defaults make old callers safe |
| `state_refresh_loop` | `src/vibemix/runtime/state_refresh_loop.py` | Calls `_update_buildup_prediction()`, `_update_beat_phase()` each tick. Writes to MusicState. Also calls `evidence_registry.register(...)` for each detected event AND audio-feature tick. | New unit test `test_state_refresh_evidence_registration` asserts every TRACK_CHANGE/PHASE/MIX_MOVE/etc. emit produces matching Evidence entry within same tick | @10Hz invariant; single-writer invariant; no separate Evidence-writer coroutine |
| `EventDetector` | `src/vibemix/events/event_detector.py` | Refactor `detect()`: layer 1 = BASELINE_DETECTORS (TRACK_CHANGE/PHASE/MIX_MOVE/HEARTBEAT — v4 verbatim), layer 2 = `router.active_detectors()` (genre-specific). Shared `ctx: dict` for paired-event coordination. `_fire()` ALSO calls `evidence_registry.register(Evidence(source="ev", key=ev.type, t_session=now))` synchronously. | `tests/events/test_event_detector.py` adds 12-15 cases for the 8 Hard Tek detectors + 5 cases for genre swap behavior + golden-equivalence with v4 for 6 baseline event types | v4 baseline behavior byte-identical when `active_genre == "hard_tek"` AND no genre-specific detector fires; cooldown machinery unchanged |
| `AudioBuffer.snapshot_features` | `src/vibemix/audio/buffer.py` | +4 fields: `kick_centroid`, `kick_harmonic_ratio`, `kick_crest`, `flatness_100_8k`. New method `estimate_bpm_and_phase()` returns `(bpm, phase_offset_sec)` band-limited 40-120Hz autocorr. | Existing buffer tests stay green; new tests in `test_kick_band_features.py` + `test_bpm_phase.py` against pinned reference WAVs | Zero-allocation invariant on `push` path (Phase 2 ring-buffer fix); FFT cost stays under 25ms/tick |
| `AICoach.build_prompt` | `src/vibemix/agent/ai_coach.py` | Reads `state.active_genre`, dispatches to `vibemix/prompts/genres/<genre>.py` for genre-specific event fragments. Adds citation-grammar block to system instruction (v1.0 prompt-only seeding). | `tests/agent/test_ai_coach.py` adds parametrized golden tests per (genre, event_type) cell | v4 task-strings byte-identical when (genre="hard_tek", event_type in v4-set); phase= omission rule (v4:1350-1351 anti-hallucination) preserved |
| `DJCoHostAgent` | `src/vibemix/agent/dj_cohost.py` | `llm_node` reads `state.cached_content_name` from session-start cache; injects via `extra_kwargs={"cached_content": ...}`. On Gemini response complete, runs `CitationLinter.validate()` BEFORE handing to TTS. On linter strip-all in live mode, suppresses response and triggers `AckBank.fire_ack()` instead. | Integration smoke test `test_dj_cohost_with_linter` asserts (a) cache hit metric > 0, (b) stripped response triggers ack-bank fire | LiveKit pipeline invariant (session.output.audio assigned before session.start); single in-flight via trigger_state |
| `coach_loop` | `src/vibemix/runtime/coach_loop.py` | Rewritten as composable pipeline: detect → register evidence → check predictive → check cancel-refire → fire ack-bank (if predicted-slow) → fire generate_reply (with cached_content) → linter validate → publish via ipc.session.event + ipc.session.citation | Full re-author of coach-loop tests; legacy `test_coach_loop_basic.py` retired | One-in-flight invariant via `trigger_state["in_flight"]`; cancel budget cap (1/8s) enforced |
| `ws_bus.py` `BroadcastBus` | `src/vibemix/runtime/ws_bus.py` | Adds `publish_event(ipc_msg)` that wraps `parse_message` validate-then-broadcast for the new typed-event family. Mascot still receives the 30Hz snapshot; new clients (overlay HTML, debrief UI) subscribe to additional ipc.* topics. | New tests in `tests/ui_bus/test_typed_event_broadcast.py` | 30Hz mascot contract byte-for-byte preserved |
| Mascot `state-machine.ts` | `tauri/ui/src/mascot/state-machine.ts` | Refactor flat priority router → 4-layer machine. `MachineState.mood / anticipation / speak / effect` replaces `MachineState.current`. `planTransition` becomes per-layer. | Existing 4 test files in `tauri/ui/src/mascot/*.test.ts` get rewritten — preserve transition golden cases but assert per-layer | Block-rule semantics (lower priority can't replace higher) preserved within a layer; cross-layer is the new freedom |
| Mascot `renderer.ts` | `tauri/ui/src/mascot/renderer.ts` | Multi-action concurrent play with `AnimationUtils.makeClipAdditive`; Hips bone procedural bob in `tick()`. | `tauri/ui/src/mascot/renderer.test.ts` adds two-action active-at-once cases; hip-bob amplitude oracle on synthetic BPM input | 60fps perf budget (Phase 13 verified ~5ms/frame on M2; +1-2ms estimated for additive blending) |
| `scripts/check_ipc_schema.py` | `scripts/check_ipc_schema.py` | Update assertion: `assert wrapper_count == 38 and oneof_count == 38 and ts_export_count == 38`. | Same script self-test must update | Drift-detection mechanism unchanged; just count bump |
| `scripts/build_sidecar.py` | `scripts/build_sidecar.py` | New include for `acks/`, `overlay/elements.json`, `sqlite_vec/`, `fpcalc/`, `ffmpeg/`. PyInstaller `binaries=` entries added in `.spec` files. | Test `test_build_sidecar_assets.py` asserts each new tree lands under `_internal/` | AIza scan stays at 0 matches across new asset trees |
| Tauri `capabilities/default.json` | `tauri/src-tauri/capabilities/default.json` | Add window allowlist for label="overlay"; add ~12 new app command identifiers. | Capability regression-test grep for each command name | Tauri 2.x auto-allow model for `#[tauri::command]` preserved; description-field doc convention from Phase 11 W4 maintained |
| `cohost_v4.py` POC | `cohost_v4.py` | **NOT TOUCHED.** Reference port-from only. Hard rule (Phase 3 G10 / all-phase gate). | n/a | POC G5 gate still passes (`test_g5_poc_files_untouched`) |

---

## VI. DATA FLOW — TRACE WALKS

### VI.A KICK_SWAP fire → grounded → linted → played

```
Step              Time     Process       Component             What happens
────────────────  ──────   ──────────    ──────────────        ─────────────────────────
T+0ms             T=0      Sidecar       AudioBuffer.push      sounddevice callback pushes 16kHz PCM frame
                                          (audio thread)        to ring (zero-alloc per Phase 2)

T+~50ms           T=50     Sidecar       AudioBuffer.          state_refresh_loop tick @10Hz calls
                                          snapshot_features()   snapshot_features(seconds=4.0); new fields
                                                                kick_centroid, kick_harmonic_ratio, kick_crest
                                                                computed in same FFT pass (single ~15ms cost)

T+~52ms           T=52     Sidecar       MusicState.update     state_refresh_loop writes new fields into
                                                                MusicState (single writer); also writes
                                                                buildup_score + beat_phase

T+~52ms           T=52     Sidecar       EvidenceRegistry.     synchronous register-on-write — for each
                                          register             audio-feature key (peak_rms, sub_share, ...),
                                                                register Evidence(source="aud", key=..., t_session)

T+~53ms           T=53     Sidecar       EventDetector.detect  Layer 1 baseline detectors run first — no match
                                                                Layer 2 (hard_tek genre) detectors run —
                                                                detect_kick_swap() finds centroid_delta > 25Hz
                                                                AND harm_delta > 0.5 AND BPM stable AND
                                                                band_energy preserved >75% AND hysteresis OK
                                                                → returns Event("KICK_SWAP", state, extra={...})

T+~53ms           T=53     Sidecar       EventDetector._fire   _fire() updates _last_fired_at[ev.type],
                                                                calls evidence_registry.register(Evidence(
                                                                source="ev", key="KICK_SWAP", t_session=T))

T+~55ms           T=55     Sidecar       coach_loop            sees Event return, checks not in_flight, checks
                                                                cooldown — passes. Calls:
                                                                  rolling_ttft_avg > 800ms → AckBank.fire_ack()

T+~60ms           T=60     Sidecar       AckBank.fire_ack      picks random non-recent OPUS sample,
                                                                decodes ~3ms, pushes 24kHz PCM directly to
                                                                PlaybackQueue (BYPASSES LiveKit TTS path);
                                                                writes ipc.session.ack_fired to shell

T+~60ms           T=60     Sidecar       MascotAnticipation.   sends ipc.mascot.tick with anticipation =
                                          fire                  {event_class: "hard_tek_kick", fires_in_ms: 0}

T+~65ms           T=65     Shell → UI    overlay subscribers   if overlay enabled AND Gemini reply later
                                                                carries `point: deck.a.kick`, that arrives
                                                                in a separate step; mascot anticipation
                                                                fires NOW

T+~70ms           T=70     Sidecar       coach_loop            builds prompt via AICoach.build_prompt:
                                                                  system_instruction = (cached, in cached_content)
                                                                  user_payload = evidence_line + task fragment
                                                                  citation grammar baked in prompt
                                                                fires session.generate_reply(extra_kwargs=
                                                                  {cached_content: cached_name})

T+~75ms           T=75     Audio out     sd output callback    plays ack-bank "yes"/"go" sample

T+~700ms          T=700    Sidecar       google.LLM stream     first chunk back from Gemini, text:
                                                                "Clean — kick character flipped at
                                                                [ev:KICK_SWAP@04:22] — distortion crept in."

T+~720ms          T=720    Sidecar       DJCoHostAgent.        accumulate stream; on stream-complete:
                                          llm_node final         CitationLinter.validate(text, mode="live")
                                                                Result: 1 valid citation [ev:KICK_SWAP@04:22]
                                                                  → response passes
                                                                Strip the citation token from text before TTS
                                                                  (text-for-display retains; text-for-TTS strips)

T+~720ms          T=720    Sidecar       linter.publish        emit ipc.session.citation: validated=true,
                                                                valid=1, invalid=0, slop_ratio rolling

T+~725ms          T=725    Sidecar       TTS pipe              cleaned text → google.beta.gemini_tts.TTS
                                                                streams PCM chunks

T+~1100ms         T=1100   Audio out     sd output callback    plays first chunk of voiced response;
                                                                ack-bank sample finished at ~T+700, brief
                                                                400ms gap (min_ack_to_response_gap_ms)

T+~2300ms         T=2300   Sidecar       VoiceRecorder         input.wav + voice.wav + events.jsonl
                                                                rows fully closed for this event

────────────────────────────────────────────────────────────────────────────────────────
Failure branch — linter strips all (live mode):
T+~720ms          T=720    Sidecar       linter                validate result: validated=false (no citations);
                                                                ack-bank already fired at T+60ms — user heard
                                                                "yes" sound; main response is dropped; ipc.
                                                                session.citation reports fallback_fired=true
```

### VI.B Overlay highlight fire — Gemini → AX → ring render

```
Step              Time     Process       Component             What happens
────────────────  ──────   ──────────    ──────────────        ─────────────────────────
T+~700ms          T=700    Sidecar       LLM stream            text response includes structured-output
                                                                point field: {"say": "...", "point":
                                                                "deck.a.mid_eq", "hold_ms": 2500}

T+~720ms          T=720    Sidecar       overlay.elements      validate point against allowlist (12 IDs);
                                          parse                 deck.a.mid_eq is valid

T+~720ms          T=720    Sidecar       coord_map.lookup      load tauri/ui/src/overlay/elements.json,
                                                                find deck.a.mid_eq → percentage coords +
                                                                AX hint {role: "AXSlider", label: "Mid EQ Deck A"}

T+~720ms          T=720    Sidecar→Shell ipc.overlay.ax_       sidecar requests AX rect from Rust parent
                                          position(query)       (NOT pyobjc in sidecar per tauri#8329)

T+~725ms          T=725    Shell         ax_bridge.rs          Rust AX call — AXUIElementCopyAttributeValue
                                                                walks djay AX tree, returns NSRect for
                                                                "AXSlider" labeled "Mid EQ Deck A" or None

T+~727ms          T=727    Shell→sidecar ipc.overlay.ax_       responds with screen_rect or null
                                          position(response)

T+~728ms          T=728    Sidecar       overlay.coord_map     if AX returned rect → use it
                                                                if AX returned null → fall back to
                                                                percentage-of-window-rect from elements.json
                                                                combined with window_tracker's last bounds

T+~730ms          T=730    Sidecar→Shell ipc.overlay.highlight emit final command: {element_id, deck,
                                                                hold_ms, ring_color: "amber"}

T+~735ms          T=735    Shell (Tauri  forward to overlay   tauri::emit("overlay_highlight", payload) to
                          event bus)     webview               the label="overlay" window

T+~737ms          T=737    Overlay UI    overlay.ts            Canvas 2D ring draws at (x, y) over the
                                          subscribeIpc          actual screen position; CSS keyframe fade-in
                                                                 250ms

T+~990ms          T=990    Overlay UI    ring animation         hold full opacity 2.5s

T+~3490ms         T=3490   Overlay UI    fade-out               CSS fade-out 250ms, then remove

────────────────────────────────────────────────────────────────────────────────────────
Concurrent gating:
- window_tracker.rs emits ipc.overlay.window_bounds @10Hz; overlay re-anchors continuously
- If djay loses focus mid-hold → ipc.overlay.dismiss fires; ring fades immediately
- If linter strips the response BEFORE T+720, the point field never propagates — no highlight fires
- If point is invalid (not in 12-element allowlist), sidecar logs and skips silently (no highlight)
```

### VI.C Post-session debrief — recording browser → sibling sidecar → markdown

```
Step       Process              What happens
─────────  ─────────────────    ─────────────────────────────────────────────
T+0        Shell (UI)           User clicks "Generate Debrief" in RecordingBrowser.ts
T+5ms      Shell (Rust)         debrief.rs spawns NEW sidecar child process with --debrief <dir>
                                 (separate from live-runtime sidecar; uses WS port 8766)
T+~2s      Sibling sidecar      starts up, loads recordings/<dir>/events.jsonl, input.wav, voice.wav
                                 emits ipc.debrief.status {stage: "loading"}
T+~2s      Sibling sidecar      DebriefPipeline.run() — sweeps events.jsonl into evidence registry
                                 (sentence-level linter for debrief mode, ±2.0s tolerance)
T+~3s      Sibling sidecar      single Gemini call: full session_summary.json + 80-min input.wav as
                                 audio Part + cached_content (session-scoped cache) + SBI/STAR-AR
                                 prompt template (Bucket E)
                                 emits ipc.debrief.status {stage: "calling_gemini", pct: 30}
T+~25s     Sibling sidecar      Gemini response complete (~15-30s for 4-chapter debrief)
                                 emits ipc.debrief.status {stage: "linting", pct: 70}
T+~25.1s   Sibling sidecar      linter sentence-level per chapter; logs per-chapter slop_ratio
                                 if any chapter >50% strip → one retry with stripped sentences
                                 fed back to Gemini ("these were unsourced — cite or remove")
T+~26s     Sibling sidecar      writes debrief.md, debrief.json to recordings/<dir>/
                                 emits ipc.debrief.status {stage: "voicing", pct: 85}
T+~28s     Sibling sidecar      Gemini TTS on 60-90s TL;DR section → debrief_tldr.wav
                                 emits ipc.debrief.result {paths, slop_ratio_per_chapter}
T+~28s     Sibling sidecar      Sidecar exits 0 cleanly (process lifecycle ends with debrief)
T+~28s     Shell (UI)           DebriefView.ts receives ipc.debrief.result, renders
                                 4-chapter markdown + clickable timeline (clicking timestamp
                                 jumps voiced_wav playback position)
```

---

## VII. PHASE-DECOMPOSITION HINTS

The roadmapper consumes this section. Build order considers:
- **Schema parity drift gate** — every phase that adds an IPC message MUST update `scripts/check_ipc_schema.py` assertion + regenerate codegen in the same commit.
- **Evidence registry is foundation** — citation linter is downstream; both ship in same phase or detector phase first.
- **AX bridge is risky** — has a hard hardware-rig requirement (djay Pro Mac on Kaan's machine); ship later when binaries pipeline (Phase 11) is stable.

### VII.A Critical-path graph

```
                             ┌─────────────────────────────┐
                             │ P15 Recording finalization  │ ← v0.1.0 absorb
                             │   (browser + retention)      │
                             └───────────┬─────────────────┘
                                         │
                                         ▼
                       ┌─────────────────────────────────┐
                       │ P16 Hallucination verification  │ ← v0.1.0 absorb
                       │   (Kaan DJ-ear gate)            │
                       └───────────┬─────────────────────┘
                                   │ unblocks ALL detector/linter work
                                   ▼
              ┌────────────────────┴──────────────────┐
              │                                       │
              ▼                                       ▼
   ┌──────────────────────────┐         ┌─────────────────────────────┐
   │ P21 Hard Tek detectors v1 │         │ P22 Evidence registry +     │
   │ (8 detectors, genre       │         │   citation grammar in       │
   │  router, MusicState +4    │         │   prompts (v1.0 prompt-only │
   │  fields, reference WAVs)  │         │   seeding, no enforcement)  │
   │ Touches: events/, audio/  │         │ Touches: grounding/, prompts/│
   │ IPC schema delta: +1      │         │ IPC schema delta: 0         │
   │  (ipc.session.event)      │         │ (linter telemetry deferred) │
   └──────────┬───────────────┘         └─────────────┬──────────────┘
              │                                       │
              └───────────────────┬───────────────────┘
                                  ▼
              ┌───────────────────────────────────────┐
              │ P23 Latency stack v1 (ack bank +      │
              │   cached_content + cancel-refire)     │
              │ Touches: latency/, agent/, coach_loop │
              │ IPC schema delta: +3                  │
              │  (ack_fired, predicted_fire,          │
              │   cancel_refire)                      │
              └─────────────────┬─────────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
   ┌────────────────────┐ ┌──────────────────┐ ┌─────────────────────┐
   │ P24 Citation       │ │ P25 Mascot 4-    │ │ P26 Pyrekordbox XML │
   │  linter ENFORCE-   │ │  layer additive  │ │  import + lookup    │
   │  MENT (live mode,  │ │  state machine + │ │ Touches: library/   │
   │  response-level,   │ │  anticipation +  │ │  rekordbox_xml +    │
   │  ack-fallback)     │ │  hip-bob         │ │  metadata + camelot │
   │ Touches: grounding/│ │ Touches: mascot/ │ │ IPC schema delta: +4│
   │  + agent/llm_node  │ │  (Rust + TS)     │ │  (import_start,     │
   │ IPC schema delta:  │ │ IPC schema delta:│ │   import_progress,  │
   │  +1 (citation tel) │ │  +1 (ipc.mascot. │ │   import_done,      │
   │                    │ │  tick promotion) │ │   lookup)           │
   └────────────────────┘ └──────────────────┘ └─────────────────────┘
              │                 │                       │
              └─────────┬───────┴───────────┬──────────┘
                        ▼                   ▼
            ┌────────────────────┐  ┌────────────────────────────┐
            │ P27 djay Pro Mac   │  │ P28 10-SKU MIDI library    │
            │  overlay highlight │  │  EXTEND (Phase 9 partial)  │
            │ Touches:           │  │ Touches: midi/library/     │
            │  tauri/ax_bridge,  │  │ IPC schema delta: 0        │
            │  window_tracker,   │  │ (existing port-discovery   │
            │  overlay_window,   │  │  IPC reused)               │
            │  ui/overlay/,      │  │                            │
            │  sidecar overlay/  │  │                            │
            │ IPC schema delta:  │  │                            │
            │  +4 (highlight,    │  │                            │
            │   dismiss,         │  │                            │
            │   window_bounds,   │  │                            │
            │   ax_position)     │  │                            │
            │ MAC ONLY           │  │                            │
            └──────────┬─────────┘  └────────────┬───────────────┘
                       │                         │
                       └────────────┬────────────┘
                                    ▼
                  ┌──────────────────────────────────┐
                  │ P29 Post-session debrief         │
                  │  (sidecar --debrief flag +       │
                  │   sibling lifecycle + Debrief UI)│
                  │ Touches: debrief/, runtime/__main│
                  │   tauri/debrief.rs + ui/debrief/ │
                  │ IPC schema delta: +3             │
                  │  (debrief.start/status/result)   │
                  │ Cross-mode citation linter       │
                  │  EXTENSION: sentence-level for   │
                  │  debrief                          │
                  └──────────────┬───────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────────┐
                  │ P30 Library intelligence (embed +│
                  │   sqlite-vec store + watcher +   │
                  │   query interfaces)              │
                  │ Touches: library/embed +         │
                  │   store + watcher + fingerprint  │
                  │ IPC schema delta: +2             │
                  │  (embed_progress, embed_done)    │
                  │ Cross-mode citation linter       │
                  │  EXTENSION: library mode          │
                  └──────────────┬───────────────────┘
                                 │
                                 ▼
                 ┌───────────────────────────────────┐
                 │ P31 Sign + notarize + GH Release  │ ← v0.1.0 absorb
                 │   (Apple Dev ID, SignPath Win,    │
                 │    DMG, MSI, latest.json updater) │
                 │ Touches: .github/workflows/       │
                 │   release.yml, build_sidecar.py   │
                 │ IPC schema delta: 0               │
                 │ Critical-path BLOCKER for ship    │
                 └───────────────┬───────────────────┘
                                 │
                                 ▼
                 ┌───────────────────────────────────┐
                 │ P32 Day-Zero ops + viral demo film│ ← v0.1.0 absorb
                 │  (fresh-VM rehearsal, demo cut,   │
                 │   IG/Reddit/HN posting)           │
                 └───────────────────────────────────┘
```

### VII.B Parallelizable bundles

- **P21 (Hard Tek detectors) || P26 (Library import)** — touch different modules (`events/` vs `library/`); both feed evidence registry but at different layers. Run in parallel after P15/P16.
- **P25 (Mascot refactor) || P28 (MIDI extend)** — completely independent. Mascot is `tauri/ui/`, MIDI is `src/vibemix/midi/`.
- **P27 (Overlay) || P29 (Debrief)** — overlay is Mac-only platform work, debrief is platform-agnostic sidecar lifecycle. Independent codepaths.
- **P30 (Library intel) depends on P26 (XML import)** — embed pipeline needs the SQLite track table to exist first.

### VII.C Phase-level invariants the roadmapper should encode

| Phase | Invariant to assert at close |
|-------|-----------------------------|
| Every phase touching IPC | `scripts/check_ipc_schema.py` exits 0 + count assertion updated |
| Every phase touching `MusicState` | `tests/state/test_music_state.py::test_v4_golden_equivalence` stays green |
| Every phase touching `EventDetector` | 6 v4 baseline event types byte-identical when `active_genre="hard_tek"` AND only baseline detectors fire |
| Every phase touching `cohost_v4.py` | DOESN'T. POC G5 gate (`test_g5_poc_files_untouched`) stays green |
| Every phase shipping a binary | `assert_no_aiza_leak` exits 0 across all new bundled assets |
| Every phase touching prompts | Golden tests in `tests/prompts/test_negative_dict.py` + `test_anchor_phrases.py` stay green |
| P21+P22 close | Phase 16 ear-test gate satisfied for KICK_SWAP + linter prompt-only seeding |
| P31 close | macOS DMG notarized + Win MSI SignPath-signed + GitHub Release tagged with both |

---

## VIII. CROSS-PROCESS CONCERNS

### VIII.A Shared state crossing the WS bus

| State | Owner process | Cross-process consumer | Cadence | Lock/race notes |
|-------|---------------|------------------------|---------|-----------------|
| MusicState snapshot (RMS, BPM, beat_phase, active_genre) | Sidecar | Shell (mascot rig consumes BPM + beat_phase) | 30Hz (ipc.mascot.tick) | Sidecar serializes single dataclass snapshot; sub-millisecond lock-hold; shell parses with ajv validator |
| Typed events (KICK_SWAP, MIX_MOVE, ...) | Sidecar | Shell (overlay highlight trigger; debrief future replay; mascot anticipation T=0 fire) | Event-driven (~0.1-2 Hz peak) | Same-loop write → broadcast; no race between EventDetector._fire and BroadcastBus.publish_event (both on asyncio event loop) |
| Citation telemetry | Sidecar | Shell (settings panel slop ratio; debrief per-chapter ratio) | Per-response | Bounded queue; if shell disconnects, sidecar drops oldest |
| AX position rect | Shell (Rust) | Sidecar (computes whether to fire overlay highlight) | Query/response | Rust call is synchronous-blocking on the asyncio side; sidecar uses `loop.run_in_executor` or awaits IPC response with 200ms timeout |
| Window bounds | Shell (Rust window_tracker) | Overlay webview (intra-shell tauri::emit) | 10Hz | Tauri event bus is thread-safe by design; overlay webview just consumes via subscribeIpc |
| Library SQLite | Sidecar | Sidecar (only) | On-demand | sqlite3 connection per coroutine via thread-local; sqlite-vec extension thread-safe at SQLITE_CONFIG_SERIALIZED |
| Library embeddings index | Sidecar | Sidecar (only) | On-demand | In-memory numpy matrix loaded once at session start; reads are lock-free; embed-worker has its own write lock |
| Long-term DJ profile | Sidecar | Sidecar (live + sibling --debrief) | Read on session start, write on debrief close | Sibling --debrief sidecar has exclusive write; live sidecar reads only. File lock via fcntl on POSIX, O_EXCL on Win |
| Recording dir | Sidecar (live writes) | Sibling --debrief sidecar (reads), Shell (lists) | Continuous live; one-shot debrief; UI poll | Append-only writes (input.wav, voice.wav grow); debrief opens files in read-mode AFTER live session ends. No concurrent write. |

### VIII.B New race conditions introduced

| Race | Manifestation | Mitigation |
|------|---------------|------------|
| Mascot anticipation vs WS bus congestion | At T+60ms sidecar fires ipc.mascot.tick with anticipation; if WS bus is congested (e.g., 1000+ status_ticks queued during a level-spike storm), anticipation arrives late and the perceived-latency mask is broken | (a) ipc.mascot.tick is high-priority queue jumper — bypasses status_tick batching; (b) BroadcastBus uses two separate asyncio queues — fast lane for events, slow lane for level data |
| Evidence registry write vs linter read | Linter is called in `coach_loop` after `generate_reply` completes (~T+700-2300ms); during that interval, new events may have registered. If linter validates against the snapshot-at-fire-time vs current state, semantic mismatch | Linter uses time-bounded tolerance window (±1.0s live, ±2.0s debrief) — looks for any registered event of the cited key within tolerance of the cited timestamp. New events that came AFTER the citation arrived are not at the cited timestamp; old events at the cited timestamp ARE found. Safe by design. |
| Predictive fire + actual event arrival mid-generation | Sidecar fires PREDICTED_DROP at T+0; actual PHASE event fires at T+800ms; LLM stream still in flight at T+800ms; new event has higher priority | `coach_loop` checks `state.in_flight_priority` vs new event priority; if new > in_flight + PRIORITY_GAP (3), calls `current_handle.interrupt(force=True)` and fires new generate_reply. Capped at 1 cancel per 8s. |
| AX bridge timeout / failure | Sidecar requests AX position; Rust ax_bridge.rs takes >200ms or returns error; sidecar's overlay.highlight is delayed | Sidecar fires overlay.highlight with `coord_map.lookup` fallback rect (percentage-of-window-rect) if AX response not received within 150ms; logs source=coord_map for telemetry. Never blocks Gemini response. |
| Sibling --debrief sidecar collision with live sidecar | User triggers "Generate Debrief" while a live session is running; both sidecars now spawned | Different WS bus ports (live=8765, debrief=8766); different recording-dir lock semantics (debrief reads only); shell allows N debrief instances but max 1 live sidecar |
| File watcher (library) firing during indexing | watchdog detects new file mid-import; embed worker queues it; FK constraint violation if track row not yet committed | Embed worker uses a single SQLite transaction per track row + cue + grid insert; chromaprint fingerprint dedupe AHEAD of embed. If race: insert with `ON CONFLICT (fingerprint) DO NOTHING` (sqlite3 supports it) |
| sqlite-vec index rebuild during live query | Embedding worker rebuilding index while user fires "what's playing similar" query | sqlite-vec supports concurrent reads even during writes (it's just a vtable over BLOB columns); reads see committed state; live query just gets a slightly stale top-K — acceptable, never wrong |
| Updater download mid-session | Tauri updater fetches v2.1 latest.json + ed25519-signed installer while user is mid-DJ-session | Updater check runs on app start only (Phase 11 default), never mid-session; user-initiated re-check is allowed but installer doesn't auto-replace running binary |

### VIII.C Locking summary

- **Inside sidecar process:** `threading.Lock` only on shared buffers (AudioBuffer ring, MicBuffer ring, PassthroughBuffer ring, ControllerState moves ring) — Phase 2/3 baseline preserved. All asyncio logic single-event-loop, no extra locks needed.
- **Evidence registry:** in-memory dict, mutated from `state_refresh_loop` and `EventDetector._fire` — BOTH run on asyncio event loop, no lock needed (cooperative scheduling).
- **Linter:** stateless except for telemetry counters; counters are simple int increments under the GIL — no lock.
- **Library SQLite:** `connection.cursor()` per-coroutine; sqlite3 module thread-safety mode SERIALIZED (default); reads + writes through the same connection serialize at sqlite3 level. No app-level lock.
- **Cross-process state:** none, except recording-dir filesystem semantics (append-only by live, read-only by debrief) — natural separation.

---

## IX. CROSS-PLATFORM PARITY

| Concern | macOS | Windows | Linux |
|---------|-------|---------|-------|
| Audio capture | BlackHole 2ch + sounddevice (existing P2 + P8) | WASAPI loopback via PyAudioWPatch (existing P7) | OUT OF SCOPE |
| Screen capture | ScreenCaptureKit (existing P8) | mss + win32 (existing P7) | OUT OF SCOPE |
| Now-playing | nowplaying-cli bundled binary (existing) | winsdk SMTC (existing P7) | OUT OF SCOPE |
| MIDI | mido + python-rtmidi cross-platform (existing P9) | same | OUT OF SCOPE |
| Mascot transparent window | Tauri WebviewWindowBuilder (existing P11) | Tauri WS_EX_LAYERED (existing P11) | OUT OF SCOPE |
| **NEW: djay Pro overlay highlight** | **MAC-ONLY** | DEFERRED to v2.1+ (Rekordbox/Serato template-match approach, separate phase) | n/a |
| **NEW: AX bridge for AX-based positions** | **MAC-ONLY** — pyobjc AX call from RUST parent (not sidecar per `tauri#8329`) | n/a — Win has UIAutomation but djay doesn't run on Win | n/a |
| **NEW: Citation linter** | cross-platform | cross-platform | n/a |
| **NEW: Evidence registry** | cross-platform | cross-platform | n/a |
| **NEW: Hard Tek detectors** | cross-platform numpy/scipy DSP | cross-platform | n/a |
| **NEW: Mascot 4-layer refactor** | cross-platform Three.js | cross-platform | n/a |
| **NEW: Pyrekordbox XML import** | cross-platform | cross-platform (XML parsing, no native deps) | n/a |
| **NEW: Library intelligence (embed + sqlite-vec + watcher)** | cross-platform; watchdog uses FSEvents on Mac, ReadDirectoryChangesW on Win; sqlite-vec ships wheels for both; chromaprint fpcalc bundled per platform; ffmpeg bundled for Win, afconvert fallback for Mac | cross-platform | n/a |
| **NEW: Post-session debrief** | cross-platform | cross-platform; sibling sidecar lifecycle identical | n/a |
| **NEW: Latency stack (ack-bank, cached_content, predictive)** | cross-platform | cross-platform | n/a |
| **NEW: Updater (Tauri Updater plugin + ed25519 latest.json)** | macOS DMG hosted on api.altidus.world | Windows MSI hosted on api.altidus.world | n/a |
| **NEW: Code signing** | Apple Developer ID (Kaan has) | SignPath Foundation OSS cert (apply day-1) | n/a |

**Mac-only feature surface:** djay Pro overlay highlight + AX bridge for position queries. Everything else is parity. Document in README: "djay Pro overlay highlight is macOS-only in v2.0; Windows + Rekordbox/Serato overlay coming in v2.1+."

**Windows-specific gotchas:** DPI virtualization (per-monitor DPI awareness V2 must be set at startup), multi-monitor at different DPIs (per-monitor scale factors), target window class names vary by version (match on GetWindowText + process exe name). Phase 7 already handles audio capture; new overlay-related work would inherit these.

---

## X. STRUCTURE RATIONALE — Why each new component lives where it does

| Decision | Rationale |
|----------|-----------|
| **CitationLinter in sidecar Python (not shell TS)** | Linter consumes Gemini output text + Evidence registry. Evidence registry lives in sidecar (events fire there, MusicState lives there). Putting linter in shell would require streaming evidence to shell every state-refresh tick (~10Hz, large payload). Sidecar local. |
| **Evidence registry in sidecar `grounding/` package** | New package sibling to existing `state/`, `events/`, `agent/`. Conceptually a CROSS-CUT — both EventDetector and state_refresh_loop write into it. Keeping it in its own package avoids circular import (state → events → grounding → state is broken; state → grounding ← events is clean). |
| **AX bridge in Rust shell, NOT Python sidecar** | `tauri#8329`: sidecars don't reliably inherit AX TCC permission from installed Mac bundles. Bundle identity is stable in the Rust parent process (signed once, TCC sticks); calling pyobjc AX from sidecar gets prompted on every launch + never sticks. Hard requirement. |
| **Overlay webview as second Tauri window, NOT separate app** | Shares signed bundle identity (one cert, one notarization). Shares WS bus connection. Tauri 2 supports multi-window cleanly. Compare to: separate app would double cert work + complicate IPC across apps. |
| **Debrief as sidecar `--debrief` FLAG, not new process type** | PyInstaller `--onedir` build cost is high (~45s + ~240MB). Same binary, different entry-point flag, exits when done. Phase 11 W4 `--wizard` flag is the precedent. No new packaging work. |
| **Library intelligence as sidecar Python package** | sqlite-vec is a Python wheel; watchdog is Python; mutagen is Python; pyrekordbox is Python; chromaprint binary spawned via subprocess (Mac+Win both). Putting it in shell would mean reimplementing in Rust or invoking Python from Rust — net higher cost. |
| **Mascot anticipation HOOK in sidecar, ANIMATION in shell** | Sidecar fires `ipc.mascot.tick` with anticipation field at T=0 (EventDetector tick). Shell mascot/state-machine.ts reads ipc.mascot.tick subscription and routes anticipation field to anticipation layer's planTransition. Animation rendering stays in Three.js where it lives today. The KEY insight: anticipation FIRES from event-detect time (sidecar knows first), not from LLM-response time. |
| **Per-genre detector files in `events/genres/`** | One file per genre (hard_tek.py, techno.py, ...) — keeps each genre's DSP + thresholds + reference tracks + Kaan-tuning history co-located. G-followup recommendation. Router does the swap atomically. |
| **Citation grammar in prompts, ENFORCEMENT in linter** | v1.0 ships prompt-only seeding (Gemini learns the grammar in prod) → v1.1 enables linter enforcement. Lets us tune linter strictness FROM telemetry instead of blind. Phasing locked. |
| **Sibling debrief sidecar uses port 8766 NOT 8765** | Avoids collision with live-runtime sidecar (if both running). Phase 11 `WizardBus` precedent — separate WS bus lifecycle, single ws_bus.py module but different port + handlers. |
| **`tauri/ui/src/overlay/elements.json` shipped in installer** | Hand-mapped coord file is part of the installer bundle (per djay Pro v5). Lives in `tauri/ui/src/overlay/` so frontend tooling versions it; bundle inclusion via `tauri.conf.json5` `resources` block. Sidecar reads via known relative path. |
| **Ack-bank OPUS files shipped, NOT generated at runtime** | Generating 40 samples at runtime needs Gemini API on first launch (cold start hostile + cost). Pre-generate offline once with Achird voice, ship in bundle. Regenerate on Gemini TTS model bump (manual ops task, not user flow). |

---

## XI. RISK + WATCHOUTS

| Risk | Severity | Mitigation |
|------|----------|------------|
| `interrupt(force=True)` regression on `livekit-agents` patch bump | HIGH — predictive cancel-refire fails silently if method semantics change | Pin `livekit-agents==1.5.8` + `livekit-plugins-google==1.5.8` in pyproject.toml; CI smoke test on every PyInstaller build verifies `force=True` succeeds against a mocked session |
| Gemini context caching token floor (1024) too close to padded system instruction | MEDIUM — falling below 1024 silently disables cache → TTFT regression 500-1500ms | One-off `client.models.count_tokens()` smoke test in P23; pad deliberately to 1400+ tokens with controller MIDI map dump + event taxonomy enum |
| AX bridge returns null on every query (djay update broke AX exposure) | HIGH — overlay highlight degrades to percentage-of-window-rect always | Fallback chain is already designed (AX → coord_map → silent skip); telemetry logs source=coord_map; Phase 16 ear-test catches false-position drift early |
| sqlite-vec wheels break on Windows ARM64 | MEDIUM — library intel disabled for ARM Surface laptops | Phase 30 ships fallback path (numpy.float32.tobytes() + in-memory cosine) per F-research; abstraction layer `LibraryStore` makes swap a 1-week migration not a rewrite |
| Mascot 4-layer additive refactor regression on hip-bone delta | HIGH — mascot floor-skates or twists weirdly | `AnimationUtils.makeClipAdditive` is required pre-processing; new clips authored with idle-zero lower-body delta (commission brief includes the constraint); visual regression test screenshots in P25 verifier |
| Tauri `visible_on_all_workspaces` doesn't cover macOS fullscreen Spaces (`tauri#11488`) | MEDIUM — overlay disappears when djay is fullscreen | Document as known gap; recommend non-fullscreen djay use; reassess when tauri ships fix |
| Sibling --debrief sidecar consumes 240MB while live sidecar is also running | LOW-MEDIUM — 480MB total RAM, acceptable on modern machines | Debrief is single-pass (lives ~30s); auto-exits; no concurrent debrief jobs |
| Linter strips too aggressively on a Gemini model bump | HIGH — user hears silence + ack-bank fallback consistently → trust break | Telemetry slop ratio rolling 7-day average; alert when >+2σ; auto-relax `tolerance_s` by 0.5 for safety; Phase 16 ear-test catches |
| Library file watcher fires 1000s of events on Spotlight reindex | MEDIUM — embed worker queue floods, free-tier RPM exhausted | watchdog has built-in debounce 100ms; embed worker queue capped at 100 pending, drops oldest with telemetry |
| Updater rollout pushes broken binary | CRITICAL — auto-update kills user installs | Tauri Updater requires ed25519 signature verification; staged rollout (10% → 50% → 100% via latest.json conditional manifests); rollback latest.json to previous version on crash-rate spike |
| Recording retention deletes session user wanted to debrief | MEDIUM — UX bug if retention window < user expectation | Default retention 30 days (Bucket E suggestion); user-configurable in Settings → Privacy; "Generate Debrief" flow auto-pins the session against retention sweeps |

---

## XII. SOURCES

### Primary (HIGH confidence, repo-verified)

- `cohost_v4.py` lines 134, 154, 224-246, 300-462, 582-598, 839-843, 965, 1167-1380, 1438-1605, 1651-1922, 2030-2033 — verbatim port-from for v4 reference logic + LiveKit invariants
- `tauri/src-tauri/src/mascot_window.rs` lines 82-104 — overlay window builder pattern
- `tauri/src-tauri/tauri.conf.json5` line 90 — `macOSPrivateApi: true` precondition
- `tauri/ui/src/ipc/messages.schema.json` (Draft-07, 19 messages, $id `vibemix.ipc.messages`)
- `scripts/check_ipc_schema.py` — drift gate
- `scripts/build_sidecar.py` — assert_no_aiza_leak Phase 5 gate
- `.planning/codebase/ARCHITECTURE.md` — existing 3-process architecture diagram + invariants
- `.planning/STATE.md` — Phase 1-14 decision log (locked decisions section)
- `.planning/PROJECT.md` — constraints + 12 feature buckets

### Secondary (MEDIUM-HIGH confidence, v2-bucket research)

- `.planning/research/v2-buckets/SYNTHESIS.md` — 12-artifact integration layer, priority matrix
- `.planning/research/v2-buckets/A-latency.md` + `A-followup-1-cancel-and-caching.md` — empirically-verified `interrupt(force=True)` + Gemini context caching 1024-token floor
- `.planning/research/v2-buckets/C-ui-overlay.md` — djay Pro Mac AX feasibility + Tauri#8329 sidecar AX bug + percentage-of-window coord map approach
- `.planning/research/v2-buckets/D-mascot-emotion.md` — 4-layer additive blend architecture + anticipation 400-1200ms latency mask + Three.js makeClipAdditive
- `.planning/research/v2-buckets/E-followup-1-citation-linter.md` — full grammar EBNF + `CitationLinter` class skeleton + per-mode prompts + telemetry shape + phasing
- `.planning/research/v2-buckets/F-library-intelligence.md` — Bravoh embed pipeline (`/var/www/bravoh-backend/app/services/embedding/service.py` lift), sqlite-vec choice rationale, 80s audio cap empirical correction, pricing projection
- `.planning/research/v2-buckets/G-followup-1-hard-tek-dsp.md` — 8 Hard Tek detector specs, GenreRouter + Detector dataclass architecture, reference tracks for tuning

### Tertiary (LOW confidence, external)

- [tauri-apps/tauri issue #8329](https://github.com/tauri-apps/tauri/issues/8329) — sidecar AX permission inheritance bug
- [tauri-apps/tauri issue #11488](https://github.com/tauri-apps/tauri/issues/11488) — visibleOnAllWorkspaces + fullscreen Spaces
- [tauri-apps/tauri issue #11461](https://github.com/tauri-apps/tauri/issues/11461) — setIgnoreCursorEvents Windows per-region hit-test
- [livekit-agents source `voice/speech_handle.py:141-154`](https://github.com/livekit/agents) — `interrupt(force=True)` semantics

---

## XIII. ASSUMPTIONS LOG

| # | Claim | Section | Risk if wrong |
|---|-------|---------|---------------|
| A1 | Schema delta of +19 messages is sufficient (38 total) — no additional messages emerge mid-build | §III | Each missing message = a Phase X extension. Low risk; the 19 enumerated cover all v2.0 features per research artifacts. |
| A2 | sqlite-vec wheel works on Windows ARM64 (untested platform) | §IV.A library/, §IX | Fallback to numpy in-memory cosine ranking; documented as F-research mitigation |
| A3 | `interrupt(force=True)` on cascade is stable across livekit-agents 1.5.x patch versions | §V coach_loop, §XI | Pin to exact version; CI smoke test on every build; fallback to `_cancel()` documented |
| A4 | Gemini cached_content extra_kwargs flows through `livekit-plugins-google` LLM.chat() without server-side dropping | §IV.A latency/cache.py, §V | 20-line smoke test in P23 verifies via `metrics.prompt_cached_tokens > 0` |
| A5 | Mascot 4-layer additive blending costs <2ms/frame on M2 (Three.js benchmark) | §V renderer.ts, §VIII | Benchmark in P25; if regresses to >4ms drop one of: hip-bob procedural OR additive blending (anticipation layer keeps as a critical path) |
| A6 | Sibling --debrief sidecar process can coexist with live-runtime sidecar without TCC permission collision | §IV.B debrief.rs, §VIII.B | Single bundle identity → TCC permission grants apply to both; verified in Phase 11 wizard precedent (--wizard flag uses same bundle) |
| A7 | djay Pro Mac v5 AX surface remains stable enough that hand-mapped coord_map + AX hints stay valid for 2026 product life | §V overlay, §IX | Pin coord map per djay major version; ship updates with new elements.json on djay updates |
| A8 | Linter regex on Python `re` stdlib is sufficient (no recursive patterns, no variable-length lookbehinds) | §V CitationLinter | Stdlib `re` confirmed sufficient per E-followup research; one-click-install hard req preserved |
| A9 | Phase 11 W3/W4 cdj-whisper-v5 token system + component-scoped registerStyle pattern accommodates new UI surfaces (overlay, debrief, library, settings panels) without per-component CSS sprawl | §IV.B ui/ | New surfaces follow existing tokens.css + registerStyle precedent; if drift appears in P14-style polish phase, run frontend-enforcement skill audit |
| A10 | Existing AICoach.build_prompt task-strings for v4 baseline events stay byte-identical after genre-router refactor when active_genre = hard_tek AND only baseline detectors fire | §V AICoach | Golden equivalence tests pin per (genre, event_type) cell; Phase 3 baseline tests carry forward |

---

*Architecture research complete. Confidence: HIGH on existing architecture surface, MEDIUM on first-time-integrated components (AX bridge, Tauri overlay window, sqlite-vec wheels on Win ARM64). All 13 sections quality-gate checked: integration points identified, new vs modified components explicit, build order considers dependencies, cross-process concerns surfaced, cross-platform parity called out.*
