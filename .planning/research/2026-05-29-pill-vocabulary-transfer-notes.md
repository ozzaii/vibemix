# 2026-05-29 Pill Vocabulary And Transfer Notes

## Purpose

This note records the vocabulary and transfer findings for moving the explored
pill behavior into the next pill implementation without losing the premium
reaction model.

The user direction is explicit: the pill should feel like a DJ is playing with
the pill on screen. A `CLEAN`, `SEXY`, `MID`, `BOMB`, `LIT AFF`, or `NEG`
moment should open the full pill and show the reaction itself, while hover on a
grounded suggestion should say `DJ KNOWS` and expose the next move.

## Source Of Truth

Backend source of truth:

- `src/vibemix/intel/move_grade.py`

Current pill mirrors:

- `tauri/ui/src/pill/move-grade-vocabulary.json`
- `tauri/ui/src/pill/move-grade-vocabulary.ts`
- `tauri/ui/src/pill/next-suggestion.ts`
- `tauri/ui/src/pill/index.ts`

The move-grade ladder is:

| slug | label | xp | intensity | sentiment | transfer meaning |
| --- | --- | ---: | ---: | --- | --- |
| `negative` | `NEG` | 0 | 0 | negative | Stop forcing it. Name the risk and reset. |
| `mid` | `MID` | 8 | 24 | neutral | Playable with care. Give a specific restraint. |
| `clean` | `CLEAN` | 28 | 48 | positive | Technically stable. Mention phrase, key, cue, or bass fit. |
| `sexy` | `SEXY` | 48 | 66 | positive | Smooth musical lift. Keep the language tactile, not thirsty. |
| `bomb` | `BOMB` | 72 | 84 | positive | Big payoff. Tell the DJ how to ride the moment. |
| `lit_aff` | `LIT AFF` | 100 | 100 | positive | Everything clicks. This is overdrive, not normal success. |

## Transfer Grammar

The TypeScript vocabulary now exports `PILL_MOVE_GRADE_COPY_GRAMMAR` as the
new-pill copy source for terse, evidence-shaped wording. Keep the visible pill
line tiny, but let the grammar guide which words are allowed for each grade:

| slug | role | evidence words | operator verbs |
| --- | --- | --- | --- |
| `negative` | risk reset | clash, tempo, cue, short, rub | stop, reset, wait, clear |
| `mid` | careful playable | timing, phrase, filter, door, care | hold, wait, trim, check |
| `clean` | technical lock | phrase, cue, bass, key, tempo | breathe, hold, land, keep |
| `sexy` | smooth lift | blend, vocal, glide, lift, handoff | float, ease, ride, keep |
| `bomb` | payoff hit | drop, room, payoff, energy, floor | snap, ride, open, push |
| `lit_aff` | overdrive | clicks, room, lock, payoff, eight | ride, hold, stretch, own |

Every grade grammar carries the banned claim words `perfect`, `flawless`, and
`guaranteed`. `MID` and `NEG` also avoid celebratory adjacent language, while
`SEXY` avoids user-directed or thirsty phrasing.

## Copy Grammar

Every reaction line should follow this shape:

```text
<GRADE>. <evidence phrase>. <operator instruction>.
```

Examples now in the demo pill:

- `CLEAN. Phrase caught. Bass swap sealed. Let it breathe.`
- `SEXY. Smooth blend. Vocal floats. Hands stay light.`
- `MID, playable. Hold the filter. Wait for a cleaner door.`
- `BOMB. Drop landed. Floor opens. Snap next cue on one.`
- `LIT AFF. Everything clicks. Whole room locks. Ride eight.`
- `NEG. Harmonic rub. Do not force it. Reset the exit.`

Rules:

- Lead with the exact grade label so animation, density, ARIA, and cohost
  parsing stay deterministic.
- Keep the line short enough for `pillReactionDensity(...) === "normal"`.
- Use musical evidence words: phrase, cue, bass, key, harmonic, energy, vocal,
  door, room, filter, exit.
- Use operator verbs: hold, ride, reset, snap, wait, breathe, keep.
- Do not say `perfect`, `guaranteed`, or `flawless`. These are explicitly
  forbidden in the backend claim contract.
- `MID` and `NEG` must not sound celebratory. They are care states.
- `SEXY` can be playful, but it should describe the musical move, not the user.

The new pill should generate or select copy from this bounded vocabulary first,
then compress it into the visible receipt. Do not make the pill longer to sound
smarter; make the source grammar smarter so the short line lands harder.

## New Pill Transfer Contract

Transfer these behaviors first:

- Full-pill reaction receipts driven by real `cohost-reaction` frames.
- Large reaction lead text with tone-aware styling.
- Production reaction motion: full-shell lens sweep, rim flash, tone-aware
  receipt rail, and quiet text bloom behind the lead.
- Collapsed reaction echo afterglow after the expanded receipt closes.
- Grounded next-suggestion hover/focus drawer.
- `DJ KNOWS` label while a grounded suggestion is peeked.
- Compact grade evidence inside the `DJ KNOWS` drawer, for example
  `SEXY +48xp`, so the next move carries both action and confidence.
