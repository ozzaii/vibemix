---
phase: 28-library-intelligence-v1
plan: 03
subsystem: library
tags: [vibe-search, query-cache, cli, snapshot-keyed-cache, json-output]

requires:
  - phase: 28-01
    provides: LibraryEmbedder.embed_query()
  - phase: 28-02
    provides: LibraryStore.search() + snapshot_hash()
  - phase: 25
    provides: RekordboxLibrary for track_id → title/artist resolution

provides:
  - vibe_search(embedder, store, library, query, k) → (results, cache_hit)
  - 24h library-snapshot-keyed query cache
  - VibeSearchResult dataclass
  - `vibemix library search <query>` CLI subcommand
  - _build_library_subparsers helper (Plans 05 + 08 will register their own subcommands here)

affects: [28-04, 28-05, 28-08]

tech-stack:
  added: []
  patterns:
    - "library-snapshot-keyed cache (re-import auto-invalidates)"
    - "Early-exit CLI subcommand dispatch — zero impact on live-session boot"

key-files:
  created:
    - src/vibemix/library/search.py
    - tests/library/test_search.py
    - tests/scripts/test_cli_library_search.py
  modified:
    - src/vibemix/library/__init__.py
    - src/vibemix/__main__.py
    - pyproject.toml (cli mark)

key-decisions:
  - "QUERY_CACHE_TTL = 86400 (24h) per CONTEXT decision."
  - "Cache key = sha256(query || snapshot_hash) — re-import invalidates without manual cleanup."
  - "Confidence clamped to [0, 1] + rounded to 4 decimals — IEEE-754 quirks survived."
  - "library subcommand dispatched BEFORE _parse_args so legacy flags untouched."
  - "JSON output by default; errors are JSON-formatted to stderr."

patterns-established:
  - "Pattern: every Phase 28 plan that adds a CLI subcommand uses _build_library_subparsers."
  - "Pattern: CLI commands accept proxy JWT via VIBEMIX_PROXY_JWT env var (developer/Kaan-side path)."
---

# Plan 28-03 — Vibe-Search CLI

Status: complete. 13/13 tests pass.

## What landed

### `src/vibemix/library/search.py`
- `vibe_search()` returns `(list[VibeSearchResult], cache_hit: bool)`.
- Cache key: `sha256(query || library_snapshot_hash)`. Co-located in `embeddings.db`.
- 24h TTL. Empty library short-circuits (no embed call).

### CLI (`__main__.py`)
- `vibemix library {search,similar,budget}` subcommand group.
- Dispatched BEFORE `_parse_args` so the legacy `--wizard` / `--session` / `--debrief` flag layer is untouched.
- `vibemix library search "driving acid techno"` → JSON to stdout.
- `_build_library_subparsers` helper makes Plans 05/08 plug-in trivially.

## Test posture

- `pytest tests/library/test_search.py` → 8 pass in 0.4s
- `pytest tests/scripts/test_cli_library_search.py` → 5 pass in 9s (subprocess startup overhead)

## P48 preservation

`grep -c "register_library" src/vibemix/__main__.py` → 2 ✓

## Deviations

- None. Plan executed as written.
