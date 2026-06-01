# 2026-05-29 Pill Polish Handoff

## Scope

This handoff documents the May 29 pill polish work for the active goal:
`pill perfection in design and utility`.

User intent during the pass:

- The pill must feel premium, not like the old cheap/safe pill.
- Full-pill reactions open the pill and show the reaction itself.
- Demo controls let the user click `CLEAN`, `SEXY`, `MID`, `BOMB`, `LIT AFF`,
  and `NEG`.
- Hover/focus on the pill reveals the next suggestion and makes the command
  obvious.
- The surface uses clean transitions, liquid glass, hover states, and real web
  effects.
- Latest direction: enhance the reaction vocabulary and start documenting how
  the explored behavior transfers into the new pill.

Boundary preserved:

- GSD was not initialized or run.
- Learn beginner-path work was not touched or verified.
- Production `data-wire` anchors were not added for demo-only visual elements.
- Native pill geometry remains owned by the existing pill window contract.
- The collapsed native size remains `280x44`; the renderer requests only finite,
  clamped expanded heights.

## Files Changed

- `tauri/ui/pill.html`
- `tauri/ui/src/pill/index.ts`
- `tauri/ui/src/pill/index.test.ts`
- `tauri/ui/src/pill/move-grade-vocabulary.json`
- `tauri/ui/src/pill/move-grade-vocabulary.ts`
- `tauri/ui/src/pill/move-grade-vocabulary.test.ts`
- `tauri/ui/src/pill/pill.css`
- `tauri/ui/src/pill/next-suggestion.ts`
- `tauri/ui/src/pill/next-suggestion.test.ts`
- `tauri/ui/src/pill/waveform.ts`
- `tauri/ui/src/pill/waveform.test.ts`
- `tauri/ui/tests/pill/playwright.config.ts`
- `tauri/ui/tests/pill/browser-care-hover.pw.ts`
- `tauri/ui/tests/pill/browser-demo-reactions.pw.ts`
- `tauri/ui/package.json`
- `.planning/research/2026-05-29-pill-vocabulary-transfer-notes.md`

## Interaction Work Completed

- Added full-pill demo reaction triggers for:
  `CLEAN`, `SEXY`, `MID`, `BOMB`, `LIT AFF`, `NEG`.
- Demo buttons emit real cohost reaction frames into the pill state machine.
- Reaction clicks expand the pill body instead of only changing tiny top text.
- Reactions render large lead text with tone-aware styling.
- Reaction copy is booth-readable while preserving the lead reaction word.
- Demo controls remain usable across desktop and narrow widths.
- At compact widths, demo controls now switch to a centered two-row, three-column
  pad bank so `LIT AFF` and the other trigger labels no longer squeeze into a
  cheap one-row strip.
- Global number shortcuts `1` through `6` trigger the demo reactions.
- Number shortcuts are ignored while typing in editable controls.
- Number-key demo hits now center the pad light before firing, so keyboard
  triggers get the same physical pad feedback as pointer clicks.
- Demo controls now stay below the pill layer whenever the pill body is open,
  so the preview toolbar cannot steal hover/click from `DJ KNOWS` or a full
  reaction receipt.
- Added a dedicated pill Playwright smoke harness:
  `npm --prefix tauri/ui run test:e2e:pill`. It starts the Vite pill preview
  with demo next enabled, injects a risky bus suggestion, and verifies the
  `DJ KNOWS`/`CARE` hover path in a real browser.
- Added real-browser demo reaction coverage for all six pads. The test clicks
  `CLEAN`, `SEXY`, `MID`, `BOMB`, `LIT AFF`, and `NEG`, then verifies full-pill
  expand, tone-specific lead text, active pad/stage state, and nonblank canvas FX
  pixels.
- The actual number-key handler is exported and unit-tested, including
  modifier keys, hidden controls, editable targets, pad aiming, and click fire.
- The actual `DJ KNOWS` Escape-close handler is exported and unit-tested, so
  peek dismissal remains a pinned keyboard contract.
