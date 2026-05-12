/* primary-panel.ts — load-bearing panel surface (UI-SPEC §2).
 *
 * Mirrors mocks/vibemix-app-ui.html .panel (lines 295-323) — gradient
 * --panel-lift → --panel, 1px --bezel-1 border, 8px radius, inset
 * top-highlight + bottom-shadow, brushed-metal vertical streak via ::before.
 *
 * Optional header: Workbench 9px UPPERCASE 0.32em with dashed --bezel-2
 * bottom border. Optional --phosphor-soft "DETECTED" badge pill on right. */

import { registerStyle } from "./_style-registry.js";

export interface PrimaryPanelProps {
  header?: string;
  badge?: string;
  children: HTMLElement | HTMLElement[];
}

const CSS = `
  .cmp-primary-panel {
    position: relative;
    background: linear-gradient(180deg, var(--panel-lift) 0%, var(--panel) 100%);
    border: 1px solid var(--bezel-1);
    border-radius: 8px;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.05),
      inset 0 -1px 0 rgba(0, 0, 0, 0.4);
    overflow: hidden;
  }
  /* Brushed-metal vertical streak — left highlight, right shadow */
  .cmp-primary-panel::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background-image: linear-gradient(
      90deg,
      var(--brushed-hi) 0%,
      transparent 12%,
      transparent 88%,
      var(--brushed-lo) 100%
    );
    mix-blend-mode: overlay;
    opacity: 0.6;
  }
  .cmp-primary-panel__header {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-md);
    padding: var(--sp-md) var(--sp-lg);
    border-bottom: 1px dashed var(--bezel-2);
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    color: var(--ink);
  }
  .cmp-primary-panel__badge {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    padding: var(--sp-xs) var(--sp-sm);
    border-radius: 3px;
    background: var(--phosphor-soft);
    color: var(--phosphor);
    line-height: 1;
  }
  .cmp-primary-panel__body {
    position: relative;
    padding: var(--sp-lg);
  }
`;

registerStyle("cmp-primary-panel", CSS);

export function PrimaryPanel(props: PrimaryPanelProps): HTMLElement {
  const root = document.createElement("section");
  root.className = "cmp-primary-panel";
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
