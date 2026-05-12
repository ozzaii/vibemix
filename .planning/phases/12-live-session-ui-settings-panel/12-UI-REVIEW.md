---
phase: 12
ui_review_depth: spec-only
auditor: autonomous-inline
reviewed_at: 2026-05-12
status: spec_approved_implementation_deferred
---

# Phase 12 — UI Review (Retroactive 6-Pillar Audit)

## Scope note

Phase 12 ran in autonomous-inline mode. Wave 1 shipped IPC schema only — **no UI code was written**. A retroactive visual audit therefore has no implementation to grade; this review audits the **UI-SPEC contract** that Waves 3-5 will execute against.

When Waves 3-5 ship, re-run `/gsd-ui-review 12` for a true 1-4 per-pillar grading of the rendered live session UI + Settings drawer.

## Inputs audited

- `12-UI-SPEC.md` — the executable design contract (821 lines)
- `12-CONTEXT.md` — locked decisions
- `mocks/vibemix-app-ui.html` — visual reference (unchanged from Phase 5 baseline)
- `tauri/ui/src/tokens.css` — token source-of-truth (unchanged from Phase 11)
- `12-01-PLAN.md` through `12-05-PLAN.md` — wave plans

## Pillar 1 — Copywriting

**Spec audit grade:** ✅ APPROVED (implementation grading deferred)

UI-SPEC §"Copywriting Contract" locks every visible string with the terse-DJ-friend tone:

- Voice rule: lowercase body / UPPERCASE labels (matches mock + HYPE_BEGINNER template). Negative-dictionary bans `Awesome`, `Welcome`, `Let me know`, `delve`, `leverage`, `as an AI`, `Continue your journey`, `Get started`. Tab-completion-of-AI-slop avoided.
- Every component string committed: titlebar (5 entries), persona panel (8), output panel (5), meters (3), timecode + phase tape (8), event ribbon (8 event-type formats), cohost panel (7), status bar (11), settings drawer (26), muted banner (2), universal microcopy (2). 85 strings total.
- Primary-CTA matrix per surface (live session / settings / status badge tooltip) — no destructive auto-actions. Single "Restart calibration" confirm-gate.

**Implementation grading deferred** until Wave 5 ships and a human can confirm the rendered strings match the spec word-for-word.

## Pillar 2 — Visuals (textured materials, atmospheric overlays)

**Spec audit grade:** ✅ APPROVED (implementation grading deferred)

UI-SPEC §"Backgrounds & Atmospheric Layers" carries forward every Phase 11 texture without diluting it:

- Body radial gradient + film grain SVG fractalNoise + scanlines `repeating-linear-gradient` — z-indexes locked at 9999 (grain) and 9998 (scanlines).
- Brushed-metal vertical streak `::before` on every panel column.
- Panel screws (4 corners of main shell) — `screw.svg.ts` shipped as inline TS module.
- Phase tape: paper-grain SVG fractalNoise overlay, perforated bottom edge radial dots, paper gradient `#f3ead7 → #ebe0c6`.
- Transcript: receipt-paper gradient, paper-grain overlay, torn-bottom illusion radial dots.
- Knurled-knob retention slider, segment LEDs, DSEG7 numerals — all hardware vocabulary intact.

NO flat fills declared. NO smooth-gradient cards. NO neumorphism. NO frosted glass.

## Pillar 3 — Color (20/80 rule, single accent, status as dots only)

**Spec audit grade:** ✅ APPROVED

