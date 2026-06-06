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

import { initCrashBanner, showFatalBanner } from "./crash-banner.js";
import { vmxLog } from "./debug-log.js";
import { isIpcMessage, parseIpcMessage } from "./ipc/validator.js";
// VIS-06 (43-06): rolling perf observer drives data-blur-perf ladder.
// Mount-side wiring is below in boot(); unmount fires on window unload.
// The observer is idempotent + cheap (single rAF chain), so we run it
// for the lifetime of the webview regardless of which surface is mounted
// (wizard vs live session) — both surfaces use the same tokens.css
// blur primitives gated on [data-blur-perf="on"].
import {
  startPerfObserver,
  stopPerfObserver,
  type PerfHandle,
} from "./mascot/perf-observer.js";
import {
  consumeUrlParam,
  getDevSurface,
  renderCurrentStep,
  subscribeStatusBar,
} from "./wizard/router.js";
import { invokeTauri, listenTauri } from "./tauri-runtime.js";
import type { DevSurface } from "./wizard/router.js";

declare global {
  interface Window {
    __vibemixDev?: DevSurface;
  }
}

// === Global error trap (Category 5 — CRITICAL) ===========================
// Install BEFORE any boot logic runs so an init-time throw or a rejected
// boot promise is loud in BOTH the console and the on-disk ui.log. A
// headless operator otherwise sees a blank window with no signal. Guarded
// on `window` so the module stays importable in a non-DOM test env.
if (typeof window !== "undefined") {
  window.addEventListener("error", (event: ErrorEvent) => {
    const err = event.error;
    vmxLog("[vmx:error]", "uncaught error", {
      message: event.message,
      source: event.filename,
      line: event.lineno,
      col: event.colno,
      stack: err instanceof Error ? err.stack : undefined,
    });
  });
  window.addEventListener("unhandledrejection", (event: PromiseRejectionEvent) => {
    const reason = event.reason;
    vmxLog("[vmx:error]", "unhandled promise rejection", {
      reason:
        reason instanceof Error
          ? { message: reason.message, stack: reason.stack }
          : String(reason),
    });
  });
}

// === DevTools diagnostic subscribers (one-shot only — status.tick is 1Hz
// so logging it floods devtools; it's still consumed by the status bar
// subscriber in wizard/router.ts which renders the LED dots).
const IPC_EVENTS = ["ipc-boot"] as const;

for (const channel of IPC_EVENTS) {
  void listenTauri<unknown>(channel, (event) => {
    try {
      const msg = parseIpcMessage(event.payload);
      // eslint-disable-next-line no-console
      console.log("[ipc]", channel, msg);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn("[ipc] schema violation:", channel, err);
    }
  });
}

void listenTauri<string>("ipc-parse-error", (event) => {
  // eslint-disable-next-line no-console
  console.warn("[ipc.parse-error] non-JSON frame:", event.payload);
});

void listenTauri<string>("ws-state", (event) => {
  vmxLog("[vmx:ws]", "rust bridge ws-state", { state: event.payload });
});

void listenTauri<string>("sidecar-error", (event) => {
  vmxLog("[vmx:error]", "sidecar-error", { detail: event.payload });
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
    const state = (await invokeTauri("read_first_run_state")) as FirstRunStateView;
    return !state?.first_run_completed;
  } catch (err) {
    // Read failure → safest default is the wizard (first-run path).
    // eslint-disable-next-line no-console
    console.warn("[boot] read_first_run_state failed; defaulting to wizard:", err);
    return true;
  }
}

