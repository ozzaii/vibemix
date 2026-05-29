# vibemix Translation Layer — Bravoh's language, made into a cohesive app

> How Forged Obsidian Chrome (see `bravoh-design-language.md`) becomes vibemix: one
> cohesive app shell in the tozpembe direction, built as frontend structure with named
> mount anchors, no backend wiring. This was the build contract for `/impeccable craft`;
> it is now also the as-built record of the shipped shell.

## Status — as-built (2026-05-29)

The shell skeleton is **built and converged** through a 3-round adversarial `/impeccable`
critique: token re-skin + a new `src/shell/` composition + 30 green shell/contract tests, tsc
clean, build green. This doc is held honest against that code. Where the original plan and the
shipped shell diverged during the critique, the **shipped** behavior wins and is flagged inline.
The short version of those corrections, so a surface-translator never re-introduces drift the
critique already removed:

- **One breath per screen (One-Rose).** At most one element breathes on screen at once: live → the
  deck tail cursor, reconnecting → the connection dot, otherwise → the sidebar brand ear. The
  energy field, the right-edge LED seam, and the foot-pill ear are **static lit**, never a second
  breath. (See DESIGN.md "The One-Rose Rule".)
- **The connection dot is steady-lit when connected**, not breathing. Only "reconnecting" pulses.
- **The tail cursor is a solid rose block** on the co-host line (eased fade on `--motion-led-pulse`,
  1400ms), **not** a rose-to-gold gradient: gradients are banned and gold is quarantined to heat.
- **Stacking is a CSS `--z-*` ladder** declared on `#shell-root`, not a JS constant map. (An
  exported `z-index.ts` was built, found to be dead code by the critique, and deleted.)
- **Fonts are the one token still on the v5 family.** `--type-display` / `--type-body` resolve to
  Saira and `--type-mono` to JetBrains Mono; `--type-serif` is Instrument Serif with a Georgia
  fallback (no vendored file yet). The Geist / Geist Mono / Instrument Serif swap below is the
  single deferred token job (Phase 1b), so the spec rows read as target, not as shipped.

Deferred, with reason: mounting the real surface interiors (collision-blocked on concurrent
session/wiring work), the font swap (above), and the responsive `minWidth` floor (set on the shell
window at window-wiring time, out of this island).

## The diagnosis

vibemix is disjointed on two axes at once, and both have to be fixed for the app to read as
one thing.

1. **Structural.** vibemix is seven separate Tauri windows (index/wizard + session, library,
   learn, pill, debrief, overlay, mascot), each its own HTML entry and its own little world.
   There is no shell. The live session is a flat titlebar + a 4-mode picker + a single deck +
   a status row. Settings is a right slide-over. Nothing ties the surfaces together, so the
   product feels like a handful of tools bolted to a tray, not "an app." This is the literal
   cause of "everything is a little confusing."

2. **Dialect.** The shipped code is a complete, disciplined system, but at plan time it still spoke the *previous* dialect:
   "CDJ Whisper v5" (cool blue-black void `#000` to `#11141c`, warm-grey silk text `#d6cfc7`,
   one amber accent `#ff8a3d`, Saira + JetBrains Mono). The locked direction is tozpembe
   (Forged Obsidian Chrome): warm void `#1A1618` to `#474144`, soft-rose `#FFA5DF`, gold
   `#e8c47a`, ink `#F2EFF1`, Geist + Geist Mono + Instrument Serif. `grep` for any of those
   hexes in `src/` returned **zero hits** at plan time — the new system lived only in
   `mocks/vibemix-bravoh-grade-pink.html`. The token re-skin (step 1) has since landed them in
   `tokens.css` (`--void-0` `#1A1618`, `--brand` `#FFA5DF`, `--gold` `#e8c47a`, `--ink-100`
   `#F2EFF1`); what remained was the structural shell, built below.

The fix is two jobs that compose: a token re-skin (cheap, propagates for free because every
component reads `var(--token)` and hex is banned), and a structural shell build (genuinely
new, no counterpart in code).

