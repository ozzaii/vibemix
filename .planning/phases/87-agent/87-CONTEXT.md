# Phase 87: AGENT — Set-Prep Co-Host Flow + Tool Integration - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning (executes AFTER the 4 engine modules land)
**Mode:** Research-driven (integration pass — wires the pure-compute engines into the agent surface)

<domain>
## Phase Boundary

Wire the four pure-compute engines (energy/discovery/sequencer/export, built in 83-86) into the agent tool surface and ship the set-prep co-host flow. This is the SINGLE integration pass that touches the shared tool files (deliberately serialized — the engine modules are disjoint, the TOOL wiring is not).

IN:
- 4 new tools in `LibraryToolset` (single tool core → inherited by Gemini + Codex/MCP + Telegram): `get_track_energy` (ENERGY-03), `discover_pool` (DISCOVER-03), `sequence_set` (SEQUENCE-03), `export_set` (EXPORT-02). Grounding seen-set gate unchanged — every track_id flows through `seen`.
- Gemini declarations in `agent.py::_tool_declarations` + MCP wrappers in `mcp_server.py::build_server` for the 4 tools.
- A set-prep agent flow: `ViberAgent.build_set(brief)` — discover → sequence → explain each transition (1-2 sentences, key/BPM/energy/vibe) → optional export. Layered on the existing matrix/lens persona seam (no voice drift), on the existing bounded no-hang harness (`MAX_TOOL_ITERATIONS`, per-call + per-tool timeouts, handlers return errors). New set-prep system instruction variant.
- CLI: `vibemix library build-set "<brief>" [--curve PRESET] [--export rekordbox] [--name N]` and `vibemix library export-set <set.json> --out <file.xml>` in `__main__.py`.

OUT: the Tauri "Build a Set" GUI (Phase 88, DEFERRED to ride the concurrent "Deck Speaks" rebuild). XGBoost, public catalog, Serato/Engine export.
</domain>

<decisions>
## Implementation Decisions (LOCKED)
- **Tool wiring is the ONLY place the shared files (toolset.py / agent.py / mcp_server.py) change** — done in one pass to avoid sequential churn. The 4 engine modules (83-86) never touch these.
- **Grounding gate unchanged (Invariant #2):** `discover_pool`/`sequence_set` results add their ids to `self.seen`; `sequence_set` only accepts ids already in `seen`; `export_set` re-validates against the live library (mirror `create_playlist`'s two-gate pattern). The model can never sequence/export an invented track.
- **Honest-null + no-hang preserved:** new handlers RETURN error dicts (never raise), run under the existing per-tool timeout in `dispatch`.
- **`get_track_energy`** = deterministic fact (calls `energy.score_energy`, cached), honest-null on no audio.
- **`discover_pool`** = calls `discovery.discover_pool(store, library, embedder, ...)`; returns pool items + records ids in seen.
- **`sequence_set`** = builds PoolTracks from seen ids (reads vectors from store + features from library + energy from the cache), calls `sequencer.sequence_set`, returns 3-5 candidate orderings with honest fit labels + relaxed-transition tags.
- **`export_set`** = calls `export_rekordbox.export_set` after library re-validation; returns the written path.
- **Set-prep flow** reuses `_run_loop`; new system-instruction `build_curator_instruction(lens)` + a SET-PREP rules block (discover → sequence → explain why → offer export; never invent; keys/bpm/energy from tools). The "explain why each transition works" is the spec's competitive delta (mentor not black-box).
- The Codex/MCP backend inherits the tools by adding `@mcp.tool()` wrappers that delegate to the shared toolset (identical grounding).
</decisions>

<code_context>
## Existing Code Insights (verified seams)
- `LibraryToolset.dispatch` (toolset.py:210) routes by a `handlers` dict + runs each under a 30s `ThreadPoolExecutor` timeout. ADD the 4 new handlers here. `self.seen`, `self._store`, `self._library`, `self._embedder` available.
- `agent.py::_tool_declarations(interactive)` (agent.py:219) builds `types.FunctionDeclaration` list. ADD the 4 set-prep tools (gated to a `set_prep=True` variant so plain curate keeps its 3-tool surface). `ViberAgent._run_loop` already dispatches via `self._dispatch` (→ toolset). Add `build_set(brief)` calling `_run_loop` with a set-prep system instruction.
- `mcp_server.py::build_server` (mcp_server.py:110) — add 4 `@mcp.tool()` wrappers delegating to `toolset.*`.
- CLI: subparsers built in `__main__.py:1539` (`sp_curate` :1606); handlers `_cmd_library_*`. ADD `sp_build_set` + `sp_export_set` + `_cmd_library_build_set` + `_cmd_library_export_set`.
- Schema/IPC: NOT needed (CLI + agent only; the GUI is Phase 88). No `messages.schema.json` edit → no `codegen:ipc` needed this phase.
</code_context>

<specifics>
## Specific Ideas
- `library build-set` prints the chosen sequence slot-by-slot (slot · title — artist · key · bpm · energy) + the per-transition why + the playlist/export path. JSON mode (`--json`) for the GUI to consume later.
- Honest green: agent tests use a fake genai client (mirror tests/library/test_agent.py); the engine calls inside the tools are real (offline). Add tests/library/test_toolset_setprep.py + extend test_agent.py for build_set.
- Reuse the bounded-harness no-hang tests pattern from test_agent.py.
</specifics>

<deferred>
## Deferred Ideas
- Tauri "Build a Set" GUI (Phase 88, gated on the "Deck Speaks" rebuild).
- Live in-session "build the rest of tonight from the now-playing track" (seed the flow from the live deck vector).
- Telegram set-prep surface (tools inherited free; surface UX later).
</deferred>
