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
import { sendIpcRequest } from "./ipc/client.js";
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
const IPC_EVENTS = ["ipc-boot", "ipc-status-tick"] as const;

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

void listen<string>("ipc-parse-error", (event) => {
  // eslint-disable-next-line no-console
  console.warn("[ipc.parse-error] non-JSON frame:", event.payload);
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

/** Apply the user's "Lighter blur" performance preference to the document
 *  by writing/clearing the `data-blur-perf` attribute on <html>. tokens.css
 *  reads the attribute via the cascade rule
 *  `html[data-blur-perf="on"] { --blur-glass-* : … }` and swaps the heavy
 *  v5 blurs for lighter variants. The Settings → Performance toggle that
 *  flips this attribute live lands in Plan 14-04; this boot read keeps
 *  the surface honest from first paint when the preference is persisted.
 */
function applyBlurPerfPreference(lighter: boolean): void {
  if (lighter) document.documentElement.setAttribute("data-blur-perf", "on");
  else document.documentElement.removeAttribute("data-blur-perf");
}

/** Best-effort boot-time read of the `lighter_blur` performance setting.
 *
 *  Reads `ipc.settings.state` via the existing sidecar round-trip. Plan
 *  14-04 lands the field as a FLAT boolean at the top of
 *  `SettingsState.payload` (mirrors the existing `muted`/`voice`/... flat
 *  shape — no nested `performance.*` grouping). Until SettingsApplier
 *  persists the bit, the field is absent on the wire and this read
 *  gracefully returns false (the safe path: full blur on a missing field
 *  means newly-installed users get the full v5 visual contract).
 *
 *  Failure modes (all default to "off"):
 *   - Outside Tauri (Vite dev with no sidecar route)
 *   - Sidecar not yet ready (10s timeout in sendIpcRequest by default;
 *     we use a tighter 2s here so boot is never blocked on perf prefs)
 *   - Schema violation on the response
 *   - Field absent on a current/older sidecar build
 */
async function readBlurPerfPreference(): Promise<boolean> {
  try {
    const resp = (await sendIpcRequest(
      "ipc.settings.get",
      {},
      "ipc.settings.state",
      2000,
    )) as { payload?: Record<string, unknown> };
    // Plan 14-04 — flat boolean field on SettingsState.payload. Index
    // defensively so a missing field reads as "off" without ever throwing.
    const payload = resp?.payload as Record<string, unknown> | undefined;
    return payload?.["lighter_blur"] === true;
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("[boot] perf preference read failed:", err);
    return false;
  }
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

  // Apply boot-time perf-blur preference (CONTEXT Area 3). Reads from
  // the existing settings IPC; defaults off if the field is absent (the
  // safe path — full v5 visual contract). Plan 14-04 wires the Settings
  // drawer toggle that updates this attribute live. OS-level
  // prefers-reduced-motion is handled independently by the
  // @media (prefers-reduced-motion: reduce) block in tokens.css — that
  // cascade fires live on a11y toggle, no JS subscription needed here.
  applyBlurPerfPreference(await readBlurPerfPreference());

  // DEV-only: `?dev=session-mock` bypasses both the wizard check and the
  // Tauri IPC bridge — mounts the live session UI with a local animator
  // so Vite dev (no Tauri runtime) shows the Phase 12 surface moving.
  // Production builds strip this branch via import.meta.env.DEV.
  if (import.meta.env.DEV) {
    const params = new URLSearchParams(window.location.search);
    if (params.get("dev") === "session-mock") {
      // eslint-disable-next-line no-console
      console.log("[boot] DEV dev=session-mock → mounting mock session UI");
      const { routeSessionMock } = await import("./session/mock.js");
      await routeSessionMock();
      return;
    }
  }

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
