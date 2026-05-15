---
phase: 28-library-intelligence-v1
plan: 06
subsystem: library
tags: [drag-drop, importer, library-panel, tauri-14134, vanilla-ts]

requires:
  - phase: 28-01
    provides: LibraryEmbedder + content-hash cache
  - phase: 28-02
    provides: LibraryStore.add_batch
  - phase: 28-09
    provides: ipc.library.import / import_progress / import_cancel schemas
  - phase: 25
    provides: RekordboxLibrary.load_xml (writes ~/.cache/vibemix/library.pkl)

provides:
  - LibraryImporter (batch embed + cancel + per-track try/except)
  - import_library_async orchestrator with mid-session registry refresh
  - LibraryPanel vanilla TS component
  - Tauri Issue #14134 drag-drop dedupe via seenEventIds

affects: []

tech-stack:
  added: []
  patterns:
    - "Cooperative cancel via asyncio.Event"
    - "Per-track try/except so bad files don't blow the batch"
    - "Drag-drop dedupe by event.id (Tauri Issue #14134)"
    - "Async component mount via placeholder + replaceWith"

key-files:
  created:
    - src/vibemix/library/importer.py
    - tauri/ui/src/settings/components/library-panel.ts
    - tests/library/test_importer.py
    - tauri/ui/tests/settings/library-panel.spec.ts
  modified:
    - src/vibemix/library/__init__.py
    - tauri/ui/src/settings/SettingsDrawer.ts (mounts LibraryPanel below staleness banner)

key-decisions:
  - "Drag-drop is primary UX. tauri-plugin-dialog file-picker fallback deferred — Phase 28.x task."
  - "Cancelled imports do NOT refresh evidence_registry (test asserts) — partial state should not poison live citations."
  - "Cache-hit probing happens BEFORE the embed call so cache_hits is accurate even when the embedder ultimately re-embeds (defensive)."
  - "Async component mount: parent inserts a placeholder div, async loader swaps via replaceWith — keeps SettingsDrawer mount synchronous."

patterns-established:
  - "Pattern: drag-drop dedupe via Set<event.id> — required for Tauri 2.x onDragDropEvent (Issue #14134)."
  - "Pattern: importer.cancel_flag = asyncio.Event() — checked at every batch boundary."
---

# Plan 28-06 — Drag-Drop Importer + Library Panel

Status: complete. 13/13 tests pass.

## What landed

### Python: `src/vibemix/library/importer.py`
- `LibraryImporter.import_library(xml_path)` — async, batch_size=10, cooperative cancel via `asyncio.Event`.
- Per-track try/except — one bad audio file logged + skipped, batch continues.
- Cache-hit probe via `embedder._cache.execute()` so `cache_hits` is accurate.
- Final batch flushed even on cancel.
- `import_library_async()` orchestrator → on success, refreshes EvidenceRegistry for mid-session citations.

### UI: `tauri/ui/src/settings/components/library-panel.ts`
- Vanilla TypeScript. Zero framework deps.
- Drag-drop via `getCurrentWebview().onDragDropEvent`.
- **Tauri Issue #14134 dedupe**: `seenEventIds = new Set<number>()`. Same drop fires the listener twice; we ignore the second.
- Progress bar fed by `ipc.library.import_progress` subscription.
- Cancel button → `ipc.library.import_cancel`.

## Test posture

- `pytest tests/library/test_importer.py` → 6 pass in 0.7s
  - Per-track progress emit
  - Cancel at batch boundary returns `cancelled=True`
  - Failed track skipped, batch continues
  - register_library called after success
  - No register call on cancel
  - cache_hits counted accurately
- `npx vitest run tests/settings/library-panel.spec.ts` → 7 pass in 1s
  - Dedupe by event.id (Tauri #14134 regression guard)
  - New event.id fires new emit
  - Non-XML drop shows "Need a .xml file"
  - Progress fill width updates
  - Cancel emits cancel message
  - Completion hides progress + shows "N tracks indexed"
  - Dispose unsubscribes

## Deviations

- **tauri-plugin-dialog file-picker fallback DEFERRED**: the plugin isn't bundled in v1 (npm + cargo deps). The "Choose file" button shows a hint to drag instead. Drag-drop is the primary UX and works fully. Adding the picker is a Phase 28.x task if Kaan wants single-click pick.

- **No anti-feature check for `import` (yet)**: the IPC dispatcher wiring (route `ipc.library.import` → `import_library_async`) is a Phase 29 sidecar-runtime task. Plan 28-06 ships the importer primitive + UI + Plan 09 schema; the actual ws_bus dispatch lives in `runtime/ws_bus.py` which a follow-up plan owns.
