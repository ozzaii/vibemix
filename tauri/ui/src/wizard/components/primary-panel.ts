/* primary-panel.ts — load-bearing panel surface (UI-SPEC §2 / CDJ Whisper v5).
 *
 * Glass shell comes from the shared `.vmx-tile .vmx-tile--panel` utility
 * (tokens.css). This component owns ONLY the internal header/body
 * structure + the optional amber pill badge.
 *
 * Critique 2026-05-14: stripped the duplicate shadow stack + retired
 * the per-panel border-anim sweep + retired the texture-streak. One CDJ
 * has one breathing light — that now lives on the cohost (session) panel
 * only. The wizard primary panel reads quiet.
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
  /* "The Deck Speaks" rebuild (2026-05-26): the wizard step is no longer a
   * glass-card hero (vmx-tile drop-shadow plate). Like the deck + the settings
   * sections, the step is content on the wizard's void — a quiet silk label,
   * a hairline under it, then the step's controls. No card fill, no drop
   * shadow. The wizard is form-bearing (device probe, window pick, MIDI listen)
   * so the controls stay; only the enclosing card is removed. */
  .cmp-primary-panel {
    position: relative;
  }
  .cmp-primary-panel__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    padding: 0 0 var(--sp-3);
    border-bottom: 1px solid var(--glass-edge);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 9px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--silk-40);
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
    padding: var(--sp-4) 0 0;
  }
`;

registerStyle("cmp-primary-panel", CSS);

export function PrimaryPanel(props: PrimaryPanelProps): HTMLElement {
  const root = document.createElement("section");
  // "The Deck Speaks" rebuild: no glass-card shell — the step is content on the
  // wizard void (was `vmx-tile` + data-tile="hero").
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
