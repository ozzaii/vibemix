---
phase: 91
slug: controller-renderer-midi-mirror
status: draft
shadcn_initialized: false
preset: none
created: 2026-05-27
---

# Phase 91 — UI Design Contract

> Visual and interaction contract for the FIRST Learn-window surface: an inline-SVG render of the DJ's actual MIDI controller, mirroring its current physical position in real time. This is the moment the v9.0 milestone becomes ear-passable — plug FLX4, see the knob move on screen, no AI yet. Treat the rendered controller diagrams as first-class UI surfaces: depth, spacing, alignment, contrast all matter.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | **none** (no shadcn; vibemix ships its own v5 "CDJ Whisper" design language in `tauri/ui/src/tokens.css`) |
| Preset | not applicable |
| Component library | **none** (vanilla TS + DOM; no React/Vue). Frontend pattern is hand-authored modules under `tauri/ui/src/learn/` — mirrors `src/debrief/` precedent |
| Icon library | **none external**. All controller-faceplate iconography is hand-authored inline SVG at `tauri/ui/src/learn/controllers/<controller_id>.svg.ts` (Vite `?raw` import). NO Lucide / Heroicons / Tabler — adding them would break the retro-futurist hardware vocabulary from `.claude/skills/frontend-enforcement/SKILL.md` rule 7. |
| Font | **Saira** (display + body, variable axes `wdth` + `wght`) + **JetBrains Mono** (numerics + control labels). Already vendored as WOFF2 in `tauri/ui/public/fonts/`; CSS in `tokens.css` lines 38-71. |
| Window topology | New `WebviewWindow` label `learn`, direct mirror of `tauri/src-tauri/src/debrief_window.rs` → new `tauri/src-tauri/src/learn_window.rs`. Title `Learn — vibemix`. Default size **1280×720**, min **960×540** (identical to debrief, fits the SVG 1280×720 design grid 1:1). Resizable, decorations on. |
| Socket | ws://127.0.0.1:8765 — SAME socket as live co-host (Invariant #4 preserved). Learn webview opens its own ws client at the same port. |

---

## Spacing Scale

Declared values (all multiples of 4; map directly to existing `tokens.css` `--sp-*` scale — DO NOT introduce new spacing tokens):

| Token | Value | Usage in Learn window |
|-------|-------|-----------------------|
| `--sp-1` | 4px | Hairline gaps between adjacent controls in the SVG legend strip; ARIA-label inline padding |
| `--sp-2` | 8px | Compact gap inside the controller-name pill, between glyph and text |
| `--sp-3` | 12px | Gap between titlebar wordmark elements (clock, status chip) |
| `--sp-4` | 16px | Default gap between status-bar segments; padding inside the empty-state card |
| `--sp-5` | 24px | Side padding of the SVG stage (left/right gutter around the controller render); padding inside titlebar |
| `--sp-6` | 40px | Top breathing room above the controller name; bottom padding before status bar |
| `--sp-7` | 64px | Page-level outer gutter at ≥1280px width (the void around the schematic — the deck breathes) |
| `--sp-8` | 96px | Reserved (unused in P91; reserved for course-list scaffolding in P97) |

**SVG-internal spacing exception:** The controller SVGs are authored to a `viewBox="0 0 1280 720"` grid; geometry inside the `<g data-control-id>` groups uses SVG user-units (not CSS pixels). Internal control-to-control spacing follows the FACTUAL hardware geometry from the manufacturer PDFs (e.g. DDJ-FLX4 jog-wheel diameter is 153 mm on a 482 mm faceplate → ratio 0.317 — preserved in SVG user-units). This is intentional: the rendered schematic must read as the same physical layout the DJ's hands feel.

**Touch-target exception:** Hit-region `<g>` groups for the smallest controls (FX-on buttons, beat-fx selectors that are ~14 mm in reality) must have a transparent `<rect>` padding box bringing the click-target to ≥36×36 CSS pixels at the default 1280×720 window. This is a WCAG 2.5.5 compliance backstop and the keyboard-nav reach guarantee.

---

## Typography

The Learn window inherits the entire type stack from `tokens.css`. NO new font weights or sizes — re-use the v5 CDJ-Whisper vocabulary. 4 declared roles, 2 weight families (regular + semibold via Saira variable axes).