- The actual `DJ KNOWS` primary-action key handler is exported and unit-tested,
  so Enter/Space completion is pinned to root focus, open peek, and a grounded
  suggestion.
- The actual `DJ KNOWS` face-click handler is exported and unit-tested, so the
  collapsed pill face itself can commit the visible suggestion without relying
  on keyboard activation or hitting the tiny peek card.
- Completion receipts keep terse face labels (`KEEP`, `CARE`, `LATER`,
  `TIMING`) for `1.4s` while the root ARIA label now announces the action meaning:
  kept, accepted with care, postponed, or timing marked wrong.
- Browser coverage now clicks the actual hover card, verifies `CARE` completion,
  suppresses the stale same suggestion, and allows a changed timing suggestion
  to appear again.
- The visible `KEEP`/`CARE` peek command now renders as a hardware capsule
  instead of a tiny tag: minimum `50px` by `17px`, 1px hairline border, static
  specular lip, rose glass for `KEEP`, warning glass for `CARE`, and no gold.
- Browser coverage now verifies a `320px` narrow `DJ KNOWS` hover card with a
  long track title and long `CARE` reason: the settled drawer keeps the card
  inside the pill, preserves readable ordering, and renders the reason as a
  natural-case `9px` warning chip with ellipsis instead of a tiny loose text
  tail.
- Compact peek transition lines now keep their booth-glance copy visible while
  exposing the fuller grounded transition as the line title, so hidden cue and
  role detail remains recoverable without adding more visible text.
- The focused pill/card ARIA label now also includes that fuller grounded
  transition as `detail:` when the visible line is intentionally compact, so
  keyboard and assistive-tech users get the same recoverable cue/role evidence.
- Browser coverage now also focuses the collapsed pill, opens `DJ KNOWS`,
  verifies the root action ARIA/shortcut affordance, presses Enter, and proves
  the positive suggestion completes into a `KEEP` receipt.
- Browser coverage now focuses the actual peek card control, verifies its
  button semantics and shortcuts, presses Enter, and proves the card itself
  completes into a `KEEP` receipt while returning focus to the pill root.
- Peek-card keyboard activation now consumes Enter/Space on the card itself,
  preventing stray bubbling while keeping the focused-card `KEEP`/`CARE`
  completion path intact.
- Browser coverage now also focuses the actual risky peek card, presses Space,
  and proves the card itself completes into a `CARE` receipt while returning
  focus to the pill root.
- Browser coverage now also focuses the actual peek card, injects a live
  cohost reaction, and proves the disappearing card returns focus to the pill
  root while the full reaction opens.
- Browser coverage now presses demo number shortcuts `1` through `6` in the
  real preview and proves each shortcut opens the full reaction with centered
  pad lighting, active stage feedback, and a live pad hit.
- Browser coverage now also focuses a risky `DJ KNOWS` suggestion, verifies the
  care-specific ARIA summary, presses Space, and proves the suggestion completes
  into a `CARE` receipt.
- Browser coverage now focuses `DJ KNOWS`, presses Escape, verifies no feedback
  receipt is created, keeps the suggestion mounted but hidden, verifies the
  hidden card is inert/untabbable, and reopens it on hover with button semantics
  restored.
- Browser coverage now also focuses the actual peek card, presses Escape,
  verifies no completion fires, returns focus to the pill root, and keeps the
  hidden suggestion mounted/inert for the next hover.
- Browser coverage now hovers `DJ KNOWS`, clicks the pill face itself, verifies
  the click lands outside the peek card, and completes the visible suggestion
  into a `KEEP` receipt.

## Vocabulary Work Completed

- The pill fallback move-grade defaults now mirror `src/vibemix/intel/move_grade.py`:
  `NEG 0`, `MID 8`, `CLEAN 28`, `SEXY 48`, `BOMB 72`, `LIT AFF 100`.
- The pill now has a local vocabulary contract in
  `tauri/ui/src/pill/move-grade-vocabulary.json`, consumed through
  `move-grade-vocabulary.ts`, so demo reactions, next-card fallbacks, backend
  parity checks, and new-pill transfer read one shared table.
