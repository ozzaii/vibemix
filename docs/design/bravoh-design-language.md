# Bravoh Design Language — "Forged Obsidian Chrome v21.0"

> What vibemix's locked direction inherits from, read straight from the live Bravoh
> frontend source (`bravoh-clean/frontend`, React 19 + Vite, native-wrapped via
> Capacitor on mobile and Tauri on desktop). This is the understanding doc. The
> companion `vibemix-translation-layer.md` turns it into a build.

## Lineage, stated plainly

vibemix's "tozpembe" direction is not inspired by Bravoh. It **is** Bravoh's design
system, re-pointed at a DJ co-host. The locked mock `mocks/vibemix-bravoh-grade-pink.html`
lifts Bravoh's warm void ladder, its soft-rose accent, its 4-level elevation, its
ease-out-cubic motion, and its DesktopShell composition almost verbatim. So the goal of
studying Bravoh is not "find a style to copy"; it is "understand the system well enough
to extend it without breaking its discipline, then make the DJ surface sexier than the
parent."

Bravoh's design system is internally named **Forged Obsidian Chrome v21.0**. The name
carries the whole thesis: forged (machined hardware, not soft Material), obsidian (warm
near-black, not gray), chrome (a single lit edge catches the light).

## The one idea

A single warm accent, spent almost entirely as low-alpha **wash**, over a rose-shifted
near-black ladder. Everything else follows from that. Brand color almost never fills a
surface; it tints a border, a selected row, a focus ring. Depth is built from warm-black
steps and one whisper-thin top-edge highlight, never from a glow or a bevel. The result
reads as powered hardware sitting at rest, not as a web page.

The discipline is enforced by infrastructure, not willpower. There are 28 explicit alpha
tokens (`--color-brand-02` through `--color-brand-90`), and an ESLint rule forbids new
inline `rgba()`. They were introduced (v37.0, Phase 403) to kill 500-plus hand-written
alpha values. The lesson for vibemix: if restraint matters, encode it as the only legal
path, do not leave it to taste at each call site.

## 1. Token system

`index.css` `:root` is the single source of truth. Three layers, strictly separated:
primitive hex (raw values, never touched by components), a semantic layer named by role
(the only layer components read), and a Tailwind bridge that holds zero hex of its own and
only passes through CSS vars. The TS files under `design-system/tokens/` exist only to
feed inline Framer Motion styles, plus a few JS-only constants (springs, z-index).

**Color.**
- Void ladder (warm near-black, rose-shifted, never gray): `#1A1618`(0) `#221D20`(5)
  `#282326`(8) `#302A2E`(10) `#352F33`(12) `#3D373A`(15) `#474144`(20) `#524C4F`(25).
- Ink ladder (warm off-white): `#F2EFF1`(100) `#D8D4D7`(80) `#C5C0C3`(60) `#ADA8AB`(40)
  `#8A858A`(20).
- Brand triad: `--color-brand #FFA5DF` (soft rose), glow `#FFB8E8`, press `#B070A0`.
- Brand alpha ladder: 28 tokens, `rgba(255,165,223, α)` from 0.02 to 0.90. The loudest the
  brand ever gets on a surface is the primary CTA at 0.16 fill / 0.22 border.
- Borders are quieter than brand: warm-white `rgba(255,220,240, α)` at 0.08 / 0.12 / 0.18.
- Agent signatures: strategist, content, creative, music. The **music agent is gold
  `#e8c47a`**, which is exactly the "heat" accent vibemix reserves for harmonic/energy data.
- Semantic status: success `#6EE7B7`, warning `#FCD34D`, error `#FC8181`, used at low
  alpha (0.08 to 0.12) in chip variants, never as loud fills.

**Type.** Four roles. `--font-primary` resolves to Geist Sans (body weight 475),
`--font-display`/`--font-serif` to PP Mondwest, `--font-mono` to Geist Mono for all data
and uppercase tracked labels. Type scale runs display-xl 48px down to micro 10px, with a
separate mono "data" scale (20/16/12px, tight tracking). Mono is the "system voice";
prose is the "human voice." (Note: the **locked vibemix mock uses Instrument Serif**, not
PP Mondwest, for its hero line. See the translation doc.)

**Space, radius, elevation.** Tailwind's 4px base is canonical, with four custom stops
(18/52/60/72px). Radius runs 6 to 32px, though components frequently hardcode 12px.
Elevation is four surfaces: void / base / raised / float = void-0 / 5 / 10 / 20. Depth is
carried by the step plus a signature `--chrome-highlight: inset 0 0.5px 0
rgba(255,200,235,0.07)` top-edge whisper and stacked black drop shadows. **Glass is dead
on purpose**: `--blur: none` globally, solid surfaces, an explicit reaction against the
frosted-card SaaS reflex.

