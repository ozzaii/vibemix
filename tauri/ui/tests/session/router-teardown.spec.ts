/**
 * @vitest-environment jsdom
 *
 * Session router lifecycle contract:
 * the router owns the live session loop and the settings overlay singleton.
 * A route bounce must not leave document-level drawer listeners or overlay
 * nodes mounted on document.body.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  unsubscribeBridge: vi.fn(),
  unsubscribeShortcuts: vi.fn(),
  unsubscribeQuitGuard: vi.fn(),
  unsubscribeTrayQuit: vi.fn(),
  unsubscribeTrayMood: vi.fn(),
  startRenderLoop: vi.fn(),
  stopRenderLoop: vi.fn(),
}));

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async () => undefined),
  convertFileSrc: (path: string): string => `asset://localhost${path}`,
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
}));

vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: vi.fn(async () => undefined),
  sendIpcRequest: vi.fn(() => new Promise(() => undefined)),
  subscribeIpc: vi.fn(async () => () => {}),
}));

vi.mock("../../src/session/ws-bridge.js", () => ({
  initSessionBridge: vi.fn(async () => ({
    unsubscribeAll: mocks.unsubscribeBridge,
  })),
  sendSettings: vi.fn(async () => undefined),
}));

vi.mock("../../src/session/render-loop.js", () => ({
  startRenderLoop: mocks.startRenderLoop,
  stopRenderLoop: mocks.stopRenderLoop,
}));

vi.mock("../../src/session/session-shortcuts.js", () => ({
  mountSessionShortcuts: vi.fn(() => mocks.unsubscribeShortcuts),
}));

vi.mock("../../src/session/quit-guard.js", () => ({
  installQuitGuard: vi.fn(() => mocks.unsubscribeQuitGuard),
  installTrayQuitListener: vi.fn(async () => mocks.unsubscribeTrayQuit),
}));

vi.mock("../../src/session/tray-mood.js", () => ({
  installTrayMoodListener: vi.fn(async () => mocks.unsubscribeTrayMood),
}));

import {
  _getMountedForTests,
  routeSession,
  teardownSession,
} from "../../src/session/router.js";
import {
  _resetDrawerForTests,
  openSettings,
} from "../../src/settings/SettingsDrawer.js";
import {
  _resetSettingsUIStateForTests,
  getSettingsUIState,
} from "../../src/settings/state.js";

beforeEach(() => {
  for (const fn of Object.values(mocks)) fn.mockClear();
  _resetDrawerForTests();
  _resetSettingsUIStateForTests();
  document.body.replaceChildren();
});

afterEach(async () => {
  await teardownSession();
  _resetDrawerForTests();
  _resetSettingsUIStateForTests();
  document.body.replaceChildren();
});

describe("session router teardown", () => {
  it("unmounts the settings drawer singleton and all route listeners", async () => {
    const host = document.createElement("div");
    document.body.append(host);

    await routeSession(host);
    openSettings();

    expect(_getMountedForTests()).toBeTruthy();
    expect(getSettingsUIState().open).toBe(true);
    expect(document.querySelector(".vmx-settings-drawer")).toBeTruthy();

    await teardownSession();

    expect(_getMountedForTests()).toBeNull();
    expect(getSettingsUIState().open).toBe(false);
    expect(document.querySelector(".vmx-settings-backdrop")).toBeNull();
    expect(document.querySelector(".vmx-settings-drawer")).toBeNull();
    expect(document.querySelector(".vmx-settings-drawer__modal-slot")).toBeNull();

    expect(mocks.stopRenderLoop).toHaveBeenCalled();
    expect(mocks.unsubscribeBridge).toHaveBeenCalledTimes(1);
    expect(mocks.unsubscribeShortcuts).toHaveBeenCalledTimes(1);
    expect(mocks.unsubscribeQuitGuard).toHaveBeenCalledTimes(1);
    expect(mocks.unsubscribeTrayQuit).toHaveBeenCalledTimes(1);
    expect(mocks.unsubscribeTrayMood).toHaveBeenCalledTimes(1);
  });
});
