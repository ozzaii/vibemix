/* panel.ts — generic panel shell helper for the live session UI.
 *
 * v5 CDJ Whisper: each panel reads as a sealed dark-glass plate — glass-2
 * backdrop with hairline top highlight, deep drop shadow, optional
 * silkscreen header strip + amber badge + JetBrains Mono spec note on
 * the right (matches the mock's section-head .right-note treatment).
 *
 * Used by: persona panel, output panel, midi panel, audio-in meters,
 * settings drawer groups. The cohost panel + timecode hero have bespoke
 * wrappers because they own their own border-anim + glass-streak. */

import { registerStyle } from "./_style-registry.js";

export interface PanelProps {
  header?: string;
  /** Amber pill on the left of the header strip (e.g. "CFG", "MASTER"). */
  badge?: string;
  /** Optional JetBrains Mono spec line on the right (e.g. "30 FPS",
   *  "16-BIT · 48K"). Matches the mock section-head right-note slot. */
  spec?: string;
  children: HTMLElement | HTMLElement[];
  /** Optional className to bolt on so callers can scope further (e.g. .timecode-block). */
  variant?: string;
}

const CSS = `
  .vmx-panel {
    /* 2026-05-19 /impeccable critique fix: panel previously carried the
     * hero-tier drop shadow + outer ring (the documented
     * [data-tile=hero] recipe), but EVERY vmx-panel in the session
     * view consumed it (PERSONA, OUTPUT, AUDIO IN), stacking five hero
     * shadows on one screen. DESIGN.md §4 restricts the drop to a single
     * hero panel per view. Demoted to inset-bezel only; the timecode
     * keeps the one allowed hero drop in the session view. */
    position: relative;
    background: var(--glass-2);
    backdrop-filter: var(--blur-glass-light);
    -webkit-backdrop-filter: var(--blur-glass-light);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    box-shadow:
      inset 0 1px 0 var(--glass-top),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45);
    overflow: hidden;
  }
  .vmx-panel > * { position: relative; z-index: 1; }
  .vmx-panel__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-md);
    padding: var(--sp-3) var(--sp-5);
    border-bottom: 1px solid var(--glass-edge);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 9px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--silk-65);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    background: rgba(0, 0, 0, 0.22);
    z-index: 2;
  }
  .vmx-panel__header-left {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-3);
    min-width: 0;
  }
  .vmx-panel__header-title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .vmx-panel__header-right {
    display: inline-flex;
    align-items: center;
    gap: var(--sp-3);
    flex-shrink: 0;
  }
  .vmx-panel__badge {
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
  .vmx-panel__spec {
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--silk-40);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-panel__body {
    position: relative;
    padding: var(--sp-5);
  }
`;

registerStyle("vmx-panel", CSS);

export function renderPanel(props: PanelProps): HTMLElement {
  const root = document.createElement("section");
  root.className = "vmx-panel";
  if (props.variant) root.classList.add(props.variant);

  // Faint diagonal glass-fingerprint streak — quiet character moment
  // shared with the session + cohost panels. Pulled from tokens.css.
  const streak = document.createElement("span");
  streak.className = "vmx-glass-streak";
  streak.setAttribute("aria-hidden", "true");
  root.append(streak);

  if (props.header) {
    const head = document.createElement("div");
    head.className = "vmx-panel__header";

    const left = document.createElement("span");
    left.className = "vmx-panel__header-left";
    const title = document.createElement("span");
    title.className = "vmx-panel__header-title";
    title.textContent = props.header;
    left.append(title);
    if (props.badge) {
      const badge = document.createElement("span");
      badge.className = "vmx-panel__badge";
      badge.textContent = props.badge;
      left.append(badge);
    }
    head.append(left);

    if (props.spec) {
      const right = document.createElement("span");
      right.className = "vmx-panel__header-right";
      const spec = document.createElement("span");
      spec.className = "vmx-panel__spec";
      spec.textContent = props.spec;
      right.append(spec);
      head.append(right);
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
