/* session-shortcuts.ts — wires the global shortcut registry into the live
 * session surface (impeccable Wave 5.A).
 *
 * Three shortcuts:
 *   `?`     → toggle the shortcuts overlay (skipped if the drawer is
 *             already open — settings owns its own Esc handler and we
 *             don't want to stack overlays on top of it).
 *   `cmd+m` / `ctrl+m` → toggle mute via the existing ws-bridge `sendMute`
 *             IPC. The sidecar replies with the new muted state which the
 *             cohost panel's inline breathing pill renders on the snapshot
 *             tick (the standalone muted-banner is currently inactive —
 *             see `components/muted-banner.ts` header for context).
 *   `esc`   → close the shortcuts overlay if open; otherwise no-op (the
 *             drawer's own Esc handler takes precedence when it's open).
 *
 * Called from `routeSession()` after the layout is mounted; returns an
 * unregister handle the router can call on teardown to drop the
 * keyboard listener. */

import { getSettingsUIState } from "../settings/state.js";
import {
  isShortcutsOverlayMounted,
  mountShortcutsOverlay,
  getShortcutsOverlayHandle,
} from "./components/shortcuts-overlay.js";
import { registerShortcuts, type Unregister } from "./shortcuts.js";
import { sendMute } from "./ws-bridge.js";

/** Wire the session-wide keyboard shortcuts. Returns an unregister fn. */
export function mountSessionShortcuts(): Unregister {
  return registerShortcuts({
    "?": () => toggleShortcutsOverlay(),
    "cmd+m": () => toggleMute(),
    // cmd+m on mac resolves to meta+m; on win/linux the same combo string
    // resolves to ctrl+m through the platform branch in parseCombo. We
    // also register ctrl+m explicitly so a mac user pressing ctrl+m
    // (some external keyboard layouts) hits the same path.
    "ctrl+m": () => toggleMute(),
    "escape": () => closeAnyOverlay(),
  });
}

function toggleShortcutsOverlay(): void {
  // If the settings drawer owns the surface, defer — `?` shouldn't stack
  // an overlay on top of an open drawer.
  try {
    if (getSettingsUIState().open) return;
  } catch {
    /* drawer state not mounted (tests) — proceed */
  }
  if (isShortcutsOverlayMounted()) {
    getShortcutsOverlayHandle()?.unmount();
    return;
  }
  mountShortcutsOverlay();
}

function toggleMute(): void {
  // Fire-and-forget; the sidecar replies with the new state which the
  // ws-bridge writes to SessionState.muted.
  void sendMute(true).catch((err) => {
    // eslint-disable-next-line no-console
    console.warn("[session-shortcuts] sendMute failed:", err);
  });
}

function closeAnyOverlay(): void {
  if (isShortcutsOverlayMounted()) {
    getShortcutsOverlayHandle()?.unmount();
    return;
  }
  // Drawer is handled by the drawer's own keydown listener. No-op here.
}
