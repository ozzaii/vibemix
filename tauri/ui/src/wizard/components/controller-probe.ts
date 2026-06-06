/* controller-probe.ts — Step 3 hero (UI-SPEC §10 / CDJ Whisper v5).
 *
 * Three vertical zones:
 *   Zone A: controller silhouette + name + port + ● CONNECTED label, or
 *           passive "controller optional" empty state.
 *   Zone B: idle "READY", 10s listening countdown, caught, or timeout.
 *   Zone C: [ Listen now ] / [ ↻ Listen again ] + non-destructive skip. */

import { registerStyle } from "./_style-registry.js";
import { DDJ_FLX4_SVG } from "../controllers/ddj-flx4.svg.js";
import { PLUG_SVG } from "../icons/speaker.svg.js";
import { Button } from "./button.js";

export type ControllerProbeState = "idle" | "listening" | "caught" | "timeout";

export interface ControllerProbeProps {
  detectedController?: { name: string; port: string; silhouette?: string };
  state: ControllerProbeState;
  caughtLabel?: string;
  secondsLeft?: number;
  onListenAgain: () => void;
  onSkip: () => void;
}

const CSS = `
  .cmp-ctrl-probe {
    display: flex;
    flex-direction: column;
    gap: var(--sp-5);
    padding: var(--sp-5);
  }
  .cmp-ctrl-probe__zone-a {
    display: grid;
    grid-template-columns: 64px 1fr auto;
    align-items: center;
    gap: var(--sp-4);
    padding: var(--sp-4);
    background: var(--glass-3);
    backdrop-filter: var(--blur-glass-display);
    -webkit-backdrop-filter: var(--blur-glass-display);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    box-shadow:
      inset 0 2px 4px rgba(0, 0, 0, 0.4),
      inset 0 1px 0 var(--glass-top);
  }
  .cmp-ctrl-probe__silhouette {
    color: var(--silk-65);
    width: 64px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .cmp-ctrl-probe[data-detected="true"] .cmp-ctrl-probe__silhouette {
    color: var(--amber);
    filter: drop-shadow(0 0 3px var(--amber-22));
  }
  .cmp-ctrl-probe__model {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .cmp-ctrl-probe__name {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 500;
    font-size: 14px;
    color: var(--silk);
  }
  .cmp-ctrl-probe__port {
    font-family: var(--type-mono);
    font-size: 11px;
    color: var(--silk-65);
  }
  .cmp-ctrl-probe__connected {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-1);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--led-ok);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .cmp-ctrl-probe__connected-led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--led-ok);
    box-shadow: 0 0 6px var(--led-ok);
  }
  .cmp-ctrl-probe__empty {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    gap: var(--sp-4);
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 14px;
    color: var(--silk-65);
  }
  .cmp-ctrl-probe__empty-glyph {
    color: var(--silk-40);
  }
  .cmp-ctrl-probe__zone-b {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--sp-4);
    padding: 48px var(--sp-5); /* mock-verbatim 48 — no v5 sp- token at 48 */
  }
  .cmp-ctrl-probe__lcd-frame {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 200px;
    height: 80px;
  }
  .cmp-ctrl-probe__rings {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }
  .cmp-ctrl-probe__ring {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 80px;
    height: 80px;
    margin: -40px 0 0 -40px;
    border: 1px solid var(--amber-22);
    border-radius: 50%;
    opacity: 0;
  }
  .cmp-ctrl-probe[data-state="listening"] .cmp-ctrl-probe__ring {
    animation: cmp-ctrl-ring var(--motion-rings-listen) ease-out infinite;
  }
  .cmp-ctrl-probe[data-state="listening"] .cmp-ctrl-probe__ring:nth-child(2) {
    animation-delay: 0.5s;
    border-color: var(--amber-40);
  }
  .cmp-ctrl-probe[data-state="listening"] .cmp-ctrl-probe__ring:nth-child(3) {
    animation-delay: 1.0s;
    border-color: var(--amber-65);
  }
  .cmp-ctrl-probe[data-state="listening"] .cmp-ctrl-probe__ring:nth-child(4) {
    animation-delay: 1.5s;
    border-color: var(--amber-22);
  }
  @keyframes cmp-ctrl-ring {
    0%   { opacity: 0.8; transform: scale(0.4); }
    100% { opacity: 0;   transform: scale(3); }
  }
  .cmp-ctrl-probe__lcd {
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-feature-settings: "tnum";
    font-size: 48px;
    color: var(--amber);
    text-shadow: var(--glow-soft);
    letter-spacing: 0.06em;
    line-height: 1;
    position: relative;
    z-index: 1;
    animation: cmp-ctrl-lcd-pulse 1s steps(1) infinite;
  }
  .cmp-ctrl-probe[data-state="timeout"] .cmp-ctrl-probe__lcd {
    color: var(--silk-40);
    text-shadow: none;
    animation: none;
  }
  .cmp-ctrl-probe[data-state="idle"] .cmp-ctrl-probe__lcd {
    color: var(--silk-65);
    text-shadow: none;
    animation: none;
  }
  .cmp-ctrl-probe[data-state="caught"] .cmp-ctrl-probe__lcd {
    color: var(--led-ok);
    text-shadow: 0 0 14px var(--led-ok);
    animation: none;
  }
  @keyframes cmp-ctrl-lcd-pulse {
    0%, 50%   { opacity: 1; }
    51%, 100% { opacity: 0.85; }
  }
  .cmp-ctrl-probe__caption {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    text-align: center;
  }
  .cmp-ctrl-probe[data-state="timeout"] .cmp-ctrl-probe__caption {
    color: var(--silk-65);
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 14px;
    letter-spacing: 0.01em;
    text-transform: none;
    text-shadow: none;
  }
  .cmp-ctrl-probe[data-state="idle"] .cmp-ctrl-probe__caption {
    color: var(--silk-65);
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 14px;
    letter-spacing: 0.01em;
    text-transform: none;
    text-shadow: none;
  }
  .cmp-ctrl-probe[data-state="caught"] .cmp-ctrl-probe__caption {
    color: var(--led-ok);
  }
  .cmp-ctrl-probe__hint {
    display: none;
    max-width: 46ch;
    margin-top: calc(var(--sp-2) * -1);
    color: var(--silk-65);
    font-family: var(--type-mono);
    font-size: 11px;
    line-height: 1.4;
    letter-spacing: 0.02em;
    text-align: center;
  }
  .cmp-ctrl-probe[data-state="timeout"] .cmp-ctrl-probe__hint {
    display: block;
  }
  .cmp-ctrl-probe[data-state="idle"] .cmp-ctrl-probe__hint {
    display: block;
  }
  .cmp-ctrl-probe__zone-c {
    display: flex;
    justify-content: space-between;
    gap: var(--sp-4);
  }
`;

