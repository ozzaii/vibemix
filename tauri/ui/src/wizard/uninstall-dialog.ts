/* uninstall-dialog.ts — Phase 49 INSTALL-07 surface.
 *
 * Renders the uninstall confirmation modal with preserve-default behavior.
 * Strings read from copy.uninstall.* (zero inline literals).
 *
 * Default CTA: `Uninstall vibemix` — preserves recordings + debriefs +
 * ghost_calibration.json.
 * Clean opt-in checkbox: `Also remove recordings and debriefs` — when
 * armed, the destructive CTA replaces the default with `Remove vibemix
 * and all data` rendered in the --led-fault border-only treatment.
 *
 * On confirm: invokes Tauri command `run_uninstall({clean: bool})` (
 * provided by main.rs — Plan 49-04 hand-off, not in this file). The
 * command dispatches to uninstall.sh / uninstall.ps1 per platform.
 *
 * Focus trap + ESC-to-dismiss + aria-labels per UI-SPEC § Uninstall.
 */

import { Button } from "./components/button.js";
import { registerStyle } from "./components/_style-registry.js";
import { copy, interpolate } from "./copy.js";

export interface UninstallDialogCallbacks {
  estimatedMb: number;
  onConfirm: (clean: boolean) => Promise<void> | void;
  onCancel: () => void;
}

const CSS = `
  .uninstall-dialog__backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.72);
    backdrop-filter: blur(8px);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .uninstall-dialog__panel {
    background: var(--glass-1);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    padding: var(--sp-5);
    max-width: 460px;
    width: calc(100% - var(--sp-6));
  }
  .uninstall-dialog__title {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 82, "wght" 700;
    font-size: 20px;
    color: var(--silk);
    margin: 0 0 var(--sp-3);
  }
  .uninstall-dialog__body {
    font-family: var(--type-body);
    font-size: 14px;
    line-height: 1.55;
    color: var(--silk-65);
    margin: 0 0 var(--sp-4);
  }
  .uninstall-dialog__clean-row {
    display: flex;
    align-items: flex-start;
    gap: var(--sp-2);
    padding: var(--sp-3);
    background: var(--glass-2);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    margin-bottom: var(--sp-3);
  }
  .uninstall-dialog__clean-row[data-armed="true"] {
    border-color: var(--led-fault);
  }
  .uninstall-dialog__clean-text {
    flex: 1 1 auto;
  }
  .uninstall-dialog__clean-label {
    font-size: 13px;
    color: var(--silk);
    margin: 0 0 var(--sp-1);
  }
  .uninstall-dialog__clean-body {
    font-size: 12px;
    color: var(--silk-40);
    margin: 0;
  }
  .uninstall-dialog__cta-row {
    display: flex;
    justify-content: space-between;
    gap: var(--sp-3);
    margin-top: var(--sp-5);
  }
`;

registerStyle("uninstall-dialog", CSS);

export function createUninstallDialog(
  callbacks: UninstallDialogCallbacks,
): HTMLElement {
  const backdrop = document.createElement("div");
  backdrop.className = "uninstall-dialog__backdrop";
  backdrop.setAttribute("role", "dialog");
  backdrop.setAttribute("aria-modal", "true");
  backdrop.setAttribute("aria-labelledby", "uninstall-dialog-title");

  const panel = document.createElement("div");
  panel.className = "uninstall-dialog__panel";

  const title = document.createElement("h2");
  title.id = "uninstall-dialog-title";
  title.className = "uninstall-dialog__title";
  title.textContent = copy.uninstall.title;

  const body = document.createElement("p");
  body.className = "uninstall-dialog__body";
  body.textContent = copy.uninstall.body;

  // Clean opt-in row
  const cleanRow = document.createElement("label");
  cleanRow.className = "uninstall-dialog__clean-row";
  cleanRow.setAttribute("data-armed", "false");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = "uninstall-clean-checkbox";
  const cleanText = document.createElement("div");
  cleanText.className = "uninstall-dialog__clean-text";
  const cleanLabel = document.createElement("p");
  cleanLabel.className = "uninstall-dialog__clean-label";
  cleanLabel.textContent = copy.uninstall.clean_opt_in;
  const cleanBody = document.createElement("p");
  cleanBody.className = "uninstall-dialog__clean-body";
  cleanBody.textContent = interpolate(copy.uninstall.clean_body, {
    mb: callbacks.estimatedMb,
  });
  cleanText.append(cleanLabel, cleanBody);
  cleanRow.append(checkbox, cleanText);

  // CTA row
  const ctaRow = document.createElement("div");
  ctaRow.className = "uninstall-dialog__cta-row";
  const cancelBtn = Button({
    label: copy.uninstall.cancel_cta,
    variant: "ghost",
    onClick: () => {
      backdrop.remove();
      callbacks.onCancel();
    },
  });
  const confirmBtn = Button({
    label: copy.uninstall.default_cta,
    variant: "primary",
    onClick: async () => {
      const isClean = checkbox.checked;
      backdrop.remove();
      await callbacks.onConfirm(isClean);
    },
  });
  ctaRow.append(cancelBtn, confirmBtn);

  checkbox.addEventListener("change", () => {
    cleanRow.setAttribute("data-armed", checkbox.checked ? "true" : "false");
    confirmBtn.textContent = checkbox.checked
      ? copy.uninstall.clean_confirm_cta
      : copy.uninstall.default_cta;
  });

  // ESC to dismiss
  backdrop.addEventListener("keydown", (ev: KeyboardEvent) => {
    if (ev.key === "Escape") {
      backdrop.remove();
      callbacks.onCancel();
    }
  });

  panel.append(title, body, cleanRow, ctaRow);
  backdrop.append(panel);
  return backdrop;
}
