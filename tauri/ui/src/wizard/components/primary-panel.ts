/* primary-panel.ts — load-bearing panel surface (UI-SPEC §2 / CDJ Whisper v5).
 *
 * v5 glass anatomy: --glass-2 + --blur-glass-light + --glass-edge stroke,
 * inset --glass-top top sheen + rgba(0,0,0,0.45) bottom hairline, deep
 * drop shadow, shared glass-fingerprint streak — unifies wizard surfaces
 * with the session deck panels.
 *
 * First child is the v5 animated border (conic-gradient sweep, tokens.css
 * .border-anim utility). Panel content sits above at z-index 1+.
 *
 * Optional header: Saira wdth 85 wght 600 9px UPPERCASE 0.28em tracking.
 * Optional amber pill badge on right (uses --amber-22 border + --amber). */

import { registerStyle } from "./_style-registry.js";

export interface PrimaryPanelProps {
  header?: string;
  badge?: string;
  children: HTMLElement | HTMLElement[];
}

const CSS = `
  .cmp-primary-panel {
    position: relative;
    background: var(--glass-2);
    backdrop-filter: var(--blur-glass-light);
    -webkit-backdrop-filter: var(--blur-glass-light);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    box-shadow:
      inset 0 1px 0 var(--glass-top),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45),
      0 16px 36px rgba(0, 0, 0, 0.5),
      0 0 0 1px rgba(255, 255, 255, 0.018);
    overflow: hidden;
  }
  .cmp-primary-panel > * { position: relative; z-index: 1; }
  .cmp-primary-panel__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    padding: var(--sp-3) var(--sp-5);
    border-bottom: 1px solid var(--glass-edge);
    background: rgba(0, 0, 0, 0.22);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 9px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--silk);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    line-height: 1;
    z-index: 2;
  }
  .cmp-primary-panel__badge {
    font-family: var(--type-mono);
    font-size: 9px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    padding: 2px var(--sp-2);
    border-radius: var(--rad-sm);
    background: rgba(255, 138, 61, 0.08);
    border: 1px solid var(--amber-22);
    color: var(--amber);
    line-height: 1;
    text-shadow: 0 0 4px var(--amber-22);
  }
  .cmp-primary-panel__body {
    position: relative;
    padding: var(--sp-5);
  }
`;

registerStyle("cmp-primary-panel", CSS);

export function PrimaryPanel(props: PrimaryPanelProps): HTMLElement {
  const root = document.createElement("section");
  root.className = "cmp-primary-panel";

  // v5 animated border — first child of every glass panel.
  // tokens.css .border-anim handles the conic-gradient sweep + mask
  // composite (parent already has position: relative + overflow: hidden).
  const borderAnim = document.createElement("div");
  borderAnim.className = "border-anim";
  borderAnim.setAttribute("aria-hidden", "true");
  root.append(borderAnim);

  // Shared glass-fingerprint streak — keep beneath component content.
  const streak = document.createElement("span");
  streak.className = "vmx-glass-streak";
  streak.setAttribute("aria-hidden", "true");
  root.append(streak);

  if (props.header) {
    const head = document.createElement("div");
    head.className = "cmp-primary-panel__header";
    const title = document.createElement("span");
    title.textContent = props.header;
    head.append(title);
    if (props.badge) {
      const badge = document.createElement("span");
      badge.className = "cmp-primary-panel__badge";
      badge.textContent = props.badge;
      head.append(badge);
    }
    root.append(head);
  }
  const body = document.createElement("div");
  body.className = "cmp-primary-panel__body";
  const kids = Array.isArray(props.children) ? props.children : [props.children];
  kids.forEach((c) => body.append(c));
  root.append(body);
  return root;
}
