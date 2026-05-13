/* Phase 12 Wave 3 — session router entry point (Plan 12-04 §Steps 5).
 *
 * The wizard router (`src/wizard/router.ts`) owns step transitions before
 * first_run_completed flips true. After that, main.ts hands off to
 * `route.session()` from this file:
 *
 *   1. Tear down the wizard DOM (the wizard mount lives at #wizard-app).
 *   2. Mount the session DOM via `mountSessionLayout(root)`.
 *   3. Boot the IPC bridge (`initSessionBridge`) so SessionState starts
 *      getting writes from the sidecar.
 *   4. Start the rAF render loop reading SessionState.
 *
 * The session DOM occupies the whole window — we replace the wizard
 * container's children rather than swap a sibling node so the underlying
 * `body > #wizard-app` shell stays valid for the crash banner. */

import { initSessionBridge } from "./ws-bridge.js";
import { installQuitGuard } from "./quit-guard.js";
import { mountSessionLayout, type Mounted } from "./SessionLayout.js";
import { startRenderLoop, stopRenderLoop } from "./render-loop.js";
import { mountSessionShortcuts } from "./session-shortcuts.js";
import { mountSettingsDrawer } from "../settings/SettingsDrawer.js";

let mounted: Mounted | null = null;
let unsubscribeBridge: (() => void) | null = null;
let unsubscribeShortcuts: (() => void) | null = null;
let unsubscribeQuitGuard: (() => void) | null = null;

/** Mount the live session and start the bridge + render loop.
 *
 *  Idempotent — calling twice tears down the prior mount before
 *  starting fresh, so a hot-reload or a route bounce doesn't accumulate
 *  duplicate loops / DOM trees. */
export async function routeSession(rootEl?: HTMLElement): Promise<void> {
  // Find the mount root — fall back to the wizard container so we
  // replace its children if main.ts didn't provide an explicit root.
  const root =
    rootEl ??
    (document.getElementById("wizard-app") as HTMLElement | null) ??
    document.body;

  // Tear down any prior session mount (idempotency for hot-reload).
  await teardownSession();

  // Replace whatever the wizard left behind. The wizard's child tree
  // (titlebar / wizard-content / status-bar / crash-banner) is shed —
  // the session window is a wholly different layout. The crash-banner
  // is re-mounted by the session via its own status bar.
  root.replaceChildren();

  // Mount the layout. mountSessionLayout returns a Mounted handle the
  // render loop reads.
  const m = mountSessionLayout(root);
  mounted = m;

  // Mount the settings drawer + backdrop on top of the layout. Settings
  // are an overlay — they don't affect the live session render loop.
  mountSettingsDrawer(document.body);

  // Boot the bridge — subscribes to ipc.* events and fires settings.get.
  const { unsubscribeAll } = await initSessionBridge();
  unsubscribeBridge = unsubscribeAll;

  // Start the render loop. From this point on every snapshot tick
  // mutates SessionState → CSS variables / data attributes on screen.
  startRenderLoop(m);

  // Wire the impeccable Wave 5.A keyboard shortcuts (?/cmd+m/esc). The
  // drawer owns its own Esc; this wiring covers the session surface.
  unsubscribeShortcuts = mountSessionShortcuts();

  // Wave 6 (H5 error prevention) — install the beforeunload guard so an
  // accidental ⌘W/⌘R during a live recording surfaces the browser's
  // native confirm. The styled "STILL LIVE" dialog is reachable via
  // confirmQuitDuringRecording() — the Rust-side onCloseRequested
  // intercept that calls it is a TODO (Phase 17).
  unsubscribeQuitGuard = installQuitGuard();
}

/** Tear down the session — stop the rAF, unsubscribe IPC, drop the
 *  Mounted handle. The DOM is left in place; route.session() replaces
 *  the root's children on next mount. */
export async function teardownSession(): Promise<void> {
  stopRenderLoop();
  if (unsubscribeBridge) {
    try {
      unsubscribeBridge();
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[session-router] unsubscribe failed:", e);
    }
    unsubscribeBridge = null;
  }
  if (unsubscribeShortcuts) {
    try {
      unsubscribeShortcuts();
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[session-router] shortcut unsubscribe failed:", e);
    }
    unsubscribeShortcuts = null;
  }
  if (unsubscribeQuitGuard) {
    try {
      unsubscribeQuitGuard();
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[session-router] quit-guard unsubscribe failed:", e);
    }
    unsubscribeQuitGuard = null;
  }
  mounted = null;
}

/** Test-only — expose the mounted handle for vitest assertions. */
export function _getMountedForTests(): Mounted | null {
  return mounted;
}
