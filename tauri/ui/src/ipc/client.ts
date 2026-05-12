/* Phase 11 Wave 4 — IPC request / response client.
 *
 * Single entry point for every webview→sidecar interaction in the wizard.
 * Three shapes:
 *
 *   1. ``sendIpcRequest(reqType, payload, resType)`` — one-shot
 *      request expecting exactly one reply of type ``resType``.
 *      Rejects on 10s timeout (RESEARCH Pitfall 6) so a crashed
 *      sidecar surfaces as a crash banner, not a hung spinner.
 *
 *   2. ``subscribeIpc(type, callback)`` — long-lived subscription to
 *      a stream of ipc.* events (status.tick, calibration.smoke_test_started,
 *      etc.). Returns an unsubscribe fn.
 *
 *   3. ``emitIpc(type, payload)`` — fire-and-forget. Used for
 *      ``ipc.calibration.user_heard_tone`` (correlated by ts) and
 *      ``ipc.wizard.done``.
 *
 * Wire-up:
 *   Webview → invoke("forward_ipc_to_sidecar", { message }) → Tauri Rust
 *           → ws_client.tx.send(JSON) → Python WizardLoop.
 *   Python WizardLoop.emit(...) → ws → Rust ws_client.run → emit ipc:type
 *           → @tauri-apps/api/event listen → callback here.
 *
 * Validation: every inbound event runs through ``parseIpcMessage`` (the
 * compiled ajv guard from Wave 0). Schema-violating frames are dropped
 * with a console warning — Wave 0's CI gate is the build-time twin.
 *
 * Warning #4 — Window picker is a WS-path ipc.* request, NOT a Tauri
 * command. The webview MUST NOT invoke a window-enum command — Wave 4's
 * grep gate fails the verifier if any such call sneaks in.
 */

import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

import type { VibemixIPCMessages as IpcMessage } from "./messages.js";
import { parseIpcMessage } from "./validator.js";

const REQUEST_TIMEOUT_MS = 10_000;

/** Send a one-shot request expecting exactly one reply of the named type.
 *
 * Rejects on:
 *   * 10s timeout (Pitfall 6 — surfaces sidecar crashes mid-request as
 *     the Tauri crash banner, not a hung wizard UI).
 *   * Schema violation on the response (parseIpcMessage throws).
 *   * Tauri invoke failure (e.g., WS not connected — Rust returns the
 *     "WS not connected" error from forward_ipc_to_sidecar).
 *
 * The optional ``timeoutMs`` override exists for the smoke-test step
 * which legitimately needs a longer window for the cascade greeting.
 */
export async function sendIpcRequest<TResponse extends IpcMessage = IpcMessage>(
  requestType: string,
  requestPayload: Record<string, unknown>,
  responseType: string,
  timeoutMs: number = REQUEST_TIMEOUT_MS,
): Promise<TResponse> {
  const requestMessage = {
    type: requestType,
    ts: new Date().toISOString(),
    payload: requestPayload,
  };

  // Subscribe to the response channel FIRST, then send the request — closes
  // the race window where a fast sidecar reply could arrive before the
  // listener is attached.
  return new Promise<TResponse>((resolve, reject) => {
    let unlisten: UnlistenFn | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const cleanup = (): void => {
      if (timer !== null) {
        clearTimeout(timer);
        timer = null;
      }
      if (unlisten !== null) {
        unlisten();
        unlisten = null;
      }
    };

    timer = setTimeout(() => {
      cleanup();
      reject(new Error(`ipc timeout: no ${responseType} within ${timeoutMs}ms`));
    }, timeoutMs);

    listen<unknown>(`ipc:${responseType}`, (event) => {
      try {
        const msg = parseIpcMessage(event.payload) as TResponse;
        cleanup();
        resolve(msg);
      } catch (err) {
        // Schema violation on the response — drop the frame, keep
        // waiting until the next valid one or the timeout fires.
        // eslint-disable-next-line no-console
        console.warn(`[ipc:${responseType}] schema violation:`, err);
      }
    })
      .then((fn) => {
        unlisten = fn;
        // Send the request after the listener is attached.
        invoke("forward_ipc_to_sidecar", { message: requestMessage }).catch((err) => {
          cleanup();
          reject(new Error(`ipc invoke failed: ${String(err)}`));
        });
      })
      .catch((err) => {
        cleanup();
        reject(new Error(`ipc listen failed: ${String(err)}`));
      });
  });
}

/** Subscribe to a stream of ipc.* events of a given type. Returns an
 * async unsubscribe fn. Use for status.tick + smoke_test_started +
 * any future broadcast channel.
 */
export async function subscribeIpc<T extends IpcMessage = IpcMessage>(
  type: string,
  callback: (msg: T) => void,
): Promise<UnlistenFn> {
  return await listen<unknown>(`ipc:${type}`, (event) => {
    try {
      const msg = parseIpcMessage(event.payload) as T;
      callback(msg);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn(`[ipc:${type}] schema violation:`, err);
    }
  });
}

/** Fire-and-forget: send a message to the sidecar; no response awaited.
 *
 * Used for ``ipc.calibration.user_heard_tone`` (correlated by ts at the
 * sidecar) and ``ipc.wizard.done`` (sidecar exits after acknowledging).
 */
export async function emitIpc(
  type: string,
  payload: Record<string, unknown>,
): Promise<void> {
  await invoke("forward_ipc_to_sidecar", {
    message: { type, ts: new Date().toISOString(), payload },
  });
}

export const _REQUEST_TIMEOUT_MS_FOR_TESTS = REQUEST_TIMEOUT_MS;
export type { IpcMessage };