## Framework verdict

The earlier worry was "maybe React is not for it, maybe React Native, maybe Electron, maybe
a more premium framework." That worry is already resolved by the existing codebase:
**vibemix is a Tauri (Rust) desktop app with a vanilla-TypeScript + Vite frontend.** Tauri is
precisely the "premium, lighter-than-Electron, does-not-look-like-a-website" native shell the
brief asked for. Bravoh itself ships its desktop build on Tauri. There is nothing to re-found.

So this is **not** a framework migration. It is: keep Tauri + vanilla TS, port Bravoh's design
system into it, and build the shell composition that Bravoh has and vibemix lacks. The
vanilla-TS constraint shapes how (no React context, no Framer Motion, no `cmdk` library), not
whether.

Constraints to honor (from `PRODUCT.md`, `DESIGN.md`, and the cardinal invariants):
- Components read `var(--token)` for branded color exclusively; only `tokens.css` may contain
  `#xxxxxx`. The one carve-out (load-bearing in the shipped shell): structural-neutral `rgba()`
  scrims for window chrome — drop shadows, the 48px recess-edge gradient, the palette backdrop — may
  be inlined; all *branded* color still comes from tokens (DESIGN.md "The Hex-Outside-Tokens Ban").
  For the chrome / furniture / panel fills use the `--scrim-chrome` / `--scrim-furniture` /
  `--scrim-panel` tokens so they re-tone with the void ladder. `--scrim-chrome` is intentionally
  semi-transparent (0.55α) so the warm-void body reads through the slim drag bar; `--scrim-furniture`
  and `--scrim-panel` are near-opaque (0.98α). Use them as-is, never substitute a solid fill. The live
  token-discipline authority is DESIGN.md ("The Hex-Outside-Tokens Ban" + "Gold-Is-Quarantined") and
  `tests/design-slop-gate.spec.ts` — the `frontend-enforcement` skill still encodes the retired v5
  amber/charcoal palette, so treat it as stale until refreshed.
- Settings controls repaint optimistically (flip `data-active` locally; the round-trip
  self-corrects). The "CSS class is the truth, TS maps state to class" model from Bravoh fits
  this exactly.
- `prefers-reduced-motion` and the `data-blur-perf` escape hatch are honored at the token layer ONLY
  for blur and the perimeter sweep (`--motion-border-sweep` → 0s); they do NOT centrally kill
  `animation`. Reduced-motion freezing is a hand-maintained allowlist — `shell.css`'s
  `@media (prefers-reduced-motion: reduce)` block names exactly `.sb-ear, .conn-dot, .tail-cursor`.
- The five cardinal invariants stay intact: single-writer MusicState, citation grounding, trust
  the audio, one socket (8765 main / 8766 debrief), idle is not fault.

## Design-language resolution

**tozpembe (Forged Obsidian Chrome) supersedes CDJ Whisper.** `DESIGN.md` was stale and has been rewritten as part of this work (step 1). But the good bones of CDJ Whisper carry over verbatim, because
they are the same bones Bravoh has: restraint, one-accent discipline, hardware tactility, no
chatbot bubble, mono numerics, "boots and works," idle is calm not faulted, no slop. The locked
mock is that fusion already. What changes is the palette, the type, and the composition; what
stays is the philosophy.

### Token re-skin spec (`tokens.css`)

Re-skin in place. Keep the current `--amber*` / `--silk*` names as deprecated aliases pointing
at the new tokens during migration, so the 100-plus existing consumers re-tone without 100 edits.

