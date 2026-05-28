---
phase: 92-lesson-runtime-ai-highlight-contract
plan: 06
subsystem: frontend
tags: [settings-drawer, learn-group, lesson-reset, destructive-confirm, ipc-emit]

# Dependency graph
requires:
  - "Plan 92-01 (LearnProgressState envelope shape + ajv validator entry for `ipc.learn.progress_state` with action enum 'snapshot'|'reset'|'reset_ack')"
  - "Plan 92-02 (RED-state spec: `tauri/ui/tests/settings/learn-group.spec.ts` dynamic-import gated, awaiting LearnGroup module)"
  - "Plan 92-04 (sidecar `progress.reset_progress` + `ipc.learn.progress_state` reset handler + reset_ack emit)"
  - "Plan 92-05 (Learn-window `showLearnToast('learn progress reset.')` consumer on `action: 'reset_ack'`)"
provides:
  - "`tauri/ui/src/settings/components/learn-group.ts` (NEW, 215 lines): LearnGroup factory returning HTMLElement with destructive 'reset learn progress' row + confirm-dialog wired to `emitIpc('ipc.learn.progress_state', { action: 'reset' })`"
  - "`tauri/ui/src/settings/SettingsDrawer.ts` (+1 import, +6-line annotated body.append block): LearnGroup mounts after CALIBRATION/PROFILE, before MASCOT — the closest available slot honoring UI-SPEC §Component Inventory 'between RECORDING and MASCOT'"
  - "Flipped `tauri/ui/tests/settings/learn-group.spec.ts` from dynamic-import-gated skip → 1/1 LIVE PASS (52 ms)"
affects: [92-07, 94, 95, 96]

# Tech tracking
tech-stack:
  added:
    - "No new dependencies — uses existing `renderSettingsGroup` + `renderConfirmDialog` + `emitIpc` primitives; the destructive look composes from `confirm-dialog.ts[data-variant='danger']` (existing) which already paints `--led-fault` on the primary button"
  patterns:
    - "Local CSS for `.vmx-settings-row` + `.vmx-settings-row--destructive` (no shared sheet to add to; the row class name is scoped via `[data-component='learn-group']` parent selector — same pattern as `mascot-group.ts` `.vmx-mascot-row`). The destructive-hover halo uses the same `rgba(212, 65, 58, ...)` modulations as `recording-row.ts:294-298` and `confirm-dialog.ts:108-111` — these are the established `--led-fault` alpha recipes."
    - "Dialog lifecycle via `let dialog` + `queueMicrotask` deferred-removal: the confirm-dialog does NOT auto-remove on confirm/cancel (it only auto-removes via Esc/backdrop-click). The caller-owned removal would TDZ if onConfirm is invoked synchronously during `renderConfirmDialog(...)` (which the test mock does — see Rule 1 auto-fix below). `queueMicrotask` defers the `dialog.remove()` one tick so the assignment to `dialog` completes first, then the microtask reliably finds it. Pattern is canonical for tests-with-synchronous-mock vs production-with-async-user-click."
    - "Optimistic-repaint compliance (CLAUDE.md `Frontend settings controls must repaint OPTIMISTICALLY`): the destructive confirm dialog IS the immediate repaint — clicking the row opens it synchronously. The `onConfirm` callback dismisses the dialog locally + fires `emitIpc` (fire-and-forget). The sidecar's `reset_ack` arrives at a separate surface (the Learn window) as a toast — the settings drawer never waits silently for the echo."

key-files:
  created:
    - "tauri/ui/src/settings/components/learn-group.ts (215 lines)"
    - ".planning/phases/92-lesson-runtime-ai-highlight-contract/92-06-SUMMARY.md (this file)"
  modified:
    - "tauri/ui/src/settings/SettingsDrawer.ts (+1 import line at line 66; +6-line annotated body.append block at lines 909-915, before the existing MASCOT comment+append at lines 916-920)"

