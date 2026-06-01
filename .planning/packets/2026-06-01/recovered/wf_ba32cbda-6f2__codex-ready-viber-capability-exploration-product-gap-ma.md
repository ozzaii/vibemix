# CODEX_READY: Viber Capability Exploration & Product-Gap Map

> **Date:** 2026-05-31 (Europe/Istanbul) · **Repo:** /Users/ozai/projects/dj-set-ai · **Branch:** live-tuning-or-brain · **Author:** Claude read-only synthesis coordinator · **Status:** READ-ONLY AUDIT / NO CODE MODIFIED

---

## 0. Evidence rules & how to read this

- **Every row carries source evidence:** a `file:line`, a test name, an IPC type + handler, or an explicit `NOT FOUND: <searched>`.
- **Status enum (exactly one per capability):** `WIRED_LIVE` (end-to-end in the running product app/live session) · `WIRED_CLI_ONLY` (works via `uv run python -m vibemix library …` or the Codex MCP agent, but no Tauri app surface) · `PRESENT_ORPHANED` (impl exists, no caller — dead) · `PARTIAL` (some legs wired, some missing) · `CLAIMED_BUT_ABSENT` (docs/memory claim it, source lacks it) · `MISSING_REQUIRED` (needed for Viber to feel real, absent) · `DROP` (present, should be abandoned).
- **Where the adversarial verify downgraded a claim, this packet uses the VERIFIED status, not the optimistic one,** and notes the refute.
- **The single biggest cross-lane divergence:** the *tool-surface* and *set-generation* lanes called the Viber MCP tools `WIRED_LIVE`; the *cue-flow* and *external-goldmine* adversarial verifiers downgraded most of them to `WIRED_CLI_ONLY` under audit-rule #4 (the Codex MCP agent is reached only via the `library …` CLI subcommands + a logged-in Codex CLI — there is **no Tauri GUI button or `ipc.*` message type that fires any Viber tool**, confirmed by the *ui-surface* lane). **This packet adopts the stricter `WIRED_CLI_ONLY` for the Viber/Codex agent surface** and reserves `WIRED_LIVE` for paths with a real `ipc.*` or ws-bus producer↔consumer in the running app (the pill next-suggestion, the staleness nudge, the CLAP centroid cache, the cohost speech guards).
- **Audit-rule #5 (no fake fallback):** flagged wherever Viber/Sven could speak from stale/uncertain context.
- **`UNVERIFIED`** is appended to any leg not source-proven this session.

---

## 1. Capability matrix

> Lane key: TS=tool-surface · SG=set-generation · LF=library-freshness · CF=cue-flow · VB=viber-sven-boundary · UI=ui-surface · OB=observability-eval · GM=external-goldmine.

