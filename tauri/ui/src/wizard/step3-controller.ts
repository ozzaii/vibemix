/* step3-controller.ts — Step 3 surface (UI-SPEC §Step 3).
 *
 * Header + ControllerProbe (3 zones). 10s countdown is mocked by the
 * router; Wave 4 wires real MIDI events.
 *
 * Continue CTA armed after caught OR skip. */

import { PrimaryPanel } from "./components/primary-panel.js";
import { ControllerProbe, type ControllerProbeState } from "./components/controller-probe.js";
import { Button } from "./components/button.js";
import { registerStyle } from "./components/_style-registry.js";

/* Phase 43 / Plan 43-03 — VIS-02 hover-glow sweep for the controller
 * step. The controller-probe carries Listen Again + Skip CTAs; the
 * scoped --glow-faint application below ensures both honour the
 * surface-wide tactility contract on :hover and :focus-visible. */
const CSS = `
  .wizard-step--controller button:not([disabled]),
  .wizard-step--controller [role="button"]:not([aria-disabled="true"]),
  .wizard-step--controller [data-interactive] {
    transition: box-shadow var(--motion-snap) ease-out;
  }
  .wizard-step--controller button:not([disabled]):hover,
  .wizard-step--controller button:not([disabled]):focus-visible,
  .wizard-step--controller [role="button"]:not([aria-disabled="true"]):hover,
  .wizard-step--controller [role="button"]:not([aria-disabled="true"]):focus-visible,
  .wizard-step--controller [data-interactive]:hover,
  .wizard-step--controller [data-interactive]:focus-visible {
    box-shadow: var(--glow-faint);
  }
`;

registerStyle("wizard-step--controller", CSS);

export interface Step3State {
  detectedController?: { name: string; port: string };
  probeState: ControllerProbeState;
  secondsLeft?: number;
  caughtLabel?: string;
}

export interface Step3Callbacks {
  onContinue: () => void;
  onListenAgain: () => void;
  onSkip: () => void;
  /** Impeccable Wave 5.A — walks the wizard one step backward. Optional
   *  for back-compat with existing tests; the router always wires it. */
  onBack?: () => void;
}

export function renderStep3(state: Step3State, cb: Step3Callbacks): HTMLElement {
  const body = document.createElement("div");
  // Scope so the VIS-02 hover-glow rule above applies (Plan 43-03).
  body.classList.add("wizard-step--controller");

  const heading = document.createElement("h1");
  heading.className = "wizard-step__heading";
  // UI-SPEC §Step 3 H1 — VERBATIM
  heading.textContent = "STEP 3 / 5 · CONTROLLER";

  const subtitle = document.createElement("p");
  subtitle.className = "wizard-step__subtitle";
  // UI-SPEC §Step 3 Subtitle — VERBATIM
  subtitle.textContent = "proving your midi gear is wired in.";

  body.append(heading, subtitle);

  body.append(
    ControllerProbe({
      detectedController: state.detectedController,
      state: state.probeState,
      caughtLabel: state.caughtLabel,
      secondsLeft: state.secondsLeft,
      onListenAgain: cb.onListenAgain,
      onSkip: cb.onSkip,
    })
  );

  const panel = PrimaryPanel({ children: body });

  const ctaRow = document.createElement("div");
  ctaRow.className = "wizard-step__cta-row";
  ctaRow.dataset.back = cb.onBack ? "true" : "false";
  if (cb.onBack) {
    ctaRow.append(
      Button({
        variant: "secondary",
        state: "idle",
        label: "Back",
        leadingGlyph: "←",
        onClick: cb.onBack,
      }),
    );
  }
  const armed = state.probeState === "caught" || state.probeState === "timeout";
  ctaRow.append(
    Button({
      variant: "primary",
      state: armed ? "armed" : "disabled",
      // UI-SPEC §Step 3 Continue button — VERBATIM
      label: "Continue",
      leadingGlyph: "[",
      trailingGlyph: "→ ]",
      onClick: cb.onContinue,
    })
  );

  const wrap = document.createElement("div");
  wrap.append(panel, ctaRow);
  return wrap;
}
