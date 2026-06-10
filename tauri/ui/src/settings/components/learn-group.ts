// SPDX-License-Identifier: Apache-2.0
//
// Phase 92 Plan 06 (LESSON-03) — Settings drawer LEARN group.
//
// Mirror of MascotGroup / HelpGroup / PerformanceGroup at
// SettingsDrawer.ts:909-927. Inserted between RECORDING/PROFILE/CALIBRATION
// and MASCOT per the existing group order (per UI-SPEC §Component Inventory:
// "Adds a `LEARN` group to the existing SettingsDrawer between RECORDING and
// MASCOT"). The actual landing site in SettingsDrawer.ts:913 is right before
// `body.append(MascotGroup())` — after CALIBRATION, before MASCOT — which is
// the closest available slot to the spec's "between RECORDING and MASCOT"
// requirement (PROFILE and CALIBRATION live between them; the LEARN group
// joins that data-user-sensitive cluster).
//
// One row: "reset learn progress". Click → destructive confirm dialog →
// emitIpc("ipc.learn.progress_state", { action: "reset" }). The sidecar
// (Plan 92-04 progress.reset_progress) wipes ~/.cache/vibemix/learn-progress.json
// + emits ipc.learn.progress_state { action: "reset_ack" } which Plan 92-05's
// learn-window.ts surfaces as a one-line toast `learn progress reset.`.
//
// Copy lock (UI-SPEC §Copywriting Contract lines 170-181, byte-exact):
//   - Row label: "reset learn progress" (lowercase, period-FREE — it's a
//     label, not a sentence)
//   - Row secondary: "clears all completed lessons. cannot be undone."
//     (two short sentences)
//   - Dialog heading: "reset learn progress?" (question form, lowercase)
//   - Dialog body: "all 36 lessons across 3 courses will reset to not
//     started. your library and DJ profile are not affected." (two
//     sentences; full disclosure of scope)
//   - Primary CTA: "reset" (one word, lowercase — NOT "Yes, reset" / "OK")
//   - Secondary CTA: "cancel" (one word, lowercase)
//   - variant: "danger" → confirm-dialog.ts paints the primary button with
//     --led-fault (NOT amber — destructive actions never light amber per
//     UI-SPEC §Color forbidden colors).
//
// Optimistic-repaint rule (CLAUDE.md: "Frontend settings controls must
// repaint OPTIMISTICALLY"): the destructive confirm dialog IS the immediate
// repaint — clicking the row opens it synchronously. The dialog's onConfirm
// fires `emitIpc` (fire-and-forget) + dismisses the dialog locally + shows
// a SESSION-window toast confirming the reset (CR-04 fix — the Learn
// window's reset_ack toast is on a separate surface, so a user clicking
// reset in Settings would otherwise never see confirmation in the window
// they're standing on; the Learn window still surfaces its own toast on
// reset_ack when it's open, but the Session-window toast is the primary
// feedback channel for the drawer click).
//
// Frontend-enforcement compliance (CDJ Whisper v5 contract):
//   - NO new design tokens; the destructive look is owned by
//     `confirm-dialog.ts[data-variant="danger"]` which uses --led-fault.
//   - 20/80 rule: zero amber on this group (destructive row is silk-only at
//     rest; --led-fault appears only inside the confirm dialog's primary
//     button — that's the existing dialog's accent budget, not new amber).
//   - Saira variable-axis display for "LEARN" heading (via the parent
//     renderSettingsGroup wrapper).
//   - lowercase, period-free label + period-terminated secondary; NO
//     exclamation marks anywhere; NO "are you sure?" — the heading IS the
//     question.

import { registerStyle } from "../../session/components/_style-registry.js";
import { emitIpc } from "../../ipc/client.js";
import { renderConfirmDialog } from "./confirm-dialog.js";
import { renderSettingsGroup } from "./group.js";

