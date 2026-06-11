---
name: vibemix
description: AI DJ co-host. Forged Obsidian Chrome (tozpembe) visual system, warm rose-shifted void + one soft-rose sign-of-life per panel, gold quarantined to heat numerics
colors:
  void-0: "#141113"
  void-5: "#1A1719"
  void-8: "#1F1B1E"
  void-10: "#262225"
  void-12: "#2B262A"
  void-15: "#322D31"
  void-20: "#3C373B"
  void-25: "#474146"
  ink-100: "#F2EFF1"
  ink-80: "#D8D4D7"
  ink-60: "#C5C0C3"
  ink-40: "#ADA8AB"
  ink-20: "#8A858A"
  brand: "#FFA5DF"
  brand-glow: "#FFB8E8"
  brand-press: "#B070A0"
  brand-04: "rgba(255, 165, 223, 0.04)"
  brand-08: "rgba(255, 165, 223, 0.08)"
  brand-12: "rgba(255, 165, 223, 0.12)"
  brand-16: "rgba(255, 165, 223, 0.16)"
  brand-22: "rgba(255, 165, 223, 0.22)"
  brand-40: "rgba(255, 165, 223, 0.40)"
  brand-65: "rgba(255, 165, 223, 0.65)"
  gold: "#e8c47a"
  gold-soft: "rgba(232, 196, 122, 0.55)"
  gold-glow: "rgba(232, 196, 122, 0.30)"
  glass-1: "rgba(31, 27, 30, 0.82)"
  glass-2: "rgba(38, 34, 37, 0.64)"
  glass-3: "rgba(20, 17, 19, 0.90)"
  border-subtle: "rgba(243, 239, 242, 0.09)"
  border-default: "rgba(243, 239, 242, 0.15)"
  border-strong: "rgba(243, 239, 242, 0.25)"
  surface-void: "#141113"
  surface-base: "#1A1719"
  surface-raised: "#262225"
  surface-float: "#3C373B"
  led-ok: "#6dd44a"
  led-warn: "#f4c542"
  led-fault: "#d4413a"
typography:
  display:
    fontFamily: "Saira, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0"
  headline:
    fontFamily: "Saira, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.04em"
  title:
    fontFamily: "Saira, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "0.02em"
  body:
    fontFamily: "Saira, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "normal"
  serif:
    fontFamily: "Instrument Serif, Georgia, serif"
    fontSize: "clamp(30px, 5vw, 58px)"   # deck hero / live line / lead track names
    fontSizeSmall: "clamp(22px, 3vw, 30px)"   # surface-empty title
    fontWeight: 400
    lineHeight: 1.1
    letterSpacing: "0"
  label:
    fontFamily: "Saira, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "0.22em"
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: "0.08em"
rounded:
  sm: "2px"
  md: "6px"
  lg: "10px"
  shell-sm: "6px"
  shell-md: "10px"
spacing:
  sp-1: "4px"
  sp-2: "8px"
  sp-3: "12px"
  sp-4: "16px"
  sp-5: "24px"
  sp-6: "40px"
  sp-7: "64px"
  sp-8: "96px"
shell:
  chrome-h: "28px"
  sidebar-collapsed: "72px"
  sidebar-expanded: "260px"
  panel-w: "280px"
motion:
  ease-brand: "cubic-bezier(0.16, 1, 0.3, 1)"
  bpm-beat: "461ms"
  bpm-bar: "1846ms"
  led-pulse: "1400ms"
  border-sweep: "22s"
components:
  glass-tile:
    backgroundColor: "{colors.glass-2}"
    rounded: "{rounded.md}"
    padding: "{spacing.sp-4}"
  button-primary:
    backgroundColor: "linear-gradient(180deg, {colors.brand-16} 0%, {colors.brand-04} 100%)"
    textColor: "{colors.brand}"
    rounded: "{rounded.sm}"
    padding: "9px 24px"
    typography: "{typography.label}"
  titlebar:
    backgroundColor: "rgba(0, 0, 0, 0.55)"
    textColor: "{colors.ink-100}"
    height: "56px"
    padding: "0 {spacing.sp-5}"
  shell-chrome:
    backgroundColor: "rgba(34, 29, 32, 0.55)"
    height: "{shell.chrome-h}"
