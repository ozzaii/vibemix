---
phase: 28-library-intelligence-v1
plan: 07
subsystem: library
tags: [staleness, nudge, snooze, atomic-write, ui-banner]

requires:
  - phase: 28-09
    provides: ipc.library.staleness_nudge + staleness_action schemas
  - phase: 25
    provides: ~/.cache/vibemix/library.pkl mtime as staleness signal

provides:
  - vibemix.library.staleness module (pure functions, no module state)
  - 30-day boundary detection with 7-day snooze persistence
  - Vanilla TS staleness banner mounted in SettingsDrawer LIBRARY group
  - Boot wiring in __main__.py — fires once per boot if stale + not snoozed

affects: [28-06]

tech-stack:
  added: []
  patterns:
    - "Atomic state.json write via tempfile + os.replace"
    - "Pure-function staleness module — caller controls boot lifecycle"
    - "Vanilla TS UI subscribes via subscribeIpc + emits via emitIpc (Phase 11 pattern)"

key-files:
  created:
    - src/vibemix/library/staleness.py
    - tauri/ui/src/settings/components/staleness-banner.ts
    - tauri/ui/tests/settings/staleness-banner.spec.ts
    - tests/library/test_staleness.py
  modified:
    - src/vibemix/library/__init__.py
    - src/vibemix/__main__.py
    - tauri/ui/src/settings/SettingsDrawer.ts (mounts banner in new LIBRARY group)

key-decisions:
  - "Boundary at exactly 30 days (STALE_AGE_SECONDS = 30 * 86400). Test verifies ±1s precision."
  - "Fresh-install (no library.pkl) returns (False, 0) — never nudge users with no library."
  - "Atomic JSON write via mkstemp + os.replace; preserves unrelated state.json keys."
  - "Malformed state.json treated as empty (logged warning) — never crash boot."
  - "v1 stub emit_ipc logs to stdout; Plan 28-06 wires the full WS broadcast pipeline."
  - "Combined dismiss + snooze into single ipc.library.staleness_action message (Plan 09 schema)."

patterns-established:
  - "Pattern: persistent UI state lives in ~/.config/vibemix/state.json with atomic write."
  - "Pattern: boot-time IPC nudge requires no module state — caller invokes once."
---

# Plan 28-07 — 30-Day Staleness Nudge

Status: complete. 19/19 tests pass (14 Python + 5 vitest).

## What landed

### Python: `src/vibemix/library/staleness.py`

Pure functions (no module state):
- `is_stale(library_pkl)` → `(stale, age_days)`. Fresh-install path returns `(False, 0)`.
- `load_snooze_state(state_path)` / `save_snooze_state(ts, state_path)` — atomic JSON I/O.
- `is_snoozed(state_path)` → `True` iff snooze set AND not expired.
- `emit_nudge_if_stale(emit_ipc, library_pkl, state_path)` → boot-time check that emits `ipc.library.staleness_nudge` exactly once.
- `apply_snooze_action(action, state_path)` — handles `"dismiss"` (no-op) and `"snooze_7d"` (persist `time.time() + 7d`). Unknown action → ValueError.

Locked constants:
- `STALE_AGE_SECONDS = 30 * 86400`
- `SNOOZE_DURATION_SECONDS = 7 * 86400`
- `STATE_FILE_PATH = ~/.config/vibemix/state.json`

### UI: `staleness-banner.ts` + SettingsDrawer mount

Vanilla TS, no React. Subscribes to `ipc.library.staleness_nudge`, emits `ipc.library.staleness_action`. Mounted in SettingsDrawer's new LIBRARY group (Plan 06 will add the drag-drop importer below).

### Boot wiring: `__main__.py`

After Phase 27's `register_library` block:

```python
from vibemix.library import emit_nudge_if_stale as _emit_staleness

def _staleness_emit(msg_type, payload):
    print(f"-> [ipc.outbound] {msg_type} {payload}", flush=True)

_emit_staleness(_staleness_emit, library_cache)
```

The stub `_staleness_emit` logs structured stdout. Plan 28-06 wires the full WS broadcast path so the renderer actually receives the message.

## Test posture

- `pytest tests/library/test_staleness.py`: 14 pass in 0.6s
  - Boundary tests at ±1 second precision
  - Snooze persist + expire round-trip
  - Atomic write under simulated power-loss (`os.replace` raises → original state preserved)
  - Malformed JSON graceful
  - Unknown action raises
- `npx vitest run tests/settings/staleness-banner.spec.ts`: 5 pass in 0.7s
  - Nudge → banner shows with age text
  - Dismiss → hide + emit `dismiss`
  - Snooze → emit `snooze_7d` + hide
  - No nudge → stays hidden
  - Singular "1 day" formatting

## P48 preservation

`grep -c "register_library" src/vibemix/__main__.py` returns 2 (unchanged from Phase 27).

## Deviations

- **Boot WS broadcast deferred to Plan 28-06**: the IPC message currently logs to stdout instead of broadcasting on the WS bus. Plan 28-06 owns the full WS pipeline (drag-drop import flow uses the same path) so factoring this into 06 is cleaner than adding a half-finished broadcast helper here.
