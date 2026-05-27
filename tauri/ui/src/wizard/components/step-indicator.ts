/* step-indicator.ts — 3-node strip across top of wizard (UI-SPEC §1 / CDJ Whisper v5).
 *
 * Pending = empty disc, 1px --glass-edge ring, faint top sheen.
 * Active  = amber dome, --amber fill + --amber-pale ring + --glow-soft,
 *           1.4s ease-in-out infinite pulse (motion-led-pulse token).
 * Complete = green dome (--led-ok) with inset highlight + tick mark.
 *
 * Connector between adjacent dots: 1px --silk-12 hairline by default;
 * --amber + faint glow when the path becomes active.
 *
 * Labels: Saira var(--type-display) wdth 85 wght 500 10px UPPERCASE
 * 0.22em tracking + engraved text-shadow.
 *   - Active label = --amber + faint amber glow
 *   - Pending      = --silk-40
 *   - Complete     = --silk-65
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
    gap: 6px;
  }
  /* Step node — v5 dome LED. Pending = empty disc with hairline border.
   * Active = amber dome with halo + breathing pulse. Complete = green
   * dome with inset highlight + tick mark. */
  .cmp-step-indicator__node {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 1px solid var(--glass-edge);
    background: rgba(15, 18, 24, 0.85);
    box-shadow:
      0 0 0 1px rgba(0, 0, 0, 0.7),
      inset 0 1px 0 rgba(255, 255, 255, 0.04);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: border-color var(--motion-transition) ease-in-out,
                background var(--motion-transition) ease-in-out,
                box-shadow var(--motion-transition) ease-in-out;
  }
  .cmp-step-indicator__node[data-state="active"] {
    background: var(--amber);
    border-color: var(--amber-pale);
    box-shadow:
      0 0 3px var(--amber),
      0 0 6px var(--amber-40),
      inset 0 1px 0 rgba(255, 255, 255, 0.3),
      inset 0 -0.5px 0 rgba(0, 0, 0, 0.4);
    animation: cmp-step-pulse var(--motion-led-pulse) ease-in-out infinite;
  }
  .cmp-step-indicator__node[data-state="complete"] {
    background: var(--led-ok);
    border-color: rgba(109, 212, 74, 0.7);
    box-shadow:
      0 0 3px var(--led-ok),
      0 0 6px rgba(109, 212, 74, 0.28),
      inset 0 1px 0 rgba(255, 255, 255, 0.35),
      inset 0 -0.5px 0 rgba(0, 0, 0, 0.4);
  }
  .cmp-step-indicator__node[data-state="complete"]::after {
    content: "";
    width: 5px;
    height: 2.5px;
    border-left: 1.5px solid var(--void);
    border-bottom: 1.5px solid var(--void);
    transform: rotate(-45deg) translate(0, -1px);
  }
  .cmp-step-indicator__label {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    line-height: 1;
    color: var(--silk-40);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    transition: color var(--motion-transition) ease-in-out,
                text-shadow var(--motion-transition) ease-in-out;
  }
  .cmp-step-indicator__node-wrap[data-state="active"] .cmp-step-indicator__label {
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
  }
  .cmp-step-indicator__node-wrap[data-state="complete"] .cmp-step-indicator__label {
    color: var(--silk-65);
  }
  /* Connector — faint silk hairline at idle. When the path becomes active
   * (prev complete + here active/complete), an amber fill TRAVELS the
   * segment left→right like a CDJ loop bar charging — segment-LED
   * ballistics, not an instant flip. The travelling fill is a ::after
   * overlay that scaleX(0→1) from the left edge over --motion-step; the
   * 1px silk rail underneath stays as the unlit track. GPU-cheap (transform
   * + opacity only). Reduced-motion → fill snaps in with no travel. */
  .cmp-step-indicator__connector {
    position: relative;
    flex: 0 0 64px;
    height: 1px;
    margin: 0 var(--sp-3);
    margin-bottom: 18px;  /* align with circle vertical center, not labels */
    background: var(--silk-12);
    overflow: visible;
  }
  .cmp-step-indicator__connector::after {
    content: "";
    position: absolute;
    inset: 0;
    background: var(--amber);
    box-shadow: 0 0 4px var(--amber-22);
    transform: scaleX(0);
    transform-origin: left center;
    opacity: 0;
    transition: transform var(--motion-step) ease-out,
                opacity var(--motion-step) ease-out;
  }
  .cmp-step-indicator__connector[data-active="true"]::after {
    transform: scaleX(1);
    opacity: 1;
  }
  @media (prefers-reduced-motion: reduce) {
    .cmp-step-indicator__connector::after {
      transition: none;
    }
  }
  @media (max-width: 720px) {
    .cmp-step-indicator {
      min-width: 0;
      overflow: hidden;
    }
    .cmp-step-indicator__connector {
      flex-basis: min(9vw, 34px);
      margin-left: var(--sp-2);
      margin-right: var(--sp-2);
    }
    .cmp-step-indicator__label {
      max-width: 74px;
      font-size: 8px;
      letter-spacing: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
  @media (max-width: 420px) {
    .cmp-step-indicator__connector {
      flex-basis: 22px;
      margin-left: 6px;
      margin-right: 6px;
    }
    .cmp-step-indicator__node-wrap:not([data-state="active"]) .cmp-step-indicator__label {
      display: none;
    }
    .cmp-step-indicator__node-wrap {
      min-width: 24px;
    }
  }
  @keyframes cmp-step-pulse {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.6; }
  }
`;

registerStyle("cmp-step-indicator", CSS);

export function StepIndicator(props: StepIndicatorProps): HTMLElement {
  const root = document.createElement("div");
  root.className = "cmp-step-indicator";
  root.setAttribute("role", "navigation");
  root.setAttribute("aria-label", "wizard progress");

  // Connectors that should read as filled. We flip data-active on the NEXT
  // frame (not at build time) so the scaleX(0→1) travel transition actually
  // fires when the strip re-mounts on a step advance — setting it inline at
  // creation would paint pre-filled with no animation. Reduced-motion users
  // get the same end-state instantly (the ::after transition is disabled).
  const toActivate: HTMLElement[] = [];
  props.steps.forEach((step, i) => {
    if (i > 0) {
      const conn = document.createElement("div");
      conn.className = "cmp-step-indicator__connector";
      const prev = props.steps[i - 1];
      const here = step;
      // Connector "active" = both adjacent nodes complete, OR previous complete + here active
      const active = prev?.state === "complete" && (here.state === "complete" || here.state === "active");
      if (active) toActivate.push(conn);
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
  // Defer the fill one frame so the L→R travel transition fires on mount.
  // requestAnimationFrame is absent under jsdom (unit tests) — fall back to
  // an immediate set so the end-state (filled) still holds for assertions.
  if (toActivate.length) {
    const flip = () => toActivate.forEach((c) => (c.dataset.active = "true"));
    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(flip);
    } else {
      flip();
    }
  }
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
