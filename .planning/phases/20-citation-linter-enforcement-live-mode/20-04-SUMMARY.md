---
phase: 20-citation-linter-enforcement-live-mode
plan: 04
subsystem: ui_bus + runtime + tauri-shell
tags: [ipc, citation, anti-slop, ground-06, tdd]
requires:
  - 20-01-SUMMARY.md  # CitationLinter (read-only consumer source)
  - 20-02-SUMMARY.md  # StrippedRateTracker (15s rolling rate source)
  - 20-03-SUMMARY.md  # replay_linter (anti-slop CI pass-gate)
provides:
  - ipc.session.citation IPC message — Draft-07 schema + Python wrapper
  - SessionCitationPayload + SessionCitation in vibemix.ui_bus
  - CITATION_PUBLISH_INTERVAL_S + ipc_bus / citation_telemetry kwargs in coach_loop
  - tauri/ui/src/settings/components/citation-diagnostics.{ts,spec.ts}
affects:
  - tauri/ui/src/ipc/messages.schema.json (oneOf 34 → 35)
  - tauri/ui/src/ipc/messages.ts (TS codegen regenerated)
  - scripts/check_ipc_schema.py (count-parity gate covers SessionCitation)
  - tests/ui_bus/test_messages_schema.py + test_recordings_messages.py +
    test_mood_change_envelope.py (literal-34 → literal-35)
  - tauri/ui/vitest.config.ts (jsdom glob extended)
tech-stack:
  added: []
  patterns:
    - "Frozen+slots dataclass payload struct under schemas/<domain>.py
       subpackage; messages.py wrapper imports it. New layout adopted in
       Plan 20-04 — keeps messages.py thin while colocating future
       payload types by domain."
    - "Periodic IPC publish gate inside coach_loop: try/except wraps the
       whole telemetry call → SessionCitation.make → ipc_bus.emit chain;
       last_publish_at is bumped in the finally block so a chronically
       broken telemetry callable cannot spam stderr faster than the
       interval (anti-DOS, T-20-04-03 mitigation)."
key-files:
  created:
    - src/vibemix/ui_bus/schemas/__init__.py
    - src/vibemix/ui_bus/schemas/citation.py
    - tests/ui_bus/test_citation_schema.py
    - tests/runtime/test_coach_citation_publish.py
    - tauri/ui/src/settings/components/citation-diagnostics.ts
    - tauri/ui/src/settings/components/citation-diagnostics.spec.ts
  modified:
    - src/vibemix/ui_bus/messages.py
    - src/vibemix/ui_bus/__init__.py
    - src/vibemix/runtime/coach.py
    - tauri/ui/src/ipc/messages.schema.json
    - tauri/ui/src/ipc/messages.ts (codegen)
    - tauri/ui/vitest.config.ts
    - scripts/check_ipc_schema.py
    - tests/ui_bus/test_messages_schema.py
    - tests/ui_bus/test_recordings_messages.py
    - tests/ui_bus/test_mood_change_envelope.py
