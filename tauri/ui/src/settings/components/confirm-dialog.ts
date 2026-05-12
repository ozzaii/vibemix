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
  /** Confirm button styling — "rec" for destructive actions
   *  (default keeps the phosphor look). Phase 12 only uses the default. */
  variant?: "default" | "danger";
}

const CSS = `
  .vmx-confirm__backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    z-index: 60;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .vmx-confirm__dialog {
    width: 360px;
    max-width: calc(100vw - var(--sp-xl));
    background: linear-gradient(180deg, var(--panel-lift) 0%, var(--panel) 100%);
    border: 1px solid var(--bezel-2);
    border-radius: 6px;
    box-shadow:
      0 12px 24px rgba(0, 0, 0, 0.6),
      inset 0 1px 0 rgba(255, 255, 255, 0.05);
    padding: var(--sp-lg);
    display: flex;
    flex-direction: column;
    gap: var(--sp-md);
    font-family: "DM Mono", monospace;
    color: var(--ink);
  }
  .vmx-confirm__heading {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--phosphor);
    line-height: 1;
    text-shadow: var(--phosphor-glow);
  }
  .vmx-confirm__body {
    font-size: 13.5px;
    line-height: 1.45;
    color: var(--ink-dim);
  }
  .vmx-confirm__row {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: var(--sp-sm);
    margin-top: var(--sp-sm);
  }
  .vmx-confirm__btn {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    line-height: 1;
    padding: var(--sp-sm) var(--sp-md);
    border-radius: 4px;
    cursor: pointer;
    transition: background var(--motion-snap) ease-out,
                color var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out;
  }
  .vmx-confirm__btn[data-kind="cancel"] {
    background: transparent;
    border: 1px solid var(--bezel-2);
    color: var(--ink-dim);
  }
  .vmx-confirm__btn[data-kind="cancel"]:hover {
    color: var(--ink);
    border-color: var(--bezel-3);
  }
  .vmx-confirm__btn[data-kind="confirm"] {
    background: var(--phosphor-soft);
    border: 1px solid var(--phosphor-dim);
    color: var(--phosphor);
  }
  .vmx-confirm__btn[data-kind="confirm"]:hover {
    background: var(--phosphor);
    color: var(--panel-deep);
    box-shadow: var(--phosphor-glow);
  }
  .vmx-confirm__btn[data-kind="confirm"][data-variant="danger"] {
    background: rgba(255, 53, 83, 0.12);
    border-color: var(--rec);
    color: var(--rec);
  }
  .vmx-confirm__btn[data-kind="confirm"][data-variant="danger"]:hover {
    background: var(--rec);
    color: var(--panel-deep);
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
