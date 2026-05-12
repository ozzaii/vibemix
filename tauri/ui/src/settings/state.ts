/* Phase 12 Wave 4 — Settings drawer local state singleton (Plan 12-05 §1).
 *
 * This is a small, focused state slice that owns the drawer's UX-only
 * concerns:
 *   - `open`               — is the slide-over visible right now?
 *   - `hotkeyCaptureMode`  — true while the user is rebinding the
 *                            push-to-mute combo (we swallow keydowns).
 *   - `pendingGenreReload` — true for ~250ms after a genre change while
 *                            the sidecar reloads its profile; drives the
 *                            "RELOADING PROFILE…" overlay.
 *   - `confirmDialog`      — null or the id of the modal confirm
 *                            currently open ("re-run-calibration" only
 *                            for Phase 12).
 *
 * Persistent settings (voice, genre, retention_days, push_to_mute_hotkey,
 * …) live in SessionState (see `src/session/state.ts`) — written by the
 * ws-bridge on `ipc.settings.state`. The drawer reads from there and
 * pushes mutations via `sendSettings(field, value)`.
 *
 * Subscriber model: tiny pub/sub. SettingsDrawer.ts subscribes once on
 * mount; setters call `notify()` which calls every listener. No external
 * deps, no React, no reactive plumbing — same pattern as Phase 11's
 * wizard/state.ts.
 */

export interface SettingsUIState {
  open: boolean;
  hotkeyCaptureMode: boolean;
  pendingGenreReload: boolean;
  confirmDialog: null | "re-run-calibration";
}

type Listener = (s: Readonly<SettingsUIState>) => void;

function makeDefault(): SettingsUIState {
  return {
    open: false,
    hotkeyCaptureMode: false,
    pendingGenreReload: false,
    confirmDialog: null,
  };
}

let current: SettingsUIState = makeDefault();
const listeners = new Set<Listener>();

function notify(): void {
  for (const l of listeners) {
    try {
      l(current);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[settings/state] listener threw:", e);
    }
  }
}

export function getSettingsUIState(): Readonly<SettingsUIState> {
  return current;
}

/** Shallow-merge patch. Top-level keys replace; same semantics as the
 *  session-state singleton so the drawer's render path can short-circuit
 *  on unchanged keys. */
export function setSettingsUIState(patch: Partial<SettingsUIState>): void {
  current = { ...current, ...patch };
  notify();
}

export function subscribeSettingsUI(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Convenience helpers — read like English in the drawer. */
export function openSettingsState(): void {
  if (!current.open) setSettingsUIState({ open: true });
}

export function closeSettingsState(): void {
  if (current.open) {
    // Closing the drawer also drops any capture/confirm state — those are
    // ephemeral UI affordances scoped to the open drawer.
    setSettingsUIState({
      open: false,
      hotkeyCaptureMode: false,
      confirmDialog: null,
    });
  }
}

/** Test-only — reset back to defaults so vitest cases stay isolated. */
export function _resetSettingsUIStateForTests(): void {
  current = makeDefault();
  listeners.clear();
}
