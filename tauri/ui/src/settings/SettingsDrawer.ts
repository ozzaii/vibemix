/* Phase 12 Wave 4 — Settings slide-over drawer (Plan 12-05 §2).
 *
 * Right-side, 400px wide, slides in over the live session. The session
 * continues rendering at full fps BEHIND the backdrop — the drawer is
 * pure overlay; it does NOT pause `render-loop.ts`.
 *
 * Mount:  `mountSettingsDrawer(root)` appends two top-level nodes to
 *         `root`:
 *           - `.vmx-settings-backdrop` (full-window dim at 0.55 opacity,
 *             clickable to dismiss)
 *           - `.vmx-settings-drawer`   (slide-over, z-index 50)
 *         Both initially `display: none` / `translateX(100%)`. The shell
 *         calls `openSettings()` to slide in, `closeSettings()` to slide out.
 *
 * State sources:
 *   - getSessionState().settings — current values for each picker / rocker.
 *   - getSettingsUIState() — drawer-local UX state (open, capture, etc).
 *
 * Outbound writes:
 *   - sendSettings(field, value) — every mutation.
 *   - invoke('rebind_hotkey', { newCombo }) — hotkey rebind (Tauri command).
 *   - emitIpc('ipc.wizard.start', {}) — calibration re-run (sidecar tears
 *     down session and routes to wizard).
 *
 * The drawer re-renders on:
 *   - settings-state diffs (subscribed via subscribeSettingsUI + a polling
 *     check on getSessionState().settings every time the drawer opens —
 *     mid-session edits trigger a sidecar broadcast which the ws-bridge
 *     writes; the drawer re-syncs its picker labels on open).
 *
 * Keyboard:
 *   - Esc closes the drawer (unless inside an in-flight modal or capture).
 */

import { invoke } from "@tauri-apps/api/core";

import { registerStyle } from "../session/components/_style-registry.js";
import { renderPicker } from "../session/components/picker.js";
import { renderRocker } from "../session/components/rocker.js";
import { getSessionState } from "../session/state.js";
import { sendSettings, type SettingsField } from "../session/ws-bridge.js";
import { emitIpc, sendIpcRequest } from "../ipc/client.js";
import type {
  RecordingsDeleteAck,
  RecordingsListResult,
} from "../ipc/messages.js";
import { renderSettingsGroup } from "./components/group.js";
import {
  renderHotkeyCapture,
  type HotkeyCaptureHandle,
} from "./components/hotkey-capture.js";
import {
  renderRecordingBrowser,
  type RecordingBrowserHandle,
} from "./components/recording-browser.js";
import {
  renderRetentionSlider,
  type RetentionSliderHandle,
} from "./components/retention-slider.js";
import { renderConfirmDialog } from "./components/confirm-dialog.js";
import { HelpGroup } from "./components/help-group.js";
import { MascotGroup } from "./components/mascot-group.js";
import { PerformanceGroup } from "./components/performance-group.js";
import {
  closeSettingsState,
  getSettingsUIState,
  openSettingsState,
  setRecordingsSlice,
  setSettingsUIState,
  subscribeSettingsUI,
} from "./state.js";