- Care-specific compact evidence for risky moves: `NEG 0xp` keeps its reason in
  the hover drawer, the visible action says `CARE`, and the warning rail/dot
  make the risky state legible without adding more text.
- Keyboard activation of the primary suggestion action from the focused pill.
- Face-click activation from the collapsed `DJ KNOWS` pill row, with the peek
  card and drag/no-drag zones excluded to avoid duplicate or accidental commits.
- Root action affordance state: expose `data-actionable="true"` and
  `aria-keyshortcuts="Enter Space"` only while the grounded primary action is
  available; clear both after receipt or when no suggestion is visible.
- Actionable-face visual affordance: a one-pixel row rail while `DJ KNOWS` can
  commit, animated in normal motion and static under reduced motion.
- Risk-aware action affordance: when `data-grade-earned="false"` or
  `data-grade-deserved="false"`, the row rail, hover wash, focus glow, reason
  marker, and primary-action arm motion must use the restrained warning state,
  not the positive rose/gold state.
- Completion receipts: `KEEP`, `CARE`, `LATER`, `TIMING`.
- Backend-aligned grade XP and reasons in TypeScript fallbacks.
- The shared local vocabulary module:
  `tauri/ui/src/pill/move-grade-vocabulary.json`, consumed by
  `tauri/ui/src/pill/move-grade-vocabulary.ts`.
- The shared copy grammar export: `PILL_MOVE_GRADE_COPY_GRAMMAR`.
- Reduced-motion suppression for all high-motion reaction effects.

## Animation Transfer Notes

The production pill now treats a reaction as a shell-level event:

- The root shell runs alternating `pill-lens-sweep-*` and `pill-rim-flash-*`
  animations from the reaction pulse slot.
- The reaction line owns `pill-reaction-rail-settle`, a one-pixel receipt rail
  under the text.
- The reaction line also owns a low-opacity bloom behind the lead. It is under
  the words, not over them, so booth readability stays intact.
- The evidence receipt layer should stay readable at booth glance: citation
  chips use a `24px` row with `10px` mono text; deck chips use a `21px` row with
  `10px` mono text.
- Canvas FX remains the loud layer for BOMB/LIT AFF, while CLEAN/MID/NEG stay
  quieter by opacity and particle profile.
- `prefers-reduced-motion: reduce` disables the shell sweep, rail animation, and
  canvas FX while keeping the static receipt readable.
- For `CARE`, reduced motion disables `pill-peek-care-arm` and the row-rail
  animation, but the static warning rail remains visible so the affordance still
  reads without motion.

For the replacement pill, transfer this choreography before inventing any new
effects. It is the current premium motion contract.

Keep demo-only:

- Demo stage.
- Demo reaction pads.
- Pad hover magnetic tilt.
- Stage hit blast layers.
- Number-key reaction triggers, unless a future debug mode explicitly needs them.

Do not transfer:

- The old tiny top-label reaction model.
- Fabricated next suggestions when production wire data is empty.
- Extra production `data-wire` anchors without updating
  `tauri/ui/src/mock-transfer/contract.ts`.
- New grade labels outside `NEG`, `MID`, `CLEAN`, `SEXY`, `BOMB`, `LIT AFF`.

## Exploration Findings

The old pill felt cheap because the emotional payload was too small: reactions
were treated as label changes instead of spatial events. The better model is a
booth object: the collapsed pill is a hardware light, the expanded pill is the
receipt, and the hover state is a confident suggestion peek.

The successful pieces are:

- Reaction state owns the whole body.
- The grade label is huge enough to read instantly.
- Copy is short and grounded.
- Motion is tone-specific and state-specific, not a generic pulse.
- Hover is useful, not decorative: it reveals the next grounded action.

## Viber And Cohost Transfer

Viber/cohost should reuse the same grade ladder and reason style. The spoken
or chat wording can be longer than the pill, but it must still cite the same
grounded grade:

- `Next CLEAN move`
- `Next SEXY move`
- `Next BOMB move`
- `Next LIT AFF move`
- `Next MID move: use care`
- `Risky move`

For the new pill, avoid letting Viber introduce parallel words like `fire`,
`insane`, `perfect`, or `safe`. The vocabulary is small on purpose so animation,
cohost citations, XP, and user memory all align.

## Open Transfer Tasks

- Consider a generated contract for move-grade labels/XP/intensity so Python and
  TypeScript cannot drift. Until then, keep
  `tauri/ui/src/pill/move-grade-vocabulary.test.ts` and
  `tests/intel/test_move_grade.py` pinned to the backend ladder.
- When the replacement pill shell exists, use `PILL_MOVE_GRADE_COPY_GRAMMAR`
  as the first copy source before adding any new cohost wording.
- Add a new-pill visual smoke once the replacement shell exists: trigger all six
  reactions, inspect full-pill text, inspect hover `DJ KNOWS`, and check reduced
  motion.
- If production `data-wire` anchors are added during transfer, update the
  mock-transfer contract in the same change.
- Keep GSD initialization out of this path until the user explicitly asks for it.
