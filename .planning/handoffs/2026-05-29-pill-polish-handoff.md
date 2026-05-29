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
- `.planning/research/2026-05-29-pill-vocabulary-transfer-notes.md`

## Interaction Work Completed

- Added full-pill demo reaction triggers for:
  `CLEAN`, `SEXY`, `MID`, `BOMB`, `LIT AFF`, `NEG`.
- Demo buttons emit real cohost reaction frames into the pill state machine.
- Reaction clicks expand the pill body instead of only changing tiny top text.
- Reactions render large lead text with tone-aware styling.
- Reaction copy is booth-readable while preserving the lead reaction word.
- Demo controls remain usable across desktop and narrow widths.
- Global number shortcuts `1` through `6` trigger the demo reactions.
- Number shortcuts are ignored while typing in editable controls.
- Number-key demo hits now center the pad light before firing, so keyboard
  triggers get the same physical pad feedback as pointer clicks.
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
  `TIMING`) while the root ARIA label now announces the action meaning:
  kept, accepted with care, postponed, or timing marked wrong.

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
- Reaction receipt chips were enlarged and re-toned for booth readability:
  citation chips now render at `24px` high / `10px` text, deck chips at `21px`
  high / `10px` text, with stronger liquid-glass beveling.
- Reduced motion disables the canvas FX and related motion-heavy effects.
- Reaction echo afterglow appears on the collapsed pill after the expanded
  reaction closes.
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
  `aria-keyshortcuts="Enter Space"` only while the grounded `DJ KNOWS` primary
  action is available, then clears both after completion/receipt states.
- The actionable `DJ KNOWS` face now paints a restrained one-pixel action rail,
  so the clickable state has a premium visual affordance without extra text.
  Reduced motion keeps the rail static.
- Risky `DJ KNOWS` suggestions now get their own `CARE` visual language:
  the collapsed action rail switches to warning color, the peek card carries a
  restrained warning wash, the reason gets a tiny warning dot, and the primary
  action uses a dedicated `pill-peek-care-arm` motion.
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
and care-affordance polish pass:

- 7 test files passed.
- 228 tests passed.

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

Whitespace check passed for touched pill/docs files after the animation pass:

```bash
git diff --check -- tauri/ui/src/pill/index.ts tauri/ui/src/pill/index.test.ts tauri/ui/src/pill/pill.css tauri/ui/src/pill/next-suggestion.ts tauri/ui/src/pill/next-suggestion.test.ts tauri/ui/src/pill/move-grade-vocabulary.json tauri/ui/src/pill/move-grade-vocabulary.ts tauri/ui/src/pill/move-grade-vocabulary.test.ts tests/intel/test_move_grade.py .planning/handoffs/2026-05-29-pill-polish-handoff.md .planning/research/2026-05-29-pill-vocabulary-transfer-notes.md
```

Browser smoke checks passed after the animation polish:

- `http://127.0.0.1:5177/pill.html` returned HTTP 200.
- Focused pill opened `DJ KNOWS` at mobile and desktop widths.
- Enter completed the focused suggestion to a full-pill `KEEP` receipt.
- Demo reaction buttons expanded the pill for all supported tones.
- Live preview clicked all six demo pads and confirmed `data-state="expand"`,
  `data-open="true"`, matching `data-reaction-tone`, and visible reaction lead
  for `CLEAN`, `SEXY`, `MID`, `BOMB`, `LIT AFF`, and `NEG`.
- Live preview confirmed the new production animation hooks on each reaction:
  `pill-reaction-rail-settle`, alternating `pill-lens-sweep-*`, alternating
  `pill-rim-flash-*`, and nonblank canvas FX.
- Live preview confirmed receipt readability after the latest polish:
  each grade showed a `24px` / `10px` citation chip and `21px` / `10px` deck
  chip, with no horizontal overflow.
- Live preview pressed demo number shortcuts and confirmed centered pad light
  variables on the triggered pad.
- Live preview focused the pill, opened `DJ KNOWS`, pressed Escape, and confirmed
  `data-peek="false"` with the face returning to `IDLE`.
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
  `data-actionable="true"` with `aria-keyshortcuts="Enter Space"`, then receipt
  state back to not actionable.
- Live preview confirmed the actionable face rail:
  normal mode uses `pill-actionable-face-rail`; reduced motion reports
  `animation-name: none` with a static rail.
- Live preview injected a risky `next_suggestion` frame through the pill bus and
  confirmed `data-intel="care"`, `CARE`, `NEG`, `data-grade-earned="false"`,
  warning action rail, warning reason dot, and `pill-peek-care-arm`.
- The same risky browser smoke confirmed reduced motion disables the care arm
  and row-rail animations while retaining the static warning rail.
- Reduced-motion browser smoke confirmed the peek card/action animations and
  transitions are disabled while the compact grade remains visible.
- Canvas FX was sampled nonblank for reaction hits.
- Reduced-motion browser smoke confirmed the lens/rail animations report `none`
  and the canvas FX layer is hidden.
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