---

# Design System: vibemix

## 1. Overview

**Creative North Star: "Forged Obsidian Chrome" (tozpembe)**

vibemix's port of Bravoh's "Forged Obsidian Chrome v21.0". The screen is a warm, rose-shifted near-black slab of machined obsidian: mostly void, a single soft-rose light per panel catching a hairline lip, gold held in reserve for heat. It keeps the v5 ethos, a Pioneer CDJ-3000 sitting at rest on the booth, breathing, and re-skins it from cold-void-plus-amber to warm-void-plus-rose, then folds vibemix's scattered windows into one self-arranging shell. The surface is hardware tactility translated into glass, warm void, and one accent; it does not perform, it sits.

This direction **supersedes the v5 "CDJ Whisper" amber system** (cold blue-black `#000`-`#11141c` + amber `#ff8a3d`). The visual contract is `mocks/vibemix-bravoh-grade-pink.html`; the parent study and the per-surface map live in `docs/design/bravoh-design-language.md` and `docs/design/vibemix-translation-layer.md`. The token migration is alias-based: every v5 token name (`--amber*`, `--silk*`, `--glass*`, `--void*`, `--glow*`) is preserved as a deprecated alias pointing at the tozpembe palette, so all existing surfaces re-tone for free.

What the rebuild adds beyond the re-skin: a **cohesive DesktopShell** (fixed sidebar furniture, an offset recessed main, a contextual grounding panel, a Cmd+K palette, a quiet floating status) that **self-arranges** around the activation state, idle → listening → live, with no setup screen. The contract is "pick it up, start play, everything arranges, go."

The system rejects the same AI-tool defaults v5 did, plus the ones the rose palette could newly invite: no neon glow on black, no glassmorphism stack of floating cards, no gradient-text headlines, no hero-metric layouts, no chatbot bubble UI, no lucide-icon-on-card patterns, no music-app cliché (gradient waveform hero, album-art bloom, Spotify-green CTAs). Rose must never drift toward "cute pink SaaS"; gold must never drift toward "navy-and-gold finance dashboard." The reference is forged hardware, not Spotify and not OpenAI.

**Key characteristics:**
- Warm near-black void ladder (`#141113` → `#474146`), obsidian-deep, warmth a whisper not a tint
- One soft-rose sign-of-life per panel, spent as a low-alpha wash via an explicit alpha ladder, never a fill
- Gold (`#e8c47a`) quarantined to Camelot / heat / energy-delta numerics: the one allowed second hue
- Hairline borders are NEUTRAL warm-white at very low alpha (never rose-tinted: pink edges everywhere graded the whole app mauve); tactility from inset bezels + a 0.5px neutral chrome highlight, never faux-3D
- Saira variable display + JetBrains Mono numerics today; Geist + Geist Mono + Instrument Serif is the locked target (Phase 1b)
- Restrained motion: 22s border sweep, 1.4s LED pulse, BPM-locked beats, eased (no spring, no square flash)
- Multi-layer film grain (overlay-blended, ~2.5% opacity) gives every surface a physical feel

## 2. Colors

The palette is a warm void stack carrying one rose, with gold held back for heat. Everything else is ink text at varying alpha, status LEDs at component-local scope, and atmospheric washes that are opt-in only (the body no longer paints them).

### Primary

- **Soft-Rose Brand** (`#FFA5DF`): the single sign-of-life accent. Used as the focus ring, the active nav indicator, the breathing border sweep on the session deck, the citation chip, the tail cursor on the co-host line, the Restart button. Spent through an explicit alpha ladder (`--brand-03` … `--brand-78`), almost always at low alpha as a wash. **Never a fill on a large surface.**
- **Brand Glow** (`#FFB8E8`): the warm top-highlight tone and the citation-chip foreground text.
- **Brand Press** (`#B070A0`): the pressed/active darker rose (also the `--amber-deep` alias target).

### Gold Heat (quarantined)

