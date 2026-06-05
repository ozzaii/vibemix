/**
 * @vitest-environment jsdom
 *
 * Regression coverage for the shell Settings nav <-> drawer bridge. Settings
 * is an overlay, not a real stage surface: opening it must keep the last task
 * surface active behind the drawer so the user never sees a fake Settings
 * empty route.
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
  it("opens Settings over the last real surface so no blank Settings route appears", () => {
    shell!.store.setActiveSurface("crate");
    shell!.store.setActiveSurface("settings");

    expect(settings.openSettings).toHaveBeenCalledTimes(1);
    expect(shell!.store.getState().activeSurface).toBe("crate");
    expect(shell!.store.getState().settingsOpen).toBe(true);
    expect(host.dataset.settings).toBe("open");
    expect(
      host.querySelector<HTMLElement>('.sb-nav-item[data-surface="settings"]')?.getAttribute(
        "aria-current",
      ),
    ).toBe("true");
    expect(
      host.querySelector<HTMLElement>('.sb-nav-item[data-surface="crate"]')?.getAttribute(
        "aria-current",
      ),
    ).toBeNull();

    settings.setOpen(false);

    expect(shell!.store.getState().activeSurface).toBe("crate");
    expect(shell!.store.getState().settingsOpen).toBe(false);
    expect(host.dataset.settings).toBe("closed");
    expect(
      host.querySelector<HTMLElement>('.sb-nav-item[data-surface="crate"]')?.getAttribute(
        "aria-current",
      ),
    ).toBe("true");

    shell!.store.setActiveSurface("settings");

    expect(settings.openSettings).toHaveBeenCalledTimes(2);
    expect(shell!.store.getState().activeSurface).toBe("crate");
  });

  it("closes the drawer on later real-surface navigation", () => {
    shell!.store.setActiveSurface("settings");
    expect(settings.openSettings).toHaveBeenCalledTimes(1);
    expect(shell!.store.getState().activeSurface).toBe("deck");
    expect(shell!.store.getState().settingsOpen).toBe(true);

    shell!.store.setActiveSurface("learn");

    expect(settings.closeSettings).toHaveBeenCalledTimes(1);
    expect(shell!.store.getState().activeSurface).toBe("learn");
    expect(shell!.store.getState().settingsOpen).toBe(false);
    expect(
      host.querySelector<HTMLElement>('.sb-nav-item[data-surface="learn"]')?.getAttribute(
        "aria-current",
      ),
    ).toBe("true");
  });
});