- `move-grade-vocabulary.ts` also exports `PILL_MOVE_GRADE_COPY_GRAMMAR`, a
  bounded transfer grammar for each grade: role, evidence words, operator
  verbs, and words to avoid.
- The demo next suggestion now uses the backend-aligned `SEXY +48xp` grade.
- Demo reaction copy was rewritten to be short, specific, and evidence-shaped:
  - `CLEAN. Phrase caught. Bass swap sealed. Let it breathe.`
  - `SEXY. Smooth blend. Vocal floats. Hands stay light.`
  - `MID, playable. Hold the filter. Wait for a cleaner door.`
  - `BOMB. Drop landed. Floor opens. Snap next cue on one.`
  - `LIT AFF. Everything clicks. Whole room locks. Ride eight.`
  - `NEG. Harmonic rub. Do not force it. Reset the exit.`
- Fallback reason copy now uses the backend/cohost register:
  `risk too high`, `works with care`, `clean fit`, `smooth blend`,
  `big payoff`, `everything clicks`.

## Animation And Visual Effects

- Added a real canvas FX layer inside the expanded pill:
  `#pill-fx` / `.pill__fx`.
- Reactions draw deterministic particles, rings, bloom, and light trails.
- Canvas FX palette follows the reaction tone:
  clean, sexy, mid, bomb, lit-aff, and negative each get separate color behavior.
- Production reaction hits now add a fast glass lens sweep and rim flash through
  the pill shell pseudo-elements, alternating by reaction pulse slot.
- Production reaction text now has a tone-aware receipt rail and a quiet bloom
  behind the lead, so the visual hit reads as a full-pill event without covering
  the words.
- `NEG` now renders as a high-contrast warning badge inside the reaction body,
  using silk text over a restrained red glass backing so negatives remain
  readable against the warning wash.
- Reaction receipt chips were enlarged and re-toned for booth readability:
  citation chips now render at `24px` high / `10px` text, deck chips at `21px`
  high / `10px` text, with stronger liquid-glass beveling.
- Reduced motion disables the canvas FX and related motion-heavy effects while
  keeping the full reaction body readable.
- Reaction echo afterglow appears on the collapsed pill for `1.8s` after the
  expanded reaction closes, long enough for a live glance without becoming a
  second panel.
- The durable reaction echo now yields to intentional hover/focus when a grounded
  next suggestion exists, so the user can still open `DJ KNOWS` immediately.
- Demo stage was added for Vite demo mode only:
  `#pill-demo-stage` / `.pill-demo-stage`.
- Stage lighting follows the active or hovered reaction tone.
- Stage light anchors to the actual clicked or hovered pad position via
  `--stage-pad-x` and `--stage-pad-y`.
- Active pad hover uses pointer-aware CSS variables for magnetic highlight and
  tilt:
  `--pad-x`, `--pad-y`, `--pad-tilt-x`, `--pad-tilt-y`.
- Repeated clicks replay the pad hit, stage hit, grab glint, and reaction shell
  pulses through alternating data slots.
- Previous active pads get a short release pulse when another pad takes over.
- Tone-specific stage hits differentiate clean lock, sexy glide, mid check,
  negative warning, and bomb/lit impact.

## Next Suggestion Utility

- Hover or keyboard focus on the collapsed pill opens the peek drawer when a
  grounded next suggestion exists.
- The collapsed label changes to `DJ KNOWS` while the peek is open.
- `data-intel` changes to `knows` during hover/focus peek.
- The peek card shows:
  track title, target deck, timing, cue rail, and primary action.
- The primary peek action is visible as `KEEP` or `CARE`.
- Positive peek suggestions now also show compact grade evidence, for example
  `SEXY +48xp`, so the hover drawer visually matches the grade already exposed
  through ARIA and the collapsed face.
- The collapsed pill row shows a pointer cursor while `DJ KNOWS` has a grounded
  suggestion, and face-click commits the visible suggestion to a `KEEP`/`CARE`
  receipt.