| Capability | Lane | Status | Wired E2E | Evidence (file:line / test / IPC+handler / NOT FOUND) | Notes |
|---|---|---|---|---|---|
| `search_vibe` (vibe search) | TS | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:148-178 (seen-set add :165-166, k clamp 1..50 :157); @mcp.tool mcp_server.py:154-159; dispatch toolset.py:1461; spawn codex_curate.py:754; app shells via library_cmds.rs:671 | Core grounded discovery. App "door" is a CLI subprocess, not an `ipc.*` type — agent-surface, downgraded from the TS lane's WIRED_LIVE. |
| `discover_pool` | TS/SG | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:570-638 (seen add :624-625, k clamp 1..200 :604); @mcp.tool mcp_server.py:305-330; dispatch :1469; build-set prompt step 1 codex_curate.py:996-998 | MMR-diverse pool over the DJ's own library. |
| `sequence_set` (energy-curve beam search) | SG | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:640-726 (seen-gate :655-663, deterministic vec/bpm/camelot/energy :669-702, unknown-curve KeyError :711-712); sequencer.py CURVE_PRESETS :63-72, BPM relax ladder :84-86; @mcp.tool mcp_server.py:332-340 | Model supplies only curve/order (Invariant #3). GM-verify downgraded WIRED_LIVE→WIRED_CLI_ONLY: only CLI caller proven. |
| `create_playlist` (the single validated write) | TS | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:454-487 (Gate#1 seen :464-472, Gate#2 library re-validate :474, sets self.created :478); @mcp.tool mcp_server.py:258-264; wrapper persist codex_curate.py:960-966 | TWO grounding gates. |
| `export_set` (→ Rekordbox XML) | TS/SG | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:728-800 (gate#1 seen :741-748, gate#2 per-id lookup :755-757, export_rekordbox.export_set :784-786, default `~/.cache/vibemix/sets/<slug>.xml` :783); @mcp.tool mcp_server.py:342-347 | Two-gate grounding. |
| `smart_hot_cues` (review-first A–H) | TS/CF | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:368-417 (seen-gate :384-391, propose_smart_cues :397, issued_cue_proposals :411); smart_cues.py SOURCE_RANK :38, `preserve_human_hot_cue` :300; @mcp.tool mcp_server.py:226-237 | Where human hot-cue slot/source preservation ships (Viber path only). |
| `export_smart_cues` (agent-safe cue write) | TS/CF | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:802-919 (rejects raw cues/track_path :809-815, proposal must be issued :819-826, re-checks proposal.track_id in seen :830-836, selected_cue_ids ⊂ proposal :848-856); @mcp.tool mcp_server.py:239-256 | Anti-slop hardened. Preserves A–H slots. |
| `transition_slate` | TS/CF | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:232-324 (candidate seen-gate :245-252, transition_scorer :274-314, live LivePosition :266-273, move_grade :1629-1634); @mcp.tool mcp_server.py:175-205 | Deterministic section-to-section candidates. `mode='live'` proves the engine can run live. |
| `compile_musical_context` | TS | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:326-366 (rejects candidate_ids not issued :333-344, compile_transition_context :353); @mcp.tool mcp_server.py:207-224 | Accepts `intent='live_next_pill'` (:348) — see §13 dead-leg note. |
| `get_track_features` | TS | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:180-201 (Camelot via harmonics.to_camelot :188, never LLM-computed, honest-null); @mcp.tool mcp_server.py:161-166 | Deterministic facts only (Invariant #3). |
| `get_track_sections` | TS/CF | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:203-230 (seen-gate :214-220, sections_for_entry :224); @mcp.tool mcp_server.py:168-173 | Rekordbox cues + conservative fallback. |
| `get_track_energy` | TS | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:537-568 (score_energy_cached :556, honest-null :553-563); @mcp.tool mcp_server.py:298-303 | Energy COMPUTED from audio, never model-supplied (Invariant #3). |
| `request_clarification` (Factor-7) | TS | WIRED_CLI_ONLY | CLI/agent | impl toolset.py:1126-1245 (validates question :1193-1200, choices 2–5 :1204-1229, terminal stop_reason :1236); @mcp.tool mcp_server.py:266-294; propagated curate :881-891 / build_set :1259-1269; app marker library_cmds.rs:359 | Terminal single-turn; no track_id surface (Invariant #2). No UI field to render a clarification (see §6). |
| `quote_moment` | TS/CF | PARTIAL | no | impl toolset.py:923-953 (resolve_quote, seen-gated :945-952); @mcp.tool mcp_server.py:366-385; dispatch :1475. **Named in NO prompt block** (codex_curate.py:226-238/992-1024/1455-1495) | TS-verify downgraded WIRED_LIVE→PARTIAL: registered but never prompt-surfaced ⇒ dormant; model never told it exists. |
| `export_cues` (single-track AI cue write) | TS/CF | PARTIAL | no | impl toolset.py:982-1027 (cue_export.export_cues :1017); @mcp.tool mcp_server.py:401-423; dispatch :1478. **NO seen-set gate** — validates only non-empty track_path + non-empty cues :987-1007 (contrast export_smart_cues :809-815) AND named in no prompt block | TS-verify downgraded WIRED_LIVE→PARTIAL. **Grounding breach — Invariant #2 hole, see §8 #1.** |
| `web_search` | TS | PARTIAL | no | impl toolset.py:491-515 (seen_urls add :508-514); @mcp.tool mcp_server.py:351-357; surfaced ONLY in chat rule#4 codex_curate.py:1469-1471. Needs `TAVILY_API_KEY` (honest error :493-495) | Dormant unless key set AND model (in chat) picks it. |
| `fetch_url` | TS | PARTIAL | no | impl toolset.py:517-533 (rejects url not in seen_urls :526-532); @mcp.tool mcp_server.py:359-364. Named in no prompt block | Depends on web_search succeeding; not itself prompt-surfaced. |
| `retrieve_dj_knowledge` (RAG) | TS | PARTIAL | no | impl toolset.py:955-980 (lazy-loads KB :970-971, honest-empty :957-958); @mcp.tool mcp_server.py:387-399; surfaced ONLY chat rule#4 :1469-1471 | Needs populated KB corpus on disk (MEMORY.md flags this prereq). |
| live-context grounded packet → Viber (chat) | TS/VB | WIRED_CLI_ONLY | CLI/agent | NOT an @mcp.tool — prompt-injection + guard. App: library_cmds.rs:747-770 `library_chat(live_context)` → `--live-context` :166; `__main__`.py:2793-2805/4045-4060 → chat_with_codex(live_context=…) :4093/4099; guard codex_curate.py:62-64 → apply_live_claim_guard deck_context.py:2240 | Anti-fake-fallback: missing context ⇒ held reply + `live_context_required`. **Body lines codex_curate.py:3290-3800 NOT line-confirmed (harness dropped page) — UNVERIFIED guard call-sites; rests on imports + Rust plumbing.** Only via `library_chat`, not curate/build-set. |
| Full build-set path: UI brief → sequenced set + why **visible in app** | SG | WIRED_LIVE | yes | UI invoke api.ts:2396 `library_build_set` → Rust #[tauri::command] library_cmds.rs:706 (registered main.rs:108) → shells `library build-set … --backend codex --json` :719-734 → `__main__`.py:5766→5698 → build_set_with_codex codex_curate.py:1072; renderer index.ts:498/1729-1735; contract test test_library_window_contract.py:21 | **This is the ONE Viber set-prep path with a real Tauri IPC command + in-app render.** SG-verify upheld the IPC spine + registration as WIRED_LIVE; index.ts render leg asserted-but-unread in one verify pass. |
| App auto-sets `VIBEMIX_CODEX_ALLOW_SHELL=1` for codex backend | SG | PARTIAL | yes (conditional) | build_library_command library_cmds.rs:126-128 sets env iff `library_args_request_codex_backend` :133-137; build_set passes `backend = library_agent_backend()` :718/730 = const `LIBRARY_AGENT_BACKEND` :144-146 | SG-verify downgrade: predicate fires only if the const == exactly `"codex"`; **const value NOT read this session — if it differs, the flag silently never sets and build-set hits `codex_mcp_blocked` in the app.** Re-verify the const. |
| Live tool-tape → in-app progress (`library://viber-tool`) | SG/UI | PARTIAL | partial | Rust emit CONFIRMED: parse_viber_tool_line library_cmds.rs:263 + app.emit(`library://viber-tool`) :277-279; producer codex_curate.py:649 `_start_tool_tape`; UI listener index.ts:2065 onViberTool (**NOT re-read in verify**) | SG-verify downgrade: Rust emit proven, UI listener + Python producer unverified end-to-end. Ride this channel for proof chips (§9). |
| Pill "what's next" suggestion **engine** (next_suggestion ranking) | CF/SG | WIRED_LIVE | yes | runtime/suggestion.py:42-52 imports next_suggestion; SuggestionService.compute :925/957-977; **instantiated `__main__`.py:1613-1621 "→ pill next-suggestion: armed"**; grounded store∩library (suggestion.py:25-29 → None) | **This is a deterministic CLAP path, NOT Viber/Codex** (confirmed: no codex/toolset/chat_with import in suggestion.py). The PRIMARY live next-track surface. |
| Pill SuggestionService → ws bus → floating pill (`next_suggestion` frame field) | CF | WIRED_LIVE | yes | ws_bus.py:1082 `mascot_frame['next_suggestion'] = suggestion_holder.current_for_state(state)` (else .current() :1084) on the live 30Hz frame; consumer pill/next-suggestion.ts:178 NextSuggestionWire mirrors `.to_dict()`; honest-null renders nothing | **No `ipc.pill.suggestion` schema type exists** (`NOT FOUND` in messages.schema.json) — pill rides as a frame FIELD, both ends matched. Producer line ws_bus.py:1082 single-stepped in CF-verify. |
| Pill feedback back-channel (`next_suggestion.choose` / `.feedback`) | CF/UI | WIRED_LIVE | yes | ws_bus.py:850-882 handles `next_suggestion.choose` → "next_suggestion_choose" / `next_suggestion.feedback` → "next_suggestion_feedback"; SuggestionService feedback_sink suggestion.py:242/651, update_taste_scores :413 | Live-pill taste loop is CLOSED (contrast Viber's open loop, §10). |
| 30-day boot staleness NUDGE (sidecar → banner → snooze) | LF | WIRED_LIVE | yes | producer staleness.py:122-146 (STALE_AGE_SECONDS=30d :26); boot `__main__`.py:1561-1573 + flush :1979-1990; action handler :1963-1975; IPC both ends messages.py:1776/1796 + schema 2487/2530 + messages.ts:624/633; consumer staleness-banner.ts:60-82 mounted SettingsDrawer.ts:1204-1207; tests test_staleness.py + staleness-banner.spec.ts | **COARSE + BOOT-ONLY** (library.pkl mtime once at boot; never re-checks collection.xml mid-session). See §3. |
| Rekordbox two-factor staleness re-parse | LF | PARTIAL | passive | rekordbox.py:96-103 (pickle exists AND recorded xml_mtime == live collection.xml mtime, else treat as miss); test test_rekordbox.py:106 | Real detection but PASSIVE — fires only when try_load_cache is called (fresh ingest); does not itself trigger re-embed. |
| Rekordbox `collection.xml` ingest | LF | WIRED_CLI_ONLY | CLI | ingest.py:1-36/756 (detect→iter→CLAP embed→store, cue-anchored, resumable); CLI dispatch `__main__`.py:331; writes library.pkl | The ONLY path that rebuilds the embedding index. |
| embed-folder walk | LF | WIRED_CLI_ONLY | CLI | folder_ingest.py:9-10/284-313 (folder mtime as xml_mtime :289-291) | Resumable; no auto re-walk. |
| Cue-anchored excerpts | LF | WIRED_CLI_ONLY | CLI | ingest.py:55-56 (anchors_for_track/cut_windows), docstring :15-19; degrades honestly :19/26-27 | Runs inside manual ingest. |
| Content-hash resume cache | LF | WIRED_CLI_ONLY | CLI | ingest.py:182-194/205-215/840-891 (`clap_embed_cache`, sha256 file-bytes key); cache_paths.py:16 `clap_embeddings.db`; folder_ingest.py:381-434 | Makes manual re-ingest cheap. |
| sqlite-vec / numpy index + library.pkl | LF | WIRED_CLI_ONLY | CLI write / live read | index_sqlite_vec.py, index_numpy.py, store.py; `__main__`.py:1543-1553 boot load + evidence_registry; pill warm :1588-1615 | Written by manual ingest, read live at boot. |
| CLAP query centroid cache (auto-recompute on store change) | LF | WIRED_LIVE | yes | centering.py:95-148 (snapshot_hash keyed, self-invalidates, recompute on stale/corrupt); consumed live store.py:79-85 `search_centered`; callers similar.py:100, search.py:134; test test_centering.py:96 | Query-side anisotropy fix; correctly NOT a source-freshness risk. (Verify corrected "search_topk"→`search_centered`.) |
| Live file/library WATCHER (auto re-ingest) | LF | MISSING_REQUIRED | no | **NOT FOUND:** `rg 'import watchfiles\|from watchfiles\|watchdog\|Observer\|inotify\|FSEvents\|on_modified\|on_created' src/vibemix` → zero. watchfiles only transitive under uvicorn (uv.lock:813), unimported. `runtime/parent_watchdog.py` = process ppid watchdog, not FS. midi/watcher.py = MIDI hot-plug | **P0.** Index never auto-refreshes; new/re-exported tracks invisible until manual CLI re-run. See §3. |
| Auto-cue engine (CUE-DETR ONNX → downbeat-refine → CueAnchor, fallback) | CF | WIRED_CLI_ONLY | CLI | cue_engine.py:156/170/176-178 (fallback to cue_detect.detect_cues); live caller cue_folder.py:111-114 reached by `__main__`.py:5986; codegraph: detect_cues_auto callers = cue_folder + tests only | CF-verify downgraded WIRED_LIVE→WIRED_CLI_ONLY: no live-session/IPC caller. |
| `library cue <folder>` CLI (→ Rekordbox/M3U8/Serato) | CF | WIRED_CLI_ONLY | CLI | parser `__main__`.py:2654 sp_cue; handler :5952 → tag_folder_serato :5971 / export_cued_folder :5986; E2E test test_cue_folder_cli.py:35-128 | Test-proven CLI. No app surface. |
| `export-set` CLI (order+cues+beatgrid → Rekordbox XML) | CF | WIRED_CLI_ONLY | CLI | parser `__main__`.py:2900; handler :5854 → export_rekordbox.export_set; hot-cue COLOR not written (pyrekordbox 0.4.4 gap, honest :37-38) | |
| Serato Markers2 universal cue carrier (cues → audio tags) | CF | WIRED_CLI_ONLY | CLI | export_serato.py:76 encode/:96 decode/:224 write (opt-in :239, merge :251, .mp3/.aif/.aiff :179); live via cue_folder.py:255-270 → `library cue --write-tags`; round-trip tests test_export_serato.py:55/84/150/163 | mutagen GPL-2.0+ runtime-import (sanctioned). Cross-app pad render = manual eye-check, NOT machine-proven (export_serato.py:25-27). |
| Single-track AI cue export (cue_export.export_cues) | CF | WIRED_CLI_ONLY | agent/CLI | cue_export.py:95; live via toolset.py:982→:1017 (Viber); round-trip test test_cue_export.py:206 (real pyrekordbox reload, 3 cues survive) | |
| Cue round-trip PROVEN by test (file-format layer) | CF | PARTIAL | n/a | test_export_serato.py:55/84/150/163, test_cue_export.py:206, test_cue_folder.py:113/139/241 | CF-verify downgraded WIRED_LIVE→PARTIAL: bytes/XML conformance machine-proven; cross-app VISUAL render = manual KAAN-ACTION gate; test lines not re-read in verify. |
| Export receipts (counts + paths + skip/drop) | CF | WIRED_CLI_ONLY | CLI | cue_folder.py:64 CueExportReport; printed `__main__`.py:6013-6025 + --json :6009-6011 | CF-verify downgraded WIRED_LIVE→WIRED_CLI_ONLY: receipts only on CLI/agent path. |
| DJ/human cues from Rekordbox ANLZ ingest | CF | PARTIAL | unverified | smart_cues.py:19/38/324/487 consume anlz/dj cues; tests test_anlz_ingest.py/test_smart_cues_anlz.py exist; **parser body anlz_ingest.py/rekordbox.py NOT read** | Consumer solid; parser-internal emit of CuePoint.source unverified. |
| Cue export Tauri app / IPC surface (GUI button) | CF/UI | MISSING_REQUIRED | no | **NOT FOUND:** no cue/export type in messages.schema.json (only learn-highlight cue_color/cue_shape :2842-2843, citation regex :2919, window-hint enum :723, library-import comment :2356); no Rust cue command (library_cmds.rs "cue" = model-install target + cue_anchored strategy) | The cue/hot-cue "moat" has NO GUI button. See §4, §8 #4. |
| Crate tab mounted in desktop shell | UI | PARTIAL | UI-only | desktop-shell.ts:12/44/88 mountCrate; library/index.ts:21; chat.ts:38 renderViberChat | Renders fine; whole pane non-functional because no Python handler answers any `ipc.library.*` (next row). |
| `LibraryBridge` (the ONLY register/emit for all `ipc.library.*`) | UI | PRESENT_ORPHANED | no | library_bridge.py:22/29 (registers 6 handlers); **repo-wide grep `LibraryBridge` = 1 hit (def only); codegraph_callers = []**; session_loop.py:44-57 builds only WizardSatellite | **P0 root cause: the entire library/Viber IPC backend has no live handler.** |
| `LibraryBridge` imports (would crash if wired) | UI | CLAIMED_BUT_ABSENT | no | calls nonexistent fns: chat_turn/curate_playlist (codex_curate has curate/run_codex_curate), search_text/search_similar (search.py has search/search_by_text), ingest_library (ingest.py has ingest), library_stats from `vibemix.library.stats` (**`ls` → No such file**) — library_bridge.py:47/72/89/108/133/150 | Bridge written against a stale/imagined backend API. |
| `ipc.library.chat.request → .reply` (Viber conversational chat in app) | UI | PARTIAL | no | TS sender api.ts:134; handler library_bridge.py:34/116 (orphaned + imports nonexistent chat_turn). 15s timeout → chat.ts:76-80 "couldn't reach my crate" | TS end wired; Python end orphaned+broken. Live = type, wait 15s, error bubble. |
| `ipc.library.chat.tool` (live tool-tape / proof chips in app) | UI | PRESENT_ORPHANED | no | TS subscriber api.ts:124 + viber-tape.ts; **emitter NOT FOUND** (`rg 'chat.tool' src/vibemix` = 0; _on_chat_tool is `pass` :164, unregistered) | The proof-chip surface is DEAD: TS subscribes, Python never emits. |
| `reply.toolCalls` rendered in chat UI | UI | PRESENT_ORPHANED | no | schema messages.schema.json:971-976; api.ts:113/144 surfaces; **chat.ts has 0 refs to reply.toolCalls** — only appends reply.text :75; tape cleared in finally :83 | Persisted grounding proof silently dropped by UI. |
| `ipc.library.curate.request → .result` | UI | PARTIAL | no | TS api.ts:178; handler library_bridge.py:35/139 (orphaned, imports nonexistent curate_playlist) | TS wired; Python orphaned+broken. |
| `ipc.library.search.request → .result` | UI | PARTIAL | no | TS api.ts:77; handler library_bridge.py:32/76 (orphaned, calls nonexistent _search_mod.search_text) | TS wired; Python orphaned+broken (wrong fn name). |
| `ipc.library.similar.request → .result` | UI | PARTIAL | no | TS api.ts:93 findSimilar; handler library_bridge.py:33/93 (orphaned, calls nonexistent search_similar) | Python end orphaned+broken; UI button caller for findSimilar unconfirmed. |
| `ipc.library.ingest.request → .progress` | UI | PARTIAL | no | TS api.ts:52/42; handler library_bridge.py:31/54 (orphaned, imports nonexistent ingest_library); emits single terminal done:True | Even if wired, progress jumps 0→100, no incremental stream. |
| `ipc.library.stats.request → .result` | UI | PARTIAL | no | TS api.ts:201; handler library_bridge.py:36/156 (orphaned, imports library_stats from nonexistent stats module) | Stats header renders loading/empty forever. |
| Curate playlist export/download/open affordance (m3uPath/Rekordbox/Serato) | UI | MISSING_REQUIRED | no | m3uPath only typed (api.ts:171/186); **NOT FOUND:** `rg 'm3uPath\|download\|export\|rekordbox\|serato\|.href\|saveAs\|blob' library/*.ts` = 2 api.ts lines only | All CLI export power has zero UI surface. |
| Freshness/staleness indicator on Viber RESULTS | UI | MISSING_REQUIRED | no | **NOT FOUND:** `rg 'fresh\|stale\|as of\|updated\|timestamp\|ago\|cached\|Date.now' library/*.ts` = 0; no time field in any result schema (messages.schema.json:965-1040) | **Rule-5 risk:** Viber can show stale curate/search/stats with zero cue. See §6, §8 #6. |
| Clarification / tool-starvation / stop-reason UI | UI | CLAIMED_BUT_ABSENT | no | memory v10.0 claims it; **NOT FOUND:** `rg 'clarif\|starv\|stop.?reason' UI+schema` = 0; LibraryChatReply carries only text/toolCalls/sessionId (messages.schema.json:965-984) | Backend clarification signal cannot reach the user. |
| Search/Curate error state rendered | UI | PRESENT_ORPHANED | no | index.ts state.lastError 3 writes (:115/121/146), **0 reads** | Dead error state for search/curate (chat DOES render via chat.ts:77). |
| `sendIpcRequest` correlation-id matching | UI | PARTIAL | yes (latent bug) | UI-verify corrected the cite: helper is client.ts:53 (NOT send.ts); request frame {type,ts,payload} no correlation id (client.ts:59-63); resolves on FIRST frame of responseType (client.ts:95/98-100); default timeout client.ts:39 = **10_000ms (not 15000)** | Two concurrent same-responseType requests cross-resolve. Not Viber-blocking today. |
| ai_observability ai_message row (Viber/Codex turn) | OB | WIRED_LIVE | yes | build_ai_message_record ai_observability.py:217 (engine/prompt/response/grounding/tools/move_grades); append_global_ai_message :350→ai_messages.jsonl :416 + prompt/response/meta artifacts :400-413; **real caller** codex_curate.py:52 import + :615 + _record_codex_ai_message :582 (codegraph: 7 callers incl debrief/bench/vision) | Env-gated (default-on; no-ops under PYTEST unless VIBEMIX_AI_OBSERVABILITY_IN_TESTS; fail-soft swallow :419-420). See §7, §8 #9. |
| eval/session_report Viber blockers | OB | WIRED_CLI_ONLY | yes (dev/release) | viber_live_verification :353, viber_library_request_live_leak :372, viber_backend_error :393, viber_tool_starvation :409, live_claim_guard_spoken_fallback :294; reads events.jsonl :114 + global ai_messages.jsonl :116; deterministic post-hoc :2-8 | Post-hoc harness, NOT inline runtime suppressor. |
| Viber runtime anti-hallucination (toolset seen-set) | OB/TS | WIRED_CLI_ONLY | agent | self.seen toolset.py:113; create_playlist invented-id reject :464; gate in export/sequence/smart_hot_cues/quote_moment :384/655/741/830/952; fetch_url seen_urls :526; tool_starvation _build_starvation_payload :1031 (never LLM-generated) | The actual inline gate that stops Viber speaking from invented context (Cardinal Invariant #2). |
| Viber forensic artifacts on disk | OB | WIRED_LIVE | yes | append_global_ai_message writes prompt.txt/response.txt/meta.json :400-413 + ai_messages.jsonl :414-418; read by session_report :116-117; producer codex_curate.py:615/582 | Both write + read sides exist, with a real Viber producer. |
| Failure-corpus benchmark for Viber | OB | WIRED_CLI_ONLY | yes (dev) | export_cohost_viber_failure_corpus session_report.py:657, run_failure_corpus_benchmark :861; FAILURE_CORPUS_SCHEMA :25, CORPUS_BENCHMARK_SCHEMA :26 | Deterministic backend + injectable repairer. |
| events.jsonl per-session forensic log (cohost) | OB | WIRED_LIVE | yes | record_session_ai_message ai_observability.py:281 → recorder.log_event :302; **live caller** _emit_observability_ai_message dj_cohost.py:3170 (codegraph); consumer session_report.py:114 | Cohost session sink (Viber sink = global ai_messages.jsonl). |
| Release matrix wrapper `check_cohost_viber_matrix.sh` | OB | WIRED_CLI_ONLY | release | EXISTS scripts/release/check_cohost_viber_matrix.sh (7.2k, 31 May); **body unread** — gating semantics + Python entrypoint UNVERIFIED | See §7, §8 #8. |
| Release matrix wrapper `check_flx4_live_context.sh` | OB | WIRED_CLI_ONLY | release | EXISTS scripts/release/check_flx4_live_context.sh (5.7k, 31 May); **body unread** | Theme = FLX4 controller live-context proof. |
| Sven (DJCoHostAgent.llm_node) = ONLY streaming TTS path | VB | WIRED_LIVE | yes | llm_node dj_cohost.py:1870 (yield TTS); constructed `__main__`.py:1491; driven coach.py:848 set_next_event; `rg '.say(\|generate_reply' src/vibemix` = only coach.py (fixed-text), cancel.py (comment), dj_cohost.py | Sven brain = Gemini; Viber/library text never enters this generation. |
| Viber chat output = TEXT/JSON only (no TTS) | VB | WIRED_LIVE | yes | library_cmds.rs:74 subprocess (0 tts/say/transcript_delta/cohost hits); `__main__`.py:4020 prints JSON; codex_curate.py:3737 (0 .say/transcript_delta) | Library window is a SEPARATE window; never touches ws_bus :8765 / TTS chain. Viber CAN NEVER speak. |
| Live-claim guard (corrected→strip→silence) — **Sven** | VB | WIRED_LIVE | yes | apply_live_claim_guard deck_context.py:2240; **imported dj_cohost.py:91, applied :2752** → citation_action='strip', spoken_stripped='', `[ai_text:live-claim-stripped]` (dj_cohost.py:2815-2834); LiveClaimGuardResult :303, held-reply constants :314-325 | **Corrects the completeness-critic: the guard IS in dj_cohost.py (NOT Viber-only).** Closes the #1 live slop bug. |
| Streaming-side live-claim defer | VB | WIRED_LIVE | yes | should_defer_live_claim_stream deck_context.py:2214; imported dj_cohost.py:112, used :2414 | Early-clip before the post-stream authoritative guard. |
| CitationLinter strip / one-shot bypass | VB | WIRED_LIVE | yes | dj_cohost.py:2852 linter ladder (after guard); bypass gated should_bypass() → `[ai_text:unverified]` :2914; strip → _push_silence_pad_and_cancel :2934; _linter_wired :1141 | The single softest seam (one rate-limited un-cited reaction can reach TTS). See §5, §8 #5. |
| Silence short-circuit + slop filter | VB | WIRED_LIVE | yes | dj_cohost.py:2705 (SILENCE_TOKEN='<silence/>' :126); filter_for_slop import :79, applied :2710 | First two gates; suppress before any TTS yield. |
| Fixed-text co-host vocals (Mastered / Judge) via session.say | VB | WIRED_LIVE | yes | coach.py:268 _speak → say(add_to_chat_ctx=False); _make_mastered_speak :256; Judge verdict_evidence_line :389 with citation_id | Deterministic engine-grounded strings only; abstain-first (abstained Judge says nothing). A second speech path but safe. |
| cohost-reaction WS emit (`ipc.session.cohost-reaction`) | VB | WIRED_LIVE | yes | producer dj_cohost.py:3077 (emit only when action ∈ emit/bypass); _build_citation_strip :666 drops unresolved citations :772; schema messages.schema.json:2092 + messages.ts:448; consumer session/ws-bridge.ts:271-279, pill/index.ts:117 | Registry-grounded chips (Invariant #2). |
| Telegram Viber surface | TS(gap) | WIRED_CLI_ONLY | bot | telegram_bridge.py (per CLAUDE.md, optional `telegram` extra, key-gated VIBEMIX_TELEGRAM_TOKEN + ALLOWED_CHATS). **Backends NOT confirmed this session** (rg returned empty); completeness-critic asserts curate-only (no chat_with_codex, no live_context) | UNVERIFIED backend set; inherits Codex-CLI + library-cache preconditions. |
| Energy-curve set sequencing (already shipped) | GM | WIRED_CLI_ONLY | CLI | build_set_with_codex codex_curate.py:1072; sequence_set mcp_server.py:332-340 | GM-verify downgraded the "already shipped WIRED_LIVE" corpus ledger claim → WIRED_CLI_ONLY (no live product caller proven; only `library build-set` CLI). DROP from goldmine — don't re-import. |

---

## 2. Set-generation path trace

Each hop with file:line and a `WIRED_LIVE` (real app IPC) vs `WIRED_CLI_ONLY` (CLI/agent only) verdict.

| # | Hop | Evidence | Verdict |
|---|---|---|---|
| 1 | **UI brief+curve → invoke** | `libraryBuildSet` → `invoke('library_build_set',{brief,curve})` api.ts:2388-2398 (dev fallback only when invoke==null :2393; real error propagates :2394-2397) | **WIRED_LIVE** |
| 2 | **Rust #[tauri::command] + registration** | library_build_set library_cmds.rs:705-737 (curve validation :712-717, spawn :719-734, parse_cli_json+map_curate_result :735-736); REGISTERED generate_handler! main.rs:78/108 | **WIRED_LIVE** |
| 3 | **Auto allow-shell env** | build_library_command sets `VIBEMIX_CODEX_ALLOW_SHELL=1` iff `--backend codex` predicate (library_cmds.rs:126-128/133-137); build_set passes `backend = library_agent_backend()` const :718/730/144-146 | **PARTIAL — const value UNVERIFIED;** if `LIBRARY_AGENT_BACKEND` ≠ `"codex"` the flag never sets and the app hits `codex_mcp_blocked`. Re-verify. |
| 4 | **CLI subcommand** | shells `library build-set <brief> --curve <c> --export rekordbox --backend codex --json` :719-732 | **WIRED_CLI_ONLY** (shared engine; same path CLI users hit) |
| 5 | **Python entry** | _cmd_library_build_set `__main__`.py:5766 → _cmd_library_build_set_codex :5698 | **WIRED_CLI_ONLY** |
| 6 | **Orchestrator** | build_set_with_codex codex_curate.py:1072 (_BUILD_SET_RULES :992, schema :1029, prompt :1042, spawn build_argv :441/subprocess :1189, stop_reason 'exported' :1347) | **WIRED_CLI_ONLY** — SG-verify: caller wire proven, orchestrator body unread in one pass (PARTIAL on internals) |
| 7 | **Codex spawns MCP server** | `codex exec` against `python -m vibemix.library.mcp_server` codex_curate.py:754; build_server mcp_server.py:137 (FastMCP @mcp.tool) | **WIRED_CLI_ONLY** (one toolset instance per run mcp_server.py:16-20) |
| 8 | **Grounded tools** | discover_pool/search_vibe populate seen toolset.py:625/166; sequence_set orders on curve :710 (sequencer beam-search, CURVE_PRESETS sequencer.py:63); export_set writes XML :784; create_playlist persists M3U/JSON | **WIRED_CLI_ONLY** — Invariant #2 seen-gate at tool boundary + wrapper re-validate codex_curate.py:498 + CLI re-validate `__main__`.py:5815 |
| 9 | **JSON → DTO** | normalizeBuildSetResult api.ts:1705 + Rust map_curate_result; export_path trusted only if file exists codex_curate.py:1327 | **WIRED_LIVE** (DTO plumbing); file-existence guard PARTIAL (unread in verify) |
| 10 | **In-app render (the visibility leg)** | renderBuildSet index.ts:498 (rows + rationale + track count + "Exported → <path>" :506-513); runBuildSet :1729-1735; loading :551; curve picker :1984; brief chips :1992 | **WIRED_LIVE per SG lane; asserted-but-unread in one verify pass** — render leg rests on api.ts BuildSetResult mapping (:174-177) + the map's index.ts cites |

**Net verdict:** The build-set set-generation path is the ONE Viber set-prep flow with a genuine Tauri IPC command + registration + in-app render — **WIRED_LIVE end-to-end** (with hop-3 const and hop-10 render leg flagged for re-confirmation). Every OTHER Viber capability (curate, chat, cue tools, search/similar/ingest/stats) is reachable in the running app only through the orphaned `LibraryBridge` (dead, §6) or the CLI/Codex agent — i.e. `WIRED_CLI_ONLY`. **Two fresh-user preconditions gate even build-set:** Codex CLI installed + `codex login`'d (else stop_reason codex_not_installed/codex_auth_required, codex_curate.py:1114-1125, surfaced honestly index.ts:517-523), and a library cache present (`__main__`.py:5778-5792 returns "No library cache" before spawn; starvation Case A toolset.py:1060-1061).

---

## 3. Library freshness & the watcher

**THE WATCHER IS P0 — NOT FOUND.**

- **Exact search:** `rg -n 'import watchfiles|from watchfiles|watchdog|Observer|inotify|FSEvents|kqueue|PatternMatchingEventHandler|on_modified|on_created' src/vibemix/` → **zero real watcher imports/handlers.**
- watchfiles appears only transitively under uvicorn (uv.lock:813), **confirmed unimported** in src/vibemix.
- `runtime/parent_watchdog.py:1-69` is a PROCESS ppid watchdog (polls os.getppid every 2s). `midi/watcher.py` is MIDI hot-plug. Neither watches the library.

**Consequence:** Tracks added or a `collection.xml` re-exported mid-session are invisible to search/similar/pill/curate until the user manually re-runs `library ingest`/`embed-folder`. For a live co-host whose pill/Viber recs are library-grounded, a silently stale index means it recommends from an out-of-date catalog and misses fresh tracks — the exact failure this lane targets.

**Two passive freshness mechanisms exist (both WIRED but coarse/passive):**
1. **30-day boot staleness NUDGE** (`WIRED_LIVE`, both-ended, mounted) — but COARSE + BOOT-ONLY: `is_stale` (staleness.py:37-47) stats `library.pkl` mtime once at boot, never compares `collection.xml` mtime to the index, never re-checks mid-session. A user who re-imported 5 days ago then added tracks gets `is_stale=False` and no warning.
2. **Rekordbox two-factor re-parse** (`PARTIAL`, passive) — rekordbox.py:96-103 re-parses on `xml_mtime` mismatch, but only when `try_load_cache` is actively called; it does not itself trigger a re-embed.

**The ingest pipeline is solid** (cue-anchored excerpts, sha256 content-hash resume cache, snapshot-hash centroid cache that self-invalidates) — the gap is purely the *trigger*. The freshness signal today is "time since last successful ingest", not "index consistent with source".

---

## 4. Cue / hot-cue flow

The cue/hot-cue flow is real, deterministic, anti-slop, round-trip-test-proven — but ships **behind the CLI + Codex agent, not the live app** (CF-verify downgraded 8 of 12 cue claims WIRED_LIVE→WIRED_CLI_ONLY).

**Two live product surfaces (both non-GUI):**
- `library cue <folder>` CLI — parser `__main__`.py:2654 → handler :5952 → export_cued_folder / tag_folder_serato; E2E test test_cue_folder_cli.py:35-128 (real argparse + handler).
- Viber Codex MCP agent — three cue tools (smart_hot_cues mcp_server.py:226, export_smart_cues :239, export_cues :401) dispatched toolset.py:368/802/982.

**Round-trip preservation — MACHINE-PROVEN at the file-format layer:**
- `test_export_serato.py:55` golden spec bytes · `:84` round-trip fields · `:150` write→read parse-back on a real mp3 · `:163` merge preserves a DJ's hand-set pad-5 cue.
- `test_cue_export.py:206` `test_export_against_real_pyrekordbox` — writes via REAL pyrekordbox, reloads the XML, asserts 3 cues (INTRO/BUILD/DROP) survive with correct names.
- `test_cue_folder.py:113/139/241` — bridge → real export_set + real-mp3 Serato read-back.

**The honest caveat the code itself states:** green tests prove bytes/XML conformance, NOT that a specific Mixxx/Serato/Rekordbox build visually lights the pad — that is an explicit one-time human eye-check (export_serato.py:25-27; parked KAAN-ACTION per memory).

**Human hot-cue preservation:** lives on the Viber/smart_cues path (SOURCE_RANK dj>anlz>auto, `preserve_human_hot_cue` smart_cues.py:300). The `library cue --export rekordbox` *folder* path uses `cue_engine→anchors_to_marks` (AUTO anchors only, no human-cue carry) — so a DJ running the folder CLI on already-cued tracks gets a vibemix-only structural set, not a merge (the Serato `--write-tags` path DOES merge-preserve foreign pads via `_merge_cues` export_serato.py:167).

**`export_cues` grounding hole — see §8 #1.**

---

## 5. Viber ↔ Sven boundary: every path where Viber/library text can become speech

The separation is **real, not just claimed.** Viber's library-chat path (library_cmds.rs:74 subprocess + codex_curate.py:3737 chat_with_codex) has ZERO references to `.say`/`tts`/`transcript_delta`/`cohost`/the :8765 ws bus/`DJCoHostAgent` — grep returned 0 across library_cmds.rs, codex_curate.py, toolset.py, suggestion.py, eval/session_report.py, ai_observability.py. **Viber can never speak.** No P0 leak found.

| Speech path | Source → Sink | Guard | Verdict |
|---|---|---|---|
| Sven `llm_node` streaming TTS | MusicState evidence (set_next_event coach.py:848) → tts yield dj_cohost.py:1870/2570/2590 | 4-stage in-loop gate (below) | **GUARDED** |
| ↳ Gate 1: silence short-circuit | `<silence/>` token dj_cohost.py:2705 | suppress before any yield | **GUARDED** |
| ↳ Gate 2: slop filter | filter_for_slop dj_cohost.py:79/2710 | banned-phrase suppress | **GUARDED** |
| ↳ Gate 3: live-claim guard (UNCONDITIONAL strip) | apply_live_claim_guard dj_cohost.py:91/2752 → strip→silence :2815-2834 | rewrites/strips any unsupported transition/blend/handoff/move-effect/judge-overpraise BEFORE the linter | **GUARDED (strongest)** |
| ↳ Gate 4: CitationLinter | dj_cohost.py:2852, strip→silence :2934 | drops un-resolved citations | **GUARDED** |
| ↳ Gate 4 bypass (one-shot) | should_bypass() → `[ai_text:unverified]` dj_cohost.py:2887/2914 | rate-limited; runs AFTER the unconditional guard | **LEAK (P2, bounded)** — see §8 #5 |
| Fixed-text co-host vocal (Mastered unlock) | _make_mastered_speak coach.py:256 → say :271 (add_to_chat_ctx=False) | deterministic fixed string, no LLM | **GUARDED** |
| Fixed-text co-host vocal (Judge verdict) | verdict_evidence_line coach.py:389 with citation_id | abstain-first; abstained Judge writes no citation, says nothing | **GUARDED** |
| cohost-reaction WS emit | dj_cohost.py:3077 (emit only when action ∈ emit/bypass); _build_citation_strip :666 drops unresolved :772 | registry-grounded chips (Invariant #2) | **GUARDED** (visual, not speech) |
| Pill "what's next" | SuggestionService → ws frame field ws_bus.py:1082; honest-null suggestion.py:25-28 | visual-only, no TTS; None when nothing qualifies | **GUARDED** (cannot reach voice) |
| Viber chat output | library_chat → JSON text rendered as DOM | separate window; never touches TTS chain | **GUARDED** (text-only by construction) |
| Viber live-claim guard (chat replies) | codex_curate.py _apply_live_claim_guard :3446/:3992 (shared :3348) | held reply when two-deck proof absent | **GUARDED** — but guard call-sites codex_curate.py:3290-3800 **UNVERIFIED** (harness dropped page); rests on imports + Rust plumbing |

**Correction to the brief:** `apply_live_claim_guard` is NOT Viber-only. Source confirms it is imported (dj_cohost.py:91) and applied (dj_cohost.py:2752) in the LIVE Sven co-host AND imported in codex_curate.py for Viber. The completeness-critic's claim that "dj_cohost.py does NOT import or call it" is **WRONG** (verified `rg apply_live_claim_guard src/vibemix/agent/dj_cohost.py` → lines 91 + 2752). Both surfaces are guarded.

---

## 6. UI surface: dead controls, proof chips, stale-state, tool starvation

**P0 ROOT CAUSE: the entire Viber/Crate IPC backend is orphaned.** The Crate UI is fully built and mounted (desktop-shell.ts:44; all 13 `ipc.library.*` types compiled into validator.generated.mjs so requests DO go on the wire), but `LibraryBridge` (the only register/emit for `ipc.library.*`) is **never instantiated** — repo-wide grep = 1 hit (def only), codegraph_callers = [], session_loop._build_satellites builds only WizardSatellite. Requests hit the bus, find no handler (ws_bus.py:491-494 silently ignores), and time out after 15s into generic errors. **Worse,** the orphaned bridge imports 5 nonexistent functions + 1 nonexistent module (`vibemix.library.stats` — `ls` → No such file) so it would `ImportError`/`AttributeError` even if wired.

**Dead controls (one-ended IPC types named explicitly):**
- `ipc.library.chat.tool` — TS subscribes (api.ts:124) + viber-tape renders; **Python never emits** (`rg 'chat.tool' src/vibemix` = 0; _on_chat_tool is `pass` :164, unregistered). The proof-chip tape is DEAD.
- `ipc.library.chat.request/.reply`, `.curate.*`, `.search.*`, `.similar.*`, `.ingest.*`, `.stats.*` — TS senders wired, Python handlers orphaned + broken (PARTIAL each).
- `reply.toolCalls` — persisted in schema (:971-976) + surfaced by api.ts:113, but chat.ts has **0 refs** — silently dropped.

**Proof chips:** NO per-pick proof chip exists in a curated set (the live-deck "receipts" panel index.ts:1083-1115 is a different surface). Even the `toolCalls` the reply carries are never rendered.

**Stale-state:** **NO freshness indicator on any Viber result** — `rg 'fresh|stale|as of|updated|timestamp|ago|cached|Date.now' library/*.ts` = 0; no result schema carries a time field. **Direct rule-5 violation:** persisted DOM curate/search/stats results + the chat transcript have zero "as of" cue.

**Tool starvation / clarification:** the v10.0-claimed clarification/tool-starvation stop-reasons **cannot reach the user** — no IPC field (LibraryChatReply has only text/toolCalls/sessionId :965-984), no UI (`rg 'clarif|starv|stop.?reason'` = 0). Viber would render a clarification request as if it were an answer.

**Latent bug:** `sendIpcRequest` (client.ts:53) matches replies by responseType + first-frame, no correlation id; default timeout 10_000ms. Two concurrent same-responseType requests cross-resolve. Not Viber-blocking today (Crate issues one in-flight request per pane).

---

## 7. Observability & eval coverage for Viber (captured vs silent)

**Captured:** A Viber/Codex curate turn DOES emit a forensic `ai_message` row (engine/prompt/response/grounding/tools/move_grades) via `append_global_ai_message` (ai_observability.py:350), with a **real Viber caller** (codex_curate.py:52 import + :615 + _record_codex_ai_message :582; codegraph confirms 7 callers incl debrief/bench/vision). Artifacts (prompt.txt/response.txt/meta.json) land per response_id (:400-413) + a row in `ai_messages.jsonl` (:414-418). The eval blocker harness (eval/session_report.py) flags ungrounded Viber output: `viber_live_verification` :353, `viber_library_request_live_leak` :372, `viber_backend_error` :393, `viber_tool_starvation` :409, plus `live_claim_guard_spoken_fallback` :294. A failure-corpus benchmark exists (export_cohost_viber_failure_corpus :657, run_failure_corpus_benchmark :861).

**Silent (the gaps):**
1. **Capture is env-gated + fail-soft.** `append_global_ai_message` no-ops under `PYTEST_CURRENT_TEST` unless `VIBEMIX_AI_OBSERVABILITY_IN_TESTS` (:379-384); the module disables under a falsey `VIBEMIX_AI_OBSERVABILITY` (`_enabled` :28-32); every write is swallowed by a bare try/except (:419-420). Flag off or app_data unwritable ⇒ a bad Viber turn produces NO forensic row AND no eval input, with nothing surfacing the gap.
2. **session_report is post-hoc, NOT an inline runtime suppressor.** A `viber_library_request_live_leak` is detected on the next report run, not blocked before the user sees it. Viber's *runtime* anti-hallucination is the toolset seen-set gate (id-level), not reply-text-level.
3. **Two release wrappers exist but their gating semantics are UNVERIFIED** — `check_cohost_viber_matrix.sh` (7.2k) and `check_flx4_live_context.sh` (5.7k) bodies were not read; cannot confirm they propagate a non-zero exit (a gate that runs but doesn't fail the build is a paper gate). **A green/red status of these is load-bearing release evidence — Codex should `cat` + run them.**

---

## 8. Top 10 product blockers before Viber feels real

Ranked by product-truth value. Each: severity + evidence + the one change that clears it.

| # | Blocker | Sev | Evidence | The one change that clears it |
|---|---|---|---|---|
| 1 | **Entire Viber/Crate IPC backend is orphaned — every Crate control is dead in the app** | **P0** | LibraryBridge never instantiated (repo grep=1 def, codegraph_callers=[], session_loop builds only WizardSatellite); requests time out 15s → generic error | Instantiate LibraryBridge in session_loop._build_satellites and register it on the live router (mirror WizardSatellite) — AND fix #2 first or it crashes |
| 2 | **LibraryBridge calls 5 nonexistent fns + 1 nonexistent module — crashes even if wired** | **P0** | library_bridge.py:47/72/89/108/133/150 vs actual defs (chat_turn/curate_playlist/search_text/search_similar/ingest_library/library_stats all absent; `vibemix.library.stats` `ls`→no file) | Rewrite the bridge against the REAL backend API (chat_with_codex/curate_with_codex/search/search_by_text/ingest/library.stats) |
| 3 | **No live file/library watcher — index never auto-refreshes** | **P0** | NOT FOUND: `rg 'watchfiles\|watchdog\|inotify\|FSEvents\|on_modified\|on_created' src/vibemix` = 0 (§3) | Add an FSEvents/watchfiles watcher on collection.xml + audio folders that debounces → triggers the resumable ingest; OR a per-session collection.xml-mtime re-check that re-emits the staleness nudge mid-session |
| 4 | **Cue/hot-cue export ("the moat") has NO Tauri app/IPC surface** | **P1** | NOT FOUND: no cue/export type in messages.schema.json; no Rust cue command (§4) | Add an `ipc.library.cue.*` message type + Rust command shelling `library cue …` (run codegen:ipc, wire BOTH ends) |
| 5 | **CitationLinter one-shot bypass can voice a single un-cited Sven reaction** | **P2** | dj_cohost.py:2887 should_bypass() → :2914 `[ai_text:unverified]`; runs AFTER the unconditional live-claim guard (:2820/2834), so transition/move/judge overclaims are stripped first | Accept-by-design OR tighten should_bypass to require at least one resolved citation; bounded blast radius (low-severity color only) |
| 6 | **No freshness indicator on any Viber result — can show stale curate/search/stats/chat (rule-5)** | **P1** | NOT FOUND: `rg 'fresh\|stale\|timestamp\|ago\|cached\|Date.now' library/*.ts` = 0; no time field in result schemas (§6) | Add an "as of <ts>" field to each result schema + render a staleness badge per result |
| 7 | **`export_cues` has NO seen-set grounding gate — Invariant #2 breach** | **P2→elevate** | toolset.py:987-1007 validates only non-empty track_path + non-empty cues; no `if track_id not in self.seen`; contrast export_smart_cues :809-815 | **DECISION REQUIRED (fix-or-drop):** add a seen-set gate, OR drop the @mcp.tool registration (mcp_server.py:401-423), OR consciously accept the hole. It currently ships registered + dispatch-routable (toolset.py:1478). |
| 8 | **Release wrappers' gating semantics unverified** | **P2** | check_cohost_viber_matrix.sh + check_flx4_live_context.sh exist; bodies unread (§7) | `cat` + run both; confirm non-zero exit propagation |
| 9 | **Viber observability capture is env-gated + fail-soft — bad turns can be silently un-recorded** | **P2** | ai_observability.py:28-32/379-384/419-420 (§7) | Make capture failures visible (log a stderr warning) when the flag is on but a write fails |
| 10 | **Auto allow-shell depends on an unread const value** | **P2** | library_cmds.rs:126-137/718/730/144-146; `LIBRARY_AGENT_BACKEND` value unread | Read the const; if ≠ `"codex"`, the build-set flow silently dies in the app (codex_mcp_blocked) |

---

## 9. Next implementation packages (ordered by product-truth value)

| # | Package | What / Why | Files likely touched | Tests to add/run | Risk & shared-file overlap | Live/release gate |
|---|---|---|---|---|---|---|
| 1 | **Resurrect the Crate backend** | Rewrite + wire LibraryBridge against the real API and instantiate it as a satellite — turns the entire dead Crate (chat/search/similar/ingest/curate/stats) live. Highest-leverage: the UI is already built. | runtime/library_bridge.py, runtime/session_loop.py:44-57, ws_bus.py | new test_library_bridge.py; run ipc-wiring-checker on all 13 `ipc.library.*` types; `npm run build && npm test` | session_loop.py is shared (concurrent sessions) — stage surgically | run drive-vibemix to confirm a Crate chat returns a real reply in-app |
| 2 | **Wire the proof-chip tape + reply.toolCalls in the Crate** | Emit `ipc.library.chat.tool` from Python (currently `pass`); render reply.toolCalls in chat.ts. Makes Viber's grounding VISIBLE — directly serves rule-5. | runtime/library_bridge.py:164, codex_curate.py (tape emit), tauri/ui/src/library/chat.ts:75/83, viber-tape.ts | viber-tape render test; ipc-wiring-checker on `ipc.library.chat.tool` | depends on #1 | grounding-review skill before ship |
| 3 | **Library watcher (P0 freshness)** | Add an FSEvents/watchfiles debounced watcher on collection.xml + audio dirs → triggers resumable ingest; emit a mid-session staleness re-check. Closes the silently-stale-index failure. | new library/watcher.py, runtime/session_loop.py, library/staleness.py | test_watcher.py (mtime change → ingest trigger); test_staleness mid-session | adds watchfiles as a real dep (currently transitive only) — update PyInstaller spec | live verify: add a track, confirm it appears in pill/search without restart |
| 4 | **Cue-export IPC + GUI surface** | Add `ipc.library.cue.*` + Rust command shelling `library cue` → makes the cue "moat" clickable. | tauri/ui/src/ipc/messages.schema.json (+codegen:ipc), tauri/src-tauri/src/library_cmds.rs, new UI panel, runtime handler | ipc-wiring-checker; test_cue_folder_cli reuse | schema.json shared — codegen:ipc mandatory or new fields rejected | run codegen:ipc; both-ends confirmed |
| 5 | **`export_cues` grounding fix (or drop)** | Add a seen-set gate to export_cues mirroring export_smart_cues, OR drop the registration. Closes the Invariant #2 hole. | library/toolset.py:982-1027, mcp_server.py:401-423 | test_toolset export_cues rejects raw track_path | low overlap | grounding-review skill |
| 6 | **Per-pick proof chips + deterministic-fact provenance** | Thread {confidence/similarity, camelot, bpm, energy} + "computed-not-guessed" tags into curated track rows (data already produced, dropped at codex_curate.py:498). | toolset.py:167/634, codex_curate.py:498, curate-result schema, UI rows | per-track chip render test | needs a curate-result wire (depends on #1) | — |
| 7 | **Freshness badge on Viber results** | Add an "as of <ts>" field to result schemas + a per-result staleness badge. Closes rule-5. | result schemas, library/*.ts result renderers | staleness-badge spec | schema.json shared (codegen:ipc) | — |
| 8 | **Verify + harden release wrappers** | Read/run check_cohost_viber_matrix.sh + check_flx4_live_context.sh; ensure non-zero exit propagation. | scripts/release/*.sh | run both scripts on current source | none | release gate |

---

## 10. Creative agent superpowers (Viber-as-Agent): adopt / defer / drop

Each grounded in existing substrate. (`✓` = substrate confirmed this audit.)

| Idea | Lens | Verdict | Grounded in | Why |
|---|---|---|---|---|
| **Grounded per-pick "why-it-works" receipts** (structured per-transition: "124→126 BPM, 8A→9A, energy 62→71") | agentic + grounding | **ADOPT** | facts already computed + discarded: harmonics.to_camelot toolset.py:188, score_energy_cached :558, transition_slate score components :319-323, TrackRelation.why() | data produced every run; only structuring missing; facts are LLM-untouchable (Invariant #3) |
| **Self-correcting tool-chain: {error, recovery_hint, retry_tool} on rejections** | agentic | **ADOPT** | handlers already never raise + _build_starvation_payload three-case classifier toolset.py:1031 | additive dict keys; Codex tolerates extra keys; pattern proven |
| **Visible self-narrating reasoning trail** (extend `[viber-tool]` tape with intent) | agentic + grounding | **ADOPT** (depends on #1/#2 wiring) | _emit_tool_event toolset.py:1398, tape pipe codex_curate.py:649/515/554 | tape pipe already wired; converts opaque "frozen prompt" into a trust trail |
| **Generalize live-claim guard to ALL Viber speech paths** | agentic + grounding | **ADOPT** | guard imported codex_curate.py:53-79; apply on chat reply path | single most important agentic-safety move; lets every other proactive idea ship without slop risk |
| **Export receipt with NAMED drops + Gate reason** (enrich the existing "N dropped") | grounding | **ADOPT** | dropped_ids already on wire api.ts:1739 + rendered index.ts:1449 | turns a scary count into a transparent report |
| **"Grounding caught this" badge** (aggregate !ok rejections from the tape) | grounding | **ADOPT** | rejection returns + tape pipeline already exist | markets the moat; makes the gate legible at summary altitude |
| **"Show your sources" link-out footer** (from seen_urls) | grounding | **ADOPT** | web_search seen_urls toolset.py:508, fetch_url hard-gate :526 | url-seen gate already guarantees Viber speaks only from fetched pages; needs TAVILY_API_KEY |
| **Deterministic-fact provenance tags** ("computed, not guessed" on Camelot/energy/genre) | grounding | **ADOPT** | honest-null already enforced toolset.py:188/553-567/419-452 | surfaces the discipline; null reads "key unknown" not a guess |
| **Cross-run grounding memory: recall_prior_picks tool (re-validated)** | agentic | **ADOPT** (cheap) | write side exists (append_global_ai_message persists track_ids codex_curate.py:631); only reader + re-ground missing | continuity without breaking per-run seen isolation |
| **Result-summary "how Viber built this set" structured trace** | grounding | **ADOPT** | _read_tool_event_trace codex_curate.py:554 (raw tape WIRED) | structured fold over ACTUAL tool calls can't hallucinate the chain |
| **Make the Viber live-claim HELD reply a VISIBLE "I won't claim that yet" chip** | grounding | **ADOPT** | guard WIRED codex_curate.py:3303/3446/4004; LiveClaimGuardResult.corrected | turns a hedge into a visible integrity moment |
| **Resident A&R / Crate Gap Finder** (set-diff + cosine + k-means on embedded library) | set-craft | **ADOPT** (Pro-tier wedge) | own CLAP engine; pure-numpy, no dep, no Gemini | "DJs forget tracks they own"; build-from-own-primitives, not an external import |
| **Latent "surprise me" novelty dial** (gamma term exists, no caller feeds it) | set-craft | **ADOPT** | sequencer.py:79 gamma + :297/359/371 surprise dict; discovery.intent_centroid :81 | a slider, not a new engine; counters k-clones |
| **Multi-hop harmonic-journey planner** (harmonics is pairwise-only) | set-craft | **ADOPT** | harmonics.py:35-62 (to_camelot/neighbors/energy_boost_key) | deterministic table BFS = anti-slop by construction |
| **"Rediscover your own library" recency-aware deep-cut surfacing** | set-craft | **ADOPT** (verify Rekordbox last-played field) | discovery.discover_pool :285; sequencer recency delta term :80 (unfed) | the project's stated #1 wedge; receiving cost term already exists |
| **Close Viber's taste loop (write-back from kept/dropped)** | agentic | **DEFER** | consume leg wired (_taste_hint codex_curate.py:262); produce leg missing; live-pill proves mechanism (suggestion.py:413) | privacy gate (unresolved observability/user-data decision) |
| **Proactive "prep-ahead" crate from the live set** | agentic + set-craft | **DEFER** | discover_pool ref_track_ids/exclude_ids toolset.py:586; SuggestionService._played :255; transition_slate mode='live' :262 | intrusion risk (violates "never break the flow"); needs new card IPC (unverified) |
| **Multi-turn editable SetPlan** | agentic | **DEFER** | build_set_with_codex :1072; sequence_set candidates :716 | breaks per-run seen isolation unless backed by the ledger (idea above) |
| **Autonomous library-hygiene agent** | agentic + set-craft | **DEFER** | staleness.py/doctor.py/ingest.py in tree; starvation Case A toolset.py:1060 | autonomous ingest writes ~/.cache — must be user-confirmed |
| **Crowd-read → set-direction feedback** | set-craft | **DEFER** | MusicState read-only; next_suggestion.choose_next | cross-boundary; sequence after pill wiring |
| **Transition-slate per-pair mix advice in UI** | set-craft | **DEFER** | transition_slate toolset.py:232 (no live caller); smart_cues | needs IPC type + UI surface |
| **B2B / back-to-back set simulation** | set-craft | **DEFER** | taste_model + profile_projection; sequencer | net-new alternating-cost loop; demos well |
| **Confidence-floor abstain on weak vibe matches** | grounding | **DEFER** | search confidence toolset.py:174; _build_starvation_payload :1031; _is_empty_or_error :1430 | needs floor tuning on funded-key ear-pass |
| **Per-pick freshness receipt** | grounding | **DEFER** | staleness.py mtime machinery; embed_cache content-hash | depends on per-file freshness extension |
| **Cross-run seen-set isolation receipt** | grounding | **DEFER** | toolset.py:91-113 per-run seen | surfaces an invariant as a promise; needs curate-result wire |

---

## 11. External goldmine (Mixxx/research relevant to Viber): adopt / defer / drop

Evidence rank: research corpus is LOWER (verify before citing); license claims were fact-checked against raw LICENSE files in the-vibe-web-map-FACTCHECK.md.

| Item | Verdict | License | Complexity | Why / Evidence |
|---|---|---|---|---|
| **Octave-aware BPM folding** in next_suggestion / sequencing BPM filter (√2 octave fold) | **ADOPT** (smallest-effort, highest-value) | Mixxx GPL-2.0 = learn-from-spec only; the fold is short math, not authored expression | low | a real bug — 174↔87 pairings wrongly rejected (the-mixxx-goldmine-map.md:72; Mixxx synccontrol.cpp:290). **CONFIRM the no-fold gap at next_suggestion.py BPM filter before building** (region re-read was blocked) |
| **Audio key detection** (HPCP/constant-Q chroma + Krumhansl 24-profile correlation + confidence margin) | **ADOPT** (spike DSP core on 20 known-key tracks first) | reimplement-from-paper only — essentia AGPL-3.0, libKeyFinder GPL-3.0; never vendor source or copy AGPL profile coefficients | medium | Camelot stack dies on untagged audio (harmonics.to_camelot honest-null); torch-free numpy CQ kernel. **MUST ship with calibrated confidence margin + abstain (Invariant #3)** — a confidently-wrong detector poisons every harmonic suggestion (the-mixxx-goldmine-map.md:97-102) |
| **Automix cue/switch-point novelty method + M-DJCUE dataset** | **DEFER** (offline eval/cross-check only) | MIT permits, but librosa+essentia+madmom-py2 stack forbids depending — reimplement from arXiv 2007.08411 | medium | cross-check vs CUE-DETR; M-DJCUE as labeled eval set. 96% figure UNVERIFIED. **Transitive madmom (NC) — never vendor** |
| **beat_this ONNX** (downbeat/beatgrid) | **DEFER** (higher value to live Judge than Viber) | code+weights MIT (CPJKU); torch-hard → ONNX export needed | medium | downbeat-aligned cue/transition scoring beyond CUE-DETR. Torch-free only via the .onnx artifact (pip pulls torch) |
| **Per-stem isolation** (demucs.onnx / python-audio-separator) | **DROP** (for the torch-free path; at most offline opt-in) | demucs.onnx = C++ ORT CLI; python-audio-separator hard-deps torch>=2.3+librosa — must NOT enter tree | high | marginal for metadata/CLAP-driven set-prep |
| **Pro DJ Link / StageLinQ off-the-wire deck identity** | **ADOPT for LIVE co-host; OUT-OF-SCOPE for Viber** | prolink/go-stagelinq/PyStageLinQ MIT; dysentery EPL-1.0 spec-only (reimplement UDP from spec) | medium | Viber reasons over the static library, not live decks. Confirmed NOT in tree (`grep prolink\|stagelinq\|50000\|51337 src/` → ZERO) |

**HARD LICENSE BLOCKS:** madmom model files are CC-BY-NC-SA-4.0 (non-commercial) — **BLOCKED transitively under Automix/All-In-One in the monetized product** (the-vibe-web-map-FACTCHECK.md:74-79). essentia (AGPL-3.0), libKeyFinder (GPL-3.0), Mixxx (GPL-2.0) = reimplement-from-spec only, never vendor source.

---

## 12. DO NOT CLAIM (for public/docs/product copy)

Every Viber claim below is NOT `WIRED_LIVE` in the running desktop app — marketing/docs must not state these as shipped app features:

- ❌ **"Chat with Viber in the app / the Crate."** The Crate chat IPC backend is orphaned (LibraryBridge never instantiated + imports nonexistent fns). In-app chat times out into an error. Chat works only via the CLI/Codex agent.
- ❌ **"In-app library search / similar / ingest / stats / curate."** All `ipc.library.*` request/result pairs are one-ended (TS sender, dead Python handler). Only `library_build_set` has a real working Tauri command.
- ❌ **"Viber shows you which tracks/tools grounded its answer" / "proof chips."** `ipc.library.chat.tool` has no Python emitter; reply.toolCalls is never rendered.
- ❌ **"One-click cue / hot-cue export / Serato tagging from the app."** No cue IPC type, no Rust cue command — CLI + Codex agent only.
- ❌ **"Viber auto-keeps your library fresh / detects new tracks."** No watcher exists; re-ingest is manual CLI only. The staleness signal is a coarse 30-day boot nudge, not live freshness.
- ❌ **"Viber learns your taste over time."** The taste loop is open — Viber consumes a static profile but never writes back from accepted/rejected picks.
- ❌ **"Cues appear on your deck in Mixxx/Serato/Rekordbox."** Bytes/XML round-trip is machine-proven, but visual pad rendering in any specific app build is an UNVERIFIED manual eye-check.
- ⚠️ **"web research / DJ-knowledge RAG / quote-a-moment."** Registered but dormant — `quote_moment`/`export_cues`/`fetch_url` are in NO prompt block; web_search/RAG are external-key/corpus-gated and chat-only. Default-user firing rate is effectively zero.
- ⚠️ **"Viber set-prep works out of the box."** Requires Codex CLI installed + `codex login`'d AND a prior `library ingest` — a fresh install gets honest errors, not a set.

---

## 13. Raw workflow transcript & inspection paths + sieve/refute summary

**Files inspected per lane (from raw_paths):**

- **tool-surface:** toolset.py:1-1675 (handlers + dispatch 1448-1479) · mcp_server.py:1-457 (16 @mcp.tool 154-423) · codex_curate.py:1-4088 · `__main__`.py:2776-2870/4045-4093/5638-5710 · main.rs:107-109 · library_cmds.rs:64/126-137/263-278/359/671-770.
- **set-generation:** codex_curate.py:1-1419 · toolset.py:1-1332 · mcp_server.py:1-457 · sequencer.py:1-90 · `__main__`.py:5698/5766/5815 · library_cmds.rs:1-300/706-737 · main.rs:78/108 · api.ts/index.ts · tests test_codex_curate.py:2855/2936, test_cli_exit_codes.py:65, test_library_window_contract.py:21.
- **library-freshness:** staleness.py:1-184 · parent_watchdog.py:1-69 · ingest.py · folder_ingest.py · cache_paths.py · centering.py:7-129 · store.py:65-84 · rekordbox.py:91-103 · `__main__`.py:1543-1992 · messages.py:1778/1798 · messages.schema.json:2477/2487/2530 · staleness-banner.ts · SettingsDrawer.ts · uv.lock:813.
- **cue-flow:** smart_cues.py:1-568 · cue_folder.py:1-296 · cue_engine.py:1-179 · export_serato.py:1-264 · cue_export.py:1-195 · export_rekordbox.py:1-309 · suggestion.py · ws_bus.py · toolset.py · mcp_server.py · `__main__`.py:2654/2900/5854/5952/1611 · pill/next-suggestion.ts · tests test_export_serato.py, test_cue_export.py, test_cue_folder.py, test_cue_folder_cli.py.
- **viber-sven-boundary:** dj_cohost.py:666/1141/1491/1870/2705/2752/2836/3045 · deck_context.py:303/314-325/2240 · coach.py:256-271/327-389/644-689/848 · suggestion.py:21-28 · codex_curate.py:143-160/3737 · `__main__`.py:1491/4020/4093 · library_cmds.rs:74 · api.ts · messages.schema.json · check_cohost_viber_matrix.sh.
- **ui-surface:** library/api.ts:1-211 · chat.ts:1-97 · index.ts (963 lines, partial) · viber-tape.ts · messages.schema.json:103-146/824-1040 · ipc/client.ts (corrected from send.ts) · validator.generated.mjs · desktop-shell.ts · library_bridge.py:1-166 · session_loop.py:40-86 · ws_bus.py:441/490-514 · codex_curate.py/search.py/ingest.py (def lists) · `ls stats.py`→absent · codegraph_callers LibraryBridge=[].
- **observability-eval:** ai_observability.py:1-438 · session_report.py:1-1440 · toolset.py:1-1332 · codex_curate.py:1-80 · deck_context.py:2239 · scripts/release/check_cohost_viber_*.sh (existence) · scripts/verify_ai_observability.py:67 · debrief/tldr.py:107.
- **external-goldmine:** /tmp/vibemix-codex-inbox/{the-vibe-web-map.md, the-vibe-web-map-FACTCHECK.md, the-mixxx-goldmine-map.md, mix-gold-mine-recovery.md, creative-idea-forge.md} (all full) · toolset.py:1-29 · next_suggestion.py (present) · /tmp/mixxx-src (GPL-2.0 clone, learn-from-spec only).

**Sieve / refute summary — what the adversarial verify downgraded:**

- **tool-surface:** 14/16 tools HELD WIRED_LIVE *at the agent level*; **quote_moment + export_cues DOWNGRADED to PARTIAL** (registered + dispatch-routable but named in NO prompt block ⇒ dormant; export_cues additionally lacks a seen-set gate). One evidence caveat: live-context guard body (codex_curate.py:3290-3800) **UNVERIFIED** — harness dropped the page; kept WIRED on imports + Rust plumbing. **This packet further reclassifies the whole agent surface to WIRED_CLI_ONLY** under the stricter ui-surface finding (no `ipc.*`/GUI door).
- **set-generation:** build-set end-to-end + the `library_build_set` IPC both-ends+registration UPHELD WIRED_LIVE; 9 sub-claims downgraded to PARTIAL (files holding the unverified leg — toolset.py/mcp_server.py/codex_curate.py/index.ts — not opened in that verify pass; NOT findings of broken wires). **One real risk:** the auto allow-shell flag hinges on `LIBRARY_AGENT_BACKEND == "codex"` (unread).
- **cue-flow:** 8/12 DOWNGRADED WIRED_LIVE→WIRED_CLI_ONLY — every cue capability is reachable only via the `library cue`/`export-set` CLI or the Codex MCP agent; **NO Tauri/IPC cue door** (live IpcRouterBus handles only next_suggestion.* + settings/profile/recordings). The round-trip-test claim → PARTIAL (file-format machine-proven, cross-app render manual). Only the pill next-suggestion engine + its ws-bus wire are genuinely WIRED_LIVE; the ws_bus.py:1082 serialize line was single-stepped.
- **viber-sven-boundary:** ZERO downgrades — all 9 boundary claims survived. Two notes: Sven's llm_node is not the literal ONLY audio producer (coach.py also speaks fixed deterministic text via session.say — safe); coach.py:854/858 generate_reply is the trigger for llm_node, not a second text generator.
- **ui-surface:** the one verified claim (sendIpcRequest) HELD PARTIAL but its evidence was mis-cited (real file ipc/client.ts:53 not send.ts; real default timeout 10_000ms not 15000). The dead-control + orphaned-LibraryBridge findings stand.
- **observability-eval:** all 7 claims VERIFIED, none refuted (an earlier "absent" emission was a tool-flake; the stack genuinely exists with a real Viber caller). Unclosed caveats: release-wrapper bodies + several session_report internal lines unread.
- **external-goldmine:** the "energy-curve sequencing already shipped WIRED_LIVE" corpus-ledger claim DOWNGRADED to WIRED_CLI_ONLY (only a CLI caller proven; tool channel died mid-audit before the caller-trace). Several in-tree negatives lean on the corpus's own grep-confirmed reality-check (mix-gold-mine-recovery.md @ HEAD 0e7bdc1c).

**Synthesis-level corrections to the brief / completeness-critic (source-verified this session):**
1. `apply_live_claim_guard` is in **dj_cohost.py (lines 91, 2752)** AND codex_curate.py — NOT Viber-only. The completeness-critic's "dj_cohost.py does NOT call it" is **refuted**. Sven's anti-fake-fallback speech protection IS audited (§5).
2. `intent='live_next_pill'` is set ONLY at toolset.py:348 and used internally by suggestion.py — **no Viber caller passes it**; compile_musical_context's acceptance of it is a handler-side string, not a wired live path. The pill is a deterministic CLAP path, **not Viber/Codex**.
3. The pill rides as a `next_suggestion` frame **field** (ws_bus.py:1082), confirmed — there is **NO `ipc.pill.suggestion` schema type** (`NOT FOUND` in messages.schema.json). Both ends (ws_bus producer + pill/next-suggestion.ts consumer) matched. The pill feedback back-channel (`next_suggestion.choose/.feedback`) is handled ws_bus.py:850-882.
4. `SuggestionService` IS instantiated (`__main__`.py:1613) — the completeness-critic's "PRESENT_ORPHANED, never instantiated" is **refuted**; the live pill engine is WIRED_LIVE.

**Remaining UNVERIFIED (Codex should close):** live-context guard body codex_curate.py:3290-3800 · `LIBRARY_AGENT_BACKEND` const value · index.ts:2065 onViberTool listener + renderBuildSet render leg · release-wrapper bodies (check_cohost_viber_matrix.sh, check_flx4_live_context.sh) · telegram_bridge.py backend set (curate-only?) · ANLZ parser body (anlz_ingest.py/rekordbox.py) · the search/similar/ingest in-app end-to-end (registered main.rs:26-35, UI senders present, but never traced through the orphaned bridge).
