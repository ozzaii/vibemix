---
name: vibemix
description: AI DJ co-host — CDJ Whisper v5 visual system, deep void + one amber light per panel
colors:
  void: "#000000"
  void-1: "#020205"
  void-2: "#05070b"
  void-3: "#0a0c12"
  void-4: "#11141c"
  glass-1: "rgba(8, 10, 16, 0.78)"
  glass-2: "rgba(12, 14, 22, 0.62)"
  glass-3: "rgba(2, 3, 6, 0.88)"
  glass-edge: "rgba(255, 255, 255, 0.065)"
  glass-edge-up: "rgba(255, 255, 255, 0.110)"
  glass-top: "rgba(255, 255, 255, 0.055)"
  silk: "#d6cfc7"
  silk-65: "rgba(214, 207, 199, 0.65)"
  silk-40: "rgba(214, 207, 199, 0.40)"
  silk-22: "rgba(214, 207, 199, 0.22)"
  silk-12: "rgba(214, 207, 199, 0.12)"
  amber: "#ff8a3d"
  amber-deep: "#ff5a1a"
  amber-pale: "#ffb88a"
  amber-22: "rgba(255, 138, 61, 0.22)"
  amber-40: "rgba(255, 138, 61, 0.40)"
  amber-65: "rgba(255, 138, 61, 0.65)"
  led-ok: "#6dd44a"
  led-warn: "#f4c542"
  led-fault: "#d4413a"
typography:
  display:
    fontFamily: "Saira, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "0.06em"
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
spacing:
  sp-1: "4px"
  sp-2: "8px"
  sp-3: "12px"
  sp-4: "16px"
  sp-5: "24px"
  sp-6: "40px"
  sp-7: "64px"
  sp-8: "96px"
components:
  tile-base:
    backgroundColor: "{colors.glass-2}"
    rounded: "{rounded.md}"
    padding: "{spacing.sp-4}"
  tile-hero:
    backgroundColor: "{colors.glass-2}"
    rounded: "{rounded.md}"
    padding: "{spacing.sp-5}"
  tile-alert:
    backgroundColor: "{colors.glass-2}"
    rounded: "{rounded.md}"
    padding: "{spacing.sp-4}"
  button-primary:
    backgroundColor: "{colors.glass-2}"
    textColor: "{colors.amber}"
    rounded: "{rounded.sm}"
    padding: "9px 24px"
    typography: "{typography.label}"
  button-primary-hover:
    backgroundColor: "{colors.glass-1}"
    textColor: "{colors.amber}"
  titlebar:
    backgroundColor: "rgba(0, 0, 0, 0.55)"
    textColor: "{colors.silk}"
    height: "56px"
    padding: "0 {spacing.sp-5}"
  status-bar:
    backgroundColor: "rgba(0, 0, 0, 0.55)"
    textColor: "{colors.silk-65}"
    height: "40px"
    padding: "0 {spacing.sp-5}"
---

# Design System: vibemix

## 1. Overview

**Creative North Star: "CDJ Whisper"**

A Pioneer CDJ-3000 sitting on the booth at rest — mostly void, a single amber breath traveling the front face, hairline bezels catching the room light. That is the surface vibemix renders. The screen is not a software dashboard pretending to be hardware; it is hardware tactility translated into glass, void, and one accent. Every panel inherits the same recipe: deep glass body, 1px hairline edge, restrained inset shadow, optionally a single amber sign-of-life element. The interface does not perform; it sits.

The system explicitly rejects the AI-tool defaults — no neon glow on black, no glassmorphism stack of floating cards, no gradient-text headlines, no hero metric layouts, no chatbot bubble UI. It also rejects the "music app" reflex: no gradient waveform hero, no album-art bloom, no Spotify-green CTAs. The reference is Pioneer hardware, not Spotify and not OpenAI.

Density is calm. The wizard is single-column at 560px wide. The session deck reads as one CDJ unit, not a grid of widgets. Whitespace is generous; rhythm comes from vertical spacing, not from card decoration.