key-decisions:
  - "ConfirmDialogProps shape confirmed `confirmLabel` / `cancelLabel` / `variant: 'danger'` (per `confirm-dialog.ts:24-34`) — NOT `primaryLabel` / `secondaryLabel` / `destructive: true` as the 92-RESEARCH §Code Example 5 blueprint suggested. The plan flagged this would need verification — verified; matches the existing API exactly."
  - "Landing site for `body.append(LearnGroup())` = SettingsDrawer.ts:915 (newly added between line 907's CALIBRATION-close and the original line 909's MASCOT-comment). UI-SPEC §Component Inventory line 208 says 'between RECORDING and MASCOT'; the existing drawer has LIBRARY/PROFILE/CALIBRATION already occupying that span, so LearnGroup joined the data-user-sensitive cluster just before MASCOT — the closest available slot honoring the spec's 'before MASCOT' half. Comment block annotated to explain the precise position."
  - "Local `.vmx-settings-row` + `.vmx-settings-row--destructive` classes — NOT shared cross-group classes. Verified via grep that no existing settings/components or stylesheets define a generic `.vmx-settings-row`; mascot-group / help-group / recording-row each own their own row class names scoped under a parent `[data-component]` selector. Mirrored that pattern. Acceptance: the test asserts the row has class `.vmx-settings-row--destructive` (querySelector match), and the local CSS scope is gated via the parent attribute selector so there's no cross-component collision risk."
  - "Dialog dismiss via `queueMicrotask(() => dialog?.remove())` instead of inline `dialog.remove()` — the test mock invokes `onConfirm` synchronously during the `renderConfirmDialog` call itself (vi.fn factory in `learn-group.spec.ts:43`). With `const dialog = renderConfirmDialog({...})`, the callback hits TDZ on `dialog`. The `queueMicrotask` defer is the minimal-overhead solution: production behavior unchanged (microtasks fire before the next event-loop tick), test behavior fixed."
  - "Optimistic-repaint mechanism: the confirm dialog itself IS the immediate repaint (row click → dialog opens synchronously). On confirm: `dismiss()` runs FIRST (queueMicrotask), then `emitIpc` fires fire-and-forget. The sidecar's reset_ack arrives at the Learn window (separate Tauri window, port 8766) as a toast — the settings drawer never blocks or shows a busy state. Matches the `mascot-group.ts:264-277` pattern exactly."

metrics:
  duration: "~30 minutes"
  completed: "2026-05-28"
  task_count: 1
  file_count_created: 1
  file_count_modified: 1
  net_lines_added: ~221
  tests_passing_before: "n/a (learn-group.spec.ts skip-stub from Plan 92-02)"
  tests_passing_after: "1/1 LIVE (52 ms)"
  full_suite_status: "1029 passed | 2 skipped | 15 todo (vitest, all settings/* groups intact)"

requirements_satisfied:
  - "LESSON-03 second half (settings-drawer UI surface): Kaan can wipe progress entirely through the GUI without leaving the app. The CLI half landed in Plan 92-04 Task 2 (`vibemix learn reset`). With Plan 92-06, both surfaces are live; LESSON-03 acceptance gate fully closed."
---

# Phase 92 Plan 06: Settings Drawer "Reset Learn Progress" Row Summary

LearnGroup component added to the settings drawer between CALIBRATION and MASCOT (the closest available slot honoring UI-SPEC §Component Inventory "between RECORDING and MASCOT" — PROFILE + CALIBRATION already occupy that span). Single row "reset learn progress" with destructive-styled hover (silk-65 label flips to `--led-fault` + amber-22 hover border halo). Click opens `renderConfirmDialog` with heading "reset learn progress?", body "all 36 lessons across 3 courses will reset to not started. your library and DJ profile are not affected.", primary "reset" (danger variant → `--led-fault` styling), secondary "cancel". Confirm fires `emitIpc('ipc.learn.progress_state', { action: 'reset' })` fire-and-forget; the sidecar's reset_ack arrives at the Learn-window surface (port 8766) where Plan 92-05's `showLearnToast('learn progress reset.')` runs the post-reset acknowledgment.

