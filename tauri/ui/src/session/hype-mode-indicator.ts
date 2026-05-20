/* Phase 54 Plan 04 / LIVE-01 (SC4 surface) — hype-mode indicator + reaction-
 * cadence pulse.
 *
 * A THIN, additive surface on the live session UI. The reaction transcript
 * stream + the [<verb> @ <mm:ss>] citation chip strip ALREADY exist; the
 * mascot is Phase 56. This module is JUST:
 *   (1) a "HYPE · LIVE" mode indicator (the active interaction mode is
 *       unambiguous), and
 *   (2) a reaction-cadence pulse — a subtle amber LED pulse on each reaction
 *       arrival that makes Success-Criterion-4 ("the cadence feels alive")
 *       a legible on-screen heartbeat. Pulse density IS the felt cadence.
 *
 * Design discipline (frontend-enforcement / CDJ-Whisper baseline
 * mocks/vibemix-direction-final.html):
 *   - 20/80 rule: amber appears at exactly THREE points — the LED dot, the
 *     "LIVE" glow, and the cadence pulse. The "HYPE ·" prefix is ink. The
 *     backing is layered charcoal (--glass / --void), never a flat fill.
 *   - Retro-futurist hardware vocabulary: a segment-LED dot with phosphor
 *     glow (the --glow-* token tiers), not a generic status badge.
 *   - Typography: --type-display (Saira) for the label; no new font, no new
 *     color — every value comes from the existing tokens.css.
 *   - Motion is intentional: ONE orchestrated ~600ms glow ramp per reaction
 *     (the "it just reacted" beat). prefers-reduced-motion degrades to a
 *     one-step opacity change (no ramp) — the pure function returns
 *     pulse=false + glow-soft for reducedMotion, so the mount applies the
 *     tier without the ramp class.
 *
 * The PURE function deriveIndicatorState is the testable core (mirrors the
 * mascot/mood.ts pure-function pattern). The DOM mount is a thin shell.
 *
 * No new ws/IPC wire field — the pulse keys off CohostReaction arrivals that
 * are ALREADY on the bus (session/state.ts). render-loop.ts, the transcript
 * renderer, the chip strip, and the mascot are NOT touched here; wiring this
 * module into the live layout is a follow-on. This file is the module + its
 * contract.
 */

import type { CohostReaction, SettingsView } from "./state.js";

// --- Module constants (one-line editable tuning knobs) --------------------- //

/** Pulse window: a reaction whose arrival is within this many ms of "now"
 *  shows the cadence pulse (glow-strong ramp). ~600ms matches the UI-SPEC
 *  glow ramp duration — the visible "it just reacted" heartbeat. */
export const PULSE_WINDOW_MS = 600;

/** Active-recency window: a reaction in the last ~10s means the co-host is
 *  "actively reacting" → the indicator reads LIVE (glow-soft). Older than
 *  this → LISTENING (glow-faint, alive but waiting). */
export const ACTIVE_WINDOW_MS = 10_000;

// --- Types ----------------------------------------------------------------- //

/** LED phosphor tier (maps to the --glow-* tokens) or the fault color. */
export type IndicatorLedTier =
  | "glow-faint"
  | "glow-soft"
  | "glow-strong"
  | "fault";

export interface IndicatorState {
  /** false when mode !== "hype" — amber is reserved for the live hype state;
   *  in coach/feedback mode the indicator hides (no amber on screen). */
  visible: boolean;
  /** "HYPE · LIVE" | "HYPE · LISTENING" | "HYPE · OFFLINE" | "" (hidden). */
  label: string;
  /** The LED phosphor tier (or fault). */
  ledTier: IndicatorLedTier;
  /** true within PULSE_WINDOW_MS of the latest reaction arrival AND motion
   *  is allowed — drives the ~600ms glow ramp. Always false under
   *  prefers-reduced-motion (the mount applies a static tier instead). */
  pulse: boolean;
}

