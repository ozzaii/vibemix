/* Safe wrappers around Tauri APIs.
 *
 * The @tauri-apps/api modules are importable in plain Vite/Playwright, but
 * calling event.listen() outside a Tauri webview rejects while trying to reach
 * window.__TAURI_INTERNALS__. These helpers keep browser/dev smokes quiet
 * without masking real backend errors inside Tauri: invoke still rejects to the
 * caller, while listeners degrade to inert noops when the runtime is absent.
 */

import { invoke as tauriInvoke } from "@tauri-apps/api/core";
import { listen as tauriListen, type UnlistenFn } from "@tauri-apps/api/event";

export type { UnlistenFn };

export function invokeTauri<T = unknown>(
  cmd: string,
  args?: Record<string, unknown>,
): Promise<T> {
  return tauriInvoke<T>(cmd, args);
}

export function listenTauri<T>(
  event: string,
  handler: Parameters<typeof tauriListen<T>>[1],
): Promise<UnlistenFn> {
  return tauriListen<T>(event, handler).catch(() => () => {});
}