| Role | CDJ Whisper (current) | tozpembe (target) |
|---|---|---|
| Void | `#000` to `#11141c` (cool) | `#1A1618` to `#474144` (warm, 7+ steps) |
| Text | silk `#d6cfc7` (warm grey) | ink `#F2EFF1` to `#8A858A`, semantic primary/secondary/tertiary/muted/disabled |
| Accent | amber `#ff8a3d` (single) | brand rose `#FFA5DF` + glow `#FFB8E8` + press `#B070A0`, explicit alpha ladder `--brand-03` … `--brand-78` (loudest on a surface is the CTA — the Restart button — at `--brand-16` fill / `--brand-40` border, per DESIGN.md) |
| Heat | (none) | gold `#e8c47a` + gold-soft + gold-glow, reserved for Camelot / heat / energy-delta numerics only |
| Body/UI font | Saira | Geist Sans (vendored) |
| Labels/numerics | JetBrains Mono | Geist Mono (vendored) |
| Hero serif | (Saira display) | **Instrument Serif** (vendored), cohost hero line + lead track names |
| Shell geometry | (none) | `--chrome-h 28`, `--sidebar-collapsed 72`, `--sidebar-expanded 260`, `--panel-w 280` |
| Motion | fixed 150/200/250ms | add `--ease-brand cubic-bezier(0.16,1,0.3,1)`, `--bpm-beat 461ms`, `--bpm-bar 1846ms` |

- **Collapse the polychrome.** The current meter/mood polychrome (green/magenta meter, blue
  COACH mood) and the locked mock disagree: the mock expresses energy purely via gold deltas
  and rose. Collapse meter + mood color into rose + gold to hold the one-accent discipline.
  Functional status LEDs (ok/warn/fault) stay, quiet and component-scoped.
- **Add the brand alpha ladder** as the only legal way to use rose at partial strength, and
  add a `--heat-*` ladder for gold, mirroring Bravoh's no-inline-rgba enforcement (the token-discipline
  authority + the `frontend-enforcement` staleness caveat are stated once under "Constraints to honor"
  above).
- **Vendor the fonts offline** (WOFF2 + SHA-256 in `LICENSE-3RD-PARTY.md`) — the one deferred token
  job (Phase 1b). The mock loads Geist / Instrument Serif from a CDN; the product must not. As
  shipped, `--type-display`/`--type-body` are still Saira and `--type-mono` is JetBrains Mono;
  `--type-serif` is Instrument Serif with a Georgia fallback. The swap must also amend
  `design-slop-gate.spec.ts` ALLOWED_FONTS (today it admits only Saira + JetBrains Mono) or the gate
  rejects the new faces. (KAAN-ACTION: license sign-off.)
- The `--chrome-highlight: inset 0 0.5px 0 rgba(255,200,235,0.07)` top-edge whisper becomes the
  universal material on every surface.

## The cohesive app-shell architecture

A new `src/shell/` module, vanilla TS, that hosts the opaque surfaces as one window. The
structural decisions, ported from Bravoh's DesktopShell:

```
+--------------------------------------------------------------+
| titlebar (drag region, mono clock)                  chrome-h |
+------------+----------------------------------+--------------+
|            |                                  |              |
|  SIDEBAR   |   MAIN  (recessed stage)         |  GROUNDING   |
|  (fixed)   |   <- 48px inset recess shadow    |  PANEL       |
|            |                                  |  (on demand) |
|  brand     |   the active surface lives here  |  cites,      |
|  + "ear"   |   keep-alive; surfaces hide via  |  next-track, |
|            |   display:none, never unmount    |  receipts    |
|  nav:      |                                  |              |
|  Deck      |   marginLeft = sidebar width     |  280px       |
|  Crate     |   (animated 0.3s ease-brand)     |              |
|  Learn     |                                  |              |
|  Debrief   |                                  |              |
|  Settings  |                                  |              |
|            |                                  |              |
|  persona   |                                  |              |
|  cohost    |                                  |              |
+------------+----------------------------------+--------------+
|  floating session-status (bottom-right, 10px, quiet)         |
+--------------------------------------------------------------+
  Cmd+K command palette overlays everything (z 1000)
```

Mechanics (vanilla-TS reimplementation of the Bravoh primitives):
- **Fixed sidebar, pushed main.** Sidebar is `position: fixed`; the main region is pushed by
  `margin-left: var(--sidebar-w)` animated `0.3s var(--ease-brand)`, never a flex sibling gap.
  The 48px left-edge inset shadow makes the stage recess beneath the chrome.