export interface DeriveIndicatorInput {
  /** The active interaction mode from settings (session/state.ts SettingsView). */
  mode: SettingsView["mode"];
  /** Whether a live session is currently running (bus connected). */
  live: boolean;
  /** Arrival time (epoch ms) of the most-recent CohostReaction, or null when
   *  no reaction has arrived yet this session. */
  lastReactionAtMs: number | null;
  /** "Now" in epoch ms (injected so the function is pure + deterministic). */
  nowMs: number;
  /** prefers-reduced-motion — when true the pulse degrades to a one-step
   *  opacity change (no ramp); the function returns pulse=false + glow-soft. */
  reducedMotion?: boolean;
}

// --- Pure core ------------------------------------------------------------- //

/** Derive the indicator state from mode + liveness + last-reaction recency.
 *
 *  Pure + deterministic — no Date.now(), no DOM, no globals. The testable
 *  core (mirrors mascot/mood.ts). The mount below applies the returned state
 *  to the DOM.
 *
 *  Decision ladder (from 54-UI-SPEC):
 *    - mode !== "hype" → hidden (no amber on screen).
 *    - !live → "HYPE · OFFLINE", fault LED, no pulse.
 *    - live + a reaction within PULSE_WINDOW_MS → "HYPE · LIVE", glow-strong
 *      (or glow-soft under reducedMotion), pulse=!reducedMotion.
 *    - live + a reaction within ACTIVE_WINDOW_MS → "HYPE · LIVE", glow-soft,
 *      no pulse.
 *    - live + idle (no recent reaction) → "HYPE · LISTENING", glow-faint,
 *      no pulse (alive and waiting, not off).
 */
export function deriveIndicatorState(
  input: DeriveIndicatorInput,
): IndicatorState {
  const { mode, live, lastReactionAtMs, nowMs } = input;
  const reducedMotion = input.reducedMotion ?? false;

  // Amber is reserved for the live hype state — hide entirely otherwise.
  if (mode !== "hype") {
    return { visible: false, label: "", ledTier: "glow-faint", pulse: false };
  }

  if (!live) {
    return {
      visible: true,
      label: "HYPE · OFFLINE",
      ledTier: "fault",
      pulse: false,
    };
  }

  const sinceReaction =
    lastReactionAtMs == null ? Number.POSITIVE_INFINITY : nowMs - lastReactionAtMs;

  // Within the pulse window — the "it just reacted" heartbeat.
  if (sinceReaction >= 0 && sinceReaction <= PULSE_WINDOW_MS) {
    return {
      visible: true,
      label: "HYPE · LIVE",
      // Under reduced motion: hold the active tier, no strong-ramp peak.
      ledTier: reducedMotion ? "glow-soft" : "glow-strong",
      pulse: !reducedMotion,
    };
  }

  // Recent enough to read as "actively reacting" → LIVE, settled glow.
  if (sinceReaction >= 0 && sinceReaction <= ACTIVE_WINDOW_MS) {
    return {
      visible: true,
      label: "HYPE · LIVE",
      ledTier: "glow-soft",
      pulse: false,
    };
  }

  // Idle — alive and waiting (the co-host is listening, not dead).
  return {
    visible: true,
    label: "HYPE · LISTENING",
    ledTier: "glow-faint",
    pulse: false,
  };
}

/** Convenience: derive the latest-reaction arrival time (epoch ms) from a
 *  CohostReaction[] ring (session/state.ts). Returns null on an empty ring.
 *  The CohostReaction.ts field is an ISO-8601 UTC string — the same join key
 *  the render-loop uses; parse it to epoch ms here so callers don't have to. */
export function lastReactionArrivalMs(
  reactions: readonly CohostReaction[],
): number | null {
  const latest = reactions[reactions.length - 1];
  if (latest == null) return null;
  const parsed = Date.parse(latest.ts);
  return Number.isNaN(parsed) ? null : parsed;
}

// --- Thin DOM mount -------------------------------------------------------- //

/** The CSS injected once per document — segment-LED dot + label on a layered
 *  charcoal backing. Amber ONLY on the LED + the LIVE glow + the pulse ramp
 *  (20/80). All values reference existing tokens.css variables — no raw hex,
 *  no new font. The pulse is a single ~600ms ease-out glow ramp toggled by a
 *  class; prefers-reduced-motion strips the ramp (the static tier still
 *  reads). */
