# CODEX_READY: Viber Library Freshness Status

Date: 2026-06-01
Author: Codex
Status: LAND packet, first slice only
Package: Package 5C - Viber Library Freshness Status

## Decision

LAND this slice as `fix(library): surface Viber freshness status`.

This is not the full watcher. It is the source-aware status layer the watcher
and stale-tool guard need before they can be honest. The app can now say
whether the library cache is missing, unreadable, source-missing, source-newer
than the cache, older than 30 days, or fresh.

## Files

- `src/vibemix/library/staleness.py`
- `src/vibemix/__main__.py`
- `tests/library/test_staleness.py`
- `tests/library/test_stats_cli.py`
- `tauri/src-tauri/src/library_cmds.rs`
- `tauri/ui/src/library/api.ts`
- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/api.test.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-viber-library-freshness-status.md`

## What Changed

- Added `LibraryFreshness` and `library_freshness_status()` beside the existing
  30-day staleness nudge.
- `library stats --json` now emits `library_freshness`,
  `library_freshness_status`, `library_stale`, `library_staleness_reason`, and
  `library_age_days`.
- The Tauri `library_stats` command preserves those fields from the Python
  sidecar JSON instead of dropping them.
- The library UI normalizer accepts the nested freshness object and the compact
  top-level fields, and the library stats label appends the current freshness
  status.
- Tests cover missing cache, fresh cache, source-newer-than-cache, source
  missing, the CLI JSON shape, Tauri/API normalization, and existing library UI
  callers.

## Evidence

Focused Python:

```text
uv run pytest -q tests/library/test_staleness.py tests/library/test_stats_cli.py
.............................                                            [100%]
29 passed in 0.39s
```

Python lint:

```text
uv run ruff check src/vibemix/library/staleness.py src/vibemix/__main__.py tests/library/test_staleness.py tests/library/test_stats_cli.py
All checks passed!
```

Library UI:

```text
npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts src/library/build.test.ts src/library/curate.test.ts
Test Files  4 passed (4)
Tests  102 passed (102)
```

Rust bridge:

```text
cargo check --manifest-path tauri/src-tauri/Cargo.toml
Finished `dev` profile [unoptimized + debuginfo] target(s) in 9.18s
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This package does not implement a long-running watcher.
- This package does not automatically re-ingest/re-embed changed libraries.
- This package by itself does not force Viber to refuse or qualify
  set-generation answers when freshness is stale. That guard is tracked
  separately in `CODEX_READY-viber-stale-setprep-tool-guard.md`.
- This package does not prove the packaged app UI badge live. It proves source,
  CLI JSON, Rust bridge compile, and UI normalization/render-facing tests.

## Next Required Package

Finish the real P0 watcher:

- Watch resolved Rekordbox `collection.xml` and selected music-folder/catalog
  sources.
- Debounce and mark library/set-prep state stale quickly.
- Offer or trigger bounded incremental ingest/re-embed.
- Surface a clear freshness badge/action in the app.
- Add source or packaged live proof by modifying the watched source and seeing
  the status change in the app.
