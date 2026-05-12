/* Phase 12 Wave 3 — webview entry point (Plan 12-04 §Steps 6).
 *
 * Boot decision (per plan must-have):
 *   1. Read first_run_state via the existing Phase 11 read_first_run_state
 *      Tauri command. If `first_run_completed === false` (or read fails) →
 *      mount the wizard (Phase 11 behaviour preserved).
 *   2. Otherwise → mount the live-session UI via the session router.
 *
 * The wizard's diagnostic subscribers (ipc.boot, ipc.status.tick,
 * ws-state, sidecar-error, ipc:parse-error) stay live in both modes —
 * the session UI consumes ipc.status.tick directly via its own bridge,
 * but the legacy console-log subscribers are kept for DevTools
 * visibility during structural checkpoint and Wave 4 settings work.
 *
 * The Wave 4 dev surface (window.__vibemixDev) is still gated on
 * import.meta.env.DEV so production strips it.
 */

import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

import { initCrashBanner } from "./crash-banner.js";
import { isIpcMessage, parseIpcMessage } from "./ipc/validator.js";
import { routeSession } from "./session/router.js";
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

// === Boot decision =======================================================

interface FirstRunStateView {
  first_run_completed?: boolean;
}

async function shouldShowWizard(): Promise<boolean> {
  // Phase 11 read_first_run_state Tauri command reads the
  // tauri-plugin-store-backed config.json. Returns the default record
  // (first_run_completed=false) when no record exists yet.
  try {
    const state = (await invoke("read_first_run_state")) as FirstRunStateView;
    return !state?.first_run_completed;
  } catch (err) {
    // Read failure → safest default is the wizard (first-run path).
    // eslint-disable-next-line no-console
    console.warn("[boot] read_first_run_state failed; defaulting to wizard:", err);
    return true;
  }
}

async function boot(): Promise<void> {
  consumeUrlParam();
  initCrashBanner();

  const wizardMode = await shouldShowWizard();

  if (wizardMode) {
    // Phase 11 path — render the wizard frame and hook the status bar.
    renderCurrentStep();
    void subscribeStatusBar();

    if (import.meta.env.DEV) {
      window.__vibemixDev = getDevSurface();
      // eslint-disable-next-line no-console
      console.log(
        "[boot] DEV mode — window.__vibemixDev exposed:",
        "advanceTo / currentStep / getState / setState / fakeMidiEvent / setStatusBar",
      );
    }
    return;
  }

  // Phase 12 path — mount the live session UI.
  // eslint-disable-next-line no-console
  console.log("[boot] first_run_completed=true → mounting live session");
  try {
    await routeSession();
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("[boot] routeSession failed:", err);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => void boot());
} else {
  void boot();
}

// Pin the validator import so tree-shaking doesn't drop the schema check
// in production builds.
export const _wave2KeepAlive = isIpcMessage;
