# CODEX_READY: Compact Pill Polish

Date: 2026-06-01
Author: Codex
Package: 6 - Compact Pill Polish
Decision: LAND
Suggested commit: `feat(pill): polish next suggestion care interactions`

## Summary

This package is ready to land as the UI-only compact pill polish slice.

It makes the collapsed next-suggestion peek behave like a small, grounded DJ control:
no fabricated fallback suggestion, no hidden optimistic completion, and no fake "success"
wording. A grounded next suggestion can be accepted from the pill face or focused peek
card; risky or auto-review moves are labeled CARE and still send the existing `accept`
intent with a care receipt.

This packet does not claim backend cue ingest/export correctness. Package 4 owns cue
provenance and Package 5 owns Viber/library live-read context. This package proves the
pill rendering and interaction layer only.

## Files In Package

- `tauri/ui/package.json`
- `tauri/ui/src/pill/index.ts`
- `tauri/ui/src/pill/index.test.ts`
- `tauri/ui/src/pill/next-suggestion.ts`
- `tauri/ui/src/pill/next-suggestion.test.ts`
- `tauri/ui/src/pill/pill.css`
- `tauri/ui/tests/pill/playwright.config.ts`
- `tauri/ui/tests/pill/browser-care-hover.pw.ts`
- `tauri/ui/tests/pill/browser-demo-reactions.pw.ts`
- `.planning/handoffs/2026-05-29-pill-polish-handoff.md`

## LAND Criteria

- Collapsed hover peek is enabled only for a real `next_suggestion` card.
- Demo next suggestion remains dev/demo opt-in and cannot mask a real wire value.
- The compact pill can complete a visible suggestion with click, Enter, or Space.
- Risky, undeserved, or auto-review suggestions surface as CARE, not "keep".
- CARE still uses the existing `accept` command intent, with honest UI/ARIA receipt.
- The hover drawer keeps full grounded transition detail in title/ARIA where visible text is compact.
- Demo reaction controls are explicitly dev/demo-only and do not steal pointer focus from an open pill.
- Reduced-motion behavior remains readable and does not rely on canvas effects.

## Source Evidence

### Runtime gate and demo discipline

- `tauri/ui/src/pill/index.ts:441-451` enables collapsed PEEK, but keeps demo next suggestions behind
  explicit `VITE_VIBEMIX_DEMO_NEXT === "1"` and states production behavior as honest silence.
- `tauri/ui/src/pill/index.ts:541-545` allows demo controls only in Vite dev, with the demo flag on,
  and with `?controls=0` able to disable them.
- `tauri/ui/src/pill/index.ts:547-617` installs demo controls as a real toolbar with labels,
  `aria-pressed`, shortcuts, pointer/focus handlers, and cleanup.
- `tauri/ui/package.json:15` adds `test:e2e:pill` as the Playwright pill gate.

### Compact suggestion semantics

- `tauri/ui/src/pill/next-suggestion.ts:636-656` generates compact peek action text such as
  `load B - in 8 bars` without dragging the full card into the collapsed surface.
- `tauri/ui/src/pill/next-suggestion.ts:666-700` keeps peek ARIA compact while preserving
  full detail and CARE reasons.
- `tauri/ui/src/pill/next-suggestion.ts:702-716` names primary action intent as `care` for
  undeserved grades and `keep` otherwise.
- `tauri/ui/src/pill/next-suggestion.ts:718-760` normalizes move grade/progress from the wire
  payload instead of inventing local optimism.

### Visual and interaction treatment

- `tauri/ui/src/pill/pill.css:2704-2725` documents the collapsed hover drawer contract:
  normal-flow, shared pill glass, no empty box when there is no grounded suggestion.
- `tauri/ui/src/pill/pill.css:2726-2753` keeps the drawer inert/invisible at rest and reveals
  with one bounded transition.
- `tauri/ui/src/pill/pill.css:2768-2849` makes interactive peek cards focusable/clickable with
  a warning rail for undeserved grades.
- `tauri/ui/src/pill/pill.css:2867-2925` renders KEEP/CARE as a hardware-like capsule and gives
  CARE a warning treatment.
- `tauri/ui/src/pill/pill.css:2935-2998` keeps compact transition/reason text contained.
- `tauri/ui/src/pill/pill.css:2999-3031` makes risky grade reasons readable without adding more
  explanatory copy.
- `tauri/ui/src/pill/pill.css:3043-3055` reveals only when `data-peek=true` and the mount is not
  empty.

## Test Evidence

### Vitest

Command:

