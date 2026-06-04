# MAP — Viber + the local library/models the engines feed on

**Scope:** Viber (Codex-backed set-prep agent), library vibe-search (CLAP), auto-cue
(CUE-DETR), next-suggestion (the pill), the local model install/first-run state, and the
"Live agent log" / `tool_trace` UI surface.
**Method:** read source + codegraph + on-disk artifact inspection on Kaan's real machine.
Verified against running state, not memory. READ-ONLY.
**Date:** 2026-06-04 · branch `ux-redesign-impeccable`

---

## TL;DR verdict

The Viber/library piece is the **most-finished, least-dark** engine in the product. Unlike
Sven (live brain orphaned from intelligence) and Learn (built-but-mute), Viber's wiring is
**real and end-to-end**: CLI → Rust command → live `[viber-tool]` tape → UI inline log, with
a 273-track CLAP-embedded library actually on disk and every local model (CLAP, CUE-DETR,
Chatterbox voice ref) present. The `tool_trace` is **NOT faked** — it is parsed from real
stderr lines the Codex MCP run emits.

The gaps are narrower and more specific than the other engines:
1. **Auto-cue (CUE-DETR) is offline-only** — wired into ingest/embed, NOT live in-session.
2. **Viber chat/curate/build depends on `codex login` + binary** — a hard external
   precondition the autonomous QA loop must satisfy or stub.
3. **next-suggestion (the pill) IS wired** (corrects a stale "0 callers" reading) but its
   live-quality is unproven by-ear; it is the one piece that touches Sven's live path.

**This piece is NOT a blocker for tonight's autonomous QA loop** — the library is populated,
models installed, and the keyless deterministic path (`auto_crate`) needs no login. See the
blocker analysis at the bottom.

---

## 1. What is LIVE vs DARK — component matrix

| Component | State | Evidence |
|---|---|---|
| **CLAP vibe-search** (text→track, track→track) | **LIVE + real data** | 273 tracks embedded (`library-clap.db::vec_library_rowids`=273); CLAP onnx weights present (282M audio + 502M text, `~/.cache/vibemix/clap-onnx/onnx/`); `clap_engine.py:1-56` wired as product path; Rust `library_search`/`library_similar` (`library_cmds.rs:665,684`) |
| **next-suggestion / the pill** | **WIRED, by-ear unproven** | `SuggestionService.compute` → `next_suggestion()` (`suggestion.py:966`); merged onto mascot frame (`ws_bus.py:1324`); choose/feedback actions handled (`ws_bus.py:1079,1098`). NOT "0 callers" — codegraph misses the indirect call. |
| **Viber chat** (one-turn) | **LIVE (needs codex login)** | `library_chat` Rust cmd (`library_cmds.rs:1074`) → CLI `library chat --backend codex` → `codex_curate.py:4410` |
| **Viber curate** (theme→playlist) | **LIVE (needs codex login)** | `library_curate` (`library_cmds.rs:858`) → `codex_curate.run_curate` (`codex_curate.py:837`) |
| **Viber build-set** (brief→sequenced set→Rekordbox) | **LIVE (needs codex login)** | `library_build_set` (`library_cmds.rs:893`) → `codex_curate.py:1429` |
| **auto_crate** (keyless deterministic set builder) | **LIVE, no login needed** | `library_auto_crate` (`library_cmds.rs:935`); deterministic Python, passes NO `--backend` (`library_cmds.rs:931-933`); `auto_crate.build_auto_crate` (`auto_crate.py:76`) |
| **auto-cue / CUE-DETR** | **OFFLINE-ONLY (ingest/embed time)** | model present (167M `cue-detr-onnx/cuedetr.fp32.onnx`); `cue_engine.detect_cues_auto` (`cue_engine.py:164`) called ONLY from `ingest.py:306,335`, `embed.py:499` — NOT from `__main__` live loop (`__main__.py:7660` is `model_status`, a status check) |
| **cue_folder / land_cues** (cue export surfaces) | **LIVE (CLI + Rust)** | `library_cue_folder` (`library_cmds.rs:993`), `library_land_cues` (`library_cmds.rs:1041`); CLI `_cmd_library_land_cues` (`__main__.py:6909`) |
| **Live "Viber tool tape"** (`[viber-tool]`) | **LIVE, real, not faked** | full chain verified — see §3 |
| **Telegram mobile Viber** | **LIVE logic, opt-in dep** | `telegram_bridge.py:214` long-poll loop; lazy `python-telegram-bot`; `build_bridge_from_env` (`telegram_bridge.py:248`); needs `VIBEMIX_TELEGRAM_TOKEN` + allow-list |
| **web_search / fetch_url** | **WIRED, needs TAVILY key** | MCP tools (`mcp_server.py:400,408`); `web_research.py`; honest-fail without `TAVILY_API_KEY` |
| **DJ-knowledge RAG** | **LIVE, corpus present** | `retrieve_dj_knowledge` (`mcp_server.py:436`); `~/.cache/vibemix/knowledge/` exists |

