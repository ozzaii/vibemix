/* picker.ts — dropdown row component (48px row, 240px dropdown).
 *
 * Used by voice picker, genre picker, output device picker. Lifted from
 * mocks/vibemix-app-ui.html `.persona-cell` (lines 442-477).
 *
 * Layout: [icon|avatar 24×24] [label DM Mono 14px wt 500] [auto-pill?] [▾]
 * Click opens an absolutely-positioned 240px panel beneath with options
 * listed at 32px row height, hover --phosphor-soft tint. */

import { registerStyle } from "./_style-registry.js";

export interface PickerOption {
  id: string;
  label: string;
  sub?: string | null;
}

export interface PickerProps {
  label: string;
  value: string;
  options: PickerOption[];
  /** Inline SVG markup for the leading 24×24 icon (e.g. headphones). */
  iconSvg?: string;
  /** Optional avatar (radial-gradient circle) instead of icon — voice picker. */
  avatar?: boolean;
  /** Show the "AUTO" pill when the value is auto-selected by the sidecar. */
  autoPill?: boolean;
  onChange?: (id: string) => void;
}

const CSS = `
  .vmx-picker {
    position: relative;
    width: 100%;
  }
  .vmx-picker__row {
    display: flex;
    align-items: center;
    gap: var(--sp-sm);
    height: 48px;
    padding: 0 var(--sp-md);
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    border: 1px solid var(--bezel-1);
    border-radius: 6px;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.04),
      inset 0 -1px 0 rgba(0, 0, 0, 0.3);
    cursor: pointer;
    transition: border-color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  .vmx-picker__row:hover,
  .vmx-picker[data-open="true"] .vmx-picker__row {
    border-color: var(--phosphor-dim);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.04),
      var(--phosphor-glow);
  }
  .vmx-picker__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    color: var(--phosphor);
    flex-shrink: 0;
  }
  .vmx-picker__avatar {
    width: 24px;
    height: 24px;
    flex-shrink: 0;
    border-radius: 50%;
    background: radial-gradient(circle at 50% 35%, var(--bezel-3), var(--panel) 70%, var(--panel-deep));
    border: 1px solid var(--bezel-3);
    box-shadow: inset 0 -1px 2px rgba(0, 0, 0, 0.5);
  }
  .vmx-picker__label {
    flex: 1;
    min-width: 0;
    font-family: "DM Mono", monospace;
    font-size: 14px;
    font-weight: 500;
    color: var(--ink);
    letter-spacing: 0.01em;
    line-height: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .vmx-picker__auto {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    padding: 2px 6px;
    border-radius: 2px;
    background: var(--phosphor-soft);
    color: var(--phosphor);
    line-height: 1;
  }
  .vmx-picker__chev {
    color: var(--ink-dim);
    font-size: 14px;
    line-height: 1;
    transition: color var(--motion-snap) ease-out,
                transform var(--motion-snap) ease-out;
  }
  .vmx-picker[data-open="true"] .vmx-picker__chev {
    color: var(--phosphor);
    transform: rotate(180deg);
  }
  .vmx-picker__list {
    position: absolute;
    left: 0;
    top: calc(100% + 4px);
    z-index: 30;
    width: 240px;
    max-height: 280px;
    overflow: auto;
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    border: 1px solid var(--bezel-2);
    border-radius: 6px;
    box-shadow:
      0 8px 16px rgba(0, 0, 0, 0.5),
      inset 0 1px 0 rgba(255, 255, 255, 0.04);
    padding: 4px;
    opacity: 0;
    transform: translateY(-4px);
    pointer-events: none;
    transition: opacity var(--motion-transition) ease-out,
                transform var(--motion-transition) ease-out;
  }
  .vmx-picker[data-open="true"] .vmx-picker__list {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
  }
  .vmx-picker__opt {
    display: flex;
    align-items: center;
    gap: var(--sp-sm);
    width: 100%;
    padding: 0 var(--sp-md);
    height: 32px;
    border: none;
    background: transparent;
    color: var(--ink);
    font-family: "DM Mono", monospace;
    font-size: 13px;
    letter-spacing: 0.01em;
    line-height: 1;
    text-align: left;
    cursor: pointer;
    border-radius: 4px;
  }
  .vmx-picker__opt:hover {
    background: var(--phosphor-soft);
    color: var(--phosphor);
  }
  .vmx-picker__opt[data-selected="true"] {
    color: var(--phosphor);
  }
  .vmx-picker__opt-sub {
    margin-left: auto;
    font-size: 11px;
    color: var(--ink-dim);
  }
`;

registerStyle("vmx-picker", CSS);

export function renderPicker(props: PickerProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "vmx-picker";
  root.dataset.open = "false";
  root.setAttribute("aria-label", props.label);

  const row = document.createElement("button");
  row.type = "button";
  row.className = "vmx-picker__row";
  row.setAttribute("aria-haspopup", "listbox");
  row.setAttribute("aria-expanded", "false");

  if (props.avatar) {
    const av = document.createElement("span");
    av.className = "vmx-picker__avatar";
    av.setAttribute("aria-hidden", "true");
    row.append(av);
  } else if (props.iconSvg) {
    const ic = document.createElement("span");
    ic.className = "vmx-picker__icon";
    ic.innerHTML = props.iconSvg;
    row.append(ic);
  }

  const lbl = document.createElement("span");
  lbl.className = "vmx-picker__label";
  lbl.textContent = props.value;
  row.append(lbl);

  if (props.autoPill) {
    const pill = document.createElement("span");
    pill.className = "vmx-picker__auto";
    pill.textContent = "AUTO";
    row.append(pill);
  }

  const chev = document.createElement("span");
  chev.className = "vmx-picker__chev";
  chev.textContent = "▾";
  chev.setAttribute("aria-hidden", "true");
  row.append(chev);

  root.append(row);

  const list = document.createElement("div");
  list.className = "vmx-picker__list";
  list.setAttribute("role", "listbox");
  for (const opt of props.options) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "vmx-picker__opt";
    btn.dataset.id = opt.id;
    btn.dataset.selected = opt.label === props.value ? "true" : "false";
    btn.setAttribute("role", "option");
    btn.setAttribute("aria-selected", opt.label === props.value ? "true" : "false");
    const t = document.createElement("span");
    t.textContent = opt.label;
    btn.append(t);
    if (opt.sub) {
      const sub = document.createElement("span");
      sub.className = "vmx-picker__opt-sub";
      sub.textContent = opt.sub;
      btn.append(sub);
    }
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      closeList();
      props.onChange?.(opt.id);
    });
    list.append(btn);
  }
  root.append(list);

  function openList(): void {
    root.dataset.open = "true";
    row.setAttribute("aria-expanded", "true");
  }
  function closeList(): void {
    root.dataset.open = "false";
    row.setAttribute("aria-expanded", "false");
  }

  row.addEventListener("click", (e) => {
    e.preventDefault();
    if (root.dataset.open === "true") closeList();
    else openList();
  });

  // Close on outside click — registered once per picker. Phase 12-04 may
  // promote this to a single document-level listener if drawer perf demands it.
  document.addEventListener("click", (e) => {
    if (root.dataset.open !== "true") return;
    if (!(e.target instanceof Node) || !root.contains(e.target)) {
      closeList();
    }
  });

  return root;
}
