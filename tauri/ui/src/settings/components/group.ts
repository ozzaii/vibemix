/* Settings drawer group wrapper.
 *
 * A "group" is one labelled section inside the slide-over drawer
 * (PERSONA, OUTPUT, HOTKEY, RECORDING, CALIBRATION, MASCOT). Visually a
 * subdued v5 plate — glass-2 backdrop with silkscreen Saira header,
 * glass-edge hairline, no streak (the drawer is already one big glass
 * surface; stacking sheens inside it reads noisy).
 *
 * Pure-function — accepts {header, children, badge?, footer?} and returns
 * an HTMLElement. No state.
 */

import { registerStyle } from "../../session/components/_style-registry.js";

export interface SettingsGroupProps {
  header: string;
  children: HTMLElement | HTMLElement[];
  /** Optional UPPER-pill on the right of the header (e.g. "CFG"). */
  badge?: string;
  /** Optional footer slot (e.g. inline error message). */
  footer?: HTMLElement | null;
}

const CSS = `
  .vmx-settings-group {
    position: relative;
    background: var(--glass-2);
    backdrop-filter: var(--blur-glass-display);
    -webkit-backdrop-filter: var(--blur-glass-display);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    overflow: hidden;
    box-shadow:
      inset 0 1px 0 var(--glass-top),
      inset 0 -1px 0 rgba(0, 0, 0, 0.4),
      0 6px 20px rgba(0, 0, 0, 0.35);
  }
  .vmx-settings-group__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    padding: 10px var(--sp-4);
    border-bottom: 1px solid var(--glass-edge);
    background: rgba(0, 0, 0, 0.25);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 9px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--silk);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-settings-group__badge {
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
  .vmx-settings-group__body {
    padding: var(--sp-4);
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
  }
  .vmx-settings-group__footer {
    padding: 8px var(--sp-4);
    border-top: 1px solid rgba(212, 65, 58, 0.25);
    background: rgba(212, 65, 58, 0.05);
    font-family: var(--type-mono);
    font-size: 11px;
    color: var(--led-fault);
    line-height: 1.35;
    text-shadow: 0 0 4px rgba(212, 65, 58, 0.18);
  }
`;

registerStyle("vmx-settings-group", CSS);

export function renderSettingsGroup(props: SettingsGroupProps): HTMLElement {
  const root = document.createElement("section");
  root.className = "vmx-settings-group";

  const head = document.createElement("div");
  head.className = "vmx-settings-group__header";
  const title = document.createElement("span");
  title.textContent = props.header;
  head.append(title);
  if (props.badge) {
    const b = document.createElement("span");
    b.className = "vmx-settings-group__badge";
    b.textContent = props.badge;
    head.append(b);
  }
  root.append(head);

  const body = document.createElement("div");
  body.className = "vmx-settings-group__body";
  const kids = Array.isArray(props.children) ? props.children : [props.children];
  for (const k of kids) body.append(k);
  root.append(body);

  if (props.footer) {
    const footer = document.createElement("div");
    footer.className = "vmx-settings-group__footer";
    footer.append(props.footer);
    root.append(footer);
  }

  return root;
}
