---
phase: 28-library-intelligence-v1
plan: 09
subsystem: ipc
tags: [ipc, schemas, dataclasses, jsonschema, draft-07, library, tauri-ui]

requires:
  - phase: 11-tauri-shell-calibration-wizard
    provides: messages.schema.json + ui_bus dataclass/jsonschema wrappers + codegen-ipc.mjs

provides:
  - 10 ipc.library.* schemas (import / progress / cancel / search / search_result / confidence / staleness_nudge / staleness_action / similar_request / similar_result)
  - LibraryImport/Progress/Cancel/etc. wrapper dataclasses in src/vibemix/ui_bus/messages.py
  - LibrarySearchRequestPayload/etc. payload dataclasses in src/vibemix/ui_bus/schemas/library.py
  - Updated check_ipc_schema.py with 10 new examples; 49/49 count parity
  - Regenerated tauri/ui/src/ipc/messages.ts + validator.generated.mjs
  - 18 schema-parity tests in tests/ipc/test_library_schemas.py

affects: [28-03, 28-04, 28-05, 28-06, 28-07, 28-08]

tech-stack:
  added: []
  patterns:
    - "JSON Schema Draft-07 as IPC contract source-of-truth"
    - "Python wrapper.make(...).to_json() = asdict → tuples→lists → validate → dumps"
    - "Count parity assertion catches one-sided drift between Python and schema"

key-files:
  created:
    - src/vibemix/ui_bus/schemas/library.py
    - tests/ipc/test_library_schemas.py
  modified:
    - tauri/ui/src/ipc/messages.schema.json
    - tauri/ui/src/ipc/messages.ts (regenerated)
    - tauri/ui/src/ipc/validator.generated.mjs (regenerated)
    - src/vibemix/ui_bus/messages.py
    - src/vibemix/ui_bus/__init__.py
    - scripts/check_ipc_schema.py

key-decisions:
  - "10 schemas not 4 (CONTEXT said 4) — full set covers every Phase 28 IPC path"
  - "Pydantic-to-typescript NOT used — existing `npm run check:ipc` codegen handles TS types"
  - "schema_version = '1' const on every payload (forward-compat marker)"
  - "additionalProperties: false on every payload (Pitfall P10)"
  - "cost_warning boolean on LibraryConfidence — surfaces Plan 08 budget telemetry to renderer"

patterns-established:
  - "Pattern: each ipc.library.* wrapper is renderer→sidecar OR sidecar→renderer, named in $comment field. test_renderer_outbound_messages_documented enforces."
  - "Pattern: anti-feature guard at schema level via $comment (LibrarySimilarRequest carries USER-ASKED-ONLY notice; CONTEXT LIBRARY-14)."
---

# Plan 28-09 — Library IPC Schemas + Wrappers

Status: complete. Lands first in wave 1 — Plans 03-08 build against this frozen contract.

## Final list of 10 schemas

| # | Schema | Direction | Owning plan |
|---|--------|-----------|-------------|
| 1 | `LibraryImport` | renderer → sidecar | 28-06 |
| 2 | `LibraryImportProgress` | sidecar → renderer | 28-06 |
| 3 | `LibraryImportCancel` | renderer → sidecar | 28-06 |
| 4 | `LibrarySearchRequest` | renderer → sidecar | 28-03 |
| 5 | `LibrarySearchResult` | sidecar → renderer | 28-03 |
| 6 | `LibraryConfidence` | sidecar → renderer | 28-04 |
| 7 | `LibraryStalenessNudge` | sidecar → renderer | 28-07 |
| 8 | `LibraryStalenessAction` | renderer → sidecar | 28-07 |
| 9 | `LibrarySimilarRequest` | renderer → sidecar | 28-05 (USER-ASKED) |
| 10 | `LibrarySimilarResult` | sidecar → renderer | 28-05 |

## CONTEXT corrections

- CONTEXT said "4 new schemas". RESEARCH and the actual flow needed 10. Plan 09 ships 10.
- CONTEXT said "TS counterparts in frontend/src/types/library.ts (auto-generated via pydantic-to-typescript)". Wrong — vibemix uses dataclasses + jsonschema, and the existing `npm run check:ipc` codegen handles TS types from the JSON Schema. Plan 09 does NOT introduce pydantic.

## Test posture

- `python scripts/check_ipc_schema.py` → 49/49 count parity OK
- `cd tauri/ui && npm run check:ipc` → codegen + `tsc --noEmit` clean
- `pytest tests/ipc/test_library_schemas.py -x -q` → 18 tests pass in 0.12s
  - 10 parametrized validate round-trips (one per schema)
  - 1 additionalProperties: false guard
  - 1 required-field guard
  - 1 schema_version pin check
  - 1 Python ↔ schema count parity
  - 1 no-pydantic-import guard (Open Q4)
  - 1 $comment direction-documented guard
  - 1 wrapper-set allowlist
  - 1 payload-only-has-no-type-field guard

## Cost-warning field

`LibraryConfidence.cost_warning: bool` — surfaces Plan 28-08 budget telemetry to the renderer. When set, the renderer should warn the user that monthly Gemini spend is approaching the €50 ceiling. Plan 28-08 owns the calculation; Plan 09 just locks the IPC field shape.

## What this unlocks

- Plan 28-03: wire `LibrarySearchRequest` / `LibrarySearchResult` in `__main__.py` and the CLI shim.
- Plan 28-04: emit `LibraryConfidence` on every grounding decision (cited / uncertain / below_threshold).
- Plan 28-05: USER-ASKED similar-track query flow.
- Plan 28-06: drag-drop flow uses `LibraryImport` + `LibraryImportProgress` + `LibraryImportCancel`.
- Plan 28-07: 30-day staleness banner uses `LibraryStalenessNudge` + `LibraryStalenessAction`.
- Plan 28-08: budget telemetry emits `cost_warning=true` on the next `LibraryConfidence` once monthly spend crosses 90%.
