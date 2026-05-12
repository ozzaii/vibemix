/* dropdown-device.ts — Step 2 output device picker (UI-SPEC §5).
 *
 * Closed = 48px row: 24px square device-class glyph in --phosphor +
 * DM Mono 14px weight 500 device name + AUTO pill + ▾ chevron.
 *
 * Open = dropdown panel below: --panel-lift gradient, 36px option rows,
 * hover --phosphor-soft background, selected --phosphor text +
 * --phosphor-glow. Max-height 240px scroll. */

import { registerStyle } from "./_style-registry.js";
import { HEADPHONES_SVG } from "../icons/headphones.svg.js";
import { SPEAKER_SVG } from "../icons/speaker.svg.js";

export interface DropdownDevice {
  id: string;
  name: string;
  isHeadphones?: boolean;
  isSpeaker?: boolean;
  isAuto?: boolean;
}

export interface DropdownDeviceProps {
  devices: DropdownDevice[];
  selectedId?: string;
  onSelect: (id: string) => void;
}

const CSS = `
  .cmp-dropdown-device {
    position: relative;
    width: 100%;
  }
  .cmp-dropdown-device__head {
    display: grid;
    grid-template-columns: 24px 1fr auto auto;
    align-items: center;
    gap: var(--sp-md);
    height: 48px;
    padding: 0 var(--sp-md);
    background: var(--panel-deep);
    border: 1px solid var(--bezel-1);
    border-radius: 5px;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.5);
    color: var(--ink);
    cursor: pointer;
    transition: border-color var(--motion-snap) ease-out;
  }
  .cmp-dropdown-device__head:hover {
    border-color: var(--bezel-2);
  }
  .cmp-dropdown-device__head[aria-expanded="true"] {
    border-color: var(--phosphor-dim);
  }
  .cmp-dropdown-device__glyph {
    color: var(--phosphor);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .cmp-dropdown-device__glyph svg {
    width: 24px;
    height: 24px;
  }
  .cmp-dropdown-device__name {
    font-family: "DM Mono", monospace;
    font-weight: 500;
    font-size: 14px;
    color: var(--ink);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cmp-dropdown-device__pill {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    padding: 2px var(--sp-sm);
    border-radius: 3px;
    background: var(--phosphor-soft);
    color: var(--phosphor);
    line-height: 1;
  }
  .cmp-dropdown-device__chevron {
    font-family: "DM Mono", monospace;
    font-size: 11px;
    color: var(--ink-dim);
    padding-right: var(--sp-sm);
    transition: transform var(--motion-snap) ease-out;
  }
  .cmp-dropdown-device__head[aria-expanded="true"] .cmp-dropdown-device__chevron {
    transform: rotate(180deg);
  }
  .cmp-dropdown-device__panel {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    z-index: 100;
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    border: 1px solid var(--bezel-1);
    border-radius: 5px;
    padding: var(--sp-sm) 0;
    max-height: 240px;
    overflow-y: auto;
    box-shadow: 0 8px 24px -8px rgba(0, 0, 0, 0.6);
  }
  .cmp-dropdown-device__panel[hidden] {
    display: none;
  }
  .cmp-dropdown-device__panel::-webkit-scrollbar {
    width: 6px;
  }
  .cmp-dropdown-device__panel::-webkit-scrollbar-track {
    background: var(--panel-deep);
  }
  .cmp-dropdown-device__panel::-webkit-scrollbar-thumb {
    background: var(--bezel-2);
    border-radius: 3px;
  }
  .cmp-dropdown-device__option {
    display: grid;
    grid-template-columns: 24px 1fr auto;
    align-items: center;
    gap: var(--sp-md);
    height: 36px;
    padding: 0 var(--sp-md);
    cursor: pointer;
    color: var(--ink);
    font-family: "DM Mono", monospace;
    font-size: 14px;
    transition: background var(--motion-snap) ease-out, color var(--motion-snap) ease-out;
  }
  .cmp-dropdown-device__option:hover {
    background: var(--phosphor-soft);
  }
  .cmp-dropdown-device__option[data-selected="true"] {
    color: var(--phosphor);
    text-shadow: var(--phosphor-glow);
  }
  .cmp-dropdown-device__option .cmp-dropdown-device__glyph {
    color: var(--ink-dim);
  }
  .cmp-dropdown-device__option[data-selected="true"] .cmp-dropdown-device__glyph {
    color: var(--phosphor);
  }
`;

registerStyle("cmp-dropdown-device", CSS);

function glyphFor(d: DropdownDevice): string {
  if (d.isHeadphones) return HEADPHONES_SVG;
  if (d.isSpeaker) return SPEAKER_SVG;
  return HEADPHONES_SVG; // default for unknown class
}

export function DropdownDevice(props: DropdownDeviceProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-dropdown-device";

  let selectedId = props.selectedId ?? props.devices[0]?.id ?? "";
  const head = document.createElement("button");
  head.type = "button";
  head.className = "cmp-dropdown-device__head";
  head.setAttribute("aria-expanded", "false");
  head.setAttribute("aria-haspopup", "listbox");

  const glyph = document.createElement("span");
  glyph.className = "cmp-dropdown-device__glyph";
  const name = document.createElement("span");
  name.className = "cmp-dropdown-device__name";
  const pill = document.createElement("span");
  pill.className = "cmp-dropdown-device__pill";
  // UI-SPEC §Step 2 — VERBATIM
  pill.textContent = "AUTO";
  pill.hidden = true;
  const chev = document.createElement("span");
  chev.className = "cmp-dropdown-device__chevron";
  chev.setAttribute("aria-hidden", "true");
  chev.textContent = "▾";
  head.append(glyph, name, pill, chev);

  const panel = document.createElement("div");
  panel.className = "cmp-dropdown-device__panel";
  panel.setAttribute("role", "listbox");
  panel.hidden = true;

  function refreshHead() {
    const sel = props.devices.find((d) => d.id === selectedId) ?? props.devices[0];
    if (!sel) {
      name.textContent = "(no devices)";
      glyph.innerHTML = "";
      pill.hidden = true;
      return;
    }
    name.textContent = sel.name;
    glyph.innerHTML = glyphFor(sel);
    pill.hidden = !sel.isAuto;
  }

  function refreshPanel() {
    panel.innerHTML = "";
    props.devices.forEach((d) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "cmp-dropdown-device__option";
      row.setAttribute("role", "option");
      row.dataset.id = d.id;
      if (d.id === selectedId) row.dataset.selected = "true";
      const g = document.createElement("span");
      g.className = "cmp-dropdown-device__glyph";
      g.innerHTML = glyphFor(d);
      const n = document.createElement("span");
      n.textContent = d.name;
      const tag = document.createElement("span");
      if (d.isAuto) {
        tag.className = "cmp-dropdown-device__pill";
        tag.textContent = "AUTO";
      }
      row.append(g, n, tag);
      row.addEventListener("click", () => {
        selectedId = d.id;
        refreshHead();
        panel.hidden = true;
        head.setAttribute("aria-expanded", "false");
        props.onSelect(d.id);
      });
      panel.append(row);
    });
  }

  head.addEventListener("click", () => {
    const open = panel.hidden;
    panel.hidden = !open;
    head.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) refreshPanel();
  });

  // Click outside to close
  document.addEventListener("click", (e) => {
    if (!root.contains(e.target as Node)) {
      panel.hidden = true;
      head.setAttribute("aria-expanded", "false");
    }
  });

  refreshHead();
  root.append(head, panel);
  return root;
}