---

## 2. The grounding gate is REAL (Cardinal Invariant #2 at the tool boundary)

This is the load-bearing anti-slop mechanism and it is **enforced in code, not prompt**:

- The MCP server carries **no system prompt of its own** (`mcp_server.py:37-44`) — it only
  exposes grounded tools; grounding lives at the toolset boundary, so the model cannot
  smuggle in an invented track regardless of reasoning.
- Every write/export tool re-validates that each `track_id` came from a prior
  `search_vibe`/`discover_pool` **this run** via the per-run `seen` set
  (`mcp_server.py:278-283` `create_playlist`, `:368-385` `export_set`).
- The per-run `LibraryToolset` lives exactly one `codex exec` run (`mcp_server.py:16-20`) —
  correct grounding scope.
- `next_suggestion` enforces the same: only `track_id`s present in BOTH store AND library
  surface; `library.lookup_by_id(tid) is None → skip` (`next_suggestion.py:147-148`), honest
  `None` when nothing qualifies (`next_suggestion.py:195-196`). The pill **can never show an
  invented track**.

This is genuinely stronger grounding than Sven's live path — it is structurally impossible
to hallucinate a track here.

---

## 3. Does the UI show real tool_trace, or is it faked? — REAL.

Full chain, verified end-to-end (this is the one place the docs and reality agree):

1. **Python toolset emits** one JSONL record per tool call to a side-channel file:
   `LibraryToolset._emit_tool_event` (`toolset.py:1735`), env-gated by
   `VIBEMIX_TOOL_EVENTS_FILE` (`toolset.py:1747`), called from `dispatch()` (`toolset.py:1845`)
   AND from the FastMCP direct-call path via `_ToolTapProxy` (`mcp_server.py:112-143`) —
   because FastMCP wrappers bypass `dispatch()`, the proxy is the chokepoint.
2. **codex_curate tails** that JSONL on a daemon thread (`_start_tool_tape` →
   `_drain_tool_tape`, `codex_curate.py:543,727`) and re-prints each as a
   `[viber-tool] <name> <ok|err> <summary>` line **to STDERR** (`codex_curate.py:570`).
   The events-file path is passed to the MCP child as `--vibemix-tool-events <path>`
   (`codex_curate.py:927`), promoted to env inside the child (`mcp_server.py:452-468`).
3. **Rust bridge parses** each stderr line: `parse_viber_tool_line` (`library_cmds.rs:424`)
   strips `[viber-tool] ` and emits a Tauri event `library://viber-tool`
   (`library_cmds.rs:438-439`).
4. **UI subscribes**: `onViberTool` (`api.ts:2965`) → `index.ts:2666` → `appendInlineToolRow`
   (`index.ts:1225`) into the live "Live agent log" (`index.ts:1211`). The final `tool_trace`
   array on the result is also rendered (`index.ts:1697-1718`), normalized + schema-validated
   (`api.ts:2063`, throws on malformed `ok` field — `api.test.ts:252`).

**Verdict: the agentic tape is genuinely live, not mocked.** The test-file `tool_trace: []`
fixtures are unit-test stubs, not the product path. Caveat: the live stream depends on the
two-process-boundary env propagation (parent → Codex CLI → MCP child); `mcp_server.py:56-76`
is an explicit boot-probe that logs whether the side-channel path crossed — if Codex CLI
strips args/env, the tape silently no-ops (best-effort by contract, `toolset.py:1766`). For
the autonomous QA loop this means: **screenshot the inline tool log to confirm the tape, do
not assume it.**

---

## 4. State of the local models — install + first-run