- **Gold** (`#e8c47a`): the one allowed second hue, reserved for Camelot key tags, heat, and energy-delta numerics. `--gold-soft` (0.55) and `--gold-glow` (0.30) are its only alpha steps. Gold is **never** an atmospheric/ambient layer and never competes with rose for the panel sign-of-life. If you reach for gold outside a heat/key numeric, you are wrong.

### Neutral

- **Void-0 → Void-25** (`#141113` → `#474146`): the warm near-black ladder, re-graded deep (2026-06-11). Void-0 is the floor; the body vignette fades over it. `--surface-void/base/raised/float` map to void-0/5/10/20 as the four-level elevation.
- **Glass-1 / Glass-2 / Glass-3** (rgba `0.80` / `0.62` / `0.88`, warm-tinted): the three glass intensities. Glass-1 primary panel, Glass-2 secondary tiles, Glass-3 recessed display windows. Dark and sealing, not floating-translucent.
- **Ink-100 → Ink-20** (`#F2EFF1` → `#8A858A`): the warm off-white text ladder, named semantically as `--text-primary/secondary/tertiary/muted/disabled`. Replaces v5 silk.
- **Borders** (`--border-subtle/default/strong`, NEUTRAL warm-white rgba `0.09` / `0.15` / `0.25`): hairlines and bezel highlights, quieter than brand, never rose-tinted. Never used as fills.

### Material

- **Chrome highlight** (`--chrome-highlight`: `inset 0 0.5px 0 rgba(246,243,245,0.12)`): the signature "light catching a machined lip", a half-pixel NEUTRAL top edge on chrome and slabs. Machined metal catches white light; only brand objects carry rose.
- **Specular / rim / shadows**: `--grad-specular`, `--rim-brand`, `--shadow-inset/-pressed/-float`, `--text-3d/-emboss`. Depth is bezel and rim, not a drop-shadow stack.

### Atmospheric (opt-in only)

The five v5 night-rave washes (`--rave-magenta/pink/cyan/purple/teal`) survive as tokens but **the body no longer paints them**. The warm void floor (a vignette over the void ladder) carries the room now. Atmospherics are opt-in per surface and remain subliminal: if you can name the color when looking at the screen, it is too strong.

### Status LEDs (component-scope only)

- **LED OK** (`#6dd44a`): audio flowing / ready / armed
- **LED Warn** (`#f4c542`): calibrating / checking
- **LED Fault** (`#d4413a`): crash banner, REC pill, hard-fail dots

### Named Rules

**The One-Rose Rule (was One-Amber).** A panel may carry exactly one breathing sign-of-life, the rose focus ring, citation chip, border sweep, tail cursor, or LED. Two things breathing in the same panel is forbidden. On the live deck the tail cursor is the sign-of-life; the energy field behind it is held static (opacity ramps by activation, it does not breathe) precisely so the cursor stays singular.

**Gold-Is-Quarantined.** Gold appears only on Camelot/key/heat/energy-delta numerics. It is never an ambient field, never a panel accent, never paired with rose as a "two-accent" scheme. This keeps the signature unambiguously rose and blocks the navy-and-gold dashboard drift.

**The Hex-Outside-Tokens Ban.** Components MUST NOT declare hex colors; they read `var(--token)` exclusively. Only `tokens.css` may contain `#xxxxxx`. (Structural neutral scrims for window chrome may inline raw `rgba()` neutrals; all *branded* color comes from tokens.) Enforced by `frontend-enforcement` + `tests/design-slop-gate.spec.ts`.

**The Migration-Alias Contract.** Every v5 token name is a live alias on the tozpembe palette. Prefer the canonical tokens (`--void-N` / `--ink-N` / `--brand*` / `--gold*` / `--surface-*` / `--text-*` / `--border-*`) in new code; do not reintroduce hard v5 hexes.

## 3. Typography

**Shipping today:** Saira (variable `wdth` 75–125, `wght` 300–800) for display/body, JetBrains Mono (400/500/600) for numerics and labels, both vendored locally as WOFF2 (SHA-256 attested in `tauri/ui/LICENSE-3RD-PARTY.md`). The cohost hero serif (`--type-serif`) points at **Instrument Serif** and falls back to **Georgia** until vendored.

