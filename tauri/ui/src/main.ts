/* Phase 11 Wave 4 — webview entry point.
 *
 * Boot order:
 *   1. Mount the wizard frame DOM (renderCurrentStep — initially Step 1).
 *   2. Subscribe to ipc.status.tick so the 4 LED dots in the status bar
 *      stay live as the sidecar's heartbeat probes report.
 *   3. Wait for the sidecar's ipc.boot event (proves the WS bus is alive).
 *      If it doesn't arrive within 5s, surface the crash banner via the
 *      sidecar-error channel.
 *   4. Strip ``window.__vibemixDev`` from production builds via
 *      ``import.meta.env.DEV`` (threat T-11-W3-02 mitigation).
 *
 * The Wave 3 console-log subscribers (ipc.boot, ipc.status.tick, ws-state,
 * sidecar-error, ipc:parse-error) are kept for DevTools visibility during
 * the structural-gate manual checkpoint.
 */

import { listen } from "@tauri-apps/api/event";

import { initCrashBanner } from "./crash-banner.js";
import { isIpcMessage, parseIpcMessage } from "./ipc/validator.js";
import {
  consumeUrlParam,
  getDevSurface,
  renderCurrentStep,
  subscribeStatusBar,
} from "./wizard/router.js";
import type { DevSurface } from "./wizard/router.js";

declare global {
  interface Window {
    __vibemixDev?: DevSurface;
  }
}

// === DevTools diagnostic subscribers (Wave 2 + Wave 4 logging) ===========
const IPC_EVENTS = ["ipc:ipc.boot", "ipc:ipc.status.tick"] as const;

for (const channel of IPC_EVENTS) {
  void listen<unknown>(channel, (event) => {
    try {
      const msg = parseIpcMessage(event.payload);
      // eslint-disable-next-line no-console
      console.log(`[${channel}]`, msg);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn(`[${channel}] schema violation:`, err);
    }
  });
}

void listen<string>("ipc:parse-error", (event) => {
  // eslint-disable-next-line no-console
  console.warn("[ipc:parse-error] non-JSON frame:", event.payload);
});

void listen<string>("ws-state", (event) => {
  // eslint-disable-next-line no-console
  console.log("[ws-state]", event.payload);
});

void listen<string>("sidecar-error", (event) => {
  // eslint-disable-next-line no-console
  console.warn("[sidecar-error]", event.payload);
});

// === Wizard boot =========================================================
function boot(): void {
  consumeUrlParam();
  renderCurrentStep();
  initCrashBanner();

  // Wire the status bar to ipc.status.tick (1Hz heartbeat).
  void subscribeStatusBar();

  // Wave 4: only expose the dev surface in dev builds. Production
  // bundles strip __vibemixDev entirely (threat T-11-W3-02 mitigation).
  if (import.meta.env.DEV) {
    window.__vibemixDev = getDevSurface();
    // eslint-disable-next-line no-console
    console.log(
      "[boot] DEV mode — window.__vibemixDev exposed:",
      "advanceTo / currentStep / getState / setState / fakeMidiEvent / setStatusBar",
    );
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}

// Pin the validator import so tree-shaking doesn't drop the schema check
// in production builds.
export const _wave2KeepAlive = isIpcMessage;