const CSS = `
  [data-component="learn-group"] {
    display: flex;
    flex-direction: column;
    gap: var(--sp-2);
  }
  /* Session-window toast for "learn progress reset." (CR-04 fix).
   * Mirrors the Learn window's .learn-toast styling so the surface
   * feels identical across windows; sits near the top-center over
   * whatever surface owns the click. z-index high enough to clear
   * the drawer + any open dialog. The drawer dialog is dismissed
   * BEFORE this toast renders so they never overlap. */
  .vmx-learn-group__toast {
    position: fixed;
    top: var(--sp-5);
    left: 50%;
    transform: translateX(-50%);
    z-index: 9000;
    padding: var(--sp-3) var(--sp-5);
    /* Warm void glass; the v5 cool blue-black toast was the drawer's last
     * cold surface (structural neutral scrim + brand hairline). */
    background:
      linear-gradient(180deg, rgba(40, 35, 38, 0.92), rgba(26, 22, 24, 0.86)),
      rgba(0, 0, 0, 0.45);
    backdrop-filter: var(--blur-glass-light);
    -webkit-backdrop-filter: var(--blur-glass-light);
    border: 1px solid var(--brand-22);
    border-radius: var(--rad-md);
    box-shadow:
      0 12px 36px rgba(0, 0, 0, 0.5),
      0 0 18px var(--brand-08);
    font-family: var(--type-mono);
    font-size: 11px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--silk);
    pointer-events: none;
  }
  /* Destructive row — mirrors recording-row's delete-button pattern (silk-65
   * at rest, --led-fault on hover) but rendered as a full row instead of a
   * 24px icon button. No amber on this row (UI-SPEC §Color forbidden
   * colors: "ANY amber-family color on the 'I got it' skip button" pattern
   * applies here too — destructive is fail-recovery, not primary CTA). */
  [data-component="learn-group"] .vmx-settings-row {
    display: flex;
    flex-direction: column;
    gap: var(--sp-1);
    width: 100%;
    padding: 10px var(--sp-3);
    background: var(--glass-3);
    border: 1px solid var(--glass-edge);
    border-radius: var(--rad-sm);
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    color: inherit;
    transition: border-color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  [data-component="learn-group"] .vmx-settings-row:hover {
    border-color: var(--silk-22);
    background: var(--glass-1);
  }
  [data-component="learn-group"] .vmx-settings-row:focus-visible {
    outline: 1px solid var(--amber);
    outline-offset: 1px;
  }
  [data-component="learn-group"] .vmx-settings-row__label {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-65);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  [data-component="learn-group"] .vmx-settings-row__secondary {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 100, "wght" 400;
    font-size: 12px;
    color: var(--silk-40);
    line-height: 1.4;
    text-transform: none;
    letter-spacing: 0;
  }
  /* Destructive variant — silk-65 label flips to --led-fault on hover (the
   * "this will harm if confirmed" cue). Mirrors recording-row.ts:294-298. */
  [data-component="learn-group"] .vmx-settings-row--destructive:hover .vmx-settings-row__label {
    color: var(--led-fault);
    text-shadow: 0 0 4px rgba(212, 65, 58, 0.28);
  }
  [data-component="learn-group"] .vmx-settings-row--destructive:hover {
    border-color: rgba(212, 65, 58, 0.45);
    box-shadow: inset 0 0 8px rgba(212, 65, 58, 0.18);
  }
`;

registerStyle("vmx-learn-group", CSS);

/** Render the LEARN settings group. Pure-function — re-renders on every
 *  drawer refresh, same pattern as `HelpGroup` / `PerformanceGroup`.
 *
 *  Returns the `<section>` element ready to append into the drawer body
 *  between RECORDING and MASCOT.
 */
export function LearnGroup(): HTMLElement {
  // --- RESET LEARN PROGRESS row -------------------------------------------
  // Single row; click opens the destructive confirm dialog. Built as a
  // <button> so keyboard-Tab reaches it natively + Space/Enter activate it
  // without manual key handlers (the dialog component owns its own keyboard
  // trap). The .vmx-settings-row + .vmx-settings-row--destructive classes
  // are local to this group (no shared CSS class collision — recording-row
  // uses .vmx-rec-row__btn[data-kind="delete"]).
  const resetRow = document.createElement("button");
  resetRow.type = "button";
  resetRow.className = "vmx-settings-row vmx-settings-row--destructive";
  resetRow.setAttribute("aria-label", "reset learn progress");
  resetRow.title = "wipes ~/.cache/vibemix/learn-progress.json; confirm dialog gates the action";

  const label = document.createElement("div");
  label.className = "vmx-settings-row__label";
  label.textContent = "reset learn progress";
  resetRow.append(label);

  const secondary = document.createElement("div");
  secondary.className = "vmx-settings-row__secondary";
  secondary.textContent = "clears all completed lessons. cannot be undone.";
  resetRow.append(secondary);

  resetRow.addEventListener("click", (e) => {
    e.preventDefault();
    openResetConfirm();
  });

  // --- Group wrapper -------------------------------------------------------
  const group = renderSettingsGroup({
    header: "LEARN",
    children: [resetRow],
  });
  group.setAttribute("data-component", "learn-group");
  return group;
}

