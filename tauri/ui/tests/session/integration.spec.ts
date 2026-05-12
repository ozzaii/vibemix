/* Phase 12 Wave 4 — full settings-drawer integration spec (Plan 12-05 §7.4).
 *
 * End-to-end inside jsdom:
 *   1. Mock the @tauri-apps/api invoke + listen surfaces.
 *   2. Mount the session layout under a host element.
 *   3. Mount the settings drawer onto document.body.
 *   4. Simulate a settings boot payload (write into SessionState via
 *      `applySettingsState`) — drawer must read these values when opened.
 *   5. Open the drawer (programmatically via openSettings).
 *   6. Click a rocker option (interaction mode "coach") — assert that
 *      `forward_ipc_to_sidecar` was invoked with `ipc.settings.set`.
 *   7. Close the drawer — assert state preserved (settings unchanged).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (_cmd: string, _args?: unknown) => undefined),
}));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
}));

import { invoke as invokeMock_ } from "@tauri-apps/api/core";
import { listen as listenMock_ } from "@tauri-apps/api/event";
// Cast the mock back to its vi.fn handle.
const invokeMock = invokeMock_ as unknown as ReturnType<typeof vi.fn>;
const listenMock = listenMock_ as unknown as ReturnType<typeof vi.fn>;

import { mountSessionLayout } from "../../src/session/SessionLayout.js";
import {
  _resetDrawerForTests,
  closeSettings,
  mountSettingsDrawer,
  openSettings,
} from "../../src/settings/SettingsDrawer.js";
import {
  _resetSettingsUIStateForTests,
  getSettingsUIState,
} from "../../src/settings/state.js";
import {
  _resetSessionStateForTests,
  getSessionState,
} from "../../src/session/state.js";
import { applySettingsState } from "../../src/session/ws-bridge.js";

beforeEach(() => {
  invokeMock.mockClear();
  listenMock.mockClear();
  _resetDrawerForTests();
  _resetSettingsUIStateForTests();
  _resetSessionStateForTests();
  document.body.replaceChildren();
});

afterEach(() => {
  _resetDrawerForTests();
  _resetSettingsUIStateForTests();
  _resetSessionStateForTests();
  document.body.replaceChildren();
});

describe("Phase 12 — session + drawer integration", () => {
  it("boots session → opens drawer → emits ipc.settings.set on rocker change → close preserves state", async () => {
    // 1. Mount the session layout.
    const host = document.createElement("div");
    document.body.append(host);
    mountSessionLayout(host);

    // 2. Mount the drawer (router does this in production).
    mountSettingsDrawer(document.body);

    // 3. Hydrate SessionState.settings via the bridge applier — mimics
    //    the sidecar's boot `ipc.settings.state` broadcast.
    applySettingsState({
      voice: "puck",
      mode: "hype",
      genre: "techno",
      output_device_id: null,
      output_profile: "hp",
      retention_days: 14,
      push_to_mute_hotkey: "cmd+shift+m",
      muted: false,
    });

    expect(getSessionState().settings.voice).toBe("puck");
    expect(getSessionState().settings.retention_days).toBe(14);

    // 4. Open the drawer (titlebar gear click in production; openSettings
    //    is the public API the gear handler calls).
    openSettings();
    expect(getSettingsUIState().open).toBe(true);

    // 5. Click the COACH rocker option (interaction mode).
    const coachBtn = Array.from(
      document.querySelectorAll<HTMLElement>(
        '.vmx-settings-drawer .vmx-rocker__seg',
      ),
    ).find((el) => el.dataset.id === "coach");
    expect(coachBtn).toBeTruthy();
    coachBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    // Allow microtasks to flush — sendSettings is async (emitIpc → invoke).
    await Promise.resolve();
    await Promise.resolve();

    // 6. Assert forward_ipc_to_sidecar was invoked at least once with
    //    a message carrying ipc.settings.set and payload field=mode,
    //    value=coach.
    expect(invokeMock).toHaveBeenCalled();
    const settingsSetCall = invokeMock.mock.calls.find((c) => {
      const args = c[1] as { message?: { type?: string; payload?: unknown } };
      return args?.message?.type === "ipc.settings.set";
    });
    expect(settingsSetCall).toBeDefined();
    const payload = (
      settingsSetCall![1] as {
        message: { payload: { field: string; value: unknown } };
      }
    ).message.payload;
    expect(payload.field).toBe("mode");
    expect(payload.value).toBe("coach");

    // 7. Close the drawer — UI state flips; SessionState.settings is
    //    unaffected by the close (the rocker click queued an ipc.settings.set;
    //    the sidecar's later ipc.settings.state ack would persist the new
    //    value, but that's a separate broadcast we don't simulate here).
    closeSettings();
    expect(getSettingsUIState().open).toBe(false);
    // The SessionState reflects whatever we last hydrated — the optimistic
    // local write happens via the sidecar round-trip, not the drawer.
    expect(getSessionState().settings.voice).toBe("puck");
  });

  it("retention slider click emits ipc.settings.set with retention_days", async () => {
    const host = document.createElement("div");
    document.body.append(host);
    mountSessionLayout(host);
    mountSettingsDrawer(document.body);

    applySettingsState({
      voice: "kore",
      mode: "hype",
      genre: "techno",
      output_device_id: null,
      output_profile: "hp",
      retention_days: 1,
      push_to_mute_hotkey: "cmd+shift+m",
      muted: false,
    });

    openSettings();
    invokeMock.mockClear();

    // Click the 30d knob (idx 4).
    const knobs = document.querySelectorAll<HTMLElement>(
      ".vmx-retention__knob",
    );
    expect(knobs.length).toBe(6);
    knobs[4]!.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    await Promise.resolve();
    await Promise.resolve();

    const settingsSetCall = invokeMock.mock.calls.find((c) => {
      const args = c[1] as { message?: { type?: string } };
      return args?.message?.type === "ipc.settings.set";
    });
    expect(settingsSetCall).toBeDefined();
    const payload = (
      settingsSetCall![1] as {
        message: { payload: { field: string; value: unknown } };
      }
    ).message.payload;
    expect(payload.field).toBe("retention_days");
    expect(payload.value).toBe(30);
  });

  it("Re-run wizard click opens confirm dialog; confirm fires ipc.wizard.start", async () => {
    const host = document.createElement("div");
    document.body.append(host);
    mountSessionLayout(host);
    mountSettingsDrawer(document.body);

    applySettingsState({
      voice: "kore",
      mode: "hype",
      genre: "techno",
      output_device_id: null,
      output_profile: "hp",
      retention_days: 7,
      push_to_mute_hotkey: "cmd+shift+m",
      muted: false,
    });

    openSettings();

    // Click "Re-run wizard" — opens the confirm modal.
    const buttons = Array.from(
      document.querySelectorAll<HTMLElement>(
        ".vmx-settings-drawer__btn",
      ),
    );
    const reRunBtn = buttons.find((b) =>
      (b.textContent ?? "").includes("RE-RUN"),
    );
    expect(reRunBtn).toBeTruthy();
    reRunBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(getSettingsUIState().confirmDialog).toBe("re-run-calibration");
    expect(document.querySelector(".vmx-confirm__dialog")).toBeTruthy();

    invokeMock.mockClear();

    // Click the confirm button.
    const confirmBtn = document.querySelector<HTMLElement>(
      '.vmx-confirm__btn[data-kind="confirm"]',
    );
    expect(confirmBtn).toBeTruthy();
    confirmBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    await Promise.resolve();
    await Promise.resolve();

    const wizardCall = invokeMock.mock.calls.find((c) => {
      const args = c[1] as { message?: { type?: string } };
      return args?.message?.type === "ipc.wizard.start";
    });
    expect(wizardCall).toBeDefined();
    // Drawer closed by emitWizardStart after the ack.
    expect(getSettingsUIState().open).toBe(false);
    expect(getSettingsUIState().confirmDialog).toBeNull();
  });
});
