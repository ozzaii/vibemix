/* Phase 12 Wave 4 — generic confirm-dialog modal (Plan 12-05 §4).
 *
 * Used by the CALIBRATION group: clicking "Re-run wizard" opens this
 * dialog with heading "RESTART CALIBRATION?" before sending
 * `ipc.wizard.start` to the sidecar (which tears down the session and
 * mounts the wizard router).
 *
 * Shape:
 *   ┌─────────────────────────────┐
 *   │ HEADING                     │
 *   │ Body text — DM Mono 13.5px  │
 *   │                             │
 *   │           [ Cancel ] [ OK ] │
 *   └─────────────────────────────┘
 *
 * Esc dismisses (treated as Cancel). Backdrop click also dismisses.
 *
 * Pure-function — caller supplies onConfirm / onCancel and mounts the
 * returned element wherever it wants (drawer mounts it on top of itself).
 */

import { registerStyle } from "../../session/components/_style-registry.js";

export interface ConfirmDialogProps {
  heading: string;
  body: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  /** Confirm button styling — "danger" for destructive actions
   *  (default keeps the v5 amber look). Phase 12 only uses the default. */
  variant?: "default" | "danger";
}

const CSS = `
  .vmx-confirm__backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    z-index: 60;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: vmx-confirm-fade-in 180ms ease-out;
  }
  @keyframes vmx-confirm-fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  /* Dialog — sealed glass-1 popover with the border-anim sweep so even
   * a modal moment carries the v5 "sign of life" character. */
  .vmx-confirm__dialog {
    position: relative;
    width: 360px;
    max-width: calc(100vw - 64px);
    background: var(--glass-1);
    backdrop-filter: var(--blur-glass);
    -webkit-backdrop-filter: var(--blur-glass);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-md);
    overflow: hidden;
    box-shadow:
      inset 0 1px 0 var(--glass-top),
      0 24px 60px rgba(0, 0, 0, 0.85),
      0 0 0 1px rgba(255, 255, 255, 0.018);
    padding: var(--sp-5) var(--sp-5) var(--sp-4);
    display: flex;
    flex-direction: column;
    gap: var(--sp-3);
    font-family: var(--type-body);
    color: var(--silk);
    animation: vmx-confirm-rise 220ms cubic-bezier(0.16, 0.84, 0.32, 1);
  }
  @keyframes vmx-confirm-rise {
    from { transform: translateY(8px) scale(0.985); opacity: 0; }
    to   { transform: translateY(0) scale(1); opacity: 1; }
  }
  .vmx-confirm__dialog > * { position: relative; z-index: 1; }
  .vmx-confirm__dialog > .border-anim { z-index: 4; }
  .vmx-confirm__heading {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 700;
    font-size: 12px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
  .vmx-confirm__heading::before {
    content: '';
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--amber);
    box-shadow: 0 0 4px var(--amber), 0 0 8px var(--amber-40);
  }
  .vmx-confirm__dialog[data-variant="danger"] .vmx-confirm__heading::before {
    background: var(--led-fault);
    box-shadow: 0 0 4px var(--led-fault), 0 0 8px rgba(212, 65, 58, 0.28);
  }
  .vmx-confirm__body {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 13px;
    line-height: 1.55;
    color: var(--silk-65);
  }
  .vmx-confirm__row {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: var(--sp-2);
    margin-top: var(--sp-3);
  }
  .vmx-confirm__btn {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    line-height: 1;
    padding: 9px var(--sp-4);
    border-radius: var(--rad-sm);
    cursor: pointer;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    transition: background var(--motion-snap) ease-out,
                color var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out,
                text-shadow var(--motion-snap) ease-out;
  }
  .vmx-confirm__btn[data-kind="cancel"] {
    background: var(--glass-2);
    border: 1px solid var(--glass-edge);
    color: var(--silk-65);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.035),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45);
  }
  .vmx-confirm__btn[data-kind="cancel"]:hover {
    color: var(--silk);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(0, 0, 0, 0.45),
      0 0 10px var(--amber-22);
  }
  .vmx-confirm__btn[data-kind="confirm"] {
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.12) 0%, rgba(255, 138, 61, 0.035) 100%);
    border: 1px solid var(--amber-40);
    color: var(--amber);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 var(--amber-40),
      inset 0 0 14px var(--amber-22),
      0 0 0 1px rgba(255, 138, 61, 0.14);
    text-shadow: 0 0 4px var(--amber-65);
  }
  .vmx-confirm__btn[data-kind="confirm"]:hover {
    border-color: var(--amber);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.08),
      inset 0 -1px 0 var(--amber-65),
      inset 0 0 18px var(--amber-40);
  }
  .vmx-confirm__btn[data-kind="confirm"][data-variant="danger"] {
    background: linear-gradient(180deg, rgba(212, 65, 58, 0.14) 0%, rgba(212, 65, 58, 0.04) 100%);
    border-color: rgba(212, 65, 58, 0.45);
    color: var(--led-fault);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 -1px 0 rgba(212, 65, 58, 0.45),
      inset 0 0 14px rgba(212, 65, 58, 0.18),
      0 0 0 1px rgba(212, 65, 58, 0.18);
    text-shadow: 0 0 4px rgba(212, 65, 58, 0.4);
  }
  .vmx-confirm__btn[data-kind="confirm"][data-variant="danger"]:hover {
    border-color: var(--led-fault);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.08),
      inset 0 -1px 0 var(--led-fault),
      inset 0 0 18px rgba(212, 65, 58, 0.28);
  }
`;