/** Open the destructive confirm dialog + wire the primary CTA to emit
 *  `ipc.learn.progress_state { action: "reset" }`. Cancel is a silent no-op.
 *
 *  The dialog mounts itself on top of the drawer (renderConfirmDialog
 *  appends a fixed-position backdrop to the DOM); we append it to
 *  document.body so it sits above the drawer's z-index 50.
 *
 *  Lifecycle: the dialog component itself does NOT auto-remove on
 *  confirm/cancel (see confirm-dialog.ts: only Esc + backdrop-click route
 *  to onCancel; the on-click callbacks just fire props.onConfirm/onCancel).
 *  We track the backdrop in a `let` and remove it from the DOM after each
 *  resolution. Deferred via queueMicrotask so the removal runs AFTER
 *  renderConfirmDialog returns — otherwise a synchronously-invoked test
 *  mock (which fires onConfirm during the call) would hit the TDZ for the
 *  not-yet-assigned `dialog` reference.
 */
function openResetConfirm(): void {
  let dialog: HTMLElement | null = null;
  const dismiss = (): void => {
    // queueMicrotask defers the removal one tick so synchronous-callback
    // test mocks (which fire onConfirm during renderConfirmDialog itself)
    // resolve cleanly — `dialog` is reliably assigned by the time the
    // microtask runs because renderConfirmDialog returns synchronously.
    queueMicrotask(() => {
      dialog?.remove();
      dialog = null;
    });
  };
  dialog = renderConfirmDialog({
    heading: "reset learn progress?",
    body:
      "all 36 lessons across 3 courses will reset to not started. " +
      "your library and DJ profile are not affected.",
    confirmLabel: "reset",
    cancelLabel: "cancel",
    variant: "danger",
    onConfirm: () => {
      // Optimistic dismiss FIRST — close the dialog locally before the
      // round-trip resolves. CR-04 fix: ALSO render a session-window
      // toast right here so the user sees confirmation in the window
      // they clicked from. The Learn window still surfaces its own
      // showLearnToast on reset_ack when it's open; the session toast
      // is the primary feedback for the drawer click. CLAUDE.md
      // optimistic-repaint rule — never wait on the round-trip.
      dismiss();
      showSessionLearnResetToast();
      void emitIpcReset();
    },
    onCancel: () => {
      // Silent no-op — no emit, no toast. Just dismiss the dialog.
      dismiss();
    },
  });
  document.body.append(dialog);
}

/** Fire-and-forget emit + console-warn on failure (no toast, no banner —
 *  the IPC layer's own retry/error UX owns the failure path). Matches the
 *  mascot-group.ts emitIpc-failure pattern. */
async function emitIpcReset(): Promise<void> {
  try {
    await emitIpc("ipc.learn.progress_state", { action: "reset" });
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("[learn-group] reset emitIpc failed:", err);
  }
}

/** CR-04 fix — render a local, transient toast in the Session window
 *  acknowledging the reset. Mirrors the Learn window's showLearnToast
 *  shape (one-line, 3s auto-dismiss) so the surface feels identical
 *  across windows. Optimistic: fires on the click, NOT on the round-trip
 *  ack (per CLAUDE.md "settings controls must repaint OPTIMISTICALLY").
 *
 *  No-op when document is undefined (vitest jsdom always supplies it,
 *  but the guard matches the showLearnToast pattern in learn-window.ts
 *  for symmetry).
 */
function showSessionLearnResetToast(): void {
  if (typeof document === "undefined") return;
  const t = document.createElement("div");
  t.className = "vmx-learn-group__toast";
  t.setAttribute("role", "alert");
  t.setAttribute("aria-live", "polite");
  t.textContent = "learn progress reset.";
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}