const CSS = `
  .vmx-settings-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(2px);
    -webkit-backdrop-filter: blur(2px);
    z-index: 49;
    opacity: 0;
    pointer-events: none;
    transition: opacity 200ms ease-out;
  }
  .vmx-settings-backdrop[data-open="true"] {
    opacity: 1;
    pointer-events: auto;
  }
  .vmx-settings-drawer {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: 400px;
    max-width: 100vw;
    z-index: 50;
    transform: translateX(100%);
    background: var(--glass-1);
    backdrop-filter: var(--blur-glass);
    -webkit-backdrop-filter: var(--blur-glass);
    border-left: 1px solid var(--glass-edge);
    box-shadow:
      inset 1px 0 0 var(--glass-top),
      -8px 0 32px rgba(0, 0, 0, 0.55),
      -1px 0 0 rgba(255, 255, 255, 0.018);
    transition: transform 250ms ease-in-out;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  /* z-index discipline — keep header + body above .border-anim (z 4). */
  .vmx-settings-drawer > :not(.border-anim) {
    position: relative;
    z-index: 5;
  }
  .vmx-settings-drawer[data-open="true"] {
    transform: translateX(0);
  }
  .vmx-settings-drawer__header {
    position: relative;
    height: 52px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 var(--sp-5);
    border-bottom: 1px solid var(--glass-edge);
    background: rgba(0, 0, 0, 0.3);
  }
  .vmx-settings-drawer__title {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 700;
    font-size: 12px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
  .vmx-settings-drawer__title::before {
    content: '';
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--amber);
    box-shadow: 0 0 4px var(--amber), 0 0 8px var(--amber-40);
  }
  .vmx-settings-drawer__close {
    width: 30px;
    height: 30px;
    border-radius: var(--rad-sm);
    background: transparent;
    border: 1px solid transparent;
    color: var(--silk-40);
    font-family: var(--type-mono);
    font-size: 16px;
    line-height: 1;
    cursor: pointer;
    transition: color var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out;
  }
  .vmx-settings-drawer__close:hover {
    color: var(--amber);
    border-color: var(--amber-40);
    background: rgba(255, 138, 61, 0.06);
  }
  .vmx-settings-drawer__body {
    flex: 1;
    overflow-y: auto;
    padding: var(--sp-5);
    display: flex;
    flex-direction: column;
    gap: var(--sp-4);
    position: relative;
  }
  .vmx-settings-drawer__body::-webkit-scrollbar { width: 6px; }
  .vmx-settings-drawer__body::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.3); }
  .vmx-settings-drawer__body::-webkit-scrollbar-thumb {
    background: var(--silk-22);
    border-radius: 3px;
  }
  .vmx-settings-drawer__body::-webkit-scrollbar-thumb:hover { background: var(--amber-40); }
  .vmx-settings-drawer__genre-wrap {
    position: relative;
  }
  .vmx-settings-drawer__reload-overlay {
    position: absolute;
    inset: 0;
    display: none;
    align-items: center;
    justify-content: center;
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
    border: 1px solid var(--amber-40);
    border-radius: var(--rad-sm);
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 9px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: var(--amber);
    text-shadow: 0 0 4px var(--amber-22);
    z-index: 2;
    transition: opacity 250ms ease-out;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.06),
      inset 0 0 14px var(--amber-22);
  }
  .vmx-settings-drawer__reload-overlay[data-shown="true"] {
    display: flex;
  }
  .vmx-settings-drawer__btn {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 600;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding: 10px var(--sp-4);
    background: rgba(0, 0, 0, 0.35);
    border: 1px solid var(--glass-edge);
    color: var(--silk-65);
    border-radius: var(--rad-sm);
    cursor: pointer;
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
    transition: color var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out,
                background var(--motion-snap) ease-out,
                box-shadow var(--motion-snap) ease-out;
  }
  .vmx-settings-drawer__btn:hover {
    color: var(--amber);
    border-color: var(--amber-40);
    background: linear-gradient(180deg, rgba(255, 138, 61, 0.06) 0%, rgba(255, 138, 61, 0.02) 100%);
    box-shadow: inset 0 0 12px var(--amber-22);
  }
  .vmx-settings-drawer__modal-slot {
    position: relative;
    z-index: 60;
  }
  .vmx-settings-drawer__label {
    font-family: var(--type-display);
    font-variation-settings: "wdth" 85, "wght" 500;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--silk-40);
    line-height: 1;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
  }
`;

registerStyle("vmx-settings-drawer", CSS);

interface DrawerHandle {
  backdrop: HTMLElement;
  drawer: HTMLElement;
  modalSlot: HTMLElement;
  refresh: () => void;
  unsubscribe: () => void;
}

let mountedHandle: DrawerHandle | null = null;

const VOICE_OPTIONS = [
  "kore",
  "puck",
  "charon",
  "fenrir",
  "aoede",
  "leda",
  "orus",
  "zephyr",
] as const;