registerStyle("cmp-ctrl-probe", CSS);

function fmtCountdown(s: number | undefined): string {
  if (s == null) return "--:--";
  const total = Math.max(0, Math.min(60, Math.round(s)));
  const mm = Math.floor(total / 60).toString().padStart(2, "0");
  const ss = (total % 60).toString().padStart(2, "0");
  return `${mm}:${ss}`;
}

export function ControllerProbe(props: ControllerProbeProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-ctrl-probe";
  root.dataset.state = props.state;
  if (props.detectedController) root.dataset.detected = "true";

  // --- Zone A ---
  const zoneA = document.createElement("div");
  zoneA.className = "cmp-ctrl-probe__zone-a";

  if (props.detectedController) {
    const sil = document.createElement("div");
    sil.className = "cmp-ctrl-probe__silhouette";
    // Phase 11 ships one silhouette (DDJ-FLX4); Phase 12+ adds the curated 10.
    sil.innerHTML = props.detectedController.silhouette ?? DDJ_FLX4_SVG;
    const model = document.createElement("div");
    model.className = "cmp-ctrl-probe__model";
    const name = document.createElement("span");
    name.className = "cmp-ctrl-probe__name";
    name.textContent = props.detectedController.name;
    const port = document.createElement("span");
    port.className = "cmp-ctrl-probe__port";
    port.textContent = props.detectedController.port;
    model.append(name, port);
    const conn = document.createElement("span");
    conn.className = "cmp-ctrl-probe__connected";
    const led = document.createElement("span");
    led.className = "cmp-ctrl-probe__connected-led";
    led.setAttribute("aria-hidden", "true");
    const txt = document.createElement("span");
    // UI-SPEC §Step 3 "Detected zone connected state" — VERBATIM
    txt.textContent = "CONNECTED";
    conn.append(led, txt);
    zoneA.append(sil, model, conn);
  } else {
    const empty = document.createElement("div");
    empty.className = "cmp-ctrl-probe__empty";
    const plug = document.createElement("div");
    plug.className = "cmp-ctrl-probe__empty-glyph";
    plug.innerHTML = PLUG_SVG;
    const txt = document.createElement("span");
    txt.textContent = "controller optional. plug one in now or continue.";
    empty.append(plug, txt);
    zoneA.append(empty);
  }

  // --- Zone B ---
  const zoneB = document.createElement("div");
  zoneB.className = "cmp-ctrl-probe__zone-b";
  const frame = document.createElement("div");
  frame.className = "cmp-ctrl-probe__lcd-frame";
  const rings = document.createElement("div");
  rings.className = "cmp-ctrl-probe__rings";
  for (let i = 0; i < 4; i++) {
    const r = document.createElement("div");
    r.className = "cmp-ctrl-probe__ring";
    rings.append(r);
  }
  const lcd = document.createElement("div");
  lcd.className = "cmp-ctrl-probe__lcd";

  const caption = document.createElement("div");
  caption.className = "cmp-ctrl-probe__caption";
  const hint = document.createElement("div");
  hint.className = "cmp-ctrl-probe__hint";
  hint.textContent =
    "Need mapping now? Click Listen now, then move a fader, knob, pad, cue, or play.";

  if (props.state === "caught") {
    lcd.textContent = "✓";
    // UI-SPEC §Step 3 "Caught state" — VERBATIM template
    caption.textContent = `✓ ${props.caughtLabel ?? "control"} · CONNECTED`;
  } else if (props.state === "timeout") {
    lcd.textContent = "--:--";
    caption.textContent = "no controller move received. continue is ready.";
  } else if (props.state === "idle") {
    lcd.textContent = "READY";
    caption.textContent = "controller detection is optional.";
  } else {
    lcd.textContent = fmtCountdown(props.secondsLeft ?? 10);
    // UI-SPEC §Step 3 "Listen instruction" — VERBATIM
    caption.textContent = "PRESS ANY PAD OR BUTTON";
  }

  frame.append(rings, lcd);
  zoneB.append(frame, caption, hint);

  // --- Zone C ---
  const zoneC = document.createElement("div");
  zoneC.className = "cmp-ctrl-probe__zone-c";
  const listenLabel = props.state === "idle" ? "Listen now" : "↻ Listen again";
  zoneC.append(
    Button({
      variant: "secondary",
      state: "idle",
      label: listenLabel,
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: props.onListenAgain,
    }),
    Button({
      variant: props.state === "timeout" ? "primary" : "secondary",
      state: props.state === "timeout" ? "armed" : "idle",
      destructive: false,
      label: "Skip · use generic mapping",
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: props.onSkip,
    })
  );

  root.append(zoneA, zoneB, zoneC);
  return root;
}
