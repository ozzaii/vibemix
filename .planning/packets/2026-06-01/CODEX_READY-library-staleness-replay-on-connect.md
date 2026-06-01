# CODEX_READY: Library Staleness Replay On Connect

Date: 2026-06-01
Author: Codex
Status: LAND packet, live replay fix slice
Package: Package 5E/5F follow-up - library staleness nudge delivery

## Decision

LAND this slice with the library freshness packages.

The source and packaged sidecar correctly detected a stale library cache, but a
live proof showed the nudge was emitted before the Tauri bridge connected. Since
`ipc.library.staleness_nudge` represents current freshness status rather than a
one-shot event, the live bus now retains the latest nudge and replays it to late
clients on connect.

## Files

- `src/vibemix/runtime/ws_bus.py`
- `src/vibemix/__main__.py`
- `tests/runtime/test_ws_bus.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_PACKAGE_SWEEP_STATUS.md`
- `.planning/packets/2026-06-01/CODEX_READY-library-staleness-replay-on-connect.md`

## What Changed

- `IpcRouterBus.emit()` now retains the latest
  `ipc.library.staleness_nudge`.
- `ws_broadcast()` replays retained sticky status frames when a new websocket
  client connects.
- `ipc.library.staleness_action` clears the retained nudge after the user
  dismisses or snoozes it, so reconnects do not resurrect a handled warning.
- Added a regression test that emits the nudge before any client connects and
  proves a late client receives it.

## Evidence

Pre-fix packaged proof exposed the bug:

```text
sidecar.log:
-> library import + staleness handlers wired
-> staleness nudge emitted (5d stale)
-> library freshness watcher armed
-> mascot bus on ws://127.0.0.1:8765

ui.log:
subscribe ipc.library.staleness_nudge
rust bridge ws-state {"state":"connected"}

ws_observe(seconds=15, type_filter="ipc.library.staleness_nudge")
count=0
```

The cache was actually stale and refreshable:

```text
library_freshness_status='stale'
library_stale=True
library_staleness_reason='source_newer_than_cache'
library_age_days=5
library_freshness.source_path='tests/library/fixtures/synthetic_collection.xml'
```

Focused tests after the fix:

```text
uv run pytest -q tests/runtime/test_ws_bus.py tests/library/test_staleness.py tests/ipc/test_library_schemas.py tests/ui_bus/test_messages_schema.py
128 passed in 1.38s
```

Lint:

```text
uv run ruff check src/vibemix/runtime/ws_bus.py src/vibemix/__main__.py tests/runtime/test_ws_bus.py
All checks passed!
```

Current-source runtime proof after the fix:

```text
VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix
-> staleness nudge emitted (5d stale)
-> mascot bus on ws://127.0.0.1:8765

ws_observe(seconds=4, type_filter="ipc.library.staleness_nudge")
count=1
{"type":"ipc.library.staleness_nudge","payload":{"age_days":5,"snoozed_until_ts":null,"source_path":"tests/library/fixtures/synthetic_collection.xml","reason":"source_newer_than_cache","schema_version":"1"}}
```

The proof runtime was stopped cleanly; no `127.0.0.1:8765` listener remained
afterwards.

## Boundaries

- No broad staging, no commit, and no product-release claim.
- The existing signed/notarized DMG does not include this replay fix. Rebuild and
  re-sign before claiming packaged proof for this slice.
- This proves the nudge reaches a late websocket client. It does not prove a
  human clicked `Refresh library`, importer progress rendered, or Viber unblocked
  after refresh; those remain final acceptance checks for Package 5F.
