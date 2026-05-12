/* step-indicator.ts — 3-node strip across top of wizard (UI-SPEC §1).
 *
 * Pending = ring --bezel-2, fill --panel-deep.
 * Active  = ring --phosphor, fill --phosphor-soft, --phosphor-glow,
 *           1.4s ease-in-out infinite pulse.
 * Complete = ring --ok, fill --ok, white ✓ inside.
 *
 * Connector between complete-complete = solid --phosphor.
 * Between pending-pending = dashed --bezel-2.
 *
 * Labels: Workbench 11px UPPERCASE 0.22em.
 *   - Active label = --phosphor
 *   - Pending = --ink-dim
 *   - Complete = --ok
 */

import { registerStyle } from "./_style-registry.js";

export type StepState = "pending" | "active" | "complete";

export interface StepIndicatorStep {
  id: string;
  label: string;
  state: StepState;
}

export interface StepIndicatorProps {
  steps: StepIndicatorStep[];
}

const CSS = `
  .cmp-step-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    height: var(--stepstrip-h);
    width: 100%;
  }
  .cmp-step-indicator__node-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--sp-xs);
  }
  .cmp-step-indicator__node {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 1.5px solid var(--bezel-2);
    background: var(--panel-deep);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: border-color var(--motion-transition) ease-in-out,
                background var(--motion-transition) ease-in-out,
                box-shadow var(--motion-transition) ease-in-out;
  }
  .cmp-step-indicator__node[data-state="active"] {
    border-color: var(--phosphor);
    background: var(--phosphor-soft);
    box-shadow: var(--phosphor-glow);
    animation: cmp-step-pulse var(--motion-led-pulse) ease-in-out infinite;
  }
  .cmp-step-indicator__node[data-state="complete"] {
    border-color: var(--ok);
    background: var(--ok);
  }
  .cmp-step-indicator__node[data-state="complete"]::after {
    content: "✓";
    color: var(--panel-deep);
    font-size: 9px;
    font-weight: 700;
    line-height: 1;
  }
  .cmp-step-indicator__label {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    line-height: 1;
    color: var(--ink-dim);
    transition: color var(--motion-transition) ease-in-out;
  }
  .cmp-step-indicator__node[data-state="active"] ~ .cmp-step-indicator__label,
  .cmp-step-indicator__node-wrap[data-state="active"] .cmp-step-indicator__label {
    color: var(--phosphor);
  }
  .cmp-step-indicator__node-wrap[data-state="complete"] .cmp-step-indicator__label {
    color: var(--ok);
  }
  .cmp-step-indicator__connector {
    flex: 0 0 64px;
    height: 1px;
    margin: 0 var(--sp-md);
    margin-bottom: 18px;  /* align with circle vertical center, not labels */
    border-top: 1px dashed var(--bezel-2);
    transition: border-top-color var(--motion-transition) ease-in-out,
                border-top-style var(--motion-transition) ease-in-out;
  }
  .cmp-step-indicator__connector[data-active="true"] {
    border-top: 1px solid var(--phosphor);
  }
  @keyframes cmp-step-pulse {
    0%, 100% { box-shadow: var(--phosphor-glow); }
    50%      { box-shadow: var(--phosphor-halo); }
  }
`;

registerStyle("cmp-step-indicator", CSS);

export function StepIndicator(props: StepIndicatorProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-step-indicator";
  root.setAttribute("role", "navigation");
  root.setAttribute("aria-label", "wizard progress");

  props.steps.forEach((step, i) => {
    if (i > 0) {
      const conn = document.createElement("div");
      conn.className = "cmp-step-indicator__connector";
      const prev = props.steps[i - 1];
      const here = step;
      // Connector "active" = both adjacent nodes complete, OR previous complete + here active
      const active = prev?.state === "complete" && (here.state === "complete" || here.state === "active");
      if (active) conn.dataset.active = "true";
      root.append(conn);
    }
    const wrap = document.createElement("div");
    wrap.className = "cmp-step-indicator__node-wrap";
    wrap.dataset.state = step.state;
    wrap.dataset.stepId = step.id;
    const node = document.createElement("div");
    node.className = "cmp-step-indicator__node";
    node.dataset.state = step.state;
    const label = document.createElement("div");
    label.className = "cmp-step-indicator__label";
    label.textContent = step.label;
    wrap.append(node, label);
    root.append(wrap);
  });
  return root;
}

export function setStepState(
  stripEl: HTMLElement,
  stepId: string,
  state: StepState
): void {
  const wrap = stripEl.querySelector<HTMLElement>(`[data-step-id="${stepId}"]`);
  if (!wrap) return;
  wrap.dataset.state = state;
  const node = wrap.querySelector<HTMLElement>(".cmp-step-indicator__node");
  if (node) node.dataset.state = state;
}
