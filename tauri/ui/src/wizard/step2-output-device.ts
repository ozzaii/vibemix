/* step2-output-device.ts — Step 2 surface (UI-SPEC §Step 2).
 *
 * Header -> conditional BlackHole banner (macOS + missing) -> DeviceDropdown
 * -> Continue CTA (armed once an output device is selected).
 *
 * Copy strings VERBATIM from UI-SPEC §Step 2. */

import { PrimaryPanel } from "./components/primary-panel.js";
import { BlackHoleBanner } from "./components/blackhole-banner.js";
import { DropdownDevice, type DropdownDevice as DropdownDeviceItem } from "./components/dropdown-device.js";
import { Button } from "./components/button.js";
import { withStepLeadGlyph } from "./step1-permissions.js";
import { registerStyle } from "./components/_style-registry.js";

/* Phase 43 / Plan 43-03 - VIS-02 hover-glow sweep for the output-device
 * step. Step 2 owns the master-output picker. The scoped block here lifts
 * the existing .wizard-step__cta-row glow rule onto those interactive
 * subtrees so the calibration surface is uniform under cursor. */
const CSS = `
  .wizard-step--output-device button:not([disabled]),
  .wizard-step--output-device [role="button"]:not([aria-disabled="true"]),
  .wizard-step--output-device [data-interactive] {
    transition: box-shadow var(--motion-snap) ease-out;
  }
  .wizard-step--output-device button:not([disabled]):hover,
  .wizard-step--output-device button:not([disabled]):focus-visible,
  .wizard-step--output-device [role="button"]:not([aria-disabled="true"]):hover,
  .wizard-step--output-device [role="button"]:not([aria-disabled="true"]):focus-visible,
  .wizard-step--output-device [data-interactive]:hover,
  .wizard-step--output-device [data-interactive]:focus-visible {
    box-shadow: var(--glow-faint);
  }
`;

registerStyle("wizard-step--output-device", CSS);

export interface Step2State {
  blackHolePresent: boolean;
  blackHoleBannerPostClick: boolean;
  devices: DropdownDeviceItem[];
  selectedDeviceId: string;
}

export interface Step2Callbacks {
  platform: "darwin" | "win32" | "linux";
  onContinue: () => void;
  onSelectDevice: (id: string) => void;
  onOpenInstall: () => void;
  onRecheckBlackHole: () => void;
  /** Impeccable Wave 5.A — walks the wizard one step backward. Optional
   *  for back-compat with existing tests; the router always wires it. */
  onBack?: () => void;
}

export function renderStep2(state: Step2State, cb: Step2Callbacks): HTMLElement {
  const body = document.createElement("div");
  // Scoping class so the VIS-02 hover-glow rule above latches onto this
  // step's interactive subtree (Plan 43-03).
  body.classList.add("wizard-step--output-device");

  const heading = document.createElement("h1");
  heading.className = "wizard-step__heading";
  heading.textContent = "OUTPUT DEVICE";
  withStepLeadGlyph(heading, 2);

  const subtitle = document.createElement("p");
  subtitle.className = "wizard-step__subtitle";
  subtitle.textContent = "choose where vibemix should play setup audio.";

  body.append(heading, subtitle);

  // Conditional BlackHole banner (macOS only + missing)
  if (cb.platform === "darwin" && !state.blackHolePresent) {
    body.append(
      BlackHoleBanner({
        onOpenInstall: cb.onOpenInstall,
        onRecheck: cb.onRecheckBlackHole,
        postClickState: state.blackHoleBannerPostClick,
      })
    );
  }

  // Device dropdown — with AUTO pill driven by state's `isAuto` flag
  const devices = state.devices.map((d) =>
    d.id === state.selectedDeviceId && state.selectedDeviceId === "airpods"
      ? { ...d, isAuto: true }
      : { ...d, isAuto: false }
  );
  body.append(
    DropdownDevice({
      devices,
      selectedId: state.selectedDeviceId,
      onSelect: cb.onSelectDevice,
    })
  );

  const panel = PrimaryPanel({ children: body });
  panel.classList.add("wizard-step__panel-rise");

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
  // Continue is armed by the real output-device selection. DJ-window
  // detection is only a background hint for first-run state because the
  // wizard does not persist a selected target window id.
  const armed = Boolean(state.selectedDeviceId);
  ctaRow.append(
    Button({
      variant: "primary",
      state: armed ? "armed" : "disabled",
      // UI-SPEC §Step 2 Continue button — VERBATIM
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
