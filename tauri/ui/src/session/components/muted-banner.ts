/* muted-banner.ts — push-to-mute banner (UI-SPEC §14).
 *
 * --rec-tinted strip pinned above the transcript inside the cohost panel.
 * Background uses the `--crash-grad-*` tokens (same charcoal+rec tinting
 * as the Phase 11 crash banner — avoids introducing new tokens). Border
 * top + bottom 1px --rec. The strip is purely presentation; SessionLayout
 * (Wave 3) wires the global push-to-mute hotkey and toggles its display. */

import { registerStyle } from "./_style-registry.js";

export interface MutedBannerProps {
  /** Display-friendly hotkey label e.g. "⌘⇧M" or "Ctrl+Shift+M". */
  hotkey: string;
}

const CSS = `
  .vmx-muted-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px var(--sp-md);
    background: linear-gradient(180deg, var(--crash-grad-top), var(--crash-grad-bottom));
    border-top: 1px solid var(--rec);
    border-bottom: 1px solid var(--rec);
    animation: vmx-muted-enter 150ms ease-out;
  }
  .vmx-muted-banner__left {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--rec);
    line-height: 1;
  }
  .vmx-muted-banner__led {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--rec);
    box-shadow: 0 0 6px var(--rec);
  }
  .vmx-muted-banner__right {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--ink-dim);
    letter-spacing: 0.01em;
    text-transform: uppercase;
    line-height: 1;
  }
  @keyframes vmx-muted-enter {
    from { transform: translateY(-4px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
`;

registerStyle("vmx-muted-banner", CSS);

export function renderMutedBanner(props: MutedBannerProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-muted-banner";
  root.setAttribute("role", "status");
  root.setAttribute("aria-live", "polite");

  const left = document.createElement("span");
  left.className = "vmx-muted-banner__left";
  const led = document.createElement("span");
  led.className = "vmx-muted-banner__led";
  led.setAttribute("aria-hidden", "true");
  const lbl = document.createElement("span");
  lbl.textContent = "MUTED";
  left.append(led, lbl);

  const right = document.createElement("span");
  right.className = "vmx-muted-banner__right";
  right.textContent = `PRESS ${props.hotkey} TO RESUME`;

  root.append(left, right);
  return root;
}
