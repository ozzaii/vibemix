# CODEX_READY: Library Freshness Watcher Pulse

Date: 2026-06-01
Author: Codex
Status: LAND packet, watcher pulse slice
Package: Package 5E - Library Freshness Watcher Pulse

## Decision

LAND this slice as `fix(library): watch freshness during live sessions`.

This package makes the existing staleness banner usable beyond cold boot. It
adds a source-aware polling pulse that emits the already-defined
`ipc.library.staleness_nudge` whenever the library freshness signature changes
into a stale state during a live session.

## Files

- `src/vibemix/library/staleness.py`
- `src/vibemix/__main__.py`
- `src/vibemix/runtime/ws_bus.py`
- `tests/library/test_staleness.py`
- `tests/runtime/test_ws_bus.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-library-freshness-watcher-pulse.md`
- `.planning/packets/2026-06-01/CODEX_READY-library-staleness-replay-on-connect.md`

## What Changed

- Added `freshness_nudge_payload()` so boot nudges are source-aware, not only
  30-day-cache-age aware.
- Added async `watch_library_freshness()` with:
  - source-aware status checks,
  - duplicate suppression by freshness signature,
  - fresh-install skip,
  - snooze respect,
  - best-effort logging instead of killing the live runtime.
- Main runtime now starts the watcher after the library import/staleness IPC
  handlers are registered and retains the task in `_background_tasks`.
- The watcher reuses the existing closed IPC schema. Rich status details remain
  in `library stats`; the nudge is the "look now" pulse.
- Follow-up live proof found the boot nudge could fire before the Tauri bridge
  connected. `IpcRouterBus` now treats `ipc.library.staleness_nudge` as sticky
  status and replays the latest nudge to late clients.

## Evidence

Freshness/watch/status:

```text
uv run pytest -q tests/library/test_staleness.py tests/library/test_stats_cli.py tests/library/test_setprep_tools.py
57 passed in 0.64s
```

Lint:

```text
uv run ruff check src/vibemix/library/staleness.py src/vibemix/__main__.py tests/library/test_staleness.py
All checks passed!
```

Main smoke:

```text
uv run pytest -q tests/test_main_smoke.py
30 passed in 2.33s
```

Existing Settings/Library UI:

```text
npm --prefix tauri/ui test -- tests/settings/staleness-banner.spec.ts tests/settings/library-panel.spec.ts src/library/api.test.ts
Test Files  3 passed (3)
Tests  59 passed (59)
```

Replay-on-connect follow-up:

```text
uv run pytest -q tests/runtime/test_ws_bus.py tests/library/test_staleness.py tests/ipc/test_library_schemas.py tests/ui_bus/test_messages_schema.py
128 passed in 1.38s
```

```text
uv run ruff check src/vibemix/runtime/ws_bus.py src/vibemix/__main__.py tests/runtime/test_ws_bus.py
All checks passed!
```

Current-source runtime proof:

```text
VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix
ws_observe(seconds=4, type_filter="ipc.library.staleness_nudge")
count=1
payload.reason=source_newer_than_cache
payload.source_path=tests/library/fixtures/synthetic_collection.xml
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This is a watcher pulse, not automatic re-ingest.
- It does not change the IPC schema, so the banner copy is still generic.
- Current-source websocket delivery is proven. Packaged proof needs a rebuild
  because the existing signed DMG predates the replay fix.
- It does not handle all selected music folders as independent roots unless the
  current `library.pkl` source path is that folder/cache source.

## Next Required Package

Add the refresh action and live proof:

- Expose a clear "refresh library" action from stale status.
- Run bounded incremental ingest/re-embed or the existing importer for the
  stale source.
- Preserve live co-host audio by keeping ingest off the hot path.
- Verify with a changed `collection.xml` or folder cache that the app nudges,
  blocks Viber set-prep, refreshes, and then unblocks Viber.
