# Architecture Research — v2.1 The Unified Cut

**Milestone:** v2.1 — The Unified Cut (SUBSEQUENT milestone — continuing from Phase 26)
**Researched:** 2026-05-14
**Confidence:** HIGH — research draws on (a) the v2.0 audit (`.planning/milestones/v2.0-MILESTONE-AUDIT.md`) which precisely names every shipped seam, (b) the audited live code in `src/vibemix/` + `tauri/` after 220 commits since `v0.1.0-rc1` and 1961 passing tests, and (c) the locked 3-process design ratified at Phase 11.

## Existing 3-Process Architecture (LOCKED — do not modify)

```
┌────────────────────────────────────────────────────────────────────────┐
│  Process 1 — Tauri 2 Rust shell  (tauri/src-tauri/)                    │
│  Owns:                                                                  │
│   • djay_ax.rs            — AX bridge (RUST PARENT ONLY — gh #8329)    │
│   • mascot_window.rs      — overlay WebviewWindow                       │
│   • overlay.rs            — djay-Pro highlight overlay window           │
│   • permissions.rs        — TCC deep-link helpers (osascript)           │
│   • sidecar.rs            — PyInstaller --onedir watchdog (3 retries)  │
│   • tray.rs               — macOS tray + Toggle Mascot menu             │
│   • updater.rs            — auto-update sig verification                │
│   • ws_client.rs          — connects to sidecar 8765 + 8766             │
│   • capabilities/         — Tauri ACL (LOCKED at Wave 2)                │
└──────────────────────┬──────────────────────────────────────────────────┘
                       │ stdio (line-buffered) + WebSocket
                       ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Process 2 — Python sidecar  (src/vibemix/, PyInstaller --onedir)      │
│  Owns audio/AI/state. Entry: src/vibemix/__main__.py:main()             │
│                                                                          │
│  Audio:   audio/ (AudioBuffer × 2, MicBuffer, Levels, PlaybackQueue)    │
│  Sense:   state/refresh.py:state_refresh_loop @100ms (THE writer)       │
│  Detect:  state/event_detector.py + state/detectors/* + events/genres/* │
│  Ground:  state/evidence_registry.py + coach/citation_linter.py         │
│  Agent:   agent/dj_cohost.py:DJCoHostAgent.llm_node (4-kwarg gate)      │
│  Coach:   runtime/coach.py:coach_loop @100ms                            │
│  Latency: agent/ack_bank.py + agent/cache.py + runtime/cancel.py        │
│           + runtime/ttft.py                                              │
│  MIDI:    midi/map_loader.py + midi/profiles/*.json (10 SKUs)           │
│  Buses:   runtime/ws_bus.py    — port 8765 (30Hz mascot + IPC mux)      │
│           __main__._run_debrief_sidecar — port 8766 (architectural slot)│
│  Subprocess flag: --debrief <session_dir> spawns DEBRIEF as 2nd sidecar │
│                  process owned by same Process-2 binary (PyInstaller    │
│                  produces ONE executable; --debrief is a flag dispatch).│
└──────────────────────┬──────────────────────────────────────────────────┘
                       │ HTTPS to api.altidus.world
                       ▼
┌────────────────────────────────────────────────────────────────────────┐
│  Process 3 — FastAPI proxy  (api.altidus.world — Bravoh-team operated) │
│  Owns Gemini API key + per-client rate limit + /healthz + updater POST │
│  (out of repo — Bravoh ops)                                             │
└────────────────────────────────────────────────────────────────────────┘
```

**Cross-process invariants v2.1 must NOT break:**

1. **AX bridge from Rust ONLY** — Tauri gh#8329 codebase grep gate (`tests/test_ax_rust_only.py` if not yet present, see Feature 11). Renderer can READ ax state via IPC; cannot CALL AX APIs.
2. **state_refresh_loop is the only writer of MusicState** — confirmed in `state/refresh.py`; one exception (`coach_loop` writes `state.last_kaan_spoke_at` inside `state._lock`).
3. **Single in-flight Gemini generation** — `trigger_state["in_flight"]` enforces this; stale-clear at 12s.
4. **POC files (`cohost.py`, `cohost_v2.py`, `cohost_lk.py`, `cohost_v4.py`, `mascot.html`) UNTOUCHED** — `tests/test_g5_poc_files_untouched.py` carries this gate.
5. **Anti-slop wired path is default-on** (`VIBEMIX_ANTI_SLOP=on` default) — 4-kwarg `DJCoHostAgent(citation_linter=, stripped_rate_tracker=, ack_bank=, playback=)` all-or-nothing.
6. **Tauri capability allowlist locks at Wave 2** — never widen mid-milestone unless explicit security pass approves.

**Sidecar subprocess pattern (DEBRIEF):** v2.0 reserved this. The sidecar binary supports a `--debrief <session_dir>` flag that spawns a **second instance of the same PyInstaller binary** with no audio I/O / no LiveKit, bound only to port 8766. This is "in the existing 3 processes" because the binary is the same; the OS sees 2 sidecar PIDs from the same exe path. v2.1 keeps this pattern — no fresh executable types.

---

## v2.1 Feature Integration Map

### Feature 1 — Autonomous Proxy Hallucination Gate (Phase 16 replacement)

