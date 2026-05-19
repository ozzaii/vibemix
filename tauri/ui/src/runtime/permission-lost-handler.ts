/* permission-lost-handler.ts — Phase 33 / INSTALL-06 / P71.
 *
 * Side-effect handler for runtime.permission_lost events from
 * tcc-watcher.ts. Pause audio capture, surface a toast, and offer a
 * re-grant button. Failures are isolated — pause + toast each run
 * inside a try/catch so a broken UI surface cannot crash the session.
 *
 * The handler returns a structured result so tests can assert
 * exactly which side-effects fired without coupling to a real
 * Tauri runtime.
 */

import type { PermissionLostEvent, TccPermissionName } from "./tcc-watcher.js";

export interface PermissionLostHandlerHooks {
  /** Pause audio capture (called once per revoke). */
  pauseAudioCapture: () => void;
  /** Render a toast — receives the user-facing copy. */
  showToast: (copy: string) => void;
  /** Render a "Grant again" affordance — receives the permission name
   *  so the consumer can open the right deep-link. */
  renderReGrantButton: (permission: TccPermissionName) => void;
}

export interface PermissionLostHandlerResult {
  paused: boolean;
  toastShown: boolean;
  reGrantRendered: boolean;
  copy: string;
}

const TOAST_COPY: Record<TccPermissionName, string> = {
  microphone: "Microphone access lost · paused",
  "screen-recording": "Screen recording access lost · paused",
  accessibility: "Accessibility access lost · paused",
  automation: "Automation access lost · paused",
};

export function handlePermissionLost(
  event: PermissionLostEvent,
  hooks: PermissionLostHandlerHooks,
): PermissionLostHandlerResult {
  const copy = TOAST_COPY[event.permission];
  const result: PermissionLostHandlerResult = {
    paused: false,
    toastShown: false,
    reGrantRendered: false,
    copy,
  };
  try {
    hooks.pauseAudioCapture();
    result.paused = true;
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("[permission-lost] pauseAudioCapture threw", err);
  }
  try {
    hooks.showToast(copy);
    result.toastShown = true;
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("[permission-lost] showToast threw", err);
  }
  try {
    hooks.renderReGrantButton(event.permission);
    result.reGrantRendered = true;
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("[permission-lost] renderReGrantButton threw", err);
  }
  return result;
}
