# Vibe Mix — UI / IPC Surface + Button Audit (wiring & live-test reference)

> From the full control-surface map (2026-05-26). Drives the sequencing/discovery/export WIRING
> (where to plug in) and the "every button works" LIVE-TEST pass. Line numbers are orientation —
> verify exact lines when editing (tree is changing under active sessions).

## Agent-engine entry points (where the set-prep flow plugs in)
- **CLI** `vibemix library curate <theme>` / `build-set` / `export-set` route through
  `__main__.py` library subcommands and the grounded tool surface.
- **Tauri Library window** (`tauri/ui/src/library/` + `tauri/src-tauri/src/library_cmds.rs`):
  the GUI spawns `vibemix library ...` as a subprocess and parses JSON stdout
  (does NOT instantiate a Viber agent in-proc). Current Library modes include
  search, chat, curate, and Build a Set.
- **Telegram** `vibemix library telegram` (`telegram_bridge.py`) — mobile curate. Tool surface inherited from `LibraryToolset`, so new tools land there for free.
- **Live session pill** — `runtime/suggestion.SuggestionService` → `next_suggestion()`; the 1-step transition primitive the sequencer generalizes.

## IPC surface (ws_bus 8765, `IpcRouterBus` → SessionLoop handlers)
Inbound (handler in `runtime/session_loop.py`): `ipc.session.mute`, `ipc.settings.set/get`, `ipc.status.recheck`, `ipc.recordings.list/delete/events`, `ipc.profile.view/regenerate/delete/set_consent`. Push-only: `ipc.session.snapshot` (30Hz), `ipc.boot`, `ipc.status.tick`. Schema: `tauri/ui/src/ipc/messages.schema.json` → **after any schema edit run `cd tauri/ui && npm run codegen:ipc`** (pre-compiled ajv validator). Library/curate results flow via Tauri commands (subprocess stdout), NOT ws IPC.

## Button audit — KNOWN-DEAD / no-op (verify + fix in the live-test pass)
1. **Skill rocker (BEG/INT/PRO)** — applies live via env-var + agent rebuild path (`_apply_skill`); persona panel built once at mount → shows default INT on boot (optimistic flip works). *Master-handoff says this WAS fixed; re-verify live.*
2. **Voice picker** — DEAD live (TTS chain has no live voice-swap; needs env-var + rebuild like skill).
3. **Output device picker** — DEAD live (device set at wizard time only).
4. **Output profile HP/SPK** — DEAD (EQ profile switch not implemented).
5. **Mood rocker (HYPE/TEACH/COACH)** — LIVE (optimistic onChange + real ipc.settings.set).
6. **Pill next-suggestion** — read-only (queue/cue action = Phase 2, not wired).
7. **Mute, profile view/regenerate/delete/consent, wizard calibration, recordings** — LIVE.

The live-test pass must: launch real `cargo tauri dev`, click every control, watch `~/Library/Application Support/world.bravoh.vibemix/vibemix/logs/ui.log` (`[vmx:click]/[vmx:ipc>]/[vmx:ipc<]/[vmx:error]`), confirm each fires + gets a reply (no timeouts). Green vitest ≠ working app ([[feedback_verify_live_app_not_just_tests]]).

## Sequencing/discovery/export seams (verified signatures)
- `store.LibraryStore`: `search(qv,k)→[(id,score)]`, `search_centered(qv,k)`,
  `_backend.load_all()→(ids:list[str], vecs:np.ndarray(N,D))`.
  **Dim-agnostic** over the current 512D local CLAP store and future embedding
  variants.
- `state.harmonics`: `to_camelot(raw)->str|None` (never raises), `compatible(a,b)->bool` (False on None — both-known gate required), `is_clash`, `semitone_distance`. **Need to ADD `to_classical(camelot)->str|None`** (Camelot→classical for Rekordbox `Tonality`).
- `rekordbox.TrackEntry`: `track_id,title,artist,album,bpm:float(0.0 if missing),key:str("" if missing),duration_s:float,cues:tuple[CuePoint],filepath:str`. `CuePoint`: `name,type:str,start_s,end_s|None,number(-1 memory / 1..8 hot)`.
- `audio/features.py`: `snapshot_features→{rms,onsets_per_sec,sub_share,low/mid/high_share}`, `energy_curve`, `long_arc_curve`, `snapshot_wav`. `cue_detect.decode_to_mono(path,sr=16000)` = offline decode; `cue_detect.detect_cues(path,max_cues=8)`.
- `_cosine`: `l2_normalize`, `cosine_topk`, `EMBEDDING_DIM`.

## Current Shared Surfaces
- `library/clap_engine.py` / `embed_clap.py` — product local CLAP ONNX/512
  embedding path.
- `library/cue_types.py` — `CueAnchor{label,start_s,end_s,confidence,source}`
  contract for cue producers and consumers.
- Coordinate before broad rewrites to shared CLAP, cue, ingest, sequencer, or
  export seams while parallel sessions are active.

## Tests
Python: `tests/library/` (agent/toolset/store/search/similar/next_suggestion/rekordbox/cue_detect/centering...), `tests/runtime/` (session_loop/ws_bus/settings_apply/suggestion). Run: `uv run pytest -q tests/library/test_X.py`. UI vitest: `npm --prefix tauri/ui test -- <path>`.