- **Integration seam:** Out-of-band CLI invoked from CI (no live-runtime touchpoint). The harness loads a recording dir (`recordings/<YYYYMMDD-HHMMSS>/`) and replays `input.wav` through the SAME shipped primitives the live runtime uses: `AudioBuffer` (re-fill from the WAV), `state_refresh_loop` (driven manually in fast-forward mode), `EventDetector.detect()`, `EvidenceRegistry.write()`, `CitationLinter.lint()`, the Phase 22 anticipation `state_machine.tick()`, etc. No mock primitives — primitives are imported from `vibemix.*` so the harness exercises real code paths.
- **New components:**
  - `scripts/eval/replay_harness.py` — orchestrator. CLI: `python -m scripts.eval.replay_harness --session <dir> --judge <model>`. Loads input.wav + events.jsonl, reconstructs MusicState ticks, runs detectors, dumps predicted-events JSONL alongside ground-truth events.jsonl.
  - `scripts/eval/judge.py` — Gemini LLM-judge scorer. For each fired reaction, sends (audio snippet + cited evidence + Gemini text + grounded MusicState diff) to Gemini 3 Pro with a rubric: classify as `grounded | partial | hallucinated`. Outputs JSONL verdicts. Uses the proxy in CI (no raw key); locally via `GEMINI_API_KEY`.
  - `scripts/eval/f1.py` — F1 + precision/recall calculator. Compares predicted vs ground-truth event timestamps (±2s tolerance per GROUND-07) and judge verdicts; emits CSV + markdown report.
  - `recordings-eval/` (NEW dir, gitignored, populated from Kaan's actual sessions) — the replay corpus. Recordings are too large for git; CI fetches from a GitHub Release asset or R2 bucket (Bravoh-team supplies). Use small fixtures (`tests/eval/fixtures/`) for unit tests.
  - `tests/eval/test_replay_harness.py` + `tests/eval/test_judge.py` + `tests/eval/test_f1.py` — unit tests using tiny WAVs (~5s) + canned ground-truth.
  - `.github/workflows/eval.yml` — NEW workflow runs on PR-to-main + nightly. Steps: fetch corpus → replay harness → judge (via proxy) → F1 → fail PR if `hallucinated_rate > 5%` or `f1 < 0.75`.
- **Data flow:** `recordings/<sess>/input.wav` → `AudioBuffer.fill_from_wav()` (NEW method; tiny extension to `audio/buffers.py`) → tick refresh loop in `time_warp` mode → events fire → registry writes → ground-truth alignment → judge call → F1 → CSV. **No state shared with live runtime.**
- **Build order:** Depends on shipped P17 + P18 + P19 + P20 + P22 (all in v2.0). No v2.1 prerequisite — can build in parallel with Features 3–13 immediately.
- **Pattern:** **NEW out-of-band harness; extends nothing in the live runtime** — only adds a `fill_from_wav` helper to AudioBuffer (additive, default callers unaffected).
- **Cross-platform:** Mac+Win — pure-Python; runs in CI on both. The judge uses the proxy in CI (no platform-specific deps). PARITY GREEN.
- **Suggested phase:** **Phase 27** — earliest-possible bucket, runs in parallel with Phases 28–34.
- **Shared state:** None. Harness reads recordings only; never mutates live registry.
- **New IPC?:** No.
- **New process?:** No. CLI subprocess of `python -m scripts.eval.*` only (transient, dies at completion).

---

### Feature 2 — Library Intelligence v1 (Gemini Embedding 2 + sqlite-vec/numpy fallback)

- **Integration seam:** Three seams. (a) Sidecar: extends `state/evidence_registry.py:register_library` (already shipped Plan 25-02 but orphaned — see audit WARNING) by adding the embedding-index call site IN `__main__.py` between line ~698 (refresh_task creation) and line ~717 (coach_task creation). (b) Sidecar IPC: extends `ui_bus/messages.py` schemas with `ipc.library.import`, `ipc.library.search`, `ipc.library.status` running on existing port 8765. (c) Renderer: new Settings → Library panel reusing existing `tauri/ui/src/settings/SettingsDrawer.ts` registration pattern.
- **New components:**
  - `src/vibemix/library/embed.py` — `LibraryEmbedder` class. Calls Gemini Embedding 2 multimodal endpoint (text title + optional 30s audio preview if local file available) via the proxy. Batches at 100 tracks/call. Memoizes by track UUID + sha1(file mtime) so re-imports reuse work.
  - `src/vibemix/library/index_sqlite_vec.py` — sqlite-vec backend (Mac primary; sqlite-vec is the recommended local vector store and works cross-platform but compiles via wheels). One table per registry: `library_embeddings(track_id PRIMARY KEY, vector BLOB, ts REAL)`. KNN via the sqlite-vec `vec_search()` virtual table.
  - `src/vibemix/library/index_numpy.py` — numpy fallback. Loads all vectors into a flat `(N, D)` ndarray on first query; computes cosine similarity by matrix-multiply. Used when sqlite-vec wheel doesn't ship on Windows ARM or when the user opts out via env.
  - `src/vibemix/library/store.py` — façade that picks `sqlite_vec` if available else `numpy`. Single interface: `add(track_id, vector)`, `knn(query_vector, k)`, `save()`, `load()`.
  - `src/vibemix/library/search.py` — `vibe_search(text_query, k=10)`. Embeds query → KNN → returns track IDs ordered by similarity → resolves via `RekordboxLibrary.tracks`.
  - `src/vibemix/library/staleness.py` — `is_stale(library_pkl, threshold_days=30)` boolean. Drives the 30-day nudge IPC envelope.
  - `tauri/ui/src/settings/components/library-panel.ts` — drag-drop UI extending the SettingsDrawer pattern. Accepts `.xml` (Rekordbox collection) drop; calls `ipc.library.import`. Shows index status + 30-day staleness chip.
  - `src/vibemix/ui_bus/schemas/library.json` — 4 new schemas: `ipc.library.import`, `ipc.library.search`, `ipc.library.status`, `ipc.library.stale-nudge`.
  - Cache location: `~/Library/Application Support/vibemix/library/` (Mac), `%APPDATA%/vibemix/library/` (Win). Files: `collection.pkl` (parsed Rekordbox), `embeddings.db` (sqlite-vec) OR `embeddings.npy` + `embeddings_ids.json` (numpy).
- **Data flow:**
  - **Import:** Renderer drag-drop → `ipc.library.import {path}` → sidecar parses XML via `library/rekordbox.py:RekordboxLibrary.from_xml()` → `LibraryEmbedder.embed_all(lib)` → `LibraryStore.add_batch(…)` → `EvidenceRegistry.register_library(lib)` (this CLOSES the v2.0 orphaned seam) → `ipc.library.status {done, count}`.
  - **Vibe search:** AI in-prompt grounding: `AICoach.build_prompt(ev, registry_snapshot)` (already wired) — Phase 27 extends `AICoach` to optionally include the top-3 vibe-match track titles as `[mix:vibe-match-N]` evidence when the genre context warrants it. Existing `[track:<id>]` citation grammar already accepts this — Phase 18 grammar locks `track` as a valid source.
  - **30-day nudge:** sidecar boot-time check (right after `sweep_crashed_sessions`) → if stale → `ipc.library.stale-nudge` envelope → renderer shows chip in Settings → Library.
- **Build order:** Depends on P25 shipped (RekordboxLibrary + `register_library`). Must be sequenced AFTER Feature 7 (long-term DJ profile) only if profile wants to reference vibe-match track IDs — recommend Feature 2 ships FIRST, Feature 7 reads from it.
- **Pattern:** **DOCK-TO-SLOT** — `register_library` is the slot, the v2.0 orphaned seam closes by Feature 2 calling it. Plus **EXTEND** `EvidenceRegistry` (no new source — `track` already valid).
- **Cross-platform:**
  - **sqlite-vec** ships pre-built wheels for `osx-arm64`, `osx-x86_64`, `win-amd64`, `linux-x86_64`. Mac+Win supported. Verify with `pip install sqlite-vec` in CI matrix.
  - **Fallback**: numpy-only on any platform where sqlite-vec wheel fails to install (`pip` falls back to source build → fail → numpy backend takes over). PARITY GREEN.
  - File paths use `runtime/config_store.app_data_dir()` which returns OS-native paths.
- **Suggested phase:** **Phase 28** — depends on nothing in v2.1 other than the 5-min orphan-closing patch from v2.0 audit (which Phase 27 can absorb).
- **Shared state:** EXTENDS `EvidenceRegistry` only (already shipped). No new sibling store.
- **New IPC?:** YES — 4 new schemas on existing port 8765. **Schema additions** (not new bus) — extend `ui_bus/schemas/messages.schema.json` with the 4 envelope shapes; renderer validator picks them up automatically.
- **New process?:** No. Embedding work runs as `loop.run_in_executor(None, …)` on the sidecar's existing executor (offload from event loop because embedding round-trips block ~50-200ms each).

---

### Feature 3 — Post-session Debrief MVP UI (dock to DEBRIEF-01/02 IPC)

- **Integration seam:** Two seams. (a) Sidecar: `__main__.py:_run_debrief_sidecar(session_dir)` (already shipped as architectural slot — currently logs a banner and exits). Phase 29 replaces the banner-log with the real session-replay → chapter-generation → TL;DR-synthesis flow. (b) Renderer: Settings → Recordings → click row → opens a NEW Tauri WebviewWindow (debrief panel) which connects to `ws://127.0.0.1:8766` (DEBRIEF port already reserved).
- **New components:**
  - `src/vibemix/debrief/` — NEW package.
    - `debrief/__main__.py` (extends the `_run_debrief_sidecar` body) — owns the lifecycle. Loads `session.json` + `events.jsonl` + `input.wav` + `voice.wav` from the session dir, calls `chapters.py` and `tldr.py`, exposes WS endpoint.
    - `debrief/chapters.py` — derives chapter markers by grouping events.jsonl into 3-7 segments based on event clustering + phase transitions. Returns `[(t_start, t_end, label)]`.
    - `debrief/tldr.py` — generates 60-90s voiced TL;DR. Calls Gemini 3 Flash with the event timeline + 3 chapter excerpts → produces text → calls the existing OpenRouter/Gemini TTS chain via `agent/tts_chain.py` → writes `tldr.opus` next to session files.
    - `debrief/drills.py` — generates 3 interactive drills (e.g. "EQ this section blind", "predict the kick swap"). Drill cards are JSON envelopes the renderer renders inline.
    - `debrief/ws_server.py` — port 8766 WebSocket server using the same `websockets` library. Emits `ipc.debrief.chapter` (DEBRIEF-01), `ipc.debrief.tldr` (DEBRIEF-02), `ipc.debrief.drill` (NEW, scoped to debrief bus — does not collide with live bus on 8765).
  - `tauri/ui/src/debrief/` — NEW renderer route.
    - `debrief/DebriefPanel.ts` — main component. Connects to ws://127.0.0.1:8766. Reuses existing `tauri/ui/src/session/components/timecode.ts` for the clickable timeline.
    - `debrief/components/audio-player.ts` — uses **WaveSurfer.js** (already widely used in the Bravoh stack per CLAUDE.md) for the audio playback + waveform. Loads `voice.wav` + `input.wav` via Tauri `asset://` protocol (already in tauri.conf.json5 scope from Phase 15).
    - `debrief/components/chapter-strip.ts` — chapter markers overlaid on waveform.
    - `debrief/components/drill-card.ts` — 3 interactive drill cards.
  - `tauri/src-tauri/src/debrief_window.rs` — new Tauri command `open_debrief_window(session_dir: String)` that spawns the debrief sidecar with `--debrief <session_dir>` AND creates a new WebviewWindow targeting the `/debrief?session=<id>` route. (Re-uses existing webview-creation pattern from `mascot_window.rs`.)
  - `tauri/src-tauri/capabilities/default.json` — extend allowlist to permit the debrief WS connection (already permitted to 127.0.0.1:8766 per Phase 25 reservation — verify the entry exists).
- **Data flow:** Settings → Recordings list (Phase 15) → row click → `invoke("open_debrief_window", { session_dir })` → Rust spawns `vibemix --debrief <session_dir>` subprocess → renderer opens new WebviewWindow → window connects to ws://127.0.0.1:8766 → receives chapter + TL;DR + drill envelopes → renders panel.
- **Build order:** Depends on P15 (recording browser — list of recordings exists), P25 (DEBRIEF architectural slot — port + schemas reserved). No v2.1 prerequisite.
- **Pattern:** **DOCK-TO-SLOT** — Phase 25 ships the slot (port, flag, schemas); Phase 29 fills it.
- **Cross-platform:**
  - Mac: Quartz screen capture not needed (debrief reads recorded files only).
  - Win: same — pure file I/O + Gemini cascade.
  - WaveSurfer.js is browser-native; identical Mac+Win.
  - Tauri `asset://` protocol works identically Mac+Win.
  - PARITY GREEN.
- **Suggested phase:** **Phase 29** — depends on Feature 2 indirectly (track citations show in chapter labels look better with library import). Can ship without Feature 2 too.
- **Shared state:** None across processes — debrief sidecar reads its session dir, doesn't touch the live EvidenceRegistry. Reads recorded `events.jsonl` only.
- **New IPC?:** EXTEND existing port-8766 schemas (DEBRIEF-01, DEBRIEF-02 already reserved). One genuinely new schema: `ipc.debrief.drill` — fits into the same v2.0-reserved namespace.
- **New process?:** Already permitted — `--debrief` flag of the same sidecar binary. Lifecycle: spawned-on-open-debrief-window, dies on close-window. The Rust shell tracks the child PID (extension of `sidecar.rs:SidecarHandle` pattern).

---

### Feature 4 — 4-Layer Mascot Full Additive State Machine

- **Integration seam:** `tauri/ui/src/mascot/state-machine.ts` + `tauri/ui/src/mascot/additive-layer.ts` (both shipped v2.0). State machine currently models 3 layers (mood + anticipation + speak/react per `additive-layer.ts` comment "v2.0 ships the 3-layer subset"). Phase 22 explicitly notes 4-layer is deferred to v2.1.
- **New components:**
  - **REWRITE in place** — `tauri/ui/src/mascot/state-machine.ts` extends from 3-layer to 4-layer additive priority stack. NO new files; same file gains:
    - `BaseLayer` (priority 50) — idle/breathing/talk/dance (always-on, weight 1.0 baseline).
    - `EmotionLayer` (priority 60) — mood: hype-man/coach/critic facial overlays.
    - `AnticipationLayer` (priority 70) — already shipped — `prep_*` clips, additive.
    - `ReactionLayer` (priority 80) — punch/cover-ears/squint, dispatched by `ev:<TYPE>` envelopes.
    - All four layers share the SAME `AnimationMixer` (Pitfall 19 — ONE mixer, no exceptions). Each layer is an `AnimationAction` with its own weight envelope.
  - `tauri/ui/src/mascot/priority-stack.ts` — NEW small module. Owns the priority-resolution policy: when two layers want incompatible animations (e.g. base says "dance" + reaction says "punch_air"), the higher-priority layer wins for its claimed bone subset; the rest of the body keeps the lower-priority animation. Uses Three.js `AnimationAction.setLoop()` + bone-mask via `addMixerAction(action, mask)`.
  - `tauri/ui/src/mascot/crossfade-policy.ts` — NEW. Per-layer crossfade durations (base=400ms, emotion=600ms, anticipation=200ms [already shipped], reaction=80ms [snappy]).
  - `src/vibemix/runtime/ws_bus.py` — EXTEND existing 30Hz payload. Already broadcasts `{music, voice, mic, audible, deck, phase, bpm, mood, bpm_confidence, downbeat_phase, beat_phase, active_genre}`. Add: `emotion` (driven by stripped-rate + recent-event-type history), `reaction_intent` (driven by EventDetector last-fire — `{type, t_session, ttl_ms}`). No new bus; same payload.
- **Data flow:** sidecar `ws_broadcast` payload at 30Hz includes `emotion` + `reaction_intent` → renderer `mascot/ws-client.ts` (already shipped) parses → `state-machine.dispatch({type: "WS_PAYLOAD", payload})` → priority-stack resolves → `additive-layer.play(state, opts)` on the right layer.
- **Build order:** Depends on Phase 22 (AdditiveLayer + asset-loader + state-machine all shipped). No other dependency.
- **Pattern:** **EXTEND** — same files, more layers; priority-stack module is the new piece.
- **Cross-platform:**
  - Three.js webview-rendered identically Mac+Win.
  - GLB asset loading uses `asset://` protocol — same on both.
  - PARITY GREEN.
- **Suggested phase:** **Phase 31** — sequenced after Phase 30 (Hard Tek detectors land first so reaction_intent has new event types to dispatch on).
- **Shared state:** EXTENDS `MusicState.mood` (already exists). Adds derived `state.emotion` written by `refresh.py` (NEW field; one-line dataclass addition). No new sibling store.
- **New IPC?:** No — extends existing 30Hz mascot payload on port 8765.
- **New process?:** No.

---

### Feature 5 — 2 Hard Tek Detectors (DISTORTION_CLIMB + ACID_LINE_ENTRY)

- **Integration seam:** `src/vibemix/state/detectors/` — already houses 6 v2.0 detectors. `src/vibemix/events/genres/hard_tek.py` — already shipped, comment explicitly says "v2.1 will add DISTORTION_CLIMB + ACID_LINE_ENTRY here". Plan is literally pre-committed.
- **New components:**
  - `src/vibemix/state/detectors/distortion_climb.py` — class `DistortionClimbDetector` with `detect(state, audio_buf)` method. DSP: rolling 4s window crest-factor + harmonic distortion ratio (THD via FFT). Fires when THD ratio rises >40% over a 3-bar window concurrent with RMS rising. Cooldown 12s.
  - `src/vibemix/state/detectors/acid_line_entry.py` — class `AcidLineEntryDetector`. DSP: tracks 303-style resonant filter sweep signature in 200-800Hz band — detects a sudden harmonic peak migration upward over 2 bars. Cooldown 18s.
  - `src/vibemix/state/detectors/__init__.py` — export both new classes.
  - `src/vibemix/events/genres/hard_tek.py` — replace `build_hard_tek_chain()` to append `DistortionClimbDetector()` + `AcidLineEntryDetector()` after the 5 shared detectors.
  - `scripts/tune_detectors.py` — EXTEND. v2.0 ships this for the 6 baseline detectors. Add 2 new rows to the genre-grouped output. Pull tuning thresholds from JSON in `src/vibemix/state/detectors/_constants.py` (NEW small file — pull tuning out of detector classes).
  - `src/vibemix/state/evidence_registry.py` — no change. `ev:DISTORTION_CLIMB` and `ev:ACID_LINE_ENTRY` already valid via `EVIDENCE_SOURCES = {ev, …}`. EventDetector._fire writes the observation automatically.
  - `tests/state/detectors/test_distortion_climb.py` + `test_acid_line_entry.py` — synthesized WAV fixtures (numpy-generated saturating sines).
- **Data flow:** `state_refresh_loop` writes MusicState diffs → `EventDetector.detect()` calls `GenreRouter.swap(state.active_genre)` then iterates chain detectors → on hard_tek active, the 2 new detectors fire → `_fire("DISTORTION_CLIMB", ...)` writes registry observation → coach_loop dispatches to agent → reaction.
- **Build order:** Depends on Phase 17 (GenreRouter + chain pattern shipped). No v2.1 prerequisite.
- **Pattern:** **EXTEND** — same chain, two more detectors slotted in.
- **Cross-platform:** Pure-numpy DSP. PARITY GREEN.
- **Suggested phase:** **Phase 30** — earliest sensible, runs in parallel with Phase 28 (library) and Phase 29 (debrief). Detector authors don't block on those.
- **Shared state:** Writes to `EvidenceRegistry` (already shipped). No new state.
- **New IPC?:** No.
- **New process?:** No.

---

### Feature 6 — Long-term DJ Profile (~2KB JSON session-regenerated)

- **Integration seam:** `agent/dj_cohost.py:DJCoHostAgent.__init__` system instruction build (line ~178). The profile becomes a SECOND prompt block injected verbatim ahead of the citation grammar. Plus a sidecar-side builder that writes the profile at end-of-session.
- **New components:**
  - `src/vibemix/profile/` — NEW package.
    - `profile/builder.py` — `build_profile(events_jsonl_paths, embedding_store) -> Profile`. Walks last 10 session `events.jsonl` files, extracts (a) common event-type distribution, (b) most-cited track IDs, (c) mode/skill/mood preferences, (d) avg session BPM range, (e) common pitfalls (turns stripped >2 in a row, etc.). Output is a `Profile` dataclass ~2KB serialized.
    - `profile/profile.py` — `@dataclass class Profile` + `to_prompt_block(self) -> str` (must enforce 2KB ceiling — token-count check via `tiktoken` or a simple char-budget proxy).
    - `profile/cache.py` — load/save `~/Library/Application Support/vibemix/profile/<install_uuid>.json` (NOT per-session — the AUDIT clarifies "session-regenerated" means recomputed once per session-start). Single file per install_uuid (already a stable ID from Phase 5).
    - `profile/disclosure.py` — first-session-after-feature-ship banner: "vibemix now adapts to your DJ profile. Stored locally only. Disable in Settings."
  - `tauri/ui/src/settings/components/profile-group.ts` — Settings → DJ Profile panel. Shows current profile JSON readable form + toggle to disable + "Re-derive now" button. Reuses existing `settings/components/group.ts` pattern.
  - `src/vibemix/__main__.py` — boot-time addition (right after `apply_genre_env`): `profile = ProfileLoader.load_or_build()` → pass to `DJCoHostAgent(profile=profile)`.
  - `src/vibemix/agent/dj_cohost.py` — extend `__init__` to accept `profile: Profile | None = None`. When non-None, prepend `profile.to_prompt_block()` to the system_instruction body. Default None preserves the byte-identical Phase 4 path.
- **Data flow:**
  - **Build (end of session):** `coach_loop` finally block (line ~801 in `__main__.py`) → `ProfileBuilder.update_from_session(events_jsonl_path)` → atomically writes new profile JSON.
  - **Inject (start of session):** `__main__.main()` boot → `Profile.load()` → `DJCoHostAgent(profile=profile)` → system instruction has profile prefix.
  - **Disclosure:** first-run gate via `runtime/config_store.py` flag `profile_disclosed: bool`. If False on session start, sidecar emits `ipc.session.profile-disclosure` envelope → renderer shows modal → on dismiss, sidecar writes flag True.
- **Build order:** Depends on Feature 2 (Library intelligence — most-cited track IDs in profile need the library), Feature 5 (Hard Tek detectors — profile distributions include `DISTORTION_CLIMB` once that exists).
- **Pattern:** **EXTEND** — DJCoHostAgent gains one optional kwarg.
- **Cross-platform:** Pure JSON; OS-native paths via `app_data_dir()`. PARITY GREEN.
- **Suggested phase:** **Phase 32** — after Phases 28 + 30.
- **Shared state:** New on-disk JSON file (per-install, not per-session). NO new in-memory store — `Profile` is constructed in `main()` and passed by ref to agent (same pattern as `EvidenceRegistry`).
- **New IPC?:** One — `ipc.session.profile-disclosure` envelope (single-shot, first-run only).
- **New process?:** No.

---

### Feature 7 — One-Click Install Hardening

- **Integration seam:** `tauri/ui/src/wizard/` (already shipped Phase 11). Phase 33 extends the 4-step wizard to fully autonomously handle TCC pre-grant + dep fetch + recovery flows.
- **New components:**
  - `tauri/src-tauri/src/permissions.rs` — EXTEND. Add commands:
    - `check_tcc_screen_recording() -> TccStatus` — invokes `tccutil` (when running with adequate entitlements) or falls back to a probe (capture 1px screenshot, check error). Returns `granted | denied | not_determined`.
    - `check_tcc_microphone() -> TccStatus` — same pattern via AVCaptureDevice probe in a tiny Swift helper bundled into the app.
    - `check_tcc_accessibility() -> TccStatus` — AX-API probe (matches the existing `djay_ax.rs` AX permission check).
    - `pre_grant_tcc_via_osascript()` — opens System Settings deep-link sequentially for each missing permission.
  - `tauri/ui/src/wizard/step1-permissions.ts` — EXTEND. Auto-polls TCC status every 1s while user is in the permissions step; advances automatically once all 3 grant. Recovery: if user denies, show "Why we need this" + open-settings button.
  - `scripts/install_rehearsal/` — NEW.
    - `install_rehearsal/macos.sh` — fresh-VM rehearsal script. Boots a Tart VM (lightweight macOS hypervisor — `brew install cirruslabs/cli/tart`), uploads DMG, runs `installer -pkg` (or drag-mount), launches the app, screencast-records the wizard flow via `xcrun simctl` recording, asserts all 3 permissions reach `granted`.
    - `install_rehearsal/windows.ps1` — same pattern via Windows Sandbox or HyperV.
    - `install_rehearsal/run_all.sh` — orchestrator that runs both VMs in CI.
  - `.github/workflows/install-rehearsal.yml` — NEW workflow, manual-trigger + nightly. Runs the rehearsal scripts against the latest signed DMG/MSI; uploads screencasts as artifacts.
  - `tauri/ui/src/wizard/step4-onboarding.ts` — NEW final wizard step. 30-second "what is vibemix" cinematic (Phase 26 viral demo film) + "Open your DJ software now" cue + skip button.
  - `src/vibemix/runtime/wizard.py` — EXTEND. Currently runs the 8 `ipc.wizard.*` handlers. Add: `ipc.wizard.recovery` — when sidecar fails to find BlackHole / audio device, emits this; renderer routes to a recovery sub-flow.
- **Data flow:**
  - **First-run:** Rust launches `vibemix --wizard` (already wired). Wizard webview drives the 4-step flow. Step 1 polls TCC every 1s; step 2 calls sidecar to enumerate audio devices; step 3 lists detected controllers; step 4 ends with onboarding cinematic.
  - **Recovery:** Audio device missing → `--wizard` flag re-enters from step 2 with a "BlackHole missing" banner + 1-click `brew install blackhole-2ch` button (via `osascript` helper). Codified in `tauri/src-tauri/src/sidecar.rs` exit-3 handler (already shipped).
- **Build order:** Depends on Phase 11 (wizard shipped). No v2.1 prerequisite.
- **Pattern:** **EXTEND**.
- **Cross-platform:**
  - macOS: Tart VM rehearsal, osascript deep-links, tccutil + AVCaptureDevice probes.
  - Windows: Windows Sandbox / HyperV rehearsal. NO TCC equivalent — Windows surfaces permissions at first-capture; the wizard step 1 collapses to "no action needed on Windows" with a single confirm button.
  - Divergence: TCC pre-grant logic is mac-only. Wizard step1 has a `#[cfg(target_os = …)]` branch in both Rust + TS layers.
- **Suggested phase:** **Phase 33** — sequenced after sign+notarize Feature 12 lands (rehearsal needs signed DMG/MSI).
- **Shared state:** Extends `runtime/config_store.py` with `first_run_completed_at`, `tcc_pre_grant_attempted` flags. No new sibling store.
- **New IPC?:** One — `ipc.wizard.recovery`. Extends existing wizard IPC namespace on port 8765.
- **New process?:** No (the VM rehearsal scripts run in CI/CD, not at app runtime).

---

### Feature 8 — Open-Source Security Pass

- **Integration seam:** Two layers — CI gates + runtime defenses.
- **New components:**
  - `.github/workflows/security.yml` — NEW workflow.
    - Job 1: `secret-scanner` — runs [gitleaks](https://github.com/gitleaks/gitleaks) + `trufflehog` against every PR; fails on findings.
    - Job 2: `cve-audit` — runs `pip-audit` against `pyproject.toml` lockfile + `cargo audit` against `Cargo.lock` + `npm audit --production` against `tauri/ui/`. Fails on `severity: high|critical`.
    - Job 3: `binary-verify` — re-fetches the latest signed DMG/MSI from GitHub Releases, runs `codesign --verify` + `signtool verify`, asserts notarization stapled.
    - Job 4: `permission-least-scope-lint` — greps `tauri/src-tauri/capabilities/default.json` against an allowlist baseline (`tests/security/capability-baseline.json`); fails if the runtime capability set grew without baseline update.
  - `.github/workflows/release.yml` — EXTEND with binary-verify post-step (after publish, fetch the just-published asset, re-verify, post comment to release).
  - `.pre-commit-config.yaml` — NEW. Local pre-commit hook: gitleaks + AIza-pattern scan (re-use `scripts/dist/verify_binary.py`'s pattern bank but apply to source).
  - `SECURITY.md` — NEW at repo root. OSS reporting policy + supported versions + PGP key fingerprint.
  - `docs/threat-model.md` — NEW. STRIDE-style threat model: T-1 API-key-leak-in-binary (mitigated by proxy), T-2 capability-widening (mitigated by Wave-2 lock + lint), T-3 sidecar privilege-escalation (mitigated by `parent_watchdog.py` orphan-kill), T-4 supply-chain (mitigated by `pip-audit` + `cargo audit`), T-5 social-engineering-via-screen (mitigated by AX-from-rust-only).
  - `scripts/security/` — NEW.
    - `security/check_capability_baseline.py` — local + CI lint helper.
    - `security/check_secrets.py` — recursively scans for AIza / sk- / signing-key patterns + git history.
  - `src/vibemix/runtime/parent_watchdog.py` — already shipped Phase 11 — verify orphan kill works (covered in v2.0 audit).
  - `src/vibemix/runtime/sec_check.py` — NEW. Sidecar startup self-check: validates that no env var leaks API keys, that `~/.config/vibemix/` is mode 0700, that the proxy hostname matches expected `api.altidus.world` (no DNS poisoning fallback). Logs warnings to stderr; never fails the run.
- **Data flow:** CI-side gates only — no runtime data flow change.
- **Build order:** Depends on Phase 21 (release workflow). Should land EARLY in v2.1 so subsequent phases ship clean. **Run in parallel with Phase 27.**
- **Pattern:** **EXTEND** existing CI + ADD docs.
- **Cross-platform:** CI runs on both mac + windows runners (already configured). PARITY GREEN.
- **Suggested phase:** **Phase 34** — but realistically threads continuously across the milestone; mostly land it in one bucket then maintenance via PR gates.
- **Shared state:** None.
- **New IPC?:** No.
- **New process?:** No.

---

### Feature 9 — Real GLB Mascot Animations + 30s Viral Demo Film (Autonomously)

- **Integration seam:** Two seams — (a) GLB assets: `tauri/src-tauri/resources/mascot/*.glb` (already shipped 5 stub `prep_*` placeholders). v2.1 replaces stubs with real GLBs + adds the new layer animations (base + emotion + reaction palettes). (b) Demo film: NEW pipeline that captures a real session screen + sidecar overlay + mascot, edits in ffmpeg, voiceovers via Gemini TTS.
- **New components:**
  - `scripts/mascot_pipeline/` — NEW.
    - `mascot_pipeline/text_to_3d.py` — wraps Meshy / Hunyuan3D API (per memory `project_mascot_as_vtuber_personality_surface`). Text-prompt → GLB. Configured via `mascot_pipeline/character.json` (the locked DJ-bat description).
    - `mascot_pipeline/mixamo_rig.py` — Mixamo auto-rig step. The pipeline uploads the unrigged GLB to Mixamo (via headless puppet — Mixamo doesn't have a public API, this is the legacy-but-known-working method using `requests` + a recorded session) OR uses `mixamo-mass-fbx-to-gltf` open-source pipeline if a manual rig file exists.
    - `mascot_pipeline/animate.py` — takes the rigged GLB, applies named Mixamo clips (idle, talk, dance, punch, cover_ears, lean_left, lean_right, prep_drop, prep_breakdown, prep_layer, prep_reentry, prep_swap, emotion_hype, emotion_critic), saves merged GLB.
    - `mascot_pipeline/manifest.py` — produces `tauri/src-tauri/resources/mascot/manifest.json` mapping mascot state → clip name + bone mask + loop policy.
    - `mascot_pipeline/run_all.sh` — orchestrator. Idempotent — skips existing GLBs.
  - `tauri/src-tauri/resources/mascot/ASSETS.md` — EXTEND. Document the real GLB provenance (Meshy session ID, Mixamo clip IDs, license).
  - `scripts/demo_film/` — NEW.
    - `demo_film/record_session.py` — wraps existing recording infra. Starts a sidecar with `RECORD_SCREEN=1` env var (NEW addition to `runtime/diag.py`), which uses `mss` (Mac) / `win32` (Win) to capture the full screen at 30fps to `session_screen.mp4`. Records 60s.
    - `demo_film/edit.py` — ffmpeg-based edit. Picks the 3 "beats" automatically from `events.jsonl`: (1) BREAKDOWN_KICK_KILL (silence + overlay highlight + mascot prep), (2) REENTRY_KICK_LAND (mascot punch + voice reaction), (3) a TRACK_CHANGE flourish. Cuts to 30s total.
    - `demo_film/voiceover.py` — generates 30s voiceover via Gemini TTS (Achird voice). Script auto-derived from events.jsonl.
    - `demo_film/render.py` — final ffmpeg compose: screen capture + voiceover + lower-third graphics (vibemix wordmark + URL).
  - `scripts/demo_film/run_all.sh` — orchestrator.
  - `tauri/ui/src/wizard/step4-onboarding.ts` (Feature 7) — references the resulting 30s film by `asset://demo.mp4` (bundled into Tauri resources OR streamed from GitHub Release).
- **Data flow:** Out-of-band pipeline — Kaan runs `bash scripts/mascot_pipeline/run_all.sh` once (or CI runs it on demand) → GLBs land in `tauri/src-tauri/resources/mascot/`. Demo film pipeline: `bash scripts/demo_film/run_all.sh` records a real session → `demo.mp4` lands in `tauri/src-tauri/resources/marketing/`. Both bundled into the Tauri install via `tauri.conf.json5` bundle.resources entry.
- **Build order:** Depends on Feature 4 (4-layer mascot — need to know the full animation palette before generating GLBs). Sequenced AFTER Phase 31.
- **Pattern:** **EXTEND** assets + **NEW** out-of-band pipeline.
- **Cross-platform:**
  - Pipeline runs on Mac only (Kaan's primary box). Output GLBs / MP4 are platform-neutral.
  - Bundled identically into Mac DMG + Win MSI.
  - PARITY GREEN at runtime; pipeline is Mac-host-only.
- **Suggested phase:** **Phase 35** — after Feature 4.
- **Shared state:** None at runtime; build-time only.
- **New IPC?:** No.
- **New process?:** No (pipeline runs as developer/CI script, not in the deployed binary).

---

### Feature 10 — Day-Zero Ops Automation

- **Integration seam:** `scripts/dayzero/` (already shipped Phase 26 with `healthz_check.sh` + `proxy_load_test.py`). Phase 36 extends with Discord auto-provisioning + GitHub release publish automation + load test runner wiring + healthz exporter telemetry.
- **New components:**
  - `scripts/dayzero/discord_provision.py` — NEW. Uses Discord API (Bot token via env) to:
    - Create the vibemix server (or update if exists).
    - Create 12 channels (#announcements, #showcase, #help-mac, #help-windows, #controller-requests, #bug-reports, #feature-requests, #vibemix-dev, #releases, #voice-techno, #voice-house, #voice-hard-tek).
    - Assign roles (Beta-Tester, Maintainer, Contributor).
    - Post seed-message in #announcements.
    - Output the invite link to stdout for the launch-trigger sequence.
  - `scripts/dayzero/release_publish.py` — NEW. Wraps `gh release create` + uploads DMG/MSI/zip artifacts + writes release notes from `CHANGELOG.md` head section. Triggers `gh workflow run release.yml` after.
  - `scripts/dayzero/proxy_load_test.py` — EXTEND. Phase 26 ships baseline; Phase 36 adds (a) sustained-load mode (100 RPS × 5min), (b) p99 latency assertion (`<500ms`), (c) healthz cross-check during load.
  - `scripts/dayzero/healthz_exporter.py` — NEW. Polls `https://api.altidus.world/healthz` every 30s, exports Prometheus-format metrics. Optional — for ops dashboard.
  - `scripts/dayzero/launch_trigger.sh` — EXTEND. Phase 26 ships skeleton; Phase 36 codifies the T-30/T+0/T+5/T+24h sequence with `at` / `cron` scheduling. Each step's command is precommitted; the shell flips ENABLED flags so Kaan can dry-run vs hot-run.
  - `.github/workflows/release.yml` — extends with social-post-publish step (NEW Feature 13). See Feature 13.
- **Data flow:** Out-of-band — runs from a launch box (likely Kaan's Mac). Never touches the deployed app binary.
- **Build order:** Depends on Phase 21 + Phase 26 (release.yml + day-zero scripts shipped). No v2.1 prerequisite.
- **Pattern:** **EXTEND** scripts.
- **Cross-platform:** Scripts target macOS host (Kaan's machine); proxy load test is platform-neutral (Python). PARITY GREEN.
- **Suggested phase:** **Phase 36** — late in v2.1, parallel with Feature 13.
- **Shared state:** None.
- **New IPC?:** No.
- **New process?:** No.

---

### Feature 11 — Cross-Phase Integration Audit Gate

- **Integration seam:** `.claude/agents/get-shit-done/integration-checker.md` (subagent already exists). Phase 37 wires an automated harness that the subagent calls, plus an E2E test directory.
- **New components:**
  - `tests/e2e/` — NEW.
    - `tests/e2e/test_seam_evidence_to_linter.py` — boots sidecar in-process with fake audio, writes a sentinel event, asserts linter reads it from registry within 1s.
    - `tests/e2e/test_seam_overlay_publish.py` — fakes a `[screen:CrossfaderA]` citation, asserts the overlay IPC envelope reaches the Rust ws_client.
    - `tests/e2e/test_seam_register_library.py` — checks `register_library` is INVOKED from `__main__` on boot (closes v2.0 audit WARNING).
    - `tests/e2e/test_seam_debrief_handshake.py` — spawns `vibemix --debrief <tmpdir>`, asserts port 8766 binds + emits chapter envelope.
    - `tests/e2e/test_seam_ax_rust_only.py` — codebase grep gate: `grep -r "Accessibility\|AXUIElement" src/vibemix/` returns zero hits. (Already shipped as a one-off — promote to e2e bucket.)
    - `tests/e2e/run_all.sh` — orchestrator running all e2e tests against a freshly-built sidecar.
  - `scripts/integration_audit.py` — NEW. Walks `.planning/milestones/v2.X-MILESTONE-AUDIT.md` template, generates a checklist of cross-phase seams from REQ-IDs, runs each e2e test, produces audit Markdown.
  - `.github/workflows/integration-audit.yml` — NEW. Manual-trigger workflow that runs `integration_audit.py` and uploads the report.
  - `.claude/agents/get-shit-done/integration-checker.md` — EXTEND with the canonical "every seam validated" pattern reference + e2e file naming convention.
- **Data flow:** CI-side — runs sidecar in subprocess, drives via test harness IPC, asserts post-conditions.
- **Build order:** Depends on EVERY OTHER FEATURE — runs as the gate at end of v2.1.
- **Pattern:** **EXTEND** subagent + NEW e2e harness.
- **Cross-platform:** Tests run on both runners. PARITY GREEN.
- **Suggested phase:** **Phase 37** — penultimate, after Features 1–10.
- **Shared state:** None.
- **New IPC?:** No (consumes existing schemas).
- **New process?:** No.

---

### Feature 12 — Signing Pipeline Autonomous Execution

- **Integration seam:** `.github/workflows/release.yml` (already shipped Phase 21 — mock-signing fallback in place). Phase 38 wires the real Apple notarytool + SignPath CLI flows.
- **New components:**
  - `.github/workflows/release.yml` — EXTEND. Replace mock-signing fallback with hard requirement when on `v*` tag:
    - macOS sign job: `scripts/dist/sign_macos.sh` already shipped — wire real `APPLE_DEVELOPER_ID_P12_BASE64` + `APPLE_TEAM_ID` + `APPLE_API_KEY_BASE64` + `APPLE_API_KEY_ID` + `APPLE_API_ISSUER_ID` secrets injection.
    - Windows sign job: SignPath `signpath/github-action-submit-signing-request@v1.2.0` step — wire `SIGNPATH_API_TOKEN` + `SIGNPATH_ORGANIZATION_ID` + `SIGNPATH_SIGNING_POLICY_SLUG` + `SIGNPATH_PROJECT_SLUG`.
    - Verifier job (NEW): post-sign, downloads the signed artifact, runs `codesign --verify --deep --strict` + `stapler validate` (mac) and `signtool verify /pa /v` (win); fails on red.
  - `scripts/dist/sign_macos.sh` (already shipped Phase 21) — verify the notarytool wiring is real not mock.
  - `scripts/dist/sign_windows.ps1` — NEW. Local rehearsal script (CI uses the SignPath GitHub Action directly; this is for Kaan to test signing locally before CI integration).
  - `docs/release-process.md` — EXTEND. Document secret injection procedure (GitHub repo → settings → secrets → add 9 mac + 4 win secrets).
  - `scripts/dist/verify_binary.py` — already shipped Phase 21 (AIza-pattern leak gate). EXTEND with notarization-status check + Win Authenticode validity check.
- **Data flow:** CI on `v*` tag push → build → sign → verify → publish to GitHub Releases → notify (Feature 13).
- **Build order:** Depends on (external) Apple Developer Program Agreement update + SignPath OSS approval. **HIGH external dependency** — Kaan must approve agreements before Phase 38 can be tested with real secrets. Code surface is buildable today.
- **Pattern:** **EXTEND**.
- **Cross-platform:** Two parallel sign jobs (mac + win). PARITY GREEN.
- **Suggested phase:** **Phase 38** — parallel with Feature 13. **Sequence with Feature 7 — install rehearsal Phase 33 NEEDS the signed binaries from Phase 38.** Recommend ordering: Phase 38 (sign) → Phase 33 (install harden + rehearsal).
- **Shared state:** None.
- **New IPC?:** No.
- **New process?:** No.

---

### Feature 13 — RC Cut + Ship Automation

- **Integration seam:** `.github/workflows/release.yml` (extended in Feature 12) + `scripts/launch/` (NEW).
- **New components:**
  - `scripts/launch/` — NEW.
    - `launch/publish_release.sh` — invokes Feature 10's `release_publish.py`.
    - `launch/publish_social_posts.py` — uses (a) Twitter API (X), (b) Instagram Graph API, (c) Discord webhook, (d) Reddit API. Reads pre-drafted post text from `.planning/research/v2-buckets/synthesis-viral-demo.md` or `BRANDING.md`. Manual approval gate before each post (interactive prompt OR `--auto` flag).
    - `launch/finalize_readme.sh` — replaces `README.md` hero banner with the final asset (Phase 26 ships drafts; Phase 39 finalizes). Generates social-preview OG image via headless Chrome screenshot of `mocks/vibemix-direction-final.html`. Updates badges, controller grid, etc.
    - `launch/cut_rc.sh` — orchestrator: bumps version → commits → tags `v2.1.0-rc1` → pushes → CI fires.
  - `.github/workflows/release.yml` — EXTEND with post-publish job:
    - Posts release URL to Discord (#releases channel).
    - Pings social-post-publish workflow (manual approval gate).
  - `BRANDING.md` — already shipped Phase 26. EXTEND with finalized hero asset paths.
- **Data flow:** Kaan runs `bash scripts/launch/cut_rc.sh v2.1.0-rc1` → tag pushes → CI builds + signs + publishes → post-publish job notifies Discord + opens approval for social posts → Kaan approves → posts go live.
- **Build order:** Depends on EVERY OTHER FEATURE — this is the gate that ships v2.1.
- **Pattern:** **NEW** scripts + EXTEND release workflow.
- **Cross-platform:** Scripts run on Mac host. PARITY GREEN.
- **Suggested phase:** **Phase 39** — final.
- **Shared state:** None.
- **New IPC?:** No.
- **New process?:** No.

---

## Cross-Cutting Concerns

### Zero-New-Process Discipline

All 13 features fit in the existing 3 processes:

- **Tauri Rust shell** gains new commands (`open_debrief_window`, `check_tcc_*`) and 1 new WebviewWindow (debrief). No new process spawned by Rust.
- **Python sidecar** gains new modules (library/, profile/, debrief/, eval scripts, security checks). Single binary with flag dispatch (`--debrief`, `--wizard`, default). The DEBRIEF flag spawns a second instance of the SAME binary — OS sees 2 PIDs but same exe; this is the v2.0 pattern.
- **FastAPI proxy** — Bravoh-team operated, out of repo. No changes from v2.1 client side beyond using existing rate-limit + healthz endpoints.

### Shared State Discipline

Existing stores (do not create siblings):

| Store | Owner | Extension in v2.1 |
|-------|-------|-------------------|
| `MusicState` (`state/music_state.py`) | `state_refresh_loop` (sole writer) + `coach_loop` (one exception) | Add `emotion` field (Feature 4) |
| `EvidenceRegistry` (`state/evidence_registry.py`) | `state_refresh_loop` + `EventDetector._fire` | Feature 2 wires `register_library`; Feature 5's 2 detectors write `ev:DISTORTION_CLIMB` + `ev:ACID_LINE_ENTRY` |
| `ControllerState` (`midi/state.py`) | MIDI daemon thread | No change |
| `runtime/config_store.py` (settings on disk) | Tauri+sidecar shared | Feature 6 adds `profile_disclosed`; Feature 7 adds `first_run_completed_at` |

NEW on-disk state (no in-memory siblings):

- Feature 2: `~/Library/Application Support/vibemix/library/{collection.pkl, embeddings.db}` (cache only — rebuildable).
- Feature 6: `~/Library/Application Support/vibemix/profile/<install_uuid>.json`.

### IPC Schema Discipline

All v2.1 IPC fits on existing ports:

| Port | Owner | v2.0 schemas | v2.1 ADDITIONS |
|------|-------|--------------|----------------|
| 8765 | live ws_bus (`runtime/ws_bus.py`) | mascot snapshot, manual trigger, citation, overlay-highlight, wizard.* | library.import, library.search, library.status, library.stale-nudge, session.profile-disclosure, wizard.recovery |
| 8766 | DEBRIEF (`__main__._run_debrief_sidecar`) | DEBRIEF-01 chapter, DEBRIEF-02 TLDR, MASCOT broadcast (all RESERVED v2.0) | debrief.drill (NEW within reserved namespace) |

Zero new buses. All schemas land in `src/vibemix/ui_bus/schemas/*.json` extending the existing validator.

### Cross-Platform (Mac + Win) Parity

| Feature | Mac path | Win path | Divergence |
|---------|----------|----------|-----------|
| 1 — Eval harness | Pure Python | Pure Python | None |
| 2 — Library | sqlite-vec primary | sqlite-vec primary, numpy fallback | None functional; wheel availability check at install |
| 3 — Debrief | Tauri webview + WaveSurfer | Same | None |
| 4 — 4-layer mascot | Three.js webview | Same | None |
| 5 — Hard Tek detectors | Pure numpy | Same | None |
| 6 — DJ profile | JSON + app_data_dir | Same | None |
| 7 — Install hardening | TCC pre-grant + Tart VM rehearsal | No TCC; Windows Sandbox rehearsal | Wizard step1 branches on `target_os` |
| 8 — Security | gitleaks + pip-audit + cargo audit + npm audit | Same | None |
| 9 — GLB pipeline + demo film | Mac-only build host | Bundled MP4/GLB consumed equally | Build-time host divergence only |
| 10 — Day-Zero ops | Mac-host scripts | Mac-host scripts | None (ops box is Kaan's Mac) |
| 11 — Integration audit | CI both runners | CI both runners | None |
| 12 — Signing | Apple notarytool | SignPath | Per-OS sign job (already designed in Phase 21) |
| 13 — RC + ship | Mac-host scripts | Mac-host scripts | None |

Divergence is contained to Features 7 + 12 — both already use `#[cfg(target_os)]` branches in Rust and per-OS YAML jobs in CI. Pattern is shipped; v2.1 just adds new branches.

---

## Proposed Phase Decomposition

Continuing from Phase 26 (last shipped) → Phase 27 onward. **13 features → 13 phases**, but some run in parallel.

```
Phase 27 — Eval Harness + Audit Tail-Closes
  Closes:
   • Feature 1 — replay_harness + judge + F1 + eval.yml CI
   • v2.0 audit WARNING: register_library wiring in __main__ (5-min patch)
  Status: parallel with 28, 30, 34
  Critical path: NO

Phase 28 — Library Intelligence v1
  Closes:
   • Feature 2 — Gemini Embedding 2 + sqlite-vec/numpy + drag-drop UI + staleness
  Depends: Phase 25 (shipped) + Phase 27 register_library patch
  Status: parallel with 27, 29, 30, 34
  Critical path: YES (Feature 6 needs this)

Phase 29 — Post-Session Debrief MVP
  Closes:
   • Feature 3 — debrief sidecar real impl + WebSurfer panel + 3 drills
  Depends: Phase 15 (browser), Phase 25 (slot)
  Status: parallel with 27, 28, 30, 34
  Critical path: NO

Phase 30 — Hard Tek Detectors Completion
  Closes:
   • Feature 5 — DISTORTION_CLIMB + ACID_LINE_ENTRY + tune_detectors extension
  Depends: Phase 17 (shipped)
  Status: parallel with 27, 28, 29, 34
  Critical path: YES (Feature 4 dispatches on these event types; Feature 6 reads them in profile)

Phase 31 — 4-Layer Mascot Additive State Machine
  Closes:
   • Feature 4 — base+emotion+anticipation+reaction priority stack
  Depends: Phase 22 (shipped) + Phase 30 (new event types for reaction layer)
  Status: sequential after 30
  Critical path: YES (Feature 9 needs the full animation palette to generate GLBs)

Phase 32 — Long-Term DJ Profile
  Closes:
   • Feature 6 — Profile builder + injection + disclosure UI
  Depends: Phase 28 (library) + Phase 30 (Hard Tek events)
  Status: sequential after 28+30
  Critical path: NO

Phase 33 — One-Click Install Hardening
  Closes:
   • Feature 7 — TCC pre-grant + recovery + step4 onboarding + VM rehearsal
  Depends: Phase 11 (wizard shipped) + Phase 38 (signed binaries for rehearsal)
  Status: sequential after 38 (signing)
  Critical path: YES (release gate)

Phase 34 — Open-Source Security Pass
  Closes:
   • Feature 8 — secret-scanner + cve-audit + binary-verify + permission-lint + SECURITY.md + threat-model
  Depends: Phase 21 (release.yml shipped)
  Status: parallel with 27, 28, 29, 30 — land EARLY so subsequent phases ship clean
  Critical path: NO (but recommended early)

Phase 35 — Real GLB Animations + 30s Viral Demo Film
  Closes:
   • Feature 9 — text-to-3D pipeline + Mixamo rig + animation palette + demo film
  Depends: Phase 31 (full 4-layer palette known)
  Status: sequential after 31
  Critical path: NO (viral demo nice-to-have; product ships without)

Phase 36 — Day-Zero Ops Automation
  Closes:
   • Feature 10 — Discord provision + release publish + load test + healthz exporter + launch trigger
  Depends: Phase 21 + Phase 26 (shipped)
  Status: parallel with 35
  Critical path: YES (launch gate)

Phase 37 — Cross-Phase Integration Audit
  Closes:
   • Feature 11 — e2e harness + integration_audit.py + integration-checker subagent updates
  Depends: EVERY OTHER feature
  Status: sequential — penultimate
  Critical path: YES

Phase 38 — Signing Pipeline Real Execution
  Closes:
   • Feature 12 — real notarytool + SignPath + verifier job
  Depends: Phase 21 (scaffold) + external (Apple agreement + SignPath OSS approval)
  Status: sequential — must precede Phase 33 (install rehearsal) and Phase 39 (RC)
  Critical path: YES (highest priority external dependency)

Phase 39 — RC Cut + Ship
  Closes:
   • Feature 13 — launch scripts + finalize README + cut tag + publish
  Depends: EVERY OTHER feature
  Status: sequential — final
  Critical path: YES (the milestone gate)
```

### Total: 13 phases (27 → 39)

### Parallel-vs-Sequential Summary

```
                    ┌──── 27 ──┐                      ┌── 35 ──┐
                    ├──── 28 ──┤── 32 ──┐             │        │
v2.0 baseline ──────┼──── 29 ──┤        │             │        │
                    ├──── 30 ──┤── 31 ──┘── 33 ──┐    │        │
                    └──── 34 ──┘                 │    │        │
                                                 │── 38 ── 36 ──┴── 37 ──── 39
                                                 │
External (Apple/SignPath) ───────────────────────┘
```

Hot path (longest): **v2.0 → 30 → 31 → 35 → 37 → 39** = 5 phases sequential. With Phase 38 sequencing under the external dependency, the real hot path is **external-approval → 38 → 33 → 37 → 39** = 4 sequential phases.

---

## Build-Order Dependency Graph (Topological Sort)

```
v2.0 ship (all phases 15-26)
  │
  ├─→ Phase 27 (Eval) ─────────────────────────────────┐
  ├─→ Phase 28 (Library) ──────┐                       │
  ├─→ Phase 29 (Debrief) ──────┤                       │
  ├─→ Phase 30 (Hard Tek) ─────┤                       │
  └─→ Phase 34 (Security) ─────┤                       │
                               │                       │
                  ┌────────────┘                       │
                  ▼                                    │
  Phase 31 (4-layer mascot) [needs 22 + 30]            │
                  │                                    │
                  ▼                                    │
  Phase 32 (DJ profile) [needs 28 + 30]                │
                  │                                    │
                  ▼                                    │
  Phase 35 (GLB + demo) [needs 31]                     │
                                                       │
External Apple/SignPath approval                       │
                  │                                    │
                  ▼                                    │
  Phase 38 (real signing) [needs external]             │
                  │                                    │
                  ▼                                    │
  Phase 33 (install hardening + VM rehearsal)          │
  [needs 11 + 38]                                      │
                  │                                    │
                  ▼                                    │
  Phase 36 (Day-Zero ops) [needs 21+26]                │
                  │                                    │
                  ▼                                    │
  Phase 37 (integration audit) [needs ALL] ────────────┘
                  │
                  ▼
  Phase 39 (RC + ship) [needs ALL]
```

---

## Open Architecture Questions for Phase Planners

1. **Feature 2 — sqlite-vec wheel availability on Windows ARM** — At time of writing (May 2026), sqlite-vec ships `osx-arm64`, `osx-x86_64`, `win-amd64`, `linux-x86_64`. Windows ARM is not a current target per v2.0 constraints (Mac + Win = `win-amd64`). PHASE 28 PLANNER: verify sqlite-vec wheel still ships for `win-amd64` Python 3.12; if not, numpy fallback is the path. Test in CI matrix.

2. **Feature 3 — debrief sidecar lifecycle** — When the user closes the debrief panel WebviewWindow, who kills the `--debrief` subprocess? Two options: (a) Rust `mascot_window.rs`-pattern with WindowEvent listener kills child on `CloseRequested`; (b) sidecar self-terminates after N seconds idle. PHASE 29 PLANNER: pick (a) — same pattern as v2.0 mascot. Add to `sidecar.rs:SidecarHandle` a second `Arc<Mutex<Option<CommandChild>>>` slot for debrief.

3. **Feature 4 — base-layer pose vocabulary** — v2.0 ships 5 `prep_*` GLBs. Feature 4 needs base poses (idle/breathing/talk/dance) — does Mixamo have free clips for the bat rig? PHASE 31 PLANNER: validate during Feature 9 pipeline design; if Mixamo doesn't have a bat-compatible rig, fall back to procedural Three.js Bone manipulation for base layer (cheap; existing tooling).

4. **Feature 6 — profile size enforcement** — "~2KB JSON" is the stated budget. Token count ≠ byte count. PHASE 32 PLANNER: pick the enforcement metric. Recommend: serialize to JSON, count UTF-8 bytes, hard cap at 2048 bytes; truncate least-recent items if exceeded. Token-count (~600 tokens for 2KB JSON) is the prompt-budget side-effect.

5. **Feature 7 — Tart VM cost** — Each rehearsal run consumes a Mac VM image. GitHub Actions macOS runners are ~10x cost of Linux. PHASE 33 PLANNER: gate the rehearsal workflow on `workflow_dispatch` + nightly cron, not every PR. Use Linux-host with Tart-replaced-by-osx-cross emulator for PR-level smoke; full rehearsal nightly.

6. **Feature 8 — capability-baseline lint false positives** — `tauri/src-tauri/capabilities/default.json` legitimately changes during normal development (e.g. Feature 3 adds debrief permissions). PHASE 34 PLANNER: make the baseline a Git-tracked file `tests/security/capability-baseline.json` updated by PR author; lint fails only when baseline diverges from runtime config AND PR doesn't update baseline. Standard "snapshot test" pattern.

7. **Feature 9 — Meshy / Hunyuan3D API authentication** — text-to-3D services rate-limit by account. PHASE 35 PLANNER: pipeline must be idempotent + checkpoint-resumable. Generated GLBs cached locally with content-hash; re-runs skip if cache hit.

8. **Feature 11 — e2e test runtime cost** — Each e2e test spawns a sidecar subprocess (~3s startup). Suite of 5 e2e tests = ~15s minimum + work. PHASE 37 PLANNER: keep e2e suite separate from unit (`pytest tests/e2e -m e2e`) and gate on PR-merge, not PR-open. Nightly canary.

9. **Feature 12 — SignPath signing latency** — SignPath OSS plan signs asynchronously; sign-job may wait 30 min - 2h. PHASE 38 PLANNER: release.yml needs `timeout-minutes: 180` on the Windows sign job + a polling retry loop with backoff.

10. **Feature 13 — social-post-publish gate** — Should `launch_trigger.sh` post automatically or require interactive approval? PHASE 39 PLANNER: per memory `feedback_autonomous_no_grey_area_pause` — Kaan's `gsd-autonomous fully` mode wants automated discharge. Recommend `--auto` flag default-on with `--dry-run` opt-out; approval gate moves to Discord webhook DM preview (auto-post 5 min later if no NACK).

---

## Sources

- `.planning/PROJECT.md` — v2.1 milestone definition (13 features).
- `.planning/milestones/v2.0-MILESTONE-AUDIT.md` — integration matrix + register_library WARNING + tech debt by phase.
- `.planning/milestones/v2.0-ROADMAP.md` — Phase 15–26 enumeration with explicit "v2.1 will add X" markers (Phase 17 hard_tek chain, Phase 22 4-layer, Phase 25 debrief slot).
- `.planning/codebase/ARCHITECTURE.md` — v2.0 layer model + naming conventions.
- `.planning/codebase/STRUCTURE.md` — file location reference for seams.
- `src/vibemix/__main__.py:653-717` — verified DJCoHostAgent kwarg path + coach_loop kwarg path live.
- `src/vibemix/state/evidence_registry.py:166-209` — register_library method shape (dormant in v2.0).
- `src/vibemix/agent/dj_cohost.py:148-218` — 4-kwarg gate.
- `src/vibemix/runtime/coach.py:1-50` — Plan 19-05 + 20-04 docstring summarizing the wired path.
- `src/vibemix/runtime/ws_bus.py:80-105` — 30Hz payload shape (mascot extension surface).
- `src/vibemix/events/genres/hard_tek.py` — explicit "v2.1 will add DISTORTION_CLIMB + ACID_LINE_ENTRY" marker.
- `tauri/ui/src/mascot/additive-layer.ts:11-14` — explicit "v2.0 ships the 3-layer subset … 4-layer model is deferred to v2.1" marker.
- `tauri/src-tauri/src/sidecar.rs` + `permissions.rs` — Rust shell pattern reference for Feature 7 + Feature 3.
- `.github/workflows/release.yml` — mock-signing fallback + 5-stage per-OS matrix shipped Phase 21.

CLAUDE.md user memory referenced:
- `project_visual_direction_cdj_whisper` — Pioneer-grade hardware aesthetic baseline.
- `project_mascot_as_vtuber_personality_surface` — Meshy/Hunyuan3D + Mixamo + Three.js pipeline.
- `feedback_no_clap_use_gemini_embedding` — Gemini Embedding 2 mandate.
- `project_gemini_embedding_2` — multimodal embedding model is the choice for Feature 2.
- `project_one_click_install_hard_req` — Mac+Win hard requirement for Feature 7.
- `feedback_autonomous_no_grey_area_pause` — autonomous discharge default for Feature 13.

---

*Architecture research for: v2.1 The Unified Cut — integration map for 13 features into existing 3-process architecture without spawning new processes.*
*Researched: 2026-05-14*
