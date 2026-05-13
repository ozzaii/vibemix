/* quit-guard.ts — confirm-on-quit when the user closes the window during
 * a live recording session (impeccable Wave 6, closes H5 "error
 * prevention").
 *
 * Two surfaces:
 *
 *   1. `beforeunload` listener — the browser-native confirm dialog the
 *      user sees if the renderer is torn down without a Tauri-side
 *      intercept (Cmd+W reload in dev, or any path where the Rust shell
 *      doesn't get the close request first). When `isRecording()` returns
 *      true we set returnValue + preventDefault so the browser shows its
 *      native "Leave this page?" prompt.
 *
 *   2. `confirmQuitDuringRecording()` — the styled confirm-dialog the
 *      Tauri shell SHOULD call from `onCloseRequested` (Rust-side
 *      intercept; TODO Phase 17 — we don't wire Rust here, just ship the
 *      JS surface so the wiring lands when the Rust intercept does).
 *      Tests pin this path.
 *
 * Why both? Tauri 2's webview surfaces `beforeunload` only for
 * navigation, not for OS-level close. To intercept the close button we'd
 * need a Rust-side `app.on_window_event` handler emitting an IPC event
 * back to the renderer (TODO). Until then the beforeunload listener is
 * the only thing standing between an in-flight recording and an
 * accidental ⌘W during a calibration pass.
 *
 * The recording-active check uses `status.livekit === "ok"` as a proxy
 * for "session is recording" — the recording pipeline (cohost_v4.py)
 * writes WAVs continuously once the LiveKit session is up, so an "ok"
 * livekit pill is functionally equivalent to "recording in progress". */

import { renderConfirmDialog } from "../settings/components/confirm-dialog.js";
import { getSessionState } from "./state.js";

/** Returns true when the cohost is actively recording — currently a proxy
 *  for "livekit session is up". Exported for tests. */
export function isRecording(): boolean {
  try {
    return getSessionState().status.livekit === "ok";
  } catch {
    return false;
  }
}

/** Mount the styled "STILL LIVE" confirm dialog and resolve with the
 *  user's choice. The dialog auto-focuses Cancel so an accidental Enter
 *  doesn't drop the recording.
 *
 *  The Rust-side `onCloseRequested` handler should call this and only
 *  forward the close IPC when the returned promise resolves to `true`.
 *
 *  For browser-level beforeunload we can't use this (no async path); the
 *  beforeunload listener uses the native browser confirm instead. */
export function confirmQuitDuringRecording(
  parent: HTMLElement = document.body,
): Promise<boolean> {
  return new Promise((resolve) => {
    const dialog = renderConfirmDialog({
      heading: "STILL LIVE",
      body: "your set is recording. quit anyway?",
      confirmLabel: "QUIT ANYWAY",
      cancelLabel: "STAY",
      variant: "danger",
      onCancel: () => {
        dialog.remove();
        resolve(false);
      },
      onConfirm: () => {
        dialog.remove();
        resolve(true);
      },
    });
    parent.append(dialog);
  });
}

/** Wire the browser-level beforeunload listener. Returns an unregister
 *  function the router calls on session teardown.
 *
 *  This is the SAFETY NET. The primary surface is the Rust-side
 *  onCloseRequested → confirmQuitDuringRecording() path; that's a TODO.
 *  In the meantime, beforeunload covers ⌘W / ⌘R / browser-pane reload. */
export function installQuitGuard(): () => void {
  const listener = (e: BeforeUnloadEvent): string | undefined => {
    if (!isRecording()) return undefined;
    // Modern browsers ignore the message but require both calls + a
    // returnValue setter to surface their built-in confirm.
    e.preventDefault();
    e.returnValue = "your set is recording. quit anyway?";
    return "your set is recording. quit anyway?";
  };
  window.addEventListener("beforeunload", listener);
  return (): void => {
    window.removeEventListener("beforeunload", listener);
  };
}
