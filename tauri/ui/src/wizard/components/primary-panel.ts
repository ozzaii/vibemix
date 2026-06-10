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
  /* FABLE PASS (2026-06-10): the v5 cool blue-black slab (raw rgba(8,10,16)
   * literals + old-silk rivets) is GONE — inside the retextured warm room it
   * read as a leftover cold tile. The panel now sits in the mock's card
   * material: warm void gradient, machined bevel, one brand hairline catching
   * the top lip (the evidence-card seam). */
  .cmp-primary-panel {
    position: relative;
    padding: var(--sp-5);
    border: 1px solid var(--border-subtle);
    border-radius: var(--rad-md);
    background: linear-gradient(180deg, var(--void-10) 0%, var(--void-5) 100%);
    box-shadow:
      var(--bevel-raised),
      0 18px 46px rgba(0, 0, 0, 0.22);
    overflow: hidden;
  }
  .cmp-primary-panel::before {
    content: "";
    position: absolute;
    inset: 0 12px auto;
    height: 1px;
    pointer-events: none;
    background: linear-gradient(90deg, transparent, var(--brand-35), transparent);
    opacity: 0.5;
  }
  .cmp-primary-panel__header {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    padding: 0 0 var(--sp-3);
    border-bottom: 1px solid var(--border-subtle);
    /* Engraved silkscreen label — the contract speaks mono for machine labels,
     * not the condensed display face. */
    font-family: var(--type-mono);
    font-weight: 600;
    font-size: 9px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--text-muted);
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
    background: rgba(255, 165, 223, 0.08);
    border: 1px solid var(--amber-22);
    color: var(--amber);
    line-height: 1;
    text-shadow: 0 0 4px var(--amber-22);
  }
  .cmp-primary-panel__body {
    position: relative;
    z-index: 2;
    padding: var(--sp-4) 0 0;
  }
  @media (max-width: 720px) {
    .cmp-primary-panel {
      padding: var(--sp-4);
    }
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
