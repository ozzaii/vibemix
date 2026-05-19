/* help-group.spec.ts — impeccable Wave 6 (closes H10 "help &
 * documentation").
 *
 * Pins:
 *   - HELP group renders inside SettingsDrawer with the expected header.
 *   - Each row renders with the expected label.
 *   - GitHub row carries the public repo URL in its title (so the click
 *     path is observable even if the capability allowlist isn't wired).
 *   - About row shows the version + build date constants.
 *   - The KEYBOARD SHORTCUTS row, when clicked, mounts the shortcuts
 *     overlay. */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock @tauri-apps/api/core before any drawer imports — drawer pulls in
// `invoke` for rebind_hotkey + the help-group shell-open calls.
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async () => undefined),
  convertFileSrc: (p: string): string => `asset://localhost${p}`,
}));
vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
}));
vi.mock("../../src/ipc/client.js", () => ({
  emitIpc: vi.fn(async () => undefined),
  sendIpcRequest: vi.fn(() => new Promise(() => undefined)),
  subscribeIpc: vi.fn(async () => () => {}),
}));

import {
  HelpGroup,
  GITHUB_REPO_URL,
  VIBEMIX_BUILD_DATE,
  VIBEMIX_VERSION,
} from "../../src/settings/components/help-group.js";
import {
  _resetDrawerForTests,
  mountSettingsDrawer,
  openSettings,
} from "../../src/settings/SettingsDrawer.js";
import {
  _resetSettingsUIStateForTests,
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

describe("HelpGroup standalone (H10)", () => {
  it("renders the HELP header and the expected row labels", () => {
    // 2026-05-19 /impeccable critique round 4 (Kaan: H10 final): added
    // DOCS row above the audio-routing checklist; renamed GITHUB row
    // to SOURCE so the two intents (read the guide vs browse the code)
    // are distinguishable in the help surface.
    const group = HelpGroup();
    document.body.append(group);
    const header = group.querySelector(".vmx-settings-group__header");
    expect(header?.textContent).toContain("HELP");

    const labels = Array.from(
      group.querySelectorAll<HTMLElement>(".vmx-help-row__label"),
    ).map((el) => el.textContent);
    expect(labels).toContain("KEYBOARD SHORTCUTS");
    expect(labels).toContain("DOCS");
    expect(labels).toContain("TROUBLESHOOT AUDIO");
    expect(labels).toContain("BLACKHOLE ROUTED?");
    expect(labels).toContain("SCREEN RECORDING?");
    expect(labels).toContain("DJAY PRO RUNNING?");
    expect(labels).toContain("SOURCE");
    expect(labels).toContain("ABOUT");
  });

  it("DOCS + SOURCE rows both route to the public repo URL", () => {
    const group = HelpGroup();
    document.body.append(group);
    const rows = Array.from(
      group.querySelectorAll<HTMLElement>(".vmx-help-row"),
    );
    const docs = rows.find((r) =>
      r.querySelector(".vmx-help-row__label")?.textContent?.includes("DOCS"),
    );
    expect(docs).toBeTruthy();
    expect(docs?.getAttribute("title")).toContain("docs");
    expect(docs?.getAttribute("aria-label")).toContain("docs");

    const source = rows.find((r) =>
      r.querySelector(".vmx-help-row__label")?.textContent?.includes("SOURCE"),
    );
    expect(source).toBeTruthy();
    expect(source?.getAttribute("title")).toContain("github");
    expect(source?.getAttribute("aria-label")).toContain("github");
    const sub = source?.querySelector(".vmx-help-row__sub")?.textContent;
    expect(sub).toContain("bravoh-ai/vibemix");
    expect(GITHUB_REPO_URL).toBe("https://github.com/bravoh-ai/vibemix");
  });

  it("ABOUT row shows the version + build-date constants", () => {
    const group = HelpGroup();
    document.body.append(group);
    const rows = Array.from(
      group.querySelectorAll<HTMLElement>(".vmx-help-row"),
    );
    const about = rows.find((r) =>
      r.querySelector(".vmx-help-row__label")?.textContent?.includes("ABOUT"),
    );
    expect(about).toBeTruthy();
    const sub = about?.querySelector(".vmx-help-row__sub")?.textContent ?? "";
    expect(sub).toContain(VIBEMIX_VERSION);
    expect(sub).toContain(VIBEMIX_BUILD_DATE);
  });

  it("KEYBOARD SHORTCUTS row, when clicked, mounts the shortcuts overlay", () => {
    const group = HelpGroup();
    document.body.append(group);
    const rows = Array.from(
      group.querySelectorAll<HTMLElement>(".vmx-help-row"),
    );
    const shortcuts = rows.find((r) =>
      r
        .querySelector(".vmx-help-row__label")
        ?.textContent?.includes("KEYBOARD SHORTCUTS"),
    );
    expect(shortcuts).toBeTruthy();
    expect(document.querySelector(".vmx-shortcuts-backdrop")).toBeNull();
    shortcuts!.click();
    expect(document.querySelector(".vmx-shortcuts-backdrop")).toBeTruthy();
    expect(document.querySelector(".vmx-shortcuts-panel")).toBeTruthy();
  });

  it("checklist rows accept status dots and render them", () => {
    const group = HelpGroup({
      blackhole: "ok",
      screenRecording: "fault",
      djay: "warn",
    });
    document.body.append(group);
    const dots = Array.from(
      group.querySelectorAll<HTMLElement>(".vmx-help-row__dot"),
    );
    expect(dots.length).toBe(3);
    expect(dots.map((d) => d.dataset.status)).toEqual([
      "ok",
      "fault",
      "warn",
    ]);
  });
});

describe("HELP group inside SettingsDrawer (H10)", () => {
  it("HELP group renders inside the drawer body when opened", () => {
    mountSettingsDrawer(document.body);
    openSettings();
    const drawer = document.querySelector<HTMLElement>(
      ".vmx-settings-drawer",
    );
    expect(drawer).toBeTruthy();
    // Find HELP group by its header text since the section is wrapped.
    const helpGroup = drawer?.querySelector<HTMLElement>(
      '[data-component="help-group"]',
    );
    expect(helpGroup).toBeTruthy();
    expect(helpGroup?.querySelector(".vmx-settings-group__header")?.textContent)
      .toContain("HELP");
  });
});