**Key Characteristics:**
- Deep void backgrounds with restrained "night-rave" ambient washes (5% alpha magenta/cyan/pink/purple/teal)
- Glass surfaces are dark and opaque (0.62–0.88 alpha) — sealing, not floating
- One amber accent per panel, max — the deck-light, never decoration
- Hairline 1px borders, faint inset bezels
- Saira variable display + JetBrains Mono numerics
- Restrained motion: 22-second border sweep, 1.4-second LED pulse, no spring or elastic
- Film grain overlay (overlay-blended, ~2% opacity) gives every surface a physical feel

## 2. Colors

The palette is a void stack carrying one amber. Everything else is silk text at varying alpha, status LEDs at component-local scope, and atmospheric rave washes that only ever appear on the body background.

### Primary

- **Amber Deck-Light** (`#ff8a3d`): the only accent in the system. Used as the focus ring, the active step indicator, the breathing border sweep on the session deck, the [Restart] button on the crash banner, the citation chip on cohost reactions. The "deck-light" name carries the rule: this is what a single LED on a CDJ-3000 front face looks like. Never used as a fill on large surfaces.
- **Amber Deep** (`#ff5a1a`): the bottom stop on amber gradients (button bottom edge, meter clip-zone, crash banner accent). Never used standalone.
- **Amber Pale** (`#ffb88a`): the top highlight stop on amber gradients and the citation-chip foreground text. The "warm hairline" tone.

### Neutral

- **Void** (`#000000`): the literal floor. The body background sits on it; vignette gradients fade to it at the edges.
- **Void-1 → Void-4** (`#020205` → `#11141c`): the cool-blue-undertone black ramp. Used for component-internal backgrounds (display windows, recessed mood-track strips, deck face).
- **Glass-1 / Glass-2 / Glass-3** (rgba 0.78 / 0.62 / 0.88): the three glass surface intensities. Glass-1 is the primary panel body, Glass-2 is secondary tiles, Glass-3 is recessed display windows (the BPM readout, the mood track).
- **Glass-Edge / Glass-Edge-Up / Glass-Top** (white at 6.5% / 11% / 5.5%): the hairlines and top-of-bezel highlights. Never used as fills.
- **Silk** (`#d6cfc7`): the warm-cream text color. Used at full opacity for primary readout, at 65% for body copy, 40% for secondary, 22% for tertiary, 12% for hairline labels.

### Atmospheric (body background only — never on chrome)

- **Rave Magenta** (`rgba(192, 56, 224, 0.055)`) — upper-left wash
- **Rave Pink** (`rgba(255, 92, 188, 0.038)`) — lower-center wash
- **Rave Cyan** (`rgba(72, 152, 255, 0.042)`) — lower-right wash
- **Rave Purple** (`rgba(118, 56, 224, 0.030)`) — upper-right corner
- **Rave Teal** (`rgba(64, 220, 200, 0.022)`) — lower-left corner

The atmospherics are subliminal. If you can name the color when looking at the screen, it is too strong.

### Status LEDs (component-scope only)

- **LED OK** (`#6dd44a`): "audio is flowing" / "ready" / "armed" indicators
- **LED Warn** (`#f4c542`): "calibrating" / "checking" intermediate states
- **LED Fault** (`#d4413a`): crash banner border, REC pill, hard-fail dots

### Named Rules

**The One Amber Rule.** A single panel may carry one breathing amber element. Two panels breathing amber in the same view is forbidden. The 2026-05-14 critique caught three concurrent sweeps in v4 and the v5 cut restricted `.border-anim` to the session deck only. Wizard tiles and cohost panels read amber via citation chips and focus rings only.

**The Hex-Outside-Tokens Ban.** Components MUST NOT declare hex colors. Every component reads `var(--token)` exclusively. Only `tokens.css` is allowed to contain `#xxxxxx`. Enforced by `frontend-enforcement` skill; new components that ship hex literals will be rejected at review.

**The Atmospherics-on-Body-Only Rule.** The five rave washes are body background-only. They never appear on chrome (titlebar, status bar, panels, tiles, buttons). If you find yourself reaching for `--rave-*` inside a component, you are wrong.

## 3. Typography