**Locked target (Phase 1b):** Geist Sans (body/UI) + Geist Mono (labels/numerics) + Instrument Serif (cohost hero + lead track names). Vendoring those WOFF2 offline, and amending the `design-slop-gate` font allow-list, is the open Phase-1b task. Until it lands, the gate locks the shipped faces to Saira + JetBrains Mono only.

**Character:** condensed Saira (`wdth: 85`) + heavy uppercase tracking carries the "industrial spec-sheet" voice (Pioneer manuals, Roland labels). JetBrains Mono numerics carry the "live readout" voice. The Instrument Serif hero is the one warm, human note: the co-host *speaking*, set large and quiet on the void.

### Hierarchy

- **Serif hero** (Instrument Serif → Georgia, weight 400, line 1.1): the only serif in the system, and the only place type gets large. Two tiers — the **deck hero / live line / lead track names** at `clamp(30px, 5vw, 58px)`, and the **surface-empty title** at `clamp(22px, 3vw, 30px)`.
- **Display** (Saira `wdth: 85`, 700, 18px, uppercase): the wordmark. Single use.
- **Headline / Title** (Saira 600 / 500, 14px / 13px): section titles, step names, button labels.
- **Body** (Saira 400, 14px, line 1.45): prose, help text. Max line length 65–75ch.
- **Label** (Saira `wdth: 85`, 600, 11px, tracking 0.22em, uppercase): button labels, system status, the instrument-panel voice.
- **Mono** (JetBrains Mono 400, 11px, tracking 0.08em): clock, BPM, RMS, timestamps, controller indicators, the shell's sidebar-nav accelerators (expanded rail; they hide when collapsed) and palette hints.

### Named Rules

**The font-stack lead rule.** Every `font-family` declaration must lead with a brand face (Saira / JetBrains Mono) or a `var(--type-*)` token; `system-ui` / `Georgia` may appear only as a trailing fallback. Generic platform fonts as a brand face are the #1 AI-slop tell, gate-enforced.

**The Tracking-by-Case Rule.** Uppercase carries ≥0.06em (button labels and status pills go to 0.22em); lowercase carries 0em. No sentence-case-at-+0.04em middle ground, that reads AI-generated.

## 4. Elevation

Flat by default. Depth is conveyed through **inset bezels** (the `--chrome-highlight` 0.5px warm-rose top lip + `--shadow-inset` / `--rim-brand`) and **hairline borders**, not drop shadows. The reference is machined faceplate: light catches the top edge, shadow falls on the bottom, the surface is matte.

Drop shadows appear in four governed places only:
1. **The hero glass tile** (`--shadow-float` / `vmx-tile[data-tile="hero"]`): one ambient drop per view, "the deck sits on a desk."
2. **The rose glow ring** (`--glow-soft` / `--glow-strong`): focused inputs, the Restart button, the alert tile, "the indicator is lit."
3. **The recessed-stage offset** (shell only): a 48px inset gradient where the offset main meets the raised sidebar slab, so the stage reads as recessed *beneath* the chrome.
4. **The grounding-drawer slide-over** (shell only): the contextual right panel casts one ambient drop (`-14px 0 60px rgba(0,0,0,0.5)`) as it slides over the recessed stage, so the drawer reads as floating above the deck rather than flush with it.

There is no card stack, no z-index ladder of floating elements, no shadow-on-hover lift. The shell's z-index is governed by a single `--z-*` ladder declared on `#shell-root` in `shell.css` (base 0, stage 1, recess 2, footer 20, sidebar 40, panel 50, palette 1000), read via `var(--z-*)` everywhere, not ad-hoc literals.

### Named Rules

**The Flat-By-Default Rule.** Surfaces are flat at rest; drops appear only on the single hero tile, on rose state, as the shell recess gradient, and on the grounding-drawer slide-over.

**The Inset-Bezel-Over-Shadow Rule.** For tactility reach for the inset bezel + chrome highlight, not a `box-shadow` drop.

## 5. The Cohesive Shell

The structural lever of the rebuild: vibemix's surfaces read as ONE app, not a scatter of separate windows. Implemented in vanilla TS under `tauri/ui/src/shell/` (no React, no cmdk), state in a single `shell-store.ts` (the role Bravoh's `DesktopSidebarContext` plays), reflected onto `#shell-root` as data-attributes for optimistic repaint.