const GENRE_OPTIONS = [
  "house",
  "tech-house",
  "techno",
  "dnb",
  "trance",
  "hip-hop",
  "edm-generic",
] as const;

/** Mount the drawer + backdrop into the provided root. Idempotent — a
 *  second call returns the same handle without re-mounting. */
export function mountSettingsDrawer(root: HTMLElement): void {
  if (mountedHandle) return;

  const backdrop = document.createElement("div");
  backdrop.className = "vmx-settings-backdrop";
  backdrop.dataset.open = "false";
  backdrop.addEventListener("click", () => {
    closeSettings();
  });

  const drawer = document.createElement("aside");
  drawer.className = "vmx-settings-drawer";
  drawer.dataset.open = "false";
  drawer.setAttribute("aria-label", "settings");
  drawer.setAttribute("role", "complementary");

  // v5 animated border — first child of the drawer glass. tokens.css:302
  // .border-anim handles the conic-gradient + mask-composite at z-index 4;
  // children promoted to z-index 5 above via the descendant selector in CSS.
  const borderAnim = document.createElement("div");
  borderAnim.className = "border-anim";
  borderAnim.setAttribute("aria-hidden", "true");
  drawer.append(borderAnim);

  // Header
  const header = document.createElement("div");
  header.className = "vmx-settings-drawer__header";
  const title = document.createElement("span");
  title.className = "vmx-settings-drawer__title";
  title.textContent = "SETTINGS";
  header.append(title);
  const close = document.createElement("button");
  close.type = "button";
  close.className = "vmx-settings-drawer__close";
  close.setAttribute("aria-label", "close settings");
  close.textContent = "✕";
  close.addEventListener("click", (e) => {
    e.preventDefault();
    closeSettings();
  });
  header.append(close);
  drawer.append(header);

  // Body — built inside refresh() so settings/state changes hydrate.
  const body = document.createElement("div");
  body.className = "vmx-settings-drawer__body";
  drawer.append(body);

  const modalSlot = document.createElement("div");
  modalSlot.className = "vmx-settings-drawer__modal-slot";

  root.append(backdrop);
  root.append(drawer);
  root.append(modalSlot);

  // Esc closes the drawer (only when open + no modal in flight).
  const onKey = (e: KeyboardEvent): void => {
    if (!getSettingsUIState().open) return;
    if (getSettingsUIState().confirmDialog) return;
    if (getSettingsUIState().hotkeyCaptureMode) return;
    if (e.key === "Escape") {
      e.preventDefault();
      closeSettings();
    }
  };
  document.addEventListener("keydown", onKey);

  const handle: DrawerHandle = {
    backdrop,
    drawer,
    modalSlot,
    refresh: () => {
      renderDrawerBody(body, modalSlot);
      const ui = getSettingsUIState();
      drawer.dataset.open = ui.open ? "true" : "false";
      backdrop.dataset.open = ui.open ? "true" : "false";
    },
    unsubscribe: () => {
      document.removeEventListener("keydown", onKey);
    },
  };

  // Subscribe to UI state changes — the drawer re-renders on every flip.
  const unsubUI = subscribeSettingsUI(() => handle.refresh());
  const origUnsub = handle.unsubscribe;
  handle.unsubscribe = () => {
    unsubUI();
    origUnsub();
  };

  mountedHandle = handle;

  // Initial paint.
  handle.refresh();
}

/** Slide the drawer in. Idempotent. */
export function openSettings(): void {
  if (!mountedHandle) return;
  openSettingsState();
  // Re-render with fresh settings (sidecar may have broadcast updates
  // while the drawer was closed).
  mountedHandle.refresh();
  // Phase 15 Plan 05 — fire the recordings.list IPC on drawer open,
  // debounced 1s to absorb flickering re-opens (Plan §Task 2 must-haves).
  const now = Date.now();
  if (now - lastLoadAt > LIST_DEBOUNCE_MS) {
    lastLoadAt = now;
    void loadRecordings();
  }
}

