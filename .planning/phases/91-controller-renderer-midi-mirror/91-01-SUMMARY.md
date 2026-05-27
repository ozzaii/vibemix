---
phase: 91-controller-renderer-midi-mirror
plan: 01
subsystem: ipc
tags: [ipc, schema, jsonschema, ajv, tauri, vite, capabilities, midi]

# Dependency graph
requires: []
provides:
  - "ipc.learn.controller_detected envelope (single-fire per MIDI port-bind/unbind)"
  - "ipc.learn.midi_position envelope (30 Hz delta-suppressed controller position)"
  - "LearnControllerDetected + LearnMidiPosition Python dataclasses + payload structs"
  - "Vite 7th rollup entry: learn (learn.html → dist/learn.html)"
  - "Tauri capability windows-scope entry: learn (mirrors debrief/pill/library precedent)"
  - "Pre-compiled ajv validator + TS types covering both new envelopes"
affects: [91-02, 91-03, 91-04, 91-05, 91-06, 91-07, 92, 93, 94, 95, 96]

# Tech tracking
tech-stack:
  added: []  # No new dependencies — pure schema + Vite/Tauri scaffolding edits
  patterns:
    - "Wrappers in sibling module (learn_messages.py) — first time a non-payload wrapper lives outside messages.py; precedent for future ipc.* domain splits"
    - "Count-parity introspection now scans both messages.py AND learn_messages.py with set-based de-duplication"

key-files:
  created:
    - "tauri/ui/learn.html"
    - "tauri/ui/src/learn/learn-window.ts (placeholder for Plan 05)"
    - "src/vibemix/ui_bus/learn_messages.py"
    - ".planning/phases/91-controller-renderer-midi-mirror/91-01-SUMMARY.md"
  modified:
    - "tauri/ui/src/ipc/messages.schema.json (+2 oneOf $refs, +2 definitions)"
    - "tauri/ui/src/ipc/messages.ts (regenerated)"
    - "tauri/ui/src/ipc/validator.generated.mjs (regenerated)"
    - "tauri/ui/vite.config.ts (+learn rollup input)"
    - "tauri/src-tauri/capabilities/default.json (windows scope append)"
    - "src/vibemix/ui_bus/__init__.py (re-export learn wrappers + payloads)"
    - "scripts/check_ipc_schema.py (multi-module introspection + 2 new examples)"
    - "tests/ui_bus/test_messages_schema.py (+2 examples, 64→66 count, def 65→67)"
    - "tests/ui_bus/test_recordings_messages.py (renamed _at_64 → _at_66)"
    - "tests/ui_bus/test_mood_change_envelope.py (64→66, scan both modules)"
    - "tests/ui_bus/test_citation_schema.py (scan both modules)"
    - "tests/ui_bus/test_overlay_schema.py (scan both modules)"
    - "tests/ipc/test_library_schemas.py (scan both modules)"

key-decisions:
  - "Wrappers live in learn_messages.py (sibling), not messages.py — keeps the Learn-domain typed surface co-located and avoids churning the 2k-line messages.py"
  - "Window LABEL learn appended to windows scope array in capabilities/default.json — NOT a new permission identifier (RESEARCH §Open Questions Q3 RESOLVED; Tauri 2.x auto-allows app commands; adding permissions identifier fails build)"
  - "positions value type integer minimum:0 maximum:127 — native MIDI CC range; 128 must reject at serialize time (regression-pinned by negative test)"
  - "Minimal placeholder tauri/ui/src/learn/learn-window.ts so vite build resolves the script src — Plan 05 replaces with real renderer"

patterns-established:
  - "Schema additions: append both oneOf $ref AND definitions block in same commit; run npm run codegen:ipc; commit regenerated artefacts alongside"
  - "Sibling-module wrappers: when a domain (e.g. learn.*) deserves its own module, count-parity introspection must scan ALL modules with set-based deduplication"
  - "Tauri capability for new window: append window LABEL to windows scope array (mirror debrief/pill/library); never add an open_<name>_window permission identifier"
  - "Vite multi-page entry needs the script src to resolve — dangling references fail build; ship a minimal placeholder when the real entrypoint is a later plan"

requirements-completed: [RENDER-01, RENDER-02, RENDER-07]

# Metrics
duration: 25min
completed: 2026-05-27
---

