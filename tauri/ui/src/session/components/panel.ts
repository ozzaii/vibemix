/* panel.ts — generic panel shell helper for the live session UI.
 *
 * Lifts the PrimaryPanel pattern from Phase 11 wizard but adds the brushed-
 * metal vertical-streak ::before overlay verbatim from mocks/vibemix-app-ui.html
 * `.col::before` (lines 195-202) — so every column in the 3-col grid feels
 * like a milled aluminium plate. Header strip is the same Workbench 9px
 * UPPERCASE 0.32em label + optional --phosphor-soft pill badge as wizard.
 *
 * Used by: persona panel, output panel, midi panel, timecode block, cohost
 * panel (via dedicated cohost.ts wrapper). Settings drawer groups also use it
 * (composed in Plan 12-05). */

import { registerStyle } from "./_style-registry.js";

export interface PanelProps {
  header?: string;
  badge?: string;
  children: HTMLElement | HTMLElement[];
  /** Optional className to bolt on so callers can scope further (e.g. .timecode-block). */
  variant?: string;
}

const CSS = `
  .vmx-panel {
    position: relative;
    background: linear-gradient(180deg, var(--panel-lift) 0%, var(--panel) 100%);
    border: 1px solid var(--bezel-1);
    border-radius: 8px;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.05),
      inset 0 -1px 0 rgba(0, 0, 0, 0.4);
    overflow: hidden;
  }
  .vmx-panel::before {
    /* Brushed-metal vertical streak — left highlight, right shadow.
     * Lifted from mocks/vibemix-app-ui.html .col::before. */
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
  .vmx-panel__header {
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
  .vmx-panel__badge {
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
  .vmx-panel__body {
    position: relative;
    padding: var(--sp-lg);
  }
`;

registerStyle("vmx-panel", CSS);

export function renderPanel(props: PanelProps): HTMLElement {
  const root = document.createElement("section");
  root.className = "vmx-panel";
  if (props.variant) root.classList.add(props.variant);
  if (props.header) {
    const head = document.createElement("div");
    head.className = "vmx-panel__header";
    const title = document.createElement("span");
    title.textContent = props.header;
    head.append(title);
    if (props.badge) {
      const badge = document.createElement("span");
      badge.className = "vmx-panel__badge";
      badge.textContent = props.badge;
      head.append(badge);
    }
    root.append(head);
  }
  const body = document.createElement("div");
  body.className = "vmx-panel__body";
  const kids = Array.isArray(props.children) ? props.children : [props.children];
  kids.forEach((c) => body.append(c));
  root.append(body);
  return root;
}
