/* dropdown-device.ts — Step 2 output device picker (UI-SPEC §5 / CDJ Whisper v5).
 *
 * Closed = 48px glass row: 24px square device-class glyph in --amber +
 * Saira body 14px weight 500 device name + amber AUTO pill + ▾ chevron.
 *
 * Open = dropdown panel below: --glass-2 + --blur-glass-light, 36px
 * option rows, hover linear-gradient(amber 0.09 → 0.025) background,
 * selected --amber text + faint amber glow. Max-height 240px scroll. */

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
    gap: var(--sp-4);
    height: 48px;
    padding: 0 var(--sp-4);
    background: var(--glass-3);
    backdrop-filter: var(--blur-glass-display);
    -webkit-backdrop-filter: var(--blur-glass-display);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.5), inset 0 1px 0 var(--glass-top);
    color: var(--silk);
    cursor: pointer;
    transition: border-color var(--motion-snap) ease-out, box-shadow var(--motion-snap) ease-out;
  }
  .cmp-dropdown-device__head:hover {
    border-color: var(--glass-edge-up);
  }
  .cmp-dropdown-device__head[aria-expanded="true"] {
    border-color: var(--amber-22);
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.5), inset 0 1px 0 var(--glass-top), 0 0 10px var(--amber-22);
  }
  .cmp-dropdown-device__glyph {
    color: var(--amber);
    display: flex;
    align-items: center;
    justify-content: center;
    filter: drop-shadow(0 0 3px var(--amber-22));
  }
  .cmp-dropdown-device__glyph svg {
    width: 24px;
    height: 24px;
  }
  .cmp-dropdown-device__name {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 500;
    font-size: 14px;
    color: var(--silk);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cmp-dropdown-device__pill {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    padding: 2px var(--sp-2);
    border-radius: var(--rad-sm);
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
    border: 1px solid var(--amber-22);
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
    line-height: 1;
  }
  .cmp-dropdown-device__chevron {
    font-family: var(--type-mono);
    font-size: 11px;
    color: var(--silk-65);
    padding-right: var(--sp-2);
    transition: transform var(--motion-snap) ease-out;
  }
  .cmp-dropdown-device__head[aria-expanded="true"] .cmp-dropdown-device__chevron {
    transform: rotate(180deg);
    color: var(--amber);
  }
  .cmp-dropdown-device__panel {
    position: absolute;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    z-index: 100;
    background: var(--glass-2);
    backdrop-filter: var(--blur-glass-light);
    -webkit-backdrop-filter: var(--blur-glass-light);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    padding: var(--sp-2) 0;
    max-height: 240px;
    overflow-y: auto;
    box-shadow:
      inset 0 1px 0 var(--glass-top),
      0 8px 24px rgba(0, 0, 0, 0.6);
  }
  .cmp-dropdown-device__panel[hidden] {
    display: none;
  }
  .cmp-dropdown-device__panel::-webkit-scrollbar {
    width: 6px;
  }
  .cmp-dropdown-device__panel::-webkit-scrollbar-track {
    background: var(--glass-3);
  }
  .cmp-dropdown-device__panel::-webkit-scrollbar-thumb {
    background: var(--silk-22);
    border-radius: 3px;
  }
  .cmp-dropdown-device__option {
    display: grid;
    grid-template-columns: 24px 1fr auto;
    align-items: center;
    gap: var(--sp-4);
    height: 36px;
    padding: 0 var(--sp-4);
    cursor: pointer;
    color: var(--silk);
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 14px;
    transition: background var(--motion-snap) ease-out, color var(--motion-snap) ease-out;
  }
  .cmp-dropdown-device__option:hover {
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
  }
  .cmp-dropdown-device__option[data-selected="true"] {
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
  }
  .cmp-dropdown-device__option .cmp-dropdown-device__glyph {
    color: var(--silk-65);
    filter: none;
  }
  .cmp-dropdown-device__option[data-selected="true"] .cmp-dropdown-device__glyph {
    color: var(--amber);
    filter: drop-shadow(0 0 3px var(--amber-22));
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