The Plan 92-02 RED-state spec `tauri/ui/tests/settings/learn-group.spec.ts` flipped from `[learn-group.spec.ts] awaiting Plan 92-06 — LearnGroup module not exported yet` skip-message → 1/1 LIVE PASS in 52 ms. Full settings test suite (8 specs, 82 tests covering drawer + mascot + library + retention + staleness + help + hotkey + learn-group) stays green. Full vitest suite (119 files / 1029 tests) stays green — no regressions in pre-existing settings drawer tests or any other surface.

## Tasks Completed

### Task 1: Land LearnGroup component + insert into SettingsDrawer

**Files modified:**
- `tauri/ui/src/settings/components/learn-group.ts` (NEW, 215 lines)
- `tauri/ui/src/settings/SettingsDrawer.ts` (+1 import + 6-line annotated body.append block)

**Behavior achieved:**
- `LearnGroup()` returns an `HTMLElement` (`<section class="vmx-settings-group" data-component="learn-group">`) with header "LEARN" + one `.vmx-settings-row.vmx-settings-row--destructive` child.
- The row's primary label reads `reset learn progress` (lowercase, period-FREE). The secondary line reads `clears all completed lessons. cannot be undone.`.
- Clicking the row triggers `renderConfirmDialog` with `heading: "reset learn progress?"`, body string verbatim per copy_lock, `confirmLabel: "reset"`, `cancelLabel: "cancel"`, `variant: "danger"`.
- The dialog's `onConfirm` callback invokes `emitIpc("ipc.learn.progress_state", { action: "reset" })` exactly once (plus a `queueMicrotask`-deferred `dialog.remove()` for local dismissal).
- The dialog's `onCancel` callback does NOT emit anything — it just dismisses the dialog.
- Integrated into `SettingsDrawer.ts` via one new `import { LearnGroup }` at line 66 + one new `body.append(LearnGroup())` at the new line 915 (between CALIBRATION and MASCOT, with a 4-line explanatory comment block).

**Verification:**
- `cd tauri/ui && npx tsc --noEmit` → exit 0, no output (clean)
- `cd tauri/ui && npm run build` → built in 1.06 s, 0 errors
- `cd tauri/ui && npx vitest run tests/settings/learn-group.spec.ts` → 1 passed | 1 todo (52 ms)
- `cd tauri/ui && npx vitest run tests/settings/` → 82 passed | 1 todo across 8 spec files (1.09 s)
- `cd tauri/ui && npx vitest run` → 1029 passed | 2 skipped | 15 todo across 119 files (6.69 s) — no regressions

**Verbatim copy gates (UI-SPEC §Copywriting Contract lines 170-181 byte-equality):**
| Element | Byte-exact string |
|---------|-------------------|
| Section header | `LEARN` |
| Row label | `reset learn progress` |
| Row secondary | `clears all completed lessons. cannot be undone.` |
| Dialog heading | `reset learn progress?` |
| Dialog body | `all 36 lessons across 3 courses will reset to not started. your library and DJ profile are not affected.` |
| Primary CTA | `reset` |
| Secondary CTA | `cancel` |

Zero exclamation marks. Zero amber color on the row itself (silk-only at rest; `--led-fault` halo on hover via established `rgba(212, 65, 58, ...)` alpha recipes from `recording-row.ts:294-298` and `confirm-dialog.ts:108-111`). Zero new design tokens. Zero hex literals — every color is a `var(--*)` read or an alpha-modulation rgba of an existing token. Saira + JetBrains Mono only via the inherited `--type-display` / `--type-body` tokens.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TDZ on `const dialog` when test mock invokes `onConfirm` synchronously**

