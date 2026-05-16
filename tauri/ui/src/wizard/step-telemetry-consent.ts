/* step-telemetry-consent.ts — Phase 34 / SEC-08.
 *
 * Wizard step inserted between "profile-consent" and "smoke-test":
 * STEP 5 / 5 · TELEMETRY. Asks the user whether to share anonymous
 * diagnostics. Default-OFF (Pitfall P67).
 *
 * No dark patterns:
 *   - Two equally-prominent radio rows (identical CSS class).
 *   - Default-selected option is "Don't share".
 *   - Continue advances regardless of selection.
 *   - There is NO "skip → off" trick; clicking Continue without changing
 *     the radio leaves the default (OFF) value in place — explicit
 *     because the radio is visibly checked.
 *
 * On Continue we emit ipc.telemetry.set_consent with the current toggle
 * value so the sidecar persists telemetry_consent: bool to state.json
 * before the smoke-test surface mounts.
 */

import { PrimaryPanel } from "./components/primary-panel.js";
import { Button } from "./components/button.js";
import { renderTelemetryConsentCard } from "./components/telemetry-consent.js";

export interface TelemetryConsentState {
  consent: boolean;
}

export interface TelemetryConsentCallbacks {
  onContinue: () => void;
  onToggle: (next: boolean) => void;
  onBack?: () => void;
}

export function renderStepTelemetryConsent(
  state: TelemetryConsentState,
  cb: TelemetryConsentCallbacks,
): HTMLElement {
  const body = document.createElement("div");

  const heading = document.createElement("h1");
  heading.className = "wizard-step__heading";
  heading.textContent = "STEP 5 / 5 · TELEMETRY";

  const subtitle = document.createElement("p");
  subtitle.className = "wizard-step__subtitle";
  subtitle.textContent =
    "help vibemix get better — anonymous diagnostics, off by default.";

  body.append(heading, subtitle);

  body.append(
    renderTelemetryConsentCard({
      consent: state.consent,
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
  root.className = "wizard-step";
  root.append(panel, ctaRow);
  return root;
}