- The root pill now exposes `data-actionable="true"` and
  `aria-keyshortcuts="Enter Space"`, `aria-controls="pill-peek"`, and
  `aria-expanded="true"` only while the grounded `DJ KNOWS` primary action is
  available, then clears them after completion/receipt and dismiss states.
- The actionable `DJ KNOWS` face now paints a restrained one-pixel action rail,
  so the clickable state has a premium visual affordance without extra text.
  The rail stays in the one-rose system with a glass-edge finish; gold remains
  quarantined to grade/heat numerics. Reduced motion keeps the rail static.
- Risky `DJ KNOWS` suggestions now get their own `CARE` visual language:
  the collapsed action rail switches to warning color, the peek card carries a
  restrained warning wash, the reason becomes a compact natural-case
  warning-backed chip, and the primary action uses a dedicated
  `pill-peek-care-arm` motion.
- The `KEEP`/`CARE` command in the peek drawer is now a measured hardware
  capsule with a visible border and specular lip, so the pill task action reads
  like a control without adding another instruction line.
- Focused `DJ KNOWS` assistive copy keeps the visible action terse, then adds a
  `detail:` clause only when compact mode hid cue/role evidence.
- Focused root `aria-label` includes the same primary action summary that the
  sighted user sees.
- Enter or Space on the focused pill completes the primary suggestion action.
- Completing the suggestion collapses to a full-pill receipt:
  `KEEP`, `CARE`, `LATER`, or `TIMING`.
- Suggestion completion clears handled suggestions from the visible peek and
  full next mounts.

## Transfer Notes For The New Pill

- Treat `src/vibemix/intel/move_grade.py` as the Python source of truth for
  grade labels, XP, intensity, deserved/overdrive semantics, and reason style.
- Keep `tauri/ui/src/pill/move-grade-vocabulary.json` aligned with that backend
  source until a generated shared contract exists. The parity is pinned by
  `tests/intel/test_move_grade.py`.
- Transfer the full-pill reaction model, not the old tiny-top-text model.
  `data-open=true` must mean the body is open for hover peek or reaction receipt.
- Transfer `DJ KNOWS` hover/focus behavior for grounded next suggestions.
- Transfer the completion receipt behavior, including `KEEP`, `CARE`, `LATER`,
  and `TIMING`.
- Transfer the care-specific compact affordance with the rest of `DJ KNOWS`:
  `data-grade-earned="false"`/`data-grade-deserved="false"` must read as care,
  not as a positive `KEEP` action in warning text only.
- Transfer `PILL_MOVE_GRADE_COPY_GRAMMAR` before adding new surface wording,
  so the new pill inherits bounded evidence words, operator verbs, and banned
  claim language.
- Keep the demo stage and reaction pads dev-only. They are proof controls, not
  production app chrome.
- Do not add production `data-wire` anchors while transferring mock/demo visuals
  unless `tauri/ui/src/mock-transfer/contract.ts` is updated at the same time.
- Do not let Viber/cohost invent new grade words. The allowed surface vocabulary
  is `NEG`, `MID`, `CLEAN`, `SEXY`, `BOMB`, `LIT AFF`, with evidence-backed
  reasons.

## Accessibility And State Contracts

- Root pill focus has a dynamic `aria-label` for the focused suggestion action.
- Peek card can act as an accessible button when it owns a primary action.
- Feedback and completion states are reflected in pill datasets.
- Demo controls expose toolbar semantics and keyboard shortcuts.
- Keyboard completion accepts only Enter and Space.
- Escape dismissal works from both the focused pill root and the focused peek
  card without consuming the suggestion.
- Focusable descendant syncing keeps hidden controls out of tab order.
- Reduced motion suppresses canvas FX, shell pulses, stage hits, pad release
  motion, dot rings, wave comb motion, grab glints, and hover choreography.
- Reduced motion also freezes the care-specific hover/action motion while
  keeping the static warning rail visible.

## Verification Completed

Focused UI tests passed:

```bash
npm --prefix tauri/ui test -- src/pill/index.test.ts
```

Focused pill suite passed:

