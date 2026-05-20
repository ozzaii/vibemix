---
phase: 54-hype-mode-live
plan: 04
title: "Hype-mode indicator + reaction-cadence pulse (LIVE-01 SC4 surface)"
status: complete
req_ids: [LIVE-01]
commits: 2
---

# 54-04 SUMMARY — Hype-mode indicator + reaction-cadence pulse (LIVE-01 SC4)

## What was built

A thin, additive live-session UI surface that makes the hype mode and its
reaction cadence VISIBLE: a "HYPE · LIVE" mode indicator and a reaction-cadence
pulse — the legible amber heartbeat for Success-Criterion-4 ("the cadence feels
alive").

### `tauri/ui/src/session/hype-mode-indicator.ts`

- **`deriveIndicatorState({mode, live, lastReactionAtMs, nowMs, reducedMotion})`**
  — the PURE, testable core (mirrors `mascot/mood.ts`). Decision ladder:
  - `mode !== "hype"` → hidden (no amber on screen — amber is reserved for the
    live hype state)
  - `!live` → `HYPE · OFFLINE`, fault LED, no pulse
  - reaction within `PULSE_WINDOW_MS` (600) → `HYPE · LIVE`, `glow-strong`,
    pulse=true (glow-soft + pulse=false under reducedMotion)
  - reaction within `ACTIVE_WINDOW_MS` (10s) → `HYPE · LIVE`, `glow-soft`
  - idle → `HYPE · LISTENING`, `glow-faint` (alive and waiting, not off)
- **`mountHypeModeIndicator(container)`** — thin DOM mount: a segment-LED dot +
  label on a layered-charcoal backing; `update(state)` applies the tier + label
  and re-triggers a ~600ms ease-out glow ramp per reaction (reflow restart so
  back-to-back reactions each get their own heartbeat).
- **`lastReactionArrivalMs(reactions)`** — parses the `CohostReaction.ts` ISO
  string ring → epoch ms (null on empty / malformed ts).
- Constants `PULSE_WINDOW_MS = 600`, `ACTIVE_WINDOW_MS = 10000` — one-line
  editable tuning knobs.

### `tauri/ui/src/session/hype-mode-indicator.test.ts`

12 vitest cases over the pure core (no DOM/animation flake): coach→hidden;
LIVE/glow-strong/pulse within the window; LIVE/glow-soft past the pulse but
within the active window; LISTENING/glow-faint when idle / no-reaction-yet;
OFFLINE/fault when not live; reducedMotion degrade; inclusive pulse-window
boundary; clock-skew (negative-since) guard; and the `lastReactionArrivalMs`
helper (empty / last / malformed-ts).

## Tokens.css reuse + frontend-enforcement adherence

- **20/80 rule:** amber appears at exactly three points — the LED dot
  (`--amber`), the LIVE glow (`--glow-soft/strong`), and the cadence pulse
  ramp. The "HYPE · …" label is ink (`--silk-65`), NOT amber.
- **Token-only colors:** grep for raw hex (`#`) in the module returns NOTHING —
  every color/glow/font references an existing `tokens.css` variable
  (`--amber`, `--amber-22/40/65` via `--glow-*`, `--void`/`--glass-*`,
  `--led-fault`, `--silk-65`, `--type-display`).
- **Retro-futurist hardware vocabulary:** a segment-LED dot with phosphor glow
  tiers, not a generic status badge. Layered charcoal backing (glass over
  void), never a flat fill.
- **Intentional motion:** ONE orchestrated ~600ms glow ramp per reaction;
  `prefers-reduced-motion` strips the ramp (the static tier still reads — the
  pure function returns pulse=false + glow-soft).
- **No generic AI fonts:** `--type-display` (Saira) for the label.
- Invoked the `frontend-enforcement` skill before writing UI code.

## Standalone — nothing else touched

No new ws/IPC wire field — the pulse keys off `CohostReaction` arrivals already
on the bus; it imports the existing `CohostReaction` / `SettingsView` types from
`./state`. `render-loop.ts`, the transcript renderer, the citation chip strip,
the mascot, and the Kaan-WIP Rust files are NOT touched. Wiring this module into
the live session layout is a follow-on; the module + its contract is this plan's
deliverable.

## Verification (real)

- `cd tauri/ui && npm test -- hype-mode-indicator` → **12 passed**.
- `cd tauri/ui && npm run -s build` (`tsc --noEmit && vite build`) → **BUILD_OK**.
  (One real strict-null typecheck error in the ring helper was caught + fixed
  before commit — `latest` possibly-undefined under `noUncheckedIndexedAccess`.)
- `git status --porcelain` confirms ONLY the two new files changed (no
  render-loop / chip strip / mascot / Rust WIP).

## Commits

1. `bdf91bd` feat(54-04): hype-mode indicator + cadence-pulse module (LIVE-01)
2. `08009d7` test(54-04): vitest cover hype-mode indicator states + cadence pulse (LIVE-01)