**Motion.** One signature ease, `--ease-brand: cubic-bezier(0.16,1,0.3,1)` (ease-out
cubic). A tight duration set: fast 150ms, normal 250ms, slow 400ms. Springs are
**explicitly rejected for panels** ("spring reads as toy-like, ease-out reads as
intentional"); spring is reserved for card landings. Z-index is a named scale (zChat 10 to
zToast 3000), no inline literals allowed.

## 2. Shell composition — the recessed stage

This is why the desktop app reads as a native app and not a web page, and it is the part
vibemix is missing entirely. One decision, repeated everywhere: **the chrome is fixed
furniture and the content is a recess beneath it.** Nothing scrolls the page; a fixed
frame holds a swappable interior.

- The root is `h-screen flex flex-col overflow-hidden`. The sidebar is `position: fixed`
  (`rgba(24,20,22,0.98)`, 1px warm-white right border), removed from document flow.
- The center `<main>` is **not** a flex sibling beside the sidebar. It is pushed with
  `marginLeft: sidebarWidth` (260 expanded / 72 collapsed), animated `0.3s var(--ease-brand)`.
  That inline margin, not a grid gap, is what makes the stage feel like it slides under
  standing furniture.
- The main region pins a **48px inset shadow** to its left edge
  (`linear-gradient(90deg, rgba(0,0,0,0.15), transparent)` at z-20) so the sidebar reads
  as a raised slab the content recesses beneath. Depth, not layout, sells the effect.
- Both inner edges run animated LED "spark" seams (sidebar `::before` on a 10s loop, panel
  on a 6s `chrome-shift`, `mix-blend-mode: screen`) so the chrome reads as powered metal.
- The right panel (`DesktopPanel`, 380px, header labeled "Workbench") mounts only on demand
  and stacks five shadows to feel milled.
- Every structural surface has a keyboard chord: `Ctrl+\` collapses the sidebar (persisted
  to localStorage, width animated 200ms), `Ctrl+]` closes the panel, `Cmd+K` opens a lazy
  command palette (z 1000), `?` opens a shortcuts sheet (z 1001).
- **Pages persist, they do not navigate.** `DesktopPages` keeps every visited route mounted
  and hides inactive ones with `display:none`, so tab switches are instant and stateful,
  like a tabbed desktop app. Tellingly, an `AnimatedOutlet` crossfade exists but has zero
  callers; the shell chose keep-alive over transition.
- A `StudioStatusFooter` floats bottom-right at 10px `text-white/30`, Tauri-only, rendering
  nothing on web. Quiet ambient telemetry that earns no attention until you look for it.
- Desktop and mobile fork at one `matchMedia('(min-width: 1024px)')` gate. Same four routes,
  two metaphors. (vibemix is desktop-only, so this fork collapses to just the desktop shell.)

## 3. AI presence — one being, three altitudes

Bravoh's hardest problem is vibemix's hardest problem: make "what is the AI doing right
now" legible at a glance, without ever feeling like a spinner or a script.

- **One agent.** `types.ts` keeps five legacy persona names but resolves every one to a
  single `BRAVOH_CONFIG` tinted `#FFA5DF`. Variety lives in a 45-entry tool taxonomy with a
  six-bucket category-color map, never in competing voices. The user tracks one being.
- **Three altitudes, one vocabulary.** Ambient: a pixel grid with three named loops, `idle`
  (5 to 7s breathing), `streaming` (0.7s pulse), `tooling` (0.9s radial ripple). Mid-level:
  a five-bar equalizer on deliberately prime-ish durations (0.47/0.61/0.53/0.71/0.59s) so it
  never mechanically syncs, plus a dual-sweep shimmer. High-level: an `AgenticPanel`
  timeline of LED nodes that **self-folds**: a finished card collapses to a mini-pill after
  2000ms, a whole run collapses to one "N tools, Xs" chip with stacked icons and one success
  haptic. Crucially, even the collapsed pill keeps the tool icon, name, and check, so folding
  never erases the receipt.
- **Status carries rhythm, not just a label.** The connection dot breathes green over 7s,
  pulses amber at 1.5s while reconnecting, dims red to 0.7 when down. You read state by feel
  before you read text.
- **Streaming gets one glyph.** A single ember-gradient `TailCursor` (rose to amber)
  breathes at 1.4s, only at the tail of the stream, never per token.
- **Errors are warm, never raw red.** A 4% amber surface with a 2px accent bar.
- **Proactive observations are quiet.** A `◇ Noticed` chip slides in over 240ms, no left
  border, no sound, optimistic dismiss. The exact register for unprompted feedback that does
  not break flow.
