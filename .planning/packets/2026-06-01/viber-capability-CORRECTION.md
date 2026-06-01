# CORRECTION — Viber Capability Packet (supersedes its §6/§8/§9 #1 claim)

> **Date:** 2026-06-01 · **Author:** Claude · **Status:** source-verified this session (read-only)
> **Corrects:** `recovered/wf_ba32cbda-6f2__codex-ready-viber-capability-exploration-product-gap-ma.md`
> (the recovered Viber packet) — specifically its **#1 P0 blocker**.
> **Trigger:** Codex re-verified the source and flagged "Viber product is entirely unplugged" as too strong. Confirmed: it is wrong.

## The error

The packet's top finding — **"the entire Viber/Crate IPC backend is orphaned — every Crate
control is dead in the app"** (§6 line 189, §8 blocker #1, §12) — is **FALSE**.

**Root cause of the audit miss:** the ui-surface lane fixated on the `ipc.library.*` **ws-bus**
message types + a `LibraryBridge` Python class, found that path dead, and concluded the whole
Crate was dead. It never checked that the UI reaches the backend through a **different
mechanism**: direct **Tauri `invoke()` commands**, not the ws-bus. (The agent read `api.ts:1-211`
but the actual `invoke()` calls are at `api.ts:2354+` — a partial-file read inverted the verdict.)

## The verified truth (file:line, this session)

The Crate's primary path **IS wired end-to-end** via Tauri commands → subprocess → renderers:

| Leg | Evidence |
|---|---|
| 9 `library_*` commands registered in the Tauri `invoke_handler` | `tauri/src-tauri/src/main.rs:105-113` (`library_search/similar/curate/build_set/chat/stats/models/embed_folder`, `open_library_window`) |
| Each command spawns `vibemix library …` subprocess | `tauri/src-tauri/src/library_cmds.rs` (`#[tauri::command]` at :503/:522/:670/:705/:746/:799/:913/:1092) |
| The UI actually invokes all of them | `tauri/ui/src/library/api.ts:2354-2476` (`invoke("library_search"…)` … `invoke("library_embed_folder"…)`) |
| The UI renders the results | `tauri/ui/src/library/index.ts`: `renderBuildSet` :498, `renderChatSide` :1259, `chatArtifactCard` :1316, `isChatClarification` :1312, `renderChatError` :1552 |
| Live Viber tool-trace tape **is rendered** (packet wrongly called it DEAD) | `index.ts` `onViberTool` :2065 → `appendLiveToolRow` :1169; `LibraryViberToolEvent` api.ts:2566; `tool_trace` parse api.ts:1864 |
| Sven→Viber `liveContext` grounding is threaded into chat | `library_cmds.rs:746-` (`library_chat(… live_context …)` serialized into the subprocess args) |

**Corrected status:** the Crate (search / similar / curate / build-set / chat / stats /
embed-folder) is **WIRED in the app** via Tauri invoke. NOT "unplugged."
**Caveat (honest):** this verifies the *wire exists* (invoke → command → subprocess → renderer).
It does **not** verify a live run returns correct, grounded data — that needs a `drive-vibemix`
pass. So: **WIRED, live-correctness UNVERIFIED.** Do not over-correct to "it all works live."

## Reclassify the packet's #1 "next package"

The packet's #1 next package — **"Resurrect LibraryBridge as a satellite (P0)"** — is **WRONG**
and would build a redundant second path. The reality:

- `src/vibemix/runtime/library_bridge.py` — **does not exist** (`ls` → no such file).
- `ipc.library.*` ws types in the schema: **5** (`messages.schema.json`), with **zero UI
  call-sites** (`rg ipc.library. tauri/ui/src/library` → empty).
- → The `ipc.library.*` ws path is **dead vestigial code**. Correct action is **DELETE the 5
  schema types** (cleanup), **not resurrect a bridge**. The live path is Tauri invoke and works.

## What in the packet STILL STANDS (re-verified this session)

These findings are unaffected by the correction — keep them:

- **No library/file watcher** (P0 freshness): `rg watchfiles|watchdog|inotify|FSEvents|on_modified
  src/vibemix/library src/vibemix/runtime` → none (only `parent_watchdog.py` = process ppid watch,
  `midi/watcher.py` = MIDI hot-plug). Stale index → recs from an out-of-date catalog. **STANDS.**
- **No cue-export GUI**: `rg library_cue|cue_folder tauri/src-tauri/src` → zero. The cue "moat"
  is CLI-only (`library cue <folder>`). **STANDS** (now the true highest-value UI gap, since the
  rest of the Crate is already wired).
- **No per-result freshness/staleness badge** on Viber results. **STANDS.**
- **§5 Viber↔Sven boundary** — the whole analysis was sound: Viber's `library_chat` path has zero
  TTS/`.say`/transcript/ws-8765 references (grep=0) → **Viber can never speak; no P0 leak.** Sven's
  speech keeps the 4-gate in-loop guard. **STANDS.**
- **The creative superpowers (§10) and goldmine (§11)** — sound; substrate-grounded.

## Corrected priority order (next packages)

1. **Cue-export IPC + GUI surface** (was packet #4) — now the #1 real UI gap; the rest of the Crate is wired.
2. **Library watcher** (P0 freshness) — unchanged.
3. **Per-pick proof chips + freshness badge** — the tool-trace tape already renders; extend it with grounding facts.
4. **`export_cues` seen-set grounding fix (or drop)** — unchanged (Invariant #2 hole at toolset.py:987-1007).
5. **DELETE the dead `ipc.library.*` ws types + remove the LibraryBridge plan** — cleanup, not a build.

— Read-only correction. No product code changed. No staging, no commit.
