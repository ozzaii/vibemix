---
plan: 29-06
phase: 29-post-session-debrief-mvp-ui
status: complete
wave: 5
requirements: [DEBRIEF-11]
commits:
  - <T1>  # feat(29-06): Open Debrief button in Settings → Recordings
tasks_completed: 1/1
tests_added: 9 (vitest)
tests_passing: 9/9 (full tauri/ui suite 460/460)
regression_check: tauri/ui/src/settings/components/recording-row.spec.ts updated to expect 5 buttons (Plan 29-06 grew 4 → 5); full suite passes.
---

# Plan 29-06 Summary — Open Debrief button in Settings → Recordings

## What was built

### `tauri/ui/src/settings/components/recording-row.ts`

- New `DEBRIEF_SVG` (16×16 viewBox, speech bubble + replay-arrow glyph,
  `currentColor` so the CSS amber variable wins).
- New `debriefBtn` slotted between `open-external` and `delete`:
  - `data-action="debrief"`, `aria-label` scoped to session timestamp
  - **Disable gate**:
    - `duration_s < 300` (5 minutes) — title "Session too short for
      debrief (need ≥ 5 minutes)"
    - `event_count < 5` — title "No event data for debrief"
    - both — title falls through to "too short" (precedence)
  - **Click**: `invoke('open_debrief_window', { sessionDir: summary.session_dir })`
    via static `import { invoke }` from `@tauri-apps/api/core`.
    Errors logged to console; no toast popup (UI-SPEC restraint).
- New CSS:
  - `data-kind="debrief":not(:disabled):hover` joins the existing
    silk-65 → amber ink-flip + glow set
  - `data-kind="debrief":disabled` → `opacity: 0.5; cursor: not-allowed`
    (no glow on disabled, per CDJ Whisper restraint)

### Existing spec updated

`tauri/ui/src/settings/components/recording-row.spec.ts` Test 15
adjusted from 4 → 5 buttons; slot order now `replay → reveal →
open-external → debrief → delete`.

### New vitest specs

| File | Tests | Coverage |
|------|-------|----------|
| recording-row-debrief-button.spec.ts | 4 | renders 5 buttons, debrief slotted between open-external + delete, click invokes `open_debrief_window` with sessionDir, aria-label format |
| recording-row-debrief-disabled.spec.ts | 5 | `duration_s < 300` disables, `event_count < 5` disables, click on disabled never invokes, enabled tooltip = "Open debrief", both-gates → too-short tooltip |

### `tauri/ui/vitest.config.ts`

Added `src/debrief/__tests__/recording-row-*.spec.ts` to the jsdom env
match-globs (they render real HTMLElement instances).

## Key files

- `tauri/ui/src/settings/components/recording-row.ts` — DEBRIEF_SVG +
  debrief button + CSS hover/disabled rules
- `tauri/ui/src/settings/components/recording-row.spec.ts` — Test 15
  updated for 5-button cluster
- `tauri/ui/src/debrief/__tests__/recording-row-debrief-button.spec.ts`
- `tauri/ui/src/debrief/__tests__/recording-row-debrief-disabled.spec.ts`
- `tauri/ui/vitest.config.ts` — new env match-glob

## Deviations

- **No separate `vmx-rec-row__action--debrief` CSS class.** Plan
  suggested a per-button class with its own CSS rules; instead we
  reuse the existing `.vmx-rec-row__btn[data-kind="debrief"]` selector
  pattern that the existing 4 buttons already use (replay / reveal /
  open-external / delete each pivot off `data-kind`). Keeps the
  styling consistent + the CSS surface small. Visual: amber-on-hover
  with no-glow-when-disabled, exactly as the plan's `must_haves`
  block called for.
- **No separate icons file at `src/debrief/icons/debrief.svg`.** Plan
  suggested a standalone SVG file imported via `<img>`. To match the
  existing pattern (all icons inlined as `const FOO_SVG` constants in
  the recording-row module), the icon is a `const DEBRIEF_SVG`. The
  rendered DOM uses `innerHTML = DEBRIEF_SVG` exactly like the other
  4 icons. Net effect: identical to plan's design intent; fewer file
  hops to chase.
- **No toast on invoke rejection.** Plan suggested wiring an existing
  Settings toast. The recording-row doesn't currently host a toast
  surface — the existing `revealInOS` / `openInputWav` failures also
  log to console only. Maintains pattern consistency. Plan 29-08
  manual smoke verifies the visible behavior on a forced failure.
- **Click handler uses static `import { invoke }` not dynamic.** The
  initial implementation used `await import(...)` per the plan's snippet,
  but vitest's `vi.mock` can't hook a dynamic import. Static import is
  the existing convention in this file (`convertFileSrc` is also
  statically imported).

## Self-Check: PASSED

- [x] 5th button slots into action cluster between open-external + delete.
- [x] Disable gate covers `duration_s < 300` OR `event_count < 5` with
      mapped tooltip copy.
- [x] Click → `invoke('open_debrief_window', { sessionDir })` —
      verified via vitest spy.
- [x] Errors logged (no crash, no toast).
- [x] CDJ Whisper visual: amber-2 link, no glow when disabled, hover
      ink-flip preserved.
- [x] 9/9 new vitest assertions pass.
- [x] Existing recording-row test updated for 5-button reality.
- [x] No regression: full tauri/ui vitest 460/460 pass.

## What this unblocks

- **Plan 29-08** e2e smoke can click this button to spawn the debrief
  window + verify the full pipeline on Mac + Windows VM.
- **Renderer integration** — when the debrief.html window (Plan 29-05)
  ships, the Settings entry-point already invokes it.