```bash
npm --prefix tauri/ui test -- src/pill/move-grade-vocabulary.test.ts src/pill/index.test.ts src/pill/next-suggestion.test.ts src/pill/waveform.test.ts src/pill/deck-chips.test.ts src/session/components/citation-strip.test.ts tests/mock-transfer-contract.spec.ts
```

Latest focused suite result after the vocabulary, primary-action, animation,
care-affordance, one-rose action rail, compact controls, and preview-toolbar
layering polish pass:

- 7 test files passed.
- 230 tests passed.

Focused focus-continuity suite passed after the suggestion-surface removal
polish:

```bash
npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts
```

Latest focused focus-continuity/action-capsule/readability result:

- 2 test files passed.
- 166 tests passed.

Backend parity test passed after the JSON contract extraction:

```bash
uv run pytest -q tests/intel/test_move_grade.py
```

Latest backend parity result:

- 5 tests passed.

Vocabulary-focused suite passed after the XP and copy alignment:

```bash
npm --prefix tauri/ui test -- src/pill/move-grade-vocabulary.test.ts src/pill/index.test.ts src/pill/next-suggestion.test.ts
```

Latest vocabulary-focused result:

- 3 test files passed.
- 151 tests passed.

Production webview build passed after the latest pill pass:

```bash
npm --prefix tauri/ui run build
```

Dedicated pill browser e2e passed after the preview-toolbar layering, compact
controls, warning-lead, durable echo, click completion, focused keyboard
completion, Escape dismissal, and demo reaction FX pass:

```bash
npm --prefix tauri/ui run test:e2e:pill
```

Latest pill browser e2e result:

- 16 Playwright tests passed.
- The first test covers the risky `DJ KNOWS` hover state, `CARE` action,
  `NEG 0xp` card semantics, demo-toolbar overlap, hit-testing ownership, and
  reduced-motion freezing for the care arm/rail. It also measures the visible
  `CARE` command capsule, proving the control is at least `50px` by `17px` with
  a solid hairline border.
- The second test clicks the risky hover card, proves the `CARE` completion
  receipt, suppresses the stale same suggestion, and accepts a retimed
  replacement suggestion.
- The third test pins narrow `320px` `DJ KNOWS` readability with a long track
  title and long `CARE` reason: the settled drawer stays inside the pill, text
  order remains readable, and the reason renders as a natural-case `9px`
  warning chip with ellipsis rather than spilling horizontally. It also proves
  the compact transition line keeps the full grounded cue/role/timing detail in
  its title and ARIA label.
- The fourth test focuses the collapsed pill, opens `DJ KNOWS`, checks
  `aria-keyshortcuts="Enter Space"` plus `aria-controls="pill-peek"` /
  `aria-expanded="true"` and the focused action summary, presses Enter, and
  proves the `KEEP` receipt clears stale peek/action chrome.
- The fifth test focuses the actual peek card control, checks its
  `role="button"` and `aria-keyshortcuts="Enter Space"` contract, presses Enter,
  and proves the `KEEP` receipt clears stale peek/action chrome while focus
  returns to the pill root.
- The sixth test focuses the actual risky peek card control, presses Space, and
  proves the `CARE` receipt clears stale peek/action chrome while focus returns
  to the pill root.
- The seventh test focuses the actual peek card, injects a live cohost reaction,
  and proves the disappearing card returns focus to the pill root while the full
  `COHOST` reaction opens.
- The eighth test focuses a risky `DJ KNOWS` suggestion, checks the
  care-specific focused action summary, presses Space, and proves the `CARE`
  receipt clears stale peek/action chrome.
- The ninth test focuses `DJ KNOWS`, presses Escape, proves no suggestion
  completion fired, keeps `data-has-next="true"`, keeps the mounted card
  inert/`tabindex="-1"` while hidden, and reopens the same suggestion on hover
  with `tabindex="0"` restored.
- The tenth test focuses the actual peek card, presses Escape, proves no
  suggestion completion fired, returns focus to the pill root, and keeps the
  mounted card inert/`tabindex="-1"` while hidden.
- The eleventh test hovers `DJ KNOWS`, clicks the pill face instead of the peek
  card, and proves the visible suggestion completes into a `KEEP` receipt.
