/* tcc-watcher.ts — Phase 33 / INSTALL-06 / P71.
 *
 * Subscribes to TCC permission state changes emitted by the
 * tauri-plugin-macos-permissions plugin and forwards a single
 * runtime.permission_lost event when a previously-granted permission
 * transitions to denied.
 *
 * The watcher is intentionally narrow — it does NOT control session
 * pause / mic mute / toast UI itself. Those side-effects live in the
 * session loop (the consumer of runtime.permission_lost). This keeps
 * the watcher unit-testable without spinning up the session machinery.
 *
 * P71 graceful-degrade contract:
 *   - On revoke → emit runtime.permission_lost with permission name +
 *     last-known state. Consumers pause audio + show toast + offer
 *     re-grant.
 *   - The watcher NEVER throws. A subscriber that throws is caught and
 *     surfaced via console.error so a single buggy listener cannot
 *     crash the session.
 */

export type TccPermissionName =
  | "microphone"
  | "screen-recording"
  | "accessibility"
  | "automation";

export type TccPermissionState = "granted" | "denied" | "not_determined";

export interface PermissionLostEvent {
  type: "runtime.permission_lost";
  permission: TccPermissionName;
  /** State at the moment we observed the revoke — typically "denied". */
  newState: TccPermissionState;
  /** Wall-clock ms (Date.now()) when the revoke was observed. */
  observedAtMs: number;
}

export type PermissionLostListener = (event: PermissionLostEvent) => void;

/** Source-of-truth for the watcher's last-known per-permission state.
 *  Exposed so tests can seed it without going through Tauri. */
export interface TccWatcherState {
  microphone: TccPermissionState;
  "screen-recording": TccPermissionState;
  accessibility: TccPermissionState;
  automation: TccPermissionState;
}

export const DEFAULT_TCC_STATE: TccWatcherState = {
  microphone: "not_determined",
  "screen-recording": "not_determined",
  accessibility: "not_determined",
  automation: "not_determined",
};

export class TccWatcher {
  private _state: TccWatcherState;
  private readonly _listeners: Set<PermissionLostListener> = new Set();

  constructor(initial: Partial<TccWatcherState> = {}) {
    this._state = { ...DEFAULT_TCC_STATE, ...initial };
  }

  subscribe(listener: PermissionLostListener): () => void {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  /** Inject a plugin-emitted state change. Returns the emitted event
   *  if a revoke was fired, or null otherwise. */
  observe(
    permission: TccPermissionName,
    newState: TccPermissionState,
    now: () => number = () => Date.now(),
  ): PermissionLostEvent | null {
    const previous = this._state[permission];
    this._state[permission] = newState;
    if (previous === "granted" && newState !== "granted") {
      const event: PermissionLostEvent = {
        type: "runtime.permission_lost",
        permission,
        newState,
        observedAtMs: now(),
      };
      for (const listener of this._listeners) {
        try {
          listener(event);
        } catch (err) {
          // Never let a single buggy listener crash the watcher.
          // eslint-disable-next-line no-console
          console.error("[tcc-watcher] listener threw", err);
        }
      }
      return event;
    }
    return null;
  }

  state(): Readonly<TccWatcherState> {
    return { ...this._state };
  }
}
