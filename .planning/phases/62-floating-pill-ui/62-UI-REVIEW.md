# Phase 62 — UI Review

**Audited:** 2026-05-22
**Baseline:** `62-UI-SPEC.md` (approved design contract; ui-checker VERIFIED 6/6)
**Screenshots:** not captured — no vibemix dev server running (port 8080 is an unrelated SearXNG instance; 3000/5173/1420 closed). Static code-only audit, as scoped by the orchestrator. The rendered look on the built `.dmg` is a known KAAN-ACTION live item (tauri#13415 transparency parity), out of this pass's reach.
**Stance:** ADVISORY / non-blocking (`gsd-autonomous fully`). Recommendations are flagged, nothing blocks.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | Silkscreen vocabulary, verbatim reaction text, honest `decks · unknown`, silence-as-empty-state — textbook anti-slop |
| 2. Visuals | 3/4 | 20/80 holds and hierarchy is clear, but the spec-mandated 200ms expand *reveal* is an un-animatable `display` snap |
| 3. Color | 4/4 | Token-only, zero hex/rgba literals, amber confined to exactly the 4 reserved accents |
| 4. Typography | 4/4 | Exactly 3 sizes (9/10/13px) + 2 weights (400/500), Saira + JetBrains Mono only — matches the contract verbatim |
| 5. Spacing | 3/4 | `--sp-*` discipline in the pill chrome, but deck-chips + waveform ship off-grid raw px (6px, 2px, 20px, 140px) |
| 6. Experience Design | 3/4 | All 4 states + real waveform + honest fallbacks + XSS-safe, but no `prefers-reduced-motion` guard on the infinite blink, no `aria-live`, and the expand transition does not actually animate |

**Overall: 21/24**

---

## Top 3 Priority Fixes

1. **Expand reveal does not animate — it is an instant `display: none → flex` snap (WARNING).** `pill.css:144,150` toggle `display` on `.pill__expand`; `display` is not a transitionable property, so the spec's "Expand: 200ms `--motion-transition` ease-out (height + opacity); ONE orchestrated reveal" (62-UI-SPEC §States) does not happen. The comment at `pill.css:141` *claims* it "uses `--motion-transition`" but no `transition` rule exists on the element. **Fix:** drive the reveal with animatable properties — keep the element in the layout and tween `max-height` (0 → cap) + `opacity` (0 → 1) under `transition: max-height var(--motion-transition) ease-out, opacity var(--motion-transition) ease-out`, gated by the `data-state="expand"` selector, instead of flipping `display`.

2. **Off-grid raw pixels break the 4-multiple `--sp-*` scale in deck-chips + waveform (WARNING).** `deck-chips.ts:58` `gap: 6px`, `:65` `height: 20px`, `:66` `padding: 0 8px`; `waveform.ts:36` `gap: 2px`, `:39` `max-width: 140px`, `:44` `min-width: 2px`. `6px` and `140px` are not on the declared scale (`--sp-1..5` = 4/8/12/16/24); `20px` and `8px` happen to be 4-multiples but are still hardcoded, not tokenised. The UI-SPEC §Spacing pins the chip inner gap to `--sp-1` (4px). **Fix:** replace `gap: 6px` with `var(--sp-1)` or `var(--sp-2)`, route chip height/padding through tokens, and treat the 2px LED-comb gap as a documented hardware-render exception (mirror how meter.ts justifies its sub-grid bar spacing) rather than a silent literal.

3. **Infinite blink/pulse has no `prefers-reduced-motion` guard (WARNING — a11y).** `pill.css:107,110` run `pill-blink` `infinite` for the listening (1.4s) and speaking (0.9s) dots; `waveform.ts` bars also transition continuously. `tokens.css` only freezes `--motion-border-sweep` and `.border-anim` under `@media (prefers-reduced-motion: reduce)` — it does NOT touch the pill's own keyframe. An always-on-top, always-visible pulsing dot in a user's peripheral vision is exactly the motion-sensitivity case the media query exists for. **Fix:** add a `@media (prefers-reduced-motion: reduce)` block in `pill.css` that sets `animation: none` (or a non-pulsing static-amber dot) on `.pill__dot` and pauses the waveform transitions.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

Best-in-class for this project's anti-slop bar. Evidence:

- **Silkscreen state vocabulary** — `state-machine.ts` `STATE_LABEL` + `pill.css:121-129` render `IDLE` / `LISTENING` / `SPEAKING` only, 9px / 0.22em-tracking / uppercase. No marketing voice (62-UI-SPEC §Copywriting honoured).
- **Silence IS the empty state** — `state-machine.ts:111-115` `baseState()` maps unknown/absent → `idle`; the idle pill shows only the dim dot + `IDLE`, with no "waiting for your set…" filler. Matches the spec's "silence is the honest empty state" exactly.
- **Verbatim reaction, no pill-side framing** — `index.ts:206` sets `view.reaction.textContent = state.reactionText` with no "AI:" prefix; `state-machine.ts:163` carries `frame.text ?? ""`. Spec-compliant.
- **Honest deck fallback** — `deck-chips.ts:131,135,150,152,188` render `unknown` (never a fabricated key) and a single `decks · unknown` chip when nothing resolves. Carries the Phase 59 honest-null contract to the surface.
- **No error banner by design** — `index.ts:351` `bus.addStatusListener(() => {})`; a bus-unreachable condition stays in `idle` (no toast over the DJ's deck). Matches §Copywriting Error state.
- The only grep hits for generic labels (`OK`) were in a test fixture string (`index.test.ts:72`), not shipped copy.

No deduction — the copy contract is met or exceeded on every line item.

### Pillar 2: Visuals (3/4)

- **Hierarchy is clear** — collapsed strip leads the eye dot → label → waveform (`pill.css:86-137`); the expand panel layers reaction body (13px silk) over mono chips (10px), a deliberate display↔data contrast.
- **20/80 surface** — dominant tone is `var(--glass-3)` dark glass on the pill body (`pill.css:45`); amber is a minority accent. The eye lands on exactly the amber dot / waveform / chips — the 20/80 scan test passes.
- **BLOCKER-adjacent WARNING:** the expand reveal does not animate (see Top Fix 1). The spec calls the reveal the pill's signature single orchestrated motion (frontend-enforcement rule 6); shipping it as an instant `display` snap is the most visible divergence from the contract and the reason this pillar is 3, not 4.
- **No expand height cap** — `62-UI-SPEC §Pill Dimensions` specifies "auto height (cap ~220px)"; `pill.css` declares no `max-height` on `.pill__expand`. The `-webkit-line-clamp: 3` on the reaction (`pill.css:160`) bounds the text block, and the window height is Rust-controlled, so this is low-risk — but the CSS cap the spec named is absent. Flag, not block.
- Material feel is appropriately restrained for a compact floating surface: hairline `--glass-edge` border + top inner-light seam + bottom void inset (`pill.css:48-52`) is the "sealed glass" read the spec asked for, without faux-3D bevels.

### Pillar 3: Color (4/4)

- **Zero color literals in shipped CSS/TS.** The grep for `#[0-9a-fA-F]{3,8}` / `rgb(` / `rgba(` returned matches ONLY inside explanatory comments (`pill.css:8`, `pill.html:26,28` documenting the `--glass-3` value). All declared colors read `var(--token)`. The deliberate `#`-less issue-ref convention (`tauri issue 13415`) keeps the no-hex grep gate clean — a thoughtful touch (62-05-SUMMARY decision).
- **Amber confined to exactly the 4 reserved accents** (62-UI-SPEC §Color list): state dot (`pill.css:104`), waveform lit-bar fill (`waveform.ts:61,64`), citation chips (inherited `--c-citation-chip-*`), and the resolved deck-key glyph (`deck-chips.ts:89`). The amber grep across `src/pill/` + `pill.css` shows 5 usages, all on these reserved elements. Amber does NOT touch the border, drag handle, reaction text, or background — the 20/80 rule is intact.
- The low-confidence deck key correctly DROPS amber authority to `--silk-40` (`deck-chips.ts:97-99,149,164`, WR-04) — a subtle anti-slop call (a barely-sure key must not read with registry-hit authority).

### Pillar 4: Typography (4/4)

- **Exactly 3 sizes:** 9px (state label, `pill.css:124`), 10px (chips, `deck-chips.ts:73`), 13px (reaction body, `pill.css:154`) — verbatim to the §Typography table.
- **Exactly 2 weights:** wght 500 (label, `pill.css:123`) and wght 400 (reaction, `pill.css:153`); deck chips use JetBrains Mono medium. No 600/700 on the pill, matching the spec's "bold display weight belongs to the full session hero, not the compact floating surface."
- **Token fonts only** — `var(--type-display)` (Saira) and `var(--type-mono)` (JetBrains Mono); the "banned font" grep produced only false positives on `interface`/`setInterval`/`pointer-events` substrings. No Inter/Roboto/Arial/system-ui.
- Line heights correct: body 1.5 (`pill.css:155`), labels/chips 1.0 (`pill.css:128`).

### Pillar 5: Spacing (3/4)

- **Chrome layout is token-clean** — `pill.css` uses `--sp-1/2/3/4/5` (gap, padding, section separation); the `--sp-6/7/8` grep returned NONE, correctly honouring "larger tokens are NOT used — the pill is a compact surface."
- **Drag-handle 28px + collapsed 44px** hit-area exceptions are documented and intentional (62-UI-SPEC §Spacing Exceptions); `pill.css:67-68` `flex: 0 0 28px` matches.
- **WARNING — off-grid raw pixels** (see Top Fix 2): `deck-chips.ts:58 gap: 6px` is off the 4-multiple scale entirely; `:65 height: 20px`, `:66 padding: 0 8px`, `waveform.ts:36 gap: 2px`, `:39 max-width: 140px`, `:44 min-width: 2px` are hardcoded literals rather than `--sp-*` tokens. The `2px` LED-comb gap is a defensible hardware-render value (matches the session meter language), but it should be a *documented* exception, not a silent literal — and `6px`/`140px` have no scale justification. This is the spacing pillar's only real gap; the chrome itself is exemplary.

### Pillar 6: Experience Design (3/4)

State coverage is strong:

- **All 4 states implemented + wired to real wire data** — `state-machine.ts` `baseState`/`applyFrame`/`tickCollapse` map `cohost_status` → idle/listening/speaking and `cohost-reaction` → expand; `pill.css:102-150` styles each. State-machine tests run **18/18 green** (verified live this audit).
- **Real signal, not fake animation** — the waveform is driven by `meters.voice.rms` floored to `WAVE_BASELINE_RMS` (`index.ts:46,375`), reusing meter.ts's `data-lit` zero-DOM-churn update path. The spec's "real TTS waveform, not a fake loop" is met.
- **Honest degradation everywhere** — empty `deck_state` → `decks · unknown`; bus-unreachable → silent idle; null camelot → dim `unknown`. No false-confident states.
- **XSS-safe trust boundary** — reaction via `textContent` (`index.ts:206`), chips filtered through `isCitationChip` shape guard (`index.ts:118-126`), deck text via `textContent`/`createTextNode` (`deck-chips.ts:156,169,173`). T-62-11/15/16 mitigated. No registry/shadcn surface (components.json absent — registry audit N/A).
- **Data-driven collapse, no timers** — the 6s expand→collapse is a `collapseAt` field ticked in the rAF loop (`state-machine.ts:194`, `index.ts:358`), keeping the machine pure/testable. Good engineering hygiene that also makes the state transitions deterministic.

Deductions (three WARNINGs, none blocking):

- **No `prefers-reduced-motion` guard on the pill's own infinite blink** (Top Fix 3) — the a11y gap. tokens.css freezes only the border-sweep, not `pill-blink`.
- **No `aria-live` / `role=status` on the state label** — `pill.html:78` `#pill-label` updates IDLE→LISTENING→SPEAKING with no live-region, and the dot/waveform are `aria-hidden`. A screen-reader user gets no announcement when the co-host starts/stops speaking. The deck chips DO carry `aria-label`s (`deck-chips.ts:176,189,211`), so the gap is specifically the dynamic status. Consider `aria-live="polite"` on `#pill-label`.
- **The expand reveal does not animate** (Top Fix 1) — counted primarily under Visuals; it also degrades the felt interaction quality (the panel pops rather than reveals), hence noted here too.

---

## Registry Safety

`components.json` absent — shadcn not initialized (confirmed). 62-UI-SPEC §Registry Safety declares no third-party registries (vanilla TS stack). **Registry audit: skipped entirely (N/A); 0 third-party blocks to vet.**

---

## Files Audited

- `tauri/ui/pill.html` — overlay webview entry + transparent-overlay invariant
- `tauri/ui/src/pill/pill.css` — pill chrome + explicit `--glass-3` rgba surface
- `tauri/ui/src/pill/index.ts` — boot, bus fan-out, drag, rAF loop, render
- `tauri/ui/src/pill/state-machine.ts` — pure 4-state machine
- `tauri/ui/src/pill/waveform.ts` — real-RMS TTS waveform
- `tauri/ui/src/pill/deck-chips.ts` — honest deck-context chips
- `tauri/ui/src/tokens.css` — design-token source of truth (read for token verification)
- `62-UI-SPEC.md`, `62-CONTEXT.md`, `62-01..05-SUMMARY.md` — audit baseline + build record
- Tests confirmed present + passing: `state-machine.test.ts` (18/18 verified), `index.test.ts`, `waveform.test.ts`, `deck-chips.test.ts`

**Not audited (out of static-code reach):** rendered transparency on the built `.dmg`, drag-on-unfocused-window feel, focus non-steal, multi-monitor clamp — all KAAN-ACTION live items recorded across the 62-0x SUMMARYs.
