---
phase: 13-3d-mascot-overlay
plan: 03
subsystem: ui
tags: [tauri, vanilla-ts, vitest, ipc, settings-drawer, mascot, frontend-enforcement]

# Dependency graph
requires:
  - phase: 12-live-session-ui-settings
    provides: "SettingsDrawer + Group wrapper + renderRocker + SessionState singleton + ws-bridge.applySettingsState"
  - phase: 11-tauri-shell-calibration-wizard
    provides: "emitIpc + invoke + registerStyle + tokens.css phosphor palette"
provides:
  - "SessionState.settings.mood ('hype-man' | 'teacher' | 'coach', default hype-man)"
  - "SessionState.settings.click_through (boolean, default false)"
  - "MascotGroup() settings component — phosphor-amber pill row for mood + binary rocker for click-through"
  - "Defensive mood-narrowing at the ws-bridge boundary (T-13-03-01 mitigation)"
  - "Cohost transcript header reshape — 42x42 mascot bubble dropped, AVERY chip + status row only"
affects: [13-02-mascot-overlay-window, 13-04-mascot-renderer, 13-05-ipc-mood-schema, 13-06-event-dispatcher]

# Tech tracking
tech-stack:
  added: []  # No new deps — reused renderRocker + Group + registerStyle from Phase 11/12
  patterns:
    - "Defensive enum-narrowing on IPC boundary (whitelist + fallback to current state value) for tampering mitigation"
    - "vi.hoisted() pattern for shared vi.fn() refs across vi.mock factory + test assertions"
    - "Settings group via existing Group() wrapper — no new container component"

key-files:
  created:
    - tauri/ui/src/settings/components/mascot-group.ts
    - tauri/ui/tests/settings/mascot-group.spec.ts
    - tauri/ui/tests/session/cohost.spec.ts
    - .planning/phases/13-3d-mascot-overlay/deferred-items.md
  modified:
    - tauri/ui/src/session/components/cohost.ts
    - tauri/ui/src/session/state.ts
    - tauri/ui/src/session/ws-bridge.ts
    - tauri/ui/src/settings/SettingsDrawer.ts
    - tauri/ui/tests/session/components.spec.ts
    - tauri/ui/tests/session/render-loop.spec.ts

key-decisions:
  - "Test files named *.spec.ts under tests/ instead of *.test.ts under src/ — vitest.config.ts globs only on *.spec.ts so the plan's nominal paths would silently skip the new assertions in default suite runs"
  - "MascotMood exported as a named type from session/state.ts so ws-bridge can import it for narrowing — keeps the union literal single-sourced"
  - "Click-through toggle reuses renderRocker with two options (off/on) rather than authoring a new toggle shape — honours Plan 13-03 frontend_enforcement_constraints"
  - "Mood pill active-state uses --phosphor-soft + --phosphor + --phosphor-dim border + phosphor halo (matches the existing interaction-rocker active-state pattern, 20/80 rule preserved — only the active pill carries accent)"
  - "ws-bridge defensively narrows incoming mood (whitelist) + click_through (typeof boolean) and falls back to current SessionState value when sidecar omits or sends a stray string — T-13-03-01 tampering mitigation kept entirely on the receive boundary, no UI exception path"

patterns-established:
  - "Settings boundary narrowing: WireSettingsStatePayload.mood?: MascotMood | string + narrowMood() helper drops anything not in VALID_MOODS"
  - "Plan-aligned testing under tests/: when a plan names a test path that vitest's config glob doesn't pick up, route to the conventional path AND mirror the assertion in the relevant existing spec so both the plan-named file and the suite assertion exist"

requirements-completed: [MASCOT-02, MASCOT-07]

# Metrics
duration: ~20min
completed: 2026-05-12
---

# Phase 13 Plan 03: Drop Mascot Placeholder + MASCOT Settings Group Summary

**Phase 12 cohost-header bubble removed and replaced by a MASCOT settings group exposing click-through + mood, with defended-at-boundary narrowing of the mood enum.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2/2 atomic commits
- **Files modified:** 6 (+4 created)

## Accomplishments

- Dropped the 42×42 mascot placeholder bubble from the Phase 12 cohost transcript header — the AVERY chip + LISTENING/TALKING/IDLE status row is now the only content (honours CONTEXT.md Open Q 2: "corner dropped entirely", "it IS the AI, dancing on your screen").
- Extended `SessionState.settings` with `mood: MascotMood` (default `"hype-man"`) and `click_through: boolean` (default `false`) — wired through ws-bridge with whitelist-narrowed mood handling so a stray future string from the sidecar can't poison the `MascotMood` union (T-13-03-01 mitigation).
- New MASCOT settings group lives at the bottom of the drawer (PERSONA / OUTPUT / HOTKEY / RECORDING / CALIBRATION / **MASCOT**) — binary rocker for click-through, 3 segmented pills for mood, all colors via `var(--phosphor*)` + `var(--ink-dim)` + `var(--bezel-*)` (zero hex literals, full frontend-enforcement compliance).
- 13 new vitest assertions across 2 new spec files; full suite still green (155/155).

