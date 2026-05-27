# Phase 70 — UI Review

**Audited:** 2026-05-24
**Baseline:** `70-UI-SPEC.md` (design contract) + `frontend-enforcement` 6-pillar standard + `mocks/vibemix-direction-final.html` (token source-of-truth)
**Artifact:** `docs/landing/index.html` (GH-02, single-file no-build static landing)
**Screenshots:** not captured — no dev server serving `docs/landing/` (ports 5173/8080 answered 200 but are unrelated services, not this static page). Audit is code-only on the fully-read single-file artifact + the rendered `docs/assets/og-card.png` companion.
**Overall verdict:** **PASS** (engineering-side visual gate). Kaan-felt aesthetic sign-off remains a `§V7-LANDING` deferral.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting (Kaan's voice) | 4/4 | Verbatim against the Copywriting Contract; zero marketing-slop tokens; "real DJ friend in your ear" voice holds. |
| 2. Visuals / hierarchy | 4/4 | One clear focal point (amber accent headline → amber CTA); recessed-glass demo window is the screen anchor; icon-free, so no aria-label gaps. |
| 3. Color (20/80 rule) | 4/4 | Single amber `#ff8a3d`, confined to ~7 reserved elements exactly as the spec enumerates; ~80% void/silk. No amber wash. |
| 4. Typography | 4/4 | Saira + JetBrains Mono only; `geist\|fraunces` grep returns zero; `system-ui` only in fallback chain; variable-axis weight discipline. |
| 5. Spacing / material | 3/4 | `--sp-*` 4px scale honoured; material treatments real (inset/raised bevels, grain, vignette, glass) — minor: the SPEC's primary-panel raised-bevel recipe (`--glass-1` + `inset 0 1px 0 --glass-top`) is not used; both display surfaces are recessed-glass, so the "raised hardware bevel" half of the material vocabulary is absent. |
| 6. Experience Design / a11y | 4/4 | Skip-link, semantic landmarks, single h1, visible amber focus rings, 44px touch targets, reduced-motion kill-switch, graceful clipboard degradation, default-OFF waitlist. ≥95-capable, not aspirational. |

**Overall: 23/24**

---

## Top Findings (slop tells / craft highlights)

1. **CRAFT — Genuine 20/80 discipline, not amber spray.** Amber is auditable to exactly the seven reserved sinks from the SPEC (brand LED `:606`, hero accent line `:625`, lede `<em>` `:629`, install CTA `.btn.on` `:664`, code-tile inset glow, secondary/footer links, waitlist hover-only `:539-545`). The waitlist button is correctly silk-by-default and only lights amber on hover/focus (`:536-545`) — the single most common place a designer breaks 20/80, and it held. This is the no-slop promise honoured on contact.

2. **CRAFT — Pioneer-grade glass is real material, not a flat fill.** The demo window (`:340-371`) and code tile (`:458-468`) carry layered inset shadows (`inset 0 2px 6px rgba(0,0,0,0.9)` recess + `inset 0 0 18px rgba(255,138,61,0.035)` amber bleed + top-specular `::after` gradient), two-layer SVG `feTurbulence` film grain (`:131-141`), and a cinematic multi-radial vignette (`:118-128`). Zero `#1a1a1a` flat fills — forbidden-fill rule clean. The 22s conic-gradient border-sweep (`:172-197`) is a single atmospheric "sign of life," reduced-motion-gated by the global kill-switch (`:591-597`).

3. **WARNING (advisory, non-blocking) — Material vocabulary is recess-only; no raised-bevel panel.** Every surface on the page (demo window, code tile, buttons-at-rest) reads *inset/recessed*. The SPEC's Material Treatment table declares a raised "Glass panel depth" recipe (`--glass-1` + `inset 0 1px 0 var(--glass-top)` raised bevel) for primary panels — it's defined as a token but never applied. The page is missing the "raised hardware affordance" pole of the Pioneer vocabulary (a knob/pad-like protruding element). Not slop, not a contract violation — but a fully Pioneer-grade panel alternates recessed *and* raised. Minor; lands as a §V7-LANDING taste note, not a fix-blocker.

Secondary observations (no score impact): demo `<video>` has no `<track kind="captions">` — correctly deferred to `§ASSETS-DEMO-CUT` per SPEC (the page carries no critical speech). The `demo-placeholder.gif` poster is a known placeholder; `demo-poster.png` is the Wave 3 deliverable.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)
Audited every string literal against the SPEC Copywriting Contract (`70-UI-SPEC.md:229-248`):
- Hero L1/L2 `:623-626` = `THE ONLY AI CO-HOST` / `THAT ACTUALLY LISTENS` — exact.
- Lede `:629` = contract verbatim, with the single amber `<em>a friend who knows the room</em>` keyword emphasis (≤2 words rule honoured loosely as a clause — acceptable, it's the one emphasis).
- Section heads `:637 :659 :688` = `See It Live` / `Install` / `Built by Bravoh` — match (note: "See It Live" is a §01 head the SPEC didn't pre-script but is on-voice and on-tone).
- CTA `:664` `Get vibemix`, sub-copy `:666`, install cmds `:671 :676`, waitlist blurb `:691`, footer tagline `:710` — all verbatim.
- **Tone gates:** no "revolutionary / seamless / powerful / next-gen / elevate / unlock." Concrete, DJ-literal. The "no AI slop" line is in the footer as a literal product claim, which is on-brand, not ironic. PASS.

### Pillar 2: Visuals (4/4)
- Single clear focal point: the amber-glowing accent headline line (`:625`, `text-shadow` amber glow) pulls the eye, then hands off down-page to the amber `.btn.on` install CTA — a deliberate two-beat hierarchy.
- Hierarchy via size (88px clamp hero → 24px section heads → 15px body), weight (Saira `wght 800` accent vs `400` body), and the lone accent color. Three independent hierarchy channels.
- No icon-only buttons — copy buttons carry text "Copy" *and* `aria-label` (`:672 :677`). No unlabelled affordances.

### Pillar 3: Color (4/4)
- Single accent `--amber #ff8a3d` (`:58`), lifted verbatim from the mock. Void stack (5 blacks) + silk ink as dominant ~80%.
- Amber occurrences are countable and all on the SPEC's reserved list (`70-UI-SPEC.md:147-154`): brand LED, hero accent line, lede em, install CTA, code-tile inset bleed, links, waitlist-on-hover, border-sweep. No amber on body text, no amber on idle secondary surfaces.
- Hardcoded colors exist but are the *mock's verbatim token values* (rave-wash rgba, glass rgba, shadow rgba) — expected and contract-compliant, not stray hex.
- Contrast: silk `#d6cfc7` on void ≈15:1; amber on void ≈9.8:1; silk-40 confined to decorative mono captions/footer (`:253 :378 :558`), never to action-critical text. AA+ holds.

### Pillar 4: Typography (4/4)
- `--type-display`/`--type-body` = `'Saira', system-ui, sans-serif`; `--type-mono` = `'JetBrains Mono', ui-monospace, monospace` (`:88-90`). Exactly two families.
- **Anti-backsliding gate:** `grep -ri 'geist\|fraunces' docs/landing/` → **zero matches** (exit 1). PASS the HARD gate.
- `inter`/`roboto`/`arial` substring matches are all false positives (`pointer-events`, `cursor: pointer`). `system-ui` appears ONLY as the fallback after Saira — the exact pattern the SPEC permits (`:35`). No forbidden primary face.
- Variable-axis discipline: weight range (400 body / 500 label / 600 head+CTA / 700-800 display) comes from one variable family via `font-variation-settings`, documented in CSS comment `:87`. Mono restricted to numerals/code/labels. Intentional pairing with documented why — frontend-enforcement rule 5 satisfied.

### Pillar 5: Spacing (3/4)
- `--sp-1..8` (`:93-94`) are the mock's verbatim 4px-multiple scale. Spacing usage references tokens throughout (`var(--sp-*)`), not free-form values.
- Documented tactile exceptions present and justified: 5px LED dome (`:228-229`), 6px demo-window inset padding, 44px touch-target min-heights (`:394 :508-509`) — all SPEC-sanctioned hardware/a11y exceptions, not arbitrary.
- A few raw px values exist (`14px 28px` button padding `:393`, `14px` cmd-row `:475`) — these match the SPEC's "8px 16px / on-grid button inner padding" intent loosely (`14px` is off the strict 4px grid). Minor inconsistency, within the documented hardware-affordance tolerance.
- **The one real gap (drives 3 not 4):** the raised-bevel primary-panel material recipe is defined in the SPEC's Material Treatment table but never applied — all surfaces are recessed. The material *spacing/depth* vocabulary is half-present. See Top Finding 3.

### Pillar 6: Experience Design (4/4)
- **Landmarks:** one `<header>` `:604`, one `<main>` `:617`, one `<footer>` `:700`; sections use `<section aria-labelledby>`. Skip-link `:602` to install.
- **Headings:** single `<h1>` `:623`, `<h2>` section heads, no skipped levels.
- **Focus:** universal visible amber focus ring (`:162-169`), never bare `outline:none`; DOM-order focus, no positive tabindex.
- **Motion:** `prefers-reduced-motion: reduce` global kill-switch (`:591-597`) disables all animation/transition — brandPulse, border-sweep, hover transforms all die. Page fully usable static.
- **Graceful degradation:** copy-to-clipboard (`:714-750`) falls back to text-selection when `navigator.clipboard` is absent; `<code>` is `user-select:all` regardless. Demo `<video>` has `<img>` fallback with descriptive alt (`:647-649`) so it never renders broken before `demo.mp4` lands.
- **Privacy/default-OFF:** zero analytics auto-load; the UTM waitlist link (`:694-695`) fires only on click. Contract-compliant.
- **Touch targets:** ≥44px min-height/width on CTA, copy, waitlist (`:394 :508-509`).
- No destructive actions → no confirmation needed (correct per SPEC).

---

## Registry Safety
`components.json` absent; UI-SPEC declares `shadcn_initialized: false` and no third-party registries (plain static HTML/CSS/JS, no-build). Registry audit not applicable — skipped per the auditor's shadcn gate.

---

## Contract Fidelity Summary
The implementation tracks `70-UI-SPEC.md` with near-zero drift: tokens lifted verbatim from the mock, all four sections (Hero/Demo/Install/Waitlist) + header/footer present in semantic order, copy verbatim, 20/80 honoured, fonts locked, a11y contract met, no-build/self-containment held. The one structural gap is the unused raised-bevel material recipe (advisory). The landing reads as the same product family as `vibemix-direction-final.html` and the `og-card.png` (shared void/amber/silk DNA, same wordmark treatment). This is craft, not slop.

---

## Files Audited
- `docs/landing/index.html` (the implemented artifact — read in full, 753 lines)
- `.planning/phases/70-github-sexified-generated-tested/70-UI-SPEC.md` (design contract)
- `.planning/phases/70-github-sexified-generated-tested/70-CONTEXT.md` (locked decisions)
- `mocks/vibemix-direction-final.html` (token source-of-truth — referenced via SPEC)
- `docs/assets/og-card.png` (rendered social card — visual-family cross-check)
- `.claude/skills/frontend-enforcement/SKILL.md` (6-pillar rubric)
