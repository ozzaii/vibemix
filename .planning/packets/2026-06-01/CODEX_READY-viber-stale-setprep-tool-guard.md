# CODEX_READY: Viber Stale Set-Prep Tool Guard

Date: 2026-06-01
Author: Codex
Status: LAND packet, guard slice
Package: Package 5D - Viber Stale Set-Prep Tool Guard

## Decision

LAND this slice as `fix(library): block stale Viber set-prep tools`.

This is the fail-closed behavior that sits on top of the freshness status
slice. If the local library/index state is not fresh, the product MCP path now
blocks Viber's local-library tools before they can search, sequence, export, or
cite stale catalog facts.

## Files

- `src/vibemix/library/toolset.py`
- `src/vibemix/library/mcp_server.py`
- `tests/library/test_setprep_tools.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-viber-stale-setprep-tool-guard.md`

## What Changed

- `LibraryToolset` accepts an optional `freshness_provider`.
- Product MCP construction passes `library_freshness_status` into the toolset.
- The MCP tool proxy checks `_freshness_guard_for_tool()` before direct handler
  calls, which is the path Codex/Viber actually uses.
- `dispatch()` also checks the same guard for direct dispatch callers.
- Guarded local-library tools return a deterministic error:
  `blocked_by: library_freshness` plus the exact freshness payload.
- Tests cover stale blocking, fresh pass-through, and the MCP direct-handler
  proxy path.

## Guarded Tools

- `search_vibe`
- `get_track_features`
- `get_track_sections`
- `transition_slate`
- `compile_musical_context`
- `smart_hot_cues`
- `create_playlist`
- `get_track_energy`
- `discover_pool`
- `sequence_set`
- `export_set`
- `export_smart_cues`
- `quote_moment`

External knowledge tools and clarification stay available:
`web_search`, `fetch_url`, `retrieve_dj_knowledge`, and
`request_clarification`.

## Evidence

Set-prep/freshness:

```text
uv run pytest -q tests/library/test_setprep_tools.py tests/library/test_staleness.py tests/library/test_stats_cli.py
57 passed in 0.83s
```

MCP/toolset surfaces:

```text
uv run pytest -q tests/library/test_toolset.py tests/library/test_mcp_server_clarification.py tests/library/test_clap_runtime_errors.py
35 passed in 0.66s
```

Viber/codex-curate guard neighborhood:

```text
uv run pytest -q tests/library/test_curate_unify.py tests/library/test_codex_curate.py -k 'library_request or non_live_outcome or live_context or chat_with_codex'
37 passed, 58 deselected in 0.23s
```

Lint:

```text
uv run ruff check src/vibemix/library/toolset.py src/vibemix/library/mcp_server.py src/vibemix/library/staleness.py tests/library/test_setprep_tools.py tests/library/test_staleness.py tests/library/test_stats_cli.py
All checks passed!
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This does not implement a long-running watcher.
- This does not start a re-ingest/re-embed job.
- This does not prove the installed Codex binary loop against a stale fixture.
- This does not block external web/DJ-knowledge lookups; the guard is for local
  library/set-prep facts only.

## Next Required Package

Finish the watcher/action surface:

- Watch resolved Rekordbox XML and music-folder sources.
- Debounce source changes into the freshness status.
- Surface a visible stale badge/action in the app.
- Offer or run bounded incremental ingest/re-embed.
- Add a source or packaged live proof where changing the watched source blocks
  Viber set-prep until the library is refreshed.