/** Slide the drawer out. Idempotent. */
export function closeSettings(): void {
  if (!mountedHandle) return;
  closeSettingsState();
  mountedHandle.refresh();
}

/** Test-only — tear down the singleton so a fresh vitest case can mount. */
export function _resetDrawerForTests(): void {
  if (mountedHandle) {
    mountedHandle.unsubscribe();
    try {
      mountedHandle.backdrop.remove();
      mountedHandle.drawer.remove();
      mountedHandle.modalSlot.remove();
    } catch {
      /* DOM already gone */
    }
  }
  mountedHandle = null;
  recordingBrowserHandle = null;
  lastLoadAt = 0;
}

// ---------------------------------------------------------------------------
// Body composition — full rebuild on each refresh(). The drawer body is
// small (<~30 DOM nodes); rebuilding sidesteps the diffing complexity that
// the live-session components own. The render-loop is unaffected.
// ---------------------------------------------------------------------------

let hotkeyHandle: HotkeyCaptureHandle | null = null;
let retentionHandle: RetentionSliderHandle | null = null;
// Phase 15 Plan 05 — Recording browser handle persists across refreshes
// so the loadRecordings() async resolver can push results into the live
// component without rebuilding it on every refresh tick.
let recordingBrowserHandle: RecordingBrowserHandle | null = null;
// Debounce window for drawer-open list refresh (Plan 15-05 §Task 2): a
// flickering re-open within 1s reuses the in-memory slice instead of
// firing a new recordings.list IPC.
let lastLoadAt = 0;
const LIST_DEBOUNCE_MS = 1000;