- Single accent: phosphor amber (`--phosphor`), reserved-for list 19 items (Phase 12 expansion of Phase 11's list 8 items).
- Dominant: anodised charcoal family — `--bg`, `--panel`, `--panel-lift`, `--panel-deep`, `--groove`, 3 bezel rings, 2 brushed-metal tones, 4 ink shades.
- Paper family (phase tape + transcript only): 9 colours scoped locally — documented as the only non-charcoal/non-amber colours allowed. Justified by frontend-enforcement rule 4 ("textured materials") as analogue interludes.
- Status accents: `--rec`, `--ok`, `--cue` — LED dots + thin markers only, NEVER panel fills. `--cue` is reserved/unused in v1.
- 20/80 inventory: dominant + ink ≈ 80%, paper surfaces ≈ 8%, accent < 12%. Passes with margin.

No second semantic color (no "info blue", no "warning yellow") — single source of meaning.

## Pillar 4 — Typography (4 families, 2 weights max per face, intentional pairing)

**Spec audit grade:** ✅ APPROVED

- 4 families: Workbench (display) + DM Mono (body) + DSEG7 Classic (numerics) + Caveat (handwritten sticker).
- 11 type roles documented with size/weight/line-height/letter-spacing per role.
- Two-weight rule held: Workbench 400 only; DM Mono 400 (body) + 500 (selected/emphasised); DSEG7 400 only; Caveat 700 only.
- NO Inter / Roboto / Arial / system-ui / SF-Pro anywhere in the spec.
- Pairing rationale carried forward from Phase 11: Workbench LED-display + DM Mono industrial mono + DSEG7 instrument readouts + Caveat human breath.

## Pillar 5 — Spacing (8-point grid, exceptions documented)

**Spec audit grade:** ✅ APPROVED

- 8-point grid: 4 / 8 / 16 / 24 / 32 / 48 / 64 — all multiples of 4. Phase 11 tokens reused unchanged.
- Window: 1240 × 860 (multiples of 4). Min: 1100 × 720.
- Settings drawer: 400px (multiple of 4).
- Mascot reserved: 256 × 256 (multiple of 4).
- Column widths: 320 + 420 + 420 = 1160 + 2×24 gap = 1208; plus 16 padding ×2 = 1240. Adds up cleanly.

No exceptions declared. NO 7px / 15px / 33px values anywhere.

## Pillar 6 — Registry Safety (no third-party UI components)

**Spec audit grade:** ✅ APPROVED

- UI-SPEC §"Registry Safety": no shadcn (not initialised), no third-party UI registries, no React/Vue/Svelte.
- Pure-function `(state) => HTMLElement` pattern lifted from Phase 11 wizard — same `registerStyle()` singleton.
- Tauri plugins added (`tauri-plugin-global-shortcut`, `tauri-plugin-window-state`) are Rust crates, not UI components — outside the registry-safety surface.
- All component assets (SVG icons, fonts, paper-grain data-URI) vendored locally.

## Phase 11 → Phase 12 continuity check

- ✓ Tokens unchanged (no new `--*` additions in `tokens.css`).
- ✓ Wizard pattern (`registerStyle`, pure-function components) extended cleanly.
- ✓ Mascot reserved corner preserved at same coordinates (left column, 256×256).
- ✓ IPC namespace continues `ipc.*` on `127.0.0.1:8765` (no new transport).
- ✓ Status badge schema upgraded from Phase 11's 4-LED footer to Phase 12's full live bar — same `ipc.status.tick` payload.
- ✓ Cohost-header 42×42 mascot circle added — Phase 13 mount point.

## Frontend-enforcement compliance (the absolute checklist)

Per `.claude/skills/frontend-enforcement/SKILL.md`:

| Rule | Status |
|------|--------|
| No Inter / Roboto / Arial / system-ui / SF-Pro | ✓ |
| No purple-on-white gradients / generic blue CTAs | ✓ |
| 20/80 rule (single dominant + minority accent) | ✓ |
| Materially textured surfaces (brushed metal, grain, scanlines, panel screws, paper) | ✓ |
| Intentional typography pairing (rationale documented) | ✓ |
| Atmospheric, not decorative motion (LED pulse, BPM-synced drop pulse, beat tick) | ✓ |
| Retro-futurist hardware vocabulary (LEDs, DSEG7, rockers, knurled knobs, screws) | ✓ |

## Recommendation

**Spec is contract-ready.** Waves 2-5 can execute against this UI-SPEC.md without further design iteration. Re-run `/gsd-ui-review 12` after Wave 5 ships to grade the rendered implementation 1-4 per pillar.

Implementation-time risks to watch (logged for Wave 3 executor):
- Paper-grain SVG fractalNoise opacity (50-55%) must be tuned per platform — Retina renders the noise crisper than 1080p externals.
- DSEG7 88px hero timecode: ensure the font ships with the "88:88" inactive-segment ghost rendering (use letter-spacing + a ghost `::before` with low-opacity "88:88").
- Phase-tape `build` chunk striped gradient animation: pin to `var(--bpm-period-ms)` not a fixed 1.6s.
- Status badge MIDI hot-unplug: WS bus must continue ticking when sidecar transitions wizard → session mode (Wave 2 SessionLoop responsibility).