## Task Commits

1. **Task 1: Drop mascot placeholder + extend SessionState.settings + ws-bridge narrowing** — `5b3e304` (feat)
2. **Task 2: Create MascotGroup settings component + wire into SettingsDrawer + spec** — `ec20f40` (feat)

## Cohost Header Reshape (before → after)

```
BEFORE (Phase 12):
  [42×42 mascot bubble]  [AVERY                ]
                         [● LISTENING          ]
  ─────────────────── transcript ────────────────

AFTER (Phase 13-03):
  [AVERY                                       ]
  [● LISTENING                                 ]
  ─────────────────── transcript ────────────────
```

The freed vertical space gives the meters + transcript more breathing room per CONTEXT.md Area 2 ("breathing room around the meters + transcript"). No SessionLayout edits — the right column is fixed at `var(--col-right) = 420px` so the reshape stays purely within the cohost component's header.

## MASCOT Group Shape

```
┌─ MASCOT ─────────────────────────────────────┐
│  CLICK-THROUGH                                │
│  [   OFF   |   ON   ]   (rocker variant)     │
│                                               │
│  MOOD                                         │
│  [ HYPE-MAN ] [ TEACHER ] [ COACH ]          │
│    (active pill = --phosphor-soft fill,      │
│     --phosphor text, phosphor halo + inset)  │
└───────────────────────────────────────────────┘
```

- Click-through rocker `onChange` → `invoke('set_mascot_click_through', { enabled })` + `emitIpc('ipc.settings.set', { field: 'click_through', value })` (both fire so Rust overlay state + sidecar settings store sync).
- Mood pill click → `emitIpc('ipc.settings.set', { field: 'mood', value })`. Already-active pill click is a no-op (idempotency).
- Group rebuilds with the drawer body on every refresh (same lifecycle as the other 5 groups) — no separate SessionState subscription.

## Files Created/Modified

- `tauri/ui/src/settings/components/mascot-group.ts` — new MascotGroup component (255 lines, scoped CSS injected via registerStyle)
- `tauri/ui/src/settings/SettingsDrawer.ts` — import + append MascotGroup() as the 6th drawer group
- `tauri/ui/src/session/components/cohost.ts` — MASCOT_PLACEHOLDER_SVG import + .vmx-cohost__mascot CSS rules + placeholder div all removed; module docstring updated
- `tauri/ui/src/session/state.ts` — exported MascotMood literal + extended SettingsView + extended makeDefault().settings
- `tauri/ui/src/session/ws-bridge.ts` — WireSettingsStatePayload.mood?/click_through? + narrowMood() helper + applySettingsState preserves Phase 13 fields when sidecar omits them
- `tauri/ui/tests/settings/mascot-group.spec.ts` — 10 vitest assertions (render shape, SessionState reflection, IPC payloads, idempotency, hex-grep guard)
- `tauri/ui/tests/session/cohost.spec.ts` — 3 vitest assertions pinning the placeholder deletion across all statuses
- `tauri/ui/tests/session/components.spec.ts` — added a mascot-null assertion to the existing renderCohostPanel block
- `tauri/ui/tests/session/render-loop.spec.ts` — extended 5 settings-literal fixtures with the new fields (mood + click_through)
- `.planning/phases/13-3d-mascot-overlay/deferred-items.md` — logged pre-existing TS error in main.ts (out of scope)

## Decisions Made

1. **Test path convention over plan-nominal path.** Plan said `src/session/components/cohost.test.ts` and `src/settings/components/mascot-group.test.ts`. The vitest.config.ts glob is `*.spec.ts` only, so plan-nominal `*.test.ts` paths would skip the suite. Filed under `tests/session/cohost.spec.ts` + `tests/settings/mascot-group.spec.ts` AND mirrored the cohost mascot-null assertion in the existing `tests/session/components.spec.ts`.

2. **MascotMood exported from state.ts, imported into ws-bridge.** Keeps the literal single-sourced — the ws-bridge whitelist (VALID_MOODS) is declared once next to the narrow() helper and the type comes from the same place the SettingsView extension reads.

3. **Click-through reuses renderRocker (variant: "rocker") instead of a new toggle.** Plan's frontend_enforcement_constraints explicitly said "Toggle uses the existing rocker.ts component" — passes the rocker `{ id: "off" | "on" }` options + maps boolean ↔ id at the edges.