const INDICATOR_CSS = `
.hype-indicator {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  /* Layered charcoal — recessed glass over void, never a flat fill. */
  background: linear-gradient(180deg, var(--glass-2), var(--glass-3));
  border: 1px solid var(--glass-edge);
  border-radius: 3px;
  box-shadow: inset 0 1px 0 var(--glass-top);
}
.hype-indicator[hidden] { display: none; }

.hype-indicator__led {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  /* Segment-LED dot — the amber phosphor source. */
  background: var(--amber);
  box-shadow: var(--glow-faint);
  transition: box-shadow 220ms ease-out;
}
.hype-indicator__led[data-tier="glow-faint"]  { box-shadow: var(--glow-faint); }
.hype-indicator__led[data-tier="glow-soft"]   { box-shadow: var(--glow-soft); }
.hype-indicator__led[data-tier="glow-strong"] { box-shadow: var(--glow-strong); }
.hype-indicator__led[data-tier="fault"] {
  background: var(--led-fault);
  box-shadow: 0 0 6px var(--led-fault);
}

/* The cadence pulse — one orchestrated ~600ms glow ramp on reaction arrival. */
.hype-indicator__led.is-pulsing {
  animation: hype-pulse 600ms ease-out;
}
@keyframes hype-pulse {
  0%   { box-shadow: var(--glow-soft); }
  35%  { box-shadow: var(--glow-strong); }
  100% { box-shadow: var(--glow-soft); }
}

.hype-indicator__label {
  font-family: var(--type-display);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  line-height: 1;
  /* Ink (--silk) — NOT amber. 20/80: amber stays on the LED + glow + pulse
     only. --silk-65 is the dimmed-ink label tier used elsewhere in session/. */
  color: var(--silk-65);
}

/* prefers-reduced-motion: no ramp — the static tier still communicates. */
@media (prefers-reduced-motion: reduce) {
  .hype-indicator__led.is-pulsing { animation: none; }
}
`;

let _styleInjected = false;

function ensureStyle(doc: Document): void {
  if (_styleInjected) return;
  const el = doc.createElement("style");
  el.setAttribute("data-hype-indicator", "");
  el.textContent = INDICATOR_CSS;
  doc.head.appendChild(el);
  _styleInjected = true;
}

export interface HypeModeIndicatorHandle {
  /** Apply a derived IndicatorState to the DOM (idempotent per-frame). */
  update(state: IndicatorState): void;
  /** The root element (for layout placement by the caller). */
  readonly el: HTMLElement;
}

/** Mount a thin LED + label into `container` and return an `update` handle.
 *
 *  The mount holds no derivation logic — the caller derives an IndicatorState
 *  (via deriveIndicatorState) each frame off the SessionState and calls
 *  update(). The pulse ramp is re-triggered on each update where state.pulse
 *  is true by removing + forcing reflow + re-adding the animation class, so
 *  consecutive reactions each get their own heartbeat. */
export function mountHypeModeIndicator(
  container: HTMLElement,
): HypeModeIndicatorHandle {
  const doc = container.ownerDocument;
  ensureStyle(doc);

  const root = doc.createElement("div");
  root.className = "hype-indicator";

  const led = doc.createElement("span");
  led.className = "hype-indicator__led";
  led.setAttribute("data-tier", "glow-faint");

  const label = doc.createElement("span");
  label.className = "hype-indicator__label";

  root.appendChild(led);
  root.appendChild(label);
  container.appendChild(root);

  function update(state: IndicatorState): void {
    if (!state.visible) {
      root.setAttribute("hidden", "");
      return;
    }
    root.removeAttribute("hidden");
    label.textContent = state.label;
    led.setAttribute("data-tier", state.ledTier);

    if (state.pulse) {
      // Re-trigger the ramp even on back-to-back reactions: drop the class,
      // force a reflow, re-add it so the keyframe restarts each heartbeat.
      led.classList.remove("is-pulsing");
      void led.offsetWidth; // reflow — restarts the animation deterministically
      led.classList.add("is-pulsing");
    } else {
      led.classList.remove("is-pulsing");
    }
  }

  return { update, el: root };
}
