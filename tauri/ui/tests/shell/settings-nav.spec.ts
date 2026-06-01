/**
 * @vitest-environment jsdom
 *
 * Regression coverage for the shell Settings nav <-> drawer bridge. Closing
 * the drawer from inside Settings must move shell navigation back to the last
 * real surface, otherwise clicking Settings again is a no-op because the shell
 * still thinks that surface is active.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const settings = vi.hoisted(() => {
  type UiState = { open: boolean };
  type Listener = (ui: Readonly<UiState>) => void;

  let open = false;
  const listeners = new Set<Listener>();

  const notify = (): void => {
    const snapshot = { open };
    for (const listener of listeners) listener(snapshot);
  };

  return {
    closeSettings: vi.fn(() => {
      if (!open) return;
      open = false;
      notify();
    }),
    getSettingsUIState: vi.fn(() => ({ open })),
    openSettings: vi.fn(() => {
      if (open) return;
      open = true;
      notify();
    }),
    reset: (): void => {
      open = false;
      listeners.clear();
    },
    setOpen: (value: boolean): void => {
      if (open === value) return;
      open = value;
      notify();
    },
    subscribeSettingsUI: vi.fn((listener: Listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    }),
  };
});

vi.mock("../../src/settings/SettingsDrawer.js", () => ({
  closeSettings: settings.closeSettings,
  openSettings: settings.openSettings,
}));

vi.mock("../../src/settings/state.js", () => ({
  getSettingsUIState: settings.getSettingsUIState,
  subscribeSettingsUI: settings.subscribeSettingsUI,
}));

import { mountDesktopShell, type MountedShell } from "../../src/shell/DesktopShell.js";
import { wireSettingsNav } from "../../src/shell/app.js";

let shell: MountedShell | null = null;
let host: HTMLElement;
let unwireSettings: (() => void) | null = null;

beforeEach(() => {
  globalThis.localStorage?.clear();
  settings.reset();
  settings.openSettings.mockClear();
  settings.closeSettings.mockClear();
  settings.getSettingsUIState.mockClear();
  settings.subscribeSettingsUI.mockClear();

  host = document.createElement("div");
  document.body.append(host);
  shell = mountDesktopShell(host);
  unwireSettings = wireSettingsNav(shell);
});

afterEach(() => {
  unwireSettings?.();
  unwireSettings = null;
  shell?.teardown();
  shell = null;
  host.remove();
});

describe("wireSettingsNav", () => {
  it("returns to the last surface when the drawer closes so Settings can reopen", () => {
    shell!.store.setActiveSurface("crate");
    shell!.store.setActiveSurface("settings");

    expect(settings.openSettings).toHaveBeenCalledTimes(1);
    expect(shell!.store.getState().activeSurface).toBe("settings");

    settings.setOpen(false);

    expect(shell!.store.getState().activeSurface).toBe("crate");

    shell!.store.setActiveSurface("settings");

    expect(settings.openSettings).toHaveBeenCalledTimes(2);
    expect(shell!.store.getState().activeSurface).toBe("settings");
  });

  it("closes the drawer when shell navigation leaves Settings", () => {
    shell!.store.setActiveSurface("settings");
    expect(settings.openSettings).toHaveBeenCalledTimes(1);

    shell!.store.setActiveSurface("learn");

    expect(settings.closeSettings).toHaveBeenCalledTimes(1);
    expect(shell!.store.getState().activeSurface).toBe("learn");
  });
});
