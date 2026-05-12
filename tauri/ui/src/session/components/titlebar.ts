/* titlebar.ts — top 56px strip for the live session window.
 *
 * Extends the Phase 11 wizard titlebar with the live-session affordances:
 *   - traffic-light spacer (left)
 *   - "vibemix" Workbench 28px wordmark with --phosphor-glow
 *   - 3 status pills (LIVE / REC / SYS) — each with a 6×6 LED
 *   - DSEG7 22px live clock
 *   - SETTINGS gear button (right) — fires onSettingsClick
 *
 * Pure-function: accept props, return HTMLElement, no internal state. The
 * SessionLayout owns the rAF loop that pokes the clock textContent and the
 * pill data-state attributes via the helpers exposed below. */

import { registerStyle } from "./_style-registry.js";
import { GEAR_SVG } from "../icons/gear.svg.js";

export type PillLevel = "ok" | "down" | "off";

export interface TitlebarProps {
  live: PillLevel;
  rec: PillLevel;
  sys: PillLevel;
  clock: string;
  onSettingsClick?: () => void;
}

const CSS = `
  .vmx-titlebar {
    display: flex;
    align-items: center;
    gap: var(--sp-4);
    height: var(--titlebar-h);
    padding: 0 var(--sp-5);
    background: rgba(0, 0, 0, 0.55);
    backdrop-filter: var(--blur-glass-light);
    -webkit-backdrop-filter: var(--blur-glass-light);
    border-bottom: 1px solid var(--glass-edge);
    -webkit-app-region: drag;
    user-select: none;
    position: relative;
    z-index: 3;
  }
  .vmx-titlebar__traffic {
    width: 72px;
    height: 100%;
    flex-shrink: 0;
    -webkit-app-region: no-drag;
  }
  .vmx-titlebar__wordmark {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 78, "wght" 800;
    font-size: 20px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--silk);
    line-height: 1;
    display: inline-flex;
    align-items: center;
    gap: 10px;
  }
  .vmx-titlebar__wordmark::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--amber);
    box-shadow: 0 0 4px var(--amber), 0 0 10px var(--amber-40);
    animation: vmx-brand-pulse 5s ease-in-out infinite;
  }
  @keyframes vmx-brand-pulse {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.45; }
  }
  .vmx-titlebar__pills {
    display: flex;
    align-items: center;
    gap: var(--sp-2);
    margin-left: var(--sp-5);
  }
  .vmx-titlebar__pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: rgba(0, 0, 0, 0.4);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-40);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-titlebar__pill-led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(15, 18, 24, 0.85);
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }
  .vmx-titlebar__pill[data-state="ok"] .vmx-titlebar__pill-led {
    background: var(--led-ok);
    box-shadow:
      0 0 3px var(--led-ok),
      0 0 6px rgba(109, 212, 74, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.3);
  }
  .vmx-titlebar__pill[data-state="ok"] { color: var(--silk); border-color: var(--silk-22); }
  .vmx-titlebar__pill[data-key="rec"][data-state="ok"] .vmx-titlebar__pill-led {
    background: var(--rec);
    box-shadow:
      0 0 3px var(--rec),
      0 0 6px rgba(212, 65, 58, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.3);
    animation: vmx-rec-blink 1400ms ease-in-out infinite;
  }
  .vmx-titlebar__pill[data-key="rec"][data-state="ok"] { color: var(--rec); border-color: rgba(212, 65, 58, 0.35); }
  .vmx-titlebar__pill[data-state="down"] .vmx-titlebar__pill-led {
    background: var(--rec);
    box-shadow: 0 0 3px var(--rec), 0 0 6px rgba(212, 65, 58, 0.28);
  }
  .vmx-titlebar__pill[data-state="down"] { color: var(--rec); border-color: rgba(212, 65, 58, 0.35); }
  @keyframes vmx-rec-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.35; }
  }
  .vmx-titlebar__clock {
    margin-left: auto;
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-weight: 500;
    font-size: 18px;
    color: var(--silk);
    text-shadow: 0 0 6px rgba(255, 138, 61, 0.18);
    letter-spacing: -0.01em;
    line-height: 1;
    -webkit-app-region: no-drag;
  }
  .vmx-titlebar__settings {
    -webkit-app-region: no-drag;
    margin-left: var(--sp-4);
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--rad-sm);
    border: 1px solid transparent;
    background: transparent;
    color: var(--silk-40);
    cursor: pointer;
    transition: color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  .vmx-titlebar__settings:hover,
  .vmx-titlebar__settings[data-active="true"] {
    color: var(--amber);
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
    border-color: var(--amber-40);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 var(--amber-40),
      inset 0 0 12px var(--amber-22);
  }
  .vmx-titlebar__settings .sr-only {
    position: absolute;
    width: 1px; height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }
`;