**Display Font:** Saira (variable axes: `wdth` 75–125, `wght` 300–800), with `system-ui, sans-serif` fallback. Vendored locally as a single WOFF2 — no Google Fonts remote `@import`. SHA-256 attested in `tauri/ui/LICENSE-3RD-PARTY.md`.

**Body Font:** Saira at the default 100 width / 400 weight axis values.

**Label/Mono Font:** JetBrains Mono (Regular 400 / Medium 500 / SemiBold 600), vendored locally. Used for numerics (BPM, timestamps, clock, meter scale), uppercase labels, and any text where the row-of-numbers needs to align.

**Character:** Saira at condensed width (`wdth: 85`) + 0.06em tracking carries the "industrial spec sheet" feel — Pioneer manuals, Roland labels, Behringer datasheets. JetBrains Mono for numerics carries the "live readout" feel — DAW BPM indicators, meter LCDs. The pairing reads as professional equipment, never as developer-tool monospace nostalgia.

### Hierarchy

- **Display** (Saira `wdth: 85`, weight 700, 18px, line 1.0, tracking 0.06em, uppercase): wordmark in the titlebar. Single use. The only place the brand name appears as type.
- **Headline** (Saira weight 600, 14px, line 1.2, tracking 0.04em): tile section titles, banner headings.
- **Title** (Saira weight 500, 13px, line 1.3, tracking 0.02em): card titles, step names, primary button labels.
- **Body** (Saira weight 400, 14px, line 1.45): cohost transcript, prose copy, help text. Maximum line length 65–75ch (enforced visually by the 560px primary column).
- **Label** (Saira weight 600, 11px, line 1.1, tracking 0.22em, uppercase): button labels, system status, REC pill, crash banner heading, navigation indicators. The tracking is heavy on purpose — this is the "instrument panel" voice.
- **Mono** (JetBrains Mono 400, 11px, line 1.3, tracking 0.08em): clock, timestamps, BPM, RMS, controller deck indicators, file paths, log lines.

### Named Rules

