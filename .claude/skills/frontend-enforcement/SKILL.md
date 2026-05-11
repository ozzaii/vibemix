---
name: frontend-enforcement
description: Project-local enforcement of vibemix frontend design standards. Loaded automatically by GSD agents that touch frontend code or UI design — frontend-design discipline, 20/80 rule, textured material feel, no AI slop.
---

# vibemix — Frontend Enforcement

**Loaded automatically by:** ui-researcher, ui-checker, ui-auditor, executor, planner, pattern-mapper, code-reviewer, code-fixer, roadmapper, phase-researcher.

## Hard rules (no exceptions)

1. **Invoke `/frontend-design:frontend-design`** before doing any frontend work — UI design contracts, HTML/CSS/JS, React/Vue, design audits. If you don't have that skill available, follow its principles from this file.
2. **20/80 rule must hold.** ~80% of the visual surface is the dominant tone (background, panels, ink). ~20% is the single chosen accent (LEDs, highlights, active states). Do NOT spread accent color across every element — that's AI slop. Test: can you scan the surface and see exactly where the eye is being guided? If accents are everywhere, you broke the rule.
3. **Heavy textured material feel.** Surfaces must look like *things*, not flat rectangles. Brushed-aluminum gradients, anodised panel depth, film grain, scanline overlays, knurled edges, inset shadows for recess, raised bevels for hardware. Solid #1a1a1a fills are forbidden — always layered with material treatment.
4. **No generic AI aesthetics.** No Inter, Roboto, Arial, system-ui, default Tailwind purple gradients on white, lazy "card with rounded-2xl shadow-lg p-6". Every typography choice must be deliberate. Every shadow must serve a material purpose.
5. **Distinctive typography pairing.** Display font (with character — DSEG7, Major Mono Display, IBM Plex Mono, Bowlby One, etc.) + body font deliberately chosen to pair with it. Document the why in code comments.
6. **Motion is intentional.** Animations exist for material/atmospheric reasons (pulsing LED, beat-synced wobble, segmented meter ballistics, slow CRT flicker), not decoration. One well-orchestrated reveal beats fifteen scattered hover micro-effects.
7. **The vibemix product aesthetic is retro-futurist hardware** — Pioneer/Roland/MPC industrial design language. Knurled-knob shadows, segment-LED numerals, glowing LED accents, dark anodised metal surfaces, faint scanlines, mechanical UI affordances. Phosphor amber (#ff8a1a-ish) is the accent. Off-near-black anodised charcoal (#14171c-ish) is the dominant.

## Review-time checklist

Use this for code-reviewer / ui-checker / ui-auditor passes:

- [ ] No Inter, Roboto, Arial, system-ui, or default platform fonts
- [ ] No purple-on-white gradients, no generic blue CTAs
- [ ] 20/80 rule honoured — single dominant tone + minority accent
- [ ] Surfaces are materially textured (gradients, grain, bevels), not flat fills
- [ ] Typography pairing has intentional contrast (display ↔ body)
- [ ] Animations are atmospheric/material, not decorative chaos
- [ ] Retro-futurist hardware vocabulary present where vibemix UI is involved (LEDs, segment numerals, panel framing, etc.)

## Why this exists

PROJECT.md core value: *"never sounding like AI slop"*. The UI is half of that promise. Generic Tailwind defaults break the brand promise on contact.
