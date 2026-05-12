/* controller-probe.ts — Step 3 hero (UI-SPEC §10).
 *
 * Three vertical zones:
 *   Zone A: controller silhouette + name + port + ● CONNECTED LED, or
 *           empty-state "no controller detected — plug one in or skip".
 *   Zone B: DSEG7 48px --phosphor --phosphor-halo countdown "00:10" with
 *           4 concentric rings expand-fade outward (2s ease-out infinite,
 *           0.5s stagger). States: listening / caught / timeout.
 *   Zone C: [ ↻ Listen again ] secondary + [ Skip — use generic mapping ]
 *           (--rec accent idle, primary-armed after timeout).
 *
 * Copy strings VERBATIM from UI-SPEC §10 + §Step 3. */

import { registerStyle } from "./_style-registry.js";
import { DDJ_FLX4_SVG } from "../controllers/ddj-flx4.svg.js";
import { PLUG_SVG } from "../icons/speaker.svg.js";
import { Button } from "./button.js";

export type ControllerProbeState = "listening" | "caught" | "timeout";

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
    gap: var(--sp-lg);
    padding: var(--sp-lg);
  }
  .cmp-ctrl-probe__zone-a {
    display: grid;
    grid-template-columns: 64px 1fr auto;
    align-items: center;
    gap: var(--sp-md);
    padding: var(--sp-md);
    background: var(--panel-deep);
    border: 1px solid var(--bezel-1);
    border-radius: 6px;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.4);
  }
  .cmp-ctrl-probe__silhouette {
    color: var(--phosphor-dim);
    width: 64px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .cmp-ctrl-probe[data-detected="true"] .cmp-ctrl-probe__silhouette {
    color: var(--phosphor-dim);
  }
  .cmp-ctrl-probe__model {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .cmp-ctrl-probe__name {
    font-family: "DM Mono", monospace;
    font-weight: 500;
    font-size: 14px;
    color: var(--ink);
  }
  .cmp-ctrl-probe__port {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--ink-dim);
  }
  .cmp-ctrl-probe__connected {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-xs);
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    color: var(--ok);
  }
  .cmp-ctrl-probe__connected-led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ok);
    box-shadow: 0 0 6px var(--ok);
  }
  .cmp-ctrl-probe__empty {
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    gap: var(--sp-md);
    font-family: "DM Mono", monospace;
    font-size: 14px;
    color: var(--ink-dim);
  }
  .cmp-ctrl-probe__empty-glyph {
    color: var(--ink-deep);
  }
  .cmp-ctrl-probe__zone-b {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--sp-md);
    padding: var(--sp-2xl) var(--sp-lg);
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
    border: 1px solid var(--phosphor-soft);
    border-radius: 50%;
    opacity: 0;
  }
  .cmp-ctrl-probe[data-state="listening"] .cmp-ctrl-probe__ring {
    animation: cmp-ctrl-ring var(--motion-rings-listen) ease-out infinite;
  }
  .cmp-ctrl-probe[data-state="listening"] .cmp-ctrl-probe__ring:nth-child(2) { animation-delay: 0.5s; }
  .cmp-ctrl-probe[data-state="listening"] .cmp-ctrl-probe__ring:nth-child(3) { animation-delay: 1.0s; }
  .cmp-ctrl-probe[data-state="listening"] .cmp-ctrl-probe__ring:nth-child(4) { animation-delay: 1.5s; }
  @keyframes cmp-ctrl-ring {
    0%   { opacity: 0.8; transform: scale(0.4); }
    100% { opacity: 0;   transform: scale(3); }
  }
  .cmp-ctrl-probe__lcd {
    font-family: "DSEG7", "DM Mono", monospace;
    font-size: 48px;
    color: var(--phosphor);
    text-shadow: var(--phosphor-halo);
    letter-spacing: 0.06em;
    line-height: 1;
    position: relative;
    z-index: 1;
    animation: cmp-ctrl-lcd-pulse 1s steps(1) infinite;
  }
  .cmp-ctrl-probe[data-state="timeout"] .cmp-ctrl-probe__lcd {
    color: var(--ink-deep);
    text-shadow: none;
    animation: none;
  }
  .cmp-ctrl-probe[data-state="caught"] .cmp-ctrl-probe__lcd {
    color: var(--ok);
    text-shadow: 0 0 14px var(--ok);
    animation: none;
  }
  @keyframes cmp-ctrl-lcd-pulse {
    0%, 50%   { opacity: 1; }
    51%, 100% { opacity: 0.85; }
  }
  .cmp-ctrl-probe__caption {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink);
    text-align: center;
  }
  .cmp-ctrl-probe[data-state="timeout"] .cmp-ctrl-probe__caption {
    color: var(--ink-dim);
    font-family: "DM Mono", monospace;
    font-size: 14px;
    letter-spacing: 0.01em;
    text-transform: none;
  }
  .cmp-ctrl-probe[data-state="caught"] .cmp-ctrl-probe__caption {
    color: var(--ok);
  }
  .cmp-ctrl-probe__zone-c {
    display: flex;
    justify-content: space-between;
    gap: var(--sp-md);
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
    // UI-SPEC §Step 3 "Empty-state" — VERBATIM
    txt.textContent = "no controller detected — plug one in or skip";
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

  if (props.state === "caught") {
    lcd.textContent = "✓";
    // UI-SPEC §Step 3 "Caught state" — VERBATIM template
    caption.textContent = `✓ ${props.caughtLabel ?? "control"} — CONNECTED`;
  } else if (props.state === "timeout") {
    lcd.textContent = "--:--";
    // UI-SPEC §Step 3 "Timeout state" — VERBATIM
    caption.textContent = "no midi received";
  } else {
    lcd.textContent = fmtCountdown(props.secondsLeft ?? 10);
    // UI-SPEC §Step 3 "Listen instruction" — VERBATIM
    caption.textContent = "PRESS ANY PAD OR BUTTON";
  }

  frame.append(rings, lcd);
  zoneB.append(frame, caption);

  // --- Zone C ---
  const zoneC = document.createElement("div");
  zoneC.className = "cmp-ctrl-probe__zone-c";
  zoneC.append(
    Button({
      variant: "secondary",
      state: "idle",
      // UI-SPEC §Step 3 "Listen-again button" — VERBATIM
      label: "↻ Listen again",
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: props.onListenAgain,
    }),
    Button({
      variant: props.state === "timeout" ? "primary" : "secondary",
      state: props.state === "timeout" ? "armed" : "idle",
      destructive: props.state !== "timeout",
      // UI-SPEC §Step 3 "Skip button" — VERBATIM
      label: "Skip — use generic mapping",
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: props.onSkip,
    })
  );

  root.append(zoneA, zoneB, zoneC);
  return root;
}