```bash
npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts
```

Result:

```text
Test Files  2 passed (2)
Tests       167 passed (167)
```

Coverage highlights:

- `tauri/ui/src/pill/index.test.ts:95-154` verifies warning rail, hardware capsule, readable
  risky reasons, and demo z-index discipline.
- `tauri/ui/src/pill/index.test.ts:369-430` verifies terse visual receipts with honest assistive
  text, including CARE for risky accepted suggestions.
- `tauri/ui/src/pill/index.test.ts:621-694` verifies primary keyboard completion is Enter/Space
  only and ignores child/closed/empty/unsupported states.
- `tauri/ui/src/pill/index.test.ts:696-730` verifies face-click completion from the collapsed pill.
- `tauri/ui/src/pill/index.test.ts:773-895` verifies demo controls remain operable, shortcut-gated,
  and produce active pad receipts.
- `tauri/ui/src/pill/next-suggestion.test.ts:774-833` verifies CARE labels still send the `accept`
  intent.
- `tauri/ui/src/pill/next-suggestion.test.ts:863-950` verifies collapsed hover completion and
  KEEP/CARE ARIA/key contracts.
- `tauri/ui/src/pill/next-suggestion.test.ts:952-984` verifies `auto_cue_review` collapses to CARE.
- `tauri/ui/src/pill/next-suggestion.test.ts:986-1113` verifies peek density stays compact while
  preserving full grounded transition detail as title/ARIA.
- `tauri/ui/src/pill/next-suggestion.test.ts:1250-1274` verifies compact assistive labels call out
  care reasons.

### Playwright

Command:

```bash
npm --prefix tauri/ui run test:e2e:pill
```

Result:

```text
16 passed (15.1s)
```

Coverage highlights:

- `tauri/ui/tests/pill/browser-care-hover.pw.ts:133-251` verifies risky suggestions own hover/click
  even when demo controls overlap, and reduced motion removes the arm animation.
- `tauri/ui/tests/pill/browser-care-hover.pw.ts:253-294` verifies CARE click completes the task,
  suppresses stale suggestions, and allows a retimed suggestion to reappear.
- `tauri/ui/tests/pill/browser-care-hover.pw.ts:296-395` verifies narrow-width CARE layout stays
  readable without spill and preserves full transition detail in ARIA/title.
- `tauri/ui/tests/pill/browser-care-hover.pw.ts:397-618` verifies focus, Enter/Space completion,
  focus return, KEEP/CARE labels, and no stale shortcuts after completion.
- `tauri/ui/tests/pill/browser-care-hover.pw.ts:620-709` verifies Escape dismisses without consuming
  the suggestion and restores inert/hidden state correctly.
- `tauri/ui/tests/pill/browser-demo-reactions.pw.ts:15-51` verifies demo pads open each full reaction
  and produce visible canvas pixels when motion is allowed.
- `tauri/ui/tests/pill/browser-demo-reactions.pw.ts:53-95` verifies number shortcuts fire full
  reactions with centered pad feedback.
- `tauri/ui/tests/pill/browser-demo-reactions.pw.ts:97-157` verifies compact controls become a
  two-row pad bank with readable warning lead.
- `tauri/ui/tests/pill/browser-demo-reactions.pw.ts:159-243` verifies reaction echo/reset and
  reduced-motion readability.

### Build And Diff Hygiene

Command:

```bash
npm --prefix tauri/ui run build
```

Result:

```text
tsc --noEmit && vite build passed
```

Command:

```bash
git diff --check -- tauri/ui/package.json tauri/ui/src/pill/index.ts tauri/ui/src/pill/index.test.ts tauri/ui/src/pill/next-suggestion.ts tauri/ui/src/pill/next-suggestion.test.ts tauri/ui/src/pill/pill.css tauri/ui/tests/pill/playwright.config.ts tauri/ui/tests/pill/browser-care-hover.pw.ts tauri/ui/tests/pill/browser-demo-reactions.pw.ts .planning/handoffs/2026-05-29-pill-polish-handoff.md
```

Result: passed with no output.

## Boundaries

- This is UI rendering and interaction proof, not live DDJ/Viber end-to-end proof.
- No sidecar/live app visual pass was run for this package. Playwright covers browser behavior and
  layout, but the remaining live gate is the optional visual pass in the running app.
- Do not claim this package proves cue ingest/export correctness. That belongs to Package 4.
- Do not claim this package proves Viber live-read correctness. That belongs to Package 5.

## Verdict

LAND as `feat(pill): polish next suggestion care interactions`.
