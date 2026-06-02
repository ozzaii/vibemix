# Learn First-Screen Product QA

Date: 2026-06-02

This note records the visual failure found from the exact signed app opened from
`dist/signed-local/vibemix-0.0.1.dmg` at `8911fba7`.

## Why it still felt bad

- The old Settings screen was stale, and the user correctly read that as "the
  shipped app is not the thing we worked on."
- Learn was technically alive, but its first paint still forced the user to
  decode diagnostic language: `controller visible` looked like an internal
  state, not a usable product state.
- The first viewport had too many competing surfaces: large ghost controller,
  lesson controls, Earned Wall context, shell session status, and sometimes the
  right grounding drawer. The user could not immediately answer "what do I do
  now?"
- `midi=1` on `ipc.status.tick` only proves a visible controller port, not live
  movement frames. Calling that "hardware signal ready" was overclaiming.

## Product rule

Treat confusing shipped UI as a product bug even when the underlying code path
is green. The screen must say the next action plainly, and the copy must not
claim a stronger proof tier than the runtime has.

## Current fix

- Folded Learn says `ready to practice` / `controller detected` instead of
  diagnostic `controller visible`.
- The accessible copy keeps the missing-MIDI-output caveat: start a lesson; if
  Learn does not react, enable FLX4 MIDI output so live moves can bind.
- The practice deck remains the primary visual, but the empty legal/footer
  clutter and empty Earned Wall are suppressed in the folded shell.

## Proof standard

Do not call this slice done from source tests alone. Rebuild/sign/notarize the
DMG, open that exact mounted app, switch to Learn, and inspect the screenshot.
