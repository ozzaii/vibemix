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
import { emitIpc } from "../ipc/client.js";
import { renderSettingsGroup } from "./components/group.js";
import {
  renderHotkeyCapture,
  type HotkeyCaptureHandle,
} from "./components/hotkey-capture.js";
import {
  renderRetentionSlider,
  type RetentionSliderHandle,
} from "./components/retention-slider.js";
import { renderConfirmDialog } from "./components/confirm-dialog.js";
import { MascotGroup } from "./components/mascot-group.js";
import {
  closeSettingsState,
  getSettingsUIState,
  openSettingsState,
  setSettingsUIState,
  subscribeSettingsUI,
} from "./state.js";

const CSS = `
  .vmx-settings-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
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
    background: linear-gradient(180deg, var(--panel-lift) 0%, var(--panel) 100%);
    border-left: 1px solid var(--bezel-3);
    box-shadow:
      inset 1px 0 0 rgba(0, 0, 0, 0.5),
      inset 2px 0 6px rgba(0, 0, 0, 0.4),
      -8px 0 24px rgba(0, 0, 0, 0.4);
    transition: transform 250ms ease-in-out;
    display: flex;
    flex-direction: column;
  }
  .vmx-settings-drawer::before {
    /* Brushed-metal streak, lifted from .vmx-panel for visual continuity. */
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background-image: linear-gradient(
      90deg,
      var(--brushed-hi) 0%,
      transparent 12%,
      transparent 88%,
      var(--brushed-lo) 100%
    );
    mix-blend-mode: overlay;
    opacity: 0.6;
  }
  .vmx-settings-drawer[data-open="true"] {
    transform: translateX(0);
  }
  .vmx-settings-drawer__header {
    position: relative;
    height: 48px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 var(--sp-lg);
    border-bottom: 1px solid var(--bezel-2);
  }
  .vmx-settings-drawer__title {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--phosphor);
    text-shadow: var(--phosphor-glow);
    line-height: 1;
  }
  .vmx-settings-drawer__close {
    width: 28px;
    height: 28px;
    border-radius: 4px;
    background: transparent;
    border: 1px solid transparent;
    color: var(--ink-dim);
    font-family: "DM Mono", monospace;
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
    transition: color var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out;
  }
  .vmx-settings-drawer__close:hover {
    color: var(--phosphor);
    border-color: var(--phosphor-dim);
  }
  .vmx-settings-drawer__body {
    flex: 1;
    overflow-y: auto;
    padding: var(--sp-lg);
    display: flex;
    flex-direction: column;
    gap: var(--sp-md);
    position: relative;
  }
  .vmx-settings-drawer__body::-webkit-scrollbar {
    width: 8px;
  }
  .vmx-settings-drawer__body::-webkit-scrollbar-track {
    background: var(--panel-deep);
  }
  .vmx-settings-drawer__body::-webkit-scrollbar-thumb {
    background: var(--bezel-2);
    border-radius: 4px;
  }
  .vmx-settings-drawer__body::-webkit-scrollbar-thumb:hover {
    background: var(--bezel-3);
  }
  .vmx-settings-drawer__genre-wrap {
    position: relative;
  }
  .vmx-settings-drawer__reload-overlay {
    position: absolute;
    inset: 0;
    display: none;
    align-items: center;
    justify-content: center;
    background: var(--phosphor-soft);
    border: 1px solid var(--phosphor-dim);
    border-radius: 6px;
    font-family: "Workbench", "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    color: var(--phosphor);
    text-shadow: var(--phosphor-glow);
    z-index: 2;
    transition: opacity 250ms ease-out;
  }
  .vmx-settings-drawer__reload-overlay[data-shown="true"] {
    display: flex;
  }
  .vmx-settings-drawer__btn {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    padding: var(--sp-sm) var(--sp-md);
    background: transparent;
    border: 1px solid var(--bezel-2);
    color: var(--ink-dim);
    border-radius: 4px;
    cursor: pointer;
    line-height: 1;
    transition: color var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out;
  }
  .vmx-settings-drawer__btn:hover {
    color: var(--phosphor);
    border-color: var(--phosphor-dim);
  }
  .vmx-settings-drawer__modal-slot {
    position: relative;
    z-index: 60;
  }
  .vmx-settings-drawer__label {
    font-family: "Workbench", "Courier New", monospace;
    font-size: 11px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ink-dim);
    line-height: 1;
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
}

// ---------------------------------------------------------------------------
// Body composition — full rebuild on each refresh(). The drawer body is
// small (<~30 DOM nodes); rebuilding sidesteps the diffing complexity that
// the live-session components own. The render-loop is unaffected.
// ---------------------------------------------------------------------------

let hotkeyHandle: HotkeyCaptureHandle | null = null;
let retentionHandle: RetentionSliderHandle | null = null;

function renderDrawerBody(body: HTMLElement, modalSlot: HTMLElement): void {
  body.replaceChildren();

  const settings = getSessionState().settings;
  const ui = getSettingsUIState();

  // --- PERSONA --------------------------------------------------------------
  const personaBody = document.createElement("div");
  personaBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-md);";

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
  outputBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-md);";
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
  hotkeyBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-sm);";
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
  recordingBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-sm);";
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
  body.append(
    renderSettingsGroup({
      header: "RECORDING",
      children: recordingBody,
    }),
  );

  // --- CALIBRATION ----------------------------------------------------------
  const calibrationBody = document.createElement("div");
  calibrationBody.style.cssText = "display:flex; flex-direction:column; gap: var(--sp-sm);";
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
  // Appended last per Plan 13-03 §Task 2: order is PERSONA / OUTPUT /
  // HOTKEY / RECORDING / CALIBRATION / MASCOT. The group is rebuilt on
  // every drawer refresh, so SessionState diffs flow through naturally
  // — same lifecycle as the other groups.
  body.append(MascotGroup());

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
  value: string | number | null,
): Promise<void> {
  try {
    await sendSettings(field, value);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn(`[settings] sendSettings(${field}) failed:`, err);
  }
}
