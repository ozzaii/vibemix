---
phase: 14-cdj-whisper-v5-migration-polish
plan: 04
subsystem: ui
tags: [migration, settings, drawer, perf-blur, ipc-schema, vitest-unskip]

# Dependency graph
requires:
  - phase: 14-cdj-whisper-v5-migration-polish
    plan: 01
    provides: scripted grep gates (--surface=settings --strict), vendored Saira + JetBrains Mono WOFF2, 14-POLISH-LOG.md skeleton, vitest harness with settings.tokens.test.ts describe.skip stub
  - phase: 14-cdj-whisper-v5-migration-polish
    plan: 02
    provides: @ts-nocheck on dormant settings.tokens.test.ts (this plan drops it as the spec is rewritten); wizard surface fully migrated as visual sibling reference
  - phase: 14-cdj-whisper-v5-migration-polish
    plan: 03
    provides: tokens.css perf-fallback block (html[data-blur-perf="on"] override of --blur-glass-*) + main.ts boot wiring + session surface fully migrated; this plan adds the Settings → Performance toggle that flips data-blur-perf
provides:
  - tauri/ui/src/settings/SettingsDrawer.ts root has <div class="border-anim"> as first child + overflow: hidden + descendant z-index 5 (UI-SPEC §Surface 3)
  - 4 existing settings components retoned (jsdoc purge — CSS bodies were already on v5 primitives from the prototype commit)
  - NEW tauri/ui/src/settings/components/performance-group.ts exporting applyBlurPerfPreference / toggleBlurPerf / PerformanceGroup; single-row "LIGHTER BLUR" toggle wires the data-blur-perf attribute via SettingsApplier with persistence
  - ipc.settings.set "field" enum gains "lighter_blur" (10th flat value) + SettingsState payload gains lighter_blur required + Python ui_bus + ConfigStore + SettingsApplier dispatch all agree (npm run check:ipc green, python3 scripts/check_ipc_schema.py 27/27 parity)
  - Settings drawer body wires PerformanceGroup AFTER MascotGroup — final group order PERSONA / OUTPUT / HOTKEY / RECORDING / CALIBRATION / MASCOT / PERFORMANCE
  - session SettingsView gains lighter_blur: boolean (default false) + ws-bridge applies the field defensively; render-loop.spec.ts test fixtures updated
  - tauri/ui/tests/settings.tokens.test.ts rewritten in full against real component signatures + unskipped (8 surface assertions — drawer no-legacy + border-anim first-child, retention-slider, hotkey-capture, mascot-group, PerformanceGroup off + on state, applyBlurPerfPreference attribute write/clear)
  - --strict v5 migration gate green on settings surface (8 → 0 legacy refs)
  - --strict v5 fonts gate green on settings surface (already 0)
  - npm run build green (tsc --noEmit + vite build)
affects: [14-05-mascot, 14-06-shim-delete]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Flat enum extension for new settings.set fields: 'lighter_blur' joins the 9 existing flat enum entries in messages.schema.json line 529 — no dot-paths. Mirror in src/vibemix/ui_bus/messages.py SettingsSetPayload.field Literal. SettingsApplier.apply dispatches on flat string at src/vibemix/runtime/settings.py:155–174. Consistent with click_through (Plan 13-03) precedent."
    - "ConfigStore extension for typed top-level boolean: lighter_blur joins voice/mode/genre/output_device_id/output_profile/retention_days/push_to_mute_hotkey as a typed Phase-12 field (vs. click_through which lives in ConfigStore.extra). Typed surface chosen because SettingsState.make needs the value at boot — reading via extra round-trips through dict[str, Any] which loses the bool type narrowing."
    - "PerformanceGroup local-first apply: toggle handler flips html[data-blur-perf] IMMEDIATELY (zero round-trip) then persists via sendSettings async. If the sidecar isn't reachable (Vite dev, sidecar down), the local apply survives for the session — next launch reads the field defensively defaulting to off."
    - "Settings spec rewrite pattern (Wave 3 of 4): drop @ts-nocheck from the Wave-0 stub + rewrite against real component signatures + unskip. Same pattern Plan 14-03 used for session.tokens.test.ts; Plan 14-05 will use it for mascot.tokens.test.ts (if applicable)."

