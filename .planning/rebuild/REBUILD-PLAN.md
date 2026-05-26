# vibemix UI Rebuild — PLAN ("The Deck Speaks", every surface)

> Companion to `WIRING.md` (data contract) and `mocks/vibemix-rebuild-session.html`
> (locked session north-star, 30/40, 4 critiques). This is the per-surface
> design direction + port order so the rebuild touches every surface coherently.
> Brief: minimal · simple · very unique · 20/80.

## The language (locked, from the session north-star)
Pure CDJ void (vignette + deep linear + film grain; NO aurora washes). No glass
cards, no panel grids, no drop-shadow stacks — hairlines + open void carry
structure. Hero type on void (Saira condensed display, JetBrains Mono numerics).
ONE breathing amber per view = the per-reaction **receipt** (rule draws → cite
ignites). Status is silk-dim when fine, lights only on a dropped input (the one
red exception). Agency is low-ink at rest, full on hover/focus + keyboard. State
is a real enum, never a boolean. Aliveness = real telemetry (meter) + the type/
receipt gesture, NOT a heartbeat dot or green LEDs.

## Per-surface application
- **Session (heart) — LOCKED.** Anchored-low hero, ghost recession, receipt
  gesture, foot master strip (bpm/key/live meter), live|silent|fault. Mock done.
- **Pill (floating, :8765, consume-only).** The smallest deck: collapsed = state
  + last-line fragment; expand (hover, Dynamic-Island morph per
  [[project_pill_hover_reveal_design]]) = the receipt in miniature (mini rule +
  cite). Kill any green; silk-dim. Resize-to-content (latent clip bug noted).
- **Settings drawer (overlay on session).** Void slab from the right, NO group
  cards. Rows on hairlines; silk labels; one amber on the active control.
  mood/skill/voice as inline tap-to-cycle (like the deck persona). Recordings/
  library/profile = quiet collapsible sections, not card stacks.
- **Wizard (first-run, main window).** Same void + hero language: each step is
  ONE large lit instruction line on void + one primary action + a hairline step
  rail. Single column, no card stack. The setup "speaks" like the deck. All
  existing step IPC (permission/calibration/midi/smoke/consent) preserved.
- **Debrief (separate window, :8766).** A reading surface, so denser, but: void
  floor, hero verdict line (the deck delivers its verdict), timeline = hairline
  horizontal strip, chapters = ghost-recession list, drills = quiet rows, TL;DR
  player minimal. Amber = evidence/cite links (same receipt thesis). Bravoh
  waitlist toggle quiet at the foot.
- **Mascot (transparent WebGL window).** Minimal CSS scope: keep the canvas fully
  transparent, the legacy chrome stays display:none. The character's mood states
  mirror the persona discipline (3D, separate from the CSS system). No second
  border-sweep, no rim-light.

## Port order (heart-out, smallest blast radius first)
1. **Session** (`SessionLayout.ts` + `render-loop.ts` + components) — the heart;
   establishes the shared CSS the others borrow.
2. **Pill** (small, shares bus + reaction/receipt shape with session).
3. **Settings drawer** (overlay; reuses session tokens).
4. **Wizard** (largest, but mostly compositional re-tone of existing steps).
5. **Debrief** (separate window; reuses the language).
6. **Mascot** (least CSS work).

## Port-risk constants (carry verbatim — see WIRING §7)
- Gesture timing: rise 400 / rule-draw 520@360 / cite-ignite 380@900 ms; re-fire
  per reaction via forced reflow / element re-key.
- Meter smoothing: 0.16 attack lerp, 0.04 peak decay, 86% ceiling; hard-stop in
  silent/fault.
- Cross-fade labels: always-mounted, opacity toggle (never mount/unmount).
- `prefers-reduced-motion` forces scaleX(1) (rule shown complete, no draw).
- tokens.css `body` change (cut --rave-* washes) is app-wide — apply once, all
  surfaces inherit.

## Verify-as-you-go (every surface, before "done")
- WIRING §7 firewall: every control traces to an OUTBOUND IPC row.
- `npm run check:ipc` (if schema touched) + `tsc --noEmit` + `vitest run` green.
- Live verify in `cargo tauri dev` (tests ≠ working app, [[feedback_verify_live_app_not_just_tests]]);
  debug via `ui.log` + ws probe ([[feedback_debug_live_app_via_ui_log]]).
- Baseline at rebuild start (2026-05-26): check:ipc=0, tsc clean, 874/874 tests.
