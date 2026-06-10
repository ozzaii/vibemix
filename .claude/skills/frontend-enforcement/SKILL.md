---
name: frontend-enforcement
description: Project-local enforcement of vibemix frontend design standards. Loaded automatically by agents that touch frontend code or UI design — Forged Obsidian Chrome (tozpembe) discipline, 20/80 rule, One-Rose, gold quarantine, no AI slop.
---

# vibemix — Frontend Enforcement

**Loaded automatically by:** ui-researcher, ui-checker, ui-auditor, executor, planner, pattern-mapper, code-reviewer, code-fixer, roadmapper, phase-researcher.

**Authority chain (highest first):** `mocks/vibemix-bravoh-grade-pink.html` (the visual contract) → root `DESIGN.md` (the token + rule source, kept current) → this file (the enforcement summary). If this file ever disagrees with DESIGN.md, DESIGN.md wins — update this file in the same commit.

## The system in one line

**Forged Obsidian Chrome (tozpembe):** a warm, rose-shifted near-black slab of machined obsidian — mostly void, ONE soft-rose sign-of-life per panel catching a hairline lip, gold held in reserve for heat. It sits; it does not perform.

> This supersedes the v5 "CDJ Whisper" amber system (cold blue-black + phosphor amber `#ff8a1a`). If you find amber-accent or charcoal-`#14171c` guidance anywhere, it is stale — the v5 token names survive only as deprecated aliases resolving to the tozpembe palette.

## Hard rules (no exceptions)

1. **Tokens only.** Components MUST NOT declare hex colors; they read `var(--token)` exclusively. Only `tokens.css` carries `#xxxxxx`. Prefer canonical names (`--void-N`, `--ink-N`, `--brand*`, `--gold*`, `--surface-*`, `--text-*`, `--border-*`); never reintroduce hard v5 hexes. Enforced by `tests/design-slop-gate.spec.ts`. (Gotcha: the legacy-token gate matches token names inside CSS comments too — don't name banned tokens in comments.)
2. **20/80 rule must hold.** Warm void + glass + ink own ~80% of any view. Soft-rose (`--brand` #FFA5DF) is the rare deck-light, spent through the alpha ladder (`--brand-04` … `--brand-65`), almost always as a low-alpha wash — never a fill on a large surface. If accents are everywhere, you broke the rule.
3. **One-Rose.** A panel carries exactly ONE breathing sign-of-life: the focus ring, citation chip, border sweep, tail cursor, or LED. Two things breathing in the same panel is forbidden. While live the deck tail cursor is the screen's single breath.
4. **Gold is quarantined.** `--gold` (#e8c47a) appears ONLY on Camelot/key/heat/energy-delta numerics. Never an ambient field, never a panel accent, never paired with rose as a two-accent scheme. Reaching for gold outside a heat/key numeric means you are wrong.
5. **Tactility = inset bezel, not faux-3D.** Depth comes from the `--chrome-highlight` 0.5px warm-rose top lip, `--shadow-inset`, and hairline warm-white borders. Flat by default; drop shadows only in the four governed places (hero tile, rose state glow, shell recess gradient, grounding-drawer slide-over). No raised bevels, no brushed-metal gradients, no shadow-on-hover lift, no card stacks.
6. **Typography is locked.** Saira (variable, condensed `wdth: 85` for labels) + JetBrains Mono (every numeric) + Instrument Serif→Georgia (the co-host hero line ONLY — the one serif, the one large type). Every `font-family` leads with a brand face or `var(--type-*)`; `system-ui`/`Georgia` only as trailing fallback. Uppercase tracks ≥0.06em (labels 0.22em); lowercase tracks 0. Gate-enforced font allow-list.
7. **Motion is sign-of-life, not flashlight.** Restrained eased breathing: 22s border sweep, 1.4s LED pulse, ease-out exponential. No spring, no elastic, no square strobe, no marketing choreography. `prefers-reduced-motion` freezes the sweep. Never animate layout properties.
8. **The co-host speaks first-person, grounded.** UI copy is the co-host talking: short, specific, evidence-tied ("I learn your crate by ear"). Not a chatbot (no bubbles, no send-button chrome), not a tagline, not marketing reassurance. **No em dashes in copy** (also not `--`) — enforced by `tests/copy-contract.spec.ts` (also bans vendor jargon, port numbers, cache paths, "vibemix-core" in shipped strings).
9. **Idle ≠ fault (cardinal invariant #5).** At idle, disconnected/ungrounded is EXPECTED state, never an error paint. Honest instruments only: never paint un-probed state green, never let a fault wear idle copy, never fake provenance.
10. **No generic AI aesthetics.** No Inter/Roboto/Arial-as-brand, no gradient text, no glassmorphism-as-default (tozpembe glass is dark and sealing, 0.62–0.88 alpha), no hero-metric layouts, no identical card grids, no lucide-icon-on-card, no chatbot chrome, no music-app cliché (gradient waveform hero, album-art bloom, Spotify-green CTAs). Rose must never drift toward cute-pink SaaS; gold must never drift toward navy-and-gold dashboard.

## Review-time checklist

Use this for code-reviewer / ui-checker / ui-auditor passes:

- [ ] Zero hex literals outside `tokens.css`; canonical token names in new code
- [ ] 20/80 honoured — warm void dominant, rose as the rare low-alpha wash
- [ ] Exactly one breathing element per panel (One-Rose)
- [ ] Gold only on Camelot/heat/energy numerics
- [ ] Depth via inset bezel + hairline, not drop-shadow stacks or faux-3D
- [ ] `font-family` leads with Saira / JetBrains Mono / `var(--type-*)`; serif only on the hero line
- [ ] Uppercase labels at 0.22em tracking; numerics in JBM
- [ ] Motion eased + restrained; reduced-motion respected; no layout-property animation
- [ ] Copy is first-person co-host voice; no em dashes; copy-contract gate green
- [ ] Idle states honest (idle ≠ fault); no instrument paints un-probed state
- [ ] Focus ring (2px rose + 2px offset) visible on every interactive control

## Why this exists

PROJECT.md core value: *"never sounding like AI slop"*. The UI is half of that promise. Generic defaults break the brand promise on contact — and a stale enforcement file pointing at the retired amber system polishes the wrong contract.
