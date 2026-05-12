/* Phase 11 Wave 2 — webview entry point.
 *
 * Mounts the crash banner subscription and logs every `ipc:*` event the
 * Rust shell forwards from the Python sidecar's WS bus. Validates each
 * frame against the Wave 0 ajv guard so schema drift surfaces in the
 * DevTools console (Wave 4 routes valid frames to wizard step handlers).
 *
 * Wave 3 replaces the placeholder copy + adds the wizard mount; Wave 4
 * adds the `parseIpcMessage` dispatch table. This file's job for Wave 2
 * is to make the IPC path visible end-to-end at the manual checkpoint.
 */

import { listen } from "@tauri-apps/api/event";

import { initCrashBanner } from "./crash-banner.js";
import { isIpcMessage, parseIpcMessage } from "./ipc/validator.js";

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

initCrashBanner();

// Pin the validator import so tree-shaking doesn't drop the schema check
// in production builds. Wave 4 deletes this when wizard handlers consume
// the validator directly.
export const _wave2KeepAlive = isIpcMessage;