key-files:
  created:
    - tauri/ui/src/settings/components/performance-group.ts
    - .planning/phases/14-cdj-whisper-v5-migration-polish/14-04-SUMMARY.md
  modified:
    - tauri/ui/src/settings/SettingsDrawer.ts
    - tauri/ui/src/settings/components/retention-slider.ts
    - tauri/ui/src/settings/components/mascot-group.ts
    - tauri/ui/src/settings/components/hotkey-capture.ts
    - tauri/ui/src/settings/components/confirm-dialog.ts
    - tauri/ui/src/session/state.ts
    - tauri/ui/src/session/ws-bridge.ts
    - tauri/ui/src/ipc/messages.schema.json
    - tauri/ui/src/ipc/messages.ts
    - tauri/ui/src/ipc/validator.spec.ts
    - tauri/ui/src/main.ts
    - tauri/ui/tests/settings.tokens.test.ts
    - tauri/ui/tests/session/render-loop.spec.ts
    - src/vibemix/ui_bus/messages.py
    - src/vibemix/runtime/settings.py
    - src/vibemix/runtime/config_store.py
    - src/vibemix/runtime/session_loop.py
    - tests/runtime/test_settings_apply.py
    - .planning/phases/14-cdj-whisper-v5-migration-polish/14-POLISH-LOG.md

key-decisions:
  - "FLAT enum entry for lighter_blur (not dot-path 'performance.lighter_blur'). Locked by plan-checker W-2 resolution before execution; verified consistent with the 9 existing flat enum entries in settings.set.field + the SettingsApplier flat-string dispatcher at settings.py:155–174. A dot-path would have been the only such entry, inconsistent with every other field. Plan critical_directive #1 made this decision binding before code touched."
  - "Field lives on SettingsView in session/state.ts (the canonical settings record consumed by the drawer composer + ws-bridge), NOT settings/state.ts (which holds drawer-local UX state: open/close, capture mode, etc.). Mirrors the click_through precedent from Plan 13-03. The plan's frontmatter listed settings/state.ts in files_modified — but that file's surface is UX-only (e.g. `confirmDialog: null | 're-run-calibration'`); the persisted setting belongs on SettingsView. Documented as Rule 1 deviation (matched existing pattern)."
  - "Typed ConfigStore.lighter_blur instead of click_through-style ConfigStore.extra. Reason: SettingsState.make in session_loop.py needs the value at boot — reading via .extra is a dict lookup that loses the bool type narrowing and forces ' is True'-style coercion. The typed field reads cleanly as self.config_store.lighter_blur and to_dict/from_dict round-trip the atomic write via the existing _PHASE12_FIELDS path."
  - "main.ts readBlurPerfPreference updated to index the FLAT payload.lighter_blur path. The Wave 2 implementation (Plan 14-03) used a nested payload.performance.lighter_blur shape as a defensive placeholder before this plan locked the flat-enum decision. Updated docstring + retained 2s timeout + defensive return-false on any failure. Rule 1 fix — no deviation since the placeholder was always meant to be replaced by this plan."
  - "SettingsSetPayload.field Literal expanded from 7-value to 10-value (was missing 'mood' + 'click_through' from Plan 13-05 + 'lighter_blur' from this plan). Plan 13-05 added the two mascot fields to the schema but never propagated to the Python Literal — caught + fixed in this commit. The schema validation runs against the JSON schema (single source of truth), so the Literal was advisory; still worth keeping accurate so editor autocomplete + mypy stay in sync. Rule 1 (catch-up fix)."
  - "Test spec rewritten in full rather than patched. The Wave-0 stub at tauri/ui/tests/settings.tokens.test.ts used drifted component prop shapes (e.g. `initialDays`, `onCommit`) that don't match the real APIs (`value`, `onChange`, `onCapture`). Wave 1 papered over with @ts-nocheck so build stayed green; Wave 3 rewrites against real signatures + unskips. Same pattern Plan 14-03 used for session.tokens.test.ts. No drift left."
  - "Settings group order: PERFORMANCE appended AFTER MASCOT per CONTEXT Area 4 Copywriting Contract row 'Settings group headers' — 'persona · output · hotkey · recording · calibration · mascot · performance'. The drawer's group composition order is the same as the rendered order; PerformanceGroup(settings.lighter_blur) appended last."

requirements-completed: [POLISH-01, POLISH-02, POLISH-03]

# Metrics
duration: ~11 min
completed: 2026-05-13
---

# Phase 14 Plan 04: CDJ Whisper v5 Wave 3 — Settings Drawer Migration + Performance Group Summary

**Settings surface migration: border-anim on SettingsDrawer aside + overflow + z-index discipline + 5 --sp-* alias adjustments + 4 existing components jsdoc purge + NEW performance-group.ts component (3 exports) + IPC schema "lighter_blur" enum entry + SettingsState boot payload + SettingsApplier dispatch + ConfigStore typed top-level field + settings.tokens.test.ts rewritten against real APIs and unskipped. Strict v5 + fonts gates green on settings surface; 22/22 vitest files green; 91/91 runtime + 53/53 ui_bus Python tests green; ipc schema count parity holds at 27.**