- The twelfth test clicks every demo reaction pad and proves the full reaction
  body opens with tone-specific lead text, active pad/stage feedback, and
  nonblank canvas FX.
- The thirteenth test presses number shortcuts `1` through `6` and proves each
  shortcut opens the full reaction with centered pad feedback, active stage
  feedback, and a live pad hit.
- The fourteenth test pins the compact two-row pad bank, `LIT AFF` no-wrap treatment,
  high-contrast `NEG` badge styling, and controls staying below the expanded
  pill.
- The fifteenth test pins the full reaction lifecycle: expanded `COHOST`, collapsed
  face echo, pad reset, 44px collapsed height, echo-to-`DJ KNOWS` hover handoff,
  and final return to `IDLE`.
- The sixteenth test pins reduced-motion full reactions: `LIT AFF` still opens and
  reads, but no `data-fx`, canvas pixels, or lead animation are emitted.

Whitespace check passed for touched pill/docs files after the latest pill pass:

```bash
git diff --check -- tauri/ui/package.json tauri/ui/tests/pill/playwright.config.ts tauri/ui/tests/pill/browser-care-hover.pw.ts tauri/ui/tests/pill/browser-demo-reactions.pw.ts tauri/ui/src/pill/index.ts tauri/ui/src/pill/index.test.ts tauri/ui/src/pill/pill.css tauri/ui/src/pill/next-suggestion.ts tauri/ui/src/pill/next-suggestion.test.ts tauri/ui/src/pill/move-grade-vocabulary.json tauri/ui/src/pill/move-grade-vocabulary.ts tauri/ui/src/pill/move-grade-vocabulary.test.ts tests/intel/test_move_grade.py .planning/handoffs/2026-05-29-pill-polish-handoff.md .planning/research/2026-05-29-pill-vocabulary-transfer-notes.md
```

Browser smoke checks passed after the animation polish:

- `http://127.0.0.1:5177/pill.html` returned HTTP 200.
- Focused pill opened `DJ KNOWS` at mobile and desktop widths.
- Enter completed the focused suggestion to a full-pill `KEEP` receipt.
- Enter on the focused peek card completed the suggestion to a full-pill `KEEP`
  receipt and returned focus to the pill root.
- Space on the focused risky peek card completed the suggestion to a full-pill
  `CARE` receipt and returned focus to the pill root.
- A live cohost reaction arriving while the peek card was focused removed the
  card, opened the full `COHOST` reaction, and returned focus to the pill root.
- Space completed a focused risky suggestion to a full-pill `CARE` receipt.
- Escape dismissed focused `DJ KNOWS` without creating a receipt, kept the
  suggestion mounted but hidden, made the hidden card inert/untabbable, and
  hover reopened it as a focusable button.
- Escape from the focused peek card returned focus to the pill root without
  creating a receipt, then left the hidden suggestion mounted and inert.
- Face-click completed a visible `DJ KNOWS` suggestion from the pill face itself,
  without requiring a click on the peek card.
- Demo reaction buttons expanded the pill for all supported tones.
- Demo number shortcuts `1` through `6` expanded the pill for all supported
  tones with centered pad lighting and stage hit feedback.
- Live preview clicked all six demo pads and confirmed `data-state="expand"`,
  `data-open="true"`, matching `data-reaction-tone`, and visible reaction lead
  for `CLEAN`, `SEXY`, `MID`, `BOMB`, `LIT AFF`, and `NEG`.
- Live preview confirmed the new production animation hooks on each reaction:
  `pill-reaction-rail-settle`, alternating `pill-lens-sweep-*`, alternating
  `pill-rim-flash-*`, and nonblank canvas FX.
- Live preview confirmed receipt readability after the latest polish:
  each grade showed a `24px` / `10px` citation chip and `21px` / `10px` deck
  chip, with no horizontal overflow.
- Live preview confirmed compact negative state at `360x360`: `NEG` reads as a
  silk-on-warning badge, and the demo controls render as two rows of pads below
  the expanded pill.