decisions:
  - "Tauri component is plain TS DOM-API style (citation-diagnostics.ts),
     NOT React .tsx. Matches the prevailing pattern in
     tauri/ui/src/settings/components/ (recording-row.ts, retention-slider.ts,
     mascot-group.ts) which all use plain TS + registerStyle helper +
     document.createElement DOM construction. Filename uses kebab-case to
     match siblings (recording-row.ts, mascot-group.ts), not PascalCase as
     the planner brief tentatively suggested with .tsx fallback. Spec file
     follows the same convention."
  - "Subscription wiring is deferred — the component exposes
     {root, update(props)} so a future Settings-drawer subscriber (Phase 14
     follow-up) can push fresh props on every ipc.session.citation message
     without rebuilding the DOM. No global IPC bus subscription added in
     this plan — the renderer is a pure function over props, ready to drop
     into whichever container the Settings drawer eventually adds."
  - "Defensive [0,1] clamp in formatPct() is a renderer safety net even
     though the schema's minimum:0/maximum:1 bound is enforced on the wire.
     Catches the unlikely case of a sidecar that bypasses jsonschema
     validation (e.g. a future codepath that emits SessionCitation directly
     without going through ipc_bus.emit's _validate_outbound) AND keeps the
     unit-test surface honest with the 7th vitest case."
metrics:
  duration: ~25min
  completed: 2026-05-14
---

# Phase 20 Plan 04: Citation Diagnostics IPC + UI Surface Summary

**One-liner:** Sidecar→shell `ipc.session.citation` channel surfaces the linter's slop_ratio + 15s rolling stripped_rate + last unverified response + bypass_active flag every 2.0s from coach_loop, with a stub Tauri renderer ready for Settings drawer integration.

## What Shipped

### Python — `vibemix.ui_bus`

**`src/vibemix/ui_bus/schemas/citation.py`** (new, 39 lines): `SessionCitationPayload` frozen+slots dataclass — single source of truth for the 4-field payload struct. Mirrors the planner brief's `schemas/<domain>.py` subpackage layout (new pattern adopted in Plan 20-04 to keep `messages.py` wrappers thin).

**`src/vibemix/ui_bus/schemas/__init__.py`** (new, 11 lines): re-exports `SessionCitationPayload`.

**`src/vibemix/ui_bus/messages.py`** (modified): adds `SessionCitation` wrapper class — frozen+slots dataclass with type Literal `"ipc.session.citation"`, `.make()` factory taking the four payload fields as kwargs, `.to_json()` returning `_serialize(self)`. Imports `SessionCitationPayload` from the new schemas subpackage.

**`src/vibemix/ui_bus/__init__.py`** (modified): re-exports `SessionCitation` + `SessionCitationPayload`; extends `__all__`.

### Schema — `tauri/ui/src/ipc/messages.schema.json`

- New `oneOf` entry `{"$ref": "#/definitions/SessionCitation"}` inserted **after** `SessionMute` to keep `session.*` grouped (line 28).
- New `SessionCitation` definition (lines 524–544): `additionalProperties: false` at all 3 levels; `type` const `"ipc.session.citation"`; payload required keys `[slop_ratio, stripped_rate_15s, last_unverified_response, bypass_active]`; `slop_ratio` + `stripped_rate_15s` typed `number` with `minimum: 0` / `maximum: 1`; `last_unverified_response` typed `["string", "null"]`; `bypass_active` typed `boolean`.
- TypeScript codegen regenerated (`npm run codegen:ipc` → `tauri/ui/src/ipc/messages.ts`).
- Schema oneOf count: 34 → **35**. `definitions` count: 35 → **36** (LevelPair stays as the shared helper not in oneOf).

### Coach loop — `src/vibemix/runtime/coach.py`

- New module constant `CITATION_PUBLISH_INTERVAL_S = 2.0` (0.5Hz; lower than ipc.session.snapshot's 30Hz because slop_ratio + stripped_rate_15s evolve slowly).
- Two new keyword-only kwargs on `coach_loop`: `ipc_bus: IpcBus | None = None` + `citation_telemetry: Callable[[], dict] | None = None` (TYPE_CHECKING import for IpcBus to avoid runtime circular).
- New publish gate inside the main loop, AFTER `now = time.time()` and BEFORE the in_flight skip — so anti-slop telemetry keeps flowing even while a reaction is generating. Body: `citation_telemetry()` → `SessionCitation.make()` with `float()` / `bool()` / `.get(default)` defensive coercion → `await ipc_bus.emit(json.loads(msg.to_json()))`. Wrapped in try/except + finally that bumps `last_citation_publish_at = now` so a chronically broken telemetry callable cannot spam stderr faster than the interval (T-20-04-03 anti-DOS mitigation).
- When either kwarg is None, the gate is skipped — Plan 19-05 byte-identical legacy path preserved.
- Module docstring updated with the Plan 20-04 wiring summary.

### Tauri UI — `tauri/ui/src/settings/components/`

**Style decision**: matched the prevailing `recording-row.ts` / `retention-slider.ts` / `mascot-group.ts` pattern — plain TS DOM-API (`document.createElement` + `textContent`), NOT React `.tsx`. Filename uses kebab-case (`citation-diagnostics.ts`, not `CitationDiagnostics.tsx`) to match siblings. The planner brief flagged this as an executor-time decision; the deviation is documented here per the planner's instruction.

**`citation-diagnostics.ts`** (new, 162 lines):
- `renderCitationDiagnostics(props)` returns `{root, update(next)}` — typed via `CitationDiagnosticsProps` (slopRatio, strippedRate15s, lastUnverifiedResponse, bypassActive) and `CitationDiagnosticsHandle`.
- Renders 3 elements:
  - **Line 1**: `Slop ratio: <pct>%  ·  Stripped rate (15s): <pct>%` (Math.round(value * 100) with defensive [0,1] clamp).
  - **Badge**: `Bypass: ACTIVE` (data-active="true", amber-tinted) or `Bypass: idle` (data-active="false", silk-65).
  - **Optional subtitle** (`citation-diag-last-unverified` class): only when `bypassActive && lastUnverifiedResponse !== null`. Shows first 60 chars + `...`; full text in the `title` attribute (XSS-safe via `textContent` + `.title` — never `innerHTML`).
- `update(next)` re-applies state without rebuilding the DOM root, ready for a future Settings drawer subscriber.
- Uses `registerStyle("vmx-citation-diag", CSS)` from the existing `_style-registry.ts` shared with session components.

**`citation-diagnostics.spec.ts`** (new, 211 lines, 10 vitest cases): pins percentage formatting, badge active/idle state, 60-char truncation + title preservation, idle-vs-bypass subtitle visibility, `update()` identity-preserving refresh, XSS safety with `<script>` literal text, defensive [0,1] clamp.

**`tauri/ui/vitest.config.ts`** (modified): extended `environmentMatchGlobs` with `["src/settings/components/citation-diagnostics.spec.ts", "jsdom"]` so the spec routes to jsdom (the existing `recording-*.spec.ts` glob did not match the new filename).

## IPC Schema (locked)

```jsonc
"SessionCitation": {
  "$comment": "Phase 20 — Sidecar to shell. Live anti-slop telemetry: per-session slop_ratio (cumulative stripped/total), 15s rolling stripped_rate, the last unverified response text (when bypass fires), and the live bypass_active flag. UX-Settings-Diagnostics surface for the citation linter. GROUND-06.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": {"const": "ipc.session.citation"},
    "ts": {"type": "string", "format": "date-time"},
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["slop_ratio", "stripped_rate_15s", "last_unverified_response", "bypass_active"],
      "properties": {
        "slop_ratio":               {"type": "number",          "minimum": 0, "maximum": 1},
        "stripped_rate_15s":        {"type": "number",          "minimum": 0, "maximum": 1},
        "last_unverified_response": {"type": ["string", "null"]},
        "bypass_active":            {"type": "boolean"}
      }
    }
  }
}
```

## Publish cadence + transport

- **Interval**: `CITATION_PUBLISH_INTERVAL_S = 2.0` seconds (0.5Hz).
- **Trigger site**: top of the `coach_loop` main while-not-stop loop, immediately after `now = time.time()`. Runs before the in_flight skip so telemetry keeps flowing during AI reactions.
- **Wire transport**: `IpcBus.emit(dict)` (alias for `WizardBus.emit` — Phase 12) over the existing `127.0.0.1:8765` ws_bus. The bus's `_validate_outbound` runs the schema before sending, so a malformed payload raises locally rather than reaching the Tauri shell.
- **Activation**: only when **both** `ipc_bus` and `citation_telemetry` kwargs are non-None. When either is None, the publish gate is a no-op and the legacy Plan 19-05 path runs byte-identically (existing test_coach.py 14 cases stay green).

## Test deltas

- **`tests/ui_bus/test_citation_schema.py`** — 9 new cases (oneOf entry, definition shape, payload round-trip, bypass-active payload, slop_ratio out-of-range rejection, stripped_rate negative rejection, additionalProperties:false rejection, frozen+slots invariant, count-parity Phase 11 W0 invariant).
- **`tests/runtime/test_coach_citation_publish.py`** — 6 new cases (legacy no-op when ipc_bus=None, no-emit when telemetry=None, periodic publish at ≥2s cadence with envelope assertion, payload shape, exception swallowed without crash, bypass_active=True + last_unverified_response preserved).
- **`tests/ui_bus/test_messages_schema.py`** + **`test_recordings_messages.py`** + **`test_mood_change_envelope.py`** — 3 literal-34 → literal-35 count assertions bumped to reflect the new wrapper. (Rule 1 auto-fix: stale magic-number invariants from Phase 15-01.)
- **`tauri/ui/src/settings/components/citation-diagnostics.spec.ts`** — 10 new vitest jsdom cases.

### Test results

- `pytest tests/ui_bus/test_citation_schema.py tests/runtime/test_coach_citation_publish.py -x`: 15/15 pass.
- `pytest tests/ui_bus/`: 87/87 pass (was 82; +5 new + 0 regression).
- `pytest tests/runtime/`: 127/127 pass (was 121; +6 new + 0 regression).
- `pytest tests/`: 1803 pass / 10 pre-existing failures / 7 skipped. **+16 net pass, 0 new failures.**
- `npx vitest run`: 421/421 pass across 35 files (+10 new vitest cases).
- `python scripts/check_ipc_schema.py`: exits 0 (35 oneOf == 35 wrappers, all wrappers round-trip clean against schema).
- `npm run check:ipc`: codegen + tsc --noEmit clean.

### Pre-existing failures (NOT introduced by this plan)

`tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4`, `tests/recording/test_phase15_success_criteria.py::*` (3), `tests/scripts/test_replay_linter.py::test_csv_report_has_correct_shape`, `tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device`, `tests/test_main_smoke.py::test_smoke_03_full_wiring` + `test_smoke_04_no_openrouter_key` + `test_smoke_05_cleanup_closes_all_streams`, `tests/test_phase05_verification.py::test_g5_poc_files_untouched`. Verified via `git stash` baseline run — all 10 failed before Plan 20-04 began.

## UI Component Status

**Shipped**: minimal renderer + 10 passing vitest cases. The component is a stub in the planner-intended sense: it accepts props and renders the locked DOM shape, but does NOT subscribe to a global IPC bus or app store. Drop-in ready for whichever container the Phase 14 Settings drawer eventually adds. `update(next)` lets a future subscriber push fresh props on every ipc.session.citation message without rebuilding the DOM.

**Not in scope for this plan** (intentional, planner brief explicit):
- Settings → Diagnostics tab container (Phase 14 follow-up).
- IPC subscription wiring in the Tauri shell.
- Upstream wiring of `citation_telemetry` callable construction (the runtime caller in `__main__.py` / `runtime/session_loop.py` is downstream — Plan 20-04 only locks the SHAPE of the callable).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Stale magic number] Bumped literal-34 count assertions to 35**
- **Found during:** Task 1 GREEN, after the new wrapper landed.
- **Issue:** Three test files hard-coded `len(_SCHEMA["oneOf"]) == 34` from Plan 15-01: `tests/ui_bus/test_messages_schema.py:261/292`, `tests/ui_bus/test_recordings_messages.py:281/282`, `tests/ui_bus/test_mood_change_envelope.py:137`.
- **Fix:** Bumped all three to 35 with comments documenting the Phase 11 W0 + 13-05 + 15-01 + 20-04 trail. The planner brief's `must_haves.artifacts` for `tests/ui_bus/test_citation_schema.py` explicitly lists "Schema parity (count assertion drift)" — these assertions are the drift surface.
- **Files modified:** `tests/ui_bus/test_messages_schema.py`, `tests/ui_bus/test_recordings_messages.py`, `tests/ui_bus/test_mood_change_envelope.py`.
- **Commit:** `4a71c63` (Task 1 GREEN, batched with the wrapper landing).

**2. [Rule 2 — Missing CI roundtrip example] Added SessionCitation to scripts/check_ipc_schema.py**
- **Found during:** Task 1 GREEN.
- **Issue:** The script's `_minimal_examples()` list had to gain a SessionCitation entry — without it, the count-parity gate's "n_ok != oneof_count" check fires (the gate compares example count against schema oneOf, both must equal the wrapper count).
- **Fix:** Added a `SessionCitation.make(slop_ratio=0.12, stripped_rate_15s=0.07, last_unverified_response=None, bypass_active=False)` example and the corresponding import.
- **Commit:** `4a71c63`.

### Planner-anticipated decisions resolved at execute time

**3. [Plan §Task 2 §action — `.tsx` vs `.ts` decision]** Confirmed the prevailing pattern in `tauri/ui/src/settings/components/` is plain TS DOM-API across all 7 sibling files. Shipped `citation-diagnostics.ts` (kebab-case, NOT `CitationDiagnostics.tsx`). The plan's `files_modified` frontmatter listed `.tsx` but with an explicit "RENAME the file to CitationDiagnostics.ts and implement DOM-API style" branch — followed.

**4. [Vitest config glob extension]** `vitest.config.ts` only routed `recording-*.spec.ts` under `src/settings/components/` to jsdom. Added a parallel `citation-diagnostics.spec.ts` glob entry so the new spec runs under jsdom (otherwise it ran in node env and the `document.createElement` call would no-op). Single-line glob addition; no other config churn.

## Authentication gates

None. Fully autonomous execution.

## Known Stubs

The Tauri component is a renderer-only stub by design (per planner brief — "ships only the renderer"). It accepts props, renders the locked DOM shape, exposes `update(next)`. The component is **not** wired to the IPC bus / app store — that wiring is a Phase 14 follow-up. Documented intentionally; this is the planner's chosen scope.

## Threat Flags

None. The planner's `threat_model` enumerated 6 STRIDE entries (T-20-04-01..06); all are mitigated by the in-band guards (jsonschema bound enforcement, defensive coercion in coach.py, try/except with debounce, textContent-only DOM construction in the renderer). No new attack surface introduced beyond what the planner anticipated.

## Decisions Made

1. **Subpackage layout adopted**: `vibemix/ui_bus/schemas/<domain>.py` for new payload structs (SessionCitationPayload). The planner brief locked this pattern; future payload structs should follow it instead of appending to the monolithic messages.py.
2. **Tauri component style**: plain TS DOM-API + kebab-case filename, matching the recording-row.ts pattern. Reaffirmed for the Settings → Diagnostics surface — no React `.tsx` introduction.
3. **Defensive renderer clamp**: kept the [0,1] clamp in `formatPct()` even though the schema enforces the bound. Belt-and-braces for any future codepath that bypasses ipc_bus._validate_outbound.

## Self-Check: PASSED

**Created files exist:**
- FOUND: src/vibemix/ui_bus/schemas/__init__.py
- FOUND: src/vibemix/ui_bus/schemas/citation.py
- FOUND: tests/ui_bus/test_citation_schema.py
- FOUND: tests/runtime/test_coach_citation_publish.py
- FOUND: tauri/ui/src/settings/components/citation-diagnostics.ts
- FOUND: tauri/ui/src/settings/components/citation-diagnostics.spec.ts

**Commits exist:**
- FOUND: fb675a4 — test(20-04): RED — SessionCitation IPC schema + wrapper coverage
- FOUND: 4a71c63 — feat(20-04): GREEN — SessionCitation IPC wrapper + schema entry
- FOUND: 7f1040c — test(20-04): RED — coach_loop ipc.session.citation publish cadence
- FOUND: 4f41090 — feat(20-04): GREEN — coach citation publish + Tauri diagnostics stub