function renderDrawerBody(body: HTMLElement, modalSlot: HTMLElement): void {
  body.replaceChildren();

  const settings = getSessionState().settings;
  const ui = getSettingsUIState();

  // --- PERSONA --------------------------------------------------------------
  const personaBody = document.createElement("div");
  personaBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-4);";

  // Voice picker
  personaBody.append(
    renderPicker({
      label: "VOICE",
      value: settings.voice,
      avatar: true,
      options: VOICE_OPTIONS.map((v) => ({ id: v, label: v })),
      onChange: (id) => {
        void sendSettingsField("voice", id);
      },
    }),
  );

  // Mode rocker
  personaBody.append(
    renderRocker({
      ariaLabel: "interaction mode",
      options: [
        { id: "hype", label: "HYPE" },
        { id: "coach", label: "COACH" },
      ],
      active: settings.mode,
      variant: "interaction",
      onChange: (id) => {
        void sendSettingsField("mode", id);
      },
    }),
  );

  // Genre dropdown with reload overlay
  const genreWrap = document.createElement("div");
  genreWrap.className = "vmx-settings-drawer__genre-wrap";
  genreWrap.append(
    renderPicker({
      label: "GENRE",
      value: settings.genre,
      autoPill: false,
      options: GENRE_OPTIONS.map((g) => ({ id: g, label: g })),
      onChange: (id) => {
        setSettingsUIState({ pendingGenreReload: true });
        void sendSettingsField("genre", id);
        // Overlay auto-dismisses after 250ms — sidecar profile reloads
        // are fast (we're not waiting for a confirmation; the live
        // session keeps rendering through this).
        window.setTimeout(() => {
          setSettingsUIState({ pendingGenreReload: false });
        }, 250);
      },
    }),
  );
  const overlay = document.createElement("div");
  overlay.className = "vmx-settings-drawer__reload-overlay";
  overlay.dataset.shown = ui.pendingGenreReload ? "true" : "false";
  overlay.textContent = "RELOADING PROFILE…";
  genreWrap.append(overlay);
  personaBody.append(genreWrap);

  body.append(
    renderSettingsGroup({
      header: "PERSONA",
      badge: "CFG",
      children: personaBody,
    }),
  );

  // --- OUTPUT ---------------------------------------------------------------
  const outputBody = document.createElement("div");
  outputBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-4);";
  outputBody.append(
    renderPicker({
      label: "DEVICE",
      value: settings.output_device_id ?? "auto",
      autoPill: !settings.output_device_id,
      options: [
        { id: "auto", label: "auto" },
        // Real device list is populated by the sidecar at boot and lives
        // off ipc.settings.state; the picker here lets the user fall
        // back to "auto" or pick a known id. v1 ships with a "auto"
        // default — Phase 15 expands.
        ...(settings.output_device_id
          ? [{ id: settings.output_device_id, label: settings.output_device_id }]
          : []),
      ],
      onChange: (id) => {
        void sendSettingsField(
          "output_device_id",
          id === "auto" ? null : id,
        );
      },
    }),
  );
  outputBody.append(
    renderRocker({
      ariaLabel: "output profile",
      options: [
        { id: "hp", label: "HP" },
        { id: "spk", label: "SPK" },
      ],
      active: settings.output_profile,
      variant: "rocker",
      onChange: (id) => {
        void sendSettingsField("output_profile", id);
      },
    }),
  );
  body.append(
    renderSettingsGroup({
      header: "OUTPUT",
      children: outputBody,
    }),
  );

  // --- HOTKEY ---------------------------------------------------------------
  const hotkeyBody = document.createElement("div");
  hotkeyBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-2);";
  const hotkeyLabel = document.createElement("div");
  hotkeyLabel.className = "vmx-settings-drawer__label";
  hotkeyLabel.textContent = "PUSH-TO-MUTE";
  hotkeyBody.append(hotkeyLabel);

  hotkeyHandle = renderHotkeyCapture({
    value: settings.push_to_mute_hotkey,
    onCapture: (combo) => {
      setSettingsUIState({ hotkeyCaptureMode: false });
      void applyHotkeyCapture(combo);
    },
  });
  hotkeyBody.append(hotkeyHandle.root);
  body.append(
    renderSettingsGroup({
      header: "HOTKEY",
      children: hotkeyBody,
    }),
  );

  // --- RECORDING ------------------------------------------------------------
  const recordingBody = document.createElement("div");
  recordingBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-2);";
  const recordingLabel = document.createElement("div");
  recordingLabel.className = "vmx-settings-drawer__label";
  recordingLabel.textContent = "RETENTION";
  recordingBody.append(recordingLabel);

  retentionHandle = renderRetentionSlider({
    value: settings.retention_days,
    onChange: (days) => {
      void sendSettingsField("retention_days", days);
    },
  });
  recordingBody.append(retentionHandle.root);

  // Phase 15 Plan 05 — Recording browser mounts BELOW the retention slider
  // (UI-SPEC §Layout: order is locked retention → disk usage line →
  // browser). The browser component owns the silkscreen disk-usage line +
  // virtualized session rows. The drawer wires:
  //   - On drawer open: fire `ipc.recordings.list` (debounced 1s) and
  //     populate the browser with sessions + usage.
  //   - On `ipc.recordings.usage` push (subscriber in ws-bridge.ts): the
  //     slice mutates → drawer refresh runs → we call setUsage() here.
  //   - On delete confirm: fire `ipc.recordings.delete` and optimistically
  //     remove the row from the slice.
  const recSlice = ui.recordings;
  const initialUsage = recSlice.loading
    ? { sessions: recSlice.usage.sessions, bytes_total: -1 }
    : recSlice.error !== null
    ? { sessions: recSlice.usage.sessions, bytes_total: -2 }
    : recSlice.usage;
  recordingBrowserHandle = renderRecordingBrowser({
    initialSessions: recSlice.sessions,
    initialUsage,
    onReplay: () => {
      // Row expansion is owned by the row component (audio + transcript
      // are local — no IPC dispatched here per UI-SPEC §Component
      // Contracts onReplay note).
    },
    onDelete: (session_dir, _timestamp) => {
      void onDeleteRecording(session_dir);
    },
  });
  recordingBody.append(recordingBrowserHandle.root);

  body.append(
    renderSettingsGroup({
      header: "RECORDING",
      children: recordingBody,
    }),
  );

  // --- CALIBRATION ----------------------------------------------------------
  const calibrationBody = document.createElement("div");
  calibrationBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-2);";
  const reRunBtn = document.createElement("button");
  reRunBtn.type = "button";
  reRunBtn.className = "vmx-settings-drawer__btn";
  reRunBtn.textContent = "↻ RE-RUN WIZARD";
  reRunBtn.addEventListener("click", (e) => {
    e.preventDefault();
    openConfirmReRun(modalSlot);
  });
  calibrationBody.append(reRunBtn);
  body.append(
    renderSettingsGroup({
      header: "CALIBRATION",
      children: calibrationBody,
    }),
  );

  // --- MASCOT (Phase 13-03) -------------------------------------------------
  // Appended per Plan 13-03 §Task 2; per Plan 14-04 the new PERFORMANCE
  // group sits AFTER MASCOT. Final order: PERSONA / OUTPUT / HOTKEY /
  // RECORDING / CALIBRATION / MASCOT / PERFORMANCE.
  body.append(MascotGroup());

  // --- PERFORMANCE (Phase 14-04) -------------------------------------------
  // Single-row group: "LIGHTER BLUR" toggle wiring the data-blur-perf
  // attribute on <html>. The toggle persists via settings.set { field:
  // "lighter_blur", value: <bool> } through SettingsApplier; the boot
  // read in main.ts re-applies it on next launch.
  body.append(PerformanceGroup(settings.lighter_blur));

  // --- HELP (impeccable Wave 6 — closes H10 "help & documentation") --------
  // Last group. Shortcuts link + audio-routing checklist + GitHub link +
  // About row. The shortcuts link mounts the same overlay as the `?` key.
  // GitHub URL isn't yet in the Tauri capability allowlist — see the TODO
  // in help-group.ts.
  body.append(HelpGroup());

  // --- Modal slot rebuild ---------------------------------------------------
  renderModalSlot(modalSlot);
}

