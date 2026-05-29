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
  /** Stable mock-transfer / integration anchor. Defaults to settings.group.<header>. */
  wireId?: string;
  /** Optional UPPER-pill on the right of the header (e.g. "CFG"). */
  badge?: string;
  /** Optional footer slot (e.g. inline error message). */
  footer?: HTMLElement | null;
}

const CSS = `
  /* "The Deck Speaks" rebuild (2026-05-26): the drawer is ALREADY one glass
   * surface, so a group is no longer a glass card stacked inside it (the old
   * --glass-2 face + drop-shadow + recessed --glass-3 body read as cards-in-a-
   * card). A group is now a hairline-divided SECTION on the drawer's void: a
   * quiet silk label, then its controls, separated from the next section by a
   * single 1px rule. No card fill, no drop shadow — rows on hairlines. */
  .vmx-settings-group {
    position: relative;
    border-top: 1px solid rgba(214, 207, 199, 0.060);
  }
  .vmx-settings-group:first-child {
    border-top: 0;
  }
  .vmx-settings-group__header {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    padding: 22px var(--sp-4) 12px;
    font-family: var(--type-body);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10.5px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: rgba(214, 207, 199, 0.72);
    line-height: 1;
  }
  .vmx-settings-group__header::after {
    content: "";
    position: absolute;
    left: var(--sp-4);
    right: var(--sp-4);
    bottom: 0;
    height: 1px;
    background: linear-gradient(90deg, rgba(214, 207, 199, 0.16), transparent 42%);
    opacity: 0.18;
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
    padding: 0 var(--sp-4) 24px;
    display: flex;
    flex-direction: column;
    gap: var(--sp-4);
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

  /* P1-b finding #2 — two-stage mechanical slide-in: STAGE 2 (the settle).
   * Stage 1 is the drawer body's 250ms translateX (owned by SettingsDrawer
   * .vmx-settings-drawer). When the drawer lands, each group row does a short
   * ~120ms micro-settle (10px up → seat) on a per-group stagger so the tray
   * reads as sliding in THEN seating into place — a mechanical drawer, not a
   * single CSS slide. The trigger is data-settling="true", set on the drawer
   * ONLY by openSettings() and cleared after the run, so mid-session body
   * rebuilds (genre reload, recordings refresh) do NOT replay it.
   *
   * Stage-2 delays START at ~250ms (after stage 1 has landed) and step by
   * 28ms per group. GPU-cheap (transform + opacity only).
   *
   * prefers-reduced-motion GATE: the settle (and its stagger) is wrapped in
   * the no-preference media query, so reduced-motion users get the seated end
   * state with no transform at all. */
  @media (prefers-reduced-motion: no-preference) {
    @keyframes vmx-group-settle {
      from { transform: translateY(10px); opacity: 0; }
      to   { transform: translateY(0);    opacity: 1; }
    }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group {
      animation: vmx-group-settle 120ms ease-out both;
    }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(1) { animation-delay: 250ms; }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(2) { animation-delay: 278ms; }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(3) { animation-delay: 306ms; }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(4) { animation-delay: 334ms; }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(5) { animation-delay: 362ms; }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(6) { animation-delay: 390ms; }
    .vmx-settings-drawer[data-settling="true"] .vmx-settings-group:nth-child(n+7) { animation-delay: 418ms; }
  }
`;

registerStyle("vmx-settings-group", CSS);

function groupWireId(header: string): string {
  const slug = header
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `settings.group.${slug || "section"}`;
}

export function renderSettingsGroup(props: SettingsGroupProps): HTMLElement {
  const root = document.createElement("section");
  root.className = "vmx-settings-group";
  root.dataset.wire = props.wireId ?? groupWireId(props.header);

  const head = document.createElement("div");
  head.className = "vmx-settings-group__header";
  head.dataset.wire = `${root.dataset.wire}.header`;
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
  body.dataset.wire = `${root.dataset.wire}.body`;
  const kids = Array.isArray(props.children) ? props.children : [props.children];
  for (const k of kids) body.append(k);
  root.append(body);

  if (props.footer) {
    const footer = document.createElement("div");
    footer.className = "vmx-settings-group__footer";
    footer.dataset.wire = `${root.dataset.wire}.footer`;
    footer.append(props.footer);
    root.append(footer);
  }

  return root;
}