# Phase 91 Plan 01: Controller Renderer + MIDI Mirror IPC Contract Summary

**2 new ipc.learn.* envelopes (controller_detected + midi_position) wired end-to-end through schema → regenerated ajv/TS → Python dataclasses → Vite/Tauri scaffolding, with shared-file edits committed atomically in 3 task commits.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-05-27T20:31:00Z
- **Completed:** 2026-05-27T20:44:03Z
- **Tasks:** 3
- **Files modified:** 14 (including test-side count-parity fixes)
- **Commits:** 3 task commits + this summary

## Accomplishments

- 2 new `ipc.learn.*` envelopes added to `messages.schema.json` (oneOf + definitions); pre-compiled ajv validator + json-schema-to-typescript output regenerated and committed alongside (CSP-safe, no `unsafe-eval` needed in webview)
- Python `LearnControllerDetected` + `LearnMidiPosition` dataclasses live in `src/vibemix/ui_bus/learn_messages.py` — frozen + slots, re-using the shared `_VALIDATOR` from `messages.py` (Draft-07 ref-resolver caches efficiently on a single instance)
- 7th Vite rollup entry `learn` wired into `vite.config.ts`; `tauri/ui/learn.html` ships as the entry; `dist/learn.html` emits at 1.77 kB
- `"learn"` window label appended to `tauri/src-tauri/capabilities/default.json` windows scope array (mirrors debrief/pill/library precedent); `permissions` array byte-identical to pre-task state
- `scripts/check_ipc_schema.py` count-parity gate green: 66 oneOf == 66 wrappers
- 7 count-parity tests across `tests/ui_bus/` + `tests/ipc/` updated to the new count or to multi-module introspection — full suites green (223 ui_bus+ipc Python tests + 951 tauri vitest tests)

## Task Commits

Each task was committed atomically by named paths only (concurrent-session discipline — never `git add -A`):

1. **Task 1: Add ipc.learn.controller_detected + ipc.learn.midi_position to messages.schema.json + regenerate** — `905e1550` (feat) — schema oneOf + definitions edits + regenerated `messages.ts` + `validator.generated.mjs`
2. **Task 2: Add learn as 7th Vite entry + capabilities windows scope + learn.html** — `e6b94619` (feat) — `vite.config.ts` rollup input + `learn.html` + `capabilities/default.json` windows scope + placeholder `learn-window.ts` (Rule 3 deviation)
3. **Task 3: Land learn_messages.py + restore count parity** — `de4808ce` (feat) — Python dataclasses + re-exports + extended check script + 6 test sites fixed

**Plan metadata commit (this SUMMARY + STATE/ROADMAP/REQUIREMENTS):** see final commit below.

## Files Created/Modified

### Created

- `tauri/ui/learn.html` — 7th Vite multi-page entry; structural mirror of `debrief.html` with title "Learn — vibemix", `id="learn-root"`, script `/src/learn/learn-window.ts`.
- `tauri/ui/src/learn/learn-window.ts` — minimal Vite-resolvable placeholder so `npm run build` emits `dist/learn.html`; Plan 05 replaces with the real renderer.
- `src/vibemix/ui_bus/learn_messages.py` — `LearnControllerDetected` + `LearnMidiPosition` envelope wrappers + their payload dataclasses; re-uses `_now_iso` + `_serialize` from `messages.py`.

### Modified (schema + codegen)

- `tauri/ui/src/ipc/messages.schema.json` — +2 oneOf `$ref` entries appended; +2 `definitions` blocks (`LearnControllerDetected`, `LearnMidiPosition`) with `additionalProperties:false` at envelope + payload + `positions.additionalProperties = {type:integer,minimum:0,maximum:127}` (native MIDI range).
- `tauri/ui/src/ipc/messages.ts` — regenerated via `npm run codegen:ipc`; SHA-256 `71b46132cdb8ade82c745d1e9dd43fe1bfe500910ada5eee1dcdb78184cf3696`.
- `tauri/ui/src/ipc/validator.generated.mjs` — regenerated; SHA-256 `84e6e1563319cf058a20b8c7086def091f102f28658333ec933e3454c7343e38`.

### Modified (Tauri/Vite scaffolding)

