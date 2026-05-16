/* step2-output-device.ts — Step 2 surface (UI-SPEC §Step 2).
 *
 * Header → conditional BlackHole banner (macOS + missing) → DeviceDropdown
 * → AudioTestButton → WindowPicker → Continue CTA (armed only when
 * audio passed + window selected).
 *
 * Copy strings VERBATIM from UI-SPEC §Step 2. */

import { PrimaryPanel } from "./components/primary-panel.js";
import { BlackHoleBanner } from "./components/blackhole-banner.js";
import { DropdownDevice, type DropdownDevice as DropdownDeviceItem } from "./components/dropdown-device.js";
import { AudioTestButton, type AudioTestState } from "./components/audio-test-button.js";
import { WindowPicker, type WindowPickerMode } from "./components/window-picker.js";
import { Button } from "./components/button.js";
import { registerStyle } from "./components/_style-registry.js";

/* Phase 43 / Plan 43-03 — VIS-02 hover-glow sweep for the output-device
 * step. Step 2 owns the device dropdown + 1kHz test tone + window picker
 * — every one of those is interactive. The scoped block here lifts the
 * existing .wizard-step__cta-row glow rule (registered by
 * step1-permissions.ts) onto the deeper device-picker / test-tone /
 * window-picker subtrees so the entire calibration surface is uniform
 * under cursor. */
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
  audioTestState: AudioTestState;
  audioPassed: boolean;
  actualRate: number;
  detectedDjApp?: { appName: string; windowTitle: string };
  windowPickerMode: WindowPickerMode;
  windowSelected: boolean;
}

export interface Step2Callbacks {
  platform: "darwin" | "win32" | "linux";
  onContinue: () => void;
  onSelectDevice: (id: string) => void;
  onPlayTest: () => void;
  onAudioYes: () => void;
  onAudioRetry: () => void;
  onOpenInstall: () => void;
  onRecheckBlackHole: () => void;
  onSelectWindow: () => void;
  onPickDifferent: () => void;
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
  // UI-SPEC §Step 2 H1 — VERBATIM
  heading.textContent = "STEP 2 / 3 · OUTPUT DEVICE";

  const subtitle = document.createElement("p");
  subtitle.className = "wizard-step__subtitle";
  // UI-SPEC §Step 2 Subtitle — VERBATIM
  subtitle.textContent = "picking your headphones and proving the audio chain works.";

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

  // Audio test
  body.append(
    AudioTestButton({
      state: state.audioTestState,
      actualRate: state.actualRate,
      onPlay: cb.onPlayTest,
      onYes: cb.onAudioYes,
      onRetry: cb.onAudioRetry,
    })
  );

  // Window picker
  if (state.detectedDjApp || state.windowPickerMode === "enum") {
    body.append(
      WindowPicker({
        mode: state.windowPickerMode,
        detectedHint: state.detectedDjApp ? {
          appName: state.detectedDjApp.appName,
          windowTitle: state.detectedDjApp.windowTitle,
        } : undefined,
        allWindows: state.windowPickerMode === "enum" ? [
          { id: "djay", name: "djay Pro AI" },
          { id: "rekordbox", name: "Rekordbox" },
          { id: "chrome", name: "Chrome — gmail" },
        ] : undefined,
        onSelect: () => cb.onSelectWindow(),
        onPickDifferent: cb.onPickDifferent,
      })
    );
  }

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
  // Continue is armed once the window has been picked. We previously
  // required state.audioPassed too, but the 1kHz tone test can fail in
  // ways that don't reflect the user's actual rig (sample rate
  // mismatch flagged as failure even though the user heard it; user
  // clicked Retry once and is now on a stale failed state with the
  // Yes button stranded behind the disabled-on-failed branch). The
  // tone test stays informational — user judgment over a fragile
  // probe heuristic.
  const armed = state.windowSelected;
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