- Browser e2e confirmed the post-reaction face echo stays visible after collapse,
  yields to an intentional `DJ KNOWS` hover, then clears back to `IDLE` after the
  echo window.
- Browser e2e confirmed the `DJ KNOWS` hover card acts as a task-completion pill:
  click shows `CARE`, hides stale next-card chrome, keeps the receipt visible
  after `900ms`, suppresses the same card, and reopens for a changed timing.
- Browser e2e confirmed the `CARE` command is no longer a micro-label: the
  rendered capsule measures at least `50px` by `17px` with a solid border.
- Browser e2e confirmed a settled narrow `DJ KNOWS` card at `320px` keeps a long
  title and long `CARE` reason ordered, clipped to the pill, horizontally
  contained, and readable as a natural-case warning-backed chip. The same check
  confirms the compact transition line exposes the full `cue A` plus
  `outro→intro` detail through its title and focused ARIA label.
- Live preview pressed demo number shortcuts and confirmed centered pad light
  variables on the triggered pad.
- Live preview focused the pill, opened `DJ KNOWS`, pressed Escape, and confirmed
  `data-peek="false"` with the face returning to the underlying live state.
- Live preview confirmed `DJ KNOWS` hover at `320`, `560`, and `900` widths:
  open pill height `140px`, peek drawer height `96px`, compact grade
  `SEXY+48xp`, and no horizontal overflow.
- Live preview confirmed focused Enter completion still turns the peek into a
  `KEEP` receipt after the compact grade render.
- Live preview confirmed face-click completion at `320` and `900` widths:
  `DJ KNOWS` + `SEXY+48xp` + pointer cursor before click, then `KEEP`,
  `data-feedback="accept"`, `data-peek="false"`, and `data-open="false"`.
- Live preview confirmed the root action affordance lifecycle:
  idle `data-actionable="false"` with no shortcuts, `DJ KNOWS`
  `data-actionable="true"` with `aria-keyshortcuts="Enter Space"` and
  `aria-controls="pill-peek"` / `aria-expanded="true"`, then receipt state back
  to not actionable.
- Live preview confirmed the actionable face rail:
  normal mode uses `pill-actionable-face-rail` without spending gold, while
  reduced motion reports `animation-name: none` with a static rail.
- Live preview injected a risky `next_suggestion` frame through the pill bus and
  confirmed `data-intel="care"`, `CARE`, `NEG`, `data-grade-earned="false"`,
  warning action rail, warning reason dot, and `pill-peek-care-arm`.
- The same risky browser smoke confirmed reduced motion disables the care arm
  and row-rail animations while retaining the static warning rail.
- Live preview reproduced the narrow toolbar collision with a real
  `page.hover("#pill")` path, then confirmed the open pill owns hit-testing:
  pill `z-index: 10`, demo controls `z-index: 8`, `DJ KNOWS` stays open, and
  the risky `CARE` card remains visible.
- Reduced-motion browser smoke confirmed the peek card/action animations and
  transitions are disabled while the compact grade remains visible.
- Canvas FX was sampled nonblank for reaction hits.
- Reduced-motion browser smoke confirmed the lens/rail animations report `none`,
  full reaction lead animation reports `none`, and the canvas FX layer is hidden
  with zero lit pixels.
- Stage hotspot matched the active button center at `320`, `560`, and `900`
  viewport widths.
- Responsive browser smoke at `320`, `560`, and `900` widths confirmed the BOMB
  reaction stays open, readable, and without horizontal overflow.

## Current Preview

The Vite pill preview was live during verification at:

```text
http://127.0.0.1:5177/pill.html
```

## Notes For Next Pass

- If transferring into a replacement pill shell, start from the state contract
  and vocabulary contract before moving visual layers.
- The most important production behavior is full-pill reaction receipts and
  grounded `DJ KNOWS` next-suggestion hover/focus.
- The demo reaction pads are allowed to be loud because they are an inspection
  rig. The production pill should keep the premium, restrained hardware feel.
- Keep reduced-motion behavior respected.
- Keep GSD and Learn beginner-path suites untouched unless explicitly requested.
