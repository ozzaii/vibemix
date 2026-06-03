/* Safe wrappers around Tauri APIs.
 *
 * The @tauri-apps/api modules are importable in plain Vite/Playwright, but
 * calling event.listen() outside a Tauri webview rejects while trying to reach
 * window.__TAURI_INTERNALS__. These helpers keep browser/dev smokes quiet
 * without masking real backend errors inside Tauri: invoke still rejects to the
 * caller, while listeners degrade to inert noops when the runtime is absent.
 */

import { invoke as tauriInvoke } from "@tauri-apps/api/core";
import {
  emit as tauriEmit,
  listen as tauriListen,
  type UnlistenFn,
} from "@tauri-apps/api/event";

export type { UnlistenFn };

export function invokeTauri<T = unknown>(
  cmd: string,
  args?: Record<string, unknown>,
): Promise<T> {
  if (!hasTauriInternals()) {
    return Promise.reject(new Error("Tauri runtime unavailable"));
  }
  return tauriInvoke<T>(cmd, args);
}

export function listenTauri<T>(
  event: string,
  handler: Parameters<typeof tauriListen<T>>[1],
): Promise<UnlistenFn> {
  if (!hasTauriInternals()) {
    return Promise.resolve(() => {});
  }
  try {
    return tauriListen<T>(event, handler).catch(() => () => {});
  } catch {
    return Promise.resolve(() => {});
  }
}

export function emitTauri<T = unknown>(event: string, payload?: T): Promise<void> {
  if (!hasTauriInternals()) {
    return Promise.resolve();
  }
  try {
    return tauriEmit(event, payload).catch(() => {});
  } catch {
    return Promise.resolve();
  }
}

function hasTauriInternals(): boolean {
  if (typeof window === "undefined") return false;
  const w = window as Window & { __TAURI_INTERNALS__?: unknown };
  return typeof w.__TAURI_INTERNALS__ === "object" && w.__TAURI_INTERNALS__ !== null;
}