- **Found during:** Initial test run after first-draft implementation
- **Issue:** The vitest mock `renderConfirmDialogMock` (defined in `tests/settings/learn-group.spec.ts:43`) immediately invokes `opts.onConfirm?.()` inside the mock factory body. When the production code wrote `const dialog = renderConfirmDialog({ onConfirm: () => { dialog.remove(); ... } })`, the synchronous mock invocation hit `dialog` before the `const` assignment completed → `ReferenceError: Cannot access 'dialog' before initialization`.
- **Fix:** Restructured to `let dialog: HTMLElement | null = null` with a `dismiss()` helper that `queueMicrotask(() => dialog?.remove())`. The microtask defers removal one tick — production-equivalent (a real user clicking confirm with a real async event also lets the synchronous return complete first), test-passing (the assignment to `dialog` reliably completes before the microtask runs).
- **Files modified:** `tauri/ui/src/settings/components/learn-group.ts` (the `openResetConfirm` function body)
- **Commit:** `509915f5` (the same commit as the LearnGroup landing — fixed before first push)

### Plan Adaptations (documented, not deviations)

- **ConfirmDialogProps API shape:** Verified `confirmLabel` / `cancelLabel` / `variant: "danger"` matches the existing `confirm-dialog.ts:24-34` API exactly. The 92-RESEARCH §Code Example 5 hedged on prop names — turned out the plan's `<copy_lock>` was already correct. No adaptation needed.
- **Insertion point in SettingsDrawer.ts:** UI-SPEC §Component Inventory said "between RECORDING and MASCOT", but the actual drawer ordering is RECORDING (line 847) → LIBRARY (868) → PROFILE (882) → CALIBRATION (902) → MASCOT (913). LearnGroup joined just before MASCOT (the closest available slot honoring the "before MASCOT" half of the spec). Annotated with a 4-line comment block explaining the precise position.
- **Local `.vmx-settings-row` classes vs shared:** The plan referenced "existing `vmx-settings-row` + `vmx-settings-row--destructive` CSS classes (recording-browser delete pattern)". Verified via grep these classes are NOT shared across the codebase — mascot-group/help-group/recording-row each scope their own row classes under a parent `[data-component]` selector. Followed that pattern: defined `.vmx-settings-row` + `.vmx-settings-row--destructive` locally inside the `[data-component="learn-group"]` parent selector. Zero cross-component collision risk; copy-paste-safe for the executor.

## Known Stubs

None — the feature is fully wired end-to-end: row click → confirm dialog → emit → sidecar (Plan 92-04) → reset_ack → toast on the Learn window (Plan 92-05).

## Self-Check: PASSED

**Files verified to exist:**
- `tauri/ui/src/settings/components/learn-group.ts` — FOUND (215 lines, exports `LearnGroup`)
- `.planning/phases/92-lesson-runtime-ai-highlight-contract/92-06-SUMMARY.md` — FOUND (this file)

**SettingsDrawer.ts integration verified:**
- 3 `LearnGroup` occurrences (import line 66 + comment-reference line 911 + body.append line 915) — ≥2 expected per plan verification gate 2.

**Copy lock byte-equality verified via grep:**
- `reset learn progress?` ✓
- `all 36 lessons across 3 courses will reset to not started` ✓
- `your library and DJ profile are not affected` ✓
- `clears all completed lessons. cannot be undone.` ✓
- `confirmLabel: "reset"` ✓
- `cancelLabel: "cancel"` ✓
- `variant: "danger"` ✓
- `"ipc.learn.progress_state", { action: "reset" }` ✓

**Forbidden patterns verified absent:**
- Exclamation marks: 0 occurrences (grep -c '!')
- Hex literals (#XXX/XXXXXX): 0 occurrences
- Forbidden fonts (Inter / Roboto / Arial / system-ui / Helvetica): 0 occurrences
- Amber (var(--amber*)) on the row body: only in `outline: 1px solid var(--amber)` for `:focus-visible` (inherited focus-ring reserved-amber element #1 per UI-SPEC §Color; not a new use)

**Tests passing:**
- `tests/settings/learn-group.spec.ts`: 1/1 LIVE PASS (52 ms; flipped from skip)
- `tests/settings/` (full): 82/82 across 8 spec files
- Full vitest suite: 1029 passed | 2 skipped | 15 todo (no regressions)
- `npx tsc --noEmit`: exit 0
- `npm run build`: 0 errors