**The Condensed-Width Rule.** Uppercase labels in the system are set at `wdth: 85` (Saira's compressed axis). This is the "label-engraved-on-the-deck-face" feel. Default `wdth: 100` is reserved for body copy.

**The Tracking-by-Case Rule.** Uppercase always carries ≥0.06em letter-spacing; the heaviest cases (button labels, status pills) go to 0.22em. Lowercase carries 0em. There is no in-between — sentence case at +0.04em looks AI-generated by default.

## 4. Elevation

The system is flat by default. Depth is conveyed through **inset bezels** (1px white-top + 1px black-bottom inside the border) and **hairline borders** (1px glass-edge), not through drop shadows. The reference is hardware faceplate machining — light catches the top edge, shadow falls on the bottom edge, the surface itself is matte.

Drop shadows appear only in two places:
1. **`.vmx-tile[data-tile="hero"]`** — the primary panel of any view carries a single `0 16px 36px rgba(0,0,0,0.5)` ambient drop. This is "the deck is sitting on a desk."
2. **The amber glow ring** (`--glow-soft`, `--glow-strong`) — appears on focused inputs, the [Restart] crash button, and the `.vmx-tile[data-tile="alert"]` state. This is "the indicator is lit."

There is no card stack, no z-index ladder of floating elements, no shadow-on-hover lift. Surfaces sit; they do not float.

### Shadow Vocabulary

- **Inset bezel** (`inset 0 1px 0 var(--glass-top), inset 0 -1px 0 rgba(0, 0, 0, 0.45)`): the every-tile baseline. Both edges 1px, white-top at 5.5%, black-bottom at 45%.
- **Hero drop** (`0 16px 36px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.018)`): single use per view, on the primary panel.
- **Glow Faint** (`0 0 5px var(--amber-22)`): hover/idle state on amber elements.
- **Glow Soft** (`0 0 6px var(--amber-40), 0 0 14px var(--amber-22)`): focus-visible ring and alert-tile outer halo.
- **Glow Strong** (`0 0 8px var(--amber-65), 0 0 18px var(--amber-22)`): reserved for the primary action button at hover/press.

### Named Rules

**The Flat-By-Default Rule.** Surfaces are flat at rest. Drop shadows appear only on the single hero panel per view and on amber state (focus, alert). The 2026-05-14 critique of v4 found tiles stacking 3 levels of shadow; the v5 cut collapsed that to one.

**The Inset-Bezel-Over-Shadow Rule.** If you want a surface to feel "tactile," reach for the inset bezel (white top + black bottom), not a `box-shadow` drop. Drops belong to the hero panel and to amber state. Everything else is bezel + hairline border.

## 5. Components

### Glass Tile (the universal surface)

The system has exactly one glass surface recipe, `.vmx-tile`, with three data-attribute density variants.

- **Shape:** 6px radius (`--rad-md`). 1px `glass-edge` border. Inset bezel always on.
- **Base** (`.vmx-tile`): `glass-2` background + `blur-glass-light` backdrop filter. Used for every tile in the wizard, every cohost reaction card, every settings row.
- **Hero** (`.vmx-tile[data-tile="hero"]`): adds the `0 16px 36px` drop and a `1px rgba(255,255,255,0.018)` outer ring. One per view.
- **Alert** (`.vmx-tile[data-tile="alert"]`): swaps the border for `amber-40`, adds `inset 0 0 14px amber-22` inner glow, and the `--glow-soft` outer halo. Used for the BlackHole-missing banner, permissions warnings, error states.

The 2026-05-14 distill collapsed four duplicate panel recipes (primary-panel, blackhole-banner, permissions-card, performance-group button) into this one utility. Components own only their internal CSS (header text, body padding, internal row layout) — the glass shell is utility-driven.

### Buttons

- **Shape:** 2px radius (`--rad-sm`) — buttons are sharper than tiles. Padding 9px × 24px.
- **Primary (Amber):** the [Restart] button on the crash banner is the canonical exemplar. Border `amber-40`. Linear-gradient background from `amber@9%` to `amber@2.5%`. Inset top white 6%, inset bottom amber-40, inset glow `amber-22`, outer ring `amber@14%`. Text `amber`, `text-shadow: 0 0 4px amber-65`. Label typography (Saira 600, 10px, tracking 0.22em, uppercase). Min-width 144px.
- **Hover:** border → `amber`, background gradient → 14% top / 4% bottom. No transform, no scale.
- **Secondary / Ghost:** silk-65 text on bare glass, no border. Tracking-0.04em. Reserved for "Cancel" / "Skip" / "Not now" copy.
- **Disabled:** `cursor: not-allowed`, opacity ~0.4. No fade-out gradient.

### Inputs

- **Style:** glass-3 background, 1px glass-edge border, 6px radius. 14px internal padding. Silk text, JBM mono for numeric inputs.
- **Focus:** 2px amber outline, 2px offset, `--glow-soft` shadow. Border stays glass-edge — the focus ring lives outside the input perimeter, not inside it.
- **Error:** border → `led-fault`, `inset 0 0 14px rgba(212, 65, 58, 0.22)`.
- **Disabled:** silk-22 text, glass-3 at 0.5× alpha, no cursor change.

### Navigation (Step Strip + Status Bar)

The wizard step strip and the bottom status bar both run at full width, full hairline border (top or bottom), `rgba(0,0,0,0.55)` background, `blur-glass-light` backdrop. They are not tiles — they are deck chrome, separated by the same 1px `glass-edge` as everywhere else.

- **Step strip:** 64px tall. Each step is a label (uppercase, tracking 0.22em). Active step carries amber underline 1px + amber text. Inactive: silk-40.
- **Status bar:** 40px tall. Mono numerics on the right (clock, version), silk-65 prose on the left (current device, current state).

### Titlebar

56px tall. macOS native traffic-light spacer at left (when `decorations: false`). Wordmark centered (Display type). Mono clock at right at silk-40. Drag region via `-webkit-app-region: drag` on the bar, `no-drag` on the traffic spacer. `rgba(0,0,0,0.55)` background + `blur-glass-light` + 1px `glass-edge` bottom.

### Signature: The Border Sweep

A conic-gradient amber ring traveling around the perimeter of the session deck panel, 22 seconds per revolution. Renders via `mask-composite: exclude` to clip into a 1px-thick stroke. **Restricted to the session deck only.** Wizard tiles, cohost panel, settings drawer, and the timecode hero previously carried duplicate sweeps; the 2026-05-14 + 2026-05-19 critiques each flagged the result as anxiety, not sign-of-life. There is no `.slow.rev` mascot variant — see the mascot section below.

The sweep is frozen entirely under `prefers-reduced-motion: reduce`. Opacity drops to 0.6 and the animation pauses. This is the canonical motion behavior.

### Signature: The Mascot Overlay

A 320×420 transparent always-on-top webview window hosting a Three.js WebGL scene. Single VTuber-style 3D character (placeholder "DJ bat") with mood-driven state machine. Sits in its own window, not embedded; Phase 13 collapsed the wizard's mascot-corner column when this surface moved out.

**The mascot window is fully transparent.** `body` is `transparent !important` and `.mascot-window` carries `background: transparent; border: none; box-shadow: none;`. No chrome, no rim-light, no second border-sweep. The 2026-05-15 direction (Kaan's "fully transparent" feedback) is the canonical contract: the WebGL canvas composites directly over the desktop, the character IS the surface. Class hooks for an earlier rim-light variant (`.border-anim.slow.rev`, `.mascot-window__top-label`, `.mascot-window__state-caption`) remain in markup as `display: none` so HMR + Vitest fixtures don't break, but they render nothing in production. The 2026-05-19 critique caught this as a contract drift; this entry resolves the drift in favor of the implementation.

## 6. Do's and Don'ts

### Do:

- **Do** reach for `.vmx-tile` first. The universal glass recipe lives there; components own only their internal layout.
- **Do** use `var(--token)` exclusively for color. Hex literals in component CSS are forbidden and enforced by review.
- **Do** carry one amber sign-of-life per panel — focus ring, citation chip, alert glow, or border sweep. Not more.
- **Do** set uppercase labels at Saira `wdth: 85`, weight 600, tracking 0.22em. That is the instrument-panel voice.
- **Do** use JetBrains Mono for every numeric (BPM, timestamp, clock, RMS, dB readout). The mono is the live-readout signal.
- **Do** freeze motion under `prefers-reduced-motion` — every animation in `tokens.css` honors it.
- **Do** render film grain overlay-blended at ~2% opacity. Every surface gets the physical-material feel.

### Don't:

- **Don't** ship gradient text. `background-clip: text` over a gradient is the AI-tool default tell. The 2026-05-14 critique never let one ship; do not be the run that lets one ship.
- **Don't** use glassmorphism as default — the glass surfaces here are darker and more opaque (0.62–0.88 alpha) than the floating-translucent-card SaaS reflex. If your glass looks like a blurred translucent card hovering, you have done it wrong.
- **Don't** stack drop shadows. The hero panel gets one `0 16px 36px` drop and nothing else gets a drop except amber state.
- **Don't** carry the rave atmospherics into chrome. They are body-background only. Tiles, buttons, banners never read `--rave-*`.
- **Don't** ship two breathing amber elements in the same view. One amber light per panel; the border sweep is restricted to the session deck.
- **Don't** ship a chatbot bubble UI for the cohost transcript. The cohost speaks; it does not chat. No message-input affordance, no send button, no "thinking..." dots.
- **Don't** ship hero metric layouts ("3,247 reactions delivered ↗ 12%"). The product is a co-host, not a dashboard. Numbers belong in the meter and the BPM readout only.
- **Don't** use side-stripe borders greater than 1px as a colored accent. Full hairline borders or nothing.
- **Don't** ship em dashes in copy. Use commas, colons, semicolons, periods, or parentheses. Also not `--`.
- **Don't** use lucide-icon-on-card patterns. The product is hardware-feel; icons here are deck-engraved (`⚠`, `▸`, `■`, `●`) or absent.
- **Don't** ride the spring/elastic motion default. Ease-out exponential only. No `cubic-bezier` overshoot, no bounce.
- **Don't** ship onboarding-tour overlays or welcome modals with cartoon graphics. The product opens, boots, and works.
