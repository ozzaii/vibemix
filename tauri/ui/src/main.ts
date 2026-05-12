/* Phase 11 Wave 3 — webview entry point.
 *
 * Mounts the calibration wizard (router.ts → step1 / step2 / step3 /
 * smoke-test). Keeps the Wave 2 crash banner + ipc.* event subscribers
 * for DevTools visibility during Wave 4 dev.
 *
 * Wave 3 drives every wizard state via MOCK data + a window.__vibemixDev
 * debug surface. Wave 4 strips the dev surface from production builds via
 * `import.meta.env.DEV` and wires the real ipc.* request flow.
 */

import { listen } from "@tauri-apps/api/event";

import { initCrashBanner } from "./crash-banner.js";
import { isIpcMessage, parseIpcMessage } from "./ipc/validator.js";
import { consumeUrlParam, getDevSurface, renderCurrentStep } from "./wizard/router.js";
import type { DevSurface } from "./wizard/router.js";

declare global {
  interface Window {
    __vibemixDev?: DevSurface;
  }
}

// === IPC subscribers ====================================================
// Wave 2 ipc:* logging — every event surfaces in DevTools so Kaan can
// confirm the WS bus pipe is alive during the watchdog smoke test.
const IPC_EVENTS = ["ipc:ipc.boot", "ipc:ipc.status.tick"] as const;

for (const channel of IPC_EVENTS) {
  listen<unknown>(channel, (event) => {
    try {
      const msg = parseIpcMessage(event.payload);
      // eslint-disable-next-line no-console
      console.log(`[${channel}]`, msg);
    } catch (err) {
      // Schema drift — log loudly. The frame is dropped, not auto-fixed.
      // eslint-disable-next-line no-console
      console.warn(`[${channel}] schema violation:`, err);
    }
  });
}

// Generic parse-error channel emitted by the Rust ws_client when text
// isn't JSON. Useful diagnostic during dev.
listen<string>("ipc:parse-error", (event) => {
  // eslint-disable-next-line no-console
  console.warn("[ipc:parse-error] non-JSON frame:", event.payload);
});

// Connect / reconnect state from the WS client.
listen<string>("ws-state", (event) => {
  // eslint-disable-next-line no-console
  console.log("[ws-state]", event.payload);
});

// One-shot error events from the sidecar process channel.
listen<string>("sidecar-error", (event) => {
  // eslint-disable-next-line no-console
  console.warn("[sidecar-error]", event.payload);
});

// === Wizard boot ========================================================
function boot(): void {
  consumeUrlParam();
  renderCurrentStep();
  initCrashBanner();

  // Wave 3 dev surface — register window.__vibemixDev. Wave 4 wraps
  // this in `if (import.meta.env.DEV) { ... }` so production builds
  // strip the surface (threat T-11-W3-02 mitigation).
  window.__vibemixDev = getDevSurface();
  // eslint-disable-next-line no-console
  console.log(
    "[boot] wizard ready — drive state via window.__vibemixDev:",
    "advanceTo / currentStep / getState / setState / fakeMidiEvent / setStatusBar"
  );
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}

// Pin the validator import so tree-shaking doesn't drop the schema check
// in production builds. Wave 4 deletes this when wizard handlers consume
// the validator directly.
export const _wave2KeepAlive = isIpcMessage;
