/* mascot-corner.ts — empty placeholder reserving Phase 13's 256×256 slot
 * (UI-SPEC §Mascot Reserved Corner + RESEARCH Pitfall 9).
 *
 * CRITICAL: NO placeholder character art. NO stock illustration. NO size
 * reduction. Just the dashed --ink-engraved outline + centered Workbench
 * 9px label "AVERY · arriving phase 13" in --ink-deep.
 *
 * Filling this rect in any Phase 11 plan/wave is a Pitfall 9 violation
 * — the UI-checker auto-rejects it (Phase 14 polish loop). */

import { registerStyle } from "./_style-registry.js";

export type MascotCornerProps = Record<string, never>;

const CSS = `
  .cmp-mascot-corner {
    width: var(--col-mascot);
    height: var(--col-mascot);
    border: 1px dashed var(--ink-engraved);
    border-radius: 6px;
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    user-select: none;
  }
  .cmp-mascot-corner__label {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    color: var(--ink-deep);
    line-height: 1.5;
  }
`;

registerStyle("cmp-mascot-corner", CSS);

export function MascotCorner(_props: MascotCornerProps = {}): HTMLElement {
  const root = document.createElement("aside");
  root.className = "cmp-mascot-corner";
  root.setAttribute("aria-hidden", "true");
  const label = document.createElement("span");
  label.className = "cmp-mascot-corner__label";
  // UI-SPEC §Mascot Reserved Corner — VERBATIM
  label.textContent = "AVERY · arriving phase 13";
  root.append(label);
  return root;
}