On-disk inspection of `~/.cache/vibemix/` (Kaan's real machine, 2026-06-04):

| Model | Present? | Size / detail |
|---|---|---|
| **CLAP ONNX** (search/embed) | YES | `clap-onnx/onnx/audio_model.onnx` 282M + `text_model.onnx` 502M + tokenizer/vocab/merges |
| **CUE-DETR ONNX** (auto-cue) | YES | `cue-detr-onnx/cuedetr.fp32.onnx` 167M |
| **Chatterbox voice ref** (live co-host voice) | YES | `cohost_voice_ref.wav` 384K (+ `learn_voice_ref.wav`, `robot_voice_ref.wav`) |
| **MOSS-TTS-Nano** (legacy local TTS) | dir present | `moss-tts-onnx/` |
| **GiantSteps key model** | YES | `giantsteps-key/` |
| **genre prototypes** | YES | `genre_prototypes.npy` + meta |
| **Embedded library** | YES | `library-clap.db` 2.2M (**273 tracks**), `section_vectors.db` (104 sections), `embeddings.db` (646 embed-cache rows), `library.pkl` 32K |

**First-run / installer path is real:** `model_assets.py` is a genuine downloader —
`_download_file` (`:155`), `_download_url_to_file` (`:255`) pull pinned files from
HuggingFace (`_CLAP_BASE_URL`, `model_assets.py:25`) with sha256 verify (`_file_ok`, `:136`)
and `ModelProgress` callbacks. CLI `library models --install clap|cue|all` and Rust
`library_models` (`library_cmds.rs:1274`) expose it. Startup payload reports per-model
`installed/installable/path/missing` to the UI (`__main__.py:7673-7690`), so **model status
IS surfaced** at startup (CLAP/Chatterbox/CUE).

> Note: there is a `clap-onnx.invalid -> /tmp/xenova_models` dangling symlink in the cache.
> Harmless leftover (real dir is `clap-onnx/`), but worth a cleanup; could confuse a naive
> path probe.

**Codex (the Viber backend) install state:**
- Binary present: `/opt/homebrew/bin/codex` → `@openai/codex/bin/codex.js`.
- `find_codex` (`codex_curate.py:391`) scans `VIBEMIX_CODEX_BIN`, `which codex`, common
  unix candidates, nvm globs — Finder-launch-safe.
- The desktop bridge **auto-sets `VIBEMIX_CODEX_ALLOW_SHELL=1`** when a codex-backend
  subcommand runs (`library_cmds.rs:133-134`) — the user does NOT need to set env vars.
- **HARD external precondition:** `codex login` (auth lives in `~/.codex`, used by
  `codex exec`). `~/.codex/` exists on this machine. Without a valid login, curate/chat/build
  fail with a structured `codex_mcp_blocked` / actionable error (NOT a crash) — surfaced to
  the UI honestly (`library_cmds.rs:890` "renders the real error, never fake data").
- Codex's own upstream regression (openai/codex#16685) forces
  `--dangerously-bypass-approvals-and-sandbox` for MCP tool calls (`codex_curate.py:486-502`)
  — a known, documented, handled landmine.

---

## 5. REAL vs ASPIRATIONAL — honest verdicts

- **REAL:** CLAP search, similar, next-suggestion engine, the grounding gate, the live tool
  tape, auto_crate (keyless deterministic), cue_folder/land_cues export, model installer,
  273-track populated library. These are wired and have data behind them.
- **REAL but gated by external auth:** Viber chat/curate/build-set (needs `codex login`),
  web_search (needs `TAVILY_API_KEY`), Telegram (needs token + allow-list).
- **REAL but offline-only (aspirational as a LIVE feature):** auto-cue / CUE-DETR runs at
  ingest/embed time, NOT in the live set. The "host live cue detection" (WIRE-THE-GOLD B4)
  is genuinely not built into the session loop.
- **UNPROVEN BY EAR (the soul gap that touches Sven):** next-suggestion's *quality* — does
  the pill suggest a track that feels right, on time? The engine is grounded and rich
  (10-signal transition scorer, section/cue-aware, taste-weighted), but no automated judge
  confirms the *musical* quality of its picks. This is the highest-leverage place this piece
  intersects the "real DJ friend" bar.
- **NOT FAKED (correcting a possible suspicion):** the `tool_trace` UI is not a mock; the
  `[]` fixtures are test-only.

---

## 6. Highest-leverage work — what must be built/wired and where

Ranked for the autonomous-QA-loop mission AND general ship value:

1. **[QA-loop enabler] Make Viber/library deterministically driveable headless.**
   The QA harness should exercise `auto_crate` (keyless, no login) as the proof-of-life for
   the whole library stack — `python -m vibemix library auto-crate "<theme>" --json`
   (`__main__.py:2938`). It needs NO Codex login, returns structured JSON, and transitively
   proves CLAP search + sequencer + export. Add a harness assertion on the JSON shape +
   grounded rationale (`auto_crate.py:350 _grounded_rationale`).
   *Where:* QA harness invokes the CLI directly; no code change in library/.

2. **[QA-loop enabler] Capture + judge the live tool tape.**
   Set `VIBEMIX_TOOL_EVENTS_FILE` to a known path before a curate/chat run, then read the
   JSONL directly (skip the stderr round-trip) to verify the agent actually called grounded
   tools (`search_vibe` before `create_playlist`). This is the cheapest, most robust
   observability hook for Viber. *Where:* `toolset.py:1747` already honors the env var.

3. **[soul] Automated judge for next-suggestion quality.**
   Feed the recorded set's track sequence as seeds, call `SuggestionService.compute` per
   transition, and judge the suggestion (harmonic compat, BPM window, energy arc, on-time
   cue) against the actual next track the recorded DJ played. This is the ONE library piece
   that can fail the "real DJ friend" bar. *Where:* `suggestion.py:925 compute` + the
   recorded-set capture.

4. **[ship] Live in-session auto-cue (WIRE-THE-GOLD B4).**
   CUE-DETR is offline-only; wiring `detect_cues_auto` into the live session so the host gets
   real cue anchors during a set is a genuine build (model already present). *Where:* the
   live loop in `__main__.py`, mirroring the ingest path `ingest.py:306`.

5. **[hygiene] Remove the `clap-onnx.invalid -> /tmp/xenova_models` dangling symlink** and
   add a doctor check (`doctor.py` exists, `library doctor`). Low effort, removes a confusing
   path probe failure mode.

6. **[robustness] Surface a clear "Viber needs codex login" UX state.** The error is honest
   in the data (`codex_mcp_blocked`) but the UX legibility of that state was not confirmed in
   this map — worth verifying the Library window renders it as an actionable setup card, not
   a raw error string.

---

## 7. Input for the AI/engines lane (handoff)

- **The library stack is the safest engine to lean on for autonomous proof-of-life** — it has
  real data (273 tracks), all models installed, and a keyless deterministic entry
  (`auto_crate`) that needs no external auth.
- **The grounding gate here is the reference implementation** of Invariant #2 done right
  (enforced at the tool boundary, not the prompt). When hardening Sven's grounding, this is
  the pattern to copy: a per-run seen-set + write-time re-validation, structurally
  un-hallucinatable.
- **The live tool tape (`VIBEMIX_TOOL_EVENTS_FILE` JSONL) is a ready-made observability
  surface** — point it at a file and you get a machine-readable record of every grounded tool
  the agent fired. Reuse it for the QA harness instead of scraping stderr.
- **Two external preconditions gate the *agentic* (Codex) Viber path:** `codex login`
  (present on this machine) and the upstream sandbox-bypass (handled). The QA loop should
  either (a) confirm login is valid up front, or (b) restrict autonomous Viber testing to the
  keyless `auto_crate` / CLAP-search paths and treat curate/chat as login-gated.
- **next-suggestion is the single library piece on Sven's live critical path** — its musical
  quality is the only un-judged "soul" risk in this engine. Everything else is grounded and
  deterministic.

---

## File:line evidence index (quick reference)

- CLAP engine product path: `src/vibemix/library/clap_engine.py:1-56,77-84`
- next-suggestion engine: `src/vibemix/library/next_suggestion.py:100-228` (grounding `:147-148,195-196`)
- SuggestionService live call: `src/vibemix/runtime/suggestion.py:966`; frame merge `src/vibemix/runtime/ws_bus.py:1324`
- MCP grounded tools + no-prompt: `src/vibemix/library/mcp_server.py:37-44,163-449`
- tool-tape emit: `src/vibemix/library/toolset.py:1735-1768,1845`; proxy `mcp_server.py:112-143`
- tool-tape drain→stderr: `src/vibemix/library/codex_curate.py:543-570,727-741,927`
- Rust tape parse+emit: `tauri/src-tauri/src/library_cmds.rs:424-443`
- UI tape subscribe+render: `tauri/ui/src/library/index.ts:1225,2666`; `api.ts:2965`; final trace render `index.ts:1697-1718`
- Rust library commands: `tauri/src-tauri/src/library_cmds.rs:665,684,858,893,935,993,1041,1074,1128,1274,1453`
- codex backend auto-allow-shell: `tauri/src-tauri/src/library_cmds.rs:133-134,140-153`
- codex locate: `src/vibemix/library/codex_curate.py:391-418`; sandbox bypass `:486-502`
- auto-cue offline-only: `cue_engine.py:164` called from `ingest.py:306,335`, `embed.py:499`; NOT live in `__main__.py`
- model installer: `src/vibemix/library/model_assets.py:155,255,136`; startup status `src/vibemix/__main__.py:7660-7690`
- on-disk: 273 tracks (`library-clap.db::vec_library_rowids`), CLAP 282M+502M, CUE-DETR 167M, codex `/opt/homebrew/bin/codex`
