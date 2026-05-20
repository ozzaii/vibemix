---
phase: 54
slug: hype-mode-live
status: draft
shadcn_initialized: false
preset: none
created: 2026-05-21
---

# Phase 54 — UI Design Contract

> Visual and interaction contract for the **hype-mode-live indicator** — a THIN
> additive surface on the existing live session UI. The cohost-reaction stream +
> citation strip ALREADY exist (`SessionCohostReaction`, debrief timeline,
> `tokens.css:260` chip styling) and are NOT touched here. The mascot is Phase 56.
> This spec covers only: (1) a "HYPE · LIVE" mode indicator and (2) a reaction-
> cadence pulse — the visible heartbeat that makes Success-Criterion-4 ("the
> cadence feels alive") legible on screen. Tokens are the LIVE ones already in
> `tauri/ui/src/tokens.css` (the `frontend-enforcement` / CDJ-Whisper baseline,
> `mocks/vibemix-direction-final.html`). No new design system, no new font.

---

## Scope Fence (what this surface is / is NOT)

**IS:**
- A mode indicator that unambiguously shows the active interaction mode is **hype** while a live session runs ("HYPE · LIVE" with a phosphor-amber LED).
- A reaction-cadence pulse: a subtle amber glow/LED pulse that fires each time a `SessionCohostReaction` arrives on the bus — a visible "the co-host just reacted" heartbeat. Density of pulses = the felt cadence (SC4).

**IS NOT:**
- The reaction transcript stream (exists).
- The `[<verb> @ <mm:ss>]` citation chip strip (exists, `tokens.css:260`).
- The mascot / VTuber surface (Phase 56).
- Any new ws/IPC wire field — the pulse keys off the existing `SessionCohostReaction` arrival already on the bus. (If a tiny additive `mode` echo is genuinely needed, it reuses the existing snapshot `mode`/interaction state in `session/state.ts` — no new envelope.)

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (hand-authored TS + CSS, matches existing `tauri/ui/src/session/`) |
| Preset | not applicable |
| Component library | none — vanilla TS module like the rest of `session/` |
| Icon library | none — LED dot + segment glyph via CSS (no icon font; retro-futurist hardware vocabulary) |
| Font | existing tokens: `--type-display` (Saira) for the "HYPE · LIVE" label, `--type-mono` (JetBrains Mono) for any count/time numerals |

---

## Spacing Scale

Declared values (multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | LED-to-label gap, inline padding |
| sm | 8px | indicator internal padding |
| md | 16px | indicator-to-panel offset |
| lg | 24px | section padding (reuse existing cohost-panel rhythm) |

Exceptions: none — the indicator inherits the existing `session/` layout grid; it does not introduce a new spacing scale.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 13px | 400 | 1.4 |
| Label ("HYPE · LIVE") | 11px | 600, letter-spacing 0.12em, uppercase | 1.0 |
| Numerals (reaction count / time, if shown) | 12px | 500, tabular-nums (`--type-mono`) | 1.0 |
| Display | n/a (no new heading on this surface) | — | — |

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `--void` / `--void-2/3` (`#000` / `#05070b` / `#0a0c12`) | Indicator backing, panel surface (anodised charcoal, layered — never a flat fill) |
| Secondary (30%) | `--glass-*` translucent surfaces | indicator chrome / inset bevel |
| Accent (10%) | `--amber` `#ff8a3d` (+ `--amber-22/40/65` glow tiers) | the LED dot, the "LIVE" glyph glow, the cadence pulse — and NOTHING else on this surface |
| Destructive | n/a | this surface has no destructive action |

Accent reserved for: the hype LED dot, the "LIVE" word glow, and the cadence pulse ONLY. The "HYPE" label text is ink, not amber. 20/80 rule: amber appears at exactly three points; the rest is charcoal + ink. (`frontend-enforcement` hard rule 2.)

---

## Interaction / Motion

| Element | Behavior |
|---------|----------|
| Mode indicator | When the session's interaction mode is `hype` AND a session is live, render "● HYPE · LIVE" with the amber LED at `--glow-soft`. When mode is not hype (e.g. feedback/coach), the indicator hides or dims to ink-only (no amber) — amber is reserved for the live hype state. |
| Reaction-cadence pulse | On each `SessionCohostReaction` arrival, the amber LED ramps `--glow-soft → --glow-strong → --glow-soft` over ~600ms (ease-out). This is the visible heartbeat — a real reaction landed. Pulses are NOT throttled artificially; their natural density IS the cadence (SC4). |
| Idle (no recent reaction) | LED holds at `--glow-faint` — present but quiet (the co-host is listening, not dead). Distinguishes "alive and waiting" from "off". |
| Motion discipline | One orchestrated pulse per reaction. No decorative hover micro-effects, no spinner. The pulse exists for a material reason (a beat-synced "it reacted" signal), per `frontend-enforcement` rule 6. `prefers-reduced-motion`: the pulse degrades to a one-frame opacity step (no ramp), still legible. |

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Mode indicator (active) | `HYPE · LIVE` |
| Mode indicator (idle/listening) | `HYPE · LISTENING` (ink, no amber) — distinguishes alive-and-waiting from off |
| Empty state (no reaction yet this session) | LED at `--glow-faint`; no text change needed — the LISTENING label already communicates it |
| Error / disconnected state | `HYPE · OFFLINE` (led-fault `#d4413a` dot) — only if the session bus drops; reuses existing `led-fault` token |

(No CTA, no destructive confirmation, no form on this surface.)

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not required |
| third-party | none | not required |

(Hand-authored TS module + CSS using existing `tokens.css` variables. No registry component pulled.)

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
