/* rocker.ts — segmented rocker switch with two visual variants.
 *
 *   variant: "rocker"      — simple segmented (BEG / INT / PRO or HP / SPK).
 *   variant: "interaction" — LED-prefixed buttons (● HYPE / ● COACH).
 *
 * Lifted verbatim from mocks/vibemix-app-ui.html `.mode-rocker` (lines
 * 351-405) and `.interaction` (lines 408-438). Active position lit
 * --phosphor background with --phosphor-glow inset and --phosphor text;
 * inactive --panel-deep + --ink-dim. Rocker bezel uses inset shadow
 * to look pressed-in. Pure-function — accepts {options, active, onChange,
 * variant} and emits a click that fires onChange(optionId). */

import { registerStyle } from "./_style-registry.js";

export type RockerVariant = "rocker" | "interaction";

export interface RockerOption {
  id: string;
  label: string;
}

export interface RockerProps {
  options: RockerOption[];
  active: string;
  onChange?: (id: string) => void;
  variant?: RockerVariant;
  ariaLabel?: string;
}

const CSS = `
  .vmx-rocker {
    display: inline-flex;
    align-items: stretch;
    gap: 0;
    background: var(--panel-deep);
    border: 1px solid var(--bezel-2);
    border-radius: 6px;
    padding: 2px;
    box-shadow:
      inset 0 2px 4px rgba(0, 0, 0, 0.5),
      inset 0 -1px 0 rgba(255, 255, 255, 0.02);
    height: 32px;
    width: 100%;
  }
  .vmx-rocker__seg {
    flex: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 0 var(--sp-sm);
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    line-height: 1;
    border: none;
    border-radius: 4px;
    background: transparent;
    color: var(--ink-dim);
    cursor: pointer;
    transition: background var(--motion-snap) ease-out,
                color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  .vmx-rocker__seg:hover {
    color: var(--ink);
  }
  .vmx-rocker[data-variant="rocker"] .vmx-rocker__seg[data-active="true"] {
    background: var(--phosphor);
    color: var(--panel-deep);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.2),
      var(--phosphor-glow);
  }
  /* --- interaction variant — LED-prefixed --- */
  .vmx-rocker[data-variant="interaction"] .vmx-rocker__seg[data-active="true"] {
    background: var(--phosphor-soft);
    color: var(--phosphor);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.04),
      var(--phosphor-glow);
  }
  .vmx-rocker__led {
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ink-engraved);
    box-shadow: inset 0 0 1px rgba(0, 0, 0, 0.5);
  }
  .vmx-rocker__seg[data-active="true"] .vmx-rocker__led {
    background: var(--phosphor);
    box-shadow: var(--phosphor-glow);
  }
`;

registerStyle("vmx-rocker", CSS);

export function renderRocker(props: RockerProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-rocker";
  root.setAttribute("role", "radiogroup");
  if (props.ariaLabel) root.setAttribute("aria-label", props.ariaLabel);
  root.dataset.variant = props.variant ?? "rocker";

  for (const opt of props.options) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "vmx-rocker__seg";
    btn.dataset.id = opt.id;
    btn.dataset.active = opt.id === props.active ? "true" : "false";
    btn.setAttribute("role", "radio");
    btn.setAttribute("aria-checked", opt.id === props.active ? "true" : "false");

    if (props.variant === "interaction") {
      const led = document.createElement("span");
      led.className = "vmx-rocker__led";
      led.setAttribute("aria-hidden", "true");
      btn.append(led);
    }
    const lbl = document.createElement("span");
    lbl.textContent = opt.label;
    btn.append(lbl);

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      if (opt.id === props.active) return;
      props.onChange?.(opt.id);
    });
    root.append(btn);
  }

  return root;
}

/** Update active segment without rebuilding the rocker. */
export function setRockerActive(el: HTMLElement, id: string): void {
  el.querySelectorAll<HTMLElement>(".vmx-rocker__seg").forEach((seg) => {
    const isActive = seg.dataset.id === id;
    seg.dataset.active = isActive ? "true" : "false";
    seg.setAttribute("aria-checked", isActive ? "true" : "false");
  });
}
