/* quit-guard.ts — confirm-on-quit when the user closes the window during
 * an active live session (impeccable Wave 6 + pass-3 Rust wiring).
 *
 * Three surfaces:
 *
 *   1. `beforeunload` listener — browser-native confirm if the renderer
 *      is torn down without going through the Tauri event channel
 *      (Cmd+W reload in dev, browser-pane refresh). Native dialog only.
 *
 *   2. `confirmQuitDuringRecording()` — styled CDJ-Whisper confirm
 *      dialog. Called by `installTrayQuitListener()` when the tray Quit
 *      menu emits `tray-quit-requested`.
 *
 *   3. `installTrayQuitListener()` — the load-bearing path. Listens for
 *      the `tray-quit-requested` event from the Rust shell (emitted by
 *      tray.rs::handle_menu_event on Quit menu click). If `isRecording()`
 *      is false → immediately emit `confirmed-quit` back to Rust. Else →
 *      mount the styled dialog; on "Quit anyway" emit `confirmed-quit`;
 *      on "Stay" do nothing (Rust falls back to exit after 1.5s if no ack,
 *      but the dialog should resolve before then).
 *
 * Pass-3 critique (2026-05-14) closes the H5 gap (was 3/4 → 4/4) by
 * wiring the Rust tray-side handshake. Cmd+Q on a live recording no
 * longer drops the take.
 *
 * The active-live-session check uses `runState === "running"` — the deck's
 * activation state (boots "armed", flips on Start, reconciled by the
 * backend's run_state snapshot). It deliberately does NOT read
 * `status.livekit`: the 1Hz status tick emits livekit="ok" from boot,
 * idle included (ws_bus.py STATUS_EVERY_N contract, never-faults by
 * construction), so keying off it armed the guard forever — quitting an
 * IDLE app threw the "STILL LIVE" dialog. It is intentionally not called
 * "recording" here: the UI carries no recorder-active bit, so the guard
 * protects the running session without claiming more than it can prove. */

import { renderConfirmDialog } from "../settings/components/confirm-dialog.js";
import { emitTauri, listenTauri, type UnlistenFn } from "../tauri-runtime.js";
import { getSessionState } from "./state.js";

/** Returns true when the cohost has an active live session. Exported for tests. */
export function isLiveSessionActive(): boolean {
  try {
    return getSessionState().runState === "running";
  } catch {
    return false;
  }
}

/** Back-compat alias for older tests/importers. Prefer isLiveSessionActive. */
export const isRecording = isLiveSessionActive;

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
      body: "your live session is running. quit anyway?",
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
 *  Safety-net for ⌘W / ⌘R / browser-pane reload paths that route around
 *  the Tauri event channel. The PRIMARY recording-safety surface is
 *  `installTrayQuitListener()` below — that intercepts the actual OS-level
 *  Quit menu click. */
export function installQuitGuard(): () => void {
  const listener = (e: BeforeUnloadEvent): string | undefined => {
    if (!isLiveSessionActive()) return undefined;
    e.preventDefault();
    e.returnValue = "your live session is running. quit anyway?";
    return "your live session is running. quit anyway?";
  };
  window.addEventListener("beforeunload", listener);
  return (): void => {
    window.removeEventListener("beforeunload", listener);
  };
}

/** Wire the Tauri tray-quit-requested → confirmed-quit handshake. The
 *  Rust shell (tray.rs::handle_menu_event MENU_ID_QUIT) emits
 *  `tray-quit-requested` instead of calling `app.exit(0)` directly. We
 *  decide here whether to confirm or pass straight through, then emit
 *  `confirmed-quit` (exit) or `quit-cancelled` (cancel the Rust-side
 *  1.5s fallback timer) so the user's Stay choice is honored. Returns
 *  an unregister function. */
export async function installTrayQuitListener(): Promise<() => void> {
  let dialogOpen = false;
  const unlisten: UnlistenFn = await listenTauri("tray-quit-requested", () => {
    if (dialogOpen) return;
    if (!isLiveSessionActive()) {
      void emitTauri("confirmed-quit");
      return;
    }
    dialogOpen = true;
    void confirmQuitDuringRecording().then((confirmed) => {
      dialogOpen = false;
      if (confirmed) {
        void emitTauri("confirmed-quit");
      } else {
        // Cancel the Rust-side fallback timer — Stay must be honored.
        void emitTauri("quit-cancelled");
      }
    });
  });
  return unlisten;
}