| Role | Family / variation | Size | Weight | Line height | Letter spacing | Usage |
|------|-------------------|------|--------|-------------|----------------|-------|
| Display (controller name) | Saira `wdth 85, wght 700`, UPPERCASE | **28px** | 700 | 1.0 | 0.06em | The detected controller's display name, rendered ONCE in the title slab above the SVG (e.g. `PIONEER DDJ-FLX4`). One hero glyph. |
| Body (annotations, empty-state body) | Saira `wdth 100, wght 400` | **16px** | 400 | 1.45 | 0 (default) | Empty-state explanatory copy, ARIA-only labels surfaced visually, "Cmd+Tab back to deck" hint. |
| Label (control labels in SVG, status-bar segments) | JetBrains Mono | **11px** | 500 | 1.0 | 0.18em UPPERCASE | Control-name labels overlaid on each `<g data-control-id>` (e.g. `EQ HI`, `TEMPO`, `JOG A`). Status-bar text. The numeric/mechanical "stamped on the panel" feel. |
| Numeric mono (latency probe readout) | JetBrains Mono | **11px** | 400 | 1.0 | 0.08em | Live `P95 latency: 38 ms` readout in the status bar (dev/debug surface; visible always in P91 because Kaan ear-pass needs it). |

**Forbidden font choices (frontend-enforcement skill rule 4):** Inter, Roboto, Arial, system-ui, Helvetica, default Tailwind sans. Adding any of these to a Learn surface fails the AI-slop gate.

**Variable-axis discipline:** All Saira uses are routed through `font-variation-settings: "wdth" N, "wght" M` — never `font-weight: bold` shorthand. This is enforced by `tauri/ui/tests/session.tokens.test.ts` precedent.

---

## Color

Per `.claude/skills/frontend-enforcement/SKILL.md` rule 2 (the 20/80 rule): the Learn window is ~80% dominant warm-black void + ~20% accent. Accent is reserved for a SHORT list of elements — NOT spread across every interactive surface.

| Role | Value (from `tokens.css`) | Usage in P91 Learn window |
|------|---------------------------|---------------------------|
| Dominant (60%) | `var(--void)` + `var(--void-1)` + `var(--void-2)` (the body background gradient: `radial-gradient(ellipse 92% 78% at 50% 42%, transparent 0%, rgba(0,0,0,0.55) 72%, rgba(0,0,0,0.92) 100%)` over `linear-gradient(180deg, #04050b 0%, #000 52%, #030206 100%)` — verbatim from `tokens.css` line 411-414, NO aurora washes) | Body background of the Learn window. Same cinematic void the session deck sits on — "one product" continuity. |
| Secondary (30%) | `var(--silk)` (`#d6cfc7`) at full opacity for primary copy; `var(--silk-65)` for secondary copy; `var(--silk-22)` for the rendered controller's "neutral inactive" stroke fill | All controller-schematic strokes, fills, control-name labels, body copy, titlebar wordmark. The SVG strokes are silk-22 by default (visible but not assertive) — the controller reads as a precision instrument in low light, not a marketing render. |
| Accent (10%) | `var(--amber)` (`#ff8a3d`) + `var(--amber-65)` + `var(--amber-22)` + `var(--glow-soft)` | **Reserved for EXACTLY these elements (no other use):** (1) the focus ring on keyboard-navigated `<g data-control-id>` hit regions; (2) the controller-name title slab (one amber wordmark under-stroke, breathing at `--motion-led-pulse` 1400ms); (3) the `--learn-highlight` CSS variable (P91 declares the variable + applies it to NO controls yet — P92 lights it on highlight). NOT used for normal control fills, NOT used for the latency-probe text, NOT used for the status-bar OK chip. |
| Destructive | `var(--led-fault)` (`#d4413a`) | Used in EXACTLY one place in P91: the "controller unplugged" toast/banner at the top of the Learn window when MIDI port disappears mid-session. Mirrors the existing `#crash-banner` border-color convention. NOT used for retry CTAs or any other interactive surface. |
| Status OK | `var(--led-ok)` (`#6dd44a`) | The "MIDI mirror live" status pip in the status bar — single 6px circle next to the latency readout. NOT used for any other purpose. |

**Reserved-for list (the explicit ten-fingers list):**

