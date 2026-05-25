# vibemix Frontend Critique + Sexification Plan

**Date:** 2026-05-25 · **Method:** impeccable `critique` (PRODUCT register) + CDJ-Whisper brand law (frontend-enforcement) · every uplift checked vs `design-slop-gate.spec.ts`.

## Headline verdict
The anti-slop promise is **already largely kept**: zero banned-font violations, 20/80 amber discipline enforced (often over-enforced), real hardware vocabulary (segment-LED ladders, peak-hold lozenges, knurled inset shadows). The slop test fails in vibemix's favor — no AI tool produces this.
**The risk is not slop, it's blandness from over-restraint.** Repeated critique passes stripped amber + motion until some surfaces (settings, debrief, library rails) read flat. "Sexification" = **richer material depth + sharper hierarchy + one more beat of intentional motion**, NOT more color.
Note: the design-slop gate only checks FONTS (banned-font list + brand-font-lead + @font-face lock). It does NOT check hex literals, 20/80, or motion — so all uplifts below are gate-safe as long as no `font-family` leads with a non-brand font.

## Per-surface scores (Nielsen + CDJ fidelity /5)
- **Pill** — best surface. CDJ fidelity 4.5/5. Only softness: the transition *into life* is a plain opacity blink + max-height tween.
- **Vibe Engine / Library** — center deck + scope strong; left console + curate mode weak. 3.5/5. Hex-literal drift (`rgba(255,138,61,…)` inline vs its own "all colors are tokens" header). Curate had no loading state + leaked stale rationale (NOW FIXED — P0-a landed).
- **Mascot overlay** — N/A (intentionally chromeless; sexification belongs in the Three.js character, not CSS).
- **Wizard** — step0 hero is a real brand moment; interior steps don't carry that energy. 4/5.
- **Settings** — blandest surface; critiqued *down* to a competent dark settings panel. 3/5. Blanket `--glow-faint` on every control breaks 20/80.
- **Debrief** — consistent but emotionally flat for a peak-end + conversion surface. Emotional resonance 2.5/5. Timeline doesn't read as a master waveform.
- **Shared (tokens.css)** — strongest file in the repo. 5/5. The one systemic drift: inline amber `rgba()` literals app-wide despite tokens.css owning the "only-this-file-has-hex" rule.

## Prioritized uplift backlog (visual-impact-per-effort)

### P0 — surface-correctness (DONE)
- **P0-a · Curate loading skeleton + rationale reset** — ✅ LANDED (skeleton rows + "building…" note + clearRationale on error/mode-switch).

### P1 — high impact, on-brand, parallel-safe (disjoint file sets → 4 parallel agents)
- **P1-a · Debrief:** timeline-as-master-waveform (LED-comb texture + region glow + playhead) + power-down staggered arrival + one amber verdict line. `debrief.css`, `src/debrief/*`. Biggest emotional-impact-per-effort.
- **P1-b · Settings:** recess control groups (inset shadow into the drawer face) + two-stage slide-then-seat motion + demote blanket glow, reserve brighter glow for the *active* control. `src/settings/*`.
- **P1-c · Pill:** beat-synced dot pulse (drive `animation-duration` from `--bpm-period-ms`) + expand reveal amber top-seam wipe + peek depth cue. `src/pill/pill.css`. (NB: overlaps the Liquid-Glass pilot — coordinate.)
- **P1-d · Library:** light-direction the 3 panels (warm pool behind center results, vignette the rails) + tokenize the inline amber/blue literals + scope phosphor afterglow. `library.css`, `src/library/scope.ts`.

### P2 — refinement
- **P2-a · Wizard:** animated step-connector fill (progress travels) + amber index glyph per step header + interior-step settle. `src/wizard/*`.
- **P2-b · Shared token sweep:** add low-alpha amber tokens (`--amber-09/04/014`) + `--rave-blue`, replace inline rgba literals app-wide, optionally CI-lock a zero-rgba-literal contract. Touches every file → run LAST/in isolation (conflicts with all P1).

## Cross-cutting guardrails for implementers
- No new `font-family` leading with a non-brand font (the only thing the slop gate enforces).
- 20/80 is the real risk, not fonts: every amber addition (seam-wipe, region glow, verdict line) must stay the *single* accent on its surface.
- Every motion addition must be `prefers-reduced-motion` gated.
- Keep color in tokens; don't add inline `rgba()` (P2-b removes them, don't multiply).

**Bottom line:** vibemix is not slop and won't read as slop. The work is converting hard-won restraint into intentional richness on the 4 surfaces (debrief, settings, library rails, pill-transitions) where stripping left flatness — without smearing amber. The pill + tokens.css are the north star; pull the others up to them.