- **Sidebar collapse:** `Ctrl+\` toggles 260/72px, persisted to localStorage, with a collapse
  handle that is `opacity:0` at rest and revealed on sidebar hover OR `.sb-collapse:focus-visible`
  (in either width state, so a keyboard user can always see the control the focus ring lands on). A
  tiny store (plain module-level state + a subscribe callback) replaces React context.
- **Keep-alive surfaces:** each surface mounts once on first visit and hides via `display:none`
  on tab switch, so deck audio state, lesson progress, and crate scroll survive navigation. This
  is what makes it feel like one app, not seven windows.
- **Command palette:** `Cmd+K` (or `Ctrl+K` on Windows) opens a 640px palette on `--surface-base` (brand tint only on the selected row); the
  binding fires on Cmd OR Ctrl (`event.metaKey || event.ctrlKey`), as do the digit/surface
  accelerators (Cmd-or-Ctrl + 1–5), so the prose can use the macOS label while both platforms work.
  Binding lives in a small hook-equivalent; as shipped the sources are the five surfaces plus four
  shell commands (toggle sidebar / toggle grounding panel / go live / return to idle), filtered by a
  case-insensitive subsequence matcher — no frecency ranking and no controller / track / lesson /
  recording sources yet. Wiring those dynamic, frecency-ranked sources (the Bravoh target) is
  deferred to surface integration (step 3). No `cmdk` dependency.
- **Right grounding panel:** `Ctrl+]` toggles the 280px panel (opens and closes; the palette labels
  the chord "Toggle grounding panel"), and `Esc` closes it — while the command palette is open the
  palette intercepts `Esc`, so one keystroke never closes both. It also auto-opens when activation
  goes live and auto-closes back at idle (`store.setActivation`). This is where citations, the
  "what's next" suggestion, and receipts live, contextual to the deck.
- **Governed stacking:** a single `--z-*` custom-property ladder declared on `#shell-root`
  (`--z-base`/`--z-stage`/`--z-recess`/`--z-footer`/`--z-sidebar`/`--z-panel`/`--z-palette`), read by
  every rule via `var(--z-*)`, so the layer order is reviewable in one place with no bare literals.
  (A JS `z-index.ts` map was tried first and deleted as dead code — the discipline lives in CSS, not
  a constant nothing imports.)
- **Floating session-status:** the spiritual sibling of Bravoh's StudioStatusFooter, quiet at 10px
  — a connection dot (steady-lit connected, pulsing reconnecting, dim disconnected) beside an
  activation label reading "idle" / "listening" / "live". Two separate channels (dot = connection,
  label = activation), never merged into one string (also fixes the idle-not-fault bug).

### State contract (the handles a surface reads)

All shell state lives on `#shell-root` as data-attributes, written only by the store-subscribed
`applyState` in `DesktopShell.ts` (single writer, optimistic repaint — a folding surface reads these,
it never holds its own copy):

- `data-state` — activation `idle` | `listening` | `live`. Drives the deck idle-vs-live hero via
  `#shell-root[data-state=…]`; mirrors the store `ActivationState`.