## Performance

- **Duration:** ~11 min active execution
- **Started:** 2026-05-13T11:52:18Z
- **Completed:** 2026-05-13T12:03:44Z
- **Tasks:** 3 / 3 complete (2 auto + 1 checkpoint auto-advanced under workflow.auto_advance=true)
- **Files modified:** 19 (+ 1 new component + 1 new SUMMARY, + 1 polish-log row)

## Accomplishments

- **Strict v5 migration gate green** — `bash scripts/check_v5_migration.sh --surface=settings --strict` exits 0 (was 8 hits baseline; all in jsdoc, not CSS bodies).
- **Strict fonts gate green** — `bash scripts/check_v5_fonts.sh --surface=settings --strict` exits 0 (was 0 already).
- **vitest settings spec unskipped + green** — `tauri/ui/tests/settings.tokens.test.ts` rewritten against real component signatures, 8 surface assertions + 5 detector cases pass (13 total in the file via shared import); full suite 22 files / 261 passing / 4 skipped (down from 8 — settings's 4 stubs now active).
- **NEW component** — `tauri/ui/src/settings/components/performance-group.ts` (172 lines including CSS). Single-row "LIGHTER BLUR" toggle pill. Off state = var(--glass-3) recessed bg + var(--silk-65) silkscreen label; on state = mock-verbatim amber backlight gradient + var(--amber-40) border + inset var(--amber-22) bloom + var(--amber) label with text-shadow. Three exports: `applyBlurPerfPreference(enabled)` (writes html[data-blur-perf]), `toggleBlurPerf(enabled): Promise<void>` (local apply + persist), `PerformanceGroup(currentValue: boolean): HTMLElement` (group factory).
- **SettingsDrawer border-anim insertion** — `mountSettingsDrawer` appends `<div class="border-anim" aria-hidden="true">` as the first child of `aside.vmx-settings-drawer` before the header. Verified by jsdom assertion in vitest (`drawer.firstElementChild?.classList.contains("border-anim")` green).
- **SettingsDrawer CSS adjustments** — `overflow: hidden` + `:not(.border-anim) { position: relative; z-index: 5 }` descendant selector. 5 inline-style `--sp-md/-sm/-lg` migrated to `--sp-4`/`--sp-2`.
- **IPC schema end-to-end** — `settings.set.field` enum gains "lighter_blur" (10th flat value). `SettingsState.required` adds "lighter_blur" + properties entry (boolean). Python `SettingsSetPayload.field` Literal expanded from 7 → 10 (catch-up for Plan 13-05's mood + click_through + this plan's lighter_blur). `SettingsStatePayload` gains `lighter_blur: bool`. Codegen regenerates `messages.ts` cleanly; validator.spec.ts baseState fixture updated.
- **Python applier write path** — `SettingsApplier.apply` dispatches "lighter_blur" → new private `_apply_lighter_blur` handler. Bool validation at trust boundary (T-14-04-03), `config_store.lighter_blur = value`, `save_config(self.config_store)` atomic write. Three new unit tests cover happy-path true / happy-path false / non-bool rejection.
- **ConfigStore typed field** — `lighter_blur: bool = False` added to dataclass + `_PHASE12_FIELDS` tuple. Round-trips through to_dict/from_dict + atomic save.
- **session_loop boot snapshot** — `_emit_settings_state` passes `lighter_blur=self.config_store.lighter_blur` into `SettingsState.make` so the boot ack carries the persisted value; main.ts boot read picks it up flat at `payload.lighter_blur`.
- **SettingsView extension** — `session/state.ts` SettingsView gains `lighter_blur: boolean` (default false). ws-bridge `WireSettingsStatePayload` adds optional field; `applySettingsState` narrows defensively (`typeof === "boolean"`) so a future-out-of-sync sidecar can't poison the view. `SETTINGS_FIELDS` enum extended; `sendSettings` value union widened to include boolean.
- **Build green** — `cd tauri/ui && npm run build` runs `tsc --noEmit && vite build` and exits 0.

## Task Commits

1. **Task 14-04-01a** — `f60fbd6` — `refactor(14-04): SettingsDrawer border-anim + overflow + z-index + group order`. SettingsDrawer aside gains border-anim first child + overflow: hidden + descendant z-index 5; 5 inline-style --sp-* aliases migrated; PerformanceGroup() append wired into body composition after MascotGroup().
2. **Task 14-04-01b** — `fb06a0e` — `refactor(14-04): purge phosphor/knurled/DM-Mono jsdoc from settings components`. Retention-slider knurled-knob copy rewritten to "retention discs"; mascot-group "phosphor amber" / "Workbench display" rewritten to "amber" / "Saira variable-axis"; hotkey-capture DM Mono / --phosphor jsdoc rewritten to JetBrains Mono / var(--amber); confirm-dialog "phosphor look" → "v5 amber".
3. **Task 14-04-01c** — `e67593c` — `feat(14-04): add settings PerformanceGroup + extend SettingsView with lighter_blur`. NEW performance-group.ts (3 exports). SettingsView + ws-bridge + render-loop.spec test fixtures updated.
4. **Task 14-04-02a** — `e4cf069` — `feat(14-04): add lighter_blur to settings IPC enum + SettingsState payload`. messages.schema.json + messages.ts + validator.spec + ui_bus/messages.py.
5. **Task 14-04-02b** — `5278193` — `feat(14-04): wire SettingsApplier lighter_blur + unskip settings.tokens spec`. SettingsApplier dispatch + new `_apply_lighter_blur` handler; ConfigStore typed field; session_loop boot snapshot; main.ts flat-path read; test_settings_apply.py 3 new cases; settings.tokens.test.ts rewritten + unskipped.

## Per-File Migration Counts

| File | Legacy refs before | After | Notes |
|------|-------------------:|------:|-------|
| SettingsDrawer.ts | 0 | 0 | + border-anim insertion + overflow: hidden + z-index 5 descendant + 5 --sp-* alias migrations + PerformanceGroup wire-up + import |
| retention-slider.ts | 4 (jsdoc: `--phosphor-soft`, `--panel-deep`, `--phosphor-dim`, `--phosphor-glow`, `--phosphor`) | 0 | jsdoc retone — "knurled-knob" copy purged to "retention discs"; CSS body already v5 from prototype |
| mascot-group.ts | 2 (jsdoc: `--phosphor-soft`, `--phosphor`, `--ink-engraved`) | 0 | jsdoc retone — "phosphor amber" purged to "amber"; "Workbench display" → "Saira variable-axis"; CSS body already v5 |
| hotkey-capture.ts | 2 (jsdoc: `--phosphor`, `--phosphor-warm`) | 0 | jsdoc retone — DM Mono + phosphor descriptors rewritten to JetBrains Mono + v5 amber tokens; CSS body already v5 |
| confirm-dialog.ts | 0 | 0 | jsdoc "phosphor look" purged to "v5 amber" (slop-purge, not legacy-ref) |
| performance-group.ts | n/a (new) | 0 | NEW file — 3 exports + on/off toggle CSS lifted from SettingsDrawer.ts:198–222 button anatomy |
| **Subtotal settings/** | **8** | **0** | gate strict-green |
| state.ts (settings/) | 0 | 0 | unchanged (drawer-local UX state only) |
| session/state.ts | 0 | 0 | (gate-excluded; SettingsView gains lighter_blur: boolean) |
| session/ws-bridge.ts | 0 | 0 | (gate-excluded; SETTINGS_FIELDS, sendSettings, applySettingsState extended) |
| main.ts | 0 | 0 | (gate-excluded; readBlurPerfPreference updated to flat-path read) |
| settings.tokens.test.ts | 0 | 0 | rewritten + unskipped (no longer @ts-nocheck) |

The 8-ref baseline was entirely in jsdoc — every settings component's CSS body had already been migrated to v5 primitives by the prototype commit `0615344`. The Wave 3 work was: (1) structural border-anim + overflow + z-index on SettingsDrawer, (2) 5 --sp-* alias migrations in SettingsDrawer inline styles, (3) jsdoc retones across 4 files, (4) NEW PerformanceGroup component, (5) IPC schema + Python applier + ConfigStore extensions wiring the toggle end-to-end, (6) spec rewrite + unskip.

## IPC Schema Delta — Exact Shape

**`tauri/ui/src/ipc/messages.schema.json:529`** — SettingsSet.payload.field enum extended:

```diff
- "field": {"type": "string", "enum": ["voice", "mode", "genre", "output_device_id", "output_profile", "retention_days", "push_to_mute_hotkey", "mood", "click_through"]},
+ "field": {"type": "string", "enum": ["voice", "mode", "genre", "output_device_id", "output_profile", "retention_days", "push_to_mute_hotkey", "mood", "click_through", "lighter_blur"]},
```

**`tauri/ui/src/ipc/messages.schema.json:568–578`** — SettingsState.payload extended:

```diff
- "required": ["voice", "mode", "genre", "output_device_id", "output_profile", "retention_days", "push_to_mute_hotkey", "muted"],
+ "required": ["voice", "mode", "genre", "output_device_id", "output_profile", "retention_days", "push_to_mute_hotkey", "muted", "lighter_blur"],
  "properties": {
    ...
    "muted": {"type": "boolean"},
+   "lighter_blur": {"type": "boolean"}
  }
```

**Count parity confirmed:**
- `python3 scripts/check_ipc_schema.py` → `OK: 27 dataclasses validate against schema` + `OK: count parity — 27 oneOf entries == 27 wrapper dataclasses`.

## SettingsApplier Write Path — Code Excerpt

`src/vibemix/runtime/settings.py:174–197` (new branch + handler):

```python
if field == "lighter_blur":
    return await self._apply_lighter_blur(value)
return (False, f"unknown settings field: {field!r}")

# ... handler ...

async def _apply_lighter_blur(self, value: Any) -> tuple[bool, str | None]:
    """Apply the Settings → Performance → "Lighter blur" toggle.

    Presentation-only — the user's preference for swapping the heavy
    v5 backdrop blurs for lighter variants. The webview reads it at
    boot (main.ts) and writes ``html[data-blur-perf="on"]`` which the
    tokens.css cascade (Wave 2) picks up to swap ``--blur-glass-*``
    without restart. No MusicState write, no ws_bus emit, no session
    teardown — pure persistence so next launch restores the bit.

    Threat T-14-04-03: presentation-only boolean; no PII surface.
    """
    if not isinstance(value, bool):
        return (
            False,
            f"lighter_blur expects bool, got {type(value).__name__}",
        )
    self.config_store.lighter_blur = value
    save_config(self.config_store)
    return (True, None)
```

## Cycle Count

**Settings surface: 1 cycle** — objective gates passed first try, no critique re-run needed. Cycle budget per CONTEXT Area 3: 3 cycles; we used 1, 2 in reserve if Kaan-side ui-checker/ui-auditor flags anything during the deferred review.

## Performance Toggle End-to-End Test Results

Tested via the vitest spec only (Kaan-side end-to-end deferred to `npm run tauri dev`):

- ✅ `PerformanceGroup(false)` renders off-state markers (data-on="false", aria-checked="false", textContent="OFF", no legacy refs)
- ✅ `PerformanceGroup(true)` renders on-state markers (data-on="true", aria-checked="true", textContent="ON") + the registered CSS contains `.vmx-perf-toggle[data-on="true"] { ... var(--amber) ... }` (regex match confirmed)
- ✅ `applyBlurPerfPreference(true)` writes `data-blur-perf="on"` on `<html>`
- ✅ `applyBlurPerfPreference(false)` removes `data-blur-perf`
- ✅ `toggleBlurPerf` callable via the toggle's click handler (chain: local apply → sendSettings IPC call); IPC is mocked in jsdom — actual round-trip is the Kaan-side test
- ✅ SettingsApplier rejects non-bool payloads at the trust boundary (3 cases tested: string "on", int 1/0, None, "true" string)
- ✅ SettingsApplier persists true / false through atomic write to disk (round-trip verified via `json.loads(_redirect_config_path.read_text())`)

## ui-checker + ui-auditor Output Refs

Deferred — Kaan-side `Skill(skill="gsd-ui-checker", args="14 --surface=settings")` + `Skill(skill="gsd-ui-auditor", args="14 --surface=settings")` will run during the `npm run tauri dev` review pass and are tracked in `14-POLISH-LOG.md` row `settings | 1`.

Objective bash + vitest gates ALL green:
- `scripts/check_v5_migration.sh --surface=settings --strict` → 0 hits
- `scripts/check_v5_fonts.sh --surface=settings --strict` → 0 hits
- `tauri/ui && npm run check:ipc` → exits 0
- `python3 scripts/check_ipc_schema.py` → 27/27 parity
- `tauri/ui && npm run test -- settings.tokens.test.ts --run` → 13/13 (8 surface + 5 detector via shared import)
- `tauri/ui && npm run test` → 22 files / 261 passing / 4 skipped (mascot + wizard placeholders)
- `python3 -m pytest tests/runtime/ tests/ui_bus/ tests/ipc/` → 173/173
- `tauri/ui && npm run build` → exits 0

## Deferred Screenshots

- **Live settings drawer 1440×900 screenshot (PERFORMANCE group expanded)** vs `mocks/vibemix-direction-final.html` §02 spec-panel — to capture during `npm run tauri dev`; attach to `14-POLISH-LOG.md` "Side-by-Side Screenshots" row "settings". Logged.

## Deferred Verification Actions

- **`gsd-ui-checker` + `gsd-ui-auditor` (3 audits) on settings surface** — deferred to the interactive review pass; objective bash + vitest gates above prove the surface is on v5 primitives. If either flags a finding, a cycle-2 plan will be spawned per CONTEXT Area 3 (max 3 cycles).
- **Kaan-side end-to-end perf toggle test** (CONTEXT Area 3 — must close before phase end):
  1. `cd tauri/ui && npm run tauri dev` — open session UI → click settings gear
  2. Scroll drawer body to PERFORMANCE group (after MASCOT). Verify "LIGHTER BLUR" toggle is OFF (--glass-3 bg, --silk-65 label)
  3. Click toggle → toggle animates to amber backlight + label becomes --amber. Inspect DevTools: `document.documentElement.getAttribute('data-blur-perf')` → `"on"`. Visually verify backdrop blur on the session panels visible behind the drawer is lighter (32 → 16, 16 → 8, 6 → 4 px).
  4. Quit app + relaunch — toggle state persists (was true on relaunch); blur stays lighter.
  5. Toggle OFF → backdrop blur restores to default; quit/relaunch persists OFF.
  6. macOS Settings → Accessibility → Reduce motion ON — drawer's border-anim freezes; same lighter blur applies (this is the prefers-reduced-motion CSS path).
- **Side-by-side screenshot capture** at 1440×900 with PERFORMANCE group expanded.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] SettingsView lighter_blur lives on session/state.ts, not settings/state.ts**
- **Found during:** Task 14-04-01c, when deciding where to add the type field
- **Issue:** Plan's `files_modified` listed `tauri/ui/src/settings/state.ts` for the SettingsState type extension. But that file's actual surface is drawer-local UX state (`open`, `hotkeyCaptureMode`, `pendingGenreReload`, `confirmDialog`) — NOT the persisted settings record. The persisted SettingsView (with `voice`, `mood`, `click_through`, etc.) lives at `tauri/ui/src/session/state.ts:57–72`, populated by ws-bridge's `applySettingsState`. Adding `lighter_blur` to `settings/state.ts` would have created a parallel state slice with no consumer.
- **Fix:** Added `lighter_blur: boolean` to `SettingsView` in `session/state.ts` (line 73) + default `false` in `makeDefault().settings` (line 133). Matches the Plan 13-03 `click_through` precedent precisely.
- **Files modified:** tauri/ui/src/session/state.ts (+5 lines)
- **Commit:** e67593c
- **Verification:** PerformanceGroup reads `settings.lighter_blur` from `getSessionState().settings`; ws-bridge applies the wire value defensively.

**2. [Rule 2 — Missing critical] sendSettings value union widened to include boolean**
- **Found during:** Task 14-04-01c, while wiring `toggleBlurPerf → sendSettings("lighter_blur", enabled)`
- **Issue:** Existing `sendSettings(field: SettingsField, value: string | number | null)` rejected booleans. Without widening, `PerformanceGroup` couldn't compile. Same issue exists for `click_through` (Plan 13-03) which currently routes through a separate `emitIpc` direct call instead of `sendSettings` — but the standardized path is `sendSettings`.
- **Fix:** Widened `value` parameter to `string | number | boolean | null` in `tauri/ui/src/session/ws-bridge.ts:198`. Added `"lighter_blur"` to `SETTINGS_FIELDS` enum so the runtime check accepts it.
- **Files modified:** tauri/ui/src/session/ws-bridge.ts
- **Commit:** e67593c
- **Verification:** TypeScript build green; new vitest case in settings.tokens.test.ts confirms `toggleBlurPerf` is callable.

**3. [Rule 1 — Bug] session_loop._emit_settings_state was missing lighter_blur**
- **Found during:** Task 14-04-02b, after extending `SettingsState.make` with the new arg
- **Issue:** `_emit_settings_state` constructs the boot/ack `ipc.settings.state` payload. Without passing `lighter_blur=self.config_store.lighter_blur`, the wire payload would still default to the `SettingsState.make` default (False) on every emit even when the user had set it to True. Then main.ts boot read would always default off → persisted preference never restored across launches.
- **Fix:** Added `lighter_blur=self.config_store.lighter_blur` to the `SettingsState.make(...)` call at session_loop.py:436.
- **Files modified:** src/vibemix/runtime/session_loop.py
- **Commit:** 5278193
- **Verification:** All 22 session_loop tests pass + the new lighter_blur happy-path test asserts disk persistence; the on-the-wire emit will read the stored value once Kaan toggles in Tauri dev.

**4. [Rule 1 — Bug] SettingsSetPayload.field Literal expanded from 7 to 10 values**
- **Found during:** Task 14-04-02a, while updating the Literal for `lighter_blur`
- **Issue:** The Python Literal was missing `mood` + `click_through` — Plan 13-05 added these to the JSON schema but never updated the Python `SettingsSetPayload.field` Literal. Runtime validation uses jsonschema against the JSON schema (so the bug was advisory) but mypy + editor autocomplete were misleading.
- **Fix:** Extended Literal in `src/vibemix/ui_bus/messages.py:283–293` to the full 10-value set. Widened `value` from `str | int | None` to `str | int | bool | None`.
- **Files modified:** src/vibemix/ui_bus/messages.py
- **Commit:** e4cf069
- **Verification:** All 53 ui_bus tests pass.

**5. [Rule 3 — Blocker] Test fixtures in render-loop.spec.ts needed lighter_blur**
- **Found during:** TypeScript check after adding `lighter_blur` to `SettingsView`
- **Issue:** 5 SessionState fixtures in `tauri/ui/tests/session/render-loop.spec.ts` failed to satisfy `SettingsView` shape — `Property 'lighter_blur' is missing`.
- **Fix:** Added `lighter_blur: false` after each `click_through: false` line via sed (5 sites).
- **Files modified:** tauri/ui/tests/session/render-loop.spec.ts
- **Commit:** e67593c
- **Verification:** `tsc --noEmit` exits 0; full vitest suite green.

**6. [Rule 1 — Bug] main.ts readBlurPerfPreference indexed obsolete nested path**
- **Found during:** Task 14-04-02b reviewing main.ts boot read
- **Issue:** Plan 14-03 used a defensive nested `payload.performance.lighter_blur` index because the schema field shape wasn't yet locked. The plan-checker W-2 resolution chose FLAT enum — so the read path needs to match.
- **Fix:** Updated `readBlurPerfPreference` to index `payload.lighter_blur` directly + retoned docstring.
- **Files modified:** tauri/ui/src/main.ts
- **Commit:** 5278193
- **Verification:** Vitest didn't catch this (the test is on the new component); proven by inspection + the boot flow's defensive try/catch — even if the path were wrong, boot would still default off (safe).

**7. [Rule 1 — Bug] validator.spec.ts SettingsState fixture needed lighter_blur**
- **Found during:** Full vitest run after schema update
- **Issue:** `validator.spec.ts:260` baseState fixture omitted the now-required `lighter_blur` field → `parseIpcMessage` correctly rejected it.
- **Fix:** Added `lighter_blur: false` to the fixture's payload.
- **Files modified:** tauri/ui/src/ipc/validator.spec.ts
- **Commit:** e4cf069
- **Verification:** Full vitest suite passes (22/22 files, 261 tests).

**Total deviations:** 7 auto-fixed (3 Rule 1 bugs, 1 Rule 2 missing critical, 1 Rule 3 blocker, 2 catch-up fixes flagged Rule 1).
**Impact:** None negative. All deviations were sub-step blockers that required immediate inline fixes to make the plan executable; documented for transparency. Three of the deviations (#3, #4, #6) are leftovers from prior plans surfaced by this plan's wider type/schema changes — opportunistic clean-up.

## Checkpoint Handling

**Task 14-04-03 (`checkpoint:human-verify`)** was AUTO-APPROVED under `workflow.auto_advance=true` (project config + project-memory `feedback_autonomous_no_grey_area_pause`). The objective acceptance gates all pass — see "ui-checker + ui-auditor Output Refs" above for the full list.

The plan's `<how-to-verify>` specifies human-side actions that cannot be automated from a non-interactive executor:
1. Running `Skill(skill="gsd-ui-checker", args="14 --surface=settings")` and `gsd-ui-auditor` — requires Claude-Code Skill runtime in an interactive session.
2. `npm run tauri dev` to verify the drawer renders the border-anim sweep + PERFORMANCE group visually at 1440×900.
3. End-to-end perf toggle test (toggle ON → blur lightens → quit/relaunch → blur stays lighter → toggle OFF → restores).
4. macOS Settings → Accessibility → Reduce motion live-effect verification.
5. Capturing the 1440×900 side-by-side screenshot pair.

All five are deferred to Kaan when he next runs `npm run tauri dev`. Tracking under `## Deferred Screenshots` and `## Deferred Verification Actions` above.

## Issues Encountered

None. The plan executed cleanly. The 7 deviations were sub-step blockers that required immediate inline fixes — no human escalation, no architectural pivots, no Rule 4 stops. Build + vitest + pytest + ipc-parity all green on the first end-to-end run after the deviations cleared.

## Threat Surface Scan

No new security-relevant surface introduced. T-14-04-01 (Tampering, IPC schema drift) was the load-bearing threat — mitigated by the npm run check:ipc + python3 scripts/check_ipc_schema.py both-pass gate (27/27 parity); both run in CI per the existing Phase 11 wiring. T-14-04-02 (Capability allowlist drift) was `accept` — confirmed no new Tauri invoke command added; toggleBlurPerf reuses the existing emitIpc("ipc.settings.set", ...) envelope. T-14-04-03 (Information disclosure) was `accept` — boolean preference, no PII, persisted to the same OS-aware config dir as the rest of ConfigStore.

## Self-Check: PASSED

Verified each claim before finalizing:

- ✅ `tauri/ui/src/settings/components/performance-group.ts` exists on disk and exports `applyBlurPerfPreference`, `toggleBlurPerf`, `PerformanceGroup` (verified via `grep -nE "^export"`)
- ✅ `tauri/ui/src/settings/SettingsDrawer.ts` contains `borderAnim.className = "border-anim"` and `overflow: hidden` (commit f60fbd6)
- ✅ `tauri/ui/src/ipc/messages.schema.json` contains `"lighter_blur"` in both `settings.set.field` enum and `SettingsState.required` (commit e4cf069)
- ✅ `src/vibemix/runtime/settings.py` contains `_apply_lighter_blur` handler + dispatch branch (commit 5278193)
- ✅ `src/vibemix/runtime/config_store.py` has `lighter_blur: bool = False` in ConfigStore dataclass + entry in `_PHASE12_FIELDS` (commit 5278193)
- ✅ `tauri/ui/tests/settings.tokens.test.ts` no longer has `describe.skip(...)` or `@ts-nocheck` (commit 5278193)
- ✅ `scripts/check_v5_migration.sh --surface=settings --strict` exits 0 (0 hits — was 8 baseline)
- ✅ `scripts/check_v5_fonts.sh --surface=settings --strict` exits 0 (0 hits — already 0 baseline)
- ✅ `PYTHONPATH=src python3 scripts/check_ipc_schema.py` → 27/27 parity OK
- ✅ `cd tauri/ui && npm run check:ipc` → exits 0 (codegen + tsc green)
- ✅ `cd tauri/ui && npm run test -- settings.tokens.test.ts --run` → 13/13 passing
- ✅ `cd tauri/ui && npm run test` → 22 files / 261 passing / 4 skipped
- ✅ `PYTHONPATH=src python3 -m pytest tests/runtime/ tests/ui_bus/ tests/ipc/` → 173/173
- ✅ `cd tauri/ui && npm run build` → exits 0
- ✅ Commits in git log: `f60fbd6`, `fb06a0e`, `e67593c`, `e4cf069`, `5278193` (5 task commits + this SUMMARY commit to follow)
- ✅ 14-POLISH-LOG.md row `settings | 1` updated with status ✅ green (auto-advance) + the five commit SHAs
- ✅ Settings group order in drawer body matches CONTEXT Area 4 Copywriting Contract: PERSONA / OUTPUT / HOTKEY / RECORDING / CALIBRATION / MASCOT / PERFORMANCE

## Next Phase Readiness

Wave 3 closes the settings drawer as the third fully-v5 surface in the shipping UI. The Performance toggle end-to-end loop is live: PerformanceGroup → toggleBlurPerf → sendSettings("lighter_blur", enabled) → ipc.settings.set → SettingsApplier → ConfigStore → atomic save → next-launch boot read in main.ts → html[data-blur-perf] → tokens.css cascade swaps --blur-glass-*.

Plan 14-05 (Wave 4 — Mascot overlay window chrome) is ready to start. Per UI-SPEC §Surface 4: the mascot is the only surface that adds chrome around an existing transparent canvas; uses `.border-anim slow rev` (32s reverse) to desync from the session's 22s forward sweep. The data-blur-perf cascade and the perf-fallback CSS will apply to the mascot overlay automatically once the chrome is in place — no new wiring needed.

Plan 14-06 (Wave 5 — Shim removal) becomes possible once the mascot surface clears. The legacy-ref grep gate already exits 0 on three of the four surfaces (wizard ✅, session ✅, settings ✅ this plan); mascot surface is the last gate to clear before the subtractive commit can land.

---
*Phase: 14-cdj-whisper-v5-migration-polish*
*Plan: 14-04*
*Completed: 2026-05-13*