registerStyle("vmx-titlebar", CSS);

const PILL_DEFS: Array<{ key: "live" | "rec" | "sys"; label: string }> = [
  { key: "live", label: "● LIVE" },
  { key: "rec", label: "● REC" },
  { key: "sys", label: "● SYS" },
];

export function renderTitlebar(props: TitlebarProps): HTMLElement {
  const root = document.createElement("header");
  root.className = "vmx-titlebar";

  const traffic = document.createElement("span");
  traffic.className = "vmx-titlebar__traffic";
  traffic.setAttribute("aria-hidden", "true");
  root.append(traffic);

  const wordmark = document.createElement("span");
  wordmark.className = "vmx-titlebar__wordmark";
  wordmark.textContent = "vibemix";
  wordmark.setAttribute("aria-label", "vibemix");
  root.append(wordmark);

  const pills = document.createElement("span");
  pills.className = "vmx-titlebar__pills";
  for (const def of PILL_DEFS) {
    const pill = document.createElement("span");
    pill.className = "vmx-titlebar__pill";
    pill.dataset.key = def.key;
    pill.dataset.state = props[def.key];
    const led = document.createElement("span");
    led.className = "vmx-titlebar__pill-led";
    led.setAttribute("aria-hidden", "true");
    const lbl = document.createElement("span");
    // strip the leading "● " glyph since we render the LED ourselves
    lbl.textContent = def.label.replace(/^●\s*/, "");
    pill.append(led, lbl);
    pills.append(pill);
  }
  root.append(pills);

  const clock = document.createElement("span");
  clock.className = "vmx-titlebar__clock";
  clock.textContent = props.clock;
  root.append(clock);

  const settings = document.createElement("button");
  settings.type = "button";
  settings.className = "vmx-titlebar__settings";
  settings.innerHTML = GEAR_SVG;
  const srLabel = document.createElement("span");
  srLabel.className = "sr-only";
  srLabel.textContent = "SETTINGS";
  settings.append(srLabel);
  settings.setAttribute("aria-label", "SETTINGS");
  if (props.onSettingsClick) {
    settings.addEventListener("click", (e) => {
      e.preventDefault();
      props.onSettingsClick?.();
    });
  }
  root.append(settings);

  return root;
}

/** Idempotent hot-update for the clock textContent — called by the rAF loop. */
export function setTitlebarClock(el: HTMLElement, clock: string): void {
  const c = el.querySelector<HTMLElement>(".vmx-titlebar__clock");
  if (c && c.textContent !== clock) c.textContent = clock;
}

/** Update a single pill state without rebuilding the titlebar. */
export function setTitlebarPill(
  el: HTMLElement,
  key: "live" | "rec" | "sys",
  state: PillLevel,
): void {
  const pill = el.querySelector<HTMLElement>(
    `.vmx-titlebar__pill[data-key="${key}"]`,
  );
  if (pill) pill.dataset.state = state;
}

/** Mark the gear button armed (drawer open). */
export function setTitlebarSettingsActive(el: HTMLElement, active: boolean): void {
  const btn = el.querySelector<HTMLElement>(".vmx-titlebar__settings");
  if (btn) btn.dataset.active = active ? "true" : "false";
}