registerStyle("vmx-confirm", CSS);

export function renderConfirmDialog(props: ConfirmDialogProps): HTMLElement {
  const backdrop = document.createElement("div");
  backdrop.className = "vmx-confirm__backdrop";
  backdrop.setAttribute("role", "dialog");
  backdrop.setAttribute("aria-modal", "true");
  backdrop.setAttribute("aria-labelledby", "vmx-confirm-heading");

  const dialog = document.createElement("div");
  dialog.className = "vmx-confirm__dialog";
  if (props.variant === "danger") dialog.dataset.variant = "danger";

  // v5 "sign of life" border-anim — even the modal moment carries the
  // slow amber light traveling the perimeter.
  const sweep = document.createElement("div");
  sweep.className = "border-anim slow";
  sweep.setAttribute("aria-hidden", "true");
  dialog.append(sweep);

  const heading = document.createElement("div");
  heading.className = "vmx-confirm__heading";
  heading.id = "vmx-confirm-heading";
  heading.textContent = props.heading;
  dialog.append(heading);

  const body = document.createElement("div");
  body.className = "vmx-confirm__body";
  body.textContent = props.body;
  dialog.append(body);

  const row = document.createElement("div");
  row.className = "vmx-confirm__row";

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "vmx-confirm__btn";
  cancelBtn.dataset.kind = "cancel";
  cancelBtn.textContent = props.cancelLabel ?? "CANCEL";
  cancelBtn.addEventListener("click", (e) => {
    e.preventDefault();
    props.onCancel();
  });
  row.append(cancelBtn);

  const confirmBtn = document.createElement("button");
  confirmBtn.type = "button";
  confirmBtn.className = "vmx-confirm__btn";
  confirmBtn.dataset.kind = "confirm";
  if (props.variant === "danger") {
    confirmBtn.dataset.variant = "danger";
  }
  confirmBtn.textContent = props.confirmLabel ?? "CONFIRM";
  confirmBtn.addEventListener("click", (e) => {
    e.preventDefault();
    props.onConfirm();
  });
  row.append(confirmBtn);

  dialog.append(row);
  backdrop.append(dialog);

  // Esc dismisses. Backdrop click (but NOT dialog click) dismisses.
  const onKey = (e: KeyboardEvent): void => {
    if (e.key === "Escape") {
      e.preventDefault();
      props.onCancel();
    }
  };
  document.addEventListener("keydown", onKey);
  // Remove listener when the dialog leaves the DOM.
  const obs = new MutationObserver(() => {
    if (!backdrop.isConnected) {
      document.removeEventListener("keydown", onKey);
      obs.disconnect();
    }
  });
  obs.observe(document.body, { childList: true, subtree: true });

  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) {
      props.onCancel();
    }
  });

  // Auto-focus the cancel button so Enter doesn't immediately confirm a
  // destructive action — UX-08-grade safety.
  queueMicrotask(() => {
    try {
      cancelBtn.focus();
    } catch {
      /* jsdom may not have focus support */
    }
  });

  return backdrop;
}
