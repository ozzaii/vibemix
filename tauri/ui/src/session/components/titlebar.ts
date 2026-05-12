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
    gap: var(--sp-md);
    height: var(--titlebar-h);
    padding: 0 var(--sp-lg);
    background: linear-gradient(180deg, var(--bezel-1) 0%, var(--panel) 50%, var(--panel) 100%);
    border-bottom: 1px solid var(--bezel-1);
    -webkit-app-region: drag;
    user-select: none;
    position: relative;
  }
  .vmx-titlebar__traffic {
    width: 72px;
    height: 100%;
    flex-shrink: 0;
    -webkit-app-region: no-drag;
  }
  .vmx-titlebar__wordmark {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 28px;
    letter-spacing: 0.04em;
    color: var(--phosphor);
    text-shadow: var(--phosphor-glow);
    line-height: 1;
  }
  .vmx-titlebar__pills {
    display: flex;
    align-items: center;
    gap: var(--sp-sm);
    margin-left: var(--sp-lg);
  }
  .vmx-titlebar__pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: var(--panel-deep);
    border: 1px solid var(--bezel-2);
    border-radius: 4px;
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-dim);
    line-height: 1;
  }
  .vmx-titlebar__pill-led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ink-engraved);
    box-shadow: inset 0 0 1px rgba(0, 0, 0, 0.5);
  }
  .vmx-titlebar__pill[data-state="ok"] .vmx-titlebar__pill-led {
    background: var(--ok);
    box-shadow: 0 0 6px var(--ok);
  }
  .vmx-titlebar__pill[data-state="ok"] { color: var(--ink); }
  .vmx-titlebar__pill[data-key="rec"][data-state="ok"] .vmx-titlebar__pill-led {
    background: var(--rec);
    box-shadow: 0 0 6px var(--rec);
    animation: vmx-rec-blink 1400ms ease-in-out infinite;
  }
  .vmx-titlebar__pill[data-key="rec"][data-state="ok"] { color: var(--rec); }
  .vmx-titlebar__pill[data-state="down"] .vmx-titlebar__pill-led {
    background: var(--rec);
    box-shadow: 0 0 6px var(--rec);
  }
  .vmx-titlebar__pill[data-state="down"] { color: var(--rec); }
  @keyframes vmx-rec-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.35; }
  }
  .vmx-titlebar__clock {
    margin-left: auto;
    font-family: "DSEG7", "DM Mono", monospace;
    font-size: 22px;
    color: var(--phosphor);
    text-shadow: var(--phosphor-glow);
    letter-spacing: 0.06em;
    line-height: 1;
    -webkit-app-region: no-drag;
  }
  .vmx-titlebar__settings {
    -webkit-app-region: no-drag;
    margin-left: var(--sp-md);
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--ink-dim);
    cursor: pointer;
    transition: color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  .vmx-titlebar__settings:hover,
  .vmx-titlebar__settings[data-active="true"] {
    color: var(--phosphor);
    background: var(--phosphor-soft);
    border-color: var(--phosphor-dim);
    box-shadow: var(--phosphor-glow);
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