**Folded into one window:** Deck, Crate, Learn, Debrief, Settings, mounted keep-alive (all five in the DOM at once, one `.is-active`). **Kept as separate transparent windows:** the floating Pill, the click-through Overlay, the Mascot.

### Furniture

- **Sidebar** (fixed slab, `--sidebar-expanded` 260px ↔ `--sidebar-collapsed` 72px, `Ctrl+\`): brand mark with a breathing "ear", one-word nav (label == route, no route-vs-label split), Cmd accelerators, a co-host foot pill (a static lit rose dot). A faint rose LED seam runs static along its right edge. The brand ear is the sidebar's only breathing mark (One-Rose).
- **Main** (recessed stage): offset by `margin-left: var(--sidebar-w)` (not a flex gap) so it recesses beneath the chrome, with the 48px inset recess gradient on its leading edge.
- **Grounding panel** (`--panel-w` 280px, `Ctrl+]`): the contextual right drawer where citations and the next-track suggestion mount during a live set. Honest at idle ("Nothing to ground yet").
- **Command palette** (`Cmd/Ctrl+K`): self-contained subsequence matcher, arrow/Enter/Esc nav. Surface jumps + structural commands.
- **Floating status** (bottom-right, quiet): a connection dot + label. **Honest:** idle + disconnected is expected, never a fault (cardinal invariant #5).

### Self-arranging activation

The shell rearranges itself around `idle → listening → live` with no setup screen. Going **live** auto-opens the grounding panel (the receipt for what the co-host just reacted to); dropping to **idle** closes it. The layout arranges itself around the music, the user does not configure panels. This is the "pick it up, start play, everything arranges, go" contract.

### Empty states

Each surface's at-rest interior is a powered deck waiting, not a stub or a SaaS empty-state template: one dim engraved glyph (`--text-disabled`, geometric mark, never a lucide icon), a serif title, and one grounded co-host line in first person. No card, no hero metric, no CTA grid. Copy is data (`SURFACES[].empty`).

## 6. Presence Grammar

How the co-host shows it is alive without performing:

- **The tail cursor:** a small rose block on the co-host's live line, an eased fade on the LED-pulse cadence (not a hard square flash). The single sign-of-life on the deck when live. Steady-on under reduced motion.
- **The energy field:** a pure-rose deck-light bloom rising from below the stage. Opacity ramps by activation (still at idle, faint at listening, present at live) but **never breathes**, so the cursor stays the sole rhythmic mark. Subliminal: under the "name it and it's too strong" threshold, rose only (no gold).
- **The brand ear:** a single slow-breathing rose dot by the wordmark, the sidebar's one sign-of-life that the co-host is awake and listening. It breathes only while NOT live; once live, the deck tail cursor becomes the screen's single breath and the ear steadies. The foot-pill ear and the right-edge LED seam are static lit rose, not a second breath (One-Rose: a panel breathes in exactly one place).
- **The border sweep** (`--motion-border-sweep` 22s): a rose conic light traveling the session-deck perimeter, frozen under `prefers-reduced-motion`. Session deck only.

### Named Rules

**Sign-of-life, not flashlight.** Motion is restrained, eased breathing, never marketing choreography, never spring/elastic, never a square strobe. At most ONE element breathes on screen at a time (PRODUCT principle 3): while live the deck tail cursor is it, so the sidebar brand ear steadies and the connection dot stays steady-lit when connected (only "reconnecting" pulses). The BPM-locked beat tokens (`--bpm-beat` 461ms, `--bpm-bar` 1846ms) are reserved for when live tempo wires in; until then the breathing and tail-cursor cadences are fixed eased timings (the tail cursor runs on `--motion-led-pulse`).

**The co-host speaks, in its own voice.** The live line and empty-state copy are the co-host talking, first person, short, specific, grounded ("I learn your crate by ear"). Not a chatbot (no bubble, no send button, no "thinking…" dots), not a tagline ("the deck speaks when the music does" is a *brand* line, never voiced as the co-host), not marketing reassurance ("works out of the box" is a principle, not a line to recite).

## 7. Components

### Glass Tile (the universal surface)

One recipe, `.vmx-tile`, with three `data-tile` density variants. Base = `glass-2` + light blur + inset bezel; **hero** adds the `--shadow-float` drop + a faint outer ring (one per view); **alert** swaps the border to rose-40, adds an inner rose glow + `--glow-soft` halo (BlackHole-missing, permissions, errors). Components own only their internal layout; the glass shell is utility-driven.

### Buttons

- **Shape:** 2px radius (`--rad-sm`), sharper than tiles. Padding 9px × 24px.
- **Primary (Rose):** the Restart button is the canonical exemplar. Border `brand-40`, gradient `brand-16 → brand-04`, inset top warm-white + inset rose, text `--brand` with a soft text-shadow, label type (Saira 600, 10px, 0.22em, uppercase), min-width 144px. Hover lifts the gradient to `brand-22 → brand-06`. No transform.
- **Secondary / Ghost:** `--text-secondary` on bare glass, no border, for Cancel / Skip / Not now.
- **Disabled:** `not-allowed`, ~0.4 opacity, no fade-out gradient.

### Inputs

Glass-3 background, 1px border, 6px radius, ink text, JBM for numerics. **Focus:** 2px rose outline + 2px offset + `--glow-soft`, ring outside the perimeter. **Error:** border → `led-fault` + inner fault glow.

### Navigation & chrome

The shell chrome (28px drag bar + mono clock), titlebar (56px), step strip (64px), and status bar (40px) are deck chrome, not tiles: full-width hairline border, `rgba(0,0,0,0.55)` backing + light blur + `--chrome-highlight`. The shell sidebar/panel/footer follow the geometry tokens in §5.

### Signature: the Mascot Overlay

A 320×420 fully transparent, always-on-top WebGL window (Three.js, single VTuber-style character with a mood state machine). `body` is `transparent`; no chrome, no rim-light, no second border-sweep, the character IS the surface. `aria-hidden`, decorative, never carries information the transcript doesn't already say.

## 8. Do's and Don'ts

### Do:

- **Do** reach for `.vmx-tile` first; read `var(--token)` exclusively for color.
- **Do** carry one rose sign-of-life per panel, focus ring, citation chip, tail cursor, LED, or sweep. Not two.
- **Do** keep gold on Camelot/key/heat/energy numerics only.
- **Do** set uppercase labels at Saira `wdth: 85`, 600, 0.22em; use JetBrains Mono for every numeric.
- **Do** write co-host copy in the first person, short, specific, grounded; vary cadence so adjacent lines don't share a template.
- **Do** keep ambient/energy layers subliminal (rose only) and freeze motion under `prefers-reduced-motion`.
- **Do** let the shell self-arrange around activation; keep the floating status honest (idle ≠ fault).
- **Do** render film grain overlay-blended at ~2.5% for the physical-material feel.

### Don't:

- **Don't** ship gradient text (`background-clip: text` over a gradient). Emphasis via weight/size/color.
- **Don't** use glassmorphism as default; tozpembe glass is dark and sealing (0.62–0.88 alpha), not floating-translucent.
- **Don't** stack drop shadows; one hero drop + rose state + the shell recess gradient, nothing else.
- **Don't** let rose become a fill or drift toward cute-pink SaaS; spend it as a low-alpha wash.
- **Don't** pair gold with rose as a two-accent scheme, or use gold as an ambient field (navy-and-gold dashboard drift).
- **Don't** ship two breathing elements in one panel; the deck energy field stays static so the tail cursor is singular.
- **Don't** ship a chatbot bubble UI, a hero-metric layout, identical card grids, or lucide-icon-on-card patterns.
- **Don't** voice brand taglines or marketing reassurance as the co-host; the co-host speaks in the first person.
- **Don't** use em dashes in copy. Use commas, colons, semicolons, periods, or parentheses. Also not `--`.
- **Don't** ride spring/elastic motion or a hard square flash; ease-out exponential only.
- **Don't** ship onboarding-tour overlays or welcome modals; the product opens, boots, and works.
