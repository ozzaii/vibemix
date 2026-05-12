/* Phase 12 Wave 4 — Settings drawer mount/open/close (Plan 12-05 §7).
 *
 * Asserts:
 *   - mountSettingsDrawer is idempotent (two calls = one DOM tree).
 *   - openSettings + closeSettings flip data-open on drawer + backdrop.
 *   - Esc closes when open; noop when closed.
 *   - Backdrop click closes the drawer.
 *   - ✕ button closes the drawer.
 *   - Esc does NOT close when a modal confirm is in flight.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock @tauri-apps/api/core BEFORE importing the drawer module — the
// drawer imports `invoke` for the rebind_hotkey command. In jsdom we
// don't want a real Tauri context.
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (_cmd: string, _args?: Record<string, unknown>) => {}),
}));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
}));

import {
  _resetDrawerForTests,
  closeSettings,
  mountSettingsDrawer,
  openSettings,
} from "../../src/settings/SettingsDrawer.js";
import {
  _resetSettingsUIStateForTests,
  getSettingsUIState,
  setSettingsUIState,
} from "../../src/settings/state.js";

beforeEach(() => {
  _resetSettingsUIStateForTests();
  _resetDrawerForTests();
  document.body.replaceChildren();
});

afterEach(() => {
  _resetDrawerForTests();
  _resetSettingsUIStateForTests();
  document.body.replaceChildren();
});

describe("mountSettingsDrawer", () => {
  it("mounts backdrop + drawer + modal slot into the provided root", () => {
    mountSettingsDrawer(document.body);
    expect(document.querySelectorAll(".vmx-settings-backdrop").length).toBe(1);
    expect(document.querySelectorAll(".vmx-settings-drawer").length).toBe(1);
    expect(
      document.querySelectorAll(".vmx-settings-drawer__modal-slot").length,
    ).toBe(1);
  });

  it("is idempotent — a second call does not duplicate nodes", () => {
    mountSettingsDrawer(document.body);
    mountSettingsDrawer(document.body);
    expect(document.querySelectorAll(".vmx-settings-drawer").length).toBe(1);
    expect(document.querySelectorAll(".vmx-settings-backdrop").length).toBe(1);
  });

  it("initial state is closed (data-open=false on both)", () => {
    mountSettingsDrawer(document.body);
    const drawer = document.querySelector<HTMLElement>(
      ".vmx-settings-drawer",
    );
    const backdrop = document.querySelector<HTMLElement>(
      ".vmx-settings-backdrop",
    );
    expect(drawer?.dataset.open).toBe("false");
    expect(backdrop?.dataset.open).toBe("false");
  });
});

describe("openSettings / closeSettings", () => {
  it("openSettings flips data-open=true on drawer + backdrop", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    const drawer = document.querySelector<HTMLElement>(
      ".vmx-settings-drawer",
    );
    const backdrop = document.querySelector<HTMLElement>(
      ".vmx-settings-backdrop",
    );
    expect(drawer?.dataset.open).toBe("true");
    expect(backdrop?.dataset.open).toBe("true");
    expect(getSettingsUIState().open).toBe(true);
  });

  it("closeSettings flips data-open=false back", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    closeSettings();
    const drawer = document.querySelector<HTMLElement>(
      ".vmx-settings-drawer",
    );
    expect(drawer?.dataset.open).toBe("false");
    expect(getSettingsUIState().open).toBe(false);
  });

  it("closeSettings clears in-flight capture + confirm state", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    setSettingsUIState({
      hotkeyCaptureMode: true,
      confirmDialog: "re-run-calibration",
    });
    closeSettings();
    const ui = getSettingsUIState();
    expect(ui.hotkeyCaptureMode).toBe(false);
    expect(ui.confirmDialog).toBeNull();
  });
});

describe("dismiss paths", () => {
  it("Esc key closes an open drawer", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    expect(getSettingsUIState().open).toBe(true);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(getSettingsUIState().open).toBe(false);
  });

  it("Esc key is a noop when drawer is closed", () => {
    mountSettingsDrawer(document.body);
    expect(getSettingsUIState().open).toBe(false);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(getSettingsUIState().open).toBe(false);
  });

  it("Esc does NOT close drawer when confirm dialog is in flight", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    setSettingsUIState({ confirmDialog: "re-run-calibration" });
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(getSettingsUIState().open).toBe(true);
  });

  it("Esc does NOT close drawer when hotkey capture is in flight", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    setSettingsUIState({ hotkeyCaptureMode: true });
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(getSettingsUIState().open).toBe(true);
  });

  it("clicking the backdrop closes the drawer", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    const backdrop = document.querySelector<HTMLElement>(
      ".vmx-settings-backdrop",
    );
    backdrop?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(getSettingsUIState().open).toBe(false);
  });

  it("clicking the ✕ button closes the drawer", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    const closeBtn = document.querySelector<HTMLElement>(
      ".vmx-settings-drawer__close",
    );
    closeBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(getSettingsUIState().open).toBe(false);
  });
});

describe("group rendering", () => {
  it("renders all five groups: PERSONA / OUTPUT / HOTKEY / RECORDING / CALIBRATION", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    const groupHeaders = Array.from(
      document.querySelectorAll<HTMLElement>(".vmx-settings-group__header"),
    ).map((h) => h.textContent ?? "");
    expect(groupHeaders.some((h) => h.includes("PERSONA"))).toBe(true);
    expect(groupHeaders.some((h) => h.includes("OUTPUT"))).toBe(true);
    expect(groupHeaders.some((h) => h.includes("HOTKEY"))).toBe(true);
    expect(groupHeaders.some((h) => h.includes("RECORDING"))).toBe(true);
    expect(groupHeaders.some((h) => h.includes("CALIBRATION"))).toBe(true);
  });

  it("PERSONA group shows the hotkey-capture component", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    expect(document.querySelectorAll(".vmx-hotkey-capture").length).toBe(1);
  });

  it("RECORDING group shows the retention slider with 6 knobs", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    expect(document.querySelectorAll(".vmx-retention__knob").length).toBe(6);
  });
});