- `tauri/ui/vite.config.ts` — appended `learn: resolve(projectRoot, "learn.html")` as the 7th `rollupOptions.input` key.
- `tauri/src-tauri/capabilities/default.json` — appended literal `"learn"` to the `windows` scope array. `permissions` array byte-identical to pre-task state (verified via `git diff`).

### Modified (Python re-exports + count-parity)

- `src/vibemix/ui_bus/__init__.py` — re-exports `LearnControllerDetected`, `LearnControllerDetectedPayload`, `LearnMidiPosition`, `LearnMidiPositionPayload` from `learn_messages.py`.
- `scripts/check_ipc_schema.py` — extended introspection to scan both `messages.py` and `learn_messages.py` with set-based de-duplication; added minimal-valid examples for the 2 new wrappers.

### Modified (test count-parity fixes)

- `tests/ui_bus/test_messages_schema.py` — +2 example entries; oneOf count 64→66; definitions count 65→67; renamed `test_schema_oneof_count_is_64` → `test_schema_oneof_count_is_66`.
- `tests/ui_bus/test_recordings_messages.py` — renamed `test_count_parity_at_64` → `test_count_parity_at_66`; scan both modules.
- `tests/ui_bus/test_mood_change_envelope.py` — count 64→66; scan both modules.
- `tests/ui_bus/test_citation_schema.py` — scan both modules (no hard-coded count; was missing `learn_messages` from `inspect.getmembers`).
- `tests/ui_bus/test_overlay_schema.py` — same fix.
- `tests/ipc/test_library_schemas.py` — same fix.

## Decisions Made

- **Wrappers live in `learn_messages.py` (sibling module), not in `messages.py`** — the plan explicitly chose this to avoid churning the 2000-line `messages.py`. Cost: count-parity introspection (in script + 6 tests) had to learn about the second module. Benefit: the Learn-domain typed surface is co-located and Plan 03 (Python backend) imports from one module rather than spreading consumers across messages.py.
- **Window LABEL `"learn"` goes in the `windows` scope array, NOT as a permission identifier** — verified by reading the file's line-4 description text and RESEARCH §Open Questions Q3 RESOLVED. Tauri 2.x auto-allows webview→app-command invocation for any command registered in `invoke_handler`; adding `"open_learn_window"` or `"learn_window:default"` would fail the build with "permission identifier not found". The `windows` scope array enrols the spawned `WebviewWindow` into the default-capabilities surface (mirrors debrief/pill/library precedent).
- **`positions` value type is `integer` with `minimum:0, maximum:127`** — native MIDI CC range; the schema's `additionalProperties: {type: integer, minimum: 0, maximum: 127}` rejects out-of-range values at serialize time (regression-pinned by the negative test in Task 3's verify gate).
- **Minimal placeholder `tauri/ui/src/learn/learn-window.ts`** — the plan assumed Vite would tolerate a dangling script src; it does not. Smallest possible placeholder unblocks `npm run build` so `dist/learn.html` emits. Plan 05 replaces with the real renderer.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Added `tauri/ui/src/learn/learn-window.ts` placeholder**
- **Found during:** Task 2 (Vite build verify step)
- **Issue:** The plan stated "Vite tolerates the dangling reference during build until Plan 05 lands." This is incorrect — Vite 6.x reports `Failed to resolve /src/learn/learn-window.ts from learn.html` and aborts before emitting `dist/learn.html`. The plan's verify command (`npm run build && test -f dist/learn.html`) would fail.
- **Fix:** Shipped a minimal 50-line `tauri/ui/src/learn/learn-window.ts` that mounts a placeholder notice ("Learn module not yet wired (Plan 05)") into `#learn-root` on DOMContentLoaded. Provides a visible seam rather than a silent blank window; the empty `export {}` keeps the module tree-shakeable to ~0.40 kB.
- **Files modified:** `tauri/ui/src/learn/learn-window.ts`
- **Verification:** `npm run build` exits 0; `dist/learn.html` (1.77 kB) + `dist/assets/learn-CjALWuLe.js` (0.40 kB) emit; Plan 05's eventual replacement will not need any other shell changes.
- **Committed in:** `e6b94619` (Task 2 commit)