function renderModalSlot(modalSlot: HTMLElement): void {
  modalSlot.replaceChildren();
  const ui = getSettingsUIState();
  if (ui.confirmDialog === "re-run-calibration") {
    const dialog = renderConfirmDialog({
      heading: "RESTART CALIBRATION?",
      body: "Your live session will pause while the wizard runs.",
      confirmLabel: "RESTART",
      cancelLabel: "CANCEL",
      onCancel: () => {
        setSettingsUIState({ confirmDialog: null });
      },
      onConfirm: () => {
        setSettingsUIState({ confirmDialog: null });
        void emitWizardStart();
      },
    });
    modalSlot.append(dialog);
  }
}

function openConfirmReRun(_modalSlot: HTMLElement): void {
  setSettingsUIState({ confirmDialog: "re-run-calibration" });
}

async function emitWizardStart(): Promise<void> {
  try {
    await emitIpc("ipc.wizard.start", {});
    // Close the drawer; the shell's session router will tear the
    // session down and mount the wizard when the sidecar acks.
    closeSettings();
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn("[settings] ipc.wizard.start failed:", err);
  }
}

async function applyHotkeyCapture(combo: string): Promise<void> {
  try {
    // 1) Tell the sidecar to persist via ipc.settings.set.
    await sendSettingsField("push_to_mute_hotkey", combo);
    // 2) Tell Rust to re-register the global shortcut.
    await invoke("rebind_hotkey", { newCombo: combo });
    hotkeyHandle?.setError(null);
  } catch (err) {
    const msg =
      err instanceof Error ? err.message : String(err ?? "rebind failed");
    hotkeyHandle?.setError(msg);
  }
}

async function sendSettingsField(
  field: SettingsField,
  value: string | number | boolean | null,
): Promise<void> {
  // WR-03 in 14-REVIEW.md — value union widened to match ws-bridge's
  // sendSettings (which was widened to include boolean for Plan
  // 14-04's lighter_blur). Without this, any future drawer-side toggle
  // wanting to flow through this try/catch wrapper would need a type
  // assertion to pass a boolean.
  try {
    await sendSettings(field, value);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn(`[settings] sendSettings(${field}) failed:`, err);
  }
}