4. **No SessionState subscription inside MascotGroup.** The drawer's `refresh()` already rebuilds the entire body on every UI/state change (same pattern as PERSONA / OUTPUT / HOTKEY). Adding a dedicated subscriber here would either double-rebuild on every ipc.settings.state ack or fight the drawer lifecycle.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `npm install` was not run in the worktree**
- **Found during:** Task 1 verification (npm run check:ipc failed with `Cannot find package 'json-schema-to-typescript'`)
- **Issue:** Worktree's `tauri/ui/node_modules` was empty — the codegen script couldn't load its deps so the TS compile gate never ran.
- **Fix:** `cd tauri/ui && npm install` (112 packages, no lockfile churn).
- **Verification:** `npm run check:ipc` then proceeded to its real check.
- **Committed in:** n/a — runtime setup only, no repo changes (`node_modules` is .gitignore'd).

**2. [Rule 1 - Bug + Rule 2 - Critical] `WireSettingsStatePayload` would have type-errored after `SettingsView` extension**
- **Found during:** Task 1 first `npm run check:ipc` (5 `tests/session/render-loop.spec.ts` errors + missing fields in `applySettingsState`).
- **Issue:** Plan only directed extending `SettingsView` — but `applySettingsState` builds a fresh settings object literal and `tests/session/render-loop.spec.ts` constructs SessionState literals in 5 places. Without compensating updates the compile breaks immediately AND there's no boundary defence for the new mood enum (T-13-03-01 mitigation called for in `<threat_model>`).
- **Fix:** Added `mood?: MascotMood | string` + `click_through?: boolean` to `WireSettingsStatePayload`; added `VALID_MOODS` whitelist + `narrowMood()` helper; `applySettingsState` now preserves current Phase 13 fields when sidecar omits them and narrows any incoming string to the union. Added `mood: "hype-man" as const, click_through: false` to all 5 `render-loop.spec.ts` settings fixtures.
- **Files modified:** `tauri/ui/src/session/ws-bridge.ts`, `tauri/ui/tests/session/render-loop.spec.ts`.
- **Verification:** `npm run check:ipc` succeeds for everything I touched; full vitest suite passes (155/155).
- **Committed in:** `5b3e304` (Task 1).

**3. [Rule 1 - Bug] `vi.mock` factory referenced an unhoisted `const`**
- **Found during:** Task 2 first vitest run on `mascot-group.spec.ts` (`Cannot access 'invokeMock' before initialization`).
- **Issue:** `vi.mock` is hoisted to file top by vitest's transformer; a `const invokeMock = vi.fn(...)` declared at module scope is still in the temporal dead zone when the factory runs.
- **Fix:** Switched to `const { invokeMock } = vi.hoisted(() => ({ invokeMock: vi.fn(...) }))` — both the mock fn and the factory are hoisted together so the spec can still inspect call args.
- **Files modified:** `tauri/ui/tests/settings/mascot-group.spec.ts`.
- **Verification:** All 10 mascot-group tests pass.
- **Committed in:** `ec20f40` (Task 2).

### Deferred (Out of Scope)

- **`src/main.ts(104,49): error TS2307: Cannot find module './session/mock.js'`** — Pre-existing at base commit (`6bb7cb6`). Logged in `.planning/phases/13-3d-mascot-overlay/deferred-items.md` for Plan 13-04 or earlier-phase fix-up to land the missing `src/session/mock.ts` companion file.

## Authentication Gates

None — entirely a frontend/UI plan.

## Threat Flags

None — no new network endpoints, no auth paths, no schema changes at trust boundaries beyond the IPC field additions which are already in the plan's `<threat_model>` register (T-13-03-01/02/03 all addressed by the defensive narrowing implemented in Task 1).

## Verification Results

| Check | Result |
|-------|--------|
| `npm run check:ipc` | PASS for plan-modified files; pre-existing `main.ts/mock.js` error documented |
| `grep -c 'vmx-cohost__mascot' src/session/components/cohost.ts` | 0 |
| `grep -c 'mood' src/session/state.ts` | 2 (type + default) |
| `grep -c 'click_through' src/session/state.ts` | 2 |
| `npx vitest run tests/session/cohost.spec.ts tests/settings/mascot-group.spec.ts` | 13/13 pass |
| `grep -E '#[0-9a-fA-F]{6}' src/settings/components/mascot-group.ts` | 0 matches |
| Full vitest suite (155 tests) | 155/155 pass |

## Self-Check: PASSED

- Files exist:
  - `tauri/ui/src/settings/components/mascot-group.ts` FOUND
  - `tauri/ui/tests/settings/mascot-group.spec.ts` FOUND
  - `tauri/ui/tests/session/cohost.spec.ts` FOUND
  - `.planning/phases/13-3d-mascot-overlay/deferred-items.md` FOUND
- Commits exist:
  - `5b3e304` (Task 1) FOUND
  - `ec20f40` (Task 2) FOUND
