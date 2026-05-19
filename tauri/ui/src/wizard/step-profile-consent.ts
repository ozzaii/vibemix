/* step-profile-consent.ts — Phase 32 / PROFILE-05.
 *
 * New wizard step inserted between "controller" and "smoke-test":
 * STEP 4 / 4 · PROFILE. Asks the user whether to enable long-term profile
 * learning. Default-OFF; the toggle is a single click; Continue advances
 * regardless of the toggle state.
 *
 * On Continue we emit ipc.profile.set_consent with the current toggle value
 * so the sidecar persists profile_consent: bool to state.json before the
 * smoke-test surface mounts. (The smoke-test → completeWizard then writes
 * the rest of first-run state.)
 */

import { PrimaryPanel } from "./components/primary-panel.js";
import { Button } from "./components/button.js";
import { renderProfileConsentCard } from "./components/profile-consent.js";
import { registerStyle } from "./components/_style-registry.js";

/* Phase 43 / Plan 43-03 — VIS-02 hover-glow sweep for the profile-consent
 * step. The consent toggle is the focal interactive element on this
 * surface; the scoped rule below routes --glow-faint into the toggle
 * row + Continue/Back CTAs on :hover and :focus-visible. The consent
 * affordance reads cleaner under cursor without competing with the
 * armed-state amber bleed already inside cmp-btn. */
const CSS = `
  .wizard-step--profile-consent button:not([disabled]),
  .wizard-step--profile-consent [role="button"]:not([aria-disabled="true"]),
  .wizard-step--profile-consent [data-interactive] {
    transition: box-shadow var(--motion-snap) ease-out;
  }
  .wizard-step--profile-consent button:not([disabled]):hover,
  .wizard-step--profile-consent button:not([disabled]):focus-visible,
  .wizard-step--profile-consent [role="button"]:not([aria-disabled="true"]):hover,
  .wizard-step--profile-consent [role="button"]:not([aria-disabled="true"]):focus-visible,
  .wizard-step--profile-consent [data-interactive]:hover,
  .wizard-step--profile-consent [data-interactive]:focus-visible {
    box-shadow: var(--glow-faint);
  }
`;

registerStyle("wizard-step--profile-consent", CSS);

export interface ProfileConsentState {
  consent: boolean;
}

export interface ProfileConsentCallbacks {
  onContinue: () => void;
  onToggle: (next: boolean) => void;
  onBack?: () => void;
}

export function renderStepProfileConsent(
  state: ProfileConsentState,
  cb: ProfileConsentCallbacks,
): HTMLElement {
  const body = document.createElement("div");

  const heading = document.createElement("h1");
  heading.className = "wizard-step__heading";
  heading.textContent = "STEP 4 / 4 · PROFILE";

  const subtitle = document.createElement("p");
  subtitle.className = "wizard-step__subtitle";
  subtitle.textContent =
    "let vibemix learn your style. coaching gets sharper over time.";

  body.append(heading, subtitle);

  body.append(
    renderProfileConsentCard({
      checked: state.consent,
      onToggle: cb.onToggle,
    }),
  );

  const panel = PrimaryPanel({ children: body });

  const ctaRow = document.createElement("div");
  ctaRow.className = "wizard-step__cta-row";
  ctaRow.dataset.back = cb.onBack ? "true" : "false";
  if (cb.onBack) {
    ctaRow.append(
      Button({
        variant: "secondary",
        state: "armed",
        label: "Back",
        leadingGlyph: "←",
        onClick: cb.onBack,
      }),
    );
  }
  ctaRow.append(
    Button({
      variant: "primary",
      state: "armed",
      label: "Continue",
      leadingGlyph: "[",
      trailingGlyph: "]",
      onClick: cb.onContinue,
    }),
  );

  const root = document.createElement("section");
  root.className = "wizard-step wizard-step--profile-consent";
  root.append(panel, ctaRow);
  return root;
}
