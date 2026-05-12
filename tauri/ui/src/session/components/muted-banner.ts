/* muted-banner.ts — push-to-mute banner (UI-SPEC §14).
 *
 * Recessed glass strip pinned above the transcript inside the cohost
 * panel, fault-toned (--led-fault) with a dome LED + Saira label and a
 * JetBrains Mono hotkey hint. v5 CDJ Whisper migration (2026-05-12):
 * dropped the FL-Studio crash-grad treatment in favour of the same dark
 * glass material the rest of the session deck is sealed in. The fault
 * signal comes from the inset bleed + dome LED, not a heavy panel tint. */

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
    padding: 8px var(--sp-4);
    background: var(--glass-3);
    backdrop-filter: var(--blur-glass-display);
    -webkit-backdrop-filter: var(--blur-glass-display);
    border-top: 1px solid rgba(212, 65, 58, 0.35);
    border-bottom: 1px solid rgba(212, 65, 58, 0.35);
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.85),
      inset 0 0 0 1px rgba(0, 0, 0, 0.5),
      inset 0 0 18px rgba(212, 65, 58, 0.08);
    animation: vmx-muted-enter 150ms ease-out;
  }
  .vmx-muted-banner__left {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--led-fault);
    line-height: 1;
    text-shadow: 0 0 4px rgba(212, 65, 58, 0.28), 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  /* Dome LED — fault-tinted with inset top highlight + outer halo
   * (matches the mock .led treatment in §02 Tactility on Dark Glass). */
  .vmx-muted-banner__led {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--led-fault);
    box-shadow:
      0 0 3px var(--led-fault),
      0 0 6px rgba(212, 65, 58, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.3),
      inset 0 -0.5px 0 rgba(0, 0, 0, 0.4);
    animation: vmx-muted-blink 1400ms ease-in-out infinite;
  }
  .vmx-muted-banner__right {
    font-family: var(--type-mono);
    font-variant-numeric: tabular-nums;
    font-size: 10px;
    color: var(--silk-65);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-muted-banner__right b {
    color: var(--silk);
    font-weight: 600;
    margin: 0 4px;
    padding: 1px 5px;
    border: 1px solid var(--silk-22);
    border-radius: var(--rad-sm);
    background: rgba(0, 0, 0, 0.35);
  }
  @keyframes vmx-muted-enter {
    from { transform: translateY(-4px); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
  }
  @keyframes vmx-muted-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.35; }
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

  // Hotkey rendered as a keycap chip so it reads as the action it is,
  // not as more body text.
  const right = document.createElement("span");
  right.className = "vmx-muted-banner__right";
  right.append(document.createTextNode("PRESS "));
  const cap = document.createElement("b");
  cap.textContent = props.hotkey;
  right.append(cap);
  right.append(document.createTextNode(" TO RESUME"));

  root.append(left, right);
  return root;
}