- **The command palette** is Raycast-grade restraint on `cmdk`: a 640px panel on
  `--surface-base`, brand tint only on the selected 44px row, fusing a seed registry with six
  frecency-ranked sources, the Cmd+K binding owned by a hook so the component stays pure render.

## 4. Component vocabulary and motion

Bravoh refuses generic primitives. The entire interactive surface is two buttons
(`VoidButton` primary, `GhostButton` secondary), one card with four elevation variants
(`ChromeCard`: default / raised / float / tool), one chip (`ChromeChip`, five semantic
colors), one input (`ChromeInput`), and a few labels. Each is a ~40-line wrapper whose only
job is to map props to a named CSS class; the styling lives in `index.css`. This split is
why the system stays coherent across hundreds of files.

The material is "chrome": a flat warm-void surface, one hairline warm-white border, and the
`--chrome-highlight` top-edge whisper. Interaction is "turn the accent up one rung": hover
lifts border alpha 0.12 to 0.22 and bumps one shadow; press deepens the brand fill 0.16 to
0.26; input focus paints a 1.5px brand ring plus a 12px bloom. Nothing glows at rest except
intentional "alive" signals.

Those alive signals are the **hardware-rack dialect**: `SessionStrip` and `PushCardStack`
swap the pink chrome for amber (`#F5A623`), an SVG fractal-noise grain at 0.025 opacity,
monospace LCD type, and a VU meter. An amber LED pulses faster as activity is more recent
(1s active, 4s idle). This dialect is the one vibemix's live deck should speak natively.

Motion is a closed vocabulary: `depthMotion` defines 14 named verbs (settle, peek, fold,
drill, lift, snap, flash, pulse, shake, and more), each tagged tier A/B/C for reduced-motion
and long-session attenuation. Raw inline animation is forbidden. gsap appears in exactly one
file; everything else is Framer Motion or CSS keyframes.

## 5. Information architecture, onboarding, voice