1. Keyboard focus ring (`*:focus-visible` inherits this from tokens.css)
2. Controller-name title under-stroke (the breathing amber light below the wordmark)
3. `--learn-highlight` CSS variable (declared in P91, not lit until P92)
4. "Controller unplugged" red banner border (destructive)
5. "MIDI mirror live" green status pip (OK)

That is the WHOLE list. Adding amber to a sixth element (e.g. the empty-state plug glyph) breaks the 20/80 rule — failing the frontend-enforcement check.

**Forbidden colors:**

- `#FF7F00` (Pioneer brand orange) — and any hue within 10° of it. The shipped `--amber` (`#ff8a3d`) is intentionally peach-tinted, NOT brand orange. Test gate: `tauri/ui/tests/learn/test_no_pioneer_orange.spec.ts` greps all `learn/**.svg.ts` files for hex literals; bare `#FF7F00`/`#ff7f00` / RGB equivalents fail red.
- Pioneer logo (any form). Same test grep for the string `Pioneer DJ` rendered as SVG path data.
- Any `fill="..."` or `stroke="..."` attribute inside controller SVGs other than `currentColor`, `none`, `var(--silk-22)`, `var(--silk)`, or `var(--learn-highlight)` — components MUST NOT hard-code hex (the `tokens.css` rule from line 30: only `tokens.css` contains `#xxxxxx`).

**Dual-channel cue baseline (RENDER-05 binding):** P91 lands the SCAFFOLDING for the dual-channel cue but does not paint it. Each `<g data-control-id>` group gets two empty `<g class="cue-color">` and `<g class="cue-shape">` child slots so the P92 highlight contract can light both channels in a single CSS-variable swap (color via `fill: var(--learn-highlight)`, shape via the `<g class="cue-shape">` slot rendering a 4px-stroke amber pulse-ring). The dual-channel a11y test in P91 is annotated `expect: stub-only` (per CONTEXT.md decisions block).

---

## Copywriting Contract

All copy in lowercase or sentence-case — NO marketing-voice exclamations, NO "great!" / "awesome!" / "let's go!" patterns (tutor-slop blocklist `scripts/launch/check_no_tutor_slop.py` enforces this in v9.0). The Learn window's P91 surface has minimal copy because there are no lessons yet — the controller IS the surface.

