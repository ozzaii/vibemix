/* rocker.ts — segmented rocker switch with two visual variants.
 *
 *   variant: "rocker"      — simple segmented (BEG / INT / PRO or HP / SPK).
 *   variant: "interaction" — mood block buttons (HYPE / TEACH / COACH).
 *
 * v5 CDJ Whisper: active segment lit with the canonical amber-bleed-
 * through-frost recipe (--amber gradient + --amber-22 inset glow +
 * --amber-40 hairline + --amber text with --glow-soft text-shadow);
 * inactive sits flat on --glass-3 + --silk-40. Rocker bezel uses inset
 * shadow to look pressed-in. Pure-function — accepts {options, active,
 * onChange, variant} and emits a click that fires onChange(optionId). */

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

/* VIS-02 (43-02): --glow-faint on hover/focus-visible per CONTEXT. The
 * rocker segments are the primary interactive control in the persona
 * panel (BEG/INT/PRO + HYPE/TEACH/COACH); closes session-audit finding
 * H-01 by adding `box-shadow: var(--glow-faint)` to the :hover state
 * and mirroring on :focus-visible for keyboard parity (WCAG 2.1). */
const CSS = `
  .vmx-rocker {
    display: inline-flex;
    align-items: stretch;
    gap: 0;
    background: var(--glass-3);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    padding: 3px;
    box-shadow:
      inset 0 2px 5px rgba(0, 0, 0, 0.85),
      inset 0 0 0 1px rgba(0, 0, 0, 0.5),
      inset 0 -1px 0 rgba(255, 255, 255, 0.028);
    height: 32px;
    width: 100%;
  }
  .vmx-rocker__seg {
    flex: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 0 var(--sp-2);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.20em;
    text-transform: uppercase;
    line-height: 1;
    border: none;
    border-radius: var(--rad-sm);
    background: transparent;
    color: var(--silk-40);
    cursor: pointer;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    transition: background var(--motion-snap) ease-out,
                color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                text-shadow var(--motion-snap) ease-out;
  }
  /* VIS-02 hover/focus glow — colour lift + faint amber halo so the
   * affordance survives against the silk-22 frame (closes H-01). The
   * :focus-visible branch mirrors :hover for keyboard reachability. */
  .vmx-rocker__seg:hover,
  .vmx-rocker__seg:focus-visible {
    color: var(--silk);
    box-shadow: var(--glow-faint);
  }
  /* The body-level *:focus-visible already paints a 2px amber outline +
   * --glow-soft so we explicitly suppress the duplicate ring on the
   * segment (its glow comes from the rule above). */
  .vmx-rocker__seg:focus-visible { outline: none; }
  /* --- rocker variant — solid amber tile when active (used for BEG/INT/PRO etc.) --- */
  .vmx-rocker[data-variant="rocker"] .vmx-rocker__seg[data-active="true"] {
    color: var(--amber);
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.12) 0%, rgba(255, 138, 61, 0.035) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 var(--amber-40),
      inset 0 0 14px var(--amber-22),
      0 0 0 1px rgba(255, 138, 61, 0.18);
    text-shadow: 0 0 4px var(--amber-65);
  }
  /* --- interaction variant — mood block (HYPE / TEACH / COACH).
   * Same amber-bleed-through-frost active state. The LED ornament from
   * the prior FL-Studio variant is dropped; v5 says concentrated amber
   * on the active tile is enough — no extra dot competing. --- */
  .vmx-rocker[data-variant="interaction"] .vmx-rocker__seg[data-active="true"] {
    color: var(--amber);
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 var(--amber-40),
      inset 0 0 14px var(--amber-22),
      0 0 0 1px rgba(255, 138, 61, 0.14);
    text-shadow: 0 0 4px var(--amber-65);
  }
  /* Legacy LED prefix kept rendering for backward-compat with the
   * existing renderRocker(variant="interaction") signature, but visually
   * suppressed — v5 mood-block uses concentrated text-glow, not a
   * separate LED ornament. */
  .vmx-rocker__led { display: none; }
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
