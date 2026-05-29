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

import { vmxLog } from "../debug-log.js";
import { invokeTauri, listenTauri, type UnlistenFn } from "../tauri-runtime.js";
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

  vmxLog("[vmx:ipc>]", `request ${requestType} → expect ${responseType}`, {
    payload: requestPayload,
  });

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
      vmxLog("[vmx:error]", `ipc timeout: no ${responseType} within ${timeoutMs}ms`, {
        requestType,
      });
      reject(new Error(`ipc timeout: no ${responseType} within ${timeoutMs}ms`));
    }, timeoutMs);

    listenTauri<unknown>(responseType.replace(/\./g, "-"), (event) => {
      try {
        const msg = parseIpcMessage(event.payload) as TResponse;
        cleanup();
        vmxLog("[vmx:ipc<]", `response ${responseType}`, { payload: msg });
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
        invokeTauri("forward_ipc_to_sidecar", { message: requestMessage }).catch((err) => {
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
  vmxLog("[vmx:ipc<]", `subscribe ${type}`);
  return await listenTauri<unknown>(type.replace(/\./g, "-"), (event) => {
    try {
      const msg = parseIpcMessage(event.payload) as T;
      // High-frequency stream types (status.tick @1Hz, session.snapshot @up to
      // 30Hz) would flood ui.log — throttle them. Low-frequency / event types
      // (reactions, settings.state, anything else) log every frame so a
      // headless operator sees the reaction land immediately.
      logSubscribedFrame(type, msg);
      callback(msg);
    } catch (err) {
      vmxLog("[vmx:error]", `ipc subscribe schema violation: ${type}`, {
        err: String(err),
      });
    }
  });
}

/** Per-stream-type last-logged-at (ms) for throttling the high-frequency
 *  subscribed frames in the on-disk log. */
const _subThrottleAt = new Map<string, number>();
const _SUB_THROTTLE_MS = 2000;
/** Stream types that arrive often enough to flood the log — summarise at most
 *  every _SUB_THROTTLE_MS. Everything else logs every frame. */
const _HIGH_FREQ_TYPES = new Set([
  "ipc.status.tick",
  "ipc.session.snapshot",
  "ipc.learn.midi_position",
]);

function logSubscribedFrame(type: string, msg: unknown): void {
  if (_HIGH_FREQ_TYPES.has(type)) {
    const now = Date.now();
    const last = _subThrottleAt.get(type) ?? 0;
    if (now - last < _SUB_THROTTLE_MS) return;
    _subThrottleAt.set(type, now);
    vmxLog("[vmx:ipc<]", `frame ${type} (throttled ${_SUB_THROTTLE_MS}ms)`, msg);
    return;
  }
  vmxLog("[vmx:ipc<]", `frame ${type}`, msg);
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
  vmxLog("[vmx:ipc>]", `emit ${type} (fire-and-forget)`, { payload });
  await invokeTauri("forward_ipc_to_sidecar", {
    message: { type, ts: new Date().toISOString(), payload },
  });
}

// ---------------------------------------------------------------------------
// Phase 15 Plan 03 — Recording shell-out wrappers.
//
// `revealInOS` and `openInputWav` are the typed gateway from the recording-
// row action cluster to the Tauri Rust shell-out commands in
// tauri/src-tauri/src/recordings.rs. The Rust side runs the security
// gate (canonicalize-prefix check against the recordings root); the JS
// side is just a typed `invoke()` shell.
//
// Argument shape: Tauri 2.x normalises Rust snake_case parameters to
// camelCase on the JS side BY DEFAULT. The Rust signatures
//   reveal_in_os(app: AppHandle, session_dir: String)
//   open_input_wav(app: AppHandle, session_dir: String)
// expose `sessionDir` as the JS-side argument key. (`app` is auto-injected
// by Tauri and is NOT passed from JS.)
// ---------------------------------------------------------------------------

/** Reveal the session directory in macOS Finder / Windows Explorer.
 *
 *  `session_dir` is the BASENAME of the session folder (e.g.
 *  `"20260513-210410"`), NOT an absolute path — the Rust command joins it
 *  under the recordings root and rejects any traversal attempt before
 *  shelling out to `open -R` (macOS) or `explorer /select,` (Windows).
 *
 *  Rejects on:
 *    * Linux / unsupported platforms — Rust returns `Err("unsupported platform")`.
 *    * Path-traversal violation — Rust returns `Err("path_traversal_rejected")`.
 *    * Missing session dir — Rust returns `Err("target canon: ...")`.
 *  Caller is responsible for surfacing failure (typically `console.error`). */
export async function revealInOS(session_dir: string): Promise<void> {
  vmxLog("[vmx:ipc>]", "invoke reveal_in_os", { sessionDir: session_dir });
  return invokeTauri("reveal_in_os", { sessionDir: session_dir });
}

/** Open `<recordings_root>/<session_dir>/input.wav` in the OS default audio app.
 *
 *  Same `session_dir` shape + same security gate as `revealInOS`. Uses
 *  tauri-plugin-shell `open()` which delegates to the OS file association
 *  (LaunchServices on macOS, ShellExecute on Windows). */
export async function openInputWav(session_dir: string): Promise<void> {
  vmxLog("[vmx:ipc>]", "invoke open_input_wav", { sessionDir: session_dir });
  return invokeTauri("open_input_wav", { sessionDir: session_dir });
}

export const _REQUEST_TIMEOUT_MS_FOR_TESTS = REQUEST_TIMEOUT_MS;
export type { IpcMessage };