- `data-conn` — connection `connected` | `reconnecting` | `disconnected` (the footer dot). `idle` +
  `disconnected` is expected, never a fault (invariant #5).
- `data-panel` — grounding panel `open` | `closed`.
- `data-collapsed` — sidebar `true` | `false`.

Keep-alive visibility is the `.surface.is-active` class: every `.surface` is `display:none` and only
the active one gets `.is-active` (`display:flex`). A folding surface toggles nothing itself — it
reads `#shell-root[data-state=…]` for its idle/listening/live presentation and lets the store own
`.is-active`. Same "class is the truth, TS maps state to class" single-store model the doc names.

### Self-arranging activation ("pick it up, start play, everything arranges, go")

The shell is stateful, not configured. Three states drive the layout, no setup screens after
first run:
- **Idle:** sidebar present, main shows the Deck surface with a warm "listening for the mix…"
  hero (invitation, not fault), grounding panel closed. Calm, one breathing life-sign.
- **Listening (audio detected):** the status footer flips to "listening" and the deck energy field
  lifts its opacity (it ramps, it never breathes). Real BPM / meters are wiring-deferred, so the
  scene line holds honest dashes ("— BPM / — / —") until live values land — trust-the-audio made
  visible, not a fake-confident readout.
- **Live (co-host reacting):** the co-host line carries the tail cursor (the screen's single breath
  while live), the grounding panel auto-opens as a labeled receipt (a "Cited" slot and a "What's
  next" slot, honest placeholders until citations wire in), and the active surface stays the Deck.
  Everything arranges around what the music is doing.

First run is the wizard (audio routing + one detected controller = the single required artifact,
Bravoh's "one real thing" move); after that, the app opens straight into the self-arranging Deck.

## Multi-window vs fold (decided)

- **Fold into one shell window:** Deck (session), Crate (library/Viber), Learn, Debrief,
  Settings become sidebar routes in the main window with keep-alive. This is the cohesion the
  goal demands.
- **Stay separate windows:** the floating Pill, the click-through Overlay, and the Mascot are
  transparent always-on-top webviews and cannot fold; they re-skin to tozpembe and read the new
  tokens via `getComputedStyle`. The pill stays the primary glance surface during a set.
- **Debrief socket:** Debrief becomes a shell route but its data source keeps the 8766 socket
  invariant for now (wiring deferred). Whether it long-term shares 8765 is a KAAN-ACTION.

## Per-surface translation map

| Surface | Today | Target in the shell |
|---|---|---|
| **Deck** (`session/SessionLayout.ts`) | titlebar + 4-mode picker + single deck + status row, amber on cold void | The home surface inside the recess. Hero line moves Saira to Instrument Serif; amber receipt rule to rose; inline scene line (BPM, gold Camelot chip, gold heat chip); phrase hairline with BPM-locked playhead; live RMS as CSS-height VU bars; master spectrum composited behind at 0.35 opacity. The 4-mode picker becomes sidebar nav. |
| **Crate** (`library/`, 6 modes) | own window, `vmx-lib-` amber chrome, LED match meter | Sidebar route. Re-skin to rose/gold. ChromeCard rows (raised = selected, float = active build slot), ChromeChip for BPM/Camelot/genre, provenance chip for grounding source ([rekordbox]/[audio]/[exemplar]/[ai]). Right grounding panel hosts Viber + "what's next". |
| **Learn** (`learn/`, MIDI renderer) | own window, SVG controllers | Sidebar route, keep-alive so controller + progress survive. Token re-skin only (dual-cue slots amber to rose); the SVGs already forbid brand-orange so they re-tone clean. Live-cued control uses the input focus ring language. |
| **Debrief** (`debrief/`, ws 8766) | own window, sidebar + main + drills | Sidebar route (data still 8766). Re-skin to Geist/ink + Instrument Serif headings. Bravoh's analytical viz (half-gauge scores, bar distributions, sparkline energy arc), all mount-once, muted palette. |
| **Settings** (`settings/SettingsDrawer.ts`) | right 400px drawer | Sidebar route (**Cmd+5**, a digit accelerator like every other surface — the bare-comma binding was dropped) or stays a drawer; pickers/rockers re-skin for free via tokens. Keep optimistic repaint. |
| **Wizard** (`index.html .wizard-app`) | first-run, shares index.html | Re-tone warm-void/rose. Single required step (routing + controller); library scan + persona skippable. Staged narration, not a bare spinner. |
| **Pill** (`pill/`, transparent) | own window, Liquid-Glass | Stays a window. Re-tint glass + state dot + waveform + citation chips amber to rose. Adopt the idle/streaming/tooling presence grammar and one ListeningIndicator life-sign. |
| **Overlay + Mascot** | transparent windows | Stay windows. Overlay ring color flips to rose automatically once `--brand` resolves; mascot mood palette gets a rose/gold pass. |

## As-built mount anchors (`data-wire`, shipped)

The literal anchor strings a surface-translator targets. Structural anchors sit on the frame
elements; the five interior surfaces mount under per-surface anchors. The deck is the one exception:
it wires onto its visible stage, the other four mount into a hidden `.surface-mount` behind their
at-rest empty state.

| Anchor | Element / location | Mount note |
|---|---|---|
| `shell.chrome` | titlebar `<header>` | drag region |
| `shell.sidebar` | sidebar `<div>` | fixed furniture |
| `shell.main` | recessed `<main>` | hosts the keep-alive surfaces |
| `shell.panel` | grounding `<aside>` | contextual right panel |
| `shell.panel.body` | panel body `<div>` | **store-driven, not a passive mount** — `GroundingPanel.render()` rewrites this node on every store change; extend `render()` (the "Cited" / "What's next" slots are the seams), do not append into it |
| `shell.cohost-pill` | sidebar foot `.sb-cohost` | co-host live pill |
| `shell.status` | footer `<button>` | session status |
| `shell.surface.deck` | the visible `.deck-stage` | deck interior wires onto the stage; it owns its idle/live hero (no hidden mount) |
| `shell.surface.crate` | hidden `.surface-mount` under Crate | real library/Viber surface mounts here, behind the empty state |
| `shell.surface.learn` | hidden `.surface-mount` under Learn | real Learn surface mounts here |
| `shell.surface.debrief` | hidden `.surface-mount` under Debrief | real Debrief surface (8766) mounts here |
| `shell.surface.settings` | hidden `.surface-mount` under Settings | real Settings surface mounts here |

These are design-time DOM mount points, distinct from `src/mock-transfer/contract.ts`, which
enumerates the WS/IPC data channels (owned by the wiring session) — the shell's `shell.*` anchors are
not registered there.

**Mount protocol.** To fold a real surface in: mount its interior inside the surface's
`.surface-mount` node, then clear that node's `hidden` attribute and hide (or remove) the sibling
`.surface-empty`. `.surface-mount` ships `hidden` with no CSS of its own, so clearing `hidden` is the
literal reveal; `.surface-empty` is the always-rendered at-rest fallback, not a permanent layer. The
deck has no `.surface-mount` — its interior wires onto `.deck-stage` directly.

**Deck scene wire-out.** The deck's `.deck-scene` line carries `aria-hidden="true"` ONLY while it
shows placeholder dashes ("— BPM / — / —"); the wiring phase MUST drop `aria-hidden` (or move it to
the still-empty individual chips) once real BPM / Camelot / vibe values render, so screen-reader users
hear the detected values. `.scene-chip--gold` is applied ONLY when a real Camelot value renders
(Gold-Is-Quarantined); at rest the key slot is a neutral dash, never gold.

**Surface geometry.** Each region is `surface surface--stub` (the four interiors) or `surface
surface--deck`; the modifier centers the at-rest empty state (`align-items` / `justify-content:
center`, and the deck adds `padding`). A full-bleed real interior folded into `.surface-mount`
inherits that centering, so its mounted root must reset `align-items` / `justify-content` and stretch
to fill (`flex: 1; align-self: stretch`) or it renders centered like the empty state.

## Presence grammar and motion contract

- **One being, three states.** The co-host's idle / listening-or-streaming / grounding-or-tooling
  maps 1:1 onto Bravoh's idle / streaming / tooling loops. The pill and the deck both speak it.
  At idle, `grounded=false` is expected, so the idle loop is alive and calm, never faulted.
- **One breath per screen (the One-Rose rule).** This is the governing motion law for translating
  any surface, and it is *stricter* than the parent: Bravoh lets the idle breath, the equalizer, and
  the connection breath all run at once; vibemix forbids it. At most one element breathes on screen
  at a time — live → the deck tail cursor, reconnecting → the connection dot, otherwise → the
  sidebar brand ear. Everything else that could pulse (energy field, LED seam, foot-pill ear) is
  held static lit. Port this rule first; every other presence detail hangs off it.
- **The tail cursor** on the co-host line: one **solid rose** block (`var(--brand)`), an eased fade
  on the LED-pulse cadence (`--motion-led-pulse`, 1400ms) while a reaction streams, never per token,
  steady-on under reduced motion. It is **not** a gradient and **not** rose-to-gold: decorative
  gradients are banned and gold is quarantined to heat numerics. It is the same gesture as the
  rose-underline-on-cite receipt, re-toned.
- **The connection dot** in the footer: connected is **steady-lit** (a stable power LED, not a
  breath — the live tail cursor owns the one breath), reconnecting pulses 1.5s, disconnected dims to
  0.7. The honest fix for the recurring "AI service unreachable" empty screen, and it keeps the
  one-breath budget intact.
- **FreqBars / VU** for meters: prime-duration bars (0.47/0.61/0.53/0.71/0.59s), CSS-height VU with
  one hard clip flip. No redraw loops.
- **Numbers roll, they do not throb** (a small NumberFlow-equivalent for BPM); an unconfident key
  dims to `--` (trust-the-audio made visible).
- **Motion vocabulary:** `--ease-brand` is the only ease; the duration budget is three named tokens — `--motion-snap` 150ms,
  `--motion-transition` 200ms, `--motion-step` 250ms — plus two structural literals the shell uses but
  does not tokenize (300ms recessed-main margin slide, 600ms deck energy-field opacity ramp). There is
  no 400ms tier; `--motion-led-pulse` (1400ms) drives the tail-cursor/LED breath, and the BPM-locked
  beat/bar are reserved for the playhead and pulse. No spring on panels. Every loop must be made to honor `prefers-reduced-motion` BY HAND: any new animated mark a folded
  surface adds MUST be listed in a `@media (prefers-reduced-motion: reduce)` block with `animation:
  none` (in `shell.css` for shell marks, or the surface's own stylesheet) — it is not inherited from
  the token layer, and marks that move via `transition`/`opacity` rather than `animation` (the energy
  field, the LED seam) are intentionally not listed since reduced motion already holds them still.
  Port `depthMotion` as a small set of named CSS classes so animation
  stays reviewable (the vanilla-TS equivalent of MOTN-07).

## Component vocabulary (vanilla-TS port)

This is the **target primitive layer for surface translation, not yet built**: the shell itself
ships only its own structural + presentation classes (the frame/furniture `.shell-*` / `.sb-*` /
`.surface*` incl. the `surface--deck` / `surface--stub` modifiers / `.palette-*` / `.pi-*`, plus the
deck readout `.deck-*` / `.scene-chip` / `.tail-cursor`, the panel chrome `.panel-*`, the footer
`.conn-dot`, and the empty state `.se-*`). When a real
surface folds in, reproduce Bravoh's closed primitive set as named CSS classes + thin TS factories
that map state to class (the "class is the truth" model, which also satisfies the optimistic-repaint
rule): `.vmx-btn` (primary rose, ghost), `.vmx-card` (default / raised / float / tool), `.vmx-chip`
(rose + gold + status), `.vmx-input` (note: the rose focus ring + bloom already ships GLOBALLY via
`*:focus-visible` in `tokens.css` — `2px solid var(--brand)` + `--glow-soft`; build on it, never
re-declare a competing per-control ring). The hardware-rack dialect
(`SessionStrip`-equivalent: LED whose pulse encodes recency, VU meter, fractal-noise grain) is the
deck's material, promoted to a reusable class rather than copy-pasted — and it obeys the one-breath
rule (the LED pulse is then the panel's single breath).

## Build sequence

The structure is built first, wiring deferred. Each phase ends green (`cd tauri/ui && npm run
build && npm test`).

1. **Tokens — ✅ done (fonts deferred).** Re-skin `tokens.css` to tozpembe (warm void, rose ladder,
   gold family, ink, shell geometry, BPM motion), keep amber/silk aliases, collapse polychrome to
   rose+gold, rewrite `DESIGN.md`. Existing surfaces re-tone for free. The Geist / Geist Mono /
   Instrument Serif vendoring is the one piece left (Phase 1b) — shipped fonts are still Saira +
   JetBrains Mono with a Georgia serif fallback.
2. **Shell skeleton — ✅ done + converged.** New `src/shell/`: fixed sidebar + recessed marginLeft
   main + right panel + Cmd+K palette + status footer + the governed `--z-*` stacking ladder + the
   keyboard chords and the tiny collapse/route store, built as structure with named `shell.*` mount
   anchors, not wired to the live bus. (Registering those anchors in `src/mock-transfer/contract.ts`
   is owned by the wiring session — that contract enumerates IPC/Tauri channels, not design.)
3. **Surface integration — ⏳ deferred (collision-blocked).** Mount Deck as home and Crate / Learn /
   Debrief / Settings as keep-alive routes; wire the self-arranging idle/listening/live states at
   the layout level; re-skin each surface's chrome. Blocked until the concurrent session/wiring work
   lands so the real interiors don't collide. Point `mock-transfer` `mockSources` at
   `vibemix-bravoh-grade-pink.html` at that time.
4. **Presence + motion — ◑ partial.** Shipped at shell level: the tail cursor, the energy-field
   opacity ramp, the steady/pulsing connection dot, and the idle "listening for the mix…" hero, all
   under the one-breath rule. The full deck readout (FreqBars/VU, BPM roll, spectrum-as-wallpaper)
   wires in with the real Deck surface (step 3).
5. **Separate windows — ◑ auto-retoned.** Pill / Overlay / Mascot re-tone for free through the
   amber/silk → rose token aliases; an explicit `/impeccable` polish pass on each is optional.
6. **Polish + verify — ✅ done.** A 3-round adversarial `/impeccable` critique converged (slop /
   craft / a11y / copy / contract lenses); `grounding-failure.spec.ts` (idle-not-fault) and
   mascot-audit stay green; full tsc/build/vitest green.

## Locked decisions

1. tozpembe (Forged Obsidian Chrome) is authoritative; `DESIGN.md` rewritten; CDJ-Whisper amber
   retired (names kept as deprecated aliases through migration).
2. Fold Deck / Crate / Learn / Debrief / Settings into one shell window; Pill / Overlay / Mascot
   stay separate transparent windows.
3. Build the structure with mount anchors; **no backend wiring** in this work (backend is a
   separate cloud workflow).
4. Vendor Geist + Geist Mono + Instrument Serif offline; no CDN fonts. (Deferred — Phase 1b; shipped
   fonts are still Saira + JetBrains Mono with a Georgia serif fallback on `--type-serif`.)
5. Collapse meter/mood polychrome into rose + gold; keep functional status LEDs quiet.
6. Hero serif is Instrument Serif (per the locked mock), not PP Mondwest.

## KAAN-ACTION (deferred, surfaced not blocking)

- Font licensing sign-off for Instrument Serif + Geist vendoring, then Phase 1b: vendor the WOFF2s,
  swap `--type-display`/`--type-body`/`--type-mono`, wire `--type-serif`, and amend
  `design-slop-gate.spec.ts` ALLOWED_FONTS (today it admits only Saira + JetBrains Mono).
- Ear-pass / eye-pass on the rebuilt shell once it runs in `cargo tauri dev`.
- Decide whether Debrief long-term keeps its own 8766 window or fully folds into the 8765 shell.
- Confirm the wordmark treatment: the shell renders it in **uppercase** condensed Saira (matching the
  titlebar; see `shell.css` `.sb-wordmark`), so confirm that same casing across pill / wizard /
  debrief / learn.
- Set the shell window `minWidth` (~720px) at window-wiring time so the recessed layout has a
  responsive floor (out of this frontend island).
- Refresh `.claude/skills/frontend-enforcement/SKILL.md` from the retired v5 amber/charcoal palette
  to tozpembe rose/gold (it still names "phosphor amber" as the accent and bans `system-ui` even as a
  trailing fallback), so the skill matches DESIGN.md + `tests/design-slop-gate.spec.ts`.
