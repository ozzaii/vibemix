/* Phase 12 Wave 4 — settings drawer group wrapper (Plan 12-05 §3).
 *
 * A "group" is one labelled section inside the slide-over drawer
 * (PERSONA, OUTPUT, HOTKEY, RECORDING, CALIBRATION). Visually it's a
 * subdued panel: Workbench 9px UPPERCASE header strip + body with
 * `--sp-md` internal padding.
 *
 * It is NOT a full `vmx-panel` — the drawer is already a single panel
 * surface (the slide-over) and stacking another brushed-metal `::before`
 * inside it would look noisy. So this is a thinner wrapper that mirrors
 * the panel header glyphs without the metal streak.
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
    background: linear-gradient(180deg, var(--panel-lift) 0%, var(--panel) 100%);
    border: 1px solid var(--bezel-1);
    border-radius: 6px;
    overflow: hidden;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.03),
      inset 0 -1px 0 rgba(0, 0, 0, 0.4);
  }
  .vmx-settings-group__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-md);
    padding: var(--sp-sm) var(--sp-md);
    border-bottom: 1px dashed var(--bezel-2);
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    color: var(--ink);
    line-height: 1;
  }
  .vmx-settings-group__badge {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.32em;
    padding: 2px var(--sp-sm);
    border-radius: 2px;
    background: var(--phosphor-soft);
    color: var(--phosphor);
    line-height: 1;
  }
  .vmx-settings-group__body {
    padding: var(--sp-md);
    display: flex;
    flex-direction: column;
    gap: var(--sp-md);
  }
  .vmx-settings-group__footer {
    padding: var(--sp-sm) var(--sp-md);
    border-top: 1px dashed var(--bezel-2);
    background: var(--panel-deep);
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--rec);
    line-height: 1.3;
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
