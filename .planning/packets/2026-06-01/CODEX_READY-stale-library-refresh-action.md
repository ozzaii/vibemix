# CODEX_READY: Stale Library Refresh Action

Date: 2026-06-01
Author: Codex
Status: LAND packet, refresh action slice
Package: Package 5F - Stale Library Refresh Action

## Decision

LAND this slice as `fix(settings): refresh stale library source`.

Package 5E made the running app notice that its source-backed library cache had
gone stale. Package 5F makes that notice actionable when the original Rekordbox
XML still exists on the machine.

## Files

- `src/vibemix/library/staleness.py`
- `src/vibemix/__main__.py`
- `src/vibemix/runtime/ws_bus.py`
- `src/vibemix/ui_bus/schemas/library.py`
- `src/vibemix/ui_bus/messages.py`
- `tests/runtime/test_ws_bus.py`
- `tests/library/test_staleness.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/settings/components/staleness-banner.ts`
- `tauri/ui/src/settings/components/library-panel.ts`
- `tauri/ui/src/settings/SettingsDrawer.ts`
- `tauri/ui/tests/settings/staleness-banner.spec.ts`
- `tauri/ui/tests/settings/library-panel.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-stale-library-refresh-action.md`

## What Changed

- `freshness_nudge_payload()` and the live freshness watcher now include a
  refreshable `source_path` only when the stale cache came from an existing
  Rekordbox XML file.
- `ipc.library.staleness_nudge` gained optional `source_path` and `reason`
  fields, with generated TypeScript and validator files refreshed.
- The Settings staleness banner now shows `Refresh library` only when the nudge
  carries a refreshable source. Otherwise it keeps the button hidden and asks
  the user to drop the Rekordbox XML below.
- The refresh action reuses `ipc.library.import`; inside Settings it delegates
  through the library panel handle when mounted so progress and errors remain
  centralized.
- No new backend command, watcher daemon, or auto-ingest loop was introduced.
- Follow-up live proof found the nudge was emitted before late UI clients could
  receive it. The bus now replays the latest staleness nudge on connect, and a
  dismiss/snooze action clears the retained nudge.

## Evidence

Freshness/status/tool guards:

```text
uv run pytest -q tests/library/test_staleness.py tests/library/test_stats_cli.py tests/library/test_setprep_tools.py tests/ui_bus/test_messages_schema.py tests/ipc/test_library_schemas.py
148 passed in 2.13s
```

Settings/UI action:

```text
npm --prefix tauri/ui test -- tests/settings/staleness-banner.spec.ts tests/settings/library-panel.spec.ts tests/settings/drawer.spec.ts src/library/api.test.ts
Test Files  4 passed (4)
Tests  87 passed (87)
```

Lint:

```text
uv run ruff check src/vibemix/library/staleness.py src/vibemix/__main__.py src/vibemix/ui_bus/schemas/library.py src/vibemix/ui_bus/messages.py tests/library/test_staleness.py
All checks passed!
```

IPC:

```text
npm --prefix tauri/ui run check:ipc
```

```text
uv run python scripts/check_ipc_schema.py
OK: 72 dataclasses validate against schema
OK: count parity - 72 oneOf entries == 72 wrapper dataclasses
OK: SettingsSet field enum parity
OK: SettingsState payload parity
```

Main smoke/schema:

```text
uv run pytest -q tests/test_main_smoke.py tests/ui_bus/test_messages_schema.py tests/ipc/test_library_schemas.py
121 passed in 3.52s
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
- Current-source websocket delivery is proven. The existing signed DMG predates
  the replay fix, so packaged proof requires a rebuild/re-sign.
- This does not auto-refresh non-XML folder caches; those still need a separate
  folder-source refresh design.
- This does not bypass Package 5D's stale-library refusal. Viber set-prep should
  remain blocked until refresh makes the freshness status current again.

## Next Required Proof

Run a live or packaged proof with a real or fixture `collection.xml`:

- Import the XML and create `library.pkl`.
- Modify the source XML after indexing.
- Observe `ipc.library.staleness_nudge` with `source_path` in the rebuilt signed
  package.
- Click `Refresh library`.
- Verify importer progress and a fresh status.
- Verify Viber set-prep tools unblock only after the refresh.