async function boot(): Promise<void> {
  vmxLog("[vmx:state]", "boot: start", { readyState: document.readyState });
  consumeUrlParam();
  initCrashBanner();

  // Tag the document with the runtime so CSS can scope native-only effects.
  // Window vibrancy (main.rs apply_main_native_material) needs a transparent
  // shell body to reveal the NSVisualEffectView; in plain Vite/browser dev
  // there is no vibrancy behind it, so that transparency would bleed white
  // through the chrome + sidebar glass. shell.css gates the transparency on
  // html[data-runtime="tauri"], set here from the live Tauri internals probe.
  document.documentElement.dataset.runtime =
    typeof (window as Window & { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ ===
    "object"
      ? "tauri"
      : "web";

  // The session bridge applies the persisted lighter-blur preference from
  // ipc.settings.state once the sidecar is connected. Keeping this boot path
  // non-blocking avoids a false timeout during sidecar startup.

  // VIS-06 (43-06): start the runtime perf observer alongside the
  // boot-time preference. If the persisted preference already flipped
  // the attribute "on", the observer noops on the flip path (it checks
  // the attribute before setting). If the preference is "off" but
  // runtime frame times degrade (integrated GPU, background load), the
  // observer flips the attribute live and tokens.css picks up the new
  // blur primitives on the next paint. Sticky-for-session per the
  // T-43-06-03 mitigation in perf-observer.ts. Unmount handler wires
  // pagehide so the rAF chain is released when the webview unloads.
  const perfHandle: PerfHandle = startPerfObserver();
  window.addEventListener("pagehide", () => stopPerfObserver(perfHandle), {
    once: true,
  });

  // DEV-only: `?dev=session-mock` bypasses both the wizard check and the
  // Tauri IPC bridge — mounts the live session UI with a local animator
  // so Vite dev (no Tauri runtime) shows the Phase 12 surface moving.
  // Production builds strip this branch via import.meta.env.DEV.
  if (import.meta.env.DEV) {
    const params = new URLSearchParams(window.location.search);
    if (params.get("dev") === "session-mock") {
      vmxLog("[vmx:state]", "boot → mock session UI (dev=session-mock)");
      const { routeSessionMock } = await import("./session/mock.js");
      await routeSessionMock();
      return;
    }
    // `?dev=shell` mounts the cohesive shell directly (bypassing the Tauri
    // first-run check) so the folded app can be eyeballed in pure Vite dev.
    if (params.get("dev") === "shell") {
      vmxLog("[vmx:state]", "boot → shell app (dev=shell)");
      // Shed the static #wizard-app skeleton so it doesn't push the shell off
      // the fold (mirrors the production boot path below).
      document.getElementById("wizard-app")?.remove();
      const { mountShellApp } = await import("./shell/app.js");
      const host = document.createElement("div");
      document.body.appendChild(host);
      await mountShellApp(host);
      return;
    }
  }

  const wizardMode = await shouldShowWizard();
  vmxLog("[vmx:state]", "boot: surface decided", {
    surface: wizardMode ? "wizard" : "session",
  });

  if (wizardMode) {
    // Phase 11 path — render the wizard frame and hook the status bar.
    renderCurrentStep();
    void subscribeStatusBar();

    if (import.meta.env.DEV) {
      window.__vibemixDev = getDevSurface();
      // eslint-disable-next-line no-console
      console.log(
        "[boot] DEV mode — window.__vibemixDev exposed:",
        "advanceTo / currentStep / getState / setState / setStatusBar",
      );
    }
    return;
  }

  // v6 tozpembe path — mount the cohesive shell app. The deck surface IS the
  // live session (routeSession folds onto the deck stage); Viber/Learn/Settings
  // fold in alongside. The shell takes over the window body, so the crash banner
  // is hoisted out of #wizard-app first (its refs are cached in crash-banner.ts,
  // so a later sidecar crash still surfaces), then the static wizard skeleton is
  // shed.
  vmxLog("[vmx:state]", "boot → mounting shell app");
  try {
    const banner = document.getElementById("crash-banner");
    if (banner && banner.parentElement !== document.body) {
      document.body.appendChild(banner);
    }
    document.getElementById("wizard-app")?.remove();
    const shellHost = document.createElement("div");
    document.body.appendChild(shellHost);
    const { mountShellApp } = await import("./shell/app.js");
    await mountShellApp(shellHost);
    vmxLog("[vmx:state]", "boot: shell app mounted");
  } catch (err) {
    // Without surfacing this, the user sees a blank window with no
    // indication anything failed. Route through the existing crash
    // banner so the Restart button is reachable — restart_sidecar
    // bounces the Python process which is usually enough to recover
    // (the webview reloads on app restart anyway).
    const detail = err instanceof Error ? err.message : String(err);
    vmxLog("[vmx:error]", "shell app mount failed", {
      detail,
      stack: err instanceof Error ? err.stack : undefined,
    });
    showFatalBanner("session-mount-failed", `App UI failed to mount: ${detail}`);
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