| Element | Copy | Source / notes |
|---------|------|----------------|
| Window title | `Learn — vibemix` | Mirror of `Debrief — <session>` pattern (debrief_window.rs:138). The em-dash separator is the established convention. |
| Hero title slab (controller name) | `<DETECTED CONTROLLER DISPLAY NAME>` — e.g. `PIONEER DDJ-FLX4` / `HERCULES INPULSE 300` / `NUMARK PARTY MIX LIVE` | Pulled VERBATIM from `display_name` field in `src/vibemix/midi/profiles/<id>.json`. UPPERCASE rendered via CSS `text-transform: uppercase` (the JSON field stays normal-case). |
| Generic-fallback hero title | `UNKNOWN CONTROLLER` | When `find_mapping(port_name)` returns None and fingerprint confidence is low. Renders the `_generic.svg.ts` labeled-zone layout. |
| Empty-state heading (no MIDI port detected at all) | `no controller detected` | Verbatim adoption of the wizard's existing `controller-probe.ts:271` copy ("no controller detected. plug one in or skip.") — one-product consistency. lowercase, period-terminated. |
| Empty-state body | `plug one in to begin.` | Continuation of the lowercase sentence above. NO icon-button to "skip" in P91 (P97 adds the mode-picker bypass). One terse line; the empty-state visual is dominant. |
| Status-bar segment 1 (controller status) | `<controller display name> · midi mirror live` (when active) OR `waiting for midi` (when no port) OR `controller unplugged` (when port disappeared mid-session) | The mirror status is the single source-of-truth signal Kaan needs during ear-pass. |
| Status-bar segment 2 (dev-visible latency probe in P91) | `P95: <NN> ms` | JetBrains Mono numerics. Updates once per second from a rolling 240-sample window. P91 ships this visible by default; P92+ can hide behind a debug flag if Kaan wants. |
| Status-bar segment 3 (window-management hint, low-ink) | `cmd+tab to deck` | macOS phrasing; Windows build will render `alt+tab to deck`. Reaches the user that this is a sibling window, not the only window. |
| Toast: controller unplugged mid-session | `<controller name> disconnected.` (in `--led-fault` border, `var(--silk)` body, 4s auto-dismiss; the mirror snaps back to neutral inactive strokes) | Mirrors the existing `#crash-banner` visual treatment but auto-dismissable (this isn't a crash). |
| Primary CTA | **(none in P91)** — there is no button to press. Plugging in the controller IS the CTA. P92 introduces the first interactive lesson; P91 is purely an observation surface. | If a CTA is later requested, the verb would be `start a lesson` (one verb + one noun, lowercase) — but this is OUT OF SCOPE for P91. |
| Destructive confirmation | **(none in P91)** | No destructive actions exist in the Learn window before P92's lesson-progress reset. |
| Error state: SVG file missing for detected controller (should never happen — CI parity gate catches this) | `mirror unavailable for <controller name>. report this at github.com/bravoh-music/vibemix/issues.` | One actionable next step (file an issue). NO "please contact support." NO "something went wrong." NO retry button (there's nothing to retry — the SVG ships in the bundle). |

**Copywriting forbidden list (extends the v9.0 tutor-slop blocklist):**

- No exclamation marks anywhere in P91 surfaces.
- No "great!" / "awesome!" / "let's go!" / "ready?" / "let's dive in" — none appear because no AI tutor is wired in P91.
- No "please" / "kindly" / "thank you for" — the surface trusts the DJ already knows what they're doing.
- No "loading…" with three dots — the SVG is inline + Vite `?raw` so it renders synchronously after detection.
- No "we" / "our" / "us" — vibemix doesn't speak in first person on this surface; copy is observational.

---

## Component Inventory (P91-specific, executor-facing)

| Component | File | Purpose | Visual contract |
|-----------|------|---------|-----------------|
| `LearnWindow` (root) | `tauri/ui/src/learn/learn-window.ts` (NEW) | Window-root; subscribes ws:8765 for `ipc.learn.controller_detected` + `ipc.learn.midi_position`; orchestrates SVG mount + control-value updates. | Grid: `var(--titlebar-h) 1fr var(--statusbar-h)`. NO sidebar. NO panels. ONE stage. |
| `LearnTitlebar` | inline in `learn-window.ts` or `learn/components/titlebar.ts` | Mirror of session/debrief titlebar shape; left = `LEARN` wordmark (Saira `wdth 85, wght 700`, 18px, silk + 12px amber text-shadow); center = controller display name (silk-65, JetBrains Mono 11px, letter-spacing 0.18em UPPERCASE); right = clock (JetBrains Mono 11px silk-40). | Background: same titlebar recipe as `wizard-app .titlebar` (linear-gradient void-glass + blur + glass-edge bottom border + inset top-sheen). 56px tall. |
| `ControllerStage` | `tauri/ui/src/learn/components/controller-stage.ts` (NEW) | The 1fr middle region. Hosts the inline-SVG render of the detected controller. Single child — the SVG. | Padding: `var(--sp-7)` top, `var(--sp-7)` left/right at ≥1280px (collapses to `var(--sp-5)` below 960px). Background: TRANSPARENT (the body void shows through; the controller floats on the void, NOT inside a card or panel). |
| `ControllerSchematic` (`.svg.ts` × 11) | `tauri/ui/src/learn/controllers/<id>.svg.ts` for each of: `pioneer_ddj_flx4`, `pioneer_ddj_flx6`, `pioneer_ddj_flx10`, `pioneer_ddj_400`, `pioneer_ddj_1000`, `pioneer_ddj_sx3`, `pioneer_xdj_rx3`, `numark_party_mix_live`, `hercules_inpulse_300`, `hercules_inpulse_500`, `_generic` | The factual geometry of one controller, authored from official hardware PDF. `<svg viewBox="0 0 1280 720" role="img" aria-label="<display name> schematic">…</svg>`. | Stroke `var(--silk-22)` default, stroke-width `1.5` for knob bodies + button outlines, `1` for hairline detail. Fill `none` for outlines, `var(--void-3)` for recessed wells, `var(--silk-12)` for raised button caps. NO gradients with stops below `var(--silk-12)` (would disappear into void). NO `<g>` group rendered without an explicit `data-control-id` matching the profile JSON — bidirectional parity gate. |
| `EmptyState` | `tauri/ui/src/learn/components/empty-state.ts` (NEW) | Shown when `mido.get_input_names()` returns no candidate controllers. | Centered single column: a faint 64×64 "plug" glyph (silk-22, currentColor) from `tauri/ui/src/wizard/icons/speaker.svg.ts` pattern; below it the 28px display heading `no controller detected`, below that the 16px body `plug one in to begin.`. No CTA button. NO illustration filling. The void DOMINATES — the empty state is the absence of the artifact, not a content surface. |
| `StatusBar` | `tauri/ui/src/learn/components/status-bar.ts` (NEW) | 40px-tall bottom rail. | Three segments separated by silk-22 hairline `|` dividers: (1) controller display name + mirror status; (2) latency probe `P95: NN ms` with a 6px `var(--led-ok)` pip when ≤50 ms / `var(--led-warn)` pip 50-80 ms / `var(--led-fault)` pip >80 ms (the red-guardrail visual signal that fires `§LEARN-LATENCY-CONTINGENCY`); (3) `cmd+tab to deck` hint. |
| `UnpluggedToast` | inline in `learn-window.ts` | One-off toast when `controller_detected.connected === false` (port disappeared) | Floats at top: `<controller name> disconnected.` in silk + `--led-fault` 1px border. `--blur-glass-light` backdrop. 4s auto-dismiss. NO close button. |

**P91 components that are NOT built (defer markers):**

- `HighlightOverlay` — defers to P92 (`ipc.learn.highlight` envelope + the actual paint).
- `LessonHud` — defers to P92.
- `TutorSpeakBubble` — defers to P92 / P94.
- `LessonProgressDots` — defers to P97.
- `ModePicker` — defers to P97.

---

## Motion + Interaction (P91-specific)

| Motion element | Token / value | Trigger | Purpose |
|----------------|---------------|---------|---------|
| Controller schematic mount | None (synchronous render after detection) | Inline-SVG Vite `?raw` import; first paint within 2s of plug-in per RENDER-01. | The SVG appears decisively, not faded in. No `opacity: 0 → 1` fade. The contract is "see your hardware on screen." |
| Control-value mirror | `transform`-only updates on knobs (rotational), `fill: var(--silk-22) → var(--silk)` on button presses, `transform: translateY(<percent>)` on faders. NO repaint of the SVG path. | `ipc.learn.midi_position` at 30 Hz (≈33 ms cadence). | Composited transform = 60 fps guaranteed (frontend-enforcement skill rule 6 compliance: motion is intentional). |
| Controller-name under-stroke breathing | `--motion-led-pulse` 1400ms (existing token) `ease-in-out` infinite. Amber color modulates between `var(--amber-22)` and `var(--amber-65)`. | Always on while a controller is connected. NOT shown in empty-state. | The "sign-of-life" pulse — mirrors the session deck's idle breathing in mascot-window. Tells the user the mirror is alive even if they're not currently touching the controller. |
| Focus ring (keyboard nav) | `outline: 2px solid var(--amber)` + `--glow-soft` (existing global focus token) | `<g data-control-id>` group receives Tab focus | A11y baseline. Inherited from `tokens.css *:focus-visible`. |
| Unplugged toast slide-in | Translate `Y(-8px) → Y(0)` over `var(--motion-snap)` 150ms, opacity 0 → 1. Auto-dismiss reverses. | `controller_detected` envelope with `connected: false`. | Same shape as `#crash-banner` enter animation. |
| Status-bar latency pip color cross-fade | 200ms ease-out background-color transition. | Latency probe rolling window crosses a threshold (50 ms / 80 ms). | Prevents flicker on edge-of-bucket measurements. |

**Forbidden motion:**

- NO `border-anim` (the 22s amber border sweep) on the Learn window — it is RESERVED for the session deck per `tokens.css` line 437-444. Adding it here duplicates the "one breathing light" rule.
- NO `vmx-glass-streak` (the diagonal sheen) on the Learn window — the schematic is the surface; no decorative texture overlay.
- NO mascot rendering inside the Learn window — the mascot is a separate overlay window per Phase 13. Learn is a quiet observational surface.
- NO confetti / celebration animations on first mirror — there are no goals to celebrate in P91. P92's lesson-advance is where motion-rewards live.

---

## Accessibility Contract (RENDER-03 + RENDER-05 binding)

| Surface | Requirement | Test gate |
|---------|-------------|-----------|
| Every `<g data-control-id>` inside every controller SVG | `role="button"` + `aria-label="<human-readable control name>, deck <A\|B>"`. Examples: `aria-label="EQ-HI knob, deck A"`, `aria-label="crossfader"`, `aria-label="play button, deck B"`. The aria-label is derived from the profile JSON via a hand-authored `tauri/ui/src/learn/controllers/_aria-labels.ts` lookup keyed on `field` + `deck`. | `tauri/ui/tests/learn/test_aria_labels_present.spec.ts` — every `<g data-control-id>` in every SVG asserts both attributes. |
| Keyboard navigation | `Tab` cycles between `<g data-control-id>` groups in DOM order (which follows the canonical control-block reading order: deck A controls → mixer → deck B controls). `Shift+Tab` reverses. `Enter` / `Space` on a focused group fires no action in P91 (no lessons), but the focus ring appears. | `tauri/ui/tests/learn/test_keyboard_nav_order.spec.ts` — playwright walks Tab order and asserts canonical sequence per controller. |
| Dual-channel cue scaffolding | Each `<g data-control-id>` has TWO empty child slots `<g class="cue-color"></g>` + `<g class="cue-shape"></g>` ready to receive P92's highlight payload. The slots are present in P91 but render nothing. | `tauri/ui/tests/learn/test_dual_cue_slots_present.spec.ts` (annotated `expect: stub-only` per CONTEXT.md decisions). |
| Color contrast | Silk (`#d6cfc7`) on void (`#020205`) = WCAG AAA at 16px+. Amber (`#ff8a3d`) on void = AAA at 18px+. Latency-probe JetBrains Mono 11px silk-40 on void = AA Large only — acceptable for a dev-visible debug surface, but if Kaan elevates this to a user-facing surface later, bump to silk-65. | `tauri/ui/tests/learn/test_contrast_ratios.spec.ts` — axe-core run on the Learn window. |
| Reduced motion | `prefers-reduced-motion: reduce` freezes the controller-name under-stroke breathing (`--motion-border-sweep: 0s` in the existing media query). The 30 Hz MIDI mirror updates STAY ON — they are functional, not decorative. The unplugged-toast slide-in is replaced by an instant opacity swap. | Inherits from `tokens.css` @media block lines 357-368. |
| Screen-reader announcement on controller detection | On first `controller_detected` envelope with `connected: true`, emit a polite `aria-live="polite"` announcement: `<display name> connected.`. On disconnect: `controller disconnected.`. NOTHING ELSE is announced — the SVG itself is `role="img"` with the display name as `aria-label`. | `tauri/ui/tests/learn/test_sr_announcement.spec.ts` |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none (project uses no shadcn) | not applicable |
| Third-party shadcn registries | none | not applicable |

The Learn window adds ZERO new JS dependencies (per v9.0 anti-creep acid test §12). The renderer uses inline SVG strings via Vite `?raw` — a built-in Vite feature, not a registry block. No `npm install` runs in P91.

---

## Asset Pipeline (controller SVGs — the load-bearing P91 deliverable)

The 11 SVG files are the PRIMARY visual artifact of P91. They must satisfy:

1. **Source provenance:** Hand-authored from manufacturer official hardware-diagram PDFs (Pioneer DJ "Operating Instructions" appendix diagrams, Hercules DJControl manuals, Numark spec sheets). NOT traced from marketing photos. NOT lifted from Mixxx (GPL-2.0 incompatible with Apache 2.0). Source PDFs MUST be cited in a comment header at the top of each `.svg.ts` file with the publisher + document title + retrieval date.
2. **No Pioneer logo.** No "Pioneer DJ" wordmark anywhere in the SVG. The controller's product name appears ONLY in the title slab outside the SVG, sourced from the profile JSON `display_name`.
3. **No Pioneer brand-orange.** No `#FF7F00` and no hue within 10° of it. The shipped `--amber` (`#ff8a3d`) IS the only orange in the design system and only renders via the reserved-for list.
4. **No photo-lift faceplates.** No `<image href="...">` raster references. Pure vector geometry.
5. **viewBox-normalized:** All 11 SVGs use `viewBox="0 0 1280 720"`. Internal geometry preserves the physical aspect ratio of the controller (e.g. DDJ-FLX4's 482×265 mm faceplate fits the 16:9 viewport with letterbox margins; the SVG geometry uses the same proportions, with margins drawn as transparent space).
6. **`<g data-control-id>` for every interactive control.** Bidirectional parity gate: every control listed in `controls` + `buttons` in the profile JSON has a matching `<g>`; every `<g>` has a profile binding. Enforced by `tauri/ui/tests/learn/test_svg_profile_parity.spec.ts` across all 11 files.
7. **`currentColor` everywhere.** No hex literals inside SVG strings. Default stroke is `currentColor`, which inherits from the parent CSS `color: var(--silk-22)` on `.learn-controller-schematic`. The P92 highlight pattern flips `color: var(--learn-highlight)` on highlighted `<g>` groups, which propagates to all `currentColor` strokes/fills inside that group.
8. **Generic fallback (`_generic.svg.ts`):** Labeled-zone layout — three large flat rectangles for "DECK A", "MIXER", "DECK B" with silk-22 dashed borders + JetBrains Mono labels. Does NOT pretend to be a specific controller. The empty-state visual that says "we don't recognize this — here's where the controls usually are."
9. **License header in every `.svg.ts` file:** Apache-2.0 SPDX header at the top, identical to the rest of the codebase. The generated SVG string is the project's authored derivative work; it does NOT contain copyrighted manufacturer art.

**Test gate file references:**

- `tauri/ui/tests/learn/test_svg_profile_parity.spec.ts` — RENDER-06 binding (bidirectional parity)
- `tauri/ui/tests/learn/test_no_pioneer_orange.spec.ts` — RENDER-08 anticipation (greps for `#ff7f00` and neighbors)
- `tauri/ui/tests/learn/test_svg_currentcolor_only.spec.ts` — frontend-enforcement compliance (no hex inside SVGs)
- `tauri/ui/tests/learn/test_svg_aria_complete.spec.ts` — RENDER-03 binding
- `tauri/ui/tests/learn/highlight-latency.test.ts` — RENDER-02 binding (50 ms target, 80 ms red guardrail)

---

## Open Decisions Flagged for Retrospective Ratification (autonomous-mode best-judgment calls)

Per "fully-autonomous" mode + the note that Kaan ratifies grey-area calls retrospectively, the following were decided without blocking:

| # | Decision | Rationale | Ratify by |
|---|----------|-----------|-----------|
| 1 | **Latency probe `P95: NN ms` visible by default in the status bar.** | Kaan's ear-pass workflow is "plug controller → see knob move → verify it's responsive." Surfacing the rolling-window P95 measurement live makes the artifact self-verifying without devtools. Trivial to hide behind `data-debug="on"` in P92 if Kaan wants. | P91 ear-pass session |
| 2 | **Hero title slab `28px` UPPERCASE Saira `wdth 85, wght 700`** for controller name. | Continuity with the session deck's persona-readout type vocabulary (`wdth 85, wght 600/700` is the established display register). 28px is the largest non-display size in the v5 type ramp; the controller IS the hero. | P91 ear-pass session |
| 3 | **No "skip" button in the empty state** (the wizard has one; the Learn window does not). | P91 has no lessons to skip into. P97's mode-picker is where "leave Learn" happens. Adding a skip button now would imply a forward path that doesn't exist yet. | P97 mode-picker plan |
| 4 | **Reserved-for list HARD-CAPS amber at 5 elements** for P91. | Frontend-enforcement skill rule 2 (20/80) + the explicit anti-pattern "accents everywhere = AI slop." This list will grow in P92 (highlight glow becomes element #6) and P94 (tutor-speak bubble accent becomes #7). | Phase 92 UI-SPEC |
| 5 | **Status-bar latency pip color: green ≤50ms / amber 50-80ms / red >80ms.** | Pip thresholds mirror the RENDER-02 CI gates exactly. Red triggers `§LEARN-LATENCY-CONTINGENCY` automatically — the pip is the user-visible early-warning system. | P91 ear-pass session |
| 6 | **Touch-target ≥36×36 CSS pixels** (WCAG 2.5.5 minimum, not 44px Apple HIG). | The schematic is primarily a VISUAL mirror, not a primary input surface. The keyboard-nav reach is the real interactivity contract. 36px is sufficient for occasional mouse-fall-back tabbing. If Kaan wants 44px later, bump in P92. | P92 lesson runtime plan |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
