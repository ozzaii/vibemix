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
    gap: var(--sp-3);
    min-width: 144px;
    padding: 12px 22px;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    line-height: 1;
    border-radius: var(--rad-sm);
    border: 1px solid var(--glass-edge);
    background: var(--glass-2);
    backdrop-filter: var(--blur-glass-display);
    -webkit-backdrop-filter: var(--blur-glass-display);
    color: var(--silk-65);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.035),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45);
    transition: background var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                color var(--motion-snap) ease-out,
                text-shadow var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  .cmp-btn .glyph-trail,
  .cmp-btn .glyph-lead {
    font-family: var(--type-mono);
    letter-spacing: 0;
    font-size: 12px;
  }
  /* --- Primary states --- */
  .cmp-btn[data-variant="primary"][data-state="disabled"] {
    background: rgba(0, 0, 0, 0.4);
    border-color: rgba(255, 255, 255, 0.03);
    color: var(--silk-22);
    text-shadow: none;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.018);
    cursor: not-allowed;
  }
  .cmp-btn[data-variant="primary"][data-state="idle"] {
    background: var(--glass-2);
    border-color: var(--glass-edge);
    color: var(--silk-65);
  }
  .cmp-btn[data-variant="primary"][data-state="idle"]:hover {
    color: var(--silk);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45),
      0 0 10px var(--amber-22);
  }
  /* Armed — internal amber bleed (mock §02 .btn.on) */
  .cmp-btn[data-variant="primary"][data-state="armed"] {
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
    border-color: rgba(255, 138, 61, 0.14);
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-65);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 var(--amber-40),
      inset 0 0 14px var(--amber-22),
      0 0 0 1px rgba(255, 138, 61, 0.14);
  }
  .cmp-btn[data-variant="primary"][data-state="armed"]:hover,
  .cmp-btn[data-variant="primary"][data-state="hover-armed"] {
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.14) 0%, rgba(255, 138, 61, 0.04) 100%);
    border-color: var(--amber);
    color: var(--amber);
    text-shadow: 0 0 6px var(--amber-65), 0 0 14px var(--amber-22);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.08),
      inset 0 -1px 0 var(--amber-65),
      inset 0 0 18px var(--amber-40),
      0 0 0 1px rgba(255, 138, 61, 0.22);
  }
  .cmp-btn[data-variant="primary"][data-state="armed"]:active,
  .cmp-btn[data-variant="primary"][data-state="pressed-armed"] {
    background: var(--void-2);
    border-color: var(--amber-40);
    color: var(--amber);
    text-shadow: 0 0 3px var(--amber-22);
    box-shadow:
      inset 0 2px 6px rgba(0, 0, 0, 0.85),
      inset 0 0 0 1px rgba(0, 0, 0, 0.45),
      inset 0 0 14px var(--amber-22);
  }
  .cmp-btn[data-variant="primary"][data-state="loading"] {
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.06) 0%, rgba(255, 138, 61, 0.018) 100%);
    border-color: var(--amber-22);
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.04),
      inset 0 0 12px var(--amber-22);
    cursor: progress;
  }
  /* --- Secondary states (text-only emphasis; never amber-bleed body) --- */
  .cmp-btn[data-variant="secondary"] {
    border-color: var(--glass-edge);
    background: var(--glass-2);
    color: var(--silk-65);
  }
  .cmp-btn[data-variant="secondary"]:hover {
    color: var(--silk);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45),
      0 0 8px var(--amber-22);
  }
  .cmp-btn[data-variant="secondary"][data-state="disabled"] {
    color: var(--silk-22);
    border-color: rgba(255, 255, 255, 0.03);
    background: rgba(0, 0, 0, 0.4);
    text-shadow: none;
    cursor: not-allowed;
  }
  .cmp-btn[data-variant="secondary"][data-state="armed"] {
    border-color: var(--amber-22);
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 0 10px var(--amber-22);
  }
  /* Destructive secondary — fault-toned hairline + text, no body fill */
  .cmp-btn[data-variant="secondary"][data-destructive="true"] {
    color: var(--led-fault);
    text-shadow: 0 0 4px rgba(212, 65, 58, 0.18);
  }
  .cmp-btn[data-variant="secondary"][data-destructive="true"]:hover {
    color: var(--led-fault);
    border-color: rgba(212, 65, 58, 0.35);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45),
      0 0 8px rgba(212, 65, 58, 0.22);
  }
  /* --- Loading spinner — amber ring matching v5 tactility --- */
  .cmp-btn .spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 1.5px solid var(--amber-22);
    border-top-color: var(--amber);
    border-radius: 50%;
    animation: cmp-btn-spin 800ms linear infinite;
    filter: drop-shadow(0 0 3px var(--amber-22));
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
