/* button.ts — Primary CTA + Secondary button (UI-SPEC §3 + §4).
 *
 * Single module for both variants because they share the same shell;
 * only borders + colors differ. State enum lifted verbatim from UI-SPEC
 * §3 table (disabled / idle / armed / hover-armed / pressed-armed /
 * loading) — applied via data-state attribute so CSS owns every
 * transition.
 *
 * Min-width 144px, padding 12px 24px, Workbench 11px UPPERCASE 0.22em,
 * border-radius 4px, trailing `→` glyph in DM Mono per UI-SPEC.
 *
 * Anti-pattern guards:
 *   - No hover micro-effects beyond UI-SPEC §Motion Budget (150ms ease-out).
 *   - Loading state shows "WORKING…" verbatim from UI-SPEC §Universal
 *     Microcopy.
 *   - Focus ring is the global :focus-visible rule from tokens.css —
 *     never overridden per-component. */

import { registerStyle } from "./_style-registry.js";

export type ButtonVariant = "primary" | "secondary";

export type ButtonState =
  | "disabled"
  | "idle"
  | "armed"
  | "hover-armed"
  | "pressed-armed"
  | "loading";

export interface ButtonProps {
  variant: ButtonVariant;
  state: ButtonState;
  label: string;
  leadingGlyph?: string;
  trailingGlyph?: string;
  onClick?: () => void;
  /* "destructive" tints text in --rec for the Skip — generic mapping case
   * (UI-SPEC §10 / §4 secondary destructive variant). */
  destructive?: boolean;
}

const CSS = `
  .cmp-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--sp-sm);
    min-width: 144px;
    padding: 12px 24px;
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    line-height: 1;
    border-radius: 4px;
    border: 1px solid var(--bezel-2);
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    color: var(--ink-dim);
    transition: background var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }
  .cmp-btn .glyph-trail {
    font-family: "DM Mono", monospace;
    letter-spacing: 0;
  }
  .cmp-btn .glyph-lead {
    font-family: "DM Mono", monospace;
    letter-spacing: 0;
  }
  /* --- Primary states --- */
  .cmp-btn[data-variant="primary"][data-state="disabled"] {
    background: var(--panel-deep);
    border-color: var(--bezel-1);
    color: var(--ink-deep);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
    cursor: not-allowed;
  }
  .cmp-btn[data-variant="primary"][data-state="idle"] {
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    border-color: var(--bezel-2);
    color: var(--ink-dim);
  }
  .cmp-btn[data-variant="primary"][data-state="armed"] {
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    border-color: var(--phosphor-dim);
    color: var(--phosphor);
    box-shadow: var(--phosphor-glow), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  }
  .cmp-btn[data-variant="primary"][data-state="armed"]:hover,
  .cmp-btn[data-variant="primary"][data-state="hover-armed"] {
    background: linear-gradient(180deg, var(--panel-hover-top), var(--panel-lift));
    border-color: var(--phosphor);
    color: var(--phosphor);
    box-shadow: var(--phosphor-halo);
  }
  .cmp-btn[data-variant="primary"][data-state="armed"]:active,
  .cmp-btn[data-variant="primary"][data-state="pressed-armed"] {
    background: linear-gradient(180deg, var(--panel), var(--panel-pressed-bottom));
    border-color: var(--phosphor);
    color: var(--phosphor);
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.6);
  }
  .cmp-btn[data-variant="primary"][data-state="loading"] {
    border-color: var(--phosphor-dim);
    color: var(--phosphor);
    box-shadow: var(--phosphor-glow);
    cursor: progress;
  }
  /* --- Secondary states (border never lit; text only) --- */
  .cmp-btn[data-variant="secondary"] {
    border-color: var(--bezel-2);
    background: linear-gradient(180deg, var(--panel-lift), var(--panel));
    color: var(--ink);
  }
  .cmp-btn[data-variant="secondary"]:hover {
    border-color: var(--phosphor-dim);
    color: var(--phosphor);
  }
  .cmp-btn[data-variant="secondary"][data-state="disabled"] {
    color: var(--ink-deep);
    border-color: var(--bezel-1);
    cursor: not-allowed;
  }
  .cmp-btn[data-variant="secondary"][data-state="armed"] {
    border-color: var(--phosphor-dim);
    color: var(--phosphor);
    box-shadow: var(--phosphor-glow);
  }
  .cmp-btn[data-variant="secondary"][data-destructive="true"] {
    color: var(--rec);
  }
  .cmp-btn[data-variant="secondary"][data-destructive="true"]:hover {
    border-color: var(--rec);
    color: var(--rec);
  }
  /* --- Loading spinner --- */
  .cmp-btn .spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 1.5px solid var(--phosphor-dim);
    border-top-color: var(--phosphor);
    border-radius: 50%;
    animation: cmp-btn-spin 800ms linear infinite;
  }
  @keyframes cmp-btn-spin {
    to { transform: rotate(360deg); }
  }
`;

registerStyle("cmp-btn", CSS);

export function Button(props: ButtonProps): HTMLButtonElement {
  const el = document.createElement("button");
  el.type = "button";
  el.className = "cmp-btn";
  el.dataset.variant = props.variant;
  el.dataset.state = props.state;
  if (props.destructive) el.dataset.destructive = "true";
  setButtonContent(el, props);
  el.disabled = props.state === "disabled" || props.state === "loading";
  if (props.onClick) {
    el.addEventListener("click", (e) => {
      if (el.disabled) return;
      e.preventDefault();
      props.onClick?.();
    });
  }
  return el;
}

export function setButtonState(el: HTMLButtonElement, state: ButtonState): void {
  el.dataset.state = state;
  el.disabled = state === "disabled" || state === "loading";
}

export function setButtonLabel(el: HTMLButtonElement, label: string): void {
  const labelEl = el.querySelector<HTMLSpanElement>(".btn-label");
  if (labelEl) labelEl.textContent = label;
}

function setButtonContent(el: HTMLButtonElement, props: ButtonProps): void {
  el.innerHTML = "";
  if (props.state === "loading") {
    const spin = document.createElement("span");
    spin.className = "spinner";
    spin.setAttribute("aria-hidden", "true");
    const label = document.createElement("span");
    label.className = "btn-label";
    label.textContent = "WORKING…";
    el.append(spin, label);
    return;
  }
  if (props.leadingGlyph) {
    const lead = document.createElement("span");
    lead.className = "glyph-lead";
    lead.textContent = props.leadingGlyph;
    lead.setAttribute("aria-hidden", "true");
    el.append(lead);
  }
  const label = document.createElement("span");
  label.className = "btn-label";
  label.textContent = props.label;
  el.append(label);
  if (props.trailingGlyph) {
    const trail = document.createElement("span");
    trail.className = "glyph-trail";
    trail.textContent = props.trailingGlyph;
    trail.setAttribute("aria-hidden", "true");
    el.append(trail);
  }
}
