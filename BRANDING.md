# vibemix Branding

> **Visual direction:** _CDJ Whisper._ Pioneer-grade DJ hardware in library mode — restrained, tactile, readable. The opposite of generic "AI assistant" branding.

The canonical visual reference is [`mocks/vibemix-direction-final.html`](mocks/vibemix-direction-final.html). When in doubt, open that file and match it.

---

## Why CDJ Whisper

vibemix's product thesis is "real DJ friend in your ear, no AI slop." The visual language has to carry the same weight: it has to feel like a piece of professional DJ gear, not a chatbot UI. That means:

- **Warm blacks, not pitch black.** Pitch black reads as a console terminal or a generic "dark mode" wrapper. Warm blacks read as anodized hardware in a dimmed booth.
- **Single accent color, four intensities.** No gradient sweeps. No multi-hue neon. The amber is the only color that earns its way onto the surface — and it earns it through restraint.
- **Tactility through faint glow, not faux 3D.** Drop shadows and bevels age badly. A 6% amber outer glow under a control reads as "this thing is active" without screaming.
- **Readability is non-negotiable.** A DJ glances at the surface mid-mix. If they have to squint, the design is broken.

---

## Palette

The full palette lives in `mocks/vibemix-direction-final.html`. Summary:

### Warm blacks (5 stops)

| Token | Hex | Use |
|-------|-----|-----|
| `--ink-0` | `#0B0A09` | Page background — the deepest stop |
| `--ink-1` | `#13110F` | Card / surface background |
| `--ink-2` | `#1A1815` | Elevated surface (hover state, dropdown) |
| `--ink-3` | `#26221E` | Border, divider |
| `--ink-4` | `#3A342D` | Disabled state, muted text |

### Amber accent (4 intensities)

| Token | Hex | Use |
|-------|-----|-----|
| `--amber-100` | `#FF8A3D` | Primary accent — wordmark, CTA, key glow |
| `--amber-80`  | `#E07332` | Hover / focused secondary |
| `--amber-40`  | `#A85522` | Subtle accent, inline link |
| `--amber-10`  | `#5C3014` | Tint, faint highlight |

### Neutral text

| Token | Hex | Use |
|-------|-----|-----|
| `--text-primary` | `#F0EBE4` | Body text on dark surface |
| `--text-muted`   | `#8A857E` | Caption, metadata, timestamp |

---

## Typography

| Family | Use |
|--------|-----|
| **Geist** (variable, weights 300-700) | All UI — buttons, body, navigation, metadata |
| **Fraunces** (variable, weights 400-700) | Display moments — hero headlines, mode names, mascot dialog labels |

Both are open-source (SIL OFL) and bundled with the app — no Google Fonts CDN call at runtime.

---

## Tactility principles

1. **Glow over bevel.** A 6-10% amber outer glow under an active control. Never a drop shadow with offset/blur trying to imitate a 3D button.
2. **Static surfaces, animated affordances.** The background never breathes or pulses. Animation is reserved for state transitions (control becoming active, mascot anticipation, beat highlight).
3. **Anchored alignment.** Everything snaps to an 8px grid. No floating elements. No off-grid micro-adjustments.
4. **Restraint over decoration.** If a panel doesn't have a functional purpose, it doesn't appear. Empty space is the default.

---

## What to avoid

Hard "no" list — these get rejected in PR review on sight:

- **Generic "AI assistant" gradients.** Cyan-to-magenta, purple-to-pink, any "Midjourney-defaults" gradient.
- **Neon cyan / electric magenta.** These signal "generic AI startup" and we are explicitly not that.
- **Glass-morphism / blur effects on backgrounds.** Reads as macOS 10.10 leftover. Solid surfaces only.
- **Faux 3D buttons.** Drop shadows trying to imitate physical depth. Glow only.
- **Multi-color palettes.** Anything beyond warm-black + amber + neutral text needs an explicit reason and a PR conversation.
- **Pure black backgrounds (`#000`).** Use `--ink-0` instead.
- **Stock icon sets.** Heroicons / FontAwesome / Material Icons are visible from orbit. Custom-traced icons or none at all.

---

## Logo

### Status: **placeholder**

The current logo at [`docs/branding/logo.svg`](docs/branding/logo.svg) is a placeholder text-based wordmark. A designer-finalized logo is a Kaan-action item post-v2.0 — tracked in [KAAN-ACTION.md](.planning/phases/26-readme-branding-day-zero-ops-viral-demo/KAAN-ACTION.md).

### Usage of the placeholder

- README hero (already in place via `docs/assets/hero.png`).
- App titlebar (Tauri window decoration).
- Open Graph image for shared links (TBD — see Phase 26 channel post drafts).

Do not use the placeholder logo for:

- Press kit (wait for the real logo).
- Merch / physical print (wait for the real logo).
- Vendor partner co-marketing (wait for the real logo).

---

## Cross-references

- Visual mock: [`mocks/vibemix-direction-final.html`](mocks/vibemix-direction-final.html)
- Logo SVG: [`docs/branding/logo.svg`](docs/branding/logo.svg)
- Memory: `project_visual_direction_cdj_whisper` (private user memory)
- License: Apache 2.0 — branding assets in `docs/branding/` and `docs/assets/` are released under the same license as the code unless marked otherwise.