**2. [Rule 3 - Blocking Issue] Extended `scripts/check_ipc_schema.py` to introspect `learn_messages.py`**
- **Found during:** Task 3 (count-parity verify step — `python3 scripts/check_ipc_schema.py exits 0` from plan's done criterion)
- **Issue:** The original `_count_wrapper_dataclasses()` only walked `dir(ui_bus_messages)`. The plan declared wrappers live in `learn_messages.py` (not `messages.py`), so 64 wrappers vs 66 oneOf — count parity broken until the script learned to scan both modules.
- **Fix:** Extended the introspection loop to walk both `ui_bus_messages` and `ui_bus_learn_messages` with a `seen: set[type]` guard for future re-export safety; added minimal-valid examples for both new wrappers (`LearnControllerDetected.make(...)` and `LearnMidiPosition.make(...)`).
- **Files modified:** `scripts/check_ipc_schema.py`, `src/vibemix/ui_bus/__init__.py` (re-exports).
- **Verification:** `python3 scripts/check_ipc_schema.py` exits 0 with "OK: 66 dataclasses validate against schema; OK: count parity — 66 oneOf entries == 66 wrapper dataclasses".
- **Committed in:** `de4808ce` (Task 3 commit)

**3. [Rule 1 - Bug] Updated 6 test sites that hard-coded the previous oneOf count (64) or didn't scan `learn_messages.py`**
- **Found during:** Task 3 (running `tests/ui_bus/` immediately after creating `learn_messages.py`)
- **Issue:** 6 count-parity tests broke after the schema grew 64→66:
  - `tests/ui_bus/test_messages_schema.py::test_schema_oneof_count_is_64` (hard-coded count) + `::test_example_count_matches_schema_oneof` (hard-coded `_EXAMPLES == 64`)
  - `tests/ui_bus/test_recordings_messages.py::test_count_parity_at_64` (hard-coded count + dir(messages) only)
  - `tests/ui_bus/test_mood_change_envelope.py::test_count_parity_holds_after_addition` (hard-coded count + dir(messages) only)
  - `tests/ui_bus/test_citation_schema.py::test_count_parity_python_vs_schema` (no hard-coded count, but `inspect.getmembers(ui_bus_messages, ...)` only)
  - `tests/ui_bus/test_overlay_schema.py::test_count_parity_python_vs_schema` (same shape)
  - `tests/ipc/test_library_schemas.py::test_count_parity_python_vs_schema` (same shape)
- **Fix:** Updated all 6 test sites in lockstep — added `from vibemix.ui_bus import learn_messages as ui_bus_learn_messages`, extended the introspection loops with set-based de-duplication, bumped hard-coded counts 64→66 and 65→67, and renamed `_is_64` → `_is_66` / `_at_64` → `_at_66` for the function names that pinned the count in their identifier. Added 2 entries to the `_EXAMPLES` list in `test_messages_schema.py` so the parameterized roundtrip test covers both new wrappers.
- **Files modified:** 6 test files (listed above).
- **Verification:** `tests/ui_bus/` 179 passed (was 171 pass + 6 fail; now 171 + 2 new param tests + 6 fixed = 179). `tests/ipc/` 44 passed. Together: 223 passed.
- **Committed in:** `de4808ce` (Task 3 commit, same atomic unit as the count-parity script fix and the new dataclasses they pin)

---

**Total deviations:** 3 auto-fixed (2 Rule 3 - Blocking Issue, 1 Rule 1 - Bug)
**Impact on plan:** None of the deviations changed plan scope. Rule 3 #1 (placeholder TS file) added one tiny scaffolding file the plan would have needed anyway by Plan 05; Rule 3 #2 (script extension) made the plan's own done criterion achievable given the plan's modular-naming decision; Rule 1 (test fixes) corrected stale infrastructure tests that hard-coded a count that legitimately changed. All commits were named-path stages (no `git add -A`) — concurrent-session discipline upheld.

## Issues Encountered

- **System Python 3.14 path mismatch:** First test run picked up `/opt/homebrew/lib/python3.14/site-packages` which lacks the project's `livekit` extra and fails import-collection. Switched to `.venv/bin/python` (3.12.12) per the project's `>=3.12,<3.13` constraint. No code change needed; documenting so future executors source the venv first.
- **No git deletions in any commit** (verified via `git diff --diff-filter=D --name-only` after each commit). Three concurrent Codex sessions are touching adjacent files in `live-tuning-or-brain` — confirming named-path staging never grabbed shared work in flight.

## Threat Flags

No new security-relevant surface flagged. The two envelopes ride the existing `127.0.0.1:8765` loopback ws bus (one-socket invariant #4 preserved) with `additionalProperties:false` on every payload and `minLength:1` on string identifiers; out-of-range integer values are rejected at serialize time on both sides. T-91-01 / T-91-02 / T-91-03 mitigations from the plan's `<threat_model>` are all implemented:
- **T-91-01 (Tampering, schema concurrent edit):** Task 1 landed BOTH new oneOf entries + BOTH new definitions + regenerated codegen output in ONE atomic commit. No half-state.
- **T-91-02 (Tampering, unvalidated ws frame):** `additionalProperties:false` at envelope + payload; `minLength:1` on `controller_id`/`display_name`; `0..127` integer bound on `positions` values. Both ajv (TS) and jsonschema (Python) enforce.
- **T-91-03 (Elevation, Tauri capability bypass):** Task 2 appended the `"learn"` window LABEL to the top-level `windows` scope (per RESEARCH §Open Questions Q3 RESOLVED). No permission-identifier entry added.

## Next Phase Readiness

- **Plan 02 (test stubs under TDD)** unblocked — both `ipc.learn.*` envelopes are wire-locked; `LearnControllerDetected` + `LearnMidiPosition` are importable from `vibemix.ui_bus.learn_messages` (or the package, via the new `__init__.py` re-exports).
- **Plan 03 (Python `midi_mirror.py` backend service)** unblocked — can import the dataclasses and emit via `ws_bus`.
- **Plan 04 (Rust `learn_window.rs` + `main.rs` registration)** unblocked — `"learn"` is in the capabilities `windows` scope so the spawned `WebviewWindow` inherits the default-capabilities surface immediately.
- **Plan 05 (TS webview entrypoint — the real renderer)** unblocked — `tauri/ui/src/learn/learn-window.ts` placeholder must be REPLACED, not extended; the placeholder's `mountPlaceholderNotice` is intentionally throwaway code. The 7th rollup entry + `dist/learn.html` build path are wired.
- **Plans 06 / 07 (per-controller SVGs + Kaan ear-pass)** depend on Plan 05 first.
- **No KAAN-ACTION items added** by this plan. The latency-contingency KAAN-ACTION `§LEARN-LATENCY-CONTINGENCY` remains queued for measurement in Plan 02's harness — not in scope for Plan 01.

## Self-Check: PASSED

- Schema oneOf count: 66 (was 64; +2 expected)
- Schema definitions count: 67 (was 65; +2 expected)
- `LearnControllerDetected` $ref in `messages.schema.json`: present in oneOf + definitions ✓
- `LearnMidiPosition` $ref in `messages.schema.json`: present in oneOf + definitions ✓
- Codegen idempotent: `npm run codegen:ipc` run twice → byte-identical output ✓
- `dist/learn.html` emitted by `npm run build`: 1772 bytes ✓
- `"learn"` in `capabilities/default.json` windows scope: ✓
- `permissions` array in `capabilities/default.json` unchanged: ✓ (verified via `git diff` showing changes only inside the `windows` array)
- No `open_learn_window` / `learn_window:default` strings anywhere in capabilities: ✓
- Python imports succeed: `from vibemix.ui_bus.learn_messages import LearnControllerDetected, LearnMidiPosition, LearnControllerDetectedPayload, LearnMidiPositionPayload` ✓
- Both envelope `.make().to_dict()` validates against `_VALIDATOR`: ✓
- `LearnMidiPosition` with `positions={"x": 128}` REJECTED by `_VALIDATOR`: ✓
- `python3 scripts/check_ipc_schema.py` exits 0: 66==66 ✓
- Three task commits exist + verified:
  - `905e1550` feat(91-01): add ipc.learn.controller_detected + ipc.learn.midi_position envelopes ✓
  - `e6b94619` feat(91-01): add learn as 7th Vite entry + capabilities windows scope ✓
  - `de4808ce` feat(91-01): land learn_messages.py Python dataclasses + restore count parity ✓
- Test suites green: 223 (ui_bus + ipc Python) + 951 (tauri vitest) ✓
- No git deletions in any task commit: ✓

---
*Phase: 91-controller-renderer-midi-mirror*
*Plan: 01*
*Completed: 2026-05-27*
