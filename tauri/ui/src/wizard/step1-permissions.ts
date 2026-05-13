/* step1-permissions.ts — Step 1 surface (UI-SPEC §Step 1).
 *
 * OS-aware: macOS = 2 cards (Screen Recording + Microphone), Windows = 1
 * card (Microphone). Wave 3 fakes OS detection via navigator.userAgent;
 * Wave 4 reads platform from Tauri's TAURI_PLATFORM env var.
 *
 * Continue CTA enabled when all required permissions granted.
 *
 * Copy strings VERBATIM from UI-SPEC §Step 1 Permissions Strings. */

import { PrimaryPanel } from "./components/primary-panel.js";
import { PermissionsCard } from "./components/permissions-card.js";
import type { PermissionState } from "./components/permissions-card.js";
import { Button } from "./components/button.js";
import { registerStyle } from "./components/_style-registry.js";

export interface Step1State {
  screenRecording: PermissionState;
  microphone: PermissionState;
}

export interface Step1Callbacks {
  platform: "darwin" | "win32" | "linux";
  onContinue: () => void;
  onGrantScreen: () => void;
  onGrantMic: () => void;
  onOpenScreenSettings: () => void;
  onOpenMicSettings: () => void;
  /** Impeccable Wave 5.A — walks the wizard one step backward. Optional
   *  for back-compat with existing tests; the router always wires it. */
  onBack?: () => void;
}

const CSS = `
  .wizard-step__heading {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 700;
    font-size: 22px;
    letter-spacing: 0.04em;
    color: var(--amber);
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7), var(--glow-soft);
    line-height: 1.1;
    margin: 0 0 var(--sp-2);
    text-transform: uppercase;
  }
  .wizard-step__subtitle {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 14px;
    color: var(--silk-65);
    line-height: 1.5;
    margin: 0 0 var(--sp-5);
  }
  .wizard-step__cards {
    display: flex;
    flex-direction: column;
    gap: var(--sp-4);
  }
  .wizard-step__cta-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    margin-top: var(--sp-5);
  }
  /* Hidden when no Back affordance is wired (intro / smoke-test / done). */
  .wizard-step__cta-row[data-back="false"] {
    justify-content: flex-end;
  }
  .wizard-step__cta-row[data-back="false"] .wizard-step__back-spacer {
    display: none;
  }
`;

registerStyle("wizard-step", CSS);

export function renderStep1(state: Step1State, cb: Step1Callbacks): HTMLElement {
  const body = document.createElement("div");

  const heading = document.createElement("h1");
  heading.className = "wizard-step__heading";
  // UI-SPEC §Step 1 H1 — VERBATIM
  heading.textContent = "STEP 1 / 3 — PERMISSIONS";

  const subtitle = document.createElement("p");
  subtitle.className = "wizard-step__subtitle";
  // UI-SPEC §Step 1 Subtitle — VERBATIM
  subtitle.textContent = "vibemix needs to listen to your master output and watch your dj window.";

  const cards = document.createElement("div");
  cards.className = "wizard-step__cards";

  const required: PermissionState[] = [];
  if (cb.platform === "darwin") {
    cards.append(
      PermissionsCard({
        kind: "screen-recording",
        state: state.screenRecording,
        onGrantClick: cb.onGrantScreen,
        onOpenSettings: cb.onOpenScreenSettings,
      })
    );
    required.push(state.screenRecording);
  }
  cards.append(
    PermissionsCard({
      kind: "microphone",
      state: state.microphone,
      onGrantClick: cb.onGrantMic,
      onOpenSettings: cb.onOpenMicSettings,
    })
  );
  required.push(state.microphone);

  body.append(heading, subtitle, cards);

  const panel = PrimaryPanel({
    header: undefined,
    children: body,
  });

  const ctaRow = document.createElement("div");
  ctaRow.className = "wizard-step__cta-row";
  ctaRow.dataset.back = cb.onBack ? "true" : "false";

  // Back button — bottom-left affordance (impeccable Wave 5.A). Hidden
  // when no callback is wired (preserves the legacy single-button layout
  // for unit tests that don't pass onBack).
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

  const allGranted = required.every((s) => s === "granted");
  ctaRow.append(
    Button({
      variant: "primary",
      state: allGranted ? "armed" : "disabled",
      // UI-SPEC §Step 1 Continue button — VERBATIM
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
