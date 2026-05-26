# Vibe Mix — UI / IPC Surface + Button Audit (wiring & live-test reference)

> From the full control-surface map (2026-05-26). Drives the sequencing/discovery/export WIRING
> (where to plug in) and the "every button works" LIVE-TEST pass. Line numbers are orientation —
> verify exact lines when editing (tree is changing under active sessions).

## Agent-engine entry points (where the set-prep flow plugs in)
- **CLI** `vibemix library curate <theme>` → `_cmd_library_curate` (`__main__.py:1894`) → `ViberAgent.curate()` / `.curate_interactive()`. Subparsers built at `__main__.py:1539` (`sp_curate` :1606). **Add `build-set` + `export-set` subparsers here.**
- **Tauri Library window** (`tauri/ui/src/library/` + `tauri/src-tauri/src/library_cmds.rs`): the GUI spawns `vibemix library …` as a subprocess and parses JSON stdout (does NOT instantiate ViberAgent in-proc). Curate GUI = one-shot. **Add a "Build a Set" mode here (curve picker → sequenced result → Export button).**
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
- `store.LibraryStore`: `search(qv,k)→[(id,score)]`, `search_centered(qv,k)`, `_backend.load_all()→(ids:list[str], vecs:np.ndarray(N,D))`. **Dim-agnostic** (D=1536 Gemini now, 512 after the staged CLAP swap — sequencer/discovery survive the swap free).
- `state.harmonics`: `to_camelot(raw)->str|None` (never raises), `compatible(a,b)->bool` (False on None — both-known gate required), `is_clash`, `semitone_distance`. **Need to ADD `to_classical(camelot)->str|None`** (Camelot→classical for Rekordbox `Tonality`).
- `rekordbox.TrackEntry`: `track_id,title,artist,album,bpm:float(0.0 if missing),key:str("" if missing),duration_s:float,cues:tuple[CuePoint],filepath:str`. `CuePoint`: `name,type:str,start_s,end_s|None,number(-1 memory / 1..8 hot)`.
- `audio/features.py`: `snapshot_features→{rms,onsets_per_sec,sub_share,low/mid/high_share}`, `energy_curve`, `long_arc_curve`, `snapshot_wav`. `cue_detect.decode_to_mono(path,sr=16000)` = offline decode; `cue_detect.detect_cues(path,max_cues=8)`.
- `_cosine`: `l2_normalize`, `cosine_topk`, `EMBEDDING_DIM`.

## Other sessions' STAGED (untracked, do not collide)
- `library/clap_engine.py` `ClapEngine` (on-device CLAP 512-d, staged-not-wired) — embedding swap.
- `library/cue_types.py` `CueAnchor{label,start_s,end_s,confidence,source}` (intro/build/breakdown/drop/outro; dj/auto) — the cue producer↔consumer contract. **Sequencer structural-mixability + cue-anchored export will consume this once committed; v1 = placeholder True.**
- metadata ingest research (Serato/Traktor/Rekordbox), modified `test_cue_detect.py`.
- Orphan-inventory test fails on their staged `ClapEngine`/`CueAnchor` — **NOT mine, do not refresh the baseline** (their commit owns it).

## Tests
Python: `tests/library/` (agent/toolset/store/search/similar/next_suggestion/rekordbox/cue_detect/centering…), `tests/runtime/` (session_loop/ws_bus/settings_apply/suggestion). New modules → new `tests/library/test_{energy,sequencer,discovery,export_rekordbox}.py`. Run: `PYTHONPATH=src python3 -m pytest tests/library/test_X.py -q`. UI vitest: `cd tauri/ui && npx vitest run <path>`.