- **IA by subtraction.** The shipped navigation is exactly four tabs, declared once, with the
  kill list documented in a comment ("Dropped per F-03: Calendar, Lab, Intelligence,
  Dashboard, Lane Feed, Pool-UI"). Every future surface has to argue against a decision
  already made.
- **Chat is home.** Root, post-login, and end-of-onboarding all funnel to `/companion`. The
  conversation is the product, not a panel beside it.
- **One real artifact unlocks everything.** Onboarding is three steps (upload one track
  required, Instagram and captions skippable), then a seeder into the app. The premise is
  "give me one real thing and I do the rest."
- **Empty is an invitation.** `EmptyState.tsx` says so verbatim: "Empty states should feel
  like an invitation, not a dead end. Breathing icon, atmospheric glow, staggered text
  reveals." Empties are also stateful: the suggested next moves are computed from track count
  and genre, so the void is always pre-loaded with the next three best actions.
- **Voice is first-person, present-tense, intimate.** "Show me what you're about", "I'll
  break it down on the spot", "I hear you. Everything I do from here is tuned to this."
  Errors stay in character ("Signal interrupted", "Lost in the frequency"). This register is
  the exact target for vibemix's "real DJ friend in your ear."
- **i18n is real.** en, it, and tr ship with identical 10-namespace structure and idiomatic
  (not literal) translation, every string keyed with an inline English fallback.

## 6. Audio and data visualization — energy as wallpaper

This is the direct answer to the hardest constraint: give the energy of the music without
bleeding the eyes. Bravoh's rule, applied everywhere: anything that reacts to live audio is
demoted to a background layer and never becomes the subject.

- The live spectrum is composited **behind** the content at `opacity: 0.35`, gradient capped
  near 19% alpha, peaks off, smoothed hard, `pointer-events: none`, and it fades rather than
  cuts. In the primary playback surface it is **disabled outright** because routing through
  an AudioContext risked silent iOS playback. Bravoh shipped less motion when motion had a
  real cost.
- What stays is **structural**: a static peak waveform of 24 or 48 discrete bars whose meaning
  lives in four opacity tiers (0.15 / 0.25 / 0.4 / 1.0). Energy reads as where you are and
  what matters, not as a dancing meter.
- Continuous levels never run a redraw loop: a VU meter is a 10px CSS-height bar with one hard
  flip to red above 0.85. Discrete metrics roll digit by digit via `@number-flow/react`.
  Analytical charts play one spring or dash-sweep on mount and then freeze.
- The viz palette is deliberately muted (`#b49ae0`, not neon), glows are alpha-clamped and
  dropped on mobile, and the only infinite motions are two gated life-signs.
- **Honesty over fullness.** A dev feature monitor dims sub-confidence rows to 40% and shows
  `--` rather than a fake-confident number. The UI admits when it cannot hear, which is
  exactly vibemix's "trust the audio" invariant made visible.

## 7. Where Bravoh itself could be sharper

Kaan asked to "even enhance it." The live source carries real drifts worth not inheriting:

- **Dead font preload.** `index.html` preloads `Satoshi-Variable.woff2` with no matching
  `@font-face`; the typography TS still lists "Inter" first and comments "Satoshi: primary",
  while the actual `--font-primary` resolves to Geist Sans. Three sources disagree about the
  primary face. Pick one, delete the dead preload.
- **Stale violet glow.** Tailwind's `glow-brand` tokens still reference `rgba(124,58,237,...)`
  from a pre-rose palette, so any component using `shadow-glow-brand` renders the wrong color.
- **Agent-color disagreement.** `index.css` and `colors.ts` ship different hexes for the
  strategist and creative agents. Two sources of truth.
- **Route-vs-label split.** Routes are functional (`/style-dna`) while labels are human
  ("DNA"); analytics, deep links, and copy end up speaking two vocabularies.
- **Copy tics.** The em-dash list cadence ("a track, a vibe, give me something") recurs across
  many subtitles until it reads as a tell. The premium staged loading copy already exists in
  the locale files but the shipped seeder uses a bare spinner instead.

vibemix should build the system **without** these drifts: one primary face, one accent with a
reconciled glow, one word per surface that is both route and label, and copy that varies its
cadence.

## 8. What vibemix should lift

The high-value, directly portable assets, in priority order:

1. **The recessed-stage shell** (fixed sidebar, marginLeft-pushed main, 48px inset recess,
   keep-alive surfaces, governed z-index, keyboard chords). This is the single biggest
   "one cohesive app" lever and it has no counterpart in the current code.
2. **The token discipline** (single `:root` source of truth, semantic layer, explicit alpha
   ladder, no hex in components) ported to vibemix's vanilla-TS `tokens.css`, which already
   enforces the no-hex rule.
3. **The presence grammar** (idle / streaming / tooling, TailCursor, the breathing connection
   dot, self-folding agentic timeline) for the live co-host line and the floating pill.
4. **The component material** (chrome-highlight top edge, two buttons, one card, accent-up-one-
   rung interaction) and the **hardware-rack dialect** (LED whose pulse encodes recency, VU
   meter, fractal grain) for the live deck.
5. **The energy-as-wallpaper rule** for meters, the spectrum, and the set-energy ribbon, with
   one upgrade: a Tauri desktop sidecar has no iOS AudioContext bug, so vibemix can finally
   ship the full live spectrum Bravoh had to cut, kept behind the deck readout at the same
   0.35 ceiling.
6. **The command palette** (`Cmd+K`, frecency sources, binding in a hook) as the desktop-native
   "understand and act in one keystroke" surface.
7. **The empty-state and voice thesis** (invitation not dead end, first-person present-tense),
   which maps onto vibemix's "Idle is not fault" invariant and "real DJ friend" persona.

## 9. Where vibemix diverges — sharper than the parent

Lifting the system faithfully also meant tightening it. These are the places the shipped vibemix
shell is deliberately stricter than the live Bravoh source, so a translator does not "restore" the
parent's looser behavior thinking it is more correct:

- **One breath per screen.** Bravoh runs the idle pixel-grid breath, the five-bar equalizer, and the
  connection-dot breath at the same time. vibemix's One-Rose rule forbids more than one breathing
  mark on screen at once: live → the deck tail cursor, reconnecting → the connection dot, otherwise →
  the sidebar brand ear; the energy field, the LED seam, and the foot-pill ear are held static lit.
- **The connection dot is steady-lit when connected.** Bravoh breathes it over 7s; vibemix holds it
  still (only "reconnecting" pulses) so the live tail cursor keeps the one-breath budget.
- **The tail cursor is solid rose, not a gradient.** Bravoh's `TailCursor` is a rose-to-amber ember
  gradient; vibemix uses a solid `--brand` block, because decorative gradients are banned and gold is
  quarantined to heat numerics.
- **The LED seam is static.** Bravoh's sidebar/panel seams crawl on 6–10s loops; vibemix holds the
  rose seam still (a machined lip, not a runner) for the same one-breath reason.
- **Governed stacking is a CSS `--z-*` ladder**, not a JS constant map — it lives in the stylesheet
  beside the rules that use it, so there is no second JS source of truth to drift.
- **The wordmark is uppercase condensed Saira**, matching the titlebar treatment, not a lowercase
  one-off.

The common thread: Bravoh's §7 drifts (dead font preload, stale violet glow, agent-color
disagreement, route-vs-label split) are all *two-sources-of-truth* bugs. Every vibemix divergence
pushes the other way, toward *one* source of truth and *one* sign-of-life. That is the discipline to
carry into every surface, not just the shell.