// ---------------------------------------------------------------------------
// Phase 15 Plan 05 — Recording browser IPC wiring.
// ---------------------------------------------------------------------------

/** Fire `ipc.recordings.list` on drawer open. Sentinel-driven loading +
 *  error states: pushes `bytes_total: -1` to the browser usage line to
 *  render `RECORDINGS · LOADING…`; on failure pushes `bytes_total: -2` to
 *  render `RECORDINGS · UNAVAILABLE` (Plan 15-04 sentinel contract).
 *
 *  Exported for vitest coverage; the production caller is `openSettings()`. */
export async function loadRecordings(): Promise<void> {
  // Mark loading + flip the usage line to the LOADING sentinel.
  setRecordingsSlice({ loading: true, error: null });
  if (recordingBrowserHandle) {
    recordingBrowserHandle.setUsage({
      sessions: getSettingsUIState().recordings.usage.sessions,
      bytes_total: -1,
    });
  }
  try {
    const reply = await sendIpcRequest<RecordingsListResult>(
      "ipc.recordings.list",
      {},
      "ipc.recordings.list_result",
    );
    const sessions = reply.payload.sessions.map((s) => ({
      session_dir: s.session_dir,
      started_at_iso: s.started_at_iso,
      duration_s: s.duration_s,
      event_count: s.event_count,
      bytes_total: s.bytes_total,
      crashed: s.crashed,
    }));
    const usage = {
      sessions: sessions.length,
      bytes_total: reply.payload.bytes_total,
    };
    setRecordingsSlice({
      sessions,
      usage,
      loading: false,
      error: null,
    });
    if (recordingBrowserHandle) {
      recordingBrowserHandle.setSessions(sessions);
      recordingBrowserHandle.setUsage(usage);
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    setRecordingsSlice({ loading: false, error: msg });
    if (recordingBrowserHandle) {
      recordingBrowserHandle.setUsage({
        sessions: getSettingsUIState().recordings.usage.sessions,
        bytes_total: -2,
      });
    }
    // eslint-disable-next-line no-console
    console.warn("[settings] ipc.recordings.list failed:", err);
  }
}

/** Dispatch `ipc.recordings.delete` and optimistically remove the row on
 *  ok=true ack. UI-SPEC §State Management: the trailing usage push from
 *  the sidecar (after the sweep fires) updates the disk usage line; we
 *  don't refetch the list here.
 *
 *  Exported for vitest coverage. */
export async function onDeleteRecording(session_dir: string): Promise<void> {
  try {
    const reply = await sendIpcRequest<RecordingsDeleteAck>(
      "ipc.recordings.delete",
      { session_dir },
      "ipc.recordings.delete_ack",
    );
    if (reply.payload.ok) {
      // Optimistic remove — slice update + push to live component.
      const current = getSettingsUIState().recordings;
      const sessions = current.sessions.filter(
        (s) => s.session_dir !== session_dir,
      );
      setRecordingsSlice({ sessions });
      if (recordingBrowserHandle) recordingBrowserHandle.setSessions(sessions);
    } else {
      // ok=false ack — surface error via the slice; the next drawer refresh
      // re-renders with the error sentinel. (UI-SPEC §Copywriting
      // error-toast row lists `Delete failed: {error}` — Plan 15-06 wires
      // the in-dialog retry surface; for v1 we expose via the slice.)
      const errMsg = reply.payload.error ?? "delete failed";
      setRecordingsSlice({ error: `delete failed: ${errMsg}` });
      // eslint-disable-next-line no-console
      console.warn(`[settings] recordings.delete ok=false: ${errMsg}`);
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    setRecordingsSlice({ error: `delete failed: ${msg}` });
    // eslint-disable-next-line no-console
    console.warn("[settings] ipc.recordings.delete failed:", err);
  }
}
